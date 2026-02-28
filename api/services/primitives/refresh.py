"""
RefreshPlatformContent Primitive (ADR-085)

Synchronous write-through cache refresh for platform content.
RAG cache-miss pattern: Search finds stale/empty → Refresh syncs latest → Search again.

Usage:
  RefreshPlatformContent(platform="slack")
  RefreshPlatformContent(platform="gmail")
  RefreshPlatformContent(platform="calendar")
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Minimum time between refreshes to prevent redundant syncs
STALENESS_THRESHOLD_MINUTES = 30


REFRESH_PLATFORM_CONTENT_TOOL = {
    "name": "RefreshPlatformContent",
    "description": """Refresh platform content by syncing latest data from a connected platform.

Use when Search(scope="platform_content") returns stale or empty results and you need current data.
Runs a targeted sync (~10-30s) and returns a summary of what was fetched.

After refreshing, use Search(scope="platform_content") to query the fresh data.

Typical flow:
1. Search(scope="platform_content", platform="slack") → stale or empty
2. RefreshPlatformContent(platform="slack") → syncs latest, returns summary
3. Search(scope="platform_content", platform="slack") → fresh results

Supported platforms: slack, gmail, notion, calendar""",
    "input_schema": {
        "type": "object",
        "properties": {
            "platform": {
                "type": "string",
                "enum": ["slack", "gmail", "notion", "calendar"],
                "description": "Platform to refresh"
            }
        },
        "required": ["platform"]
    }
}


async def handle_refresh_platform_content(auth: Any, input: dict) -> dict:
    """
    Handle RefreshPlatformContent primitive.

    Checks connection status and freshness, then runs a synchronous sync
    via the existing platform worker pipeline.

    Args:
        auth: Auth context with user_id and client
        input: {"platform": "slack|gmail|notion|calendar"}

    Returns:
        {success, platform, items_synced, message, refreshed_at}
    """
    platform = input.get("platform", "")

    if not platform:
        return {
            "success": False,
            "error": "missing_platform",
            "message": "Platform is required (slack, gmail, notion, calendar)",
        }

    if platform not in ("slack", "gmail", "notion", "calendar"):
        return {
            "success": False,
            "error": "invalid_platform",
            "message": f"Unsupported platform: {platform}. Use: slack, gmail, notion, calendar",
        }

    user_id = auth.user_id

    # Google OAuth stores one DB row as platform="gmail" for both Gmail and Calendar
    db_platform = "gmail" if platform in ("gmail", "calendar") else platform

    # 1. Check platform is connected
    try:
        conn_result = auth.client.table("platform_connections").select(
            "id, status"
        ).eq("user_id", user_id).eq("platform", db_platform).maybe_single().execute()

        if not conn_result.data:
            return {
                "success": False,
                "error": "not_connected",
                "message": f"{platform} is not connected. Connect it in Settings.",
            }

        status = conn_result.data.get("status")
        if status not in ("connected", "active"):
            return {
                "success": False,
                "error": "not_active",
                "message": f"{platform} connection is {status}. Reconnect in Settings.",
            }
    except Exception as e:
        logger.error(f"[REFRESH] Failed to check connection for {platform}: {e}")
        return {
            "success": False,
            "error": "connection_check_failed",
            "message": f"Failed to check {platform} connection: {e}",
        }

    # 2. Check freshness — skip if recently synced
    try:
        now = datetime.now(timezone.utc)
        threshold = now - timedelta(minutes=STALENESS_THRESHOLD_MINUTES)

        freshness_result = auth.client.table("platform_content").select(
            "fetched_at"
        ).eq("user_id", user_id).eq("platform", platform).gte(
            "fetched_at", threshold.isoformat()
        ).limit(1).execute()

        if freshness_result.data:
            # Content was fetched recently — count existing items instead of re-syncing
            count_result = auth.client.table("platform_content").select(
                "id", count="exact"
            ).eq("user_id", user_id).eq("platform", platform).execute()

            item_count = count_result.count or 0

            return {
                "success": True,
                "platform": platform,
                "items_synced": 0,
                "skipped": True,
                "existing_items": item_count,
                "message": f"{platform} content is fresh (synced within {STALENESS_THRESHOLD_MINUTES}min). "
                           f"{item_count} items available. Use Search(scope='platform_content', platform='{platform}') to query.",
            }
    except Exception as e:
        # Non-fatal — proceed with sync anyway
        logger.warning(f"[REFRESH] Freshness check failed for {platform}: {e}")

    # 3. Run synchronous sync via existing worker pipeline
    try:
        from workers.platform_worker import _sync_platform_async

        logger.info(f"[REFRESH] Starting sync for user {user_id[:8]}... platform={platform}")

        result = await _sync_platform_async(
            user_id=user_id,
            provider=platform,
            selected_sources=None,  # Worker fetches from DB
            supabase_url=os.environ.get("SUPABASE_URL"),
            supabase_key=os.environ.get("SUPABASE_SERVICE_KEY"),
        )

        if result.get("success"):
            items_synced = result.get("items_synced", 0)
            logger.info(f"[REFRESH] Completed: {platform} → {items_synced} items")

            return {
                "success": True,
                "platform": platform,
                "items_synced": items_synced,
                "refreshed_at": datetime.now(timezone.utc).isoformat(),
                "message": f"Refreshed {platform}: {items_synced} items synced. "
                           f"Use Search(scope='platform_content', platform='{platform}') to query.",
            }
        else:
            error_msg = result.get("error", "Unknown sync error")
            logger.warning(f"[REFRESH] Sync failed for {platform}: {error_msg}")
            return {
                "success": False,
                "error": "sync_failed",
                "platform": platform,
                "message": f"Failed to refresh {platform}: {error_msg}",
            }

    except Exception as e:
        logger.error(f"[REFRESH] Unexpected error syncing {platform}: {e}")
        return {
            "success": False,
            "error": "refresh_failed",
            "platform": platform,
            "message": f"Failed to refresh {platform}: {e}",
        }
