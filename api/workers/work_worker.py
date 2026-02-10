"""
Background Work Worker (ADR-039: Background Work Agents)

Worker entry point for background work execution.
Called by RQ when jobs are dequeued.

This module runs in a separate worker process, not the API server.
It uses the service role key for database access.

Usage:
    # Via RQ
    rq worker work --url $REDIS_URL

    # The worker picks up jobs enqueued by job_queue.py
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from supabase import create_client

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s] %(message)s"
)
logger = logging.getLogger(__name__)


def execute_work_background(
    ticket_id: str,
    user_id: str,
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None,
) -> dict:
    """
    Background worker entry point for work execution.

    This function is called by RQ when a job is dequeued.
    It wraps the async execution in an event loop.

    Args:
        ticket_id: Work ticket ID to execute
        user_id: User ID who owns the ticket
        supabase_url: Supabase URL (uses env var if not provided)
        supabase_key: Service role key (uses env var if not provided)

    Returns:
        Dict with execution result
    """
    logger.info(f"[WORKER] Starting background execution: ticket={ticket_id}")

    # Run the async execution
    result = asyncio.run(_execute_work_async(
        ticket_id=ticket_id,
        user_id=user_id,
        supabase_url=supabase_url or os.environ.get("SUPABASE_URL"),
        supabase_key=supabase_key or os.environ.get("SUPABASE_SERVICE_ROLE_KEY"),
    ))

    logger.info(f"[WORKER] Completed: ticket={ticket_id}, success={result.get('success')}")
    return result


async def _execute_work_async(
    ticket_id: str,
    user_id: str,
    supabase_url: str,
    supabase_key: str,
) -> dict:
    """
    Async implementation of background work execution.

    Args:
        ticket_id: Work ticket ID
        user_id: User ID
        supabase_url: Supabase URL
        supabase_key: Service role key

    Returns:
        Dict with execution result
    """
    from services.job_queue import (
        log_execution_event,
        update_ticket_progress,
    )

    # Create Supabase client with service role
    if not supabase_url or not supabase_key:
        logger.error("[WORKER] Missing Supabase credentials")
        return {
            "success": False,
            "error": "Missing Supabase credentials",
        }

    client = create_client(supabase_url, supabase_key)

    # Log start
    await log_execution_event(
        client, ticket_id, "started",
        "Background execution started by worker"
    )

    try:
        # Update status to running
        client.table("work_tickets").update({
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", ticket_id).execute()

        # Update progress
        await update_ticket_progress(
            client, ticket_id,
            stage="initializing",
            percent=10,
            message="Loading context and preparing agent..."
        )

        # Import here to avoid circular imports
        from services.work_execution import execute_work_ticket

        # Execute with progress callback
        async def on_progress(stage: str, message: str, percent: int = 50):
            await update_ticket_progress(client, ticket_id, stage, percent, message)
            await log_execution_event(client, ticket_id, "progress", message)

        # Note: Current execute_work_ticket doesn't support on_progress callback
        # We'll add that in the next step. For now, just execute directly.
        result = await execute_work_ticket(
            client=client,
            user_id=user_id,
            ticket_id=ticket_id,
        )

        # Update final progress
        if result.get("success"):
            await update_ticket_progress(
                client, ticket_id,
                stage="completed",
                percent=100,
                message="Work completed successfully"
            )
            await log_execution_event(
                client, ticket_id, "completed",
                f"Execution completed in {result.get('execution_time_ms', 0)}ms"
            )
        else:
            await log_execution_event(
                client, ticket_id, "failed",
                result.get("error", "Unknown error")
            )

        return result

    except Exception as e:
        logger.error(f"[WORKER] Execution failed: {e}", exc_info=True)

        # Update ticket status
        try:
            client.table("work_tickets").update({
                "status": "failed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "error_message": str(e),
            }).eq("id", ticket_id).execute()

            await log_execution_event(
                client, ticket_id, "failed",
                str(e),
                metadata={"exception_type": type(e).__name__}
            )
        except Exception as update_error:
            logger.error(f"[WORKER] Failed to update ticket status: {update_error}")

        return {
            "success": False,
            "error": str(e),
            "ticket_id": ticket_id,
        }


# For direct execution (development/testing)
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python -m workers.work_worker <ticket_id> <user_id>")
        sys.exit(1)

    ticket_id = sys.argv[1]
    user_id = sys.argv[2]

    result = execute_work_background(ticket_id, user_id)
    print(f"Result: {result}")
