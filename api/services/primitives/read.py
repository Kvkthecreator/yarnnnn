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
    "description": """Retrieve any entity by reference. Returns full content.

IMPORTANT: Use the exact `ref` value returned by Search or List. The ref contains a UUID, not a filename.

Examples:
- Read(ref="document:abc12345-def6-7890-ghij-klmnopqrstuv") - document by UUID from Search results
- Read(ref="deliverable:latest") - most recent deliverable
- Read(ref="platform:slack") - platform by provider name
- Read(ref="memory:uuid-123") - specific memory

For documents: Returns full content from all pages, not just metadata.

Reference format: <type>:<UUID>
Types: deliverable, platform, memory, session, domain, document, work

Workflow:
1. Search(query="...", scope="document") → returns results with `ref` field
2. Read(ref="document:<UUID from search>") → returns full document content""",
    "input_schema": {
        "type": "object",
        "properties": {
            "ref": {
                "type": "string",
                "description": "Entity reference from Search/List results (e.g., 'document:abc12345-uuid'). Must use UUID, not filename."
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

    elif parsed.entity_type == "document":
        filename = data.get("filename", "Unknown")
        page_count = data.get("page_count", 0)
        word_count = data.get("word_count", 0)
        has_content = bool(data.get("content"))
        content_note = "with content" if has_content else "metadata only"
        return f"Document: {filename} ({page_count} pages, {word_count} words, {content_note})"

    return f"Retrieved {parsed.entity_type}"
