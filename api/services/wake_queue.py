"""ADR-298 — Reviewer wake queue service module.

The queue is **transient compute + deterministic enforcement, not authoritative
state** per ADR-298 D2 (Critical classification per Axiom 1). Modeled on
the `tasks` scheduling-index precedent (ADR-231 D4): mechanically
reconstructable from filesystem state + DB telemetry at every moment.

This module provides the canonical interface to the wake_queue table.
All five wake sources enqueue here; the scheduler drainer pulls
next-eligible rows respecting lane + single-in-flight semantics.

ADR-298 phases:
- Phase 1 (this commit): table + service helpers + test gate.
  No production callers yet.
- Phase 2: pace substrate + Schedule primitive gate.
- Phase 3: enqueue refactor — all five wake sources cut over to
  this module (Singular Implementation cutover; no dual paths).
- Phase 4: bundle minimum_pace + activation gate.
- Phase 5: cockpit FE + canary + status flip.

Per ADR-298 D6: cross-source dedup uses (user_id, wake_source, dedup_key)
UNIQUE constraint. Per-source dedup-key derivation lives in the wake
sources themselves (`wake_sources/*.py`), passed in here as the
`dedup_key` arg.

Per ADR-298 D3: lane is 'paced' for cron_tick judgment recurrences,
'live' for everything else. The lane determines drain rate, not
concurrency — both lanes share the single-in-flight-per-workspace
constraint.

References:
- docs/adr/ADR-298-reviewer-wake-queue-and-pace.md (canonical spec)
- supabase/migrations/179_wake_queue.sql (table definition)
- docs/architecture/FOUNDATIONS.md Axiom 1 (filesystem-is-substrate)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ─── Constants ──────────────────────────────────────────────────────────────


VALID_WAKE_SOURCES = frozenset({
    "cron_tick",
    "addressed",
    "substrate_event",
    "proposal_arrival",
    "manual_fire",
})

VALID_LANES = frozenset({"paced", "live"})

VALID_STATUSES = frozenset({
    "pending", "locked", "completed", "failed", "dropped",
})

# Default stale-lock threshold per ADR-298 §8. Empirically chosen as
# 2× p95 of current execution_events.duration_ms; population shows
# sessions 30-75s with p95 ≈ 75s → 150s baseline. Round to 180s for
# safety margin. Re-tune from production telemetry post-cutover.
DEFAULT_STALE_LOCK_SECONDS = 180

# Default GC threshold per ADR-298 D2. Completed/failed/dropped rows
# older than this are deleted by the back-office maintenance task.
DEFAULT_GC_DAYS = 7


# ─── Errors ─────────────────────────────────────────────────────────────────


class WakeQueueError(Exception):
    """Base class for wake_queue errors."""


class InvalidWakeSourceError(WakeQueueError):
    """Raised when wake_source is not in the canonical enum."""


class InvalidLaneError(WakeQueueError):
    """Raised when lane is not 'paced' or 'live'."""


# ─── Lane resolution ────────────────────────────────────────────────────────


# Per ADR-298 D3 — table mapping wake sources to lanes.
_WAKE_SOURCE_TO_LANE = {
    "cron_tick":        "paced",
    "addressed":        "live",
    "substrate_event":  "live",
    "proposal_arrival": "live",
    "manual_fire":      "live",
}


def resolve_lane(wake_source: str) -> str:
    """ADR-298 D3: cron_tick → paced; everything else → live."""
    if wake_source not in VALID_WAKE_SOURCES:
        raise InvalidWakeSourceError(
            f"Unknown wake_source: {wake_source!r}. "
            f"Must be one of {sorted(VALID_WAKE_SOURCES)}."
        )
    return _WAKE_SOURCE_TO_LANE[wake_source]


# ─── Enqueue ────────────────────────────────────────────────────────────────


def enqueue(
    client,
    *,
    user_id: str,
    wake_source: str,
    payload: dict,
    dedup_key: Optional[str] = None,
    slug: Optional[str] = None,
) -> Optional[str]:
    """Insert a wake into the queue. Returns inserted row id, or None if
    silently dropped by the UNIQUE constraint (cross-source dedup hit).

    Per ADR-298 D6: dedup_key is per-source (revision_id for substrate_event,
    '<slug>:<minute>' for cron_tick, message_id for addressed, etc.). The
    UNIQUE (user_id, wake_source, dedup_key) constraint enforces single-
    fire at insert time. NULL dedup_key (manual_fire only) bypasses
    dedup by design.

    The caller (each wake source's submit path) derives the dedup_key
    from its source-of-truth (revision_id from workspace_file_versions,
    message_id from session_messages, etc.). This module does not derive
    dedup_keys — it only enforces them.
    """
    if wake_source not in VALID_WAKE_SOURCES:
        raise InvalidWakeSourceError(
            f"Unknown wake_source: {wake_source!r}. "
            f"Must be one of {sorted(VALID_WAKE_SOURCES)}."
        )

    lane = resolve_lane(wake_source)
    row = {
        "user_id": user_id,
        "wake_source": wake_source,
        "lane": lane,
        "slug": slug,
        "payload": payload,
        "dedup_key": dedup_key,
        "status": "pending",
    }

    try:
        result = client.table("wake_queue").insert(row).execute()
    except Exception as exc:
        # Postgres UNIQUE constraint violation surfaces here. Supabase
        # client wraps it; the contract is "if dedup hit, return None
        # silently" — the same contract walk_hooks already relies on
        # at the wake_dedup_key column per ADR-272.
        message = str(exc).lower()
        if "wake_queue_dedup_unique" in message or "duplicate key" in message:
            logger.debug(
                "[wake_queue] dedup hit user=%s source=%s key=%s",
                user_id[:8], wake_source, dedup_key,
            )
            return None
        raise

    if not result.data:
        return None
    return result.data[0]["id"]


# ─── Next-pending lookup ────────────────────────────────────────────────────


def get_next_pending(
    client,
    *,
    user_id: str,
    lane: Optional[str] = None,
) -> Optional[dict]:
    """Return the oldest pending row for this user, optionally scoped to
    a specific lane. Used by the drainer to decide what to lock next.

    When lane is None, returns the oldest pending row across both lanes
    (the drainer uses lane-specific lookups separately — paced lane is
    gated by pace drain rate, live lane is unrestricted).

    Does NOT acquire a lock — caller must follow up with try_lock()
    to atomically claim the row.
    """
    if lane is not None and lane not in VALID_LANES:
        raise InvalidLaneError(
            f"Unknown lane: {lane!r}. Must be one of {sorted(VALID_LANES)}."
        )

    query = (
        client.table("wake_queue")
        .select("*")
        .eq("user_id", user_id)
        .eq("status", "pending")
        .order("enqueued_at", desc=False)
        .limit(1)
    )
    if lane is not None:
        query = query.eq("lane", lane)

    result = query.execute()
    if not result.data:
        return None
    return result.data[0]


def has_in_flight(client, *, user_id: str) -> bool:
    """ADR-298 D1: single-in-flight constraint per workspace. Returns
    True if any locked row exists for this user. The drainer must check
    this before starting a new wake.
    """
    result = (
        client.table("wake_queue")
        .select("id")
        .eq("user_id", user_id)
        .eq("status", "locked")
        .limit(1)
        .execute()
    )
    return bool(result.data)


# ─── Lock / complete / fail / drop ──────────────────────────────────────────


def try_lock(
    client,
    *,
    queue_id: str,
    instance_id: str,
) -> bool:
    """Atomically transition a row from 'pending' to 'locked'. Returns
    True if this caller acquired the lock, False if another instance
    raced and won (the WHERE-clause CAS naturally handles concurrent
    drainer instances).
    """
    result = (
        client.table("wake_queue")
        .update({
            "status": "locked",
            "locked_at": datetime.now(timezone.utc).isoformat(),
            "locked_by": instance_id,
        })
        .eq("id", queue_id)
        .eq("status", "pending")  # CAS guard — only locks if still pending
        .execute()
    )
    return bool(result.data)


def mark_completed(
    client,
    *,
    queue_id: str,
    execution_event_id: Optional[str] = None,
) -> None:
    """Transition a locked row to 'completed'. Pairs the queue entry
    to its execution_events row for audit traceability."""
    client.table("wake_queue").update({
        "status": "completed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "execution_event_id": execution_event_id,
    }).eq("id", queue_id).execute()


def mark_failed(
    client,
    *,
    queue_id: str,
    execution_event_id: Optional[str] = None,
) -> None:
    """Transition a locked row to 'failed'. Same shape as mark_completed
    but distinguishes execution-failure from happy-path completion in
    drainer telemetry."""
    client.table("wake_queue").update({
        "status": "failed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "execution_event_id": execution_event_id,
    }).eq("id", queue_id).execute()


def mark_dropped(client, *, queue_id: str, reason: str) -> None:
    """Transition a pending row to 'dropped'. Used for pace-cap drops
    (ADR-298 D9), manual GC, or admin actions. reason persists into
    the payload for audit."""
    # Read payload, append reason, write back.
    existing = (
        client.table("wake_queue")
        .select("payload")
        .eq("id", queue_id)
        .single()
        .execute()
    )
    payload = (existing.data or {}).get("payload", {}) or {}
    payload["_drop_reason"] = reason
    client.table("wake_queue").update({
        "status": "dropped",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }).eq("id", queue_id).execute()


# ─── Stale-lock reclaim (Scenario J) ────────────────────────────────────────


def reclaim_stale_locks(
    client,
    *,
    threshold_seconds: int = DEFAULT_STALE_LOCK_SECONDS,
) -> int:
    """Reset 'locked' rows whose locked_at is older than threshold back
    to 'pending' for re-execution. Returns count of rows reclaimed.

    ADR-298 Scenario J: scheduler instance crashes mid-wake → lock
    stays held. Next scheduler tick sweeps stale locks and reclaims
    them. Idempotent — running multiple times in succession is safe.
    """
    cutoff = (
        datetime.now(timezone.utc) - timedelta(seconds=threshold_seconds)
    ).isoformat()
    result = (
        client.table("wake_queue")
        .update({
            "status": "pending",
            "locked_at": None,
            "locked_by": None,
        })
        .eq("status", "locked")
        .lt("locked_at", cutoff)
        .execute()
    )
    count = len(result.data or [])
    if count > 0:
        logger.warning(
            "[wake_queue] reclaimed %d stale lock(s) older than %ds",
            count, threshold_seconds,
        )
    return count


# ─── GC sweep ───────────────────────────────────────────────────────────────


def gc_completed(client, *, older_than_days: int = DEFAULT_GC_DAYS) -> int:
    """Delete completed/failed/dropped rows older than threshold.
    Returns count deleted. Called by the back-office maintenance task
    per ADR-298 D2 (7d retention mirroring execution_events).
    """
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=older_than_days)
    ).isoformat()
    result = (
        client.table("wake_queue")
        .delete()
        .in_("status", ["completed", "failed", "dropped"])
        .lt("completed_at", cutoff)
        .execute()
    )
    count = len(result.data or [])
    if count > 0:
        logger.info(
            "[wake_queue] gc swept %d row(s) older than %dd",
            count, older_than_days,
        )
    return count


# ─── Inspect (telemetry only — operators read substrate, not queue) ─────────


def queue_depth(
    client,
    *,
    user_id: str,
    lane: Optional[str] = None,
) -> int:
    """Count pending rows for a user, optionally scoped to a lane.
    For cockpit telemetry only — the queue is not operator-readable
    substrate per ADR-298 D2. This helper exists so the FE can render
    'paced lane: 3 pending' without leaking queue internals.
    """
    if lane is not None and lane not in VALID_LANES:
        raise InvalidLaneError(
            f"Unknown lane: {lane!r}. Must be one of {sorted(VALID_LANES)}."
        )

    query = (
        client.table("wake_queue")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("status", "pending")
    )
    if lane is not None:
        query = query.eq("lane", lane)

    result = query.execute()
    return result.count or 0
