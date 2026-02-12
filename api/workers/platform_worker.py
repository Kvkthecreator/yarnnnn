"""
Platform Sync Worker

Background worker for syncing platform data (Slack, Gmail, Notion, Calendar).
Called by RQ when platform_sync jobs are enqueued.

ADR-056: Per-Source Sync Implementation
- Only syncs user's selected sources (not all available)
- Respects tier limits via selected_sources list
- Enables monetization based on source count

This refreshes the ephemeral_context for a provider by:
1. Filtering to selected sources only
2. Fetching recent content per source
3. Storing in ephemeral_context table with TTL
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from supabase import create_client

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s] %(message)s"
)
logger = logging.getLogger(__name__)


def sync_platform(
    user_id: str,
    provider: str,
    selected_sources: Optional[list[str]] = None,
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None,
) -> dict:
    """
    Background worker entry point for platform sync.

    ADR-056: Syncs only the user's selected sources, not all available.

    Args:
        user_id: User ID to sync for
        provider: Provider name (slack, gmail, notion, calendar)
        selected_sources: List of source IDs to sync (channel IDs, label IDs, etc.)
                         If None, will be fetched from integration.landscape.selected_sources
        supabase_url: Supabase URL (uses env var if not provided)
        supabase_key: Service role key (uses env var if not provided)

    Returns:
        Dict with sync result
    """
    sources_info = f", sources={len(selected_sources)}" if selected_sources else ""
    logger.info(f"[PLATFORM_WORKER] Starting sync: user={user_id[:8]}, provider={provider}{sources_info}")

    result = asyncio.run(_sync_platform_async(
        user_id=user_id,
        provider=provider,
        selected_sources=selected_sources,
        supabase_url=supabase_url or os.environ.get("SUPABASE_URL"),
        supabase_key=supabase_key or os.environ.get("SUPABASE_SERVICE_ROLE_KEY"),
    ))

    logger.info(f"[PLATFORM_WORKER] Completed: provider={provider}, success={result.get('success')}")
    return result


async def _sync_platform_async(
    user_id: str,
    provider: str,
    selected_sources: Optional[list[str]],
    supabase_url: str,
    supabase_key: str,
) -> dict:
    """
    Async implementation of platform sync.

    ADR-056: Extracts selected_sources from integration if not provided,
    then passes to provider-specific sync functions.
    """
    if not supabase_url or not supabase_key:
        logger.error("[PLATFORM_WORKER] Missing Supabase credentials")
        return {
            "success": False,
            "error": "Missing Supabase credentials",
        }

    client = create_client(supabase_url, supabase_key)

    try:
        # Get user's integration for this provider
        result = client.table("user_integrations").select("*").eq(
            "user_id", user_id
        ).eq("provider", provider).single().execute()

        if not result.data:
            return {
                "success": False,
                "error": f"No {provider} integration found for user",
            }

        integration = result.data

        # Check if integration is connected
        if integration.get("status") != "connected":
            return {
                "success": False,
                "error": f"{provider} integration is not connected",
            }

        # ADR-056: Extract selected_sources from landscape if not provided
        if selected_sources is None:
            landscape = integration.get("landscape", {}) or {}
            selected_list = landscape.get("selected_sources", [])
            # Extract just the IDs from the selected_sources objects
            selected_sources = [s.get("id") if isinstance(s, dict) else s for s in selected_list]
            logger.info(f"[PLATFORM_WORKER] Extracted {len(selected_sources)} selected sources from landscape")

        # Perform the sync based on provider
        if provider == "slack":
            sync_result = await _sync_slack(client, user_id, integration, selected_sources)
        elif provider == "gmail":
            sync_result = await _sync_gmail(client, user_id, integration, selected_sources)
        elif provider == "notion":
            sync_result = await _sync_notion(client, user_id, integration, selected_sources)
        elif provider == "calendar":
            sync_result = await _sync_calendar(client, user_id, integration, selected_sources)
        else:
            return {
                "success": False,
                "error": f"Unknown provider: {provider}",
            }

        # Update last_synced_at
        client.table("user_integrations").update({
            "last_synced_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", integration["id"]).execute()

        return {
            "success": True,
            "provider": provider,
            **sync_result,
        }

    except Exception as e:
        logger.error(f"[PLATFORM_WORKER] Sync failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


async def _sync_slack(client, user_id: str, integration: dict, selected_sources: list[str]) -> dict:
    """
    Sync Slack channels and messages.

    ADR-056: Only syncs channels in selected_sources list.
    """
    from integrations.core.client import MCPClientManager

    settings = integration.get("settings", {})
    bot_token = settings.get("bot_token") or integration.get("access_token")
    team_id = settings.get("team_id")

    if not bot_token:
        return {"error": "Missing Slack bot token", "items_synced": 0}

    # ADR-056: If no sources selected, nothing to sync
    if not selected_sources:
        logger.info("[PLATFORM_WORKER] No Slack channels selected, skipping sync")
        return {"items_synced": 0, "channels_synced": 0, "skipped": "no_sources_selected"}

    selected_set = set(selected_sources)
    logger.info(f"[PLATFORM_WORKER] Slack sync: {len(selected_set)} channels selected")

    manager = MCPClientManager()
    items_synced = 0
    channels_synced = 0
    channels_skipped = 0

    try:
        # Get list of channels
        channels = await manager.list_slack_channels(
            user_id=user_id,
            bot_token=bot_token,
            team_id=team_id,
        )

        # ADR-056: Filter to only selected channels
        for channel in channels:
            channel_id = channel.get("id")
            channel_name = channel.get("name", channel_id)

            # Skip if not in selected sources
            if channel_id not in selected_set:
                channels_skipped += 1
                continue

            logger.debug(f"[PLATFORM_WORKER] Syncing Slack channel: #{channel_name} ({channel_id})")

            messages = await manager.get_slack_messages(
                user_id=user_id,
                channel_id=channel_id,
                bot_token=bot_token,
                team_id=team_id,
                limit=50,
            )

            # Store in ephemeral_context
            for msg in messages:
                await _store_ephemeral_context(
                    client=client,
                    user_id=user_id,
                    source_type="slack",
                    resource_id=channel_id,
                    resource_name=f"#{channel_name}",
                    content=msg.get("text", ""),
                    content_type="message",
                    metadata={
                        "user": msg.get("user"),
                        "ts": msg.get("ts"),
                        "reactions": msg.get("reactions", []),
                    },
                    source_timestamp=msg.get("ts"),
                )
                items_synced += 1

            channels_synced += 1

        logger.info(f"[PLATFORM_WORKER] Slack sync complete: {channels_synced} channels, {items_synced} messages (skipped {channels_skipped})")
        return {
            "items_synced": items_synced,
            "channels_synced": channels_synced,
            "channels_skipped": channels_skipped,
        }

    except Exception as e:
        logger.warning(f"[PLATFORM_WORKER] Slack sync error: {e}")
        return {"error": str(e), "items_synced": items_synced}
    finally:
        await manager.close_all()


async def _sync_gmail(client, user_id: str, integration: dict, selected_sources: list[str]) -> dict:
    """
    Sync Gmail messages.

    ADR-055/ADR-056: Will implement label-based sync.
    For now, logs warning that label-based sync is pending implementation.

    selected_sources format: ["label:Label_123", "label:Label_456"]
    """
    from integrations.providers.gmail import GmailClient

    settings = integration.get("settings", {})
    access_token = integration.get("access_token")
    refresh_token = integration.get("refresh_token")

    if not access_token:
        return {"error": "Missing Gmail access token", "items_synced": 0}

    # ADR-055: TODO - Implement label-based sync
    # For now, warn that we're falling back to broad inbox
    if selected_sources:
        logger.warning(f"[PLATFORM_WORKER] Gmail label-based sync not yet implemented. "
                       f"Selected {len(selected_sources)} labels but syncing broad inbox instead.")

    items_synced = 0

    try:
        gmail = GmailClient(
            access_token=access_token,
            refresh_token=refresh_token,
        )

        # TODO ADR-055: Iterate over selected_sources (labels) and fetch per-label
        # For now, fetch recent emails broadly
        messages = await gmail.list_messages(max_results=50)

        for msg in messages:
            await _store_ephemeral_context(
                client=client,
                user_id=user_id,
                source_type="gmail",
                resource_id=msg.get("id"),
                resource_name=msg.get("subject", "No subject"),
                content=msg.get("snippet", ""),
                content_type="email",
                metadata={
                    "from": msg.get("from"),
                    "to": msg.get("to"),
                    "labels": msg.get("labels", []),
                },
                source_timestamp=msg.get("date"),
            )
            items_synced += 1

        return {"items_synced": items_synced}

    except Exception as e:
        logger.warning(f"[PLATFORM_WORKER] Gmail sync error: {e}")
        return {"error": str(e), "items_synced": items_synced}


async def _sync_notion(client, user_id: str, integration: dict, selected_sources: list[str]) -> dict:
    """
    Sync Notion pages.

    ADR-056: Only syncs pages in selected_sources list.
    """
    from integrations.core.client import MCPClientManager

    settings = integration.get("settings", {})
    notion_token = settings.get("notion_token") or integration.get("access_token")

    if not notion_token:
        return {"error": "Missing Notion token", "items_synced": 0}

    # ADR-056: If no sources selected, nothing to sync
    if not selected_sources:
        logger.info("[PLATFORM_WORKER] No Notion pages selected, skipping sync")
        return {"items_synced": 0, "pages_synced": 0, "skipped": "no_sources_selected"}

    selected_set = set(selected_sources)
    logger.info(f"[PLATFORM_WORKER] Notion sync: {len(selected_set)} pages selected")

    manager = MCPClientManager()
    items_synced = 0
    pages_synced = 0
    pages_skipped = 0

    try:
        # Search for recent pages (we still need to fetch to get content)
        pages = await manager.search_notion(
            user_id=user_id,
            notion_token=notion_token,
            query="",  # Empty query returns recent pages
            limit=100,  # Fetch more to increase chance of hitting selected ones
        )

        # ADR-056: Filter to only selected pages
        for page in pages:
            page_id = page.get("id")

            # Skip if not in selected sources
            if page_id not in selected_set:
                pages_skipped += 1
                continue

            page_title = page.get("title", "Untitled")
            logger.debug(f"[PLATFORM_WORKER] Syncing Notion page: {page_title} ({page_id})")

            await _store_ephemeral_context(
                client=client,
                user_id=user_id,
                source_type="notion",
                resource_id=page_id,
                resource_name=page_title,
                content=page.get("content", ""),
                content_type="page",
                metadata={
                    "url": page.get("url"),
                    "last_edited": page.get("last_edited_time"),
                },
                source_timestamp=page.get("last_edited_time"),
            )
            items_synced += 1
            pages_synced += 1

        logger.info(f"[PLATFORM_WORKER] Notion sync complete: {pages_synced} pages synced (skipped {pages_skipped})")
        return {
            "items_synced": items_synced,
            "pages_synced": pages_synced,
            "pages_skipped": pages_skipped,
        }

    except Exception as e:
        logger.warning(f"[PLATFORM_WORKER] Notion sync error: {e}")
        return {"error": str(e), "items_synced": items_synced}
    finally:
        await manager.close_all()


async def _sync_calendar(client, user_id: str, integration: dict, selected_sources: list[str]) -> dict:
    """
    Sync Google Calendar events.

    ADR-056: Placeholder - calendar sync not yet implemented.
    """
    # ADR-056: Calendar sync is defined in tier limits but not implemented yet
    logger.warning("[PLATFORM_WORKER] Calendar sync not yet implemented")

    if not selected_sources:
        return {"items_synced": 0, "skipped": "no_sources_selected"}

    # TODO: Implement calendar sync
    # 1. Use Google Calendar API to fetch events
    # 2. Iterate over selected_sources (calendar IDs)
    # 3. Store events in ephemeral_context

    return {
        "items_synced": 0,
        "error": "Calendar sync not yet implemented",
        "calendars_requested": len(selected_sources),
    }


async def _store_ephemeral_context(
    client,
    user_id: str,
    source_type: str,
    resource_id: str,
    resource_name: str,
    content: str,
    content_type: str,
    metadata: dict,
    source_timestamp: Optional[str] = None,
) -> None:
    """Store item in ephemeral_context table with TTL."""
    from datetime import timedelta
    from uuid import uuid4

    # TTL based on source type
    ttl_hours = {
        "slack": 72,
        "gmail": 168,  # 1 week
        "notion": 168,
    }.get(source_type, 72)

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=ttl_hours)

    try:
        # Upsert to avoid duplicates
        client.table("ephemeral_context").upsert({
            "id": str(uuid4()),
            "user_id": user_id,
            "platform": source_type,
            "resource_id": resource_id,
            "resource_name": resource_name,
            "content": content[:10000],  # Truncate long content
            "content_type": content_type,
            "metadata": metadata,
            "source_timestamp": source_timestamp,
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
        }, on_conflict="user_id,platform,resource_id").execute()

    except Exception as e:
        logger.warning(f"[PLATFORM_WORKER] Failed to store context: {e}")


# For direct execution (development/testing)
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python -m workers.platform_worker <user_id> <provider>")
        sys.exit(1)

    user_id = sys.argv[1]
    provider = sys.argv[2]

    result = sync_platform(user_id, provider)
    print(f"Result: {result}")
