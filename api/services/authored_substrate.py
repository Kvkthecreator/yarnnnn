"""
Authored Substrate — ADR-209 (Phase 1)

The substrate-level commitment that every mutation to workspace_files is
attributed, purposeful, and retained. Three of git's five capabilities
implemented natively in Postgres:
  - content-addressed retention (workspace_blobs table)
  - parent-pointer history (workspace_file_versions.parent_version_id)
  - authored-by attribution (authored_by + message columns)

Branching and distributed replication deferred as cheaply-recoverable
extensions — see docs/architecture/authored-substrate.md §7.

PHASE 1 STATUS (this PR): additive foundation only. This module exposes
write_revision() and helper read functions, but no call sites in the
codebase route through it yet. Phase 2 (next PR) migrates every existing
write path (AgentWorkspace.write, KnowledgeBase.write, TaskWorkspace.write,
UserMemory.write, reviewer_audit.append_decision, etc.) to use this
module, and deletes the /history/ subfolder convention (ADR-119 Phase 3).

Do not import write_revision from application code yet — Phase 2 will
add the call-site migration as one coherent PR. The function exists
now so Phase 1 can ship the substrate foundation + backfill + tests
without touching live write paths.

Canonical references:
  - docs/architecture/authored-substrate.md (design rationale)
  - docs/adr/ADR-209-authored-substrate.md (decision record)
  - supabase/migrations/158_adr209_authored_substrate.sql (schema)
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Authored-by taxonomy
# ---------------------------------------------------------------------------
#
# authored_by is a prefixed string. The prefix maps to a FOUNDATIONS Axiom 2
# cognitive layer plus a system:* namespace for deterministic actors. The
# write path validates only that the string is non-empty — the taxonomy
# here is a reference for call-site code, not a hard constraint.
#
# Examples:
#   operator
#   yarnnn:claude-sonnet-4-7
#   agent:alpha-research
#   specialist:writer
#   reviewer:human
#   reviewer:ai-sonnet-v1
#   system:outcome-reconciliation
#   system:workspace-cleanup
#   system:backfill-158

VALID_AUTHOR_PREFIXES = (
    "operator",
    "yarnnn:",
    "agent:",
    "specialist:",
    "reviewer:",
    "system:",
)


def is_valid_author(authored_by: str) -> bool:
    """Return True if the authored_by string starts with a known prefix.

    This is a soft check for call-site validation — the DB enforces only
    non-emptiness. Useful for caller-side linting and the primitive
    contract test that Phase 2 introduces.
    """
    if not authored_by:
        return False
    if authored_by == "operator":
        return True
    return any(authored_by.startswith(p) for p in VALID_AUTHOR_PREFIXES if p.endswith(":"))


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Revision:
    """A single revision record — the unit of Authored Substrate.

    Mirrors a row in workspace_file_versions joined with workspace_blobs.
    """
    id: str
    user_id: str
    path: str
    blob_sha: str
    parent_version_id: Optional[str]
    authored_by: str
    author_identity_uuid: Optional[str]
    message: str
    created_at: datetime
    content: Optional[str] = None  # populated when joined with workspace_blobs


# ---------------------------------------------------------------------------
# Core write path (the singular substrate mutation function)
# ---------------------------------------------------------------------------

def _sha256(content: str) -> str:
    """Compute hex sha256 of content (utf-8 encoded)."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _upsert_blob(db_client: Any, sha: str, content: str) -> None:
    """Insert a blob if not already present. Content-addressed by sha256.

    Uses ON CONFLICT DO NOTHING semantics via the Supabase client's upsert.
    Identical content across workspaces shares a single blob — this is the
    content-addressed dedup property.
    """
    # The Supabase Python client's upsert uses the table's primary key as
    # the conflict target by default. sha256 is the PK, so this is
    # idempotent by construction.
    db_client.table("workspace_blobs").upsert(
        {"sha256": sha, "content": content},
        on_conflict="sha256",
    ).execute()


def _read_head_revision_id(db_client: Any, user_id: str, path: str) -> Optional[str]:
    """Return the current (newest) revision id for (user_id, path), or None.

    Authoritative source: workspace_file_versions ordered by created_at DESC.
    The denormalized workspace_files.head_version_id pointer is a Phase 2
    read-optimization layer kept in sync by the full write path; the
    revision chain itself is the source of truth for "what is the most
    recent revision" and therefore for "what is the next write's parent."
    """
    result = (
        db_client.table("workspace_file_versions")
        .select("id")
        .eq("user_id", user_id)
        .eq("path", path)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    return result.data[0]["id"]


def _insert_revision(
    db_client: Any,
    *,
    user_id: str,
    path: str,
    blob_sha: str,
    parent_version_id: Optional[str],
    authored_by: str,
    author_identity_uuid: Optional[str],
    message: str,
) -> str:
    """Insert one revision row, return the new revision id."""
    row = {
        "user_id": user_id,
        "path": path,
        "blob_sha": blob_sha,
        "parent_version_id": parent_version_id,
        "authored_by": authored_by,
        "author_identity_uuid": author_identity_uuid,
        "message": message,
    }
    result = (
        db_client.table("workspace_file_versions")
        .insert(row)
        .execute()
    )
    if not result.data:
        raise RuntimeError(
            f"[AUTHORED_SUBSTRATE] Failed to insert revision for {user_id}:{path}"
        )
    return result.data[0]["id"]


def write_revision(
    db_client: Any,
    *,
    user_id: str,
    path: str,
    content: str,
    authored_by: str,
    message: str,
    author_identity_uuid: Optional[str] = None,
) -> str:
    """The single write path for every substrate mutation.

    Semantics:
      1. Compute sha256 of content; upsert workspace_blobs.
      2. Read the newest revision for (user_id, path) from the revision
         chain; becomes the new revision's parent_version_id (NULL if
         this path has no prior revision).
      3. Insert workspace_file_versions row with authored_by + message.

    Phase 2 will additionally update workspace_files.head_version_id +
    content + updated_at in the same transaction — so that the
    denormalized pointer + content columns on workspace_files stay in
    sync with the revision chain for read-path performance. That
    migration is intentionally deferred so Phase 1 doesn't touch live
    write paths. Phase 1 usage of write_revision() is limited to tests
    and the backfill context; parent resolution already works correctly
    because it queries workspace_file_versions directly, not the
    denormalized pointer.

    Returns the new revision id.

    Raises:
      ValueError — if authored_by or message is empty.
      RuntimeError — if the revision insert fails.

    Note on atomicity: Supabase client does not expose a multi-statement
    transaction helper in the same way raw psycopg does. Phase 2 will
    introduce a single RPC (stored function) that performs blob upsert +
    revision insert + workspace_files sync atomically in one call. For
    Phase 1, the three-step sequence here is acceptable because no live
    call sites yet rely on atomicity — only tests and the backfill, both
    of which run in controlled contexts.
    """
    if not authored_by or not authored_by.strip():
        raise ValueError("authored_by is required and must be non-empty")
    if not message or not message.strip():
        raise ValueError("message is required and must be non-empty")

    sha = _sha256(content)
    _upsert_blob(db_client, sha, content)

    parent_version_id = _read_head_revision_id(db_client, user_id, path)

    new_revision_id = _insert_revision(
        db_client,
        user_id=user_id,
        path=path,
        blob_sha=sha,
        parent_version_id=parent_version_id,
        authored_by=authored_by,
        author_identity_uuid=author_identity_uuid,
        message=message,
    )

    logger.debug(
        f"[AUTHORED_SUBSTRATE] wrote revision {new_revision_id} for "
        f"{user_id}:{path} by {authored_by} (parent={parent_version_id})"
    )

    return new_revision_id


# ---------------------------------------------------------------------------
# Read helpers (primitive-facing versions land in Phase 3)
# ---------------------------------------------------------------------------

def list_revisions(
    db_client: Any,
    *,
    user_id: str,
    path: str,
    limit: int = 10,
) -> list[dict]:
    """Return the revision chain for (user_id, path), newest first.

    Each entry: {id, authored_by, message, created_at, parent_version_id}.
    Content is NOT fetched — use read_revision() for that.

    Phase 3 wraps this in a ListRevisions primitive exposed to chat +
    headless + MCP.
    """
    result = (
        db_client.table("workspace_file_versions")
        .select("id, authored_by, author_identity_uuid, message, created_at, parent_version_id")
        .eq("user_id", user_id)
        .eq("path", path)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return list(result.data or [])


def read_revision(
    db_client: Any,
    *,
    user_id: str,
    path: str,
    revision_id: Optional[str] = None,
    offset: Optional[int] = None,
) -> Optional[Revision]:
    """Read a specific revision's content.

    Exactly one of {revision_id, offset} should be provided:
      - revision_id: the UUID of the revision to read
      - offset: integer, -1 = previous revision, -2 = two ago, etc.
                0 (and positive) treated as "no offset — read head"

    Returns None if the requested revision doesn't exist.

    Phase 3 wraps this in a ReadRevision primitive exposed to chat +
    headless + MCP.
    """
    if revision_id is not None and offset is not None:
        raise ValueError("Specify revision_id OR offset, not both")

    # Resolve to a concrete revision id first
    target_id: Optional[str] = revision_id

    if target_id is None:
        # Offset-based lookup: walk the chain from newest backward
        walk_back = 0 if offset is None else max(0, -offset)
        revisions = list_revisions(
            db_client,
            user_id=user_id,
            path=path,
            limit=walk_back + 1,
        )
        if len(revisions) <= walk_back:
            return None
        target_id = revisions[walk_back]["id"]

    # Fetch the full revision with content joined from workspace_blobs
    result = (
        db_client.table("workspace_file_versions")
        .select("id, user_id, path, blob_sha, parent_version_id, "
                "authored_by, author_identity_uuid, message, created_at, "
                "workspace_blobs(content)")
        .eq("id", target_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None

    row = result.data[0]
    blob = row.get("workspace_blobs") or {}
    content = blob.get("content") if isinstance(blob, dict) else None

    return Revision(
        id=row["id"],
        user_id=row["user_id"],
        path=row["path"],
        blob_sha=row["blob_sha"],
        parent_version_id=row.get("parent_version_id"),
        authored_by=row["authored_by"],
        author_identity_uuid=row.get("author_identity_uuid"),
        message=row["message"],
        created_at=row["created_at"],
        content=content,
    )


def count_revisions(db_client: Any, *, user_id: str, path: str) -> int:
    """Return the total number of revisions for (user_id, path)."""
    result = (
        db_client.table("workspace_file_versions")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("path", path)
        .execute()
    )
    return result.count or 0
