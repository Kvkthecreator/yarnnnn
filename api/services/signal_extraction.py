"""
Signal Extraction Service — ADR-068

Deterministic behavioral signal extraction from filesystem_items (Layer 3).
No LLM involved. Reads platform cache metadata to produce a structured
SignalSummary that the signal processing function reasons over.

Signal types extracted:
- CalendarSignal: upcoming events in the next 48h with attendee context
- SilenceSignal: Gmail threads where user has no outbound reply in N days

These are the signals required for the first signal-emergent deliverable type:
meeting_prep with commitment context (ADR-068 Phase 1).
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
    start_time: str                  # ISO8601 from metadata
    attendee_emails: list[str]       # All attendees
    location: Optional[str]
    calendar_id: str                 # The resource_id (calendar)
    hours_until: float               # Computed at extraction time


@dataclass
class SilenceSignal:
    """A Gmail thread that has gone quiet — no user-sent message in N days."""
    thread_subject: str
    sender: str                      # Who the thread is with (from: header)
    last_received: str               # ISO8601 of last incoming message
    days_silent: float               # Days since last message in thread
    label_id: str                    # The Gmail label/resource


@dataclass
class SignalSummary:
    """
    Structured behavioral signal extracted from a user's platform cache.

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
    Extract behavioral signals from filesystem_items for a user.

    Reads only metadata columns — not content. Deterministic, no LLM.

    Args:
        client: Supabase service-role client
        user_id: The user to extract signals for

    Returns:
        SignalSummary with extracted signals. Empty summary if no platform data.
    """
    now = datetime.now(timezone.utc)
    summary = SignalSummary(user_id=user_id, extracted_at=now)

    try:
        calendar_signals = await _extract_calendar_signals(client, user_id, now)
        summary.calendar_signals = calendar_signals
    except Exception as e:
        logger.warning(f"[SIGNAL_EXTRACTION] Calendar signal extraction failed for {user_id}: {e}")

    try:
        silence_signals = await _extract_silence_signals(client, user_id, now)
        summary.silence_signals = silence_signals
    except Exception as e:
        logger.warning(f"[SIGNAL_EXTRACTION] Silence signal extraction failed for {user_id}: {e}")

    try:
        summary.platform_activity = await _extract_platform_activity(client, user_id)
    except Exception as e:
        logger.warning(f"[SIGNAL_EXTRACTION] Platform activity extraction failed for {user_id}: {e}")

    summary.has_signals = bool(summary.calendar_signals or summary.silence_signals)

    logger.info(
        f"[SIGNAL_EXTRACTION] user={user_id}: "
        f"calendar={len(summary.calendar_signals)}, "
        f"silence={len(summary.silence_signals)}, "
        f"activity={summary.platform_activity}"
    )

    return summary


async def _extract_calendar_signals(
    client, user_id: str, now: datetime
) -> list[CalendarSignal]:
    """Extract upcoming calendar events within the lookahead window."""
    lookahead_cutoff = (now + timedelta(hours=CALENDAR_LOOKAHEAD_HOURS)).isoformat()

    result = (
        client.table("filesystem_items")
        .select("item_id, resource_id, resource_name, metadata, source_timestamp")
        .eq("user_id", user_id)
        .eq("platform", "calendar")
        .eq("content_type", "event")
        .gte("source_timestamp", now.isoformat())
        .lte("source_timestamp", lookahead_cutoff)
        .order("source_timestamp")
        .execute()
    )

    signals = []
    for row in (result.data or []):
        meta = row.get("metadata") or {}
        event_id = meta.get("event_id") or row.get("item_id", "")
        start_time = meta.get("start") or row.get("source_timestamp", "")
        attendees = meta.get("attendees") or []
        title = row.get("resource_name", "Untitled event")

        # Compute hours until event
        hours_until = 0.0
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            hours_until = (start_dt - now).total_seconds() / 3600
        except (ValueError, TypeError):
            pass

        signals.append(CalendarSignal(
            event_id=event_id,
            title=title,
            start_time=start_time,
            attendee_emails=[e for e in attendees if e],
            location=meta.get("location"),
            calendar_id=row.get("resource_id", ""),
            hours_until=round(hours_until, 1),
        ))

    return signals


async def _extract_silence_signals(
    client, user_id: str, now: datetime
) -> list[SilenceSignal]:
    """
    Extract Gmail threads that have gone quiet.

    A thread is 'silent' if the most recent item in that thread is older
    than SILENCE_THRESHOLD_DAYS. We identify threads by subject/sender
    using the resource_id (label) + metadata grouping.

    Note: This is an approximation — filesystem_items stores individual emails,
    not threaded conversations. We group by subject prefix to approximate threads.
    """
    silence_cutoff = (now - timedelta(days=SILENCE_THRESHOLD_DAYS)).isoformat()

    # Fetch recent Gmail items, ordered by resource and timestamp
    result = (
        client.table("filesystem_items")
        .select("item_id, resource_id, resource_name, metadata, source_timestamp")
        .eq("user_id", user_id)
        .eq("platform", "gmail")
        .eq("content_type", "email")
        .order("source_timestamp", desc=True)
        .limit(100)
        .execute()
    )

    if not result.data:
        return []

    # Group by subject (resource_name) to approximate threads
    # Take the most recent email per subject
    seen_subjects: dict[str, dict] = {}
    for row in result.data:
        subject = row.get("resource_name", "")
        if subject and subject not in seen_subjects:
            seen_subjects[subject] = row

    signals = []
    for subject, row in seen_subjects.items():
        source_ts = row.get("source_timestamp")
        if not source_ts:
            continue

        # Only surface threads that have gone quiet
        try:
            msg_dt = datetime.fromisoformat(source_ts.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue

        if msg_dt.isoformat() > silence_cutoff:
            continue  # Still active

        days_silent = (now - msg_dt).total_seconds() / 86400
        meta = row.get("metadata") or {}
        sender = meta.get("from", "")

        signals.append(SilenceSignal(
            thread_subject=subject,
            sender=sender,
            last_received=source_ts,
            days_silent=round(days_silent, 1),
            label_id=row.get("resource_id", ""),
        ))

        if len(signals) >= SILENCE_MAX_THREADS:
            break

    return signals


async def _extract_platform_activity(client, user_id: str) -> dict:
    """Count cached items per platform — lightweight activity indicator."""
    result = (
        client.table("filesystem_items")
        .select("platform")
        .eq("user_id", user_id)
        .execute()
    )

    counts: dict[str, int] = {}
    for row in (result.data or []):
        platform = row.get("platform", "unknown")
        counts[platform] = counts.get(platform, 0) + 1

    return counts
