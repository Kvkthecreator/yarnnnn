"""
Platform Tools for Thinking Partner

ADR-050: Tool definitions and handlers for platform operations.
These tools are dynamically added to TP based on user's connected integrations.
Tool calls are routed to MCP Gateway (Slack) or Direct API (Notion, Gmail, Calendar).
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
        "version": "2026-02-19",
        "adr_refs": ["ADR-046", "ADR-050"],
        "changelog": "Added calendar update_event and delete_event tools; full CRUD complete",
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
    "gmail": {
        "version": "2026-02-12",
        "adr_refs": ["ADR-046"],
        "changelog": "Added search, get_thread, send, create_draft tools via Direct API",
    },
    "calendar": {
        "version": "2026-02-19",
        "adr_refs": ["ADR-046", "ADR-050"],
        "changelog": "Added update_event and delete_event tools; full CRUD now complete. TP handles scheduling intelligence (conflict detection, free-slot reasoning) in-context.",
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

# ADR-046: Gmail tools (Direct API, not MCP Gateway)
GMAIL_TOOLS = [
    {
        "name": "platform_gmail_search",
        "description": """Search Gmail messages. Returns message summaries with IDs.

Use Gmail query syntax:
- "from:sarah@company.com" - Messages from specific sender
- "subject:quarterly report" - Subject contains text
- "is:unread" - Unread messages
- "after:2024/01/01" - Messages after date
- Combine with spaces: "from:boss@company.com is:unread"
""",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Gmail search query"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum messages to return (default: 10, max: 50)",
                    "default": 10
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "platform_gmail_get_thread",
        "description": "Get a full email thread (conversation). Use after searching to get complete context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "thread_id": {
                    "type": "string",
                    "description": "Thread ID from search results"
                }
            },
            "required": ["thread_id"]
        }
    },
    {
        "name": "platform_gmail_send",
        "description": """Send an email. Prefer create_draft unless user explicitly asks to send.

Defaults to user's own email if 'to' is omitted.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient email (optional - defaults to user's own email)"
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject"
                },
                "body": {
                    "type": "string",
                    "description": "Email body (plain text)"
                },
                "cc": {
                    "type": "string",
                    "description": "CC recipients (optional, comma-separated)"
                },
                "thread_id": {
                    "type": "string",
                    "description": "Thread ID to reply to (optional)"
                }
            },
            "required": ["subject", "body"]
        }
    },
    {
        "name": "platform_gmail_create_draft",
        "description": """Create an email draft for user review. PREFERRED for deliverables.

Defaults to user's own email if 'to' is omitted. User can then edit/forward the draft.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient email (optional - defaults to user's own email)"
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject"
                },
                "body": {
                    "type": "string",
                    "description": "Email body (plain text)"
                },
                "cc": {
                    "type": "string",
                    "description": "CC recipients (optional, comma-separated)"
                }
            },
            "required": ["subject", "body"]
        }
    },
]

# ADR-046: Calendar tools (Direct API, not MCP Gateway)
CALENDAR_TOOLS = [
    {
        "name": "platform_calendar_list_events",
        "description": """List upcoming calendar events.

Time filters use relative format:
- "now" - Current time
- "+2h" - 2 hours from now
- "+7d" - 7 days from now

Uses designated_calendar_id if set, otherwise 'primary'.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "time_min": {
                    "type": "string",
                    "description": "Start time (default: 'now'). Use 'now' or relative like '+2h'"
                },
                "time_max": {
                    "type": "string",
                    "description": "End time (default: '+7d'). Use relative like '+24h', '+7d'"
                },
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID. Get from list_integrations designated_calendar_id, or use 'primary'"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum events to return (default: 25, max: 100)",
                    "default": 25
                }
            },
            "required": []
        }
    },
    {
        "name": "platform_calendar_get_event",
        "description": "Get details of a specific calendar event including attendees and description.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "Event ID"
                },
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID. Get from list_integrations designated_calendar_id, or use 'primary'"
                }
            },
            "required": ["event_id"]
        }
    },
    {
        "name": "platform_calendar_create_event",
        "description": """Create a new calendar event.

PRIMARY USE: Create on user's designated calendar so they own the output.
1. Call list_integrations to get designated_calendar_id
2. Use that calendar ID as the target

Uses designated_calendar_id if set, otherwise 'primary'.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Event title"
                },
                "start_time": {
                    "type": "string",
                    "description": "Start time in ISO format (e.g., '2024-01-15T10:00:00')"
                },
                "end_time": {
                    "type": "string",
                    "description": "End time in ISO format"
                },
                "description": {
                    "type": "string",
                    "description": "Event description (optional)"
                },
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of attendee email addresses (optional)"
                },
                "location": {
                    "type": "string",
                    "description": "Event location (optional)"
                },
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID. Get from list_integrations designated_calendar_id, or use 'primary'"
                }
            },
            "required": ["summary", "start_time", "end_time"]
        }
    },
    {
        "name": "platform_calendar_update_event",
        "description": """Update an existing calendar event (partial update — only provided fields change).

Workflow:
1. platform_calendar_list_events() → find the event by title/time
2. platform_calendar_get_event(event_id="...") → confirm it's the right event with the user
3. Confirm what changes will be made before calling this tool
4. platform_calendar_update_event(event_id="...", <only changed fields>) → apply changes

IMPORTANT: Only pass fields that are actually changing. Omitted fields keep their current values.
Do NOT guess event_id — always get it from list_events → get_event workflow first.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "Event ID. Get from platform_calendar_list_events."
                },
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID. Get from list_integrations designated_calendar_id, or use 'primary'"
                },
                "summary": {
                    "type": "string",
                    "description": "New event title (optional — omit to keep current)"
                },
                "start_time": {
                    "type": "string",
                    "description": "New start time in ISO format (optional — omit to keep current)"
                },
                "end_time": {
                    "type": "string",
                    "description": "New end time in ISO format (optional — omit to keep current)"
                },
                "description": {
                    "type": "string",
                    "description": "New event description (optional — omit to keep current)"
                },
                "location": {
                    "type": "string",
                    "description": "New location (optional — omit to keep current)"
                },
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Replacement attendee list — email addresses (optional — omit to keep current)"
                }
            },
            "required": ["event_id"]
        }
    },
    {
        "name": "platform_calendar_delete_event",
        "description": """Delete (cancel) a calendar event. This is permanent.

Workflow:
1. platform_calendar_list_events() → find the event by title/time
2. platform_calendar_get_event(event_id="...") → confirm with the user it's the right event
3. Get explicit user confirmation before deleting
4. platform_calendar_delete_event(event_id="...") → delete it

NEVER delete without confirming the exact event with the user first.
Do NOT guess event_id — always get it from list_events → get_event workflow.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "Event ID. Get from platform_calendar_list_events."
                },
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID. Get from list_integrations designated_calendar_id, or use 'primary'"
                }
            },
            "required": ["event_id"]
        }
    },
]

# All platform tools by provider
# Note: gmail and google are separate DB providers but overlap in tools.
# Use CALENDAR_TOOLS only for google since gmail already provides GMAIL_TOOLS.
# The get_platform_tools_for_user function deduplicates by tool name.
PLATFORM_TOOLS_BY_PROVIDER = {
    "slack": SLACK_TOOLS,
    "notion": NOTION_TOOLS,
    "gmail": GMAIL_TOOLS,
    "google": CALENDAR_TOOLS,  # Only calendar; gmail tools come from gmail provider
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

    ADR-050 Routing:
    - Slack: MCP Gateway (local stdio transport)
    - Notion: Direct API (MCP incompatible with OAuth tokens)
    - Gmail: Direct API
    - Calendar: Direct API

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

    # ADR-050: Route by provider
    # - Slack: MCP Gateway (only platform that works with MCP + OAuth)
    # - Everything else: Direct API
    if provider == "slack":
        return await _handle_mcp_tool(auth, provider, tool, tool_input)
    elif provider == "notion":
        return await _handle_notion_tool(auth, tool, tool_input)
    elif provider in ("gmail", "calendar"):
        return await _handle_google_tool(auth, provider, tool, tool_input)
    else:
        return {"success": False, "error": f"Unknown provider: {provider}"}


async def _handle_mcp_tool(auth: Any, provider: str, tool: str, tool_input: dict) -> dict:
    """Handle MCP Gateway-routed tools (Slack only)."""
    from services.mcp_gateway import call_platform_tool, is_gateway_available

    # Check if gateway is available
    if not is_gateway_available():
        return {
            "success": False,
            "error": "MCP Gateway not configured. Set MCP_GATEWAY_URL environment variable.",
            "hint": "Platform tools require the MCP Gateway service to be running.",
        }

    # Get user's integration credentials
    try:
        integration = auth.client.table("platform_connections").select(
            "credentials_encrypted, metadata"
        ).eq("user_id", auth.user_id).eq("platform", provider).eq("status", "active").single().execute()

        if not integration.data:
            return {
                "success": False,
                "error": f"No active {provider} integration. Connect it in Settings.",
            }

        # Decrypt token
        token_manager = get_token_manager()
        token = token_manager.decrypt(integration.data["credentials_encrypted"])
        metadata = integration.data.get("metadata") or {}

    except Exception as e:
        logger.error(f"[PLATFORM-TOOLS] Failed to get credentials: {e}")
        return {
            "success": False,
            "error": f"Failed to get {provider} credentials",
        }

    # Map tool input to MCP tool format
    mcp_tool, mcp_args = map_to_mcp_format(provider, tool, tool_input)

    # Call gateway
    result = await call_platform_tool(
        provider=provider,
        tool=mcp_tool,
        args=mcp_args,
        token=token,
        metadata=metadata,
    )

    # Normalize MCP results before TP sees them (strip raw API noise)
    if result.get("success"):
        if tool == "list_channels":
            result = _normalize_list_channels_result(result)
        elif tool == "get_channel_history":
            result = _normalize_get_channel_history_result(result)

    return result


def _normalize_list_channels_result(result: dict) -> dict:
    """
    Normalize list_channels result to only the fields TP needs.

    The Slack MCP server returns the raw conversations.list response — 20+ fields
    per channel including internal Slack metadata. This noise causes the model to
    misread the data (e.g. treating valid channel names as "redacted").

    Strip down to: id, name, is_private, is_archived.
    If names are missing (scope issue), add a warning signal.
    """
    raw = result.get("result")
    channels = None

    if isinstance(raw, list):
        channels = raw
    elif isinstance(raw, dict):
        channels = raw.get("channels")

    if not channels or not isinstance(channels, list):
        return result

    # Normalize: keep only the fields TP needs
    normalized = [
        {
            "id": ch.get("id"),
            "name": ch.get("name") or ch.get("name_normalized"),
            "is_private": ch.get("is_private", False),
            "is_archived": ch.get("is_archived", False),
        }
        for ch in channels
        if isinstance(ch, dict) and ch.get("id")
    ]

    result = dict(result)
    result["result"] = {"channels": normalized, "count": len(normalized)}

    # Detect missing names (token scope issue) — add warning signal
    names_missing = all(not ch["name"] for ch in normalized)
    if names_missing and len(normalized) > 0:
        result["warning"] = "channel_names_unavailable"
        result["hint"] = (
            "Channel names unavailable — Slack token may lack channels:read or groups:read scope. "
            "Ask the user for the channel link (right-click → Copy link in Slack)."
        )
        logger.warning("[PLATFORM-TOOLS] list_channels: channel names unavailable (scope issue)")
    else:
        logger.info(f"[PLATFORM-TOOLS] list_channels: normalized {len(normalized)} channels")

    return result


def _normalize_get_channel_history_result(result: dict) -> dict:
    """
    Normalize get_channel_history result to only the fields TP needs.

    The Slack MCP server returns the raw conversations.history response including
    ok, has_more, pin_count, response_metadata, and 15+ fields per message.
    Strip down to: text, user, ts, reactions (count only).
    """
    raw = result.get("result")
    messages = None

    if isinstance(raw, list):
        messages = raw
    elif isinstance(raw, dict):
        messages = raw.get("messages") or raw.get("history")

    if not messages or not isinstance(messages, list):
        return result

    normalized = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        text = msg.get("text", "")
        # Skip empty/bot messages with no text
        if not text:
            continue
        entry: dict = {
            "user": msg.get("user") or msg.get("username"),
            "text": text,
            "ts": msg.get("ts"),
        }
        # Include reactions as simple name counts if present
        reactions = msg.get("reactions")
        if reactions:
            entry["reactions"] = [
                {"name": r.get("name"), "count": r.get("count", 0)}
                for r in reactions
                if isinstance(r, dict)
            ]
        normalized.append(entry)

    result = dict(result)
    result["result"] = {"messages": normalized, "count": len(normalized)}
    logger.info(f"[PLATFORM-TOOLS] get_channel_history: normalized {len(normalized)} messages")

    return result


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


async def _handle_google_tool(auth: Any, provider: str, tool: str, tool_input: dict) -> dict:
    """
    ADR-046: Handle Google tools (Gmail, Calendar) via Direct API.

    Uses GoogleAPIClient - NOT MCP.
    """
    import os
    from integrations.core.google_client import get_google_client

    # Get Google OAuth credentials
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        return {
            "success": False,
            "error": "Google OAuth not configured",
        }

    # Get user's Google integration (try 'google' first, fall back to 'gmail')
    try:
        integration = None
        for p in ["google", "gmail"]:
            result = auth.client.table("platform_connections").select(
                "credentials_encrypted, refresh_token_encrypted, metadata"
            ).eq("user_id", auth.user_id).eq("platform", p).eq("status", "active").execute()

            if result.data:
                integration = result.data[0]
                break

        if not integration:
            return {
                "success": False,
                "error": "No active Google integration. Connect Gmail or Google in Settings.",
            }

        # Get refresh token
        token_manager = get_token_manager()
        refresh_token_encrypted = integration.get("refresh_token_encrypted")

        if not refresh_token_encrypted:
            return {
                "success": False,
                "error": "Missing Google refresh token. Please reconnect your Google account.",
            }

        refresh_token = token_manager.decrypt(refresh_token_encrypted)

    except Exception as e:
        logger.error(f"[PLATFORM-TOOLS] Failed to get Google credentials: {e}")
        return {
            "success": False,
            "error": "Failed to get Google credentials",
        }

    # Get Google API client (NOT MCP)
    google_client = get_google_client()

    # ADR-050: Get user_email from metadata for default landing zone
    metadata = integration.get("metadata") or {}
    user_email = metadata.get("email")

    # Debug logging to diagnose missing email
    if not user_email:
        logger.warning(f"[PLATFORM-TOOLS] No email in metadata for user {auth.user_id}. Metadata keys: {list(metadata.keys())}")

    try:
        # Route to appropriate handler
        if provider == "gmail":
            return await _execute_gmail_tool(
                google_client, tool, tool_input,
                client_id, client_secret, refresh_token,
                user_email=user_email  # Pass for default fallback
            )
        elif provider == "calendar":
            return await _execute_calendar_tool(
                google_client, tool, tool_input,
                client_id, client_secret, refresh_token
            )
        else:
            return {"success": False, "error": f"Unknown Google provider: {provider}"}

    except Exception as e:
        logger.error(f"[PLATFORM-TOOLS] Google API error: {e}")
        return {
            "success": False,
            "error": f"Google API error: {str(e)}",
        }


async def _execute_gmail_tool(
    google_client,
    tool: str,
    args: dict,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    user_email: str = None  # ADR-050: Default landing zone fallback
) -> dict:
    """Execute Gmail-specific tools via GoogleAPIClient (NOT MCP)."""

    # ADR-050: Auto-default 'to' field to user's email if not provided or placeholder
    if tool in ("send", "create_draft") and user_email:
        to_value = args.get("to", "")
        # Detect placeholder/missing values and fall back to user's email
        if not to_value or to_value in ("test@example.com", "example@example.com", "recipient@example.com"):
            args = {**args, "to": user_email}
            logger.info(f"[PLATFORM-TOOLS] Auto-defaulting 'to' to user's email: {user_email}")

    if tool == "search":
        messages = await google_client.list_gmail_messages(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            query=args.get("query"),
            max_results=min(args.get("max_results", 10), 50),
        )

        # Format results
        results = []
        for msg in messages[:20]:  # Cap display at 20
            results.append({
                "id": msg.get("id"),
                "thread_id": msg.get("threadId"),
                "snippet": msg.get("snippet", ""),
            })

        return {
            "success": True,
            "messages": results,
            "count": len(messages),
        }

    elif tool == "get_thread":
        thread = await google_client.get_gmail_thread(
            thread_id=args["thread_id"],
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
        )

        # Format thread messages
        formatted_messages = []
        for msg in thread.get("messages", []):
            headers = {}
            for h in msg.get("payload", {}).get("headers", []):
                headers[h["name"]] = h["value"]

            formatted_messages.append({
                "id": msg.get("id"),
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "snippet": msg.get("snippet", ""),
            })

        return {
            "success": True,
            "thread_id": thread.get("id"),
            "messages": formatted_messages,
        }

    elif tool == "send":
        # Get the actual 'to' address (may have been auto-defaulted)
        to_address = args.get("to", user_email) or user_email

        result = await google_client.send_gmail_message(
            to=to_address,
            subject=args["subject"],
            body=args["body"],
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            cc=args.get("cc"),
            thread_id=args.get("thread_id"),
        )

        if result.status.value == "success":
            return {
                "success": True,
                "message": f"Email sent to {to_address}",
                "to": to_address,
                "subject": args["subject"],
            }
        else:
            return {
                "success": False,
                "error": result.error_message,
            }

    elif tool == "create_draft":
        # Get the actual 'to' address (may have been auto-defaulted)
        to_address = args.get("to") or user_email

        # Warn if no recipient but still create draft (Gmail allows this)
        if not to_address:
            logger.warning(f"[PLATFORM-TOOLS] Creating draft without 'to' address. User may need to reconnect Google.")

        result = await google_client.create_gmail_draft(
            to=to_address,
            subject=args["subject"],
            body=args["body"],
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            cc=args.get("cc"),
        )

        if result.status.value == "success":
            # Clear message about where draft went
            if to_address:
                msg = f"Draft created to {to_address} - check your Gmail drafts folder"
            else:
                msg = "Draft created (no recipient set) - check your Gmail drafts folder and add a recipient"
            return {
                "success": True,
                "message": msg,
                "to": to_address,
                "subject": args["subject"],
            }
        else:
            return {
                "success": False,
                "error": result.error_message,
            }

    else:
        return {"success": False, "error": f"Unknown Gmail tool: {tool}"}


async def _execute_calendar_tool(
    google_client,
    tool: str,
    args: dict,
    client_id: str,
    client_secret: str,
    refresh_token: str
) -> dict:
    """Execute Calendar-specific tools via GoogleAPIClient (NOT MCP)."""

    try:
        if tool == "list_events":
            events = await google_client.list_calendar_events(
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
                calendar_id=args.get("calendar_id", "primary"),
                time_min=args.get("time_min"),
                time_max=args.get("time_max"),
                max_results=args.get("max_results", 25),
            )

            # Format events
            formatted = []
            for e in events:
                start = e.get("start", {})
                formatted.append({
                    "id": e.get("id"),
                    "summary": e.get("summary", "Untitled"),
                    "start": start.get("dateTime") or start.get("date"),
                    "end": e.get("end", {}).get("dateTime") or e.get("end", {}).get("date"),
                    "location": e.get("location"),
                    "attendees": len(e.get("attendees", [])),
                })

            return {
                "success": True,
                "events": formatted,
                "count": len(events),
            }

        elif tool == "get_event":
            event = await google_client.get_calendar_event(
                event_id=args["event_id"],
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
                calendar_id=args.get("calendar_id", "primary"),
            )

            return {
                "success": True,
                "event": {
                    "id": event.get("id"),
                    "summary": event.get("summary"),
                    "description": event.get("description"),
                    "start": event.get("start"),
                    "end": event.get("end"),
                    "location": event.get("location"),
                    "attendees": [
                        {
                            "email": a.get("email"),
                            "name": a.get("displayName"),
                            "response": a.get("responseStatus"),
                        }
                        for a in event.get("attendees", [])
                    ],
                    "hangout_link": event.get("hangoutLink"),
                },
            }

        elif tool == "create_event":
            created = await google_client.create_calendar_event(
                summary=args["summary"],
                start_time=args["start_time"],
                end_time=args["end_time"],
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
                calendar_id=args.get("calendar_id", "primary"),
                description=args.get("description"),
                location=args.get("location"),
                attendees=args.get("attendees"),
            )

            return {
                "success": True,
                "event_id": created.get("id"),
                "html_link": created.get("htmlLink"),
            }

        elif tool == "update_event":
            if not args.get("event_id"):
                return {"success": False, "error": "event_id is required"}

            updated = await google_client.update_calendar_event(
                event_id=args["event_id"],
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
                calendar_id=args.get("calendar_id", "primary"),
                summary=args.get("summary"),
                start_time=args.get("start_time"),
                end_time=args.get("end_time"),
                description=args.get("description"),
                location=args.get("location"),
                attendees=args.get("attendees"),
            )

            return {
                "success": True,
                "event_id": updated.get("id"),
                "summary": updated.get("summary"),
                "html_link": updated.get("htmlLink"),
                "message": f"Event updated: {updated.get('summary', args['event_id'])}",
            }

        elif tool == "delete_event":
            if not args.get("event_id"):
                return {"success": False, "error": "event_id is required"}

            await google_client.delete_calendar_event(
                event_id=args["event_id"],
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
                calendar_id=args.get("calendar_id", "primary"),
            )

            return {
                "success": True,
                "event_id": args["event_id"],
                "message": "Event deleted from calendar.",
            }

        else:
            return {"success": False, "error": f"Unknown Calendar tool: {tool}"}

    except Exception as e:
        logger.error(f"[PLATFORM-TOOLS] Calendar API error: {e}")
        return {"success": False, "error": str(e)}


def map_to_mcp_format(provider: str, tool: str, args: dict) -> tuple[str, dict]:
    """
    Map our tool names/args to MCP server expected format.

    Only used for Slack (the only MCP-routed platform).
    Notion uses Direct API now (ADR-050).

    Slack MCP server tool names (@modelcontextprotocol/server-slack):
      slack_post_message, slack_list_channels, slack_get_channel_history,
      slack_get_users, slack_get_user_profile

    Returns:
        (mcp_tool_name, mcp_args)
    """
    if provider == "slack":
        if tool == "send_message":
            return "slack_post_message", {
                "channel_id": args.get("channel_id"),
                "text": args.get("text"),
            }
        elif tool == "list_channels":
            return "slack_list_channels", {}
        elif tool == "get_channel_history":
            mcp_args: dict = {"channel_id": args.get("channel_id")}
            if args.get("limit"):
                mcp_args["limit"] = args["limit"]
            if args.get("oldest"):
                mcp_args["oldest"] = args["oldest"]
            return "slack_get_channel_history", mcp_args

    # Default: pass through
    return tool, args


def is_platform_tool(tool_name: str) -> bool:
    """Check if a tool name is a platform tool."""
    return tool_name.startswith("platform_")
