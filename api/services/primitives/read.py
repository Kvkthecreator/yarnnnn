"""
LookupEntity Primitive (ADR-168 Commit 4: renamed from Read)

Retrieve entity by typed reference. Entity layer — operates on the relational
abstraction via parse_ref/resolve_ref, NOT on the filesystem.

Distinct from ReadFile (file layer, path-based, agent-scoped).

Usage:
  LookupEntity(ref="agent:uuid-123")
  LookupEntity(ref="platform:twitter")
  LookupEntity(refs=["memory:uuid-1", "memory:uuid-2"])  # Batch
"""

from typing import Any

from .refs import parse_ref, resolve_ref


LOOKUP_ENTITY_TOOL = {
    "name": "LookupEntity",
    "description": """Look up any entity by reference. Returns full content.

This is the ENTITY LAYER primitive — it operates on the relational abstraction
(typed refs like agent:uuid, document:uuid), not on the filesystem. For file
reads, use ReadFile (path-based, agent-scoped).

IMPORTANT: Use the exact `ref` value returned by SearchEntities or ListEntities. The ref contains a UUID, not a filename.

Examples:
- LookupEntity(ref="document:abc12345-def6-7890-ghij-klmnopqrstuv") - document by UUID from SearchEntities results
- LookupEntity(ref="agent:latest") - most recent agent
- LookupEntity(ref="platform:slack") - platform by provider name
- LookupEntity(ref="memory:uuid-123") - specific memory

For documents: Returns full content from all pages, not just metadata.

Reference format: <type>:<UUID>
Types: agent, platform, memory, session, domain, document, task, version

Workflow:
1. SearchEntities(query="...", scope="document") → returns results with `ref` field
2. LookupEntity(ref="document:<UUID from search>") → returns full document content""",
    "input_schema": {
        "type": "object",
        "properties": {
            "ref": {
                "type": "string",
                "description": "Entity reference from SearchEntities/ListEntities results (e.g., 'document:abc12345-uuid'). Must use UUID, not filename."
            },
            "refs": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Multiple refs for batch lookup"
            }
        }
    }
}


async def handle_lookup_entity(auth: Any, input: dict) -> dict:
    """
    Handle LookupEntity primitive (ADR-168: renamed from handle_read).

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
            # Provide retry hint based on entity type
            # (ADR-196: "memory" retired — memory is filesystem-native;
            # agents/YARNNN read /workspace/*.md directly via ReadFile.)
            if parsed.entity_type == "document":
                retry_hint = "Use Search(scope='document') first to find documents and get their UUID refs."
            elif parsed.entity_type == "agent":
                retry_hint = "Use List(pattern='agent:*') to see available agents."
            else:
                retry_hint = f"Use Search or List to find valid {parsed.entity_type} refs."

            return {
                "success": False,
                "error": "not_found",
                "message": f"{parsed.entity_type} not found",
                "ref": ref_str,
                "retry_hint": retry_hint,
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
            "retry_hint": "Refs must be in format '<type>:<uuid>' where type is agent, document, memory, etc. Use Search to get valid refs.",
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
    if parsed.entity_type == "agent":
        title = data.get("title", "Untitled")
        status = data.get("status", "unknown")
        return f"Agent: {title} ({status})"

    elif parsed.entity_type == "platform":
        provider = data.get("provider", "unknown")
        status = data.get("status", "unknown")
        return f"Platform: {provider} ({status})"

    # ADR-196: memory message branch removed (user_memory table dropped).

    elif parsed.entity_type == "document":
        filename = data.get("filename", "Unknown")
        page_count = data.get("page_count", 0)
        word_count = data.get("word_count", 0)
        has_content = bool(data.get("content"))
        content_note = "with content" if has_content else "metadata only"
        return f"Document: {filename} ({page_count} pages, {word_count} words, {content_note})"

    return f"Retrieved {parsed.entity_type}"
