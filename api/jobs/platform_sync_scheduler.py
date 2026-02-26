"""
Platform Sync Scheduler

ADR-053: Tier-based platform sync scheduling.

Sync Frequency by Tier:
- Free: 2x/day (8am, 6pm in user's timezone)
- Starter: 4x/day (every 6 hours)
- Pro: Hourly

Run every 5 minutes via Render cron (checks if any syncs are due):
  schedule: "*/5 * * * *"
  command: cd api && python -m jobs.platform_sync_scheduler

This is separate from unified_scheduler.py to:
1. Keep sync logic isolated from deliverable/work processing
2. Allow independent scaling of sync jobs
3. Maintain clear separation of concerns (ADR-053)
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from supabase import create_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


PROVIDERS = ["slack", "gmail", "notion", "calendar"]


async def get_users_due_for_sync(supabase_client) -> list[dict]:
    """
    Query users who are due for platform sync based on their tier.

    Returns users with their tier, timezone, and connected platforms.
    """
    from services.platform_limits import (
        TIER_LIMITS,
        normalize_timezone_name,
        should_sync_now,
    )

    # Get all users with connected platforms
    result = supabase_client.table("platform_connections").select(
        "user_id, platform, settings, last_synced_at"
    ).in_("status", ["connected", "active"]).execute()

    if not result.data:
        return []

    # Group by user
    user_platforms: dict[str, list[dict]] = {}
    for row in result.data:
        user_id = row["user_id"]
        if user_id not in user_platforms:
            user_platforms[user_id] = []
        user_platforms[user_id].append(row)

    # Check each user's sync schedule
    users_due = []

    for user_id, platforms in user_platforms.items():
        # Get user's tier and timezone
        user_info = await _get_user_sync_info(supabase_client, user_id)
        if not user_info:
            continue

        tier = user_info.get("tier", "free")
        user_tz = normalize_timezone_name(user_info.get("timezone", "UTC"))

        limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
        sync_frequency = limits.sync_frequency

        # Check if this user should sync now
        if should_sync_now(sync_frequency, user_tz):
            # Filter to platforms that haven't been synced recently
            platforms_to_sync = []
            for platform in platforms:
                if _needs_sync(platform, sync_frequency):
                    platforms_to_sync.append(platform["platform"])

            if platforms_to_sync:
                users_due.append({
                    "user_id": user_id,
                    "tier": tier,
                    "timezone": user_tz,
                    "sync_frequency": sync_frequency,
                    "providers": platforms_to_sync,
                })

    return users_due


async def _get_user_sync_info(supabase_client, user_id: str) -> Optional[dict]:
    """Get user's tier and timezone for sync scheduling.

    ADR-059: timezone lives in user_context (key='timezone').
    Tier comes from workspaces.subscription_status.
    """
    try:
        # Timezone from user_context (ADR-059)
        tz_result = supabase_client.table("user_context").select(
            "value"
        ).eq("user_id", user_id).eq("key", "timezone").maybe_single().execute()
        timezone = tz_result.data.get("value", "UTC") if tz_result.data else "UTC"

        # Tier from workspaces.subscription_status
        ws_result = supabase_client.table("workspaces").select(
            "subscription_status"
        ).eq("owner_id", user_id).maybe_single().execute()
        tier = ws_result.data.get("subscription_status", "free") if ws_result.data else "free"

        return {"tier": tier, "timezone": timezone}

    except Exception as e:
        logger.warning(f"Failed to get user sync info: {e}")
        return {"tier": "free", "timezone": "UTC"}


def _needs_sync(platform: dict, sync_frequency: str) -> bool:
    """
    Check if a platform needs to be synced based on last sync time.

    Prevents running sync too frequently if scheduler runs often.
    """
    from datetime import timedelta

    last_synced = platform.get("last_synced_at")
    if not last_synced:
        return True  # Never synced

    try:
        if isinstance(last_synced, str):
            if last_synced.endswith("Z"):
                last_synced = last_synced[:-1] + "+00:00"
            last_synced_dt = datetime.fromisoformat(last_synced)
        else:
            last_synced_dt = last_synced
    except (ValueError, TypeError):
        return True

    now = datetime.now(timezone.utc)
    time_since_sync = now - last_synced_dt

    # Minimum time between syncs to prevent duplicates
    min_intervals = {
        "2x_daily": timedelta(hours=6),   # At least 6 hours between syncs
        "4x_daily": timedelta(hours=4),   # At least 4 hours between syncs
        "hourly": timedelta(minutes=45),  # At least 45 minutes between syncs
    }

    min_interval = min_intervals.get(sync_frequency, timedelta(hours=6))
    return time_since_sync >= min_interval


async def process_user_sync(supabase_client, user: dict) -> dict:
    """
    Process platform sync for a single user.

    ADR-056: Fetches selected_sources for each provider and passes to worker.

    Args:
        supabase_client: Supabase client
        user: User dict with user_id, tier, providers

    Returns:
        Dict with sync results
    """
    from workers.platform_worker import sync_platform

    user_id = user["user_id"]
    providers = user["providers"]

    logger.info(f"[SYNC] Processing user {user_id[:8]}... providers={providers}")

    results = {}
    for provider in providers:
        try:
            # ADR-056: Fetch selected_sources from integration landscape
            selected_sources = await _get_selected_sources(supabase_client, user_id, provider)

            if not selected_sources:
                logger.info(f"[SYNC] Skipping {provider}: no sources selected")
                results[provider] = {"success": True, "items_synced": 0, "skipped": "no_sources_selected"}
                continue

            logger.info(f"[SYNC] {provider}: syncing {len(selected_sources)} selected sources")

            # Run sync for this provider with selected sources
            result = sync_platform(
                user_id=user_id,
                provider=provider,
                selected_sources=selected_sources,
                supabase_url=os.environ.get("SUPABASE_URL"),
                supabase_key=os.environ.get("SUPABASE_SERVICE_KEY"),
            )
            results[provider] = result

            if result.get("success"):
                logger.info(f"[SYNC] ✓ {provider}: {result.get('items_synced', 0)} items")
            else:
                logger.warning(f"[SYNC] ✗ {provider}: {result.get('error')}")

        except Exception as e:
            logger.error(f"[SYNC] Error syncing {provider}: {e}")
            results[provider] = {"success": False, "error": str(e)}

    return results


async def _get_selected_sources(supabase_client, user_id: str, provider: str) -> list[str]:
    """
    Get selected source IDs for a user's platform integration.

    ADR-056: Returns list of source IDs from integration.landscape.selected_sources
    """
    try:
        result = supabase_client.table("platform_connections").select(
            "landscape"
        ).eq("user_id", user_id).eq("platform", provider).single().execute()

        if not result.data:
            return []

        landscape = result.data.get("landscape", {}) or {}
        selected = landscape.get("selected_sources", [])

        # Extract IDs from objects if needed
        source_ids = []
        for s in selected:
            if isinstance(s, dict):
                source_ids.append(s.get("id"))
            else:
                source_ids.append(s)

        return [sid for sid in source_ids if sid]  # Filter out None/empty

    except Exception as e:
        logger.warning(f"[SYNC] Failed to get selected sources for {provider}: {e}")
        return []


async def run_platform_sync_scheduler():
    """
    Main scheduler entry point.

    Checks which users are due for sync based on their tier's frequency,
    and triggers syncs for eligible users.
    """
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        return

    supabase = create_client(supabase_url, supabase_key)

    now = datetime.now(timezone.utc)
    logger.info(f"[{now.isoformat()}] Starting platform sync scheduler...")

    # Get users due for sync
    users_due = await get_users_due_for_sync(supabase)
    logger.info(f"[SYNC] Found {len(users_due)} user(s) due for sync")

    if not users_due:
        logger.info("[SYNC] No syncs needed at this time")
        return

    # Process each user's sync
    success_count = 0
    total_providers = 0

    for user in users_due:
        try:
            total_providers += len(user["providers"])
            results = await process_user_sync(supabase, user)

            # Count successes
            for provider, result in results.items():
                if result.get("success"):
                    success_count += 1

        except Exception as e:
            logger.error(f"[SYNC] Unexpected error for user {user['user_id'][:8]}: {e}")

    logger.info(f"[SYNC] Completed: {success_count}/{total_providers} provider syncs successful")


if __name__ == "__main__":
    asyncio.run(run_platform_sync_scheduler())
