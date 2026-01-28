"""
YARNNN v5 - Digest Scheduler

Run hourly via Render cron:
  schedule: "0 * * * *"
  command: python -m api.jobs.scheduler

Flow:
1. Query workspaces due for digest (matches day + hour in their timezone)
2. For each workspace, gather activity and generate digest
3. Send email via Resend
4. Record in scheduled_messages
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from .digest import generate_digest_content, DigestContent
from .email import send_email, EmailResult


async def get_workspaces_due_for_digest(supabase_client) -> list[dict]:
    """
    Query workspaces that are due for their weekly digest.
    Uses the get_workspaces_due_for_digest database function.
    """
    now = datetime.now(timezone.utc)

    result = supabase_client.rpc(
        "get_workspaces_due_for_digest",
        {"check_time": now.isoformat()}
    ).execute()

    return result.data or []


async def create_scheduled_message(
    supabase_client,
    workspace_id: UUID,
    recipient_email: str,
    content: DigestContent,
) -> UUID:
    """Create a scheduled_message record for tracking."""
    now = datetime.now(timezone.utc)

    result = supabase_client.table("scheduled_messages").insert({
        "workspace_id": str(workspace_id),
        "scheduled_for": now.isoformat(),
        "message_type": "weekly_digest",
        "subject": content.subject,
        "content": content.to_dict(),
        "recipient_email": recipient_email,
        "status": "pending",
    }).execute()

    return UUID(result.data[0]["id"])


async def mark_message_sent(
    supabase_client,
    message_id: UUID,
    success: bool,
    failure_reason: Optional[str] = None,
):
    """Update scheduled_message status after send attempt."""
    now = datetime.now(timezone.utc)

    update_data = {
        "status": "sent" if success else "failed",
        "sent_at": now.isoformat() if success else None,
        "failure_reason": failure_reason,
    }

    supabase_client.table("scheduled_messages").update(update_data).eq(
        "id", str(message_id)
    ).execute()


async def process_workspace_digest(
    supabase_client,
    workspace_id: UUID,
    owner_email: str,
    workspace_name: str,
) -> bool:
    """
    Generate and send digest for a single workspace.
    Returns True if successful.
    """
    # Generate digest content
    content = await generate_digest_content(
        supabase_client,
        workspace_id,
        workspace_name,
    )

    # Skip if no activity
    if content.is_empty:
        # Optionally record as "skipped" for transparency
        return True

    # Create tracking record
    message_id = await create_scheduled_message(
        supabase_client,
        workspace_id,
        owner_email,
        content,
    )

    # Send email
    result = await send_email(
        to=owner_email,
        subject=content.subject,
        html=content.html,
        text=content.text,
    )

    # Update status
    await mark_message_sent(
        supabase_client,
        message_id,
        success=result.success,
        failure_reason=result.error,
    )

    return result.success


async def run_scheduler():
    """
    Main scheduler entry point.
    Called by Render cron every hour.
    """
    from supabase import create_client

    # Initialize Supabase client (service role for admin access)
    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting digest scheduler...")

    # Get workspaces due for digest
    workspaces = await get_workspaces_due_for_digest(supabase)
    print(f"Found {len(workspaces)} workspace(s) due for digest")

    # Process each workspace
    success_count = 0
    for ws in workspaces:
        try:
            success = await process_workspace_digest(
                supabase,
                workspace_id=UUID(ws["workspace_id"]),
                owner_email=ws["owner_email"],
                workspace_name=ws["workspace_name"],
            )
            if success:
                success_count += 1
                print(f"  ✓ Sent digest for workspace: {ws['workspace_name']}")
            else:
                print(f"  ✗ Failed to send digest for: {ws['workspace_name']}")
        except Exception as e:
            print(f"  ✗ Error processing {ws['workspace_name']}: {e}")

    print(f"Completed: {success_count}/{len(workspaces)} digests sent")


if __name__ == "__main__":
    asyncio.run(run_scheduler())
