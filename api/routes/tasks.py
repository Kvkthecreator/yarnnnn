"""
Tasks routes — read-only views over recurrence declarations + thin scheduling index.

ADR-231 Phase 3.7 (atomic deletion alongside legacy task_pipeline / TaskWorkspace /
manage_task / task_types / task_derivation): this file rewrites to read from
the recurrence-declaration substrate (workspace_files YAML at natural-home
paths) + the thin tasks scheduling index, dispatching writes through
services.invocation_dispatcher and services.primitives.update_context.

The HTTP surface (`/api/tasks/*`) is preserved for the frontend until
Phase 3.8 renames URLs to `/api/recurrences/*`. The internal data model is
already the post-cutover model — this file is a translation layer.

Endpoints:
- GET /tasks - List user's recurrences
- GET /tasks/{slug} - Get recurrence detail
- POST /tasks/{slug}/run - Manually fire an invocation
- PUT /tasks/{slug} - Update recurrence (status / paused mapping)
- PATCH /tasks/{slug}/sources - Update declaration sources
- DELETE /tasks/{slug} - Archive recurrence
- GET /tasks/{slug}/outputs[/...] - Read output substrate at natural-home paths
- GET /tasks/{slug}/status - Run status from agent_runs
- POST /tasks/{slug}/repurpose - Repurpose latest output
- GET /tasks/{slug}/export - Export latest output (PDF/XLSX/etc.)
"""

from __future__ import annotations

import json as _json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.recurrence import (
    RecurrenceDeclaration,
    RecurrenceShape,
    walk_workspace_recurrences,
)
from services.recurrence_paths import resolve_paths
from services.supabase import UserClient
from services.workspace import UserMemory

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Response Models — frontend-facing shape preserved across cutover
# =============================================================================


class TaskUpdate(BaseModel):
    """Update payload accepted by PUT /tasks/{slug}.

    Only fields that map cleanly to the recurrence YAML are accepted; the
    legacy ManageTask multi-action surface dissolved per ADR-231 D5. Use
    UpdateContext(target='recurrence', ...) directly for richer changes.
    """

    status: Optional[str] = None
    schedule: Optional[str] = None


class TaskResponse(BaseModel):
    id: str
    slug: str
    status: str
    mode: Optional[str] = None  # legacy field — derived from declaration shape
    schedule: Optional[str] = None
    next_run_at: Optional[str] = None
    last_run_at: Optional[str] = None
    created_at: str
    updated_at: str
    title: Optional[str] = None
    type_key: Optional[str] = None  # vestigial — always None post-ADR-231
    output_kind: Optional[str] = None
    objective: Optional[dict] = None
    process: Optional[dict] = None
    agent_slugs: Optional[list] = None
    delivery: Optional[str] = None
    success_criteria: Optional[list] = None
    output_spec: Optional[list] = None
    context_reads: Optional[list] = None
    context_writes: Optional[list] = None
    phase: Optional[str] = None
    essential: bool = False  # vestigial — always False post-ADR-231
    sources: Optional[dict] = None
    run_log: Optional[str] = None
    deliverable_spec: Optional[dict] = None
    declaration_path: Optional[str] = None  # ADR-231: pointer to YAML truth
    shape: Optional[str] = None  # ADR-231: deliverable | accumulation | action | maintenance


class TaskOutputEntry(BaseModel):
    folder: str
    date: str
    status: str
    renderable: bool
    manifest: Optional[dict] = None


class TaskSectionEntry(BaseModel):
    slug: str
    title: Optional[str] = None
    kind: Optional[str] = None
    produced_at: Optional[str] = None
    source_files: list[str] = []


class TaskOutputLatest(BaseModel):
    content: Optional[str] = None
    html_content: Optional[str] = None
    date: Optional[str] = None
    manifest: Optional[dict] = None
    sys_manifest: Optional[dict] = None
    sections: list[TaskSectionEntry] = []


class TaskRunTriggered(BaseModel):
    triggered: bool
    task_slug: str


class RunStatusResponse(BaseModel):
    status: str
    current_step: int = 0
    total_steps: int = 0
    completed_steps: list[dict] = []
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


# =============================================================================
# Internal helpers
# =============================================================================


def _output_kind_for_shape(shape: RecurrenceShape) -> str:
    return {
        RecurrenceShape.DELIVERABLE: "produces_deliverable",
        RecurrenceShape.ACCUMULATION: "accumulates_context",
        RecurrenceShape.ACTION: "external_action",
        RecurrenceShape.MAINTENANCE: "system_maintenance",
    }[shape]


def _decl_to_response(
    row: dict,
    decl: Optional[RecurrenceDeclaration],
    *,
    run_log: Optional[str] = None,
    deliverable_spec: Optional[dict] = None,
) -> TaskResponse:
    """Build a TaskResponse from the scheduling-index row + declaration."""
    title = (decl.display_name if decl else None) or row["slug"]
    output_kind = _output_kind_for_shape(decl.shape) if decl else None
    objective = (
        {"prose": decl.objective} if decl and decl.objective else None
    )
    process = None
    if decl and decl.data.get("page_structure"):
        process = {"page_structure": decl.data["page_structure"]}

    return TaskResponse(
        id=str(row["id"]),
        slug=row["slug"],
        status=row["status"],
        mode="recurring" if decl and decl.schedule else "reactive",
        schedule=(decl.schedule if decl else row.get("schedule")) or None,
        next_run_at=row.get("next_run_at"),
        last_run_at=row.get("last_run_at"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        title=title,
        type_key=None,
        output_kind=output_kind,
        objective=objective,
        process=process,
        agent_slugs=decl.agents if decl else None,
        delivery=(
            decl.data.get("delivery") if decl and isinstance(decl.data.get("delivery"), str)
            else None
        ),
        success_criteria=None,
        output_spec=None,
        context_reads=decl.context_reads if decl else None,
        context_writes=decl.context_writes if decl else None,
        phase=None,
        essential=False,
        sources=decl.data.get("sources") if decl else None,
        run_log=run_log,
        deliverable_spec=deliverable_spec,
        declaration_path=decl.declaration_path if decl else row.get("declaration_path"),
        shape=decl.shape.value if decl else None,
    )


def _decl_for_slug(
    decls: list[RecurrenceDeclaration], slug: str
) -> Optional[RecurrenceDeclaration]:
    return next((d for d in decls if d.slug == slug), None)


def _strip_ws_prefix(p: str) -> str:
    return p[len("/workspace/"):] if p.startswith("/workspace/") else p


# =============================================================================
# List + Detail
# =============================================================================


@router.get("")
async def list_tasks(
    auth: UserClient,
    status: Optional[str] = None,
    limit: int = 100,
    include_system: bool = False,
) -> list[TaskResponse]:
    """List all recurrences (joined index + declaration walker).

    `include_system=true` includes back-office maintenance recurrences.
    """
    query = (
        auth.client.table("tasks")
        .select("id, slug, status, schedule, next_run_at, last_run_at, "
                "created_at, updated_at, declaration_path, paused")
        .eq("user_id", auth.user_id)
        .order("created_at", desc=True)
        .limit(limit)
    )
    if status:
        query = query.eq("status", status)
    rows = (query.execute()).data or []

    if not include_system:
        rows = [r for r in rows if not (r.get("slug") or "").startswith("back-office-")]

    decls = walk_workspace_recurrences(auth.client, auth.user_id)
    return [_decl_to_response(r, _decl_for_slug(decls, r["slug"])) for r in rows]


@router.get("/{slug}")
async def get_task(slug: str, auth: UserClient) -> TaskResponse:
    """Recurrence detail: index row + declaration + run log."""
    rows = (
        auth.client.table("tasks")
        .select("id, slug, status, schedule, next_run_at, last_run_at, "
                "created_at, updated_at, declaration_path, paused")
        .eq("user_id", auth.user_id)
        .eq("slug", slug)
        .limit(1)
        .execute()
    ).data
    if not rows:
        raise HTTPException(status_code=404, detail="Task not found")
    row = rows[0]

    decls = walk_workspace_recurrences(auth.client, auth.user_id)
    decl = _decl_for_slug(decls, slug)
    if decl is None:
        return _decl_to_response(row, None)

    paths = resolve_paths(decl)
    um = UserMemory(auth.client, auth.user_id)
    run_log = await um.read(_strip_ws_prefix(paths.run_log_path))

    deliverable_spec = None
    deliverable_block = decl.data.get("deliverable")
    if isinstance(deliverable_block, dict):
        deliverable_spec = deliverable_block

    return _decl_to_response(row, decl, run_log=run_log, deliverable_spec=deliverable_spec)


# =============================================================================
# Update + Archive
# =============================================================================


@router.put("/{slug}")
async def update_task(
    slug: str,
    request: TaskUpdate,
    auth: UserClient,
) -> dict:
    """Update recurrence — maps to UpdateContext(target='recurrence', ...) for
    schedule changes; flips paused flag for status='paused' (legacy frontend)."""
    rows = (
        auth.client.table("tasks")
        .select("id, slug, status, declaration_path, paused")
        .eq("user_id", auth.user_id)
        .eq("slug", slug)
        .limit(1)
        .execute()
    ).data
    if not rows:
        raise HTTPException(status_code=404, detail="Task not found")
    row = rows[0]

    db_updates: dict = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if request.status is not None:
        if request.status not in ("active", "paused", "completed", "archived"):
            raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")
        # ADR-231 Phase 3.4: paused is an explicit flag, not a status.
        if request.status == "paused":
            db_updates["paused"] = True
            db_updates["status"] = "active"
        else:
            db_updates["paused"] = False
            db_updates["status"] = request.status
    if request.schedule is not None:
        db_updates["schedule"] = request.schedule

    auth.client.table("tasks").update(db_updates).eq("user_id", auth.user_id).eq(
        "slug", slug
    ).execute()

    # Mirror schedule + paused changes into the YAML declaration via
    # UpdateContext(target='recurrence', action='update'/'pause'/'resume').
    decls = walk_workspace_recurrences(auth.client, auth.user_id)
    decl = _decl_for_slug(decls, slug)
    if decl is not None:
        from services.primitives.update_context import handle_update_context

        if request.status == "paused":
            await handle_update_context(auth, {
                "target": "recurrence", "action": "pause",
                "shape": decl.shape.value, "slug": slug,
                "domain": decl.domain,
            })
        elif request.status in ("active",) and row.get("paused"):
            await handle_update_context(auth, {
                "target": "recurrence", "action": "resume",
                "shape": decl.shape.value, "slug": slug,
                "domain": decl.domain,
            })
        if request.schedule is not None:
            await handle_update_context(auth, {
                "target": "recurrence", "action": "update",
                "shape": decl.shape.value, "slug": slug,
                "domain": decl.domain,
                "changes": {"schedule": request.schedule},
            })

    return {"success": True}


@router.delete("/{slug}")
async def archive_task(slug: str, auth: UserClient) -> dict:
    """Archive a recurrence — marks the index row archived and tells
    UpdateContext to remove the YAML declaration."""
    rows = (
        auth.client.table("tasks")
        .select("id, slug, declaration_path")
        .eq("user_id", auth.user_id)
        .eq("slug", slug)
        .limit(1)
        .execute()
    ).data
    if not rows:
        raise HTTPException(status_code=404, detail="Task not found")

    auth.client.table("tasks").update({
        "status": "archived",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("user_id", auth.user_id).eq("slug", slug).execute()

    decls = walk_workspace_recurrences(auth.client, auth.user_id)
    decl = _decl_for_slug(decls, slug)
    if decl is not None:
        from services.primitives.update_context import handle_update_context
        await handle_update_context(auth, {
            "target": "recurrence", "action": "archive",
            "shape": decl.shape.value, "slug": slug,
            "domain": decl.domain,
        })

    return {"success": True}


@router.patch("/{slug}/sources")
async def update_task_sources(
    slug: str,
    sources: dict,
    auth: UserClient,
) -> dict:
    """Update the recurrence's per-platform source selection."""
    decls = walk_workspace_recurrences(auth.client, auth.user_id)
    decl = _decl_for_slug(decls, slug)
    if decl is None:
        raise HTTPException(status_code=404, detail="Task not found")

    from services.primitives.update_context import handle_update_context
    await handle_update_context(auth, {
        "target": "recurrence", "action": "update",
        "shape": decl.shape.value, "slug": slug,
        "domain": decl.domain,
        "changes": {"sources": sources},
    })
    return {"success": True}


# =============================================================================
# Run trigger + status
# =============================================================================


@router.post("/{slug}/run")
async def trigger_task_run(slug: str, auth: UserClient) -> TaskRunTriggered:
    """Fire an invocation against the recurrence declaration immediately."""
    rows = (
        auth.client.table("tasks")
        .select("id, slug, status")
        .eq("user_id", auth.user_id)
        .eq("slug", slug)
        .limit(1)
        .execute()
    ).data
    if not rows:
        raise HTTPException(status_code=404, detail="Task not found")
    if rows[0]["status"] != "active":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot trigger run: status is '{rows[0]['status']}'",
        )

    try:
        from services.supabase import get_service_client
        from services.invocation_dispatcher import dispatch
        svc_client = get_service_client()
        decls = walk_workspace_recurrences(svc_client, auth.user_id)
        decl = _decl_for_slug(decls, slug)
        if decl is None:
            raise HTTPException(status_code=404, detail=f"No declaration for slug '{slug}'")
        result = await dispatch(svc_client, auth.user_id, decl)
        logger.info(f"[TASKS] inline dispatch for {slug}: {result.get('status', '?')}")
        return TaskRunTriggered(triggered=True, task_slug=slug)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[TASKS] inline execution failed for {slug}: {e}")
        raise HTTPException(status_code=500, detail=f"Task execution failed: {e}")


@router.get("/{slug}/status")
async def get_run_status(slug: str, auth: UserClient) -> RunStatusResponse:
    """Latest run status for a recurrence — derived from agent_runs."""
    decls = walk_workspace_recurrences(auth.client, auth.user_id)
    decl = _decl_for_slug(decls, slug)
    if decl is None or not decl.agents:
        return RunStatusResponse(status="not_found")

    # Look up the assigned agent's most recent run
    agent_slug = decl.agents[0]
    agent_row = (
        auth.client.table("agents")
        .select("id")
        .eq("user_id", auth.user_id)
        .eq("slug", agent_slug)
        .limit(1)
        .execute()
    ).data
    if not agent_row:
        return RunStatusResponse(status="not_found")

    runs = (
        auth.client.table("agent_runs")
        .select("status, created_at, delivered_at")
        .eq("agent_id", agent_row[0]["id"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    ).data
    if not runs:
        return RunStatusResponse(status="not_found")
    r = runs[0]
    return RunStatusResponse(
        status=r.get("status", "unknown"),
        started_at=r.get("created_at"),
        completed_at=r.get("delivered_at"),
    )


# =============================================================================
# Output reads (natural-home substrate)
# =============================================================================


@router.get("/{slug}/outputs")
async def list_task_outputs(slug: str, auth: UserClient) -> list[TaskOutputEntry]:
    """List dated output folders for a DELIVERABLE recurrence."""
    decls = walk_workspace_recurrences(auth.client, auth.user_id)
    decl = _decl_for_slug(decls, slug)
    if decl is None or decl.shape != RecurrenceShape.DELIVERABLE:
        return []

    paths = resolve_paths(decl)
    substrate_root = paths.substrate_root  # /workspace/reports/{slug}

    result = (
        auth.client.table("workspace_files")
        .select("path, content")
        .eq("user_id", auth.user_id)
        .like("path", f"{substrate_root}/%/output.md")
        .execute()
    ).data or []

    entries = []
    for row in result:
        path = row["path"]
        # Extract date folder: substrate_root/{date}/output.md
        rel = path[len(substrate_root) + 1:]  # strip prefix + "/"
        date_folder = rel.split("/")[0]
        entries.append(TaskOutputEntry(
            folder=date_folder,
            date=date_folder,
            status="active",
            renderable=True,
            manifest=None,
        ))
    entries.sort(key=lambda e: e.date, reverse=True)
    return entries


@router.get("/{slug}/outputs/latest")
async def get_latest_task_output(slug: str, auth: UserClient) -> TaskOutputLatest:
    """Latest output for a DELIVERABLE recurrence."""
    decls = walk_workspace_recurrences(auth.client, auth.user_id)
    decl = _decl_for_slug(decls, slug)
    if decl is None or decl.shape != RecurrenceShape.DELIVERABLE:
        return TaskOutputLatest()

    paths = resolve_paths(decl)
    substrate_root = paths.substrate_root

    latest = (
        auth.client.table("workspace_files")
        .select("path, content")
        .eq("user_id", auth.user_id)
        .like("path", f"{substrate_root}/%/output.md")
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    ).data or []
    if not latest:
        return TaskOutputLatest()
    row = latest[0]
    rel = row["path"][len(substrate_root) + 1:]
    date_folder = rel.split("/")[0]

    return TaskOutputLatest(
        content=row.get("content"),
        date=date_folder,
    )


@router.get("/{slug}/outputs/{date_folder}")
async def get_task_output_by_date(
    slug: str, date_folder: str, auth: UserClient
) -> TaskOutputLatest:
    decls = walk_workspace_recurrences(auth.client, auth.user_id)
    decl = _decl_for_slug(decls, slug)
    if decl is None or decl.shape != RecurrenceShape.DELIVERABLE:
        return TaskOutputLatest()

    paths = resolve_paths(decl)
    substrate_root = paths.substrate_root
    um = UserMemory(auth.client, auth.user_id)
    output_md = await um.read(_strip_ws_prefix(f"{substrate_root}/{date_folder}/output.md"))
    if not output_md:
        return TaskOutputLatest()
    return TaskOutputLatest(content=output_md, date=date_folder)


# =============================================================================
# Export + Repurpose (delegated to existing services)
# =============================================================================


@router.get("/{slug}/export")
async def export_task_output(
    slug: str,
    format: str,
    auth: UserClient,
    date_folder: Optional[str] = None,
):
    """Export latest output as PDF/XLSX/etc. via render service."""
    decls = walk_workspace_recurrences(auth.client, auth.user_id)
    decl = _decl_for_slug(decls, slug)
    if decl is None or decl.shape != RecurrenceShape.DELIVERABLE:
        raise HTTPException(status_code=404, detail="Task not found or not deliverable")

    paths = resolve_paths(decl)
    substrate_root = paths.substrate_root

    if not date_folder:
        latest = (
            auth.client.table("workspace_files")
            .select("path")
            .eq("user_id", auth.user_id)
            .like("path", f"{substrate_root}/%/output.md")
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        ).data or []
        if not latest:
            raise HTTPException(status_code=404, detail="No output found")
        date_folder = latest[0]["path"][len(substrate_root) + 1:].split("/")[0]

    from services.compose.task_html import compose_task_output_html
    html_content = await compose_task_output_html(
        auth.client, auth.user_id, slug, date_folder
    )
    if not html_content:
        raise HTTPException(status_code=404, detail="No output to export")

    render_url = os.environ.get("RENDER_SERVICE_URL", "https://yarnnn-render.onrender.com")
    render_secret = os.environ.get("RENDER_SERVICE_SECRET", "")
    headers = {"X-Render-Secret": render_secret} if render_secret else {}

    async with httpx.AsyncClient(timeout=60.0) as http:
        resp = await http.post(
            f"{render_url}/export",
            json={"html": html_content, "format": format, "user_id": auth.user_id},
            headers=headers,
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Render export failed: {resp.status_code}")
    return StreamingResponse(
        iter([resp.content]),
        media_type=resp.headers.get("content-type", "application/octet-stream"),
    )


@router.post("/{slug}/repurpose")
async def repurpose_task_output(
    slug: str,
    payload: dict,
    auth: UserClient,
) -> dict:
    """Repurpose latest output to a different target format."""
    from services.primitives.repurpose import handle_repurpose
    return await handle_repurpose(auth, {
        "task_slug": slug,
        "target": payload.get("target"),
        "output_date": payload.get("output_date"),
    })
