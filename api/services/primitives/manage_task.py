"""
ManageTask Primitive — ADR-146: Primitive Hardening

Unified task lifecycle primitive. Replaces 4 separate primitives:
- TriggerTask → action="trigger"
- UpdateTask → action="update"
- PauseTask → action="pause"
- ResumeTask → action="resume"

Design principle P3 (One Tool Per Decision): TP decides "manage this task"
and picks the action. One tool, one decision.
"""

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

**action="update"** — Change schedule, delivery, or mode.
  ManageTask(task_slug="weekly-briefing", action="update", schedule="daily")
  ManageTask(task_slug="weekly-briefing", action="update", delivery="user@example.com")
  ManageTask(task_slug="weekly-briefing", action="update", mode="goal")

**action="pause"** — Stop future scheduled runs (can be resumed later).
  ManageTask(task_slug="weekly-briefing", action="pause")

**action="resume"** — Restore scheduled runs for a paused task.
  ManageTask(task_slug="weekly-briefing", action="resume")""",
    "input_schema": {
        "type": "object",
        "properties": {
            "task_slug": {
                "type": "string",
                "description": "The task to manage"
            },
            "action": {
                "type": "string",
                "enum": ["trigger", "update", "pause", "resume"],
                "description": "What to do with the task"
            },
            "context": {
                "type": "string",
                "description": "For action='trigger': optional context to inject for this run"
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

    if action not in ("trigger", "update", "pause", "resume"):
        return {"success": False, "error": "invalid_action", "message": "action must be one of: trigger, update, pause, resume"}

    if action == "trigger":
        return await _handle_trigger(auth, task_slug, input)
    elif action == "update":
        return await _handle_update(auth, task_slug, input)
    elif action == "pause":
        return await _handle_pause(auth, task_slug)
    elif action == "resume":
        return await _handle_resume(auth, task_slug)

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
    """Run task immediately. Was: handle_trigger_task."""
    context = input.get("context")
    now = datetime.now(timezone.utc)

    task = await _find_task(auth, task_slug, select="id, slug, status, schedule")
    if task.get("error"):
        return task

    if task["status"] != "active":
        return {"success": False, "error": "not_active", "message": f"Task '{task_slug}' is {task['status']} — cannot trigger."}

    # Set next_run_at to now
    try:
        auth.client.table("tasks").update({
            "next_run_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }).eq("id", task["id"]).execute()
    except Exception as e:
        return {"success": False, "error": "update_failed", "message": str(e)}

    # Optionally write trigger context
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

    # Activity log
    try:
        from services.activity_log import write_activity
        await write_activity(
            client=auth.client, user_id=auth.user_id,
            event_type="task_triggered", summary=f"Triggered task: {task_slug}",
            event_ref=task["id"],
            metadata={"task_slug": task_slug, "has_context": bool(context)},
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

    if not changes:
        return {"success": False, "error": "no_changes", "message": "No changes specified. Use schedule, delivery, or mode parameters."}

    # Apply DB update
    try:
        auth.client.table("tasks").update(update_data).eq("id", task["id"]).execute()
    except Exception as e:
        return {"success": False, "error": "update_failed", "message": str(e)}

    # Update TASK.md delivery field if changed
    if new_delivery is not None:
        try:
            from services.task_workspace import TaskWorkspace
            import re
            tw = TaskWorkspace(auth.client, auth.user_id, task_slug)
            task_md = await tw.read_task()
            if task_md:
                if "**Delivery:**" in task_md:
                    task_md = re.sub(r"\*\*Delivery:\*\*.*", f"**Delivery:** {new_delivery}", task_md)
                else:
                    task_md += f"\n**Delivery:** {new_delivery}"
                await tw.write("TASK.md", task_md, summary=f"Updated delivery: {new_delivery}")
        except Exception as e:
            logger.warning(f"[MANAGE_TASK] TASK.md update failed (non-fatal): {e}")

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

    try:
        from services.activity_log import write_activity
        await write_activity(
            client=auth.client, user_id=auth.user_id,
            event_type="task_paused", summary=f"Paused task: {task_slug}",
            event_ref=task["id"], metadata={"task_slug": task_slug},
        )
    except Exception:
        pass

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

    try:
        from services.activity_log import write_activity
        await write_activity(
            client=auth.client, user_id=auth.user_id,
            event_type="task_resumed", summary=f"Resumed task: {task_slug}",
            event_ref=task["id"], metadata={"task_slug": task_slug, "next_run_at": next_run},
        )
    except Exception:
        pass

    return {
        "success": True,
        "task_slug": task_slug,
        "next_run_at": next_run,
        "message": f"Task '{task_slug}' resumed. Next run: {next_run or 'to be scheduled'}.",
    }
