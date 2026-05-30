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
2. If the domain has reviewable substrate (`_money_truth.md`,
   `_operator_profile.md`, or non-empty `principles.md`) → AI Reviewer
   invocation (`reviewer_agent.review_proposal`) renders a verdict. If
   the domain has no reviewable substrate → observe-only fallback.
3. The Reviewer's verdict (`approve` | `reject` | `defer`) routes:
   - `approve` → loads AUTONOMY, calls `should_auto_apply`.
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
from typing import Any, Optional

from services.reviewer_audit import append_decision
from services.reviewer_chat_surfacing import write_reviewer_message
from services.reviewer_envelope import load_reviewer_governance_envelope

logger = logging.getLogger(__name__)


#: Observation tag — written to decisions.md when the orchestration layer
#: records that a proposal was seen but no occupant has yet rendered a
#: verdict (either no auto-approve policy applies for this domain, or the
#: AI occupant itself deferred). Distinct from human:* and ai:* occupant
#: identities — this is an ORCHESTRATION-LAYER tag, not an occupant verdict.
#: Functions as "seat saw the proposal, waiting for occupant" marker.
_REVIEWER_OBSERVATION_IDENTITY = "reviewer-layer:observed"

# ADR-307: proposals store `primitive` (platform tool name) + `family`, not
# action_type. Domain resolution keys on the primitive prefix.
#: platform primitives that map to context_domain="trading".
_TRADING_PRIMITIVE_PREFIX = "platform_trading_"
#: platform primitives that map to context_domain="revenue".
_COMMERCE_PRIMITIVE_PREFIX = "platform_commerce_"

# ADR-253 D2: propose_followup allow-list DELETED.
# propose_followup (ADR-229 D2) replaced by directives.
# Directives execute immediately — no action_proposals row, no second Reviewer pass.
# See _execute_reviewer_directives() at bottom of this file.


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
    verdict binds via `should_auto_apply` AFTER judgment, not
    before.
    """
    try:
        primitive = proposal_row.get("primitive") or "unknown"
        family = proposal_row.get("family") or "capital"
        # action_type-shaped label for logs/audit continuity.
        action_type = f"{family}:{primitive}"

        # ADR-252 D5 + ADR-307 D6: skip reactive Reviewer when the Reviewer
        # ITSELF authored this proposal — re-invoking would be a self-judgment
        # loop (and, for substrate writes the gate queues, a self-WAKE loop).
        # The gate stamps source="reviewer:<occupant>" on Reviewer-authored
        # proposals (enqueue_gated_action). The AUTONOMY gate still applies
        # downstream (auto-execute or queue for operator click).
        source = proposal_row.get("source") or ""
        if source.startswith("reviewer:") or source in (
            "reviewer_periodic", "reviewer_addressed", "reviewer_heartbeat",
        ):
            logger.info(
                "[REVIEW_DISPATCH] skipping reactive Reviewer for source=%r proposal=%s "
                "(Reviewer self-authored — closes self-wake loop)",
                source,
                (proposal_id or "?")[:8],
            )
            return

        # 1. Resolve context_domain from (primitive, family)
        context_domain = _resolve_context_domain(primitive, family)

        # 2. Determine whether this domain has reviewable substrate.
        #    Without ANY of {principles.md, _money_truth.md, _operator_profile.md},
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
        #    IDENTITY + principles + PRECEDENT + _money_truth + _risk +
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


def _resolve_context_domain(primitive: str, family: str = "capital") -> str | None:
    """Map (primitive, family) → context_domain slug for substrate lookup.

    ADR-307: keys on the stored `primitive` + `family`.
      - platform_trading_*  → "trading"   (capital)
      - platform_commerce_* → "revenue"   (capital)
      - family='substrate'  → "_shared"   (workspace-scope; the substrate-write
        proposal reaches the Reviewer's verdict path against workspace
        governance, NOT observe-only — risk #5)
    Returns None only for capital primitives without a tracked domain (e.g.
    platform_email_*), which fall through to observe-only.
    """
    if family == "substrate":
        return "_shared"
    if primitive.startswith(_TRADING_PRIMITIVE_PREFIX):
        return "trading"
    if primitive.startswith(_COMMERCE_PRIMITIVE_PREFIX):
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
    invocation_id: Optional[str] = None,  # ADR-289 D5
) -> None:
    """Write the observe-only decisions.md entry. Seat awaits operator-in-real-time occupant
    (per FOUNDATIONS v8.4 Axiom 2 two-embodiments — neither embodiment is a separate party,
    the seat is simply waiting for the human embodiment to render judgment)."""
    # ADR-307: derive from primitive + family-shaped decision_context.
    _family = proposal_row.get("family") or "capital"
    _prim = proposal_row.get("primitive") or "unknown"
    action_type = f"{_family}:{_prim}"
    _dc = proposal_row.get("decision_context") or {}
    reversibility = _dc.get("reversibility")
    expires_at = proposal_row.get("expires_at")
    rationale = (_dc.get("rationale") or "").strip()

    # Framing per ADR-249 D3: Reviewer is the operator's judgment function.
    # Observe-only = no reviewable substrate yet, so the judgment seat cannot
    # reason. Your confirmation is needed not because you're external to the
    # Reviewer — you ARE the Reviewer in manual posture.
    reasoning_lines = [
        f"No reviewable substrate for `{action_type}` — {gate_reason}.",
        "Your judgment is needed to proceed.",
        "",
    ]
    if rationale:
        reasoning_lines.append("Proposal rationale:")
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
        outcome="pending_operator",
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
    # Observe-only means "Reviewer layer saw this, seat awaits operator-in-real-time
    # occupant" — per FOUNDATIONS v8.4 Axiom 2 two-embodiments framing.
    await write_reviewer_message(
        client, user_id,
        content=reasoning_text,
        proposal_id=proposal_id,
        verdict="observation",
        occupant=_REVIEWER_OBSERVATION_IDENTITY,
        action_type=action_type,
        task_slug=proposal_row.get("task_slug"),
        invocation_id=invocation_id,  # ADR-289 D5
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

    - approve verdict → loads AUTONOMY, calls should_auto_apply.
      If binding → handle_execute_proposal. If non-binding → advisory
      observation entry, proposal queued for operator click.
    - reject verdict → handle_reject_proposal (terminal, never bound by
      autonomy — Reviewer's narrowing is its own).
    - defer verdict → decisions.md entry; if propose_followup present
      per ADR-229 D2, dispatch as fresh ProposeAction with allow-list
      action_type validation.

    Never raises — AI failure falls back to observe-only so the human
    can still decide via ProposalCard.

    ADR-289 D2 + D3: proposal-arrival reactive cycles become first-class
    invocations. We pre-generate the invocation_id, stamp it on the
    Reviewer call, the action narrations, and every write_reviewer_message
    write produced during the cycle, then finalize the canonical
    execution_events row at function exit.
    """
    from agents.reviewer_agent import invoke_reviewer, REVIEWER_MODEL_IDENTITY
    from agents.reviewer_agent_compat import output_to_review_decision
    import uuid as _uuid

    # ADR-289 D2 + D3 (partial): canonical invocation atom id for this
    # proposal-arrival reactive cycle. Threaded through invoke_reviewer +
    # surface_reviewer_actions + write_reviewer_message so the FE groups
    # narrative rows from this cycle under one invocation card on the Feed
    # surface. The execution_events row for proposal-arrival cycles is
    # deferred to Phase 1B (this function has 7+ exit branches; finalizing
    # the audit row across all of them is its own refactor — Phase 1 ships
    # narrative grouping first, audit-row coverage second).
    invocation_id = str(_uuid.uuid4())

    # ADR-307: derive from primitive + family-shaped decision_context.
    _prim = proposal_row.get("primitive") or "unknown"
    _family = proposal_row.get("family") or "capital"
    action_type = f"{_family}:{_prim}"
    reversibility = (proposal_row.get("decision_context") or {}).get("reversibility")

    # ADR-276 implementation completion (2026-05-21): use canonical
    # `load_reviewer_governance_envelope` helper rather than hand-rolling
    # 6 envelope reads. The helper assembles the full 8-key universal
    # envelope (identity_md / principles_md / precedent_md / mandate_md /
    # autonomy_md / preferences_yaml / occupant_md / standing_intent_md)
    # PLUS bundle-declared program-shaped envelope keys per the active
    # bundle's MANIFEST `substrate_abi.reviewer_wake_envelope`. For
    # alpha-trader workspaces this surfaces operator_profile_md, risk_md,
    # ground_truth_md (= `_money_truth.md`), and signal_files. For
    # alpha-author it surfaces voice_md, editorial_md, corpus_signal_md,
    # and audience_signal_md.
    #
    # Pre-2026-05-21 this function hand-rolled 6 reads + missed MANDATE,
    # AUTONOMY, _preferences.yaml, OCCUPANT.md, standing_intent.md,
    # signal_files — meaning capital-judgment wakes (the highest-stakes
    # Reviewer wakes) operated without MANDATE (operator's Primary Action
    # declaration) and AUTONOMY (delegation ceiling). The drift was the
    # third instance of the prose-named-but-not-pre-loaded class (first
    # two closed by ADR-275 D5 refinement + ADR-276); this commit closes
    # the class by routing every invoke_reviewer call site through the
    # same helper.
    #
    # `context_domain` parameter is preserved for backward-compat with
    # logging + downstream branches but no longer drives substrate
    # reads — the bundle's substrate_abi is the source of truth for
    # per-program envelope shape per ADR-281 D2.
    governance_envelope, _envelope_load_ms = await load_reviewer_governance_envelope(
        client, user_id
    )

    output = await invoke_reviewer(
        client, user_id,
        trigger="reactive",  # ADR-260 D2: proposal arrival is the canonical reactive trigger
        invocation_id=invocation_id,  # ADR-289 D4
        context={
            **governance_envelope,  # ADR-276 + ADR-281 D2 (this commit closes the third instance)
            "proposal_row": proposal_row,
            # 2026-05-27 Hat-A parity fix: explicit wake_source so the Reviewer
            # perceives proposal_arrival as a distinct reactive sub-class within
            # trigger=reactive. The proposal_row already names the anchor; the
            # triggering_path/revision_id are empty strings (the proposal is the
            # anchor, not a workspace_file revision).
            "wake_source": "proposal_arrival",
            "triggering_path": "",
            "triggering_revision_id": "",
        },
    )
    # ADR-258 (revised): surface any consequential actions the Reviewer took
    # during its loop as System Agent narration entries — matches addressed
    # + heartbeat triggers so operator sees consistent conversational shape
    # regardless of which trigger fired.
    if output and (output.get("actions_taken") or []):
        from services.reviewer_chat_surfacing import surface_reviewer_actions
        try:
            await surface_reviewer_actions(
                client, user_id,
                actions_taken=output.get("actions_taken") or [],
            )
        except Exception as exc:
            logger.warning(
                "[REVIEW_DISPATCH] action narration failed: %s", exc,
            )
    decision = output_to_review_decision(output)

    if decision is None:
        # AI failed or produced no valid decision — observe-only fallback
        await _write_observation(
            client, user_id,
            proposal_id=proposal_id,
            proposal_row=proposal_row,
            gate_reason="AI Reviewer unavailable or returned invalid decision; seat defers to human",
            invocation_id=invocation_id,  # ADR-289 D5
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
            load_principles,
            autonomy_for_domain,
            principles_for_domain,
            should_auto_apply,
        )
        autonomy = load_autonomy(client, user_id)
        autonomy_policy = autonomy_for_domain(autonomy, context_domain)
        principles = load_principles(client, user_id)
        principles_policy = principles_for_domain(principles, context_domain)
        estimated_cents = _estimate_proposal_value_cents(proposal_row)

        # ADR-293 D4: uniform AUTONOMY-mode gate (capital-action class).
        # Substrate-write class flows through handle_write_file's parallel call.
        should_bind, gate_reason = should_auto_apply(
            autonomy_policy=autonomy_policy,
            action_class="capital",
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
        # Framing per ADR-249 D3: the Reviewer IS the operator's judgment
        # function. "Advisory" means autonomy mode requires the user's
        # real-time confirmation before execution — not that a separate
        # party needs to ratify. The gate reason explains why.
        # Per FOUNDATIONS v8.4 Axiom 2 (operator is one principal with two
        # runtime embodiments): the Reviewer-as-personified embodiment
        # rendered approve; AUTONOMY requires the operator-in-real-time
        # embodiment to confirm before binding. Phrasing reflects the
        # two-embodiments framing — neither embodiment is a separate party.
        advisory_reasoning = (
            f"{ai_reasoning}\n\n"
            f"— {REVIEWER_MODEL_IDENTITY} (confidence: {confidence})\n\n"
            f"**Operator-in-real-time confirmation required** ({gate_reason}). "
            f"Approve to bind this judgment to execution."
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
            invocation_id=invocation_id,  # ADR-289 D5
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
    # ADR-253 D2: defer can include `directives` — System Agent instructions
    # that execute immediately (no action_proposals row, no second Reviewer pass).
    # Replaces the deleted propose_followup (ADR-229 D2).

    directives = decision.get("directives") or []
    directive_note = ""
    directive_results: list[str] = []

    if directives and isinstance(directives, list):
        results = await _execute_reviewer_directives(
            client, user_id, directives,
            proposal_id=proposal_id,
            invocation_id=invocation_id,  # ADR-289 D5
        )
        directive_results = results
        if results:
            directive_note = (
                f"\n\n**Reviewer directives executed (ADR-253 D2):** "
                + "; ".join(results)
            )

    full_reasoning_with_directives = full_reasoning + directive_note

    # Record the defer entry with directive linkage if any.
    await append_decision(
        client, user_id,
        proposal_id=proposal_id,
        action_type=action_type,
        decision="defer",
        reviewer_identity=REVIEWER_MODEL_IDENTITY,
        reasoning=full_reasoning_with_directives,
        reversibility=reversibility,
        outcome="pending_operator",
    )
    # Unified chat thread — AI reviewed, chose to defer.
    await write_reviewer_message(
        client, user_id,
        content=full_reasoning_with_directives,
        proposal_id=proposal_id,
        verdict="defer",
        occupant=REVIEWER_MODEL_IDENTITY,
        action_type=action_type,
        task_slug=proposal_row.get("task_slug"),
        invocation_id=invocation_id,  # ADR-289 D5
    )
    logger.info(
        "[REVIEW_DISPATCH] AI deferred proposal=%s user=%s action=%s directives=%d",
        proposal_id[:8], user_id[:8], action_type, len(directive_results),
    )


# Note: pre-2026-05-21 this module carried a local `_read_workspace_file`
# helper that the proposal-arrival hand-rolled envelope assembly called.
# Migration to `services.reviewer_envelope.load_reviewer_governance_envelope`
# (ADR-276 implementation completion) dissolved every caller; helper deleted
# per Singular Implementation. Canonical workspace reads now route through
# the envelope helper for Reviewer-bound assembly + `UserMemory.read` for
# other contexts.


# ---------------------------------------------------------------------------
# Reviewer directive executor — ADR-253 D2
# ---------------------------------------------------------------------------

async def _execute_reviewer_directives(
    client: Any,
    user_id: str,
    directives: list[dict],
    *,
    proposal_id: str | None = None,
    invocation_id: str | None = None,  # ADR-289 D5: stamped on clarify narration
) -> list[str]:
    """Execute Reviewer directives immediately after a defer verdict.

    ADR-253 D2 (amended by ADR-296 v2 D3): replaces the deleted
    propose_followup (ADR-229 D2). Directives are System Agent instructions
    with no action_proposals row and no second Reviewer pass.

    Two allowed actions (ADR-296 v2 D3 removed the `fire_invocation`
    action — Reviewer does not self-invoke; cadence is authored via
    Schedule, not via directive-fire of upstream recurrences):
    - write_file: write to /workspace/review/ only
    - clarify: surface a question to the operator in the narrative

    Returns a list of human-readable result strings for the decisions.md entry.
    Never raises.
    """
    results: list[str] = []
    for d in directives:
        if not isinstance(d, dict):
            continue
        action = d.get("action", "")
        reason = d.get("reason", "")

        try:
            if action == "write_file":
                path = d.get("path", "")
                content = d.get("content", "")
                if not path or not path.startswith("/workspace/review/"):
                    results.append(f"write_file: path must be within /workspace/review/ — skipped ({path})")
                    continue
                from services.authored_substrate import write_revision
                write_revision(
                    client,
                    user_id=user_id,
                    path=path,
                    content=content,
                    authored_by=f"reviewer:{REVIEWER_MODEL_IDENTITY}",
                    message=f"Reviewer directive: {reason[:100]}",
                    summary=f"Reviewer write: {path.split('/')[-1]}",
                )
                results.append(f"write_file({path.split('/')[-1]}): written")
                logger.info(
                    "[REVIEWER_DIRECTIVE] write_file path=%s proposal=%s user=%s",
                    path, (proposal_id or "?")[:8], user_id[:8],
                )

            elif action == "clarify":
                message = d.get("message", reason)
                if not message:
                    continue
                from services.reviewer_chat_surfacing import write_reviewer_message
                await write_reviewer_message(
                    client, user_id,
                    content=f"**Reviewer clarification needed:** {message}",
                    proposal_id=proposal_id,
                    verdict="clarify",
                    occupant=REVIEWER_MODEL_IDENTITY,
                    invocation_id=invocation_id,  # ADR-289 D5
                )
                results.append(f"clarify: surfaced to operator")
                logger.info(
                    "[REVIEWER_DIRECTIVE] clarify proposal=%s user=%s",
                    (proposal_id or "?")[:8], user_id[:8],
                )

            else:
                results.append(f"unknown directive action={action!r} — skipped")

        except Exception as exc:
            logger.warning(
                "[REVIEWER_DIRECTIVE] directive action=%s failed proposal=%s: %s",
                action, (proposal_id or "?")[:8], exc,
            )
            results.append(f"{action}: failed ({exc})")

    return results
