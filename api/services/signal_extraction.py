"""
Signal Extraction Service

ADR-073: Reads from platform_content (no live API calls).
Platform sync is the only subsystem that calls external APIs.

This module reads stored platform content and builds a SignalSummary
for signal processing to reason over.

Key principles:
- Reads from platform_content table (populated by platform_sync)
- No live API calls — all content comes from the unified fetch layer
- Respects selected_sources from landscape configuration
- Same output shape (SignalSummary) for compatibility with signal_processing.py
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PlatformContent:
    """Content read from platform_content table for signal processing."""

    platform: str  # "gmail", "calendar", "slack", "notion"
    items_count: int
    content_summary: str  # Human-readable summary for LLM reasoning
    raw_items: list  # Full items for detailed reasoning if needed
    fetch_timestamp: datetime
    time_range_start: Optional[datetime] = None
    time_range_end: Optional[datetime] = None


@dataclass
class SignalSummary:
    """
    Aggregated content from all connected platforms for LLM reasoning.

    This is NOT a threshold/absence detector. It's a content snapshot
    that the orchestrator reasons over to determine significance.
    """

    gmail_content: Optional[PlatformContent] = None
    calendar_content: Optional[PlatformContent] = None
    slack_content: Optional[PlatformContent] = None
    notion_content: Optional[PlatformContent] = None
    total_items: int = 0
    platforms_queried: list = None

    def __post_init__(self):
        if self.platforms_queried is None:
            self.platforms_queried = []

    @property
    def has_signals(self) -> bool:
        """Check if any platform content was fetched."""
        return self.total_items > 0


async def extract_signal_summary(
    client,
    user_id: str,
    signals_filter: str = "all",
) -> SignalSummary:
    """
    Read platform content for signal processing.

    ADR-073: Reads from platform_content table instead of live APIs.
    Content is populated by platform_sync_scheduler → platform_worker.

    Args:
        client: Supabase client
        user_id: User UUID
        signals_filter: "all", "calendar_only", "non_calendar" (for cron scheduling)

    Returns:
        SignalSummary with content from platform_content table
    """
    now = datetime.now(timezone.utc)
    summary = SignalSummary()

    # Query active platform connections
    platforms_result = (
        client.table("platform_connections")
        .select("platform, status, landscape")
        .eq("user_id", user_id)
        .in_("status", ["active", "connected"])
        .execute()
    )

    if not platforms_result.data:
        logger.info(f"[SIGNAL] No active platforms for user {user_id}")
        return summary

    active_platforms = {p["platform"] for p in platforms_result.data}
    # Build a map of platform → selected_sources for filtering
    platform_sources = {}
    for conn in platforms_result.data:
        platform = conn["platform"]
        landscape = conn.get("landscape", {}) or {}
        selected = landscape.get("selected_sources", [])
        source_ids = [
            s.get("id") if isinstance(s, dict) else s
            for s in selected
        ]
        platform_sources[platform] = [sid for sid in source_ids if sid]

    logger.info(f"[SIGNAL] User {user_id} has {len(active_platforms)} active platforms: {active_platforms}")

    # Read content from platform_content for each platform based on filter mode
    if signals_filter in ("all", "calendar_only") and "google" in active_platforms:
        summary.calendar_content = await _read_calendar_content(
            client, user_id, now, platform_sources.get("google", [])
        )
        if summary.calendar_content:
            summary.total_items += summary.calendar_content.items_count
            summary.platforms_queried.append("calendar")

    if signals_filter in ("all", "non_calendar"):
        if "google" in active_platforms:
            summary.gmail_content = await _read_gmail_content(
                client, user_id, now, platform_sources.get("google", [])
            )
            if summary.gmail_content:
                summary.total_items += summary.gmail_content.items_count
                summary.platforms_queried.append("gmail")

        if "slack" in active_platforms:
            summary.slack_content = await _read_slack_content(
                client, user_id, now, platform_sources.get("slack", [])
            )
            if summary.slack_content:
                summary.total_items += summary.slack_content.items_count
                summary.platforms_queried.append("slack")

        if "notion" in active_platforms:
            summary.notion_content = await _read_notion_content(
                client, user_id, now, platform_sources.get("notion", [])
            )
            if summary.notion_content:
                summary.total_items += summary.notion_content.items_count
                summary.platforms_queried.append("notion")

    logger.info(
        f"[SIGNAL_EXTRACTION] user={user_id} filter={signals_filter}: "
        f"platforms={len(summary.platforms_queried)}, total_items={summary.total_items}"
    )

    return summary


async def _read_calendar_content(
    client,
    user_id: str,
    now: datetime,
    selected_sources: list[str],
) -> Optional[PlatformContent]:
    """Read calendar events from platform_content."""
    try:
        query = (
            client.table("platform_content")
            .select("content, metadata, source_timestamp, resource_name, title, author")
            .eq("user_id", user_id)
            .eq("platform", "calendar")
            .eq("content_type", "event")
            .or_(f"retained.eq.true,expires_at.gt.{now.isoformat()}")
            .order("source_timestamp", desc=False)
            .limit(50)
        )

        if selected_sources:
            query = query.in_("resource_id", selected_sources)

        result = query.execute()
        items = result.data or []

        if not items:
            return PlatformContent(
                platform="calendar",
                items_count=0,
                content_summary="No upcoming calendar events in platform_content",
                raw_items=[],
                fetch_timestamp=now,
            )

        # Build content summary for LLM reasoning
        summary_lines = []
        for item in items[:10]:
            content = item.get("content", "")
            meta = item.get("metadata", {}) or {}
            start = meta.get("start", "")
            attendees = len(meta.get("attendees", []))
            summary_lines.append(f"- {content[:100]} ({start}) - {attendees} attendees")

        content_summary = "\n".join(summary_lines)
        if len(items) > 10:
            content_summary += f"\n... and {len(items) - 10} more events"

        return PlatformContent(
            platform="calendar",
            items_count=len(items),
            content_summary=content_summary,
            raw_items=items,
            fetch_timestamp=now,
            time_range_start=now,
            time_range_end=now + timedelta(days=7),
        )

    except Exception as e:
        logger.warning(f"[SIGNAL] Calendar content read failed: {e}")
        return None


async def _read_gmail_content(
    client,
    user_id: str,
    now: datetime,
    selected_sources: list[str],
) -> Optional[PlatformContent]:
    """Read Gmail messages from platform_content."""
    try:
        # Filter to recent content (last 7 days — matches sync window)
        cutoff = (now - timedelta(days=7)).isoformat()

        query = (
            client.table("platform_content")
            .select("content, metadata, source_timestamp, resource_name, title, author")
            .eq("user_id", user_id)
            .eq("platform", "gmail")
            .eq("content_type", "email")
            .gt("fetched_at", cutoff)
            .or_(f"retained.eq.true,expires_at.gt.{now.isoformat()}")
            .order("source_timestamp", desc=True)
            .limit(30)
        )

        # Gmail selected_sources use "label:LABEL_ID" format
        label_sources = [s for s in selected_sources if s.startswith("label:")]
        if label_sources:
            query = query.in_("resource_id", label_sources)

        result = query.execute()
        items = result.data or []

        if not items:
            return PlatformContent(
                platform="gmail",
                items_count=0,
                content_summary="No recent Gmail messages in platform_content",
                raw_items=[],
                fetch_timestamp=now,
            )

        # Build content summary
        summary_lines = []
        for item in items[:10]:
            title = item.get("title", "No subject")
            author = item.get("author", "Unknown")
            summary_lines.append(f"- {title} (from: {author})")

        content_summary = "\n".join(summary_lines)
        if len(items) > 10:
            content_summary += f"\n... and {len(items) - 10} more messages"

        return PlatformContent(
            platform="gmail",
            items_count=len(items),
            content_summary=content_summary,
            raw_items=items,
            fetch_timestamp=now,
            time_range_start=now - timedelta(days=7),
            time_range_end=now,
        )

    except Exception as e:
        logger.warning(f"[SIGNAL] Gmail content read failed: {e}")
        return None


async def _read_slack_content(
    client,
    user_id: str,
    now: datetime,
    selected_sources: list[str],
) -> Optional[PlatformContent]:
    """Read Slack messages from platform_content."""
    try:
        # Filter to recent content (last 2 days)
        cutoff = (now - timedelta(days=2)).isoformat()

        query = (
            client.table("platform_content")
            .select("content, metadata, source_timestamp, resource_name, title, author")
            .eq("user_id", user_id)
            .eq("platform", "slack")
            .gt("fetched_at", cutoff)
            .or_(f"retained.eq.true,expires_at.gt.{now.isoformat()}")
            .order("source_timestamp", desc=True)
            .limit(100)
        )

        if selected_sources:
            query = query.in_("resource_id", selected_sources)

        result = query.execute()
        items = result.data or []

        if not items:
            return PlatformContent(
                platform="slack",
                items_count=0,
                content_summary="No recent Slack activity in platform_content",
                raw_items=[],
                fetch_timestamp=now,
            )

        # Build content summary
        summary_lines = []
        for item in items[:10]:
            text = (item.get("content") or "")[:100]
            author = item.get("author", "Unknown")
            summary_lines.append(f"- {author}: {text}")

        content_summary = "\n".join(summary_lines)
        if len(items) > 10:
            content_summary += f"\n... and {len(items) - 10} more messages"

        return PlatformContent(
            platform="slack",
            items_count=len(items),
            content_summary=content_summary,
            raw_items=items,
            fetch_timestamp=now,
            time_range_start=now - timedelta(days=2),
            time_range_end=now,
        )

    except Exception as e:
        logger.warning(f"[SIGNAL] Slack content read failed: {e}")
        return None


async def _read_notion_content(
    client,
    user_id: str,
    now: datetime,
    selected_sources: list[str],
) -> Optional[PlatformContent]:
    """Read Notion pages from platform_content."""
    try:
        query = (
            client.table("platform_content")
            .select("content, metadata, source_timestamp, resource_name, title, author")
            .eq("user_id", user_id)
            .eq("platform", "notion")
            .eq("content_type", "page")
            .or_(f"retained.eq.true,expires_at.gt.{now.isoformat()}")
            .order("fetched_at", desc=True)
            .limit(20)
        )

        if selected_sources:
            query = query.in_("resource_id", selected_sources)

        result = query.execute()
        items = result.data or []

        if not items:
            return PlatformContent(
                platform="notion",
                items_count=0,
                content_summary="No Notion pages in platform_content",
                raw_items=[],
                fetch_timestamp=now,
            )

        # Build content summary
        summary_lines = []
        for item in items[:10]:
            title = item.get("title") or item.get("resource_name") or "Untitled"
            content = (item.get("content") or "")[:100]
            summary_lines.append(f"- {title}: {content}")

        content_summary = "\n".join(summary_lines)
        if len(items) > 10:
            content_summary += f"\n... and {len(items) - 10} more pages"

        return PlatformContent(
            platform="notion",
            items_count=len(items),
            content_summary=content_summary,
            raw_items=items,
            fetch_timestamp=now,
        )

    except Exception as e:
        logger.warning(f"[SIGNAL] Notion content read failed: {e}")
        return None
