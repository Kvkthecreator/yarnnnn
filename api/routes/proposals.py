"""
Proposals routes — ADR-193: user approval surface for proposed actions.

Endpoints:
- GET    /proposals                       → list pending proposals
- GET    /proposals/{id}                  → fetch single proposal
- POST   /proposals/{id}/approve          → approve + execute (calls handle_execute_proposal)
- POST   /proposals/{id}/reject           → reject with optional reason

The approve/reject endpoints wrap the primitive handlers so the frontend
can act on proposals without going through the LLM chat loop — faster,
cheaper, deterministic. The LLM picks up status changes on the next
conversation turn via the compact index.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.supabase import UserClient

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request models
# =============================================================================

class ApproveRequest(BaseModel):
    """Approval payload.

    modified_inputs: optional field overrides merged over proposal.inputs.
    reviewer_reasoning: optional short reasoning; lands in action_proposals +
      /workspace/review/decisions.md per ADR-194 v2 Phase 2a.
    """
    modified_inputs: Optional[dict] = None
    reviewer_reasoning: Optional[str] = None


class RejectRequest(BaseModel):
    """Rejection payload.

    reason: short explanation (also used as reviewer_reasoning if the latter
      is not provided).
    reviewer_reasoning: optional override for the audit-trail reasoning.
    """
    reason: Optional[str] = None
    reviewer_reasoning: Optional[str] = None


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/proposals")
async def list_proposals(
    auth: UserClient,
    status: Optional[str] = "pending",
    limit: int = 50,
):
    """List proposals for the authenticated user.

    Args:
        status: filter by status (default 'pending'). Use 'all' for no filter.
        limit: max rows to return.
    """
    try:
        query = (
            auth.client.table("action_proposals")
            .select("*")
            .eq("user_id", auth.user_id)
            .order("created_at", desc=True)
            .limit(min(limit, 200))
        )
        if status and status != "all":
            query = query.eq("status", status)
        result = query.execute()
        return {"proposals": result.data or []}
    except Exception as e:
        logger.error(f"[PROPOSALS] list failed for {auth.user_id[:8]}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/proposals/{proposal_id}")
async def get_proposal(proposal_id: str, auth: UserClient):
    """Fetch a single proposal."""
    try:
        result = (
            auth.client.table("action_proposals")
            .select("*")
            .eq("id", proposal_id)
            .eq("user_id", auth.user_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Proposal not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PROPOSALS] get {proposal_id} failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/proposals/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: str,
    request: ApproveRequest,
    auth: UserClient,
):
    """Approve + execute a proposal.

    Wraps `handle_execute_proposal`. Returns the execution result on
    success, or an error payload if the proposal is not pending / expired /
    fails at execution.

    ADR-194 v2 Phase 2a: frontend approvals always fill the Reviewer seat
    as `human:<user_id>`. The audit entry + proposal-row metadata are
    written by the primitive handler.
    """
    from services.primitives.propose_action import handle_execute_proposal

    result = await handle_execute_proposal(
        auth,
        {
            "proposal_id": proposal_id,
            "modified_inputs": request.modified_inputs,
            "reviewer_identity": f"human:{auth.user_id}",
            "reviewer_reasoning": request.reviewer_reasoning,
        },
    )
    if not result.get("success"):
        # Map known errors to HTTP status codes
        error = result.get("error") or "execution_failed"
        if error == "proposal_not_found":
            raise HTTPException(status_code=404, detail=result.get("message") or "Proposal not found")
        if error == "proposal_not_pending":
            raise HTTPException(status_code=409, detail=result)
        if error == "proposal_expired":
            raise HTTPException(status_code=410, detail=result)
        # Execution failures return 200 with success=false so frontend can surface details
        return result
    return result


@router.post("/proposals/{proposal_id}/reject")
async def reject_proposal(
    proposal_id: str,
    request: RejectRequest,
    auth: UserClient,
):
    """Reject a proposal with optional reason. Wraps `handle_reject_proposal`.

    ADR-194 v2 Phase 2a: frontend rejections fill the Reviewer seat as
    `human:<user_id>`. The audit entry + proposal-row metadata are
    written by the primitive handler.
    """
    from services.primitives.propose_action import handle_reject_proposal

    result = await handle_reject_proposal(
        auth,
        {
            "proposal_id": proposal_id,
            "reason": request.reason,
            "reviewer_identity": f"human:{auth.user_id}",
            "reviewer_reasoning": request.reviewer_reasoning,
        },
    )
    if not result.get("success"):
        error = result.get("error") or "rejection_failed"
        if error == "proposal_not_pending_or_not_found":
            raise HTTPException(status_code=404, detail=result.get("message") or "Proposal not found or not pending")
        raise HTTPException(status_code=400, detail=result)
    return result
