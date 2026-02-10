"""
Job Queue Service (ADR-039: Background Work Agents)

Provides Redis-backed job queue for background work execution.
Uses RQ (Redis Queue) for reliable async job processing.

Architecture:
- Jobs are enqueued with ticket_id and auth context
- Worker processes pick up jobs from the queue
- Progress is tracked in Supabase (source of truth)
- RQ handles retries and failure recovery

Usage:
    from services.job_queue import enqueue_work, get_queue_status

    # Enqueue work for background processing
    job_id = await enqueue_work(ticket_id, user_id)

    # Check queue health
    status = get_queue_status()
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)

# Redis connection settings
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

# Queue configuration
WORK_QUEUE_NAME = "work"
JOB_TIMEOUT_SECONDS = 600  # 10 minutes max per job
JOB_RESULT_TTL_SECONDS = 86400  # Keep results for 24 hours

# Optional: Set to True to gracefully handle missing Redis
REDIS_OPTIONAL = os.environ.get("REDIS_OPTIONAL", "false").lower() == "true"

# Lazy-loaded Redis connection and queue
_redis_conn = None
_work_queue = None


def _get_redis_connection():
    """Get or create Redis connection (lazy initialization)."""
    global _redis_conn

    if _redis_conn is not None:
        return _redis_conn

    try:
        import redis
        _redis_conn = redis.from_url(REDIS_URL)
        # Test connection
        _redis_conn.ping()
        logger.info(f"Connected to Redis at {REDIS_URL[:30]}...")
        return _redis_conn
    except ImportError:
        logger.warning("redis package not installed - background jobs disabled")
        return None
    except Exception as e:
        if REDIS_OPTIONAL:
            logger.warning(f"Redis not available (optional): {e}")
            return None
        raise


def _get_work_queue():
    """Get or create the work queue (lazy initialization)."""
    global _work_queue

    if _work_queue is not None:
        return _work_queue

    conn = _get_redis_connection()
    if conn is None:
        return None

    try:
        from rq import Queue
        _work_queue = Queue(WORK_QUEUE_NAME, connection=conn)
        return _work_queue
    except ImportError:
        logger.warning("rq package not installed - background jobs disabled")
        return None


def is_queue_available() -> bool:
    """Check if the job queue is available and connected."""
    try:
        queue = _get_work_queue()
        return queue is not None
    except Exception:
        return False


async def enqueue_work(
    ticket_id: str,
    user_id: str,
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None,
) -> Optional[str]:
    """
    Add work to background queue.

    The worker will use service key for execution, so we pass
    user_id for context but don't need user's auth token.

    Args:
        ticket_id: Work ticket ID to execute
        user_id: User ID who owns the ticket
        supabase_url: Optional Supabase URL (uses env var if not provided)
        supabase_key: Optional service key (uses env var if not provided)

    Returns:
        Job ID if enqueued, None if queue not available
    """
    queue = _get_work_queue()
    if queue is None:
        logger.warning("Job queue not available - cannot enqueue work")
        return None

    try:
        from rq import Retry

        job = queue.enqueue(
            "workers.work_worker.execute_work_background",
            args=(ticket_id, user_id),
            kwargs={
                "supabase_url": supabase_url or os.environ.get("SUPABASE_URL"),
                "supabase_key": supabase_key or os.environ.get("SUPABASE_SERVICE_ROLE_KEY"),
            },
            job_timeout=JOB_TIMEOUT_SECONDS,
            result_ttl=JOB_RESULT_TTL_SECONDS,
            retry=Retry(max=2, interval=[30, 60]),  # Retry twice with backoff
            description=f"work:{ticket_id[:8]}",
        )

        logger.info(f"Enqueued work ticket {ticket_id} as job {job.id}")
        return job.id

    except Exception as e:
        logger.error(f"Failed to enqueue work {ticket_id}: {e}")
        return None


def get_job_status(job_id: str) -> dict:
    """
    Get status of a queued job from RQ.

    Args:
        job_id: RQ job ID

    Returns:
        Dict with status, result, and error info
    """
    queue = _get_work_queue()
    if queue is None:
        return {"status": "queue_unavailable"}

    try:
        job = queue.fetch_job(job_id)
        if job is None:
            return {"status": "not_found"}

        status = job.get_status()

        result = {
            "status": status,
            "job_id": job_id,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None,
        }

        if status == "finished":
            result["result"] = job.result
        elif status == "failed":
            result["error"] = str(job.exc_info) if job.exc_info else "Unknown error"

        return result

    except Exception as e:
        logger.error(f"Failed to get job status {job_id}: {e}")
        return {"status": "error", "error": str(e)}


def get_queue_status() -> dict:
    """
    Get overall queue health and statistics.

    Returns:
        Dict with queue counts and health info
    """
    queue = _get_work_queue()
    if queue is None:
        return {
            "available": False,
            "reason": "Queue not configured or Redis unavailable",
        }

    try:
        from rq.registry import FailedJobRegistry, StartedJobRegistry

        conn = _get_redis_connection()
        failed_registry = FailedJobRegistry(queue=queue, connection=conn)
        started_registry = StartedJobRegistry(queue=queue, connection=conn)

        return {
            "available": True,
            "queue_name": WORK_QUEUE_NAME,
            "pending_jobs": len(queue),
            "running_jobs": len(started_registry),
            "failed_jobs": len(failed_registry),
            "job_timeout_seconds": JOB_TIMEOUT_SECONDS,
        }

    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        return {
            "available": False,
            "error": str(e),
        }


async def update_ticket_queue_status(
    client,
    ticket_id: str,
    job_id: str,
) -> None:
    """
    Update ticket with queue info after enqueuing.

    Args:
        client: Supabase client
        ticket_id: Work ticket ID
        job_id: RQ job ID
    """
    try:
        client.table("work_tickets").update({
            "status": "queued",
            "execution_mode": "background",
            "job_id": job_id,
            "queued_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", ticket_id).execute()

        logger.info(f"Updated ticket {ticket_id} with job_id {job_id}")

    except Exception as e:
        logger.error(f"Failed to update ticket queue status: {e}")


async def log_execution_event(
    client,
    ticket_id: str,
    stage: str,
    message: str,
    metadata: Optional[dict] = None,
) -> None:
    """
    Log an execution event for debugging.

    Args:
        client: Supabase client
        ticket_id: Work ticket ID
        stage: Event stage (queued, started, progress, completed, failed)
        message: Human-readable message
        metadata: Optional additional data
    """
    try:
        client.table("work_execution_log").insert({
            "ticket_id": ticket_id,
            "stage": stage,
            "message": message,
            "metadata": metadata or {},
        }).execute()

    except Exception as e:
        # Don't fail the job for logging errors
        logger.warning(f"Failed to log execution event: {e}")


async def update_ticket_progress(
    client,
    ticket_id: str,
    stage: str,
    percent: int,
    message: str,
) -> None:
    """
    Update ticket progress for UI display.

    Args:
        client: Supabase client
        ticket_id: Work ticket ID
        stage: Current stage name
        percent: Progress percentage (0-100)
        message: Status message
    """
    try:
        progress = {
            "stage": stage,
            "percent": min(100, max(0, percent)),
            "message": message,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        client.table("work_tickets").update({
            "progress": progress,
        }).eq("id", ticket_id).execute()

    except Exception as e:
        logger.warning(f"Failed to update ticket progress: {e}")
