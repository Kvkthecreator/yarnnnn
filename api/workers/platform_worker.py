"""
Platform Sync Worker

Background worker for syncing platform data (Slack, Gmail, Notion).
Called by RQ when platform_sync jobs are enqueued.

This refreshes the ephemeral_context for a provider by:
1. Discovering resources (landscape)
2. Fetching recent content
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
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None,
) -> dict:
    """
    Background worker entry point for platform sync.

    Args:
        user_id: User ID to sync for
        provider: Provider name (slack, gmail, notion)
        supabase_url: Supabase URL (uses env var if not provided)
        supabase_key: Service role key (uses env var if not provided)

    Returns:
        Dict with sync result
    """
    logger.info(f"[PLATFORM_WORKER] Starting sync: user={user_id[:8]}, provider={provider}")

    result = asyncio.run(_sync_platform_async(
        user_id=user_id,
        provider=provider,
        supabase_url=supabase_url or os.environ.get("SUPABASE_URL"),
        supabase_key=supabase_key or os.environ.get("SUPABASE_SERVICE_ROLE_KEY"),
    ))

    logger.info(f"[PLATFORM_WORKER] Completed: provider={provider}, success={result.get('success')}")
    return result


async def _sync_platform_async(
    user_id: str,
    provider: str,
    supabase_url: str,
    supabase_key: str,
) -> dict:
    """
    Async implementation of platform sync.
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

        # Perform the sync based on provider
        if provider == "slack":
            sync_result = await _sync_slack(client, user_id, integration)
        elif provider == "gmail":
            sync_result = await _sync_gmail(client, user_id, integration)
        elif provider == "notion":
            sync_result = await _sync_notion(client, user_id, integration)
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


async def _sync_slack(client, user_id: str, integration: dict) -> dict:
    """Sync Slack channels and messages."""
    from integrations.core.client import MCPClientManager

    settings = integration.get("settings", {})
    bot_token = settings.get("bot_token") or integration.get("access_token")
    team_id = settings.get("team_id")

    if not bot_token:
        return {"error": "Missing Slack bot token", "items_synced": 0}

    manager = MCPClientManager()
    items_synced = 0

    try:
        # Get list of channels
        channels = await manager.list_slack_channels(
            user_id=user_id,
            bot_token=bot_token,
            team_id=team_id,
        )

        # For each channel, fetch recent messages and store as ephemeral context
        for channel in channels[:10]:  # Limit to 10 channels
            channel_id = channel.get("id")
            channel_name = channel.get("name", channel_id)

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

        return {"items_synced": items_synced}

    except Exception as e:
        logger.warning(f"[PLATFORM_WORKER] Slack sync error: {e}")
        return {"error": str(e), "items_synced": items_synced}
    finally:
        await manager.close_all()


async def _sync_gmail(client, user_id: str, integration: dict) -> dict:
    """Sync Gmail messages."""
    from integrations.providers.gmail import GmailClient

    settings = integration.get("settings", {})
    access_token = integration.get("access_token")
    refresh_token = integration.get("refresh_token")

    if not access_token:
        return {"error": "Missing Gmail access token", "items_synced": 0}

    items_synced = 0

    try:
        gmail = GmailClient(
            access_token=access_token,
            refresh_token=refresh_token,
        )

        # Fetch recent emails
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


async def _sync_notion(client, user_id: str, integration: dict) -> dict:
    """Sync Notion pages."""
    from integrations.core.client import MCPClientManager

    settings = integration.get("settings", {})
    notion_token = settings.get("notion_token") or integration.get("access_token")

    if not notion_token:
        return {"error": "Missing Notion token", "items_synced": 0}

    manager = MCPClientManager()
    items_synced = 0

    try:
        # Search for recent pages
        pages = await manager.search_notion(
            user_id=user_id,
            notion_token=notion_token,
            query="",  # Empty query returns recent pages
            limit=20,
        )

        for page in pages:
            await _store_ephemeral_context(
                client=client,
                user_id=user_id,
                source_type="notion",
                resource_id=page.get("id"),
                resource_name=page.get("title", "Untitled"),
                content=page.get("content", ""),
                content_type="page",
                metadata={
                    "url": page.get("url"),
                    "last_edited": page.get("last_edited_time"),
                },
                source_timestamp=page.get("last_edited_time"),
            )
            items_synced += 1

        return {"items_synced": items_synced}

    except Exception as e:
        logger.warning(f"[PLATFORM_WORKER] Notion sync error: {e}")
        return {"error": str(e), "items_synced": items_synced}
    finally:
        await manager.close_all()


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
