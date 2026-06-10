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
) -> int:
    """Delete all rows in a user-scoped table. Returns count deleted."""
    try:
        count_result = (
            client.table(table)
            .select("*", count="exact")
            .eq(user_column, user_id)
            .execute()
        )
        count = count_result.count or 0
        if count > 0:
            client.table(table).delete().eq(user_column, user_id).execute()
        return count
    except Exception as e:
        if optional and _is_missing_relation_error(e):
            return 0
        if optional:
            logger.warning(f"[PURGE] Optional delete failed for {table}: {e}")
            return 0
        raise


def _delete_workspace_files(client: Any, user_id: str, path_prefix: str | None = None) -> int:
    """Delete workspace_files rows, optionally filtered by path prefix."""
    try:
        query = (
            client.table("workspace_files")
            .select("*", count="exact")
            .eq("user_id", user_id)
        )
        if path_prefix:
            query = query.like("path", f"{path_prefix}%")
        count_result = query.execute()
        count = count_result.count or 0
        if count > 0:
            dq = client.table("workspace_files").delete().eq("user_id", user_id)
            if path_prefix:
                dq = dq.like("path", f"{path_prefix}%")
            dq.execute()
        return count
    except Exception as e:
        logger.warning(f"[PURGE] workspace_files delete failed (prefix={path_prefix}): {e}")
        return 0


def _null_head_version_pointers(client: Any, user_id: str) -> None:
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
            client.table("workspace_files")
            .update({"head_version_id": None})
            .eq("user_id", user_id)
            .execute()
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
    what they chose to clear). The slug lives as a marker in the MANDATE.md first
    heading (`# Mandate — {slug}`); `parse_active_program_slug` returns None for
    any other heading shape, and `_all_slugs()` validates it's a real bundle.

    Best-effort: a failure here is non-fatal (returns None — operator can
    re-activate from the Workspace tab), never a correctness invariant.
    """
    try:
        from services.workspace import UserMemory
        from services.workspace_paths import CONSTITUTION_MANDATE_PATH
        from services.programs import parse_active_program_slug
        from services.bundle_reader import _all_slugs

        um = UserMemory(client, user_id)
        mandate_pre = await um.read(CONSTITUTION_MANDATE_PATH)
        candidate = parse_active_program_slug(mandate_pre)
        if candidate and candidate in _all_slugs():
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

    # ADR-209 FK order: workspace_files.head_version_id → workspace_file_versions.id.
    # Null the pointer first so revisions can be wiped without violating the FK;
    # then wipe the revision chain; then wipe the files.
    _null_head_version_pointers(client, user_id)
    deleted["workspace_file_versions"] = _delete_rows(client, "workspace_file_versions", user_id)

    # Workspace filesystem — the primary data store
    deleted["workspace_files"] = _delete_workspace_files(client, user_id)

    # Relational tables referencing agents/tasks
    deleted["tasks"] = _delete_rows(client, "tasks", user_id, optional=True)
    deleted["agents"] = _delete_rows(client, "agents", user_id)
    # ADR-194 Reviewer proposal queue — prior proposals must not survive reset
    deleted["action_proposals"] = _delete_rows(client, "action_proposals", user_id)
    deleted["chat_sessions"] = _delete_rows(client, "chat_sessions", user_id)
    deleted["activity_log"] = _delete_rows(client, "activity_log", user_id)
    deleted["event_trigger_log"] = _delete_rows(client, "event_trigger_log", user_id, optional=True)
    deleted["notifications"] = _delete_rows(client, "notifications", user_id, optional=True)
    # ADR-298 wake queue — transient Reviewer-execution compute. `user_id` is NOT
    # FK-cascaded to auth.users (RLS service-role-only, transient by design), so it
    # survives a workspace wipe unless purged explicitly. Stale `pending` rows would
    # otherwise drain a Reviewer wake against substrate that no longer exists.
    deleted["wake_queue"] = _delete_rows(client, "wake_queue", user_id, optional=True)
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

        reinit_summary = await initialize_workspace(
            client, user_id, program_slug=prior_program_slug
        )
        logger.info(
            f"[PURGE] User {user_id} reinit after clear: "
            f"{len(reinit_summary.get('agents_created', []))} agents, "
            f"program={reinit_summary.get('activated_program')}"
        )
    except Exception as reinit_err:  # noqa: BLE001
        logger.error(f"[PURGE] Workspace reinit after clear failed for {user_id}: {reinit_err}")

    return {
        "deleted": deleted,
        "prior_program_slug": prior_program_slug,
        "reinit_summary": reinit_summary,
    }
