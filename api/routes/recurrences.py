"""
Recurrences routes — read/write surface over /workspace/_recurrences.yaml.

Per ADR-261 D1 + D2: every recurrence is `{slug, schedule, prompt}` in
the canonical file. Per ADR-262 D1: substrate paths are slug-templated
via the conventions module — every recurrence's outputs land at
``/workspace/reports/{slug}/{date}/output.md``.

The HTTP surface lives at ``/api/recurrences/*``. The TaskResponse model
matches the FE Recurrence type post-Phase-I (post-merge sweep, 2026-05-10):
the legacy ``output_kind`` and ``shape`` fields have been DELETED — the
FE compositor (`MiddleResolver`, `WorkListSurface`) no longer dispatches
on those axes per ADR-261 D1's "one execution shape." Bundles can still
override `MiddleResolver` per-recurrence via slug-match in SURFACES.yaml.

Endpoints:
- GET  /recurrences            list user's recurrences
- GET  /recurrences/{slug}     recurrence detail
- PUT  /recurrences/{slug}     update recurrence (status / paused / schedule)
- DELETE /recurrences/{slug}   archive recurrence
- POST /recurrences/{slug}/run fire an invocation now
- GET  /recurrences/{slug}/status                latest run status
- GET  /recurrences/{slug}/outputs               list dated outputs
- GET  /recurrences/{slug}/outputs/latest        latest output
- GET  /recurrences/{slug}/outputs/{date_folder} specific dated output
- GET  /recurrences/{slug}/export                export latest output
- POST /recurrences/{slug}/repurpose             repurpose latest output
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional, Union

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.conventions import (
    RECURRENCES_PATH,
    report_root,
    report_run_log_path,
)
from services.recurrence import Recurrence, walk_workspace_recurrences
from services.supabase import UserClient
from services.workspace import UserMemory

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Response models — frontend contract preserved
# =============================================================================


class TaskUpdate(BaseModel):
    status: Optional[str] = None
    # ADR-268: schedule accepts plain UTC cron, @-prefixed semantic, OR
    # a list of either (multiple fires per day). Mutating via
    # Schedule(action='update') accepts both shapes.
    schedule: Optional[Union[str, list[str]]] = None


class TaskResponse(BaseModel):
    id: str
    slug: str
    status: str
    # ADR-263: mode is the recurrence's wake-intent declaration
    # ('judgment' | 'mechanical'), authored at create-time. Replaces the
    # previously-derived mode value (which was just shorthand for
    # 'is schedule set' — redundant with the schedule field itself; the FE
    # already derives that label client-side via `recurrenceLabel(schedule)`).
    mode: Optional[str] = None
    # ADR-268: schedule is the recurrence's authored schedule string OR
    # a list of strings (multiple fires per day, e.g. `track-universe`'s
    # three RTH snapshots). FE consumers normalize via `scheduleDisplay()`
    # in web/lib/schedule.ts.
    schedule: Optional[Union[str, list[str]]] = None
    next_run_at: Optional[str] = None
    last_run_at: Optional[str] = None
    created_at: str
    updated_at: str
    title: Optional[str] = None
    type_key: Optional[str] = None
    # output_kind + shape DELETED post-Phase I (2026-05-10) per ADR-261 D1.
    objective: Optional[dict] = None
    process: Optional[dict] = None
    agent_slugs: Optional[list] = None
    delivery: Optional[str] = None
    success_criteria: Optional[list] = None
    output_spec: Optional[list] = None
    context_reads: Optional[list] = None
    context_writes: Optional[list] = None
    phase: Optional[str] = None
    essential: bool = False
    paused: bool = False
    sources: Optional[dict] = None
    run_log: Optional[str] = None
    deliverable_spec: Optional[dict] = None
    declaration_path: Optional[str] = None


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


def _strip_ws_prefix(p: str) -> str:
    return p[len("/workspace/"):] if p.startswith("/workspace/") else p


def _rec_for_slug(
    recurrences: list[Recurrence], slug: str
) -> Optional[Recurrence]:
    return next((r for r in recurrences if r.slug == slug), None)


def _decode_persisted_schedule(value: Any) -> Optional[Union[str, list[str]]]:
    """Decode the `tasks.schedule` column back to its authored shape.

    Per ADR-268 we persist list-form schedules as JSON-encoded strings
    so the `text` column stays consistent. On read, attempt to parse JSON
    when the value starts with `[`; otherwise return as plain string.
    Returns None for empty/None values.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if s.startswith("["):
        try:
            import json
            parsed = json.loads(s)
            if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
                return parsed
        except Exception:
            pass
    return s


def _rec_to_response(
    row: dict,
    rec: Optional[Recurrence],
    *,
    run_log: Optional[str] = None,
) -> TaskResponse:
    """Build a TaskResponse from the scheduling-index row + recurrence.

    Per ADR-261 D1 the recurrence is `{slug, schedule, prompt, options}`.
    Frontend fields that previously came from per-shape declaration data
    (objective, agents, delivery, context_reads/writes) now come from the
    optional ``options`` blob if the operator chose to set them; otherwise
    None. The FE renders them defensively.

    ADR-268: `schedule` is Union[str, list[str], None]. When the parsed
    Recurrence is available, surface its authored form directly. Fallback
    to row.schedule (decoded back from its JSON-string persisted form
    if it was a list).
    """
    options = (rec.options if rec else {}) or {}
    title = options.get("display_name") or row["slug"]
    objective = options.get("objective")
    if isinstance(objective, str):
        objective = {"prose": objective}

    return TaskResponse(
        id=str(row["id"]),
        slug=row["slug"],
        status=row["status"],
        # ADR-263: surface the recurrence's authored mode (judgment | mechanical).
        # Falls back to the dataclass default ('judgment') when no Recurrence is
        # available — preserves backward compatibility for legacy entries that
        # exist only as scheduling-index rows without a parsed YAML body.
        mode=(rec.mode if rec else "judgment"),
        schedule=(rec.schedule if rec else _decode_persisted_schedule(row.get("schedule"))),
        next_run_at=row.get("next_run_at"),
        last_run_at=row.get("last_run_at"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        title=title,
        type_key=None,
        objective=objective if isinstance(objective, dict) else None,
        process=options.get("process"),
        agent_slugs=options.get("agents") or options.get("agent_slugs"),
        delivery=options.get("delivery") if isinstance(options.get("delivery"), str) else None,
        success_criteria=options.get("success_criteria"),
        output_spec=options.get("output_spec"),
        context_reads=options.get("context_reads"),
        context_writes=options.get("context_writes"),
        phase=None,
        essential=False,
        paused=bool(row.get("paused", False)),
        sources=options.get("sources"),
        run_log=run_log,
        deliverable_spec=options.get("deliverable") if isinstance(options.get("deliverable"), dict) else None,
        declaration_path=row.get("declaration_path") or RECURRENCES_PATH,
    )


# =============================================================================
# List + Detail
# =============================================================================


@router.get("")
async def list_recurrences(
    auth: UserClient,
    status: Optional[str] = None,
    limit: int = 100,
    include_system: bool = False,
) -> list[TaskResponse]:
    """List user's recurrences (joined index + walker)."""
    query = (
        auth.client.table("tasks")
        .select(
            "id, slug, status, schedule, next_run_at, last_run_at, "
            "created_at, updated_at, declaration_path, paused"
        )
        .eq("user_id", auth.user_id)
        .order("created_at", desc=True)
        .limit(limit)
    )
    if status:
        query = query.eq("status", status)
    rows = (query.execute()).data or []

    if not include_system:
        rows = [r for r in rows if not (r.get("slug") or "").startswith("back-office-")]

    recurrences = walk_workspace_recurrences(auth.client, auth.user_id)
    return [_rec_to_response(r, _rec_for_slug(recurrences, r["slug"])) for r in rows]


@router.get("/{slug}")
async def get_recurrence(slug: str, auth: UserClient) -> TaskResponse:
    """Recurrence detail: index row + recurrence + run log."""
    rows = (
        auth.client.table("tasks")
        .select(
            "id, slug, status, schedule, next_run_at, last_run_at, "
            "created_at, updated_at, declaration_path, paused"
        )
        .eq("user_id", auth.user_id)
        .eq("slug", slug)
        .limit(1)
        .execute()
    ).data
    if not rows:
        raise HTTPException(status_code=404, detail="Recurrence not found")
    row = rows[0]

    recurrences = walk_workspace_recurrences(auth.client, auth.user_id)
    rec = _rec_for_slug(recurrences, slug)
    if rec is None:
        return _rec_to_response(row, None)

    um = UserMemory(auth.client, auth.user_id)
    run_log = await um.read(_strip_ws_prefix(report_run_log_path(slug)))

    return _rec_to_response(row, rec, run_log=run_log)


# =============================================================================
# Update + Archive
# =============================================================================


@router.put("/{slug}")
async def update_recurrence(
    slug: str,
    request: TaskUpdate,
    auth: UserClient,
) -> dict:
    """Update recurrence — maps to Schedule(action='update'/'pause'/'resume').

    Keeps the legacy frontend behavior where status='paused' flips the
    paused flag rather than changing status.
    """
    rows = (
        auth.client.table("tasks")
        .select("id, slug, status, declaration_path, paused")
        .eq("user_id", auth.user_id)
        .eq("slug", slug)
        .limit(1)
        .execute()
    ).data
    if not rows:
        raise HTTPException(status_code=404, detail="Recurrence not found")
    row = rows[0]

    db_updates: dict = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if request.status is not None:
        if request.status not in ("active", "paused", "completed", "archived"):
            raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")
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

    # Mirror schedule + paused changes into _recurrences.yaml via Schedule.
    from services.primitives.schedule import handle_schedule

    if request.status == "paused":
        await handle_schedule(auth, {"action": "pause", "slug": slug, "authored_by": "operator"})
    elif request.status == "active" and row.get("paused"):
        await handle_schedule(auth, {"action": "resume", "slug": slug, "authored_by": "operator"})
    if request.schedule is not None:
        await handle_schedule(auth, {
            "action": "update",
            "slug": slug,
            "changes": {"schedule": request.schedule},
            "authored_by": "operator",
        })

    return {"success": True}


@router.patch("/{slug}/sources")
async def update_recurrence_sources(
    slug: str,
    sources: dict,
    auth: UserClient,
) -> dict:
    """Update the recurrence's per-platform source selection. Stored as
    metadata under ``options.sources`` in the recurrence entry."""
    from services.primitives.schedule import handle_schedule

    result = await handle_schedule(auth, {
        "action": "update",
        "slug": slug,
        "changes": {"sources": sources},
        "authored_by": "operator",
    })
    if not result.get("success"):
        raise HTTPException(
            status_code=404,
            detail=result.get("message", "Recurrence not found"),
        )
    return {"success": True}


@router.delete("/{slug}")
async def archive_recurrence(slug: str, auth: UserClient) -> dict:
    """Archive a recurrence — marks the index row archived and removes the
    entry from _recurrences.yaml via Schedule(action='archive')."""
    rows = (
        auth.client.table("tasks")
        .select("id, slug, declaration_path")
        .eq("user_id", auth.user_id)
        .eq("slug", slug)
        .limit(1)
        .execute()
    ).data
    if not rows:
        raise HTTPException(status_code=404, detail="Recurrence not found")

    auth.client.table("tasks").update({
        "status": "archived",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("user_id", auth.user_id).eq("slug", slug).execute()

    from services.primitives.schedule import handle_schedule
    await handle_schedule(auth, {"action": "archive", "slug": slug, "authored_by": "operator"})

    return {"success": True}


# =============================================================================
# Run trigger + status
# =============================================================================


@router.post("/{slug}/run")
async def trigger_recurrence_run(slug: str, auth: UserClient) -> TaskRunTriggered:
    """Fire an invocation against the recurrence immediately."""
    rows = (
        auth.client.table("tasks")
        .select("id, slug, status")
        .eq("user_id", auth.user_id)
        .eq("slug", slug)
        .limit(1)
        .execute()
    ).data
    if not rows:
        raise HTTPException(status_code=404, detail="Recurrence not found")
    if rows[0]["status"] != "active":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot trigger run: status is '{rows[0]['status']}'",
        )

    try:
        # ADR-296 v2 D1: operator manual fire from the recurrence-detail
        # surface routes through the manual_fire wake source. The funnel
        # auto-escalates (operator explicit assertion is a wake-warrant).
        from services.wake_sources.manual_fire import fire as wake_manual_fire
        from services.supabase import get_service_client
        svc_client = get_service_client()
        recurrences = walk_workspace_recurrences(svc_client, auth.user_id)
        rec = _rec_for_slug(recurrences, slug)
        if rec is None:
            raise HTTPException(
                status_code=404,
                detail=f"No recurrence entry for slug '{slug}' in _recurrences.yaml",
            )
        result = await wake_manual_fire(svc_client, auth.user_id, rec)
        logger.info(
            f"[RECURRENCE] inline dispatch for {slug}: "
            f"{result.get('success', '?')}"
        )
        return TaskRunTriggered(triggered=True, task_slug=slug)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[RECURRENCE] inline execution failed for {slug}: {e}")
        raise HTTPException(status_code=500, detail=f"Recurrence execution failed: {e}")


@router.get("/{slug}/status")
async def get_run_status(slug: str, auth: UserClient) -> RunStatusResponse:
    """Latest run status — derived from agent_runs by slug.

    Under the unified model, the assigned-agent concept dissolves (the
    Reviewer dispatches specialists per-invocation). We look up the most
    recent agent_run row associated with this recurrence's slug via
    metadata, falling back to a synthesized status from the tasks index.
    """
    rows = (
        auth.client.table("tasks")
        .select("status, last_run_at, next_run_at")
        .eq("user_id", auth.user_id)
        .eq("slug", slug)
        .limit(1)
        .execute()
    ).data
    if not rows:
        return RunStatusResponse(status="not_found")

    row = rows[0]
    return RunStatusResponse(
        status="active" if row.get("status") == "active" else row.get("status", "unknown"),
        started_at=row.get("last_run_at"),
        completed_at=row.get("last_run_at"),
    )


# =============================================================================
# Output reads (slug-templated substrate per ADR-262 D1)
# =============================================================================


@router.get("/{slug}/outputs")
async def list_recurrence_outputs(slug: str, auth: UserClient) -> list[TaskOutputEntry]:
    """List dated output folders under /workspace/reports/{slug}/."""
    substrate_root = report_root(slug)

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
        rel = path[len(substrate_root) + 1:]
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
async def get_latest_recurrence_output(slug: str, auth: UserClient) -> TaskOutputLatest:
    """Latest output for a recurrence."""
    substrate_root = report_root(slug)

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
async def get_recurrence_output_by_date(
    slug: str, date_folder: str, auth: UserClient
) -> TaskOutputLatest:
    substrate_root = report_root(slug)
    um = UserMemory(auth.client, auth.user_id)
    output_md = await um.read(_strip_ws_prefix(f"{substrate_root}/{date_folder}/output.md"))
    if not output_md:
        return TaskOutputLatest()
    return TaskOutputLatest(content=output_md, date=date_folder)


# =============================================================================
# Export + Repurpose
# =============================================================================


@router.get("/{slug}/export")
async def export_recurrence_output(
    slug: str,
    format: str,
    auth: UserClient,
    date_folder: Optional[str] = None,
):
    """Export latest output as PDF/XLSX/etc. via render service."""
    substrate_root = report_root(slug)

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
async def repurpose_recurrence_output(
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
