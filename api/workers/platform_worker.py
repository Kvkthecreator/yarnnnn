"""
Platform Sync Worker

Background worker for syncing platform data (Slack, Gmail, Notion, Calendar).
Called by RQ when platform_sync jobs are enqueued.

ADR-056: Per-Source Sync Implementation
- Only syncs user's selected sources (not all available)
- Respects tier limits via selected_sources list
- Enables monetization based on source count

This refreshes the filesystem_items for a provider by:
1. Filtering to selected sources only
2. Fetching recent content per source
3. Storing in filesystem_items table with TTL
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
        result = client.table("platform_connections").select("*").eq(
            "user_id", user_id
        ).eq("platform", provider).single().execute()

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
        client.table("platform_connections").update({
            "last_synced_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", integration["id"]).execute()

        # ADR-058: Trigger profile inference after successful sync
        try:
            from services.profile_inference import trigger_profile_inference_after_sync
            await trigger_profile_inference_after_sync(user_id, provider, client)
        except Exception as e:
            logger.warning(f"[PLATFORM_WORKER] Profile inference failed (non-critical): {e}")

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

            # Store in filesystem_items
            for msg in messages:
                await _store_filesystem_items(
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

    ADR-055/ADR-056: Label-based sync - only syncs selected labels.
    selected_sources format: ["label:Label_123", "label:Label_456"] or ["Label_123", "Label_456"]
    """
    from integrations.core.google_client import GoogleAPIClient
    from datetime import timedelta
    import os

    settings = integration.get("settings", {})
    refresh_token = integration.get("refresh_token")

    if not refresh_token:
        return {"error": "Missing Gmail refresh token", "items_synced": 0}

    # ADR-056: If no sources selected, nothing to sync
    if not selected_sources:
        logger.info("[PLATFORM_WORKER] No Gmail labels selected, skipping sync")
        return {"items_synced": 0, "labels_synced": 0, "skipped": "no_sources_selected"}

    logger.info(f"[PLATFORM_WORKER] Gmail sync: {len(selected_sources)} labels selected")

    google_client = GoogleAPIClient()
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        return {"error": "Missing Google OAuth credentials", "items_synced": 0}

    items_synced = 0
    labels_synced = 0

    try:
        # ADR-055: Recency filter - last 7 days
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
        date_filter = f"after:{cutoff_date.strftime('%Y/%m/%d')}"

        for source in selected_sources:
            # Handle both "label:Label_123" and "Label_123" formats
            if source.startswith("label:"):
                label_id = source.split(":", 1)[1]
                resource_id = source  # Keep full format for storage
            else:
                label_id = source
                resource_id = f"label:{source}"

            logger.debug(f"[PLATFORM_WORKER] Syncing Gmail label: {label_id}")

            try:
                # Fetch messages for this label
                messages = await google_client.list_gmail_messages(
                    client_id=client_id,
                    client_secret=client_secret,
                    refresh_token=refresh_token,
                    query=date_filter,
                    max_results=50,
                    label_ids=[label_id],
                )

                # Fetch and store full message content
                for msg in messages[:50]:  # Cap at 50 per label
                    msg_id = msg.get("id")
                    if not msg_id:
                        continue

                    try:
                        full_msg = await google_client.get_gmail_message(
                            message_id=msg_id,
                            client_id=client_id,
                            client_secret=client_secret,
                            refresh_token=refresh_token,
                        )

                        # Extract headers
                        headers = {h["name"].lower(): h["value"] for h in full_msg.get("payload", {}).get("headers", [])}
                        subject = headers.get("subject", "No subject")
                        sender = headers.get("from", "")
                        date_str = headers.get("date", "")

                        await _store_filesystem_items(
                            client=client,
                            user_id=user_id,
                            source_type="gmail",
                            resource_id=resource_id,  # ADR-055: Use label: prefix
                            resource_name=subject,
                            content=full_msg.get("snippet", ""),
                            content_type="email",
                            metadata={
                                "message_id": msg_id,
                                "from": sender,
                                "label_id": label_id,
                                "labels": full_msg.get("labelIds", []),
                            },
                            source_timestamp=date_str,
                        )
                        items_synced += 1

                    except Exception as e:
                        logger.warning(f"[PLATFORM_WORKER] Failed to fetch Gmail message {msg_id}: {e}")

                labels_synced += 1

            except Exception as e:
                logger.warning(f"[PLATFORM_WORKER] Failed to sync Gmail label {label_id}: {e}")

        logger.info(f"[PLATFORM_WORKER] Gmail sync complete: {labels_synced} labels, {items_synced} emails")
        return {
            "items_synced": items_synced,
            "labels_synced": labels_synced,
        }

    except Exception as e:
        logger.warning(f"[PLATFORM_WORKER] Gmail sync error: {e}")
        return {"error": str(e), "items_synced": items_synced}


async def _sync_notion(client, user_id: str, integration: dict, selected_sources: list[str]) -> dict:
    """
    Sync Notion pages.

    ADR-056: Directly fetches selected pages by ID (not search-then-filter).
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

    logger.info(f"[PLATFORM_WORKER] Notion sync: {len(selected_sources)} pages selected")

    manager = MCPClientManager()
    items_synced = 0
    pages_synced = 0
    pages_failed = 0

    try:
        # ADR-056: Directly fetch each selected page by ID
        for page_id in selected_sources:
            try:
                logger.debug(f"[PLATFORM_WORKER] Fetching Notion page: {page_id}")

                page_content = await manager.get_notion_page_content(
                    user_id=user_id,
                    page_id=page_id,
                    auth_token=notion_token,
                )

                if not page_content:
                    logger.warning(f"[PLATFORM_WORKER] Notion page not found: {page_id}")
                    pages_failed += 1
                    continue

                page_title = page_content.get("title", "Untitled")

                # Extract text content from page
                content = page_content.get("content", "")
                if isinstance(content, list):
                    # If content is blocks, join text
                    content = "\n".join(
                        block.get("text", "") if isinstance(block, dict) else str(block)
                        for block in content
                    )

                await _store_filesystem_items(
                    client=client,
                    user_id=user_id,
                    source_type="notion",
                    resource_id=page_id,
                    resource_name=page_title,
                    content=content,
                    content_type="page",
                    metadata={
                        "url": page_content.get("url"),
                        "last_edited": page_content.get("last_edited_time"),
                    },
                    source_timestamp=page_content.get("last_edited_time"),
                )
                items_synced += 1
                pages_synced += 1

            except Exception as e:
                logger.warning(f"[PLATFORM_WORKER] Failed to sync Notion page {page_id}: {e}")
                pages_failed += 1

        logger.info(f"[PLATFORM_WORKER] Notion sync complete: {pages_synced} pages synced, {pages_failed} failed")
        return {
            "items_synced": items_synced,
            "pages_synced": pages_synced,
            "pages_failed": pages_failed,
        }

    except Exception as e:
        logger.warning(f"[PLATFORM_WORKER] Notion sync error: {e}")
        return {"error": str(e), "items_synced": items_synced}
    finally:
        await manager.close_all()


async def _sync_calendar(client, user_id: str, integration: dict, selected_sources: list[str]) -> dict:
    """
    Sync Google Calendar events.

    ADR-056: Syncs only selected calendars (calendar IDs).
    Fetches upcoming events for the next 7 days.
    """
    from integrations.core.google_client import GoogleAPIClient
    import os

    settings = integration.get("settings", {})
    refresh_token = integration.get("refresh_token")

    if not refresh_token:
        return {"error": "Missing Calendar refresh token", "items_synced": 0}

    # ADR-056: If no sources selected, nothing to sync
    if not selected_sources:
        logger.info("[PLATFORM_WORKER] No calendars selected, skipping sync")
        return {"items_synced": 0, "calendars_synced": 0, "skipped": "no_sources_selected"}

    logger.info(f"[PLATFORM_WORKER] Calendar sync: {len(selected_sources)} calendars selected")

    google_client = GoogleAPIClient()
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        return {"error": "Missing Google OAuth credentials", "items_synced": 0}

    items_synced = 0
    calendars_synced = 0

    try:
        for calendar_id in selected_sources:
            try:
                logger.debug(f"[PLATFORM_WORKER] Syncing Calendar: {calendar_id}")

                # Fetch events for next 7 days
                events = await google_client.list_calendar_events(
                    client_id=client_id,
                    client_secret=client_secret,
                    refresh_token=refresh_token,
                    calendar_id=calendar_id,
                    time_min="now",
                    time_max="+7d",
                    max_results=50,
                )

                for event in events:
                    event_id = event.get("id")
                    if not event_id:
                        continue

                    summary = event.get("summary", "No title")
                    description = event.get("description", "")
                    location = event.get("location", "")

                    # Get start time
                    start = event.get("start", {})
                    start_time = start.get("dateTime") or start.get("date", "")

                    # Build content from event details
                    content_parts = [summary]
                    if description:
                        content_parts.append(description)
                    if location:
                        content_parts.append(f"Location: {location}")
                    content = "\n".join(content_parts)

                    await _store_filesystem_items(
                        client=client,
                        user_id=user_id,
                        source_type="calendar",
                        resource_id=calendar_id,
                        resource_name=summary,
                        content=content,
                        content_type="event",
                        metadata={
                            "event_id": event_id,
                            "start": start_time,
                            "end": event.get("end", {}).get("dateTime") or event.get("end", {}).get("date"),
                            "location": location,
                            "attendees": [a.get("email") for a in event.get("attendees", [])],
                            "html_link": event.get("htmlLink"),
                        },
                        source_timestamp=start_time,
                    )
                    items_synced += 1

                calendars_synced += 1

            except Exception as e:
                logger.warning(f"[PLATFORM_WORKER] Failed to sync calendar {calendar_id}: {e}")

        logger.info(f"[PLATFORM_WORKER] Calendar sync complete: {calendars_synced} calendars, {items_synced} events")
        return {
            "items_synced": items_synced,
            "calendars_synced": calendars_synced,
        }

    except Exception as e:
        logger.warning(f"[PLATFORM_WORKER] Calendar sync error: {e}")
        return {"error": str(e), "items_synced": items_synced}


async def _store_filesystem_items(
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
    """Store item in filesystem_items table with TTL."""
    from datetime import timedelta
    from uuid import uuid4

    # TTL based on source type
    ttl_hours = {
        "slack": 72,
        "gmail": 168,  # 1 week
        "notion": 168,
        "calendar": 168,  # 1 week
    }.get(source_type, 72)

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=ttl_hours)

    try:
        # Upsert to avoid duplicates
        client.table("filesystem_items").upsert({
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
