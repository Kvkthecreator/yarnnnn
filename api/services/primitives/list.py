"""
ListEntities Primitive (ADR-168 Commit 4: renamed from List)

Find entities by structure/pattern. Entity layer — operates on the relational
abstraction via typed refs, NOT on the filesystem.

Distinct from ListFiles (file layer, path-based, agent-scoped).

Usage:
  ListEntities(pattern="platform:*")
  ListEntities(pattern="session:*")
"""

from typing import Any

from .refs import parse_ref, resolve_ref, ENTITY_TYPES


LIST_ENTITIES_TOOL = {
    "name": "ListEntities",
    "description": """Find entities by pattern (structural navigation).

This is the ENTITY LAYER primitive — it enumerates database-backed entities
by typed pattern. For filesystem listings, use ListFiles.

Examples (the /proc core — platform, session):
- ListEntities(pattern="platform:*") - all connected platforms
- ListEntities(pattern="session:*") - chat sessions

NOT entities: documents (files — use ListFiles(path='uploads/')), tasks/recurrences
(use ListFiles + Schedule), agents (a being is kernel data, not a workspace row).

Pattern format: <type>:<identifier|*>[?<filters>]""",
    "input_schema": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Pattern to match (e.g., 'platform:*')"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum results. Default: 20"
            },
            "order_by": {
                "type": "string",
                "description": "Field to order by. Default: 'updated_at'"
            },
            "ascending": {
                "type": "boolean",
                "description": "Sort ascending. Default: false (newest first)"
            }
        },
        "required": ["pattern"]
    }
}


async def handle_list_entities(auth: Any, input: dict) -> dict:
    """
    Handle ListEntities primitive (ADR-168: renamed from handle_list).

    Args:
        auth: Auth context with user_id and client
        input: {"pattern": "...", "limit": N, ...}

    Returns:
        {"success": True, "items": [...], "count": N}
        or {"success": False, "error": "...", "message": "..."}
    """
    pattern = input.get("pattern", "")
    limit = input.get("limit", 20)
    order_by = input.get("order_by", "updated_at")
    ascending = input.get("ascending", False)

    if not pattern:
        return {
            "success": False,
            "error": "missing_pattern",
            "message": "Pattern is required",
        }

    try:
        parsed = parse_ref(pattern)
    except ValueError as e:
        return {
            "success": False,
            "error": "invalid_pattern",
            "message": str(e),
        }

    # List should return collections
    if not parsed.is_collection and parsed.identifier not in ("*",):
        # Add * if specific ID given (treat as filter)
        pass

    try:
        # Merge limit into query if not present
        if "limit" not in parsed.query:
            parsed.query["limit"] = str(limit)

        data = await resolve_ref(parsed, auth)

        # Handle ordering (resolve_ref doesn't handle this yet)
        if isinstance(data, list) and len(data) > 1:
            # Sort in memory for now
            try:
                data.sort(
                    key=lambda x: x.get(order_by, ""),
                    reverse=not ascending,
                )
            except Exception:
                pass  # Skip sorting if field doesn't exist

        items = data if isinstance(data, list) else [data] if data else []

        return {
            "success": True,
            "items": items,
            "count": len(items),
            "pattern": pattern,
            "entity_type": parsed.entity_type,
            "message": _format_list_message(parsed.entity_type, items),
        }

    except Exception as e:
        return {
            "success": False,
            "error": "list_failed",
            "message": str(e),
            "pattern": pattern,
        }


def _format_list_message(entity_type: str, items: list) -> str:
    """Generate a human-readable message for the list result."""
    count = len(items)

    if count == 0:
        return f"No {entity_type}s found"

    # Provide summary based on type
    if entity_type == "platform":
        connected = sum(1 for i in items if i.get("status") == "active")
        return f"Found {count} platform(s) ({connected} connected)"

    # ADR-196: memory list branch removed (user_memory dropped).
    # ADR-322: the `task` branch is removed too — `task` stopped being an
    # entity type there, so the branch was unreachable (swept 2026-08-26).

    return f"Found {count} {entity_type}(s)"
