"""
Read Primitive

Retrieve entity by reference.

Usage:
  Read(ref="deliverable:uuid-123")
  Read(ref="platform:twitter")
  Read(refs=["memory:uuid-1", "memory:uuid-2"])  # Batch
"""

from typing import Any

from .refs import parse_ref, resolve_ref


READ_TOOL = {
    "name": "Read",
    "description": """Retrieve any entity by reference.

Examples:
- Read(ref="deliverable:latest") - most recent deliverable
- Read(ref="platform:twitter") - Twitter platform config
- Read(ref="memory:uuid-123") - specific memory
- Read(refs=["deliverable:uuid-1", "deliverable:uuid-2"]) - batch read

Reference format: <type>:<identifier>[/<subpath>][?<query>]
Types: deliverable, platform, memory, session, domain, document, work""",
    "input_schema": {
        "type": "object",
        "properties": {
            "ref": {
                "type": "string",
                "description": "Entity reference (e.g., 'deliverable:uuid-123')"
            },
            "refs": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Multiple refs for batch read"
            }
        }
    }
}


async def handle_read(auth: Any, input: dict) -> dict:
    """
    Handle Read primitive.

    Args:
        auth: Auth context with user_id and client
        input: {"ref": "..."} or {"refs": [...]}

    Returns:
        {"success": True, "data": ..., "ref": "..."}
        or {"success": False, "error": "...", "ref": "..."}
    """
    ref_str = input.get("ref")
    refs = input.get("refs", [])

    # Batch mode
    if refs:
        results = []
        for r in refs:
            try:
                parsed = parse_ref(r)
                data = await resolve_ref(parsed, auth)
                results.append({
                    "ref": r,
                    "success": True,
                    "data": data,
                })
            except Exception as e:
                results.append({
                    "ref": r,
                    "success": False,
                    "error": str(e),
                })

        return {
            "success": all(r["success"] for r in results),
            "results": results,
            "count": len(results),
        }

    # Single ref mode
    if not ref_str:
        return {
            "success": False,
            "error": "missing_ref",
            "message": "Either 'ref' or 'refs' is required",
        }

    try:
        parsed = parse_ref(ref_str)
        data = await resolve_ref(parsed, auth)

        if data is None:
            return {
                "success": False,
                "error": "not_found",
                "message": f"{parsed.entity_type} not found",
                "ref": ref_str,
            }

        # Format response based on entity type
        return {
            "success": True,
            "data": data,
            "ref": ref_str,
            "entity_type": parsed.entity_type,
            "message": _format_read_message(parsed, data),
        }

    except ValueError as e:
        return {
            "success": False,
            "error": "invalid_ref",
            "message": str(e),
            "ref": ref_str,
        }
    except PermissionError as e:
        return {
            "success": False,
            "error": "permission_denied",
            "message": str(e),
            "ref": ref_str,
        }
    except Exception as e:
        return {
            "success": False,
            "error": "read_failed",
            "message": str(e),
            "ref": ref_str,
        }


def _format_read_message(parsed, data) -> str:
    """Generate a human-readable message for the read result."""
    if isinstance(data, list):
        return f"Found {len(data)} {parsed.entity_type}(s)"

    # Single entity messages
    if parsed.entity_type == "deliverable":
        title = data.get("title", "Untitled")
        status = data.get("status", "unknown")
        return f"Deliverable: {title} ({status})"

    elif parsed.entity_type == "platform":
        provider = data.get("provider", "unknown")
        status = data.get("status", "unknown")
        return f"Platform: {provider} ({status})"

    elif parsed.entity_type == "memory":
        content = data.get("content", "")[:50]
        return f"Memory: {content}..."

    elif parsed.entity_type == "work":
        task = data.get("task", "")[:50]
        status = data.get("status", "unknown")
        return f"Work: {task}... ({status})"

    return f"Retrieved {parsed.entity_type}"
