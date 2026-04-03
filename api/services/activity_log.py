"""
Activity Log — ADR-063 Four-Layer Model + ADR-129 Two-Tier Scoping

Append-only system provenance log. Records what YARNNN has done across all pipelines.

Layer: Activity (between Memory and Context in the four-layer model)
Table: activity_log
Scoping: Two-tier (ADR-129) — workspace-level macro + project-level micro via metadata.project_slug

Write points (all non-fatal — callers continue regardless of log failure):
  - agent_execution.py: 'agent_run' after version created
  - routes/agents.py: 'agent_approved' / 'agent_rejected' on version status change
  - routes/integrations.py: 'integration_connected' / 'integration_disconnected' on OAuth lifecycle
  - TP memory tools: 'memory_written' after user_memory upsert
  - chat.py: 'chat_session' when session ends
  - unified_scheduler.py: 'scheduler_heartbeat' on hourly heartbeat writes
  - unified_scheduler.py: 'content_cleanup' kept for legacy cleanup history
  - task_pipeline.py: 'task_executed' after task execution (ADR-141)

Read points:
  - working_memory.py: get_recent_activity() → injected as "Recent activity" block
    in TP system prompt (~300 tokens, last 10 events, 7-day window)
  - system_state.py: Aggregates operational state for TP GetSystemState primitive
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def resolve_agent_project_slug(agent: dict) -> Optional[str]:
    """
    Stub — projects table dropped (migration 129). Always returns None.
    Kept for callers that pass result into metadata (harmless None).
    """
    return None


async def resolve_agent_project_slug_full(client, user_id: str, agent: dict) -> Optional[str]:
    """
    Stub — projects table dropped (migration 129). Always returns None.
    Kept for callers that pass result into metadata (harmless None).
    """
    return None

VALID_EVENT_TYPES = frozenset({
    # Task lifecycle (ADR-138/141)
    "task_executed",                # Task pipeline completed (scheduled or manual)
    "task_created",                 # Task created via TP primitive
    "task_triggered",               # Task manually triggered (Run Now)
    "task_paused",                  # Task paused via TP primitive
    "task_resumed",                 # Task resumed via TP primitive
    # Agent lifecycle
    "agent_run",                    # Legacy: pre-ADR-141 execution events (still in DB)
    "agent_approved",
    "agent_rejected",
    "agent_bootstrapped",           # ADR-110/140: Auto-created or scaffolded agent
    "agent_scheduled",              # Lifecycle hygiene action
    # Platform & sync
    "platform_synced",              # Legacy — kept for historical events
    "integration_connected",
    "integration_disconnected",
    "content_cleanup",              # Legacy — kept for historical events
    # Sessions & memory
    "chat_session",
    "memory_written",
    "session_summary_written",      # Legacy / compatibility event
    # System
    "scheduler_heartbeat",          # ADR-072: Scheduler execution cycle
    "composer_heartbeat",           # Legacy — kept for historical events
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
        event_type: One of 'agent_run', 'agent_approved', 'agent_rejected',
            'memory_written', 'platform_synced', 'integration_connected',
            'integration_disconnected', 'chat_session'
        summary: Human-readable one-liner (shown in working memory block)
        event_ref: UUID of related record (run_id, session_id, etc.) — optional
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
