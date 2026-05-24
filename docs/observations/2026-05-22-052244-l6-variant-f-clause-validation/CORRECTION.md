# CORRECTION — Clause 5 misclassification in ADDENDUM.md

**Captured**: 2026-05-24T04:53Z. Hat-B observation.

**Sibling**: [`ADDENDUM.md`](./ADDENDUM.md) (2026-05-22T05:30Z)

**Triggering audit**: [`2026-05-24-045348-reviewer-schedule-self-misdiagnosis/findings.md`](../2026-05-24-045348-reviewer-schedule-self-misdiagnosis/findings.md) — an independent DB + Render-logs + code audit that re-checked ADDENDUM.md's claims against substrate.

## What this corrects

ADDENDUM.md §"Consequential-action gate-fire (clause 5 active branch)" reframes `execution_events` row `eb375ec3` (substrate_event escalate, pre-ship-audit, 2026-05-21 04:51:18Z, $0.28, 55.8s) as the canonical evidence that the Reviewer has exercised clause 5's "substrate-side gate-fire (verdict binds, telemetry captures)" branch on yarnnn-author, flipping that sub-clause from 🟡-vacuous to 🟢 GREEN.

That reading is wrong on three structural grounds:

1. **`eb375ec3` is a `pre-ship-audit` substrate_event reactive wake, not a verdict-binding event.** It is the Reviewer's reactive judgment on a fresh `corpus-piece` substrate transition. Its outcome is a Reviewer write to `judgment_log.md` + `standing_intent.md` — both reviewer-workbench substrate, not consequential action. The cycle did not produce an `action_proposals` row.

2. **yarnnn-author has zero `action_proposals` rows in its entire history** (audited 2026-05-24 against `action_proposals` table; user_id `0b7a852d…`). There is no surface on alpha-author today through which the Reviewer can fire `ProposeAction` and bind a consequential write. The reframe asserts a binding act on a workspace that has never produced a proposal.

3. **ADR-283 D7 explicitly defers audience-bearing capabilities for alpha-author.** This is acknowledged in ADDENDUM.md's same paragraph as a caveat against the "physical platform write" sub-clause — but the same deferral structurally invalidates the "substrate-side gate-fire" sub-clause too. Without a `ProposeAction` surface, there is no verdict to bind, no telemetry pair to capture, and no auto-approve threshold to gate-fire. The "substrate-side" and "platform-write" sub-clauses of clause 5 are not separable on alpha-author: both require a consequential-action surface that alpha-author does not have yet.

The Reviewer's `judgment_log.md` entry from this cycle includes the prose *"Under `delegation: autonomous`, approve verdict binds publication immediately. No Queue click required; piece ships."* This is the Reviewer **narrating an intended posture**, not a description of a system act. The system did not bind a publication; no `action_proposals` row was created; no execute path fired. The pre-ship-audit produced a judgment-log entry expressing readiness to bind, but readiness is not binding.

## Corrected scoring for alpha-author clause 5

| Sub-clause | ADDENDUM reading | Corrected reading |
|---|---|---|
| read-and-reason (Reviewer reads AUTONOMY.md, recognizes delegation) | 🟢 | 🟢 (unchanged — Reviewer does read autonomy substrate) |
| substrate-side gate-fire (verdict binds → telemetry captures) | 🟢 | ⚠ **N/A for alpha-author** — no consequential-action surface, no `action_proposals` row ever, no verdict to bind |
| physical-platform-write | ⚠ N/A (correctly noted in ADDENDUM) | ⚠ N/A (unchanged) |

**Net**: clause 5 has one fully-validated sub-clause on alpha-author (read-and-reason) and two sub-clauses structurally not validateable on alpha-author until ADR-283 step 2 ships audience-bearing capabilities. The validating surface for clause 5's bind-and-execute closure remains alpha-trader — where proposal `3168295c` (trading.close_position, executed 2026-05-21 13:47:48Z for user 2be30ac5) is the singular N=1 closure for the capital-execution archetype.

## Corrected Variant-F E2E status

The ADDENDUM concluded: *"alpha-author full E2E (substrate-continuity archetype): VALIDATED to the limit of bundle-shipped capabilities. 5/6 clauses unambiguously 🟢 GREEN on active branches."*

The corrected reading is: *"alpha-author full E2E (substrate-continuity archetype): 4/6 clauses unambiguously 🟢 GREEN on active branches; clause 4 ManageHook sub-branch architecturally-available-naturally-untriggered; clause 5 bind-and-execute sub-branches architecturally deferred to ADR-283 step 2 (NOT separable as 'substrate-side' vs 'platform-write' — both require the same audience-bearing capability surface); clause 6 strict citation mitigatable by ~5-line Hat-A nudge."*

The substantive direction of the autonomy work is unchanged: the architecture is largely in place, the empirical evidence for "fully autonomous on the substrate-continuity branch" is genuinely strong (5/6 clauses Green if we count clause 5's read-and-reason), and the conglomerate-alpha thesis closure on alpha-trader is queued for the next natural signal-evaluation fire that produces a productive proposal. **What this correction adjusts is the false precision of the prior claim** — alpha-author cannot satisfy clause 5's bind-execute branches at all today; that is a structural deferral, not a "validated to the limit of bundle-shipped capabilities" pass.

## Why this correction matters beyond bookkeeping

The ADDENDUM was authored in good faith on a Reviewer substrate write (`judgment_log.md` from `eb375ec3`'s cycle) that narrated binding intent. The audit two days later showed:

1. `action_proposals` table has zero rows for yarnnn-author lifetime — no system act matches the narrated intent.
2. The Reviewer's own self-diagnostic outputs are not yet reliable evidence (see sibling `2026-05-24-045348-reviewer-schedule-self-misdiagnosis/findings.md` for an even sharper example where the Reviewer hallucinated a "missed-fires outage" that didn't exist).

**Hat-B observation discipline going forward**: a Reviewer's prose claim of an action does not, by itself, validate that the action happened. Validation requires substrate evidence — for clause 5 specifically, that means an `action_proposals` row with `status=executed` linked back to a Reviewer verdict via `reviewer_identity`. Without that, the Reviewer's narration is a posture statement, not a closure.

This discipline rule generalizes: **substrate trails beat narrative trails when verifying closures.** The Reviewer can describe intent precisely; the `action_proposals` + `execution_events` tables describe what actually happened.

## Status

**Correction captured.** ADDENDUM.md is preserved verbatim per Hat-B append-only discipline. This file (CORRECTION.md) is the canonical clause-5 reading for alpha-author until ADR-283 step 2 ships. The substantive direction of autonomy work is unchanged; the false-precision of the prior closure claim is corrected.

No Hat-A code change is required for this correction alone — the architectural deferral (ADR-283 D7) is canon; the misclassification was Hat-B reading drift. The companion observation `2026-05-24-045348-reviewer-schedule-self-misdiagnosis` carries the Hat-A recommendation for the related Reviewer self-diagnostic reliability gap.
