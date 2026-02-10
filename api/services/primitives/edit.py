"""
Edit Primitive

Modify existing entity.

Usage:
  Edit(ref="deliverable:uuid-123", changes={status: "paused"})
  Edit(ref="memory:uuid-456", changes={content: "Updated content"})
"""

from typing import Any
from datetime import datetime, timezone

from .refs import parse_ref, resolve_ref, TABLE_MAP


EDIT_TOOL = {
    "name": "Edit",
    "description": """Modify an existing entity.

Examples:
- Edit(ref="deliverable:uuid-123", changes={status: "paused"})
- Edit(ref="memory:uuid-456", changes={content: "Updated preference"})
- Edit(ref="work:uuid-789", changes={is_active: false})

Only specified fields are updated; others remain unchanged.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "ref": {
                "type": "string",
                "description": "Entity reference (e.g., 'deliverable:uuid-123')"
            },
            "changes": {
                "type": "object",
                "description": "Fields to update"
            }
        },
        "required": ["ref", "changes"]
    }
}


# Fields that cannot be edited
IMMUTABLE_FIELDS = {"id", "user_id", "created_at"}


async def handle_edit(auth: Any, input: dict) -> dict:
    """
    Handle Edit primitive.

    Args:
        auth: Auth context with user_id and client
        input: {"ref": "type:id", "changes": {...}}

    Returns:
        {"success": True, "data": {...}, "ref": "...", "changes_applied": [...]}
        or {"success": False, "error": "...", "message": "..."}
    """
    ref_str = input.get("ref", "")
    changes = input.get("changes", {})

    if not ref_str:
        return {
            "success": False,
            "error": "missing_ref",
            "message": "Reference is required",
        }

    if not changes:
        return {
            "success": False,
            "error": "no_changes",
            "message": "No changes specified",
        }

    try:
        parsed = parse_ref(ref_str)
    except ValueError as e:
        return {
            "success": False,
            "error": "invalid_ref",
            "message": str(e),
        }

    # Cannot edit collections or special refs
    if parsed.is_collection or parsed.identifier in ("new", "current", "latest"):
        return {
            "success": False,
            "error": "invalid_operation",
            "message": "Edit requires a specific entity reference",
        }

    # Get table
    table = TABLE_MAP.get(parsed.entity_type)
    if not table:
        return {
            "success": False,
            "error": "unsupported_type",
            "message": f"Cannot edit entities of type: {parsed.entity_type}",
        }

    # Verify entity exists and user has access
    try:
        existing = await resolve_ref(parsed, auth)
        if not existing:
            return {
                "success": False,
                "error": "not_found",
                "message": f"{parsed.entity_type} not found",
                "ref": ref_str,
            }
    except PermissionError as e:
        return {
            "success": False,
            "error": "permission_denied",
            "message": str(e),
            "ref": ref_str,
        }

    # Filter out immutable fields
    filtered_changes = {
        k: v for k, v in changes.items()
        if k not in IMMUTABLE_FIELDS
    }

    if not filtered_changes:
        return {
            "success": False,
            "error": "no_valid_changes",
            "message": f"Cannot modify fields: {', '.join(changes.keys())}",
        }

    # Add updated_at
    filtered_changes["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Perform update
    try:
        # Build update query based on entity type
        if parsed.entity_type == "platform":
            query = auth.client.table(table).update(filtered_changes).eq(
                "provider", parsed.identifier
            ).eq("user_id", auth.user_id)
        else:
            query = auth.client.table(table).update(filtered_changes).eq(
                "id", parsed.identifier
            ).eq("user_id", auth.user_id)

        result = query.execute()

        if not result.data:
            return {
                "success": False,
                "error": "update_failed",
                "message": "Failed to update entity",
                "ref": ref_str,
            }

        updated = result.data[0]

        return {
            "success": True,
            "data": updated,
            "ref": ref_str,
            "entity_type": parsed.entity_type,
            "changes_applied": list(filtered_changes.keys()),
            "message": _format_edit_message(parsed.entity_type, filtered_changes, updated),
        }

    except Exception as e:
        return {
            "success": False,
            "error": "edit_failed",
            "message": str(e),
            "ref": ref_str,
        }


def _format_edit_message(entity_type: str, changes: dict, data: dict) -> str:
    """Generate a human-readable message for the edit result."""
    change_list = list(changes.keys())
    # Remove updated_at from display
    if "updated_at" in change_list:
        change_list.remove("updated_at")

    if entity_type == "deliverable":
        title = data.get("title", "Untitled")
        if "status" in changes:
            return f"Updated {title}: now {changes['status']}"
        return f"Updated {title}: {', '.join(change_list)}"

    elif entity_type == "memory":
        if "content" in changes:
            return f"Updated memory content"
        return f"Updated memory: {', '.join(change_list)}"

    elif entity_type == "work":
        if "is_active" in changes:
            status = "resumed" if changes["is_active"] else "paused"
            return f"Work {status}"
        return f"Updated work: {', '.join(change_list)}"

    return f"Updated {entity_type}: {', '.join(change_list)}"
