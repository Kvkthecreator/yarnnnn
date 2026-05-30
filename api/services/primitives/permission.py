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


async def resolve_permission(auth: Any, name: str, input: dict) -> tuple[PermissionDecision, str]:
    """The single permission gate (ADR-307 D1). Called by execute_primitive
    BEFORE dispatching to a handler.

    Returns (decision, reason). The caller acts on the decision:
      APPLY → run the handler
      QUEUE → route the action to action_proposals (Phase 2+)
      DENY  → return a governance_locked error

    Phase 1 (this commit) is BEHAVIOR-PRESERVING: it classifies read-only vs
    consequential and resolves the autonomy decision through this one function,
    but the per-handler outcomes for capital + substrate are unchanged (capital
    still queues at the dispatch layer; substrate still errors inside
    handle_write_file). Phase 2 moves the substrate QUEUE realization here.

    The gate only engages for Reviewer-authored calls (the operator and
    headless production callers have their own authorization paths — ADR-293
    scopes the autonomy gate to Reviewer-runtime writes). Non-Reviewer callers
    and read-only primitives resolve APPLY.
    """
    # Read-only / narration → never gates (ADR-307 D2).
    if is_read_only(name):
        return PermissionDecision.APPLY, "read_only"

    # The autonomy gate is scoped to Reviewer-runtime consequential writes
    # (ADR-293). Operator-chat and headless callers authorize via their own
    # paths and are not autonomy-gated here.
    if not getattr(auth, "reviewer_caller", False):
        return PermissionDecision.APPLY, "non_reviewer_caller"

    # Consequential + Reviewer caller → resolve the autonomy decision.
    # NOTE (Phase 1): the substrate-write path still resolves its own gate
    # inside handle_write_file (preserved behavior); this function returns the
    # advisory classification so execute_primitive can short-circuit reads and
    # so Phase 2/3 can move QUEUE realization here without a second decision
    # site. The capital path resolves at review_proposal_dispatch.
    action_class = action_class_for(name)
    return PermissionDecision.APPLY, f"consequential:{action_class}:phase1_passthrough"
