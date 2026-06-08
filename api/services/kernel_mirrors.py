"""
Kernel mirrors — per-tick maintenance phase helpers (ADR-301 D4).

The Reviewer's wake envelope (ADR-274 + ADR-276 + ADR-281 + ADR-284 +
ADR-301) needs two compact substrate files mirrored from the system's
own scheduling index + execution_events ledger:

- /workspace/system/_schedule_index.md — projects `tasks` rows + each
  recurrence's literal `schedule:` string + last_run_at + next_run_at +
  paused flag. The Reviewer reads this to reason correctly about its own
  cadence.
- /workspace/system/_recent_execution.md — projects last-24h
  `execution_events` into a deterministic markdown rollup. The Reviewer
  reads this to know what has actually fired and with what outcome.

Both mirrors are diff-aware (no revision noise on no-op ticks). They run
per scheduler tick across every workspace via the helpers below. Same
precedent as `wake_queue.reclaim_stale_locks` + `wake_drainer.drain_all_
users_with_pending`: kernel maintenance runs in the scheduler tick's
maintenance phase, not as workspace-side recurrences.

Why not a kernel-universal `_recurrences.yaml` entry per ADR-285 D4? Two
reasons:

1. Kernel maintenance is scheduler-side by precedent. `reclaim_stale_locks`
   doesn't enqueue itself as a wake_queue row; neither should the kernel
   mirrors. Keeps kernel/program separation clean.
2. Scaffolding a kernel-universal recurrence at workspace-init would add a
   workspace_init responsibility (`_kernel_recurrences.yaml` write) that
   doesn't exist today and that no other ADR has needed. Avoiding new
   moving parts when an existing pattern works.

Error isolation: each per-workspace mirror runs in its own try/except. One
workspace's mirror failure does not block others. Telemetry is logged but
not surfaced into `execution_events` (these are kernel ops, not workspace
work).
"""

from __future__ import annotations

import logging
from typing import Any

from services.primitives.mirror_schedule_index import handle_mirror_schedule_index
from services.primitives.mirror_recent_execution import handle_mirror_recent_execution
from services.primitives.mirror_calibration import handle_mirror_calibration

logger = logging.getLogger(__name__)


class _MirrorAuth:
    """Auth shape for primitive handlers. Matches the `_MechanicalAuth`
    pattern from `services.wake.py` — caller_identity carries the ADR-209
    attribution string default, but the mirror primitives override with
    their own specific actor name (`system:mirror-schedule-index`,
    `system:mirror-recent-execution`) so attribution stays narrow."""

    def __init__(self, user_id: str, client: Any, caller_identity: str):
        self.user_id = user_id
        self.client = client
        self.caller_identity = caller_identity


def _list_active_workspaces(client: Any) -> list[str]:
    """Return user_ids of workspaces with at least one active recurrence
    OR at least one recent execution_events row in the last 24h. We bound
    the set to workspaces likely to benefit from a refreshed mirror.

    A workspace with neither active recurrences nor recent executions will
    have both mirrors generate "empty state" content — write-once via
    diff-aware skip — so the cost of including it is bounded.
    """
    try:
        res = (
            client.table("tasks")
            .select("user_id")
            .neq("status", "archived")
            .execute()
        )
    except Exception as exc:
        logger.warning("[KERNEL_MIRRORS] tasks query failed: %s", exc)
        return []
    user_ids: set[str] = set()
    for row in res.data or []:
        uid = row.get("user_id")
        if uid:
            user_ids.add(uid)
    return sorted(user_ids)


async def mirror_schedule_index_for_all_users(client: Any) -> dict:
    """Run MirrorScheduleIndex once per active workspace. Returns a summary
    dict with counts. Error per workspace is logged, not raised — one
    workspace's failure does not block others."""
    user_ids = _list_active_workspaces(client)
    written = 0
    skipped = 0
    failed = 0
    for user_id in user_ids:
        auth = _MirrorAuth(
            user_id=user_id, client=client,
            caller_identity="system:mirror-schedule-index",
        )
        try:
            result = await handle_mirror_schedule_index(auth, {"diff_aware": True})
            if result.get("success"):
                if result.get("paths_written"):
                    written += 1
                if result.get("paths_skipped"):
                    skipped += 1
            else:
                failed += 1
                logger.warning(
                    "[KERNEL_MIRRORS:schedule_index] user=%s failed: %s",
                    user_id[:8], result.get("error"),
                )
        except Exception as exc:
            failed += 1
            logger.warning(
                "[KERNEL_MIRRORS:schedule_index] user=%s exception: %s",
                user_id[:8], exc,
            )
    return {
        "users_processed": len(user_ids),
        "written": written,
        "skipped": skipped,
        "failed": failed,
    }


async def mirror_recent_execution_for_all_users(client: Any) -> dict:
    """Run MirrorRecentExecution once per active workspace. Returns a
    summary dict with counts. Error isolation same as above."""
    user_ids = _list_active_workspaces(client)
    written = 0
    skipped = 0
    failed = 0
    for user_id in user_ids:
        auth = _MirrorAuth(
            user_id=user_id, client=client,
            caller_identity="system:mirror-recent-execution",
        )
        try:
            result = await handle_mirror_recent_execution(
                auth, {"diff_aware": True, "window_hours": 24}
            )
            if result.get("success"):
                if result.get("paths_written"):
                    written += 1
                if result.get("paths_skipped"):
                    skipped += 1
            else:
                failed += 1
                logger.warning(
                    "[KERNEL_MIRRORS:recent_execution] user=%s failed: %s",
                    user_id[:8], result.get("error"),
                )
        except Exception as exc:
            failed += 1
            logger.warning(
                "[KERNEL_MIRRORS:recent_execution] user=%s exception: %s",
                user_id[:8], exc,
            )
    return {
        "users_processed": len(user_ids),
        "written": written,
        "skipped": skipped,
        "failed": failed,
    }


async def mirror_calibration_for_all_users(client: Any) -> dict:
    """Run MirrorCalibration once per active workspace (ADR-327 D6 —
    the self-improving loop). Correlates each workspace's cadence-authoring
    history against ground-truth outcome quality, writing calibration
    evidence the Reviewer reads before reasoning about cadence. Error
    isolation same as the sibling mirrors."""
    user_ids = _list_active_workspaces(client)
    written = 0
    skipped = 0
    failed = 0
    for user_id in user_ids:
        auth = _MirrorAuth(
            user_id=user_id, client=client,
            caller_identity="system:mirror-calibration",
        )
        try:
            result = await handle_mirror_calibration(
                auth, {"diff_aware": True, "window_days": 14}
            )
            if result.get("success"):
                if result.get("paths_written"):
                    written += 1
                if result.get("paths_skipped"):
                    skipped += 1
            else:
                failed += 1
                logger.warning(
                    "[KERNEL_MIRRORS:calibration] user=%s failed: %s",
                    user_id[:8], result.get("error"),
                )
        except Exception as exc:
            failed += 1
            logger.warning(
                "[KERNEL_MIRRORS:calibration] user=%s exception: %s",
                user_id[:8], exc,
            )
    return {
        "users_processed": len(user_ids),
        "written": written,
        "skipped": skipped,
        "failed": failed,
    }
