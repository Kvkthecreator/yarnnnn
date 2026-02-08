"""
Ephemeral Context Service - ADR-031 Phase 1

Manages time-bounded context that expires after TTL.
This is distinct from long-term memories (user_memories table).

Ephemeral context is defined by LIFESPAN, not source:
- Platform imports (Slack, Gmail, Notion)
- Calendar/schedule events
- Session context
- Time-bounded user notes
- Recent deliverable outputs

Usage:
- Writer: Store extracted platform data with TTL
- Reader: Fetch fresh context for deliverable generation
- Cleanup: Delete expired entries (run periodically)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal
from dataclasses import dataclass
from uuid import UUID

logger = logging.getLogger(__name__)


# =============================================================================
# Types
# =============================================================================

SourceType = Literal["slack", "gmail", "notion", "calendar", "session", "user_note", "deliverable"]


@dataclass
class EphemeralContextItem:
    """A single ephemeral context entry."""
    id: str
    source_type: SourceType  # Column is "platform" but semantically "source_type"
    resource_id: str
    resource_name: Optional[str]
    content: str
    content_type: Optional[str]  # message, thread_summary, page_update, event, note
    metadata: dict  # Source-specific metadata
    source_timestamp: Optional[datetime]
    created_at: datetime
    expires_at: datetime


@dataclass
class PlatformSemanticSignals:
    """
    Platform-specific signals extracted from raw data.
    These inform "what's worth saying" not just "how to say it".
    """
    # Thread signals (Slack)
    thread_reply_count: int = 0
    has_unanswered_question: bool = False
    is_stalled_thread: bool = False  # No replies in 24h after question

    # Engagement signals
    reaction_count: int = 0
    reaction_types: list[str] = None  # emoji names

    # Urgency signals
    mentions_deadline: bool = False
    mentions_blocker: bool = False
    has_action_request: bool = False

    # Participants
    unique_participants: list[str] = None

    def __post_init__(self):
        if self.reaction_types is None:
            self.reaction_types = []
        if self.unique_participants is None:
            self.unique_participants = []

    def to_dict(self) -> dict:
        return {
            "thread_reply_count": self.thread_reply_count,
            "has_unanswered_question": self.has_unanswered_question,
            "is_stalled_thread": self.is_stalled_thread,
            "reaction_count": self.reaction_count,
            "reaction_types": self.reaction_types,
            "mentions_deadline": self.mentions_deadline,
            "mentions_blocker": self.mentions_blocker,
            "has_action_request": self.has_action_request,
            "unique_participants": self.unique_participants,
        }


# =============================================================================
# TTL Configuration
# =============================================================================

DEFAULT_TTL_HOURS = {
    "slack": 168,      # 7 days - messages age quickly
    "gmail": 336,      # 14 days - emails have longer relevance
    "notion": 720,     # 30 days - docs change less frequently
    "calendar": 24,    # 1 day - events are immediately relevant then stale
    "session": 4,      # 4 hours - session context is short-lived
    "user_note": 168,  # 7 days - time-bounded notes
    "deliverable": 72, # 3 days - recent outputs for reference
}


def get_ttl(source_type: SourceType, custom_hours: Optional[int] = None) -> timedelta:
    """Get TTL for a source type."""
    hours = custom_hours or DEFAULT_TTL_HOURS.get(source_type, 168)
    return timedelta(hours=hours)


# =============================================================================
# Writer Functions
# =============================================================================

async def store_ephemeral_context(
    db_client,
    user_id: str,
    source_type: SourceType,
    resource_id: str,
    content: str,
    content_type: Optional[str] = None,
    resource_name: Optional[str] = None,
    metadata: Optional[dict] = None,
    source_timestamp: Optional[datetime] = None,
    ttl_hours: Optional[int] = None,
) -> str:
    """
    Store a single ephemeral context entry.

    Args:
        db_client: Supabase client
        user_id: User UUID
        source_type: Source category (slack, gmail, calendar, etc.)
        resource_id: Identifier within source (channel_id, label, page_id)
        content: The actual context content
        content_type: Type of content (message, thread_summary, etc.)
        resource_name: Human-readable name (channel name, page title)
        metadata: Source-specific metadata (thread_ts, reactions, etc.)
        source_timestamp: When it happened at source
        ttl_hours: Custom TTL override

    Returns:
        ID of created entry
    """
    now = datetime.now(timezone.utc)
    expires_at = now + get_ttl(source_type, ttl_hours)

    record = {
        "user_id": user_id,
        "platform": source_type,  # Column named "platform" but stores source_type
        "resource_id": resource_id,
        "resource_name": resource_name,
        "content": content,
        "content_type": content_type,
        "platform_metadata": metadata or {},
        "source_timestamp": source_timestamp.isoformat() if source_timestamp else None,
        "expires_at": expires_at.isoformat(),
    }

    result = db_client.table("ephemeral_context").insert(record).execute()

    if result.data:
        logger.debug(f"[EPHEMERAL] Stored {source_type}/{resource_id}: {content[:50]}...")
        return result.data[0]["id"]

    raise ValueError("Failed to store ephemeral context")


async def store_slack_context_batch(
    db_client,
    user_id: str,
    channel_id: str,
    channel_name: str,
    messages: list[dict],
    signals: Optional[PlatformSemanticSignals] = None,
) -> int:
    """
    Store Slack messages as ephemeral context.

    Enriches each message with platform-semantic signals.
    Returns count of entries stored.
    """
    if not messages:
        return 0

    now = datetime.now(timezone.utc)
    expires_at = now + get_ttl("slack")

    records = []
    for msg in messages:
        # Skip bot/system messages
        if msg.get("subtype") in ("bot_message", "channel_join", "channel_leave"):
            continue

        # Extract message timestamp
        source_ts = None
        try:
            ts = msg.get("ts", "")
            source_ts = datetime.fromtimestamp(float(ts), tz=timezone.utc)
        except (ValueError, TypeError):
            pass

        # Build metadata with platform-semantic signals
        metadata = {
            "ts": msg.get("ts"),
            "user": msg.get("user"),
            "thread_ts": msg.get("thread_ts"),
            "reply_count": msg.get("reply_count", 0),
            "reactions": msg.get("reactions", []),
        }

        # Add signals if this is a thread parent
        if signals and not msg.get("thread_ts"):
            metadata["signals"] = signals.to_dict()

        content_type = "thread_parent" if msg.get("reply_count", 0) > 0 else "message"
        if msg.get("thread_ts") and msg.get("thread_ts") != msg.get("ts"):
            content_type = "thread_reply"

        records.append({
            "user_id": user_id,
            "platform": "slack",
            "resource_id": channel_id,
            "resource_name": channel_name,
            "content": msg.get("text", ""),
            "content_type": content_type,
            "platform_metadata": metadata,
            "source_timestamp": source_ts.isoformat() if source_ts else None,
            "expires_at": expires_at.isoformat(),
        })

    if not records:
        return 0

    result = db_client.table("ephemeral_context").insert(records).execute()
    count = len(result.data) if result.data else 0

    logger.info(f"[EPHEMERAL] Stored {count} Slack messages from #{channel_name}")
    return count


async def store_gmail_context_batch(
    db_client,
    user_id: str,
    label: str,
    messages: list[dict],
) -> int:
    """
    Store Gmail messages as ephemeral context.
    Returns count of entries stored.
    """
    if not messages:
        return 0

    now = datetime.now(timezone.utc)
    expires_at = now + get_ttl("gmail")

    records = []
    for msg in messages:
        headers = msg.get("headers", {})

        # Parse date
        source_ts = None
        date_str = headers.get("Date", headers.get("date", ""))
        if date_str:
            try:
                from email.utils import parsedate_to_datetime
                source_ts = parsedate_to_datetime(date_str)
            except (ValueError, TypeError):
                pass

        # Build content from body and subject
        subject = headers.get("Subject", headers.get("subject", ""))
        body = msg.get("body", msg.get("snippet", ""))
        content = f"Subject: {subject}\n\n{body}" if subject else body

        metadata = {
            "message_id": msg.get("id"),
            "thread_id": msg.get("threadId"),
            "from": headers.get("From", headers.get("from")),
            "to": headers.get("To", headers.get("to")),
            "labels": msg.get("labelIds", []),
        }

        records.append({
            "user_id": user_id,
            "platform": "gmail",
            "resource_id": label,
            "resource_name": label,
            "content": content[:10000],  # Truncate very long emails
            "content_type": "email",
            "platform_metadata": metadata,
            "source_timestamp": source_ts.isoformat() if source_ts else None,
            "expires_at": expires_at.isoformat(),
        })

    if not records:
        return 0

    result = db_client.table("ephemeral_context").insert(records).execute()
    count = len(result.data) if result.data else 0

    logger.info(f"[EPHEMERAL] Stored {count} Gmail messages from {label}")
    return count


async def store_notion_context(
    db_client,
    user_id: str,
    page_id: str,
    page_title: str,
    content: str,
    metadata: Optional[dict] = None,
) -> str:
    """
    Store Notion page content as ephemeral context.
    Returns ID of created entry.
    """
    return await store_ephemeral_context(
        db_client=db_client,
        user_id=user_id,
        source_type="notion",
        resource_id=page_id,
        resource_name=page_title,
        content=content,
        content_type="page",
        metadata=metadata,
    )


# =============================================================================
# Reader Functions
# =============================================================================

async def get_ephemeral_context(
    db_client,
    user_id: str,
    source_types: Optional[list[SourceType]] = None,
    resource_ids: Optional[list[str]] = None,
    limit: int = 100,
    include_expired: bool = False,
) -> list[EphemeralContextItem]:
    """
    Fetch ephemeral context for a user.

    Args:
        db_client: Supabase client
        user_id: User UUID
        source_types: Filter by source types (None = all)
        resource_ids: Filter by resource IDs (None = all)
        limit: Max items to return
        include_expired: Include expired items (for debugging)

    Returns:
        List of EphemeralContextItem
    """
    query = (
        db_client.table("ephemeral_context")
        .select("*")
        .eq("user_id", user_id)
        .order("source_timestamp", desc=True)
        .limit(limit)
    )

    if source_types:
        query = query.in_("platform", source_types)

    if resource_ids:
        query = query.in_("resource_id", resource_ids)

    if not include_expired:
        now = datetime.now(timezone.utc).isoformat()
        query = query.gt("expires_at", now)

    result = query.execute()

    items = []
    for row in result.data or []:
        items.append(EphemeralContextItem(
            id=row["id"],
            source_type=row["platform"],
            resource_id=row["resource_id"],
            resource_name=row.get("resource_name"),
            content=row["content"],
            content_type=row.get("content_type"),
            metadata=row.get("platform_metadata", {}),
            source_timestamp=_parse_datetime(row.get("source_timestamp")),
            created_at=_parse_datetime(row["created_at"]),
            expires_at=_parse_datetime(row["expires_at"]),
        ))

    return items


async def get_context_for_deliverable(
    db_client,
    user_id: str,
    deliverable_sources: list[dict],
    limit_per_source: int = 50,
) -> list[EphemeralContextItem]:
    """
    Fetch ephemeral context relevant to a deliverable's sources.

    Args:
        db_client: Supabase client
        user_id: User UUID
        deliverable_sources: List of source configs from deliverable
            Each has: provider, resource_id, resource_name
        limit_per_source: Max items per source

    Returns:
        Combined list of EphemeralContextItem, sorted by recency
    """
    all_items = []

    for source in deliverable_sources:
        provider = source.get("provider")
        resource_id = source.get("resource_id")

        if not provider or not resource_id:
            continue

        items = await get_ephemeral_context(
            db_client=db_client,
            user_id=user_id,
            source_types=[provider],
            resource_ids=[resource_id],
            limit=limit_per_source,
        )

        all_items.extend(items)

    # Sort by source_timestamp (most recent first)
    all_items.sort(
        key=lambda x: x.source_timestamp or x.created_at,
        reverse=True,
    )

    return all_items


async def get_context_summary_for_generation(
    db_client,
    user_id: str,
    deliverable_sources: list[dict],
    max_items: int = 100,
) -> str:
    """
    Get ephemeral context formatted for LLM generation prompt.

    Returns a formatted string ready to include in generation context.
    """
    items = await get_context_for_deliverable(
        db_client=db_client,
        user_id=user_id,
        deliverable_sources=deliverable_sources,
        limit_per_source=max_items // max(len(deliverable_sources), 1),
    )

    if not items:
        return ""

    # Group by source
    by_source = {}
    for item in items:
        key = f"{item.source_type}:{item.resource_name or item.resource_id}"
        if key not in by_source:
            by_source[key] = []
        by_source[key].append(item)

    # Format for prompt
    sections = []
    for source_key, source_items in by_source.items():
        source_type, source_name = source_key.split(":", 1)

        section_lines = [f"## Recent context from {source_type.title()}: {source_name}"]

        for item in source_items[:20]:  # Cap per source
            # Format timestamp
            ts_str = ""
            if item.source_timestamp:
                ts_str = f"[{item.source_timestamp.strftime('%Y-%m-%d %H:%M')}] "

            # Add metadata signals if present
            signals_str = ""
            if item.metadata.get("signals"):
                signals = item.metadata["signals"]
                if signals.get("has_unanswered_question"):
                    signals_str = " ⚠️ UNANSWERED"
                elif signals.get("is_stalled_thread"):
                    signals_str = " ⏳ STALLED"
                elif signals.get("thread_reply_count", 0) > 5:
                    signals_str = f" 🔥 HOT ({signals['thread_reply_count']} replies)"

            section_lines.append(f"{ts_str}{item.content}{signals_str}")

        sections.append("\n".join(section_lines))

    return "\n\n".join(sections)


# =============================================================================
# Cleanup Functions
# =============================================================================

async def cleanup_expired_context(db_client) -> int:
    """
    Delete expired ephemeral context entries.
    Should be run periodically (e.g., hourly).

    Returns count of deleted entries.
    """
    now = datetime.now(timezone.utc).isoformat()

    # First count
    count_result = (
        db_client.table("ephemeral_context")
        .select("id", count="exact")
        .lt("expires_at", now)
        .execute()
    )

    count = count_result.count or 0

    if count == 0:
        return 0

    # Delete in batches to avoid timeout
    deleted = 0
    batch_size = 100

    while deleted < count:
        result = (
            db_client.table("ephemeral_context")
            .delete()
            .lt("expires_at", now)
            .limit(batch_size)
            .execute()
        )

        batch_deleted = len(result.data) if result.data else 0
        deleted += batch_deleted

        if batch_deleted == 0:
            break

    logger.info(f"[EPHEMERAL] Cleaned up {deleted} expired entries")
    return deleted


# =============================================================================
# Helpers
# =============================================================================

def _parse_datetime(value) -> Optional[datetime]:
    """Parse datetime from string or return None."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        # Handle ISO format with or without timezone
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
