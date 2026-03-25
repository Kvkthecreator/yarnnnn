"""
Tasks routes — CRUD for task definitions.

ADR-138: Agents as Work Units — tasks are the WHAT (work definitions).

Endpoints:
- POST /tasks - Create a new task
- GET /tasks - List user's tasks
- GET /tasks/{slug} - Get task detail
- PUT /tasks/{slug} - Update task
- DELETE /tasks/{slug} - Archive task (soft delete)
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.supabase import UserClient

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class TaskCreate(BaseModel):
    title: str
    slug: Optional[str] = None  # auto-generated from title if not provided
    schedule: Optional[str] = None
    objective: Optional[dict] = None  # {deliverable, audience, purpose, format}
    success_criteria: Optional[list] = None
    process: Optional[dict] = None  # {agents: [slug], cadence, delivery}
    output_spec: Optional[list] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    schedule: Optional[str] = None
    status: Optional[str] = None  # active, paused, completed, archived
    objective: Optional[dict] = None
    success_criteria: Optional[list] = None
    process: Optional[dict] = None
    output_spec: Optional[list] = None


class TaskResponse(BaseModel):
    id: str
    slug: str
    status: str
    schedule: Optional[str] = None
    next_run_at: Optional[str] = None
    last_run_at: Optional[str] = None
    created_at: str
    updated_at: str
    # Enriched from TASK.md
    title: Optional[str] = None
    objective: Optional[dict] = None
    process: Optional[dict] = None


# =============================================================================
# Helpers
# =============================================================================

def _slugify(title: str) -> str:
    """Generate a URL-safe slug from title. Lowercase, hyphens, truncated."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not slug:
        slug = "untitled"
    # Truncate to reasonable length
    return slug[:60]


def _format_task_md(
    title: str,
    objective: Optional[dict] = None,
    success_criteria: Optional[list] = None,
    process: Optional[dict] = None,
    output_spec: Optional[list] = None,
) -> str:
    """Build TASK.md content from structured fields."""
    lines = [f"# {title}", ""]

    if objective:
        lines.append("## Objective")
        for key in ("deliverable", "audience", "purpose", "format"):
            val = objective.get(key)
            if val:
                lines.append(f"- **{key.capitalize()}**: {val}")
        lines.append("")

    if success_criteria:
        lines.append("## Success Criteria")
        for criterion in success_criteria:
            lines.append(f"- {criterion}")
        lines.append("")

    if process:
        lines.append("## Process")
        agents = process.get("agents")
        if agents:
            lines.append(f"- **Agents**: {', '.join(agents)}")
        cadence = process.get("cadence")
        if cadence:
            lines.append(f"- **Cadence**: {cadence}")
        delivery = process.get("delivery")
        if delivery:
            lines.append(f"- **Delivery**: {delivery}")
        lines.append("")

    if output_spec:
        lines.append("## Output Spec")
        for item in output_spec:
            lines.append(f"- {item}")
        lines.append("")

    return "\n".join(lines)


def _parse_task_md(content: str) -> dict:
    """Parse TASK.md content into structured fields.

    Best-effort extraction: returns title, objective, process as found.
    """
    result: dict = {"title": None, "objective": None, "process": None}

    lines = content.split("\n")

    # Title from first H1
    for line in lines:
        if line.startswith("# "):
            result["title"] = line[2:].strip()
            break

    # Objective section — extract key-value pairs
    in_objective = False
    objective: dict = {}
    for line in lines:
        if line.strip() == "## Objective":
            in_objective = True
            continue
        if line.startswith("## ") and in_objective:
            break
        if in_objective and line.startswith("- **"):
            match = re.match(r"- \*\*(\w+)\*\*:\s*(.*)", line)
            if match:
                objective[match.group(1).lower()] = match.group(2).strip()
    if objective:
        result["objective"] = objective

    # Process section
    in_process = False
    process: dict = {}
    for line in lines:
        if line.strip() == "## Process":
            in_process = True
            continue
        if line.startswith("## ") and in_process:
            break
        if in_process and line.startswith("- **"):
            match = re.match(r"- \*\*(\w+)\*\*:\s*(.*)", line)
            if match:
                key = match.group(1).lower()
                val = match.group(2).strip()
                if key == "agents":
                    process["agents"] = [a.strip() for a in val.split(",")]
                else:
                    process[key] = val
    if process:
        result["process"] = process

    return result


def _task_row_to_response(row: dict, task_md_parsed: Optional[dict] = None) -> TaskResponse:
    """Convert a DB row + optional TASK.md parse into TaskResponse."""
    title = None
    objective = None
    process = None

    if task_md_parsed:
        title = task_md_parsed.get("title")
        objective = task_md_parsed.get("objective")
        process = task_md_parsed.get("process")

    return TaskResponse(
        id=str(row["id"]),
        slug=row["slug"],
        status=row["status"],
        schedule=row.get("schedule"),
        next_run_at=row["next_run_at"] if row.get("next_run_at") else None,
        last_run_at=row["last_run_at"] if row.get("last_run_at") else None,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        title=title,
        objective=objective,
        process=process,
    )


# =============================================================================
# CRUD Routes
# =============================================================================

@router.get("")
async def list_tasks(
    auth: UserClient,
    status: Optional[str] = None,
    limit: int = 50,
) -> list[TaskResponse]:
    """
    List user's tasks, enriched with TASK.md content from workspace.
    """
    import asyncio
    from services.task_workspace import TaskWorkspace

    query = (
        auth.client.table("tasks")
        .select("id, slug, status, schedule, next_run_at, last_run_at, created_at, updated_at")
        .eq("user_id", auth.user_id)
        .order("created_at", desc=True)
        .limit(limit)
    )

    if status:
        query = query.eq("status", status)

    result = query.execute()
    rows = result.data or []

    # Enrich each task with TASK.md content in parallel
    async def _enrich(row: dict) -> TaskResponse:
        try:
            ws = TaskWorkspace(auth.client, auth.user_id, row["slug"])
            content = await ws.read_task()
            parsed = _parse_task_md(content) if content else None
        except Exception as e:
            logger.warning(f"[TASKS] TASK.md read failed for {row['slug']}: {e}")
            parsed = None
        return _task_row_to_response(row, parsed)

    responses = await asyncio.gather(*[_enrich(r) for r in rows])
    return list(responses)


@router.get("/{slug}")
async def get_task(
    slug: str,
    auth: UserClient,
) -> TaskResponse:
    """
    Get task detail: DB row + TASK.md + latest output.
    """
    from services.task_workspace import TaskWorkspace

    result = (
        auth.client.table("tasks")
        .select("id, slug, status, schedule, next_run_at, last_run_at, created_at, updated_at")
        .eq("user_id", auth.user_id)
        .eq("slug", slug)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        raise HTTPException(status_code=404, detail="Task not found")

    row = rows[0]

    # Read TASK.md
    ws = TaskWorkspace(auth.client, auth.user_id, slug)
    content = await ws.read_task()
    parsed = _parse_task_md(content) if content else None

    return _task_row_to_response(row, parsed)


@router.post("", status_code=201)
async def create_task(
    request: TaskCreate,
    auth: UserClient,
) -> TaskResponse:
    """
    Create a new task. Creates DB row + writes TASK.md to workspace.

    Does NOT auto-assign agents (Phase 4 will do this via TP primitives).
    """
    from services.task_workspace import TaskWorkspace

    title = request.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title is required")

    # Generate slug
    slug = _slugify(request.slug) if request.slug else _slugify(title)

    # Check uniqueness
    existing = (
        auth.client.table("tasks")
        .select("id")
        .eq("user_id", auth.user_id)
        .eq("slug", slug)
        .limit(1)
        .execute()
    )
    if existing.data:
        raise HTTPException(
            status_code=409,
            detail=f"Task with slug '{slug}' already exists",
        )

    # Insert DB row
    now = datetime.now(timezone.utc).isoformat()
    insert_data = {
        "user_id": auth.user_id,
        "slug": slug,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    if request.schedule:
        insert_data["schedule"] = request.schedule

    result = (
        auth.client.table("tasks")
        .insert(insert_data)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create task")

    row = result.data[0]

    # Write TASK.md to workspace
    ws = TaskWorkspace(auth.client, auth.user_id, slug)
    task_md = _format_task_md(
        title=title,
        objective=request.objective,
        success_criteria=request.success_criteria,
        process=request.process,
        output_spec=request.output_spec,
    )
    await ws.write(
        "TASK.md",
        task_md,
        summary=f"Task definition: {title}",
        tags=["task", "charter"],
    )

    parsed = _parse_task_md(task_md)
    return _task_row_to_response(row, parsed)


@router.put("/{slug}")
async def update_task(
    slug: str,
    request: TaskUpdate,
    auth: UserClient,
) -> TaskResponse:
    """
    Update task. Updates DB fields + rewrites TASK.md if content fields changed.
    """
    from services.task_workspace import TaskWorkspace

    # Fetch existing
    existing = (
        auth.client.table("tasks")
        .select("id, slug, status, schedule, next_run_at, last_run_at, created_at, updated_at")
        .eq("user_id", auth.user_id)
        .eq("slug", slug)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Task not found")

    row = existing.data[0]

    # Update DB fields
    db_updates: dict = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if request.status is not None:
        if request.status not in ("active", "paused", "completed", "archived"):
            raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")
        db_updates["status"] = request.status
    if request.schedule is not None:
        db_updates["schedule"] = request.schedule

    result = (
        auth.client.table("tasks")
        .update(db_updates)
        .eq("user_id", auth.user_id)
        .eq("slug", slug)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to update task")

    updated_row = result.data[0]

    # Rewrite TASK.md if any content fields provided
    ws = TaskWorkspace(auth.client, auth.user_id, slug)
    content_changed = any([
        request.title is not None,
        request.objective is not None,
        request.success_criteria is not None,
        request.process is not None,
        request.output_spec is not None,
    ])

    if content_changed:
        # Read existing TASK.md to merge with updates
        existing_content = await ws.read_task()
        existing_parsed = _parse_task_md(existing_content) if existing_content else {}

        # Merge: request fields override existing
        title = request.title.strip() if request.title else (existing_parsed.get("title") or slug)
        objective = request.objective if request.objective is not None else existing_parsed.get("objective")
        process = request.process if request.process is not None else existing_parsed.get("process")

        task_md = _format_task_md(
            title=title,
            objective=objective,
            success_criteria=request.success_criteria,
            process=process,
            output_spec=request.output_spec,
        )
        await ws.write(
            "TASK.md",
            task_md,
            summary=f"Task definition: {title}",
            tags=["task", "charter"],
        )

    # Read back TASK.md for response
    content = await ws.read_task()
    parsed = _parse_task_md(content) if content else None

    return _task_row_to_response(updated_row, parsed)


@router.delete("/{slug}")
async def archive_task(
    slug: str,
    auth: UserClient,
) -> TaskResponse:
    """
    Archive a task (soft delete — sets status='archived').
    """
    # Verify exists
    existing = (
        auth.client.table("tasks")
        .select("id, slug, status, schedule, next_run_at, last_run_at, created_at, updated_at")
        .eq("user_id", auth.user_id)
        .eq("slug", slug)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Task not found")

    result = (
        auth.client.table("tasks")
        .update({
            "status": "archived",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("user_id", auth.user_id)
        .eq("slug", slug)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to archive task")

    row = result.data[0]
    return _task_row_to_response(row)
