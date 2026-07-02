# Freddie envelope refactor — Rung-3 measurement (lazy CC-shape envelope, Arm B)

**Date**: 2026-07-02 · **Hat**: B
**Plan**: [freddie-envelope-refactor-plan-2026-07-02.md](../../analysis/freddie-envelope-refactor-plan-2026-07-02.md), Rung 3 · **Scaffolding**: the envelope-collapse Arm B (`YARNNN_ENVELOPE_ARM=B` → `_build_user_message_stripped`: governance block + substrate snapshot [heads, not bodies] + bare ask; NO trigger framing, NO fact sections, NO mirror dumps)
**Model**: Haiku 4.5 throughout — deliberately (the model-agnostic validation rule: if posture holds on the weak model, it holds anywhere).

## Runs

1. **Addressed v1** (`../2026-07-02-freddie-envelope-rung3-armB/`): 4/6 closed — asks 2+5 did their work then **silently exited without ReturnVerdict**.
2. **Root cause + fix**: Arm B strips `_TRIGGER_FRAMING`; post-ADR-397 the close instruction lived ONLY there. The close **contract** is agent↔runtime interface (DP22) and was misplaced in strippable coaching. Moved to `_compute_minimal_frame` (one paragraph); the addressed framing's duplicate line removed; gate `test_close_contract_lives_in_the_frame` added.
3. **Addressed v2** (this folder): **6/6 closed, 0 errors** — wall 24.9s · rounds 4.0 · tools 7.2 · chars 448 ≈ **parity with the full production envelope** (rung2: 22.4 / 4.3 / 7.2 / 491).
4. **Reactive** (bare-steward `--live` under Arm B): ledger `status=success`, 9 rounds; stewardship **more thorough than the production-arm baseline** — touched BOTH seeded conditions (dump + mis-attribution; baseline touched only the dump), 3 gated proposals. Heuristic HALF-2 "capital terms" flags are false positives on human read ("competitive *positioning*", "alpha-*trader*" named while correctly describing steward-vs-operation).

## Corrections to earlier findings

- **The reactive "closed WITHOUT ReturnVerdict" baseline finding was a probe artifact.** `execution_events` shows both bare-steward wakes (baseline arm + Arm B) recorded `success` — the probe's parsing of `_invoke_recurrence_wake` output is stale (same class as its deleted `mode=` field). The ADR-360 fault shape did NOT occur.
- **The "paying twice" (re-read) argument was reactive/kvk-specific**: rung-2 addressed transcripts show 0 re-reads of pre-loaded paths on the bare workspace. Arm B's addressed-path case rests on dilution + the uncached volatile suffix, not re-reads.

## Verdict

**The lazy envelope is VIABLE on the weak model — behavior parity on addressed, improvement on reactive.** The plan's fear (Haiku can't do directed retrieval) is empirically dead: reads were fewer and well-targeted in every run. The one regression the experiment produced (silent exits) was root-caused to a misplaced interface contract and fixed at the frame — a durable win independent of the arm decision.

**Landing checklist before Arm B becomes production** (next session unit):
1. Cache-mark the stripped shape (Arm B is a plain string; production needs the governance-prefix `cache_control` blocks the Arm-A path already has — without it every wake pays full input rate on ~16k governance tokens).
2. One trader-workspace **proposal wake** under Arm B (capital judgment is the one trigger shape not yet measured lazily).
3. Fold the pending-proposals inventory line into the substrate snapshot (the rung-2 residual: turns re-derive placements whose proposals sit unapproved).
4. Flip the arm + DELETE the toggle and the Arm-A partition path (singular implementation — the code comments already anticipate "removed once the collapse lands").
