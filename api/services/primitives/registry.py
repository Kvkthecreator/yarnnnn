"""
Primitive Registry

Central registry for all primitives and their handlers.
ADR-050: Platform tools are routed to MCP Gateway.
"""

from typing import Any, Callable

from .read import READ_TOOL, handle_read
from .write import WRITE_TOOL, handle_write
from .edit import EDIT_TOOL, handle_edit
from .search import SEARCH_TOOL, handle_search
from .list import LIST_TOOL, handle_list
from .execute import EXECUTE_TOOL, handle_execute
from .todo import TODO_TOOL, handle_todo
from .web_search import WEB_SEARCH_PRIMITIVE, handle_web_search
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
    # Web operations (ADR-045)
    WEB_SEARCH_PRIMITIVE,
    # Platform discovery — resolves connection metadata (authed_user_id, designated_page_id, etc.)
    LIST_INTEGRATIONS_TOOL,
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
    "Todo": handle_todo,
    "WebSearch": handle_web_search,
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
