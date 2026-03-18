"""
Project routes — ADR-119 Phase 2

Cross-agent collaboration projects. CRUD over /api/projects.

Endpoints:
- GET /projects — list all projects
- GET /projects/{slug} — project detail (parsed PROJECT.md + contributors + assemblies)
- POST /projects — create project
- PATCH /projects/{slug} — update PROJECT.md fields
- DELETE /projects/{slug} — archive project
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from services.supabase import UserClient

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Pydantic models
# =============================================================================

class ProjectIntent(BaseModel):
    deliverable: Optional[str] = None
    audience: Optional[str] = None
    format: Optional[str] = None
    purpose: Optional[str] = None


class ProjectContributor(BaseModel):
    agent_id: str
    expected_contribution: str = ""


class CreateProjectRequest(BaseModel):
    title: str
    intent: Optional[ProjectIntent] = None
    contributors: list[ProjectContributor] = Field(default_factory=list)
    assembly_spec: str = ""
    delivery: Optional[dict] = None


class UpdateProjectRequest(BaseModel):
    title: Optional[str] = None
    intent: Optional[ProjectIntent] = None
    contributors: Optional[list[ProjectContributor]] = None
    assembly_spec: Optional[str] = None
    delivery: Optional[dict] = None


# =============================================================================
# Routes
# =============================================================================

@router.get("")
async def list_projects(user: UserClient):
    """List all projects for the user."""
    try:
        # Query workspace_files for /projects/*/PROJECT.md
        result = (
            user.client.table("workspace_files")
            .select("path, summary, updated_at, metadata")
            .eq("user_id", user.user_id)
            .like("path", "/projects/%/PROJECT.md")
            .in_("lifecycle", ["active", "delivered"])
            .order("updated_at", desc=True)
            .execute()
        )

        projects = []
        for row in (result.data or []):
            # Extract slug from path: /projects/{slug}/PROJECT.md
            path = row["path"]
            parts = path.split("/")
            if len(parts) >= 3:
                slug = parts[2]
                projects.append({
                    "project_slug": slug,
                    "summary": row.get("summary", ""),
                    "updated_at": row.get("updated_at"),
                })

        return {"projects": projects, "count": len(projects)}
    except Exception as e:
        logger.error(f"[PROJECTS] List failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to list projects")


@router.get("/{slug}")
async def get_project(slug: str, user: UserClient):
    """Get project detail: parsed PROJECT.md + contributors + assemblies."""
    from services.workspace import ProjectWorkspace

    pw = ProjectWorkspace(user.client, user.user_id, slug)
    project = await pw.read_project()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {slug}")

    contributor_slugs = await pw.list_contributors()
    contributions = {}
    for cs in contributor_slugs:
        files = await pw.list_contributions(cs)
        contributions[cs] = files

    assemblies = await pw.list_assemblies()

    return {
        "project_slug": slug,
        "project": project,
        "contributions": contributions,
        "assemblies": assemblies,
    }


@router.post("", status_code=201)
async def create_project(body: CreateProjectRequest, user: UserClient):
    """Create a new project."""
    from services.workspace import ProjectWorkspace, AgentWorkspace, get_project_slug, get_agent_slug
    import json as _json

    project_slug = get_project_slug(body.title)

    # Check if project already exists
    pw = ProjectWorkspace(user.client, user.user_id, project_slug)
    existing = await pw.read_project()
    if existing:
        raise HTTPException(status_code=409, detail=f"Project already exists: {project_slug}")

    # Resolve contributors
    contributors = []
    for c in body.contributors:
        try:
            result = (
                user.client.table("agents")
                .select("id, title")
                .eq("id", c.agent_id)
                .eq("user_id", user.user_id)
                .maybe_single()
                .execute()
            )
            if result and result.data:
                agent_slug = get_agent_slug(result.data)
                contributors.append({
                    "agent_slug": agent_slug,
                    "agent_id": c.agent_id,
                    "expected_contribution": c.expected_contribution,
                })
        except Exception as e:
            logger.warning(f"[PROJECTS] Contributor lookup failed: {c.agent_id}: {e}")

    # Write PROJECT.md
    intent = body.intent.model_dump(exclude_none=True) if body.intent else {}
    success = await pw.write_project(
        title=body.title,
        intent=intent,
        contributors=contributors,
        assembly_spec=body.assembly_spec,
        delivery=body.delivery or {},
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create project")

    # Seed contributor workspaces
    for c in contributors:
        try:
            agent_ws = AgentWorkspace(user.client, user.user_id, c["agent_slug"])
            existing_json = await agent_ws.read("memory/projects.json")
            if existing_json:
                try:
                    projects_list = _json.loads(existing_json)
                except _json.JSONDecodeError:
                    projects_list = []
            else:
                projects_list = []

            if not any(p.get("project_slug") == project_slug for p in projects_list):
                projects_list.append({
                    "project_slug": project_slug,
                    "title": body.title,
                    "expected_contribution": c["expected_contribution"],
                })

            await agent_ws.write(
                "memory/projects.json",
                _json.dumps(projects_list, indent=2),
                summary=f"Project memberships ({len(projects_list)} projects)",
                content_type="application/json",
            )
        except Exception as e:
            logger.warning(f"[PROJECTS] Failed to seed contributor {c['agent_slug']}: {e}")

    logger.info(f"[PROJECTS] Created project '{body.title}' ({project_slug})")

    return {
        "project_slug": project_slug,
        "title": body.title,
        "contributors": [{"agent_slug": c["agent_slug"], "agent_id": c["agent_id"]} for c in contributors],
    }


@router.patch("/{slug}")
async def update_project(slug: str, body: UpdateProjectRequest, user: UserClient):
    """Update PROJECT.md fields (merge update)."""
    from services.workspace import ProjectWorkspace

    pw = ProjectWorkspace(user.client, user.user_id, slug)
    existing = await pw.read_project()
    if not existing:
        raise HTTPException(status_code=404, detail=f"Project not found: {slug}")

    # Merge updates
    title = body.title or existing["title"]
    intent = existing.get("intent", {})
    if body.intent:
        intent.update(body.intent.model_dump(exclude_none=True))

    contributors = existing.get("contributors", [])
    if body.contributors is not None:
        from services.workspace import get_agent_slug
        contributors = []
        for c in body.contributors:
            try:
                result = (
                    user.client.table("agents")
                    .select("id, title")
                    .eq("id", c.agent_id)
                    .eq("user_id", user.user_id)
                    .maybe_single()
                    .execute()
                )
                if result and result.data:
                    agent_slug = get_agent_slug(result.data)
                    contributors.append({
                        "agent_slug": agent_slug,
                        "agent_id": c.agent_id,
                        "expected_contribution": c.expected_contribution,
                    })
            except Exception:
                pass

    assembly_spec = body.assembly_spec if body.assembly_spec is not None else existing.get("assembly_spec", "")
    delivery = body.delivery if body.delivery is not None else existing.get("delivery", {})

    success = await pw.write_project(
        title=title,
        intent=intent,
        contributors=contributors,
        assembly_spec=assembly_spec,
        delivery=delivery,
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update project")

    return {"project_slug": slug, "title": title, "updated": True}


@router.delete("/{slug}")
async def archive_project(slug: str, user: UserClient):
    """Archive a project (set lifecycle=archived on all project files)."""
    from services.workspace import ProjectWorkspace
    from datetime import datetime, timezone

    pw = ProjectWorkspace(user.client, user.user_id, slug)
    existing = await pw.read_project()
    if not existing:
        raise HTTPException(status_code=404, detail=f"Project not found: {slug}")

    # Set lifecycle=archived on all files under /projects/{slug}/
    try:
        user.client.table("workspace_files").update({
            "lifecycle": "archived",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq(
            "user_id", user.user_id
        ).like(
            "path", f"/projects/{slug}/%"
        ).execute()

        logger.info(f"[PROJECTS] Archived project: {slug}")
        return {"project_slug": slug, "archived": True}
    except Exception as e:
        logger.error(f"[PROJECTS] Archive failed: {slug}: {e}")
        raise HTTPException(status_code=500, detail="Failed to archive project")
