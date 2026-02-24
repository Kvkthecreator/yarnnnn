"""
Landscape Discovery Service

Discovers available resources (labels, channels, pages, calendars) from
connected platforms. Used by:
- GET /integrations/{provider}/landscape (on-demand from context page)
- Platform worker (after content sync to keep landscape fresh)

No LLM calls — purely platform API reads.
"""

import logging
from datetime import datetime, timezone

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
    import httpx

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

        if not integration.get("refresh_token_encrypted"):
            logger.warning(
                f"[LANDSCAPE] No refresh token for {provider} user {user_id}. "
                "Cannot discover landscape."
            )
            return {"resources": []}

        refresh_token = token_manager.decrypt(integration["refresh_token_encrypted"])
        resources = []

        # List Gmail labels
        try:
            labels = await google_client.list_gmail_labels(
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token
            )
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

        # Also list calendars if google provider
        if provider == "google":
            try:
                calendars = await fetch_google_calendars(
                    user_id=user_id,
                    client_id=client_id,
                    client_secret=client_secret,
                    refresh_token=refresh_token
                )
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
        from integrations.core.client import get_mcp_manager

        bot_token = token_manager.decrypt(integration["credentials_encrypted"])
        team_id = integration.get("metadata", {}).get("team_id", "")
        mcp_manager = get_mcp_manager()

        channels = await mcp_manager.list_slack_channels(
            user_id=user_id,
            bot_token=bot_token,
            team_id=team_id
        )

        resources = []
        for channel in channels:
            resources.append({
                "id": channel.get("id"),
                "name": f"#{channel.get('name', '')}",
                "type": "channel",
                "metadata": {
                    "is_private": channel.get("is_private", False),
                    "num_members": channel.get("num_members", 0),
                    "topic": channel.get("topic", {}).get("value"),
                    "purpose": channel.get("purpose", {}).get("value")
                }
            })

        return {"resources": resources}

    elif provider == "notion":
        from integrations.core.notion_client import get_notion_client

        auth_token = token_manager.decrypt(integration["credentials_encrypted"])

        try:
            notion_client = get_notion_client()
            pages = await notion_client.search(access_token=auth_token, query="", page_size=100)
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

        new_landscape["selected_sources"] = valid_sources

        client.table("platform_connections").update({
            "landscape": new_landscape,
            "landscape_discovered_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", integration["id"]).execute()

        logger.info(
            f"[LANDSCAPE] Refreshed {provider} for user {user_id[:8]}: "
            f"{len(new_landscape['resources'])} resources, "
            f"{len(valid_sources)} selected"
        )
        return True

    except Exception as e:
        logger.warning(f"[LANDSCAPE] Refresh failed for {provider} user {user_id[:8]}: {e}")
        return False
