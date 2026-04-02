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
from typing import Any, Optional

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
# ADR-156: Deterministic Lifecycle Hygiene (replaces Composer)
# Zero LLM — mechanical rules only. Runs in scheduler cron.
# =============================================================================

UNDERPERFORMER_MIN_RUNS = 8
UNDERPERFORMER_MAX_APPROVAL = 0.30


async def _pause_underperformers(client: Any, user_id: str) -> int:
    """
    Pause agents with consistently low approval rates.

    Rule: >= UNDERPERFORMER_MIN_RUNS runs AND < UNDERPERFORMER_MAX_APPROVAL approval rate
    AND origin != 'user_configured' (respect user's explicit choices).

    Returns count of agents paused this cycle.
    """
    # Get active agents with their run stats
    agents_result = client.table("agents").select(
        "id, title, role, origin"
    ).eq("user_id", user_id).eq("status", "active").execute()
    agents = agents_result.data or []
    if not agents:
        return 0

    agent_ids = [a["id"] for a in agents]

    # Batch query: approval rates per agent
    runs_result = client.table("agent_runs").select(
        "agent_id, status"
    ).in_("agent_id", agent_ids).execute()
    runs = runs_result.data or []

    # Compute per-agent stats
    stats: dict[str, dict] = {}
    for run in runs:
        aid = run["agent_id"]
        if aid not in stats:
            stats[aid] = {"total": 0, "approved": 0}
        stats[aid]["total"] += 1
        if run.get("status") == "approved":
            stats[aid]["approved"] += 1

    paused_count = 0
    for agent in agents:
        aid = agent["id"]
        # Skip user-configured agents — respect explicit choices
        if agent.get("origin") == "user_configured":
            continue

        agent_stats = stats.get(aid)
        if not agent_stats:
            continue

        total = agent_stats["total"]
        if total < UNDERPERFORMER_MIN_RUNS:
            continue

        approval_rate = agent_stats["approved"] / total
        if approval_rate >= UNDERPERFORMER_MAX_APPROVAL:
            continue

        # Pause the underperformer
        try:
            client.table("agents").update(
                {"status": "paused"}
            ).eq("id", aid).execute()

            # Write coaching feedback
            from services.feedback_distillation import write_feedback_entry
            await write_feedback_entry(
                client=client,
                user_id=user_id,
                agent=agent,
                feedback_text=f"Auto-paused: {approval_rate:.0%} approval over {total} runs. Review output quality and deliverable spec.",
                source="system_lifecycle",
            )

            # Log activity
            from services.activity_log import write_activity
            await write_activity(
                client=client,
                user_id=user_id,
                event_type="agent_scheduled",
                summary=f"Auto-paused {agent['title']} ({approval_rate:.0%} approval over {total} runs)",
                metadata={
                    "agent_id": aid,
                    "lifecycle_action": "paused",
                    "approval_rate": round(approval_rate, 2),
                    "run_count": total,
                    "origin": "lifecycle_hygiene",
                },
            )

            paused_count += 1
            logger.info(f"[LIFECYCLE] Paused {agent['title']} ({approval_rate:.0%} approval, {total} runs)")
        except Exception as e:
            logger.warning(f"[LIFECYCLE] Failed to pause {agent['title']}: {e}")

    return paused_count


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
    # Shared: Discover active users once, reuse across phases
    # -------------------------------------------------------------------------
    try:
        _conn_result = supabase.table("platform_connections").select(
            "user_id"
        ).in_("status", ["connected", "active"]).execute()
        active_user_ids = list(set(row["user_id"] for row in (_conn_result.data or [])))
    except Exception:
        active_user_ids = []

    # Also include users with active agents but no platform connections
    try:
        _agent_result = supabase.table("agents").select(
            "user_id"
        ).eq("status", "active").execute()
        all_user_ids_set = set(active_user_ids)
        for row in (_agent_result.data or []):
            all_user_ids_set.add(row["user_id"])
        all_heartbeat_user_ids = list(all_user_ids_set)
    except Exception:
        all_heartbeat_user_ids = list(active_user_ids)

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
    # ADR-156: Deterministic lifecycle hygiene (replaces Composer heartbeat)
    # Zero LLM — mechanical rule: pause agents with >=8 runs AND <30% approval
    # that are NOT user-configured. Runs once per cycle.
    # -------------------------------------------------------------------------
    lifecycle_paused = 0
    try:
        for lc_uid in all_heartbeat_user_ids:
            try:
                paused = await _pause_underperformers(supabase, lc_uid)
                lifecycle_paused += paused
            except Exception as e:
                logger.warning(f"[LIFECYCLE] Underperformer check failed for {lc_uid}: {e}")
    except Exception as e:
        logger.warning(f"[LIFECYCLE] Lifecycle phase skipped: {e}")

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
    if lifecycle_paused > 0:
        summary_parts.append(f"lifecycle={lifecycle_paused} paused")

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

            heartbeat_summary = f"Scheduler cycle: tasks={task_success}/{tasks_found}, imports={import_success}/{import_count}"
            heartbeat_metadata = {
                "tasks_due": tasks_found,
                "tasks_succeeded": task_success,
                "tasks_failed": task_failed,
                "imports_checked": import_count,
                "imports_triggered": import_success,
                "lifecycle_paused": lifecycle_paused,
                "memory_extracted": memory_extracted,
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
