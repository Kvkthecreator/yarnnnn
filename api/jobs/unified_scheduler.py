"""
YARNNN v5 - Unified Scheduler (Pulse Dispatcher — ADR-126)

Gives each agent its turn to pulse (sense→decide), then acts on the decision.
The scheduler dispatches pulses — agents decide whether to generate.

Consolidates:
- Agent pulse dispatch (ADR-126) — all modes, all agents
- TP Composer Heartbeat (ADR-111 Phase 3, being thinned by ADR-126)
- Import jobs
- Nightly conversation analysis + memory extraction
- Platform content cleanup (ADR-072)
- Workspace ephemeral cleanup (ADR-119)

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
from uuid import UUID

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
# Agent Processing (ADR-018)
# =============================================================================

async def get_due_pulse_agents(supabase_client) -> list[dict]:
    """
    ADR-126: Query ALL active agents due for pulse.

    Returns active agents where next_pulse_at <= now, regardless of mode.
    Every agent gets a pulse — the pulse decides whether to generate.
    """
    now = datetime.now(timezone.utc)

    result = (
        supabase_client.table("agents")
        .select("id, user_id, title, scope, role, type_config, schedule, sources, destination, recipient_context, last_run_at, agent_instructions, mode, trigger_config, project_id")
        .eq("status", "active")
        .lte("next_pulse_at", now.isoformat())
        .execute()
    )

    return result.data or []


def resolve_due_duties(agent: dict) -> list[dict]:
    """ADR-117 Phase 3: Resolve which duties are due for this agent.

    Returns list of {duty, trigger} dicts to execute. When duties is null
    (pre-ADR-117 agent), returns a synthetic single duty matching the seed role.
    """
    duties = agent.get("duties")
    role = agent.get("role", "custom")

    if not duties:
        # Backwards compat: single-duty agent uses seed role
        return [{"duty": role, "trigger": "recurring"}]

    # Filter to active duties only
    return [
        d for d in duties
        if d.get("status", "active") == "active"
    ]


async def process_agent(supabase_client, agent: dict) -> bool:
    """
    Process a single agent: generate version, send email, update schedule.

    ADR-042: Uses simplified execute_agent_generation() instead of 3-step pipeline.
    ADR-117 Phase 3: Iterates over due duties when agent has multi-duty portfolio.

    Returns True if successful.
    """
    from services.trigger_dispatch import dispatch_trigger
    from services.activity_log import write_activity, resolve_agent_project_slug

    agent_id = agent["id"]
    user_id = agent["user_id"]
    title = agent["title"]
    role = agent.get("role", "custom")
    schedule = agent.get("schedule", {})

    # ADR-129: Resolve project_slug once for all activity events
    _proj_slug = resolve_agent_project_slug(agent)

    # ADR-117 Phase 3: Resolve duties to execute
    duties = resolve_due_duties(agent)
    logger.info(f"[AGENT] Processing: {title} ({agent_id}), duties={[d['duty'] for d in duties]}")

    # ADR-072: Write agent_scheduled event when queued for execution
    try:
        next_run = calculate_next_pulse_from_schedule(schedule)
        _sched_meta = {
            "agent_id": agent_id,
            "scheduled_for": datetime.now(timezone.utc).isoformat(),
            "trigger_reason": "schedule",
            "role": role,
            "duties": [d["duty"] for d in duties],
        }
        # ADR-129: Enrich with project_slug
        _proj_slug = resolve_agent_project_slug(agent)
        if _proj_slug:
            _sched_meta["project_slug"] = _proj_slug
        await write_activity(
            client=supabase_client,
            user_id=user_id,
            event_type="agent_scheduled",
            summary=f"Queued: {title}",
            event_ref=agent_id,
            metadata=_sched_meta,
        )
    except Exception as e:
        logger.warning(f"[AGENT] Failed to write scheduled event: {e}")

    all_success = True

    for duty in duties:
        duty_name = duty["duty"]
        try:
            # ADR-088: Route through dispatch — schedule triggers always generate (high)
            # ADR-117 Phase 3: Pass duty in trigger_context for effective_role resolution
            result = await dispatch_trigger(
                client=supabase_client,
                agent=agent,
                trigger_type="schedule",
                trigger_context={"type": "schedule", "duty": duty_name},
                signal_strength="high",
            )

            success = result.get("success", False)

            if success:
                logger.info(f"[AGENT] ✓ Complete: {title} (duty={duty_name})")
                try:
                    _gen_meta = {
                        "role": role,
                        "duty": duty_name,
                        "run_id": result.get("run_id"),
                    }
                    # ADR-129: Enrich with project_slug
                    if _proj_slug:
                        _gen_meta["project_slug"] = _proj_slug
                    await write_activity(
                        client=supabase_client,
                        user_id=user_id,
                        event_type="agent_generated",
                        summary=f"Generated: {title}" + (f" ({duty_name})" if duty_name != role else ""),
                        event_ref=agent_id,
                        metadata=_gen_meta,
                    )
                except Exception as e:
                    logger.debug(f"[AGENT] Activity log write failed for {title}: {e}")
            else:
                logger.warning(f"[AGENT] ✗ Failed: {title} (duty={duty_name}) - {result.get('error')}")
                all_success = False

        except Exception as e:
            logger.error(f"[AGENT] ✗ Error processing {title} (duty={duty_name}): {e}")
            all_success = False

    # Calculate and update next_pulse_at (once, after all duties processed)
    try:
        next_run = calculate_next_pulse_from_schedule(schedule)
        supabase_client.table("agents").update({
            "last_run_at": datetime.now(timezone.utc).isoformat(),
            "next_pulse_at": next_run.isoformat(),
        }).eq("id", agent_id).execute()
    except Exception as e:
        logger.warning(f"[AGENT] Failed to update next_pulse_at for {title}: {e}")

    return all_success


# =============================================================================
# Main Entry Point
# =============================================================================

async def run_unified_scheduler():
    """
    Main scheduler entry point — pulse dispatcher (ADR-126).

    Dispatches agent pulses, processes imports, runs Composer heartbeat,
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
    # ADR-126: Pulse Dispatch — all agents (pipeline execution removed)
    # -------------------------------------------------------------------------
    from services.agent_pulse import run_agent_pulse, calculate_next_pulse_at

    all_due_agents = await get_due_pulse_agents(supabase)
    standalone_agents = all_due_agents  # No project filtering — all agents pulse independently
    logger.info(f"[PULSE] Found {len(standalone_agents)} agents due for pulse")

    pulse_generated = 0
    pulse_observed = 0
    pulse_waited = 0
    pulse_escalated = 0
    agent_success = 0

    for agent in standalone_agents:
        try:
            # Agent decides via pulse (Tier 1 deterministic → Tier 2 self-assessment)
            decision = await run_agent_pulse(supabase, agent)

            if decision.action == "generate":
                pulse_generated += 1
                # Existing execution pipeline — unchanged
                if await process_agent(supabase, agent):
                    agent_success += 1
            elif decision.action == "observe":
                pulse_observed += 1
            elif decision.action == "wait":
                pulse_waited += 1
            elif decision.action == "escalate":
                pulse_escalated += 1

            # Update next_pulse_at for next cycle
            next_pulse = calculate_next_pulse_at(agent, decision)
            supabase.table("agents").update({
                "next_pulse_at": next_pulse.isoformat(),
            }).eq("id", agent["id"]).execute()

        except Exception as e:
            logger.error(f"[PULSE] Unexpected error for {agent.get('title', '?')}: {e}")

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
            from services.session_continuity import generate_session_summary, generate_project_session_summary

            # Get sessions from yesterday (both global TP and project sessions — ADR-125)
            yesterday = (now - timedelta(days=1)).date().isoformat()
            today = now.date().isoformat()

            sessions_result = (
                supabase.table("chat_sessions")
                .select("id, user_id, created_at, session_type, project_slug")
                .gte("created_at", yesterday)
                .lt("created_at", today)
                .in_("session_type", ["thinking_partner", "project"])
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
                    # ADR-125: Include metadata for author attribution in project sessions
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

                        # Session summary (ADR-067 Phase 1 + ADR-125)
                        # Requires ≥ 5 user messages — substantive sessions only
                        if user_msg_count >= 5:
                            project_slug = session.get("project_slug")
                            if session_type == "project" and project_slug:
                                # ADR-125: Author-aware summary for project sessions
                                summary = await generate_project_session_summary(
                                    messages=messages,
                                    session_date=session_date,
                                    project_slug=project_slug,
                                )
                            else:
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
    total_pulsed = len(all_due_agents)
    pulse_summary = f"pulse={total_pulsed} (gen={pulse_generated} obs={pulse_observed} wait={pulse_waited}"
    if pulse_escalated > 0:
        pulse_summary += f" esc={pulse_escalated}"
    pulse_summary += f") runs={agent_success}"

    summary_parts = [
        pulse_summary,
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
        heartbeat_summary = f"Pulse dispatch: {total_pulsed} pulsed, {agent_success} generated"

        # Write per-user heartbeat for all users with active connections
        # so the system page can show scheduler status per user
        heartbeat_metadata = {
            "agents_pulsed": total_pulsed,
            "pulse_generated": pulse_generated,
            "pulse_observed": pulse_observed,
            "pulse_waited": pulse_waited,
            "pulse_escalated": pulse_escalated,
            "agents_generated": agent_success,
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
