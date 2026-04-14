"""
ManageTask Primitive — ADR-146 + ADR-149 + ADR-168: Unified Task Lifecycle

Single task lifecycle primitive. 9 actions:
- create   — scaffold a new task from a task type and assign to an agent (ADR-168)
- trigger  — run task immediately
- update   — change schedule, delivery, mode, type, sources (ADR-158)
- pause    — stop scheduled runs
- resume   — restore scheduled runs
- evaluate — TP reads output + DELIVERABLE.md → quality judgment (ADR-149)
- steer    — TP writes cycle-specific guidance to steering.md (ADR-149)
- complete — mark task done, clear scheduling (ADR-149)
- archive  — soft-delete a task (essential tasks cannot be archived)

Design principle P3 (One Tool Per Decision): TP decides "manage this task"
and picks the action. One tool, one decision. Symmetric with ManageAgent,
which covers agent creation in the same primitive.

ADR-168 Commit 3 folded the former CreateTask primitive into action="create".
No parallel creation path, no shim, no CreateTask tool — singular implementation.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from services.schedule_utils import calculate_next_run_at, get_user_timezone

logger = logging.getLogger(__name__)


MANAGE_TASK_TOOL = {
    "name": "ManageTask",
    "description": """Manage task lifecycle: create, trigger, update, pause, resume, evaluate, steer, complete, or archive.

- create: scaffold from type_key (preferred, auto-populates pipeline/agent/schedule) or agent_slug + objective
- trigger: run immediately; pass context= to focus this run only
- update: change schedule, delivery, mode, type_key, or sources
- pause/resume: stop or restore scheduled runs
- evaluate: assess latest output against DELIVERABLE.md; returns criteria_met, gaps, recommendation
- steer: write guidance for next run (steering=); pass target_section= to force one section to regenerate
- complete: mark goal task done, clear scheduling
- archive: soft-delete a task (essential tasks cannot be archived; use pause instead)""",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "trigger", "update", "pause", "resume", "evaluate", "steer", "complete", "archive"],
                "description": "What to do with the task"
            },
            "task_slug": {
                "type": "string",
                "description": "The task to manage. Required for all actions EXCEPT 'create' (where slug is generated from title)."
            },
            # --- action="create" fields (ADR-168 Commit 3: absorbed from former CreateTask primitive) ---
            "title": {
                "type": "string",
                "description": "For action='create': task name, e.g. 'Weekly Competitive Briefing'"
            },
            "type_key": {
                "type": "string",
                "description": "For action='create' or 'update': task type from the registry (auto-populates pipeline + schedule + agents). Required for action='create' unless agent_slug is provided."
            },
            "agent_slug": {
                "type": "string",
                "description": "For action='create': agent to assign (for custom tasks without type_key)."
            },
            "focus": {
                "type": "string",
                "description": "For action='create': topic or focus area to customize the deliverable, e.g. 'AI agent platforms' or 'Acme Corp'"
            },
            "objective": {
                "type": "object",
                "properties": {
                    "deliverable": {"type": "string"},
                    "audience": {"type": "string"},
                    "purpose": {"type": "string"},
                    "format": {"type": "string"},
                },
                "description": "For action='create' with a custom task: task objective (auto-populated from type_key if provided)"
            },
            "success_criteria": {
                "type": "array",
                "items": {"type": "string"},
                "description": "For action='create': what constitutes success for this task"
            },
            "output_spec": {
                "type": "array",
                "items": {"type": "string"},
                "description": "For action='create': expected sections in output (flat list — use page_structure for structured compose layout)"
            },
            "page_structure": {
                "type": "array",
                "items": {"type": "object"},
                "description": "For action='create' with a custom produces_deliverable task: structured section layout for the compose pipeline. Each item: {id, title, kind, source_domains?, asset_type?}. Kind values: narrative, metric-cards, entity-grid, comparison-table, trend-chart, callout. Takes precedence over registry page_structure. Omit for accumulates_context/external_action/system_maintenance tasks."
            },
            "team": {
                "type": "array",
                "items": {"type": "string"},
                "description": "For action='create': explicit team composition for this task — list of specialist role keys (e.g. ['researcher', 'analyst', 'writer']). Overrides registry_default_team. TP uses this when the work intent warrants a non-default composition. Omit to use registry default."
            },
            # --- Shared fields used by multiple actions ---
            "context": {
                "type": "string",
                "description": "For action='trigger': optional context to inject for this run"
            },
            "steering": {
                "type": "string",
                "description": "For action='steer': guidance for the next execution cycle"
            },
            "target_section": {
                "type": "string",
                "description": "For action='steer': optional section slug to force regeneration of (produces_deliverable tasks only, ADR-170). E.g. 'executive-summary'. Forces that section stale regardless of domain freshness."
            },
            "schedule": {
                "type": "string",
                "description": "For action='create' or 'update': cadence (daily, weekly, monthly, or cron expression)"
            },
            "delivery": {
                "type": "string",
                "description": "For action='create' or 'update': delivery target (email or 'none')"
            },
            "mode": {
                "type": "string",
                "enum": ["recurring", "goal", "reactive"],
                "description": "For action='create' or 'update': temporal behavior"
            },
            "sources": {
                "type": "object",
                "description": "For action='create' or 'update': per-task platform source selection. Map of platform → list of source IDs. E.g. {\"slack\": [\"C123\", \"C456\"]}"
            },
        },
        "required": ["action"]
    }
}


async def handle_manage_task(auth: Any, input: dict) -> dict:
    """
    Handle ManageTask — route to appropriate action handler.

    ADR-146: Single entry point for task lifecycle mutations.
    ADR-168 Commit 3: action="create" absorbed from the former CreateTask primitive.
    """
    action = input.get("action", "")

    valid_actions = ("create", "trigger", "update", "pause", "resume", "evaluate", "steer", "complete", "archive")
    if action not in valid_actions:
        return {"success": False, "error": "invalid_action", "message": f"action must be one of: {', '.join(valid_actions)}"}

    # action="create" is the only action that doesn't require task_slug — the slug
    # is generated from the title inside the handler.
    if action == "create":
        return await _handle_create(auth, input)

    task_slug = input.get("task_slug", "").strip()
    if not task_slug:
        return {"success": False, "error": "missing_slug", "message": "task_slug is required for this action"}

    if action == "trigger":
        return await _handle_trigger(auth, task_slug, input)
    elif action == "update":
        return await _handle_update(auth, task_slug, input)
    elif action == "pause":
        return await _handle_pause(auth, task_slug)
    elif action == "resume":
        return await _handle_resume(auth, task_slug)
    elif action == "evaluate":
        return await _handle_evaluate(auth, task_slug)
    elif action == "steer":
        return await _handle_steer(auth, task_slug, input)
    elif action == "complete":
        return await _handle_complete(auth, task_slug)
    elif action == "archive":
        return await _handle_archive(auth, task_slug)

    return {"success": False, "error": "unknown_action", "message": f"Unhandled action: {action}"}


# ---------------------------------------------------------------------------
# Internal handlers — absorbed from task.py
# ---------------------------------------------------------------------------

def _compute_next_run(schedule: str, user_timezone: str = "UTC") -> Optional[str]:
    """Compute next_run_at from schedule using user-local cadence semantics."""
    next_run = calculate_next_run_at(
        schedule=schedule,
        last_run_at=datetime.now(timezone.utc),
        user_timezone=user_timezone,
    )
    return next_run.isoformat() if next_run else None


async def _find_task(auth: Any, task_slug: str, select: str = "id, slug, status, schedule, mode") -> dict:
    """Look up task by slug. Returns task dict or error dict."""
    try:
        result = (
            auth.client.table("tasks")
            .select(select)
            .eq("user_id", auth.user_id)
            .eq("slug", task_slug)
            .maybe_single()
            .execute()
        )
        if not result or not result.data:
            return {"error": True, "success": False, "error_code": "not_found", "message": f"Task '{task_slug}' not found."}
        return result.data
    except Exception as e:
        return {"error": True, "success": False, "error_code": "lookup_failed", "message": str(e)}


async def _handle_trigger(auth: Any, task_slug: str, input: dict) -> dict:
    """Run task immediately — executes inline, not via scheduler queue.

    Calls execute_task() directly for instant results. Output goes to the same
    paths as scheduler-triggered runs (agent_runs, workspace files, task outputs).
    """
    context = input.get("context")
    now = datetime.now(timezone.utc)

    task = await _find_task(auth, task_slug, select="id, slug, status, schedule")
    if task.get("error"):
        return task

    if task["status"] != "active":
        return {"success": False, "error": "not_active", "message": f"Task '{task_slug}' is {task['status']} — cannot trigger."}

    # Optionally write trigger context before execution
    if context:
        try:
            from services.task_workspace import TaskWorkspace
            tw = TaskWorkspace(auth.client, auth.user_id, task_slug)
            await tw.write(
                "working/trigger_context.md",
                f"# Trigger Context\n\n{context}\n\n_Triggered at {now.strftime('%Y-%m-%d %H:%M UTC')}_\n",
                summary="Ad-hoc trigger context",
                tags=["trigger", "ephemeral"],
                lifecycle="ephemeral",
            )
        except Exception as e:
            logger.warning(f"[MANAGE_TASK] Context write failed (non-fatal): {e}")

    # Execute task inline — same pipeline as scheduler, instant results
    try:
        from services.supabase import get_service_client
        from services.task_pipeline import execute_task

        svc_client = get_service_client()
        result = await execute_task(svc_client, auth.user_id, task_slug)

        # ADR-164: task_triggered activity_log write removed. Task triggers
        # are visible via the task's run history (agent_runs + task outputs)
        # and the task's `last_run_at` column — no need to denormalize into
        # activity_log.

        if result.get("success"):
            return {
                "success": True,
                "task_id": task["id"],
                "task_slug": task_slug,
                "message": f"Task '{task_slug}' executed successfully. {result.get('message', '')}",
                "run_result": result,
                "ui_action": {
                    "type": "NAVIGATE",
                    "data": {"url": f"/agents", "label": f"View {task_slug}"},
                },
            }
        else:
            return {
                "success": False,
                "task_slug": task_slug,
                "error": "execution_failed",
                "message": f"Task execution failed: {result.get('message', 'unknown error')}",
                "run_result": result,
            }

    except Exception as e:
        logger.error(f"[MANAGE_TASK] Inline execution failed for {task_slug}: {e}")
        return {"success": False, "error": "execution_error", "message": str(e)}


async def _handle_update(auth: Any, task_slug: str, input: dict) -> dict:
    """Update task schedule, delivery, or mode. Was: handle_update_task."""
    task = await _find_task(auth, task_slug)
    if task.get("error"):
        return task

    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    changes = []
    user_timezone = get_user_timezone(auth.client, auth.user_id)

    new_schedule = input.get("schedule")
    if new_schedule:
        update_data["schedule"] = new_schedule
        next_run = _compute_next_run(new_schedule, user_timezone=user_timezone)
        if next_run:
            update_data["next_run_at"] = next_run
        changes.append(f"schedule → {new_schedule}")

    new_mode = input.get("mode")
    if new_mode and new_mode in ("recurring", "goal", "reactive"):
        update_data["mode"] = new_mode
        changes.append(f"mode → {new_mode}")
    else:
        new_mode = None  # ensure we don't accidentally patch TASK.md if invalid/absent

    new_delivery = input.get("delivery")
    if new_delivery is not None:
        changes.append(f"delivery → {new_delivery}")

    new_type_key = input.get("type_key", "").strip() or None
    new_sources = input.get("sources")  # ADR-158 Phase 2

    if not changes and not new_type_key and not new_sources:
        return {"success": False, "error": "no_changes", "message": "No changes specified. Use schedule, delivery, mode, or type_key parameters."}

    # Apply DB update
    try:
        auth.client.table("tasks").update(update_data).eq("id", task["id"]).execute()
    except Exception as e:
        return {"success": False, "error": "update_failed", "message": str(e)}

    # Update TASK.md for delivery and/or type_key
    from services.task_workspace import TaskWorkspace
    import re
    tw = TaskWorkspace(auth.client, auth.user_id, task_slug)

    if new_delivery is not None:
        try:
            task_md = await tw.read_task()
            if task_md:
                if "**Delivery:**" in task_md:
                    task_md = re.sub(r"\*\*Delivery:\*\*.*", f"**Delivery:** {new_delivery}", task_md)
                else:
                    task_md += f"\n**Delivery:** {new_delivery}"
                await tw.write("TASK.md", task_md, summary=f"Updated delivery: {new_delivery}")
        except Exception as e:
            logger.warning(f"[MANAGE_TASK] TASK.md delivery update failed (non-fatal): {e}")

    # ADR-178 critical invariant: tasks.mode (DB) == TASK.md **Mode:** at all times.
    # Both are patched atomically in the same update action.
    if new_mode is not None:
        try:
            task_md = await tw.read_task()
            if task_md:
                if "**Mode:**" in task_md:
                    task_md = re.sub(r"\*\*Mode:\*\*.*", f"**Mode:** {new_mode}", task_md)
                else:
                    task_md += f"\n**Mode:** {new_mode}"
                await tw.write("TASK.md", task_md, summary=f"Updated mode: {new_mode}")
        except Exception as e:
            logger.warning(f"[MANAGE_TASK] TASK.md mode update failed (non-fatal): {e}")

    # ADR-158 Phase 2: Update sources in TASK.md
    if new_sources and isinstance(new_sources, dict):
        try:
            task_md = await tw.read_task()
            if task_md:
                # Serialize sources
                parts = []
                for platform, ids in new_sources.items():
                    if isinstance(ids, list) and ids:
                        parts.append(f"{platform}:{','.join(str(i) for i in ids)}")
                sources_str = "; ".join(parts) if parts else "none"

                if "**Sources:**" in task_md:
                    task_md = re.sub(r"\*\*Sources:\*\*.*", f"**Sources:** {sources_str}", task_md)
                else:
                    # Insert after Context Writes line, or after Delivery
                    if "**Context Writes:**" in task_md:
                        task_md = re.sub(
                            r"(\*\*Context Writes:\*\*.*)",
                            rf"\1\n**Sources:** {sources_str}",
                            task_md,
                        )
                    else:
                        task_md += f"\n**Sources:** {sources_str}"
                await tw.write("TASK.md", task_md, summary=f"Updated sources: {sources_str}")
                changes.append(f"sources → {sources_str}")
        except Exception as e:
            logger.warning(f"[MANAGE_TASK] TASK.md sources update failed (non-fatal): {e}")

    # Assign type_key → updates TASK.md with type + process definition from registry
    if new_type_key:
        try:
            from services.task_types import get_task_type, resolve_process_agents

            task_type_def = get_task_type(new_type_key)
            if not task_type_def:
                return {"success": False, "error": "unknown_type", "message": f"Task type '{new_type_key}' not found in registry."}

            # Read current TASK.md
            task_md = await tw.read_task() or ""

            # Update or add **Type:** line
            if "**Type:**" in task_md:
                task_md = re.sub(r"\*\*Type:\*\*.*", f"**Type:** {new_type_key}", task_md)
            else:
                # Insert after first line (title)
                lines = task_md.split("\n")
                insert_pos = 1 if len(lines) > 0 else 0
                lines.insert(insert_pos, f"\n**Type:** {new_type_key}")
                task_md = "\n".join(lines)

            # Resolve process agents from user's roster
            user_agents = auth.client.table("agents").select("slug, role, title, status").eq("user_id", auth.user_id).eq("status", "active").execute()
            resolved_steps = resolve_process_agents(new_type_key, user_agents.data or [])

            # Replace or add ## Process section
            if "## Process" in task_md:
                # Remove existing process section
                before_process = task_md[:task_md.index("## Process")]
                after_idx = task_md.find("\n## ", task_md.index("## Process") + 1)
                after_process = task_md[after_idx:] if after_idx != -1 else ""
                task_md = before_process.rstrip() + "\n\n"
            else:
                task_md = task_md.rstrip() + "\n\n"

            # Build process section from resolved steps
            process_lines = ["## Process\n"]
            for i, step in enumerate(resolved_steps, 1):
                process_lines.append(f"### Step {i}: {step.get('step', f'Step {i}')}")
                process_lines.append(f"- **Agent:** {step.get('agent_slug', 'unassigned')}")
                process_lines.append(f"- **Type:** {step.get('agent_type', 'unknown')}")
                if step.get("instruction"):
                    process_lines.append(f"- **Instruction:** {step['instruction']}")
                process_lines.append("")

            if "## Process" in task_md:
                task_md += "\n".join(process_lines) + after_process
            else:
                task_md += "\n".join(process_lines)

            await tw.write("TASK.md", task_md, summary=f"Assigned type: {new_type_key} with {len(resolved_steps)} process steps")
            changes.append(f"type → {new_type_key} ({len(resolved_steps)} steps)")

        except Exception as e:
            logger.error(f"[MANAGE_TASK] type_key assignment failed: {e}", exc_info=True)
            return {"success": False, "error": "type_assignment_failed", "message": f"Failed to assign type: {str(e)}"}

    return {
        "success": True,
        "task_slug": task_slug,
        "changes": changes,
        "message": f"Updated task '{task_slug}': {', '.join(changes)}.",
    }


async def _handle_pause(auth: Any, task_slug: str) -> dict:
    """Pause task. Was: handle_pause_task."""
    now = datetime.now(timezone.utc)

    task = await _find_task(auth, task_slug, select="id, slug, status")
    if task.get("error"):
        return task

    if task["status"] == "paused":
        return {"success": True, "task_slug": task_slug, "message": f"Task '{task_slug}' is already paused."}

    try:
        auth.client.table("tasks").update({
            "status": "paused",
            "updated_at": now.isoformat(),
        }).eq("id", task["id"]).execute()
    except Exception as e:
        return {"success": False, "error": "update_failed", "message": str(e)}

    # ADR-164: task_paused activity_log write removed. Task state is in the
    # tasks table — the current status is authoritative, no event needed.

    return {
        "success": True,
        "task_slug": task_slug,
        "message": f"Task '{task_slug}' paused. No future runs until resumed.",
    }


async def _handle_resume(auth: Any, task_slug: str) -> dict:
    """Resume paused task. Was: handle_resume_task."""
    now = datetime.now(timezone.utc)

    task = await _find_task(auth, task_slug, select="id, slug, status, schedule")
    if task.get("error"):
        return task

    if task["status"] == "active":
        return {"success": True, "task_slug": task_slug, "message": f"Task '{task_slug}' is already active."}

    schedule = task.get("schedule", "weekly")
    user_timezone = get_user_timezone(auth.client, auth.user_id)
    next_run = _compute_next_run(schedule, user_timezone=user_timezone) if schedule else None

    try:
        auth.client.table("tasks").update({
            "status": "active",
            "next_run_at": next_run,
            "updated_at": now.isoformat(),
        }).eq("id", task["id"]).execute()
    except Exception as e:
        return {"success": False, "error": "update_failed", "message": str(e)}

    # ADR-164: task_resumed activity_log write removed. Task state is in the
    # tasks table — authoritative, no event needed.

    return {
        "success": True,
        "task_slug": task_slug,
        "next_run_at": next_run,
        "message": f"Task '{task_slug}' resumed. Next run: {next_run or 'to be scheduled'}.",
    }


# ---------------------------------------------------------------------------
# ADR-149: Evaluation, Steering, Completion
# ---------------------------------------------------------------------------

EVALUATE_MODEL = "claude-haiku-4-5-20251001"  # Cost-conscious evaluation


async def _handle_evaluate(auth: Any, task_slug: str) -> dict:
    """Evaluate latest task output against DELIVERABLE.md quality spec.

    ADR-149: TP reads output + DELIVERABLE.md → produces structured quality
    assessment → writes to memory/feedback.md (source: evaluation).

    Returns assessment dict for TP to act on (steer, complete, or no action).
    """
    from services.task_workspace import TaskWorkspace
    from services.anthropic import get_anthropic_client

    task = await _find_task(auth, task_slug)
    if task.get("error"):
        return task

    tw = TaskWorkspace(auth.client, auth.user_id, task_slug)

    # Read latest output
    latest_output = await tw.read("outputs/latest/output.md")
    if not latest_output:
        return {"success": False, "error": "no_output", "message": f"No output found for task '{task_slug}'. Run the task first."}

    # Read DELIVERABLE.md
    deliverable_spec = await tw.read("DELIVERABLE.md")
    if not deliverable_spec:
        return {"success": False, "error": "no_deliverable", "message": f"No DELIVERABLE.md found for task '{task_slug}'."}

    # Read task mode
    mode = task.get("mode", "recurring")

    # Read context domain health (ADR-151/152: from TASK.md, not registry)
    context_health = ""
    try:
        from services.task_pipeline import parse_task_md
        task_md = await tw.read_task()
        if task_md:
            task_info = parse_task_md(task_md)
            context_reads = task_info.get("context_reads", [])
            if context_reads:
                    from services.directory_registry import get_domain_folder
                    for domain_key in context_reads:
                        folder = get_domain_folder(domain_key)
                        if folder:
                            prefix = f"/workspace/{folder}"
                            result = (
                                auth.client.table("workspace_files")
                                .select("path, updated_at")
                                .eq("user_id", auth.user_id)
                                .like("path", f"{prefix}/%")
                                .order("updated_at", desc=True)
                                .limit(5)
                                .execute()
                            )
                            files = result.data or []
                            if files:
                                latest_update = files[0].get("updated_at", "")[:10]
                                context_health += f"- {domain_key}: {len(files)} files, latest update {latest_update}\n"
                            else:
                                context_health += f"- {domain_key}: empty (no accumulated context yet)\n"
    except Exception as e:
        logger.warning(f"[MANAGE_TASK] Context health check failed: {e}")

    # LLM evaluation (Haiku for cost)
    eval_prompt = f"""You are evaluating a task output against its quality specification.

DELIVERABLE SPECIFICATION:
{deliverable_spec[:3000]}

LATEST OUTPUT (truncated):
{latest_output[:4000]}

TASK MODE: {mode}
{"CONTEXT DOMAIN HEALTH:" + chr(10) + context_health if context_health else ""}

Evaluate this output. Return a JSON object with:
- "criteria_met": "X/Y" (how many quality criteria are satisfied)
- "gaps": ["list of specific gaps or missing elements"]
- "context_health": "healthy|thin|empty" (based on domain health above)
- "quality_assessment": one sentence summary
- "recommendation": "deliver" | "steer" | "escalate" (what TP should do next)

For goal mode: recommend "deliver" only when ALL criteria are met.
For recurring mode: recommend "deliver" (always auto-delivers), but note quality trajectory.

Return ONLY the JSON object, no other text."""

    try:
        anthropic = get_anthropic_client()
        response = anthropic.messages.create(
            model=EVALUATE_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": eval_prompt}],
        )
        eval_text = response.content[0].text.strip()

        # ADR-171: Record token spend for this evaluation
        try:
            from services.platform_limits import record_token_usage
            from services.supabase import get_service_client
            record_token_usage(
                get_service_client(),
                user_id=auth.user_id,
                caller="evaluation",
                model=EVALUATE_MODEL,
                input_tokens=getattr(response.usage, "input_tokens", 0),
                output_tokens=getattr(response.usage, "output_tokens", 0),
                metadata={"task_slug": task_slug},
            )
        except Exception as _e:
            logger.warning(f"[TOKEN_USAGE] evaluation record failed: {_e}")

        # Parse JSON response
        try:
            # Handle markdown code blocks
            if eval_text.startswith("```"):
                eval_text = eval_text.split("```")[1]
                if eval_text.startswith("json"):
                    eval_text = eval_text[4:]
                eval_text = eval_text.strip()
            assessment = json.loads(eval_text)
        except (json.JSONDecodeError, IndexError):
            assessment = {
                "criteria_met": "unknown",
                "gaps": [],
                "context_health": "unknown",
                "quality_assessment": eval_text[:200],
                "recommendation": "escalate",
            }

    except Exception as e:
        logger.error(f"[MANAGE_TASK] Evaluation LLM call failed: {e}")
        return {"success": False, "error": "evaluation_failed", "message": str(e)}

    # Write evaluation to memory/feedback.md (source: evaluation)
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d %H:%M")
    eval_entry = (
        f"## Evaluation ({date_str}, source: evaluation)\n"
        f"- Criteria: {assessment.get('criteria_met', 'unknown')}\n"
        f"- Gaps: {', '.join(assessment.get('gaps', [])) or 'none identified'}\n"
        f"- Context health: {assessment.get('context_health', 'unknown')}\n"
        f"- Quality: {assessment.get('quality_assessment', 'no assessment')}\n"
        f"- Recommendation: {assessment.get('recommendation', 'unknown')}\n"
    )

    try:
        existing_feedback = await tw.read("memory/feedback.md") or ""
        # Prepend (newest first)
        if existing_feedback.startswith("# Task Feedback"):
            header = existing_feedback.split("\n", 2)
            rest = header[2] if len(header) > 2 else ""
            updated = f"{header[0]}\n{header[1] if len(header) > 1 else ''}\n\n{eval_entry}\n{rest}"
        else:
            updated = f"# Task Feedback\n\n{eval_entry}\n{existing_feedback}"
        await tw.write("memory/feedback.md", updated,
                      summary=f"Evaluation: {assessment.get('criteria_met', '?')} criteria met")
    except Exception as e:
        logger.warning(f"[MANAGE_TASK] Evaluation write to feedback.md failed: {e}")

    # ADR-164: task_evaluated activity_log write removed. Evaluation is
    # written to /tasks/{slug}/memory/feedback.md (ADR-149) — that file is
    # the authoritative record. No denormalization.

    # ADR-178: TP-initiated inference trigger. If feedback.md has ≥2 entries
    # since the last inference run, call infer_task_deliverable_preferences()
    # in the same evaluate turn (preserves ADR-156 single intelligence layer).
    inference_triggered = False
    try:
        feedback_content = await tw.read("memory/feedback.md") or ""
        entry_count = len(re.findall(r"^## ", feedback_content, re.MULTILINE))
        deliverable_content = await tw.read("DELIVERABLE.md") or ""
        # Check last inference timestamp from DELIVERABLE.md metadata comment
        last_inference_match = re.search(r"<!-- last_inference: ([\d\-T:Z]+) -->", deliverable_content)
        if last_inference_match:
            last_inference_str = last_inference_match.group(1)
            try:
                last_inference_dt = datetime.fromisoformat(last_inference_str.rstrip("Z")).replace(tzinfo=timezone.utc)
                entries_since = len(re.findall(
                    rf"^## .+\(({re.escape(last_inference_str[:7])}.+?)\)",
                    feedback_content,
                    re.MULTILINE,
                ))
                # Recount entries added after last inference using date comparison
                new_entries = 0
                for match in re.finditer(r"^## .+?\((\d{4}-\d{2}-\d{2} \d{2}:\d{2})", feedback_content, re.MULTILINE):
                    try:
                        entry_dt = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                        if entry_dt > last_inference_dt:
                            new_entries += 1
                    except ValueError:
                        pass
                entries_since = new_entries
            except (ValueError, AttributeError):
                entries_since = entry_count  # assume all are new if timestamp unparseable
        else:
            entries_since = entry_count  # no prior inference — all entries are new

        if entries_since >= 2:
            from services.task_deliverable_inference import infer_task_deliverable_preferences
            # Returns updated DELIVERABLE.md content (str) or None if skipped/failed
            updated_deliverable = await infer_task_deliverable_preferences(
                client=auth.client,
                user_id=auth.user_id,
                task_slug=task_slug,
            )
            inference_triggered = updated_deliverable is not None
            if inference_triggered:
                # Stamp last_inference timestamp into DELIVERABLE.md metadata comment
                # so future calls can count entries since last inference
                now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                stamped = re.sub(
                    r"<!-- last_inference: [\d\-T:Z]+ -->",
                    f"<!-- last_inference: {now_iso} -->",
                    updated_deliverable,
                )
                if "<!-- last_inference:" not in stamped:
                    stamped = stamped + f"\n<!-- last_inference: {now_iso} -->"
                await tw.write("DELIVERABLE.md", stamped, summary=f"Inference timestamp stamped ({now_iso[:10]})")
                logger.info(f"[MANAGE_TASK] Inference triggered post-evaluate for '{task_slug}': {entries_since} feedback entries since last inference")
    except Exception as e:
        logger.warning(f"[MANAGE_TASK] Post-evaluate inference check failed (non-fatal): {e}")

    return {
        "success": True,
        "task_slug": task_slug,
        "assessment": assessment,
        "inference_triggered": inference_triggered,
        "message": f"Evaluated '{task_slug}': {assessment.get('quality_assessment', 'assessment complete')}",
    }


async def _handle_steer(auth: Any, task_slug: str, input: dict) -> dict:
    """Write cycle-specific guidance to memory/steering.md.

    ADR-149: TP writes management notes that the pipeline reads on next execution.
    Steering is overwritten each time (latest guidance only, not accumulated).

    ADR-170: Optional target_section forces a specific page_structure section to
    regenerate on next run, bypassing the manifest staleness check. Written as a
    metadata directive at the top of steering.md — read by revision.py.
    """
    steering_text = input.get("steering", "").strip()
    target_section = input.get("target_section", "").strip()

    if not steering_text:
        return {"success": False, "error": "missing_steering", "message": "steering text is required for action='steer'"}

    task = await _find_task(auth, task_slug)
    if task.get("error"):
        return task

    from services.task_workspace import TaskWorkspace
    tw = TaskWorkspace(auth.client, auth.user_id, task_slug)

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d %H:%M")

    target_line = f"target_section: {target_section}\n" if target_section else ""
    steering_content = (
        f"# Steering Notes\n"
        f"<!-- Written by TP. Read by pipeline on next execution. Overwritten per evaluation. -->\n"
        f"<!-- {target_line}-->\n\n"
        f"## Guidance ({date_str})\n"
        f"{steering_text}\n"
    )

    try:
        await tw.write("memory/steering.md", steering_content,
                      summary=f"Steering: {steering_text[:50]}")
    except Exception as e:
        return {"success": False, "error": "write_failed", "message": str(e)}

    # ADR-164: task_steered activity_log write removed. Steering lives in
    # /tasks/{slug}/memory/steering.md — the file is the record.

    msg = f"Steering notes written for '{task_slug}'. Next run will incorporate this guidance."
    if target_section:
        msg += f" Section '{target_section}' will be force-regenerated."

    return {
        "success": True,
        "task_slug": task_slug,
        "target_section": target_section or None,
        "message": msg,
    }


async def _handle_complete(auth: Any, task_slug: str) -> dict:
    """Mark task as completed. Clear scheduling.

    ADR-149: Used when goal task criteria are met, or manual completion.
    Sets status=completed, clears next_run_at. Irreversible without manual DB update.
    """
    now = datetime.now(timezone.utc)

    task = await _find_task(auth, task_slug)
    if task.get("error"):
        return task

    if task["status"] == "completed":
        return {"success": True, "task_slug": task_slug, "message": f"Task '{task_slug}' is already completed."}

    try:
        auth.client.table("tasks").update({
            "status": "completed",
            "next_run_at": None,
            "updated_at": now.isoformat(),
        }).eq("id", task["id"]).execute()
    except Exception as e:
        return {"success": False, "error": "update_failed", "message": str(e)}

    # ADR-164: task_completed activity_log write removed. Task state is in
    # the tasks table — `status='completed'` is the record.

    return {
        "success": True,
        "task_slug": task_slug,
        "message": f"Task '{task_slug}' marked as completed. No further runs will be scheduled.",
    }


async def _handle_archive(auth: Any, task_slug: str) -> dict:
    """Soft-delete a task by setting status='archived'.

    ADR-161: Essential tasks (e.g., daily-update) cannot be archived.
    Use pause instead if the user wants to stop a required task.
    """
    now = datetime.now(timezone.utc)

    task = await _find_task(auth, task_slug, select="id, slug, status, essential")
    if task.get("error"):
        return task

    if task.get("essential"):
        return {
            "success": False,
            "error": "essential_task",
            "message": f"Task '{task_slug}' is essential to your workspace and cannot be archived. You can pause it instead.",
        }

    if task["status"] == "archived":
        return {"success": True, "task_slug": task_slug, "message": f"Task '{task_slug}' is already archived."}

    try:
        auth.client.table("tasks").update({
            "status": "archived",
            "next_run_at": None,
            "updated_at": now.isoformat(),
        }).eq("id", task["id"]).execute()
    except Exception as e:
        return {"success": False, "error": "update_failed", "message": str(e)}

    return {
        "success": True,
        "task_slug": task_slug,
        "message": f"Task '{task_slug}' archived successfully.",
    }


# ---------------------------------------------------------------------------
# Create helpers (ADR-168 Commit 3: absorbed from the former task.py primitive)
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    """Generate a filesystem-safe slug from text."""
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9-]", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:50] or "task"


def _build_custom_task_md(
    title: str,
    slug: str,
    agent_slug: str,
    mode: str = "recurring",
    objective: Optional[dict] = None,
    schedule: Optional[str] = None,
    delivery: Optional[str] = None,
    success_criteria: Optional[list] = None,
    output_spec: Optional[list] = None,
    page_structure: Optional[list] = None,
    team: Optional[list] = None,
) -> str:
    """Build TASK.md content for a custom task (no type_key).

    Type-key tasks use `build_task_md_from_type()` from task_types registry.

    ADR-174 Phase 3: page_structure (list of section dicts) is serialized as a
    YAML block under ## Page Structure. The compose pipeline reads it at execution
    time, taking precedence over any registry definition.
    """
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

    # ADR-176 Phase 2: team composition for custom tasks
    if team and isinstance(team, list):
        lines.append("")
        lines.append("## Team")
        for role in team:
            lines.append(f"- {role}")

    # ADR-174 Phase 3: bespoke compose layout — YAML block readable by parse_task_md()
    if page_structure and isinstance(page_structure, list):
        import yaml as _yaml
        lines.append("")
        lines.append("## Page Structure")
        try:
            yaml_block = _yaml.dump(page_structure, default_flow_style=False, allow_unicode=True).rstrip()
            lines.append(yaml_block)
        except Exception:
            pass  # Malformed structure — silently skip; compose falls back to raw output

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# _handle_create — absorbed from the former CreateTask primitive (task.py, deleted)
# ADR-168 Commit 3: CreateTask folded into ManageTask(action="create") for symmetry
# with ManageAgent, which already covered agent creation in a single primitive.
# ---------------------------------------------------------------------------

async def _handle_create(auth: Any, input: dict) -> dict:
    """
    Create a new task and assign it to an agent.

    Two paths:
    A. type_key provided → resolve from registry, auto-populate pipeline + objective
    B. agent_slug provided → custom task

    Steps:
    1. Validate title + (type_key OR agent_slug)
    2. Generate slug from title
    3. Resolve agent(s) — from pipeline or explicit agent_slug
    4. Create DB row in tasks table (with auto-suffix on slug collision)
    5. Write TASK.md via TaskWorkspace
    6. Scaffold DELIVERABLE.md (ADR-149) + memory/feedback.md + memory/steering.md + awareness.md
    7. Scaffold context domains for task's context_writes (ADR-151)
    8. Update WORKSPACE.md manifest
    9. Trigger immediate first run if warranted (bootstrap tasks or goal mode)
    10. Return success with task slug + process narration

    Run-on-creation logic (step 9):
    - Bootstrap tasks (accumulates_context with context domains to seed) run immediately
      so the domain is populated before the first scheduled cycle. next_run_at is already
      set to NOW for these — we execute inline to close the 5-minute scheduler gap.
    - goal mode tasks represent a specific deliverable the user wants now. Running on
      creation gives the user output without a manual trigger.
    - recurring tasks without bootstrap criteria run on their natural cadence (no change).
    - reactive tasks are explicitly dispatch-and-done; caller triggers when ready.
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
    # ADR-174 Phase 3: bespoke page_structure for TP-authored custom tasks
    page_structure = input.get("page_structure")  # list[dict] | None
    # ADR-176 Phase 2: team composition override (list of role strings)
    team_override = input.get("team")  # list[str] | None

    if mode not in ("recurring", "goal", "reactive"):
        mode = "recurring"

    # Fall back to type registry default_title if caller omitted a title
    if not title and type_key:
        from services.task_types import get_task_type as _get_type_for_title
        _type_def = _get_type_for_title(type_key)
        if _type_def and _type_def.get("default_title"):
            title = _type_def["default_title"]

    if not title:
        return {"success": False, "error": "missing_title", "message": "title is required for action='create'"}
    if not type_key and not agent_slug:
        return {"success": False, "error": "missing_type_or_agent", "message": "Either type_key or agent_slug is required for action='create'"}

    user_id = auth.user_id
    slug = _slugify(title)

    # --- Path A: Type-key based creation (ADR-145) ---
    resolved_agent_slugs: list[str] = []
    resolved_steps: list = []
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
                    .eq("platform", platform)
                    .eq("status", "active")
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
                            logger.info(f"[MANAGE_TASK] Auto-populated {len(source_ids)} {platform} sources from platform_connections")
            except Exception as e:
                logger.warning(f"[MANAGE_TASK] Failed to read platform sources: {e}")

        # Build TASK.md from type template.
        # ADR-176 Decision 2: pass team_override so TP's composition judgment
        # is reflected in both ## Process agent labels and ## Team section.
        task_md_content = build_task_md_from_type(
            type_key=type_key,
            title=title,
            slug=slug,
            focus=focus,
            schedule=schedule,
            delivery=delivery,
            agent_slugs=resolved_agent_slugs or None,
            sources=task_sources,
            team_override=team_override or None,
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
        logger.error(f"[MANAGE_TASK] Agent lookup failed: {e}")
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
        user_timezone = get_user_timezone(auth.client, auth.user_id)
        next_run_at = _compute_next_run(schedule, user_timezone=user_timezone) if schedule else None

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
            logger.error(f"[MANAGE_TASK] DB insert failed: {e}")
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
            task_md = _build_custom_task_md(
                title=title,
                slug=slug,
                agent_slug=agent_slug,
                mode=mode,
                objective=objective,
                schedule=schedule,
                delivery=delivery,
                success_criteria=success_criteria,
                output_spec=output_spec,
                page_structure=page_structure,
                team=team_override,
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
                                    metadata={"domain": domain_key, "type": "synthesis"},
                                )
                                logger.info(f"[MANAGE_TASK] Scaffolded context domain: {domain_key}")

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
                                    )
            except Exception as e:
                logger.warning(f"[MANAGE_TASK] Context domain scaffold failed (non-fatal): {e}")

    except Exception as e:
        logger.warning(f"[MANAGE_TASK] TASK.md write failed (non-fatal): {e}")

    # ADR-154: memory/tasks.json dissolved — task assignments tracked via TASK.md, not agent memory
    # ADR-164: task_created activity_log write removed. tasks table + TASK.md ARE the record.

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

    # Run on creation: bootstrap tasks and goal mode tasks execute immediately.
    # Bootstrap: next_run_at is already NOW — we fire inline to close the
    #   5-minute scheduler gap so the context domain is seeded right away.
    # Goal: user wants a specific deliverable now, not at the next cadence tick.
    # Recurring without bootstrap: runs on its natural schedule (no change).
    # Reactive: explicitly caller-triggered; skip.
    first_run_result = None
    should_run_now = has_bootstrap or mode == "goal"
    if should_run_now:
        try:
            first_run_result = await _handle_trigger(auth, slug, {})
            if first_run_result.get("success"):
                logger.info(f"[MANAGE_TASK] First run completed inline for '{slug}'")
            else:
                logger.warning(f"[MANAGE_TASK] First run failed for '{slug}': {first_run_result.get('message')}")
        except Exception as e:
            logger.warning(f"[MANAGE_TASK] First run exception for '{slug}' (non-fatal): {e}")
            first_run_result = None

    return {
        "success": True,
        "action": "create",
        "task_id": task_id,
        "task_slug": slug,
        "type_key": type_key,
        "agent_slug": agent_slug,
        "process_agents": resolved_agent_slugs or [agent_slug],
        "process_narration": process_narration,
        "mode": mode,
        "schedule": schedule,
        "next_run_at": next_run_at,
        "first_run": "completed" if first_run_result and first_run_result.get("success") else ("failed" if first_run_result else "scheduled"),
        "message": f"Created task '{title}'" + (f" ({type_key})" if type_key else "") + f" — {schedule or 'on-demand'}."
                   + (f" Process: {process_narration}." if process_narration else "")
                   + (" First run completed." if first_run_result and first_run_result.get("success") else ""),
        "ui_action": {
            "type": "NAVIGATE",
            "data": {"url": f"/work", "label": title},
        },
    }
