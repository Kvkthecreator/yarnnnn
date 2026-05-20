"""
Scheduling — ADR-261 D3 walker over /workspace/_recurrences.yaml.

The scheduler walks the canonical recurrences file per user
(via services.recurrence.walk_workspace_recurrences) and dispatches due
invocations through services.wake_sources.cron_tick.dispatch_recurrence
(per ADR-296 v2 D1 — the cron-tick wake source).

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
  (YAML schema + walker) and `services.wake` (singular invocation gateway
  per ADR-296 v2 D1).
- Consumer: `jobs.unified_scheduler.run_unified_scheduler()`.
- Producers (both call materialize_scheduling_index when the canonical
  recurrences YAML changes):
    * `services.primitives.schedule.handle_schedule` — operator-driven
      mutations via Schedule(action=create|update|pause|resume|archive).
    * `services.programs.fork_reference_workspace` — initial bundle fork
      at activation time (signup, /api/programs/activate, L2/L4 reset
      reinit when prior_program_slug is preserved per ADR-244 D4).
  These are the only two writers to `/workspace/_recurrences.yaml`;
  every write site syncs the index in the same call, so the scheduler's
  next tick always sees a coherent index without waiting for a separate
  reconciliation pass.

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

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Union

from services.conventions import RECURRENCES_PATH
from services.market_calendars import (
    SESSIONS,
    MarketCalendar,
    calendar_for_market_context,
)
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
# Semantic schedule parsing — ADR-268 §D2
# ---------------------------------------------------------------------------
#
# Two grammars under the @-prefix:
#
#   @<session>_<edge> [+|-] <N> <unit>     anchored fire (single)
#   @every <N> <unit> during <session>     interval within session
#
# Examples handled:
#   @market_open                  → next regular_hours open
#   @market_open + 15min          → 15 min after next regular_hours open
#   @market_close - 30min         → 30 min before next regular_hours close
#   @pre_market_open              → next pre_market open
#   @after_hours_close - 10min    → 10 min before next after_hours close
#   @every 1min during regular_hours
#   @every 5min during pre_market

# Map shorthand "market_open" → "regular_hours_open" so the common case is
# pleasant to author. ADR-268 §D2: "`@market_open` is an alias for
# `@regular_hours_open`."
_SESSION_ALIASES = {
    "market": "regular_hours",  # @market_open → @regular_hours_open
}


_ANCHOR_RE = re.compile(
    r"^@(?P<session>market|regular_hours|pre_market|after_hours)"
    r"_(?P<edge>open|close)"
    r"(?:\s*(?P<sign>[+-])\s*(?P<n>\d+)\s*(?P<unit>min|h))?$"
)


_INTERVAL_RE = re.compile(
    r"^@every\s+(?P<n>\d+)\s*(?P<unit>min|h)"
    r"\s+during\s+(?P<session>regular_hours|pre_market|after_hours)$"
)


def _resolve_session_key(raw: str) -> str:
    """`market` → `regular_hours`; otherwise return as-is."""
    return _SESSION_ALIASES.get(raw, raw)


def _unit_to_minutes(n: int, unit: str) -> int:
    return n * 60 if unit == "h" else n


def _is_semantic(schedule: str) -> bool:
    return schedule.startswith("@")


def resolve_semantic_schedule(
    schedule: str,
    market_context: dict,
    last_run_at: Optional[datetime],
    now: datetime,
) -> Optional[datetime]:
    """Resolve a single @-prefixed semantic schedule to the next UTC fire time.

    Per ADR-268 §D3 this is the canonical compile-time resolution path.
    `last_run_at` is used to ensure interval-mode schedules advance past
    the last fire; for anchor-mode schedules `last_run_at` is consulted
    to skip the current day's anchor if it has already been hit.

    Returns None on parse failure (logged + raised would be tempting but
    the scheduler must keep walking other recurrences when one is malformed).
    """
    cal = calendar_for_market_context(market_context)

    anchor_match = _ANCHOR_RE.match(schedule.strip())
    if anchor_match:
        return _resolve_anchor(anchor_match, cal, last_run_at, now)

    interval_match = _INTERVAL_RE.match(schedule.strip())
    if interval_match:
        return _resolve_interval(interval_match, cal, last_run_at, now)

    logger.warning(
        "[SCHED] unparseable semantic schedule: %s. "
        "Valid forms: @<session>_<edge>[±Nunit], @every N unit during <session>.",
        schedule,
    )
    return None


def _resolve_anchor(
    match: re.Match,
    cal: MarketCalendar,
    last_run_at: Optional[datetime],
    now: datetime,
) -> datetime:
    """Resolve `@<session>_<edge> [±Nunit]` to next UTC fire."""
    session = _resolve_session_key(match.group("session"))
    edge = match.group("edge")  # open | close
    sign = match.group("sign")
    n_raw = match.group("n")
    unit = match.group("unit")

    offset_minutes = 0
    if sign and n_raw and unit:
        offset_minutes = _unit_to_minutes(int(n_raw), unit)
        if sign == "-":
            offset_minutes = -offset_minutes

    # Start search from the most-recent of (now, last_run_at + 1min).
    # Adding 1min avoids re-firing the same minute when last_run_at == anchor.
    floor = now
    if last_run_at and last_run_at + timedelta(minutes=1) > floor:
        floor = last_run_at + timedelta(minutes=1)

    # Walk forward day-by-day until we find a trading day whose anchor
    # is strictly after `floor`.
    candidate_date = floor.astimezone(cal.timezone).date()
    for offset_days in range(30):
        d = candidate_date + timedelta(days=offset_days)
        if not cal.is_trading_day(d):
            continue
        open_dt, close_dt = cal.session_window(d, session)
        anchor_dt = open_dt if edge == "open" else close_dt
        fire_dt = anchor_dt + timedelta(minutes=offset_minutes)
        fire_utc = fire_dt.astimezone(timezone.utc)
        if fire_utc > floor:
            return fire_utc

    raise RuntimeError(
        f"could not resolve anchor schedule within 30 days: "
        f"@{match.group(0)} starting from {floor.isoformat()}"
    )


def _resolve_interval(
    match: re.Match,
    cal: MarketCalendar,
    last_run_at: Optional[datetime],
    now: datetime,
) -> datetime:
    """Resolve `@every N unit during <session>` to next UTC fire.

    Semantics: the first fire of each session is at session-open exactly,
    then every N units thereafter until session-close (inclusive of fires
    AT session-close). Outside the session, no fires.
    """
    n = int(match.group("n"))
    unit = match.group("unit")
    session = match.group("session")
    interval_min = _unit_to_minutes(n, unit)
    if interval_min <= 0:
        raise ValueError(f"interval must be positive: {match.group(0)}")

    # Start search from the most-recent of (now, last_run_at + 1min).
    floor = now
    if last_run_at and last_run_at + timedelta(minutes=1) > floor:
        floor = last_run_at + timedelta(minutes=1)

    candidate_date = floor.astimezone(cal.timezone).date()
    for offset_days in range(30):
        d = candidate_date + timedelta(days=offset_days)
        if not cal.is_trading_day(d):
            continue
        open_dt, close_dt = cal.session_window(d, session)

        # Within this trading day's session, find the next fire-time >= floor.
        # Fire times are session_open + k*interval for k=0,1,2,...
        floor_in_tz = floor.astimezone(cal.timezone)
        if floor_in_tz >= close_dt:
            # Past this session's close; move to next trading day.
            continue

        if floor_in_tz <= open_dt:
            return open_dt.astimezone(timezone.utc)

        # floor is between open and close; compute next interval boundary
        elapsed_min = (floor_in_tz - open_dt).total_seconds() / 60
        # ceil(elapsed / interval) * interval = next fire offset from open
        import math
        k = math.ceil(elapsed_min / interval_min)
        # If we landed exactly on a boundary (elapsed % interval == 0)
        # and floor is at that boundary, advance one step.
        if abs(elapsed_min - k * interval_min) < 0.5:  # within 30s
            k = int(elapsed_min // interval_min) + 1
        fire_dt = open_dt + timedelta(minutes=k * interval_min)
        if fire_dt <= close_dt:
            return fire_dt.astimezone(timezone.utc)
        # k overshoots; move to next trading day's open
        continue

    raise RuntimeError(
        f"could not resolve interval schedule within 30 days: "
        f"@{match.group(0)} starting from {floor.isoformat()}"
    )


# ---------------------------------------------------------------------------
# compute_next_run_at — pure timing math
# ---------------------------------------------------------------------------


def compute_next_run_at(
    rec: Recurrence,
    last_run_at: Optional[datetime] = None,
    now: Optional[datetime] = None,
    user_timezone: str = DEFAULT_TIMEZONE,
    market_context: Optional[dict] = None,
) -> Optional[datetime]:
    """Compute the next firing time for a recurrence.

    Honors `paused` and `paused_until`. Returns None when:
      - recurrence has no schedule (reactive — fires on event, not cron)
      - recurrence is paused with no `paused_until` (indefinite)
      - recurrence's `paused_until` is in the future (still paused)

    Per ADR-268 §D3 the `schedule` field accepts:
      - A plain UTC cron expression (existing path, unchanged).
      - A @-prefixed semantic schedule (resolved via market_calendars).
      - A list of either of the above; next_run_at = min of each member's
        individually-resolved next time.

    `market_context` is required when ANY member of `schedule` is semantic.
    """
    if rec.paused:
        if rec.paused_until and (now is None or rec.paused_until > now):
            return rec.paused_until
        return None

    now_utc = now or datetime.now(timezone.utc)

    # ADR-270: fire-on-activation. Operator-authored on the recurrence YAML
    # body via `fire_on_activation: true` (parsed into `rec.options`). When
    # set AND no prior run has been recorded, return `now` so the next
    # scheduler tick after fork picks the row up immediately. After the
    # first fire records last_run_at, subsequent calls fall through to the
    # regular schedule resolution below. This closes the activation gap:
    # bundles that need substrate populated before the first periodic fire
    # (cold-start research, regime substrate, universe snapshots) declare
    # themselves activation-fired. No new trigger primitive — the existing
    # scheduler path picks up the due row via the standard cron tick.
    if rec.options.get("fire_on_activation") and last_run_at is None:
        return now_utc

    schedule = rec.schedule
    if not schedule:
        return None

    base = last_run_at or now_utc

    # Normalize to list-of-strings for unified handling. A single string
    # becomes a one-element list; a list stays a list.
    schedules: list[str] = schedule if isinstance(schedule, list) else [schedule]

    candidates: list[datetime] = []
    for member in schedules:
        if not isinstance(member, str) or not member.strip():
            continue
        if _is_semantic(member):
            if market_context is None:
                raise ValueError(
                    f"recurrence {rec.slug!r} schedule {member!r} is semantic "
                    f"but no market_context was supplied — bundle MANIFEST.yaml "
                    f"must declare 'market_context:' to use @-prefixed schedules"
                )
            try:
                resolved = resolve_semantic_schedule(
                    member, market_context, last_run_at, now_utc,
                )
            except Exception as e:
                logger.warning(
                    "[SCHED] failed to resolve semantic schedule %r for %s: %s",
                    member, rec.slug, e,
                )
                continue
            if resolved:
                candidates.append(resolved)
        else:
            resolved = _calc_legacy(
                schedule=member,
                last_run_at=base,
                user_timezone=user_timezone,
            )
            if resolved:
                candidates.append(resolved)

    if not candidates:
        return None
    return min(candidates)


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
    # ADR-268: load workspace's active bundle market_context once. Passed
    # to compute_next_run_at for any recurrence with semantic (@-prefixed)
    # schedules. None is acceptable when no bundle declares market_context
    # — recurrences with plain-cron schedules resolve normally; semantic
    # schedules in such a workspace raise ValueError loudly.
    from services.bundle_reader import get_market_context_for_user
    market_context = get_market_context_for_user(user_id, client)
    touched = 0

    for slug, rec in by_slug.items():
        existing_row = existing_by_slug.get(slug)
        last_run_at_iso = existing_row.get("last_run_at") if existing_row else None
        last_run_at = _parse_iso(last_run_at_iso)

        try:
            next_run = compute_next_run_at(
                rec,
                last_run_at=last_run_at,
                now=now,
                user_timezone=user_tz,
                market_context=market_context,
            )
        except ValueError as e:
            # Semantic schedule + no market_context. Log loudly; skip this
            # recurrence so the rest still index. Operator-visible error.
            logger.error(
                "[SCHED] %s/%s schedule resolution failed: %s",
                user_id[:8], slug, e,
            )
            next_run = None

        # Persist schedule in a string-stable form. JSON-encode lists so
        # the `tasks` column stays valid text and round-trips through
        # display tools without breaking on list-vs-string assumptions.
        if isinstance(rec.schedule, list):
            schedule_persist: Optional[str] = json.dumps(rec.schedule)
        else:
            schedule_persist = rec.schedule

        row = {
            "user_id": user_id,
            "slug": slug,
            "status": "active",
            "schedule": schedule_persist,
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
    error_reason: Optional[str] = None,
) -> None:
    """Write last_run_at + recomputed next_run_at to the thin index
    post-dispatch. Always sets next_run_at — either the next scheduled
    time or None to clear the optimistic sentinel claim_task_run set.

    Cold-start ordering fix (ADR-272 Phase 2 follow-up, 2026-05-14):
    when the dispatch failed because the required platform was not
    connected (``error_reason == "capability_missing"``) AND the
    recurrence declares ``fire_on_activation: true`` AND ``last_run_at``
    was still NULL pre-dispatch (i.e. the activation flag was armed),
    DO NOT write last_run_at. Reason: the work didn't actually happen,
    so the activation flag should re-arm so the next scheduler tick
    (post-connect) picks the row up immediately. Without this, operators
    who activate before connect have a silent workspace until the next
    periodic cron — the flag is consumed by a failure that wasn't the
    work's failure.

    next_run_at always advances (clears the sentinel). The activation
    flag's re-fire arming lives in compute_next_run_at's `last_run_at
    is None` check, which we preserve here by not writing last_run_at.
    """
    user_tz = user_timezone or get_user_timezone(client, user_id)
    # ADR-268: load market_context for semantic-schedule resolution.
    from services.bundle_reader import get_market_context_for_user
    market_context = get_market_context_for_user(user_id, client)

    # Cold-start ordering fix: detect armed-and-blocked activation.
    preserve_activation_arming = bool(
        error_reason == "capability_missing"
        and recurrence.options.get("fire_on_activation")
    )
    if preserve_activation_arming:
        # Check whether last_run_at was still NULL pre-dispatch. If so,
        # this is the armed-and-blocked case — don't consume the flag.
        try:
            existing = (
                client.table("tasks")
                .select("last_run_at")
                .eq("user_id", user_id)
                .eq("slug", recurrence.slug)
                .limit(1)
                .execute()
            )
            had_prior_run = bool(
                existing.data
                and existing.data[0].get("last_run_at") is not None
            )
        except Exception:
            had_prior_run = True  # fail-closed — preserve original behavior
        if not had_prior_run:
            # Preserve arming (last_run_at stays NULL) AND set next_run_at
            # to a gentle retry delay (+60s) so the scheduler picks the row
            # up regularly while waiting for the operator to connect the
            # platform. Once connected, the very next retry succeeds.
            # The capability_missing narrative emits once via the existing
            # transition-detection logic — subsequent retries log silently.
            retry_at = datetime.now(timezone.utc) + timedelta(seconds=60)
            logger.info(
                "[SCHED] %s/%s capability_missing while fire_on_activation armed — "
                "preserving last_run_at=NULL + retry at %s (60s) for self-heal",
                user_id[:8], recurrence.slug, retry_at.isoformat(),
            )
            update = {"next_run_at": retry_at.isoformat()}
            try:
                client.table("tasks").update(update).eq("user_id", user_id).eq(
                    "slug", recurrence.slug
                ).execute()
            except Exception as e:
                logger.warning(
                    "[SCHED] record_task_run (preserve-arming) update failed for %s/%s: %s",
                    user_id[:8], recurrence.slug, e,
                )
            return

    try:
        next_run = compute_next_run_at(
            recurrence,
            last_run_at=last_run_at,
            now=last_run_at,
            user_timezone=user_tz,
            market_context=market_context,
        )
    except ValueError as e:
        # Semantic schedule + no market_context. Log loudly; next_run stays
        # None, advancing the index off this recurrence until operator
        # surfaces the config gap (re-fork bundle, or edit YAML to plain cron).
        logger.error(
            "[SCHED] record_task_run %s/%s schedule resolution failed: %s",
            user_id[:8], recurrence.slug, e,
        )
        next_run = None
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
