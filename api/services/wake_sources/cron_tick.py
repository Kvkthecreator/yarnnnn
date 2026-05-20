"""
services/wake_sources/cron_tick.py — Cron-tick wake source (ADR-296 v2 D1).

The scheduler walks `/workspace/_recurrences.yaml` declarations + the
thin `tasks` scheduling index for due rows, then submits one wake
proposal per due recurrence to the singular funnel.

Caller: `jobs/unified_scheduler.py` (every ~5 minutes). The scheduler
remains thin per ADR-261 D3 — it computes "which recurrences are due"
and hands each one to `dispatch_recurrence()`. The funnel decides
whether the wake escalates to the Reviewer's full cycle.

ADR-296 v2 D2 — funnel decisions for cron-tick wakes:
  - mechanical-mode recurrence → "mechanical" (deterministic Python; no Reviewer)
  - judgment-mode + budget OK + ambiguous freshness → "tier_2" (Haiku gate)
  - judgment-mode + kernel gate failed → "skip" (balance/spend/cap/min-interval)
  - judgment-mode + clean → "escalate" (Reviewer full cycle)
"""

from __future__ import annotations

import logging
from typing import Optional

from services.recurrence import Recurrence
from services.wake import submit_wake_proposal

logger = logging.getLogger(__name__)


async def dispatch_recurrence(
    client,
    user_id: str,
    recurrence: Recurrence,
    *,
    context: Optional[str] = None,
) -> dict:
    """Submit a wake proposal for a cron-tick-fired recurrence.

    This is the singular entry point the scheduler uses. The funnel
    decides whether the wake escalates to the Reviewer's full cycle.

    Args:
        client: Supabase service client
        user_id: Workspace owner UUID
        recurrence: parsed Recurrence to fire (judgment or mechanical mode)
        context: optional one-shot steering (appended to the recurrence's
                 prompt; does not mutate the recurrence record)

    Returns:
        WakeOutcome dict per services.wake.submit_wake_proposal contract.
    """
    return await submit_wake_proposal(
        client, user_id,
        source="cron_tick",
        payload={"recurrence": recurrence, "context": context},
    )


__all__ = ["dispatch_recurrence"]
