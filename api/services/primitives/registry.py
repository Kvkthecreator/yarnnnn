"""
Primitive Registry

Central registry for all primitives and their handlers.
"""

from typing import Any, Callable

from .read import READ_TOOL, handle_read
from .write import WRITE_TOOL, handle_write
from .edit import EDIT_TOOL, handle_edit
from .search import SEARCH_TOOL, handle_search
from .list import LIST_TOOL, handle_list
from .execute import EXECUTE_TOOL, handle_execute
from .todo import TODO_TOOL, handle_todo


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


# All primitives
PRIMITIVES = [
    # Data operations
    READ_TOOL,
    WRITE_TOOL,
    EDIT_TOOL,
    SEARCH_TOOL,
    LIST_TOOL,
    # External operations
    EXECUTE_TOOL,
    # Progress tracking
    TODO_TOOL,
    # Communication
    RESPOND_TOOL,
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
    "Respond": handle_respond,
    "Clarify": handle_clarify,
}


async def execute_primitive(name: str, auth: Any, input: dict) -> dict:
    """
    Execute a primitive by name.

    Args:
        name: Primitive name (e.g., "Read", "Write")
        auth: Auth context with user_id and client
        input: Primitive input parameters

    Returns:
        Primitive result dict
    """
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
