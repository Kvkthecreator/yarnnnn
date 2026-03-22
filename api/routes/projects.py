"""
Project routes — ADR-119 Phase 2 + Phase 4 + ADR-127

Cross-agent collaboration projects. CRUD over /api/projects.

Endpoints:
- GET /projects — list all projects
- GET /projects/{slug} — project detail (parsed PROJECT.md + contributors + assemblies)
- GET /projects/{slug}/activity — project activity timeline
- GET /projects/{slug}/outputs — list assemblies with parsed manifests (P4b)
- GET /projects/{slug}/outputs/{folder} — single assembly detail with content (P4b)
- GET /projects/{slug}/files — list workspace files under /projects/{slug}/ (ADR-124 P4)
- GET /projects/{slug}/files/{path} — read specific file content (ADR-124 P4)
- GET /projects/{slug}/contributions/{agent_slug} — contribution files with content (P4b)
- POST /projects — create project
- POST /projects/{slug}/share — share a file to project user_shared/ (ADR-127)
- PATCH /projects/{slug} — update PROJECT.md fields
- DELETE /projects/{slug} — archive project
"""

import json as _json
import logging
import re
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

from services.supabase import UserClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PROJECT.md field extractors (inlined from deleted routes/dashboard.py)
# ---------------------------------------------------------------------------

def _extract_title(content: str) -> str:
    """Extract title (first H1) from PROJECT.md content."""
    for line in (content or "").split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _extract_type_key(content: str) -> str | None:
    """Extract type_key from PROJECT.md content without full parse."""
    match = re.search(r'\*\*Type\*\*:\s*(\S+)', content or "")
    return match.group(1) if match else None


def _extract_purpose(content: str) -> str | None:
    """Extract Purpose from PROJECT.md Objective section."""
    in_objective = False
    for line in (content or "").split("\n"):
        if line.strip().startswith("## Objective"):
            in_objective = True
            continue
        if in_objective and line.strip().startswith("## "):
            break
        if in_objective and "**Purpose**:" in line:
            return line.split("**Purpose**:", 1)[1].strip()
    return None


# =============================================================================
# ADR-128 Phase 6: Cognitive state parsing helpers
# =============================================================================

# Regex for contributor self-assessment fields:
# **Mandate**: description (high|medium|low — optional reason)
_ASSESSMENT_FIELD_RE = re.compile(
    r"\*\*(\w[\w ]*)\*\*:\s*(.+?)\s*\((high|medium|low)(?:\s*[—–-]\s*(.+?))?\)",
    re.IGNORECASE,
)

# Map field names from self_assessment.md to API field names
_FIELD_NAME_MAP = {
    "mandate": "mandate",
    "domain fitness": "fitness",
    "context currency": "currency",
    "output confidence": "confidence",
}


def _parse_self_assessment(content: str) -> Optional[dict]:
    """Parse self_assessment.md → cognitive state dict with trajectory.

    Returns:
        {
            "mandate": {"level": "high", "reason": "..."},
            "fitness": {"level": "medium", "reason": "..."},
            "currency": {"level": "high"},
            "confidence": {"level": "medium", "reason": "..."},
            "confidence_trajectory": ["medium", "high", "high", "low", "high"],
        }
        or None if no parseable assessment found.
    """
    if not content or "Not yet assessed" in content:
        return None

    # Split into entries by ## headers (each run is a ## section)
    entries = re.split(r"(?=^## )", content, flags=re.MULTILINE)
    entries = [e.strip() for e in entries if e.strip() and e.strip().startswith("##")]

    if not entries:
        return None

    # Parse latest entry (first one — newest first convention)
    latest = entries[0]
    state = {}
    for match in _ASSESSMENT_FIELD_RE.finditer(latest):
        field_name = match.group(1).strip().lower()
        api_name = _FIELD_NAME_MAP.get(field_name)
        if api_name:
            entry = {"level": match.group(3).lower()}
            reason = match.group(4)
            if reason:
                entry["reason"] = reason.strip()[:120]
            state[api_name] = entry

    if not state:
        return None

    # Build confidence trajectory from all entries (up to 5)
    trajectory = []
    for entry_text in entries[:5]:
        for m in _ASSESSMENT_FIELD_RE.finditer(entry_text):
            if m.group(1).strip().lower() == "output confidence":
                trajectory.append(m.group(3).lower())
                break

    if trajectory:
        state["confidence_trajectory"] = trajectory

    return state


def _parse_pm_assessment(content: str) -> Optional[dict]:
    """Parse project_assessment.md → PM cognitive state.

    PM assessment may be JSON (PM produces JSON) or structured markdown.
    Returns:
        {
            "layers": {
                "commitment": "satisfied"|"broken"|"unknown",
                "structure": ...,
                "context": ...,
                "quality": ...,
                "readiness": ...,
            },
            "constraint_summary": "first broken layer summary",
            "raw_assessment": "full text (capped)",
        }
        or None if no assessment.
    """
    if not content or "No assessment yet" in content:
        return None

    raw = content[:2000]
    layer_names = ["commitment", "structure", "context", "quality", "readiness"]

    # Try JSON parse first (PM often produces JSON)
    try:
        data = _json.loads(content)
        if isinstance(data, dict):
            layers = {}
            constraint_summary = None
            for ln in layer_names:
                layer_data = data.get(ln) or data.get(f"layer_{ln}") or {}
                if isinstance(layer_data, dict):
                    status = layer_data.get("status", "unknown")
                    if status in ("satisfied", "ok", "healthy", "green"):
                        layers[ln] = "satisfied"
                    elif status in ("broken", "blocked", "red", "constraint"):
                        layers[ln] = "broken"
                        if not constraint_summary:
                            constraint_summary = (
                                layer_data.get("summary")
                                or layer_data.get("assessment")
                                or layer_data.get("reason")
                                or ""
                            )[:200]
                    else:
                        layers[ln] = "unknown"
                elif isinstance(layer_data, str):
                    lower = layer_data.lower()
                    if any(w in lower for w in ("satisfied", "ok", "healthy")):
                        layers[ln] = "satisfied"
                    elif any(w in lower for w in ("broken", "blocked", "missing", "constraint")):
                        layers[ln] = "broken"
                        if not constraint_summary:
                            constraint_summary = layer_data[:200]
                    else:
                        layers[ln] = "unknown"
                else:
                    layers[ln] = "unknown"

            return {
                "layers": layers,
                "constraint_summary": constraint_summary,
                "raw_assessment": raw,
            }
    except (_json.JSONDecodeError, ValueError, TypeError):
        pass

    # Fallback: markdown heuristic — look for layer references
    layers = {}
    constraint_summary = None
    content_lower = content.lower()
    for ln in layer_names:
        # Look for patterns like "Layer 1 — Commitment: satisfied" or "✓ Commitment" or "✗ Context"
        if re.search(rf"[✓✔☑]\s*{ln}", content_lower):
            layers[ln] = "satisfied"
        elif re.search(rf"[✗✘☒]\s*{ln}", content_lower):
            layers[ln] = "broken"
            if not constraint_summary:
                # Try to grab text after the broken layer marker
                m = re.search(rf"[✗✘☒]\s*{ln}[:\s—–-]*(.{{1,200}})", content_lower)
                if m:
                    constraint_summary = m.group(1).strip()[:200]
        elif re.search(rf"layer.*{ln}.*(?:broken|blocked|missing|constraint)", content_lower):
            layers[ln] = "broken"
        elif re.search(rf"layer.*{ln}.*(?:satisfied|ok|healthy)", content_lower):
            layers[ln] = "satisfied"
        else:
            layers[ln] = "unknown"

    if all(v == "unknown" for v in layers.values()):
        # Couldn't parse layers — return raw only
        return {"layers": {ln: "unknown" for ln in layer_names}, "raw_assessment": raw}

    return {
        "layers": layers,
        "constraint_summary": constraint_summary,
        "raw_assessment": raw,
    }

router = APIRouter()


# =============================================================================
# Pydantic models
# =============================================================================

class ProjectObjective(BaseModel):
    deliverable: Optional[str] = None
    audience: Optional[str] = None
    format: Optional[str] = None
    purpose: Optional[str] = None


class ProjectContributor(BaseModel):
    agent_id: str
    expected_contribution: str = ""


class CreateProjectRequest(BaseModel):
    title: str
    objective: Optional[ProjectObjective] = None
    contributors: list[ProjectContributor] = Field(default_factory=list)
    assembly_spec: str = ""
    delivery: Optional[dict] = None


class UpdateProjectRequest(BaseModel):
    title: Optional[str] = None
    objective: Optional[ProjectObjective] = None
    contributors: Optional[list[ProjectContributor]] = None
    assembly_spec: Optional[str] = None
    delivery: Optional[dict] = None


# =============================================================================
# Routes
# =============================================================================

@router.get("")
async def list_projects(user: UserClient):
    """List all projects for the user — parsed from PROJECT.md content."""
    try:
        # Query workspace_files for /projects/*/PROJECT.md (include content for parsing)
        result = (
            user.client.table("workspace_files")
            .select("path, content, updated_at")
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
                content = row.get("content", "")
                projects.append({
                    "project_slug": slug,
                    "title": _extract_title(content),
                    "type_key": _extract_type_key(content),
                    "purpose": _extract_purpose(content),
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
    contribution_counts = {}
    for cs in contributor_slugs:
        files = await pw.list_contributions(cs)
        contribution_counts[cs] = len(files)

    assemblies = await pw.list_assemblies()

    # ADR-124: Enrich contributors with full agent data for Members display.
    # PROJECT.md only stores agent_slug + expected_contribution — resolve to full agent record.
    enriched_contributors = project.get("contributors", [])
    try:
        from services.workspace import get_agent_slug as _gas
        agents_result = user.client.table("agents").select(
            "id, title, role, scope, mode, status, origin, schedule, "
            "last_run_at, created_at, updated_at, avatar_url"
        ).eq("user_id", user.user_id).execute()
        # Build slug → agent map for O(1) lookup
        slug_to_agent = {}
        id_to_agent = {}
        for agent in (agents_result.data or []):
            slug_to_agent[_gas(agent)] = agent
            id_to_agent[agent["id"]] = agent
        for c in enriched_contributors:
            agent = None
            if c.get("agent_id"):
                agent = id_to_agent.get(c["agent_id"])
            elif c.get("agent_slug"):
                agent = slug_to_agent.get(c["agent_slug"])
            if agent:
                c["agent_id"] = agent.get("id")
                c["title"] = agent.get("title")
                c["role"] = agent.get("role")
                c["scope"] = agent.get("scope")
                c["mode"] = agent.get("mode")
                c["status"] = agent.get("status", "active")
                c["origin"] = agent.get("origin")
                c["schedule"] = agent.get("schedule")
                c["last_run_at"] = agent.get("last_run_at")
                c["created_at"] = agent.get("created_at")
                c["avatar_url"] = agent.get("avatar_url")
    except Exception:
        pass

    # Enrich contributors with workspace identity data (AGENT.md summary, thesis, seniority)
    try:
        from services.workspace import AgentWorkspace, get_agent_slug as _gas2
        for c in enriched_contributors:
            agent_slug = c.get("agent_slug")
            agent_id = c.get("agent_id")
            if not agent_slug:
                continue
            try:
                ws = AgentWorkspace(user.client, user.user_id, agent_slug)
                # AGENT.md → first non-header paragraph as bio
                agent_md = await ws.read("AGENT.md")
                if agent_md:
                    lines = agent_md.strip().split("\n")
                    bio_lines = [l.strip() for l in lines if l.strip() and not l.strip().startswith("#") and not l.strip().startswith("---")]
                    c["bio"] = bio_lines[0][:200] if bio_lines else None
                # thesis.md → first 150 chars
                thesis = await ws.read("thesis.md")
                if thesis:
                    clean = thesis.strip().split("\n")
                    thesis_lines = [l.strip() for l in clean if l.strip() and not l.strip().startswith("#")]
                    c["thesis_snippet"] = thesis_lines[0][:150] if thesis_lines else None
                # Seniority from run stats
                if agent_id:
                    runs_result = user.client.table("agent_runs").select(
                        "id, status, edit_distance_score"
                    ).eq("agent_id", agent_id).execute()
                    runs = runs_result.data or []
                    total_runs = len(runs)
                    approved = sum(1 for r in runs if r.get("status") in ("approved", "delivered", "staged"))
                    approval_rate = (approved / total_runs * 100) if total_runs > 0 else 0
                    if total_runs >= 10 and approval_rate >= 80:
                        seniority = "senior"
                    elif total_runs >= 5 and approval_rate >= 60:
                        seniority = "associate"
                    else:
                        seniority = "new"
                    c["seniority"] = seniority
                    c["total_runs"] = total_runs
                    c["approval_rate"] = round(approval_rate)
                # ADR-128 Phase 6: Cognitive state from self_assessment.md
                if c.get("role") != "pm":
                    sa_content = await ws.read("memory/self_assessment.md")
                    if sa_content:
                        cognitive = _parse_self_assessment(sa_content)
                        if cognitive:
                            c["cognitive_state"] = cognitive
            except Exception:
                pass  # Non-critical — card still works without identity data
    except Exception:
        pass

    project["contributors"] = enriched_contributors

    # ADR-123 Phase 3: PM intelligence — quality assessment + briefs
    pm_intelligence = {}
    quality_md = await pw.read("memory/quality_assessment.md")
    if quality_md:
        pm_intelligence["quality_assessment"] = quality_md
    briefs = {}
    for cs in contributor_slugs:
        brief = await pw.read_brief(cs)
        if brief:
            briefs[cs] = brief
    if briefs:
        pm_intelligence["briefs"] = briefs

    # ADR-128 Phase 6: PM cognitive state from project_assessment.md
    project_cognitive_state = None
    try:
        pa_content = await pw.read("memory/project_assessment.md")
        if pa_content:
            project_cognitive_state = _parse_pm_assessment(pa_content)
    except Exception:
        pass

    return {
        "project_slug": slug,
        "project": project,
        "contribution_counts": contribution_counts,
        "assembly_count": len(assemblies),
        "pm_intelligence": pm_intelligence if pm_intelligence else None,
        "project_cognitive_state": project_cognitive_state,
    }


@router.post("", status_code=201)
async def create_project(body: CreateProjectRequest, user: UserClient):
    """Create a new project via scaffold_project() — single path for all creation.

    Delegates to project_registry.scaffold_project() which handles:
    - PROJECT.md creation
    - Contributor workspace seeding
    - PM agent auto-creation (for multi-agent projects)
    - Agent creation from type specs
    """
    from services.project_registry import scaffold_project
    from services.workspace import get_agent_slug

    # Resolve contributor agent_ids to {agent_slug, agent_id, expected_contribution}
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

    objective = body.objective.model_dump(exclude_none=True) if body.objective else {}

    result = await scaffold_project(
        client=user.client,
        user_id=user.user_id,
        type_key="custom",
        title_override=body.title,
        objective_override=objective,
        contributors=contributors,
        assembly_spec_override=body.assembly_spec or None,
        delivery_override=body.delivery,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=409 if result.get("reason") == "already_exists" else 500,
            detail=result.get("message", "Failed to create project"),
        )

    return {
        "project_slug": result["project_slug"],
        "title": body.title,
        "contributors": result.get("contributors_created", []),
        "pm_agent_id": result.get("pm_agent_id"),
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
    objective = existing.get("objective", {})
    if body.objective:
        objective.update(body.objective.model_dump(exclude_none=True))

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
        objective=objective,
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
# ADR-129: Expanded to include agent lifecycle events (enriched with project_slug)
PROJECT_EVENT_TYPES = [
    # PM coordination events (always had project_slug)
    "project_heartbeat",
    "project_assembled",
    "project_escalated",
    "project_contributor_advanced",
    "project_quality_assessed",
    "project_contributor_steered",
    "project_file_triaged",
    "pm_pulsed",
    # Agent lifecycle events (ADR-129: now enriched with project_slug)
    "agent_pulsed",
    "agent_run",
    "agent_scheduled",
    "agent_generated",
    "agent_approved",
    "agent_rejected",
    # Composer events that carry project_slug
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
    for folder_name in reversed(folders[-limit:]):
        manifest_raw = await pw.read(f"assembly/{folder_name}/manifest.json")
        if not manifest_raw:
            continue
        try:
            manifest = _json.loads(manifest_raw)
        except _json.JSONDecodeError:
            continue

        folder_id = folder_name
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


@router.get("/{slug}/files")
async def get_project_files(slug: str, user: UserClient):
    """ADR-124 Phase 4: List all workspace files under /projects/{slug}/ for the Context tab."""
    from services.workspace import ProjectWorkspace

    pw = ProjectWorkspace(user.client, user.user_id, slug)

    try:
        # Query all files under this project path with metadata
        result = (
            user.client.table("workspace_files")
            .select("path, summary, content_type, updated_at, lifecycle")
            .eq("user_id", user.user_id)
            .like("path", f"/projects/{slug}/%")
            .neq("lifecycle", "archived")
            .order("path")
            .limit(200)
            .execute()
        )
        files = result.data or []

        # Strip project prefix for relative paths
        prefix = f"/projects/{slug}/"
        for f in files:
            f["relative_path"] = f["path"][len(prefix):] if f["path"].startswith(prefix) else f["path"]

        return {"files": files, "total": len(files)}
    except Exception as e:
        return {"files": [], "total": 0, "error": str(e)}


@router.get("/{slug}/files/{file_path:path}")
async def get_project_file_content(slug: str, file_path: str, user: UserClient):
    """ADR-124 Phase 4: Read a specific file's content from the project workspace."""
    from services.workspace import ProjectWorkspace

    pw = ProjectWorkspace(user.client, user.user_id, slug)
    content = await pw.read(file_path)

    if content is None:
        raise HTTPException(status_code=404, detail="File not found")

    return {"path": file_path, "content": content}


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


# =============================================================================
# SHARE FILE — ADR-127: User-Shared File Staging
# =============================================================================

class ShareFileRequest(BaseModel):
    filename: str = Field(..., description="Name for the shared file (e.g., 'brief.md')")
    content: str = Field(..., description="Text content of the file")


@router.post("/projects/{slug}/share")
async def share_file_to_project(
    slug: str,
    body: ShareFileRequest,
    user: UserClient = None,
):
    """
    ADR-127: Share a file to a project's user_shared/ staging area.

    Files land in /projects/{slug}/user_shared/{filename} with ephemeral lifecycle (30-day TTL).
    PM triages: promotes to contributions/memory/knowledge, or lets expire.
    """
    from services.workspace import ProjectWorkspace

    filename = body.filename.strip()
    if not filename:
        raise HTTPException(status_code=400, detail="filename is required")
    content = body.content
    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="content is required")

    # Sanitize filename — lowercase kebab, no path traversal
    import re
    safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '-', filename).strip('-')
    if not safe_filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    pw = ProjectWorkspace(user.client, user.user_id, slug)

    # Verify project exists
    project = await pw.read_project()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {slug}")

    # Write to user_shared/ (lifecycle auto-inferred as ephemeral by _infer_lifecycle)
    path = f"user_shared/{safe_filename}"
    await pw.write(path, content, summary=f"User shared: {safe_filename}")

    logger.info(f"[SHARE] User shared file {safe_filename} to project {slug}")

    return {
        "success": True,
        "path": f"/projects/{slug}/{path}",
        "filename": safe_filename,
        "message": f"File shared to project. PM will triage on next cycle.",
    }
