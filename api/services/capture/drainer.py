"""
Capture drainer (ADR-393) — the scheduler-tick maintenance phase for captures.

Walks due capture rows, CAS-claims each, runs it through the capture lane, and
advances the index. This is the capture analogue of
``jobs.unified_scheduler.dispatch_due_invocations`` (recurrences) — but it does
NOT go through the wake funnel: captures are deterministic, wake no one, and
run in the scheduler tick's maintenance phase, sibling to
``services.kernel_mirrors`` + ``services.wake_drainer`` (the proven precedent
for scheduler-side mechanical work).

Called once per tick from ``run_unified_scheduler`` inside the AGENT_ENABLED
gate (a capture makes substrate the steward reads at wake — pointless when the
steward never wakes; same gate as the recurrence dispatch + kernel mirrors).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def drain_due_captures(client) -> tuple[int, int, int]:
    """Find due captures and run each one through the capture lane.

    Returns (found, succeeded, failed). Mirrors dispatch_due_invocations'
    CAS-claim → run → record shape, but the "run" is deterministic lane
    execution (zero LLM), not a wake proposal.
    """
    from services.capture.scheduling import (
        claim_capture_run,
        get_due_captures,
        record_capture_run,
    )
    from services.capture.lane import run_capture_declaration

    now = datetime.now(timezone.utc)
    pairs = await get_due_captures(client, now=now)
    found = len(pairs)
    if found == 0:
        return 0, 0, 0

    succeeded = 0
    failed = 0

    for user_id, declaration in pairs:
        # CAS claim — read baseline next_run_at, atomically bump to sentinel so
        # concurrent scheduler instances skip the claimed row.
        try:
            row = (
                client.table("tasks")
                .select("next_run_at")
                .eq("user_id", user_id)
                .eq("slug", declaration.slug)
                .eq("kind", "capture")
                .limit(1)
                .execute()
            )
            original_next_run = row.data[0]["next_run_at"] if row.data else None
        except Exception as e:
            logger.warning(
                "[CAPTURE_DRAIN] could not read baseline next_run_at for %s/%s: %s",
                user_id[:8], declaration.slug, e,
            )
            failed += 1
            continue

        if not claim_capture_run(client, user_id, declaration.slug, original_next_run):
            logger.info(
                "[CAPTURE_DRAIN] %s/%s already claimed by another instance; skipping",
                user_id[:8], declaration.slug,
            )
            continue

        try:
            result = await run_capture_declaration(client, user_id, declaration)
            if result.get("success"):
                succeeded += 1
            else:
                failed += 1
                logger.info(
                    "[CAPTURE_DRAIN] ✗ %s/%s: %s",
                    user_id[:8], declaration.slug, result.get("error_reason", "?"),
                )
        except Exception as e:
            failed += 1
            logger.exception(
                "[CAPTURE_DRAIN] capture run raised for %s/%s: %s",
                user_id[:8], declaration.slug, e,
            )
        finally:
            # Always advance next_run_at — clears the sentinel even on failure
            # so the capture doesn't get stuck.
            try:
                record_capture_run(
                    client, user_id, declaration,
                    last_run_at=datetime.now(timezone.utc),
                )
            except Exception as e:
                logger.warning(
                    "[CAPTURE_DRAIN] record_capture_run failed for %s/%s: %s",
                    user_id[:8], declaration.slug, e,
                )

    return found, succeeded, failed


__all__ = ["drain_due_captures"]
