"""
Tasks routes — CRUD for task definitions.

ADR-138: Agents as Work Units — tasks are the WHAT (work definitions).

Endpoints:
- POST /tasks - Create a new task
- GET /tasks - List user's tasks
- GET /tasks/{slug} - Get task detail
- PUT /tasks/{slug} - Update task
- DELETE /tasks/{slug} - Archive task (soft delete)
- GET /tasks/{slug}/outputs - List task output history
- GET /tasks/{slug}/outputs/latest - Get latest task output
- POST /tasks/{slug}/run - Trigger a task run immediately
"""

from __future__ import annotations

import json as _json
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
    agent_slugs: Optional[list] = None
    delivery: Optional[str] = None
    success_criteria: Optional[list] = None
    output_spec: Optional[list] = None
    # Enriched from workspace (detail endpoint only)
    run_log: Optional[str] = None


class TaskOutputEntry(BaseModel):
    folder: str           # date folder name (e.g., "2026-03-25T1400")
    date: str             # same as folder — display-friendly alias
    status: str           # from manifest or default "active"
    has_html: bool
    manifest: Optional[dict] = None


class TaskOutputLatest(BaseModel):
    content: Optional[str] = None
    html_content: Optional[str] = None
    date: Optional[str] = None
    manifest: Optional[dict] = None


class TaskRunTriggered(BaseModel):
    triggered: bool
    task_slug: str


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

    # Top-level bold fields (Agent, Mode, Schedule, Delivery, Slug)
    agent_slugs = []
    for line in lines:
        agent_match = re.match(r"\*\*Agent:\*\*\s*(.*)", line)
        if agent_match:
            agent_slugs = [a.strip() for a in agent_match.group(1).split(",")]

    # Process section (multi-agent tasks may have Agents list here)
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
                    agent_slugs = [a.strip() for a in val.split(",")]
                    process["agents"] = agent_slugs
                else:
                    process[key] = val
    if process:
        result["process"] = process

    # Agent slugs (from top-level field or Process section)
    if agent_slugs:
        result["agent_slugs"] = agent_slugs

    # Success criteria
    in_criteria = False
    criteria = []
    for line in lines:
        if line.strip() == "## Success Criteria":
            in_criteria = True
            continue
        if line.startswith("## ") and in_criteria:
            break
        if in_criteria and line.strip().startswith("- "):
            criteria.append(line.strip()[2:])
    if criteria:
        result["success_criteria"] = criteria

    # Delivery (top-level field)
    for line in lines:
        delivery_match = re.match(r"\*\*Delivery:\*\*\s*(.*)", line)
        if delivery_match:
            result["delivery"] = delivery_match.group(1).strip()
            break

    # Output spec
    in_spec = False
    output_spec = []
    for line in lines:
        if line.strip() == "## Output Spec":
            in_spec = True
            continue
        if line.startswith("## ") and in_spec:
            break
        if in_spec and line.strip().startswith("- "):
            output_spec.append(line.strip()[2:])
    if output_spec:
        result["output_spec"] = output_spec

    return result


def _task_row_to_response(row: dict, task_md_parsed: Optional[dict] = None) -> TaskResponse:
    """Convert a DB row + optional TASK.md parse into TaskResponse."""
    objective = None
    process = None

    if task_md_parsed:
        objective = task_md_parsed.get("objective")
        process = task_md_parsed.get("process")

    # Title: prefer TASK.md title, fall back to slug
    title = (task_md_parsed.get("title") if task_md_parsed else None) or row["slug"]

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
        agent_slugs=task_md_parsed.get("agent_slugs") if task_md_parsed else None,
        delivery=task_md_parsed.get("delivery") if task_md_parsed else None,
        success_criteria=task_md_parsed.get("success_criteria") if task_md_parsed else None,
        output_spec=task_md_parsed.get("output_spec") if task_md_parsed else None,
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

    # Read TASK.md + run_log (detail-only enrichment)
    ws = TaskWorkspace(auth.client, auth.user_id, slug)
    content = await ws.read_task()
    parsed = _parse_task_md(content) if content else None
    run_log = await ws.read("memory/run_log.md")

    response = _task_row_to_response(row, parsed)
    response.run_log = run_log
    return response


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


# =============================================================================
# Output & Run Routes
# =============================================================================

@router.get("/{slug}/outputs")
async def list_task_outputs(
    slug: str,
    auth: UserClient,
) -> list[TaskOutputEntry]:
    """
    List task output history — one entry per output folder, sorted by date descending.
    """
    from services.task_workspace import TaskWorkspace

    # Verify task exists and belongs to user
    existing = (
        auth.client.table("tasks")
        .select("id")
        .eq("user_id", auth.user_id)
        .eq("slug", slug)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Task not found")

    ws = TaskWorkspace(auth.client, auth.user_id, slug)

    # Query all output.md files under /tasks/{slug}/outputs/
    prefix = ws._full_path("outputs/")
    try:
        result = (
            auth.client.table("workspace_files")
            .select("path")
            .eq("user_id", auth.user_id)
            .like("path", f"{prefix}%/output.md")
            .in_("lifecycle", ["active", "delivered"])
            .order("path", desc=True)
            .execute()
        )
    except Exception as e:
        logger.error(f"[TASKS] list_task_outputs query failed for {slug}: {e}")
        return []

    rows = result.data or []
    entries: list[TaskOutputEntry] = []

    for row in rows:
        # path like /tasks/{slug}/outputs/2026-03-25T1400/output.md
        path = row["path"]
        # Extract date folder: strip prefix and /output.md
        relative = path[len(prefix):]  # "2026-03-25T1400/output.md"
        date_folder = relative.split("/")[0] if "/" in relative else relative

        # Check if output.html exists in same folder
        html_exists = await ws.exists(f"outputs/{date_folder}/output.html")

        # Read manifest.json if available
        manifest_content = await ws.read(f"outputs/{date_folder}/manifest.json")
        manifest = None
        if manifest_content:
            try:
                manifest = _json.loads(manifest_content)
            except (ValueError, _json.JSONDecodeError):
                pass

        # Derive status from manifest or lifecycle
        output_status = "active"
        if manifest:
            output_status = manifest.get("status", "active")
        if html_exists:
            output_status = "delivered"

        entries.append(TaskOutputEntry(
            folder=date_folder,
            date=date_folder,
            status=output_status,
            has_html=html_exists,
            manifest=manifest,
        ))

    return entries


@router.get("/{slug}/outputs/latest")
async def get_latest_task_output(
    slug: str,
    auth: UserClient,
) -> TaskOutputLatest:
    """
    Get the most recent task output — markdown content, HTML if available, and manifest.
    """
    from services.task_workspace import TaskWorkspace

    # Verify task exists and belongs to user
    existing = (
        auth.client.table("tasks")
        .select("id")
        .eq("user_id", auth.user_id)
        .eq("slug", slug)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Task not found")

    ws = TaskWorkspace(auth.client, auth.user_id, slug)

    # Find the most recent output.md by lexicographic sort (ISO dates sort correctly)
    prefix = ws._full_path("outputs/")
    try:
        result = (
            auth.client.table("workspace_files")
            .select("path, content")
            .eq("user_id", auth.user_id)
            .like("path", f"{prefix}%/output.md")
            .in_("lifecycle", ["active", "delivered"])
            .order("path", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as e:
        logger.error(f"[TASKS] get_latest_task_output query failed for {slug}: {e}")
        return TaskOutputLatest()

    rows = result.data or []
    if not rows:
        return TaskOutputLatest()

    path = rows[0]["path"]
    content = rows[0]["content"]

    # Extract date folder
    relative = path[len(prefix):]
    date_folder = relative.split("/")[0] if "/" in relative else relative

    # Read output.html if it exists
    html_content = await ws.read(f"outputs/{date_folder}/output.html")

    # Read manifest.json if available
    manifest_content = await ws.read(f"outputs/{date_folder}/manifest.json")
    manifest = None
    if manifest_content:
        try:
            manifest = _json.loads(manifest_content)
        except (ValueError, _json.JSONDecodeError):
            pass

    return TaskOutputLatest(
        content=content,
        html_content=html_content,
        date=date_folder,
        manifest=manifest,
    )


@router.get("/{slug}/outputs/{date_folder}")
async def get_task_output_by_date(
    slug: str,
    date_folder: str,
    auth: UserClient,
) -> TaskOutputLatest:
    """
    Get a specific task output by date folder (e.g., 2026-03-25T1400).
    """
    from services.task_workspace import TaskWorkspace

    # Verify task exists and belongs to user
    existing = (
        auth.client.table("tasks")
        .select("id")
        .eq("user_id", auth.user_id)
        .eq("slug", slug)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Task not found")

    ws = TaskWorkspace(auth.client, auth.user_id, slug)

    content = await ws.read(f"outputs/{date_folder}/output.md")
    html_content = await ws.read(f"outputs/{date_folder}/output.html")

    manifest_content = await ws.read(f"outputs/{date_folder}/manifest.json")
    manifest = None
    if manifest_content:
        try:
            manifest = _json.loads(manifest_content)
        except (ValueError, _json.JSONDecodeError):
            pass

    return TaskOutputLatest(
        content=content,
        html_content=html_content,
        date=date_folder,
        manifest=manifest,
    )


@router.post("/{slug}/run")
async def trigger_task_run(
    slug: str,
    auth: UserClient,
) -> TaskRunTriggered:
    """
    Trigger a task run immediately by setting next_run_at to now.
    The scheduler will pick it up on the next cycle.
    """
    # Fetch task — must exist and be active
    existing = (
        auth.client.table("tasks")
        .select("id, slug, status")
        .eq("user_id", auth.user_id)
        .eq("slug", slug)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Task not found")

    task = existing.data[0]
    if task["status"] != "active":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot trigger run: task status is '{task['status']}' (must be 'active')",
        )

    # Set next_run_at to now so the scheduler picks it up
    now = datetime.now(timezone.utc).isoformat()
    result = (
        auth.client.table("tasks")
        .update({
            "next_run_at": now,
            "updated_at": now,
        })
        .eq("user_id", auth.user_id)
        .eq("slug", slug)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to trigger task run")

    logger.info(f"[TASKS] Triggered run for task '{slug}' (next_run_at set to now)")
    return TaskRunTriggered(triggered=True, task_slug=slug)
