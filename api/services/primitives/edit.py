"""
Edit Primitive

Modify existing entity.

Usage:
  Edit(ref="agent:uuid-123", changes={status: "paused"})
  Edit(ref="agent:uuid-123", changes={agent_instructions: "Use formal tone."})
  Edit(ref="memory:uuid-456", changes={content: "Updated content"})

For agent_memory, use append_observation or set_goal keys (scoped writes, not replace):
  Edit(ref="agent:uuid-123", changes={append_observation: {note: "Q4 data finalized"}})
  Edit(ref="agent:uuid-123", changes={set_goal: {description: "...", status: "in_progress"}})
"""

from typing import Any
from datetime import datetime, timezone

from .refs import parse_ref, resolve_ref, TABLE_MAP


EDIT_TOOL = {
    "name": "Edit",
    "description": """Modify an existing entity.

Examples:
- Edit(ref="agent:uuid-123", changes={status: "paused"})
- Edit(ref="agent:uuid-123", changes={agent_instructions: "Always use bullet points."})
- Edit(ref="agent:uuid-123", changes={append_observation: {note: "Q4 data is now finalized"}})
- Edit(ref="agent:uuid-123", changes={set_goal: {description: "...", status: "in_progress", milestones: [...]}})
- Edit(ref="memory:uuid-456", changes={content: "Updated preference"})

For agent_memory, use append_observation or set_goal (scoped writes — do not pass raw agent_memory JSONB).
Only specified fields are updated; others remain unchanged.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "ref": {
                "type": "string",
                "description": "Entity reference (e.g., 'agent:uuid-123')"
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

    # ADR-091: Scoped agent_memory writes — append_observation / set_goal
    # These are handled specially to avoid clobbering system-accumulated memory.
    if parsed.entity_type == "agent" and (
        "append_observation" in changes or "set_goal" in changes
    ):
        return await _handle_agent_memory_write(auth, parsed, existing, changes)

    # Filter out immutable fields (and scoped memory keys, handled above)
    filtered_changes = {
        k: v for k, v in changes.items()
        if k not in IMMUTABLE_FIELDS and k not in ("append_observation", "set_goal", "agent_memory")
    }

    if not filtered_changes:
        return {
            "success": False,
            "error": "no_valid_changes",
            "message": f"Cannot modify fields: {', '.join(changes.keys())}. "
                       f"Use append_observation or set_goal to write agent memory.",
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


async def _handle_agent_memory_write(auth: Any, parsed: Any, existing: dict, changes: dict) -> dict:
    """
    Scoped write to agent_memory JSONB.

    ADR-091: append_observation appends to observations list (never replaces).
    set_goal replaces the goal object only (observations untouched).
    Raw agent_memory writes are blocked to avoid clobbering system-accumulated memory.
    """
    import json

    current_memory = existing.get("agent_memory") or {}
    if isinstance(current_memory, str):
        try:
            current_memory = json.loads(current_memory)
        except Exception:
            current_memory = {}

    updated_memory = dict(current_memory)
    applied = []

    if "append_observation" in changes:
        obs = changes["append_observation"]
        if not isinstance(obs, dict) or "note" not in obs:
            return {
                "success": False,
                "error": "invalid_observation",
                "message": "append_observation requires {note: '...', source: '...' (optional)}",
            }
        observation = {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "source": obs.get("source", "user"),
            "note": obs["note"],
        }
        observations = list(updated_memory.get("observations") or [])
        observations.append(observation)
        # Cap at 20 — headless extraction compacts periodically
        updated_memory["observations"] = observations[-20:]
        applied.append("append_observation")

    if "set_goal" in changes:
        goal = changes["set_goal"]
        if not isinstance(goal, dict) or "description" not in goal:
            return {
                "success": False,
                "error": "invalid_goal",
                "message": "set_goal requires {description: '...', status: '...', milestones: [...] (optional)}",
            }
        updated_memory["goal"] = {
            "description": goal["description"],
            "status": goal.get("status", "in_progress"),
            "milestones": goal.get("milestones", []),
        }
        applied.append("set_goal")

    try:
        result = auth.client.table("agents").update({
            "agent_memory": updated_memory,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", parsed.identifier).eq("user_id", auth.user_id).execute()

        if not result.data:
            return {
                "success": False,
                "error": "update_failed",
                "message": "Failed to update agent memory",
            }

        return {
            "success": True,
            "data": result.data[0],
            "ref": f"agent:{parsed.identifier}",
            "entity_type": "agent",
            "changes_applied": applied,
            "message": _format_memory_write_message(applied, changes),
        }
    except Exception as e:
        return {
            "success": False,
            "error": "memory_write_failed",
            "message": str(e),
        }


def _format_memory_write_message(applied: list, changes: dict) -> str:
    parts = []
    if "append_observation" in applied:
        note = changes["append_observation"].get("note", "")
        parts.append(f"Observation added: \"{note[:60]}{'...' if len(note) > 60 else ''}\"")
    if "set_goal" in applied:
        desc = changes["set_goal"].get("description", "")
        parts.append(f"Goal set: \"{desc[:60]}{'...' if len(desc) > 60 else ''}\"")
    return ". ".join(parts)


def _format_edit_message(entity_type: str, changes: dict, data: dict) -> str:
    """Generate a human-readable message for the edit result."""
    change_list = list(changes.keys())
    # Remove updated_at from display
    if "updated_at" in change_list:
        change_list.remove("updated_at")

    if entity_type == "agent":
        title = data.get("title", "Untitled")
        if "status" in changes:
            return f"Updated {title}: now {changes['status']}"
        return f"Updated {title}: {', '.join(change_list)}"

    elif entity_type == "memory":
        if "content" in changes:
            return f"Updated memory content"
        return f"Updated memory: {', '.join(change_list)}"

    return f"Updated {entity_type}: {', '.join(change_list)}"
