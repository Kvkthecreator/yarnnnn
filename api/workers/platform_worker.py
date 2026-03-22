"""
Platform Sync Worker

Background worker for syncing platform data (Slack, Notion).
Called by scheduler cron, manual "Sync Now" button, and TP RefreshPlatformContent.

ADR-131: Gmail and Calendar integrations sunset — only Slack and Notion remain.

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
- Notion: compares last_edited_time to skip unchanged pages

ADR-112: Sync Efficiency & Concurrency Control
- Atomic sync lock on platform_connections prevents overlapping syncs
- Heartbeat fast-path (Phase 0) checks for platform changes before source iteration
- All three sync paths (scheduled, manual, TP) coordinate via the same lock
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from supabase import create_client

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ADR-112: Stale lock timeout — if a sync started more than this long ago,
# assume it crashed and allow a new sync to proceed.
_SYNC_LOCK_TIMEOUT = timedelta(minutes=10)


async def acquire_sync_lock(client, user_id: str, platform: str) -> bool:
    """Atomically acquire the sync lock for a platform connection.

    ADR-112: Prevents overlapping syncs from any path (scheduled, manual, TP).
    Uses UPDATE ... WHERE to atomically check and set the lock.
    Stale locks (older than _SYNC_LOCK_TIMEOUT) are force-acquired.

    Returns True if lock acquired, False if another sync is in progress.
    """
    now = datetime.now(timezone.utc)
    stale_cutoff = (now - _SYNC_LOCK_TIMEOUT).isoformat()

    # Google OAuth may store as gmail/google — check both
    if platform in ("gmail", "calendar", "google"):
        db_platforms = ["gmail", "google"]
    else:
        db_platforms = [platform]

    # Use microsecond-precision timestamp as a nonce to verify we own the lock.
    lock_nonce = now.isoformat()

    try:
        for db_platform in db_platforms:
            # Conditional UPDATE: only set lock if not already held (or stale).
            # PostgREST .or_() with .update() may return empty result.data even
            # when the update succeeds, so we verify ownership via the nonce.
            client.table("platform_connections").update({
                "sync_in_progress": True,
                "sync_started_at": lock_nonce,
            }).eq("user_id", user_id).eq("platform", db_platform).or_(
                "sync_in_progress.eq.false,sync_in_progress.is.null,sync_started_at.lt." + stale_cutoff
            ).execute()

            # Verify: did our conditional update succeed? The DB stores our exact
            # nonce only if the WHERE conditions were met.
            check = client.table("platform_connections").select(
                "sync_started_at"
            ).eq("user_id", user_id).eq("platform", db_platform).eq(
                "sync_in_progress", True
            ).limit(1).execute()

            if check.data and check.data[0].get("sync_started_at", "").startswith(lock_nonce[:23]):
                return True
        return False
    except Exception as e:
        logger.warning(f"[SYNC_LOCK] Failed to acquire lock for {platform}: {e}")
        return False


async def release_sync_lock(client, user_id: str, platform: str) -> None:
    """Release the sync lock for a platform connection.

    ADR-112: Called in finally block after sync completes (success or failure).
    """
    if platform in ("gmail", "calendar", "google"):
        db_platforms = ["gmail", "google"]
    else:
        db_platforms = [platform]

    try:
        for db_platform in db_platforms:
            client.table("platform_connections").update({
                "sync_in_progress": False,
                "sync_started_at": None,
            }).eq("user_id", user_id).eq("platform", db_platform).execute()
    except Exception as e:
        logger.warning(f"[SYNC_LOCK] Failed to release lock for {platform}: {e}")


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
    ADR-112: Acquires sync lock before execution, releases in finally block.
    """
    if not supabase_url or not supabase_key:
        logger.error("[PLATFORM_WORKER] Missing Supabase credentials")
        return {
            "success": False,
            "error": "Missing Supabase credentials",
        }

    client = create_client(supabase_url, supabase_key)

    try:
        # Google OAuth may be stored as platform="gmail" or platform="google" depending
        # on when the connection was created. Try both variants for Google-related providers.
        if provider in ("gmail", "calendar", "google"):
            db_candidates = ["gmail", "google"]
        else:
            db_candidates = [provider]

        # Find an active connection from the candidate platform names
        integration = None
        for db_platform in db_candidates:
            try:
                result = client.table("platform_connections").select("*").eq(
                    "user_id", user_id
                ).eq("platform", db_platform).maybe_single().execute()
                if result.data and result.data.get("status") in ("connected", "active"):
                    integration = result.data
                    break
            except Exception:
                continue

        if not integration:
            return {
                "success": False,
                "error": f"No active {provider} integration found for user",
            }

        # ADR-112: Acquire sync lock — prevents overlapping syncs from any path
        lock_acquired = await acquire_sync_lock(client, user_id, provider)
        if not lock_acquired:
            logger.info(f"[PLATFORM_WORKER] Sync already in progress for {provider}, skipping")
            return {
                "success": True,
                "skipped": True,
                "error": "sync_already_in_progress",
                "message": f"Sync already in progress for {provider}",
                "items_synced": 0,
            }

        try:
            return await _sync_platform_inner(client, user_id, provider, selected_sources, integration)
        finally:
            await release_sync_lock(client, user_id, provider)

    except Exception as e:
        logger.error(f"[PLATFORM_WORKER] Sync failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


async def _sync_platform_inner(
    client,
    user_id: str,
    provider: str,
    selected_sources: Optional[list[str]],
    integration: dict,
) -> dict:
    """Inner sync logic, called with lock held. ADR-112: Extracted for lock/finally clarity."""
    try:
        # ADR-056: Extract selected_sources from landscape if not provided
        if selected_sources is None:
            landscape = integration.get("landscape", {}) or {}
            selected_list = landscape.get("selected_sources", [])
            # Extract just the IDs from the selected_sources objects
            selected_sources = [s.get("id") if isinstance(s, dict) else s for s in selected_list]
            logger.info(f"[PLATFORM_WORKER] Extracted {len(selected_sources)} selected sources from landscape")

        # ADR-112 Phase 0: Heartbeat fast-path — check if anything changed before
        # iterating sources. One lightweight API call per platform.
        heartbeat_skip = await _heartbeat_check(client, user_id, provider, integration)
        if heartbeat_skip:
            logger.info(f"[PLATFORM_WORKER] Heartbeat: no changes detected for {provider}, skipping source iteration")
            # Update sync_registry timestamps so freshness shows "fresh"
            from services.freshness import get_platform_freshness_from_registry
            # Activity log: record heartbeat-skipped sync
            try:
                from services.activity_log import write_activity
                await write_activity(
                    client=client,
                    user_id=user_id,
                    event_type="platform_synced",
                    summary=f"Synced {provider}: 0 items (no changes detected)",
                    metadata={"platform": provider, "items_synced": 0, "heartbeat": True},
                )
            except Exception:
                pass
            return {
                "success": True,
                "provider": provider,
                "items_synced": 0,
                "heartbeat_skip": True,
            }

        # Perform the sync based on provider
        if provider == "slack":
            sync_result = await _sync_slack(client, user_id, integration, selected_sources)
        elif provider == "notion":
            sync_result = await _sync_notion(client, user_id, integration, selected_sources)
        else:
            return {
                "success": False,
                "error": f"Unknown provider: {provider}",
            }

        # Check if sync actually succeeded (provider functions return error key on failure)
        has_error = "error" in sync_result and sync_result.get("items_synced", 0) == 0
        sync_success = not has_error

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

        # ADR-122: Onboarding Bootstrap — scaffold platform digest project on first sync
        if sync_success and not has_error:
            try:
                from services.onboarding_bootstrap import maybe_bootstrap_project
                project_slug = await maybe_bootstrap_project(client, user_id, provider)
                if project_slug:
                    logger.info(f"[PLATFORM_WORKER] Bootstrap project created: {project_slug}")
            except Exception as e:
                logger.warning(f"[PLATFORM_WORKER] Bootstrap check failed (non-fatal): {e}")

        # ADR-114: Event-driven Composer heartbeat after sync with new content
        items_synced = sync_result.get("items_synced", 0)
        if sync_success and items_synced > 0:
            try:
                from services.composer import maybe_trigger_heartbeat
                await maybe_trigger_heartbeat(client, user_id, "platform_synced", {
                    "platform": provider, "items_synced": items_synced,
                })
            except Exception as e:
                logger.warning(f"[PLATFORM_WORKER] Event heartbeat trigger failed: {e}")

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


async def _heartbeat_check(client, user_id: str, provider: str, integration: dict) -> bool:
    """ADR-112 Phase 0: Lightweight platform heartbeat to detect "nothing changed".

    Returns True if no changes detected (caller should skip full sync).
    Returns False if changes detected or on error (caller should proceed with full sync).

    Heartbeat cursors stored in platform_connections.settings.sync_cursor.
    """
    settings = integration.get("settings", {}) or {}
    sync_cursor = settings.get("sync_cursor", {}) or {}

    try:
        from integrations.core.tokens import get_token_manager

        if provider == "slack":
            # Slack: compare channel latest timestamps
            metadata = integration.get("metadata", {}) or {}
            bot_token = (
                settings.get("bot_token")
                or metadata.get("bot_token")
                or integration.get("access_token")
            )
            # Fallback: decrypt credentials_encrypted (same pattern as _sync_slack)
            if not bot_token and integration.get("credentials_encrypted"):
                try:
                    token_mgr = get_token_manager()
                    bot_token = token_mgr.decrypt(integration["credentials_encrypted"])
                except Exception:
                    pass
            if not bot_token:
                return False

            # Get selected channels
            landscape = integration.get("landscape", {}) or {}
            selected_list = landscape.get("selected_sources", [])
            channel_ids = [s.get("id") if isinstance(s, dict) else s for s in selected_list]
            channel_ids = [c for c in channel_ids if c]

            if not channel_ids:
                return False

            from integrations.core.slack_client import SlackAPIClient
            slack = SlackAPIClient()
            current_latest = await slack.get_channels_latest(bot_token, channel_ids)

            prev_latest = sync_cursor.get("slack_channel_latest", {})
            # Don't trust heartbeat if all values are "0" — means bot can't read channel info
            all_zero = all(v == "0" for v in current_latest.values()) if current_latest else True
            if all_zero:
                logger.warning(f"[HEARTBEAT] Slack: all channel latest values are '0' — bot may not have access, forcing full sync")
            if prev_latest and current_latest == prev_latest and not all_zero:
                return True  # No changes

            # Store updated cursor
            sync_cursor["slack_channel_latest"] = current_latest
            _update_sync_cursor(client, integration["id"], settings, sync_cursor)
            return False

        elif provider == "notion":
            # Notion: search for recently edited pages
            token_mgr = get_token_manager()
            creds = await token_mgr.get_credentials(client, user_id, "notion")
            if not creds:
                return False

            access_token = creds.get("access_token", "")
            if not access_token:
                return False

            from services.freshness import get_platform_freshness_from_registry
            last_synced = await get_platform_freshness_from_registry(client, user_id, "notion")
            if not last_synced:
                return False  # Never synced — must do full sync

            from integrations.core.notion_client import NotionAPIClient
            notion = NotionAPIClient()
            has_changes = await notion.check_recent_changes(access_token, last_synced)
            return not has_changes

    except Exception as e:
        logger.debug(f"[HEARTBEAT] Check failed for {provider} (falling through to full sync): {e}")
        return False

    return False


def _update_sync_cursor(client, connection_id: str, settings: dict, sync_cursor: dict) -> None:
    """Persist heartbeat cursor in platform_connections.settings (ADR-112)."""
    try:
        updated_settings = {**settings, "sync_cursor": sync_cursor}
        client.table("platform_connections").update({
            "settings": updated_settings,
        }).eq("id", connection_id).execute()
    except Exception as e:
        logger.debug(f"[HEARTBEAT] Failed to update sync_cursor: {e}")


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
    channel_errors: list[str] = []

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
                    channel_errors.append(f"{channel_id}:{error}")
                    await update_sync_registry(
                        client, user_id, "slack", channel_id,
                        last_error=f"Slack API error: {error}",
                    )
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
                channel_items = 0  # Per-channel item count for sync_registry

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
                        channel_items += 1
                    except Exception as e:
                        logger.warning(f"[SLACK] Failed to insert message {msg_ts} in {channel_name}: {e}")

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
                                channel_items += 1
                        except Exception as e:
                            logger.warning(f"[PLATFORM_WORKER] Thread expansion failed for {msg_ts}: {e}")

                # ADR-073: Update sync cursor with latest message ts
                await update_sync_registry(
                    client, user_id, "slack", channel_id,
                    resource_name=channel_name,
                    platform_cursor=latest_ts,
                    item_count=channel_items,
                )
                channels_synced += 1

                logger.info(
                    f"[PLATFORM_WORKER] Slack {channel_name}: "
                    f"{len(filtered_messages)} messages, {thread_expansions} threads expanded"
                )

            except Exception as e:
                logger.warning(f"[PLATFORM_WORKER] Slack channel {channel_id} sync error: {e}")
                channel_errors.append(f"{channel_id}:{str(e)[:120]}")
                await update_sync_registry(
                    client, user_id, "slack", channel_id,
                    last_error=str(e),
                )

        logger.info(f"[PLATFORM_WORKER] Slack sync complete: {channels_synced} channels, {items_synced} items")
        response = {
            "items_synced": items_synced,
            "channels_synced": channels_synced,
        }
        # If every selected channel failed, surface provider-level error.
        if channels_synced == 0 and channel_errors:
            response["error"] = "; ".join(channel_errors[:3])
        return response

    except Exception as e:
        logger.warning(f"[PLATFORM_WORKER] Slack sync error: {e}")
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
    resource_names = {}
    for r in landscape.get("resources", []):
        if isinstance(r, dict) and r.get("id"):
            resource_types[r["id"]] = r.get("type", "page")
            resource_names[r["id"]] = r.get("name", r["id"])

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
            await update_sync_registry(
                client, user_id, "notion", page_id,
                last_error=str(e),
            )
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

                    db_items_synced = 0
                    for db_page in db_pages:
                        child_page_id = db_page.get("id")
                        if child_page_id:
                            await asyncio.sleep(0.35)  # Rate limit
                            synced = await _sync_one_page(child_page_id, parent_resource_id=source_id)
                            if synced:
                                db_items_synced += 1

                    # Mark selected database source as synced even when no child rows changed.
                    await update_sync_registry(
                        client, user_id, "notion", source_id,
                        resource_name=resource_names.get(source_id, source_id),
                        platform_cursor=datetime.now(timezone.utc).isoformat(),
                        item_count=db_items_synced,
                    )

                except Exception as e:
                    logger.warning(f"[PLATFORM_WORKER] Failed to query Notion database {source_id}: {e}")
                    pages_failed += 1
                    await update_sync_registry(
                        client, user_id, "notion", source_id,
                        last_error=str(e),
                    )
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
