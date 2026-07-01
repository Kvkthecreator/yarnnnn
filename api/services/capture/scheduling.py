"""
Capture scheduling (ADR-393) — the capture lane's slice of the `tasks` index.

The decision (ADR-393 §4-Q2): the capture lane REUSES the thin `tasks`
scheduling index (ADR-231 D4) rather than a sibling table — one index, one
CAS-claim mechanism, one market-context resolver. A `kind` column (migration
193) discriminates:

    kind = 'judgment'  →  a recurrence   (services.scheduling / services.wake)
    kind = 'capture'   →  a capture       (THIS module / services.capture.lane)

This module mirrors `services.scheduling` but capture-scoped: it materializes
capture rows, queries due capture rows, and (via the drainer wiring in
`unified_scheduler`) advances them. It reuses `compute_next_run_at` from
`services.scheduling` — a CaptureDeclaration is structurally compatible with
what that helper reads (`slug`, `schedule`, `paused`, `paused_until`,
`options`), including ADR-268 semantic market-anchored schedules and ADR-270
`fire_on_activation`.

Kind-disjointness invariant: the two materializers write DISJOINT row sets
(recurrence slugs live in _recurrences.yaml, capture slugs in _captures.yaml).
Each materializer only deletes stale rows OF ITS OWN KIND, so they never
clobber each other. `_recurrences.yaml` and `_captures.yaml` are single-writer
per ADR-286; a slug appearing in both is an authoring error the operator owns.

Backward-safety: if the `kind` column is not yet present (migration 193 not
applied), the capture writers degrade to no-op-safe behavior and the recurrence
path is byte-identical to today (all rows read as judgment). The branch is
mergeable before the migration runs.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from services.capture.declarations import CaptureDeclaration, walk_workspace_captures
from services.conventions import CAPTURES_PATH
from services.scheduling import compute_next_run_at, _parse_iso
from services.schedule_utils import get_user_timezone

logger = logging.getLogger(__name__)

CAPTURE_KIND = "capture"


async def materialize_capture_index(
    client,
    user_id: str,
    *,
    now: Optional[datetime] = None,
) -> int:
    """Sync the `tasks` index (kind='capture' rows) against ``_captures.yaml``.

    Idempotent. Drops capture rows whose declaration no longer exists. Only
    touches kind='capture' rows — recurrence rows are untouched. Returns count
    of rows touched.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    declarations = walk_workspace_captures(client, user_id)
    by_slug: dict[str, CaptureDeclaration] = {d.slug: d for d in declarations}

    # Read only this workspace's CAPTURE rows. Selecting `kind` explicitly so a
    # pre-migration DB (no column) fails the select and we degrade to "no
    # existing capture rows" — the inserts below will also fail gracefully and
    # be logged, but the recurrence path is never touched.
    try:
        existing = (
            client.table("tasks")
            .select("id, slug, last_run_at, next_run_at, schedule, status, kind")
            .eq("user_id", user_id)
            .eq("kind", CAPTURE_KIND)
            .execute()
        )
        existing_by_slug: dict[str, dict] = {
            r["slug"]: r for r in (existing.data or [])
        }
    except Exception as e:
        logger.warning(
            "[CAPTURE_SCHED] index read failed for %s (kind column may be absent "
            "pre-migration-193): %s", user_id[:8], e,
        )
        return 0

    user_tz = get_user_timezone(client, user_id)
    from services.bundle_reader import get_market_context_for_user
    market_context = get_market_context_for_user(user_id, client)
    touched = 0

    for slug, decl in by_slug.items():
        existing_row = existing_by_slug.get(slug)
        last_run_at = _parse_iso(existing_row.get("last_run_at") if existing_row else None)

        try:
            next_run = compute_next_run_at(
                decl,
                last_run_at=last_run_at,
                now=now,
                user_timezone=user_tz,
                market_context=market_context,
            )
        except ValueError as e:
            logger.error(
                "[CAPTURE_SCHED] %s/%s schedule resolution failed: %s",
                user_id[:8], slug, e,
            )
            next_run = None

        if isinstance(decl.schedule, list):
            schedule_persist: Optional[str] = json.dumps(decl.schedule)
        else:
            schedule_persist = decl.schedule

        row = {
            "user_id": user_id,
            "slug": slug,
            "status": "active",
            "kind": CAPTURE_KIND,
            "schedule": schedule_persist,
            "next_run_at": next_run.isoformat() if next_run else None,
            "declaration_path": CAPTURES_PATH,
            "paused": decl.paused,
        }

        try:
            if existing_row:
                client.table("tasks").update(row).eq("id", existing_row["id"]).execute()
            else:
                client.table("tasks").insert(row).execute()
            touched += 1
        except Exception as e:
            logger.warning(
                "[CAPTURE_SCHED] upsert failed for %s/%s: %s", user_id[:8], slug, e
            )

    # Drop capture rows whose declaration no longer exists.
    for slug, existing_row in existing_by_slug.items():
        if slug not in by_slug:
            try:
                client.table("tasks").delete().eq("id", existing_row["id"]).execute()
                touched += 1
                logger.info(
                    "[CAPTURE_SCHED] dropped capture index row for %s/%s (no matching declaration)",
                    user_id[:8], slug,
                )
            except Exception as e:
                logger.warning(
                    "[CAPTURE_SCHED] delete failed for %s/%s: %s", user_id[:8], slug, e
                )

    return touched


async def get_due_captures(
    client,
    now: Optional[datetime] = None,
) -> list[tuple[str, CaptureDeclaration]]:
    """Return all due ``(user_id, CaptureDeclaration)`` pairs (kind='capture').

    Queries `tasks` for kind='capture' rows with next_run_at <= now AND active,
    then re-reads each user's ``_captures.yaml`` (truth) and matches by slug.
    Mirrors ``services.scheduling.get_due_recurrences`` capture-side.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    try:
        result = (
            client.table("tasks")
            .select("id, user_id, slug, status, schedule, next_run_at, last_run_at, kind")
            .eq("status", "active")
            .eq("kind", CAPTURE_KIND)
            .lte("next_run_at", now.isoformat())
            .execute()
        )
        due_rows = result.data or []
    except Exception as e:
        logger.debug("[CAPTURE_SCHED] due query failed (kind column may be absent): %s", e)
        return []

    rows_by_user: dict[str, list[dict]] = {}
    for row in due_rows:
        rows_by_user.setdefault(row["user_id"], []).append(row)

    pairs: list[tuple[str, CaptureDeclaration]] = []
    for user_id, user_rows in rows_by_user.items():
        declarations = walk_workspace_captures(client, user_id)
        by_slug = {d.slug: d for d in declarations}
        for row in user_rows:
            slug = row.get("slug")
            decl = by_slug.get(slug)
            if decl is None:
                logger.warning(
                    "[CAPTURE_SCHED] due row %s/%s has no matching declaration; skipping",
                    user_id[:8], slug,
                )
                continue
            if decl.paused:
                continue
            pairs.append((user_id, decl))

    return pairs


def claim_capture_run(
    client,
    user_id: str,
    slug: str,
    original_next_run: Optional[str],
    *,
    sentinel_hours: int = 2,
) -> bool:
    """CAS atomic claim for a due capture row (kind-scoped). Same mechanism as
    ``services.scheduling.claim_task_run`` but bounded to kind='capture' so a
    recurrence and a same-named capture (authoring error) can't cross-claim."""
    if original_next_run is None:
        logger.warning(
            "[CAPTURE_SCHED] refusing to claim %s/%s without baseline next_run_at",
            user_id[:8], slug,
        )
        return False

    from datetime import timedelta
    sentinel = (datetime.now(timezone.utc) + timedelta(hours=sentinel_hours)).isoformat()
    try:
        result = (
            client.table("tasks")
            .update({"next_run_at": sentinel})
            .eq("user_id", user_id)
            .eq("slug", slug)
            .eq("kind", CAPTURE_KIND)
            .eq("next_run_at", original_next_run)
            .execute()
        )
        return bool(result.data)
    except Exception as e:
        logger.warning("[CAPTURE_SCHED] claim failed for %s/%s: %s", user_id[:8], slug, e)
        return False


def record_capture_run(
    client,
    user_id: str,
    declaration: CaptureDeclaration,
    *,
    last_run_at: datetime,
    user_timezone: Optional[str] = None,
) -> None:
    """Write last_run_at + recomputed next_run_at to the capture row post-run.

    Always sets next_run_at (clears the CAS sentinel) — the next scheduled time,
    or None. Honors ADR-270 fire_on_activation via compute_next_run_at's
    last_run_at handling. Kind-scoped update so it never touches a recurrence row.
    """
    user_tz = user_timezone or get_user_timezone(client, user_id)
    from services.bundle_reader import get_market_context_for_user
    market_context = get_market_context_for_user(user_id, client)

    try:
        next_run = compute_next_run_at(
            declaration,
            last_run_at=last_run_at,
            now=last_run_at,
            user_timezone=user_tz,
            market_context=market_context,
        )
    except ValueError as e:
        logger.error(
            "[CAPTURE_SCHED] record_capture_run %s/%s schedule resolution failed: %s",
            user_id[:8], declaration.slug, e,
        )
        next_run = None

    update = {
        "last_run_at": last_run_at.isoformat(),
        "next_run_at": next_run.isoformat() if next_run else None,
    }
    try:
        client.table("tasks").update(update).eq("user_id", user_id).eq(
            "slug", declaration.slug
        ).eq("kind", CAPTURE_KIND).execute()
    except Exception as e:
        logger.warning(
            "[CAPTURE_SCHED] record_capture_run update failed for %s/%s: %s",
            user_id[:8], declaration.slug, e,
        )


__all__ = [
    "CAPTURE_KIND",
    "materialize_capture_index",
    "get_due_captures",
    "claim_capture_run",
    "record_capture_run",
]
