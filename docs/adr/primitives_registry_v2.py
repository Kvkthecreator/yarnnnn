"""
Primitives Registry v2

7 primitives for TP interaction with YARNNN's entity filesystem.

Removed from v1:
- Respond: TP's natural text output serves as the response
- Todo: No multi-step workflows yet; re-add when deliverable.generate pipelines exist

Usage:
    from services.primitives import PRIMITIVES, execute_primitive
    
    # PRIMITIVES = tool definitions for Claude
    # execute_primitive = unified execution handler
"""

from typing import Any

# --- Primitive Handlers ---
# Each handler: async (auth: dict, input: dict) -> dict

from .read import handle_read
from .write import handle_write
from .edit import handle_edit
from .list import handle_list
from .search import handle_search
from .execute import handle_execute
from .clarify import handle_clarify

# --- Registry ---

HANDLERS = {
    "Read": handle_read,
    "Write": handle_write,
    "Edit": handle_edit,
    "List": handle_list,
    "Search": handle_search,
    "Execute": handle_execute,
    "Clarify": handle_clarify,
}

# --- Tool Definitions (for Claude tool_use) ---

PRIMITIVES = [
    {
        "name": "Read",
        "description": "Get a single entity by reference. Use when you need details about a specific deliverable, platform, document, or work ticket.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ref": {
                    "type": "string",
                    "description": "Entity reference. Format: type:identifier. Examples: deliverable:uuid-123, platform:slack, document:latest"
                }
            },
            "required": ["ref"]
        }
    },
    {
        "name": "Write",
        "description": "Create a new entity. Always confirm with the user before creating. Check for duplicates with List first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ref": {
                    "type": "string",
                    "description": "Reference with :new identifier. Examples: deliverable:new, work:new"
                },
                "content": {
                    "type": "object",
                    "description": "Entity fields. Required fields vary by type. Deliverable: title, deliverable_type. Work: task, agent_type."
                }
            },
            "required": ["ref", "content"]
        }
    },
    {
        "name": "Edit",
        "description": "Modify an existing entity. Cannot change id, user_id, or created_at.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ref": {
                    "type": "string",
                    "description": "Reference to existing entity. Example: deliverable:uuid-123"
                },
                "changes": {
                    "type": "object",
                    "description": "Fields to update. Example: {\"status\": \"paused\"}"
                }
            },
            "required": ["ref", "changes"]
        }
    },
    {
        "name": "List",
        "description": "Find entities by pattern. Use for browsing, filtering, checking duplicates before creating, and exploring existing patterns before asking the user.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Entity pattern with optional filters. Examples: deliverable:?status=active, platform:*, document:?content_type=pdf"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results. Default: 20"
                },
                "order_by": {
                    "type": "string",
                    "description": "Sort field. Default: updated_at"
                }
            },
            "required": ["pattern"]
        }
    },
    {
        "name": "Search",
        "description": "Semantic search across documents and platform content. Use when List pattern matching isn't sufficient — e.g., finding content by meaning rather than structure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query"
                },
                "scope": {
                    "type": "string",
                    "enum": ["deliverable", "document", "platform_content", "all"],
                    "description": "Where to search. Default: all"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results. Default: 10"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "Execute",
        "description": "Trigger an external operation. Core actions: platform.sync (pull data), deliverable.generate (create content), platform.publish (deliver output). Also: platform.auth, deliverable.schedule, deliverable.approve, work.run.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform. Examples: platform.sync, deliverable.generate, platform.publish"
                },
                "target": {
                    "type": "string",
                    "description": "Entity reference for the action target. Examples: platform:slack, deliverable:uuid-123"
                },
                "params": {
                    "type": "object",
                    "description": "Optional action-specific parameters. Example for publish: {\"via\": \"platform:slack\", \"channel\": \"#team-updates\"}"
                }
            },
            "required": ["action", "target"]
        }
    },
    {
        "name": "Clarify",
        "description": "Ask the user a focused question. LAST RESORT — only use after: (1) checking {context} for existing information, (2) using List to explore entities, (3) using Search if needed. If you can infer a reasonable default, confirm it instead of asking.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "A single, focused question"
                },
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional choices to present. Keep to 2-5 options."
                }
            },
            "required": ["question"]
        }
    },
]


# --- Unified Execution ---

async def execute_primitive(auth: dict, name: str, input_data: dict) -> dict:
    """
    Execute a primitive by name.
    
    This is the single entry point for all TP tool calls.
    Handles routing, error wrapping, and consistent response format.
    
    Args:
        auth: User authentication context {user_id, ...}
        name: Primitive name (Read, Write, Edit, List, Search, Execute, Clarify)
        input_data: Primitive-specific input parameters
    
    Returns:
        dict with at minimum {success: bool}
        On success: + data/items/results/question depending on primitive
        On error: + error (code), message (human-readable)
    """
    handler = HANDLERS.get(name)
    
    if handler is None:
        return {
            "success": False,
            "error": "unknown_primitive",
            "message": f"Unknown primitive: {name}. Available: {', '.join(HANDLERS.keys())}"
        }
    
    try:
        result = await handler(auth, input_data)
        return result
    except Exception as e:
        # Log the full error for debugging
        # logger.error(f"Primitive {name} failed: {e}", exc_info=True)
        
        return {
            "success": False,
            "error": "execution_failed",
            "message": f"Failed to execute {name}: {str(e)}"
        }
