"""
Platform Sync Worker

Background worker for syncing platform data (Slack, Gmail, Notion, Calendar).
Called by RQ when platform_sync jobs are enqueued.

ADR-056: Per-Source Sync Implementation
- Only syncs user's selected sources (not all available)
- Respects tier limits via selected_sources list
- Enables monetization based on source count

ADR-072: Unified Content Layer
- Writes to platform_content table (replaces filesystem_items)
- Content starts as ephemeral (retained=false, expires_at set)
- Downstream systems mark content as retained when referenced

ADR-073: Sync Tokens (Incremental Sync)
- Reads/writes platform_cursor via sync_registry for each (user, platform, resource)
- Slack: passes `oldest` ts to skip already-fetched messages
- Gmail: refines `after:` date query from last sync timestamp
- Calendar: uses Google Calendar syncToken for delta event sync
- Notion: compares last_edited_time to skip unchanged pages
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
        supabase_key=supabase_key or os.environ.get("SUPABASE_SERVICE_KEY"),
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

        # Check if integration is connected (accept both "connected" and "active")
        status = integration.get("status")
        if status not in ("connected", "active"):
            return {
                "success": False,
                "error": f"{provider} integration is not connected (status={status})",
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
        elif provider == "google":
            # Google OAuth provides both Gmail and Calendar from a single connection.
            # Split selected_sources by type using landscape resource metadata.
            landscape = integration.get("landscape", {}) or {}
            resources = landscape.get("resources", [])
            gmail_ids = {r["id"] for r in resources if isinstance(r, dict) and r.get("metadata", {}).get("platform") == "gmail"}
            calendar_ids = {r["id"] for r in resources if isinstance(r, dict) and r.get("metadata", {}).get("platform") == "calendar"}

            gmail_sources = [s for s in selected_sources if s in gmail_ids]
            calendar_sources = [s for s in selected_sources if s in calendar_ids]

            total_items = 0
            errors = []

            if gmail_sources:
                gmail_result = await _sync_gmail(client, user_id, integration, gmail_sources)
                total_items += gmail_result.get("items_synced", 0)
                if "error" in gmail_result:
                    errors.append(f"gmail: {gmail_result['error']}")

            if calendar_sources:
                cal_result = await _sync_calendar(client, user_id, integration, calendar_sources)
                total_items += cal_result.get("items_synced", 0)
                if "error" in cal_result:
                    errors.append(f"calendar: {cal_result['error']}")

            sync_result = {
                "items_synced": total_items,
                "gmail_sources": len(gmail_sources),
                "calendar_sources": len(calendar_sources),
            }
            if errors:
                sync_result["error"] = "; ".join(errors)

            logger.info(f"[PLATFORM_WORKER] Google split sync: gmail={len(gmail_sources)} sources, calendar={len(calendar_sources)} sources, items={total_items}")
        else:
            return {
                "success": False,
                "error": f"Unknown provider: {provider}",
            }

        # Check if sync actually succeeded (provider functions return error key on failure)
        has_error = "error" in sync_result and sync_result.get("items_synced", 0) == 0
        sync_success = not has_error

        # Only update last_synced_at if sync actually produced data
        if sync_success:
            client.table("platform_connections").update({
                "last_synced_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", integration["id"]).execute()

        # Activity log: record this sync batch (ADR-063)
        try:
            from services.activity_log import write_activity
            items_synced = sync_result.get("items_synced", 0)
            status_label = "error" if has_error else "success"
            await write_activity(
                client=client,
                user_id=user_id,
                event_type="platform_synced",
                summary=f"Synced {provider}: {items_synced} items ({status_label})",
                metadata={
                    "platform": provider,
                    "items_synced": items_synced,
                    **({} if not has_error else {"error": sync_result.get("error")}),
                },
            )
        except Exception:
            pass  # Non-fatal — never block sync

        return {
            "success": sync_success,
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
    from integrations.core.tokens import get_token_manager

    settings = integration.get("settings", {}) or {}
    metadata = integration.get("metadata", {}) or {}

    # Try multiple sources for bot token
    bot_token = settings.get("bot_token") or metadata.get("bot_token") or integration.get("access_token")

    # If not found, try decrypting credentials_encrypted
    if not bot_token and integration.get("credentials_encrypted"):
        try:
            token_manager = get_token_manager()
            bot_token = token_manager.decrypt(integration["credentials_encrypted"])
        except Exception as e:
            logger.warning(f"[PLATFORM_WORKER] Failed to decrypt Slack token: {e}")

    team_id = settings.get("team_id") or metadata.get("team_id")

    if not bot_token:
        return {"error": "Missing Slack bot token", "items_synced": 0}

    # ADR-056: If no sources selected, nothing to sync
    if not selected_sources:
        logger.info("[PLATFORM_WORKER] No Slack channels selected, skipping sync")
        return {"items_synced": 0, "channels_synced": 0, "skipped": "no_sources_selected"}

    from services.freshness import get_sync_state, update_sync_registry

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

            # ADR-073: Read sync cursor for incremental fetch
            sync_state = await get_sync_state(client, user_id, "slack", channel_id)
            oldest = sync_state.get("platform_cursor") if sync_state else None

            messages = await manager.get_slack_channel_history(
                user_id=user_id,
                channel_id=channel_id,
                bot_token=bot_token,
                team_id=team_id,
                limit=50,
                oldest=oldest,
            )

            # Track latest message ts for cursor update
            latest_ts = oldest
            for msg in messages:
                msg_ts = msg.get("ts", "")
                if msg_ts and (not latest_ts or msg_ts > latest_ts):
                    latest_ts = msg_ts

                try:
                    await _store_platform_content(
                        client=client,
                        user_id=user_id,
                        source_type="slack",
                        resource_id=channel_id,
                        resource_name=f"#{channel_name}",
                        item_id=msg_ts,
                        content=msg.get("text", ""),
                        content_type="message",
                        metadata={
                            "user": msg.get("user"),
                            "ts": msg_ts,
                            "reactions": msg.get("reactions", []),
                        },
                        source_timestamp=msg_ts,
                    )
                    items_synced += 1
                except Exception:
                    pass  # Already logged in _store_platform_content

            # ADR-073: Update sync cursor with latest message ts
            await update_sync_registry(
                client, user_id, "slack", channel_id,
                resource_name=f"#{channel_name}",
                platform_cursor=latest_ts,
                item_count=len(messages),
            )
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
    from integrations.core.tokens import get_token_manager
    from datetime import timedelta
    import os

    refresh_token_encrypted = integration.get("refresh_token_encrypted")
    if not refresh_token_encrypted:
        return {"error": "Missing Gmail refresh token", "items_synced": 0}

    token_manager = get_token_manager()
    refresh_token = token_manager.decrypt(refresh_token_encrypted)

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

    from services.freshness import get_sync_state, update_sync_registry

    items_synced = 0
    labels_synced = 0

    try:
        for source in selected_sources:
            # Handle both "label:Label_123" and "Label_123" formats
            if source.startswith("label:"):
                label_id = source.split(":", 1)[1]
                resource_id = source  # Keep full format for storage
            else:
                label_id = source
                resource_id = f"label:{source}"

            logger.debug(f"[PLATFORM_WORKER] Syncing Gmail label: {label_id}")

            # ADR-073: Use sync cursor for tighter date filter
            sync_state = await get_sync_state(client, user_id, "gmail", resource_id)
            if sync_state and sync_state.get("platform_cursor"):
                # Cursor stores ISO date of last successful sync
                date_filter = f"after:{sync_state['platform_cursor']}"
            else:
                # First sync: fall back to 7-day window
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
                date_filter = f"after:{cutoff_date.strftime('%Y/%m/%d')}"

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

                label_items = 0
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

                        await _store_platform_content(
                            client=client,
                            user_id=user_id,
                            source_type="gmail",
                            resource_id=resource_id,  # ADR-055: Use label: prefix
                            resource_name=subject,
                            item_id=msg_id,
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
                        label_items += 1

                    except Exception as e:
                        logger.warning(f"[PLATFORM_WORKER] Failed to fetch/store Gmail message {msg_id}: {e}")

                # ADR-073: Update sync cursor with today's date
                now = datetime.now(timezone.utc)
                await update_sync_registry(
                    client, user_id, "gmail", resource_id,
                    resource_name=label_id,
                    platform_cursor=now.strftime('%Y/%m/%d'),
                    item_count=label_items,
                )
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
    ADR-062: Uses NotionAPIClient (direct REST) instead of MCP Gateway.
             MCP Gateway requires internal ntn_... tokens; OAuth tokens only work via direct API.
    """
    from integrations.core.notion_client import get_notion_client
    from integrations.core.tokens import get_token_manager

    credentials_encrypted = integration.get("credentials_encrypted")
    if not credentials_encrypted:
        return {"error": "Missing Notion credentials", "items_synced": 0}

    token_manager = get_token_manager()
    access_token = token_manager.decrypt(credentials_encrypted)

    if not access_token:
        return {"error": "Failed to decrypt Notion access token", "items_synced": 0}

    # ADR-056: If no sources selected, nothing to sync
    if not selected_sources:
        logger.info("[PLATFORM_WORKER] No Notion pages selected, skipping sync")
        return {"items_synced": 0, "pages_synced": 0, "skipped": "no_sources_selected"}

    logger.info(f"[PLATFORM_WORKER] Notion sync: {len(selected_sources)} pages selected")

    from services.freshness import get_sync_state, update_sync_registry

    notion_client = get_notion_client()
    items_synced = 0
    pages_synced = 0
    pages_skipped = 0
    pages_failed = 0

    try:
        # ADR-056: Directly fetch each selected page by ID
        for page_id in selected_sources:
            try:
                logger.debug(f"[PLATFORM_WORKER] Fetching Notion page: {page_id}")

                # Fetch page metadata (title, last_edited_time, url)
                page_meta = await notion_client.get_page(access_token, page_id)

                # Extract title from page properties
                page_title = "Untitled"
                props = page_meta.get("properties", {})
                for prop in props.values():
                    if prop.get("type") == "title":
                        title_parts = prop.get("title", [])
                        page_title = "".join(t.get("plain_text", "") for t in title_parts) or "Untitled"
                        break

                last_edited = page_meta.get("last_edited_time")
                page_url = page_meta.get("url")

                # ADR-073: Skip content fetch if page hasn't changed since last sync
                sync_state = await get_sync_state(client, user_id, "notion", page_id)
                if sync_state and sync_state.get("platform_cursor") == last_edited:
                    logger.debug(f"[PLATFORM_WORKER] Notion page {page_id} unchanged, skipping content fetch")
                    pages_skipped += 1
                    continue

                # Fetch page content blocks
                blocks = await notion_client.get_page_content(access_token, page_id)
                content = _extract_text_from_notion_blocks(blocks)

                await _store_platform_content(
                    client=client,
                    user_id=user_id,
                    source_type="notion",
                    resource_id=page_id,
                    resource_name=page_title,
                    item_id=page_id,
                    content=content,
                    content_type="page",
                    metadata={
                        "url": page_url,
                        "last_edited": last_edited,
                    },
                    source_timestamp=last_edited,
                )
                items_synced += 1
                pages_synced += 1

                # ADR-073: Save last_edited_time as cursor
                await update_sync_registry(
                    client, user_id, "notion", page_id,
                    resource_name=page_title,
                    platform_cursor=last_edited,
                    item_count=1,
                )

            except Exception as e:
                logger.warning(f"[PLATFORM_WORKER] Failed to sync Notion page {page_id}: {e}")
                pages_failed += 1

        logger.info(f"[PLATFORM_WORKER] Notion sync complete: {pages_synced} synced, {pages_skipped} unchanged, {pages_failed} failed")
        return {
            "items_synced": items_synced,
            "pages_synced": pages_synced,
            "pages_skipped": pages_skipped,
            "pages_failed": pages_failed,
        }

    except Exception as e:
        logger.warning(f"[PLATFORM_WORKER] Notion sync error: {e}")
        return {"error": str(e), "items_synced": items_synced}


def _extract_text_from_notion_blocks(blocks: list[dict]) -> str:
    """
    Extract plain text from Notion block objects.

    Notion API returns structured block objects, each with a `type` and
    a matching key containing rich_text arrays.
    """
    lines = []
    text_block_types = {
        "paragraph", "heading_1", "heading_2", "heading_3",
        "bulleted_list_item", "numbered_list_item", "to_do",
        "toggle", "quote", "callout", "code",
    }

    for block in blocks:
        block_type = block.get("type", "")
        block_data = block.get(block_type, {})

        if block_type in text_block_types:
            rich_text = block_data.get("rich_text", [])
            text = "".join(t.get("plain_text", "") for t in rich_text)
            if text:
                lines.append(text)

    return "\n".join(lines)


async def _sync_calendar(client, user_id: str, integration: dict, selected_sources: list[str]) -> dict:
    """
    Sync Google Calendar events.

    ADR-056: Syncs only selected calendars (calendar IDs).
    Fetches upcoming events for the next 7 days.
    """
    from integrations.core.google_client import GoogleAPIClient
    from integrations.core.tokens import get_token_manager
    import os

    refresh_token_encrypted = integration.get("refresh_token_encrypted")
    if not refresh_token_encrypted:
        return {"error": "Missing Calendar refresh token", "items_synced": 0}

    token_manager = get_token_manager()
    refresh_token = token_manager.decrypt(refresh_token_encrypted)

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

    from services.freshness import get_sync_state, update_sync_registry

    items_synced = 0
    calendars_synced = 0

    try:
        for calendar_id in selected_sources:
            try:
                logger.debug(f"[PLATFORM_WORKER] Syncing Calendar: {calendar_id}")

                # ADR-073: Try incremental sync with syncToken first
                sync_state = await get_sync_state(client, user_id, "calendar", calendar_id)
                stored_sync_token = sync_state.get("platform_cursor") if sync_state else None

                if stored_sync_token:
                    cal_result = await google_client.list_calendar_events(
                        client_id=client_id,
                        client_secret=client_secret,
                        refresh_token=refresh_token,
                        calendar_id=calendar_id,
                        max_results=50,
                        sync_token=stored_sync_token,
                    )
                    # If token expired (410 Gone), fall back to full sync
                    if cal_result.get("invalid_sync_token"):
                        logger.info(f"[PLATFORM_WORKER] Calendar syncToken expired for {calendar_id}, doing full sync")
                        stored_sync_token = None

                if not stored_sync_token:
                    # Full sync: fetch events for next 7 days
                    cal_result = await google_client.list_calendar_events(
                        client_id=client_id,
                        client_secret=client_secret,
                        refresh_token=refresh_token,
                        calendar_id=calendar_id,
                        time_min="now",
                        time_max="+7d",
                        max_results=50,
                    )

                events = cal_result.get("items", [])
                next_sync_token = cal_result.get("next_sync_token")

                for event in events:
                    event_id = event.get("id")
                    if not event_id:
                        continue

                    # Incremental sync may return cancelled events
                    if event.get("status") == "cancelled":
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

                    await _store_platform_content(
                        client=client,
                        user_id=user_id,
                        source_type="calendar",
                        resource_id=calendar_id,
                        resource_name=summary,
                        item_id=event_id,
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

                # ADR-073: Save syncToken for next incremental sync
                await update_sync_registry(
                    client, user_id, "calendar", calendar_id,
                    platform_cursor=next_sync_token,
                    item_count=len(events),
                )
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


async def _store_platform_content(
    client,
    user_id: str,
    source_type: str,
    resource_id: str,
    resource_name: str,
    item_id: str,
    content: str,
    content_type: str,
    metadata: dict,
    source_timestamp: Optional[str] = None,
) -> None:
    """Store item in platform_content table with TTL (ADR-072).

    item_id is the platform-native identifier for the specific item within the resource:
    - Slack: message ts
    - Gmail: message_id
    - Calendar: event_id
    - Notion: page_id (same as resource_id for Notion since each page is its own resource)

    Upserts on (user_id, platform, resource_id, item_id, content_hash) — matching the UNIQUE constraint.
    Content starts as ephemeral (retained=false); downstream systems mark as retained when referenced.
    """
    from datetime import timedelta
    import hashlib

    # TTL based on source type (ADR-072)
    ttl_hours = {
        "slack": 168,     # 7 days
        "gmail": 336,     # 14 days
        "notion": 720,    # 30 days
        "calendar": 24,   # 1 day
    }.get(source_type, 168)

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=ttl_hours)
    content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()

    # Convert Unix epoch timestamps (e.g. Slack ts "1771827176.313839") to ISO 8601
    iso_timestamp = None
    if source_timestamp:
        try:
            # Check if it looks like a Unix epoch (all digits and dots)
            float_val = float(source_timestamp)
            if float_val > 1_000_000_000:  # Clearly a Unix epoch
                iso_timestamp = datetime.fromtimestamp(float_val, tz=timezone.utc).isoformat()
            else:
                iso_timestamp = source_timestamp
        except (ValueError, TypeError, OSError):
            iso_timestamp = source_timestamp  # Pass through as-is (RFC dates, ISO dates)

    try:
        client.table("platform_content").upsert({
            "user_id": user_id,
            "platform": source_type,
            "resource_id": resource_id,
            "resource_name": resource_name,
            "item_id": item_id,
            "content": content[:10000],
            "content_type": content_type,
            "content_hash": content_hash,
            "metadata": metadata,
            "source_timestamp": iso_timestamp,
            "fetched_at": now.isoformat(),
            "retained": False,
            "expires_at": expires_at.isoformat(),
        }, on_conflict="user_id,platform,resource_id,item_id,content_hash").execute()

    except Exception as e:
        logger.warning(f"[PLATFORM_WORKER] Failed to store content: {e}")
        raise  # Re-raise so callers can track failures


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
