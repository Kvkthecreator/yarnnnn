"""
Platform Tools for Thinking Partner

ADR-050: Tool definitions and handlers for platform operations.
These tools are dynamically added to TP based on user's connected integrations.
Tool calls are routed to the MCP Gateway.
"""

import logging
from typing import Any

from integrations.core.tokens import get_token_manager

logger = logging.getLogger(__name__)


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
        "description": "List channels in the Slack workspace. Only needed if user explicitly asks to post to a channel.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
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
        "name": "platform_notion_create_comment",
        "description": "Add a comment to a Notion page.",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {
                    "type": "string",
                    "description": "Page ID (UUID format)"
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

    try:
        # Get user's active integrations
        result = auth.client.table("user_integrations").select(
            "provider, status"
        ).eq("user_id", auth.user_id).eq("status", "active").execute()

        connected_providers = [i["provider"] for i in (result.data or [])]

        for provider in connected_providers:
            provider_tools = PLATFORM_TOOLS_BY_PROVIDER.get(provider, [])
            tools.extend(provider_tools)

        logger.info(f"[PLATFORM-TOOLS] User has {len(tools)} platform tools from {connected_providers}")

    except Exception as e:
        logger.error(f"[PLATFORM-TOOLS] Error loading tools: {e}")

    return tools


# =============================================================================
# Tool Handlers
# =============================================================================

async def handle_platform_tool(auth: Any, tool_name: str, tool_input: dict) -> dict:
    """
    Handle a platform tool call by routing to MCP Gateway.

    Args:
        auth: Auth context
        tool_name: Tool name (e.g., platform_slack_send_message)
        tool_input: Tool arguments

    Returns:
        Tool result dict
    """
    from services.mcp_gateway import call_platform_tool, is_gateway_available

    # Parse tool name: platform_{provider}_{tool}
    parts = tool_name.split("_", 2)
    if len(parts) < 3 or parts[0] != "platform":
        return {
            "success": False,
            "error": f"Invalid platform tool name: {tool_name}",
        }

    provider = parts[1]
    tool = "_".join(parts[2:])  # Handle multi-part tool names

    # Check if gateway is available
    if not is_gateway_available():
        return {
            "success": False,
            "error": "MCP Gateway not configured. Set MCP_GATEWAY_URL environment variable.",
            "hint": "Platform tools require the MCP Gateway service to be running.",
        }

    # Get user's integration credentials
    try:
        integration = auth.client.table("user_integrations").select(
            "access_token_encrypted, metadata"
        ).eq("user_id", auth.user_id).eq("provider", provider).eq("status", "active").single().execute()

        if not integration.data:
            return {
                "success": False,
                "error": f"No active {provider} integration. Connect it in Settings.",
            }

        # Decrypt token
        token_manager = get_token_manager()
        token = token_manager.decrypt(integration.data["access_token_encrypted"])
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

    return result


def map_to_mcp_format(provider: str, tool: str, args: dict) -> tuple[str, dict]:
    """
    Map our tool names/args to MCP server expected format.

    Returns:
        (mcp_tool_name, mcp_args)
    """
    if provider == "slack":
        if tool == "send_message":
            # Slack MCP server expects channel_id and text
            return "slack_post_message", {
                "channel_id": args.get("channel_id"),
                "text": args.get("text"),
            }
        elif tool == "list_channels":
            return "slack_list_channels", {}

    elif provider == "notion":
        if tool == "search":
            # Official Notion MCP server v2: search-notion (not notion-search)
            return "search-notion", {
                "query": args.get("query"),
            }
        elif tool == "create_comment":
            # Official Notion MCP server v2: create-a-comment
            return "create-a-comment", {
                "page_id": args.get("page_id"),
                "markdown": args.get("content"),
            }

    # Default: pass through
    return tool, args


def is_platform_tool(tool_name: str) -> bool:
    """Check if a tool name is a platform tool."""
    return tool_name.startswith("platform_")
