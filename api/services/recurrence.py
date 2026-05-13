"""
Recurrence — ADR-261 unified schema.

A recurrence is a record with three load-bearing fields per ADR-261 D1:

    slug:     stable identifier (used in audit trails, feed entries,
              operator chat references)
    schedule: cron expression (or null for reactive)
    prompt:   the message handed to the Reviewer at the scheduled time
              as the addressed-equivalent envelope

There is one execution shape. Output_kind is deleted as a recurrence-level
discriminator. Per-shape declaration files (`_spec.yaml`, `_recurring.yaml`,
`_action.yaml`, `back-office.yaml`) are deleted. RecurrenceShape enum is
deleted. Per-shape natural-home path resolution (recurrence_paths.py) is
deleted — paths are slug-templated by the conventions module.

Every recurrence for a workspace lives in **/workspace/_recurrences.yaml**
(per ADR-261 D2; constant ``conventions.RECURRENCES_PATH``). It is a flat
list. The operator can read the entire scheduled-work surface in 30
seconds.

This module provides:
  - `Recurrence` dataclass (the parsed entry)
  - `parse_recurrences_yaml(content, user_id)` — single canonical parser
  - `walk_workspace_recurrences(client, user_id)` — filesystem scanner
  - `compute_next_run_at(rec, now)` — scheduler-facing timing helper

The dispatcher (`api/services/invocation_dispatcher.py`) consumes
``Recurrence`` objects and invokes the Reviewer with each entry's
``prompt`` per ADR-260 D1 + ADR-261 D3. There is one dispatch path.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, Union

import yaml

from services.conventions import RECURRENCES_PATH

logger = logging.getLogger(__name__)


# ADR-268: a recurrence's schedule may be a single string (plain cron OR
# semantic `@`-prefixed) OR a list of such strings. List-form represents
# multiple-fires-per-recurrence (e.g. three RTH snapshots/day); the
# scheduler resolves each member individually and uses the minimum
# next-run-at across all members.
Schedule = Optional[Union[str, list[str]]]


# ---------------------------------------------------------------------------
# Recurrence dataclass
# ---------------------------------------------------------------------------


# ADR-263: recurrence mode declares at authoring time whether a recurrence
# wakes the Reviewer (judgment) or runs as deterministic Python (mechanical).
# Default is "judgment" — preserves backward compatibility for legacy entries
# in existing _recurrences.yaml files. Mechanical recurrences expect their
# `prompt` field to name a primitive invocation (`@primitive: ...`); the
# dispatcher parses and executes deterministically with no LLM session.
RECURRENCE_MODES = ("judgment", "mechanical")
DEFAULT_RECURRENCE_MODE = "judgment"


def is_valid_mode(mode: str) -> bool:
    """Soft check for caller-side validation. The parser coerces invalid
    values to the default and logs a warning."""
    return mode in RECURRENCE_MODES


@dataclass
class Recurrence:
    """One parsed recurrence entry per ADR-261 D1, extended by ADR-263.

    The four load-bearing fields are ``slug``, ``schedule``, ``mode``, ``prompt``.
    Optional ``options`` carries operator-legibility metadata
    (``display_name``, ``description``, etc.) that does not affect
    execution shape per ADR-261 D1.

    ADR-263: ``mode`` declares whether the recurrence wakes the Reviewer
    (``judgment``) or runs as deterministic Python (``mechanical``). Authored
    at create-time by operator-via-YARNNN, Reviewer-mid-loop, or
    system-bundle-fork; editable thereafter via Schedule(action="update").
    """

    slug: str  # operator-legible identifier
    # ADR-268: schedule accepts plain UTC cron OR `@`-prefixed semantic
    # (resolved against bundle's market_context) OR a list of either
    # (multiple fires per day). None = reactive (fires on event, not cron).
    schedule: Schedule = None
    # Defaulted only to satisfy dataclass field-ordering after `schedule`
    # gained a default; parser enforces non-empty at construction time.
    prompt: str = ""
    mode: str = DEFAULT_RECURRENCE_MODE  # ADR-263: judgment | mechanical

    # Optional metadata
    paused: bool = False
    paused_until: Optional[datetime] = None
    options: dict = field(default_factory=dict)

    # Provenance (set by walker)
    user_id: Optional[str] = None
    last_modified: Optional[datetime] = None

    def is_due(self, now: datetime) -> bool:
        """Cheap deterministic gate. Returns True if this recurrence should
        fire at ``now``. Honors paused / paused_until. Does NOT parse the
        cron expression — that's the scheduler's job; this is a coarse
        filter for invocation-side gating."""
        if self.paused:
            return False
        if self.paused_until and now < self.paused_until:
            return False
        if not self.schedule:
            # Reactive recurrences are never auto-due; they fire on event.
            return False
        return True


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_recurrences_yaml(
    content: str,
    user_id: Optional[str] = None,
    last_modified: Optional[datetime] = None,
) -> list[Recurrence]:
    """Parse the canonical ``/workspace/_recurrences.yaml`` body.

    The schema is a YAML list (or a dict with ``recurrences:`` key holding
    a list — both shapes accepted for operator legibility). Each entry is
    a dict with at minimum ``slug`` + ``schedule`` + ``prompt``.

    Returns an empty list on parse error or empty content. Logs a warning
    for malformed entries; one bad entry doesn't abort the whole parse.
    """
    if not content or not content.strip():
        return []

    try:
        parsed = yaml.safe_load(content)
    except yaml.YAMLError as e:
        logger.error("[RECURRENCE] YAML parse error: %s", e)
        return []

    if parsed is None:
        return []

    # Accept either a top-level list or a dict with a ``recurrences:`` key.
    if isinstance(parsed, dict):
        entries = parsed.get("recurrences") or parsed.get("entries")
        if entries is None:
            logger.warning(
                "[RECURRENCE] expected list at top-level or under 'recurrences:' key"
            )
            return []
    elif isinstance(parsed, list):
        entries = parsed
    else:
        logger.warning(
            "[RECURRENCE] expected list or dict at top level, got %s",
            type(parsed).__name__,
        )
        return []

    if not isinstance(entries, list):
        logger.warning("[RECURRENCE] entries must be a list, got %s", type(entries).__name__)
        return []

    out: list[Recurrence] = []
    for idx, raw in enumerate(entries):
        if not isinstance(raw, dict):
            logger.warning("[RECURRENCE] entry #%d is not a dict, skipping", idx)
            continue

        slug = raw.get("slug")
        if not slug:
            logger.warning("[RECURRENCE] entry #%d missing slug, skipping", idx)
            continue

        prompt = raw.get("prompt")
        if not prompt or not str(prompt).strip():
            logger.warning(
                "[RECURRENCE] entry '%s' missing prompt, skipping", slug
            )
            continue

        # ``schedule`` may be null (reactive), a string (single cron or
        # semantic), or a list of strings (multiple fires per day —
        # ADR-268 §D8). Normalize to one of: None | str | list[str].
        schedule_raw = raw.get("schedule")
        schedule: Schedule
        if schedule_raw is None:
            schedule = None
        elif isinstance(schedule_raw, list):
            cleaned = [str(s).strip() for s in schedule_raw if s and str(s).strip()]
            schedule = cleaned if cleaned else None
            if schedule and len(cleaned) == 1:
                # Singleton lists collapse to plain string — uniform
                # downstream handling, no special-cased branches.
                schedule = cleaned[0]
        elif str(schedule_raw).strip():
            schedule = str(schedule_raw).strip()
        else:
            schedule = None

        # ``paused_until``: ISO-8601 string or datetime
        paused_until = _coerce_datetime(raw.get("paused_until"))

        # ADR-263: ``mode`` declares wake intent at authoring time.
        # Default to "judgment" when absent (legacy entries) for backward
        # compatibility. Coerce invalid values to default + log warning.
        mode_raw = raw.get("mode") or DEFAULT_RECURRENCE_MODE
        mode = str(mode_raw).strip().lower()
        if mode not in RECURRENCE_MODES:
            logger.warning(
                "[RECURRENCE] entry '%s' has invalid mode=%r — coercing to %r",
                slug, mode_raw, DEFAULT_RECURRENCE_MODE,
            )
            mode = DEFAULT_RECURRENCE_MODE

        # ``options`` is everything else the operator put in the entry
        # (display_name, description, etc.) — optional metadata only.
        options = {
            k: v
            for k, v in raw.items()
            if k not in {"slug", "schedule", "prompt", "mode", "paused", "paused_until"}
        }

        out.append(
            Recurrence(
                slug=str(slug),
                schedule=schedule,
                prompt=str(prompt).strip(),
                mode=mode,
                paused=bool(raw.get("paused", False)),
                paused_until=paused_until,
                options=options,
                user_id=user_id,
                last_modified=last_modified,
            )
        )

    return out


def _coerce_datetime(v: Any) -> Optional[datetime]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    if isinstance(v, str):
        try:
            d = datetime.fromisoformat(v.replace("Z", "+00:00"))
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            logger.warning("[RECURRENCE] invalid datetime value: %r", v)
            return None
    return None


# ---------------------------------------------------------------------------
# Workspace walker
# ---------------------------------------------------------------------------


def walk_workspace_recurrences(client, user_id: str) -> list[Recurrence]:
    """Read ``/workspace/_recurrences.yaml`` for a user and return the
    parsed entries.

    Per ADR-261 D2 there is one canonical file per workspace. Returns an
    empty list if the file doesn't exist or is empty.
    """
    if client is None:
        return []

    try:
        result = (
            client.table("workspace_files")
            .select("content,updated_at")
            .eq("user_id", user_id)
            .eq("path", RECURRENCES_PATH)
            .limit(1)
            .execute()
        )
    except Exception as e:
        logger.error(
            "[RECURRENCE] read failed for user=%s: %s", user_id[:8], e
        )
        return []

    rows = result.data or []
    if not rows:
        return []

    content = rows[0].get("content") or ""
    last_modified = _coerce_datetime(rows[0].get("updated_at"))
    return parse_recurrences_yaml(
        content, user_id=user_id, last_modified=last_modified
    )


# ---------------------------------------------------------------------------
# Scheduling — next-run computation
# ---------------------------------------------------------------------------


def compute_next_run_at(
    rec: Recurrence, now: Optional[datetime] = None
) -> Optional[datetime]:
    """Compute the next firing time after ``now`` for this recurrence.

    Returns None for reactive recurrences (no schedule) or paused
    recurrences. Uses ``croniter`` for cron expression parsing — same
    library the scheduler uses.
    """
    if rec.paused or not rec.schedule:
        return None

    try:
        from croniter import croniter
    except ImportError:
        logger.warning("[RECURRENCE] croniter not available — cannot compute next_run_at")
        return None

    base = now or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)

    try:
        cron = croniter(rec.schedule, base)
        return cron.get_next(datetime)
    except Exception as e:
        logger.warning(
            "[RECURRENCE] invalid schedule %r for %s: %s",
            rec.schedule, rec.slug, e,
        )
        return None


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def serialize_recurrences_yaml(recurrences: list[Recurrence]) -> str:
    """Serialize a list of recurrences back to ``_recurrences.yaml`` body.

    Output is a flat YAML list (top-level), preserving operator-legibility
    field order: slug, schedule, prompt, paused, paused_until, then any
    options keys.
    """
    if not recurrences:
        return "[]\n"

    out = []
    for rec in recurrences:
        entry = {"slug": rec.slug, "schedule": rec.schedule}
        # ADR-263: emit `mode` only when non-default to keep legacy YAML clean.
        # Operator-edited files that don't carry `mode` re-serialize without it.
        if rec.mode != DEFAULT_RECURRENCE_MODE:
            entry["mode"] = rec.mode
        entry["prompt"] = rec.prompt
        if rec.paused:
            entry["paused"] = True
        if rec.paused_until:
            entry["paused_until"] = rec.paused_until.isoformat()
        # Append options keys in insertion order
        for k, v in rec.options.items():
            entry[k] = v
        out.append(entry)

    return yaml.safe_dump(
        out,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=80,
    )


__all__ = [
    "Recurrence",
    "parse_recurrences_yaml",
    "walk_workspace_recurrences",
    "compute_next_run_at",
    "serialize_recurrences_yaml",
    "RECURRENCES_PATH",  # re-exported for caller convenience
    "RECURRENCE_MODES",  # ADR-263
    "DEFAULT_RECURRENCE_MODE",  # ADR-263
    "is_valid_mode",  # ADR-263
]
