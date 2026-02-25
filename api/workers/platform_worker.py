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
import base64
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

        # Refresh landscape alongside content sync (keeps resource list current)
        try:
            from services.landscape import refresh_landscape
            await refresh_landscape(client, user_id, provider, integration)
        except Exception as e:
            logger.warning(f"[PLATFORM_WORKER] Landscape refresh failed (non-fatal): {e}")

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
    ADR-077: Full paginated fetch, thread expansion, system message filtering, user resolution.
    """
    from integrations.core.slack_client import get_slack_client
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

    if not bot_token:
        return {"error": "Missing Slack bot token", "items_synced": 0}

    # ADR-056: If no sources selected, nothing to sync
    if not selected_sources:
        logger.info("[PLATFORM_WORKER] No Slack channels selected, skipping sync")
        return {"items_synced": 0, "channels_synced": 0, "skipped": "no_sources_selected"}

    from services.freshness import get_sync_state, update_sync_registry

    # ADR-077: System subtypes to filter out (noise, not conversation content)
    SKIP_SUBTYPES = {
        "bot_message", "channel_join", "channel_leave",
        "channel_purpose", "channel_topic", "channel_rename",
        "channel_archive", "channel_unarchive", "group_join",
        "group_leave", "group_purpose", "group_topic",
    }
    MAX_THREAD_EXPANSIONS = 20  # Cap thread fetches per channel per sync

    selected_set = set(selected_sources)
    logger.info(f"[PLATFORM_WORKER] Slack sync: {len(selected_set)} channels selected")

    slack_client = get_slack_client()
    items_synced = 0
    channels_synced = 0

    try:
        for channel_id in selected_set:
            try:
                # ADR-073: Read sync cursor for incremental fetch
                sync_state = await get_sync_state(client, user_id, "slack", channel_id)
                oldest = sync_state.get("platform_cursor") if sync_state else None
                is_initial = oldest is None

                # ADR-077: Paginated fetch — 1000 on initial backfill, 500 on incremental
                max_msgs = 1000 if is_initial else 500

                messages, error = await slack_client.get_channel_history_paginated(
                    bot_token=bot_token,
                    channel_id=channel_id,
                    oldest=oldest,
                    max_messages=max_msgs,
                )

                # Handle not_in_channel with auto-join
                if error == "not_in_channel":
                    joined = await slack_client.join_channel(bot_token=bot_token, channel_id=channel_id)
                    if joined:
                        messages, error = await slack_client.get_channel_history_paginated(
                            bot_token=bot_token, channel_id=channel_id,
                            oldest=oldest, max_messages=max_msgs,
                        )

                if error and not messages:
                    logger.warning(f"[PLATFORM_WORKER] Slack channel {channel_id} error: {error}")
                    continue

                # ADR-077: Filter system messages, collect user IDs for resolution
                user_ids: set[str] = set()
                filtered_messages = []
                for msg in messages:
                    subtype = msg.get("subtype")
                    if subtype in SKIP_SUBTYPES:
                        continue
                    filtered_messages.append(msg)
                    if msg.get("user"):
                        user_ids.add(msg["user"])

                # ADR-077: Resolve user IDs to display names (once per channel)
                user_names: dict[str, str] = {}
                if user_ids:
                    try:
                        user_names = await slack_client.resolve_users(bot_token, user_ids)
                    except Exception as e:
                        logger.warning(f"[PLATFORM_WORKER] User resolution failed: {e}")

                # Get channel name from landscape or use ID
                channel_name = channel_id
                landscape = integration.get("landscape", {}) or {}
                for r in landscape.get("resources", []):
                    if isinstance(r, dict) and r.get("id") == channel_id:
                        channel_name = r.get("name", channel_id)
                        break

                # Track latest message ts for cursor update
                latest_ts = oldest
                thread_expansions = 0

                for msg in filtered_messages:
                    msg_ts = msg.get("ts", "")
                    if msg_ts and (not latest_ts or msg_ts > latest_ts):
                        latest_ts = msg_ts

                    msg_user = msg.get("user", "")
                    author = user_names.get(msg_user, msg_user)

                    try:
                        await _store_platform_content(
                            client=client,
                            user_id=user_id,
                            source_type="slack",
                            resource_id=channel_id,
                            resource_name=channel_name,
                            item_id=msg_ts,
                            content=msg.get("text", ""),
                            content_type="message",
                            author=author,
                            metadata={
                                "user": msg_user,
                                "ts": msg_ts,
                                "reactions": msg.get("reactions", []),
                                "reply_count": msg.get("reply_count", 0),
                            },
                            source_timestamp=msg_ts,
                        )
                        items_synced += 1
                    except Exception:
                        pass

                    # ADR-077: Expand threads with 2+ replies (cap per channel)
                    reply_count = msg.get("reply_count", 0)
                    if reply_count >= 2 and thread_expansions < MAX_THREAD_EXPANSIONS:
                        thread_expansions += 1
                        try:
                            replies = await slack_client.get_thread_replies(
                                bot_token=bot_token,
                                channel_id=channel_id,
                                thread_ts=msg_ts,
                            )
                            for reply in replies:
                                reply_ts = reply.get("ts", "")
                                reply_user = reply.get("user", "")
                                reply_author = user_names.get(reply_user, reply_user)

                                await _store_platform_content(
                                    client=client,
                                    user_id=user_id,
                                    source_type="slack",
                                    resource_id=channel_id,
                                    resource_name=channel_name,
                                    item_id=reply_ts,
                                    content=reply.get("text", ""),
                                    content_type="thread_reply",
                                    author=reply_author,
                                    metadata={
                                        "user": reply_user,
                                        "ts": reply_ts,
                                        "thread_ts": msg_ts,
                                    },
                                    source_timestamp=reply_ts,
                                )
                                items_synced += 1
                        except Exception as e:
                            logger.warning(f"[PLATFORM_WORKER] Thread expansion failed for {msg_ts}: {e}")

                # ADR-073: Update sync cursor with latest message ts
                await update_sync_registry(
                    client, user_id, "slack", channel_id,
                    resource_name=channel_name,
                    platform_cursor=latest_ts,
                    item_count=len(filtered_messages),
                )
                channels_synced += 1

                logger.info(
                    f"[PLATFORM_WORKER] Slack {channel_name}: "
                    f"{len(filtered_messages)} messages, {thread_expansions} threads expanded"
                )

            except Exception as e:
                logger.warning(f"[PLATFORM_WORKER] Slack channel {channel_id} sync error: {e}")

        logger.info(f"[PLATFORM_WORKER] Slack sync complete: {channels_synced} channels, {items_synced} items")
        return {
            "items_synced": items_synced,
            "channels_synced": channels_synced,
        }

    except Exception as e:
        logger.warning(f"[PLATFORM_WORKER] Slack sync error: {e}")
        return {"error": str(e), "items_synced": items_synced}


def _extract_gmail_body(payload: dict) -> str:
    """Extract plain text body from Gmail message payload.

    Gmail messages can be:
    - Simple: body.data directly on payload
    - Multipart: parts[] with different mimeTypes
    - Nested multipart: parts containing parts (multipart/alternative inside multipart/mixed)
    """
    def _decode_body(data: str) -> str:
        try:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        except Exception:
            return ""

    def _find_text_parts(part: dict) -> list[str]:
        mime = part.get("mimeType", "")
        body_data = part.get("body", {}).get("data")
        parts = part.get("parts", [])

        if mime == "text/plain" and body_data:
            return [_decode_body(body_data)]
        if mime == "text/html" and body_data and not parts:
            # HTML fallback — strip tags for plain text
            import re
            html = _decode_body(body_data)
            text = re.sub(r"<[^>]+>", " ", html)
            text = re.sub(r"\s+", " ", text).strip()
            return [text]
        # Recurse into sub-parts
        results = []
        for sub in parts:
            results.extend(_find_text_parts(sub))
        return results

    texts = _find_text_parts(payload)
    return "\n".join(texts)[:10000] if texts else ""


async def _sync_gmail(client, user_id: str, integration: dict, selected_sources: list[str]) -> dict:
    """
    Sync Gmail messages.

    ADR-055/ADR-056: Label-based sync - only syncs selected labels.
    ADR-077: Paginated message list, concurrent fetch, 30-day initial window.
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

    # ADR-077: Concurrent message fetch helper
    sem = asyncio.Semaphore(10)

    async def _fetch_one_message(msg_id: str) -> Optional[dict]:
        async with sem:
            try:
                return await google_client.get_gmail_message(
                    message_id=msg_id,
                    client_id=client_id,
                    client_secret=client_secret,
                    refresh_token=refresh_token,
                )
            except Exception as e:
                logger.warning(f"[PLATFORM_WORKER] Failed to fetch Gmail message {msg_id}: {e}")
                return None

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
                date_filter = f"after:{sync_state['platform_cursor']}"
            else:
                # ADR-077: 30-day initial window (was 7 days)
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
                date_filter = f"after:{cutoff_date.strftime('%Y/%m/%d')}"

            try:
                # ADR-077: Paginated fetch — up to 200 message stubs per label
                messages = await google_client.list_gmail_messages_paginated(
                    client_id=client_id,
                    client_secret=client_secret,
                    refresh_token=refresh_token,
                    query=date_filter,
                    label_ids=[label_id],
                    max_messages=200,
                )

                # ADR-077: Concurrent message content fetch (batches of 10)
                msg_ids = [m.get("id") for m in messages if m.get("id")]
                label_items = 0

                # Fetch in batches of 10 concurrently
                for batch_start in range(0, len(msg_ids), 10):
                    batch = msg_ids[batch_start:batch_start + 10]
                    full_msgs = await asyncio.gather(
                        *[_fetch_one_message(mid) for mid in batch]
                    )

                    for full_msg in full_msgs:
                        if not full_msg:
                            continue

                        msg_id = full_msg.get("id", "")

                        # Extract headers
                        headers = {
                            h["name"].lower(): h["value"]
                            for h in full_msg.get("payload", {}).get("headers", [])
                        }
                        subject = headers.get("subject", "No subject")
                        sender = headers.get("from", "")
                        date_str = headers.get("date", "")

                        # Extract body text from payload
                        body_text = _extract_gmail_body(full_msg.get("payload", {}))
                        content = body_text or full_msg.get("snippet", "")

                        try:
                            await _store_platform_content(
                                client=client,
                                user_id=user_id,
                                source_type="gmail",
                                resource_id=resource_id,
                                resource_name=subject,
                                item_id=msg_id,
                                content=content,
                                title=subject,
                                author=sender,
                                content_type="email",
                                metadata={
                                    "message_id": msg_id,
                                    "subject": subject,
                                    "from": sender,
                                    "label_id": label_id,
                                    "labels": full_msg.get("labelIds", []),
                                    "thread_id": full_msg.get("threadId"),
                                },
                                source_timestamp=date_str,
                            )
                            items_synced += 1
                            label_items += 1
                        except Exception as e:
                            logger.warning(f"[PLATFORM_WORKER] Failed to store Gmail message {msg_id}: {e}")

                # ADR-073: Update sync cursor with today's date
                now = datetime.now(timezone.utc)
                await update_sync_registry(
                    client, user_id, "gmail", resource_id,
                    resource_name=label_id,
                    platform_cursor=now.strftime('%Y/%m/%d'),
                    item_count=label_items,
                )
                labels_synced += 1

                logger.info(f"[PLATFORM_WORKER] Gmail label {label_id}: {label_items} emails from {len(msg_ids)} found")

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
    Sync Notion pages and databases.

    ADR-056: Directly fetches selected pages/databases by ID.
    ADR-077: Recursive block fetch, database query support, rate limiting.
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
        logger.info("[PLATFORM_WORKER] No Notion sources selected, skipping sync")
        return {"items_synced": 0, "pages_synced": 0, "skipped": "no_sources_selected"}

    logger.info(f"[PLATFORM_WORKER] Notion sync: {len(selected_sources)} sources selected")

    from services.freshness import get_sync_state, update_sync_registry

    notion_client = get_notion_client()
    items_synced = 0
    pages_synced = 0
    pages_skipped = 0
    pages_failed = 0

    # ADR-077: Determine source types from landscape metadata
    landscape = integration.get("landscape", {}) or {}
    resource_types = {}
    for r in landscape.get("resources", []):
        if isinstance(r, dict) and r.get("id"):
            resource_types[r["id"]] = r.get("type", "page")

    async def _sync_one_page(page_id: str, parent_resource_id: Optional[str] = None) -> bool:
        """Sync a single Notion page. Returns True if content was stored."""
        nonlocal items_synced, pages_synced, pages_skipped, pages_failed

        try:
            page_meta = await notion_client.get_page(access_token, page_id)

            # Extract title
            page_title = "Untitled"
            props = page_meta.get("properties", {})
            for prop in props.values():
                if prop.get("type") == "title":
                    title_parts = prop.get("title", [])
                    page_title = "".join(t.get("plain_text", "") for t in title_parts) or "Untitled"
                    break

            last_edited = page_meta.get("last_edited_time")
            page_url = page_meta.get("url")
            resource_id = parent_resource_id or page_id

            # ADR-073: Skip if unchanged
            sync_state = await get_sync_state(client, user_id, "notion", page_id)
            if sync_state and sync_state.get("platform_cursor") == last_edited:
                pages_skipped += 1
                return False

            # ADR-077: Recursive block fetch with pagination
            blocks = await notion_client.get_page_content_full(
                access_token, page_id, max_blocks=500, max_depth=3
            )
            content = _extract_text_from_notion_blocks(blocks)

            await _store_platform_content(
                client=client,
                user_id=user_id,
                source_type="notion",
                resource_id=resource_id,
                resource_name=page_title,
                item_id=page_id,
                content=content,
                content_type="page",
                metadata={
                    "url": page_url,
                    "last_edited": last_edited,
                    "parent_database": parent_resource_id,
                },
                source_timestamp=last_edited,
            )
            items_synced += 1
            pages_synced += 1

            await update_sync_registry(
                client, user_id, "notion", page_id,
                resource_name=page_title,
                platform_cursor=last_edited,
                item_count=1,
            )
            return True

        except Exception as e:
            logger.warning(f"[PLATFORM_WORKER] Failed to sync Notion page {page_id}: {e}")
            pages_failed += 1
            return False

    try:
        for source_id in selected_sources:
            source_type = resource_types.get(source_id, "page")

            if source_type == "database":
                # ADR-077: Query database rows (child pages) and sync each
                try:
                    # Rate limit
                    await asyncio.sleep(0.35)
                    db_pages = await notion_client.query_database(
                        access_token, source_id, page_size=100, max_pages=3
                    )
                    logger.info(f"[PLATFORM_WORKER] Notion database {source_id}: {len(db_pages)} rows")

                    for db_page in db_pages:
                        child_page_id = db_page.get("id")
                        if child_page_id:
                            await asyncio.sleep(0.35)  # Rate limit
                            await _sync_one_page(child_page_id, parent_resource_id=source_id)

                except Exception as e:
                    logger.warning(f"[PLATFORM_WORKER] Failed to query Notion database {source_id}: {e}")
                    pages_failed += 1
            else:
                # Regular page sync
                await asyncio.sleep(0.35)  # Rate limit
                await _sync_one_page(source_id)

        logger.info(
            f"[PLATFORM_WORKER] Notion sync complete: "
            f"{pages_synced} synced, {pages_skipped} unchanged, {pages_failed} failed"
        )
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

    ADR-077: Extended to handle additional block types including
    tables, columns, bookmarks, embeds, and dividers.
    """
    lines = []
    text_block_types = {
        "paragraph", "heading_1", "heading_2", "heading_3",
        "bulleted_list_item", "numbered_list_item", "to_do",
        "toggle", "quote", "callout", "code",
        "table_row",
    }

    for block in blocks:
        block_type = block.get("type", "")
        block_data = block.get(block_type, {})

        if block_type in text_block_types:
            rich_text = block_data.get("rich_text", [])
            # table_row uses "cells" instead of "rich_text"
            if block_type == "table_row":
                cells = block_data.get("cells", [])
                cell_texts = []
                for cell in cells:
                    cell_texts.append("".join(t.get("plain_text", "") for t in cell))
                text = " | ".join(cell_texts)
            else:
                text = "".join(t.get("plain_text", "") for t in rich_text)
            if text:
                lines.append(text)
        elif block_type == "bookmark":
            url = block_data.get("url", "")
            caption = block_data.get("caption", [])
            caption_text = "".join(t.get("plain_text", "") for t in caption)
            if url:
                lines.append(f"[Bookmark: {caption_text or url}]")
        elif block_type == "embed":
            url = block_data.get("url", "")
            if url:
                lines.append(f"[Embed: {url}]")
        elif block_type == "divider":
            lines.append("---")

    return "\n".join(lines)


async def _sync_calendar(client, user_id: str, integration: dict, selected_sources: list[str]) -> dict:
    """
    Sync Google Calendar events.

    ADR-056: Syncs only selected calendars (calendar IDs).
    ADR-077: Wider time window (-7d to +14d), pagination, debug logging.
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

    logger.info(f"[PLATFORM_WORKER] Calendar sync: {len(selected_sources)} calendars selected: {selected_sources}")

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
                logger.info(f"[PLATFORM_WORKER] Syncing calendar: {calendar_id}")

                # ADR-073: Try incremental sync with syncToken first
                sync_state = await get_sync_state(client, user_id, "calendar", calendar_id)
                stored_sync_token = sync_state.get("platform_cursor") if sync_state else None

                cal_result = None
                if stored_sync_token:
                    logger.info(f"[PLATFORM_WORKER] Calendar {calendar_id}: attempting incremental sync with stored token")
                    cal_result = await google_client.list_calendar_events(
                        client_id=client_id,
                        client_secret=client_secret,
                        refresh_token=refresh_token,
                        calendar_id=calendar_id,
                        max_results=200,
                        sync_token=stored_sync_token,
                    )
                    # If token expired (410 Gone), fall back to full sync
                    if cal_result.get("invalid_sync_token"):
                        logger.info(f"[PLATFORM_WORKER] Calendar syncToken expired for {calendar_id}, falling back to full sync")
                        cal_result = None

                if cal_result is None:
                    # ADR-077: Full sync with wider window — past 7 days + next 14 days
                    logger.info(f"[PLATFORM_WORKER] Calendar {calendar_id}: full sync -7d to +14d")
                    cal_result = await google_client.list_calendar_events(
                        client_id=client_id,
                        client_secret=client_secret,
                        refresh_token=refresh_token,
                        calendar_id=calendar_id,
                        time_min="-7d",
                        time_max="+14d",
                        max_results=200,
                    )

                events = cal_result.get("items", [])
                next_sync_token = cal_result.get("next_sync_token")

                logger.info(
                    f"[PLATFORM_WORKER] Calendar {calendar_id}: "
                    f"API returned {len(events)} events, "
                    f"next_sync_token={'yes' if next_sync_token else 'no'}"
                )

                stored_count = 0
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

                    # Get start/end times
                    start = event.get("start", {})
                    start_time = start.get("dateTime") or start.get("date", "")
                    end = event.get("end", {})
                    end_time = end.get("dateTime") or end.get("date", "")

                    # Build content from event details
                    content_parts = [summary]
                    if start_time:
                        content_parts.append(f"When: {start_time} — {end_time}")
                    if description:
                        content_parts.append(description)
                    if location:
                        content_parts.append(f"Location: {location}")
                    attendees = event.get("attendees", [])
                    if attendees:
                        names = [a.get("displayName") or a.get("email", "") for a in attendees[:10]]
                        content_parts.append(f"Attendees: {', '.join(names)}")
                    content = "\n".join(content_parts)

                    try:
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
                                "end": end_time,
                                "location": location,
                                "attendees": [a.get("email") for a in attendees],
                                "organizer": event.get("organizer", {}).get("email"),
                                "html_link": event.get("htmlLink"),
                                "status": event.get("status"),
                            },
                            source_timestamp=start_time,
                        )
                        items_synced += 1
                        stored_count += 1
                    except Exception as e:
                        logger.warning(f"[PLATFORM_WORKER] Failed to store calendar event {event_id}: {e}")

                # ADR-073: Save syncToken for next incremental sync
                await update_sync_registry(
                    client, user_id, "calendar", calendar_id,
                    platform_cursor=next_sync_token,
                    item_count=stored_count,
                )
                calendars_synced += 1

                logger.info(f"[PLATFORM_WORKER] Calendar {calendar_id}: {stored_count} events stored")

            except Exception as e:
                logger.warning(f"[PLATFORM_WORKER] Failed to sync calendar {calendar_id}: {e}", exc_info=True)

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
    title: Optional[str] = None,
    author: Optional[str] = None,
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

    # TTL based on source type (ADR-072, extended ADR-077)
    ttl_hours = {
        "slack": 336,     # 14 days (was 7)
        "gmail": 720,     # 30 days (was 14)
        "notion": 2160,   # 90 days (was 30)
        "calendar": 48,   # 2 days  (was 1)
    }.get(source_type, 336)

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

    row = {
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
    }
    if title:
        row["title"] = title
    if author:
        row["author"] = author

    try:
        client.table("platform_content").upsert(
            row, on_conflict="user_id,platform,resource_id,item_id,content_hash"
        ).execute()

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
