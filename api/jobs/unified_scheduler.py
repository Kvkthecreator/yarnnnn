"""
YARNNN v5 - Unified Scheduler (ADR-138 + ADR-141 + ADR-156 + ADR-164)

Three-layer execution: mechanical scheduling, LLM generation, TP intelligence.

Layer 1 (this file — pure dispatcher, zero LLM cost):
- Task scheduling: SQL query → execute_task() for each due task
- Atomic CAS claim to prevent duplicate execution
- Hourly scheduler_heartbeat activity_log write

ADR-164 update: lifecycle hygiene and ephemeral workspace cleanup are NO LONGER
in this file. They have been migrated to back office tasks owned by TP:
  - back-office-agent-hygiene → services/back_office/agent_hygiene.py
  - back-office-workspace-cleanup → services/back_office/workspace_cleanup.py
Both run through execute_task() via the TP dispatch branch in task_pipeline.py
(_execute_tp_task). The scheduler has no knowledge of what any particular task
does — it just dispatches execute_task() for everything that's due.

Layer 2 (task_pipeline.py — Sonnet per user task; zero LLM for TP tasks):
- TASK.md → resolve agent → dispatch
- If agent.role == 'thinking_partner': _execute_tp_task() → run declared executor
- Else: standard Sonnet generation path
- All paths: save output, update last_run_at, calculate next_run_at

Layer 3 (thinking_partner.py — user-present only):
- Chat mode with primitives. TP is the single intelligence layer (ADR-156).
- Memory: TP writes facts in-session via UpdateContext(target="memory")
- Session continuity: inline summary at session close (chat.py) + AWARENESS.md

Run every 5 minutes via Render cron:
  schedule: "*/5 * * * *"
  command: cd api && python -m jobs.unified_scheduler
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from croniter import croniter

# import_jobs DELETED (ADR-153 + ADR-156: platform data flows through task execution)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Shared Utilities
# =============================================================================

def calculate_next_pulse_from_schedule(schedule: dict, from_time: Optional[datetime] = None) -> datetime:
    """
    Calculate next pulse time from a schedule config (ADR-126).

    Supports both cron expressions and frequency-based schedules.
    The schedule defines the default pulse rhythm — how often the agent senses.

    Args:
        schedule: Schedule dict with frequency, day, time, timezone, cron
        from_time: Base time (defaults to now)

    Returns:
        Next pulse time as UTC datetime
    """
    import pytz

    if from_time is None:
        from_time = datetime.now(timezone.utc)

    tz_name = schedule.get("timezone", "UTC")
    try:
        tz = pytz.timezone(tz_name)
    except pytz.UnknownTimeZoneError:
        tz = pytz.UTC

    # If cron expression provided, use it
    cron_expr = schedule.get("cron")
    if cron_expr:
        local_time = from_time.astimezone(tz)
        cron = croniter(cron_expr, local_time)
        next_local = cron.get_next(datetime)
        return next_local.astimezone(timezone.utc)

    # Otherwise, use frequency-based calculation
    frequency = schedule.get("frequency", "weekly")
    day = schedule.get("day", "monday")
    time_str = schedule.get("time", "09:00")

    # Parse time
    try:
        hour, minute = map(int, time_str.split(":"))
    except (ValueError, AttributeError):
        hour, minute = 9, 0

    local_now = from_time.astimezone(tz)

    if frequency == "daily":
        next_run = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= local_now:
            next_run += timedelta(days=1)

    elif frequency == "weekly":
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        day_str = (day or "monday").lower()
        target_day = days.index(day_str) if day_str in days else 0
        current_day = local_now.weekday()
        days_ahead = target_day - current_day
        if days_ahead < 0:
            days_ahead += 7
        next_run = local_now + timedelta(days=days_ahead)
        next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= local_now:
            next_run += timedelta(weeks=1)

    elif frequency == "biweekly":
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        day_str = (day or "monday").lower()
        target_day = days.index(day_str) if day_str in days else 0
        current_day = local_now.weekday()
        days_ahead = target_day - current_day
        if days_ahead < 0:
            days_ahead += 7
        next_run = local_now + timedelta(days=days_ahead)
        next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= local_now:
            next_run += timedelta(weeks=2)

    elif frequency == "monthly":
        # First occurrence of day in next month
        next_run = local_now.replace(day=1, hour=hour, minute=minute, second=0, microsecond=0)
        if next_run.month == 12:
            next_run = next_run.replace(year=next_run.year + 1, month=1)
        else:
            next_run = next_run.replace(month=next_run.month + 1)
        # Find the first target_day
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        day_str = (day or "monday").lower()
        target_day = days.index(day_str) if day_str in days else 0
        while next_run.weekday() != target_day:
            next_run += timedelta(days=1)

    else:
        # Default: next week same time
        next_run = local_now + timedelta(weeks=1)
        next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)

    return next_run.astimezone(timezone.utc)


def format_schedule_description(schedule: dict) -> str:
    """Format schedule as human-readable string."""
    frequency = schedule.get("frequency", "weekly")
    day = schedule.get("day", "monday")
    time_str = schedule.get("time", "09:00")

    day_display = day.capitalize() if day else ""

    if frequency == "daily":
        return f"Daily at {time_str}"
    elif frequency == "weekly":
        return f"Every {day_display} at {time_str}"
    elif frequency == "biweekly":
        return f"Every other {day_display} at {time_str}"
    elif frequency == "monthly":
        return f"Monthly on {day_display} at {time_str}"
    else:
        return f"{frequency.capitalize()} at {time_str}"


async def get_user_email(supabase_client, user_id: str) -> Optional[str]:
    """Get user's email for notification."""
    try:
        result = supabase_client.auth.admin.get_user_by_id(user_id)
        if result and result.user:
            return result.user.email
    except Exception as e:
        logger.warning(f"Failed to get user email: {e}")
    return None


async def should_send_email(supabase_client, user_id: str, notification_type: str) -> bool:
    """
    Check if user has email notifications enabled for this type.

    Args:
        supabase_client: Supabase client
        user_id: User ID
        notification_type: 'agent_ready', 'agent_failed', 'suggestion_created'

    Returns:
        True if should send email (defaults to True if no preferences set)
    """
    # Map notification type to column name
    column_map = {
        "agent_ready": "email_agent_ready",
        "agent_failed": "email_agent_failed",
        "suggestion_created": "email_suggestion_created",
    }

    column = column_map.get(notification_type)
    if not column:
        # Unknown notification type, default to sending
        return True

    try:
        # Query user notification preferences using the helper function
        result = supabase_client.rpc(
            "get_notification_preferences",
            {"p_user_id": user_id}
        ).execute()

        if result.data and len(result.data) > 0:
            prefs = result.data[0]
            # Return the preference value (defaults handled by DB function)
            return prefs.get(column, True)

        # No preferences found, default to sending
        return True

    except Exception as e:
        logger.warning(f"Failed to check notification preferences for {user_id}: {e}")
        # On error, default to sending
        return True


# =============================================================================
# Task Scheduling (ADR-138)
# =============================================================================

async def get_due_tasks(supabase_client) -> list[dict]:
    """
    ADR-141: Query tasks table for due tasks.

    Returns active tasks where next_run_at <= now.
    """
    now = datetime.now(timezone.utc)

    try:
        result = (
            supabase_client.table("tasks")
            .select("id, user_id, slug, status, schedule, next_run_at, last_run_at")
            .eq("status", "active")
            .lte("next_run_at", now.isoformat())
            .execute()
        )
        return result.data or []
    except Exception as e:
        # tasks table may not exist yet or be empty — graceful degradation
        logger.debug(f"[TASKS] Query failed (expected if no tasks yet): {e}")
        return []


async def execute_due_tasks(supabase_client, due_tasks: list[dict]) -> tuple[int, int]:
    """
    ADR-141: Execute all due tasks. Returns (success_count, fail_count).

    Each task is executed independently — one failure doesn't block others.
    """
    from services.task_pipeline import execute_task

    success = 0
    failed = 0

    for task in due_tasks:
        user_id = task.get("user_id")
        slug = task.get("slug")
        if not user_id or not slug:
            logger.warning(f"[TASKS] Skipping task with missing user_id or slug: {task.get('id')}")
            failed += 1
            continue

        # Atomic claim: bump next_run_at to sentinel (+2h) only if it still
        # matches what we queried. If another scheduler instance already
        # claimed this task, the update affects 0 rows and we skip.
        # This prevents duplicate execution from concurrent cron instances.
        original_next_run = task.get("next_run_at")
        sentinel = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        try:
            claim_result = (
                supabase_client.table("tasks")
                .update({"next_run_at": sentinel})
                .eq("id", task["id"])
                .eq("next_run_at", original_next_run)  # CAS — only if unchanged
                .execute()
            )
            if not claim_result.data:
                logger.info(f"[TASKS] Skipping {slug} — already claimed by another instance")
                continue
        except Exception as e:
            logger.warning(f"[TASKS] Claim failed for {slug}: {e}")
            continue

        try:
            result = await execute_task(supabase_client, user_id, slug)
            if result.get("success"):
                success += 1
                logger.info(f"[TASKS] ✓ {slug}: {result.get('message', 'OK')}")
            else:
                failed += 1
                logger.warning(f"[TASKS] ✗ {slug}: {result.get('message', 'Unknown error')}")
        except Exception as e:
            failed += 1
            logger.error(f"[TASKS] Exception executing {slug}: {e}")

    return success, failed


# =============================================================================
# ADR-164: Lifecycle hygiene migrated from this file to a back office task.
# Was _pause_underperformers() + UNDERPERFORMER_MIN_RUNS + UNDERPERFORMER_MAX_APPROVAL.
# Now lives at services/back_office/agent_hygiene.py and is executed through
# the task pipeline via a back-office-agent-hygiene task owned by TP. Same
# rules, same thresholds — just declarative and visible to the user as a
# regular task run rather than hidden in scheduler code.
# =============================================================================


# =============================================================================
# Main Entry Point
# =============================================================================

async def run_unified_scheduler():
    """
    Main scheduler entry point (ADR-138: clean slate).

    Queries due tasks (stub — Phase 3), processes imports, runs Composer heartbeat,
    and handles nightly memory extraction. Called by Render cron every 5 minutes.
    """
    from supabase import create_client

    # Initialize Supabase client
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        return

    supabase = create_client(supabase_url, supabase_key)

    now = datetime.now(timezone.utc)
    is_hourly_tick = now.minute < 5  # First tick of each hour
    logger.info(f"[{now.isoformat()}] Starting unified scheduler...")

    # -------------------------------------------------------------------------
    # Discover active users (those with platform connections) for heartbeat writes.
    # ADR-164: We no longer need a separate "all users with agents" list —
    # lifecycle hygiene moved to back office tasks that run per-user via the
    # normal task dispatch path.
    # -------------------------------------------------------------------------
    try:
        _conn_result = supabase.table("platform_connections").select(
            "user_id"
        ).eq("status", "active").execute()
        active_user_ids = list(set(row["user_id"] for row in (_conn_result.data or [])))
    except Exception:
        active_user_ids = []

    # -------------------------------------------------------------------------
    # ADR-141: Task execution — find and run due tasks
    # -------------------------------------------------------------------------
    due_tasks = await get_due_tasks(supabase)
    tasks_found = len(due_tasks)
    task_success = 0
    task_failed = 0

    if tasks_found > 0:
        logger.info(f"[TASKS] Found {tasks_found} due tasks — executing...")
        task_success, task_failed = await execute_due_tasks(supabase, due_tasks)
        logger.info(f"[TASKS] Execution complete: {task_success} succeeded, {task_failed} failed")
    else:
        logger.info(f"[TASKS] No due tasks")

    # -------------------------------------------------------------------------
    # ADR-164: Ephemeral cleanup and lifecycle hygiene migrated to back office
    # tasks owned by TP. Both now run through execute_task() via the TP dispatch
    # branch in task_pipeline.py. See services/back_office/workspace_cleanup.py
    # and services/back_office/agent_hygiene.py. The scheduler is now a pure
    # dispatcher — no knowledge of what any particular task does.
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    summary_parts = [
        f"tasks={task_success}/{tasks_found}",
    ]

    # -------------------------------------------------------------------------
    # ADR-072: Write scheduler_heartbeat event for system state awareness
    # -------------------------------------------------------------------------
    errors_encountered: list[str] = []
    # Note: Errors are already logged inline; heartbeat captures aggregate counts

    # Write scheduler_heartbeat hourly (not every 5 min) to reduce activity log bloat.
    # System status page only needs the latest heartbeat per user — hourly is sufficient.
    if is_hourly_tick:
        try:
            from services.activity_log import write_activity

            heartbeat_summary = f"Scheduler cycle: tasks={task_success}/{tasks_found}"
            heartbeat_metadata = {
                "tasks_due": tasks_found,
                "tasks_succeeded": task_success,
                "tasks_failed": task_failed,
                "errors": errors_encountered if errors_encountered else None,
                "cycle_started_at": now.isoformat(),
                "cycle_completed_at": datetime.now(timezone.utc).isoformat(),
            }

            for hb_user_id in active_user_ids:
                await write_activity(
                    client=supabase,
                    user_id=hb_user_id,
                    event_type="scheduler_heartbeat",
                    summary=heartbeat_summary,
                    metadata=heartbeat_metadata,
                )
        except Exception as e:
            logger.warning(f"[SCHEDULER] Failed to write heartbeat event: {e}")

    logger.info(f"Completed: {', '.join(summary_parts)}")


if __name__ == "__main__":
    asyncio.run(run_unified_scheduler())
