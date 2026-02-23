"""
Platform Content Service - ADR-072 Unified Content Layer

Manages platform-synced content with retention-based accumulation.
This replaces the old filesystem.py (which used filesystem_items).

ADR-072 Key Changes:
- platform_content: Unified content table (replaces filesystem_items)
- Retention policy: Content starts ephemeral, becomes retained when referenced
- Semantic search: pgvector embeddings for similarity search
- Content versioning: version_of FK chain for content updates
- Provenance tracking: retained_reason, retained_ref

Usage:
- Writer: Store synced platform data with TTL (retained=false, expires_at set)
- Retention: Mark content retained when referenced (retained=true, expires_at=NULL)
- Reader: Fetch content for TP search, deliverable execution, signal processing
- Cleanup: Delete expired non-retained entries (run periodically)
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal
from dataclasses import dataclass
from uuid import UUID

logger = logging.getLogger(__name__)


# =============================================================================
# Types
# =============================================================================

PlatformType = Literal["slack", "gmail", "notion", "calendar"]
RetainedReason = Literal["deliverable_execution", "signal_processing", "tp_session"]


@dataclass
class PlatformContentItem:
    """A single platform content item (replaces FilesystemItem)."""
    id: str
    platform: PlatformType
    resource_id: str
    resource_name: Optional[str]
    item_id: str
    content: str
    content_type: Optional[str]
    content_hash: Optional[str]
    title: Optional[str]
    author: Optional[str]
    author_id: Optional[str]
    is_user_authored: bool
    metadata: dict
    source_timestamp: Optional[datetime]
    fetched_at: datetime
    # Retention fields (ADR-072)
    retained: bool
    retained_reason: Optional[str]
    retained_ref: Optional[str]
    retained_at: Optional[datetime]
    expires_at: Optional[datetime]


@dataclass
class PlatformSemanticSignals:
    """
    Platform-specific signals extracted from raw data.
    These inform "what's worth saying" not just "how to say it".
    """
    # Thread signals (Slack)
    thread_reply_count: int = 0
    has_unanswered_question: bool = False
    is_stalled_thread: bool = False

    # Engagement signals
    reaction_count: int = 0
    reaction_types: list[str] = None

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
    "slack": 168,      # 7 days
    "gmail": 336,      # 14 days
    "notion": 720,     # 30 days
    "calendar": 24,    # 1 day
}


def get_ttl(platform: PlatformType, custom_hours: Optional[int] = None) -> timedelta:
    """Get TTL for a platform type."""
    hours = custom_hours or DEFAULT_TTL_HOURS.get(platform, 168)
    return timedelta(hours=hours)


def compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash of content for deduplication."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


# =============================================================================
# Writer Functions
# =============================================================================

async def store_platform_content(
    db_client,
    user_id: str,
    platform: PlatformType,
    resource_id: str,
    item_id: str,
    content: str,
    content_type: Optional[str] = None,
    resource_name: Optional[str] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
    author_id: Optional[str] = None,
    is_user_authored: bool = False,
    metadata: Optional[dict] = None,
    source_timestamp: Optional[datetime] = None,
    ttl_hours: Optional[int] = None,
    # Retention fields (for signal processing dual-writer)
    retained: bool = False,
    retained_reason: Optional[RetainedReason] = None,
    retained_ref: Optional[str] = None,
) -> str:
    """
    Store a single platform content item.

    Args:
        db_client: Supabase client
        user_id: User UUID
        platform: Platform type (slack, gmail, notion, calendar)
        resource_id: Identifier within platform (channel_id, label, page_id)
        item_id: Unique identifier for the item within resource
        content: The actual content
        content_type: Type of content (message, thread_summary, email, page)
        resource_name: Human-readable name (channel name, page title)
        title: Item title (email subject, page title)
        author: Author name
        author_id: Author ID on platform
        is_user_authored: Whether this was written by the user
        metadata: Platform-specific metadata
        source_timestamp: When it happened at source
        ttl_hours: Custom TTL override
        retained: Whether to mark as retained (signal processing uses this)
        retained_reason: Why it's retained
        retained_ref: FK to the record that marked it retained

    Returns:
        ID of created entry
    """
    now = datetime.now(timezone.utc)
    content_hash = compute_content_hash(content)

    # Retention logic
    if retained:
        expires_at = None
        retained_at = now
    else:
        expires_at = now + get_ttl(platform, ttl_hours)
        retained_at = None

    record = {
        "user_id": user_id,
        "platform": platform,
        "resource_id": resource_id,
        "resource_name": resource_name,
        "item_id": item_id,
        "content": content,
        "content_type": content_type,
        "content_hash": content_hash,
        "title": title,
        "author": author,
        "author_id": author_id,
        "is_user_authored": is_user_authored,
        "source_timestamp": source_timestamp.isoformat() if source_timestamp else None,
        "fetched_at": now.isoformat(),
        "retained": retained,
        "retained_reason": retained_reason,
        "retained_ref": retained_ref,
        "retained_at": retained_at.isoformat() if retained_at else None,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "metadata": metadata or {},
    }

    result = db_client.table("platform_content").upsert(
        record,
        on_conflict="user_id,platform,resource_id,item_id,content_hash"
    ).execute()

    if result.data:
        logger.debug(f"[PLATFORM_CONTENT] Stored {platform}/{resource_id}/{item_id}: {content[:50]}...")
        return result.data[0]["id"]

    raise ValueError("Failed to store platform content")


async def store_slack_items_batch(
    db_client,
    user_id: str,
    channel_id: str,
    channel_name: str,
    messages: list[dict],
    user_slack_id: Optional[str] = None,
    signals: Optional[PlatformSemanticSignals] = None,
) -> int:
    """
    Store Slack messages as platform content.
    Returns count of entries stored.
    """
    if not messages:
        return 0

    now = datetime.now(timezone.utc)
    expires_at = now + get_ttl("slack")

    records = []
    for msg in messages:
        if msg.get("subtype") in ("bot_message", "channel_join", "channel_leave"):
            continue

        source_ts = None
        ts = msg.get("ts", "")
        try:
            source_ts = datetime.fromtimestamp(float(ts), tz=timezone.utc)
        except (ValueError, TypeError):
            pass

        content = msg.get("text", "")
        content_hash = compute_content_hash(content)

        metadata = {
            "ts": ts,
            "user": msg.get("user"),
            "thread_ts": msg.get("thread_ts"),
            "reply_count": msg.get("reply_count", 0),
            "reactions": msg.get("reactions", []),
        }

        if signals and not msg.get("thread_ts"):
            metadata["signals"] = signals.to_dict()

        content_type = "thread_parent" if msg.get("reply_count", 0) > 0 else "message"
        if msg.get("thread_ts") and msg.get("thread_ts") != msg.get("ts"):
            content_type = "thread_reply"

        is_user_authored = user_slack_id and msg.get("user") == user_slack_id

        records.append({
            "user_id": user_id,
            "platform": "slack",
            "resource_id": channel_id,
            "resource_name": channel_name,
            "item_id": ts,
            "content": content,
            "content_type": content_type,
            "content_hash": content_hash,
            "title": None,
            "author": msg.get("user"),
            "author_id": msg.get("user"),
            "is_user_authored": is_user_authored,
            "source_timestamp": source_ts.isoformat() if source_ts else None,
            "fetched_at": now.isoformat(),
            "retained": False,
            "expires_at": expires_at.isoformat(),
            "metadata": metadata,
        })

    if not records:
        return 0

    result = db_client.table("platform_content").upsert(
        records,
        on_conflict="user_id,platform,resource_id,item_id,content_hash"
    ).execute()
    count = len(result.data) if result.data else 0

    if count > 0:
        await _update_sync_registry_after_store(
            db_client,
            user_id,
            platform="slack",
            resource_id=channel_id,
            resource_name=channel_name,
            item_count=count,
            source_latest_at=_get_latest_source_timestamp(messages, platform="slack"),
        )

    logger.info(f"[PLATFORM_CONTENT] Stored {count} Slack messages from #{channel_name}")
    return count


async def store_gmail_items_batch(
    db_client,
    user_id: str,
    label: str,
    messages: list[dict],
    user_email: Optional[str] = None,
) -> int:
    """
    Store Gmail messages as platform content.
    Returns count of entries stored.
    """
    if not messages:
        return 0

    now = datetime.now(timezone.utc)
    expires_at = now + get_ttl("gmail")

    records = []
    for msg in messages:
        headers = msg.get("headers", {})

        source_ts = None
        date_str = headers.get("Date", headers.get("date", ""))
        if date_str:
            try:
                from email.utils import parsedate_to_datetime
                source_ts = parsedate_to_datetime(date_str)
            except (ValueError, TypeError):
                pass

        subject = headers.get("Subject", headers.get("subject", ""))
        body = msg.get("body", msg.get("snippet", ""))
        content = f"Subject: {subject}\n\n{body}" if subject else body
        content_hash = compute_content_hash(content)

        from_header = headers.get("From", headers.get("from", ""))

        is_user_authored = False
        if user_email and from_header:
            is_user_authored = user_email.lower() in from_header.lower()

        metadata = {
            "message_id": msg.get("id"),
            "thread_id": msg.get("threadId"),
            "from": from_header,
            "to": headers.get("To", headers.get("to")),
            "labels": msg.get("labelIds", []),
        }

        records.append({
            "user_id": user_id,
            "platform": "gmail",
            "resource_id": label,
            "resource_name": label,
            "item_id": msg.get("id", ""),
            "content": content[:10000],
            "content_type": "email",
            "content_hash": content_hash,
            "title": subject,
            "author": from_header,
            "author_id": None,
            "is_user_authored": is_user_authored,
            "source_timestamp": source_ts.isoformat() if source_ts else None,
            "fetched_at": now.isoformat(),
            "retained": False,
            "expires_at": expires_at.isoformat(),
            "metadata": metadata,
        })

    if not records:
        return 0

    result = db_client.table("platform_content").upsert(
        records,
        on_conflict="user_id,platform,resource_id,item_id,content_hash"
    ).execute()
    count = len(result.data) if result.data else 0

    if count > 0:
        await _update_sync_registry_after_store(
            db_client,
            user_id,
            platform="gmail",
            resource_id=label,
            resource_name=label,
            item_count=count,
            source_latest_at=_get_latest_source_timestamp(messages, platform="gmail"),
        )

    logger.info(f"[PLATFORM_CONTENT] Stored {count} Gmail messages from {label}")
    return count


async def store_notion_item(
    db_client,
    user_id: str,
    page_id: str,
    page_title: str,
    content: str,
    metadata: Optional[dict] = None,
    is_user_authored: bool = False,
) -> str:
    """
    Store Notion page content.
    Returns ID of created entry.
    """
    entry_id = await store_platform_content(
        db_client=db_client,
        user_id=user_id,
        platform="notion",
        resource_id=page_id,
        item_id=page_id,
        resource_name=page_title,
        content=content,
        content_type="page",
        title=page_title,
        is_user_authored=is_user_authored,
        metadata=metadata,
    )

    if entry_id:
        source_latest_at = None
        if metadata:
            edited = metadata.get("last_edited_time") or metadata.get("lastEditedTime")
            if edited:
                source_latest_at = _parse_datetime(edited)

        await _update_sync_registry_after_store(
            db_client,
            user_id,
            platform="notion",
            resource_id=page_id,
            resource_name=page_title,
            item_count=1,
            source_latest_at=source_latest_at,
        )

    return entry_id


# =============================================================================
# Retention Functions (ADR-072)
# =============================================================================

async def mark_content_retained(
    db_client,
    content_ids: list[str],
    reason: RetainedReason,
    ref: Optional[str] = None,
) -> int:
    """
    Mark content items as retained.

    Called by:
    - Deliverable execution after synthesis (reason='deliverable_execution')
    - Signal processing when content is significant (reason='signal_processing')
    - TP session when content is accessed (reason='tp_session')

    Args:
        db_client: Supabase client
        content_ids: List of platform_content IDs to retain
        reason: Why content is being retained
        ref: FK to the record that triggered retention

    Returns:
        Count of items marked retained
    """
    if not content_ids:
        return 0

    now = datetime.now(timezone.utc)

    # Use the SQL function we created in migration
    result = db_client.rpc(
        "mark_content_retained",
        {
            "p_content_ids": content_ids,
            "p_reason": reason,
            "p_ref": ref,
        }
    ).execute()

    count = result.data if result.data else 0
    logger.info(f"[PLATFORM_CONTENT] Marked {count} items retained ({reason})")
    return count


# =============================================================================
# Reader Functions
# =============================================================================

async def get_platform_content(
    db_client,
    user_id: str,
    platforms: Optional[list[PlatformType]] = None,
    resource_ids: Optional[list[str]] = None,
    limit: int = 100,
    include_expired: bool = False,
    retained_only: bool = False,
    user_authored_only: bool = False,
) -> list[PlatformContentItem]:
    """
    Fetch platform content for a user.

    Args:
        db_client: Supabase client
        user_id: User UUID
        platforms: Filter by platforms (None = all)
        resource_ids: Filter by resource IDs (None = all)
        limit: Max items to return
        include_expired: Include expired non-retained items
        retained_only: Only return retained items (ADR-072)
        user_authored_only: Only return user-authored items

    Returns:
        List of PlatformContentItem
    """
    query = (
        db_client.table("platform_content")
        .select("*")
        .eq("user_id", user_id)
        .order("fetched_at", desc=True)
        .limit(limit)
    )

    if platforms:
        query = query.in_("platform", platforms)

    if resource_ids:
        query = query.in_("resource_id", resource_ids)

    if retained_only:
        query = query.eq("retained", True)
    elif not include_expired:
        # Non-expired: either retained=true OR expires_at > now
        now = datetime.now(timezone.utc).isoformat()
        query = query.or_(f"retained.eq.true,expires_at.gt.{now}")

    if user_authored_only:
        query = query.eq("is_user_authored", True)

    result = query.execute()

    items = []
    for row in result.data or []:
        items.append(PlatformContentItem(
            id=row["id"],
            platform=row["platform"],
            resource_id=row["resource_id"],
            resource_name=row.get("resource_name"),
            item_id=row["item_id"],
            content=row["content"],
            content_type=row.get("content_type"),
            content_hash=row.get("content_hash"),
            title=row.get("title"),
            author=row.get("author"),
            author_id=row.get("author_id"),
            is_user_authored=row.get("is_user_authored", False),
            metadata=row.get("metadata", {}),
            source_timestamp=_parse_datetime(row.get("source_timestamp")),
            fetched_at=_parse_datetime(row["fetched_at"]),
            retained=row.get("retained", False),
            retained_reason=row.get("retained_reason"),
            retained_ref=row.get("retained_ref"),
            retained_at=_parse_datetime(row.get("retained_at")),
            expires_at=_parse_datetime(row.get("expires_at")),
        ))

    return items


async def search_platform_content(
    db_client,
    user_id: str,
    query_text: Optional[str] = None,
    query_embedding: Optional[list[float]] = None,
    platforms: Optional[list[str]] = None,
    resource_ids: Optional[list[str]] = None,
    retained_only: bool = False,
    limit: int = 50,
    similarity_threshold: float = 0.7,
) -> list[tuple[PlatformContentItem, float]]:
    """
    Search platform content using semantic or text search.

    ADR-072: Uses pgvector for semantic search when embedding provided,
    falls back to full-text search otherwise.

    Args:
        db_client: Supabase client
        user_id: User UUID
        query_text: Text query for full-text search
        query_embedding: Embedding vector for semantic search
        platforms: Filter by platforms
        resource_ids: Filter by resource IDs
        retained_only: Only search retained content
        limit: Max results
        similarity_threshold: Min similarity for semantic search

    Returns:
        List of (PlatformContentItem, similarity_score) tuples
    """
    # Use the SQL function we created in migration
    result = db_client.rpc(
        "search_platform_content",
        {
            "p_user_id": user_id,
            "p_query_embedding": query_embedding,
            "p_query_text": query_text,
            "p_platforms": platforms,
            "p_resource_ids": resource_ids,
            "p_retained_only": retained_only,
            "p_limit": limit,
            "p_similarity_threshold": similarity_threshold,
        }
    ).execute()

    items = []
    for row in result.data or []:
        item = PlatformContentItem(
            id=row["id"],
            platform=row["platform"],
            resource_id=row["resource_id"],
            resource_name=row.get("resource_name"),
            item_id=row["item_id"],
            content=row["content"],
            content_type=row.get("content_type"),
            content_hash=None,
            title=row.get("title"),
            author=row.get("author"),
            author_id=None,
            is_user_authored=False,
            metadata={},
            source_timestamp=_parse_datetime(row.get("source_timestamp")),
            fetched_at=datetime.now(timezone.utc),
            retained=row.get("retained", False),
            retained_reason=None,
            retained_ref=None,
            retained_at=None,
            expires_at=None,
        )
        items.append((item, row.get("similarity", 1.0)))

    return items


async def get_content_for_deliverable(
    db_client,
    user_id: str,
    deliverable_sources: list[dict],
    limit_per_source: int = 50,
) -> list[PlatformContentItem]:
    """
    Fetch platform content relevant to a deliverable's sources.

    Args:
        db_client: Supabase client
        user_id: User UUID
        deliverable_sources: List of source configs from deliverable
        limit_per_source: Max items per source

    Returns:
        Combined list sorted by recency
    """
    all_items = []

    for source in deliverable_sources:
        provider = source.get("provider") or source.get("platform")
        resource_id = source.get("resource_id")

        if not provider or not resource_id:
            continue

        items = await get_platform_content(
            db_client=db_client,
            user_id=user_id,
            platforms=[provider],
            resource_ids=[resource_id],
            limit=limit_per_source,
        )

        all_items.extend(items)

    all_items.sort(
        key=lambda x: x.source_timestamp or x.fetched_at,
        reverse=True,
    )

    return all_items


async def get_content_summary_for_generation(
    db_client,
    user_id: str,
    deliverable_sources: list[dict],
    max_items: int = 100,
) -> tuple[str, list[str]]:
    """
    Get platform content formatted for LLM generation prompt.

    Returns:
        Tuple of (formatted_string, list_of_content_ids)
        The content_ids can be used to mark content as retained after synthesis.
    """
    items = await get_content_for_deliverable(
        db_client=db_client,
        user_id=user_id,
        deliverable_sources=deliverable_sources,
        limit_per_source=max_items // max(len(deliverable_sources), 1),
    )

    if not items:
        return "", []

    content_ids = [item.id for item in items]
    now = datetime.now(timezone.utc)

    by_source = {}
    for item in items:
        key = f"{item.platform}:{item.resource_name or item.resource_id}"
        if key not in by_source:
            by_source[key] = []
        by_source[key].append(item)

    sections = []
    for source_key, source_items in by_source.items():
        platform, source_name = source_key.split(":", 1)

        newest = max(
            (i.source_timestamp or i.fetched_at for i in source_items),
            default=now
        )

        age = now - newest
        if age.days > 0:
            freshness = f"{age.days}d ago"
        elif age.seconds > 3600:
            freshness = f"{age.seconds // 3600}h ago"
        else:
            freshness = "just now"

        header = f"## {platform.title()}: {source_name}"
        header += f"\n_({len(source_items)} items, most recent: {freshness})_"

        section_lines = [header]

        for item in source_items[:20]:
            ts_str = ""
            if item.source_timestamp:
                ts_str = f"[{item.source_timestamp.strftime('%m/%d %H:%M')}] "

            author_str = ""
            if item.author:
                author_str = f"<{item.author}> "

            signals_str = ""
            if item.metadata.get("signals"):
                signals = item.metadata["signals"]
                signal_markers = []
                if signals.get("has_unanswered_question"):
                    signal_markers.append("UNANSWERED")
                if signals.get("is_stalled_thread"):
                    signal_markers.append("STALLED")
                if signals.get("is_urgent") or signals.get("mentions_blocker"):
                    signal_markers.append("URGENT")
                if signals.get("thread_reply_count", 0) > 5:
                    signal_markers.append(f"HOT ({signals['thread_reply_count']} replies)")
                if signals.get("is_decision"):
                    signal_markers.append("DECISION")
                if signal_markers:
                    signals_str = " [" + ", ".join(signal_markers) + "]"

            content = item.content[:500] if len(item.content) > 500 else item.content
            section_lines.append(f"{ts_str}{author_str}{content}{signals_str}")

        sections.append("\n".join(section_lines))

    return "\n\n".join(sections), content_ids


# =============================================================================
# Cleanup Functions
# =============================================================================

async def cleanup_expired_content(db_client, batch_size: int = 1000) -> int:
    """
    Delete expired non-retained content.
    Should be run periodically (e.g., hourly).

    Returns count of deleted entries.
    """
    # Use the SQL function we created in migration
    result = db_client.rpc(
        "cleanup_expired_platform_content",
        {"p_batch_size": batch_size}
    ).execute()

    count = result.data if result.data else 0
    if count > 0:
        logger.info(f"[PLATFORM_CONTENT] Cleaned up {count} expired items")
    return count


# =============================================================================
# Freshness Check
# =============================================================================

async def has_fresh_content_since(
    db_client,
    user_id: str,
    deliverable_sources: list[dict],
    since: datetime,
) -> tuple[bool, int]:
    """
    Check if there's new platform content since a given time.

    Args:
        db_client: Supabase client
        user_id: User UUID
        deliverable_sources: List of source configs from deliverable
        since: Timestamp to check against

    Returns:
        Tuple of (has_fresh_content, count_of_new_items)
    """
    if not deliverable_sources:
        return False, 0

    source_filters = []
    for source in deliverable_sources:
        provider = source.get("provider") or source.get("platform")
        resource_id = source.get("resource_id")
        if provider and resource_id:
            source_filters.append((provider, resource_id))

    if not source_filters:
        return False, 0

    now = datetime.now(timezone.utc)
    total_new = 0

    for provider, resource_id in source_filters:
        result = (
            db_client.table("platform_content")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("platform", provider)
            .eq("resource_id", resource_id)
            .gt("fetched_at", since.isoformat())
            .or_(f"retained.eq.true,expires_at.gt.{now.isoformat()}")
            .execute()
        )

        count = result.count or 0
        total_new += count

    has_fresh = total_new > 0
    logger.debug(f"[PLATFORM_CONTENT] Fresh content check: {total_new} new items since {since.isoformat()}")

    return has_fresh, total_new


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
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


async def _update_sync_registry_after_store(
    db_client,
    user_id: str,
    platform: str,
    resource_id: str,
    resource_name: Optional[str],
    item_count: int,
    source_latest_at: Optional[datetime],
) -> None:
    """Update sync_registry after storing platform content."""
    from services.freshness import update_sync_registry

    await update_sync_registry(
        client=db_client,
        user_id=user_id,
        platform=platform,
        resource_id=resource_id,
        resource_name=resource_name,
        item_count=item_count,
        source_latest_at=source_latest_at,
    )


def _get_latest_source_timestamp(messages: list[dict], platform: str = "slack") -> Optional[datetime]:
    """Extract the latest source timestamp from a batch of messages."""
    latest = None

    for msg in messages:
        ts = None

        if platform == "slack":
            try:
                ts_str = msg.get("ts", "")
                ts = datetime.fromtimestamp(float(ts_str), tz=timezone.utc)
            except (ValueError, TypeError):
                pass

        elif platform == "gmail":
            date_str = msg.get("headers", {}).get("Date") or msg.get("headers", {}).get("date", "")
            if date_str:
                try:
                    from email.utils import parsedate_to_datetime
                    ts = parsedate_to_datetime(date_str)
                except (ValueError, TypeError):
                    pass

        elif platform == "notion":
            edited = msg.get("last_edited_time") or msg.get("lastEditedTime")
            if edited:
                ts = _parse_datetime(edited)

        if ts and (latest is None or ts > latest):
            latest = ts

    return latest


