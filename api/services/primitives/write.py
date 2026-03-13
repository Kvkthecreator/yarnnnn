"""
Write Primitive

Create new entity.

Usage:
  Write(ref="agent:new", content={...})
  Write(ref="memory:new", content={...})
"""

from typing import Any
from uuid import uuid4
from datetime import datetime, timezone

from .refs import parse_ref, TABLE_MAP


WRITE_TOOL = {
    "name": "Write",
    "description": """Create a new memory or document entity.

For agents, use CreateAgent instead.

Examples:
- Write(ref="memory:new", content={content: "User prefers bullet points", tags: ["preference"]})
- Write(ref="document:new", content={name: "Q2 Report", url: "..."})
Use ref ending in ':new' to create. Content schema depends on entity type.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "ref": {
                "type": "string",
                "description": "Entity reference with ':new' (e.g., 'agent:new')"
            },
            "content": {
                "type": "object",
                "description": "Entity data to create"
            }
        },
        "required": ["ref", "content"]
    }
}


# Required fields per entity type
REQUIRED_FIELDS = {
    "agent": ["title"],  # scope + skill defaulted in _process_agent()
    "memory": ["content"],
    "document": ["name"],
    "domain": ["name"],
}

# Default values per entity type
# Note: agent.schedule is JSONB, frequency goes inside it
DEFAULTS = {
    "agent": {
        "status": "active",
    },
    "memory": {
        "tags": [],
        "source": "user_stated",  # ADR-058: User-stated facts via TP
        "entry_type": "fact",  # Default type
        "is_active": True,
        "importance": 0.5,
    },
}


async def handle_write(auth: Any, input: dict) -> dict:
    """
    Handle Write primitive.

    Args:
        auth: Auth context with user_id and client
        input: {"ref": "type:new", "content": {...}}

    Returns:
        {"success": True, "data": {...}, "ref": "type:uuid"}
        or {"success": False, "error": "...", "message": "..."}
    """
    ref_str = input.get("ref", "")
    content = input.get("content", {})

    if not ref_str:
        return {
            "success": False,
            "error": "missing_ref",
            "message": "Reference is required",
        }

    try:
        parsed = parse_ref(ref_str)
    except ValueError as e:
        return {
            "success": False,
            "error": "invalid_ref",
            "message": str(e),
        }

    # Validate it's a create operation
    if not parsed.is_create:
        return {
            "success": False,
            "error": "invalid_operation",
            "message": "Write requires ':new' identifier. Use Edit for modifications.",
        }

    # ADR-111: Agent creation moved to CreateAgent primitive
    if parsed.entity_type == "agent":
        return {
            "success": False,
            "error": "use_create_agent",
            "message": "Use CreateAgent to create agents. Write handles memories and documents only. Example: CreateAgent(title=\"Weekly Status\", skill=\"synthesize\", frequency=\"weekly\")",
        }

    # Get table
    table = TABLE_MAP.get(parsed.entity_type)
    if not table:
        return {
            "success": False,
            "error": "unsupported_type",
            "message": f"Cannot create entities of type: {parsed.entity_type}",
        }

    # Validate required fields
    required = REQUIRED_FIELDS.get(parsed.entity_type, [])
    missing = [f for f in required if f not in content]
    if missing:
        return {
            "success": False,
            "error": "missing_fields",
            "message": f"Missing required fields: {', '.join(missing)}",
            "required": required,
        }

    # Build entity data
    now = datetime.now(timezone.utc).isoformat()
    entity_id = str(uuid4())

    entity_data = {
        "id": entity_id,
        "user_id": auth.user_id,
        "created_at": now,
        "updated_at": now,
        **DEFAULTS.get(parsed.entity_type, {}),
        **content,
    }

    # Entity-specific processing
    if parsed.entity_type == "agent":
        entity_data = _process_agent(entity_data)
    elif parsed.entity_type == "memory":
        entity_data = _process_memory(entity_data)
    elif parsed.entity_type == "document":
        entity_data = _process_document(entity_data)

    # ADR-106: Extract workspace-only fields before DB insert
    ws_instructions = entity_data.pop("_workspace_instructions", None)

    try:
        result = auth.client.table(table).insert(entity_data).execute()

        if not result.data:
            return {
                "success": False,
                "error": "insert_failed",
                "message": "Failed to create entity",
            }

        created = result.data[0]
        new_ref = f"{parsed.entity_type}:{entity_id}"

        # ADR-106: Seed workspace AGENT.md (singular source of truth)
        if parsed.entity_type == "agent" and ws_instructions:
                try:
                    from services.workspace import AgentWorkspace, get_agent_slug
                    ws = AgentWorkspace(auth.client, auth.user_id, get_agent_slug(created))
                    await ws.write("AGENT.md", ws_instructions, summary="Agent instructions")
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"[WRITE] Workspace seed failed for {entity_id}: {e}")

        return {
            "success": True,
            "data": created,
            "ref": new_ref,
            "entity_type": parsed.entity_type,
            "message": _format_write_message(parsed.entity_type, created),
        }

    except Exception as e:
        return {
            "success": False,
            "error": "write_failed",
            "message": str(e),
        }


# ADR-111: Agent creation logic moved to services/agent_creation.py
# Re-export for any remaining imports
from services.agent_creation import VALID_SCOPES, VALID_SKILLS, SKILL_TO_SCOPE  # noqa: F401


def _process_memory(data: dict) -> dict:
    """Process memory-specific fields.

    Flat field mappings (convenience for TP):
    - note, fact, preference -> content (aliases)
    - category, type, context -> added to tags
    """
    # Handle content aliases
    for alias in ["note", "fact", "preference"]:
        if alias in data and "content" not in data:
            data["content"] = data.pop(alias)
        elif alias in data:
            data.pop(alias)  # Remove if content already set

    # Add category/type/context to tags
    tags = data.get("tags", [])
    if isinstance(tags, list):
        for field in ["category", "type", "context"]:
            if field in data:
                value = data.pop(field)
                if value and value not in tags:
                    tags.append(value)
    data["tags"] = tags

    return data


def _process_document(data: dict) -> dict:
    """Process document-specific fields.

    Flat field mappings (convenience for TP):
    - name, title -> filename (aliases)
    - url -> file_url (alias)
    """
    # Handle filename aliases
    for alias in ["name", "title"]:
        if alias in data and "filename" not in data:
            data["filename"] = data.pop(alias)
        elif alias in data:
            data.pop(alias)  # Remove if filename already set

    # Handle file_url alias
    if "url" in data and "file_url" not in data:
        data["file_url"] = data.pop("url")
    elif "url" in data:
        data.pop("url")

    return data


def _format_write_message(entity_type: str, data: dict) -> str:
    """Generate a human-readable message for the write result."""
    if entity_type == "agent":
        title = data.get("title", "Untitled")
        freq = data.get("frequency", "weekly")
        return f"Created agent: {title} ({freq})"

    elif entity_type == "memory":
        content = data.get("content", "")[:40]
        return f"Saved: {content}..."

    elif entity_type == "document":
        name = data.get("name", "Untitled")
        return f"Created document: {name}"

    return f"Created {entity_type}"
