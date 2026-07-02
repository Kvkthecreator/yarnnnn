"""Reviewer Occupant Contract — the published substrate↔occupant ABI (ADR-315).

This module is the **named seam** between the domain-agnostic kernel (substrate +
seat + wake/dispatch harness) and the swappable Reviewer *occupant* (the AI agent
that fills the seat). Per ADR-315:

- The *seat* is substrate (`/workspace/persona/*` + ADR-209 attribution + the
  wake/verdict contract). It stays substrate — ADR-194 v2's "no ABC" retraction
  is preserved.
- The *occupant* is a module (`agents/freddie_agent.py`). It consumes a
  substrate-assembled context bag (`FreddieContext`), runs a bounded tool-use
  loop, and returns one shape (`FreddieOutput`). Today's occupant is
  `FREDDIE_MODEL_IDENTITY` (`ai:freddie-sonnet-v8`); the seat is
  occupant-class-agnostic (`human` / `ai` / `external:<service>` / `impersonated`,
  per FOUNDATIONS Derived Principle 15 + reviewer-substrate.md).

**Pure data, zero heavy imports.** This module imports `typing` only — no
`anthropic`, no `services.*`. That is deliberate and load-bearing: it is the
standing proof that the ABI is decoupled from the LLM runtime. The kernel/harness
(`services/programs.py`, `routes/feed.py`, `services/wake.py`,
`services/review_proposal_dispatch.py`) import the contract from here, never from
the occupant implementation — closing the one reverse leak (ADR-315 D3).

The kernel side of the ABI is `services/freddie_envelope.py::
load_freddie_governance_envelope()`, which reads substrate and returns an
`envelope_dict` keyed by `FreddieContext` field names. The occupant side is
`agents/freddie_agent.py::invoke_freddie(trigger, context)`. The full contract:

    load_freddie_governance_envelope()  →  FreddieContext
        →  invoke_freddie(trigger, context)  →  FreddieOutput
            →  freddie_audit / dispatcher write back to substrate

History note: these three symbols were defined inside `freddie_agent.py` until
ADR-315 (2026-06-04) promoted them here as the canonical definition home.
`freddie_agent.py` re-exports them so existing `from agents.freddie_agent
import ...` callers keep resolving (one definition, re-exported — not a dual
definition).
"""

from __future__ import annotations

from typing import TypedDict


#: ADR-256: occupant identity bumped to v8. v1-v7 history in git log.
#: v8 = unified invoke_freddie() replacing four separate mode-functions.
#: ADR-315: canonical home moved here from freddie_agent.py — the occupant's
#: self-identity belongs with the published contract, not buried in the impl.
FREDDIE_MODEL_IDENTITY = "ai:freddie-sonnet-v8"


# ---------------------------------------------------------------------------
# Output type — single shape for all triggers (ADR-256 D5)
# ---------------------------------------------------------------------------

class FreddieOutput(TypedDict, total=False):
    """Unified output of invoke_freddie() across both trigger shapes
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

class FreddieContext(TypedDict, total=False):
    """Substrate bag passed by callers. Each trigger pre-loads what it has;
    the Reviewer uses ReadFile tool to fetch anything else it needs.

    Three valid context shapes per trigger sub-shape (enforced by
    ``_validate_context_shape`` at the top of ``invoke_freddie``):

      1. proposal-arrival (trigger="reactive"):
         REQUIRES: proposal_row
      2. recurrence-fire (trigger="reactive"):
         REQUIRES: recurrence_prompt AND recurrence_slug
      3. addressed (trigger="addressed"):
         REQUIRES: user_message

    A context bag that doesn't satisfy any shape causes ``invoke_freddie``
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
    # ADR-381 D3 / ADR-380 D3 — the Rung harness split (carried, not exercised).
    #   mandate_md + autonomy_md are CARRIED on every wake (one contract across
    #   activation rungs — the kernel never forks FreddieContext by occupant)
    #   but EXERCISED only at Rung 2 (a consequential-action persona occupant,
    #   ADR-382). Over a Rung-1 steward (Freddie, reversible substrate) they are
    #   DEGENERATE — there is no consequential external write for the AUTONOMY
    #   ceiling to gate, and a MANDATE with no value-moving action to hard-gate
    #   is a config string. Do NOT read budget_yaml/pace the same way: those ARE
    #   exercised at Rung 1 (Freddie burns tokens + has a cadence). Consequence
    #   (load-bearing): "the autonomy harness was validated on Freddie" is FALSE.
    #   Conditionally stripping these at Rung 1 would fork the contract by
    #   occupant (Singular-Implementation violation) — the carriage is correct;
    #   the degeneracy is in EXERCISE, not LOADING. Canon prose:
    #   docs/architecture/reviewer-occupant-contract.md §"The Rung-1 harness split."
    mandate_md: str
    autonomy_md: str
    # ADR-275 refinement (run-2): operator-authored cadence preferences.
    # Pre-loaded into the wake envelope — same shape as MANDATE/AUTONOMY/etc.
    # The Reviewer cannot author cadence correctly without seeing what the
    # operator declared they want on cadence. Treating it as load-bearing
    # substrate (not a "remember to ReadFile" side-quest) makes Derived
    # Principle 18's first-wake obligation structural.
    preferences_yaml: str
    # ADR-327 — operator-declared budget (Trigger-dimension dial of the
    # Budget + Autonomy + Identity trifecta; supersedes the retired pace
    # dial). The operation's dollar spend envelope over a timeframe.
    # Pre-loaded so the Reviewer reasons about wake allocation within the
    # operator's declared envelope (the self-improving loop, ADR-327 D6).
    budget_yaml: str
    # ADR-345 — the operation's output contract (Expected Output): what the
    # workspace owes (kind + delivery-cadence + bar). Orthogonal to budget
    # (Rhythm = how often the agent works; Expected Output = what it owes when
    # it does). The machine face of MANDATE ## Expected Output. The standing-
    # obligation check (DP30) reads it declared-then-derive (ADR-344 fallback).
    # Empty string when no _expected_output.yaml is authored (key always present).
    expected_output_yaml: str
    # ADR-284: seat occupant + standing intent. The canonical envelope helper
    # populates both via `_UNIVERSAL_ENVELOPE_DECLS`; the renderer at
    # `_build_user_message` reads them via `ctx.get(...)`. Declaring them
    # here closes the prior drift between the TypedDict + the renderer +
    # the envelope helper (surfaced by the 2026-05-21 ADR-276 test gate
    # realignment).
    occupant_md: str
    standing_intent_md: str
    # ADR-364 D2: the reflection gap-fact — recent verdicts joined to their
    # ground-truth outcomes by proposal_id (the closed intent→outcome loop),
    # presented (not judged). The Reviewer authors persona/reflection.md from
    # it. Empty string when no joinable verdict↔outcome pairs exist yet.
    reflection_gap_fact: str
    # ADR-387 follow-on (2026-06-30): the attribution fact — recent
    # workspace_file_versions rows (path · authored_by · message · when),
    # presented raw (DP19-clean: the kernel presents, Freddie's
    # attribution-integrity rule judges). The steward's perception surface for
    # the attribution-integrity + intake-placement duties — without it a sweep
    # has NO signal that attribution drifted (the bare-Freddie eval gap,
    # docs/evaluations/2026-06-29-freddie-bare-workspace-steward-FINDING.md
    # Finding 1: Freddie placed a mis-attributed file but accepted the
    # authored_by lie because nothing surfaced it). Empty when no recent
    # revisions. Analogous to reflection_gap_fact but on the perception axis.
    attribution_fact: str
    # Steward-envelope re-scope (2026-06-30): the workspace as a commons-with-a-
    # perimeter. The principal commons (WHO may write + who DID recently) gives
    # the attribution_fact a REFERENT — the steward cannot judge whether
    # `authored_by: operator` is honest without knowing the workspace's
    # principals. The peripheral field (connection + source HEALTH) gives the
    # connection-hygiene + source-freshness duties perceptible state. Both
    # present-not-judged (DP19), both empty on a quiet single-owner bare
    # workspace. See docs/analysis/perception-and-the-principal-commons-first-
    # principles-2026-06-30.md. principal = intent-bearing/grant-backed (judge
    # HONESTY); peripheral = driver-class transport (judge HEALTH).
    principal_commons_fact: str
    peripheral_field_fact: str
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
    # ADR-327 D6 — calibration evidence (the self-improving loop). Kernel-
    # mirrored substrate correlating the Reviewer's cadence-authoring history
    # against ground-truth outcome quality. Read before reasoning about cadence.
    calibration_md: str
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
