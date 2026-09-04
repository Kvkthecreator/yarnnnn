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
from services.schedule_utils import get_workspace_timezone

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

    user_tz = get_workspace_timezone(client, user_id)
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


async def due_captures(
    client, now: Optional[datetime] = None,
) -> list[tuple[str, CaptureDeclaration, Optional[str]]]:
    """The due ``(user_id, declaration, stored next_run_at)`` triples of
    kind='capture' — the shape the ONE drain loop consumes (ADR-639 D3).

    Queries `tasks` for active capture rows with next_run_at <= now, then
    re-reads each user's ``_captures.yaml`` (truth) and matches by slug. The
    third element is the baseline the claim compares against — read here, in
    the same scan, rather than re-read per row by the loop.
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

    out: list[tuple[str, CaptureDeclaration, Optional[str]]] = []
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
            out.append((user_id, decl, row.get("next_run_at")))

    return out


def record_capture(client, user_id: str, declaration: CaptureDeclaration,
                   last_run_at: datetime) -> None:
    """The capture kind's `record` adapter for the ONE drain loop — the shared
    ``record_run`` with the trader's market context (semantic schedules,
    ADR-268). ``claim_capture_run`` / ``record_capture_run`` — this kind's
    byte-twins of the loop's own functions — are DELETED (ADR-639 D3)."""
    from services.bundle_reader import get_market_context_for_user
    from services.scheduling import record_run

    record_run(
        client, user_id, declaration, CAPTURE_KIND, last_run_at=last_run_at,
        market_context=get_market_context_for_user(user_id, client),
    )


__all__ = [
    "CAPTURE_KIND",
    "materialize_capture_index",
    "due_captures",
    "record_capture",
]
