"""
YARNNN v5 - Unified Scheduler

Consolidates all scheduled job processing:
- ADR-017: Recurring work tickets
- ADR-018: Recurring deliverables

Run every 5 minutes via Render cron:
  schedule: "*/5 * * * *"
  command: cd api && python -m jobs.unified_scheduler

This replaces the separate work_scheduler.py to reduce cron job overhead.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from croniter import croniter

from .email import (
    send_email,
    send_work_complete_email,
)
from .digest import generate_digest_content
from .import_jobs import get_pending_import_jobs, process_import_job, recover_stale_processing_jobs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Shared Utilities
# =============================================================================

def calculate_next_run_from_schedule(schedule: dict, from_time: Optional[datetime] = None) -> datetime:
    """
    Calculate next run time from a schedule config.

    Supports both cron expressions and frequency-based schedules.

    Args:
        schedule: Schedule dict with frequency, day, time, timezone, cron
        from_time: Base time (defaults to now)

    Returns:
        Next run time as UTC datetime
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
        notification_type: 'deliverable_ready', 'deliverable_failed', 'work_complete', 'weekly_digest'

    Returns:
        True if should send email (defaults to True if no preferences set)
    """
    # Map notification type to column name
    column_map = {
        "deliverable_ready": "email_deliverable_ready",
        "deliverable_failed": "email_deliverable_failed",
        "work_complete": "email_work_complete",
        "weekly_digest": "email_weekly_digest",
        "suggestion_created": "email_suggestion_created",  # ADR-060
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
# Deliverable Processing (ADR-018)
# =============================================================================

async def get_due_deliverables(supabase_client) -> list[dict]:
    """
    Query deliverables due for generation.

    Returns active deliverables where next_run_at <= now.
    Includes last_run_at for freshness check (ADR-031).
    """
    now = datetime.now(timezone.utc)

    result = (
        supabase_client.table("deliverables")
        .select("id, user_id, title, deliverable_type, type_config, schedule, sources, destination, recipient_context, last_run_at")
        .eq("status", "active")
        .lte("next_run_at", now.isoformat())
        .execute()
    )

    return result.data or []


async def should_skip_deliverable(
    supabase_client,
    deliverable: dict,
) -> tuple[bool, str]:
    """
    Check if a deliverable should be skipped due to no new context.

    ADR-031 Phase 3: Skip generation if no fresh ephemeral context since last run.

    Args:
        supabase_client: Supabase client
        deliverable: Deliverable dict with sources and last_run_at

    Returns:
        Tuple of (should_skip, reason)
    """
    from services.platform_content import has_fresh_content_since

    sources = deliverable.get("sources", [])
    if not sources:
        # No sources configured - can't skip based on freshness
        return False, ""

    # Get last_run_at - if never run, don't skip
    last_run_at = deliverable.get("last_run_at")
    if not last_run_at:
        return False, ""

    # Parse last_run_at
    try:
        if isinstance(last_run_at, str):
            if last_run_at.endswith("Z"):
                last_run_at = last_run_at[:-1] + "+00:00"
            last_run_at = datetime.fromisoformat(last_run_at)
    except (ValueError, TypeError):
        return False, ""

    # Check for fresh platform content (ADR-072)
    try:
        has_fresh, count = await has_fresh_content_since(
            db_client=supabase_client,
            user_id=deliverable["user_id"],
            deliverable_sources=sources,
            since=last_run_at,
        )

        if not has_fresh:
            return True, "No new content since last run"

        return False, ""

    except Exception as e:
        # On error, don't skip - better to run than miss updates
        logger.warning(f"[DELIVERABLE] Freshness check failed: {e}")
        return False, ""


async def process_deliverable(supabase_client, deliverable: dict) -> bool:
    """
    Process a single deliverable: generate version, send email, update schedule.

    ADR-042: Uses simplified execute_deliverable_generation() instead of 3-step pipeline.

    Returns True if successful.
    """
    from services.deliverable_execution import execute_deliverable_generation
    from services.activity_log import write_activity

    deliverable_id = deliverable["id"]
    user_id = deliverable["user_id"]
    title = deliverable["title"]
    deliverable_type = deliverable["deliverable_type"]
    schedule = deliverable.get("schedule", {})

    logger.info(f"[DELIVERABLE] Processing: {title} ({deliverable_id})")

    # ADR-072: Write deliverable_scheduled event when queued for execution
    try:
        next_run = calculate_next_run_from_schedule(schedule)
        await write_activity(
            client=supabase_client,
            user_id=user_id,
            event_type="deliverable_scheduled",
            summary=f"Queued: {title}",
            event_ref=deliverable_id,
            metadata={
                "deliverable_id": deliverable_id,
                "scheduled_for": datetime.now(timezone.utc).isoformat(),
                "trigger_reason": "schedule",
                "deliverable_type": deliverable_type,
            },
        )
    except Exception as e:
        logger.warning(f"[DELIVERABLE] Failed to write scheduled event: {e}")

    try:
        # ADR-042: Single call replaces version creation + 3-step pipeline
        result = await execute_deliverable_generation(
            client=supabase_client,
            user_id=user_id,
            deliverable=deliverable,
            trigger_context={"type": "schedule"},
        )

        success = result.get("success", False)

        # 3. Calculate and update next_run_at
        next_run = calculate_next_run_from_schedule(schedule)
        supabase_client.table("deliverables").update({
            "last_run_at": datetime.now(timezone.utc).isoformat(),
            "next_run_at": next_run.isoformat(),
        }).eq("id", deliverable_id).execute()

        # Notifications handled by delivery service (delivery.py → notifications.py)
        # No scheduler-level email — single notification path via ADR-040.

        if success:
            logger.info(f"[DELIVERABLE] ✓ Complete: {title}")
            try:
                await write_activity(
                    client=supabase_client,
                    user_id=user_id,
                    event_type="deliverable_generated",
                    summary=f"Generated: {title}",
                    event_ref=deliverable_id,
                    metadata={
                        "deliverable_type": deliverable_type,
                        "version_id": result.get("version_id"),
                    },
                )
            except Exception:
                pass
        else:
            logger.warning(f"[DELIVERABLE] ✗ Failed: {title} - {result.get('error')}")

        return success

    except Exception as e:
        logger.error(f"[DELIVERABLE] ✗ Error processing {title}: {e}")

        # Still update next_run_at to prevent retry storm
        try:
            next_run = calculate_next_run_from_schedule(schedule)
            supabase_client.table("deliverables").update({
                "next_run_at": next_run.isoformat(),
            }).eq("id", deliverable_id).execute()
        except Exception:
            pass

        # Notify failure via delivery service's single notification path
        try:
            from services.notifications import notify_deliverable_failed
            from services.supabase import get_service_client
            await notify_deliverable_failed(
                db_client=get_service_client(),
                user_id=user_id,
                deliverable_id=deliverable_id,
                deliverable_title=title,
                error=str(e),
            )
        except Exception:
            pass

        return False


# =============================================================================
# Work Ticket Processing (ADR-017) - Preserved from work_scheduler.py
# =============================================================================

async def get_due_work(supabase_client) -> list[dict]:
    """Query recurring work due for execution."""
    now = datetime.now(timezone.utc)

    # Try new ADR-017 function first
    try:
        result = supabase_client.rpc(
            "get_due_work",
            {"check_time": now.isoformat()}
        ).execute()
        return result.data or []
    except Exception:
        pass

    # Fall back to old function
    try:
        result = supabase_client.rpc(
            "get_due_work_templates",
            {"check_time": now.isoformat()}
        ).execute()
        return result.data or []
    except Exception:
        return []


async def process_work(supabase_client, work: dict) -> bool:
    """Process a single recurring work item."""
    from services.work_execution import execute_work_ticket

    work_id = work.get("work_id") or work.get("template_id")
    user_id = work["user_id"]
    cron_expr = work.get("frequency_cron") or work.get("schedule_cron")
    tz_name = work.get("timezone") or work.get("schedule_timezone", "UTC")

    logger.info(f"[WORK] Processing: {work['task'][:50]}...")

    try:
        # 1. Spawn execution ticket
        ticket_data = {
            "task": work["task"],
            "agent_type": work["agent_type"],
            "status": "pending",
            "parameters": work.get("parameters", {}),
            "user_id": user_id,
            "parent_template_id": work_id,
            "is_template": False,
        }

        result = supabase_client.table("work_tickets").insert(ticket_data).execute()
        if not result.data:
            logger.error(f"[WORK] Failed to create execution ticket")
            return False

        ticket_id = result.data[0]["id"]
        logger.info(f"[WORK] Created execution: {ticket_id}")

        # 2. Execute the work
        exec_result = await execute_work_ticket(supabase_client, user_id, ticket_id)

        if not exec_result.get("success"):
            logger.warning(f"[WORK] Execution failed: {exec_result.get('error')}")

        # 3. Update schedule
        now = datetime.now(timezone.utc)
        import pytz
        try:
            tz = pytz.timezone(tz_name)
        except Exception:
            tz = pytz.UTC

        if cron_expr:
            local_time = now.astimezone(tz)
            cron = croniter(cron_expr, local_time)
            next_run = cron.get_next(datetime).astimezone(timezone.utc)
        else:
            next_run = now + timedelta(weeks=1)

        supabase_client.table("work_tickets").update({
            "schedule_last_run_at": now.isoformat(),
            "schedule_next_run_at": next_run.isoformat(),
        }).eq("id", work_id).execute()

        # 4. Send completion email
        if await should_send_email(supabase_client, user_id, "work_complete"):
            user_email = await get_user_email(supabase_client, user_id)
            if user_email and exec_result.get("success"):
                # Get outputs
                outputs_result = supabase_client.table("work_outputs").select("id, title, output_type, content").eq("ticket_id", ticket_id).execute()
                outputs = []
                for row in (outputs_result.data or []):
                    import json
                    summary = ""
                    content = row.get("content", "")
                    if content:
                        try:
                            parsed = json.loads(content)
                            if isinstance(parsed, dict):
                                summary = parsed.get("summary", "")[:200]
                        except Exception:
                            summary = content[:200] if content else ""
                    outputs.append({
                        "id": row["id"],
                        "title": row["title"],
                        "type": row["output_type"],
                        "summary": summary,
                    })

                await send_work_complete_email(
                    to=user_email,
                    project_name="yarnnn",
                    agent_type=work["agent_type"],
                    task=work["task"],
                    outputs=outputs,
                    project_id="",
                )
                logger.info(f"[WORK] ✓ Email sent to {user_email}")

        logger.info(f"[WORK] ✓ Complete: {work['task'][:50]}")
        return exec_result.get("success", False)

    except Exception as e:
        logger.error(f"[WORK] ✗ Error: {e}")

        # Update schedule to prevent retry storm
        try:
            now = datetime.now(timezone.utc)
            next_run = now + timedelta(weeks=1)
            supabase_client.table("work_tickets").update({
                "schedule_next_run_at": next_run.isoformat(),
            }).eq("id", work_id).execute()
        except Exception:
            pass

        return False


# =============================================================================
# Digest Processing (Weekly Digests)
# =============================================================================

async def get_workspaces_due_for_digest(supabase_client) -> list[dict]:
    """
    Query workspaces that are due for their weekly digest.
    Uses the get_workspaces_due_for_digest database function.
    """
    now = datetime.now(timezone.utc)

    try:
        result = supabase_client.rpc(
            "get_workspaces_due_for_digest",
            {"check_time": now.isoformat()}
        ).execute()
        return result.data or []
    except Exception as e:
        logger.warning(f"[DIGEST] Failed to query workspaces: {e}")
        return []


async def process_workspace_digest(
    supabase_client,
    workspace_id: str,
    owner_email: str,
    workspace_name: str,
    owner_id: str,
) -> bool:
    """
    Generate and send digest for a single workspace.
    Returns True if successful.
    """
    from uuid import UUID

    # Check if user wants digest emails
    if not await should_send_email(supabase_client, owner_id, "weekly_digest"):
        logger.info(f"[DIGEST] Skipping (user opted out): {workspace_name}")
        return True

    # Generate digest content
    content = await generate_digest_content(
        supabase_client,
        UUID(workspace_id),
        workspace_name,
    )

    # Skip if no activity
    if content.is_empty:
        logger.info(f"[DIGEST] Skipping (no activity): {workspace_name}")
        return True

    now = datetime.now(timezone.utc)

    # Create tracking record
    try:
        result = supabase_client.table("scheduled_messages").insert({
            "workspace_id": workspace_id,
            "scheduled_for": now.isoformat(),
            "message_type": "weekly_digest",
            "subject": content.subject,
            "content": content.to_dict(),
            "recipient_email": owner_email,
            "status": "pending",
        }).execute()
        message_id = result.data[0]["id"] if result.data else None
    except Exception as e:
        logger.warning(f"[DIGEST] Failed to create message record: {e}")
        message_id = None

    # Send email
    email_result = await send_email(
        to=owner_email,
        subject=content.subject,
        html=content.html,
        text=content.text,
    )

    # Update status
    if message_id:
        try:
            update_data = {
                "status": "sent" if email_result.success else "failed",
                "sent_at": now.isoformat() if email_result.success else None,
                "failure_reason": email_result.error,
            }
            supabase_client.table("scheduled_messages").update(update_data).eq(
                "id", message_id
            ).execute()
        except Exception:
            pass

    if email_result.success:
        logger.info(f"[DIGEST] ✓ Sent to {owner_email} for {workspace_name}")
    else:
        logger.warning(f"[DIGEST] ✗ Failed for {workspace_name}: {email_result.error}")

    return email_result.success


# =============================================================================
# Main Entry Point
# =============================================================================

async def run_unified_scheduler():
    """
    Main scheduler entry point.

    Processes deliverables (ADR-018), work tickets (ADR-017), and weekly digests.
    Called by Render cron every 5 minutes.
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
    # Process Deliverables (ADR-018)
    # -------------------------------------------------------------------------
    deliverables = await get_due_deliverables(supabase)
    logger.info(f"[DELIVERABLE] Found {len(deliverables)} due for generation")

    deliverable_success = 0
    deliverable_skipped = 0
    for deliverable in deliverables:
        try:
            # ADR-031 Phase 3: Skip if no new context since last run
            should_skip, skip_reason = await should_skip_deliverable(supabase, deliverable)
            if should_skip:
                logger.info(f"[DELIVERABLE] Skipping '{deliverable['title']}': {skip_reason}")
                deliverable_skipped += 1
                # Still update next_run_at to prevent re-checking every 5 minutes
                schedule = deliverable.get("schedule", {})
                next_run = calculate_next_run_from_schedule(schedule)
                supabase.table("deliverables").update({
                    "next_run_at": next_run.isoformat(),
                }).eq("id", deliverable["id"]).execute()
                continue

            if await process_deliverable(supabase, deliverable):
                deliverable_success += 1
        except Exception as e:
            logger.error(f"[DELIVERABLE] Unexpected error: {e}")

    # -------------------------------------------------------------------------
    # Process Work Tickets (ADR-017)
    # -------------------------------------------------------------------------
    work_items = await get_due_work(supabase)
    logger.info(f"[WORK] Found {len(work_items)} due for execution")

    work_success = 0
    for work in work_items:
        try:
            if await process_work(supabase, work):
                work_success += 1
        except Exception as e:
            logger.error(f"[WORK] Unexpected error: {e}")

    # -------------------------------------------------------------------------
    # Process Weekly Digests (runs hourly, but we check if due)
    # Only check at the top of each hour to avoid duplicate sends
    # -------------------------------------------------------------------------
    digest_success = 0
    digest_count = 0
    if now.minute < 5:  # Only run digest check in first 5 minutes of each hour
        workspaces = await get_workspaces_due_for_digest(supabase)
        digest_count = len(workspaces)
        logger.info(f"[DIGEST] Found {digest_count} workspace(s) due for digest")

        for ws in workspaces:
            try:
                success = await process_workspace_digest(
                    supabase,
                    workspace_id=ws["workspace_id"],
                    owner_email=ws["owner_email"],
                    workspace_name=ws["workspace_name"],
                    owner_id=ws.get("owner_id", ""),
                )
                if success:
                    digest_success += 1
            except Exception as e:
                logger.error(f"[DIGEST] Unexpected error for {ws.get('workspace_name')}: {e}")

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
                # Write per-user cleanup events
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
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"[PLATFORM_CONTENT] Cleanup failed (non-fatal): {e}")

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
    # -------------------------------------------------------------------------
    # ADR-060/061: Conversation Analysis Phase (daily)
    # ADR-060 Amendment 001: Behavioral pattern detection with user stages
    # Detects patterns in user conversations, creates suggested deliverables
    # -------------------------------------------------------------------------
    analysis_users = 0
    analysis_suggestions = 0
    analysis_cold_starts = 0
    # Run once per day at 6 AM UTC (when hour == 6 and minute < 5)
    if now.hour == 6 and now.minute < 5:
        try:
            from services.conversation_analysis import run_analysis_for_user
            from services.notifications import notify_suggestion_created, notify_analyst_cold_start

            # Get users with recent activity
            active_users_result = supabase.rpc(
                "get_active_users_for_analysis",
                {"days_back": 7}
            ).execute()

            # Fallback if function doesn't exist
            if not active_users_result.data:
                # Query users with recent sessions directly
                since = (now - timedelta(days=7)).isoformat()
                active_users_result = (
                    supabase.table("chat_sessions")
                    .select("user_id")
                    .gte("started_at", since)
                    .execute()
                )
                # Deduplicate
                user_ids = list(set(s["user_id"] for s in (active_users_result.data or [])))
            else:
                user_ids = [u["user_id"] for u in active_users_result.data]

            logger.info(f"[ANALYSIS] Found {len(user_ids)} users with recent activity")

            for user_id in user_ids:
                try:
                    # ADR-060 Amendment 001: run_analysis_for_user handles stage detection
                    suggestions_created, user_stage = await run_analysis_for_user(
                        supabase, user_id
                    )

                    if user_stage == "onboarding":
                        # Skip onboarding users entirely
                        continue

                    analysis_users += 1
                    analysis_suggestions += suggestions_created

                    if suggestions_created > 0:
                        # Get suggestion titles for notification
                        # Query the recently created suggestions
                        try:
                            recent_suggestions = (
                                supabase.table("deliverable_versions")
                                .select("deliverable_id, deliverables(title)")
                                .eq("status", "suggested")
                                .order("created_at", desc=True)
                                .limit(suggestions_created)
                                .execute()
                            )
                            titles = [
                                s.get("deliverables", {}).get("title", "Untitled")
                                for s in (recent_suggestions.data or [])
                            ]

                            await notify_suggestion_created(
                                db_client=supabase,
                                user_id=user_id,
                                suggestion_count=suggestions_created,
                                titles=titles,
                            )
                        except Exception as notify_err:
                            logger.warning(f"[ANALYSIS] Suggestion notification failed: {notify_err}")
                    else:
                        # ADR-060 Amendment 001: Send cold start if no suggestions
                        try:
                            cold_start_sent = await notify_analyst_cold_start(
                                supabase, user_id
                            )
                            if cold_start_sent:
                                analysis_cold_starts += 1
                                logger.info(f"[ANALYSIS] Sent cold start to {user_id}")
                        except Exception as cold_err:
                            logger.warning(f"[ANALYSIS] Cold start failed for {user_id}: {cold_err}")

                except Exception as e:
                    logger.warning(f"[ANALYSIS] Error for user {user_id}: {e}")

            if analysis_users > 0 or analysis_suggestions > 0 or analysis_cold_starts > 0:
                logger.info(
                    f"[ANALYSIS] Processed {analysis_users} users, "
                    f"created {analysis_suggestions} suggestions, "
                    f"sent {analysis_cold_starts} cold starts"
                )
                # Write per-user analysis events
                try:
                    from services.activity_log import write_activity as _aw
                    for uid in user_ids:
                        await _aw(
                            client=supabase,
                            user_id=uid,
                            event_type="conversation_analyzed",
                            summary=f"Conversation analysis: {analysis_suggestions} suggestion(s) created",
                            metadata={
                                "users_analyzed": analysis_users,
                                "suggestions_created": analysis_suggestions,
                                "cold_starts_sent": analysis_cold_starts,
                            },
                        )
                except Exception:
                    pass

        except Exception as e:
            logger.warning(f"[ANALYSIS] Analysis phase skipped: {e}")

    # -------------------------------------------------------------------------
    # Memory Extraction + Session Summaries (ADR-064, ADR-067 Phase 1)
    # Process yesterday's sessions — only run at midnight UTC
    # -------------------------------------------------------------------------
    memory_users = 0
    memory_extracted = 0
    summaries_written = 0
    if now.hour == 0 and now.minute < 5:  # Only in first 5 minutes of midnight UTC
        try:
            from services.memory import process_conversation, generate_session_summary

            # Get sessions from yesterday
            yesterday = (now - timedelta(days=1)).date().isoformat()
            today = now.date().isoformat()

            sessions_result = (
                supabase.table("chat_sessions")
                .select("id, user_id, created_at")
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
                        .select("role, content")
                        .eq("session_id", session_id)
                        .order("sequence_number")
                        .execute()
                    )
                    messages = messages_result.data or []
                    user_msg_count = len([m for m in messages if m.get("role") == "user"])

                    if user_msg_count >= 3:
                        # Memory extraction (ADR-064)
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
                except Exception:
                    pass

        except Exception as e:
            logger.warning(f"[MEMORY] Memory extraction phase skipped: {e}")

    # -------------------------------------------------------------------------
    # ADR-064: Activity Pattern Detection (daily at midnight UTC)
    # Analyzes activity_log for behavioral patterns and writes to user_context
    # -------------------------------------------------------------------------
    pattern_users = 0
    pattern_extracted = 0

    if now.hour == 0 and now.minute < 5:
        try:
            from services.memory import process_patterns

            # Get users with recent activity (bounded — pattern detection only useful for active users)
            since_patterns = (now - timedelta(days=14)).isoformat()
            users_result = (
                supabase.table("activity_log")
                .select("user_id")
                .gte("created_at", since_patterns)
                .limit(200)
                .execute()
            )
            # Deduplicate
            _pattern_user_ids = list(set(
                row["user_id"] for row in (users_result.data or [])
            ))
            users_result_data = [{"id": uid} for uid in _pattern_user_ids]

            for user_row in users_result_data:
                user_id = user_row["id"]
                try:
                    extracted = await process_patterns(
                        client=supabase,
                        user_id=user_id,
                    )
                    if extracted > 0:
                        pattern_extracted += extracted
                        pattern_users += 1
                except Exception as e:
                    logger.warning(f"[PATTERN] Error detecting patterns for {user_id}: {e}")

            if pattern_users > 0:
                logger.info(
                    f"[PATTERN] Activity pattern detection complete: {pattern_users} users, "
                    f"{pattern_extracted} patterns extracted"
                )
                # Write per-user pattern events
                try:
                    from services.activity_log import write_activity as _pw
                    for user_row in users_result_data:
                        await _pw(
                            client=supabase,
                            user_id=user_row["id"],
                            event_type="pattern_detected",
                            summary=f"Pattern detection: {pattern_extracted} pattern(s) found",
                            metadata={
                                "patterns_extracted": pattern_extracted,
                                "users_analyzed": pattern_users,
                            },
                        )
                except Exception:
                    pass

        except Exception as e:
            logger.warning(f"[PATTERN] Activity pattern detection phase skipped: {e}")

    # -------------------------------------------------------------------------
    # ADR-068 Phase 4: Split Signal Processing
    # - Calendar signals (hourly): Time-sensitive meeting prep briefs
    # - Other signals (hourly): Gmail, Slack, Notion signals
    # Cost gate: Only runs for users with active platform connections.
    # -------------------------------------------------------------------------
    signal_users = 0
    signal_created = 0
    signal_daily_users = 0
    signal_daily_created = 0

    if now.minute < 5:
        try:
            from services.signal_extraction import extract_signal_summary
            from services.signal_processing import process_signal, execute_signal_actions
            from services.activity_log import get_recent_activity

            # Get users with active platform connections (cost gate)
            active_result = (
                supabase.table("platform_connections")
                .select("user_id")
                .eq("status", "active")
                .execute()
            )
            active_user_ids = list(set(
                row["user_id"] for row in (active_result.data or [])
            ))

            logger.info(f"[SIGNAL] Signal check: {len(active_user_ids)} users with active platforms")

            # ADR-053: Filter out free-tier users (signal processing requires Starter+)
            from services.platform_limits import get_user_tier
            paid_user_ids = []
            for uid in active_user_ids:
                tier = get_user_tier(supabase, uid)
                if tier != "free":
                    paid_user_ids.append(uid)
                else:
                    logger.debug(f"[SIGNAL] Skipping free-tier user {uid}")

            if len(paid_user_ids) < len(active_user_ids):
                logger.info(
                    f"[SIGNAL] Tier gate: {len(paid_user_ids)}/{len(active_user_ids)} users eligible (Starter+)"
                )

            # Run both signal phases per user (calendar + non_calendar)
            for user_id in paid_user_ids:
                for signals_filter, label in [("calendar_only", "calendar"), ("non_calendar", "daily")]:
                    try:
                        signal_summary = await extract_signal_summary(
                            supabase, user_id, signals_filter=signals_filter
                        )

                        if not signal_summary.has_signals:
                            continue

                        # Fetch context for reasoning
                        user_context_result = (
                            supabase.table("user_context")
                            .select("key, value")
                            .eq("user_id", user_id)
                            .limit(20)
                            .execute()
                        )
                        user_context = user_context_result.data or []

                        recent_activity = await get_recent_activity(
                            client=supabase,
                            user_id=user_id,
                            limit=10,
                            days=7,
                        )

                        # ADR-069: Fetch Layer 4 content for signal reasoning
                        # Bounded: limit to 5 most recent versions per deliverable
                        existing_deliverables_raw = (
                            supabase.table("deliverables")
                            .select("""
                                id, title, deliverable_type, next_run_at, status,
                                deliverable_versions!inner(
                                    final_content,
                                    draft_content,
                                    created_at,
                                    status
                                )
                            """)
                            .eq("user_id", user_id)
                            .in_("status", ["active", "paused"])
                            .limit(20)
                            .execute()
                        )

                        # Extract most recent version per deliverable (sort versions client-side)
                        existing_deliverables = []
                        for d in (existing_deliverables_raw.data or []):
                            versions = sorted(
                                d.get("deliverable_versions", []),
                                key=lambda v: v.get("created_at", ""),
                                reverse=True,
                            )
                            recent_version = versions[0] if versions else None
                            existing_deliverables.append({
                                "id": d["id"],
                                "title": d["title"],
                                "deliverable_type": d["deliverable_type"],
                                "next_run_at": d.get("next_run_at"),
                                "status": d["status"],
                                "recent_content": (
                                    recent_version.get("final_content") or
                                    recent_version.get("draft_content")
                                ) if recent_version else None,
                                "recent_version_date": recent_version.get("created_at") if recent_version else None,
                            })

                        # Single LLM call — reason over signals
                        processing_result = await process_signal(
                            client=supabase,
                            user_id=user_id,
                            signal_summary=signal_summary,
                            user_context=user_context,
                            recent_activity=recent_activity,
                            existing_deliverables=existing_deliverables,
                        )

                        if processing_result.actions:
                            created = await execute_signal_actions(
                                client=supabase,
                                user_id=user_id,
                                result=processing_result,
                            )
                            if label == "calendar":
                                signal_created += created
                                if created > 0:
                                    signal_users += 1
                            else:
                                signal_daily_created += created
                                if created > 0:
                                    signal_daily_users += 1

                            if created > 0:
                                logger.info(
                                    f"[SIGNAL] Created {created} {label} signal deliverable(s) "
                                    f"for {user_id}"
                                )
                        else:
                            # Write signal_processed even when 0 actions so system page shows last run
                            try:
                                from services.activity_log import write_activity as _sw
                                await _sw(
                                    client=supabase,
                                    user_id=user_id,
                                    event_type="signal_processed",
                                    summary=f"Signal processing ({label}): {signal_summary.total_items} item(s), 0 actions",
                                    metadata={"signals_evaluated": signal_summary.total_items, "actions_taken": [], "items_processed": 0},
                                )
                            except Exception:
                                pass

                    except Exception as e:
                        logger.warning(f"[SIGNAL] Error processing {label} signals for {user_id}: {e}")

            total_su = signal_users + signal_daily_users
            total_sc = signal_created + signal_daily_created
            if total_su > 0:
                logger.info(
                    f"[SIGNAL] Signal phase complete: {total_su} users, "
                    f"{total_sc} deliverables created"
                )

        except Exception as e:
            logger.warning(f"[SIGNAL] Signal processing skipped: {e}")

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    deliverable_summary = f"{deliverable_success}/{len(deliverables)}"
    if deliverable_skipped > 0:
        deliverable_summary += f" ({deliverable_skipped} skipped)"

    summary_parts = [
        f"deliverables={deliverable_summary}",
        f"work={work_success}/{len(work_items)}",
        f"digests={digest_success}/{digest_count}",
        f"imports={import_success}/{import_count}",
    ]
    if analysis_users > 0 or analysis_suggestions > 0:
        summary_parts.append(f"analysis={analysis_suggestions} suggestions from {analysis_users} users")
    if memory_extracted > 0:
        summary_parts.append(f"memory={memory_extracted} from {memory_users} sessions")
    if signal_users > 0 or signal_daily_users > 0:
        total_signal_created = signal_created + signal_daily_created
        total_signal_users = signal_users + signal_daily_users
        summary_parts.append(f"signals={total_signal_created} from {total_signal_users} users")

    # -------------------------------------------------------------------------
    # ADR-072: Write scheduler_heartbeat event for system state awareness
    # -------------------------------------------------------------------------
    errors_encountered: list[str] = []
    # Note: Errors are already logged inline; heartbeat captures aggregate counts

    try:
        from services.activity_log import write_activity

        # Build heartbeat summary
        total_checked = len(deliverables) + len(work_items) + digest_count + import_count
        total_triggered = deliverable_success + work_success + digest_success + import_success

        heartbeat_summary = f"Scheduler cycle: {total_triggered}/{total_checked} items processed"

        # Write per-user heartbeat for all users with active connections
        # so the system page can show scheduler status per user
        heartbeat_metadata = {
            "deliverables_checked": len(deliverables),
            "deliverables_triggered": deliverable_success,
            "deliverables_skipped": deliverable_skipped,
            "work_checked": len(work_items),
            "work_triggered": work_success,
            "digests_checked": digest_count,
            "digests_triggered": digest_success,
            "imports_checked": import_count,
            "imports_triggered": import_success,
            "signals_created": signal_created + signal_daily_created,
            "memory_extracted": memory_extracted,
            "analysis_suggestions": analysis_suggestions,
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
