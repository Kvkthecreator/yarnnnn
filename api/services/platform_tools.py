"""
Platform Tools for Thinking Partner

ADR-050: Tool definitions and handlers for platform operations.
These tools are dynamically added to TP based on user's connected integrations.
Tool calls are routed to the MCP Gateway (Slack, Notion) or Direct API (Gmail, Calendar).
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
        "version": "2026-02-12",
        "adr_refs": ["ADR-046", "ADR-050"],
        "changelog": "Added Gmail/Calendar direct API tools, fixed Notion MCP tool names",
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
        "version": "2026-02-12",
        "adr_refs": ["ADR-046", "ADR-050"],
        "changelog": "Added list_events, get_event, create_event tools via Direct API, added designated_calendar_id pattern",
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
        "description": """Send an email.

PRIMARY USE: Send to user's own email so they own the output.
1. Call list_integrations to get user_email
2. Use that email as the recipient

IMPORTANT: Prefer create_draft over send. Only send directly if user explicitly asks.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient email. Get from list_integrations user_email for self"
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
            "required": ["to", "subject", "body"]
        }
    },
    {
        "name": "platform_gmail_create_draft",
        "description": """Create an email draft for user review. PREFERRED for deliverables.

PRIMARY USE: Draft to user's own email so they own the output.
1. Call list_integrations to get user_email
2. Use that email as the recipient (default to self)

User can then edit/forward the draft as needed.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient email. Get from list_integrations user_email for self"
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
            "required": ["to", "subject", "body"]
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
]

# All platform tools by provider
PLATFORM_TOOLS_BY_PROVIDER = {
    "slack": SLACK_TOOLS,
    "notion": NOTION_TOOLS,
    "gmail": GMAIL_TOOLS,
    "google": GMAIL_TOOLS + CALENDAR_TOOLS,  # Google integration has both
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
    Handle a platform tool call by routing to appropriate backend.

    - Slack, Notion: Route to MCP Gateway
    - Gmail, Calendar (Google): Route to Direct API

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

    # ADR-046: Route Gmail/Calendar to Direct API, others to MCP Gateway
    if provider in ("gmail", "calendar"):
        return await _handle_google_tool(auth, provider, tool, tool_input)
    else:
        return await _handle_mcp_tool(auth, provider, tool, tool_input)


async def _handle_mcp_tool(auth: Any, provider: str, tool: str, tool_input: dict) -> dict:
    """Handle MCP Gateway-routed tools (Slack, Notion)."""
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


async def _handle_google_tool(auth: Any, provider: str, tool: str, tool_input: dict) -> dict:
    """
    ADR-046: Handle Google tools (Gmail, Calendar) via Direct API.

    Uses GoogleAPIClient - NOT MCP. The distinction matters:
    - MCP Gateway (Node.js): Slack, Notion
    - Google API Client (Python): Gmail, Calendar
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
            result = auth.client.table("user_integrations").select(
                "access_token_encrypted, refresh_token_encrypted, metadata"
            ).eq("user_id", auth.user_id).eq("provider", p).eq("status", "active").execute()

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

    try:
        # Route to appropriate handler
        if provider == "gmail":
            return await _execute_gmail_tool(
                google_client, tool, tool_input,
                client_id, client_secret, refresh_token
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
    refresh_token: str
) -> dict:
    """Execute Gmail-specific tools via GoogleAPIClient (NOT MCP)."""

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
        result = await google_client.send_gmail_message(
            to=args["to"],
            subject=args["subject"],
            body=args["body"],
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            cc=args.get("cc"),
            thread_id=args.get("thread_id"),
        )

        return {
            "success": result.status.value == "success",
            "message_id": result.external_id,
            "error": result.error_message,
        }

    elif tool == "create_draft":
        result = await google_client.create_gmail_draft(
            to=args["to"],
            subject=args["subject"],
            body=args["body"],
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            cc=args.get("cc"),
        )

        return {
            "success": result.status.value == "success",
            "draft_id": result.external_id,
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

        else:
            return {"success": False, "error": f"Unknown Calendar tool: {tool}"}

    except Exception as e:
        logger.error(f"[PLATFORM-TOOLS] Calendar API error: {e}")
        return {"success": False, "error": str(e)}


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
            # Official Notion MCP server: notion-search
            return "notion-search", {
                "query": args.get("query"),
            }
        elif tool == "create_comment":
            # Official Notion MCP server: notion-create-comment
            return "notion-create-comment", {
                "page_id": args.get("page_id"),
                "markdown": args.get("content"),
            }

    # Default: pass through
    return tool, args


def is_platform_tool(tool_name: str) -> bool:
    """Check if a tool name is a platform tool."""
    return tool_name.startswith("platform_")
