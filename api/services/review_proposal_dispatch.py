"""Review-seat orchestration — ADR-194 v2 Phase 2b + Phase 3.

**This module is review orchestration, not the reviewer entity.** It is
runtime coordination — the plumbing that routes a proposal from
creation to whichever occupant currently fills the Reviewer seat, then
to the verdict-consumers. The judgment itself is rendered elsewhere
(see `reviewer_agent.py` for the AI occupant's judgment logic; human
occupants render judgment through the approval UX). Per
docs/architecture/reviewer-substrate.md §"Review orchestration vs.
reviewer entity — the split", the two are architecturally distinct:
this is plumbing, agency lives in the entity.

Reactive handler for proposal creation events. Fires from
`handle_propose_action` after `action_proposals` row insert, before the
handler returns. Per FOUNDATIONS v6.0 Axiom 4 (Trigger — reactive
sub-shape), this is an event handler, not a scheduled task.

**Phase 3 scope:** policy-gated routing between observe-only and
AI-occupant invocation.

On proposal creation, the dispatcher:

1. Loads the operator's declared review framework (`principles.md`).
2. Checks per-domain auto-approve eligibility (via
   `review_principles.is_eligible_for_auto_approve`).
3. If ineligible → observe-only path (Phase 2b behavior): appends a
   `decision="defer"` entry with `reviewer_identity="reviewer-layer:
   observed"` so the Stream surface still records the event. The
   seat stays open for the human occupant (proposal remains pending).
4. If eligible → AI-occupant invocation (Phase 3 behavior): reads the
   domain's `_performance.md` + `_risk.md` + operator profile, calls
   the AI occupant (`reviewer_agent.review_proposal`) for a verdict, and:
     - `approve` → calls `handle_execute_proposal` with
       `reviewer_identity="ai:reviewer-sonnet-v1"`
     - `reject`  → calls `handle_reject_proposal` with the same identity
     - `defer`   → falls through to observe-only (human occupant decides later)

**Never raises.** Dispatch failures degrade gracefully — the proposal
remains pending, the operator can still act via ProposalCard.

**Invariant:** AI-occupant verdicts never gate *human-occupant* approvals.
If the operator clicks Approve on the ProposalCard, the existing routes
run through `handle_execute_proposal` with
`reviewer_identity="human:<user_id>"` — the AI observation becomes a
historical note in decisions.md but does not block or alter the human
decision. This preserves Principle 14: both occupants render independent
verdicts into the same seat; neither is subordinate to the other.
"""

from __future__ import annotations

import logging
from typing import Any

from services.reviewer_audit import append_decision

logger = logging.getLogger(__name__)


#: Observation tag — written to decisions.md when the orchestration layer
#: records that a proposal was seen but no occupant has yet rendered a
#: verdict (either no auto-approve policy applies for this domain, or the
#: AI occupant itself deferred). Distinct from human:* and ai:* occupant
#: identities — this is an ORCHESTRATION-LAYER tag, not an occupant verdict.
#: Functions as "seat saw the proposal, waiting for occupant" marker.
_REVIEWER_OBSERVATION_IDENTITY = "reviewer-layer:observed"

#: Prefix for all action_type values that map to context_domain="trading".
#: Used to locate the right _performance.md and to decide whether to
#: load _risk.md.
_TRADING_ACTION_PREFIX = "trading."
#: Prefix for commerce actions — map to context_domain="revenue".
_COMMERCE_ACTION_PREFIX = "commerce."


async def on_proposal_created(
    client: Any,
    user_id: str,
    proposal_id: str,
    proposal_row: dict,
) -> None:
    """Handle the reactive event of a new proposal being created.

    Args:
        client: Supabase client (user JWT — same client that inserted
            the proposal row and will carry RLS for filesystem writes).
        user_id: The proposal's owning user.
        proposal_id: UUID of the newly created proposal.
        proposal_row: The row dict as returned from the INSERT.

    Returns None. Never raises — dispatch failure is logged.
    """
    try:
        action_type = proposal_row.get("action_type") or "unknown"
        reversibility = proposal_row.get("reversibility") or ""

        # 1. Resolve context_domain from action_type
        context_domain = _resolve_context_domain(action_type)

        # 2. Load operator's declared policy
        from services.review_principles import (
            load_principles,
            policy_for_domain,
            is_eligible_for_auto_approve,
        )
        policies = load_principles(client, user_id)
        policy = policy_for_domain(policies, context_domain) if context_domain else {}

        # 3. Estimate action value (for threshold comparison)
        estimated_cents = _estimate_proposal_value_cents(proposal_row)

        # 4. Eligibility gate
        eligible, reason = is_eligible_for_auto_approve(
            policy=policy,
            action_type=action_type,
            estimated_cents=estimated_cents,
            reversibility=reversibility,
        )

        if not eligible:
            # Observe-only path (Phase 2b behavior preserved)
            await _write_observation(
                client, user_id,
                proposal_id=proposal_id,
                proposal_row=proposal_row,
                gate_reason=reason,
            )
            return

        # 5. AI Reviewer path (Phase 3)
        await _run_ai_reviewer(
            client, user_id,
            proposal_id=proposal_id,
            proposal_row=proposal_row,
            context_domain=context_domain,
            policy=policy,
        )
    except Exception as exc:  # noqa: BLE001 — must not block proposal creation
        logger.warning(
            "[REVIEW_DISPATCH] on_proposal_created failed for proposal=%s user=%s: %s",
            proposal_id[:8] if proposal_id else "?",
            user_id[:8] if user_id else "?",
            exc,
        )


# ---------------------------------------------------------------------------
# Policy helpers
# ---------------------------------------------------------------------------


def _resolve_context_domain(action_type: str) -> str | None:
    """Map action_type → context_domain slug used for _performance.md lookup.

    Mirrors the domain assignment in OutcomeProvider implementations:
      - trading.*  → "trading"
      - commerce.* → "revenue"
    Returns None for action_types without a tracked domain (e.g., email.*
    which doesn't yet have a performance domain; falls through to
    observe-only).
    """
    if action_type.startswith(_TRADING_ACTION_PREFIX):
        return "trading"
    if action_type.startswith(_COMMERCE_ACTION_PREFIX):
        return "revenue"
    return None


def _estimate_proposal_value_cents(proposal_row: dict) -> int | None:
    """Extract a dollar-valued scalar from proposal.inputs for threshold
    comparison. Best-effort — returns None when no reliable signal.

    Supported shapes:
      - trading: inputs.qty * inputs.limit_price (or fill_price)
      - commerce: inputs.price_cents, inputs.total_cents, inputs.amount_cents
    """
    inputs = proposal_row.get("inputs") or {}

    # Direct cents fields (commerce)
    for key in ("price_cents", "total_cents", "amount_cents", "value_cents"):
        v = inputs.get(key)
        if isinstance(v, (int, float)) and v != 0:
            return int(v)

    # Trading notional
    qty = inputs.get("qty")
    price = inputs.get("limit_price") or inputs.get("fill_price") or inputs.get("price")
    try:
        if qty is not None and price is not None:
            notional_dollars = float(qty) * float(price)
            return int(round(notional_dollars * 100))
    except (TypeError, ValueError):
        pass

    return None


# ---------------------------------------------------------------------------
# Observe-only (Phase 2b path) + AI Reviewer (Phase 3 path)
# ---------------------------------------------------------------------------


async def _write_observation(
    client: Any,
    user_id: str,
    *,
    proposal_id: str,
    proposal_row: dict,
    gate_reason: str,
) -> None:
    """Write the observe-only decisions.md entry. Seat defers to human."""
    action_type = proposal_row.get("action_type") or "unknown"
    reversibility = proposal_row.get("reversibility")
    expires_at = proposal_row.get("expires_at")
    rationale = (proposal_row.get("rationale") or "").strip()

    reasoning_lines = [
        "Reviewer layer observed proposal creation.",
        f"Seat defers to human — {gate_reason}.",
        "",
    ]
    if rationale:
        reasoning_lines.append("Proposal rationale (from YARNNN / caller):")
        reasoning_lines.append(f"> {rationale}")
        reasoning_lines.append("")
    if expires_at:
        reasoning_lines.append(f"Proposal expires: {expires_at}")

    ok = await append_decision(
        client, user_id,
        proposal_id=proposal_id,
        action_type=action_type,
        decision="defer",
        reviewer_identity=_REVIEWER_OBSERVATION_IDENTITY,
        reasoning="\n".join(reasoning_lines),
        reversibility=reversibility,
        outcome="pending_human",
    )
    if ok:
        logger.info(
            "[REVIEW_DISPATCH] observed proposal=%s user=%s action=%s — %s",
            proposal_id[:8],
            user_id[:8],
            action_type,
            gate_reason,
        )


async def _run_ai_reviewer(
    client: Any,
    user_id: str,
    *,
    proposal_id: str,
    proposal_row: dict,
    context_domain: str,
    policy: dict,
) -> None:
    """Run the AI Reviewer and route its decision to the appropriate
    primitive handler. Never raises — AI failure falls back to
    observe-only so the human can still decide via ProposalCard.
    """
    from agents.reviewer_agent import review_proposal, REVIEWER_MODEL_IDENTITY

    action_type = proposal_row.get("action_type") or "unknown"
    reversibility = proposal_row.get("reversibility")

    # Load substrate the AI reads against
    principles_md = _read_workspace_file(
        client, user_id, "/workspace/review/principles.md",
    ) or ""
    performance_md = _read_workspace_file(
        client, user_id, f"/workspace/context/{context_domain}/_performance.md",
    )
    # _risk.md is trading-specific today; extensible per domain
    risk_md = None
    if context_domain == "trading":
        risk_md = _read_workspace_file(
            client, user_id, "/workspace/context/trading/_risk.md",
        )
    operator_profile_md = _read_workspace_file(
        client, user_id, f"/workspace/context/{context_domain}/_operator_profile.md",
    )

    decision = await review_proposal(
        client=client,
        user_id=user_id,
        proposal_row=proposal_row,
        principles_md=principles_md,
        performance_md=performance_md,
        risk_md=risk_md,
        operator_profile_md=operator_profile_md,
    )

    if decision is None:
        # AI failed or produced no valid decision — observe-only fallback
        await _write_observation(
            client, user_id,
            proposal_id=proposal_id,
            proposal_row=proposal_row,
            gate_reason="AI Reviewer unavailable or returned invalid decision; seat defers to human",
        )
        return

    # Build a minimal auth-shaped object for the primitive handlers.
    # handle_execute_proposal / handle_reject_proposal expect
    # auth.client + auth.user_id — no other fields touched.
    from types import SimpleNamespace
    auth_for_primitive = SimpleNamespace(client=client, user_id=user_id)

    ai_reasoning = decision["reasoning"]
    confidence = decision["confidence"]
    full_reasoning = (
        f"{ai_reasoning}\n\n"
        f"— decided by {REVIEWER_MODEL_IDENTITY} (confidence: {confidence})"
    )

    if decision["decision"] == "approve":
        from services.primitives.propose_action import handle_execute_proposal
        result = await handle_execute_proposal(
            auth_for_primitive,
            {
                "proposal_id": proposal_id,
                "reviewer_identity": REVIEWER_MODEL_IDENTITY,
                "reviewer_reasoning": full_reasoning,
            },
        )
        ok = bool(result and result.get("success"))
        logger.info(
            "[REVIEW_DISPATCH] AI approved proposal=%s user=%s action=%s execute_success=%s",
            proposal_id[:8], user_id[:8], action_type, ok,
        )
        # handle_execute_proposal already appended a decision entry via
        # the Phase 2a audit path; no additional append needed here.
        return

    if decision["decision"] == "reject":
        from services.primitives.propose_action import handle_reject_proposal
        result = await handle_reject_proposal(
            auth_for_primitive,
            {
                "proposal_id": proposal_id,
                "reason": ai_reasoning[:240],
                "reviewer_identity": REVIEWER_MODEL_IDENTITY,
                "reviewer_reasoning": full_reasoning,
            },
        )
        ok = bool(result and result.get("success"))
        logger.info(
            "[REVIEW_DISPATCH] AI rejected proposal=%s user=%s action=%s reject_success=%s",
            proposal_id[:8], user_id[:8], action_type, ok,
        )
        return

    # decision == "defer" — AI looked but chose not to decide. Record
    # the AI's reasoning as an observation so it's visible to the human
    # in decisions.md; the proposal stays pending.
    await append_decision(
        client, user_id,
        proposal_id=proposal_id,
        action_type=action_type,
        decision="defer",
        reviewer_identity=REVIEWER_MODEL_IDENTITY,
        reasoning=full_reasoning,
        reversibility=reversibility,
        outcome="pending_human",
    )
    logger.info(
        "[REVIEW_DISPATCH] AI deferred proposal=%s user=%s action=%s — human to decide",
        proposal_id[:8], user_id[:8], action_type,
    )


# ---------------------------------------------------------------------------
# Filesystem read helper — same pattern as risk_gate + reviewer_audit
# ---------------------------------------------------------------------------


def _read_workspace_file(client: Any, user_id: str, path: str) -> str | None:
    """Read a workspace file's content. Returns None on missing or error."""
    try:
        result = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", path)
            .limit(1)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[REVIEW_DISPATCH] read failed for %s (user=%s): %s",
            path, user_id[:8], exc,
        )
        return None
    rows = result.data or []
    if not rows:
        return None
    return rows[0].get("content") or None
