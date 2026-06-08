"""
Budget endpoint — kernel governance dial (ADR-327).

`GET /api/budget` returns the operator's declared spend envelope
(`_budget.yaml`) + window-to-date spend + live wake_queue depth. Budget is
the Trigger-dimension dial of the Budget + Autonomy + Identity trifecta
(ADR-327, supersedes the retired pace dial) — a KERNEL governance concern,
not trader-program data.

Supersedes the ADR-298/300/312 `/api/pace` endpoint. The FE `/budget`
atomic surface consumes this for the utilization view ("$12 of $50 used,
N days left").

Auth boundary: derives user from `auth.user_id`. No cross-user reads.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from services.supabase import UserClient

logger = logging.getLogger(__name__)

router = APIRouter()


class BudgetResponse(BaseModel):
    """ADR-327 — operator spend envelope + window-to-date utilization.

    Surfaces the dollar budget over a timeframe (the Trigger-dimension dial)
    alongside how much of it has been spent this window + the live wake_queue
    depth, so the operator sees at a glance where the spend went.
    """

    amount_usd: float           # the declared spend envelope
    window: str                 # 'monthly' | 'weekly' | 'daily'
    window_spend_usd: float     # spend so far this window (execution_events sum)
    remaining_usd: float        # max(0, amount - spend)
    per_wake_ceiling_usd: float # runaway floor — single-fire cap
    queue_depth: int = 0        # pending wakes (single lane post-ADR-327)


@router.get("", response_model=BudgetResponse)
async def get_budget(auth: UserClient) -> BudgetResponse:
    """Return the operator's spend envelope + window-to-date spend + queue depth.

    The window-spend is summed from the execution_events cost ledger
    (ADR-291) over the current budget window. Falls back to kernel defaults
    ($50/monthly) when no `_budget.yaml` is authored.
    """
    from services.budget import load_budget, window_spend
    from services.wake_queue import queue_depth

    budget = load_budget(auth.client, auth.user_id)

    try:
        spent = window_spend(auth.client, auth.user_id, budget.window)
    except Exception as exc:
        logger.warning("[BUDGET] window_spend failed for %s: %s", auth.user_id[:8], exc)
        spent = 0.0

    try:
        depth = queue_depth(auth.client, user_id=auth.user_id)
    except Exception as exc:
        logger.warning("[BUDGET] queue_depth failed: %s", exc)
        depth = 0

    return BudgetResponse(
        amount_usd=round(budget.amount_usd, 2),
        window=budget.window,
        window_spend_usd=round(spent, 2),
        remaining_usd=round(max(0.0, budget.amount_usd - spent), 2),
        per_wake_ceiling_usd=round(budget.per_wake_ceiling_usd, 2),
        queue_depth=depth,
    )
