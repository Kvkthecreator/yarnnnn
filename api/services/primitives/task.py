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
    "description": """Create a new task — a defined unit of work with objective, cadence, and delivery target. Assign an agent to execute it.

Required: title, agent_slug
Optional: mode, objective, schedule, delivery, success_criteria, output_spec

mode: 'recurring' (default), 'goal' (bounded, completes when done), 'reactive' (on-demand/event-triggered)
schedule: 'daily', 'weekly', 'monthly', or a cron expression (default: 'weekly')

Examples:
- CreateTask(title="Weekly Competitive Briefing", agent_slug="competitive-intel", schedule="weekly")
- CreateTask(title="Daily Slack Recap", agent_slug="slack-digest", schedule="daily", delivery="user@example.com")
- CreateTask(title="Acquisition Due Diligence", agent_slug="research-agent", mode="goal", schedule="daily")""",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Task name, e.g. 'Weekly Competitive Briefing'"
            },
            "agent_slug": {
                "type": "string",
                "description": "Slug of the agent to assign. Must exist."
            },
            "mode": {
                "type": "string",
                "enum": ["recurring", "goal", "reactive"],
                "description": "Temporal behavior: 'recurring' (indefinite cadence), 'goal' (bounded, completes when criteria met), 'reactive' (on-demand)"
            },
            "objective": {
                "type": "object",
                "properties": {
                    "deliverable": {"type": "string"},
                    "audience": {"type": "string"},
                    "purpose": {"type": "string"},
                    "format": {"type": "string"}
                },
                "description": "Task objective: what to deliver, for whom, why, in what format"
            },
            "schedule": {
                "type": "string",
                "description": "Cadence: 'daily', 'weekly', 'monthly', or cron expression"
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
        "required": ["title", "agent_slug"]
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

    1. Extract fields
    2. Generate slug from title
    3. Verify agent_slug exists
    4. Create DB row in tasks table
    5. Write TASK.md via TaskWorkspace
    6. Update agent's memory/tasks.json
    7. Calculate next_run_at from schedule
    8. Return success with task slug
    """
    title = input.get("title", "").strip()
    agent_slug = input.get("agent_slug", "").strip()
    mode = input.get("mode", "recurring")
    objective = input.get("objective")
    schedule = input.get("schedule", "weekly")
    delivery = input.get("delivery")
    success_criteria = input.get("success_criteria")
    output_spec = input.get("output_spec")

    # Validate mode
    if mode not in ("recurring", "goal", "reactive"):
        mode = "recurring"

    if not title:
        return {"success": False, "error": "missing_title", "message": "title is required"}
    if not agent_slug:
        return {"success": False, "error": "missing_agent", "message": "agent_slug is required"}

    user_id = auth.user_id
    slug = _slugify(title)

    # Verify agent exists
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

    # Calculate next_run_at
    next_run_at = _compute_next_run(schedule) if schedule else None

    # Create tasks row
    now = datetime.now(timezone.utc)
    try:
        row = {
            "user_id": user_id,
            "slug": slug,
            "mode": mode,
            "status": "active",
            "schedule": schedule,
            "next_run_at": next_run_at,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        insert_result = auth.client.table("tasks").insert(row).execute()
        if not insert_result.data:
            return {"success": False, "error": "insert_failed", "message": "Failed to create task row"}
        task_id = insert_result.data[0]["id"]
    except Exception as e:
        error_str = str(e)
        if "tasks_user_slug_unique" in error_str:
            return {
                "success": False,
                "error": "duplicate_slug",
                "message": f"A task with slug '{slug}' already exists.",
            }
        logger.error(f"[CREATE_TASK] DB insert failed: {e}")
        return {"success": False, "error": "insert_failed", "message": error_str}

    # Write TASK.md via TaskWorkspace
    try:
        from services.task_workspace import TaskWorkspace
        tw = TaskWorkspace(auth.client, user_id, slug)
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
    except Exception as e:
        logger.warning(f"[CREATE_TASK] TASK.md write failed (non-fatal): {e}")

    # Update agent's memory/tasks.json
    try:
        from services.workspace import AgentWorkspace
        agent_data = agent_result.data
        aw = AgentWorkspace(auth.client, user_id, agent_slug)
        existing_raw = await aw.read("memory/tasks.json")
        if existing_raw:
            try:
                tasks_list = _json.loads(existing_raw)
            except (ValueError, TypeError):
                tasks_list = []
        else:
            tasks_list = []

        tasks_list.append({
            "task_slug": slug,
            "title": title,
            "schedule": schedule,
            "created_at": now.isoformat(),
        })
        await aw.write(
            "memory/tasks.json",
            _json.dumps(tasks_list, indent=2),
            summary=f"Task assignments for {agent_slug}",
            tags=["tasks", "memory"],
        )
    except Exception as e:
        logger.warning(f"[CREATE_TASK] Agent tasks.json update failed (non-fatal): {e}")

    # Activity log
    try:
        from services.activity_log import write_activity
        await write_activity(
            client=auth.client,
            user_id=user_id,
            event_type="task_created",
            summary=f"Created task: {title} (assigned to {agent_slug})",
            event_ref=task_id,
            metadata={
                "task_slug": slug,
                "agent_slug": agent_slug,
                "schedule": schedule,
            },
        )
    except Exception:
        pass

    return {
        "success": True,
        "task_id": task_id,
        "task_slug": slug,
        "agent_slug": agent_slug,
        "mode": mode,
        "schedule": schedule,
        "next_run_at": next_run_at,
        "message": f"Created task '{title}' (mode={mode}) assigned to agent '{agent_slug}'.",
        "ui_action": {
            "type": "NAVIGATE",
            "data": {"url": f"/tasks/{slug}", "label": title},
        },
    }


# =============================================================================
# TriggerTask
# =============================================================================

TRIGGER_TASK_TOOL = {
    "name": "TriggerTask",
    "description": """Run a task immediately, outside its normal cadence. Optionally inject context for this run.

Sets the task's next_run_at to now — the scheduler will pick it up on the next tick.

Examples:
- TriggerTask(task_slug="weekly-competitive-briefing")
- TriggerTask(task_slug="daily-slack-recap", context="Focus on the product launch discussion from today")""",
    "input_schema": {
        "type": "object",
        "properties": {
            "task_slug": {
                "type": "string",
                "description": "The task to trigger"
            },
            "context": {
                "type": "string",
                "description": "Optional context to inject for this run"
            }
        },
        "required": ["task_slug"]
    }
}


async def handle_trigger_task(auth: Any, input: dict) -> dict:
    """
    Handle TriggerTask primitive — run a task immediately.

    1. Find task by slug
    2. Verify task is active
    3. Update task's next_run_at to now
    4. Optionally write context to task workspace /working/trigger_context.md
    5. Return success
    """
    task_slug = input.get("task_slug", "").strip()
    context = input.get("context")

    if not task_slug:
        return {"success": False, "error": "missing_slug", "message": "task_slug is required"}

    user_id = auth.user_id
    now = datetime.now(timezone.utc)

    # Find task
    try:
        task_result = (
            auth.client.table("tasks")
            .select("id, slug, status, schedule")
            .eq("user_id", user_id)
            .eq("slug", task_slug)
            .maybe_single()
            .execute()
        )
        if not task_result or not task_result.data:
            return {
                "success": False,
                "error": "not_found",
                "message": f"Task '{task_slug}' not found.",
            }

        task = task_result.data
        if task["status"] != "active":
            return {
                "success": False,
                "error": "not_active",
                "message": f"Task '{task_slug}' is {task['status']} — cannot trigger.",
            }
    except Exception as e:
        logger.error(f"[TRIGGER_TASK] Lookup failed: {e}")
        return {"success": False, "error": "lookup_failed", "message": str(e)}

    # Set next_run_at to now
    try:
        auth.client.table("tasks").update({
            "next_run_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }).eq("id", task["id"]).execute()
    except Exception as e:
        logger.error(f"[TRIGGER_TASK] Update failed: {e}")
        return {"success": False, "error": "update_failed", "message": str(e)}

    # Optionally write trigger context
    if context:
        try:
            from services.task_workspace import TaskWorkspace
            tw = TaskWorkspace(auth.client, user_id, task_slug)
            await tw.write(
                "working/trigger_context.md",
                f"# Trigger Context\n\n{context}\n\n_Triggered at {now.strftime('%Y-%m-%d %H:%M UTC')}_\n",
                summary="Ad-hoc trigger context",
                tags=["trigger", "ephemeral"],
                lifecycle="ephemeral",
            )
        except Exception as e:
            logger.warning(f"[TRIGGER_TASK] Context write failed (non-fatal): {e}")

    # Activity log
    try:
        from services.activity_log import write_activity
        await write_activity(
            client=auth.client,
            user_id=user_id,
            event_type="task_triggered",
            summary=f"Triggered task: {task_slug}",
            event_ref=task["id"],
            metadata={
                "task_slug": task_slug,
                "has_context": bool(context),
            },
        )
    except Exception:
        pass

    return {
        "success": True,
        "task_id": task["id"],
        "task_slug": task_slug,
        "message": f"Task '{task_slug}' triggered — will run on next scheduler tick.",
        "ui_action": {
            "type": "NAVIGATE",
            "data": {"url": f"/tasks/{task_slug}", "label": f"View {task_slug}"},
        },
    }


# =============================================================================
# UpdateTask
# =============================================================================

UPDATE_TASK_TOOL = {
    "name": "UpdateTask",
    "description": """Update a task's schedule, delivery, or status.

Examples:
- UpdateTask(task_slug="weekly-briefing", schedule="daily")
- UpdateTask(task_slug="weekly-briefing", delivery="user@example.com")
- UpdateTask(task_slug="weekly-briefing", mode="goal")""",
    "input_schema": {
        "type": "object",
        "properties": {
            "task_slug": {
                "type": "string",
                "description": "The task to update"
            },
            "schedule": {
                "type": "string",
                "description": "New cadence: 'daily', 'weekly', 'monthly', or cron expression"
            },
            "delivery": {
                "type": "string",
                "description": "New delivery target: email address or 'none'"
            },
            "mode": {
                "type": "string",
                "enum": ["recurring", "goal", "reactive"],
                "description": "New temporal behavior"
            },
        },
        "required": ["task_slug"]
    }
}


async def handle_update_task(auth: Any, input: dict) -> dict:
    """Handle UpdateTask primitive — update task schedule, delivery, or mode."""
    task_slug = input.get("task_slug", "").strip()
    if not task_slug:
        return {"success": False, "error": "missing_slug", "message": "task_slug is required"}

    user_id = auth.user_id

    # Find task
    try:
        task_result = (
            auth.client.table("tasks")
            .select("id, slug, status, schedule, mode")
            .eq("user_id", user_id)
            .eq("slug", task_slug)
            .maybe_single()
            .execute()
        )
        if not task_result or not task_result.data:
            return {"success": False, "error": "not_found", "message": f"Task '{task_slug}' not found."}
    except Exception as e:
        return {"success": False, "error": "lookup_failed", "message": str(e)}

    # Build update
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

    if not changes:
        return {"success": False, "error": "no_changes", "message": "No changes specified."}

    # Apply DB update
    try:
        auth.client.table("tasks").update(update_data).eq("id", task_result.data["id"]).execute()
    except Exception as e:
        return {"success": False, "error": "update_failed", "message": str(e)}

    # Update TASK.md delivery field if changed
    if new_delivery is not None:
        try:
            from services.task_workspace import TaskWorkspace
            tw = TaskWorkspace(auth.client, user_id, task_slug)
            task_md = await tw.read_task()
            if task_md:
                # Simple replace of delivery line
                import re
                if "**Delivery:**" in task_md:
                    task_md = re.sub(r"\*\*Delivery:\*\*.*", f"**Delivery:** {new_delivery}", task_md)
                else:
                    task_md += f"\n**Delivery:** {new_delivery}"
                await tw.write("TASK.md", task_md, summary=f"Updated delivery: {new_delivery}")
        except Exception as e:
            logger.warning(f"[UPDATE_TASK] TASK.md update failed (non-fatal): {e}")

    return {
        "success": True,
        "task_slug": task_slug,
        "changes": changes,
        "message": f"Updated task '{task_slug}': {', '.join(changes)}.",
    }


# =============================================================================
# PauseTask
# =============================================================================

PAUSE_TASK_TOOL = {
    "name": "PauseTask",
    "description": """Pause a task — stops future scheduled runs. The task can be resumed later.

Example: PauseTask(task_slug="weekly-briefing")""",
    "input_schema": {
        "type": "object",
        "properties": {
            "task_slug": {
                "type": "string",
                "description": "The task to pause"
            },
        },
        "required": ["task_slug"]
    }
}


async def handle_pause_task(auth: Any, input: dict) -> dict:
    """Handle PauseTask — set task status to 'paused'."""
    task_slug = input.get("task_slug", "").strip()
    if not task_slug:
        return {"success": False, "error": "missing_slug", "message": "task_slug is required"}

    user_id = auth.user_id
    now = datetime.now(timezone.utc)

    try:
        task_result = (
            auth.client.table("tasks")
            .select("id, slug, status")
            .eq("user_id", user_id)
            .eq("slug", task_slug)
            .maybe_single()
            .execute()
        )
        if not task_result or not task_result.data:
            return {"success": False, "error": "not_found", "message": f"Task '{task_slug}' not found."}

        if task_result.data["status"] == "paused":
            return {"success": True, "task_slug": task_slug, "message": f"Task '{task_slug}' is already paused."}

        auth.client.table("tasks").update({
            "status": "paused",
            "updated_at": now.isoformat(),
        }).eq("id", task_result.data["id"]).execute()

    except Exception as e:
        return {"success": False, "error": "update_failed", "message": str(e)}

    # Activity log
    try:
        from services.activity_log import write_activity
        await write_activity(
            client=auth.client, user_id=user_id,
            event_type="task_paused", summary=f"Paused task: {task_slug}",
            event_ref=task_result.data["id"],
            metadata={"task_slug": task_slug},
        )
    except Exception:
        pass

    return {
        "success": True,
        "task_slug": task_slug,
        "message": f"Task '{task_slug}' paused. No future runs will be scheduled until resumed.",
    }


# =============================================================================
# ResumeTask
# =============================================================================

RESUME_TASK_TOOL = {
    "name": "ResumeTask",
    "description": """Resume a paused task — restores scheduled runs.

Example: ResumeTask(task_slug="weekly-briefing")""",
    "input_schema": {
        "type": "object",
        "properties": {
            "task_slug": {
                "type": "string",
                "description": "The task to resume"
            },
        },
        "required": ["task_slug"]
    }
}


async def handle_resume_task(auth: Any, input: dict) -> dict:
    """Handle ResumeTask — set task status back to 'active' and schedule next run."""
    task_slug = input.get("task_slug", "").strip()
    if not task_slug:
        return {"success": False, "error": "missing_slug", "message": "task_slug is required"}

    user_id = auth.user_id
    now = datetime.now(timezone.utc)

    try:
        task_result = (
            auth.client.table("tasks")
            .select("id, slug, status, schedule")
            .eq("user_id", user_id)
            .eq("slug", task_slug)
            .maybe_single()
            .execute()
        )
        if not task_result or not task_result.data:
            return {"success": False, "error": "not_found", "message": f"Task '{task_slug}' not found."}

        if task_result.data["status"] == "active":
            return {"success": True, "task_slug": task_slug, "message": f"Task '{task_slug}' is already active."}

        # Calculate next run from schedule
        schedule = task_result.data.get("schedule", "weekly")
        next_run = _compute_next_run(schedule) if schedule else None

        auth.client.table("tasks").update({
            "status": "active",
            "next_run_at": next_run,
            "updated_at": now.isoformat(),
        }).eq("id", task_result.data["id"]).execute()

    except Exception as e:
        return {"success": False, "error": "update_failed", "message": str(e)}

    # Activity log
    try:
        from services.activity_log import write_activity
        await write_activity(
            client=auth.client, user_id=user_id,
            event_type="task_resumed", summary=f"Resumed task: {task_slug}",
            event_ref=task_result.data["id"],
            metadata={"task_slug": task_slug, "next_run_at": next_run},
        )
    except Exception:
        pass

    return {
        "success": True,
        "task_slug": task_slug,
        "next_run_at": next_run,
        "message": f"Task '{task_slug}' resumed. Next run: {next_run or 'to be scheduled'}.",
    }
