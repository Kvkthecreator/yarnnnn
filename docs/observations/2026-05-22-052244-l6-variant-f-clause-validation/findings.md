# findings.md — L6 Variant F clause-level validation

**Spec**: FOUNDATIONS Derived Principle 21 (Variant F), canonized this morning in commit `b4e8a30`.

**Captured**: two substrate-event reactive wake cycles on yarnnn-author (canary v6 + canary v7).

**Verdict legend**:
- 🟢 **GREEN** — clause clearly satisfied with substantive evidence
- 🟡 **GREEN-with-caveat** — clause satisfied but with a stricter reading caveat worth naming
- 🟡-vacuous — clause satisfied vacuously (no action exercised this cycle); not a fail
- 🔴 **RED** — clause violated; Hat-A or Hat-B recommendation required

---

## Cycle traces

### Canary v6 (operator-fired, 2026-05-22T02:50:23Z)
- **wake_queue row**: `6fa5bd0b-a44e-4ec9-a22d-899d882ea1f0`, `wake_source=substrate_event`, `lane=live`, `slug=pre-ship-audit`
- **Status timeline**: pending @ 02:50:23.370 → locked @ 02:50:23.528 → completed @ 02:52:07.063 (104s run)
- **Reviewer substrate writes**: 3 to `/workspace/review/standing_intent.md`, all `authored_by="reviewer:ai:reviewer-sonnet-v8"`
- **Final standing_intent revision**: `52147775` ("Cycle update: piece 1 approved, test-cycle status transitions underway. Watching for publication resolution and piece 2-3 submission. No material action warranted until piece 2 submits or Mon May 27 publication deadline passes.")
- **execution_events row**: absent (pre-Phase-5 deploy-ordering anomaly, captured in canary v6 findings)
- **judgment_log.md write**: none

### Canary v7 (Claude Code-fired, 2026-05-22T05:10:36Z)
- **wake_queue row**: `d11c075c-b723-4cc4-895a-727d5afe585d`, `wake_source=substrate_event`, `lane=live`, `slug=pre-ship-audit`
- **Status timeline**: pending @ 05:10:36.364 → locked @ 05:10:36.635 → completed @ 05:11:42.320 (66s run)
- **Reviewer substrate writes**: 2 to `/workspace/review/standing_intent.md`, both `authored_by="reviewer:ai:reviewer-sonnet-v8"`
- **Final standing_intent revision**: `bfa6e75a` (2.5KB — see below for content snippets)
- **execution_events row**: `da595786-a11c-4e6a-8533-b842b7c66694` — `wake_source=substrate_event`, `funnel_decision=escalate`, `mode=judgment`, `status=success`, 64.7s, $0.2057, 33089 input / 4648 output tokens — **L8 telemetry pairing CONFIRMED post-Phase-5 (canary v6 anomaly resolved on the natural-next-wake basis the canary v6 findings predicted)**
- **judgment_log.md write**: none

---

## Per-clause verdicts (N=2)

### Clause 1 — Persona-bearing 🟢

**Required**: Reviewer's verdict references the persona from `/workspace/review/IDENTITY.md`, not generic "AI".

**Evidence (canary v6)**:
- Both standing_intent.md writes carry frontmatter `occupant: "ai:reviewer-sonnet-v8"` — runtime-truth-aligned per ADR-284
- Reasoning posture matches IDENTITY.md's editor-shaped persona: voice-first ("Specific anti-patterns tracked with heightened attention: list-of-three openers, hedge stacks, 'It's worth noting' constructions, adverb intensifiers…"), continuity-paranoid ("Continuity baseline confirmed: this is operator's native discipline"), anti-slop ("Hard-action-trigger threshold: if both pieces 2 and 3 show >2 instances of the same anti-pattern…")
- Reviewer cites the persona's own framework files: `_voice.md`, `_editorial.md`, principles.md

**Evidence (canary v7)**:
- Same frontmatter shape, same persona-shaped reasoning
- Adds calibration claim crossing cycles: "Standing intent correctly predicted the pause" — Reviewer treating its own prior standing_intent as authored substrate, not throwaway state

**Stricter reading caveat**: IDENTITY.md ships with a *default* editor-shaped persona (not a named character like "Robert Gottlieb" or operator-authored original). The operator has not overwritten IDENTITY.md to embody a specific named editor. So the persona is present-but-default. The clause is satisfied; if a stricter operator-named-editor test were intended, that's a follow-on observation.

**Verdict: 🟢 GREEN.**

---

### Clause 2 — Full substrate authoring 🟢

**Required**: at least one Reviewer WriteFile lands outside the lock set with `authored_by="reviewer:<occupant>"`.

**Evidence (canary v6)**: 3 writes to `/workspace/review/standing_intent.md`, all `authored_by="reviewer:ai:reviewer-sonnet-v8"`. Path is outside `DEFAULT_REVIEWER_WRITE_LOCKS` (which contains: AUTONOMY.md, _autonomy.yaml, _token_budget.yaml, _preferences.yaml, _pace.yaml).

**Evidence (canary v7)**: 2 writes to same path, same attribution shape, same lock-set compliance.

**Substantive content**: Final canary v7 write is 2.5KB of forward-looking judgment substrate — frontmatter (as_of, horizon, occupant) + three structured section headings (What I'm watching for / What would change my next move / Open questions for next operator interaction). Schema matches ADR-284 + persona-frame spec.

**No drift observed**: across N=2 cycles, the Reviewer wrote zero times to any lock-set path. The lock enforcement at `services/primitives/workspace.py::_is_path_locked_for_reviewer` is not exercised as a deny path during these cycles (because the Reviewer doesn't try to write there), but the substrate-authoring discipline holds.

**Verdict: 🟢 GREEN.**

---

### Clause 3 — Wake-fired 🟢

**Required**: cycle traces to one row in `wake_queue` with `status: pending → locked → completed`, no parallel direct-dispatch path observed.

**Evidence (canary v6)**: wake_queue row `6fa5bd0b` traces the full lifecycle, single-row, no parallel dispatch. Canary v6 findings document layer-by-layer L1→L8 (queue enqueue, drainer lock, dispatch, substrate writes, completion, cross-tick dedup).

**Evidence (canary v7)**: wake_queue row `d11c075c` traces same shape; `execution_events` row `da595786` pairs cleanly (`funnel_decision=escalate`, `mode=judgment`, `trigger_type=reactive`) — confirms ADR-296 v2 D1 singular invocation gateway + ADR-298 D2 single-lane queue serialization.

**No `FireInvocation` in Reviewer surface**: per ADR-296 v2 D3, the Reviewer cannot self-invoke. REVIEWER_PRIMITIVES contains no FireInvocation (verified by `api/test_reviewer_formalization.py::test_reviewer_primitives_contract`, 8/8 PASS this morning). Neither canary cycle produced a self-invocation attempt.

**Verdict: 🟢 GREEN.**

---

### Clause 4 — Self-pacing 🟡-vacuous-on-author / 🟢-on-honor

**Required**: Reviewer either uses Schedule/ManageHook to shape future wakes (if cycle warrants), OR honors existing `_preferences.yaml`.

**Author-side evidence (both canaries)**: **No `Schedule` or `ManageHook` calls fired across either cycle**. Verified by querying `workspace_file_versions` for revisions on `/workspace/_recurrences.yaml` and `/workspace/_hooks.yaml` in both windows — zero rows.

**Honor-side evidence (canary v6)**: standing_intent.md explicitly tracks existing scheduled fires:
> "**Weekly-corpus-review**: fires Sunday May 26 at 18:00 UTC (94 hours from now). If piece 1 is published by then, I'll synthesize week 1 voice + continuity findings into `_signal.md` rolling windows per spec."
> "**Corpus-coherence-check**: fires Monday May 27 at 12:00 UTC."

**Honor-side evidence (canary v7)**: same shape — Reviewer reasons against the next scheduled `weekly-corpus-review` fire, treats it as a constraint on what to defer to that fire vs handle now.

**Why no Schedule call**: the Reviewer's judgment was that no cadence change was warranted. The standing_intent's "What would change my next move" section enumerates conditions (piece 1 publication, drift pattern emergence, new entity introduction, operator updates to canon) that would warrant a future re-cadence — but none triggered this cycle. This is **correct restraint**, not failure.

**Stricter reading**: a clause that requires the Reviewer to "use Schedule/ManageHook" is vacuously satisfied here; only the "honors existing _preferences.yaml" branch is exercised. To get an active-author-branch observation, we'd need a cycle where the operator changes `_preferences.yaml` or where the Reviewer's standing intent shifts enough to warrant a cadence change. **Recommended follow-on**: a future observation that captures an active Schedule call (e.g., operator adds a new preference to `_preferences.yaml`, observe Reviewer's reconciliation cycle author the Schedule).

**Verdict: 🟡 GREEN-on-honor, vacuous-on-author. Not a fail; the author branch is correctly absent because no cadence change warranted.**

---

### Clause 5 — Operator-set ceilings respected 🟡-vacuous-on-gate-fire / 🟢-on-read-and-reason

**Required**: `should_auto_apply` consults `_autonomy.yaml::delegation` + `ceiling_cents`; if consequential action attempted, gating logic visible in `execution_events`.

**Read-and-reason evidence (canary v6)**: standing_intent.md explicitly cites:
> "**Autonomous delegation posture confirmed**
> - _autonomy.yaml shows `delegation: autonomous`.
> - Approve verdicts bind publication immediately; no Queue click required."

Reviewer correctly read `_autonomy.yaml` (which it cannot write per DEFAULT_REVIEWER_WRITE_LOCKS) and reasoned about its delegation posture.

**Read-and-reason evidence (canary v7)**: same shape, restated:
> "`_autonomy.yaml::delegation = autonomous`; no category ceilings (all piece_types auto-ship on my approve). My approve binds publication immediately under this config."

**Gate-fire evidence**: **None** — neither cycle attempted a consequential action (no `ProposeAction`, no `ExecuteProposal`). The standing_intent reflects a deliberate forward-watching posture rather than capital-shaped writes. So `should_auto_apply` was not exercised this cycle. The clause's conditional ("if consequential action attempted, gating logic visible") is vacuously satisfied.

**Stricter reading**: clause 5's harder validation is the consequential-action branch. The canary v5/v6 findings note this is exercised in alpha-trader's `signal-evaluation` cycle (which fires `ProposeAction` inline). Alpha-author has no `ProposeAction`-shaped recurrences today — the bundle's publication-mediated authority lands through approve/reject verdicts on `pre-ship-audit` hook (canary v6's piece 1 approval was binding under autonomous delegation, but that approval landed in a previous cycle outside this observation window). **Recommended follow-on**: an L6 closure observation on alpha-trader during market hours, where `signal-evaluation` fires + emits `ProposeAction` + the `should_auto_apply` gate exercises against the `ceiling_cents` ceiling on a real proposal.

**Verdict: 🟡 GREEN-on-read-and-reason, vacuous-on-gate-fire. The clause's conditional triggers only when consequential action is attempted; alpha-author substrate-event cycles don't typically attempt them.**

---

### Clause 6 — Mandate-driven 🟡-amber-with-strict-reading / 🟢-with-structural-reading

**Required**: Reviewer's reasoning surfaces in `/workspace/review/judgment_log.md` and references MANDATE.md content (not generic reasoning).

**Strict reading**: **Neither canary cycle produced a `judgment_log.md` write**. The material-outcome gate (`render_lineage_entry_if_material` per ADR-281 §5.D3) did not fire — both cycles ended in stand-down posture without a material-outcome event. So the judgment_log.md surface is not exercised, only standing_intent.md.

**Substantive reading**: **Reviewer's reasoning in standing_intent.md structurally tracks MANDATE.md success criteria**:
- MANDATE.md: *"Voice fingerprint stable across rolling 30 days"* → Reviewer: *"Baseline floor from piece 1: Zero anti-AI-slop instances across 1,200+ words"* + tracks specific anti-patterns
- MANDATE.md: *"Continuity preserved across the corpus — no unacknowledged contradiction"* → Reviewer: *"Continuity baseline confirmed: this is operator's native discipline"* + tracks bridge-discipline
- MANDATE.md: *"Anti-AI-slop signatures absent from shipped pieces"* → Reviewer: *"Hard-action-trigger threshold: if both pieces 2 and 3 show >2 instances of the same anti-pattern, Clarify"*
- MANDATE.md: *"Cadence honored"* → Reviewer's tracking of weekly-corpus-review fire timing + missed-interval thresholds

**But** the string `MANDATE.md` does not appear in either standing_intent.md. The mandate is invoked through the IDENTITY.md → principles.md framework chain (which IS authored to instantiate the mandate), not via direct citation.

**Stricter reading argument**: a strict reading would call this 🔴 RED — the clause says "references MANDATE.md content (not generic reasoning)" and there's no direct reference. Counter: the IDENTITY.md "What I optimize for" section explicitly cites *"operator's chosen success bar per MANDATE.md"* — the reference exists in the persona-frame chain that the Reviewer embodies. The structural inheritance is load-bearing.

**Mitigation observation**: standing_intent.md in canary v7 ends with an `**Evidence basis**` block citing the substrate it reasoned from. That block does NOT include MANDATE.md in the citation list — it cites `governance-as-trust profile.md`, `_autonomy.yaml`, `GetSystemState`, prior standing_intent. **A small Hat-A nudge in the persona frame or the hook prompt could make MANDATE.md citation explicit in evidence-basis blocks**, closing the strict-reading gap.

**Verdict: 🟡 GREEN with caveat — structural mandate-derivation visible through IDENTITY.md framework chain; explicit MANDATE.md citation absent. Hat-A recommendation below.**

---

## Summary scorecard

| Clause | Canary v6 | Canary v7 | Combined |
|---|---|---|---|
| 1. Persona-bearing | 🟢 | 🟢 | 🟢 |
| 2. Full substrate authoring | 🟢 | 🟢 | 🟢 |
| 3. Wake-fired | 🟢 | 🟢 | 🟢 |
| 4. Self-pacing | 🟡-on-honor (vacuous-on-author) | 🟡-on-honor (vacuous-on-author) | 🟡-on-honor |
| 5. Operator-set ceilings | 🟡-on-read (vacuous-on-gate-fire) | 🟡-on-read (vacuous-on-gate-fire) | 🟡-on-read |
| 6. Mandate-driven | 🟡 GREEN-with-caveat (structural-yes, explicit-no) | 🟡 GREEN-with-caveat (structural-yes, explicit-no) | 🟡 GREEN-with-caveat |

**N=2 reproducibility**: identical clause-by-clause results across both cycles. No flake; the Reviewer's behavior is stable.

**Headline**: **No clauses are RED on either canary cycle.** Three clauses (1, 2, 3) are unambiguously GREEN. Three clauses (4, 5, 6) are GREEN with structurally-named caveats — none of which are bugs, all of which are *follow-on observations to fill out the validation envelope on the active-branch of each clause*.

---

## What this validates about Variant F

The architectural one-liner (FOUNDATIONS DP21) is an **honest description** of what shipped — to within the scope a single substrate-event cycle exercises. The clauses that need follow-on observations to be exercised on their active branches (Schedule-authoring path; consequential-action gate-fire path; explicit-MANDATE-citation path) are not bugs; they're branches that didn't trigger in alpha-author substrate-event cycles.

The wake-architecture commitments (clause 3: wake-fired + single-lane queue) and substrate-discipline commitments (clause 2: lock-gated full authoring; clause 1: persona-bearing through IDENTITY) are unambiguously evidenced.

**Variant F is validated** as an honest description; the residual amber-on-some-branches doesn't change that — it just signals the natural complementary observations to fill out the full validation envelope.

---

## Hat-A recommendations (queued, not in scope for this observation)

### Recommendation 1 — Align stale spec files to Variant F (high-leverage)
`docs/alpha/ALPHA-1-PLAYBOOK.md §0` and `docs/alpha/E2E-EXECUTION-CONTRACT.md §0` carry the older, longer one-liner — not Variant F. The two sentences differ in three substantive places (named in [`PLAYBOOK.md`](PLAYBOOK.md)). A Hat-A pass updating both to quote Variant F + cite FOUNDATIONS DP21 would close the spec-drift gap surfaced before this observation. **Scope**: 2 file edits, ~50 LOC. **Risk**: low; both files are operator-facing docs, no code-path coupling.

### Recommendation 2 — Persona-frame nudge for explicit MANDATE.md citation in standing_intent.md (medium-leverage)
The Reviewer's `**Evidence basis**` block in standing_intent.md cites the substrate it reasoned from but never names MANDATE.md (canary v7 final write is the worked example). A small addition to the persona-frame "Standing intent has a substrate home" section or to the alpha-author `pre-ship-audit` hook prompt could prompt the Reviewer to cite MANDATE.md when it's load-bearing in the reasoning. **Closes clause 6's strict-reading caveat**. **Scope**: ~2 sentences in persona frame or one in the hook prompt. **Risk**: low — additive prose; would need CHANGELOG entry per Prompt Change Protocol.

### Recommendation 3 (deferred) — Active-branch observation for clauses 4 + 5
- For clause 4 (Schedule-authoring): observe a cycle where the operator updates `_preferences.yaml` and the Reviewer reconciles via a Schedule call. Or wait for the next natural occurrence in the alpha-author workflow.
- For clause 5 (gate-fire on consequential action): the natural site is alpha-trader during market hours. The alpha-trader `signal-evaluation` recurrence at 09:45 ET fires `ProposeAction` inline when conditions warrant; `should_auto_apply` exercises against `_autonomy.yaml::ceiling_cents`. **Recommended**: capture the next natural signal-fire (no synthetic harness needed).

---

## Cross-references

- Variant F canon source: FOUNDATIONS Derived Principle 21 (commit `b4e8a30`, this morning's Hat-A sweep — landed via the swept-up commit per [`2026-05-22-043009-reviewer-formalization-audit/RESOLUTION.md`](../2026-05-22-043009-reviewer-formalization-audit/RESOLUTION.md))
- Variant F GLOSSARY entry: `docs/architecture/GLOSSARY.md` line 179
- Variant F persona-frame preamble: `api/agents/reviewer_agent.py::_PERSONA_FRAME`
- Regression gate enforcing Variant F invariants: `api/test_reviewer_formalization.py` (8/8 PASS)
- Canary v6 layer-integrity validation: [`2026-05-22-024952-canary-v6-l6-validation/findings.md`](../2026-05-22-024952-canary-v6-l6-validation/findings.md)
- Canary v5 structural validation: [`2026-05-22-020000-canary-v5-adr298-cutover/findings.md`](../2026-05-22-020000-canary-v5-adr298-cutover/findings.md)
- Canary harness: `api/scripts/operator/canary_v4_substrate_event.py` (reused for v5, v6, v7)
- Reviewer cycle artifacts:
  - Canary v6 wake_queue row: `6fa5bd0b-a44e-4ec9-a22d-899d882ea1f0`
  - Canary v6 standing_intent.md revisions: `03ebe5da` / `05ea99cf` / `52147775`
  - Canary v7 wake_queue row: `d11c075c-b723-4cc4-895a-727d5afe585d`
  - Canary v7 execution_events row: `da595786-a11c-4e6a-8533-b842b7c66694` (L8 telemetry confirmed post-Phase-5)
  - Canary v7 standing_intent.md revisions: `3e366bb4` / `bfa6e75a`
- Spec divergence finding (PLAYBOOK §0 vs Variant F): [`PLAYBOOK.md`](PLAYBOOK.md) §"Spec divergence flagged before observation"

## Status

**L6 closure observation: COMPLETE.** Variant F validated end-to-end across N=2 substrate-event reactive wake cycles on yarnnn-author. No RED clauses. Three GREEN clauses, three GREEN-with-caveat clauses (caveats are structural-not-bug, naming the natural follow-on observations to fill out the full validation envelope).

The line has moved from "architecture-claim" to **"validated on the substrate-continuity branch, with active-branch follow-on observations queued for clauses 4 and 5."**
