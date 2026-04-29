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
- GET /tasks/{slug}/outputs/{date_folder}/steps - Get pipeline step outputs (ADR-145)
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
    """Canonical task-creation payload.

    Dispatches through ManageTask._handle_create (ADR-168 Commit 3 canonical
    path). A caller supplies EITHER type_key (registry-driven path — team +
    process resolved from TASK_TYPES) OR agent_slug (custom-task path —
    primary agent assignment, optional team override).
    """
    title: str
    schedule: Optional[str] = None

    # Canonical targeting (ADR-168): one of these is required
    type_key: Optional[str] = None      # registry lookup (ADR-145/166)
    agent_slug: Optional[str] = None    # primary agent for custom tasks

    # Mode — ADR-178 invariant: DB tasks.mode and TASK.md **Mode:** stay in sync
    mode: Optional[str] = None          # recurring | goal | reactive; default=recurring

    # Team composition — ADR-176 Phase 2: list of role/slug strings rendered under ## Team
    team: Optional[list] = None

    # Charter body
    objective: Optional[dict] = None    # {deliverable, audience, purpose, format}
    success_criteria: Optional[list] = None
    output_spec: Optional[list] = None
    delivery: Optional[str] = None      # email, cockpit-only, etc.
    page_structure: Optional[list] = None  # ADR-174 Phase 3: bespoke compose layout

    # Pipeline wiring — ADR-166 (output_kind) + ADR-151/152 (context domains).
    # Required for custom (typeless) tasks so the pipeline routes signals,
    # scans domains, and sizes the tool budget correctly. Ignored when type_key
    # is supplied (the registry provides these).
    output_kind: Optional[str] = None       # accumulates_context | produces_deliverable | external_action | system_maintenance
    context_reads: Optional[list] = None    # e.g. ["trading", "signals"]
    context_writes: Optional[list] = None   # e.g. ["trading", "signals"]

    # ADR-207 P3 + ADR-227: capability declaration is BOTH a dispatch-time gate
    # against active platform_connections AND (post-ADR-227) a tool-surface
    # augmentation that merges program-specific platform tools (e.g.
    # platform_trading_get_market_data) into a universal-role agent's tool list.
    # Missing this field on a task that needs platform tools causes the agent
    # to fall back to WebSearch — the prompt cannot recover from a tool surface
    # that doesn't include the platform tool.
    required_capabilities: Optional[list] = None  # e.g. ["read_trading"]


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
    mode: Optional[str] = None  # ADR-154: recurring | goal | reactive
    schedule: Optional[str] = None
    next_run_at: Optional[str] = None
    last_run_at: Optional[str] = None
    created_at: str
    updated_at: str
    # Enriched from TASK.md
    title: Optional[str] = None
    type_key: Optional[str] = None  # ADR-154: task type key
    # ADR-166: 4-value enum — accumulates_context | produces_deliverable |
    # external_action | system_maintenance. Was task_class (context | synthesis).
    output_kind: Optional[str] = None
    objective: Optional[dict] = None
    process: Optional[dict] = None
    agent_slugs: Optional[list] = None
    delivery: Optional[str] = None
    success_criteria: Optional[list] = None
    output_spec: Optional[list] = None
    context_reads: Optional[list] = None
    context_writes: Optional[list] = None
    # ADR-154: Phase + bootstrap
    phase: Optional[str] = None  # bootstrap | steady | complete
    # ADR-161: Essential anchor flag — true for daily-update, blocks archive
    essential: bool = False
    # ADR-158: Task-level source selection (platform:id,id format, parsed from TASK.md)
    # Dict of {platform: [id, ...]} e.g. {"slack": ["C123", "C456"]}
    sources: Optional[dict] = None
    # Enriched from workspace (detail endpoint only)
    run_log: Optional[str] = None
    # ADR-178 Phase 6: DELIVERABLE.md as living quality contract
    deliverable_spec: Optional[dict] = None


class TaskOutputEntry(BaseModel):
    folder: str           # date folder name (e.g., "2026-03-25T1400")
    date: str             # same as folder — display-friendly alias
    status: str           # from manifest or default "active"
    # ADR-213: was `has_html` when output.html was pre-rendered by the pipeline.
    # Now every output folder with sys_manifest.json or output.md is renderable
    # on demand via compose_task_output_html().
    renderable: bool
    manifest: Optional[dict] = None


class TaskSectionEntry(BaseModel):
    """A parsed section from sys_manifest.json sections dict (ADR-170)."""
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
    # ADR-170: Compose substrate — section provenance and manifest
    sys_manifest: Optional[dict] = None          # Full sys_manifest.json parsed
    sections: list[TaskSectionEntry] = []        # Ordered section list for view-time rendering


class TaskRunTriggered(BaseModel):
    triggered: bool
    task_slug: str


class ProcessStepEntry(BaseModel):
    step: int
    step_name: str
    agent_type: str
    agent_slug: str
    content: Optional[str] = None
    tokens: Optional[dict] = None

# Keep alias for backwards compat during rename
PipelineStepEntry = ProcessStepEntry


class ProcessStepsResponse(BaseModel):
    steps: list[ProcessStepEntry]
    process_definition: Optional[list] = None  # from task type registry
    type_key: Optional[str] = None

# Keep alias for backwards compat during rename
PipelineStepsResponse = ProcessStepsResponse


class RunStatusResponse(BaseModel):
    status: str  # "running" | "completed" | "failed" | "not_found"
    current_step: int = 0
    total_steps: int = 0
    completed_steps: list[dict] = []
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


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


def _parse_deliverable_md(content: str, output_kind: Optional[str] = None) -> Optional[dict]:
    """
    Parse DELIVERABLE.md into a structured deliverable_spec dict.
    ADR-178 Phase 6: DELIVERABLE.md as living quality contract surfaced in TaskDetail.

    Returns None if content is empty or unparseable.
    """
    if not content or not content.strip():
        return None

    def _extract_section(md: str, heading: str) -> Optional[str]:
        """Extract content of a ## Heading section, stopping at the next ## heading."""
        pattern = rf"##\s+{re.escape(heading)}\s*\n(.*?)(?=\n##\s|\Z)"
        match = re.search(pattern, md, re.DOTALL | re.IGNORECASE)
        if not match:
            return None
        return match.group(1).strip() or None

    def _parse_bullet_list(text: Optional[str]) -> Optional[list]:
        """Convert a bullet list string into a list of strings. Returns None if empty."""
        if not text:
            return None
        lines = [
            re.sub(r"^[-*]\s*", "", line).strip()
            for line in text.splitlines()
            if re.match(r"^\s*[-*]\s+", line)
        ]
        return lines if lines else None

    def _parse_expected_output(text: Optional[str]) -> Optional[dict]:
        """Parse ## Expected Output section into structured fields."""
        if not text:
            return None
        result = {}
        for line in text.splitlines():
            line = line.strip().lstrip("- ")
            if line.lower().startswith("format:"):
                result["format"] = line.split(":", 1)[1].strip()
            elif line.lower().startswith("surface:"):
                result["surface"] = line.split(":", 1)[1].strip()
            elif line.lower().startswith("sections:"):
                sections_raw = line.split(":", 1)[1].strip()
                result["sections"] = [s.strip() for s in sections_raw.split(",") if s.strip()]
            elif line.lower().startswith("word count:"):
                result["word_count"] = line.split(":", 1)[1].strip()
            elif line.lower().startswith("paths:"):
                # Context-driven tasks list file paths instead of sections
                result["paths"] = line.split(":", 1)[1].strip()
        return result if result else None

    output_section = _extract_section(content, "Expected Output")
    assets_section = _extract_section(content, "Expected Assets")
    criteria_section = _extract_section(content, "Quality Criteria")
    audience_section = _extract_section(content, "Audience")
    prefs_section = _extract_section(content, "User Preferences (inferred)")

    # Infer route from output_kind
    route = None
    if output_kind == "produces_deliverable":
        route = "output-driven"
    elif output_kind == "accumulates_context":
        route = "context-driven"

    spec = {
        "expected_output": _parse_expected_output(output_section),
        "expected_assets": _parse_bullet_list(assets_section),
        "quality_criteria": _parse_bullet_list(criteria_section),
        "audience": audience_section,
        "user_preferences": prefs_section,
        "route": route,
    }

    # Return None if all values are None (empty/unparseable DELIVERABLE.md)
    if all(v is None for v in spec.values()):
        return None

    return spec


# _format_task_md removed — ADR-168 singular-implementation cleanup.
# TASK.md serialization now lives exclusively in services/primitives/manage_task.py
# (_build_custom_task_md + build_task_md_from_type). Route-scoped formatter was
# a structurally-incomplete duplicate that omitted **Mode:**, **Output:**,
# **Agent:**, ## Team, and skipped DELIVERABLE.md/feedback.md/steering.md/
# awareness.md/context-domain scaffolding. Create path now dispatches through
# ManageTask._handle_create.


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

    # Process section
    in_process = False
    process: dict = {}
    process_agent_slugs: list[str] = []
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
        # Extract agent slugs from numbered process steps: "1. **StepName** (agent-slug): ..."
        if in_process:
            step_match = re.match(r"\d+\.\s+\*\*.*?\*\*\s+\(([^)]+)\)", line)
            if step_match:
                slug_val = step_match.group(1).strip()
                if slug_val not in process_agent_slugs:
                    process_agent_slugs.append(slug_val)
    if process:
        result["process"] = process

    # Agent slugs: prefer top-level **Agent:** field, then **Agents:** in process,
    # then extract from numbered process steps (build_task_md_from_type format)
    if not agent_slugs and process_agent_slugs:
        agent_slugs = process_agent_slugs
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

    # Top-level bold metadata fields
    for line in lines:
        # ADR-154/166: Mode, Type, Output (was Class)
        mode_match = re.match(r"\*\*Mode:\*\*\s*(.*)", line)
        if mode_match:
            result["mode"] = mode_match.group(1).strip()
        type_match = re.match(r"\*\*Type:\*\*\s*(.*)", line)
        if type_match:
            result["type_key"] = type_match.group(1).strip()
        # ADR-166: **Output:** is canonical. Legacy **Class:** still parsed.
        output_match = re.match(r"\*\*Output:\*\*\s*(.*)", line)
        if output_match:
            result["output_kind"] = output_match.group(1).strip()
        class_match = re.match(r"\*\*Class:\*\*\s*(.*)", line)
        if class_match:
            legacy = class_match.group(1).strip()
            _legacy_map = {
                "context": "accumulates_context",
                "synthesis": "produces_deliverable",
                "back_office": "system_maintenance",
            }
            result["output_kind"] = _legacy_map.get(legacy, "produces_deliverable")

        cr_match = re.match(r"\*\*Context Reads:\*\*\s*(.*)", line)
        if cr_match:
            raw = cr_match.group(1).strip()
            result["context_reads"] = [d.strip() for d in raw.split(",") if d.strip() and d.strip() != "none"]
        cw_match = re.match(r"\*\*Context Writes:\*\*\s*(.*)", line)
        if cw_match:
            raw = cw_match.group(1).strip()
            result["context_writes"] = [d.strip() for d in raw.split(",") if d.strip() and d.strip() != "none"]
        # ADR-158: parse **Sources:** field into {platform: [id, ...]} dict
        src_match = re.match(r"\*\*Sources:\*\*\s*(.*)", line)
        if src_match:
            raw = src_match.group(1).strip()
            if raw and raw != "none":
                sources: dict = {}
                for part in raw.split(";"):
                    part = part.strip()
                    if ":" in part:
                        platform, ids_str = part.split(":", 1)
                        platform = platform.strip()
                        ids = [i.strip() for i in ids_str.split(",") if i.strip()]
                        if platform and ids:
                            sources[platform] = ids
                if sources:
                    result["sources"] = sources
        # ADR-154: output_category parsing removed

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

    # ADR-154: Mode from DB (scheduling index), enriched from TASK.md
    mode = row.get("mode")
    if not mode and task_md_parsed:
        mode = task_md_parsed.get("mode")

    return TaskResponse(
        id=str(row["id"]),
        slug=row["slug"],
        status=row["status"],
        mode=mode,
        schedule=row.get("schedule"),
        next_run_at=row["next_run_at"] if row.get("next_run_at") else None,
        last_run_at=row["last_run_at"] if row.get("last_run_at") else None,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        title=title,
        type_key=task_md_parsed.get("type_key") if task_md_parsed else None,
        output_kind=task_md_parsed.get("output_kind") if task_md_parsed else None,
        objective=objective,
        process=process,
        agent_slugs=task_md_parsed.get("agent_slugs") if task_md_parsed else None,
        delivery=task_md_parsed.get("delivery") if task_md_parsed else None,
        success_criteria=task_md_parsed.get("success_criteria") if task_md_parsed else None,
        output_spec=task_md_parsed.get("output_spec") if task_md_parsed else None,
        context_reads=task_md_parsed.get("context_reads") if task_md_parsed else None,
        context_writes=task_md_parsed.get("context_writes") if task_md_parsed else None,
        sources=task_md_parsed.get("sources") if task_md_parsed else None,
        essential=bool(row.get("essential", False)),
    )


# =============================================================================
# Task Type Catalog — DELETED (ADR-207 P4b, 2026-04-22)
# =============================================================================
# `GET /api/tasks/types` and `GET /api/tasks/types/{type_key}` REMOVED. Per
# ADR-207 P4b, TASK_TYPES is no longer a user-facing catalog — task creation
# happens via YARNNN self-declaration (agent + objective + capabilities +
# context domains) OR via the `type_key` convenience field on
# ManageTask(action="create"). The frontend CreateTaskModal stops fetching a
# type list; YARNNN is the sole task authoring surface.


# =============================================================================
# CRUD Routes
# =============================================================================

@router.get("")
async def list_tasks(
    auth: UserClient,
    status: Optional[str] = None,
    limit: int = 50,
    include_system: bool = False,
) -> list[TaskResponse]:
    """
    List user's tasks, enriched with TASK.md content from workspace.

    ADR-206: `back-office-*` tasks are infrastructure plumbing, not
    operator-facing work. Excluded from default response. Diagnostic surfaces
    (e.g. /settings/system) pass `include_system=true` to see them.
    """
    import asyncio
    from services.task_workspace import TaskWorkspace

    query = (
        auth.client.table("tasks")
        .select("id, slug, status, mode, schedule, next_run_at, last_run_at, created_at, updated_at, essential")
        .eq("user_id", auth.user_id)
        .order("created_at", desc=True)
        .limit(limit)
    )

    if status:
        query = query.eq("status", status)

    result = query.execute()
    rows = result.data or []

    if not include_system:
        rows = [r for r in rows if not (r.get("slug") or "").startswith("back-office-")]

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
        .select("id, slug, status, mode, schedule, next_run_at, last_run_at, created_at, updated_at, essential")
        .eq("user_id", auth.user_id)
        .eq("slug", slug)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        raise HTTPException(status_code=404, detail="Task not found")

    row = rows[0]

    # Read TASK.md + run_log + DELIVERABLE.md (detail-only enrichment)
    ws = TaskWorkspace(auth.client, auth.user_id, slug)
    content = await ws.read_task()
    parsed = _parse_task_md(content) if content else None
    run_log = await ws.read("memory/_run_log.md")
    deliverable_md = await ws.read("DELIVERABLE.md")

    response = _task_row_to_response(row, parsed)
    response.run_log = run_log
    # ADR-178 Phase 6: parse DELIVERABLE.md into structured quality contract
    response.deliverable_spec = _parse_deliverable_md(deliverable_md, output_kind=response.output_kind)
    return response


@router.post("", status_code=201)
async def create_task(
    request: TaskCreate,
    auth: UserClient,
) -> TaskResponse:
    """
    Create a new task — dispatches through ManageTask._handle_create.

    Per ADR-168 (singular implementation), the route is a thin shell over
    the canonical primitive. The primitive handles:
    - Slug generation + auto-suffix on collision
    - DB row insert with mode from payload (ADR-178 invariant — DB mode
      and TASK.md **Mode:** stay synced; the DB default 'recurring' no
      longer silently swallows reactive/goal tasks)
    - Full TASK.md serialization (**Slug:**, **Agent:**, **Mode:**,
      **Schedule:**, **Delivery:**, ## Objective, ## Success Criteria,
      ## Output Spec, ## Team, ## Page Structure) via _build_custom_task_md
      or build_task_md_from_type
    - DELIVERABLE.md scaffold from registry (ADR-149) or minimal custom
      template
    - feedback.md / memory/steering.md / awareness.md scaffolding
      (ADR-181, ADR-149, ADR-154)
    - Context-domain scaffolding for declared context_writes (ADR-151)
    - First-run auto-trigger for bootstrap and goal-mode tasks (ADR-154)

    Caller must supply `type_key` (registry-driven team + process) OR
    `agent_slug` (custom task with primary-agent assignment).
    """
    from services.primitives.manage_task import _handle_create
    from services.task_workspace import TaskWorkspace

    title = (request.title or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title is required")
    if not request.type_key and not request.agent_slug:
        raise HTTPException(
            status_code=400,
            detail="Either type_key or agent_slug is required",
        )

    payload = request.model_dump(exclude_none=True)

    result = await _handle_create(auth, payload)

    if not result.get("success"):
        status = 409 if result.get("error") == "duplicate_slug" else 400
        raise HTTPException(
            status_code=status,
            detail=result.get("message", result.get("error", "create_failed")),
        )

    # Re-read the created task so the response shape exactly matches
    # GET /tasks/{slug}. Cheap — one row + one file read.
    slug = result["task_slug"]
    row_result = (
        auth.client.table("tasks")
        .select(
            "id, slug, status, mode, schedule, next_run_at, last_run_at, "
            "created_at, updated_at, essential"
        )
        .eq("user_id", auth.user_id)
        .eq("slug", slug)
        .limit(1)
        .execute()
    )
    rows = row_result.data or []
    if not rows:
        raise HTTPException(status_code=500, detail="Task created but row not found")

    ws = TaskWorkspace(auth.client, auth.user_id, slug)
    task_md = await ws.read_task()
    parsed = _parse_task_md(task_md) if task_md else None
    return _task_row_to_response(rows[0], parsed)


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
        .select("id, slug, status, mode, schedule, next_run_at, last_run_at, created_at, updated_at, essential")
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
        # ADR-231 Phase 3.4 (migration 164): paused is now an explicit flag,
        # not a status enum value. Map "paused" → paused=true, status='active'.
        # tasks_status_check now rejects 'paused' as a status string.
        if request.status == "paused":
            db_updates["paused"] = True
            db_updates["status"] = "active"
        else:
            db_updates["paused"] = False
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


class TaskSourcesUpdate(BaseModel):
    # ADR-158: {platform: [id, ...]} e.g. {"slack": ["C123", "C456"]}
    sources: dict


@router.patch("/{slug}/sources")
async def update_task_sources(
    slug: str,
    request: TaskSourcesUpdate,
    auth: UserClient,
) -> TaskResponse:
    """
    Update the **Sources:** field in TASK.md for a platform task.

    ADR-158 Phase 2: Task-level source selection. Patches the Sources line in
    TASK.md without touching other task fields. Used by the Work surface source
    editor for slack-digest, notion-digest, github-digest, slack-respond,
    notion-update tasks.
    """
    from services.task_workspace import TaskWorkspace

    # Verify task exists and belongs to user
    existing = (
        auth.client.table("tasks")
        .select("id, slug, status, mode, schedule, next_run_at, last_run_at, created_at, updated_at, essential")
        .eq("user_id", auth.user_id)
        .eq("slug", slug)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Task not found")

    row = existing.data[0]
    ws = TaskWorkspace(auth.client, auth.user_id, slug)
    task_md = await ws.read_task()
    if not task_md:
        raise HTTPException(status_code=404, detail="TASK.md not found")

    # Serialize sources: "slack:C123,C456; notion:page-id-1"
    parts = []
    for platform, ids in request.sources.items():
        if ids:
            parts.append(f"{platform}:{','.join(ids)}")
    sources_str = "; ".join(parts) if parts else "none"

    # Patch the **Sources:** line in-place (or append after the nearest header field)
    if "**Sources:**" in task_md:
        task_md = re.sub(r"\*\*Sources:\*\*[^\n]*", f"**Sources:** {sources_str}", task_md)
    else:
        # Insert on a new line after **Context Writes:**, **Context Reads:**, or **Schedule:**
        inserted = False
        for pattern in (
            r"(\*\*Context Writes:\*\*[^\n]*)",
            r"(\*\*Context Reads:\*\*[^\n]*)",
            r"(\*\*Schedule:\*\*[^\n]*)",
        ):
            if re.search(pattern, task_md):
                task_md = re.sub(
                    pattern,
                    rf"\1\n**Sources:** {sources_str}",
                    task_md,
                    count=1,
                )
                inserted = True
                break
        if not inserted:
            task_md += f"\n**Sources:** {sources_str}"

    await ws.write("TASK.md", task_md, summary=f"Updated sources: {sources_str}")

    # Read back for response
    content = await ws.read_task()
    parsed = _parse_task_md(content) if content else None
    return _task_row_to_response(row, parsed)


@router.delete("/{slug}")
async def archive_task(
    slug: str,
    auth: UserClient,
) -> TaskResponse:
    """
    Archive a task (soft delete — sets status='archived').

    ADR-161: Essential tasks (e.g., daily-update) cannot be archived.
    They can be paused via PATCH if the user wants to opt out.
    """
    # Verify exists
    existing = (
        auth.client.table("tasks")
        .select("id, slug, status, mode, schedule, next_run_at, last_run_at, created_at, updated_at, essential")
        .eq("user_id", auth.user_id)
        .eq("slug", slug)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Task not found")

    # ADR-231 Phase 3.4: essential-task archive guard removed. Per ADR-231 D6,
    # daily-update reframes as a recurrence declaration; if the operator
    # deletes the YAML, the recurrence stops. There's no architectural
    # reason to forbid archival — the YAML is the source of truth.

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

        # ADR-145: Skip pipeline step outputs (step-N/output.md) — only show final outputs
        if "/step-" in path:
            continue

        # Extract date folder: strip prefix and /output.md
        relative = path[len(prefix):]  # "2026-03-25T1400/output.md"
        date_folder = relative.split("/")[0] if "/" in relative else relative

        # ADR-213: a folder is renderable when substrate is present
        # (sys_manifest.json for section-based composition, or output.md for
        # markdown fallback). HTML is composed on demand, not pre-written.
        sys_manifest_exists = await ws.exists(f"outputs/{date_folder}/sys_manifest.json")
        output_md_exists = await ws.exists(f"outputs/{date_folder}/output.md")
        renderable = sys_manifest_exists or output_md_exists

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
        if renderable:
            output_status = "delivered"

        entries.append(TaskOutputEntry(
            folder=date_folder,
            date=date_folder,
            status=output_status,
            renderable=renderable,
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
    # Fetch several rows to skip pipeline step outputs (step-N/output.md)
    prefix = ws._full_path("outputs/")
    try:
        result = (
            auth.client.table("workspace_files")
            .select("path, content")
            .eq("user_id", auth.user_id)
            .like("path", f"{prefix}%/output.md")
            .in_("lifecycle", ["active", "delivered"])
            .order("path", desc=True)
            .limit(20)
            .execute()
        )
    except Exception as e:
        logger.error(f"[TASKS] get_latest_task_output query failed for {slug}: {e}")
        return TaskOutputLatest()

    rows = result.data or []

    # ADR-145: Skip pipeline step outputs. Prefer newest dated folder over
    # outputs/latest so html/content stays aligned to a concrete run artifact.
    chosen = None
    for row in rows:
        path = row["path"]
        if "/step-" in path:
            continue
        relative = path[len(prefix):]
        folder = relative.split("/")[0] if "/" in relative else relative
        if folder != "latest":
            chosen = row
            break

    # Fallback: use /outputs/latest if no dated output exists.
    if not chosen:
        for row in rows:
            if "/step-" not in row["path"]:
                chosen = row
                break

    # Fallback: if no non-step output, use the latest step output
    if not chosen and rows:
        chosen = rows[0]

    if not chosen:
        return TaskOutputLatest()

    path = chosen["path"]
    content = chosen["content"]

    # Extract date folder
    relative = path[len(prefix):]
    date_folder = relative.split("/")[0] if "/" in relative else relative

    # ADR-213: Compose HTML on demand via the shared helper. The render
    # service caches by content hash, so repeat reads on unchanged substrate
    # are ~10ms.
    from services.compose.task_html import compose_task_output_html
    html_content = await compose_task_output_html(
        auth.client, auth.user_id, slug, date_folder
    )

    # Read manifest.json if available
    manifest_content = await ws.read(f"outputs/{date_folder}/manifest.json")
    manifest = None
    if manifest_content:
        try:
            manifest = _json.loads(manifest_content)
        except (ValueError, _json.JSONDecodeError):
            pass

    # ADR-170: Read sys_manifest.json for compose-substrate section provenance
    sys_manifest_content = await ws.read(f"outputs/{date_folder}/sys_manifest.json")
    sys_manifest = None
    sections_list: list[TaskSectionEntry] = []
    if sys_manifest_content:
        try:
            sys_manifest = _json.loads(sys_manifest_content)
            # Build ordered sections list from manifest.sections dict
            raw_sections = sys_manifest.get("sections", {})
            for slug, sec in raw_sections.items():
                sections_list.append(TaskSectionEntry(
                    slug=slug,
                    title=sec.get("title"),
                    kind=sec.get("kind"),
                    produced_at=sec.get("produced_at"),
                    source_files=sec.get("source_files", []),
                ))
        except (ValueError, _json.JSONDecodeError):
            pass

    return TaskOutputLatest(
        content=content,
        html_content=html_content,
        date=date_folder,
        manifest=manifest,
        sys_manifest=sys_manifest,
        sections=sections_list,
    )


@router.get("/{slug}/outputs/{date_folder}/steps")
async def get_pipeline_steps(
    slug: str,
    date_folder: str,
    auth: UserClient,
) -> PipelineStepsResponse:
    """
    ADR-145: Get pipeline step outputs for a specific run.
    Returns step manifests + content for the pipeline visualization tab.
    """
    from services.task_workspace import TaskWorkspace
    from services.task_pipeline import parse_task_md

    # Verify task exists and belongs to user
    existing = (
        auth.client.table("tasks")
        .select("id, slug")
        .eq("user_id", auth.user_id)
        .eq("slug", slug)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Task not found")

    ws = TaskWorkspace(auth.client, auth.user_id, slug)

    # ADR-207 P4b: read pipeline definition directly from parsed TASK.md
    # process_steps — no registry lookup. TASK.md is authoritative.
    task_md = await ws.read("TASK.md") or ""
    pipeline_definition = None
    if task_md:
        parsed = parse_task_md(task_md)
        process_steps = parsed.get("process_steps", [])
        if process_steps:
            pipeline_definition = [
                {
                    "agent_type": step.get("agent_ref", "unknown"),
                    "step": step.get("step", "step"),
                }
                for step in process_steps
            ]

    # Enumerate step folders by querying workspace for step manifests
    prefix = f"/tasks/{slug}/outputs/{date_folder}/step-"
    result = (
        auth.client.table("workspace_files")
        .select("path, content")
        .eq("user_id", auth.user_id)
        .like("path", f"{prefix}%/manifest.json")
        .order("path")
        .execute()
    )

    steps: list[PipelineStepEntry] = []
    for row in result.data or []:
        path = row["path"]
        # Extract step number from path like .../step-1/manifest.json
        try:
            step_folder = path.split("/step-")[1].split("/")[0]
            step_num = int(step_folder)
        except (IndexError, ValueError):
            continue

        # Parse manifest
        manifest = {}
        if row.get("content"):
            try:
                manifest = _json.loads(row["content"])
            except (ValueError, _json.JSONDecodeError):
                pass

        # Read step output content
        step_content = await ws.read(f"outputs/{date_folder}/step-{step_num}/output.md")

        steps.append(PipelineStepEntry(
            step=manifest.get("step", step_num),
            step_name=manifest.get("step_name", f"Step {step_num}"),
            agent_type=manifest.get("agent_type", "unknown"),
            agent_slug=manifest.get("agent_slug", "unknown"),
            content=step_content,
            tokens=manifest.get("tokens"),
        ))

    # Sort by step number
    steps.sort(key=lambda s: s.step)

    return ProcessStepsResponse(
        steps=steps,
        process_definition=pipeline_definition,
        type_key=type_key,
    )


@router.get("/{slug}/status")
async def get_run_status(
    slug: str,
    auth: UserClient,
) -> RunStatusResponse:
    """
    Get live execution status for a task's latest run.
    Reads status.json from the most recent output folder.
    Used by frontend for progress polling during execution.
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

    # Find the most recent status.json by listing output folders
    prefix = f"/tasks/{slug}/outputs/"
    result = (
        auth.client.table("workspace_files")
        .select("path, content")
        .eq("user_id", auth.user_id)
        .like("path", f"{prefix}%/status.json")
        .order("path", desc=True)
        .limit(1)
        .execute()
    )

    if not result.data:
        return RunStatusResponse(status="not_found")

    try:
        status_data = _json.loads(result.data[0]["content"])
        return RunStatusResponse(
            status=status_data.get("status", "unknown"),
            current_step=status_data.get("current_step", 0),
            total_steps=status_data.get("total_steps", 0),
            completed_steps=status_data.get("completed_steps", []),
            started_at=status_data.get("started_at"),
            completed_at=status_data.get("completed_at"),
        )
    except (ValueError, _json.JSONDecodeError):
        return RunStatusResponse(status="not_found")


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

    # ADR-213: compose on demand through the shared helper
    from services.compose.task_html import compose_task_output_html
    html_content = await compose_task_output_html(
        auth.client, auth.user_id, slug, date_folder
    )

    manifest_content = await ws.read(f"outputs/{date_folder}/manifest.json")
    manifest = None
    if manifest_content:
        try:
            manifest = _json.loads(manifest_content)
        except (ValueError, _json.JSONDecodeError):
            pass

    # ADR-170: sys_manifest for section provenance
    sys_manifest_content = await ws.read(f"outputs/{date_folder}/sys_manifest.json")
    sys_manifest = None
    sections_list: list[TaskSectionEntry] = []
    if sys_manifest_content:
        try:
            sys_manifest = _json.loads(sys_manifest_content)
            raw_sections = sys_manifest.get("sections", {})
            for s_slug, sec in raw_sections.items():
                sections_list.append(TaskSectionEntry(
                    slug=s_slug,
                    title=sec.get("title"),
                    kind=sec.get("kind"),
                    produced_at=sec.get("produced_at"),
                    source_files=sec.get("source_files", []),
                ))
        except (ValueError, _json.JSONDecodeError):
            pass

    return TaskOutputLatest(
        content=content,
        html_content=html_content,
        date=date_folder,
        manifest=manifest,
        sys_manifest=sys_manifest,
        sections=sections_list,
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

    # Execute task inline — same pipeline as scheduler, instant results
    try:
        from services.supabase import get_service_client
        from services.task_pipeline import execute_task

        svc_client = get_service_client()
        exec_result = await execute_task(svc_client, auth.user_id, slug)

        logger.info(f"[TASKS] Inline execution for '{slug}': {exec_result.get('status', 'unknown')}")
        return TaskRunTriggered(triggered=True, task_slug=slug)

    except Exception as e:
        logger.error(f"[TASKS] Inline execution failed for '{slug}': {e}")
        raise HTTPException(status_code=500, detail=f"Task execution failed: {str(e)}")


# =============================================================================
# Export — ADR-148 + ADR-213: Derive PDF/XLSX from on-demand composed HTML
# =============================================================================

@router.get("/{slug}/export")
async def export_task_output(
    slug: str,
    format: str,  # pdf, xlsx, docx
    auth: UserClient,
    date_folder: Optional[str] = None,
):
    """
    Export a task's composed output as PDF, XLSX, or DOCX.

    ADR-148 + ADR-213: Composes HTML on demand (via compose_task_output_html),
    then calls render service to convert HTML → requested format. The pipeline
    no longer pre-writes output.html; composition is a pull, not a push.
    Returns a redirect to the storage URL of the exported file.
    """
    import httpx
    import os
    from services.compose.task_html import compose_task_output_html

    RENDER_SERVICE_URL = os.environ.get("RENDER_SERVICE_URL", "https://yarnnn-render.onrender.com")
    RENDER_SERVICE_SECRET = os.environ.get("RENDER_SERVICE_SECRET", "")

    if format not in ("pdf", "xlsx", "docx"):
        raise HTTPException(status_code=400, detail=f"Unsupported export format: {format}. Use: pdf, xlsx, docx")

    # Resolve date_folder — explicit or latest output.md in workspace
    if not date_folder:
        md_result = (
            auth.client.table("workspace_files")
            .select("path")
            .eq("user_id", auth.user_id)
            .like("path", f"/tasks/{slug}/outputs/%/output.md")
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        if not md_result.data:
            raise HTTPException(status_code=404, detail="No output found for this task")
        md_path = md_result.data[0]["path"]
        prefix = f"/tasks/{slug}/outputs/"
        date_folder = md_path[len(prefix):].split("/")[0]

    md_path = f"/tasks/{slug}/outputs/{date_folder}/output.md"

    # Compose HTML on demand (cache-hit path inside the helper)
    html_content = await compose_task_output_html(
        auth.client, auth.user_id, slug, date_folder
    )

    # Read source markdown (still needed for xlsx table extraction path)
    md_result = (
        auth.client.table("workspace_files")
        .select("content")
        .eq("user_id", auth.user_id)
        .eq("path", md_path)
        .limit(1)
        .execute()
    )
    md_content = md_result.data[0]["content"] if md_result.data else None

    if not html_content and not md_content:
        raise HTTPException(status_code=404, detail="Output content not found")

    # Get task title for the export filename
    task_result = (
        auth.client.table("workspace_files")
        .select("content")
        .eq("user_id", auth.user_id)
        .eq("path", f"/tasks/{slug}/TASK.md")
        .limit(1)
        .execute()
    )
    title = slug  # fallback
    if task_result.data:
        first_line = (task_result.data[0]["content"] or "").split("\n")[0]
        if first_line.startswith("#"):
            title = first_line.lstrip("# ").strip()

    # Build render request
    if format in ("pdf", "docx"):
        skill_type = "pdf"
        render_input = {"title": title}
        if html_content:
            render_input["html"] = html_content
        else:
            render_input["markdown"] = md_content
    elif format == "xlsx":
        # Extract tables from markdown for XLSX
        import re
        tables = []
        if md_content:
            table_pattern = re.compile(
                r'(\|[^\n]+\|\n\|[-:\| ]+\|\n(?:\|[^\n]+\|\n?)+)',
                re.MULTILINE
            )
            for match in table_pattern.finditer(md_content):
                table_text = match.group(1).strip()
                lines = table_text.split("\n")
                if len(lines) < 3:
                    continue
                headers = [h.strip() for h in lines[0].strip("|").split("|")]
                rows = []
                for line in lines[2:]:
                    cells = [c.strip().strip("*") for c in line.strip("|").split("|")]
                    rows.append(cells)
                tables.append({"name": f"Table {len(tables)+1}", "headers": headers, "rows": rows})

        if not tables:
            raise HTTPException(status_code=400, detail="No tables found in output to export as XLSX")

        skill_type = "xlsx"
        render_input = {"title": title, "sheets": tables}

    # Call render service
    try:
        headers = {"Content-Type": "application/json"}
        if RENDER_SERVICE_SECRET:
            headers["X-Render-Secret"] = RENDER_SERVICE_SECRET

        async with httpx.AsyncClient(timeout=60.0) as http:
            resp = await http.post(
                f"{RENDER_SERVICE_URL}/render",
                json={
                    "type": skill_type,
                    "input": render_input,
                    "output_format": format,
                    "user_id": auth.user_id,
                },
                headers=headers,
            )

            if resp.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Render service returned {resp.status_code}: {resp.text[:200]}",
                )

            data = resp.json()
            if not data.get("success"):
                raise HTTPException(status_code=502, detail=f"Render failed: {data.get('error')}")

            output_url = data.get("output_url")
            if not output_url:
                raise HTTPException(status_code=502, detail="Render service returned no output URL")

            return {
                "success": True,
                "format": format,
                "url": output_url,
                "title": title,
                "content_type": data.get("content_type"),
                "size_bytes": data.get("size_bytes"),
            }

    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Render service unreachable: {str(e)}")


# =============================================================================
# Repurpose — ADR-148 Phase 4: Adapt output for different format/channel
# =============================================================================

@router.post("/{slug}/repurpose")
async def repurpose_task_output(
    slug: str,
    auth: UserClient,
    target: str = "summary",
    output_date: Optional[str] = None,
):
    """
    Repurpose a task output for a different format or channel.

    ADR-148 Phase 4: Routes mechanical targets (pdf, xlsx) to render service,
    editorial targets (linkedin, slides, summary) to agent adaptation.
    """
    from services.primitives.repurpose import handle_repurpose_output

    # Build a minimal auth-like object for the primitive
    class _Auth:
        def __init__(self, client, user_id):
            self.client = client
            self.user_id = user_id
    primitive_auth = _Auth(auth.client, auth.user_id)

    result = await handle_repurpose_output(primitive_auth, {
        "task_slug": slug,
        "target": target,
        "output_date": output_date or "",
    })

    if not result.get("success"):
        raise HTTPException(
            status_code=400 if result.get("error") in ("missing_task_slug", "invalid_target", "no_output", "no_tables") else 502,
            detail=result.get("message", "Repurpose failed"),
        )

    return result
