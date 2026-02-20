"""
Signal Extraction Service — ADR-068

Behavioral signal extraction from **live platform APIs** (NOT filesystem_items cache).

The whole point of hourly cron execution is to get the fresh, current state of
the user's external world. Signal processing compares this live snapshot against
YARNNN's internal state (Memory, Activity, existing deliverables) to determine
what proactive actions are warranted.

Architecture:
- Queries live Google Calendar API for upcoming events (next 48h)
- Queries live Gmail API for quiet threads (no reply in 5+ days)
- Decrypts credentials from platform_connections
- Returns structured SignalSummary (not raw platform data)
- No LLM involved — deterministic extraction only

This is the opposite of filesystem_items (which is a stale cache for conversational
search). Signal processing must see the real-time state to detect time-sensitive
signals like "meeting in 6 hours" or "thread went silent yesterday".
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Windows for signal detection
CALENDAR_LOOKAHEAD_HOURS = 48       # Surface events within this window
SILENCE_THRESHOLD_DAYS = 5          # Gmail threads quiet for this long
SILENCE_MAX_THREADS = 10            # Cap on silence signals per run
SLACK_SILENCE_DAYS = 7              # Slack channels quiet for this long
SLACK_MAX_SIGNALS = 10              # Cap on Slack signals per run
NOTION_STALE_DAYS = 14              # Notion pages not edited in this long
NOTION_MAX_SIGNALS = 10             # Cap on Notion signals per run


@dataclass
class CalendarSignal:
    """An upcoming calendar event that may warrant a proactive brief."""
    event_id: str
    title: str
    start_time: str                  # ISO8601
    attendee_emails: list[str]       # All attendees
    location: Optional[str]
    calendar_id: str
    hours_until: float               # Computed at extraction time


@dataclass
class SilenceSignal:
    """A Gmail thread that has gone quiet — no user-sent message in N days."""
    thread_subject: str
    sender: str                      # Who the thread is with (from: header)
    last_received: str               # ISO8601 of last incoming message
    days_silent: float               # Days since last message in thread
    label_id: str                    # The Gmail label


@dataclass
class SlackSignal:
    """A Slack channel or DM that has gone quiet or needs response."""
    channel_id: str
    channel_name: str
    signal_type: str                 # "channel_silence" or "unanswered_dm"
    last_message_ts: str             # Slack timestamp of last message
    days_silent: float               # Days since last activity
    last_sender: Optional[str]       # Who sent last message (for DMs)
    message_preview: Optional[str]   # First 100 chars of last message


@dataclass
class NotionSignal:
    """A Notion page or task that needs attention."""
    page_id: str
    page_title: str
    signal_type: str                 # "stale_page" or "overdue_task"
    last_edited: str                 # ISO8601 of last edit
    days_stale: float                # Days since last edit
    database_name: Optional[str]     # Parent database name if applicable
    status: Optional[str]            # Status property value (for tasks)


@dataclass
class SignalSummary:
    """
    Structured behavioral signal extracted from live platform APIs.

    Consumed by signal_processing.py to decide what (if anything) to create.
    Content is compact and structured — not raw platform data.
    """
    user_id: str
    extracted_at: datetime
    calendar_signals: list[CalendarSignal] = field(default_factory=list)
    silence_signals: list[SilenceSignal] = field(default_factory=list)
    slack_signals: list[SlackSignal] = field(default_factory=list)
    notion_signals: list[NotionSignal] = field(default_factory=list)
    platform_activity: dict = field(default_factory=dict)  # counts per platform
    has_signals: bool = False


async def extract_signal_summary(
    client, user_id: str, signals_filter: str = "all"
) -> SignalSummary:
    """
    Extract behavioral signals from live platform APIs for a user.

    Queries all connected platforms directly (NOT filesystem_items cache):
    - Google Calendar (events in next 48h)
    - Gmail (silent threads)
    - Slack (silent channels)
    - Notion (stale pages, overdue tasks)

    Args:
        client: Supabase service-role client
        user_id: The user to extract signals for
        signals_filter: Which signals to extract:
            - "all": Extract all signal types (default)
            - "calendar_only": Extract only calendar signals (hourly cron)
            - "non_calendar": Extract only non-calendar signals (daily cron)

    Returns:
        SignalSummary with extracted signals. Empty summary if no platforms connected.
    """
    now = datetime.now(timezone.utc)
    summary = SignalSummary(user_id=user_id, extracted_at=now)

    # Extract calendar signals (live Google Calendar API)
    if signals_filter in ("all", "calendar_only"):
        try:
            calendar_signals = await _extract_calendar_signals(client, user_id, now)
            summary.calendar_signals = calendar_signals
        except Exception as e:
            logger.warning(f"[SIGNAL_EXTRACTION] Calendar signal extraction failed for {user_id}: {e}")

    # Extract silence signals (live Gmail API)
    if signals_filter in ("all", "non_calendar"):
        try:
            silence_signals = await _extract_silence_signals(client, user_id, now)
            summary.silence_signals = silence_signals
        except Exception as e:
            logger.warning(f"[SIGNAL_EXTRACTION] Silence signal extraction failed for {user_id}: {e}")

    # Extract Slack signals (live Slack MCP)
    if signals_filter in ("all", "non_calendar"):
        try:
            slack_signals = await _extract_slack_signals(client, user_id, now)
            summary.slack_signals = slack_signals
        except Exception as e:
            logger.warning(f"[SIGNAL_EXTRACTION] Slack signal extraction failed for {user_id}: {e}")

    # Extract Notion signals (live Notion API)
    if signals_filter in ("all", "non_calendar"):
        try:
            notion_signals = await _extract_notion_signals(client, user_id, now)
            summary.notion_signals = notion_signals
        except Exception as e:
            logger.warning(f"[SIGNAL_EXTRACTION] Notion signal extraction failed for {user_id}: {e}")

    summary.has_signals = bool(
        summary.calendar_signals or
        summary.silence_signals or
        summary.slack_signals or
        summary.notion_signals
    )

    logger.info(
        f"[SIGNAL_EXTRACTION] user={user_id} filter={signals_filter}: "
        f"calendar={len(summary.calendar_signals)}, "
        f"silence={len(summary.silence_signals)}, "
        f"slack={len(summary.slack_signals)}, "
        f"notion={len(summary.notion_signals)}"
    )

    return summary


async def _extract_calendar_signals(
    client, user_id: str, now: datetime
) -> list[CalendarSignal]:
    """Extract upcoming calendar events from live Google Calendar API."""
    from integrations.core.google_client import get_google_client
    from integrations.core.tokens import get_token_manager

    # Get user's Gmail/Google connection (Calendar uses same OAuth scope)
    conn_result = (
        client.table("platform_connections")
        .select("credentials_encrypted, refresh_token_encrypted, settings")
        .eq("user_id", user_id)
        .eq("platform", "google")
        .eq("status", "active")
        .single()
        .execute()
    )

    if not conn_result.data:
        return []  # No Google connection

    token_manager = get_token_manager()
    refresh_token = token_manager.decrypt(conn_result.data["refresh_token_encrypted"])

    # Get OAuth credentials from environment (same as other Google API calls)
    import os
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        logger.error("[SIGNAL_EXTRACTION] Google OAuth credentials not configured")
        return []

    # Query live Google Calendar API for events in next 48h
    google_client = get_google_client()
    time_min = now.isoformat()
    time_max = (now + timedelta(hours=CALENDAR_LOOKAHEAD_HOURS)).isoformat()

    events = await google_client.list_calendar_events(
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token,
        calendar_id="primary",
        time_min=time_min,
        time_max=time_max,
        max_results=50
    )

    signals = []
    for event in events:
        event_id = event.get("id", "")
        title = event.get("summary", "Untitled event")
        start = event.get("start", {})
        start_time = start.get("dateTime") or start.get("date", "")

        attendees = event.get("attendees") or []
        attendee_emails = [a.get("email") for a in attendees if a.get("email")]

        location = event.get("location")

        # Compute hours until event
        hours_until = 0.0
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            hours_until = (start_dt - now).total_seconds() / 3600
        except (ValueError, TypeError):
            pass

        # Only include events with external attendees (not solo events)
        if len(attendee_emails) > 0:
            signals.append(CalendarSignal(
                event_id=event_id,
                title=title,
                start_time=start_time,
                attendee_emails=attendee_emails,
                location=location,
                calendar_id="primary",
                hours_until=hours_until,
            ))

    return signals


async def _extract_silence_signals(
    client, user_id: str, now: datetime
) -> list[SilenceSignal]:
    """
    Extract Gmail threads that have gone silent (no user reply in N days).

    ADR-068 Phase 4: Full implementation using live Gmail API.
    Queries threads from INBOX, analyzes message history to detect threads
    where user has not replied in SILENCE_THRESHOLD_DAYS.
    """
    from integrations.core.google_client import get_google_client
    from integrations.core.tokens import get_token_manager

    # Get user's Google connection (Gmail uses Google OAuth)
    conn_result = (
        client.table("platform_connections")
        .select("credentials_encrypted, refresh_token_encrypted, settings")
        .eq("user_id", user_id)
        .eq("platform", "google")
        .eq("status", "active")
        .single()
        .execute()
    )

    if not conn_result.data:
        return []  # No Google connection

    token_manager = get_token_manager()
    refresh_token = token_manager.decrypt(conn_result.data["refresh_token_encrypted"])

    # Get OAuth credentials from environment
    import os
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        logger.error("[SIGNAL_EXTRACTION] Google OAuth credentials not configured")
        return []

    # Query live Gmail API for threads in INBOX from last 14 days
    google_client = get_google_client()
    cutoff_date = (now - timedelta(days=SILENCE_THRESHOLD_DAYS)).strftime("%Y/%m/%d")

    # Gmail query: messages in INBOX from the last 14 days, not sent by user
    query = f"in:inbox after:{cutoff_date} -from:me"

    try:
        messages = await google_client.list_gmail_messages(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            query=query,
            max_results=50,  # Limit to top 50 threads for cost control
        )
    except Exception as e:
        logger.warning(f"[SIGNAL_EXTRACTION] Gmail API query failed: {e}")
        return []

    # Group messages by thread_id and analyze each thread
    thread_ids = list(set(msg.get("threadId") for msg in messages if msg.get("threadId")))
    signals = []

    for thread_id in thread_ids[:SILENCE_MAX_THREADS]:  # Cap at 10 threads
        try:
            thread = await google_client.get_gmail_thread(
                thread_id=thread_id,
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
            )

            # Analyze thread messages to determine silence
            thread_messages = thread.get("messages", [])
            if not thread_messages:
                continue

            # Find last message timestamp and check if user replied
            last_msg = thread_messages[-1]
            last_msg_headers = {
                h["name"].lower(): h["value"]
                for h in last_msg.get("payload", {}).get("headers", [])
            }

            sender = last_msg_headers.get("from", "Unknown")
            subject = last_msg_headers.get("subject", "No subject")
            last_msg_time_ms = int(last_msg.get("internalDate", 0))
            last_msg_time = datetime.fromtimestamp(last_msg_time_ms / 1000, tz=timezone.utc)

            # Check if last message was FROM user (then thread is not silent)
            # User's email is in the connection settings or we can check label_ids
            # For simplicity, check if last message has SENT label
            last_msg_labels = last_msg.get("labelIds", [])
            if "SENT" in last_msg_labels:
                # User sent last message - not silent
                continue

            # Compute days since last received message
            days_silent = (now - last_msg_time).total_seconds() / 86400

            if days_silent >= SILENCE_THRESHOLD_DAYS:
                signals.append(SilenceSignal(
                    thread_subject=subject,
                    sender=sender,
                    last_received=last_msg_time.isoformat(),
                    days_silent=days_silent,
                    label_id=thread_id,  # Store thread_id in label_id field
                ))

        except Exception as e:
            logger.warning(f"[SIGNAL_EXTRACTION] Failed to analyze thread {thread_id}: {e}")
            continue

    logger.info(f"[SIGNAL_EXTRACTION] Found {len(signals)} silence signals for {user_id}")
    return signals
"""
Slack and Notion signal extraction functions.

Temporary file for implementation - will be integrated into signal_extraction.py
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Import constants from signal_extraction.py
SLACK_SILENCE_DAYS = 7
SLACK_MAX_SIGNALS = 10
NOTION_STALE_DAYS = 14
NOTION_MAX_SIGNALS = 10


async def _extract_slack_signals(
    client, user_id: str, now: datetime
) -> list:
    """
    Extract Slack signals: silent channels and unanswered DMs.

    Uses MCP Slack server via MCPClientManager to query:
    - Channel message history (last 7 days)
    - DM conversations awaiting response

    Returns list of SlackSignal objects.
    """
    from dataclasses import dataclass
    from typing import Optional

    @dataclass
    class SlackSignal:
        channel_id: str
        channel_name: str
        signal_type: str
        last_message_ts: str
        days_silent: float
        last_sender: Optional[str]
        message_preview: Optional[str]

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
        return []  # No Slack connection

    settings = conn_result.data.get("settings", {})
    selected_channels = settings.get("selected_channels", [])

    if not selected_channels:
        return []  # No channels configured

    # Query Slack via MCP
    from integrations.mcp.client_manager import MCPClientManager

    signals = []
    mcp_manager = MCPClientManager()

    try:
        # Get Slack client
        slack_client = await mcp_manager.get_client("slack")

        if not slack_client:
            logger.warning(f"[SIGNAL_EXTRACTION] Slack MCP client not available for {user_id}")
            return []

        cutoff_time = now - timedelta(days=SLACK_SILENCE_DAYS)

        # Check each selected channel for silence
        for channel in selected_channels[:SLACK_MAX_SIGNALS]:
            channel_id = channel.get("id")
            channel_name = channel.get("name", "unknown")

            try:
                # Call slack_read_channel via MCP
                result = await slack_client.call_tool(
                    "slack_read_channel",
                    {
                        "channel_id": channel_id,
                        "limit": 20,  # Last 20 messages
                    }
                )

                messages = result.get("messages", [])

                if not messages:
                    # Channel has no messages - treat as silent
                    signals.append(SlackSignal(
                        channel_id=channel_id,
                        channel_name=channel_name,
                        signal_type="channel_silence",
                        last_message_ts="",
                        days_silent=SLACK_SILENCE_DAYS,
                        last_sender=None,
                        message_preview=None,
                    ))
                    continue

                # Find last message timestamp
                last_msg = messages[0]  # MCP returns newest first
                last_ts = last_msg.get("ts", "")
                last_text = last_msg.get("text", "")
                last_user = last_msg.get("user")

                # Parse Slack timestamp (Unix epoch with decimal)
                try:
                    last_msg_time = datetime.fromtimestamp(float(last_ts), tz=timezone.utc)
                    days_silent = (now - last_msg_time).total_seconds() / 86400

                    if days_silent >= SLACK_SILENCE_DAYS:
                        signals.append(SlackSignal(
                            channel_id=channel_id,
                            channel_name=channel_name,
                            signal_type="channel_silence",
                            last_message_ts=last_ts,
                            days_silent=days_silent,
                            last_sender=last_user,
                            message_preview=last_text[:100] if last_text else None,
                        ))
                except (ValueError, TypeError):
                    pass

            except Exception as e:
                logger.warning(f"[SIGNAL_EXTRACTION] Failed to query Slack channel {channel_id}: {e}")
                continue

    finally:
        await mcp_manager.cleanup()

    logger.info(f"[SIGNAL_EXTRACTION] Found {len(signals)} Slack signals for {user_id}")
    return signals


async def _extract_notion_signals(
    client, user_id: str, now: datetime
) -> list:
    """
    Extract Notion signals: stale pages and overdue tasks.

    Uses live Notion API to query:
    - Pages not edited in 14+ days (from selected databases)
    - Database items with status != "Done" and due_date < today

    Returns list of NotionSignal objects.
    """
    from dataclasses import dataclass
    from typing import Optional

    @dataclass
    class NotionSignal:
        page_id: str
        page_title: str
        signal_type: str
        last_edited: str
        days_stale: float
        database_name: Optional[str]
        status: Optional[str]

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
        return []  # No Notion connection

    settings = conn_result.data.get("settings", {})
    selected_pages = settings.get("selected_pages", [])

    if not selected_pages:
        return []  # No pages configured

    # Decrypt Notion integration token
    from integrations.core.tokens import get_token_manager

    token_manager = get_token_manager()
    notion_token = token_manager.decrypt(conn_result.data["credentials_encrypted"])

    # Query Notion API
    from integrations.notion.client import NotionAPIClient

    notion_client = NotionAPIClient(notion_token)
    signals = []

    cutoff_time = now - timedelta(days=NOTION_STALE_DAYS)

    # Check each selected page for staleness
    for page in selected_pages[:NOTION_MAX_SIGNALS]:
        page_id = page.get("id")
        page_name = page.get("name", "Untitled")

        try:
            # Get page metadata
            page_data = await notion_client.get_page(page_id)

            last_edited_str = page_data.get("last_edited_time", "")

            # Parse last edited time
            try:
                last_edited = datetime.fromisoformat(last_edited_str.replace("Z", "+00:00"))
                days_stale = (now - last_edited).total_seconds() / 86400

                if days_stale >= NOTION_STALE_DAYS:
                    # Check if this is a database (for task detection)
                    parent = page_data.get("parent", {})
                    database_id = parent.get("database_id")

                    signal_type = "stale_page"
                    status = None
                    database_name = None

                    # If part of a database, check for overdue task properties
                    if database_id:
                        try:
                            database_data = await notion_client.get_database(database_id)
                            database_name = database_data.get("title", [{}])[0].get("plain_text", "Database")

                            # Check for Status and Due Date properties
                            props = page_data.get("properties", {})
                            status_prop = props.get("Status", {})
                            status = status_prop.get("status", {}).get("name") if status_prop else None

                            due_date_prop = props.get("Due Date", {}) or props.get("Due", {})
                            due_date_str = due_date_prop.get("date", {}).get("start") if due_date_prop else None

                            if due_date_str and status and status != "Done":
                                due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
                                if due_date < now:
                                    signal_type = "overdue_task"
                        except Exception:
                            pass  # Database query failed, treat as stale page

                    signals.append(NotionSignal(
                        page_id=page_id,
                        page_title=page_name,
                        signal_type=signal_type,
                        last_edited=last_edited_str,
                        days_stale=days_stale,
                        database_name=database_name,
                        status=status,
                    ))

            except (ValueError, TypeError):
                pass

        except Exception as e:
            logger.warning(f"[SIGNAL_EXTRACTION] Failed to query Notion page {page_id}: {e}")
            continue

    logger.info(f"[SIGNAL_EXTRACTION] Found {len(signals)} Notion signals for {user_id}")
    return signals
