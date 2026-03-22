"""
Platform Tools for Thinking Partner

ADR-076: Tool definitions and handlers for platform operations.
These tools are dynamically added to TP based on user's connected integrations.
All platforms use Direct API: SlackAPIClient, NotionAPIClient.

ADR-131: Gmail and Calendar sunset — only Slack and Notion remain.
"""

import logging
from typing import Any

from integrations.core.tokens import get_token_manager

logger = logging.getLogger(__name__)


# =============================================================================
# Prompt Versioning
# =============================================================================

PROMPT_VERSIONS = {
    "platform_tools": {
        "version": "2026-03-22",
        "adr_refs": ["ADR-050", "ADR-131"],
        "changelog": "ADR-131: Gmail and Calendar sunset — only Slack and Notion remain",
    },
    "slack": {
        "version": "2026-02-12",
        "adr_refs": ["ADR-050"],
        "changelog": "Streamlined for personal DM pattern (send to authed_user_id)",
    },
    "notion": {
        "version": "2026-02-12",
        "adr_refs": ["ADR-050"],
        "changelog": "Fixed MCP tool names for v2 server, added designated_page_id pattern",
    },
}


def get_prompt_version(component: str) -> dict:
    """Get version info for a platform tool component."""
    return PROMPT_VERSIONS.get(component, {})


def get_all_prompt_versions() -> dict:
    """Get all prompt version metadata."""
    return PROMPT_VERSIONS.copy()


# =============================================================================
# Tool Definitions (Anthropic format)
# =============================================================================

SLACK_TOOLS = [
    {
        "name": "platform_slack_send_message",
        "description": """Send a message to a Slack DM (direct message to self).

PRIMARY USE: Send to user's own DM so they own the output.
1. Call list_integrations to get authed_user_id
2. Use that user ID as channel_id

The user's authed_user_id is in integration metadata. Always send to self unless explicitly asked for a channel.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "channel_id": {
                    "type": "string",
                    "description": "User ID for DM (U...). Get from list_integrations authed_user_id"
                },
                "text": {
                    "type": "string",
                    "description": "Message text"
                }
            },
            "required": ["channel_id", "text"]
        }
    },
    {
        "name": "platform_slack_list_channels",
        "description": """List channels in the Slack workspace. Returns channel IDs and names.

Use to find a channel_id before calling platform_slack_get_channel_history.

After getting the list:
- If the user's channel name matches exactly → call get_channel_history immediately
- If no exact match → show the channel list to the user and ask which one they meant. Do NOT fall back to Search.
- If warning="channel_names_unavailable" → ask briefly for the channel link (one question, no tutorial)""",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "platform_slack_get_channel_history",
        "description": """Get recent message history from a Slack channel.

USE THIS to read what was discussed in a channel — this is the primary way to get Slack message content.

Workflow:
1. platform_slack_list_channels() → find the channel_id matching the channel name the user gave
2. platform_slack_get_channel_history(channel_id="C...", limit=50) → get messages

Do NOT fall back to Search at any point — Search only queries old cached content, not live messages. If the channel isn't found in list_channels, ask the user which channel they meant.

For "last 7 days", use oldest = Unix timestamp of 7 days ago (e.g., str(int(time.time()) - 7*86400)).

Parameters:
- channel_id: Channel ID (C...) — get from platform_slack_list_channels
- limit: Number of messages to retrieve (default 50, max 200)
- oldest: Unix timestamp string — filter messages after this time (optional, for date ranges)""",
        "input_schema": {
            "type": "object",
            "properties": {
                "channel_id": {
                    "type": "string",
                    "description": "Channel ID (C...). Get from platform_slack_list_channels."
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of messages to retrieve. Default: 50, max: 200."
                },
                "oldest": {
                    "type": "string",
                    "description": "Unix timestamp string. Only return messages after this time."
                }
            },
            "required": ["channel_id"]
        }
    },
]

NOTION_TOOLS = [
    {
        "name": "platform_notion_search",
        "description": "Search for pages in the Notion workspace. Returns page IDs for use with other tools.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "platform_notion_get_page",
        "description": """Read the content of a Notion page by ID.

Use AFTER platform_notion_search to read the actual content of a page.

Workflow:
1. platform_notion_search(query="...") → find the page, get its id
2. platform_notion_get_page(page_id="<id from search>") → read the content

Returns the page title and its text content as plain text blocks. Do NOT use Read or create_comment to probe page content — use this tool.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {
                    "type": "string",
                    "description": "Page ID (UUID). Get from platform_notion_search results."
                }
            },
            "required": ["page_id"]
        }
    },
    {
        "name": "platform_notion_create_comment",
        "description": """Add a comment to a Notion page.

PRIMARY USE: Add to user's designated page so they own the output.
1. Call list_integrations to get designated_page_id
2. Use that page ID as the target

The user's designated_page_id is in integration metadata. Use it unless user explicitly asks for a different page.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {
                    "type": "string",
                    "description": "Page ID (UUID). Get from list_integrations designated_page_id or search"
                },
                "content": {
                    "type": "string",
                    "description": "Comment text"
                }
            },
            "required": ["page_id", "content"]
        }
    },
]

# ADR-131: Gmail and Calendar tools removed (sunset)

# All platform tools by provider
PLATFORM_TOOLS_BY_PROVIDER = {
    "slack": SLACK_TOOLS,
    "notion": NOTION_TOOLS,
}


# =============================================================================
# Dynamic Tool Loading
# =============================================================================

async def get_platform_tools_for_user(auth: Any) -> list[dict]:
    """
    Get platform tools for a user based on their connected integrations.

    Args:
        auth: Auth context with user_id and client

    Returns:
        List of tool definitions for connected platforms
    """
    tools = []
    seen_names: set[str] = set()  # Dedupe by tool name

    try:
        # Get user's active integrations
        result = auth.client.table("platform_connections").select(
            "platform, status"
        ).eq("user_id", auth.user_id).eq("status", "active").execute()

        connected_providers = [i["platform"] for i in (result.data or [])]

        for provider in connected_providers:
            provider_tools = PLATFORM_TOOLS_BY_PROVIDER.get(provider, [])
            for tool in provider_tools:
                tool_name = tool.get("name")
                if tool_name and tool_name not in seen_names:
                    tools.append(tool)
                    seen_names.add(tool_name)

        logger.info(f"[PLATFORM-TOOLS] User has {len(tools)} platform tools from {connected_providers}")

    except Exception as e:
        logger.error(f"[PLATFORM-TOOLS] Error loading tools: {e}")

    return tools


# =============================================================================
# Tool Handlers
# =============================================================================

async def handle_platform_tool(auth: Any, tool_name: str, tool_input: dict) -> dict:
    """
    Handle a platform tool call by routing to appropriate backend.

    ADR-076 Routing (all Direct API), ADR-131 (Gmail/Calendar sunset):
    - Slack: Direct API (SlackAPIClient)
    - Notion: Direct API (NotionAPIClient)

    Args:
        auth: Auth context
        tool_name: Tool name (e.g., platform_slack_send_message)
        tool_input: Tool arguments

    Returns:
        Tool result dict
    """
    # Parse tool name: platform_{provider}_{tool}
    parts = tool_name.split("_", 2)
    if len(parts) < 3 or parts[0] != "platform":
        return {
            "success": False,
            "error": f"Invalid platform tool name: {tool_name}",
        }

    provider = parts[1]
    tool = "_".join(parts[2:])  # Handle multi-part tool names

    # ADR-076: All platforms use Direct API
    # ADR-131: Only Slack and Notion remain
    if provider == "slack":
        return await _handle_slack_tool(auth, tool, tool_input)
    elif provider == "notion":
        return await _handle_notion_tool(auth, tool, tool_input)
    else:
        return {"success": False, "error": f"Unknown provider: {provider}"}


async def _handle_slack_tool(auth: Any, tool: str, tool_input: dict) -> dict:
    """Handle Slack tools via Direct API (ADR-076, replaces MCP Gateway)."""
    from integrations.core.slack_client import get_slack_client

    # Get user's integration credentials
    try:
        integration = auth.client.table("platform_connections").select(
            "credentials_encrypted, metadata"
        ).eq("user_id", auth.user_id).eq("platform", "slack").eq("status", "active").single().execute()

        if not integration.data:
            return {
                "success": False,
                "error": "No active Slack integration. Connect it in Settings.",
            }

        token_manager = get_token_manager()
        bot_token = token_manager.decrypt(integration.data["credentials_encrypted"])

    except Exception as e:
        logger.error(f"[PLATFORM-TOOLS] Failed to get Slack credentials: {e}")
        return {
            "success": False,
            "error": "Failed to get Slack credentials",
        }

    slack_client = get_slack_client()

    if tool == "send_message":
        result = await slack_client.post_message(
            bot_token=bot_token,
            channel_id=tool_input["channel_id"],
            text=tool_input["text"],
        )
        if result.get("ok"):
            return {
                "success": True,
                "result": {"ts": result.get("ts"), "channel": result.get("channel")},
            }
        return {"success": False, "error": result.get("error", "Slack API error")}

    elif tool == "list_channels":
        channels = await slack_client.list_channels(bot_token=bot_token)
        result_dict: dict = {
            "success": True,
            "result": {"channels": channels, "count": len(channels)},
        }
        # Detect missing names (token scope issue)
        if channels and all(not ch.get("name") for ch in channels):
            result_dict["warning"] = "channel_names_unavailable"
            result_dict["hint"] = (
                "Channel names unavailable — Slack token may lack channels:read scope. "
                "Ask the user for the channel link."
            )
        return result_dict

    elif tool == "get_channel_history":
        messages = await slack_client.get_channel_history(
            bot_token=bot_token,
            channel_id=tool_input["channel_id"],
            limit=tool_input.get("limit", 50),
            oldest=tool_input.get("oldest"),
        )
        # Normalize for TP readability
        normalized = []
        for msg in messages:
            text = msg.get("text", "")
            if not text:
                continue
            entry: dict = {
                "user": msg.get("user") or msg.get("username"),
                "text": text,
                "ts": msg.get("ts"),
            }
            reactions = msg.get("reactions")
            if reactions:
                entry["reactions"] = [
                    {"name": r.get("name"), "count": r.get("count", 0)}
                    for r in reactions
                    if isinstance(r, dict)
                ]
            normalized.append(entry)
        return {"success": True, "result": {"messages": normalized, "count": len(normalized)}}

    return {"success": False, "error": f"Unknown Slack tool: {tool}"}




def _extract_rich_text(rich_text_arr: list) -> str:
    """Extract plain text from a Notion rich_text array."""
    return "".join(part.get("plain_text", "") for part in rich_text_arr if isinstance(part, dict))


def _normalize_notion_blocks(blocks: list) -> list[dict]:
    """
    Convert Notion block objects to simple {type, text} dicts for TP readability.

    Notion blocks have deeply nested rich_text arrays inside type-specific sub-dicts.
    This normalizes to plain text so TP doesn't see raw API noise.
    """
    normalized = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_type = block.get("type")
        if not block_type:
            continue

        # Most block types have rich_text inside a type-keyed sub-dict
        type_data = block.get(block_type, {})
        rich_text = type_data.get("rich_text", [])
        text = _extract_rich_text(rich_text)

        # Special handling for specific types
        if block_type == "child_page":
            text = type_data.get("title", "")
        elif block_type == "image":
            img = type_data.get("external") or type_data.get("file") or {}
            text = img.get("url", "[image]")
        elif block_type == "divider":
            text = "---"
        elif block_type == "equation":
            text = type_data.get("expression", "")
        elif block_type == "to_do":
            checked = type_data.get("checked", False)
            prefix = "[x]" if checked else "[ ]"
            text = f"{prefix} {text}"
        elif block_type == "code":
            lang = type_data.get("language", "")
            text = f"```{lang}\n{text}\n```"

        if text or block_type in ("divider",):
            normalized.append({"type": block_type, "text": text})

    return normalized


async def _handle_notion_tool(auth: Any, tool: str, tool_input: dict) -> dict:
    """
    ADR-050: Handle Notion tools via Direct API.

    Why Direct API instead of MCP?
    1. @notionhq/notion-mcp-server requires internal tokens (ntn_...), not OAuth
    2. mcp.notion.com manages its own OAuth sessions, incompatible with pass-through
    3. Direct API works perfectly with our OAuth access tokens
    """
    from integrations.core.notion_client import get_notion_client
    from integrations.core.tokens import get_token_manager

    # Get user's Notion integration
    try:
        result = auth.client.table("platform_connections").select(
            "credentials_encrypted, metadata"
        ).eq("user_id", auth.user_id).eq("platform", "notion").eq("status", "active").single().execute()

        if not result.data:
            return {
                "success": False,
                "error": "No active Notion integration. Connect it in Settings.",
            }

        # Decrypt access token
        token_manager = get_token_manager()
        access_token = token_manager.decrypt(result.data["credentials_encrypted"])
        metadata = result.data.get("metadata") or {}

    except Exception as e:
        logger.error(f"[PLATFORM-TOOLS] Failed to get Notion credentials: {e}")
        return {
            "success": False,
            "error": "Failed to get Notion credentials",
        }

    # Get Notion API client
    notion_client = get_notion_client()

    try:
        return await _execute_notion_tool(notion_client, tool, tool_input, access_token, metadata)
    except Exception as e:
        logger.error(f"[PLATFORM-TOOLS] Notion API error: {e}")
        return {
            "success": False,
            "error": f"Notion API error: {str(e)}",
        }


async def _execute_notion_tool(
    notion_client,
    tool: str,
    args: dict,
    access_token: str,
    metadata: dict
) -> dict:
    """Execute Notion-specific tools via NotionAPIClient (NOT MCP)."""

    if tool == "search":
        results = await notion_client.search(
            access_token=access_token,
            query=args.get("query", ""),
            page_size=10,
        )

        # Format results for readability
        formatted = []
        for item in results:
            obj_type = item.get("object")
            title = ""

            # Extract title based on object type
            if obj_type == "page":
                props = item.get("properties", {})
                title_prop = props.get("title") or props.get("Name") or {}
                if "title" in title_prop:
                    title_arr = title_prop["title"]
                    if title_arr:
                        title = title_arr[0].get("plain_text", "Untitled")
            elif obj_type == "database":
                title_arr = item.get("title", [])
                if title_arr:
                    title = title_arr[0].get("plain_text", "Untitled Database")

            formatted.append({
                "id": item.get("id"),
                "type": obj_type,
                "title": title or "Untitled",
                "url": item.get("url"),
            })

        return {
            "success": True,
            "results": formatted,
            "count": len(results),
        }

    elif tool == "get_page":
        page_id = args.get("page_id")
        if not page_id:
            return {"success": False, "error": "page_id is required"}

        # Get page metadata (title, properties)
        page_meta = await notion_client.get_page(
            access_token=access_token,
            page_id=page_id,
        )

        # Extract title from page properties
        title = "Untitled"
        props = page_meta.get("properties", {})
        title_prop = props.get("title") or props.get("Name") or {}
        title_arr = title_prop.get("title", [])
        if title_arr:
            title = _extract_rich_text(title_arr) or "Untitled"

        # Get page content (blocks)
        blocks = await notion_client.get_page_content(
            access_token=access_token,
            page_id=page_id,
            page_size=100,
        )

        normalized_blocks = _normalize_notion_blocks(blocks)
        logger.info(f"[PLATFORM-TOOLS] notion get_page: {len(normalized_blocks)} blocks from page {page_id}")

        return {
            "success": True,
            "page_id": page_id,
            "title": title,
            "url": page_meta.get("url"),
            "blocks": normalized_blocks,
            "block_count": len(normalized_blocks),
        }

    elif tool == "create_comment":
        page_id = args.get("page_id")
        content = args.get("content")

        if not page_id:
            # Try to use designated page from metadata
            page_id = metadata.get("designated_page_id")
            if not page_id:
                return {
                    "success": False,
                    "error": "No page_id provided and no designated page set",
                }

        result = await notion_client.create_comment(
            access_token=access_token,
            page_id=page_id,
            content=content,
        )

        return {
            "success": True,
            "comment_id": result.get("id"),
            "page_id": page_id,
            "message": "Comment added to Notion page",
        }

    else:
        return {"success": False, "error": f"Unknown Notion tool: {tool}"}



# ADR-131: _handle_google_tool, _execute_gmail_tool, _execute_calendar_tool deleted (sunset)




def is_platform_tool(tool_name: str) -> bool:
    """Check if a tool name is a platform tool."""
    return tool_name.startswith("platform_")
