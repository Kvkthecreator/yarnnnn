"""
Platform Limits Service

ADR-100: Simplified 2-tier monetization (Free + Pro).
ADR-077: Widened source limits to support richer content accumulation.

Tier Structure (ADR-100, 2026-03-09):
- Free: 5 slack/5 gmail/10 notion, all 4 platforms, 1x/day sync, 50 messages/month, 2 deliverables
- Pro ($19/mo, Early Bird $9/mo): unlimited sources, all platforms, hourly sync, unlimited messages, 10 deliverables

Key gates (by cost impact):
1. Monthly messages — user-understandable proxy for Anthropic API spend
2. Active deliverables — each is a recurring Sonnet call
3. Source count — controls platform_content volume
4. Sync frequency — controls API call frequency (lowest cost impact)
"""

import logging
from typing import Optional, Literal

logger = logging.getLogger(__name__)
from dataclasses import dataclass
from datetime import datetime, timedelta
import pytz


SyncFrequency = Literal["1x_daily", "2x_daily", "4x_daily", "hourly"]


@dataclass
class PlatformLimits:
    """Resource limits for a user tier (ADR-100)."""
    slack_channels: int       # -1 for unlimited
    gmail_labels: int         # -1 for unlimited
    notion_pages: int         # -1 for unlimited
    calendars: int            # -1 for unlimited (no source selection for calendar)
    total_platforms: int
    sync_frequency: SyncFrequency
    monthly_messages: int     # -1 for unlimited (ADR-100: replaces daily_token_budget)
    active_deliverables: int  # -1 for unlimited


# Tier definitions (ADR-100: 2-tier model, 2026-03-09)
TIER_LIMITS = {
    "free": PlatformLimits(
        slack_channels=5,
        gmail_labels=5,
        notion_pages=10,
        calendars=-1,            # No source selection for calendar
        total_platforms=4,       # All platforms open
        sync_frequency="1x_daily",
        monthly_messages=50,
        active_deliverables=2,
    ),
    "pro": PlatformLimits(
        slack_channels=-1,       # Unlimited
        gmail_labels=-1,
        notion_pages=-1,
        calendars=-1,
        total_platforms=4,
        sync_frequency="hourly",
        monthly_messages=-1,     # Unlimited
        active_deliverables=10,
    ),
}

# Provider to limit field mapping
PROVIDER_LIMIT_MAP = {
    "slack": "slack_channels",
    "gmail": "gmail_labels",
    "notion": "notion_pages",
    "calendar": "calendars",
}

# Sync frequency schedules (times in user's timezone)
SYNC_SCHEDULES = {
    "1x_daily": ["08:00"],                              # Morning only
    "2x_daily": ["08:00", "18:00"],                     # Morning + evening
    "4x_daily": ["00:00", "06:00", "12:00", "18:00"],   # Every 6 hours
    "hourly": None,                                      # Every hour on the hour
}

# Allow one extra 5-minute cron slot to avoid missing windows on slight scheduler drift.
SCHEDULE_WINDOW_MINUTES = 10

# Common user-facing timezone labels mapped to IANA names.
TIMEZONE_ALIASES = {
    "seoul": "Asia/Seoul",
}


def _resolve_timezone(user_timezone: Optional[str]) -> pytz.BaseTzInfo:
    """Resolve a user timezone string to a valid pytz timezone, defaulting to UTC."""
    tz_value = (user_timezone or "UTC").strip()
    if not tz_value:
        return pytz.UTC

    # Direct IANA timezone (preferred).
    try:
        return pytz.timezone(tz_value)
    except pytz.UnknownTimeZoneError:
        pass

    # Known alias fallback.
    alias = TIMEZONE_ALIASES.get(tz_value.lower())
    if alias:
        return pytz.timezone(alias)

    # City-like fallback, e.g. "Seoul" -> "Asia/Seoul" if uniquely matchable.
    normalized = tz_value.replace(" ", "_")
    if "/" not in normalized:
        suffix = f"/{normalized.lower()}"
        matches = [name for name in pytz.all_timezones if name.lower().endswith(suffix)]
        if len(matches) == 1:
            return pytz.timezone(matches[0])

    return pytz.UTC


def normalize_timezone_name(user_timezone: Optional[str]) -> str:
    """Return canonical timezone name used internally."""
    return _resolve_timezone(user_timezone).zone


def get_user_tier(client, user_id: str) -> str:
    """
    Get user's subscription tier from workspace.

    ADR-100: 2-tier model (free/pro). Legacy "starter" mapped to "pro".
    """
    try:
        result = client.table("workspaces")\
            .select("subscription_status")\
            .eq("owner_id", user_id)\
            .single()\
            .execute()

        if result.data:
            status = result.data.get("subscription_status", "free")
            # ADR-100: Legacy "starter" subscribers treated as "pro"
            if status in ("starter", "pro"):
                return "pro"
            if status == "free":
                return "free"
            return "free"

        return "free"

    except Exception:
        return "free"


def get_limits_for_user(client, user_id: str) -> PlatformLimits:
    """Get the resource limits for a user based on their tier."""
    tier = get_user_tier(client, user_id)
    return TIER_LIMITS.get(tier, TIER_LIMITS["free"])


def get_source_count(client, user_id: str, provider: str) -> int:
    """
    Count selected sources for a provider.

    ADR-058: Sources are stored in platform_connections.landscape.selected_sources.
    """
    try:
        result = (
            client.table("platform_connections")
            .select("landscape")
            .eq("user_id", user_id)
            .eq("platform", provider)
            .eq("status", "connected")
            .execute()
        )

        if not result.data:
            return 0

        total = 0
        for platform in result.data:
            landscape = platform.get("landscape", {}) or {}
            sources = landscape.get("selected_sources", [])
            total += len(sources) if isinstance(sources, list) else 0

        return total

    except Exception:
        return 0


def get_platform_count(client, user_id: str) -> int:
    """Count connected platforms for a user."""
    try:
        result = (
            client.table("platform_connections")
            .select("id")
            .eq("user_id", user_id)
            .eq("status", "connected")
            .execute()
        )
        return len(result.data) if result.data else 0
    except Exception:
        return 0


def check_source_limit(
    client,
    user_id: str,
    provider: str,
    additional_count: int = 1,
) -> tuple[bool, str]:
    """
    Check if user can add more sources for a provider.

    Returns:
        Tuple of (allowed: bool, message: str)
    """
    limits = get_limits_for_user(client, user_id)
    limit_field = PROVIDER_LIMIT_MAP.get(provider)

    if not limit_field:
        return True, "Unknown provider, no limits applied"

    max_sources = getattr(limits, limit_field)

    # -1 means unlimited
    if max_sources == -1:
        return True, "Unlimited sources for this provider"

    current_count = get_source_count(client, user_id, provider)
    new_total = current_count + additional_count

    if new_total > max_sources:
        return False, f"Source limit exceeded: {current_count}/{max_sources} {provider} sources. Upgrade for more."

    return True, f"OK: {new_total}/{max_sources} sources after adding"


def get_usage_summary(client, user_id: str, user_timezone: str = "UTC") -> dict:
    """
    Get full usage summary for a user (ADR-100).

    Returns dict with tier, limits, current usage, and next sync time.
    """
    tier = get_user_tier(client, user_id)
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])

    # Get monthly message count via RPC (ADR-100)
    monthly_messages_used = 0
    try:
        result = client.rpc(
            "get_monthly_message_count",
            {"p_user_id": user_id}
        ).execute()
        monthly_messages_used = result.data if isinstance(result.data, int) else 0
    except Exception as e:
        logger.debug(f"Failed to fetch monthly message count: {e}")

    return {
        "tier": tier,
        "limits": {
            "slack_channels": limits.slack_channels,
            "gmail_labels": limits.gmail_labels,
            "notion_pages": limits.notion_pages,
            "calendars": limits.calendars,
            "total_platforms": limits.total_platforms,
            "sync_frequency": limits.sync_frequency,
            "monthly_messages": limits.monthly_messages,
            "active_deliverables": limits.active_deliverables,
        },
        "usage": {
            "slack_channels": get_source_count(client, user_id, "slack"),
            "gmail_labels": get_source_count(client, user_id, "gmail"),
            "notion_pages": get_source_count(client, user_id, "notion"),
            "calendars": get_source_count(client, user_id, "calendar"),
            "platforms_connected": get_platform_count(client, user_id),
            "monthly_messages_used": monthly_messages_used,
            "active_deliverables": get_active_deliverable_count(client, user_id),
        },
        "next_sync": get_next_sync_time(limits.sync_frequency, user_timezone),
    }


def validate_sources_update(
    client,
    user_id: str,
    provider: str,
    new_source_ids: list[str],
) -> tuple[bool, str, list[str]]:
    """
    Validate a sources update request.

    If new sources exceed limit, returns allowed sources (up to limit).
    """
    limits = get_limits_for_user(client, user_id)
    limit_field = PROVIDER_LIMIT_MAP.get(provider)

    if not limit_field:
        return True, "OK", new_source_ids

    max_sources = getattr(limits, limit_field)

    # -1 means unlimited
    if max_sources == -1:
        return True, "OK", new_source_ids

    requested_count = len(new_source_ids)

    if requested_count <= max_sources:
        return True, f"OK: {requested_count}/{max_sources} sources", new_source_ids

    # Over limit - truncate to max
    allowed_ids = new_source_ids[:max_sources]
    return (
        False,
        f"Requested {requested_count} sources but limit is {max_sources}. Only first {max_sources} will be saved.",
        allowed_ids,
    )


# =============================================================================
# Deliverable Limits (ADR-053)
# =============================================================================


def get_active_deliverable_count(client, user_id: str) -> int:
    """
    Count active deliverables for a user.

    Active = status 'active' (ADR-059: deliverables use status, not enabled column).
    """
    try:
        result = (
            client.table("deliverables")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("status", "active")
            .execute()
        )

        return result.count if result.count else 0

    except Exception:
        return 0


def check_deliverable_limit(client, user_id: str) -> tuple[bool, str]:
    """
    Check if user can create another active deliverable.

    Returns:
        Tuple of (allowed: bool, message: str)
    """
    limits = get_limits_for_user(client, user_id)

    # -1 means unlimited
    if limits.active_deliverables == -1:
        return True, "Unlimited deliverables"

    current_count = get_active_deliverable_count(client, user_id)

    if current_count >= limits.active_deliverables:
        return False, f"Active deliverable limit reached: {current_count}/{limits.active_deliverables}. Upgrade for more."

    return True, f"OK: {current_count + 1}/{limits.active_deliverables} active deliverables"


# =============================================================================
# Monthly Message Limit (ADR-100, replaces daily token budget)
# =============================================================================


def get_monthly_message_count(client, user_id: str) -> int:
    """
    Get total user messages sent this month via SQL function.

    ADR-100: Counts session_messages where role='user' for current month.
    """
    try:
        result = client.rpc(
            "get_monthly_message_count",
            {"p_user_id": user_id}
        ).execute()
        return result.data if isinstance(result.data, int) else 0
    except Exception:
        return 0


def check_monthly_message_limit(client, user_id: str) -> tuple[bool, int, int]:
    """
    Check if user is within monthly message limit.

    ADR-100: Replaces daily token budget with user-understandable monthly messages.

    Returns:
        Tuple of (allowed: bool, messages_used: int, message_limit: int)
    """
    limits = get_limits_for_user(client, user_id)

    # -1 means unlimited
    if limits.monthly_messages == -1:
        return True, 0, -1

    messages_used = get_monthly_message_count(client, user_id)

    if messages_used >= limits.monthly_messages:
        return False, messages_used, limits.monthly_messages

    return True, messages_used, limits.monthly_messages


# =============================================================================
# Sync Frequency Helpers (ADR-053)
# =============================================================================


def get_next_sync_time(sync_frequency: SyncFrequency, user_timezone: str = "UTC") -> str:
    """
    Calculate the next scheduled sync time for a user.
    """
    tz = _resolve_timezone(user_timezone)

    now = datetime.now(tz)

    if sync_frequency == "hourly":
        next_sync = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        schedule = SYNC_SCHEDULES.get(sync_frequency, ["08:00"])
        next_sync = _find_next_scheduled_time(now, schedule, tz)

    return next_sync.isoformat()


def _find_next_scheduled_time(
    now: datetime, schedule: list[str], tz: pytz.BaseTzInfo
) -> datetime:
    """Find the next scheduled time from a list of HH:MM strings."""
    today = now.date()

    for time_str in schedule:
        hour, minute = map(int, time_str.split(":"))
        scheduled = tz.localize(datetime.combine(today, datetime.min.time().replace(hour=hour, minute=minute)))

        if scheduled > now:
            return scheduled

    # All times today have passed, use first time tomorrow
    tomorrow = today + timedelta(days=1)
    first_time = schedule[0]
    hour, minute = map(int, first_time.split(":"))
    return tz.localize(datetime.combine(tomorrow, datetime.min.time().replace(hour=hour, minute=minute)))


def get_sync_frequency_for_user(client, user_id: str) -> SyncFrequency:
    """Get the sync frequency for a user based on their tier."""
    limits = get_limits_for_user(client, user_id)
    return limits.sync_frequency


def should_sync_now(sync_frequency: SyncFrequency, user_timezone: str = "UTC") -> bool:
    """
    Check if a sync should run now based on frequency schedule.

    Called by the scheduler to determine which users to sync.
    """
    tz = _resolve_timezone(user_timezone)

    now = datetime.now(tz)

    if sync_frequency == "hourly":
        return now.minute < SCHEDULE_WINDOW_MINUTES

    schedule = SYNC_SCHEDULES.get(sync_frequency, [])

    for time_str in schedule:
        hour, minute = map(int, time_str.split(":"))
        if now.hour == hour and now.minute < SCHEDULE_WINDOW_MINUTES:
            return True

    return False
