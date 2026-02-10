"""
Write Primitive

Create new entity.

Usage:
  Write(ref="deliverable:new", content={...})
  Write(ref="memory:new", content={...})
"""

from typing import Any
from uuid import uuid4
from datetime import datetime, timezone

from .refs import parse_ref, TABLE_MAP


WRITE_TOOL = {
    "name": "Write",
    "description": """Create a new entity.

Examples:
- Write(ref="deliverable:new", content={title: "Weekly Update", deliverable_type: "status_report"})
- Write(ref="memory:new", content={content: "User prefers bullet points", tags: ["preference"]})
- Write(ref="work:new", content={task: "Research competitors", agent_type: "research"})

Use ref ending in ':new' to create. Content schema depends on entity type.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "ref": {
                "type": "string",
                "description": "Entity reference with ':new' (e.g., 'deliverable:new')"
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
    "deliverable": ["title", "deliverable_type"],
    "memory": ["content"],
    "work": ["task", "agent_type"],
    "document": ["name"],
    "domain": ["name"],
}

# Default values per entity type
DEFAULTS = {
    "deliverable": {
        "status": "active",
        "frequency": "weekly",
        "governance": "manual",
    },
    "memory": {
        "tags": [],
    },
    "work": {
        "frequency": "once",
        "status": "pending",
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
    if parsed.entity_type == "deliverable":
        entity_data = _process_deliverable(entity_data)
    elif parsed.entity_type == "work":
        entity_data = _process_work(entity_data)

    try:
        result = await auth.client.table(table).insert(entity_data).execute()

        if not result.data:
            return {
                "success": False,
                "error": "insert_failed",
                "message": "Failed to create entity",
            }

        created = result.data[0]
        new_ref = f"{parsed.entity_type}:{entity_id}"

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


def _process_deliverable(data: dict) -> dict:
    """Process deliverable-specific fields."""
    # Calculate next_run_at based on frequency
    from services.deliverable_pipeline import calculate_next_run

    if "next_run_at" not in data:
        data["next_run_at"] = calculate_next_run(
            frequency=data.get("frequency", "weekly"),
            day=data.get("day"),
            time=data.get("time", "09:00"),
            timezone=data.get("timezone", "UTC"),
        )

    return data


def _process_work(data: dict) -> dict:
    """Process work-specific fields."""
    # Set is_recurring based on frequency
    frequency = data.get("frequency", "once")
    data["is_recurring"] = frequency != "once"

    return data


def _format_write_message(entity_type: str, data: dict) -> str:
    """Generate a human-readable message for the write result."""
    if entity_type == "deliverable":
        title = data.get("title", "Untitled")
        freq = data.get("frequency", "weekly")
        return f"Created deliverable: {title} ({freq})"

    elif entity_type == "memory":
        content = data.get("content", "")[:40]
        return f"Saved: {content}..."

    elif entity_type == "work":
        task = data.get("task", "")[:40]
        return f"Created work: {task}..."

    elif entity_type == "document":
        name = data.get("name", "Untitled")
        return f"Created document: {name}"

    return f"Created {entity_type}"
