"""
services/wake_sources/proposal_arrival.py — Proposal-arrival wake source (ADR-296 v2 D1).

A new row landed in `action_proposals`. Per ADR-296 v2 D1, proposal
creation is itself a wake-warrant — Tier 1 auto-escalates.

Caller: `routes/proposals.py` (or wherever the proposal INSERT happens).
The Reviewer evaluates the proposal against principles + PRECEDENT +
money-truth + risk; AUTONOMY gates whether the verdict binds via
`should_auto_apply` (per ADR-229 D1 judgment-first ordering).

Per ADR-252 D5: when `proposal_row.source` ∈ {`reviewer_periodic`,
`reviewer_addressed`, `reviewer_heartbeat`}, the Reviewer already judged
this proposal in another cycle — invoking it again would be a self-
judgment loop. The downstream handler short-circuits in that case.
"""

from __future__ import annotations

import logging

from services.wake import submit_wake_proposal

logger = logging.getLogger(__name__)


async def on_created(
    client,
    user_id: str,
    proposal_id: str,
    proposal_row: dict,
) -> dict:
    """Submit a wake proposal for a newly-created action_proposals row.

    Args:
        client: Supabase service client
        user_id: Workspace owner UUID
        proposal_id: UUID of the newly created proposal
        proposal_row: row dict as returned from the INSERT

    Returns:
        WakeOutcome dict per services.wake.submit_wake_proposal contract.
    """
    return await submit_wake_proposal(
        client, user_id,
        source="proposal_arrival",
        payload={
            "proposal_id": proposal_id,
            "proposal_row": proposal_row,
        },
    )


__all__ = ["on_created"]
