"""
Scheduling — ADR-231 Phase 3.3 thin index over recurrence YAML declarations.

The scheduler walks the workspace_files filesystem for recurrence YAML
declarations (per services.recurrence.walk_workspace_recurrences), computes
next-run timing per declaration, and dispatches due invocations through
services.invocation_dispatcher.dispatch.

The `tasks` table is preserved as the Path B thin scheduling index per
ADR-231 D4: it stores `last_run_at` + `next_run_at` per (user_id, slug)
for scheduler-side CAS atomic claims and fast-path due queries. It does
NOT store work substrate — that lives in the YAML declaration at
`declaration_path`.

Module ownership (per discipline rule 10):
- Owner: scheduling concerns. Sibling to `services.recurrence` (YAML schema
  + walker) and `services.invocation_dispatcher` (firing).
- Consumer: `jobs.unified_scheduler.run_unified_scheduler()`.
- Producer: `services.primitives.update_context` post-write hook (when
  recurrence YAML changes, materialize_scheduling_index re-syncs the index).

Public surface:

    compute_next_run_at(decl, last_run_at, now) -> Optional[datetime]
        Pure timing math. Uses croniter against decl.schedule.

    materialize_scheduling_index(client, user_id) -> int
        Walk all declarations for user, upsert thin tasks rows. Idempotent.
        Returns count of rows touched. Drops rows whose declaration no
        longer exists (operator deleted the YAML).

    get_due_declarations(client, now=None) -> list[(user_id, RecurrenceDeclaration)]
        Cross-user query: tasks where next_run_at <= now AND NOT paused.
        For each due row, re-parse the YAML at declaration_path (truth is
        in filesystem). Returns parsed declarations, ready to dispatch.

    claim_task_run(client, user_id, slug, original_next_run) -> bool
        CAS atomic claim: bumps tasks.next_run_at to a +2h sentinel only if
        the row's next_run_at still equals original_next_run. Prevents
        duplicate execution from concurrent scheduler instances.

    record_task_run(client, user_id, slug, last_run_at, next_run_at) -> None
        Post-dispatch: writes last_run_at + next_run_at into the index.

ADR-231 D4 Path B is the locked decision: thin index now, full Path A
(filesystem-only walk per tick) deferred until alpha→beta scale justifies
removing the table. Migration 164 (Phase 3.4) drops mode + essential and
adds declaration_path + paused to formalize the Path B shape.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from services.recurrence import (
    RecurrenceDeclaration,
    parse_recurrence_yaml,
    walk_workspace_recurrences,
)
from services.schedule_utils import (
    DEFAULT_TIMEZONE,
    calculate_next_run_at as _calc_legacy,
    get_user_timezone,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# compute_next_run_at — pure timing math
# ---------------------------------------------------------------------------


def compute_next_run_at(
    decl: RecurrenceDeclaration,
    last_run_at: Optional[datetime] = None,
    now: Optional[datetime] = None,
    user_timezone: str = DEFAULT_TIMEZONE,
) -> Optional[datetime]:
    """Compute the next firing time for a declaration.

    Honors `paused` and `paused_until`. Returns None when:
      - declaration has no schedule (manual-fire only)
      - declaration is paused with no `paused_until` (indefinite pause)
      - declaration's `paused_until` is itself in the future (still paused)

    For active scheduled declarations, delegates to the legacy
    `services.schedule_utils.calculate_next_run_at` which handles cron + dict
    schedule shapes uniformly. The legacy helper is preserved across the
    cutover; only the dispatcher and scheduler perimeters change.
    """
    if decl.paused:
        # Honor paused_until — when set and in the future, return that as
        # the next-eligible time so the index doesn't fire prematurely.
        if decl.paused_until and (now is None or decl.paused_until > now):
            return decl.paused_until
        return None

    schedule = decl.schedule
    if not schedule:
        return None

    base = last_run_at or now or datetime.now(timezone.utc)
    return _calc_legacy(
        schedule=schedule,
        last_run_at=base,
        user_timezone=user_timezone,
    )


# ---------------------------------------------------------------------------
# materialize_scheduling_index — idempotent filesystem→table sync
# ---------------------------------------------------------------------------


async def materialize_scheduling_index(
    client,
    user_id: str,
    *,
    now: Optional[datetime] = None,
) -> int:
    """Sync the `tasks` index against current YAML declarations for a user.

    Walks `walk_workspace_recurrences(client, user_id)` for the authoritative
    set of declarations. For each declaration, upserts a thin row carrying
    `(slug, status, schedule, next_run_at, last_run_at, declaration_path,
     paused)`.

    Drops rows whose declaration no longer exists (operator-driven
    archival via `UpdateContext(target='recurrence', action='archive')`).

    Idempotent: re-running with no YAML changes is a no-op for `next_run_at`
    when last_run_at is unchanged. Schedule changes recompute next_run_at
    from now (preserves last_run_at if present).

    Returns count of rows touched (upserted + deleted). Caller logs;
    failure is best-effort — partial sync is acceptable.

    Migration 164 (Phase 3.4) adds `declaration_path` + `paused` columns;
    until that migration runs, this function writes only the legacy column
    set. The `_TABLE_HAS_DECLARATION_PATH` check is performed lazily via
    a try/except on the first write — Postgres rejects unknown columns.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # 1. Walk YAML declarations
    decls = walk_workspace_recurrences(client, user_id)
    decls_by_slug: dict[str, RecurrenceDeclaration] = {d.slug: d for d in decls}

    # 2. Read existing index rows
    try:
        existing = (
            client.table("tasks")
            .select("id, slug, last_run_at, next_run_at, schedule, status")
            .eq("user_id", user_id)
            .execute()
        )
        existing_by_slug: dict[str, dict] = {
            r["slug"]: r for r in (existing.data or [])
        }
    except Exception as e:
        logger.warning("[SCHED] index read failed for %s: %s", user_id[:8], e)
        return 0

    user_tz = get_user_timezone(client, user_id)
    touched = 0

    # 3. Upsert per declaration
    for slug, decl in decls_by_slug.items():
        existing_row = existing_by_slug.get(slug)
        last_run_at_iso = existing_row.get("last_run_at") if existing_row else None
        last_run_at = _parse_iso(last_run_at_iso)

        next_run = compute_next_run_at(
            decl,
            last_run_at=last_run_at,
            now=now,
            user_timezone=user_tz,
        )

        row: dict = {
            "user_id": user_id,
            "slug": slug,
            "status": "active",  # paused is a separate flag post-migration 164
            "schedule": decl.schedule,
        }
        if next_run is not None:
            row["next_run_at"] = next_run.isoformat()
        else:
            row["next_run_at"] = None

        # Best-effort: include declaration_path + paused if migration 164 has run.
        # Pre-migration these columns don't exist; the upsert falls back below.
        row_with_new_columns = {
            **row,
            "declaration_path": decl.declaration_path,
            "paused": decl.paused,
        }

        try:
            if existing_row:
                # Update existing row — try with new columns first
                try:
                    client.table("tasks").update(row_with_new_columns).eq(
                        "id", existing_row["id"]
                    ).execute()
                except Exception:
                    # Pre-migration 164: retry without unknown columns
                    client.table("tasks").update(row).eq(
                        "id", existing_row["id"]
                    ).execute()
            else:
                # Insert new row
                try:
                    client.table("tasks").insert(row_with_new_columns).execute()
                except Exception:
                    client.table("tasks").insert(row).execute()
            touched += 1
        except Exception as e:
            logger.warning("[SCHED] upsert failed for %s/%s: %s", user_id[:8], slug, e)

    # 4. Delete rows whose declaration no longer exists
    for slug, existing_row in existing_by_slug.items():
        if slug not in decls_by_slug:
            try:
                client.table("tasks").delete().eq("id", existing_row["id"]).execute()
                touched += 1
                logger.info(
                    "[SCHED] dropped index row for %s/%s (no matching declaration)",
                    user_id[:8], slug,
                )
            except Exception as e:
                logger.warning("[SCHED] delete failed for %s/%s: %s", user_id[:8], slug, e)

    return touched


# ---------------------------------------------------------------------------
# get_due_declarations — cross-user due-row query → parsed declarations
# ---------------------------------------------------------------------------


async def get_due_declarations(
    client,
    now: Optional[datetime] = None,
) -> list[tuple[str, RecurrenceDeclaration]]:
    """Return all due (user_id, RecurrenceDeclaration) pairs.

    Strategy:
      1. Query `tasks` for rows where next_run_at <= now AND status='active'.
         (Pre-migration 164: paused rows have status='paused'; post-migration:
          paused rows have paused=true. The status='active' filter handles both.)
      2. For each due row, re-read the YAML at declaration_path and re-parse.
         The YAML is truth; the row is the index.
      3. Return parsed declarations matched by slug.

    A row whose declaration no longer exists (deleted YAML, stale index) is
    skipped + logged. The next `materialize_scheduling_index` call cleans
    up the stale row.

    Returns empty list on error (graceful — caller proceeds with no work).
    """
    if now is None:
        now = datetime.now(timezone.utc)

    try:
        result = (
            client.table("tasks")
            .select("id, user_id, slug, status, schedule, next_run_at, last_run_at")
            .eq("status", "active")
            .lte("next_run_at", now.isoformat())
            .execute()
        )
        due_rows = result.data or []
    except Exception as e:
        logger.debug("[SCHED] due query failed: %s", e)
        return []

    pairs: list[tuple[str, RecurrenceDeclaration]] = []
    # Group by user to amortize the workspace walk
    rows_by_user: dict[str, list[dict]] = {}
    for row in due_rows:
        rows_by_user.setdefault(row["user_id"], []).append(row)

    for user_id, user_rows in rows_by_user.items():
        decls = walk_workspace_recurrences(client, user_id)
        decls_by_slug = {d.slug: d for d in decls}
        for row in user_rows:
            slug = row.get("slug")
            decl = decls_by_slug.get(slug)
            if decl is None:
                logger.warning(
                    "[SCHED] due row %s/%s has no matching YAML declaration; skipping",
                    user_id[:8], slug,
                )
                continue
            if decl.paused:
                # Index didn't catch the pause yet (or migration 164 not run);
                # honor declaration as truth.
                continue
            pairs.append((user_id, decl))

    return pairs


# ---------------------------------------------------------------------------
# CAS atomic claim
# ---------------------------------------------------------------------------


def claim_task_run(
    client,
    user_id: str,
    slug: str,
    original_next_run: Optional[str],
    *,
    sentinel_hours: int = 2,
) -> bool:
    """Atomically claim a due task to prevent duplicate execution.

    Bumps `next_run_at` to a +2h sentinel only if the row's next_run_at
    still equals `original_next_run`. If another scheduler instance already
    claimed this row, the update affects 0 rows and we return False.

    Returns True when this caller is the rightful executor; False when the
    row was already claimed (or the row has gone missing).
    """
    if original_next_run is None:
        # No baseline to CAS against — this is unusual. Refuse to claim.
        logger.warning(
            "[SCHED] refusing to claim %s/%s without baseline next_run_at",
            user_id[:8], slug,
        )
        return False

    sentinel = (datetime.now(timezone.utc) + timedelta(hours=sentinel_hours)).isoformat()
    try:
        result = (
            client.table("tasks")
            .update({"next_run_at": sentinel})
            .eq("user_id", user_id)
            .eq("slug", slug)
            .eq("next_run_at", original_next_run)  # CAS guard
            .execute()
        )
        return bool(result.data)
    except Exception as e:
        logger.warning("[SCHED] claim failed for %s/%s: %s", user_id[:8], slug, e)
        return False


# ---------------------------------------------------------------------------
# Post-dispatch: record run + recompute next_run_at
# ---------------------------------------------------------------------------


def record_task_run(
    client,
    user_id: str,
    decl: RecurrenceDeclaration,
    *,
    last_run_at: datetime,
    user_timezone: Optional[str] = None,
) -> None:
    """Write last_run_at + recomputed next_run_at to the thin index post-dispatch.

    Always sets next_run_at — either to the next scheduled time or None to
    clear the optimistic +2h sentinel claim_task_run set. Without this,
    on-demand/reactive declarations get re-picked when the sentinel expires.
    """
    user_tz = user_timezone or get_user_timezone(client, user_id)
    next_run = compute_next_run_at(
        decl,
        last_run_at=last_run_at,
        now=last_run_at,
        user_timezone=user_tz,
    )
    update = {
        "last_run_at": last_run_at.isoformat(),
        "next_run_at": next_run.isoformat() if next_run else None,
    }
    try:
        client.table("tasks").update(update).eq("user_id", user_id).eq(
            "slug", decl.slug
        ).execute()
    except Exception as e:
        logger.warning(
            "[SCHED] record_task_run update failed for %s/%s: %s",
            user_id[:8], decl.slug, e,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


__all__ = [
    "compute_next_run_at",
    "materialize_scheduling_index",
    "get_due_declarations",
    "claim_task_run",
    "record_task_run",
]
