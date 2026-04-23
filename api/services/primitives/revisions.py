"""
Revision-aware primitives — ADR-209 Phase 3.

Three read-side primitives that surface the Authored Substrate's revision
chain to chat + headless + MCP consumers:

  ListRevisions(path, limit=10)
    Returns the revision chain for a path, newest first. Each entry
    carries (id, authored_by, message, created_at, parent_version_id).
    The bread-and-butter read — "who has edited this file lately?"

  ReadRevision(path, offset=-1 | revision_id=...)
    Returns a specific historical revision's content + metadata.
    Exactly one of {offset, revision_id} must be supplied; offset is
    interpreted as "N revisions ago" (offset=0 → head, offset=-1 →
    previous, etc.).

  DiffRevisions(path, from_rev, to_rev)
    Pure-Python unified diff between two revisions of the same path.
    Deterministic, zero LLM cost. Revisions must refer to the same path.

Plus extensions wired in services/primitives/list.py + workspace.py:

  ListEntities now accepts authored_by / since / until filters
  ListFiles    now accepts authored_by / since / until filters

Handlers route through the read helpers in services/authored_substrate.py.
No new write surface — revision mutations happen only through
write_revision() at the standard write path.

Canonical references:
  - docs/adr/ADR-209-authored-substrate.md (Phase 3 scope)
  - docs/architecture/authored-substrate.md §4 (read-with-provenance)
  - docs/architecture/primitives-matrix.md (mode × capability matrix)
"""

from __future__ import annotations

import difflib
import logging
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# Tool definitions
# =============================================================================

LIST_REVISIONS_TOOL = {
    "name": "ListRevisions",
    "description": """List the revision chain for a workspace file.

Returns every recorded revision for the given path, newest first. Each
entry carries the revision id, authored_by identity (operator | yarnnn |
agent:<slug> | reviewer:<identity> | system:<actor>), a short message,
and a timestamp. Use this to answer questions like "who has edited
MANDATE.md this week?" or "how many times has _performance.md been
reconciled?"

Path is absolute within the workspace filesystem, e.g.:
  /workspace/context/_shared/MANDATE.md
  /agents/alpha-research/AGENT.md
  /tasks/weekly-brief/feedback.md
  /workspace/review/decisions.md

Read-only. Use ReadRevision(path, revision_id=...) to fetch a specific
revision's content, or DiffRevisions(path, from_rev, to_rev) to compare
two revisions.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute workspace path, e.g. '/workspace/context/_shared/MANDATE.md'",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum revisions to return (default 10).",
                "minimum": 1,
                "maximum": 100,
            },
        },
        "required": ["path"],
    },
}


READ_REVISION_TOOL = {
    "name": "ReadRevision",
    "description": """Read a specific historical revision of a workspace file.

Exactly one of {offset, revision_id} must be supplied:
  - offset=-1 → previous revision (one before current head)
  - offset=-N → N revisions ago
  - offset=0  → current head (same as ReadFile)
  - revision_id → a specific revision UUID (from ListRevisions)

Returns the revision's content plus its attribution metadata
(authored_by, message, created_at, parent_version_id). Use this to
inspect prior states — e.g. "what did MANDATE.md look like before the
operator's last edit" or "show me the reviewer's reasoning from three
decisions ago."

Path is absolute within the workspace filesystem.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute workspace path",
            },
            "offset": {
                "type": "integer",
                "description": "Revisions to walk back from head (0=head, -1=previous, -N=N ago). Mutually exclusive with revision_id.",
            },
            "revision_id": {
                "type": "string",
                "description": "UUID of a specific revision (from ListRevisions). Mutually exclusive with offset.",
            },
        },
        "required": ["path"],
    },
}


DIFF_REVISIONS_TOOL = {
    "name": "DiffRevisions",
    "description": """Compare two revisions of the same workspace file.

Returns a unified text diff between from_rev and to_rev. Deterministic,
zero LLM cost. Both revisions must refer to the same path.

Use this to answer questions like "what changed in MANDATE.md between
the operator's last two edits" or "how did the reviewer's principles
evolve over the past week." Typical flow: ListRevisions(path) →
choose two revision ids → DiffRevisions(path, from_rev, to_rev).

Revisions can be passed as:
  - revision UUID (from ListRevisions)
  - offset integer (0=head, -1=previous, -N=N ago)""",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute workspace path",
            },
            "from_rev": {
                "description": "Starting revision — UUID string OR integer offset (0=head, -1=previous)",
                "oneOf": [{"type": "string"}, {"type": "integer"}],
            },
            "to_rev": {
                "description": "Target revision — UUID string OR integer offset",
                "oneOf": [{"type": "string"}, {"type": "integer"}],
            },
        },
        "required": ["path", "from_rev", "to_rev"],
    },
}


# =============================================================================
# Handlers
# =============================================================================


async def handle_list_revisions(auth: Any, input: dict) -> dict:
    """ListRevisions primitive handler."""
    from services.authored_substrate import list_revisions

    path = input.get("path") or ""
    if not path:
        return {"success": False, "error": "missing_path", "message": "path is required"}

    limit = input.get("limit") or 10
    try:
        limit = max(1, min(100, int(limit)))
    except (TypeError, ValueError):
        limit = 10

    try:
        revisions = list_revisions(
            auth.client,
            user_id=auth.user_id,
            path=path,
            limit=limit,
        )
    except Exception as e:
        logger.warning(f"[LIST_REVISIONS] failed for {path}: {e}")
        return {"success": False, "error": "query_failed", "message": str(e)}

    return {
        "success": True,
        "path": path,
        "count": len(revisions),
        "revisions": revisions,  # newest first — each has id, authored_by, message, created_at, parent_version_id
    }


def _resolve_revision_ref(
    client: Any,
    user_id: str,
    path: str,
    ref: Any,
):
    """Resolve a revision reference (UUID string or integer offset) to a Revision.

    Returns the Revision object (with content) or None if the ref can't
    be resolved. Raises ValueError on malformed input.
    """
    from services.authored_substrate import read_revision

    if isinstance(ref, int):
        # offset-based
        return read_revision(client, user_id=user_id, path=path, offset=ref)
    if isinstance(ref, str):
        # UUID
        if not ref:
            raise ValueError("empty revision reference")
        return read_revision(client, user_id=user_id, path=path, revision_id=ref)
    raise ValueError(f"revision reference must be int offset or UUID string, got {type(ref).__name__}")


async def handle_read_revision(auth: Any, input: dict) -> dict:
    """ReadRevision primitive handler."""
    from services.authored_substrate import read_revision

    path = input.get("path") or ""
    if not path:
        return {"success": False, "error": "missing_path", "message": "path is required"}

    offset = input.get("offset")
    revision_id = input.get("revision_id") or None

    if offset is not None and revision_id is not None:
        return {
            "success": False,
            "error": "ambiguous_reference",
            "message": "Provide exactly one of {offset, revision_id}, not both.",
        }

    try:
        if revision_id:
            rev = read_revision(
                auth.client,
                user_id=auth.user_id,
                path=path,
                revision_id=revision_id,
            )
        else:
            offset_val = int(offset) if offset is not None else 0
            rev = read_revision(
                auth.client,
                user_id=auth.user_id,
                path=path,
                offset=offset_val,
            )
    except ValueError as e:
        return {"success": False, "error": "invalid_input", "message": str(e)}
    except Exception as e:
        logger.warning(f"[READ_REVISION] failed for {path}: {e}")
        return {"success": False, "error": "query_failed", "message": str(e)}

    if rev is None:
        return {
            "success": False,
            "error": "revision_not_found",
            "message": f"No revision found for {path} (offset={offset}, revision_id={revision_id})",
        }

    return {
        "success": True,
        "path": path,
        "revision": {
            "id": rev.id,
            "authored_by": rev.authored_by,
            "author_identity_uuid": rev.author_identity_uuid,
            "message": rev.message,
            "created_at": str(rev.created_at) if rev.created_at else None,
            "parent_version_id": rev.parent_version_id,
            "blob_sha": rev.blob_sha,
            "content": rev.content,
        },
    }


async def handle_diff_revisions(auth: Any, input: dict) -> dict:
    """DiffRevisions primitive handler. Pure-Python unified diff."""
    path = input.get("path") or ""
    if not path:
        return {"success": False, "error": "missing_path", "message": "path is required"}

    from_ref = input.get("from_rev")
    to_ref = input.get("to_rev")
    if from_ref is None or to_ref is None:
        return {
            "success": False,
            "error": "missing_refs",
            "message": "Both from_rev and to_rev are required.",
        }

    try:
        from_rev = _resolve_revision_ref(auth.client, auth.user_id, path, from_ref)
        to_rev = _resolve_revision_ref(auth.client, auth.user_id, path, to_ref)
    except ValueError as e:
        return {"success": False, "error": "invalid_input", "message": str(e)}
    except Exception as e:
        logger.warning(f"[DIFF_REVISIONS] resolution failed for {path}: {e}")
        return {"success": False, "error": "query_failed", "message": str(e)}

    if from_rev is None or to_rev is None:
        return {
            "success": False,
            "error": "revision_not_found",
            "message": f"One or both revisions not found for {path}",
        }

    from_content = from_rev.content or ""
    to_content = to_rev.content or ""

    # Unified diff — 3 lines of context by default, enough for operator legibility.
    diff_lines = list(
        difflib.unified_diff(
            from_content.splitlines(keepends=True),
            to_content.splitlines(keepends=True),
            fromfile=f"{path}@{from_rev.id[:8]}",
            tofile=f"{path}@{to_rev.id[:8]}",
            n=3,
        )
    )
    diff_text = "".join(diff_lines)

    return {
        "success": True,
        "path": path,
        "from": {
            "id": from_rev.id,
            "authored_by": from_rev.authored_by,
            "message": from_rev.message,
            "created_at": str(from_rev.created_at) if from_rev.created_at else None,
        },
        "to": {
            "id": to_rev.id,
            "authored_by": to_rev.authored_by,
            "message": to_rev.message,
            "created_at": str(to_rev.created_at) if to_rev.created_at else None,
        },
        "diff": diff_text,
        "identical": from_rev.blob_sha == to_rev.blob_sha,
    }
