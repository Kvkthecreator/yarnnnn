"""
Activity Log — ADR-063: Four-Layer Model + ADR-072: System State Awareness

Append-only system provenance log. Records what YARNNN has done across all pipelines.

Layer: Activity (between Memory and Context in the four-layer model)
Table: activity_log

Write points (all non-fatal — callers continue regardless of log failure):
  - deliverable_execution.py: 'deliverable_run' after version created
  - routes/deliverables.py: 'deliverable_approved' / 'deliverable_rejected' on version status change
  - platform_worker.py: 'platform_synced' after sync batch completes
  - routes/integrations.py: 'integration_connected' / 'integration_disconnected' on OAuth lifecycle
  - TP memory tools: 'memory_written' after user_context upsert
  - chat.py: 'chat_session' when session ends
  - signal_processing.py: 'signal_processed' after signal reasoning pass (ADR-072)
  - unified_scheduler.py: 'deliverable_scheduled' when deliverable queued (ADR-072)
  - unified_scheduler.py: 'deliverable_generated' after successful deliverable generation
  - unified_scheduler.py: 'scheduler_heartbeat' on each execution cycle (ADR-072)
  - unified_scheduler.py: 'content_cleanup' after expired content deletion
  - unified_scheduler.py: 'session_summary_written' after session summary generation
  - unified_scheduler.py: 'pattern_detected' after activity pattern detection
  - unified_scheduler.py: 'conversation_analyzed' after conversation analysis

Read points:
  - working_memory.py: get_recent_activity() → injected as "Recent activity" block
    in TP system prompt (~300 tokens, last 10 events, 7-day window)
  - system_state.py: Aggregates operational state for TP GetSystemState primitive (ADR-072)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

VALID_EVENT_TYPES = frozenset({
    "deliverable_run",
    "deliverable_approved",
    "deliverable_rejected",
    "deliverable_scheduled",    # ADR-072: System state awareness - queued for execution
    "deliverable_generated",    # Deliverable content actually generated (distinct from scheduled)
    "memory_written",
    "platform_synced",
    "integration_connected",
    "integration_disconnected",
    "chat_session",
    "signal_processed",         # ADR-072: System state awareness - signal reasoning pass
    "scheduler_heartbeat",      # ADR-072: System state awareness - scheduler execution cycle
    "content_cleanup",          # Expired platform_content cleaned up
    "session_summary_written",  # Session compaction summaries generated
    "pattern_detected",         # Activity pattern detection completed
    "conversation_analyzed",    # Conversation analysis + suggestions created
})


async def write_activity(
    client,
    user_id: str,
    event_type: str,
    summary: str,
    event_ref: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Optional[str]:
    """
    Append an event to activity_log.

    Non-fatal by design — a log failure never blocks the primary operation.
    Callers should wrap in try/except and continue regardless.

    Args:
        client: Supabase service-role client
        user_id: The user this event belongs to
        event_type: One of 'deliverable_run', 'deliverable_approved', 'deliverable_rejected',
            'memory_written', 'platform_synced', 'integration_connected',
            'integration_disconnected', 'chat_session'
        summary: Human-readable one-liner (shown in working memory block)
        event_ref: UUID of related record (version_id, session_id, etc.) — optional
        metadata: Structured detail dict — optional

    Returns:
        activity_log row id, or None on error
    """
    if event_type not in VALID_EVENT_TYPES:
        logger.warning(f"[activity_log] Unknown event_type ignored: {event_type!r}")
        return None

    row: dict = {
        "user_id": user_id,
        "event_type": event_type,
        "summary": summary,
    }
    if event_ref is not None:
        row["event_ref"] = str(event_ref)
    if metadata is not None:
        row["metadata"] = metadata

    try:
        result = client.table("activity_log").insert(row).execute()
        inserted = result.data[0] if result.data else {}
        return inserted.get("id")
    except Exception as e:
        logger.error(f"[activity_log] write failed (event_type={event_type}): {e}")
        return None


async def get_recent_activity(
    client,
    user_id: str,
    limit: int = 10,
    days: int = 7,
) -> list[dict]:
    """
    Fetch recent activity events for working memory injection.

    Args:
        client: Supabase client (anon or service role)
        user_id: The user
        limit: Max rows to return (default 10)
        days: Lookback window in days (default 7)

    Returns:
        List of activity_log rows ordered by created_at DESC.
        Fields: event_type, event_ref, summary, metadata, created_at
    """
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    try:
        result = (
            client.table("activity_log")
            .select("event_type, event_ref, summary, metadata, created_at")
            .eq("user_id", user_id)
            .gte("created_at", since)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"[activity_log] get_recent_activity failed: {e}")
        return []
