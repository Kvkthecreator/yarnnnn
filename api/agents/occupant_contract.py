"""Reviewer Occupant Contract — the published substrate↔occupant ABI (ADR-315).

This module is the **named seam** between the domain-agnostic kernel (substrate +
seat + wake/dispatch harness) and the swappable Reviewer *occupant* (the AI agent
that fills the seat). Per ADR-315:

- The *seat* is substrate (`/workspace/persona/*` + ADR-209 attribution + the
  wake/verdict contract). It stays substrate — ADR-194 v2's "no ABC" retraction
  is preserved.
- The *occupant* is a module (`agents/reviewer_agent.py`). It consumes a
  substrate-assembled context bag (`ReviewerContext`), runs a bounded tool-use
  loop, and returns one shape (`ReviewerOutput`). Today's occupant is
  `REVIEWER_MODEL_IDENTITY` (`ai:reviewer-sonnet-v8`); the seat is
  occupant-class-agnostic (`human` / `ai` / `external:<service>` / `impersonated`,
  per FOUNDATIONS Derived Principle 15 + reviewer-substrate.md).

**Pure data, zero heavy imports.** This module imports `typing` only — no
`anthropic`, no `services.*`. That is deliberate and load-bearing: it is the
standing proof that the ABI is decoupled from the LLM runtime. The kernel/harness
(`services/programs.py`, `routes/feed.py`, `services/wake.py`,
`services/review_proposal_dispatch.py`) import the contract from here, never from
the occupant implementation — closing the one reverse leak (ADR-315 D3).

The kernel side of the ABI is `services/reviewer_envelope.py::
load_reviewer_governance_envelope()`, which reads substrate and returns an
`envelope_dict` keyed by `ReviewerContext` field names. The occupant side is
`agents/reviewer_agent.py::invoke_reviewer(trigger, context)`. The full contract:

    load_reviewer_governance_envelope()  →  ReviewerContext
        →  invoke_reviewer(trigger, context)  →  ReviewerOutput
            →  reviewer_audit / dispatcher write back to substrate

History note: these three symbols were defined inside `reviewer_agent.py` until
ADR-315 (2026-06-04) promoted them here as the canonical definition home.
`reviewer_agent.py` re-exports them so existing `from agents.reviewer_agent
import ...` callers keep resolving (one definition, re-exported — not a dual
definition).
"""

from __future__ import annotations

from typing import TypedDict


#: ADR-256: occupant identity bumped to v8. v1-v7 history in git log.
#: v8 = unified invoke_reviewer() replacing four separate mode-functions.
#: ADR-315: canonical home moved here from reviewer_agent.py — the occupant's
#: self-identity belongs with the published contract, not buried in the impl.
REVIEWER_MODEL_IDENTITY = "ai:reviewer-sonnet-v8"


# ---------------------------------------------------------------------------
# Output type — single shape for all triggers (ADR-256 D5)
# ---------------------------------------------------------------------------

class ReviewerOutput(TypedDict, total=False):
    """Unified output of invoke_reviewer() across both trigger shapes
    (addressed + reactive). Trigger taxonomy collapsed from four to two
    by ADR-263 D2 — the historical reflection/heartbeat-specific verdicts
    survive as substrate-write directives the Reviewer can emit on any
    trigger; the trigger axis no longer gates which verdicts are valid.

    `verdict`, `reasoning`, `confidence` always present on success.
    `proposals` + `evidence_summary` may appear on any reactive
    invocation that includes recurrence-fire prompts directing the
    Reviewer to author proposals or summarize evidence.
    `actions_taken` records tool calls made during the loop (audit trail).
    `invocation_id` (ADR-289 D4) — the execution_events.id of this cycle;
    propagated from the caller and re-exposed so downstream surfacing /
    audit writes share one stable invocation atom identifier.
    """
    verdict: str          # approve|reject|defer (proposal-arrival reactive)
                          # no_change|narrow|relax|character_note|pause_autonomy
                          #   (reflection-shaped recurrence prompts)
                          # stand_down (no action warranted)
    reasoning: str
    confidence: str       # low | medium | high
    actions_taken: list   # tool calls executed during the loop
    invocation_id: str    # ADR-289: execution_events.id for this cycle
    # reflection-only
    proposals: list
    evidence_summary: str
    # ADR-291 cost ledger pass-through — the Reviewer's loop accumulates
    # token usage (incl. cache breakdown) and surfaces it on the output so
    # the dispatcher can write the authoritative `execution_events` row.
    # NULL when the loop never reached LLM dispatch (shape-violation
    # early-return).
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_create_tokens: int
    model: str
    tool_rounds: int


# ---------------------------------------------------------------------------
# Trigger context — caller pre-loads relevant substrate (ADR-256 D1)
# ---------------------------------------------------------------------------

class ReviewerContext(TypedDict, total=False):
    """Substrate bag passed by callers. Each trigger pre-loads what it has;
    the Reviewer uses ReadFile tool to fetch anything else it needs.

    Three valid context shapes per trigger sub-shape (enforced by
    ``_validate_context_shape`` at the top of ``invoke_reviewer``):

      1. proposal-arrival (trigger="reactive"):
         REQUIRES: proposal_row
      2. recurrence-fire (trigger="reactive"):
         REQUIRES: recurrence_prompt AND recurrence_slug
      3. addressed (trigger="addressed"):
         REQUIRES: user_message

    A context bag that doesn't satisfy any shape causes ``invoke_reviewer``
    to fail loudly with a log error + return None — replacing the prior
    silent fallback where mismatched context names caused the Reviewer to
    wake with empty user message and produce inert stand_down. The bug
    that prompted this discipline lived for days because nothing asserted
    the shape (commit 85c9736 fixed the symptom — discarded reasoning;
    this contract enforcement prevents the class of bug).

    Field naming: ``recurrence_prompt`` + ``recurrence_slug`` are
    canonical for the recurrence-fire shape. The legacy ``trigger_slug``
    field was removed 2026-05-13 — singular implementation per CLAUDE.md
    item 1.
    """
    # Governance layer — all triggers should pass these when available
    identity_md: str
    principles_md: str
    precedent_md: str
    mandate_md: str
    autonomy_md: str
    # ADR-275 refinement (run-2): operator-authored cadence preferences.
    # Pre-loaded into the wake envelope — same shape as MANDATE/AUTONOMY/etc.
    # The Reviewer cannot author cadence correctly without seeing what the
    # operator declared they want on cadence. Treating it as load-bearing
    # substrate (not a "remember to ReadFile" side-quest) makes Derived
    # Principle 18's first-wake obligation structural.
    preferences_yaml: str
    # ADR-298 D11 — operator-declared pace (Trigger-dimension dial of the
    # Pace + Autonomy + Persona trifecta). Pre-loaded so the Reviewer can
    # surface Clarify with the actual declared kind when Schedule() returns
    # pace_exceeded, and so the wake envelope carries the workspace's
    # current cadence intent.
    pace_yaml: str
    # ADR-284: seat occupant + standing intent. The canonical envelope helper
    # populates both via `_UNIVERSAL_ENVELOPE_DECLS`; the renderer at
    # `_build_user_message` reads them via `ctx.get(...)`. Declaring them
    # here closes the prior drift between the TypedDict + the renderer +
    # the envelope helper (surfaced by the 2026-05-21 ADR-276 test gate
    # realignment).
    occupant_md: str
    standing_intent_md: str
    # Domain substrate
    ground_truth_md: str
    risk_md: str
    operator_profile_md: str
    # Sub-shape: proposal-arrival
    proposal_row: dict
    # Sub-shape: recurrence-fire (canonical key names; both must be set
    # together — invocation_dispatcher.py passes them in lockstep).
    recurrence_prompt: str
    recurrence_slug: str
    # Sub-shape: addressed (operator chat turn)
    user_message: str
    conversation_window: str
    # Shared across shapes (optional pre-loads the caller can include)
    recent_decisions_md: str
    signal_files: str
    workspace_state: str
    # Spec inventory — bundle-shipped capability specs under /workspace/operation/specs/.
    # Format: one line per spec, "- {path} — {title}". Bodies read on demand
    # via ReadFile. Closes the discovery gap that produced the operator-
    # facing question "do those spec files exist?" in standing intent.
    specs_inventory: str
    # ADR-274 / FOUNDATIONS v8.5: time + market context for Trigger-authoring.
    # Surfaces "now" perception per the Axiom 4 amendment (time is envelope,
    # not substrate). Callers assemble via _format_operating_context_block.
    operating_context_block: str
    # ADR-301 Pulse envelope — Reviewer's perception of its own cadence +
    # recent fires. Both files are kernel-mirrored substrate written per
    # scheduler tick by services.kernel_mirrors. The Reviewer reads them
    # to reason from substrate (not memory) about its own pulse.
    schedule_index_md: str
    recent_execution_md: str
    # Wake context (ADR-296 v2 wake source taxonomy + 2026-05-27 Hat-A
    # parity fix). Pre-loaded so the Reviewer perceives WHY it was woken,
    # not just that it was woken. Pre-this-field, the fine-grained
    # wake_source (cron_tick | substrate_event | proposal_arrival |
    # manual_fire | addressed) collapsed to the coarse `trigger` parameter
    # (reactive | addressed) before reaching the Reviewer. The eval-suite
    # framework surfaced this as the "wake-source-disambiguation" gap:
    # within trigger=reactive, the Reviewer could not distinguish a cron
    # fire from a substrate-event fire from a proposal arrival, even
    # though those are structurally different reasoning contexts.
    #
    # All four scaffolded substrate inputs (MANDATE + AUTONOMY + PACE +
    # PREFERENCES) had file→loader→envelope→renderer parity; wake_source
    # was the missing fifth input. This field closes the gap.
    #
    # `wake_source` is the ADR-296 v2 taxonomy value. `triggering_revision_id`
    # populated for substrate_event wakes (the workspace_file_versions row
    # whose creation fired the hook). `triggering_path` populated for
    # substrate_event wakes (the workspace_files path that transitioned).
    # Both `triggering_*` fields are empty strings for non-substrate_event
    # wakes (cron_tick / proposal_arrival / manual_fire / addressed).
    wake_source: str
    triggering_revision_id: str
    triggering_path: str
