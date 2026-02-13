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
    "deliverable": ["title"],  # deliverable_type has default in schema
    "memory": ["content"],
    "work": ["task", "agent_type"],
    "document": ["name"],
    "domain": ["name"],
}

# Default values per entity type
# Note: deliverable.schedule is JSONB, frequency goes inside it
DEFAULTS = {
    "deliverable": {
        "status": "active",
    },
    "memory": {
        "tags": [],
        "source": "user_stated",  # ADR-058: User-stated facts via TP
        "entry_type": "fact",  # Default type
        "is_active": True,
        "importance": 0.5,
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
    elif parsed.entity_type == "memory":
        entity_data = _process_memory(entity_data)
    elif parsed.entity_type == "work":
        entity_data = _process_work(entity_data)
    elif parsed.entity_type == "document":
        entity_data = _process_document(entity_data)

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
    """Process deliverable-specific fields.

    Schema notes:
    - schedule: JSONB with {frequency, day, time, timezone}
    - deliverable_type: defaults to 'custom' in schema
    - recipient_context: JSONB with {name, role, priorities, company}
    - type_config: JSONB with type-specific settings

    Flat field mappings (convenience for TP):
    - frequency, day, time, timezone -> schedule.*
    - recipient_name, recipient_role, company, priorities -> recipient_context.*
    - audience, tone, sections, detail_level, subject, format -> type_config.*
    - email, slack_channel -> destination.*
    """
    from jobs.unified_scheduler import calculate_next_run_from_schedule

    # Build schedule JSONB from flat fields or existing schedule
    schedule = data.get("schedule", {})
    if isinstance(schedule, dict):
        # Allow flat frequency/day/time fields to override schedule
        if "frequency" in data and "frequency" not in schedule:
            schedule["frequency"] = data.pop("frequency")
        if "day" in data and "day" not in schedule:
            schedule["day"] = data.pop("day")
        if "time" in data and "time" not in schedule:
            schedule["time"] = data.pop("time")
        if "timezone" in data and "timezone" not in schedule:
            schedule["timezone"] = data.pop("timezone")

    # Apply defaults to schedule
    if "frequency" not in schedule:
        schedule["frequency"] = "weekly"
    if "time" not in schedule:
        schedule["time"] = "09:00"
    if "timezone" not in schedule:
        schedule["timezone"] = "UTC"

    data["schedule"] = schedule

    # Build recipient_context JSONB from flat fields
    recipient_context = data.get("recipient_context", {})
    if isinstance(recipient_context, dict):
        if "recipient_name" in data:
            recipient_context["name"] = data.pop("recipient_name")
        if "recipient_role" in data:
            recipient_context["role"] = data.pop("recipient_role")
        if "company" in data:
            recipient_context["company"] = data.pop("company")
        if "priorities" in data:
            recipient_context["priorities"] = data.pop("priorities")
    data["recipient_context"] = recipient_context

    # Build type_config JSONB from flat fields
    type_config = data.get("type_config", {})
    if isinstance(type_config, dict):
        # Type-specific configuration fields
        for field in ["audience", "tone", "sections", "detail_level", "subject", "format"]:
            if field in data:
                type_config[field] = data.pop(field)
    data["type_config"] = type_config

    # Build destination JSONB from flat fields
    destination = data.get("destination", {})
    if isinstance(destination, dict):
        if "email" in data:
            destination["type"] = "email"
            destination["email"] = data.pop("email")
        if "slack_channel" in data:
            destination["type"] = "slack"
            destination["channel"] = data.pop("slack_channel")
    if destination:
        data["destination"] = destination

    # Calculate next_run_at based on schedule
    if "next_run_at" not in data:
        next_run = calculate_next_run_from_schedule(schedule)
        data["next_run_at"] = next_run.isoformat()

    return data


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


def _process_work(data: dict) -> dict:
    """Process work-specific fields.

    Flat field mappings (convenience for TP):
    - description, priority, deadline -> parameters.*
    """
    # Set is_recurring based on frequency
    frequency = data.get("frequency", "once")
    data["is_recurring"] = frequency != "once"

    # Move convenience fields to parameters JSONB
    parameters = data.get("parameters", {})
    if isinstance(parameters, dict):
        for field in ["description", "priority", "deadline"]:
            if field in data:
                parameters[field] = data.pop(field)
    if parameters:
        data["parameters"] = parameters

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
