"""
services/wake_sources/manual_fire.py — Manual-fire wake source (ADR-296 v2 D1).

The operator explicitly fired a recurrence via `FireInvocation` in chat.
Per ADR-296 v2 D3, FireInvocation remains in CHAT_PRIMITIVES (operator
manual fire path); the Reviewer does NOT have this primitive in its
surface — the Reviewer's authority is over cadence + standing intent,
not over invoking itself or upstream recurrences.

Per ADR-296 v2 D1, operator explicit assertion is a wake-warrant —
Tier 1 auto-escalates. The downstream funnel decision is `escalate`
unless a kernel gate (balance/spend) trips.

Caller: `services/primitives/fire_invocation.py::handle_fire_invocation`.
Future: admin debug endpoints, scenario harnesses, alpha-ops scripts
may also call this directly when simulating operator behavior.
"""

from __future__ import annotations

import logging
from typing import Optional

from services.recurrence import Recurrence
from services.wake import submit_wake_proposal

logger = logging.getLogger(__name__)


async def fire(
    client,
    user_id: str,
    recurrence: Recurrence,
    *,
    context: Optional[str] = None,
) -> dict:
    """Submit a wake proposal for an operator-initiated manual fire.

    Args:
        client: Supabase service client
        user_id: Workspace owner UUID
        recurrence: parsed Recurrence the operator wants to fire now
        context: optional one-shot steering (appended to prompt;
                 does not mutate the recurrence record)

    Returns:
        WakeOutcome dict per services.wake.submit_wake_proposal contract.
    """
    return await submit_wake_proposal(
        client, user_id,
        source="manual_fire",
        payload={"recurrence": recurrence, "context": context},
    )


__all__ = ["fire"]
