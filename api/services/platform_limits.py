"""
Platform Limits Service — ADR-171: Token Spend Metering

Universal meter: cost_usd across all LLM call surfaces (chat, task_pipeline,
web_search, inference, evaluation, session_summary). One number per user per month.

User-facing billing rates: 2x Anthropic API rates.
  Sonnet: $6.00/MTok input, $30.00/MTok output (Anthropic: $3/$15)
  Opus:   $30.00/MTok input, $150.00/MTok output (Anthropic: $15/$75)
  Haiku:  $1.60/MTok input, $8.00/MTok output (Anthropic: $0.80/$4) — internal only

Cache discount not passed through — platform margin.
Overage model: hard stop at monthly limit.

Tier allocations:
  Free:  $3.00/mo included token spend
  Pro:   $20.00/mo included token spend ($19/mo subscription)
"""

import logging
from typing import Optional, Literal

logger = logging.getLogger(__name__)
from dataclasses import dataclass
from datetime import datetime, timedelta
import pytz


SyncFrequency = Literal["1x_daily", "2x_daily", "4x_daily", "hourly"]


# =============================================================================
# Billing rates — user-facing rates at 2x Anthropic API rates (April 2026)
# Keys match model strings used in API calls.
# Rates are decoupled from Anthropic's rates — update at our discretion.
# Haiku is internal only — never shown in user-facing billing UI.
# =============================================================================

BILLING_RATES: dict[str, dict[str, float]] = {
    "claude-sonnet-4-20250514":  {"input_per_mtok": 6.00,  "output_per_mtok": 30.00},
    "claude-opus-4-6":           {"input_per_mtok": 30.00, "output_per_mtok": 150.00},
    "claude-haiku-4-5-20251001": {"input_per_mtok": 1.60,  "output_per_mtok": 8.00},
}
_DEFAULT_BILLING_RATE = BILLING_RATES["claude-sonnet-4-20250514"]


def compute_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Compute cost_usd at user-facing billing rates. Cache-agnostic (no cache discount).

    All internal models (Haiku) are billed at their published rate even though
    they are not user-selectable — ensures accurate cost accounting.
    """
    rate = BILLING_RATES.get(model, _DEFAULT_BILLING_RATE)
    cost = (
        (input_tokens  / 1_000_000) * rate["input_per_mtok"]
        + (output_tokens / 1_000_000) * rate["output_per_mtok"]
    )
    return round(cost, 6)


# =============================================================================
# Tier definitions — single place to tune all limits
# =============================================================================

@dataclass
class PlatformLimits:
    """Resource limits for a user tier."""
    slack_channels: int           # -1 for unlimited
    notion_pages: int             # -1 for unlimited
    github_repos: int             # -1 for unlimited (ADR-147)
    total_platforms: int
    sync_frequency: SyncFrequency
    monthly_messages: int         # -1 for unlimited (Pro)
    active_tasks: int             # -1 for unlimited
    monthly_spend_usd_limit: float  # ADR-171: monthly token spend cap in USD


TIER_LIMITS = {
    "free": PlatformLimits(
        slack_channels=5,
        notion_pages=10,
        github_repos=3,
        total_platforms=3,
        sync_frequency="1x_daily",
        monthly_messages=150,
        active_tasks=2,
        monthly_spend_usd_limit=3.00,   # ADR-171: $3/mo included
    ),
    "pro": PlatformLimits(
        slack_channels=-1,
        notion_pages=-1,
        github_repos=-1,
        total_platforms=3,
        sync_frequency="hourly",
        monthly_messages=-1,            # Unlimited chat for Pro
        active_tasks=10,
        monthly_spend_usd_limit=20.00,  # ADR-171: $20/mo included
    ),
}

# Provider to limit field mapping
PROVIDER_LIMIT_MAP = {
    "slack": "slack_channels",
    "notion": "notion_pages",
    "github": "github_repos",   # ADR-147
}

# Sync frequency schedules (times in user's timezone)
SYNC_SCHEDULES = {
    "1x_daily": ["08:00"],
    "2x_daily": ["08:00", "18:00"],
    "4x_daily": ["00:00", "06:00", "12:00", "18:00"],
    "hourly": None,
}

_SCHEDULE_MATCH_WINDOW = 10

TIMEZONE_ALIASES = {
    "seoul": "Asia/Seoul",
}


# =============================================================================
# Timezone helpers
# =============================================================================

def _resolve_timezone(user_timezone: Optional[str]) -> pytz.BaseTzInfo:
    """Resolve a user timezone string to a valid pytz timezone, defaulting to UTC."""
    tz_value = (user_timezone or "UTC").strip()
    if not tz_value:
        return pytz.UTC

    try:
        return pytz.timezone(tz_value)
    except pytz.UnknownTimeZoneError:
        pass

    alias = TIMEZONE_ALIASES.get(tz_value.lower())
    if alias:
        return pytz.timezone(alias)

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


# =============================================================================
# Core tier lookup
# =============================================================================

def get_user_tier(client, user_id: str) -> str:
    """Get user's subscription tier. Legacy "starter" mapped to "pro"."""
    try:
        result = client.table("workspaces")\
            .select("subscription_status")\
            .eq("owner_id", user_id)\
            .limit(1)\
            .execute()

        rows = result.data or []
        if rows:
            status = rows[0].get("subscription_status", "free")
            if status in ("starter", "pro"):
                return "pro"
        return "free"
    except Exception:
        return "free"


def get_limits_for_user(client, user_id: str) -> PlatformLimits:
    """Get the resource limits for a user based on their tier."""
    tier = get_user_tier(client, user_id)
    return TIER_LIMITS.get(tier, TIER_LIMITS["free"])


# =============================================================================
# Source limits
# =============================================================================

def get_source_count(client, user_id: str, provider: str) -> int:
    """Count selected sources for a provider."""
    try:
        result = (
            client.table("platform_connections")
            .select("landscape")
            .eq("user_id", user_id)
            .eq("platform", provider)
            .eq("status", "active")
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
            .eq("status", "active")
            .execute()
        )
        return len(result.data) if result.data else 0
    except Exception:
        return 0


def check_source_limit(
    client, user_id: str, provider: str, additional_count: int = 1,
) -> tuple[bool, str]:
    """Check if user can add more sources for a provider."""
    limits = get_limits_for_user(client, user_id)
    limit_field = PROVIDER_LIMIT_MAP.get(provider)
    if not limit_field:
        return True, "Unknown provider, no limits applied"

    max_sources = getattr(limits, limit_field)
    if max_sources == -1:
        return True, "Unlimited sources for this provider"

    current_count = get_source_count(client, user_id, provider)
    new_total = current_count + additional_count
    if new_total > max_sources:
        return False, f"Source limit exceeded: {current_count}/{max_sources} {provider} sources. Upgrade for more."
    return True, f"OK: {new_total}/{max_sources} sources after adding"


def validate_sources_update(
    client, user_id: str, provider: str, new_source_ids: list[str],
) -> tuple[bool, str, list[str]]:
    """Validate a sources update request. Truncates to limit if exceeded."""
    limits = get_limits_for_user(client, user_id)
    limit_field = PROVIDER_LIMIT_MAP.get(provider)
    if not limit_field:
        return True, "OK", new_source_ids

    max_sources = getattr(limits, limit_field)
    if max_sources == -1:
        return True, "OK", new_source_ids

    requested_count = len(new_source_ids)
    if requested_count <= max_sources:
        return True, f"OK: {requested_count}/{max_sources} sources", new_source_ids

    allowed_ids = new_source_ids[:max_sources]
    return (
        False,
        f"Requested {requested_count} sources but limit is {max_sources}. Only first {max_sources} will be saved.",
        allowed_ids,
    )


# =============================================================================
# Task limits (was: agent limits)
# =============================================================================

def get_active_agent_count(client, user_id: str) -> int:
    """Count active agents for a user, excluding PM agents."""
    try:
        result = (
            client.table("agents")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("status", "active")
            .neq("role", "pm")
            .execute()
        )
        return result.count if result.count else 0
    except Exception:
        return 0


def get_active_task_count(client, user_id: str) -> int:
    """Count active tasks for a user."""
    try:
        result = (
            client.table("tasks")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("status", "active")
            .execute()
        )
        return result.count if result.count else 0
    except Exception:
        return 0


def check_task_limit(client, user_id: str) -> tuple[bool, str]:
    """Check if user can create another active task."""
    limits = get_limits_for_user(client, user_id)
    if limits.active_tasks == -1:
        return True, "Unlimited tasks"

    current_count = get_active_task_count(client, user_id)
    if current_count >= limits.active_tasks:
        return False, f"Active task limit reached: {current_count}/{limits.active_tasks}. Upgrade for more."
    return True, f"OK: {current_count + 1}/{limits.active_tasks} active tasks"


# Backwards compat alias — callers using check_agent_limit still work
check_agent_limit = check_task_limit


# =============================================================================
# Monthly message limit (Free tier only — Pro is unlimited)
# =============================================================================

def get_monthly_message_count(client, user_id: str) -> int:
    """Get total user messages sent this month via SQL function."""
    try:
        result = client.rpc(
            "get_monthly_message_count",
            {"p_user_id": user_id}
        ).execute()
        return result.data if isinstance(result.data, int) else 0
    except Exception:
        return 0


def check_monthly_message_limit(client, user_id: str) -> tuple[bool, int, int]:
    """Check if user is within monthly message limit. Pro = unlimited."""
    limits = get_limits_for_user(client, user_id)
    if limits.monthly_messages == -1:
        return True, 0, -1

    messages_used = get_monthly_message_count(client, user_id)
    if messages_used >= limits.monthly_messages:
        return False, messages_used, limits.monthly_messages
    return True, messages_used, limits.monthly_messages


# =============================================================================
# Token spend metering — ADR-171
# Universal meter: cost_usd across all LLM surfaces.
# =============================================================================

def get_monthly_spend_usd(client, user_id: str) -> float:
    """Total token spend in USD for the current calendar month."""
    try:
        result = client.rpc(
            "get_monthly_spend_usd",
            {"p_user_id": user_id}
        ).execute()
        val = result.data
        return float(val) if val is not None else 0.0
    except Exception:
        return 0.0


def check_spend_budget(client, user_id: str) -> tuple[bool, float, float]:
    """Check if user is within monthly token spend limit.

    Returns: (allowed, spent_usd, limit_usd)
    Hard stop — no soft overage (ADR-171).
    """
    limits = get_limits_for_user(client, user_id)
    limit = limits.monthly_spend_usd_limit
    spent = get_monthly_spend_usd(client, user_id)
    if spent >= limit:
        return False, spent, limit
    return True, spent, limit


def record_token_usage(
    client,
    user_id: str,
    caller: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    ref_id: str = None,
    metadata: dict = None,
) -> None:
    """Record one LLM call to token_usage. Called at every call site.

    caller: 'chat' | 'task_pipeline' | 'web_search' | 'inference' |
            'evaluation' | 'session_summary'
    cost_usd computed at user-facing billing rates (cache-agnostic).
    """
    cost = compute_cost_usd(model, input_tokens, output_tokens)
    try:
        row = {
            "user_id": user_id,
            "caller": caller,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost,
        }
        if ref_id:
            row["ref_id"] = str(ref_id)
        if metadata:
            row["metadata"] = metadata
        client.table("token_usage").insert(row).execute()
    except Exception as e:
        logger.warning(
            f"[TOKEN_USAGE] Failed to record {caller} "
            f"({input_tokens}in/{output_tokens}out tokens, ${cost:.4f}): {e}"
        )


# =============================================================================
# Usage summary (consumed by /api/user/limits endpoint)
# =============================================================================

def get_usage_summary(client, user_id: str, user_timezone: str = "UTC") -> dict:
    """Get full usage summary — tier, limits, current usage, next sync."""
    tier = get_user_tier(client, user_id)
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])

    monthly_messages_used = 0
    if limits.monthly_messages != -1:
        monthly_messages_used = get_monthly_message_count(client, user_id)

    spend_usd = get_monthly_spend_usd(client, user_id)

    return {
        "tier": tier,
        "limits": {
            "slack_channels": limits.slack_channels,
            "notion_pages": limits.notion_pages,
            "total_platforms": limits.total_platforms,
            "sync_frequency": limits.sync_frequency,
            "monthly_messages": limits.monthly_messages,
            "active_tasks": limits.active_tasks,
            "monthly_spend_usd_limit": limits.monthly_spend_usd_limit,
        },
        "usage": {
            "slack_channels": get_source_count(client, user_id, "slack"),
            "notion_pages": get_source_count(client, user_id, "notion"),
            "platforms_connected": get_platform_count(client, user_id),
            "monthly_messages_used": monthly_messages_used,
            "active_tasks": get_active_task_count(client, user_id),
            "spend_usd": round(spend_usd, 4),
        },
        "next_sync": get_next_sync_time(limits.sync_frequency, user_timezone),
    }


# =============================================================================
# Sync frequency helpers
# =============================================================================

def get_next_sync_time(sync_frequency: SyncFrequency, user_timezone: str = "UTC") -> str:
    """Calculate the next scheduled sync time for a user."""
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

    tomorrow = today + timedelta(days=1)
    first_time = schedule[0]
    hour, minute = map(int, first_time.split(":"))
    return tz.localize(datetime.combine(tomorrow, datetime.min.time().replace(hour=hour, minute=minute)))


def get_sync_frequency_for_user(client, user_id: str) -> SyncFrequency:
    """Get the sync frequency for a user based on their tier."""
    limits = get_limits_for_user(client, user_id)
    return limits.sync_frequency


def should_sync_now(sync_frequency: SyncFrequency, user_timezone: str = "UTC") -> bool:
    """Check if a sync should run now based on frequency schedule."""
    tz = _resolve_timezone(user_timezone)
    now = datetime.now(tz)

    if sync_frequency == "hourly":
        return now.minute < _SCHEDULE_MATCH_WINDOW

    schedule = SYNC_SCHEDULES.get(sync_frequency, [])
    for time_str in schedule:
        hour, minute = map(int, time_str.split(":"))
        if now.hour == hour and now.minute < _SCHEDULE_MATCH_WINDOW:
            return True
    return False
