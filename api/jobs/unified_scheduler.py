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
    send_deliverable_ready_email,
    send_deliverable_failed_email,
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
        target_day = days.index(day.lower()) if day.lower() in days else 0
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
        target_day = days.index(day.lower()) if day.lower() in days else 0
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
        target_day = days.index(day.lower()) if day.lower() in days else 0
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
        .select("id, user_id, title, deliverable_type, type_config, schedule, sources, recipient_context, last_run_at")
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
    from services.ephemeral_context import has_fresh_context_since

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

    # Check for fresh context
    try:
        has_fresh, count = await has_fresh_context_since(
            db_client=supabase_client,
            user_id=deliverable["user_id"],
            deliverable_sources=sources,
            since=last_run_at,
        )

        if not has_fresh:
            return True, "No new context since last run"

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

    deliverable_id = deliverable["id"]
    user_id = deliverable["user_id"]
    title = deliverable["title"]
    deliverable_type = deliverable["deliverable_type"]
    schedule = deliverable.get("schedule", {})

    logger.info(f"[DELIVERABLE] Processing: {title} ({deliverable_id})")

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

        # 4. Send email notification
        if await should_send_email(supabase_client, user_id, "deliverable_ready"):
            user_email = await get_user_email(supabase_client, user_id)
            if user_email:
                if success:
                    await send_deliverable_ready_email(
                        to=user_email,
                        deliverable_title=title,
                        deliverable_id=deliverable_id,
                        deliverable_type=deliverable_type,
                        schedule_description=format_schedule_description(schedule),
                        next_run_at=next_run.isoformat(),
                    )
                    logger.info(f"[DELIVERABLE] ✓ Sent ready email to {user_email}")
                else:
                    error_msg = result.get("error", "Unknown error during generation")
                    await send_deliverable_failed_email(
                        to=user_email,
                        deliverable_title=title,
                        deliverable_id=deliverable_id,
                        error_message=error_msg,
                    )
                    logger.info(f"[DELIVERABLE] ✓ Sent failure email to {user_email}")

        if success:
            logger.info(f"[DELIVERABLE] ✓ Complete: {title}")
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

        # Send failure email
        try:
            if await should_send_email(supabase_client, user_id, "deliverable_failed"):
                user_email = await get_user_email(supabase_client, user_id)
                if user_email:
                    await send_deliverable_failed_email(
                        to=user_email,
                        deliverable_title=title,
                        deliverable_id=deliverable_id,
                        error_message=str(e),
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
    # ADR-031: Cleanup Expired Ephemeral Context (hourly)
    # -------------------------------------------------------------------------
    ephemeral_cleaned = 0
    if now.minute < 5:  # Only run cleanup in first 5 minutes of each hour
        try:
            from services.ephemeral_context import cleanup_expired_context
            ephemeral_cleaned = await cleanup_expired_context(supabase)
            if ephemeral_cleaned > 0:
                logger.info(f"[EPHEMERAL] Cleaned up {ephemeral_cleaned} expired entries")
        except Exception as e:
            logger.warning(f"[EPHEMERAL] Cleanup failed (non-fatal): {e}")

    # -------------------------------------------------------------------------
    # ADR-031 Phase 4: Cleanup Expired Event Trigger Cooldowns (hourly)
    # -------------------------------------------------------------------------
    cooldowns_cleaned = 0
    if now.minute < 5:  # Only run cleanup in first 5 minutes of each hour
        try:
            from services.event_triggers import cleanup_expired_cooldowns
            cooldowns_cleaned = cleanup_expired_cooldowns()
            if cooldowns_cleaned > 0:
                logger.info(f"[COOLDOWN] Cleaned up {cooldowns_cleaned} expired entries")
        except Exception as e:
            logger.warning(f"[COOLDOWN] Cleanup failed (non-fatal): {e}")

    # -------------------------------------------------------------------------
    # Process Integration Import Jobs (ADR-027)
    # -------------------------------------------------------------------------
    # First, recover any stale processing jobs (safety net for crashed processes)
    recovered_count = await recover_stale_processing_jobs(supabase, stale_minutes=10)
    if recovered_count > 0:
        logger.info(f"[IMPORT] Recovered {recovered_count} stale job(s)")

    import_jobs = await get_pending_import_jobs(supabase)
    import_count = len(import_jobs)
    logger.info(f"[IMPORT] Found {import_count} pending import job(s)")

    import_success = 0
    for job in import_jobs:
        try:
            if await process_import_job(supabase, job):
                import_success += 1
        except Exception as e:
            logger.error(f"[IMPORT] Unexpected error for job {job.get('id')}: {e}")

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    deliverable_summary = f"{deliverable_success}/{len(deliverables)}"
    if deliverable_skipped > 0:
        deliverable_summary += f" ({deliverable_skipped} skipped)"

    logger.info(
        f"Completed: "
        f"deliverables={deliverable_summary}, "
        f"work={work_success}/{len(work_items)}, "
        f"digests={digest_success}/{digest_count}, "
        f"imports={import_success}/{import_count}"
    )


if __name__ == "__main__":
    asyncio.run(run_unified_scheduler())
