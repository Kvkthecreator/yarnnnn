"""Workspace deletion — the lifecycle (ADR-578).

Three verbs, one vocabulary shared with ADR-478's file-scoped delete:

    delete  → soft: `deleted_at` set. Every byte retained. Hidden + unreachable.
    restore → clears `deleted_at`. A column write; nothing to rebuild.
    purge   → terminal. Content destroyed; financial history preserved (D5).

## Why a raw DELETE was never an option

Probed on production 2026-08-18: of 22 FKs referencing `workspaces`, only 11
CASCADE. Ten are `NO ACTION`, so Postgres REFUSES to delete any workspace that
has ever been used —

    ERROR: update or delete on table "workspaces" violates foreign key
    constraint "execution_events_workspace_id_fkey"

— while a freshly-created (empty) workspace deletes cleanly. A "just add a
delete button" implementation therefore passes its own test and 500s for every
real operator. `purge_workspace` clears the blocking tables in dependency order
before deleting the row, which is the entire reason this module exists.

## No timer, deliberately

The conventional SaaS shape is soft-delete → grace period → scheduled hard
purge. We take the first two and REFUSE the third: ADR-478 D2 already ruled that
"a 30-day timer is the system deleting a member's work with nobody witnessing
it" (ADR-405's witness dial). A deleted workspace stays deleted until a
principal finishes the job. The grace period is real; its END is an act.

Adding a scheduler here later would re-introduce, at workspace scope, exactly
the decision canon refused at file scope — and would be the second delete
vocabulary this module exists to avoid.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


class WorkspaceDeleteError(Exception):
    """A delete/restore/purge was refused. Message is operator-safe."""


# The ten `NO ACTION` tables, in FK-dependency order (children before parents).
# A raw DELETE on workspaces is refused while ANY of these hold a row, so this
# list is not housekeeping — it is the precondition for the final delete.
#
# ⚠️ Ordering is load-bearing: agent_runs references agents, action_proposals
# and execution_events reference runs. Reordering this list reintroduces the
# very FK violation the module exists to clear.
_BLOCKING_TABLES = (
    "action_proposals",
    "execution_events",
    "agent_runs",
    "agents",
    "wake_queue",
    "tasks",
    "chat_sessions",
    "activity_log",
    "sync_registry",
    "platform_connections",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _owned_live_workspaces(client: Any, user_id: str) -> list:
    """Live (non-deleted) workspaces this principal owns, oldest-first."""
    rows = (
        client.table("workspaces")
        .select("id, name, deleted_at")
        .eq("owner_id", user_id)
        .order("created_at", desc=False)
        .execute()
    ).data or []
    return [r for r in rows if not r.get("deleted_at")]


def other_principals(client: Any, workspace_id: str, owner_id: str) -> list:
    """The principals who LOSE ACCESS if this workspace is deleted (D4).

    ADR-405's witness dial: the operator is not prevented from ending a shared
    commons, but they may not do it without being shown who it lands on. The
    confirmation names these; a generic "this cannot be undone" would hide the
    only fact that makes the act heavy.
    """
    rows = (
        client.table("principal_grants")
        .select("principal_id, role")
        .eq("workspace_id", workspace_id)
        .eq("status", "active")
        .execute()
    ).data or []
    others = [r for r in rows if str(r.get("principal_id")) != str(owner_id)]

    # Name them. The docstring above is the reason: this list is "the only fact
    # that makes the act heavy", and a raw UUID hides that fact as effectively
    # as omitting the list would — the card rendered `a3f9c1e2-… (member)`.
    # Best-effort by contract: an unresolved id simply keeps its raw value, and
    # a lookup failure never breaks the delete preview.
    try:
        from services.principal_display import resolve_member_names

        names = resolve_member_names(
            client, [str(r.get("principal_id")) for r in others]
        )
        for r in others:
            label = names.get(str(r.get("principal_id")))
            if label:
                r["label"] = label
    except Exception as exc:  # noqa: BLE001 — humanization is best-effort
        logger.debug("[WORKSPACE_DELETE] principal naming failed: %s", exc)

    return others


def soft_delete_workspace(client: Any, user_id: str, workspace_id: str) -> dict:
    """Mark a workspace deleted (D1). Reversible; destroys nothing.

    Refuses the caller's LAST owned live workspace (D3): deleting it would drop
    them into the cold-user door, which mints a replacement (ADR-465 D2) — so
    the act would read as "my workspace was silently replaced with an empty
    one" rather than as a deletion.
    """
    row = (
        client.table("workspaces")
        .select("id, name, owner_id, deleted_at")
        .eq("id", workspace_id)
        .limit(1)
        .execute()
    ).data or []
    if not row:
        raise WorkspaceDeleteError("Workspace not found")
    ws = row[0]
    if ws.get("deleted_at"):
        raise WorkspaceDeleteError("This workspace is already deleted")

    live = _owned_live_workspaces(client, user_id)
    if len(live) <= 1 and any(w["id"] == workspace_id for w in live):
        raise WorkspaceDeleteError(
            "This is your only workspace. Create another one first — deleting "
            "your last workspace would immediately mint a replacement."
        )

    updated = (
        client.table("workspaces")
        .update({"deleted_at": _now(), "deleted_by": user_id})
        .eq("id", workspace_id)
        .execute()
    ).data or []
    if not updated:
        raise WorkspaceDeleteError("Could not delete this workspace")

    _clear_owner_cache()
    logger.info("[ADR-578] %s soft-deleted workspace %s", user_id, workspace_id)
    return {"workspace_id": workspace_id, "name": ws.get("name"), "deleted": True}


def restore_workspace(client: Any, user_id: str, workspace_id: str) -> dict:
    """Undo a soft delete (D1). A column write — nothing is rebuilt."""
    updated = (
        client.table("workspaces")
        .update({"deleted_at": None, "deleted_by": None})
        .eq("id", workspace_id)
        .execute()
    ).data or []
    if not updated:
        raise WorkspaceDeleteError("Could not restore this workspace")
    _clear_owner_cache()
    logger.info("[ADR-578] %s restored workspace %s", user_id, workspace_id)
    return {"workspace_id": workspace_id, "restored": True}


def purge_workspace(client: Any, user_id: str, workspace_id: str) -> dict:
    """Terminal delete (D1 second act). Content destroyed, ledger preserved.

    Order is the whole function:
      1. the ADR-476 content purge (files, revisions, blobs) — reused verbatim,
         not reimplemented, so content deletion has ONE implementation.
      2. the ten `NO ACTION` tables, children first — without this the final
         DELETE is refused by Postgres.
      3. the row. `balance_transactions` / `subscription_events` are SET NULL
         (migration 242), so financial history survives with `workspace_ref`
         still naming its origin; every other FK cascades its content away.

    Requires the workspace to be soft-deleted first: purge is the SECOND act,
    never a shortcut past the reversible one.
    """
    row = (
        client.table("workspaces")
        .select("id, name, owner_id, deleted_at")
        .eq("id", workspace_id)
        .limit(1)
        .execute()
    ).data or []
    if not row:
        raise WorkspaceDeleteError("Workspace not found")
    if not row[0].get("deleted_at"):
        raise WorkspaceDeleteError(
            "Delete this workspace before purging it — purge is permanent."
        )

    deleted: dict = {}

    # 1. Content, through the SINGLE existing implementation (ADR-476).
    try:
        from services.workspace_purge import purge_l2_workspace

        # ADR-578: pass the workspace BEING purged. Without it the content
        # phase re-resolved the caller's home workspace while phases 2 and 3
        # used this argument — so purging any non-home workspace wiped the
        # wrong one's files.
        deleted.update(purge_l2_workspace(client, user_id, workspace_id))
    except Exception as exc:  # noqa: BLE001 — continue to the blocking sweep
        logger.warning("[ADR-578] content purge partial for %s: %s", workspace_id, exc)

    # 2. The blocking tables. Ordering is load-bearing (see _BLOCKING_TABLES).
    for table in _BLOCKING_TABLES:
        try:
            res = (
                client.table(table).delete().eq("workspace_id", workspace_id).execute()
            )
            n = len(res.data or [])
            if n:
                deleted[table] = deleted.get(table, 0) + n
        except Exception as exc:  # noqa: BLE001 — a missing table is not fatal
            logger.debug("[ADR-578] purge skip %s: %s", table, exc)

    # 3. The row itself. Financial FKs are SET NULL (mig 242); the rest cascade.
    try:
        client.table("workspaces").delete().eq("id", workspace_id).execute()
    except Exception as exc:
        # A surviving FK reference means _BLOCKING_TABLES is incomplete — say so
        # loudly rather than reporting a purge that did not happen.
        raise WorkspaceDeleteError(
            f"Workspace could not be fully purged (a reference survives): {exc}"
        )

    _clear_owner_cache()
    logger.info("[ADR-578] %s PURGED workspace %s (%s)", user_id, workspace_id, deleted)
    return {"workspace_id": workspace_id, "purged": True, "deleted": deleted}


def _clear_owner_cache() -> None:
    """Drop the memoized owner→workspace mapping.

    `_resolve_owner_workspace_id_cached` is an lru_cache; a delete/restore/purge
    changes which workspaces a principal owns, and a stale entry would resolve a
    deleted workspace as someone's home.
    """
    try:
        from services.supabase import _resolve_owner_workspace_id_cached

        _resolve_owner_workspace_id_cached.cache_clear()
    except Exception:  # pragma: no cover — best-effort
        pass
