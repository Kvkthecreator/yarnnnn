"""
Platform Limits Service

ADR-053: Platform sync as monetization base layer.

Tier Structure:
- Free: 1 source per platform, 2 platforms, 2x/day sync, 20 TP convos, 3 deliverables
- Starter ($9/mo): 5 sources, 4 platforms, 4x/day sync, 100 TP convos, 10 deliverables
- Pro ($19/mo): 15-25 sources, 4 platforms, hourly sync, unlimited

Key insight: Sync is cheap (~$0.003/user/day), monetization lever is source count + frequency.
"""

from typing import Optional, Literal
from dataclasses import dataclass
from datetime import datetime, timedelta
import pytz


SyncFrequency = Literal["2x_daily", "4x_daily", "hourly"]


@dataclass
class PlatformLimits:
    """Resource limits for a user tier (ADR-053)."""
    slack_channels: int
    gmail_labels: int
    notion_pages: int
    calendars: int
    total_platforms: int
    sync_frequency: SyncFrequency
    tp_conversations_per_month: int  # -1 for unlimited
    active_deliverables: int  # -1 for unlimited


# Tier definitions (ADR-053)
TIER_LIMITS = {
    "free": PlatformLimits(
        slack_channels=1,
        gmail_labels=1,
        notion_pages=1,
        calendars=1,
        total_platforms=2,
        sync_frequency="2x_daily",
        tp_conversations_per_month=20,
        active_deliverables=3,
    ),
    "starter": PlatformLimits(
        slack_channels=5,
        gmail_labels=5,
        notion_pages=5,
        calendars=3,
        total_platforms=4,
        sync_frequency="4x_daily",
        tp_conversations_per_month=100,
        active_deliverables=10,
    ),
    "pro": PlatformLimits(
        slack_channels=20,
        gmail_labels=15,
        notion_pages=25,
        calendars=10,
        total_platforms=4,
        sync_frequency="hourly",
        tp_conversations_per_month=-1,  # unlimited
        active_deliverables=-1,  # unlimited
    ),
}

# Provider to limit field mapping
PROVIDER_LIMIT_MAP = {
    "slack": "slack_channels",
    "gmail": "gmail_labels",
    "google": "gmail_labels",  # Google uses Gmail limits
    "notion": "notion_pages",
    "calendar": "calendars",
}

# Sync frequency schedules (times in user's timezone)
SYNC_SCHEDULES = {
    "2x_daily": ["08:00", "18:00"],  # Morning + evening
    "4x_daily": ["00:00", "06:00", "12:00", "18:00"],  # Every 6 hours
    "hourly": None,  # Every hour on the hour
}


def get_user_tier(client, user_id: str) -> str:
    """
    Get user's subscription tier from workspace.

    ADR-053: Looks up subscription_status from workspaces table.
    Returns 'free', 'starter', or 'pro'.
    """
    try:
        result = client.table("workspaces")\
            .select("subscription_status")\
            .eq("owner_id", user_id)\
            .single()\
            .execute()

        if result.data:
            status = result.data.get("subscription_status", "free")
            # Normalize status to valid tier
            if status in ("free", "starter", "pro"):
                return status
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

    Sources are stored in platform_connections.config.selected_sources.
    """
    try:
        result = (
            client.table("platform_connections")
            .select("config")
            .eq("user_id", user_id)
            .eq("platform", provider)
            .eq("status", "connected")
            .execute()
        )

        if not result.data:
            return 0

        total = 0
        for platform in result.data:
            config = platform.get("config", {}) or {}
            sources = config.get("selected_sources", [])
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

    Args:
        client: Supabase client
        user_id: User UUID
        provider: Platform provider (slack, gmail, notion)
        additional_count: Number of sources to add

    Returns:
        Tuple of (allowed: bool, message: str)
    """
    limits = get_limits_for_user(client, user_id)
    limit_field = PROVIDER_LIMIT_MAP.get(provider)

    if not limit_field:
        return True, "Unknown provider, no limits applied"

    max_sources = getattr(limits, limit_field)
    current_count = get_source_count(client, user_id, provider)
    new_total = current_count + additional_count

    if new_total > max_sources:
        return False, f"Source limit exceeded: {current_count}/{max_sources} {provider} sources. Upgrade for more."

    return True, f"OK: {new_total}/{max_sources} sources after adding"


def check_platform_limit(client, user_id: str) -> tuple[bool, str]:
    """
    Check if user can connect another platform.

    Returns:
        Tuple of (allowed: bool, message: str)
    """
    limits = get_limits_for_user(client, user_id)
    current_count = get_platform_count(client, user_id)

    if current_count >= limits.total_platforms:
        return False, f"Platform limit reached: {current_count}/{limits.total_platforms}. Upgrade for more."

    return True, f"OK: {current_count + 1}/{limits.total_platforms} platforms after connecting"


def get_usage_summary(client, user_id: str, user_timezone: str = "UTC") -> dict:
    """
    Get full usage summary for a user (ADR-053).

    Returns dict with tier, limits, current usage, and next sync time.
    """
    tier = get_user_tier(client, user_id)
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])

    return {
        "tier": tier,
        "limits": {
            "slack_channels": limits.slack_channels,
            "gmail_labels": limits.gmail_labels,
            "notion_pages": limits.notion_pages,
            "calendars": limits.calendars,
            "total_platforms": limits.total_platforms,
            "sync_frequency": limits.sync_frequency,
            "tp_conversations_per_month": limits.tp_conversations_per_month,
            "active_deliverables": limits.active_deliverables,
        },
        "usage": {
            "slack_channels": get_source_count(client, user_id, "slack"),
            "gmail_labels": get_source_count(client, user_id, "gmail"),
            "notion_pages": get_source_count(client, user_id, "notion"),
            "calendars": get_source_count(client, user_id, "calendar"),
            "platforms_connected": get_platform_count(client, user_id),
            "tp_conversations_this_month": get_tp_conversation_count(client, user_id),
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

    Args:
        client: Supabase client
        user_id: User UUID
        provider: Platform provider
        new_source_ids: Requested source IDs

    Returns:
        Tuple of (valid: bool, message: str, allowed_ids: list)
    """
    limits = get_limits_for_user(client, user_id)
    limit_field = PROVIDER_LIMIT_MAP.get(provider)

    if not limit_field:
        return True, "OK", new_source_ids

    max_sources = getattr(limits, limit_field)
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
# TP Conversation & Deliverable Limits (ADR-053)
# =============================================================================


def get_tp_conversation_count(client, user_id: str) -> int:
    """
    Count TP conversations for the current month.

    Conversations are stored in the chat_sessions table.
    """
    try:
        # Get start of current month
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        result = (
            client.table("chat_sessions")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .gte("created_at", month_start.isoformat())
            .execute()
        )

        return result.count if result.count else 0

    except Exception:
        return 0


def get_active_deliverable_count(client, user_id: str) -> int:
    """
    Count active deliverables for a user.

    Active = enabled and not deleted.
    """
    try:
        result = (
            client.table("deliverables")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("enabled", True)
            .execute()
        )

        return result.count if result.count else 0

    except Exception:
        return 0


def check_tp_conversation_limit(client, user_id: str) -> tuple[bool, str]:
    """
    Check if user can start another TP conversation this month.

    Returns:
        Tuple of (allowed: bool, message: str)
    """
    limits = get_limits_for_user(client, user_id)

    # -1 means unlimited
    if limits.tp_conversations_per_month == -1:
        return True, "Unlimited TP conversations"

    current_count = get_tp_conversation_count(client, user_id)

    if current_count >= limits.tp_conversations_per_month:
        return False, f"Monthly conversation limit reached: {current_count}/{limits.tp_conversations_per_month}. Upgrade for more."

    return True, f"OK: {current_count + 1}/{limits.tp_conversations_per_month} conversations this month"


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
# Sync Frequency Helpers (ADR-053)
# =============================================================================


def get_next_sync_time(sync_frequency: SyncFrequency, user_timezone: str = "UTC") -> str:
    """
    Calculate the next scheduled sync time for a user.

    Args:
        sync_frequency: The tier's sync frequency
        user_timezone: User's timezone (e.g., "America/New_York")

    Returns:
        ISO timestamp of next sync time
    """
    try:
        tz = pytz.timezone(user_timezone)
    except pytz.UnknownTimeZoneError:
        tz = pytz.UTC

    now = datetime.now(tz)

    if sync_frequency == "hourly":
        # Next hour on the hour
        next_sync = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        schedule = SYNC_SCHEDULES.get(sync_frequency, ["08:00", "18:00"])
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

    Args:
        sync_frequency: The tier's sync frequency
        user_timezone: User's timezone

    Returns:
        True if sync should run now
    """
    try:
        tz = pytz.timezone(user_timezone)
    except pytz.UnknownTimeZoneError:
        tz = pytz.UTC

    now = datetime.now(tz)

    if sync_frequency == "hourly":
        # Hourly syncs run on the hour (within 5 min window)
        return now.minute < 5

    schedule = SYNC_SCHEDULES.get(sync_frequency, [])

    # Check if current time is within 5 min of any scheduled time
    for time_str in schedule:
        hour, minute = map(int, time_str.split(":"))
        if now.hour == hour and now.minute < 5:
            return True

    return False
