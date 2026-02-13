"""
Filesystem Service - ADR-058 Knowledge Base Architecture

Manages platform-synced content (filesystem_items) and documents.
This is the "raw data" layer - synced content from platforms.

ADR-058 Terminology:
- filesystem_items: Synced platform content (was ephemeral_context)
- filesystem_documents: Uploaded files (was documents)
- filesystem_chunks: Document chunks (was chunks)

Usage:
- Writer: Store synced platform data with TTL
- Reader: Fetch content for deliverable generation or knowledge inference
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

PlatformType = Literal["slack", "gmail", "notion", "calendar"]


@dataclass
class FilesystemItem:
    """A single filesystem item (synced platform content)."""
    id: str
    platform: PlatformType
    resource_id: str
    resource_name: Optional[str]
    item_id: str
    content: str
    content_type: Optional[str]  # message, thread_summary, page_update, event, email
    title: Optional[str]
    author: Optional[str]
    author_id: Optional[str]
    is_user_authored: bool
    metadata: dict
    source_timestamp: Optional[datetime]
    synced_at: datetime
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
}


def get_ttl(platform: PlatformType, custom_hours: Optional[int] = None) -> timedelta:
    """Get TTL for a platform type."""
    hours = custom_hours or DEFAULT_TTL_HOURS.get(platform, 168)
    return timedelta(hours=hours)


# =============================================================================
# Writer Functions
# =============================================================================

async def store_filesystem_item(
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
) -> str:
    """
    Store a single filesystem item.

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

    Returns:
        ID of created entry
    """
    now = datetime.now(timezone.utc)
    expires_at = now + get_ttl(platform, ttl_hours)

    record = {
        "user_id": user_id,
        "platform": platform,
        "resource_id": resource_id,
        "resource_name": resource_name,
        "item_id": item_id,
        "content": content,
        "content_type": content_type,
        "title": title,
        "author": author,
        "author_id": author_id,
        "is_user_authored": is_user_authored,
        "source_timestamp": source_timestamp.isoformat() if source_timestamp else None,
        "synced_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "metadata": metadata or {},
        "sync_metadata": {},
    }

    result = db_client.table("filesystem_items").upsert(
        record,
        on_conflict="user_id,platform,resource_id,item_id"
    ).execute()

    if result.data:
        logger.debug(f"[FILESYSTEM] Stored {platform}/{resource_id}/{item_id}: {content[:50]}...")
        return result.data[0]["id"]

    raise ValueError("Failed to store filesystem item")


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
    Store Slack messages as filesystem items.

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
        ts = msg.get("ts", "")
        try:
            source_ts = datetime.fromtimestamp(float(ts), tz=timezone.utc)
        except (ValueError, TypeError):
            pass

        # Build metadata with platform-semantic signals
        metadata = {
            "ts": ts,
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

        # Determine if user-authored
        is_user_authored = user_slack_id and msg.get("user") == user_slack_id

        records.append({
            "user_id": user_id,
            "platform": "slack",
            "resource_id": channel_id,
            "resource_name": channel_name,
            "item_id": ts,  # Use timestamp as item_id
            "content": msg.get("text", ""),
            "content_type": content_type,
            "title": None,
            "author": msg.get("user"),
            "author_id": msg.get("user"),
            "is_user_authored": is_user_authored,
            "source_timestamp": source_ts.isoformat() if source_ts else None,
            "synced_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "metadata": metadata,
            "sync_metadata": {},
        })

    if not records:
        return 0

    result = db_client.table("filesystem_items").upsert(
        records,
        on_conflict="user_id,platform,resource_id,item_id"
    ).execute()
    count = len(result.data) if result.data else 0

    # Update sync_registry after storing
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

    logger.info(f"[FILESYSTEM] Stored {count} Slack messages from #{channel_name}")
    return count


async def store_gmail_items_batch(
    db_client,
    user_id: str,
    label: str,
    messages: list[dict],
    user_email: Optional[str] = None,
) -> int:
    """
    Store Gmail messages as filesystem items.
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

        # Get sender info
        from_header = headers.get("From", headers.get("from", ""))

        # Determine if user-authored (sent by user)
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
            "content": content[:10000],  # Truncate very long emails
            "content_type": "email",
            "title": subject,
            "author": from_header,
            "author_id": None,
            "is_user_authored": is_user_authored,
            "source_timestamp": source_ts.isoformat() if source_ts else None,
            "synced_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "metadata": metadata,
            "sync_metadata": {},
        })

    if not records:
        return 0

    result = db_client.table("filesystem_items").upsert(
        records,
        on_conflict="user_id,platform,resource_id,item_id"
    ).execute()
    count = len(result.data) if result.data else 0

    # Update sync_registry after storing
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

    logger.info(f"[FILESYSTEM] Stored {count} Gmail messages from {label}")
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
    Store Notion page content as filesystem item.
    Returns ID of created entry.
    """
    entry_id = await store_filesystem_item(
        db_client=db_client,
        user_id=user_id,
        platform="notion",
        resource_id=page_id,
        item_id=page_id,  # Page ID is also the item ID
        resource_name=page_title,
        content=content,
        content_type="page",
        title=page_title,
        is_user_authored=is_user_authored,
        metadata=metadata,
    )

    # Update sync_registry after storing
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
# Reader Functions
# =============================================================================

async def get_filesystem_items(
    db_client,
    user_id: str,
    platforms: Optional[list[PlatformType]] = None,
    resource_ids: Optional[list[str]] = None,
    limit: int = 100,
    include_expired: bool = False,
    user_authored_only: bool = False,
) -> list[FilesystemItem]:
    """
    Fetch filesystem items for a user.

    Args:
        db_client: Supabase client
        user_id: User UUID
        platforms: Filter by platforms (None = all)
        resource_ids: Filter by resource IDs (None = all)
        limit: Max items to return
        include_expired: Include expired items (for debugging)
        user_authored_only: Only return user-authored items (for style inference)

    Returns:
        List of FilesystemItem
    """
    query = (
        db_client.table("filesystem_items")
        .select("*")
        .eq("user_id", user_id)
        .order("source_timestamp", desc=True)
        .limit(limit)
    )

    if platforms:
        query = query.in_("platform", platforms)

    if resource_ids:
        query = query.in_("resource_id", resource_ids)

    if not include_expired:
        now = datetime.now(timezone.utc).isoformat()
        query = query.gt("expires_at", now)

    if user_authored_only:
        query = query.eq("is_user_authored", True)

    result = query.execute()

    items = []
    for row in result.data or []:
        items.append(FilesystemItem(
            id=row["id"],
            platform=row["platform"],
            resource_id=row["resource_id"],
            resource_name=row.get("resource_name"),
            item_id=row["item_id"],
            content=row["content"],
            content_type=row.get("content_type"),
            title=row.get("title"),
            author=row.get("author"),
            author_id=row.get("author_id"),
            is_user_authored=row.get("is_user_authored", False),
            metadata=row.get("metadata", {}),
            source_timestamp=_parse_datetime(row.get("source_timestamp")),
            synced_at=_parse_datetime(row["synced_at"]),
            expires_at=_parse_datetime(row["expires_at"]),
        ))

    return items


async def get_items_for_deliverable(
    db_client,
    user_id: str,
    deliverable_sources: list[dict],
    limit_per_source: int = 50,
) -> list[FilesystemItem]:
    """
    Fetch filesystem items relevant to a deliverable's sources.

    Args:
        db_client: Supabase client
        user_id: User UUID
        deliverable_sources: List of source configs from deliverable
            Each has: provider, resource_id, resource_name
        limit_per_source: Max items per source

    Returns:
        Combined list of FilesystemItem, sorted by recency
    """
    all_items = []

    for source in deliverable_sources:
        provider = source.get("provider")
        resource_id = source.get("resource_id")

        if not provider or not resource_id:
            continue

        items = await get_filesystem_items(
            db_client=db_client,
            user_id=user_id,
            platforms=[provider],
            resource_ids=[resource_id],
            limit=limit_per_source,
        )

        all_items.extend(items)

    # Sort by source_timestamp (most recent first)
    all_items.sort(
        key=lambda x: x.source_timestamp or x.synced_at,
        reverse=True,
    )

    return all_items


async def get_items_summary_for_generation(
    db_client,
    user_id: str,
    deliverable_sources: list[dict],
    max_items: int = 100,
) -> str:
    """
    Get filesystem items formatted for LLM generation prompt.

    Returns a formatted string ready to include in generation context.
    Includes provenance (source, timestamps) and freshness indicators.
    """
    items = await get_items_for_deliverable(
        db_client=db_client,
        user_id=user_id,
        deliverable_sources=deliverable_sources,
        limit_per_source=max_items // max(len(deliverable_sources), 1),
    )

    if not items:
        return ""

    now = datetime.now(timezone.utc)

    # Group by source
    by_source = {}
    for item in items:
        key = f"{item.platform}:{item.resource_name or item.resource_id}"
        if key not in by_source:
            by_source[key] = []
        by_source[key].append(item)

    # Format for prompt with clear provenance
    sections = []
    for source_key, source_items in by_source.items():
        platform, source_name = source_key.split(":", 1)

        # Calculate freshness for this source
        newest = max(
            (i.source_timestamp or i.synced_at for i in source_items),
            default=now
        )

        # Format time range
        age = now - newest
        if age.days > 0:
            freshness = f"{age.days}d ago"
        elif age.seconds > 3600:
            freshness = f"{age.seconds // 3600}h ago"
        else:
            freshness = "just now"

        # Section header with provenance
        header = f"## {platform.title()}: {source_name}"
        header += f"\n_({len(source_items)} items, most recent: {freshness})_"

        section_lines = [header]

        for item in source_items[:20]:  # Cap per source
            # Format timestamp
            ts_str = ""
            if item.source_timestamp:
                ts_str = f"[{item.source_timestamp.strftime('%m/%d %H:%M')}] "

            # Add author if available
            author_str = ""
            if item.author:
                author_str = f"<{item.author}> "

            # Add metadata signals if present
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

            # Build line
            content = item.content[:500] if len(item.content) > 500 else item.content
            section_lines.append(f"{ts_str}{author_str}{content}{signals_str}")

        sections.append("\n".join(section_lines))

    return "\n\n".join(sections)


# =============================================================================
# Cleanup Functions
# =============================================================================

async def cleanup_expired_items(db_client) -> int:
    """
    Delete expired filesystem items.
    Should be run periodically (e.g., hourly).

    Returns count of deleted entries.
    """
    now = datetime.now(timezone.utc).isoformat()

    # First count
    count_result = (
        db_client.table("filesystem_items")
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
            db_client.table("filesystem_items")
            .delete()
            .lt("expires_at", now)
            .limit(batch_size)
            .execute()
        )

        batch_deleted = len(result.data) if result.data else 0
        deleted += batch_deleted

        if batch_deleted == 0:
            break

    logger.info(f"[FILESYSTEM] Cleaned up {deleted} expired items")
    return deleted


# =============================================================================
# Freshness Check
# =============================================================================

async def has_fresh_items_since(
    db_client,
    user_id: str,
    deliverable_sources: list[dict],
    since: datetime,
) -> tuple[bool, int]:
    """
    Check if there's new filesystem items since a given time.

    Used by scheduler to skip deliverable generation if no new content.

    Args:
        db_client: Supabase client
        user_id: User UUID
        deliverable_sources: List of source configs from deliverable
        since: Timestamp to check against (usually last_run_at)

    Returns:
        Tuple of (has_fresh_items, count_of_new_items)
    """
    if not deliverable_sources:
        return False, 0

    # Build list of (provider, resource_id) tuples
    source_filters = []
    for source in deliverable_sources:
        provider = source.get("provider")
        resource_id = source.get("resource_id")
        if provider and resource_id:
            source_filters.append((provider, resource_id))

    if not source_filters:
        return False, 0

    now = datetime.now(timezone.utc)
    total_new = 0

    for provider, resource_id in source_filters:
        result = (
            db_client.table("filesystem_items")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("platform", provider)
            .eq("resource_id", resource_id)
            .gt("synced_at", since.isoformat())
            .gt("expires_at", now.isoformat())
            .execute()
        )

        count = result.count or 0
        total_new += count

    has_fresh = total_new > 0
    logger.debug(f"[FILESYSTEM] Fresh items check: {total_new} new items since {since.isoformat()}")

    return has_fresh, total_new


async def get_latest_item_timestamp(
    db_client,
    user_id: str,
    deliverable_sources: list[dict],
) -> Optional[datetime]:
    """
    Get the timestamp of the most recent filesystem item for given sources.

    Useful for understanding data freshness before generation.

    Returns:
        Most recent synced_at timestamp, or None if no items
    """
    if not deliverable_sources:
        return None

    latest = None
    now = datetime.now(timezone.utc)

    for source in deliverable_sources:
        provider = source.get("provider")
        resource_id = source.get("resource_id")

        if not provider or not resource_id:
            continue

        result = (
            db_client.table("filesystem_items")
            .select("synced_at")
            .eq("user_id", user_id)
            .eq("platform", provider)
            .eq("resource_id", resource_id)
            .gt("expires_at", now.isoformat())
            .order("synced_at", desc=True)
            .limit(1)
            .execute()
        )

        if result.data:
            ts = _parse_datetime(result.data[0]["synced_at"])
            if ts and (latest is None or ts > latest):
                latest = ts

    return latest


# =============================================================================
# User-Authored Content (for Style Inference)
# =============================================================================

async def get_user_authored_items(
    db_client,
    user_id: str,
    platform: Optional[PlatformType] = None,
    limit: int = 100,
) -> list[FilesystemItem]:
    """
    Get items authored by the user for style inference.

    This is used by the inference engine to analyze the user's
    writing style across platforms.

    Args:
        db_client: Supabase client
        user_id: User UUID
        platform: Optional platform filter
        limit: Max items to return

    Returns:
        List of user-authored FilesystemItem
    """
    return await get_filesystem_items(
        db_client=db_client,
        user_id=user_id,
        platforms=[platform] if platform else None,
        limit=limit,
        user_authored_only=True,
    )


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


# =============================================================================
# Sync Registry Helpers
# =============================================================================

async def _update_sync_registry_after_store(
    db_client,
    user_id: str,
    platform: str,
    resource_id: str,
    resource_name: Optional[str],
    item_count: int,
    source_latest_at: Optional[datetime],
) -> None:
    """
    Update sync_registry after storing filesystem items.

    Called by store_*_items functions to track sync state.
    """
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
    """
    Extract the latest source timestamp from a batch of messages.

    Args:
        messages: List of message dicts
        platform: Platform type to determine timestamp field

    Returns:
        Most recent timestamp, or None if no valid timestamps
    """
    latest = None

    for msg in messages:
        ts = None

        if platform == "slack":
            # Slack uses Unix timestamp in "ts" field
            try:
                ts_str = msg.get("ts", "")
                ts = datetime.fromtimestamp(float(ts_str), tz=timezone.utc)
            except (ValueError, TypeError):
                pass

        elif platform == "gmail":
            # Gmail uses Date header
            date_str = msg.get("headers", {}).get("Date") or msg.get("headers", {}).get("date", "")
            if date_str:
                try:
                    from email.utils import parsedate_to_datetime
                    ts = parsedate_to_datetime(date_str)
                except (ValueError, TypeError):
                    pass

        elif platform == "notion":
            # Notion uses last_edited_time
            edited = msg.get("last_edited_time") or msg.get("lastEditedTime")
            if edited:
                ts = _parse_datetime(edited)

        if ts and (latest is None or ts > latest):
            latest = ts

    return latest


# =============================================================================
# Backwards Compatibility Aliases (TEMPORARY - will be removed)
# =============================================================================

# These exist only for the migration period. Remove after all callers are updated.
# DO NOT use these in new code.

EphemeralContextItem = FilesystemItem
SourceType = PlatformType

async def store_ephemeral_context(*args, **kwargs):
    """DEPRECATED: Use store_filesystem_item instead."""
    logger.warning("store_ephemeral_context is deprecated. Use store_filesystem_item.")
    return await store_filesystem_item(*args, **kwargs)

async def store_slack_context_batch(*args, **kwargs):
    """DEPRECATED: Use store_slack_items_batch instead."""
    logger.warning("store_slack_context_batch is deprecated. Use store_slack_items_batch.")
    return await store_slack_items_batch(*args, **kwargs)

async def store_gmail_context_batch(*args, **kwargs):
    """DEPRECATED: Use store_gmail_items_batch instead."""
    logger.warning("store_gmail_context_batch is deprecated. Use store_gmail_items_batch.")
    return await store_gmail_items_batch(*args, **kwargs)

async def store_notion_context(*args, **kwargs):
    """DEPRECATED: Use store_notion_item instead."""
    logger.warning("store_notion_context is deprecated. Use store_notion_item.")
    return await store_notion_item(*args, **kwargs)

async def get_ephemeral_context(*args, **kwargs):
    """DEPRECATED: Use get_filesystem_items instead."""
    logger.warning("get_ephemeral_context is deprecated. Use get_filesystem_items.")
    return await get_filesystem_items(*args, **kwargs)

async def get_context_for_deliverable(*args, **kwargs):
    """DEPRECATED: Use get_items_for_deliverable instead."""
    logger.warning("get_context_for_deliverable is deprecated. Use get_items_for_deliverable.")
    return await get_items_for_deliverable(*args, **kwargs)

async def cleanup_expired_context(*args, **kwargs):
    """DEPRECATED: Use cleanup_expired_items instead."""
    logger.warning("cleanup_expired_context is deprecated. Use cleanup_expired_items.")
    return await cleanup_expired_items(*args, **kwargs)

async def has_fresh_context_since(*args, **kwargs):
    """DEPRECATED: Use has_fresh_items_since instead."""
    logger.warning("has_fresh_context_since is deprecated. Use has_fresh_items_since.")
    return await has_fresh_items_since(*args, **kwargs)
