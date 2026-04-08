"""
ManageTask Primitive — ADR-146 + ADR-149: Primitive Hardening + Task Lifecycle

Unified task lifecycle primitive. 7 actions:
- trigger  — run task immediately
- update   — change schedule, delivery, mode, type, sources (ADR-158)
- pause    — stop scheduled runs
- resume   — restore scheduled runs
- evaluate — TP reads output + DELIVERABLE.md → quality judgment (ADR-149)
- steer    — TP writes cycle-specific guidance to steering.md (ADR-149)
- complete — mark task done, clear scheduling (ADR-149)

Design principle P3 (One Tool Per Decision): TP decides "manage this task"
and picks the action. One tool, one decision.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


MANAGE_TASK_TOOL = {
    "name": "ManageTask",
    "description": """Manage an existing task — trigger, update, pause, or resume.

**action="trigger"** — Run the task immediately, outside normal cadence.
  ManageTask(task_slug="weekly-briefing", action="trigger")
  ManageTask(task_slug="daily-recap", action="trigger", context="Focus on the product launch discussion")

**action="update"** — Change schedule, delivery, mode, type, or sources.
  ManageTask(task_slug="weekly-briefing", action="update", schedule="daily")
  ManageTask(task_slug="weekly-briefing", action="update", delivery="user@example.com")
  ManageTask(task_slug="weekly-briefing", action="update", mode="goal")
  ManageTask(task_slug="weekly-briefing", action="update", type_key="competitive-intel-brief")
  ManageTask(task_slug="slack-digest", action="update", sources={"slack": ["C123", "C456"]})

  type_key assigns a task type from the registry, which defines the execution process
  (multi-step pipeline, agent assignments). Use when a task was created generically
  and needs a proper process definition. Available type_keys: competitive-intel-brief,
  market-research-report, industry-signal-monitor, due-diligence-summary,
  meeting-prep-brief, stakeholder-update, relationship-health-digest,
  project-status-report, slack-recap, notion-sync-report, content-brief,
  launch-material, gtm-tracker

**action="pause"** — Stop future scheduled runs (can be resumed later).
  ManageTask(task_slug="weekly-briefing", action="pause")

**action="resume"** — Restore scheduled runs for a paused task.
  ManageTask(task_slug="weekly-briefing", action="resume")

**action="evaluate"** — Assess the latest output against DELIVERABLE.md quality spec (ADR-149).
  ManageTask(task_slug="weekly-briefing", action="evaluate")
  Returns: criteria_met, gaps, context_health, quality_assessment. Auto-writes evaluation to memory/feedback.md.
  Use after runs complete (mandatory for goal mode, periodic for recurring, skip for reactive).

**action="steer"** — Write cycle-specific guidance for the next run (ADR-149).
  ManageTask(task_slug="weekly-briefing", action="steer", steering="Focus on Acme Corp pricing changes next cycle")
  Writes to memory/steering.md — read by pipeline on next execution.

**action="complete"** — Mark task as completed, stop all future runs (ADR-149).
  ManageTask(task_slug="due-diligence-report", action="complete")
  Sets status=completed, clears next_run_at. Use when goal task criteria are met.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "task_slug": {
                "type": "string",
                "description": "The task to manage"
            },
            "action": {
                "type": "string",
                "enum": ["trigger", "update", "pause", "resume", "evaluate", "steer", "complete"],
                "description": "What to do with the task"
            },
            "context": {
                "type": "string",
                "description": "For action='trigger': optional context to inject for this run"
            },
            "steering": {
                "type": "string",
                "description": "For action='steer': guidance for the next execution cycle"
            },
            "schedule": {
                "type": "string",
                "description": "For action='update': new cadence (daily, weekly, monthly, or cron)"
            },
            "delivery": {
                "type": "string",
                "description": "For action='update': new delivery target (email or 'none')"
            },
            "mode": {
                "type": "string",
                "enum": ["recurring", "goal", "reactive"],
                "description": "For action='update': new temporal behavior"
            },
            "type_key": {
                "type": "string",
                "description": "For action='update': assign a task type from the registry (defines execution process + agent pipeline)"
            },
            "sources": {
                "type": "object",
                "description": "For action='update': per-task platform source selection. Map of platform → list of source IDs. E.g. {\"slack\": [\"C123\", \"C456\"]}"
            },
        },
        "required": ["task_slug", "action"]
    }
}


async def handle_manage_task(auth: Any, input: dict) -> dict:
    """
    Handle ManageTask — route to appropriate action handler.

    ADR-146: Single entry point for task lifecycle mutations.
    """
    task_slug = input.get("task_slug", "").strip()
    action = input.get("action", "")

    if not task_slug:
        return {"success": False, "error": "missing_slug", "message": "task_slug is required"}

    valid_actions = ("trigger", "update", "pause", "resume", "evaluate", "steer", "complete")
    if action not in valid_actions:
        return {"success": False, "error": "invalid_action", "message": f"action must be one of: {', '.join(valid_actions)}"}

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

    return {"success": False, "error": "unknown_action", "message": f"Unhandled action: {action}"}


# ---------------------------------------------------------------------------
# Internal handlers — absorbed from task.py
# ---------------------------------------------------------------------------

def _compute_next_run(schedule: str) -> Optional[str]:
    """Compute next_run_at from a human-readable schedule string."""
    now = datetime.now(timezone.utc)
    schedule_lower = schedule.lower().strip()

    if schedule_lower == "daily":
        next_run = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        return next_run.isoformat()
    elif schedule_lower == "weekly":
        days_ahead = 7 - now.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_run = (now + timedelta(days=days_ahead)).replace(hour=9, minute=0, second=0, microsecond=0)
        return next_run.isoformat()
    elif schedule_lower == "monthly":
        if now.month == 12:
            next_run = now.replace(year=now.year + 1, month=1, day=1, hour=9, minute=0, second=0, microsecond=0)
        else:
            next_run = now.replace(month=now.month + 1, day=1, hour=9, minute=0, second=0, microsecond=0)
        return next_run.isoformat()
    else:
        # Cron or unknown — let scheduler interpret
        return None


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

    new_schedule = input.get("schedule")
    if new_schedule:
        update_data["schedule"] = new_schedule
        next_run = _compute_next_run(new_schedule)
        if next_run:
            update_data["next_run_at"] = next_run
        changes.append(f"schedule → {new_schedule}")

    new_mode = input.get("mode")
    if new_mode and new_mode in ("recurring", "goal", "reactive"):
        update_data["mode"] = new_mode
        changes.append(f"mode → {new_mode}")

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
    next_run = _compute_next_run(schedule) if schedule else None

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

    return {
        "success": True,
        "task_slug": task_slug,
        "assessment": assessment,
        "message": f"Evaluated '{task_slug}': {assessment.get('quality_assessment', 'assessment complete')}",
    }


async def _handle_steer(auth: Any, task_slug: str, input: dict) -> dict:
    """Write cycle-specific guidance to memory/steering.md.

    ADR-149: TP writes management notes that the pipeline reads on next execution.
    Steering is overwritten each time (latest guidance only, not accumulated).
    """
    steering_text = input.get("steering", "").strip()

    if not steering_text:
        return {"success": False, "error": "missing_steering", "message": "steering text is required for action='steer'"}

    task = await _find_task(auth, task_slug)
    if task.get("error"):
        return task

    from services.task_workspace import TaskWorkspace
    tw = TaskWorkspace(auth.client, auth.user_id, task_slug)

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d %H:%M")

    steering_content = (
        f"# Steering Notes\n"
        f"<!-- Written by TP. Read by pipeline on next execution. Overwritten per evaluation. -->\n\n"
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

    return {
        "success": True,
        "task_slug": task_slug,
        "message": f"Steering notes written for '{task_slug}'. Next run will incorporate this guidance.",
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
