"""
Scheduling — ADR-261 D3 walker over /workspace/_recurrences.yaml.

The scheduler walks the canonical recurrences file per user
(via services.recurrence.walk_workspace_recurrences) and dispatches due
invocations through services.invocation_dispatcher.dispatch.

The `tasks` table is preserved as the Path B thin scheduling index
(per ADR-231 D4): it stores `last_run_at` + `next_run_at` per
(user_id, slug) for scheduler-side CAS atomic claims and fast-path due
queries. Substrate truth is the YAML file; the table is the index.

Per ADR-261 D2 + D3 there is one canonical file
(`/workspace/_recurrences.yaml`); per-shape declaration files are gone.
The `declaration_path` column on tasks now always equals the canonical
RECURRENCES_PATH constant — kept for schema compat and future trace.

Module ownership (per discipline rule 10):
- Owner: scheduling concerns. Sibling to `services.recurrence`
  (YAML schema + walker) and `services.invocation_dispatcher` (firing).
- Consumer: `jobs.unified_scheduler.run_unified_scheduler()`.
- Producer: `services.primitives.schedule` post-write hook (when
  recurrences YAML changes, materialize_scheduling_index re-syncs).

Public surface:

    compute_next_run_at(rec, last_run_at, now) -> Optional[datetime]
        Pure timing math. Uses croniter against rec.schedule.

    materialize_scheduling_index(client, user_id) -> int
        Walk recurrences, upsert thin tasks rows. Idempotent. Drops rows
        whose recurrence no longer exists. Returns count touched.

    get_due_recurrences(client, now=None) -> list[(user_id, Recurrence)]
        Cross-user query: tasks where next_run_at <= now AND active.
        Re-parse each user's `_recurrences.yaml` (truth) and return.

    claim_task_run(client, user_id, slug, original_next_run) -> bool
        CAS atomic claim to prevent duplicate execution.

    record_task_run(client, user_id, recurrence, last_run_at) -> None
        Post-dispatch: write last_run_at + recomputed next_run_at.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from services.conventions import RECURRENCES_PATH
from services.recurrence import (
    Recurrence,
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
    rec: Recurrence,
    last_run_at: Optional[datetime] = None,
    now: Optional[datetime] = None,
    user_timezone: str = DEFAULT_TIMEZONE,
) -> Optional[datetime]:
    """Compute the next firing time for a recurrence.

    Honors `paused` and `paused_until`. Returns None when:
      - recurrence has no schedule (reactive — fires on event, not cron)
      - recurrence is paused with no `paused_until` (indefinite)
      - recurrence's `paused_until` is in the future (still paused)
    """
    if rec.paused:
        if rec.paused_until and (now is None or rec.paused_until > now):
            return rec.paused_until
        return None

    schedule = rec.schedule
    if not schedule:
        return None

    base = last_run_at or now or datetime.now(timezone.utc)
    return _calc_legacy(
        schedule=schedule,
        last_run_at=base,
        user_timezone=user_timezone,
    )


# ---------------------------------------------------------------------------
# materialize_scheduling_index — idempotent recurrences→tasks sync
# ---------------------------------------------------------------------------


async def materialize_scheduling_index(
    client,
    user_id: str,
    *,
    now: Optional[datetime] = None,
) -> int:
    """Sync the `tasks` index against current ``_recurrences.yaml`` content.

    Idempotent. Drops rows whose recurrence was archived (operator-driven
    via Schedule(action='archive')). Schedule changes recompute next_run_at
    from now (preserves last_run_at if present).

    Returns count of rows touched (upserted + deleted).
    """
    if now is None:
        now = datetime.now(timezone.utc)

    recurrences = walk_workspace_recurrences(client, user_id)
    by_slug: dict[str, Recurrence] = {r.slug: r for r in recurrences}

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

    for slug, rec in by_slug.items():
        existing_row = existing_by_slug.get(slug)
        last_run_at_iso = existing_row.get("last_run_at") if existing_row else None
        last_run_at = _parse_iso(last_run_at_iso)

        next_run = compute_next_run_at(
            rec,
            last_run_at=last_run_at,
            now=now,
            user_timezone=user_tz,
        )

        row = {
            "user_id": user_id,
            "slug": slug,
            "status": "active",
            "schedule": rec.schedule,
            "next_run_at": next_run.isoformat() if next_run else None,
            "declaration_path": RECURRENCES_PATH,
            "paused": rec.paused,
        }

        try:
            if existing_row:
                client.table("tasks").update(row).eq(
                    "id", existing_row["id"]
                ).execute()
            else:
                client.table("tasks").insert(row).execute()
            touched += 1
        except Exception as e:
            logger.warning(
                "[SCHED] upsert failed for %s/%s: %s", user_id[:8], slug, e
            )

    # Drop rows whose recurrence no longer exists
    for slug, existing_row in existing_by_slug.items():
        if slug not in by_slug:
            try:
                client.table("tasks").delete().eq(
                    "id", existing_row["id"]
                ).execute()
                touched += 1
                logger.info(
                    "[SCHED] dropped index row for %s/%s (no matching recurrence)",
                    user_id[:8], slug,
                )
            except Exception as e:
                logger.warning(
                    "[SCHED] delete failed for %s/%s: %s", user_id[:8], slug, e
                )

    return touched


# ---------------------------------------------------------------------------
# get_due_recurrences — cross-user query → parsed Recurrences
# ---------------------------------------------------------------------------


async def get_due_recurrences(
    client,
    now: Optional[datetime] = None,
) -> list[tuple[str, Recurrence]]:
    """Return all due ``(user_id, Recurrence)`` pairs.

    Strategy:
      1. Query `tasks` for rows where next_run_at <= now AND status='active'.
      2. For each due row, re-read the user's ``_recurrences.yaml``
         (truth lives in filesystem; the row is the index).
      3. Return parsed recurrences matched by slug.

    A row whose recurrence no longer exists (deleted, stale index) is
    skipped + logged. The next ``materialize_scheduling_index`` call
    cleans up the stale row.
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

    pairs: list[tuple[str, Recurrence]] = []
    rows_by_user: dict[str, list[dict]] = {}
    for row in due_rows:
        rows_by_user.setdefault(row["user_id"], []).append(row)

    for user_id, user_rows in rows_by_user.items():
        recurrences = walk_workspace_recurrences(client, user_id)
        by_slug = {r.slug: r for r in recurrences}
        for row in user_rows:
            slug = row.get("slug")
            rec = by_slug.get(slug)
            if rec is None:
                logger.warning(
                    "[SCHED] due row %s/%s has no matching recurrence; skipping",
                    user_id[:8], slug,
                )
                continue
            if rec.paused:
                continue
            pairs.append((user_id, rec))

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

    Bumps ``next_run_at`` to a +sentinel_hours sentinel only if the row's
    current ``next_run_at`` still equals ``original_next_run``. If another
    instance already claimed, returns False.
    """
    if original_next_run is None:
        logger.warning(
            "[SCHED] refusing to claim %s/%s without baseline next_run_at",
            user_id[:8], slug,
        )
        return False

    sentinel = (
        datetime.now(timezone.utc) + timedelta(hours=sentinel_hours)
    ).isoformat()
    try:
        result = (
            client.table("tasks")
            .update({"next_run_at": sentinel})
            .eq("user_id", user_id)
            .eq("slug", slug)
            .eq("next_run_at", original_next_run)
            .execute()
        )
        return bool(result.data)
    except Exception as e:
        logger.warning("[SCHED] claim failed for %s/%s: %s", user_id[:8], slug, e)
        return False


# ---------------------------------------------------------------------------
# record_task_run — post-dispatch index advance
# ---------------------------------------------------------------------------


def record_task_run(
    client,
    user_id: str,
    recurrence: Recurrence,
    *,
    last_run_at: datetime,
    user_timezone: Optional[str] = None,
) -> None:
    """Write last_run_at + recomputed next_run_at to the thin index
    post-dispatch. Always sets next_run_at — either the next scheduled
    time or None to clear the optimistic sentinel claim_task_run set.
    """
    user_tz = user_timezone or get_user_timezone(client, user_id)
    next_run = compute_next_run_at(
        recurrence,
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
            "slug", recurrence.slug
        ).execute()
    except Exception as e:
        logger.warning(
            "[SCHED] record_task_run update failed for %s/%s: %s",
            user_id[:8], recurrence.slug, e,
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
    "get_due_recurrences",
    "claim_task_run",
    "record_task_run",
]
