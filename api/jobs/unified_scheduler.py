"""
YARNNN v5 - Unified Scheduler (ADR-138 + ADR-141)

Three-layer execution: mechanical scheduling, LLM generation, TP intelligence.

Layer 1 (this file — zero LLM cost):
- Task scheduling: SQL query → execute_task() for each due task
- Platform content cleanup (ADR-072)
- Workspace ephemeral cleanup (ADR-119)
- Import jobs
- Composer heartbeat (ADR-111)
- Memory extraction (nightly)

Layer 2 (task_execution.py — Sonnet per task):
- TASK.md → AGENT.md → context → generate → deliver

Layer 3 (thinking_partner.py — user-present + periodic heartbeat):
- Chat mode + TP heartbeat (reads health flags, orchestrates)

Run every 5 minutes via Render cron:
  schedule: "*/5 * * * *"
  command: cd api && python -m jobs.unified_scheduler
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

from croniter import croniter

from .import_jobs import get_pending_import_jobs, process_import_job, recover_stale_processing_jobs

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
    logger.info(f"[{now.isoformat()}] Starting unified scheduler...")

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
    # ADR-072: Cleanup Expired Platform Content (hourly)
    # -------------------------------------------------------------------------
    content_cleaned = 0
    if now.minute < 5:  # Only run cleanup in first 5 minutes of each hour
        try:
            from services.platform_content import cleanup_expired_content
            content_cleaned = await cleanup_expired_content(supabase)
            if content_cleaned > 0:
                logger.info(f"[PLATFORM_CONTENT] Cleaned up {content_cleaned} expired items")
            # Always log cleanup event so system page never shows "never_run"
            try:
                from services.activity_log import write_activity as _cw
                active_users = supabase.table("platform_connections").select(
                    "user_id"
                ).eq("status", "active").execute()
                for uid in set(row["user_id"] for row in (active_users.data or [])):
                    await _cw(
                        client=supabase,
                        user_id=uid,
                        event_type="content_cleanup",
                        summary=f"Cleaned {content_cleaned} expired content items",
                        metadata={"items_deleted": content_cleaned},
                    )
            except Exception as e:
                logger.debug(f"[PLATFORM_CONTENT] Activity log write failed for cleanup: {e}")
        except Exception as e:
            logger.warning(f"[PLATFORM_CONTENT] Cleanup failed (non-fatal): {e}")

    # -------------------------------------------------------------------------
    # ADR-119/127: Cleanup Ephemeral Workspace Files (hourly)
    # Two-tier TTL: /working/ scratch = 24h, /user_shared/ staging = 30 days.
    # -------------------------------------------------------------------------
    if now.minute < 5:  # Same cadence as content cleanup
        try:
            # Tier 1: /working/ scratch files — 24h TTL
            working_cleaned = supabase.table("workspace_files").delete().eq(
                "lifecycle", "ephemeral"
            ).like(
                "path", "%/working/%"
            ).lt(
                "updated_at", (now - timedelta(hours=24)).isoformat()
            ).execute()
            working_count = len(working_cleaned.data or [])

            # Tier 2: /user_shared/ staging files — 30 day TTL (ADR-127)
            shared_cleaned = supabase.table("workspace_files").delete().eq(
                "lifecycle", "ephemeral"
            ).like(
                "path", "%/user_shared/%"
            ).lt(
                "updated_at", (now - timedelta(days=30)).isoformat()
            ).execute()
            shared_count = len(shared_cleaned.data or [])

            total_cleaned = working_count + shared_count
            if total_cleaned > 0:
                logger.info(f"[WORKSPACE] ADR-119/127: Cleaned {working_count} working + {shared_count} user_shared ephemeral files")
        except Exception as e:
            logger.warning(f"[WORKSPACE] Ephemeral cleanup failed (non-fatal): {e}")

    # -------------------------------------------------------------------------
    # ADR-040: Event trigger cooldowns are database-backed (event_trigger_log).
    # No in-memory cleanup needed.

    # -------------------------------------------------------------------------
    # Process Integration Import Jobs (ADR-027)
    # -------------------------------------------------------------------------
    import_count = 0
    import_success = 0

    try:
        # First, recover any stale processing jobs (safety net for crashed processes)
        recovered_count = await recover_stale_processing_jobs(supabase, stale_minutes=10)
        if recovered_count > 0:
            logger.info(f"[IMPORT] Recovered {recovered_count} stale job(s)")

        import_jobs = await get_pending_import_jobs(supabase)
        import_count = len(import_jobs)
        logger.info(f"[IMPORT] Found {import_count} pending import job(s)")

        for job in import_jobs:
            try:
                if await process_import_job(supabase, job):
                    import_success += 1
            except Exception as e:
                logger.error(f"[IMPORT] Unexpected error for job {job.get('id')}: {e}")
    except Exception as e:
        # Handle schema cache miss or table not found errors gracefully
        # PGRST205 = table not found in schema cache (needs cache refresh in Supabase)
        logger.warning(f"[IMPORT] Import jobs processing skipped: {e}")

    # -------------------------------------------------------------------------
    # ADR-111 Phase 3: TP Composer Heartbeat
    # Cheap data query per user → Composer assessment only when warranted.
    # Free: daily (midnight UTC). Pro: every cycle (cheap-first = negligible cost).
    # -------------------------------------------------------------------------
    composer_users = 0
    composer_created = 0
    composer_lifecycle = 0  # ADR-111 Phase 5: lifecycle actions (pause, expand)
    try:
        from services.composer import run_heartbeat
        from services.platform_limits import get_user_tier

        # Get all users with substrate: platform connections OR active agents
        # Platform connections are the onramp, but users with research/knowledge
        # agents (no platforms) still need Heartbeat (FOUNDATIONS.md: platform ≠ engine)
        active_conn = supabase.table("platform_connections").select(
            "user_id"
        ).in_("status", ["connected", "active"]).execute()
        heartbeat_user_ids_set = set(
            row["user_id"] for row in (active_conn.data or [])
        )
        # Also include users with active agents but no platform connections
        active_agents_users = supabase.table("agents").select(
            "user_id"
        ).eq("status", "active").execute()
        for row in (active_agents_users.data or []):
            heartbeat_user_ids_set.add(row["user_id"])

        for hb_uid in heartbeat_user_ids_set:
            # Tier gating: free = daily only (midnight window), pro = every cycle
            tier = get_user_tier(supabase, hb_uid)
            is_midnight_window = now.hour == 0 and now.minute < 5
            if tier == "free" and not is_midnight_window:
                continue

            try:
                hb_result = await run_heartbeat(supabase, hb_uid)
                composer_users += 1

                composer_result = hb_result.get("composer_result") or {}
                created_count = len(composer_result.get("contributors_created", []))
                composer_created += created_count

                # ADR-111 Phase 5: Count lifecycle actions from Heartbeat
                lifecycle_actions = composer_result.get("lifecycle_actions", [])
                composer_lifecycle += len(lifecycle_actions)

                # Write heartbeat event
                try:
                    from services.activity_log import write_activity as _chw
                    await _chw(
                        client=supabase,
                        user_id=hb_uid,
                        event_type="composer_heartbeat",
                        summary=f"Composer heartbeat: {hb_result.get('reason', 'OK')}",
                        metadata={
                            "origin": "cron",  # ADR-114: distinguish from event-driven heartbeats
                            "should_act": hb_result.get("should_act", False),
                            "reason": hb_result.get("reason", ""),
                            "contributors_created": created_count,
                            "lifecycle_actions": len(lifecycle_actions),
                            **hb_result.get("assessment_summary", {}),
                        },
                    )
                except Exception:
                    pass  # Non-fatal
            except Exception as e:
                logger.warning(f"[COMPOSER] Heartbeat failed for {hb_uid}: {e}")
    except Exception as e:
        logger.warning(f"[COMPOSER] Heartbeat phase skipped: {e}")

    # -------------------------------------------------------------------------
    # Memory Extraction + Session Summaries (ADR-064, ADR-067 Phase 1)
    # Process yesterday's sessions — only run at midnight UTC
    # -------------------------------------------------------------------------
    memory_users = 0
    memory_extracted = 0
    summaries_written = 0
    if now.hour == 0 and now.minute < 5:  # Only in first 5 minutes of midnight UTC
        try:
            from services.memory import process_conversation
            from services.session_continuity import generate_session_summary

            # Get TP sessions from yesterday
            yesterday = (now - timedelta(days=1)).date().isoformat()
            today = now.date().isoformat()

            sessions_result = (
                supabase.table("chat_sessions")
                .select("id, user_id, created_at, session_type")
                .gte("created_at", yesterday)
                .lt("created_at", today)
                .eq("session_type", "thinking_partner")
                .execute()
            )
            sessions = sessions_result.data or []
            logger.info(f"[MEMORY] Found {len(sessions)} sessions from yesterday to process")

            for session in sessions:
                try:
                    session_id = session["id"]
                    user_id = session["user_id"]
                    session_date = session.get("created_at", yesterday)[:10]

                    # Get messages for this session
                    messages_result = (
                        supabase.table("session_messages")
                        .select("role, content, metadata")
                        .eq("session_id", session_id)
                        .order("sequence_number")
                        .execute()
                    )
                    messages = messages_result.data or []
                    user_msg_count = len([m for m in messages if m.get("role") == "user"])

                    if user_msg_count >= 3:
                        # Memory extraction (ADR-064) — global TP sessions only
                        # Project sessions have multi-agent context; memory extraction
                        # is user-scoped and doesn't apply to project conversations
                        session_type = session.get("session_type", "thinking_partner")
                        if session_type == "thinking_partner":
                            extracted = await process_conversation(
                                client=supabase,
                                user_id=user_id,
                                messages=messages,
                                session_id=session_id,
                            )
                            if extracted > 0:
                                memory_extracted += extracted
                                memory_users += 1
                                logger.info(f"[MEMORY] Extracted {extracted} memories from session {session_id}")

                        # Session summary (ADR-067 Phase 1)
                        # Requires ≥ 5 user messages — substantive sessions only
                        if user_msg_count >= 5:
                            summary = await generate_session_summary(
                                messages=messages,
                                session_date=session_date,
                            )
                        else:
                            summary = None
                        if summary:
                            supabase.table("chat_sessions").update(
                                {"summary": summary}
                            ).eq("id", session_id).execute()
                            summaries_written += 1
                            logger.info(f"[MEMORY] Wrote session summary for {session_id}")

                except Exception as session_err:
                    logger.warning(f"[MEMORY] Error processing session {session['id']}: {session_err}")

            if memory_users > 0 or summaries_written > 0:
                logger.info(
                    f"[MEMORY] Processed {memory_users} sessions, "
                    f"extracted {memory_extracted} memories, "
                    f"wrote {summaries_written} session summaries"
                )

            # Write session_summary_written events (aggregate per user who had sessions)
            if summaries_written > 0:
                try:
                    from services.activity_log import write_activity as _ssw
                    # Get unique user_ids from yesterday's sessions
                    session_user_ids = list(set(
                        s.get("user_id") for s in (sessions_result.data or []) if s.get("user_id")
                    ))
                    for uid in session_user_ids:
                        await _ssw(
                            client=supabase,
                            user_id=uid,
                            event_type="session_summary_written",
                            summary=f"Session summaries: {summaries_written} written, {memory_extracted} memories extracted",
                            metadata={
                                "summaries_written": summaries_written,
                                "memories_extracted": memory_extracted,
                                "sessions_processed": memory_users,
                            },
                        )
                except Exception as e:
                    logger.debug(f"[MEMORY] Activity log write failed for session summaries: {e}")

        except Exception as e:
            logger.warning(f"[MEMORY] Memory extraction phase skipped: {e}")

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    summary_parts = [
        f"tasks={task_success}/{tasks_found}",
        f"imports={import_success}/{import_count}",
    ]
    if memory_extracted > 0:
        summary_parts.append(f"memory={memory_extracted} from {memory_users} sessions")
    if composer_users > 0:
        composer_summary = f"composer={composer_users} users"
        if composer_created > 0:
            composer_summary += f" ({composer_created} created)"
        if composer_lifecycle > 0:
            composer_summary += f" ({composer_lifecycle} lifecycle)"
        summary_parts.append(composer_summary)

    # -------------------------------------------------------------------------
    # ADR-072: Write scheduler_heartbeat event for system state awareness
    # -------------------------------------------------------------------------
    errors_encountered: list[str] = []
    # Note: Errors are already logged inline; heartbeat captures aggregate counts

    try:
        from services.activity_log import write_activity

        # Build heartbeat summary
        heartbeat_summary = f"Scheduler cycle: tasks={task_success}/{tasks_found}, imports={import_success}/{import_count}"

        # Write per-user heartbeat for all users with active connections
        # so the system page can show scheduler status per user
        heartbeat_metadata = {
            "tasks_due": tasks_found,
            "tasks_succeeded": task_success,
            "tasks_failed": task_failed,
            "imports_checked": import_count,
            "imports_triggered": import_success,
            "composer_users": composer_users,
            "composer_created": composer_created,
            "composer_lifecycle": composer_lifecycle,
            "memory_extracted": memory_extracted,
            "errors": errors_encountered if errors_encountered else None,
            "cycle_started_at": now.isoformat(),
            "cycle_completed_at": datetime.now(timezone.utc).isoformat(),
        }

        # Get all users with active platform connections
        active_users = supabase.table("platform_connections").select(
            "user_id"
        ).eq("status", "active").execute()
        heartbeat_user_ids = list(set(
            row["user_id"] for row in (active_users.data or [])
        ))

        for hb_user_id in heartbeat_user_ids:
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
