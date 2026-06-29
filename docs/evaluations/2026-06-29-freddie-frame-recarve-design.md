# Freddie persona-frame re-carve — design + as-built record

**Date**: 2026-06-29
**Hat**: A (system editor). The behavioral half of [ADR-383](../adr/ADR-383-the-consistent-agent-framework-and-mandate-as-purpose.md) + the [Freddie re-cut](../adr/ADR-381-freddie-the-rung-1-substrate-steward.md).
**Status**: **Implemented** (commit `13b1be3`). This is the design that was confirmed with the operator + the as-built notes. Referenced by `api/prompts/CHANGELOG.md [2026.06.29.4]`, `agent-composition.md` §3.2.1/§4.4 (the ADR-383 amendment banner), and `reviewer-seat-substrate.md`.

---

## 1. The thesis (confirmed with operator)

The persona frame (`api/agents/reviewer_agent.py::_compute_minimal_frame`) carries **only** the two irreducible model↔runtime things, expressed for the **installed steward** self-model:
1. **Principal-shift** → "you are this workspace's installed *agent* — the steward / the system agent" (NOT "the operator's installed *judgment*").
2. **Action-grammar** → tool-call-IS-action, direct-not-execute, read-fresh, anti-confabulation, cite-sources, close-the-cycle, topological write boundary. **Rung-agnostic — unchanged in substance.**

The **consequential-judgment posture** (standing-obligation / aperture-floor / capital-action / EV-over-ground-truth) **leaves the frame**. It is not the *systemic* occupant's (the steward's); it belongs to the program-authored `principles.md` the envelope renders. When a program is active, *its* `principles.md` carries that posture and the occupant reasons from it as substrate.

## 2. The finding that made it safe (no dogfood loss, no fork)

**The bundles already carry the judgment posture.** Both `alpha-trader` and `alpha-author` `principles.md` already hold the aperture/floor split, the writable-path/standing-obligation test, dormancy→widen-aperture, and when-to-Clarify — explicitly tagged *"Migrated here from the system persona-frame by the 2026-05-29 collapse."* So the frame's standing-obligation block was a **duplicate**. Removing it strips no behavior from a program workspace — the canonical copy lives in the bundle the agent reads every wake.

**No rung-branch / no second frame.** The frame is one static cached prompt (`_SYSTEM_PROMPT_CACHE`), shared across every wake and the running trader/author dogfood. "Rung" is an activation-ladder concept, not a prompt-architecture switch. The re-carve is a *reframe + residue removal* on the one frame, with the steward-vs-judgment routing done by the **MANDATE/principles.md content** (which ADR-383's steward defaults make always-present), not by a code branch.

## 3. What shipped (as-built, commit `13b1be3`)

| Block | Change |
|---|---|
| **"What you are"** | Reframed steward-first: "you are this workspace's installed agent… read your MANDATE to know which you are: stewardship (the system agent) or, when a program declares an operation, that operation's installed judgment." The Variant-F sentence (DP21) **kept verbatim** as the SEAT's structure (occupant-agnostic; the formalization gate requires it). IDENTITY-empty fallback "skeptical, independent judge" → "careful, independent steward". |
| **"How you act"** | "you cannot bind a **capital** action" → "a **consequential** action" + a clause: the AUTONOMY ceiling has nothing to bind over reversible substrate (the system-agent case) and binds only once an operation's value-moving action is in play. Directs-not-executes grammar unchanged (coherence gate). |
| **Standing-obligation residue (the ~349–379 block)** | **REMOVED** (duplicate of bundle principles.md). Replaced with a rung-agnostic pointer: "a wake is a situation; your principles.md declares what your operation is on the hook to produce and how to read a shortfall — apply it; for the system agent it is stewardship, for an operation it is that operation's judgment." |
| **Docstring** | Added the ADR-383 two-order note. |

Frame size: ~11K → **~7.5K chars** (residue removal; consistent with the ADR-306 collapse discipline).

## 4. Canon edits that shipped with it

- **FOUNDATIONS DP21 two-order amendment** (commit `13b1be3`): the 7 structural claims describe the SEAT (occupant-agnostic); the systemic frame's self-model is steward-first, judgment-on-operation-activation. Aligns DP21 to the already-ratified DP33 (the two-order collapse).
- **`test_adr314_substrate_conditional_posture.py`**: the MANDATE-standby premise updated for ADR-383 (MANDATE is now always populated — steward-default for a bare workspace; the general honest-about-absent-headers behavior is preserved + asserted).
- **`agent-composition.md` §3.2.1 + §4.4** (doc-cascade commit): the ADR-383 amendment banner — the capital-judgment stance is no longer frame-resident; the frame carries the rung-agnostic obligation-pointer + the steward self-model; the *content* is each agent's principles.md.

## 5. Partition (§3.2.1) + composed-coherence (§3.2.2) — run on the as-built frame

- **§3.2.1 partition**: the frame carries only principal-shift (steward self-model) + action-grammar (incl. the obligation-pointer). The one rule-of-judgment block (standing-obligation) is gone → principles.md. **PASS.**
- **§3.2.2 composed-coherence**: read the assembled frame + envelope (MANDATE + principles.md) as one document — (a) what it is: steward-or-judgment by MANDATE, coherent; (b) how it acts: ONE directs-not-executes grammar, unchanged; (c) where agency ends: topological boundary + consequential-action ceiling + witness dial. **PASS, and strictly more coherent in the bare-workspace state** (the frame no longer asserts "you are a judgment seat" over a steward workspace with no operation).

## 6. Validation (the confidence checkpoints)

- `test_reviewer_formalization.py`: **8/8 frame-relevant** (`test_persona_frame_action_grammar_coherence`, `..._header_quotes_variant_f`, `..._no_banned_phrases`, `..._names_what_it_is` all PASS). 2 pre-existing failures untouched (`mandate_citation` + `judgment_prompts_bind_return_verdict` — fail on clean HEAD too; another lane's debt).
- `test_adr314_substrate_conditional_posture.py`: **6/6** (premise updated for ADR-383).
- `test_adr323_frame_collapse_finished.py`: **6/6**. `test_adr302_phase1_section_registry.py`: **10/10**.
- **Hat-B static**: the removed posture is fully present in both bundle `principles.md` (alpha-trader lines 7–30, tagged "migrated from frame 2026-05-29"); the frame pointer routes to it. **A program workspace's judgment is preserved by construction.** A live-wake Hat-B confirmation (a real trader/author wake reading judgment from the bundle, transcript-vs-receipt) is the deeper validation and is its own session (requires DB + LLM).

## 7. What this did NOT do

- No rung-branch / second frame / occupant fork.
- No envelope (`ReviewerContext`) change — the carried-not-exercised harness (ADR-381 D3) holds; the frame just stops asserting the judgment self-model over the steward.
- No bundle `principles.md` edit — they already carry the posture.
- No fix of the 2 pre-existing formalization-gate failures (another lane's debt — out of scope).
