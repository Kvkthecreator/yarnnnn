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

**Phase 3 + ADR-229:** judgment-first dispatch with post-judgment
binding gate.

Per ADR-229 D1, the dispatch order inverts: judgment runs first, the
autonomy gate filters whether the verdict binds.

On proposal creation, the dispatcher:

1. Resolves `context_domain` from `action_type`.
2. If the domain has reviewable substrate (`_performance.md`,
   `_operator_profile.md`, or non-empty `principles.md`) → AI Reviewer
   invocation (`reviewer_agent.review_proposal`) renders a verdict. If
   the domain has no reviewable substrate → observe-only fallback.
3. The Reviewer's verdict (`approve` | `reject` | `defer`) routes:
   - `approve` → loads AUTONOMY, calls `should_auto_execute_verdict`.
     If binding → `handle_execute_proposal`. If non-binding → advisory
     observation entry, proposal queued for operator click.
   - `reject` → `handle_reject_proposal` (Reviewer's own narrowing is
     terminal; never bound by autonomy).
   - `defer` → decisions.md entry. Per ADR-229 D2, if the verdict
     carries `propose_followup`, dispatch as a fresh `ProposeAction`
     so the Reviewer's "I need evidence" recursion produces the
     substrate-building work it asked for.

**Why judgment runs before autonomy** (ADR-229 D1): pre-ADR-229 the
autonomy gate ran first and short-circuited the Reviewer's invocation
for proposals outside the ceiling — forfeiting calibration on exactly
the proposals where calibration matters most. Today's order: Reviewer
always sees the proposal; AUTONOMY decides whether the Reviewer's
approve binds or surfaces as advisory. ADR-217 D4's narrowing-only
invariant is preserved: the strictest of (verdict, autonomy ceiling)
wins.

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
from services.reviewer_chat_surfacing import write_reviewer_message

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

#: ADR-229 D2 propose_followup allow-list. The Reviewer's defer may emit
#: a follow-up proposal of one of these reversible/capital-neutral
#: action_types so the recursion produces substrate-building work
#: without the Reviewer side-channeling into capital action.
#:
#: Phase 1 scope (ADR-229): task creation only. The other entries in the
#: ADR's spec ("context.read_more", "signal.observe", "position.review")
#: are deferred until concrete action_types for them exist in the dispatch
#: map; today they would fail at handle_propose_action's
#: ACTION_DISPATCH_MAP check anyway. Adding them here is a separate
#: commit alongside the action_type registrations.
_FOLLOWUP_ALLOWED_ACTION_TYPES = frozenset({
    "task.create",
})


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

    ADR-229 D1: judgment-first ordering. Reviewer runs ALWAYS (when the
    domain has reviewable substrate); autonomy filters whether the
    verdict binds via `should_auto_execute_verdict` AFTER judgment, not
    before.
    """
    try:
        action_type = proposal_row.get("action_type") or "unknown"

        # 1. Resolve context_domain from action_type
        context_domain = _resolve_context_domain(action_type)

        # 2. Determine whether this domain has reviewable substrate.
        #    Without ANY of {principles.md, _performance.md, _operator_profile.md},
        #    Sonnet has no framework or evidence to reason against — fall
        #    back to observe-only. This is the ONE remaining condition for
        #    the observe-only path post-ADR-229; everything else flows
        #    through judgment-first dispatch.
        if not context_domain:
            await _write_observation(
                client, user_id,
                proposal_id=proposal_id,
                proposal_row=proposal_row,
                gate_reason=f"action_type={action_type!r} has no resolved context_domain — no reviewable substrate",
            )
            return

        # 3. Run the AI Reviewer first (ADR-229 D1 inversion). Loads
        #    IDENTITY + principles + PRECEDENT + _performance + _risk +
        #    operator_profile internally and renders a verdict.
        await _run_ai_reviewer(
            client, user_id,
            proposal_id=proposal_id,
            proposal_row=proposal_row,
            context_domain=context_domain,
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

    reasoning_text = "\n".join(reasoning_lines)
    ok = await append_decision(
        client, user_id,
        proposal_id=proposal_id,
        action_type=action_type,
        decision="defer",
        reviewer_identity=_REVIEWER_OBSERVATION_IDENTITY,
        reasoning=reasoning_text,
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

    # Unified chat thread — surface observation to operator's active session.
    # Observe-only means "Reviewer layer saw this, seat defers to human."
    await write_reviewer_message(
        client, user_id,
        content=reasoning_text,
        proposal_id=proposal_id,
        verdict="observation",
        occupant=_REVIEWER_OBSERVATION_IDENTITY,
        action_type=action_type,
        task_slug=proposal_row.get("task_slug"),
    )


async def _run_ai_reviewer(
    client: Any,
    user_id: str,
    *,
    proposal_id: str,
    proposal_row: dict,
    context_domain: str,
) -> None:
    """Run the AI Reviewer and route its decision per ADR-229 D1+D2.

    - approve verdict → loads AUTONOMY, calls should_auto_execute_verdict.
      If binding → handle_execute_proposal. If non-binding → advisory
      observation entry, proposal queued for operator click.
    - reject verdict → handle_reject_proposal (terminal, never bound by
      autonomy — Reviewer's narrowing is its own).
    - defer verdict → decisions.md entry; if propose_followup present
      per ADR-229 D2, dispatch as fresh ProposeAction with allow-list
      action_type validation.

    Never raises — AI failure falls back to observe-only so the human
    can still decide via ProposalCard.
    """
    from agents.reviewer_agent import review_proposal, REVIEWER_MODEL_IDENTITY

    action_type = proposal_row.get("action_type") or "unknown"
    reversibility = proposal_row.get("reversibility")

    # Load substrate the AI reads against
    principles_md = _read_workspace_file(
        client, user_id, "/workspace/review/principles.md",
    ) or ""
    # ADR-216 Commit 2: IDENTITY.md is the persona the Reviewer embodies.
    # Read at reasoning time and injected as the opening section of the
    # user message so operator-authored persona content (e.g. Simons-
    # character for a trading Reviewer) flows into the model. Fall back
    # to empty string — the model treats empty as neutral skeptical
    # baseline.
    identity_md = _read_workspace_file(
        client, user_id, "/workspace/review/IDENTITY.md",
    ) or ""
    # persona-reflection.md v1.1: PRECEDENT.md is the operator-authored
    # durable-interpretation substrate (committed fd4917a). The Reviewer
    # must read it alongside principles.md so that operator-declared
    # boundary-case resolutions land in every verdict. Operator-declared
    # interpretations narrow (or in some cases open) the persona's own
    # framework; precedent + principles combine into the full narrowing
    # layer the persona applies on top of the AUTONOMY.md ceiling.
    precedent_md = _read_workspace_file(
        client, user_id, "/workspace/context/_shared/PRECEDENT.md",
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
        identity_md=identity_md,
        principles_md=principles_md,
        precedent_md=precedent_md,
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
        # ADR-229 D1: post-judgment autonomy gate. Reviewer approved;
        # AUTONOMY decides whether the approve binds (auto-execute) or
        # surfaces as advisory (operator clicks Approve in cockpit).
        from services.review_policy import (
            load_autonomy,
            autonomy_for_domain,
            should_auto_execute_verdict,
        )
        autonomy = load_autonomy(client, user_id)
        autonomy_policy = autonomy_for_domain(autonomy, context_domain)
        estimated_cents = _estimate_proposal_value_cents(proposal_row)

        should_bind, gate_reason = should_auto_execute_verdict(
            autonomy_policy=autonomy_policy,
            verdict="approve",
            action_type=action_type,
            estimated_cents=estimated_cents,
            reversibility=reversibility or "",
        )

        if should_bind:
            # Binding approve: execute immediately under Reviewer's identity.
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
                "[REVIEW_DISPATCH] AI approved+bound proposal=%s user=%s action=%s execute_success=%s",
                proposal_id[:8], user_id[:8], action_type, ok,
            )
            # handle_execute_proposal already appended a decision entry via
            # the Phase 2a audit path; no additional append needed here.
            return

        # Advisory approve: Reviewer reasoned approve, AUTONOMY says it
        # doesn't auto-bind (manual mode, irreversible, over ceiling, etc).
        # Record the verdict + the reason it's advisory, leave proposal
        # pending for operator click.
        advisory_reasoning = (
            f"{ai_reasoning}\n\n"
            f"— decided by {REVIEWER_MODEL_IDENTITY} (confidence: {confidence})\n\n"
            f"**Advisory only** (ADR-229 post-judgment gate): {gate_reason}\n"
            f"Operator must click Approve in cockpit to bind this verdict."
        )
        await append_decision(
            client, user_id,
            proposal_id=proposal_id,
            action_type=action_type,
            decision="approve",
            reviewer_identity=REVIEWER_MODEL_IDENTITY,
            reasoning=advisory_reasoning,
            reversibility=reversibility,
            outcome="advisory_pending_operator",
        )
        await write_reviewer_message(
            client, user_id,
            content=advisory_reasoning,
            proposal_id=proposal_id,
            verdict="approve_advisory",
            occupant=REVIEWER_MODEL_IDENTITY,
            action_type=action_type,
            task_slug=proposal_row.get("task_slug"),
        )
        logger.info(
            "[REVIEW_DISPATCH] AI approved (advisory) proposal=%s user=%s action=%s gate=%s",
            proposal_id[:8], user_id[:8], action_type, gate_reason,
        )
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

    # decision == "defer" — Reviewer looked but chose not to decide.
    # ADR-229 D2: defer can be GENERATIVE — Reviewer may include a
    # `propose_followup` field naming a research/observation task that
    # would let it reconsider. Dispatch the followup as a fresh
    # ProposeAction so the recursion produces substrate-building work.

    followup = decision.get("propose_followup")
    followup_proposal_id = None
    followup_note = ""

    if followup and isinstance(followup, dict):
        followup_action_type = followup.get("action_type")
        if followup_action_type in _FOLLOWUP_ALLOWED_ACTION_TYPES:
            try:
                from services.primitives.propose_action import handle_propose_action
                followup_payload = {
                    "action_type": followup_action_type,
                    "reversibility": "reversible",  # allow-list is reversible-only
                    "task_slug": proposal_row.get("task_slug"),
                    "agent_slug": "reviewer",
                    "inputs": followup.get("inputs") or {},
                    "rationale": (
                        f"Generated by Reviewer (ADR-229 D2 propose_followup) on "
                        f"defer of proposal {proposal_id[:8]}.\n\n"
                        f"Reviewer's reasoning: {ai_reasoning}\n\n"
                        f"Followup rationale: {followup.get('rationale', '(none provided)')}"
                    ),
                    "expected_effect": (
                        f"Substrate-building task created at Reviewer's request to "
                        f"unblock evaluation of proposal {proposal_id[:8]}."
                    ),
                    "expires_in_hours": 24,
                }
                followup_result = await handle_propose_action(
                    auth_for_primitive, followup_payload
                )
                if followup_result and followup_result.get("success"):
                    followup_proposal_id = followup_result.get("proposal_id")
                    followup_note = (
                        f"\n\n**Generative defer (ADR-229 D2):** Reviewer requested "
                        f"a follow-up `{followup_action_type}` to gather evidence. "
                        f"Followup proposal id: `{followup_proposal_id}`."
                    )
                    logger.info(
                        "[REVIEW_DISPATCH] defer generated followup proposal=%s "
                        "(action=%s) for original=%s user=%s",
                        followup_proposal_id[:8] if followup_proposal_id else "?",
                        followup_action_type,
                        proposal_id[:8], user_id[:8],
                    )
            except Exception as exc:
                logger.warning(
                    "[REVIEW_DISPATCH] defer followup dispatch failed for proposal=%s: %s",
                    proposal_id[:8], exc,
                )
        else:
            followup_note = (
                f"\n\n_(Reviewer requested followup `{followup_action_type}` "
                f"but action_type is outside the propose_followup allow-list.)_"
            )
            logger.info(
                "[REVIEW_DISPATCH] defer followup REJECTED — action_type=%s not in allow-list "
                "for proposal=%s user=%s",
                followup_action_type, proposal_id[:8], user_id[:8],
            )

    full_reasoning_with_followup = full_reasoning + followup_note

    # Record the defer entry, with followup linkage if any.
    await append_decision(
        client, user_id,
        proposal_id=proposal_id,
        action_type=action_type,
        decision="defer",
        reviewer_identity=REVIEWER_MODEL_IDENTITY,
        reasoning=full_reasoning_with_followup,
        reversibility=reversibility,
        outcome="pending_human",
    )
    # Unified chat thread — AI reviewed, chose to defer. Human (or the
    # generated followup, once it accumulates substrate) will resolve.
    await write_reviewer_message(
        client, user_id,
        content=full_reasoning_with_followup,
        proposal_id=proposal_id,
        verdict="defer",
        occupant=REVIEWER_MODEL_IDENTITY,
        action_type=action_type,
        task_slug=proposal_row.get("task_slug"),
    )
    logger.info(
        "[REVIEW_DISPATCH] AI deferred proposal=%s user=%s action=%s followup=%s",
        proposal_id[:8], user_id[:8], action_type,
        followup_proposal_id[:8] if followup_proposal_id else "none",
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
