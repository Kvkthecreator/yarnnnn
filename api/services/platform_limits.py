"""
Platform Limits Service

Enforces resource limits per user tier (DECISION-001).

Limits:
- Free tier: 5 Slack channels, 3 Gmail labels, 5 Notion pages
- Pro tier (future): 20 channels, 10 labels, 25 pages
"""

from typing import Optional
from dataclasses import dataclass


@dataclass
class PlatformLimits:
    """Resource limits for a user tier."""
    slack_channels: int
    gmail_labels: int
    notion_pages: int
    total_platforms: int


# Tier definitions
TIER_LIMITS = {
    "free": PlatformLimits(
        slack_channels=5,
        gmail_labels=3,
        notion_pages=5,
        total_platforms=3,
    ),
    "pro": PlatformLimits(
        slack_channels=20,
        gmail_labels=10,
        notion_pages=25,
        total_platforms=10,
    ),
    "enterprise": PlatformLimits(
        slack_channels=100,
        gmail_labels=50,
        notion_pages=100,
        total_platforms=50,
    ),
}

# Provider to limit field mapping
PROVIDER_LIMIT_MAP = {
    "slack": "slack_channels",
    "gmail": "gmail_labels",
    "notion": "notion_pages",
}


def get_user_tier(client, user_id: str) -> str:
    """
    Get user's subscription tier.

    For now, returns 'free' for all users.
    Future: Look up from user_settings or subscription table.
    """
    # TODO: Implement tier lookup when subscription system exists
    # try:
    #     result = client.table("user_settings").select("tier").eq("user_id", user_id).single().execute()
    #     return result.data.get("tier", "free") if result.data else "free"
    # except:
    #     return "free"
    return "free"


def get_limits_for_user(client, user_id: str) -> PlatformLimits:
    """Get the resource limits for a user based on their tier."""
    tier = get_user_tier(client, user_id)
    return TIER_LIMITS.get(tier, TIER_LIMITS["free"])


def get_source_count(client, user_id: str, provider: str) -> int:
    """
    Count selected sources for a provider.

    Sources are stored in platforms.config.selected_sources.
    """
    try:
        result = (
            client.table("platforms")
            .select("config")
            .eq("user_id", user_id)
            .eq("provider", provider)
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
            client.table("platforms")
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


def get_usage_summary(client, user_id: str) -> dict:
    """
    Get full usage summary for a user.

    Returns dict with limits and current usage per resource type.
    """
    tier = get_user_tier(client, user_id)
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])

    return {
        "tier": tier,
        "limits": {
            "slack_channels": limits.slack_channels,
            "gmail_labels": limits.gmail_labels,
            "notion_pages": limits.notion_pages,
            "total_platforms": limits.total_platforms,
        },
        "usage": {
            "slack_channels": get_source_count(client, user_id, "slack"),
            "gmail_labels": get_source_count(client, user_id, "gmail"),
            "notion_pages": get_source_count(client, user_id, "notion"),
            "platforms_connected": get_platform_count(client, user_id),
        },
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
