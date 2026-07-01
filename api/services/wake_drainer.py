"""ADR-298 Phase 3 — Wake queue drainer.

This module is the **single execution path** for wakes after Phase 3's
Singular Implementation cutover. The lifecycle:

  enqueue (services/wake.py::submit_wake_proposal)
      → wake_queue row in 'pending' status
      → drain_next_for_user (this module)
          → respects pace cap on paced lane
          → acquires single-in-flight lock via wake_queue.try_lock
          → reconstructs payload (Recurrence / hook dict / proposal row)
          → dispatches to the source-specific Reviewer invocation body
            in services/wake.py (the existing _invoke_*_wake helpers,
            unchanged — only their call sites moved)
          → marks the queue row completed/failed with execution_event FK

The drainer is called by:
  - api/jobs/unified_scheduler.py (cron-tick + substrate-event cycle —
    after walker enqueues, drainer runs until queue is empty or pace cap
    is hit).
  - services/wake.py::stream_addressed_wake (Option α — addressed turns
    wait for lock by polling drain_can_acquire_for_user, then drain
    themselves).

Per ADR-298 D2 the queue is transient compute, not state. This drainer
does not persist its own state — every decision derives from wake_queue
+ filesystem substrate.

Per ADR-298 D3 the paced lane is throttled by pace; the live lane is
unrestricted. Both lanes share the single-in-flight constraint per
workspace.
"""

from __future__ import annotations

import logging
import os
import socket
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Scheduler instance ID (for locked_by attribution)
# ---------------------------------------------------------------------------


_INSTANCE_ID = os.environ.get("RENDER_INSTANCE_ID") or socket.gethostname()


def instance_id() -> str:
    """Return a stable identifier for this scheduler/api process."""
    return _INSTANCE_ID


# ---------------------------------------------------------------------------
# Single-in-flight check
# ---------------------------------------------------------------------------
#
# ADR-327 D5: the pace-driven `paced_lane_eligible_to_drain` throttle is
# DELETED. The paced/live lane split existed only to serve the pace drain
# rate. With pace retired, the drainer is lane-agnostic: it drains FIFO,
# bounded by the single-in-flight constraint (one Reviewer per workspace at
# a time — no concurrency stampede) and the window-budget gate (Tier-1 +
# wake.py Gate 1 — no overspend). The per-slug min-interval floor prevents
# per-recurrence thrash. Together these fully cover what the throttle did;
# stampede verification confirmed sequential single-in-flight + budget ceiling
# is sufficient (ADR-327 D5 + §5 Q1).


def drain_can_acquire_for_user(client, user_id: str) -> bool:
    """ADR-298 D1: returns True if no wake is currently locked for this
    workspace. Caller (drainer + addressed-SSE wait loop) consults this
    before attempting to drain/acquire.

    Note: there is a race between this check and the subsequent try_lock —
    that race is resolved by wake_queue.try_lock's CAS guard (it only
    transitions pending→locked if status is still pending). This helper
    is for cheap early-exit, not exclusion.
    """
    from services.wake_queue import has_in_flight

    return not has_in_flight(client, user_id=user_id)


# ---------------------------------------------------------------------------
# Drain one wake (the core loop body)
# ---------------------------------------------------------------------------


async def drain_next_for_user(
    client,
    user_id: str,
) -> Optional[dict]:
    """Pull the next pending wake for this workspace and execute it.

    Returns the execution result dict (the same shape the legacy
    _invoke_*_wake helpers returned), or None if there was nothing
    eligible to drain.

    The execution path (ADR-327 D5 — lane-agnostic):
      1. Check single-in-flight constraint (D1). If a wake is locked,
         return None — caller decides whether to wait or move on.
      2. Pull the oldest pending wake (FIFO, no lane scoping); attempt
         lock-acquire.
      3. Reconstruct the source-specific payload and dispatch to the
         Reviewer invocation body in services/wake.py.
      4. Mark queue row completed (or failed) with execution_event FK.

    Cost is bounded downstream by the window-budget gate (wake.py Gate 1);
    the per-slug min-interval floor prevents per-recurrence thrash; the
    single-in-flight constraint prevents concurrency. No pace throttle.
    """
    from services.wake_queue import (
        get_next_pending,
        try_lock,
        mark_completed,
        mark_failed,
    )

    # D1 — single-in-flight.
    if not drain_can_acquire_for_user(client, user_id):
        return None

    pending = get_next_pending(client, user_id=user_id)
    if not pending:
        return None

    queue_id = pending["id"]
    inst = instance_id()
    if not try_lock(client, queue_id=queue_id, instance_id=inst):
        # Another instance won the race; let it proceed.
        return None

    wake_source = pending["wake_source"]
    payload = pending.get("payload") or {}

    # Dispatch to the source-specific Reviewer invocation body. The
    # bodies live in services/wake.py — they were already there before
    # Phase 3; only the call site moved (used to be inline within
    # submit_wake_proposal; now drainer-called).
    result: dict = {"success": False, "message": "drain dispatch not implemented"}
    execution_event_id: Optional[str] = None
    try:
        result = await _dispatch_drained_wake(
            client, user_id, wake_source=wake_source, payload=payload,
        )
        execution_event_id = result.get("execution_event_id")
    except Exception as exc:
        logger.exception(
            "[drain:%s] dispatch raised for %s/%s: %s",
            user_id[:8], wake_source, pending.get("slug", "?"), exc,
        )
        result = {
            "success": False,
            "error": "dispatch_exception",
            "message": str(exc),
        }

    if result.get("success"):
        mark_completed(client, queue_id=queue_id, execution_event_id=execution_event_id)
    else:
        mark_failed(client, queue_id=queue_id, execution_event_id=execution_event_id)

    return result


async def _dispatch_drained_wake(
    client,
    user_id: str,
    *,
    wake_source: str,
    payload: dict,
) -> dict:
    """Reconstruct payload + call the source-specific Reviewer body.

    Each wake source serializes its dispatch payload at enqueue time;
    here we deserialize and call the body. The bodies live in
    services/wake.py — they are the same code paths that ran inline
    pre-Phase 3, only the call site moved.
    """
    from services.wake import (
        _invoke_recurrence_wake,
        _invoke_substrate_event_wake,
    )

    if wake_source in ("cron_tick", "manual_fire"):
        # Recurrence payload: {"recurrence_data": {...}, "context": str|None}
        from services.recurrence import Recurrence
        rec_data = payload.get("recurrence_data") or {}
        recurrence = Recurrence(
            slug=rec_data.get("slug", ""),
            schedule=rec_data.get("schedule"),
            prompt=rec_data.get("prompt", ""),
            # ADR-393: `mode` removed — recurrences are judgment-only.
        )
        # Restore fields not in the bare dataclass constructor.
        if "paused" in rec_data:
            recurrence.paused = bool(rec_data["paused"])
        if "options" in rec_data and isinstance(rec_data["options"], dict):
            recurrence.options = dict(rec_data["options"])
        return await _invoke_recurrence_wake(
            client, user_id,
            recurrence=recurrence,
            wake_source=wake_source,  # type: ignore[arg-type]
            context=payload.get("context"),
        )

    if wake_source == "substrate_event":
        return await _invoke_substrate_event_wake(
            client, user_id,
            hook=payload.get("hook") or {},
            path=payload.get("path") or "",
            field_change=payload.get("field_change") or {},
            revision_id=payload.get("revision_id"),
        )

    if wake_source == "proposal_arrival":
        # proposal_arrival dispatches through the existing event-driven path
        # in services/review_proposal_dispatch.py — same shape as pre-Phase-3
        # submit_wake_proposal branch.
        from services.review_proposal_dispatch import on_proposal_created
        proposal_row = payload.get("proposal_row") or {}
        proposal_id = proposal_row.get("id") or payload.get("proposal_id") or ""
        await on_proposal_created(
            client, user_id,
            proposal_id=proposal_id,
            proposal_row=proposal_row,
        )
        return {
            "success": True,
            "source": "proposal_arrival",
            "proposal_id": proposal_id,
            "funnel_decision": "escalate",
        }

    # addressed is handled by stream_addressed_wake's own drain loop
    # (Option α) — it never reaches this drainer dispatch.
    return {
        "success": False,
        "error": "unsupported_drain_source",
        "message": f"drainer does not dispatch source={wake_source!r}",
    }


# ---------------------------------------------------------------------------
# Drain loop for the scheduler tick
# ---------------------------------------------------------------------------


async def drain_user_until_empty(
    client,
    user_id: str,
    *,
    max_iterations: int = 100,
) -> int:
    """Drain pending wakes for a single user until the queue is empty.
    Returns count of wakes drained.

    Bounded by max_iterations to prevent runaway loops on misbehavior.
    The natural exit is "no more pending wakes." Cost is bounded by the
    window-budget gate inside each drain (ADR-327), not by a drain-rate cap.
    """
    count = 0
    for _ in range(max_iterations):
        result = await drain_next_for_user(client, user_id)
        if result is None:
            break
        count += 1
    return count


async def drain_all_users_with_pending(
    client,
    *,
    max_iterations_per_user: int = 100,
) -> int:
    """Find every workspace with pending wakes and drain each one.
    Returns total wakes drained across all users.

    The scheduler tick calls this after walker has enqueued cron-tick
    + substrate-event wakes. It's the closing step of every scheduler
    cycle.
    """
    try:
        result = (
            client.table("wake_queue")
            .select("user_id")
            .eq("status", "pending")
            .execute()
        )
    except Exception as exc:
        logger.warning("[drain] failed to query pending users: %s", exc)
        return 0

    user_ids = {row["user_id"] for row in (result.data or [])}
    total = 0
    for user_id in user_ids:
        try:
            total += await drain_user_until_empty(
                client, user_id,
                max_iterations=max_iterations_per_user,
            )
        except Exception as exc:
            logger.exception(
                "[drain] drain_user_until_empty raised for %s: %s",
                user_id[:8], exc,
            )
    return total
