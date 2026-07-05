"""
ProposeAction / ExecuteProposal / RejectProposal — ADR-193 Phase 1

Approval-loop primitives that let YARNNN propose writes instead of
executing them immediately. Creates a persisted record in
`action_proposals`, returns proposal_id for the chat stream to render
as an approve/modify/reject card.

Three primitives:
- ProposeAction — YARNNN creates a proposal
- ExecuteProposal — user-approved; dispatches underlying write
- RejectProposal — user-declined; captures reason for learning

Integrates with ADR-192 risk gate: autonomous-mode rejections will emit
proposals instead of hard errors (Phase 3 wiring).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from services.workspace_context import effective_workspace_id, substrate_scope_filter

logger = logging.getLogger(__name__)


# =============================================================================
# action_type → platform tool name mapping
# =============================================================================
#
# ExecuteProposal dispatches through execute_primitive using the mapped
# tool name. Add entries here as new write primitives become proposable.

def build_trading_expected_effect(action_type: str, inputs: dict) -> str:
    """Build a human-readable preview for a trading proposal (ADR-193 Phase 3).

    Used by the risk-gate → proposal integration path. Kept close to the
    dispatch map so new action types get consistent preview text.
    """
    ticker = inputs.get("ticker") or "?"
    side = inputs.get("side") or "?"
    qty = inputs.get("qty")

    if action_type == "trading.submit_order":
        order_type = inputs.get("order_type", "market")
        price = inputs.get("limit_price") or inputs.get("stop_price")
        price_str = f" at ${price}" if price else ""
        return f"Submit {order_type} {side} of {qty} shares of {ticker}{price_str}."

    if action_type == "trading.submit_bracket_order":
        entry = inputs.get("entry_limit_price") or "market"
        tp = inputs.get("take_profit_limit_price")
        sl = inputs.get("stop_loss_stop_price")
        return (
            f"Enter {side} bracket on {ticker}: {qty} shares @ {entry}, "
            f"take-profit {tp}, stop-loss {sl}."
        )

    if action_type == "trading.submit_trailing_stop":
        trail = inputs.get("trail_percent")
        if trail is not None:
            trail_str = f"{trail}%"
        else:
            trail_str = f"${inputs.get('trail_price')}"
        return f"Trailing stop on {ticker}: {qty} shares, trail {trail_str}."

    # Fallback for any trading action
    return f"Execute {action_type} on {ticker} ({side}, {qty} shares)."


# ADR-307 D4/D6: ACTION_DISPATCH_MAP DELETED. The queue stores the `primitive`
# directly; ExecuteProposal replays execute_primitive(primitive, inputs) — no
# dispatch-time map. The dead `task.create → ManageTask` entry (ManageTask
# deleted by ADR-231) is gone with it, along with `_maybe_inject_manage_task_action`.
#
# `ACTION_TYPE_TO_PRIMITIVE` survives ONLY as a propose-time naming convenience
# for the capital family: the LLM/risk-gate caller proposes with a semantic
# `action_type` (e.g. "trading.submit_order"), which resolves once at insert to
# the platform-tool `primitive` stored on the row. This is naming, not dispatch
# authority — handle_execute_proposal reads the stored `primitive`, never this.
# Trading entry action_types subject to the emit-contract guard (2026-06-19
# finding). These are the order-emitting types whose inputs are passed RAW to
# the broker primitive — field-name drift between judgment and execution is the
# class of bug the guard closes. Exits/admin (cancel/close/watchlist) are not
# stop-bearing entries, so they're out of scope.
TRADING_EMIT_CONTRACT_TYPES = frozenset({
    "trading.submit_order",
    "trading.submit_bracket_order",
    "trading.submit_trailing_stop",
})

ACTION_TYPE_TO_PRIMITIVE: dict[str, str] = {
    # Trading (ADR-187 + ADR-192)
    "trading.submit_order":                 "platform_trading_submit_order",
    "trading.submit_bracket_order":         "platform_trading_submit_bracket_order",
    "trading.submit_trailing_stop":         "platform_trading_submit_trailing_stop",
    "trading.update_order":                 "platform_trading_update_order",
    "trading.cancel_order":                 "platform_trading_cancel_order",
    "trading.cancel_all_orders":            "platform_trading_cancel_all_orders",
    "trading.close_position":               "platform_trading_close_position",
    "trading.partial_close":                "platform_trading_partial_close",
    "trading.add_to_watchlist":             "platform_trading_add_to_watchlist",
    "trading.remove_from_watchlist":        "platform_trading_remove_from_watchlist",
    # Commerce (ADR-183 + ADR-192)
    "commerce.create_product":              "platform_commerce_create_product",
    "commerce.update_product":              "platform_commerce_update_product",
    "commerce.create_discount":             "platform_commerce_create_discount",
    "commerce.issue_refund":                "platform_commerce_issue_refund",
    "commerce.update_variant":              "platform_commerce_update_variant",
    "commerce.bulk_update_variant_prices":  "platform_commerce_bulk_update_variant_prices",
    "commerce.create_variant":              "platform_commerce_create_variant",
    "commerce.update_customer":             "platform_commerce_update_customer",
    # Email (ADR-192 Phase 4)
    "email.send":                           "platform_email_send",
    "email.send_bulk":                      "platform_email_send_bulk",
}


# =============================================================================
# TTL defaults by reversibility
# =============================================================================

DEFAULT_TTL_HOURS: dict[str, int] = {
    "reversible": 24,        # refund, product update, watchlist
    "soft-reversible": 6,    # campaign email, order modification
    "irreversible": 1,       # trading orders, bulk ops
}


VALID_REVERSIBILITY = ("reversible", "soft-reversible", "irreversible")


# =============================================================================
# ProposeAction
# =============================================================================

PROPOSE_ACTION_TOOL = {
    "name": "ProposeAction",
    "description": """Propose a write action for user approval instead of executing it directly (ADR-193).

Use when:
- You're acting on your own initiative (not user explicitly asked) AND the action is irreversible
- You're running autonomously (scheduled task / no user present) AND the action is soft-reversible or irreversible
- A risk-gate rejection in autonomous mode needs user review (auto-proposed by the handler)

Don't use when:
- User explicitly asked for the specific action ("refund order 123" → execute directly)
- Action is trivially reversible and user is in chat (update a product description — just do it)
- You're running a scheduled task and the action is reversible (e.g., add to watchlist — just do it)

Creates a persisted proposal with rationale + expected effect + reversibility. User sees an
approve/modify/reject card inline in chat. Returns proposal_id for narrative reference.

Args:
  action_type: namespaced capital action string (e.g., "commerce.issue_refund",
    "trading.submit_bracket_order") — resolves to the platform primitive at insert
  inputs: dict of kwargs that would pass to the platform tool
  rationale: why you're proposing this (short; 1-2 sentences)
  expected_effect: human-readable preview of what would happen on approval
  reversibility: "reversible" | "soft-reversible" | "irreversible"
  risk_warnings: optional list of warning strings (usually from risk_gate output)
  task_slug: optional — link proposal to originating task
  agent_slug: optional — link proposal to originating agent
  expires_in_hours: override default TTL (reversible=24, soft-reversible=6, irreversible=1)""",
    "input_schema": {
        "type": "object",
        "properties": {
            "action_type": {
                "type": "string",
                "description": "Namespaced action (e.g., 'commerce.issue_refund').",
            },
            "inputs": {
                "type": "object",
                "description": "kwargs for the underlying platform tool.",
            },
            "rationale": {
                "type": "string",
                "description": "Why this action is proposed (1-2 sentences).",
            },
            "expected_effect": {
                "type": "string",
                "description": "Human-readable preview of what approval would do.",
            },
            "reversibility": {
                "type": "string",
                "enum": ["reversible", "soft-reversible", "irreversible"],
            },
            "risk_warnings": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional warnings (e.g., from risk_gate).",
            },
            "task_slug": {"type": "string"},
            "agent_slug": {"type": "string"},
            "expires_in_hours": {
                "type": "integer",
                "description": "Override default TTL by reversibility.",
            },
        },
        "required": ["action_type", "inputs", "rationale", "expected_effect", "reversibility"],
    },
}


async def enqueue_gated_action(
    auth: Any,
    *,
    primitive: str,
    inputs: dict,
    family: str,
    decision_context: dict,
    source: Optional[str] = None,
    task_slug: Optional[str] = None,
    agent_slug: Optional[str] = None,
    ttl_hours: int = 24,
) -> dict:
    """ADR-307 D4: insert a generic gated-action queue row.

    The single insert path for ANY family. `handle_propose_action` (capital,
    LLM-facing) and the permission gate (substrate, when a Reviewer WriteFile
    must queue) both funnel here. Stores (primitive, inputs) + family-shaped
    decision_context; ExecuteProposal replays execute_primitive(primitive,
    inputs) on approve.

    `source` (ADR-252 D5 / ADR-307 D6): set to "reviewer:<...>" for
    Reviewer-authored proposals so the reactive dispatcher skips re-judging
    them (closes the self-wake loop).
    """
    expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
    row = {
        "user_id": auth.user_id,
        "primitive": primitive,
        "inputs": inputs,
        "family": family,
        "decision_context": decision_context or {},
        "task_slug": task_slug,
        "agent_slug": agent_slug,
        "expires_at": expires_at.isoformat(),
        "status": "pending",
        "source": source or None,
    }
    # ADR-407: stamp the acting workspace explicitly when it resolves;
    # otherwise omit and let the migration-201 trigger fill it.
    acting_ws = effective_workspace_id(auth.user_id)
    if acting_ws:
        row["workspace_id"] = acting_ws
    result = auth.client.table("action_proposals").insert(row).execute()
    if not result.data:
        return {"success": False, "error": "insert_failed"}
    created = result.data[0]
    proposal_id = created.get("id")
    logger.info(
        f"[QUEUE] {str(auth.user_id)[:8]} enqueued family={family} "
        f"primitive={primitive} (expires {ttl_hours}h, "
        f"id={proposal_id[:8] if proposal_id else '?'}, source={source or 'none'})"
    )
    # Reactive Reviewer wake on proposal arrival (ADR-296 v2 D1). The
    # dispatcher's source-skip (ADR-252 D5) prevents self-judgment when
    # source startswith "freddie:".
    if proposal_id:
        try:
            from services.wake_sources.proposal_arrival import on_created
            await on_created(auth.client, auth.user_id, proposal_id, created)
        except Exception as dispatch_exc:  # noqa: BLE001
            logger.warning(
                "[QUEUE] reviewer dispatch failed for %s: %s",
                proposal_id, dispatch_exc,
            )
    return {"success": True, "proposal_id": proposal_id, "proposal": created}


async def handle_propose_action(auth: Any, input: dict) -> dict:
    """Create a capital-family action_proposals row (ADR-193 + ADR-307 D4).

    The LLM/risk-gate caller proposes with a semantic `action_type`
    (e.g. "trading.submit_order"), resolved once here to the platform-tool
    `primitive`. rationale/expected_effect/reversibility/risk_warnings fold
    into the capital-family `decision_context`. Substrate-family proposals are
    NOT created here — the permission gate creates them via enqueue_gated_action.
    """
    action_type = input.get("action_type", "")
    inputs = input.get("inputs", {})
    rationale = input.get("rationale", "")
    expected_effect = input.get("expected_effect", "")
    reversibility = input.get("reversibility", "")

    # Validation
    if not action_type:
        return {"success": False, "error": "action_type is required"}

    # Trading emit-contract guard (2026-06-19 finding): the signal-evaluation
    # Reviewer reasons a stop correctly but serializes it into a shape no
    # executor reads (plain submit_order + stop_loss_price). Repair the known
    # drifts to the executor's exact schema at PROPOSE time, or fail loudly here
    # — never let a stop-bearing decision die silently at execution as "no
    # stop". This does NOT relax the floor (DP24); it makes the already-correct
    # stop reach the gate. May promote submit_order → submit_bracket_order, so
    # it runs before ACTION_TYPE_TO_PRIMITIVE resolves.
    if action_type in TRADING_EMIT_CONTRACT_TYPES:
        from services.primitives.trading_emit_contract import validate_and_repair_trading_emit
        check = validate_and_repair_trading_emit(action_type, inputs)
        if check["error"]:
            return {"success": False, "error": "trading_emit_contract", "message": check["error"]}
        action_type = check["action_type"]
        inputs = check["inputs"]
        emit_repairs = check["repaired"]
    else:
        emit_repairs = []

    primitive = ACTION_TYPE_TO_PRIMITIVE.get(action_type)
    if not primitive:
        return {
            "success": False,
            "error": "unsupported_action_type",
            "message": f"action_type '{action_type}' not proposable. Supported: {sorted(ACTION_TYPE_TO_PRIMITIVE.keys())}",
        }
    if not isinstance(inputs, dict):
        return {"success": False, "error": "inputs must be a dict"}
    if reversibility not in VALID_REVERSIBILITY:
        return {
            "success": False,
            "error": "invalid_reversibility",
            "message": f"reversibility must be one of {VALID_REVERSIBILITY}",
        }

    # TTL (capital family: reversibility-keyed, per ADR-307 risk #3 — the
    # reversibility-keyed TTL stays inside the capital family only).
    ttl_hours = input.get("expires_in_hours") or DEFAULT_TTL_HOURS[reversibility]
    try:
        ttl_hours = int(ttl_hours)
        if ttl_hours <= 0:
            raise ValueError("expires_in_hours must be positive")
    except (TypeError, ValueError):
        return {"success": False, "error": "expires_in_hours must be a positive integer"}

    # Capital-family decision_context (ADR-307 D4).
    decision_context = {
        "rationale": rationale,
        "expected_effect": expected_effect,
        "reversibility": reversibility,
        "risk_warnings": input.get("risk_warnings") or [],
    }
    # Record any deterministic emit-contract repairs on the proposal so the
    # audit trail stays honest about what shape the model emitted vs. what was
    # stored (2026-06-19 finding). Empty list when the emit was already clean.
    if emit_repairs:
        decision_context["emit_repairs"] = emit_repairs

    try:
        enq = await enqueue_gated_action(
            auth,
            primitive=primitive,
            inputs=inputs,
            family="capital",
            decision_context=decision_context,
            source=input.get("source"),
            task_slug=input.get("task_slug"),
            agent_slug=input.get("agent_slug"),
            ttl_hours=ttl_hours,
        )
        if not enq.get("success"):
            return enq
        created = enq["proposal"]
        proposal_id = enq["proposal_id"]
        return {
            "success": True,
            "proposal_id": proposal_id,
            "proposal": {
                "id": proposal_id,
                "primitive": primitive,
                "family": "capital",
                "decision_context": decision_context,
                "expires_at": created.get("expires_at"),
                "status": "pending",
            },
        }
    except Exception as e:
        logger.error(f"[PROPOSE_ACTION] insert failed: {e}")
        return {"success": False, "error": "execution_error", "message": str(e)}


# =============================================================================
# ExecuteProposal
# =============================================================================

EXECUTE_PROPOSAL_TOOL = {
    "name": "ExecuteProposal",
    "description": """Approve-and-execute a previously proposed action by its proposal_id (ADR-193 + ADR-194 v2 Phase 2a).

Validates the proposal is still pending + not expired, then dispatches the underlying platform tool
via execute_primitive. Optionally merges modified_inputs to support user adjustments before approval.

For trading actions, re-runs the risk gate on the final (possibly modified) inputs before executing.
If the gate rejects at execution time, the proposal is marked rejected_at_execution.

ADR-194 v2 Phase 2a: every approval writes a decision entry to
/workspace/persona/judgment_log.md (the Reviewer's audit trail) and stamps
reviewer_identity + reviewer_reasoning on the action_proposals row.

Args:
  proposal_id: UUID of the proposal to execute
  modified_inputs: optional dict of field overrides (e.g., adjust qty, price)
  reviewer_identity: who fills the Reviewer seat for this approval.
    Defaults to "human:<user_id>" when invoked directly by the user.
    Future callers will pass "ai:<model-slug>" or "impersonated:<admin-as-persona>".
  reviewer_reasoning: short reasoning for the proposal-card UX and audit trail.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "proposal_id": {"type": "string"},
            "modified_inputs": {
                "type": "object",
                "description": "Optional field overrides merged over proposal.inputs.",
            },
            "reviewer_identity": {
                "type": "string",
                "description": "Who filled the Reviewer seat. Default: human:<user_id>.",
            },
            "reviewer_reasoning": {
                "type": "string",
                "description": "Short reasoning recorded to decisions.md + action_proposals.reviewer_reasoning.",
            },
        },
        "required": ["proposal_id"],
    },
}


async def handle_execute_proposal(auth: Any, input: dict) -> dict:
    """Approve + execute a proposal.

    ADR-194 v2 Phase 2a: persists `reviewer_identity` + `reviewer_reasoning`
    on the action_proposals row and appends a decision entry to
    /workspace/persona/judgment_log.md. Default reviewer_identity is
    "human:<user_id>" — matches the frontend approval UX; the LLM or
    AI Reviewer can override by passing reviewer_identity explicitly.
    """
    from services.primitives.registry import execute_primitive
    from services.freddie_audit import append_decision
    from services.freddie_chat_surfacing import write_freddie_message

    proposal_id = input.get("proposal_id")
    if not proposal_id:
        return {"success": False, "error": "proposal_id is required"}

    reviewer_identity = input.get("reviewer_identity") or f"human:{auth.user_id}"
    reviewer_reasoning = input.get("reviewer_reasoning") or ""

    # Fetch proposal
    try:
        result = (
            auth.client.table("action_proposals")
            .select("*")
            .eq("id", proposal_id)
            .eq(*substrate_scope_filter(auth.user_id))  # RLS enforces but be explicit
            .limit(1)
            .execute()
        )
        if not result.data:
            return {"success": False, "error": "proposal_not_found"}
        proposal = result.data[0]
    except Exception as e:
        return {"success": False, "error": "fetch_failed", "message": str(e)}

    # Status checks
    if proposal["status"] != "pending":
        return {
            "success": False,
            "error": "proposal_not_pending",
            "status": proposal["status"],
            "message": f"Proposal is '{proposal['status']}', cannot execute.",
        }

    # Expiration check
    try:
        expires_at = datetime.fromisoformat(proposal["expires_at"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) >= expires_at:
            # Mark expired and return error
            auth.client.table("action_proposals").update(
                {"status": "expired"}
            ).eq("id", proposal_id).execute()
            return {
                "success": False,
                "error": "proposal_expired",
                "message": f"Proposal expired at {proposal['expires_at']}.",
            }
    except Exception as e:
        logger.warning(f"[EXECUTE_PROPOSAL] expires_at parse failed: {e}")
        # Continue; don't block on parse error

    # ADR-307 D4: the primitive to replay is stored on the row. No map.
    tool_name = proposal["primitive"]
    if not tool_name:
        return {
            "success": False,
            "error": "missing_primitive",
            "message": f"proposal {proposal_id} has no primitive to replay",
        }
    # decision_context carries family-shaped operator context (capital:
    # rationale/expected_effect/reversibility/risk_warnings; substrate:
    # diff/message). action_type/reversibility no longer columns — derive
    # display values from decision_context for the audit trail.
    decision_context = proposal.get("decision_context") or {}
    family = proposal.get("family") or "capital"
    # `action_type`-shaped label for audit/log continuity (the reconciler keys
    # on id + inputs, not this label).
    action_type = f"{family}:{tool_name}"

    # Merge inputs
    merged_inputs = dict(proposal["inputs"] or {})
    modified = input.get("modified_inputs")
    if isinstance(modified, dict):
        merged_inputs.update(modified)

    # P&L unification (2026-05-12): inject proposal.id as underscore-prefixed
    # `_proposal_id` so platform-specific handlers can round-trip it to the
    # external platform (e.g., Alpaca's client_order_id field). The outcome
    # reconciler reads it back on fill to recover signal attribution from
    # action_proposals.inputs without heuristic joins on (symbol, qty, time).
    # Underscore prefix marks it as a dispatch-layer concern, not part of the
    # operator-authored proposal contract.
    merged_inputs.setdefault("_proposal_id", proposal_id)

    # Mark approved BEFORE executing — even if execution fails, approval was
    # recorded. We update to 'executed' on success or 'rejected_at_execution'
    # on validation failure inside the dispatch. Phase 2a: stamp reviewer
    # identity + reasoning at approve time, not execute time (so the audit
    # trail captures "who approved" even if downstream execution fails).
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        auth.client.table("action_proposals").update({
            "status": "approved",
            "approved_at": now_iso,
            "approved_by": "user",
            "reviewer_identity": reviewer_identity,
            "reviewer_reasoning": reviewer_reasoning or None,
        }).eq("id", proposal_id).execute()
    except Exception as e:
        logger.warning(f"[EXECUTE_PROPOSAL] approved update failed (non-fatal): {e}")

    # FOUNDATIONS v8.4 Axiom 1 fourth sub-clause (substrate-as-bus): write
    # the intent-to-execute audit entry BEFORE dispatching the real action.
    # Without this, a Supabase blip between execute_primitive() success and
    # the post-execute append_decision call would leave a real-world action
    # (e.g., Alpaca order placed) with no substrate record — substrate
    # would lag reality. Audit-first pattern: substrate records intent,
    # action runs, substrate records outcome. Both substrate writes are
    # best-effort; under failure the gap is between "intent recorded" and
    # "outcome recorded" rather than between "action happened" and "any
    # substrate trace exists" — a recoverable gap (orphan `executing`
    # entries are detectable by reconcilers) instead of a silent gap.
    intent_msg = (
        (reviewer_reasoning + "\n\n" if reviewer_reasoning else "")
        + "Operator confirmed; dispatching to execution layer."
    )
    reversibility_pre = decision_context.get("reversibility")
    await append_decision(
        auth.client, auth.user_id,
        proposal_id=proposal_id,
        action_type=action_type,
        decision="approve",
        reviewer_identity=reviewer_identity,
        reasoning=intent_msg,
        reversibility=reversibility_pre,
        outcome="executing",
    )

    # Dispatch via execute_primitive
    try:
        exec_result = await execute_primitive(auth, tool_name, merged_inputs)
    except Exception as e:
        logger.error(f"[EXECUTE_PROPOSAL] dispatch raised: {e}")
        exec_result = {"success": False, "error": "dispatch_error", "message": str(e)}

    # Update final status + append the outcome entry to decisions.md
    # (intent entry was already written pre-dispatch per audit-first pattern).
    reversibility = reversibility_pre
    if isinstance(exec_result, dict) and exec_result.get("success"):
        try:
            auth.client.table("action_proposals").update({
                "status": "executed",
                "executed_at": datetime.now(timezone.utc).isoformat(),
                "execution_result": exec_result,
            }).eq("id", proposal_id).execute()
        except Exception as e:
            logger.warning(f"[EXECUTE_PROPOSAL] status=executed update failed: {e}")
        logger.info(f"[EXECUTE_PROPOSAL] {proposal_id[:8]} executed successfully")
        # Audit trail OUTCOME entry — pairs with the pre-dispatch INTENT
        # entry to give operators a complete two-step audit trail per
        # execute (intent → outcome). Never blocks; logs on failure.
        await append_decision(
            auth.client, auth.user_id,
            proposal_id=proposal_id,
            action_type=action_type,
            decision="approve",
            reviewer_identity=reviewer_identity,
            reasoning=("Execution succeeded.\n\n" + (reviewer_reasoning or "")).strip(),
            reversibility=reversibility,
            outcome="executed",
        )
        # Unified chat thread — surface verdict to operator's active session.
        # Best-effort; decisions.md + action_proposals remain authoritative.
        await write_freddie_message(
            auth.client, auth.user_id,
            content=(reviewer_reasoning or f"Approved {action_type}."),
            proposal_id=proposal_id,
            verdict="approve",
            occupant=reviewer_identity,
            action_type=action_type,
            task_slug=proposal.get("task_slug"),
        )
        return {
            "success": True,
            "proposal_id": proposal_id,
            "action_type": action_type,
            "execution_result": exec_result,
            "reviewer_identity": reviewer_identity,
        }
    else:
        # Execution failed — could be risk-gate re-rejection, API failure, etc.
        err = (exec_result.get("error") if isinstance(exec_result, dict) else None) or "unknown"
        try:
            auth.client.table("action_proposals").update({
                "status": "rejected_at_execution",
                "execution_result": exec_result,
            }).eq("id", proposal_id).execute()
        except Exception as e:
            logger.warning(f"[EXECUTE_PROPOSAL] status=rejected_at_execution update failed: {e}")
        logger.info(f"[EXECUTE_PROPOSAL] {proposal_id[:8]} rejected at execution: {err}")
        # Audit trail captures the approval + downstream execution failure.
        downstream_msg = (
            (reviewer_reasoning + "\n\n" if reviewer_reasoning else "")
            + f"Approval recorded, but execution failed downstream: {err}"
        )
        await append_decision(
            auth.client, auth.user_id,
            proposal_id=proposal_id,
            action_type=action_type,
            decision="approve",
            reviewer_identity=reviewer_identity,
            reasoning=downstream_msg,
            reversibility=reversibility,
            outcome="rejected_at_execution",
        )
        await write_freddie_message(
            auth.client, auth.user_id,
            content=downstream_msg,
            proposal_id=proposal_id,
            verdict="approve",
            occupant=reviewer_identity,
            action_type=action_type,
            task_slug=proposal.get("task_slug"),
        )
        return {
            "success": False,
            "error": "execution_failed",
            "proposal_id": proposal_id,
            "execution_result": exec_result,
            "reviewer_identity": reviewer_identity,
        }


# =============================================================================
# RejectProposal
# =============================================================================

REJECT_PROPOSAL_TOOL = {
    "name": "RejectProposal",
    "description": """Reject a pending proposal by its proposal_id (ADR-193 + ADR-194 v2 Phase 2a).

Captures optional reason for learning. Marks proposal status='rejected'.
Use when the user declines an approval, or when YARNNN recognizes on
reflection that the proposal was wrong.

ADR-194 v2 Phase 2a: every rejection writes a decision entry to
/workspace/persona/judgment_log.md (the Reviewer's audit trail) and stamps
reviewer_identity + reviewer_reasoning on the action_proposals row.

Args:
  proposal_id: UUID of the proposal
  reason: optional short reason (shown in timeline / used for learning)
  reviewer_identity: who fills the Reviewer seat for this rejection.
    Defaults to "human:<user_id>".
  reviewer_reasoning: short reasoning for the proposal card + audit trail.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "proposal_id": {"type": "string"},
            "reason": {"type": "string"},
            "reviewer_identity": {
                "type": "string",
                "description": "Who filled the Reviewer seat. Default: human:<user_id>.",
            },
            "reviewer_reasoning": {
                "type": "string",
                "description": "Short reasoning recorded to decisions.md + action_proposals.reviewer_reasoning.",
            },
        },
        "required": ["proposal_id"],
    },
}


async def handle_reject_proposal(auth: Any, input: dict) -> dict:
    """Mark a proposal rejected.

    ADR-194 v2 Phase 2a: persists reviewer_identity + reviewer_reasoning +
    appends to /workspace/persona/judgment_log.md. Default reviewer_identity
    is "human:<user_id>".
    """
    from services.freddie_audit import append_decision
    from services.freddie_chat_surfacing import write_freddie_message

    proposal_id = input.get("proposal_id")
    if not proposal_id:
        return {"success": False, "error": "proposal_id is required"}

    reason = input.get("reason") or "user declined"
    reviewer_identity = input.get("reviewer_identity") or f"human:{auth.user_id}"
    reviewer_reasoning = input.get("reviewer_reasoning") or reason

    try:
        # Only update if still pending
        result = (
            auth.client.table("action_proposals")
            .update({
                "status": "rejected",
                "rejection_reason": reason,
                "reviewer_identity": reviewer_identity,
                "reviewer_reasoning": reviewer_reasoning or None,
            })
            .eq("id", proposal_id)
            .eq(*substrate_scope_filter(auth.user_id))
            .eq("status", "pending")
            .execute()
        )
        if not result.data:
            return {
                "success": False,
                "error": "proposal_not_pending_or_not_found",
                "message": "Proposal may not exist, belong to another user, or already be approved/rejected/executed.",
            }

        # ADR-307: derive audit labels from primitive + family-shaped
        # decision_context (action_type/reversibility are no longer columns).
        action_type = None
        reversibility = None
        try:
            proposal_row = result.data[0]
            _family = proposal_row.get("family") or "capital"
            _prim = proposal_row.get("primitive") or "unknown"
            action_type = f"{_family}:{_prim}"
            reversibility = (proposal_row.get("decision_context") or {}).get("reversibility")
        except Exception:
            pass

        logger.info(f"[REJECT_PROPOSAL] {proposal_id[:8]} rejected: {reason}")

        # Audit trail — never blocks; logs on failure.
        await append_decision(
            auth.client, auth.user_id,
            proposal_id=proposal_id,
            action_type=action_type or "unknown",
            decision="reject",
            reviewer_identity=reviewer_identity,
            reasoning=reviewer_reasoning,
            reversibility=reversibility,
            outcome="rejected",
        )

        # Unified chat thread — surface verdict to operator's active session.
        task_slug = None
        try:
            task_slug = proposal_row.get("task_slug")
        except Exception:
            pass
        await write_freddie_message(
            auth.client, auth.user_id,
            content=(reviewer_reasoning or f"Rejected: {reason}"),
            proposal_id=proposal_id,
            verdict="reject",
            occupant=reviewer_identity,
            action_type=action_type or "unknown",
            task_slug=task_slug,
        )

        return {
            "success": True,
            "proposal_id": proposal_id,
            "status": "rejected",
            "reason": reason,
            "reviewer_identity": reviewer_identity,
        }
    except Exception as e:
        logger.error(f"[REJECT_PROPOSAL] update failed: {e}")
        return {"success": False, "error": "execution_error", "message": str(e)}
