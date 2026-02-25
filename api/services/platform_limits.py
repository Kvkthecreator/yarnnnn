"""
Platform Limits Service

ADR-053: Platform sync as monetization base layer.
ADR-077: Widened source limits to support richer content accumulation.

Tier Structure (updated 2026-02-25):
- Free: 5 slack/5 gmail/10 notion, all 4 platforms, 1x/day sync, 50k tokens/day, 2 deliverables, no signal processing
- Starter ($9/mo): 15 slack/10 gmail/25 notion, all platforms, 4x/day sync, 250k tokens/day, 5 deliverables, signal processing on
- Pro ($19/mo): unlimited sources, all platforms, hourly sync, 1M tokens/day, unlimited deliverables

Key gates (by cost impact):
1. Active deliverables — each is a recurring Sonnet call
2. Daily token budget — direct proxy for Anthropic API spend
3. Signal processing — Haiku + potential Sonnet for emergent deliverables
4. Source count — controls platform_content volume
5. Sync frequency — controls API call frequency (lowest cost impact)
"""

from typing import Optional, Literal
from dataclasses import dataclass
from datetime import datetime, timedelta
import pytz


SyncFrequency = Literal["1x_daily", "2x_daily", "4x_daily", "hourly"]


@dataclass
class PlatformLimits:
    """Resource limits for a user tier (ADR-053)."""
    slack_channels: int       # -1 for unlimited
    gmail_labels: int         # -1 for unlimited
    notion_pages: int         # -1 for unlimited
    calendars: int            # -1 for unlimited (no source selection for calendar)
    total_platforms: int
    sync_frequency: SyncFrequency
    daily_token_budget: int   # -1 for unlimited
    active_deliverables: int  # -1 for unlimited


# Tier definitions (ADR-053, widened ADR-077 2026-02-25)
TIER_LIMITS = {
    "free": PlatformLimits(
        slack_channels=5,
        gmail_labels=5,
        notion_pages=10,
        calendars=-1,            # No source selection for calendar
        total_platforms=4,       # All platforms open
        sync_frequency="1x_daily",
        daily_token_budget=50_000,
        active_deliverables=2,
    ),
    "starter": PlatformLimits(
        slack_channels=15,
        gmail_labels=10,
        notion_pages=25,
        calendars=-1,
        total_platforms=4,
        sync_frequency="4x_daily",
        daily_token_budget=250_000,
        active_deliverables=5,
    ),
    "pro": PlatformLimits(
        slack_channels=-1,       # Unlimited
        gmail_labels=-1,
        notion_pages=-1,
        calendars=-1,
        total_platforms=4,
        sync_frequency="hourly",
        daily_token_budget=-1,   # Unlimited
        active_deliverables=-1,
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
    Get full usage summary for a user (ADR-053).

    Returns dict with tier, limits, current usage, and next sync time.
    """
    tier = get_user_tier(client, user_id)
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])

    # Get daily token usage via RPC (returns 0 if function not yet deployed)
    daily_tokens = 0
    try:
        result = client.rpc(
            "get_daily_token_usage",
            {"p_user_id": user_id}
        ).execute()
        daily_tokens = result.data if isinstance(result.data, int) else 0
    except Exception:
        pass

    return {
        "tier": tier,
        "limits": {
            "slack_channels": limits.slack_channels,
            "gmail_labels": limits.gmail_labels,
            "notion_pages": limits.notion_pages,
            "calendars": limits.calendars,
            "total_platforms": limits.total_platforms,
            "sync_frequency": limits.sync_frequency,
            "daily_token_budget": limits.daily_token_budget,
            "active_deliverables": limits.active_deliverables,
        },
        "usage": {
            "slack_channels": get_source_count(client, user_id, "slack"),
            "gmail_labels": get_source_count(client, user_id, "gmail"),
            "notion_pages": get_source_count(client, user_id, "notion"),
            "calendars": get_source_count(client, user_id, "calendar"),
            "platforms_connected": get_platform_count(client, user_id),
            "daily_tokens_used": daily_tokens,
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
# Daily Token Budget (ADR-053, replaces conversation count)
# =============================================================================


def get_daily_token_usage(client, user_id: str) -> int:
    """
    Get total tokens consumed today via SQL function.

    Calls get_daily_token_usage() RPC which sums input_tokens + output_tokens
    from session_messages.metadata for today's assistant messages.
    """
    try:
        result = client.rpc(
            "get_daily_token_usage",
            {"p_user_id": user_id}
        ).execute()
        return result.data if isinstance(result.data, int) else 0
    except Exception:
        return 0


def check_daily_token_budget(client, user_id: str) -> tuple[bool, int, int]:
    """
    Check if user is within daily token budget.

    Returns:
        Tuple of (allowed: bool, tokens_used: int, token_limit: int)
    """
    limits = get_limits_for_user(client, user_id)

    # -1 means unlimited
    if limits.daily_token_budget == -1:
        return True, 0, -1

    tokens_used = get_daily_token_usage(client, user_id)

    if tokens_used >= limits.daily_token_budget:
        return False, tokens_used, limits.daily_token_budget

    return True, tokens_used, limits.daily_token_budget


# =============================================================================
# Sync Frequency Helpers (ADR-053)
# =============================================================================


def get_next_sync_time(sync_frequency: SyncFrequency, user_timezone: str = "UTC") -> str:
    """
    Calculate the next scheduled sync time for a user.
    """
    try:
        tz = pytz.timezone(user_timezone)
    except pytz.UnknownTimeZoneError:
        tz = pytz.UTC

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
    try:
        tz = pytz.timezone(user_timezone)
    except pytz.UnknownTimeZoneError:
        tz = pytz.UTC

    now = datetime.now(tz)

    if sync_frequency == "hourly":
        return now.minute < 5

    schedule = SYNC_SCHEDULES.get(sync_frequency, [])

    for time_str in schedule:
        hour, minute = map(int, time_str.split(":"))
        if now.hour == hour and now.minute < 5:
            return True

    return False
