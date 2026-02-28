"""
Primitive Registry

Central registry for all primitives and their handlers.
ADR-050: Platform tools are routed via handle_platform_tool.
ADR-080: Mode-gated primitives — each primitive declares which modes
it supports (chat, headless). get_tools_for_mode() and
create_headless_executor() provide the headless mode interface.
"""

import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

from .read import READ_TOOL, handle_read
from .write import WRITE_TOOL, handle_write
from .edit import EDIT_TOOL, handle_edit
from .search import SEARCH_TOOL, handle_search
from .list import LIST_TOOL, handle_list
from .execute import EXECUTE_TOOL, handle_execute
from .refresh import REFRESH_PLATFORM_CONTENT_TOOL, handle_refresh_platform_content
from .todo import TODO_TOOL, handle_todo
from .web_search import WEB_SEARCH_PRIMITIVE, handle_web_search
from .system_state import GET_SYSTEM_STATE_TOOL, handle_get_system_state
from services.platform_tools import is_platform_tool, handle_platform_tool
from services.project_tools import handle_list_integrations


# Communication primitives (kept from legacy for respond/clarify)
RESPOND_TOOL = {
    "name": "Respond",
    "description": """Send a message to the user.

Use after other primitives to provide context, confirm actions, or continue conversation.
The message appears inline in chat.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "The message to send"
            }
        },
        "required": ["message"]
    }
}


CLARIFY_TOOL = {
    "name": "Clarify",
    "description": """Ask the user for input before proceeding.

Use when you need more information or want to offer choices.
Appears as a focused prompt.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question to ask"
            },
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of choices"
            }
        },
        "required": ["question"]
    }
}


async def handle_respond(auth: Any, input: dict) -> dict:
    """Handle Respond primitive."""
    message = input.get("message", "")
    return {
        "success": True,
        "message": message,
        "ui_action": {
            "type": "RESPOND",
            "data": {"message": message},
        },
    }


async def handle_clarify(auth: Any, input: dict) -> dict:
    """Handle Clarify primitive."""
    question = input.get("question", "")
    options = input.get("options", [])
    return {
        "success": True,
        "question": question,
        "options": options,
        "ui_action": {
            "type": "CLARIFY",
            "data": {"question": question, "options": options},
        },
    }


LIST_INTEGRATIONS_TOOL = {
    "name": "list_integrations",
    "description": """List the user's connected platform integrations and their metadata.

Call this first when about to use a platform tool, to get:
- Which platforms are active (slack, gmail, notion, google/calendar)
- Slack: authed_user_id — use as channel_id when sending DMs to self
- Notion: designated_page_id — use as page_id when writing to user's YARNNN page
- Gmail/Calendar: user_email and designated_calendar_id

AGENTIC BEHAVIOR: Don't ask "are you connected to Slack?" — call list_integrations and find out.
If not connected, suggest connecting in Settings.""",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}


# All primitives exposed to TP
# Excluded:
# - Todo: conversation stream IS the progress indicator (Claude Code pattern)
# - Respond: TP's natural text output serves as the response
PRIMITIVES = [
    # Data operations
    READ_TOOL,
    WRITE_TOOL,
    EDIT_TOOL,
    SEARCH_TOOL,
    LIST_TOOL,
    # External operations
    EXECUTE_TOOL,
    # Platform content refresh (ADR-085)
    REFRESH_PLATFORM_CONTENT_TOOL,
    # Web operations (ADR-045)
    WEB_SEARCH_PRIMITIVE,
    # Platform discovery — resolves connection metadata (authed_user_id, designated_page_id, etc.)
    LIST_INTEGRATIONS_TOOL,
    # System state introspection (ADR-072)
    GET_SYSTEM_STATE_TOOL,
    # Communication (Clarify only - Respond removed)
    CLARIFY_TOOL,
]


# Handler mapping
HANDLERS: dict[str, Callable] = {
    "Read": handle_read,
    "Write": handle_write,
    "Edit": handle_edit,
    "Search": handle_search,
    "List": handle_list,
    "Execute": handle_execute,
    "RefreshPlatformContent": handle_refresh_platform_content,
    "Todo": handle_todo,
    "WebSearch": handle_web_search,
    "GetSystemState": handle_get_system_state,
    "Respond": handle_respond,
    "Clarify": handle_clarify,
    "list_integrations": handle_list_integrations,
}


async def execute_primitive(auth: Any, name: str, input: dict) -> dict:
    """
    Execute a primitive by name.

    ADR-050: Platform tools (platform_*) are routed to MCP Gateway.

    Args:
        auth: Auth context with user_id and client
        name: Primitive name (e.g., "Read", "Write") or platform tool (e.g., "platform_slack_send_message")
        input: Primitive input parameters

    Returns:
        Primitive result dict
    """
    # ADR-050: Route platform tools to MCP Gateway
    if is_platform_tool(name):
        try:
            result = await handle_platform_tool(auth, name, input)
            return result
        except Exception as e:
            return {
                "success": False,
                "error": "platform_tool_error",
                "message": str(e),
                "tool": name,
            }

    handler = HANDLERS.get(name)
    if not handler:
        return {
            "success": False,
            "error": "unknown_primitive",
            "message": f"Unknown primitive: {name}",
            "available": list(HANDLERS.keys()),
        }

    try:
        result = await handler(auth, input)
        return result
    except Exception as e:
        return {
            "success": False,
            "error": "execution_error",
            "message": str(e),
            "primitive": name,
        }


# =============================================================================
# ADR-080: Mode-Gated Primitives
# =============================================================================

# Which primitives are available in each mode.
# "chat" = full TP session (streaming, user present)
# "headless" = background generation (non-streaming, no user)
PRIMITIVE_MODES: dict[str, list[str]] = {
    # Read-only investigation — both modes
    "Search":           ["chat", "headless"],
    "Read":             ["chat", "headless"],
    "List":             ["chat", "headless"],
    "GetSystemState":   ["chat", "headless"],
    "WebSearch":        ["chat", "headless"],

    # Write/action/UI primitives — chat only
    "Write":            ["chat"],
    "Edit":             ["chat"],
    "Execute":          ["chat"],
    "RefreshPlatformContent": ["chat"],  # ADR-085
    "Todo":             ["chat"],
    "Respond":          ["chat"],
    "Clarify":          ["chat"],
    "list_integrations": ["chat"],
}

# Note: platform_* tools (dynamic, loaded per user) are chat-only by default.


def get_tools_for_mode(mode: str) -> list[dict]:
    """
    Get tool definitions filtered by mode.

    Args:
        mode: "chat" or "headless"

    Returns:
        List of tool definition dicts for the Anthropic API
    """
    tools = []
    for tool_def in PRIMITIVES:
        name = tool_def.get("name", "")
        modes = PRIMITIVE_MODES.get(name, ["chat"])
        if mode in modes:
            tools.append(tool_def)
    return tools


def create_headless_executor(client: Any, user_id: str):
    """
    Create a tool executor function for headless mode.

    Returns an async callable (tool_name, tool_input) -> result_dict
    that dispatches to primitive handlers with headless-appropriate
    error handling (log + return error dict, never raise).

    Args:
        client: Supabase client (service role)
        user_id: User UUID for data scoping
    """
    class HeadlessAuth:
        """Minimal auth context for headless execution."""
        def __init__(self, client, user_id):
            self.client = client
            self.user_id = user_id

    auth = HeadlessAuth(client, user_id)

    async def executor(tool_name: str, tool_input: dict) -> dict:
        # Verify tool is allowed in headless mode
        modes = PRIMITIVE_MODES.get(tool_name, [])
        if "headless" not in modes:
            logger.warning(
                f"[HEADLESS] Tool {tool_name} not available in headless mode, skipping"
            )
            return {
                "success": False,
                "error": "not_available",
                "message": f"Tool {tool_name} is not available in headless mode",
            }

        handler = HANDLERS.get(tool_name)
        if not handler:
            return {
                "success": False,
                "error": "unknown_primitive",
                "message": f"Unknown primitive: {tool_name}",
            }

        try:
            result = await handler(auth, tool_input)
            return result
        except Exception as e:
            logger.error(f"[HEADLESS] Tool {tool_name} failed: {e}")
            return {
                "success": False,
                "error": "execution_error",
                "message": f"Tool execution failed: {e}",
            }

    return executor
