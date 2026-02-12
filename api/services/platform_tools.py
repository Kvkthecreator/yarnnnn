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
        "description": """Send an email. Use for deliverable outputs when user requests email delivery.

IMPORTANT: Always confirm recipient before sending. Prefer creating drafts unless explicitly asked to send.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient email address"
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
        "description": "Create an email draft for user review. PREFERRED over direct send for deliverables.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient email address"
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
""",
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
                    "description": "Calendar ID (default: 'primary')"
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
                    "description": "Calendar ID (default: 'primary')"
                }
            },
            "required": ["event_id"]
        }
    },
    {
        "name": "platform_calendar_create_event",
        "description": "Create a new calendar event.",
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
                    "description": "Calendar ID (default: 'primary')"
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

    Uses the existing implementations in integrations/core/client.py.
    """
    import os
    from integrations.core.client import MCPManager

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

    # Create MCP manager for API calls
    mcp_manager = MCPManager()

    try:
        # Route to appropriate handler
        if provider == "gmail":
            return await _execute_gmail_tool(
                mcp_manager, auth.user_id, tool, tool_input,
                client_id, client_secret, refresh_token
            )
        elif provider == "calendar":
            return await _execute_calendar_tool(
                auth.user_id, tool, tool_input,
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
    mcp_manager,
    user_id: str,
    tool: str,
    args: dict,
    client_id: str,
    client_secret: str,
    refresh_token: str
) -> dict:
    """Execute Gmail-specific tools."""

    if tool == "search":
        messages = await mcp_manager.list_gmail_messages(
            user_id=user_id,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            query=args.get("query"),
            max_results=min(args.get("max_results", 10), 50),
        )

        # Format results
        results = []
        for msg in messages[:20]:  # Cap display at 20
            # Get basic info from message
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
        thread = await mcp_manager.get_gmail_thread(
            user_id=user_id,
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
        result = await mcp_manager.send_gmail_message(
            user_id=user_id,
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
        result = await mcp_manager.create_gmail_draft(
            user_id=user_id,
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
    user_id: str,
    tool: str,
    args: dict,
    client_id: str,
    client_secret: str,
    refresh_token: str
) -> dict:
    """Execute Calendar-specific tools."""
    import httpx
    from datetime import datetime, timedelta

    # Get fresh access token
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
            return {"success": False, "error": f"Token refresh failed: {token_response.text}"}

        access_token = token_response.json().get("access_token")

        if tool == "list_events":
            # Parse time filters
            def parse_time(val: str, default_offset_days: int = 0) -> str:
                if not val:
                    return (datetime.utcnow() + timedelta(days=default_offset_days)).isoformat() + "Z"
                if val == "now":
                    return datetime.utcnow().isoformat() + "Z"
                if val.startswith("+"):
                    val = val[1:]
                    if val.endswith("h"):
                        delta = timedelta(hours=int(val[:-1]))
                    elif val.endswith("d"):
                        delta = timedelta(days=int(val[:-1]))
                    else:
                        delta = timedelta(days=int(val))
                    return (datetime.utcnow() + delta).isoformat() + "Z"
                return val

            time_min = parse_time(args.get("time_min", "now"), 0)
            time_max = parse_time(args.get("time_max", "+7d"), 7)
            calendar_id = args.get("calendar_id", "primary")
            max_results = min(args.get("max_results", 25), 100)

            response = await client.get(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "timeMin": time_min,
                    "timeMax": time_max,
                    "maxResults": max_results,
                    "singleEvents": "true",
                    "orderBy": "startTime",
                }
            )

            if response.status_code != 200:
                return {"success": False, "error": f"Calendar API error: {response.text}"}

            events = response.json().get("items", [])

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
            calendar_id = args.get("calendar_id", "primary")
            event_id = args["event_id"]

            response = await client.get(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code != 200:
                return {"success": False, "error": f"Calendar API error: {response.text}"}

            event = response.json()

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
            calendar_id = args.get("calendar_id", "primary")

            event_body = {
                "summary": args["summary"],
                "start": {"dateTime": args["start_time"], "timeZone": "UTC"},
                "end": {"dateTime": args["end_time"], "timeZone": "UTC"},
            }

            if args.get("description"):
                event_body["description"] = args["description"]
            if args.get("location"):
                event_body["location"] = args["location"]
            if args.get("attendees"):
                event_body["attendees"] = [{"email": e} for e in args["attendees"]]

            response = await client.post(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=event_body,
            )

            if response.status_code not in (200, 201):
                return {"success": False, "error": f"Calendar API error: {response.text}"}

            created = response.json()

            return {
                "success": True,
                "event_id": created.get("id"),
                "html_link": created.get("htmlLink"),
            }

        else:
            return {"success": False, "error": f"Unknown Calendar tool: {tool}"}


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
