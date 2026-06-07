"""Unified Permission Gate — ADR-307.

ONE gate, above all primitives. The permission decision (apply / queue / deny)
is resolved here, at the single execute-by-name chokepoint (`execute_primitive`
in registry.py), NOT inside individual primitive handlers. This is the
Claude-Code architecture (uniform harness gate + `isReadOnly` fail-closed +
deny > ask > allow precedence) adapted to YARNNN's absent-operator setting:
where Claude Code pauses one synchronous loop and fails closed when no human is
present, YARNNN persists the "ask" outcome to the durable `action_proposals`
queue (the Reviewer acts in the operator's absence and cannot pause in-loop).

Taxonomy (ADR-307 D1–D3):
  - A *consequential* primitive mutates substrate or has external effect.
    It passes the gate.
  - A *read-only* primitive (read / search / introspection / narration) is
    non-consequential. It never gates and never queues.
  - The gate resolves, per call, from:
      (autonomy_mode × primitive.read_only × action_class × governance-locks)
    to exactly one of:
      APPLY  — run the handler now (read-only, or autonomous in-scope)
      QUEUE  — route to action_proposals; operator approves later (the one
               waiting room; Channel surface per FOUNDATIONS DP12)
      DENY   — governance-locked; bypass-immune (gates even under autonomous)

`read_only` is declared per primitive in READ_ONLY_PRIMITIVES below, fail-closed:
a primitive NOT in the set is treated as consequential (Claude Code's
"assume writes" default, Tool.ts:757-760).
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PermissionDecision(str, Enum):
    """The three gate outcomes (ADR-307 D1). Maps to Claude Code's
    allow | ask | deny, with `ask` realized as a durable queue."""

    APPLY = "apply"   # run the handler now
    QUEUE = "queue"   # route to action_proposals; operator approves later
    DENY = "deny"     # governance-locked; bypass-immune


# ---------------------------------------------------------------------------
# read_only declarations (ADR-307 D2) — the canonical gated-vs-not boundary.
# Fail-closed: any primitive NOT listed is consequential and passes the gate.
# ---------------------------------------------------------------------------
#
# Reads (entity/file/introspection layers): observe substrate, mutate nothing.
# Narration (Clarify, ReturnVerdict): emit narrative entries, mutate no
# operator/operational substrate — non-consequential per ADR-307 D2.
#
# This set is the single source of truth for "this primitive never gates."
# A new read/introspection primitive MUST be added here or it will (correctly,
# fail-closed) be treated as consequential.
READ_ONLY_PRIMITIVES: frozenset[str] = frozenset({
    # Entity layer — reads
    "LookupEntity",
    "ListEntities",
    "SearchEntities",
    # File layer — reads
    "ReadFile",
    "ListFiles",
    "SearchFiles",
    "ReadAgentFile",
    # Authored-substrate revision reads (ADR-209 Phase 3)
    "ListRevisions",
    "ReadRevision",
    "DiffRevisions",
    # Semantic-query read (ADR-151)
    "QueryKnowledge",
    # Introspection
    "GetSystemState",
    "DiscoverAgents",
    "list_integrations",
    # External read
    "WebSearch",
    # Narration / interaction (non-consequential — emit narrative, mutate no
    # operator/operational substrate). ReturnVerdict closes the Reviewer turn;
    # Clarify surfaces a question. Neither is a substrate mutation or external
    # effect that the operator must pre-approve.
    "Clarify",
    "ReturnVerdict",
})


def is_read_only(name: str) -> bool:
    """A primitive is read-only iff explicitly declared. Fail-closed:
    unknown / unlisted primitives are consequential (ADR-307 D2)."""
    return name in READ_ONLY_PRIMITIVES


# ---------------------------------------------------------------------------
# action_class mapping (ADR-293 D4 + ADR-307 D5) — consequential primitives.
# Capital actions (verdict-bound platform writes via the proposal mechanism)
# vs substrate actions (everything else that mutates substrate or has external
# effect). The class selects which branch of should_auto_apply applies.
# ---------------------------------------------------------------------------
#
# Capital primitives carry verdict/ceiling semantics (estimated_cents,
# reversibility). Everything consequential-but-not-capital is `substrate`.
_CAPITAL_PRIMITIVES: frozenset[str] = frozenset({
    # ExecuteProposal binds a capital action the operator approved; the
    # capital gate is applied at the proposal-dispatch layer
    # (review_proposal_dispatch) where verdict + estimated_cents are known.
    "ExecuteProposal",
})


def action_class_for(name: str) -> str:
    """Return the action_class ('capital' | 'substrate') for a consequential
    primitive. Read-only primitives never reach this (they short-circuit
    APPLY in the gate)."""
    if name in _CAPITAL_PRIMITIVES:
        return "capital"
    return "substrate"


# Primitives whose QUEUE realization the gate owns directly (ADR-307 D4/D5).
# A Reviewer call to one of these under bounded/manual is enqueued as a
# family='substrate' proposal by execute_primitive; under autonomous it
# applies (subject to each primitive's own orthogonal resource ceiling —
# Schedule's pace cap, RuntimeDispatch/DispatchSpecialist's token budget —
# which remain additive checks, not replaced by the autonomy gate).
#
# WriteFile is path-addressed (governance lock + diff). The others are
# substrate-mutating but not path-addressed; for them the gate applies only
# the delegation decision (manual/bounded → queue, autonomous → apply).
GATE_QUEUEABLE_PRIMITIVES: frozenset[str] = frozenset({
    "WriteFile",
    "Schedule",
    "ManageHook",
    "ManageAgent",
    "ManageDomains",
    "RuntimeDispatch",
    "DispatchSpecialist",
    # ADR-325: Embed is consequential + autonomy-governed (the autonomy mode IS
    # the embed policy). Under bounded/manual a Reviewer Embed QUEUEs; under
    # autonomous it applies. Carries an orthogonal cost ceiling (embed daily cap)
    # checked in the handler — additive, like Schedule's pace cap.
    "Embed",
})

#: Subset of GATE_QUEUEABLE_PRIMITIVES that are path-addressed (governance-lock
#: + diff apply). Only WriteFile today.
_PATH_ADDRESSED_QUEUEABLE: frozenset[str] = frozenset({"WriteFile"})


async def resolve_permission(auth: Any, name: str, input: dict) -> tuple[PermissionDecision, str]:
    """The single permission gate (ADR-307 D1). Called by execute_primitive
    BEFORE dispatching to a handler.

    Returns (decision, reason):
      APPLY → run the handler
      QUEUE → execute_primitive enqueues a family='substrate' proposal instead
              of running the handler (operator approves later)
      DENY  → governance-locked; bypass-immune

    The gate engages only for Reviewer-authored consequential calls (ADR-293
    scopes the autonomy gate to Reviewer-runtime writes; operator + headless
    callers authorize via their own paths). Read-only primitives and
    non-Reviewer callers resolve APPLY.

    For a Reviewer WriteFile (the Phase-2 queueable primitive): the governance
    lock → DENY (bypass-immune); the autonomy decision → APPLY under
    `autonomous`, QUEUE under `bounded`/`manual`. The capital path's gate stays
    at review_proposal_dispatch (verdict + estimated_cents known there).
    """
    # Read-only / narration → never gates (ADR-307 D2).
    if is_read_only(name):
        return PermissionDecision.APPLY, "read_only"

    # Foreign-LLM (MCP) caller gate — ADR-310 follow-on.
    # The MCP caller is lower-trust than operator/Reviewer: it may contribute to
    # the commons but must never directly rewrite operator-authored intent or
    # the Reviewer seat. A path-addressed write under a locked subtree DENYs;
    # all other foreign writes APPLY (and fire the eventually-judged wake per
    # ADR-310 D2). This branch precedes the non_reviewer short-circuit so the
    # foreign caller does NOT inherit the operator/headless free-pass.
    if getattr(auth, "caller_identity", "") == "yarnnn:mcp":
        if name in _PATH_ADDRESSED_QUEUEABLE:  # WriteFile today
            from services.primitives.workspace import (
                _resolve_workspace_path_for_gate, _is_path_locked, _caller_class,
            )
            path = _resolve_workspace_path_for_gate(input)
            if path is not None and _is_path_locked(_caller_class(auth), path):
                return PermissionDecision.DENY, f"mcp_topology_locked:{path}"
        return PermissionDecision.APPLY, "mcp_caller_unlocked_path"

    # Autonomy gate scoped to Reviewer-runtime calls (ADR-293).
    if not getattr(auth, "reviewer_caller", False):
        return PermissionDecision.APPLY, "non_reviewer_caller"

    # Capital actions gate at the proposal-dispatch layer (verdict + cents),
    # not here. They reach execute_primitive only via ExecuteProposal on
    # approve — already operator-authorized.
    if name not in GATE_QUEUEABLE_PRIMITIVES:
        return PermissionDecision.APPLY, f"consequential:{action_class_for(name)}:not_gate_owned"

    # Gate-owned consequential primitive authored by the Reviewer. Resolve the
    # autonomy decision (+ governance lock for path-addressed primitives).
    try:
        from services.review_policy import (
            load_autonomy, autonomy_for_domain, should_auto_apply,
        )

        substrate_path = ""
        if name in _PATH_ADDRESSED_QUEUEABLE:
            # Path-addressed (WriteFile): resolve the target path; non-workspace
            # scope is not autonomy-gated; governance lock → bypass-immune DENY.
            from services.primitives.workspace import (
                _resolve_workspace_path_for_gate, _is_path_locked, _caller_class,
            )
            path = _resolve_workspace_path_for_gate(input)
            if path is None:
                return PermissionDecision.APPLY, "non_workspace_scope"
            if _is_path_locked(_caller_class(auth), path):
                return PermissionDecision.DENY, f"topology_locked:{path}"
            substrate_path = path

        # Delegation decision (manual/bounded → queue; autonomous → apply).
        # For non-path-addressed primitives substrate_path="" — never_auto
        # path-matching simply doesn't match; the delegation gate still fires.
        autonomy = load_autonomy(auth.client, auth.user_id)
        autonomy_policy = autonomy_for_domain(autonomy, "")
        allowed, gate_reason = should_auto_apply(
            autonomy_policy=autonomy_policy,
            action_class="substrate",
            substrate_path=substrate_path,
            caller_identity=getattr(auth, "caller_identity", "") or "",
        )
    except Exception as exc:  # fail closed — queue rather than apply
        logger.warning(
            "[PERMISSION] gate evaluation failed for %s: %s — failing closed (QUEUE).",
            name, exc,
        )
        return PermissionDecision.QUEUE, f"gate_error:{exc}"

    if allowed:
        return PermissionDecision.APPLY, f"autonomy_allows:{gate_reason}"
    return PermissionDecision.QUEUE, f"autonomy_requires_approval:{gate_reason}"
