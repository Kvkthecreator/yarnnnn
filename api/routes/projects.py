"""
Project routes — ADR-119 Phase 2 + Phase 4

Cross-agent collaboration projects. CRUD over /api/projects.

Endpoints:
- GET /projects — list all projects
- GET /projects/{slug} — project detail (parsed PROJECT.md + contributors + assemblies)
- GET /projects/{slug}/activity — project activity timeline
- GET /projects/{slug}/outputs — list assemblies with parsed manifests (P4b)
- GET /projects/{slug}/outputs/{folder} — single assembly detail with content (P4b)
- GET /projects/{slug}/contributions/{agent_slug} — contribution files with content (P4b)
- POST /projects — create project
- PATCH /projects/{slug} — update PROJECT.md fields
- DELETE /projects/{slug} — archive project
"""

import json as _json
import logging
from fastapi import APIRouter, HTTPException, Query
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


# ADR-119 Phase 4: Project activity event types
PROJECT_EVENT_TYPES = [
    "project_heartbeat",
    "project_assembled",
    "project_escalated",
    "project_contributor_advanced",
    "duty_promoted",
]


@router.get("/{slug}/activity")
async def get_project_activity(slug: str, user: UserClient, limit: int = 20):
    """Activity timeline for a specific project — personified work log."""
    try:
        result = (
            user.client.table("activity_log")
            .select("id, event_type, summary, metadata, created_at")
            .eq("user_id", user.user_id)
            .in_("event_type", PROJECT_EVENT_TYPES)
            .filter("metadata->>project_slug", "eq", slug)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        activities = result.data or []
        return {"activities": activities, "total": len(activities)}
    except Exception as e:
        logger.error(f"[PROJECTS] Activity query failed for {slug}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch project activity")


# =============================================================================
# ADR-119 Phase 4b: Output + Contribution endpoints
# =============================================================================

@router.get("/{slug}/outputs")
async def list_project_outputs(slug: str, user: UserClient, limit: int = Query(default=20, le=50)):
    """List assemblies with parsed manifests — output history for the project."""
    from services.workspace import ProjectWorkspace

    pw = ProjectWorkspace(user.client, user.user_id, slug)
    folders = await pw.list_assemblies()

    outputs = []
    for full_folder in reversed(folders[-limit:]):
        manifest_raw = await pw.read(f"{full_folder}/manifest.json")
        if not manifest_raw:
            continue
        try:
            manifest = _json.loads(manifest_raw)
        except _json.JSONDecodeError:
            continue

        # Strip "assembly/" prefix for the folder identifier (matches detail URL param)
        folder_id = full_folder.removeprefix("assembly/")
        outputs.append({
            "folder": folder_id,
            "version": manifest.get("version", 0),
            "created_at": manifest.get("created_at"),
            "status": manifest.get("status", "active"),
            "files": manifest.get("files", []),
            "sources": manifest.get("sources", []),
            "delivery": manifest.get("delivery"),
        })

    return {"outputs": outputs, "total": len(outputs)}


@router.get("/{slug}/outputs/{folder}")
async def get_project_output(slug: str, folder: str, user: UserClient):
    """Single assembly detail — output.md content + full manifest."""
    from services.workspace import ProjectWorkspace

    pw = ProjectWorkspace(user.client, user.user_id, slug)

    content = await pw.read(f"assembly/{folder}/output.md")
    manifest_raw = await pw.read(f"assembly/{folder}/manifest.json")

    if not content and not manifest_raw:
        raise HTTPException(status_code=404, detail=f"Assembly not found: {folder}")

    manifest = None
    if manifest_raw:
        try:
            manifest = _json.loads(manifest_raw)
        except _json.JSONDecodeError:
            pass

    return {
        "folder": folder,
        "content": content or "",
        "manifest": manifest,
    }


@router.get("/{slug}/contributions/{agent_slug}")
async def get_project_contributions(slug: str, agent_slug: str, user: UserClient):
    """Contribution files with content for a specific contributor agent."""
    from services.workspace import ProjectWorkspace

    pw = ProjectWorkspace(user.client, user.user_id, slug)
    file_names = await pw.list_contributions(agent_slug)

    files = []
    for fname in file_names:
        file_content = await pw.read(f"contributions/{agent_slug}/{fname}")
        # Get metadata from workspace_files
        try:
            result = (
                user.client.table("workspace_files")
                .select("updated_at")
                .eq("user_id", user.user_id)
                .eq("path", f"/projects/{slug}/contributions/{agent_slug}/{fname}")
                .maybe_single()
                .execute()
            )
            updated_at = result.data.get("updated_at") if result and result.data else None
        except Exception:
            updated_at = None

        files.append({
            "path": fname,
            "content": file_content or "",
            "updated_at": updated_at,
        })

    return {"agent_slug": agent_slug, "files": files}
