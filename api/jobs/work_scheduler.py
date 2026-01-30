"""
YARNNN v5 - Work Scheduler

ADR-009 Phase 3: Scheduled Work Execution

Run every 5 minutes via Render cron:
  schedule: "*/5 * * * *"
  command: python -m jobs.work_scheduler

Flow:
1. Query work templates due for execution (schedule_next_run_at <= now)
2. For each template, spawn a new ticket
3. Execute the spawned ticket
4. Send completion email
5. Update template's next run time
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


async def get_due_templates(supabase_client) -> list[dict]:
    """
    Query work templates due for execution.
    Uses the get_due_work_templates database function.
    """
    now = datetime.now(timezone.utc)

    result = supabase_client.rpc(
        "get_due_work_templates",
        {"check_time": now.isoformat()}
    ).execute()

    return result.data or []


async def spawn_ticket(supabase_client, template: dict) -> Optional[str]:
    """
    Create a new ticket from a template.

    Args:
        supabase_client: Supabase client
        template: Template data

    Returns:
        New ticket ID or None on failure
    """
    ticket_data = {
        "task": template["task"],
        "agent_type": template["agent_type"],
        "status": "pending",
        "parameters": template.get("parameters", {}),
        "project_id": template["project_id"],
        "user_id": template["user_id"],
        "parent_template_id": template["template_id"],
        "is_template": False,
    }

    result = supabase_client.table("work_tickets").insert(ticket_data).execute()

    if result.data:
        return result.data[0]["id"]
    return None


async def update_template_schedule(
    supabase_client,
    template_id: str,
    cron_expr: str,
    tz_name: str,
) -> None:
    """Update template's last run and next run times."""
    now = datetime.now(timezone.utc)
    next_run = calculate_next_run(cron_expr, tz_name, now)

    supabase_client.table("work_tickets").update({
        "schedule_last_run_at": now.isoformat(),
        "schedule_next_run_at": next_run.isoformat(),
    }).eq("id", template_id).execute()


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


async def process_template(supabase_client, template: dict) -> bool:
    """
    Process a single template: spawn ticket, execute, send email.

    Args:
        supabase_client: Supabase client
        template: Template data from get_due_work_templates

    Returns:
        True if successful
    """
    from services.work_execution import execute_work_ticket

    template_id = template["template_id"]
    user_id = template["user_id"]
    project_id = template["project_id"]
    cron_expr = template["schedule_cron"]
    tz_name = template.get("schedule_timezone", "UTC")

    print(f"  Processing template {template_id}: {template['task'][:50]}...")

    try:
        # 1. Spawn ticket from template
        ticket_id = await spawn_ticket(supabase_client, template)
        if not ticket_id:
            print(f"    ✗ Failed to spawn ticket")
            return False

        print(f"    Created ticket: {ticket_id}")

        # 2. Execute the ticket
        result = await execute_work_ticket(supabase_client, user_id, ticket_id)

        if not result.get("success"):
            print(f"    ✗ Execution failed: {result.get('error')}")
            # Still update template schedule so we don't retry immediately
            await update_template_schedule(supabase_client, template_id, cron_expr, tz_name)
            return False

        print(f"    ✓ Execution complete: {result.get('output_count', 0)} outputs")

        # 3. Update template schedule
        await update_template_schedule(supabase_client, template_id, cron_expr, tz_name)

        # 4. Send completion email
        user_email = await get_user_email(supabase_client, user_id)
        if user_email:
            project_info = await get_project_info(supabase_client, project_id)
            project_name = project_info.get("name", "Unknown Project") if project_info else "Unknown Project"

            outputs = await get_ticket_outputs(supabase_client, ticket_id)

            email_result = await send_work_complete_email(
                to=user_email,
                project_name=project_name,
                agent_type=template["agent_type"],
                task=template["task"],
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
            await update_template_schedule(supabase_client, template_id, cron_expr, tz_name)
        except Exception:
            pass
        return False


async def run_work_scheduler():
    """
    Main work scheduler entry point.
    Called by Render cron every 5 minutes.
    """
    from supabase import create_client

    # Initialize Supabase client (service role for admin access)
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        return

    supabase = create_client(supabase_url, supabase_key)

    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting work scheduler...")

    # Get templates due for execution
    templates = await get_due_templates(supabase)
    print(f"Found {len(templates)} template(s) due for execution")

    if not templates:
        print("No work to process")
        return

    # Process each template
    success_count = 0
    for template in templates:
        try:
            success = await process_template(supabase, template)
            if success:
                success_count += 1
        except Exception as e:
            print(f"  ✗ Unexpected error processing template: {e}")

    print(f"Completed: {success_count}/{len(templates)} templates processed successfully")


if __name__ == "__main__":
    asyncio.run(run_work_scheduler())
