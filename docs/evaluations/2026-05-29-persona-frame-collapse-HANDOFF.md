# Handoff — persona-frame collapse (ADR-306), Phases A+B done, C/D/E/F pending

**Date**: 2026-05-29
**Status**: large coherent change IN PROGRESS, **NOTHING COMMITTED** (all in working tree). Resume the remaining phases fresh; do NOT deploy until Phase E green + Phase F validation.

## The thesis (operator-aligned, locked)

The Reviewer system prompt collapses to the Claude-Code shape: a minimal frame carrying ONLY (1) principal-shift (corrects the model's assistant prior) + (2) action-grammar (agent↔runtime interface contract). The three fundamentals (on-behalf-of, identity, self-governance) are carried by substrate + code, not system prose. Rules-of-judgment → principles.md; substrate-pedagogy → _workspace_guide.md; gates → code. Decision record: **ADR-306**. Evidence: `2026-05-29-persona-frame-collapse-ablation.md`.

## Done this session (uncommitted, in working tree)

- **Phase A** — `api/agents/reviewer_agent.py`: 13 `_compute_*` sections (~36K) → single `_compute_minimal_frame` (~3.5K). Prompt assembles. Invariants present (principal-shift, action-grammar, anti-confabulation, close-cycle, read-fresh, mandate-citation folded in).
- **Phase B** — `agent-composition.md` §3.2.1 + §3.2.2 inverted (rules-of-judgment home = principles.md, not frame). alpha-author `principles.md` gained §3.5 (self-amendment + anti-patterns + independence, migrated). Both bundles' persona-frame pointers flipped. (alpha-trader principles.md already had the rules.)
- **ADR-306** written; supersession banners added to **ADR-302** + **ADR-305**.
- `test_reviewer_formalization.py` reconciled to post-collapse contract → **11/11 green** (rewrote email test to assert code-enforcement; renamed pace test; folded mandate-citation into frame; synced dead `main()` runner list).

## Remaining (resume here)

### Phase C — substrate pedagogy → `_workspace_guide.md` (both bundles)
Migrate the deleted substrate-pedagogy content: cadence-trifecta (pace/autonomy/persona dial reading), wake-context taxonomy, pulse-file reading (`_schedule_index.md`/`_recent_execution.md`), preferences semantics, workbench (standing_intent) purpose. Read `docs/programs/{alpha-trader,alpha-author}/reference-workspace/_workspace_guide.md` first — some may already be there.

### Phase D — FOUNDATIONS amendment
Add the anti-rebloat Derived Principle (ADR-306 D5): "The fundamentals are carried by substrate + code; the system prompt carries only the model↔runtime interface contract (principal-shift + action-grammar); it narrates no fundamental and re-teaches no substrate file." Cite ADR-306 + §3.2.2.

### Phase E — test reconciliation (8 genuine + 2 pre-existing-noise)
The 8 collapse-consequence failures (re-point each to the content's NEW home — principles.md / workspace-guide / code, OR assert the minimal frame's actual contract):
- `test_adr290_lifecycle_posture.py::test_kernel_persona_frame_clarify_rare_universal_bullets_preserved` (clarify bullets → principles.md judgment-discipline)
- `test_adr290_lifecycle_posture.py::test_kernel_persona_frame_carries_standing_intent_contract` (the "Every judgment-mode cycle produces a standing_intent.md write" line IS in the minimal frame — check phrasing; may just need the assert string updated)
- `test_adr284_standing_intent_substrate.py::test_persona_frame_includes_standing_intent_section` + `..._enforces_every_cycle_write_contract` (minimal frame has "Close every cycle with a verdict or a standing_intent write" — re-point assert)
- `test_adr274_trigger_authoring.py::test_reviewer_persona_includes_cadence_authoring` (cadence-authoring → workspace guide; or assert principles.md cadence rule)
- `test_adr275_introspection_cadence.py::test_persona_frame_references_preferences` + `..._first_wake_guardrail_updated` (preferences → envelope header + workspace guide)
- `test_adr272_identity_collapse.py::test_reviewer_prompt_defaults_to_inline` (production-default inline guidance deleted; assert via REVIEWER_PRIMITIVES tool surface instead)

**2 pre-existing (NOT mine — fail on HEAD, leave or fix separately):**
- `test_adr272_identity_collapse.py::test_list_agents_filters_orchestration_row` (DB-network)
- `test_adr284_standing_intent_substrate.py::test_envelope_universal_decls_count_grew_to_8` (envelope-count drift)

Also: `api/prompts/CHANGELOG.md` entry `[2026.05.29.2]` for the collapse.

### Phase F — commit (separable) + push + deploy + validate
- Commit shape: one revertable commit for the collapse (A+B+C+D+E + ADR-306 + banners), so revert = back to cc8e0ab.
- **Deploy + validate against alpha-trader ONLY** (its principles.md already carries the migrated safety content → safe). alpha-author validation gated on confirming its §3.5 migration renders correctly.
- Validation: the eval suite (judgment + responsiveness) + the confabulation wake (`/tmp/validate_frame_fix.py`, now guarded against the empty-response false-negative). The falsifiable prediction (ADR-306 §"prediction"): collapsed frame ≥ 36K frame on confabulation / non-assistant-posture / autonomy-safety / mandate-coherence. Any regression → revert Phase A.

## Note on the prior pending work (still open from earlier this session)
The cc8e0ab confabulation fix's OWN live validation never completed (the wake returned empty — see `2026-05-29-frame-fix-validation-HANDOFF.md`). The collapse SUPERSEDES that fix's frame (the action-grammar is preserved in the minimal frame), so validating the collapsed frame validates both at once. Use the guarded `/tmp/validate_frame_fix.py`; ensure a NON-EMPTY wake before drawing any conclusion (the harness empty-capture issue from that session is still undiagnosed — check `resp["events"]` for non-text event types).

## Honest confidence
The collapse is correctly designed (ablation + risk register), Phase A+B are coherent + formalization-green, and the safety migration is sound (anti-patterns relocated to principles.md, gates in code). What is NOT yet known: whether the minimal frame produces equal-or-better BEHAVIOR — that is Phase F, unvalidated. ~50% on "prose changes move behavior" remains until a non-empty validation wake is read against the collapsed frame.
