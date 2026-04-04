"""
Task Primitives — ADR-138

  CreateTask   — create a task (unit of work) and assign it to an agent
  TriggerTask  — run a task immediately, outside its normal cadence

Tasks are the scheduling/execution layer. Agents are identities; tasks are work.
"""

from __future__ import annotations

import json as _json
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# CreateTask
# =============================================================================

CREATE_TASK_TOOL = {
    "name": "CreateTask",
    "description": """Create a new task — a defined unit of work with objective, cadence, and delivery target.

Two creation paths:
1. From type registry (preferred): provide type_key + title. Pipeline, schedule, and objective are auto-populated from the registry.
2. Custom: provide title + agent_slug + objective manually.

type_key values: competitive-intel-brief, market-research-report, industry-signal-monitor, due-diligence-summary, meeting-prep-brief, stakeholder-update, relationship-health-digest, project-status-report, slack-recap, notion-sync-report, content-brief, launch-material, gtm-tracker

Required: title
Required (one of): type_key OR agent_slug

Optional: mode, objective, schedule, delivery, success_criteria, output_spec, focus (topic to customize the deliverable)

mode: 'recurring' (default), 'goal' (bounded, completes when done), 'reactive' (on-demand/event-triggered)
schedule: 'daily', 'weekly', 'monthly', or a cron expression (default from type or 'weekly')

Examples:
- CreateTask(title="Weekly Competitive Briefing", type_key="competitive-intel-brief", focus="AI agent platforms")
- CreateTask(title="Daily Slack Recap", type_key="slack-recap", delivery="user@example.com")
- CreateTask(title="Acme Corp Due Diligence", type_key="due-diligence-summary", focus="Acme Corp acquisition target")
- CreateTask(title="Custom Research Task", agent_slug="research-agent", objective={...})""",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Task name, e.g. 'Weekly Competitive Briefing'"
            },
            "type_key": {
                "type": "string",
                "description": "Task type from registry. Auto-populates pipeline, schedule, and objective."
            },
            "agent_slug": {
                "type": "string",
                "description": "Slug of the agent to assign (for custom tasks without type_key)."
            },
            "focus": {
                "type": "string",
                "description": "Topic or focus area to customize the deliverable, e.g. 'AI agent platforms' or 'Acme Corp'"
            },
            "mode": {
                "type": "string",
                "enum": ["recurring", "goal", "reactive"],
                "description": "Temporal behavior: 'recurring' (indefinite cadence), 'goal' (bounded), 'reactive' (on-demand)"
            },
            "objective": {
                "type": "object",
                "properties": {
                    "deliverable": {"type": "string"},
                    "audience": {"type": "string"},
                    "purpose": {"type": "string"},
                    "format": {"type": "string"}
                },
                "description": "Task objective (auto-populated from type_key if provided)"
            },
            "schedule": {
                "type": "string",
                "description": "Cadence override (defaults from type registry or 'weekly')"
            },
            "delivery": {
                "type": "string",
                "description": "Delivery target: email address or 'none'"
            },
            "success_criteria": {
                "type": "array",
                "items": {"type": "string"},
                "description": "What constitutes success for this task"
            },
            "output_spec": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Expected sections in output"
            }
        },
        "required": ["title"]
    }
}


def _slugify(text: str) -> str:
    """Generate a filesystem-safe slug from text."""
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9-]", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:50] or "task"


def _compute_next_run(schedule: str) -> Optional[str]:
    """Compute next_run_at from a human-readable schedule string.

    For simple cadences (daily/weekly/monthly), returns a timestamp.
    For cron expressions, returns None (scheduler will interpret).
    """
    now = datetime.now(timezone.utc)
    schedule_lower = schedule.lower().strip()

    if schedule_lower == "daily":
        # Next day at 09:00 UTC
        next_run = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        return next_run.isoformat()
    elif schedule_lower == "weekly":
        # Next Monday at 09:00 UTC
        days_ahead = 7 - now.weekday()  # 0=Monday
        if days_ahead == 0:
            days_ahead = 7
        next_run = (now + timedelta(days=days_ahead)).replace(hour=9, minute=0, second=0, microsecond=0)
        return next_run.isoformat()
    elif schedule_lower == "monthly":
        # First of next month at 09:00 UTC
        if now.month == 12:
            next_run = now.replace(year=now.year + 1, month=1, day=1, hour=9, minute=0, second=0, microsecond=0)
        else:
            next_run = now.replace(month=now.month + 1, day=1, hour=9, minute=0, second=0, microsecond=0)
        return next_run.isoformat()
    else:
        # Cron expression or unknown — store raw, scheduler interprets
        return None


def _build_task_md(
    title: str,
    slug: str,
    agent_slug: str,
    mode: str = "recurring",
    objective: Optional[dict] = None,
    schedule: Optional[str] = None,
    delivery: Optional[str] = None,
    success_criteria: Optional[list] = None,
    output_spec: Optional[list] = None,
) -> str:
    """Build TASK.md content."""
    lines = [f"# {title}", "", f"**Slug:** {slug}", f"**Agent:** {agent_slug}", f"**Mode:** {mode}"]

    if schedule:
        lines.append(f"**Schedule:** {schedule}")
    if delivery:
        lines.append(f"**Delivery:** {delivery}")

    if objective:
        lines.append("")
        lines.append("## Objective")
        for key in ["deliverable", "audience", "purpose", "format"]:
            val = objective.get(key)
            if val:
                lines.append(f"- **{key.capitalize()}:** {val}")

    if success_criteria:
        lines.append("")
        lines.append("## Success Criteria")
        for criterion in success_criteria:
            lines.append(f"- {criterion}")

    if output_spec:
        lines.append("")
        lines.append("## Output Spec")
        for section in output_spec:
            lines.append(f"- {section}")

    lines.append("")
    return "\n".join(lines)


async def handle_create_task(auth: Any, input: dict) -> dict:
    """
    Handle CreateTask primitive — create a task and assign it to an agent.

    Two paths:
    A. type_key provided → resolve from registry, auto-populate pipeline + objective
    B. agent_slug provided → custom task (existing behavior)

    Steps:
    1. Extract fields, resolve type_key if provided
    2. Generate slug from title
    3. Resolve agent(s) — from pipeline or explicit agent_slug
    4. Create DB row in tasks table
    5. Write TASK.md via TaskWorkspace
    6. Update agent's memory/tasks.json for primary agent
    7. Calculate next_run_at from schedule
    8. Return success with task slug
    """
    title = input.get("title", "").strip()
    type_key = input.get("type_key", "").strip() or None
    agent_slug = input.get("agent_slug", "").strip() or None
    focus = input.get("focus", "").strip() or None
    mode = input.get("mode", "recurring")
    objective = input.get("objective")
    schedule = input.get("schedule")
    delivery = input.get("delivery")
    success_criteria = input.get("success_criteria")
    output_spec = input.get("output_spec")

    # Validate mode
    if mode not in ("recurring", "goal", "reactive"):
        mode = "recurring"

    if not title:
        return {"success": False, "error": "missing_title", "message": "title is required"}
    if not type_key and not agent_slug:
        return {"success": False, "error": "missing_type_or_agent", "message": "Either type_key or agent_slug is required"}

    user_id = auth.user_id
    slug = _slugify(title)

    # --- Path A: Type-key based creation (ADR-145) ---
    resolved_agent_slugs: list[str] = []
    task_md_content: Optional[str] = None

    if type_key:
        from services.task_types import get_task_type, resolve_process_agents, build_task_md_from_type

        task_type_def = get_task_type(type_key)
        if not task_type_def:
            return {"success": False, "error": "unknown_type", "message": f"Task type '{type_key}' not found in registry."}

        # Use type's default schedule if not overridden
        if not schedule:
            schedule = task_type_def["default_schedule"]
            if schedule == "on-demand":
                schedule = None  # reactive tasks don't have a schedule

        # ADR-154: Mode from registry, not inferred from schedule
        if not input.get("mode"):
            from services.task_types import get_default_mode
            mode = get_default_mode(type_key)

        # Resolve process agents from user's roster
        agents_result = (
            auth.client.table("agents")
            .select("id, title, slug, role, status")
            .eq("user_id", user_id)
            .execute()
        )
        user_agents = agents_result.data or []

        resolved_steps = resolve_process_agents(type_key, user_agents)
        if resolved_steps:
            resolved_agent_slugs = [s["agent_slug"] for s in resolved_steps if s["agent_slug"]]

        # Use first process agent as primary (for single-step compat)
        if not agent_slug and resolved_agent_slugs:
            agent_slug = resolved_agent_slugs[0]

        # ADR-158 Phase 2: Auto-populate sources from platform_connections
        # for platform task types (requires_platform set in registry)
        task_sources = input.get("sources")  # explicit override from TP
        if not task_sources and task_type_def.get("requires_platform"):
            platform = task_type_def["requires_platform"]
            try:
                conn_result = (
                    auth.client.table("platform_connections")
                    .select("landscape")
                    .eq("user_id", user_id)
                    .eq("provider", platform)
                    .eq("status", "connected")
                    .maybe_single()
                    .execute()
                )
                if conn_result and conn_result.data:
                    landscape = conn_result.data.get("landscape") or {}
                    selected = landscape.get("selected_sources") or []
                    if selected:
                        source_ids = [s.get("id") for s in selected if s.get("id")]
                        if source_ids:
                            task_sources = {platform: source_ids}
                            logger.info(f"[CREATE_TASK] Auto-populated {len(source_ids)} {platform} sources from platform_connections")
            except Exception as e:
                logger.warning(f"[CREATE_TASK] Failed to read platform sources: {e}")

        # Build TASK.md from type template
        task_md_content = build_task_md_from_type(
            type_key=type_key,
            title=title,
            slug=slug,
            focus=focus,
            schedule=schedule,
            delivery=delivery,
            agent_slugs=resolved_agent_slugs or None,
            sources=task_sources,
        )

    # --- Verify primary agent exists ---
    if not agent_slug:
        return {"success": False, "error": "no_agent_resolved", "message": "Could not resolve an agent for this task type. Check your agent roster."}

    try:
        agent_result = (
            auth.client.table("agents")
            .select("id, title, slug")
            .eq("user_id", user_id)
            .eq("slug", agent_slug)
            .maybe_single()
            .execute()
        )
        if not agent_result or not agent_result.data:
            return {
                "success": False,
                "error": "agent_not_found",
                "message": f"Agent '{agent_slug}' not found. Create the agent first.",
            }
    except Exception as e:
        logger.error(f"[CREATE_TASK] Agent lookup failed: {e}")
        return {"success": False, "error": "agent_lookup_failed", "message": str(e)}

    # Default schedule for custom tasks
    if not schedule:
        schedule = "weekly"

    # ADR-154: First run on creation for tasks with bootstrap criteria
    # Bootstrap phase → run immediately. Otherwise → standard cadence.
    has_bootstrap = False
    if type_key:
        from services.task_types import get_bootstrap_criteria
        has_bootstrap = bool(get_bootstrap_criteria(type_key))

    if has_bootstrap:
        next_run_at = datetime.now(timezone.utc).isoformat()
    else:
        next_run_at = _compute_next_run(schedule) if schedule else None

    # Create tasks row
    now = datetime.now(timezone.utc)
    # Try insert with auto-suffix on duplicate slug
    task_id = None
    max_attempts = 5
    for attempt in range(max_attempts):
        try_slug = slug if attempt == 0 else f"{slug}-{attempt + 1}"
        try:
            row = {
                "user_id": user_id,
                "slug": try_slug,
                "mode": mode,
                "status": "active",
                "schedule": schedule,
                "next_run_at": next_run_at,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
            insert_result = auth.client.table("tasks").insert(row).execute()
            if insert_result.data:
                task_id = insert_result.data[0]["id"]
                slug = try_slug  # Use the successful slug going forward
                break
        except Exception as e:
            error_str = str(e)
            if "tasks_user_slug_unique" in error_str:
                if attempt < max_attempts - 1:
                    continue  # Try next suffix
                return {
                    "success": False,
                    "error": "duplicate_slug",
                    "message": f"A task with slug '{slug}' already exists (tried {max_attempts} suffixes).",
                }
            logger.error(f"[CREATE_TASK] DB insert failed: {e}")
            return {"success": False, "error": "insert_failed", "message": error_str}
    if not task_id:
        return {"success": False, "error": "insert_failed", "message": "Failed to create task row"}

    # Write TASK.md via TaskWorkspace
    try:
        from services.task_workspace import TaskWorkspace
        tw = TaskWorkspace(auth.client, user_id, slug)

        if task_md_content:
            # Type-based: use pre-built TASK.md from registry
            task_md = task_md_content
        else:
            # Custom: build manually
            task_md = _build_task_md(
                title=title,
                slug=slug,
                agent_slug=agent_slug,
                mode=mode,
                objective=objective,
                schedule=schedule,
                delivery=delivery,
                success_criteria=success_criteria,
                output_spec=output_spec,
            )
        await tw.write("TASK.md", task_md, summary=f"Task definition: {title}", tags=["task", "definition"])

        # ADR-149: Scaffold DELIVERABLE.md from type registry
        if type_key:
            from services.task_types import build_deliverable_md_from_type
            deliverable_md = build_deliverable_md_from_type(type_key)
            if deliverable_md:
                await tw.write("DELIVERABLE.md", deliverable_md,
                              summary=f"Deliverable spec for {title}", tags=["deliverable", "spec"])
        else:
            # Custom task — minimal deliverable scaffold
            custom_deliverable = (
                "# Deliverable Specification\n\n"
                "## Expected Output\n"
                f"- Format: HTML document\n"
                f"- Layout: As specified in objective\n\n"
                "## Expected Assets\n"
                "- Visual assets optional where data supports\n\n"
                "## Quality Criteria\n"
                + ("\n".join(f"- {c}" for c in success_criteria) + "\n" if success_criteria else "- Output addresses the stated objective\n")
                + "\n## Audience\n"
                + (objective.get("audience", "") if isinstance(objective, dict) else "")
                + "\n\n## User Preferences (inferred)\n"
                "<!-- Populated by feedback inference (ADR-149). Empty at creation. -->\n"
            )
            await tw.write("DELIVERABLE.md", custom_deliverable,
                          summary=f"Deliverable spec for {title}", tags=["deliverable", "spec"])

        # ADR-149: Seed empty task memory files
        await tw.write("memory/feedback.md",
                      "# Task Feedback\n<!-- User corrections + TP evaluations. Newest first. ADR-149. -->\n",
                      summary="ADR-149: task feedback file", tags=["memory"])
        await tw.write("memory/steering.md",
                      "# Steering Notes\n<!-- TP management notes for next cycle. Overwritten per evaluation. ADR-149. -->\n",
                      summary="ADR-149: task steering file", tags=["memory"])

        # ADR-154: Seed task awareness file
        await tw.write("awareness.md",
                      "# Task Awareness\n\nFirst run — no prior cycles.\n",
                      summary="ADR-154: task awareness file", tags=["awareness"])

        # ADR-151: Scaffold workspace context domains for this task's context_writes
        if type_key:
            try:
                from services.task_types import get_task_type
                from services.directory_registry import get_domain, get_domain_folder, get_synthesis_content
                from services.workspace import UserMemory

                task_type_def = get_task_type(type_key)
                context_writes = (task_type_def or {}).get("context_writes", [])

                if context_writes:
                    um = UserMemory(auth.client, user_id)
                    for domain_key in context_writes:
                        domain = get_domain(domain_key)
                        if not domain:
                            continue
                        folder = get_domain_folder(domain_key)
                        if not folder:
                            continue

                        # Check if domain synthesis file already exists (domain already scaffolded)
                        synthesis = get_synthesis_content(domain_key)
                        if synthesis:
                            synthesis_file, synthesis_template = synthesis
                            existing = await um.read(f"{folder}/{synthesis_file}")
                            if not existing:
                                await um.write(
                                    f"{folder}/{synthesis_file}",
                                    synthesis_template,
                                    summary=f"ADR-151: scaffold {domain_key} domain",
                                    tags=["context", domain_key],
                                    metadata={"domain": domain_key, "type": "synthesis"},
                                )
                                logger.info(f"[CREATE_TASK] Scaffolded context domain: {domain_key}")

                        # ADR-154: Scaffold _tracker.md for entity-bearing domains
                        from services.directory_registry import has_entity_tracker, get_tracker_path, build_tracker_md
                        if has_entity_tracker(domain_key):
                            tracker_path = get_tracker_path(domain_key)
                            if tracker_path:
                                existing_tracker = await um.read(tracker_path)
                                if not existing_tracker:
                                    tracker_content = build_tracker_md(domain_key, [])
                                    await um.write(
                                        tracker_path, tracker_content,
                                        summary=f"ADR-154: entity tracker for {domain_key}",
                                        tags=["tracker", domain_key],
                                    )
            except Exception as e:
                logger.warning(f"[CREATE_TASK] Context domain scaffold failed (non-fatal): {e}")

    except Exception as e:
        logger.warning(f"[CREATE_TASK] TASK.md write failed (non-fatal): {e}")

    # ADR-154: memory/tasks.json dissolved — task assignments tracked via TASK.md, not agent memory

    # Activity log
    try:
        from services.activity_log import write_activity
        await write_activity(
            client=auth.client,
            user_id=user_id,
            event_type="task_created",
            summary=f"Created task: {title}" + (f" (type: {type_key})" if type_key else f" (agent: {agent_slug})"),
            event_ref=task_id,
            metadata={
                "task_slug": slug,
                "type_key": type_key,
                "agent_slug": agent_slug,
                "process_agents": resolved_agent_slugs or [agent_slug],
                "schedule": schedule,
            },
        )
    except Exception:
        pass

    # Update WORKSPACE.md manifest (living manifest — ADR-152)
    try:
        from services.workspace_init import update_workspace_manifest
        await update_workspace_manifest(auth.client, user_id)
    except Exception:
        pass  # Non-fatal

    # Build process narration for TP to explain the workflow
    process_narration = None
    if type_key and resolved_steps:
        step_descriptions = []
        for s in resolved_steps:
            agent_label = s.get("agent_title") or s.get("agent_type", "agent")
            step_descriptions.append(f"{agent_label} ({s['step']})")
        process_narration = " → ".join(step_descriptions)

    return {
        "success": True,
        "task_id": task_id,
        "task_slug": slug,
        "type_key": type_key,
        "agent_slug": agent_slug,
        "process_agents": resolved_agent_slugs or [agent_slug],
        "process_narration": process_narration,
        "mode": mode,
        "schedule": schedule,
        "next_run_at": next_run_at,
        "message": f"Created task '{title}'" + (f" ({type_key})" if type_key else "") + f" — {schedule or 'on-demand'}."
                   + (f" Process: {process_narration}." if process_narration else ""),
        "ui_action": {
            "type": "NAVIGATE",
            "data": {"url": f"/tasks/{slug}", "label": title},
        },
    }


# ADR-146: TriggerTask, UpdateTask, PauseTask, ResumeTask deleted.
# Absorbed into ManageTask(action="trigger"|"update"|"pause"|"resume") in manage_task.py.
