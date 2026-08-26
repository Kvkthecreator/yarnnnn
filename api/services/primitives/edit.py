"""
EditEntity Primitive (ADR-168 Commit 4: renamed from Edit)

Modify existing entity by typed reference. Entity layer — operates on the
relational abstraction, NOT on the filesystem.

Distinct from WriteFile (file layer, path-based, agent-scoped).

Chat-only — mutates entities under explicit user direction. Headless has
no user-authorization path.

Usage:
  EditEntity(ref="platform:notion", changes={status: "paused"})

2026-08-26 — the `agent` target is REMOVED with the pre-ADR-596 agent model
(the `agents` table held zero rows; every agent: ref resolved to None, so all
four agent branches here were unreachable behind the not-found gate). The
agent_memory / agent_instructions writes went with it — a being's character
lives in `services/agents_registry.AGENTS`, and editing a KERNEL being is
refused at `assert_editable`, not performed here.
"""

from typing import Any
from datetime import datetime, timezone

from .refs import parse_ref, resolve_ref, TABLE_MAP


EDIT_ENTITY_TOOL = {
    "name": "EditEntity",
    "description": """Modify an existing entity by typed ref.

This is the ENTITY LAYER primitive — it mutates database-backed entities. It
serves the mutable /proc record: **platform** (a connection's own settings).
For filesystem writes (including domain context + uploaded docs), use WriteFile.
Documents and tasks are not entities — they are files / recurrence YAML; and
agents are not entities either (a being is kernel data, not a workspace row).

Examples:
- EditEntity(ref="platform:notion", changes={status: "paused"})

Only specified fields are updated; others remain unchanged.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "ref": {
                "type": "string",
                "description": "Entity reference (e.g., 'platform:notion')"
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


async def handle_edit_entity(auth: Any, input: dict) -> dict:
    """
    Handle EditEntity primitive (ADR-168: renamed from handle_edit).

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

    # 2026-08-26 — the four `agent` branches are DELETED with the entity type:
    # the ADR-091 agent_memory write, the ADR-106 agent_instructions write to
    # AGENT.md, and the ADR-109 scope/role validation. All four sat BEHIND the
    # resolve_ref not-found gate above, so with the `agents` table empty none
    # was reachable; removing the type removes them honestly rather than
    # leaving branches keyed on a value `parse_ref` can no longer produce.

    # Filter out immutable fields
    filtered_changes = {
        k: v for k, v in changes.items()
        if k not in IMMUTABLE_FIELDS
    }

    if not filtered_changes:
        return {
            "success": False,
            "error": "no_valid_changes",
            # 2026-08-26 — the old hint named append_observation / set_goal,
            # verbs deleted with the `agent` entity type. A refusal that names
            # a tool the caller does not have sends them looking for it.
            "message": f"Cannot modify fields: {', '.join(changes.keys())}. "
                       f"Only mutable, non-identity fields can be edited here.",
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


# _handle_agent_memory_write DELETED 2026-08-26 with the `agent` entity type.

# _format_memory_write_message DELETED with its only caller.

def _format_edit_message(entity_type: str, changes: dict, data: dict) -> str:
    """Generate a human-readable message for the edit result."""
    change_list = list(changes.keys())
    # Remove updated_at from display
    if "updated_at" in change_list:
        change_list.remove("updated_at")

    # ADR-196 + ADR-235: memory edit branch removed (user_memory dropped;
    # memory is filesystem-native, mutated via WriteFile(scope="workspace",
    # path="system/notes.md", ...), not EditEntity).

    return f"Updated {entity_type}: {', '.join(change_list)}"
