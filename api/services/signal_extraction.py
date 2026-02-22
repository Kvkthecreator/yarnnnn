"""
Signal Extraction Service

ADR-068: Signal-emergent deliverables
Architectural correction (2026-02-20): Signal processing reads LIVE platform content
via the same credential infrastructure as deliverable execution, not cached content.

This module fetches fresh content from connected platforms and determines what's
significant enough to warrant creating or triggering deliverables.

Key principles:
- Uses live platform API reads (same pattern as fetch_integration_source_data)
- Reasons about content significance, not absence/thresholds
- Aligns with strategic deliverable types (daily_strategy_reflection,
  intelligence_brief, deep_research)
- Handles cold-start gracefully (insufficient content → no_action)
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PlatformContent:
    """Live content fetched from a platform for signal processing."""

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
    Fetch live platform content for signal processing.

    This is the entry point for signal processing. It queries active platform
    connections and fetches recent content using live APIs (same infrastructure
    as deliverable execution).

    Args:
        client: Supabase client
        user_id: User UUID
        signals_filter: "all", "calendar_only", "non_calendar" (for cron scheduling)

    Returns:
        SignalSummary with live content from connected platforms
    """
    from integrations.core.client import MCPClientManager
    from integrations.core.google_client import get_google_client
    from integrations.core.tokens import get_token_manager

    now = datetime.utcnow()
    summary = SignalSummary()

    # Query active platform connections
    platforms_result = (
        client.table("platform_connections")
        .select("platform, status")
        .eq("user_id", user_id)
        .eq("status", "active")
        .execute()
    )

    if not platforms_result.data:
        logger.info(f"[SIGNAL] No active platforms for user {user_id}")
        return summary

    active_platforms = {p["platform"] for p in platforms_result.data}
    logger.info(f"[SIGNAL] User {user_id} has {len(active_platforms)} active platforms: {active_platforms}")

    # Fetch content from each platform based on filter mode
    if signals_filter in ("all", "calendar_only") and "google" in active_platforms:
        summary.calendar_content = await _fetch_calendar_content(
            client, user_id, now, get_google_client(), get_token_manager()
        )
        if summary.calendar_content:
            summary.total_items += summary.calendar_content.items_count
            summary.platforms_queried.append("calendar")

    if signals_filter in ("all", "non_calendar"):
        if "google" in active_platforms:
            summary.gmail_content = await _fetch_gmail_content(
                client, user_id, now, get_google_client(), get_token_manager()
            )
            if summary.gmail_content:
                summary.total_items += summary.gmail_content.items_count
                summary.platforms_queried.append("gmail")

        if "slack" in active_platforms:
            summary.slack_content = await _fetch_slack_content(
                client, user_id, now, MCPClientManager(), get_token_manager()
            )
            if summary.slack_content:
                summary.total_items += summary.slack_content.items_count
                summary.platforms_queried.append("slack")

        if "notion" in active_platforms:
            summary.notion_content = await _fetch_notion_content(
                client, user_id, now, MCPClientManager(), get_token_manager()
            )
            if summary.notion_content:
                summary.total_items += summary.notion_content.items_count
                summary.platforms_queried.append("notion")

    logger.info(
        f"[SIGNAL_EXTRACTION] user={user_id} filter={signals_filter}: "
        f"platforms={len(summary.platforms_queried)}, total_items={summary.total_items}"
    )

    return summary


async def _fetch_calendar_content(
    client,
    user_id: str,
    now: datetime,
    google_client,
    token_manager,
) -> Optional[PlatformContent]:
    """
    Fetch upcoming calendar events (next 7 days) from live Google Calendar API.

    Mirrors the pattern in fetch_integration_source_data() - uses platform_connections
    credentials and live API reads.
    """
    import os

    # Get Google connection
    conn_result = (
        client.table("platform_connections")
        .select("credentials_encrypted, refresh_token_encrypted")
        .eq("user_id", user_id)
        .eq("platform", "google")
        .eq("status", "active")
        .single()
        .execute()
    )

    if not conn_result.data:
        return None

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        logger.error("[SIGNAL] Google OAuth credentials not configured")
        return None

    refresh_token = token_manager.decrypt(conn_result.data["refresh_token_encrypted"])

    try:
        # Fetch next 7 days of calendar events
        time_min = now.isoformat() + "Z"
        time_max = (now + timedelta(days=7)).isoformat() + "Z"

        events = await google_client.list_calendar_events(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            time_min=time_min,
            time_max=time_max,
            max_results=50,
        )

        if not events:
            return PlatformContent(
                platform="calendar",
                items_count=0,
                content_summary="No upcoming calendar events in next 7 days",
                raw_items=[],
                fetch_timestamp=now,
                time_range_start=now,
                time_range_end=now + timedelta(days=7),
            )

        # Build content summary for LLM reasoning
        summary_lines = []
        for event in events[:10]:  # Top 10 for summary
            summary = event.get("summary", "Untitled")
            start = event.get("start", {}).get("dateTime", event.get("start", {}).get("date", ""))
            attendees = len(event.get("attendees", []))
            summary_lines.append(f"- {summary} ({start}) - {attendees} attendees")

        content_summary = "\n".join(summary_lines)
        if len(events) > 10:
            content_summary += f"\n... and {len(events) - 10} more events"

        return PlatformContent(
            platform="calendar",
            items_count=len(events),
            content_summary=content_summary,
            raw_items=events,
            fetch_timestamp=now,
            time_range_start=now,
            time_range_end=now + timedelta(days=7),
        )

    except Exception as e:
        logger.warning(f"[SIGNAL] Calendar content fetch failed: {e}")
        return None


async def _fetch_gmail_content(
    client,
    user_id: str,
    now: datetime,
    google_client,
    token_manager,
) -> Optional[PlatformContent]:
    """
    Fetch recent Gmail messages (last 3 days) from live Gmail API.

    Focus: Recent email activity that might contain significant developments,
    decisions, or topics worth synthesizing.
    """
    import os

    # Get Google connection
    conn_result = (
        client.table("platform_connections")
        .select("credentials_encrypted, refresh_token_encrypted")
        .eq("user_id", user_id)
        .eq("platform", "google")
        .eq("status", "active")
        .single()
        .execute()
    )

    if not conn_result.data:
        return None

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        logger.error("[SIGNAL] Google OAuth credentials not configured")
        return None

    refresh_token = token_manager.decrypt(conn_result.data["refresh_token_encrypted"])

    try:
        # Fetch last 3 days of inbox messages
        after_date = (now - timedelta(days=3)).strftime("%Y/%m/%d")
        query = f"in:inbox after:{after_date}"

        messages = await google_client.list_gmail_messages(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            query=query,
            max_results=30,
        )

        if not messages:
            return PlatformContent(
                platform="gmail",
                items_count=0,
                content_summary="No recent inbox messages in last 3 days",
                raw_items=[],
                fetch_timestamp=now,
                time_range_start=now - timedelta(days=3),
                time_range_end=now,
            )

        # Build content summary
        summary_lines = []
        for msg in messages[:10]:
            subject = next((h["value"] for h in msg.get("payload", {}).get("headers", []) if h["name"] == "Subject"), "No subject")
            from_email = next((h["value"] for h in msg.get("payload", {}).get("headers", []) if h["name"] == "From"), "Unknown")
            summary_lines.append(f"- {subject} (from: {from_email})")

        content_summary = "\n".join(summary_lines)
        if len(messages) > 10:
            content_summary += f"\n... and {len(messages) - 10} more messages"

        return PlatformContent(
            platform="gmail",
            items_count=len(messages),
            content_summary=content_summary,
            raw_items=messages,
            fetch_timestamp=now,
            time_range_start=now - timedelta(days=3),
            time_range_end=now,
        )

    except Exception as e:
        logger.warning(f"[SIGNAL] Gmail content fetch failed: {e}")
        return None


async def _fetch_slack_content(
    client,
    user_id: str,
    now: datetime,
    mcp_manager,
    token_manager,
) -> Optional[PlatformContent]:
    """
    Fetch recent Slack activity (last 2 days) via MCP Slack server.

    Focus: Channel discussions, mentions, threads that might indicate
    strategic developments or decisions.
    """
    # Get Slack connection
    conn_result = (
        client.table("platform_connections")
        .select("credentials_encrypted, settings")
        .eq("user_id", user_id)
        .eq("platform", "slack")
        .eq("status", "active")
        .single()
        .execute()
    )

    if not conn_result.data:
        return None

    credentials = token_manager.decrypt(conn_result.data["credentials_encrypted"])
    settings = conn_result.data.get("settings", {})
    selected_channels = settings.get("selected_channels", [])

    if not selected_channels:
        return PlatformContent(
            platform="slack",
            items_count=0,
            content_summary="No Slack channels selected for monitoring",
            raw_items=[],
            fetch_timestamp=now,
        )

    try:
        slack_client = mcp_manager.get_client("slack")
        if not slack_client:
            return None

        # Fetch recent messages from selected channels (last 2 days)
        oldest_ts = (now - timedelta(days=2)).timestamp()
        all_messages = []

        for channel_id in selected_channels[:5]:  # Cap at 5 channels for performance
            try:
                messages = await slack_client.read_channel(
                    channel_id=channel_id,
                    oldest=str(oldest_ts),
                    limit=20,
                )
                all_messages.extend(messages)
            except Exception as e:
                logger.warning(f"[SIGNAL] Failed to read Slack channel {channel_id}: {e}")
                continue

        if not all_messages:
            return PlatformContent(
                platform="slack",
                items_count=0,
                content_summary=f"No recent activity in {len(selected_channels)} monitored channels",
                raw_items=[],
                fetch_timestamp=now,
                time_range_start=now - timedelta(days=2),
                time_range_end=now,
            )

        # Build content summary
        summary_lines = []
        for msg in all_messages[:10]:
            text = msg.get("text", "")[:100]
            user = msg.get("user", "Unknown")
            summary_lines.append(f"- {user}: {text}")

        content_summary = "\n".join(summary_lines)
        if len(all_messages) > 10:
            content_summary += f"\n... and {len(all_messages) - 10} more messages"

        return PlatformContent(
            platform="slack",
            items_count=len(all_messages),
            content_summary=content_summary,
            raw_items=all_messages,
            fetch_timestamp=now,
            time_range_start=now - timedelta(days=2),
            time_range_end=now,
        )

    except Exception as e:
        logger.warning(f"[SIGNAL] Slack content fetch failed: {e}")
        return None


async def _fetch_notion_content(
    client,
    user_id: str,
    now: datetime,
    mcp_manager,
    token_manager,
) -> Optional[PlatformContent]:
    """
    Fetch recent Notion activity (last 7 days) via direct Notion API.

    Focus: Page edits, new pages, task updates that might indicate
    strategic shifts or emerging topics.
    """
    # Get Notion connection
    conn_result = (
        client.table("platform_connections")
        .select("credentials_encrypted, settings")
        .eq("user_id", user_id)
        .eq("platform", "notion")
        .eq("status", "active")
        .single()
        .execute()
    )

    if not conn_result.data:
        return None

    credentials = token_manager.decrypt(conn_result.data["credentials_encrypted"])
    settings = conn_result.data.get("settings", {})
    selected_pages = settings.get("selected_pages", [])

    if not selected_pages:
        return PlatformContent(
            platform="notion",
            items_count=0,
            content_summary="No Notion pages selected for monitoring",
            raw_items=[],
            fetch_timestamp=now,
        )

    try:
        # Note: Notion API implementation would go here
        # For now, return placeholder
        logger.info("[SIGNAL] Notion content fetch not yet implemented")
        return PlatformContent(
            platform="notion",
            items_count=0,
            content_summary="Notion content fetch pending implementation",
            raw_items=[],
            fetch_timestamp=now,
        )

    except Exception as e:
        logger.warning(f"[SIGNAL] Notion content fetch failed: {e}")
        return None
