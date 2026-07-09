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

    amount_usd: float           # the backend runaway-safety envelope (ADR-433: no longer an operator dollar dial)
    window: str                 # 'monthly' | 'weekly' | 'daily'
    window_spend_usd: float     # spend so far this window (execution_events sum)
    remaining_usd: float        # max(0, amount - spend)
    per_wake_ceiling_usd: float # runaway floor — single-fire cap
    queue_depth: int = 0        # pending wakes (single lane post-ADR-327)
    # ADR-433 D2 — the REAL pooled balance (allowance + top-ups − metered spend,
    # ADR-396/429). The pace pane draws consumption as a % of window_spend against
    # this, so the draw-down is honest money, not the fictional envelope. None on
    # a balance-read failure (the FE then falls back to the envelope %).
    effective_balance_usd: Optional[float] = None
    # ADR-338 D4.4 — runway framing: balance + observed burn → time remaining.
    # daily_burn = window_spend / days-elapsed-in-window (observed, not projected
    # from history). runway_days = remaining / daily_burn. Both null/None when
    # there isn't enough spend this window to project (fresh window, zero spend).
    daily_burn_usd: Optional[float] = None
    runway_days: Optional[float] = None


@router.get("", response_model=BudgetResponse)
async def get_budget(auth: UserClient) -> BudgetResponse:
    """Return the operator's spend envelope + window-to-date spend + queue depth.

    The window-spend is summed from the execution_events cost ledger
    (ADR-291) over the current budget window. Falls back to kernel defaults
    ($50/monthly) when no `_budget.yaml` is authored.
    """
    from services.budget import load_budget, window_spend, window_elapsed_days
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

    remaining = max(0.0, budget.amount_usd - spent)

    # ADR-433 D3 — runway projects against the REAL pooled balance, not the
    # per-agent envelope (`amount_usd − spent`). Pre-433 "N days left" meant N
    # days until a fictional $50 envelope ran out; the honest runway is N days
    # until the operator's actual money (get_effective_balance = allowance +
    # top-ups − metered spend, ADR-396/429) is exhausted. Best-effort: on any
    # balance-read failure we fall back to the envelope remaining so the line is
    # never silently wrong-by-omission (a runway is better than none), but the
    # real balance is preferred.
    runway_basis = remaining
    effective_balance: Optional[float] = None
    try:
        from services.platform_limits import get_effective_balance
        eff = get_effective_balance(auth.client, auth.user_id)
        if eff is not None:
            effective_balance = max(0.0, float(eff))
            runway_basis = effective_balance
    except Exception as exc:  # pragma: no cover — fall back to envelope remaining
        logger.debug("[BUDGET] effective-balance runway basis unavailable: %s", exc)

    # ADR-338 D4.4 — runway: observed daily burn → days of remaining balance.
    # daily_burn = window_spend / days-elapsed. None when spend is ~0 (no signal
    # to project from yet). runway_days = runway_basis / daily_burn; clamps high.
    daily_burn: Optional[float] = None
    runway_days: Optional[float] = None
    if spent > 0.005:  # > half a cent — enough to have a real burn signal
        elapsed = window_elapsed_days(budget.window)
        burn = spent / elapsed if elapsed > 0 else None
        if burn and burn > 0:
            daily_burn = round(burn, 4)
            # Cap the displayed runway at 999 days — beyond that it's "plenty."
            runway_days = round(min(runway_basis / burn, 999.0), 1)

    return BudgetResponse(
        amount_usd=round(budget.amount_usd, 2),
        window=budget.window,
        window_spend_usd=round(spent, 2),
        remaining_usd=round(remaining, 2),
        per_wake_ceiling_usd=round(budget.per_wake_ceiling_usd, 2),
        queue_depth=depth,
        daily_burn_usd=daily_burn,
        runway_days=runway_days,
        effective_balance_usd=round(effective_balance, 2) if effective_balance is not None else None,
    )


class PrincipalSpendRow(BaseModel):
    """One principal's attributed draw on the shared workspace pool (ADR-416)."""

    principal_id: str
    spend_usd: float
    event_count: int


class SpendByPrincipalResponse(BaseModel):
    """ADR-416 Phase 1 — the "who spent what" rollup over the workspace pool.

    The rows attribute the pool's spend-since-anchor to the acting principals; they
    sum (up to rounding) to the balance gate's spend for the same window. Legibility
    only — the hard-stop stays workspace-summed (one pool).
    """

    rows: list[PrincipalSpendRow]


@router.get("/spend-by-principal", response_model=SpendByPrincipalResponse)
async def get_spend_by_principal(auth: UserClient) -> SpendByPrincipalResponse:
    """Return per-principal spend attribution over the acting workspace's pool.

    ADR-416 D3 / Phase 1 — the consumer of `execution_events.principal_id`. "Who
    spent what" for the multi-principal commons. The acting workspace is resolved
    the same way the balance gate resolves it (contextvar / owner fallback), so the
    rollup names the same pool the balance draws from.
    """
    from services.platform_limits import spend_by_principal

    rows = spend_by_principal(auth.client, auth.user_id)
    return SpendByPrincipalResponse(
        rows=[
            PrincipalSpendRow(
                principal_id=str(r["principal_id"]),
                spend_usd=round(r["spend_usd"], 4),
                event_count=r["event_count"],
            )
            for r in rows
        ]
    )
