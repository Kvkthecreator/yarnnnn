"""
Landscape Discovery Service

Discovers available resources (labels, channels, pages, calendars) from
connected platforms. Used by:
- GET /integrations/{provider}/landscape (on-demand from context page)
- Platform worker (after content sync to keep landscape fresh)

ADR-078: Smart auto-selection — when landscape is first discovered and no
sources are selected, auto-selects the most valuable sources up to tier limit.

No LLM calls — purely platform API reads.
"""

import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)


def _extract_notion_title(page: dict) -> str:
    """Extract title from Notion page object."""
    props = page.get("properties", {})
    for key in ["title", "Title", "Name", "name"]:
        if key in props:
            title_prop = props[key]
            if isinstance(title_prop, dict):
                title_array = title_prop.get("title") or title_prop.get("rich_text", [])
                if isinstance(title_array, list) and title_array:
                    return title_array[0].get("plain_text", "Untitled")
            elif isinstance(title_prop, str):
                return title_prop
    return "Untitled"


def _extract_notion_parent_type(page: dict) -> str:
    """Extract parent type from Notion page object."""
    parent = page.get("parent", {})
    if "workspace" in parent:
        return "workspace"
    elif "page_id" in parent:
        return "page"
    elif "database_id" in parent:
        return "database"
    return "unknown"


async def fetch_google_calendars(
    user_id: str,
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> list[dict]:
    """
    Fetch list of calendars from Google Calendar API.
    Uses refresh token to get fresh access token, then lists calendars.
    """
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
        )

        if token_response.status_code != 200:
            raise Exception(f"Failed to refresh token: {token_response.text}")

        access_token = token_response.json().get("access_token")

        calendar_response = await client.get(
            "https://www.googleapis.com/calendar/v3/users/me/calendarList",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"maxResults": 50}
        )

        if calendar_response.status_code != 200:
            raise Exception(f"Failed to list calendars: {calendar_response.text}")

        data = calendar_response.json()
        return data.get("items", [])


async def discover_landscape(provider: str, user_id: str, integration: dict) -> dict:
    """
    Discover resources from a provider.

    Args:
        provider: Platform name (gmail, google, slack, notion)
        user_id: User UUID
        integration: Row from platform_connections with credentials

    Returns:
        {"resources": [{"id": "...", "name": "...", "type": "...", "metadata": {...}}]}
    """
    from integrations.core.tokens import get_token_manager

    token_manager = get_token_manager()

    if provider in ("gmail", "google"):
        from integrations.core.google_client import get_google_client
        from integrations.core.oauth import OAUTH_CONFIGS

        google_client = get_google_client()
        google_config = OAUTH_CONFIGS.get("google") or OAUTH_CONFIGS["gmail"]
        client_id = google_config.client_id
        client_secret = google_config.client_secret

        # Determine access method: prefer refresh token, fall back to stored access token
        # (access token is valid ~1 hour after OAuth, enough for initial landscape discovery)
        access_token = None
        refresh_token = None

        if integration.get("refresh_token_encrypted"):
            refresh_token = token_manager.decrypt(integration["refresh_token_encrypted"])
        elif integration.get("credentials_encrypted"):
            access_token = token_manager.decrypt(integration["credentials_encrypted"])
            logger.info(
                f"[LANDSCAPE] No refresh token for {provider} user {user_id[:8]}, "
                "using stored access token for landscape discovery."
            )
        else:
            logger.warning(
                f"[LANDSCAPE] No refresh token or access token for {provider} user {user_id}. "
                "Cannot discover landscape."
            )
            return {"resources": []}

        resources = []

        # List Gmail labels
        try:
            if refresh_token:
                labels = await google_client.list_gmail_labels(
                    client_id=client_id,
                    client_secret=client_secret,
                    refresh_token=refresh_token
                )
            else:
                # Direct access token call (no refresh available)
                async with httpx.AsyncClient() as http_client:
                    resp = await http_client.get(
                        "https://gmail.googleapis.com/gmail/v1/users/me/labels",
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    data = resp.json()
                    if "error" in data:
                        raise RuntimeError(f"Gmail API error: {data['error'].get('message', data['error'])}")
                    labels = data.get("labels", [])

            for label in labels:
                resources.append({
                    "id": label.get("id"),
                    "name": label.get("name"),
                    "type": "label",
                    "metadata": {
                        "type": label.get("type"),
                        "messageListVisibility": label.get("messageListVisibility"),
                        "labelListVisibility": label.get("labelListVisibility"),
                        "platform": "gmail",
                    }
                })
        except Exception as e:
            logger.warning(f"[LANDSCAPE] Failed to list Gmail labels for {user_id}: {e}")

        # Also list calendars (Google OAuth covers both Gmail and Calendar)
        try:
            if refresh_token:
                calendars = await fetch_google_calendars(
                    user_id=user_id,
                    client_id=client_id,
                    client_secret=client_secret,
                    refresh_token=refresh_token
                )
            else:
                # Direct access token call (no refresh available)
                async with httpx.AsyncClient() as http_client:
                    resp = await http_client.get(
                        "https://www.googleapis.com/calendar/v3/users/me/calendarList",
                        headers={"Authorization": f"Bearer {access_token}"},
                        params={"maxResults": 50},
                    )
                    data = resp.json()
                    if "error" in data:
                        raise RuntimeError(f"Calendar API error: {data['error']}")
                    calendars = data.get("items", [])

            for cal in calendars:
                resources.append({
                    "id": cal.get("id"),
                    "name": cal.get("summary", "Untitled Calendar"),
                    "type": "calendar",
                    "metadata": {
                        "primary": cal.get("primary", False),
                        "accessRole": cal.get("accessRole"),
                        "platform": "calendar",
                    }
                })
        except Exception as e:
            logger.warning(f"[LANDSCAPE] Failed to list calendars for {user_id}: {e}")

        return {"resources": resources}

    elif provider == "slack":
        from integrations.core.slack_client import get_slack_client

        bot_token = token_manager.decrypt(integration["credentials_encrypted"])
        slack_client = get_slack_client()

        # ADR-077: Use paginated channel list for full discovery
        channels = await slack_client.list_channels_paginated(bot_token=bot_token)

        resources = []
        for channel in channels:
            resources.append({
                "id": channel.get("id"),
                "name": f"#{channel.get('name', '')}",
                "type": "channel",
                "metadata": {
                    "is_private": channel.get("is_private", False),
                    "num_members": channel.get("num_members", 0),
                    "topic": channel.get("topic"),
                    "purpose": channel.get("purpose"),
                }
            })

        return {"resources": resources}

    elif provider == "notion":
        from integrations.core.notion_client import get_notion_client

        auth_token = token_manager.decrypt(integration["credentials_encrypted"])

        try:
            notion_client = get_notion_client()
            # ADR-077: Paginated search for full workspace discovery
            pages = await notion_client.search_paginated(
                access_token=auth_token, query="", max_results=500
            )
        except Exception as e:
            logger.warning(f"[LANDSCAPE] Notion search failed: {e}")
            return {"resources": []}

        resources = []
        for page in pages:
            resources.append({
                "id": page.get("id"),
                "name": _extract_notion_title(page),
                "type": "page" if page.get("object") == "page" else "database",
                "metadata": {
                    "parent_type": _extract_notion_parent_type(page),
                    "last_edited": page.get("last_edited_time"),
                    "url": page.get("url")
                }
            })

        return {"resources": resources}

    return {"resources": []}


def compute_smart_defaults(
    provider: str,
    resources: list[dict],
    max_sources: int,
) -> list[dict]:
    """
    ADR-078: Auto-select the most valuable sources up to tier limit.

    Called when landscape is first discovered and no sources are selected,
    or when backfilling existing users. Returns a list of selected source
    objects ({"id": ..., "name": ..., "type": ...}).

    Selection heuristics per platform:
    - Slack: Sort by num_members desc (busy channels = more context)
    - Gmail: INBOX + SENT first, then user-created labels (skip system noise)
    - Calendar: ALL calendars (unlimited, tiny data volume)
    - Notion: Sort by last_edited desc (recently active pages = most relevant)
    """
    if not resources:
        return []

    selected = []

    if provider in ("gmail", "google"):
        # Split by metadata.platform
        gmail_resources = [r for r in resources if r.get("metadata", {}).get("platform") == "gmail"]
        calendar_resources = [r for r in resources if r.get("metadata", {}).get("platform") == "calendar"]

        # Calendar: auto-select ALL (unlimited tier, tiny data)
        for cal in calendar_resources:
            selected.append({
                "id": cal["id"],
                "name": cal.get("name", ""),
                "type": cal.get("type", "calendar"),
            })

        # Gmail: prioritize high-value labels
        # Priority order: INBOX > SENT > STARRED > IMPORTANT > user labels > system labels
        GMAIL_PRIORITY = ["INBOX", "SENT", "STARRED", "IMPORTANT"]
        GMAIL_SKIP = {"SPAM", "TRASH", "DRAFT", "UNREAD", "CATEGORY_PERSONAL",
                       "CATEGORY_SOCIAL", "CATEGORY_PROMOTIONS", "CATEGORY_UPDATES",
                       "CATEGORY_FORUMS"}

        priority_labels = []
        user_labels = []
        for r in gmail_resources:
            label_id = r.get("id", "")
            label_type = r.get("metadata", {}).get("type", "")
            if label_id in GMAIL_PRIORITY:
                priority_labels.append((GMAIL_PRIORITY.index(label_id), r))
            elif label_id in GMAIL_SKIP:
                continue  # Never auto-select noise labels
            elif label_type == "user" or "/" in r.get("name", ""):
                # User-created labels or nested labels (e.g., INBOX/FYI)
                user_labels.append(r)

        # Sort priority labels by defined order
        priority_labels.sort(key=lambda x: x[0])
        gmail_ranked = [r for _, r in priority_labels] + user_labels

        # Apply limit (max_sources applies to gmail portion only)
        for r in gmail_ranked[:max_sources]:
            selected.append({
                "id": r["id"],
                "name": r.get("name", ""),
                "type": r.get("type", "label"),
            })

    elif provider == "slack":
        # Sort by num_members descending — busiest channels have most context
        ranked = sorted(
            resources,
            key=lambda r: r.get("metadata", {}).get("num_members", 0),
            reverse=True,
        )
        for r in ranked[:max_sources]:
            selected.append({
                "id": r["id"],
                "name": r.get("name", ""),
                "type": r.get("type", "channel"),
            })

    elif provider == "notion":
        # Sort by last_edited descending — recently active pages are most relevant
        def notion_sort_key(r):
            edited = r.get("metadata", {}).get("last_edited", "")
            # Deprioritize "Untitled" pages
            name_penalty = "0" if r.get("name", "").startswith("Untitled") else "1"
            return (name_penalty, edited or "")

        ranked = sorted(resources, key=notion_sort_key, reverse=True)
        for r in ranked[:max_sources]:
            selected.append({
                "id": r["id"],
                "name": r.get("name", ""),
                "type": r.get("type", "page"),
            })

    return selected


async def refresh_landscape(
    client,
    user_id: str,
    provider: str,
    integration: dict,
) -> bool:
    """
    Refresh landscape for a platform, preserving selected_sources.

    Called after content sync to keep the landscape in sync with
    the actual platform state.

    Args:
        client: Supabase service-role client
        user_id: User UUID
        provider: Platform name
        integration: Row from platform_connections

    Returns:
        True if landscape was updated, False on error
    """
    try:
        new_landscape = await discover_landscape(provider, user_id, integration)

        if not new_landscape.get("resources"):
            logger.info(f"[LANDSCAPE] No resources discovered for {provider} user {user_id[:8]}, skipping update")
            return False

        # Re-read selected_sources from DB (not the stale integration dict)
        # to avoid overwriting user changes made during sync
        fresh = client.table("platform_connections").select(
            "landscape"
        ).eq("id", integration["id"]).limit(1).execute()

        fresh_landscape = (fresh.data[0].get("landscape") or {}) if fresh.data else {}
        selected_sources = fresh_landscape.get("selected_sources", [])

        # Filter out stale source IDs that no longer exist in the new landscape
        # selected_sources can be dicts ({"id": ..., "name": ...}) or plain strings
        new_resource_ids = {r["id"] for r in new_landscape["resources"]}
        valid_sources = [
            s for s in selected_sources
            if (s.get("id") if isinstance(s, dict) else s) in new_resource_ids
        ]

        if len(valid_sources) < len(selected_sources):
            removed = len(selected_sources) - len(valid_sources)
            logger.info(f"[LANDSCAPE] Pruned {removed} stale source(s) for {provider} user {user_id[:8]}")

        # ADR-078: If no sources are selected after pruning, auto-select smart defaults
        if valid_sources:
            new_landscape["selected_sources"] = valid_sources
        else:
            from services.platform_limits import get_limits_for_user, PROVIDER_LIMIT_MAP
            limits = get_limits_for_user(client, user_id)
            limit_field = PROVIDER_LIMIT_MAP.get(
                "gmail" if provider == "google" else provider,
                "slack_channels"
            )
            max_sources = getattr(limits, limit_field, 5)
            if max_sources == -1:
                max_sources = 999
            smart_selected = compute_smart_defaults(
                provider, new_landscape["resources"], max_sources
            )
            new_landscape["selected_sources"] = smart_selected
            logger.info(
                f"[LANDSCAPE] Auto-selected {len(smart_selected)} sources for "
                f"{provider} user {user_id[:8]} (no prior selection)"
            )

        client.table("platform_connections").update({
            "landscape": new_landscape,
            "landscape_discovered_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", integration["id"]).execute()

        logger.info(
            f"[LANDSCAPE] Refreshed {provider} for user {user_id[:8]}: "
            f"{len(new_landscape['resources'])} resources, "
            f"{len(new_landscape.get('selected_sources', []))} selected"
        )
        return True

    except Exception as e:
        logger.warning(f"[LANDSCAPE] Refresh failed for {provider} user {user_id[:8]}: {e}")
        return False
