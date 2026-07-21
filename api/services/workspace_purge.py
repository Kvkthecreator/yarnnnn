"""
Workspace purge — the single L2 clear-workspace implementation.

Extracted from `routes/account.py::clear_workspace` so there is exactly ONE
body for the L2 ("clear workspace") purge + reinit sequence, callable from
two entry points:

  - the JWT-scoped HTTP route `DELETE /api/account/workspace` (operator clears
    their own workspace), and
  - the service key (a soak/eval harness clean-slating a chosen persona by
    user_id, with no JWT available — the route alone cannot reach another
    operator's workspace).

Before this module existed, the second entry point was served by COPYING the
purge logic into one-shot scripts (e.g. `scripts/oneshot/adr281_e2e_purge_
reinit_kvk.py`, whose helpers are literally docstringed "Mirror of
routes/account.py::_delete_rows"). That copy is the Singular-Implementation
drift this module retires.

The mechanical DB helpers (`_delete_rows`, `_delete_workspace_files`,
`_null_head_version_pointers`) live here now; `routes/account.py` imports them
back so L1/L3/L4 keep their single implementation too. Routes-importing-from-
services is the correct direction; services-importing-from-routes was the smell.

Scope boundary: this module owns the **L2** sequence (workspace-scoped wipe —
preserves `execution_events`, `platform_connections`, `user_admin_flags`,
notification prefs). The **L4** full-account-reset in `routes/account.py` is a
genuinely broader operation (account-scoped, resets the `workspaces` row) and
keeps its own delete sequence; it shares only the program-capture +
reinit pieces, which are factored here as `capture_active_program_slug()`.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Scope spine (ADR-476 D1)
# =============================================================================
#
# The substrate's binding unit is the WORKSPACE (ADR-373, ADR-474). Purge kept
# deleting by `user_id` because the ADR-373 read sweep never reached it — so in
# a multi-member workspace "clear everything" quietly meant "clear the rows I
# happened to author", and a member's content was unreachable by any purge.
#
# This mirrors `authored_substrate._substrate_scope` exactly rather than
# inventing a second rule: prefer `workspace_id` when it resolves, fall back to
# `user_id` (byte-identical at N=1, where a workspace's rows and its owner's
# rows are the same set).


def _purge_scope(query: Any, user_id: str, workspace_id: Optional[str]) -> Any:
    """Scope a purge query to the workspace, falling back to the user at N=1."""
    if workspace_id:
        return query.eq("workspace_id", workspace_id)
    return query.eq("user_id", user_id)


def resolve_purge_workspace(user_id: str) -> Optional[str]:
    """The workspace a purge for this user acts on.

    Uses the same resolution spine as every read path (ADR-373). Best-effort:
    None falls the callers back to `user_id` scoping, which is today's behavior
    and correct at N=1 — a purge must never be blocked by a resolution failure.
    """
    try:
        from services.workspace_context import effective_workspace_id

        return effective_workspace_id(user_id, None)
    except Exception as exc:  # noqa: BLE001 — best-effort by design
        logger.warning(f"[PURGE] workspace resolve failed for {user_id}: {exc}")
        return None


# =============================================================================
# Mechanical DB helpers (relocated from routes/account.py — single home)
# =============================================================================

def _is_missing_relation_error(error: Exception) -> bool:
    message = str(error).lower()
    return "relation" in message and "does not exist" in message


def _delete_rows(
    client: Any,
    table: str,
    user_id: str,
    *,
    user_column: str = "user_id",
    optional: bool = False,
    workspace_id: Optional[str] = None,
) -> int:
    """Delete all rows in a scoped table. Returns count deleted.

    ADR-476 D1: when `workspace_id` is supplied AND the table carries that
    column, the delete is workspace-scoped — it reaches every member's rows,
    not only the purging user's. Callers pass it for the workspace-scoped
    tables and omit it for genuinely user-scoped ones (a member's own MCP
    OAuth tokens are theirs, not the workspace's).
    """
    scoped = workspace_id is not None and user_column == "user_id"
    try:
        base = client.table(table).select("*", count="exact")
        count_result = (
            _purge_scope(base, user_id, workspace_id)
            if scoped
            else base.eq(user_column, user_id)
        ).execute()
        count = count_result.count or 0
        if count > 0:
            dq = client.table(table).delete()
            (
                _purge_scope(dq, user_id, workspace_id)
                if scoped
                else dq.eq(user_column, user_id)
            ).execute()
        return count
    except Exception as e:
        if optional and _is_missing_relation_error(e):
            return 0
        if optional:
            logger.warning(f"[PURGE] Optional delete failed for {table}: {e}")
            return 0
        raise


def _delete_workspace_files(
    client: Any,
    user_id: str,
    path_prefix: str | None = None,
    workspace_id: Optional[str] = None,
) -> int:
    """Delete workspace_files rows, optionally filtered by path prefix.

    ADR-476 D1: workspace-scoped — reaches every member's files, not only the
    purging user's.
    """
    try:
        query = _purge_scope(
            client.table("workspace_files").select("*", count="exact"),
            user_id,
            workspace_id,
        )
        if path_prefix:
            query = query.like("path", f"{path_prefix}%")
        count_result = query.execute()
        count = count_result.count or 0
        if count > 0:
            dq = _purge_scope(
                client.table("workspace_files").delete(), user_id, workspace_id
            )
            if path_prefix:
                dq = dq.like("path", f"{path_prefix}%")
            dq.execute()
        return count
    except Exception as e:
        logger.warning(f"[PURGE] workspace_files delete failed (prefix={path_prefix}): {e}")
        return 0


def _collect_blob_shas(
    client: Any, user_id: str, workspace_id: Optional[str] = None
) -> list[tuple[str, str]]:
    """The (workspace_id, sha256) pairs this WORKSPACE's revisions cite.

    ADR-474. Must run BEFORE the revision chain is deleted: the revisions are
    the only thing that names the content. Read from the revision rows rather
    than from `workspace_blobs` directly so the scope is exactly "content this
    workspace's substrate cites" — never another workspace's rows.

    ADR-476 D1 fixes an ADR-474 regression: this filtered `.eq("user_id", …)`,
    so it collected only the PURGING USER's content and left every other
    member's blobs behind. ADR-474 made purge able to reach content; this makes
    it reach the workspace's content.
    """
    try:
        rows = (
            _purge_scope(
                client.table("workspace_file_versions").select(
                    "workspace_id, blob_sha"
                ),
                user_id,
                workspace_id,
            ).execute()
        ).data or []
        return sorted({
            (r["workspace_id"], r["blob_sha"])
            for r in rows
            if r.get("workspace_id") and r.get("blob_sha")
        })
    except Exception as e:  # noqa: BLE001 — never block the purge
        logger.warning(f"[PURGE] blob sha collection failed for {user_id}: {e}")
        return []


def _delete_workspace_blobs(
    client: Any, user_id: str, blob_shas: list[tuple[str, str]]
) -> int:
    """Collect the content the purged revisions cited (ADR-474 §4).

    Routes through the storage seam so the bucket object is removed alongside
    the row — deleting only the row would strand the object unreachably, since
    the `storage_key` lives nowhere else.

    Best-effort per blob: a failure leaves that row behind (collectable later,
    reachable via its workspace) rather than aborting the purge. The composite
    FK is the safety net — a blob any surviving revision still cites cannot be
    deleted at all.
    """
    if not blob_shas:
        return 0
    try:
        from services.storage_backend import get_storage_backend

        backend = get_storage_backend(client)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[PURGE] storage backend unavailable, blobs kept: {e}")
        return 0

    removed = 0
    for workspace_id, sha in blob_shas:
        try:
            if backend.delete_blob(sha, workspace_id=workspace_id):
                removed += 1
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[PURGE] blob delete failed for {sha[:12]}: {e}")
    logger.info(
        f"[PURGE] collected {removed}/{len(blob_shas)} blobs for user {user_id}"
    )
    return removed


def _null_head_version_pointers(
    client: Any, user_id: str, workspace_id: Optional[str] = None
) -> None:
    """Null out `workspace_files.head_version_id` before wiping
    `workspace_file_versions`.

    ADR-209 added `workspace_files.head_version_id → workspace_file_versions.id`
    as a FK without ON DELETE semantics. Deleting the revision first violates the
    constraint; deleting files first violates the inverse relationship. Correct
    order: null pointers → delete revisions → delete files. No-op when the user
    has no rows. Swallows errors (best-effort) because the subsequent delete will
    surface the real constraint violation if something is still wrong.
    """
    try:
        (
            _purge_scope(
                client.table("workspace_files").update({"head_version_id": None}),
                user_id,
                workspace_id,
            ).execute()
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[PURGE] null head_version_id failed for {user_id}: {e}")


# =============================================================================
# Shared L2/L4 pieces
# =============================================================================

async def capture_active_program_slug(client: Any, user_id: str) -> Optional[str]:
    """Read the active program slug from the operator's MANDATE.md, validated
    against the bundle registry. Returns None when no program is active.

    ADR-244 D4: the operator's *choice* of program survives an L2/L4 purge so the
    reinit can re-fork the bundle. Their authored content does not (it's part of
    what they chose to clear). ADR-414 D5: the choice is recorded as the HIRE
    GRANT ROW (principal_grants, role='own-agent'), which survives a file purge
    by construction; `resolve_hired_program_slug` validates against the registry.

    Best-effort: a failure here is non-fatal (returns None — operator can
    re-activate from the Workspace tab), never a correctness invariant.
    """
    try:
        from services.programs import resolve_hired_program_slug

        # ADR-414 D5: the activation record is the hire grant row (which
        # survives an L2 file purge by construction — grants are not files).
        candidate = resolve_hired_program_slug(user_id)
        if candidate:
            logger.info(
                f"[PURGE] User {user_id} — captured active program for re-fork: {candidate}"
            )
            return candidate
    except Exception as pre_err:  # noqa: BLE001
        logger.warning(f"[PURGE] program capture failed for {user_id}: {pre_err}")
    return None


# =============================================================================
# L2 purge sequence + the composed clear-workspace entry point
# =============================================================================

def purge_l2_workspace(client: Any, user_id: str) -> dict[str, int]:
    """The L2 ("clear workspace") purge sequence — workspace-scoped wipe.

    Verbatim port of `routes/account.py::clear_workspace` Phase 1, preserving
    the ADR-209 FK ordering (null head pointers → revisions → files) and the
    ADR-298 wake_queue purge (transient compute, no auth cascade — stale
    `pending` rows would otherwise drain a Reviewer wake against substrate that
    no longer exists after reinit).

    PRESERVES (L2 invariant): platform_connections, user_admin_flags,
    user_notification_preferences, execution_events (cost ledger — L4 only).

    Returns the per-table deleted-count dict.
    """
    deleted: dict[str, int] = {}

    # ADR-476 D1: resolve the workspace ONCE and scope every workspace-scoped
    # delete to it. Without this, a purge in a multi-member workspace deletes
    # only the rows the purging user happened to author — the workspace reports
    # "cleared" and every other member's files survive.
    ws = resolve_purge_workspace(user_id)
    logger.info(f"[PURGE] L2 for user {user_id} scoped to workspace {ws or '(N=1 fallback)'}")

    # ADR-209 FK order: workspace_files.head_version_id → workspace_file_versions.id.
    # Null the pointer first so revisions can be wiped without violating the FK;
    # then wipe the revision chain; then wipe the files.
    #
    # ADR-474: capture the workspace's blob addresses BEFORE the revisions that
    # cite them are deleted — afterwards nothing points at them and the content
    # would be unreachable (the leak this ADR closes).
    blob_shas = _collect_blob_shas(client, user_id, ws)

    _null_head_version_pointers(client, user_id, ws)
    deleted["workspace_file_versions"] = _delete_rows(
        client, "workspace_file_versions", user_id, workspace_id=ws
    )

    # Workspace filesystem — the primary data store
    deleted["workspace_files"] = _delete_workspace_files(client, user_id, workspace_id=ws)

    # ADR-474: the content layer. Runs AFTER the revisions are gone — the
    # composite FK (workspace_id, blob_sha) refuses to drop a blob any surviving
    # revision still cites, which is what makes this safe independent of the
    # ordering above. Deletes the bucket object too (the storage_key lives only
    # on the row), and only when this workspace is the content address's last
    # owner.
    deleted["workspace_blobs"] = _delete_workspace_blobs(client, user_id, blob_shas)

    # Relational tables referencing agents/tasks. ADR-476 D1: these all carry a
    # `workspace_id` (verified populated, 0 NULLs live), so they scope to the
    # workspace — a member's agents/sessions/activity are the workspace's, not
    # the purging user's private rows.
    deleted["tasks"] = _delete_rows(client, "tasks", user_id, optional=True, workspace_id=ws)
    deleted["agents"] = _delete_rows(client, "agents", user_id, workspace_id=ws)
    # ADR-194 Reviewer proposal queue — prior proposals must not survive reset
    deleted["action_proposals"] = _delete_rows(
        client, "action_proposals", user_id, workspace_id=ws
    )
    deleted["chat_sessions"] = _delete_rows(client, "chat_sessions", user_id, workspace_id=ws)
    deleted["activity_log"] = _delete_rows(client, "activity_log", user_id, workspace_id=ws)
    # ADR-298 wake queue — transient Reviewer-execution compute. `user_id` is NOT
    # FK-cascaded to auth.users (RLS service-role-only, transient by design), so it
    # survives a workspace wipe unless purged explicitly. Stale `pending` rows would
    # otherwise drain a Reviewer wake against substrate that no longer exists.
    deleted["wake_queue"] = _delete_rows(
        client, "wake_queue", user_id, optional=True, workspace_id=ws
    )

    # ADR-476 D1: genuinely USER-scoped — these have no `workspace_id` column and
    # should not acquire one. A member's notifications and MCP OAuth tokens are
    # THEIRS (ADR-431: an AI connection belongs to the member who authorized it);
    # clearing the workspace must not revoke another member's connectors.
    deleted["event_trigger_log"] = _delete_rows(client, "event_trigger_log", user_id, optional=True)
    deleted["notifications"] = _delete_rows(client, "notifications", user_id, optional=True)
    # MCP OAuth tokens — user's active MCP sessions should not survive a workspace clear
    for table in ("mcp_oauth_codes", "mcp_oauth_access_tokens", "mcp_oauth_refresh_tokens"):
        deleted[table] = _delete_rows(client, table, user_id, optional=True)

    return deleted


async def clear_workspace_for_user(client: Any, user_id: str) -> dict:
    """The single L2 clear-workspace implementation: capture program → purge →
    reinit. Both the HTTP route and the harness call this; there is no second
    body.

    Returns a summary dict:
        {
          "deleted": {<table>: <count>, ...},
          "prior_program_slug": <slug or None>,
          "reinit_summary": {<initialize_workspace result>},
        }

    The reinit (`initialize_workspace`, which is already a singular service
    function) restores fresh-account invariants + re-forks the captured program
    per ADR-244 D4. A reinit failure is logged but does not raise — the purge
    succeeded, and the lazy init path in `GET /api/workspace/state` remains a
    safety net.
    """
    # ADR-244 D4: capture BEFORE purge so we can re-fork the bundle during reinit.
    prior_program_slug = await capture_active_program_slug(client, user_id)

    deleted = purge_l2_workspace(client, user_id)
    logger.info(f"[PURGE] User {user_id} cleared workspace: {deleted}")

    reinit_summary: dict = {}
    try:
        from services.workspace_init import initialize_workspace

        # ADR-414 D4: genesis is pure — it never forks. The ADR-244 D4
        # re-fork is the CALLER's post-genesis act (the same seam the
        # activation endpoint uses), keeping "activation is a hire" true
        # even on the reinit path.
        reinit_summary = await initialize_workspace(client, user_id)
        if prior_program_slug:
            try:
                from services.programs import fork_reference_workspace

                fork_summary = await fork_reference_workspace(
                    client, user_id, prior_program_slug
                )
                reinit_summary["activated_program"] = prior_program_slug
                reinit_summary["fork_files_written"] = fork_summary.get(
                    "files_written", []
                )
            except Exception as fork_err:  # noqa: BLE001
                logger.error(
                    f"[PURGE] Program re-fork after clear failed for "
                    f"{user_id} (program={prior_program_slug}): {fork_err}"
                )
                reinit_summary["fork_error"] = str(fork_err)
        logger.info(
            f"[PURGE] User {user_id} reinit after clear: "
            f"{len(reinit_summary.get('workspace_files_seeded', []))} files, "
            f"program={reinit_summary.get('activated_program')}"
        )
    except Exception as reinit_err:  # noqa: BLE001
        logger.error(f"[PURGE] Workspace reinit after clear failed for {user_id}: {reinit_err}")

    return {
        "deleted": deleted,
        "prior_program_slug": prior_program_slug,
        "reinit_summary": reinit_summary,
    }
