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
    "description": """Look up a database-backed entity by reference. Returns the full row.

This is the ENTITY LAYER primitive — the agent OS's `/proc` (ADR-322). It
operates on the relational abstraction (typed refs like agent:uuid) over
genuinely-non-file DB records, NOT on the filesystem. For file reads (including
uploaded documents at uploads/{slug}.md), use ReadFile (path-based).

IMPORTANT: Use the exact `ref` value returned by SearchEntities or ListEntities. The ref contains a UUID, not a filename.

Examples:
- LookupEntity(ref="agent:latest") - most recent agent
- LookupEntity(ref="platform:slack") - platform connection by provider name
- LookupEntity(ref="session:uuid-123") - a chat session
- LookupEntity(ref="version:uuid-123") - an agent run (run ledger)

Reference format: <type>:<UUID>
Types (ADR-322 /proc core): agent, platform, session, version.
NOT entities (use the file family / Schedule instead):
- documents → ReadFile('uploads/{slug}.md') (they are files, ADR-197)
- tasks/recurrences → ReadFile of the YAML + Schedule (ADR-231)""",
    "input_schema": {
        "type": "object",
        "properties": {
            "ref": {
                "type": "string",
                "description": "Entity reference from SearchEntities/ListEntities results (e.g., 'agent:abc12345-uuid'). Must use UUID, not filename."
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

    # ADR-322 D2: `task` and `document` are no longer entity types — but a model
    # may still try LookupEntity(ref="task:..."/"document:..."). Catch those
    # prefixes BEFORE parse_ref raises "Unknown entity type" and steer to the
    # right primitive (the helpful redirect ADR-322 preserves).
    if ref_str.startswith("task:"):
        ident = ref_str.split(":", 1)[1].split("/", 1)[0].split("?", 1)[0]
        hint = (
            f"`task` is no longer an entity type (ADR-231/322). Work lives in "
            f"recurrence YAML at natural-home paths — check "
            f"/workspace/operation/{{domain}}/_recurring.yaml (accumulation), "
            f"/workspace/operation/reports/{ident}/_spec.yaml (deliverable), "
            f"/workspace/operation/operations/{ident}/_action.yaml (action), "
            f"or /workspace/_shared/back-office.yaml (maintenance). Use ListFiles "
            f"or ReadFile with the path; for scheduling/status use "
            f"Schedule(slug='{ident}', action='...')."
        )
        return {"success": False, "error": "not_an_entity_type", "message": hint, "ref": ref_str, "retry_hint": hint}
    if ref_str.startswith("document:"):
        hint = (
            "`document` is no longer an entity type (ADR-322) — uploaded documents "
            "are files. Use SearchFiles(scope='workspace', path_prefix='uploads/') "
            "to find them and ReadFile('uploads/{slug}.md') to read them."
        )
        return {"success": False, "error": "not_an_entity_type", "message": hint, "ref": ref_str, "retry_hint": hint}

    try:
        parsed = parse_ref(ref_str)

        # Ergonomic guard: agent refs must be UUIDs (or 'latest'/'*'). If caller
        # passed a slug-looking identifier, return a targeted hint instead of
        # letting Postgres explode with "invalid input syntax for type uuid".
        if parsed.entity_type == "agent" and parsed.identifier not in {"*", "latest", "current", "new"}:
            import re as _re
            _UUID_RE = _re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", _re.IGNORECASE)
            if not _UUID_RE.match(parsed.identifier):
                hint = (
                    f"'{parsed.identifier}' looks like a slug, not a UUID. "
                    f"For agent content, use ReadFile(path='/agents/{parsed.identifier}/AGENT.md'). "
                    f"For the entity row, pass the id from ListEntities(pattern='agent:*')."
                )
                return {
                    "success": False,
                    "error": "slug_not_uuid",
                    "message": hint,
                    "ref": ref_str,
                    "retry_hint": hint,
                }

        data = await resolve_ref(parsed, auth)

        if data is None:
            # Provide retry hint based on entity type
            # (ADR-196: "memory" retired — memory is filesystem-native;
            # agents/YARNNN read /workspace/*.md directly via ReadFile.)
            if parsed.entity_type == "agent":
                retry_hint = "Use ListEntities(pattern='agent:*') to see available agents."
            else:
                retry_hint = f"Use SearchEntities or ListEntities to find valid {parsed.entity_type} refs."

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
