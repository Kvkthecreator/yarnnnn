"""
Authored Substrate — ADR-209 (Phase 2)

The substrate-level commitment that every mutation to workspace_files is
attributed, purposeful, and retained. Three of git's five capabilities
implemented natively in Postgres:
  - content-addressed retention (workspace_blobs table)
  - parent-pointer history (workspace_file_versions.parent_version_id)
  - authored-by attribution (authored_by + message columns)

Branching and distributed replication deferred as cheaply-recoverable
extensions — see docs/architecture/authored-substrate.md §7.

PHASE 2 STATUS: the singular write path. write_revision() is the ONE
function every workspace_files mutation routes through. It:
  1. Upserts the content as a content-addressed blob
  2. Reads the current newest revision for (user_id, path); becomes
     the new revision's parent_version_id
  3. Inserts a revision row with required authored_by + message
  4. Upserts workspace_files with head_version_id set to the new
     revision, plus content / updated_at / optional metadata columns

Every direct workspace_files INSERT/UPDATE/UPSERT at the content layer
has been removed — callers MUST go through write_revision(). The
Phase 2 grep gate (api/test_adr209_phase2.py) enforces this.

NOT routed through write_revision (by design):
  - workspace_files.delete() — deletion is a distinct operation;
    ephemeral cleanup + account wipe are the only legitimate uses
  - workspace_files.embedding updates (metadata-only, no content change)
  - workspace_files.metadata-only updates that do NOT mutate content

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
#   operator-proxy:claude-sonnet-4-7:acting-as-alpha-trader-2
#   operator-proxy:scenario-runner:acting-as-kvk
#   operator-proxy:external:chatgpt-5:acting-as-yarnnn-author
#
# ADR-294 D2: operator-proxy:* sub-namespace names the operator's voice
# materialized by a non-human caller — Claude running scenarios, future
# MCP-as-operator callers (ADR-169 thesis), scripted scenario players,
# and workspace-delegated agents. The role is operator-voice; the
# identity is the proxy. Audit trail stays interpretable about who
# *really* did what.

VALID_AUTHOR_PREFIXES = (
    "operator",
    "operator-proxy:",  # ADR-294 D2
    "yarnnn:",
    "agent:",
    "specialist:",
    "reviewer:",
    "system:",
    # ADR-303 D2/D6 (2026-05-26): dispatcher-synthesized substrate writes
    # that fill posture-cell side-effect contracts on the Reviewer's
    # behalf when the model exits without producing the substrate itself
    # (P3 tried-was-gated narrative entries, P4 budget-exhausted
    # standing_intent, P5 text-only-mid-loop standing_intent). Distinct
    # from `reviewer:` so future evaluations can tell model-authored
    # substrate from dispatcher-slot-filled substrate at the attribution
    # layer — the distinction the reverted hotfix 9e7c1c7 conflated.
    "dispatcher:",
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
    workspace_id: Optional[str] = None,
) -> str:
    """Insert one revision row, return the new revision id.

    ADR-373: ``workspace_id`` is dual-written alongside ``user_id`` when the
    caller supplies it (resolved once via ``AuthenticatedClient``). Omitted →
    NULL, which migration 189's backfill / a later write fills; in N=1 the
    column is redundant with ``user_id`` (one user owns one workspace), so the
    write is byte-identical whether or not ``workspace_id`` is passed.
    """
    row = {
        "user_id": user_id,
        "path": path,
        "blob_sha": blob_sha,
        "parent_version_id": parent_version_id,
        "authored_by": authored_by,
        "author_identity_uuid": author_identity_uuid,
        "message": message,
    }
    if workspace_id is not None:
        row["workspace_id"] = workspace_id
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


def _upsert_workspace_file(
    db_client: Any,
    *,
    user_id: str,
    path: str,
    content: str,
    head_version_id: str,
    summary: Optional[str] = None,
    tags: Optional[list[str]] = None,
    lifecycle: Optional[str] = None,
    content_type: Optional[str] = None,
    content_url: Optional[str] = None,
    metadata: Optional[dict] = None,
    workspace_id: Optional[str] = None,
) -> None:
    """Upsert the workspace_files row to reflect the new head revision.

    Carries the denormalized content + head pointer + optional metadata
    columns. Idempotent via ON CONFLICT (user_id, path).

    ADR-373: ``workspace_id`` is dual-written when supplied (see
    ``_insert_revision``). The ON CONFLICT target stays ``(user_id, path)``
    during Phase 1 — the existing UNIQUE constraint is unchanged; in N=1
    ``(workspace_id, path)`` is 1:1 with it, so conflict semantics are
    identical. (A later phase moves the conflict target once code is fully off
    ``user_id``.)
    """
    from datetime import datetime, timezone

    data = {
        "user_id": user_id,
        "path": path,
        "content": content,
        "head_version_id": head_version_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if workspace_id is not None:
        data["workspace_id"] = workspace_id
    if summary is not None:
        data["summary"] = summary
    if tags is not None:
        data["tags"] = tags
    if lifecycle is not None:
        data["lifecycle"] = lifecycle
    if content_type is not None:
        data["content_type"] = content_type
    if content_url is not None:
        data["content_url"] = content_url
    if metadata is not None:
        data["metadata"] = metadata

    db_client.table("workspace_files").upsert(
        data,
        on_conflict="user_id,path",
    ).execute()


def write_revision(
    db_client: Any,
    *,
    user_id: str,
    path: str,
    content: str,
    authored_by: str,
    message: str,
    author_identity_uuid: Optional[str] = None,
    summary: Optional[str] = None,
    tags: Optional[list[str]] = None,
    lifecycle: Optional[str] = None,
    content_type: Optional[str] = None,
    content_url: Optional[str] = None,
    metadata: Optional[dict] = None,
    workspace_id: Optional[str] = None,
) -> str:
    """The single write path for every substrate mutation.

    Semantics (Phase 2 — complete):
      1. Compute sha256 of content; upsert workspace_blobs.
      2. Read the newest revision for (user_id, path) from the revision
         chain; becomes the new revision's parent_version_id (NULL if
         this path has no prior revision).
      3. Insert workspace_file_versions row with authored_by + message.
      4. Upsert workspace_files with head_version_id = new revision id,
         plus denormalized content + updated_at + optional metadata
         columns.

    Every caller in the codebase MUST route through this function. Direct
    INSERT/UPDATE/UPSERT against workspace_files at the content layer is
    disallowed — the Phase 2 grep gate enforces it.

    Metadata-only updates (e.g., embedding refresh, metadata JSONB
    tweaks that don't change content) can update workspace_files
    directly — they don't mutate substrate content and shouldn't
    produce a revision. Likewise, deletions use workspace_files.delete()
    directly.

    Returns the new revision id.

    Raises:
      ValueError — if authored_by or message is empty.
      RuntimeError — if the revision insert fails.

    Note on atomicity: the four-step sequence is not wrapped in a single
    transaction — Supabase's Python client doesn't expose one-shot
    multi-statement transactions the way raw psycopg does. In practice
    the operations are independent and idempotent: a failure between
    step 3 and step 4 leaves a revision row without a head pointer
    update, which is reconciled by the next write to the same path
    (the next write's parent_version_id resolution reads the newest
    revision, which is the orphan — and then the workspace_files upsert
    advances the head past it). The orphan revision remains in the
    chain and is walkable, which is the substrate invariant we care
    about. A future optimization may introduce a stored procedure to
    collapse the sequence, but it is not required for correctness.
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
        workspace_id=workspace_id,
    )

    _upsert_workspace_file(
        db_client,
        user_id=user_id,
        path=path,
        content=content,
        head_version_id=new_revision_id,
        summary=summary,
        tags=tags,
        lifecycle=lifecycle,
        content_type=content_type,
        content_url=content_url,
        metadata=metadata,
        workspace_id=workspace_id,
    )

    logger.debug(
        f"[AUTHORED_SUBSTRATE] wrote revision {new_revision_id} for "
        f"{user_id}:{path} by {authored_by} (parent={parent_version_id})"
    )

    return new_revision_id


def delete_live_file(
    db_client: Any,
    *,
    user_id: str,
    path: str,
    authored_by: str,
    message: str,
    workspace_id: Optional[str] = None,
) -> Optional[str]:
    """Remove a file from the live view with an attributed tombstone (ADR-337 D2).

    Two steps, both attributed:
      1. Insert a tombstone revision carrying the file's CURRENT blob (no new
         blob) — the chain records who deleted, when, why, and what the
         content was at deletion time.
      2. Delete the workspace_files live row (the operation ADR-209 already
         sanctions for deletions; this helper makes it attributed).

    Deletion is a view change, not information loss: ListRevisions /
    ReadRevision query the chain, not the live row, so the full history
    (including the tombstone) survives. Restore is the canonical ADR-209 D7
    revert-as-write: read a prior revision, write it back.

    Returns the tombstone revision id, or None when the path has no live row.
    Raises ValueError on empty authored_by/message (same contract as
    write_revision).
    """
    if not authored_by or not authored_by.strip():
        raise ValueError("authored_by is required and must be non-empty")
    if not message or not message.strip():
        raise ValueError("message is required and must be non-empty")

    live = (
        db_client.table("workspace_files")
        .select("id, content")
        .eq("user_id", user_id)
        .eq("path", path)
        .limit(1)
        .execute()
    ).data or []
    if not live:
        return None

    current_content = live[0].get("content") or ""
    sha = _sha256(current_content)
    # The blob almost certainly exists (it backs the head revision), but
    # upsert is idempotent and covers legacy rows that predate the chain.
    _upsert_blob(db_client, sha, current_content)
    parent_version_id = _read_head_revision_id(db_client, user_id, path)

    tombstone_id = _insert_revision(
        db_client,
        user_id=user_id,
        path=path,
        blob_sha=sha,
        parent_version_id=parent_version_id,
        authored_by=authored_by,
        author_identity_uuid=None,
        message=message,
        workspace_id=workspace_id,
    )

    db_client.table("workspace_files").delete().eq(
        "user_id", user_id
    ).eq("path", path).execute()

    logger.info(
        f"[AUTHORED_SUBSTRATE] deleted live file {user_id}:{path} by "
        f"{authored_by} (tombstone={tombstone_id}; revisions retained)"
    )
    return tombstone_id


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

    # Fetch the full revision with content joined from workspace_blobs.
    # Defense-in-depth (ADR-310 follow-on): filter by user_id even though
    # target_id is a PK. A caller-supplied revision_id (now reachable via the
    # MCP-exposed ReadRevision/DiffRevisions primitives) must not be able to
    # read another workspace's revision content by UUID. Same-workspace reads
    # are unaffected; a foreign revision_id returns None (not found).
    result = (
        db_client.table("workspace_file_versions")
        .select("id, user_id, path, blob_sha, parent_version_id, "
                "authored_by, author_identity_uuid, message, created_at, "
                "workspace_blobs(content)")
        .eq("id", target_id)
        .eq("user_id", user_id)
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
