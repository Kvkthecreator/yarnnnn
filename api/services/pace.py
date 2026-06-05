"""ADR-298 Phase 2 — Pace substrate + recurrence-population constraint.

Pace is the operator's first-class dial for **how often the agent works**
(ADR-298 D11 — Pace + Autonomy + Persona trifecta, mapping to Trigger +
Mechanism + Identity dimensions of FOUNDATIONS Axiom 0). Substrate file:
``/workspace/governance/_pace.yaml`` (operator-authored, machine-parsed
per File Format Discipline §9).

Pace's authority is **enforced at recurrence declaration time** (ADR-298
D5), NOT at runtime queue drain. The system computes the cumulative
fire-frequency of declared scheduled recurrences against the workspace's
declared pace drain rate. If a new ``Schedule(action="create"|"update")``
call would push total frequency past the drain rate, the call fails
with ``pace_exceeded``. This prevents the unbounded-queue-depth failure
mode (paced lane growing indefinitely when declarations exceed drain).

Pace enum:
  ``hourly``     — drain paced lane ≤1 wake/hour    (≤24 fires/day)
  ``daily``      — drain paced lane ≤1 wake/day     (≤1 fires/day)
  ``weekly``     — drain paced lane ≤1 wake/week    (≤1 fires/7days)
  ``continuous`` — no drain rate cap

Fire-frequency gate partition (ADR-313): Pace owns the DRAIN-LANE RATE —
the workspace-wide tempo at which the paced wake lane empties. This is the
sibling-but-distinct gate to TOKEN-BUDGET (`services/token_budget.py`,
ADR-293 D7), which owns COST + PER-SLUG FLOOR. `pace.min_interval_seconds`
is a workspace-wide drain interval; `token_budget.min_interval_for(slug)`
is a per-recurrence floor — same word, different layer, different scope.
The two gates are sequential, not redundant. See ADR-313 for the canonical
partition statement.

Numeric override (`every: <ISO 8601 duration>`) is parsed and computed
back to the nearest enum band for cockpit display + drain rate. First
iteration: enum-band coercion. Pure-numeric drain rate is a future
iteration (ADR-298 §8).

References:
- docs/adr/ADR-298-reviewer-wake-queue-and-pace.md (canonical spec)
- docs/architecture/FOUNDATIONS.md Axiom 0 (Trigger dimension) + Axiom 4
- docs/architecture/FOUNDATIONS.md Principle 18 (standing-intent
  implies Trigger-authoring authority — pace constrains but does not
  remove the authority)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ─── Constants ──────────────────────────────────────────────────────────────


PACE_KINDS = frozenset({"hourly", "daily", "weekly", "continuous"})

# Per-kind drain rate expressed as max fires per day. The pace check
# compares cumulative recurrence frequency (also normalized to fires/day)
# against this ceiling.
PACE_FIRES_PER_DAY = {
    "hourly":     24.0,
    "daily":      1.0,
    "weekly":     1.0 / 7.0,
    "continuous": float("inf"),
}


# ─── Dataclass ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Pace:
    """Parsed operator pace declaration."""
    kind: str                       # one of PACE_KINDS
    every_iso: Optional[str] = None # numeric override (e.g., "4h") — preserved
                                    # for cockpit display + future pure-numeric drain

    @property
    def fires_per_day_cap(self) -> float:
        """Drain rate ceiling for the paced lane, expressed as fires/day.
        ``continuous`` returns infinity (no cap)."""
        return PACE_FIRES_PER_DAY[self.kind]

    @property
    def min_interval_seconds(self) -> float:
        """Minimum seconds between paced-lane drains under this pace.

        Singular implementation (ADR-301 cleanup): drain-side throttle
        arithmetic and FE display + declaration-time gate all consume
        this property. Pre-cleanup, the `86400 / fires_per_day` inline
        was duplicated in `wake_drainer.paced_lane_eligible_to_drain`;
        post-cleanup it lives only here. `continuous` returns 0 (no
        interval); zero-cap kinds (defensive) return infinity.
        """
        cap = self.fires_per_day_cap
        if cap == float("inf"):
            return 0.0
        if cap <= 0:
            return float("inf")
        return 86400.0 / cap


# ─── Errors ─────────────────────────────────────────────────────────────────


class PaceError(Exception):
    """Base class for pace errors."""


class InvalidPaceKindError(PaceError):
    """Raised when pace.kind is not in the canonical enum."""


class PaceParseError(PaceError):
    """Raised when _pace.yaml is malformed."""


# ─── Pace ordering ──────────────────────────────────────────────────────────


def pace_at_least_as_frequent(declared: str, minimum: str) -> bool:
    """ADR-298 D7 — return True iff ``declared`` pace fires at least as
    often as ``minimum``. Used by the activation gate to refuse operator
    pace below the bundle's declared floor.

    Ordering: ``continuous > hourly > daily > weekly`` (more frequent → larger
    fires_per_day cap). ``continuous`` satisfies any minimum; ``weekly`` only
    satisfies itself; ``hourly`` satisfies daily + weekly + itself but not
    continuous; etc.

    Raises :class:`InvalidPaceKindError` on unknown enum values — both args
    must be in PACE_KINDS.
    """
    if declared not in PACE_KINDS:
        raise InvalidPaceKindError(
            f"declared pace {declared!r} must be one of {sorted(PACE_KINDS)}"
        )
    if minimum not in PACE_KINDS:
        raise InvalidPaceKindError(
            f"minimum pace {minimum!r} must be one of {sorted(PACE_KINDS)}"
        )
    return PACE_FIRES_PER_DAY[declared] >= PACE_FIRES_PER_DAY[minimum]


# ─── Parser ─────────────────────────────────────────────────────────────────


# ISO 8601 duration subset accepted in `every`. We support hours and days
# (`4h`, `12h`, `3d`, `7d`) — the common cases. Future iteration may
# extend to weeks/months. The numeric override is round-tripped to the
# nearest enum band; raw value preserved for FE display.
_EVERY_PATTERN = re.compile(r"^\s*(\d+)\s*([hd])\s*$", re.IGNORECASE)


def _every_to_hours(raw: str) -> Optional[float]:
    """`4h` → 4.0; `3d` → 72.0; otherwise None."""
    m = _EVERY_PATTERN.match(raw)
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2).lower()
    return n * 24.0 if unit == "d" else float(n)


def _hours_to_kind(hours: float) -> str:
    """Coerce a numeric `every` to its nearest enum band per ADR-298 D4."""
    if hours <= 0:
        # Pathological — treat as continuous (no cap).
        return "continuous"
    fires_per_day = 24.0 / hours
    # Bands: continuous if effectively unbounded, else hourly/daily/weekly
    # based on which fires-per-day ceiling the override is *under or equal to*.
    # Operator declaring `every: 4h` means "fires every 4h" = 6/day → falls
    # within hourly band (24/day cap), so hourly is the correct band.
    if fires_per_day > 1.0:
        return "hourly"
    if fires_per_day >= 1.0 / 7.0:
        return "daily"
    return "weekly"


def parse_pace_yaml(content: str) -> Optional[Pace]:
    """Parse ``_pace.yaml`` content. Returns ``None`` if the file is empty,
    missing, or carries no ``pace:`` block — workspace operates with no
    declared pace (live-lane only, no paced lane constraints).

    Raises :class:`PaceParseError` on malformed YAML or invalid kind.
    Raises :class:`InvalidPaceKindError` on unknown ``kind`` value.
    """
    if not content or not content.strip():
        return None

    try:
        import yaml
        loaded = yaml.safe_load(content)
    except Exception as exc:
        raise PaceParseError(f"_pace.yaml YAML parse failed: {exc}") from exc

    if loaded is None:
        return None
    if not isinstance(loaded, dict):
        raise PaceParseError(
            f"_pace.yaml must be a mapping at top level, got {type(loaded).__name__}"
        )

    block = loaded.get("pace")
    if block is None:
        return None
    if not isinstance(block, dict):
        raise PaceParseError(
            f"_pace.yaml `pace:` must be a mapping, got {type(block).__name__}"
        )

    raw_kind = block.get("kind")
    raw_every = block.get("every")

    if raw_kind is not None:
        if not isinstance(raw_kind, str) or raw_kind.strip().lower() not in PACE_KINDS:
            raise InvalidPaceKindError(
                f"_pace.yaml pace.kind={raw_kind!r} must be one of {sorted(PACE_KINDS)}"
            )
        kind = raw_kind.strip().lower()
    elif raw_every is not None:
        # Numeric override without explicit kind — compute the band.
        if not isinstance(raw_every, str):
            raise PaceParseError(
                f"_pace.yaml pace.every={raw_every!r} must be a string"
            )
        hours = _every_to_hours(raw_every)
        if hours is None:
            raise PaceParseError(
                f"_pace.yaml pace.every={raw_every!r} must match `<N>h` or `<N>d` "
                "(ISO 8601 duration subset)"
            )
        kind = _hours_to_kind(hours)
    else:
        raise PaceParseError(
            "_pace.yaml `pace:` must declare either `kind` or `every`"
        )

    every_iso = raw_every if isinstance(raw_every, str) else None
    return Pace(kind=kind, every_iso=every_iso)


# ─── Read from workspace ────────────────────────────────────────────────────


async def read_pace(client: Any, user_id: str) -> Optional[Pace]:
    """Load and parse the workspace's `_pace.yaml`. Returns None if absent."""
    from services.workspace import UserMemory
    from services.workspace_paths import GOVERNANCE_PACE_PATH

    um = UserMemory(client, user_id)
    # Strip leading "/workspace/" if GOVERNANCE_PACE_PATH has it; UserMemory
    # prepends. Path constants in workspace_paths are workspace-relative
    # ("constitution/+governance/+operation/ (legacy _shared, ADR-320)/...") so no strip needed.
    content = await um.read(GOVERNANCE_PACE_PATH)
    if not content:
        return None
    return parse_pace_yaml(content)


# ─── Cron → fires-per-day ──────────────────────────────────────────────────


def cron_fires_per_day(cron_expr: str) -> float:
    """Approximate the fires-per-day of a cron expression by counting
    fires over a 7-day sample window and dividing by 7.

    Returns 0.0 for null/empty schedules (reactive recurrences don't
    fire on cron — they fire on substrate events; they don't count
    against pace).

    Returns ``float("inf")`` for non-parseable cron expressions, which
    will fail the population check loudly — better than silently
    accepting a malformed schedule.

    Semantic schedules (``@market_open``, etc.) are out of scope for
    Phase 2 — they're resolved by ``services.scheduling.resolve_semantic_schedule``
    against market context. For pace purposes, semantic schedules are
    treated as their daily-anchored equivalent (most fire once per
    trading day ≈ 1/day; ``@every_5m`` etc. are domain-specific). This
    helper covers plain UTC cron expressions; semantic-schedule pace
    coverage is a Phase 4 concern when bundle minimum_pace lands.
    """
    if not cron_expr or not isinstance(cron_expr, str) or not cron_expr.strip():
        return 0.0

    expr = cron_expr.strip()
    if expr.startswith("@"):
        # Semantic schedule — assume 1 fire/day (most are trading-day-
        # anchored). Phase 4 may refine this when bundle minimum_pace
        # surfaces semantic-aware pace minimums.
        return 1.0

    try:
        from croniter import croniter
        from datetime import datetime, timedelta, timezone
    except ImportError:
        logger.warning("[pace] croniter not available — cannot compute fires-per-day")
        return float("inf")

    try:
        now = datetime.now(timezone.utc)
        sample_end = now + timedelta(days=7)
        cron = croniter(expr, now)
        count = 0
        nxt = cron.get_next(datetime)
        while nxt < sample_end:
            count += 1
            nxt = cron.get_next(datetime)
        return count / 7.0
    except Exception as exc:
        logger.warning(
            "[pace] cron_fires_per_day failed for %r: %s — treating as infinity",
            cron_expr, exc,
        )
        return float("inf")


# ─── Population constraint check ───────────────────────────────────────────


@dataclass(frozen=True)
class PopulationCheckResult:
    """Result of a recurrence-population check against pace."""
    pace: Optional[Pace]
    current_fires_per_day: float
    proposed_fires_per_day: float
    drain_rate_fires_per_day: float  # inf for continuous
    exceeds: bool
    detail: str


def check_population_constraint(
    pace: Optional[Pace],
    existing_recurrences: list,
    new_schedule: Optional[str],
    *,
    replacing_slug: Optional[str] = None,
) -> PopulationCheckResult:
    """Compute whether adding `new_schedule` would exceed the workspace's
    declared pace drain rate.

    Args:
      pace: parsed Pace from `_pace.yaml`, or None (workspace has no
        declared pace; all schedules pass).
      existing_recurrences: list of objects with `.slug`, `.schedule`,
        `.mode` attributes (from `services.recurrence.Recurrence`).
        Mechanical-mode recurrences are excluded (they don't enter the
        paced lane per ADR-298 D3). Reactive recurrences (schedule=None)
        are also excluded — they don't fire on cron.
      new_schedule: the proposed cron expression. None means reactive
        (always passes).
      replacing_slug: when `Schedule(action="update")` modifies an
        existing recurrence, exclude its current schedule from the
        existing-sum so we're not double-counting.

    Returns a :class:`PopulationCheckResult` describing whether the
    operation should proceed.
    """
    if pace is None or pace.kind == "continuous":
        # No cap — every operation passes.
        cap = float("inf")
        cur = sum(
            cron_fires_per_day(r.schedule)
            for r in existing_recurrences
            if getattr(r, "schedule", None)
            and getattr(r, "mode", "judgment") == "judgment"
            and (replacing_slug is None or r.slug != replacing_slug)
        )
        proposed = cron_fires_per_day(new_schedule) if new_schedule else 0.0
        return PopulationCheckResult(
            pace=pace,
            current_fires_per_day=cur,
            proposed_fires_per_day=proposed,
            drain_rate_fires_per_day=cap,
            exceeds=False,
            detail="no pace cap (None or continuous)",
        )

    cap = pace.fires_per_day_cap
    cur = sum(
        cron_fires_per_day(r.schedule)
        for r in existing_recurrences
        if getattr(r, "schedule", None)
        and getattr(r, "mode", "judgment") == "judgment"
        and (replacing_slug is None or r.slug != replacing_slug)
    )
    proposed = cron_fires_per_day(new_schedule) if new_schedule else 0.0
    total = cur + proposed

    # Allow a tiny tolerance to avoid floating-point precision rejecting
    # a perfectly-sized declaration. 1e-9 fires/day is below any real
    # cron rate; this only matters at the equality boundary.
    exceeds = total > cap + 1e-9

    detail = (
        f"workspace pace={pace.kind} (cap={cap:.4f}/day); "
        f"existing judgment recurrences contribute {cur:.4f}/day; "
        f"new schedule {new_schedule!r} contributes {proposed:.4f}/day; "
        f"total={total:.4f}/day {'EXCEEDS' if exceeds else 'within'} cap"
    )

    return PopulationCheckResult(
        pace=pace,
        current_fires_per_day=cur,
        proposed_fires_per_day=proposed,
        drain_rate_fires_per_day=cap,
        exceeds=exceeds,
        detail=detail,
    )
