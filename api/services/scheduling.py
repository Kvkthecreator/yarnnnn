"""
Scheduling — the schedule math shared by the standing lanes (ADR-268 semantic
schedules, ADR-596 D4 workspace timezone).

`compute_next_run_at(rec, ...)` takes any declaration-shaped object with
`slug` / `schedule` / `paused` / `paused_until` (a strings declaration, a
capture declaration) and returns the next firing time. `preserve_due_commitment`
keeps a due moment across a re-declaration.

ADR-632: the recurrence INDEX half of this module (`materialize_scheduling_index`,
`get_due_recurrences`, `claim_task_run`, `record_task_run`, the `tasks` rows) is
DELETED with the steward — recurrences were retired by ADR-603 D5 and the
index had no live reader once the cron-tick wake source went. The `tasks`
table survives as data until a follow-up migration drops it.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

from services.market_calendars import (
    SESSIONS,
    MarketCalendar,
    calendar_for_market_context,
)
from services.schedule_utils import (
    DEFAULT_TIMEZONE,
    calculate_next_run_at as _calc_legacy,
    get_workspace_timezone,
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
#   @every <N> <unit>                      bare interval (session-less;
#                                          NO market context needed —
#                                          ADR-401, the connector-capture
#                                          cadence shape)
#
# Examples handled:
#   @market_open                  → next regular_hours open
#   @market_open + 15min          → 15 min after next regular_hours open
#   @market_close - 30min         → 30 min before next regular_hours close
#   @pre_market_open              → next pre_market open
#   @after_hours_close - 10min    → 10 min before next after_hours close
#   @every 1min during regular_hours
#   @every 5min during pre_market
#   @every 15min                  → last_run + 15 minutes, any workspace

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


# Bare session-less interval — `@every 15min`, `@every 1h`, `@every 24h`.
# Resolved as last_run + interval with NO market context (ADR-401): this is
# the connector-capture cadence shape, valid on any workspace. Pre-fix, the
# seeded `@every 15min` was classified semantic and unresolvable everywhere
# (bare workspaces raised on missing market_context; program workspaces
# failed the `during <session>` grammar) — so connector captures NEVER
# became due. The bare form is checked BEFORE the semantic branch.
_BARE_INTERVAL_RE = re.compile(
    r"^@every\s+(?P<n>\d+)\s*(?P<unit>min(?:ute)?s?|h(?:(?:ou)?rs?)?|d(?:ay)?s?)$",
    re.IGNORECASE,
)


def _parse_bare_interval(member: str) -> Optional[timedelta]:
    """`@every N unit` (no session) → timedelta, else None."""
    m = _BARE_INTERVAL_RE.match((member or "").strip())
    if not m:
        return None
    n = int(m.group("n"))
    unit = m.group("unit").lower()
    if unit.startswith("min"):
        return timedelta(minutes=n)
    if unit.startswith("h"):
        return timedelta(hours=n)
    return timedelta(days=n)


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


def preserve_due_commitment(
    stored_next: Optional[datetime],
    computed_next: Optional[datetime],
    *,
    now: datetime,
    paused: bool,
) -> Optional[datetime]:
    """A due-but-unfired ``next_run_at`` is a COMMITMENT, never a stale value.

    ``compute_next_run_at`` anchors on ``last_run_at or now``, so for a
    recurrence that has NEVER run (and declares no ``fire_on_activation``)
    every re-materialization recomputes from *now* — rolling an already-due
    firing time forward past the due scan. Where the materializer runs at the
    top of the same tick whose due scan would claim the row (a standing
    drainer, e.g. Strings), that is not a skipped occurrence but a loop that can
    never start: observed live 2026-08-13, a conversationally-created watched
    folder (ADR-567 D3 writes no fire_on_activation) armed for 09:00 was
    re-materialized to the next day at the 09:04 tick, permanently.

    The rule: when the stored ``next_run_at`` has come due and the
    declaration still wants to run (not paused), the materializer must KEEP
    it, so the due scan claims it. The claim CAS then parks the row on its
    in-flight sentinel and the post-run record re-anchors on ``last_run_at``
    — the commitment is consumed by exactly one run, never re-preserved.
    A paused declaration is honored over any commitment (pause wins, as it
    does in ``compute_next_run_at``).
    """
    if paused:
        return computed_next
    if stored_next is not None and stored_next <= now:
        return stored_next
    return computed_next


def compute_next_run_at(
    rec: Any,
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
        # Bare session-less interval (`@every 15min`) — resolved as
        # base + interval, market-context-free. Checked BEFORE the semantic
        # branch so connector-capture cadences work on any workspace.
        bare = _parse_bare_interval(member)
        if bare is not None:
            candidates.append(base + bare)
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
    "preserve_due_commitment",
    "get_due_recurrences",
    "claim_task_run",
    "record_task_run",
]


# =============================================================================
# The ONE drain loop (ADR-639 D3) — every unattended kind rides it
# =============================================================================
#
# Before ADR-639 the standing lane (strings) and the capture lane each carried a
# byte-twin of this loop: kind-scoped CAS claim → run → record-in-finally. Two
# copies of one mechanism is the second-home drift; ADR-603 D6 waited for a
# "second declaration kind" to generalise and the second instance of the LOOP
# had been here all along. The declaration SHAPE stays per kind (each kind
# supplies its own discovery + run body); only the loop is shared.
#
# A kind supplies:
#   due(client, now)        → list of (user_id, decl, original_next_run) — the
#                             rows that should run now, already filtered for
#                             paused / problem states; `original_next_run` is
#                             the stored value the claim compares against
#   run(client, user_id, decl) → {"success": bool, "error_reason"?: str, …}
#   record(client, user_id, decl, last_run_at) → None — advances the row
#
# `decl` is any object with `.slug`, `.schedule`, `.paused`, `.paused_until`,
# `.options` (what `compute_next_run_at` reads).

#: How long a claimed row is held by its sentinel before another scheduler
#: instance may reclaim it. Long enough for the slowest run; short enough that
#: a crashed instance does not strand the row for a day.
CLAIM_SENTINEL_HOURS = 2


def claim_run(
    client, user_id: str, slug: str, kind: str, original_next_run: Optional[str],
    *, sentinel_hours: int = CLAIM_SENTINEL_HOURS,
) -> bool:
    """CAS atomic claim on ONE kind's index row.

    Bumps `next_run_at` to a sentinel iff it still equals `original_next_run`,
    so concurrent scheduler instances (and the manual Run-now door, ADR-618 D2)
    cannot both execute one row. Kind-scoped so two kinds sharing a slug (an
    authoring error) can never cross-claim. `None` for the baseline refuses:
    there is nothing to compare against, and a caller that reads None as a
    lost race would make a never-indexed declaration un-fireable by hand — the
    caller decides what None means (ADR-618 D2).
    """
    if original_next_run is None:
        return False
    sentinel = (datetime.now(timezone.utc) + timedelta(hours=sentinel_hours)).isoformat()
    try:
        result = (
            client.table("tasks")
            .update({"next_run_at": sentinel})
            .eq("user_id", user_id)
            .eq("slug", slug)
            .eq("kind", kind)
            .eq("next_run_at", original_next_run)
            .execute()
        )
        return bool(result.data)
    except Exception as e:  # noqa: BLE001 — a failed claim is a skipped row
        logger.warning("[DRAIN:%s] claim failed for %s/%s: %s", kind, user_id[:8], slug, e)
        return False


def record_run(
    client, user_id: str, decl: Any, kind: str, *, last_run_at: datetime,
    user_timezone: Optional[str] = None, market_context: Optional[dict] = None,
) -> None:
    """Advance `last_run_at` + `next_run_at` after a run (clears the sentinel).

    Always writes `next_run_at` — the next scheduled time, or None — so a row
    never stays stranded on its claim sentinel after a failed run.
    """
    if user_timezone is None:
        from services.schedule_utils import get_workspace_timezone
        user_timezone = get_workspace_timezone(client, user_id)
    try:
        next_run = compute_next_run_at(
            decl, last_run_at=last_run_at, now=last_run_at,
            user_timezone=user_timezone, market_context=market_context,
        )
    except ValueError as e:
        logger.error("[DRAIN:%s] %s/%s schedule resolution failed: %s",
                     kind, user_id[:8], decl.slug, e)
        next_run = None
    try:
        (
            client.table("tasks")
            .update({
                "last_run_at": last_run_at.isoformat(),
                "next_run_at": next_run.isoformat() if next_run else None,
            })
            .eq("user_id", user_id).eq("slug", decl.slug).eq("kind", kind)
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("[DRAIN:%s] record run failed for %s/%s: %s",
                       kind, user_id[:8], decl.slug, e)


async def drain_due(
    client, kind: str, *, due: Any, run: Any, record: Any,
) -> tuple[int, int, int]:
    """Run every due row of one kind: claim → run → record, each isolated.

    Returns (found, succeeded, failed). A run that reports failure logs its
    REASON here (ADR-618's named gap: a count cannot say `router_disabled`,
    and that is what let production's one string fail four days running while
    every log line looked ordinary). A raised run is a failure, never a
    crashed tick. `record` runs in `finally` so a row is never left on its
    claim sentinel.
    """
    now = datetime.now(timezone.utc)
    try:
        rows = await due(client, now)
    except Exception as e:  # noqa: BLE001
        logger.warning("[DRAIN:%s] due scan raised: %s", kind, e)
        return 0, 0, 0

    found = succeeded = failed = 0
    for user_id, decl, original_next_run in rows:
        found += 1
        if not claim_run(client, user_id, decl.slug, kind, original_next_run):
            logger.info("[DRAIN:%s] %s/%s already claimed by another instance; skipping",
                        kind, user_id[:8], decl.slug)
            continue
        try:
            result = await run(client, user_id, decl)
            if result.get("success"):
                succeeded += 1
            else:
                failed += 1
                logger.error("[DRAIN:%s] run failed for %s/%s: %s", kind, user_id[:8],
                             decl.slug, result.get("error_reason") or "unknown")
        except Exception as e:  # noqa: BLE001
            failed += 1
            logger.exception("[DRAIN:%s] run raised for %s/%s: %s", kind, user_id[:8], decl.slug, e)
        finally:
            try:
                record(client, user_id, decl, datetime.now(timezone.utc))
            except Exception as e:  # noqa: BLE001
                logger.warning("[DRAIN:%s] record failed for %s/%s: %s", kind, user_id[:8], decl.slug, e)
    return found, succeeded, failed
