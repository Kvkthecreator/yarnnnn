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
    platform_activity: dict = field(default_factory=dict)  # counts per platform
    has_signals: bool = False


async def extract_signal_summary(client, user_id: str) -> SignalSummary:
    """
    Extract behavioral signals from live platform APIs for a user.

    Queries Google Calendar and Gmail APIs directly (NOT filesystem_items cache).
    Decrypts credentials from platform_connections.

    Args:
        client: Supabase service-role client
        user_id: The user to extract signals for

    Returns:
        SignalSummary with extracted signals. Empty summary if no platforms connected.
    """
    now = datetime.now(timezone.utc)
    summary = SignalSummary(user_id=user_id, extracted_at=now)

    # Extract calendar signals (live Google Calendar API)
    try:
        calendar_signals = await _extract_calendar_signals(client, user_id, now)
        summary.calendar_signals = calendar_signals
    except Exception as e:
        logger.warning(f"[SIGNAL_EXTRACTION] Calendar signal extraction failed for {user_id}: {e}")

    # Extract silence signals (live Gmail API)
    try:
        silence_signals = await _extract_silence_signals(client, user_id, now)
        summary.silence_signals = silence_signals
    except Exception as e:
        logger.warning(f"[SIGNAL_EXTRACTION] Silence signal extraction failed for {user_id}: {e}")

    summary.has_signals = bool(summary.calendar_signals or summary.silence_signals)

    logger.info(
        f"[SIGNAL_EXTRACTION] user={user_id}: "
        f"calendar={len(summary.calendar_signals)}, "
        f"silence={len(summary.silence_signals)}"
    )

    return summary


async def _extract_calendar_signals(
    client, user_id: str, now: datetime
) -> list[CalendarSignal]:
    """Extract upcoming calendar events from live Google Calendar API."""
    from integrations.core.google_client import get_google_client
    from integrations.core.tokens import get_token_manager

    # Get user's Google Calendar connection
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

    Note: Simplified Phase 1 implementation. Full thread tracking requires
    Gmail API thread history analysis to determine last user-sent message.
    For now, returns empty — silence signals deferred to Phase 2.
    """
    # TODO Phase 2: Implement Gmail thread silence detection via live API
    # Requires:
    # 1. Query Gmail threads from selected labels (INBOX, etc.)
    # 2. For each thread, find last message
    # 3. Check if user sent a reply after last received message
    # 4. If not, compute days since last received
    # 5. Return threads silent >= SILENCE_THRESHOLD_DAYS

    return []
