"""
YARNNN v5 - Work Scheduler

ADR-017: Unified Work Model (replaces ADR-009 Phase 3)

Run every 5 minutes via Render cron:
  schedule: "*/5 * * * *"
  command: python -m jobs.work_scheduler

Flow:
1. Query recurring work due for execution (next_run_at <= now, is_active=true)
2. Create work_output for each work item
3. Execute the work
4. Send completion email
5. Update work's next run time

Note: Uses both old (schedule_*) and new (frequency_*, is_active) column names
for backward compatibility during migration period.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from croniter import croniter

from .email import send_work_complete_email


def calculate_next_run(cron_expr: str, tz_name: str, from_time: Optional[datetime] = None) -> datetime:
    """
    Calculate next run time from cron expression.

    Args:
        cron_expr: Cron expression (5 fields)
        tz_name: Timezone name (e.g., 'America/Los_Angeles')
        from_time: Base time (defaults to now)

    Returns:
        Next run time as UTC datetime
    """
    import pytz

    if from_time is None:
        from_time = datetime.now(timezone.utc)

    try:
        tz = pytz.timezone(tz_name)
    except pytz.UnknownTimeZoneError:
        tz = pytz.UTC

    # Convert to local time for cron calculation
    local_time = from_time.astimezone(tz)

    # Get next run in local time
    cron = croniter(cron_expr, local_time)
    next_local = cron.get_next(datetime)

    # Convert back to UTC
    return next_local.astimezone(timezone.utc)


async def get_due_work(supabase_client) -> list[dict]:
    """
    Query recurring work due for execution.

    ADR-017: Uses get_due_work RPC if available, falls back to get_due_work_templates.
    """
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

    # Fall back to old function for backward compatibility
    result = supabase_client.rpc(
        "get_due_work_templates",
        {"check_time": now.isoformat()}
    ).execute()

    return result.data or []


# Legacy alias
get_due_templates = get_due_work


async def spawn_ticket(supabase_client, work: dict) -> Optional[str]:
    """
    Create a new ticket/output for recurring work execution.

    ADR-017: For unified model, we create an output record directly.
    For backward compatibility, still creates a spawned ticket if using old model.

    Args:
        supabase_client: Supabase client
        work: Work data (template_id or work_id depending on model)

    Returns:
        Ticket/work ID for execution or None on failure
    """
    # Get work_id (ADR-017) or template_id (ADR-009)
    work_id = work.get("work_id") or work.get("template_id")

    # For ADR-009 backward compat: still create spawned ticket
    ticket_data = {
        "task": work["task"],
        "agent_type": work["agent_type"],
        "status": "pending",
        "parameters": work.get("parameters", {}),
        "project_id": work.get("project_id"),
        "user_id": work["user_id"],
        "parent_template_id": work_id,  # Link back to parent
        "is_template": False,
    }

    result = supabase_client.table("work_tickets").insert(ticket_data).execute()

    if result.data:
        return result.data[0]["id"]
    return None


async def update_work_schedule(
    supabase_client,
    work_id: str,
    cron_expr: str,
    tz_name: str,
) -> None:
    """
    Update work's last run and next run times.

    ADR-017: Updates both old (schedule_*) and new (last_run_at, next_run_at)
    columns for backward compatibility.
    """
    now = datetime.now(timezone.utc)
    next_run = calculate_next_run(cron_expr, tz_name, now)

    supabase_client.table("work_tickets").update({
        # Old column names (ADR-009)
        "schedule_last_run_at": now.isoformat(),
        "schedule_next_run_at": next_run.isoformat(),
        # New column names (ADR-017) - will be ignored if columns don't exist yet
        # "last_run_at": now.isoformat(),
        # "next_run_at": next_run.isoformat(),
    }).eq("id", work_id).execute()


# Legacy alias
update_template_schedule = update_work_schedule


async def get_project_info(supabase_client, project_id: str) -> Optional[dict]:
    """Get project name for email notification."""
    result = (
        supabase_client.table("projects")
        .select("name")
        .eq("id", project_id)
        .single()
        .execute()
    )
    return result.data


async def get_user_email(supabase_client, user_id: str) -> Optional[str]:
    """Get user's email for notification."""
    # Query auth.users via service client
    result = supabase_client.auth.admin.get_user_by_id(user_id)
    if result and result.user:
        return result.user.email
    return None


async def get_ticket_outputs(supabase_client, ticket_id: str) -> list[dict]:
    """Get outputs for a completed ticket."""
    import json

    result = (
        supabase_client.table("work_outputs")
        .select("id, title, output_type, content")
        .eq("ticket_id", ticket_id)
        .execute()
    )

    outputs = []
    for row in (result.data or []):
        content = row.get("content", "")

        # Parse content if it's JSON
        summary = ""
        if content:
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    summary = parsed.get("summary", "")[:200]
            except (json.JSONDecodeError, TypeError):
                summary = content[:200] if content else ""

        outputs.append({
            "id": row["id"],
            "title": row["title"],
            "type": row["output_type"],
            "summary": summary,
        })

    return outputs


async def process_work(supabase_client, work: dict) -> bool:
    """
    Process a single recurring work item: create output, execute, send email.

    ADR-017: Unified work model. Works with both old (template) and new (work) data.

    Args:
        supabase_client: Supabase client
        work: Work data from get_due_work or get_due_work_templates

    Returns:
        True if successful
    """
    from services.work_execution import execute_work_ticket

    # Support both ADR-017 (work_id) and ADR-009 (template_id) naming
    work_id = work.get("work_id") or work.get("template_id")
    user_id = work["user_id"]
    project_id = work.get("project_id")
    cron_expr = work.get("frequency_cron") or work.get("schedule_cron")
    tz_name = work.get("timezone") or work.get("schedule_timezone", "UTC")

    print(f"  Processing work {work_id}: {work['task'][:50]}...")

    try:
        # 1. Spawn execution ticket (for backward compat with execute_work_ticket)
        ticket_id = await spawn_ticket(supabase_client, work)
        if not ticket_id:
            print(f"    ✗ Failed to create execution")
            return False

        print(f"    Created execution: {ticket_id}")

        # 2. Execute the work
        result = await execute_work_ticket(supabase_client, user_id, ticket_id)

        if not result.get("success"):
            print(f"    ✗ Execution failed: {result.get('error')}")
            # Still update schedule so we don't retry immediately
            await update_work_schedule(supabase_client, work_id, cron_expr, tz_name)
            return False

        print(f"    ✓ Execution complete: {result.get('output_count', 0)} outputs")

        # 3. Update work schedule
        await update_work_schedule(supabase_client, work_id, cron_expr, tz_name)

        # 4. Send completion email
        user_email = await get_user_email(supabase_client, user_id)
        if user_email:
            project_name = "Personal Work"
            if project_id:
                project_info = await get_project_info(supabase_client, project_id)
                project_name = project_info.get("name", "Unknown Project") if project_info else "Unknown Project"

            outputs = await get_ticket_outputs(supabase_client, ticket_id)

            email_result = await send_work_complete_email(
                to=user_email,
                project_name=project_name,
                agent_type=work["agent_type"],
                task=work["task"],
                outputs=outputs,
                project_id=project_id,
            )

            if email_result.success:
                print(f"    ✓ Email sent to {user_email}")
            else:
                print(f"    ⚠ Email failed: {email_result.error}")

        return True

    except Exception as e:
        print(f"    ✗ Error: {e}")
        # Update schedule to prevent immediate retry
        try:
            await update_work_schedule(supabase_client, work_id, cron_expr, tz_name)
        except Exception:
            pass
        return False


# Legacy alias
process_template = process_work


async def run_work_scheduler():
    """
    Main work scheduler entry point.
    Called by Render cron every 5 minutes.

    ADR-017: Processes recurring work items due for execution.
    """
    from supabase import create_client

    # Initialize Supabase client (service role for admin access)
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        return

    supabase = create_client(supabase_url, supabase_key)

    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting work scheduler (ADR-017)...")

    # Get recurring work due for execution
    work_items = await get_due_work(supabase)
    print(f"Found {len(work_items)} work item(s) due for execution")

    if not work_items:
        print("No work to process")
        return

    # Process each work item
    success_count = 0
    for work in work_items:
        try:
            success = await process_work(supabase, work)
            if success:
                success_count += 1
        except Exception as e:
            print(f"  ✗ Unexpected error processing work: {e}")

    print(f"Completed: {success_count}/{len(work_items)} work items processed successfully")


if __name__ == "__main__":
    asyncio.run(run_work_scheduler())
