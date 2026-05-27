# Alpha-Trader Playbook Audit — Noise-vs-Signal Candidates Pre-Mandate-Coherence Measurement

**Captured**: 2026-05-27. Hat-B analysis memo.

**Companion to**: [`docs/evaluations/2026-05-27-000919-mandate-coherence-criterion/findings.md`](../evaluations/2026-05-27-000919-mandate-coherence-criterion/) — declares the mandate-coherence criterion this audit's recommendations will be measured against.

**Workspace-carve dependency**: depends on the 2026-05-27 workspace carve session, which left two active workspaces (`kvkthecreator@gmail.com` alpha-trader with 3 active judgment recurrences; `yarnnn-author@yarnnn.com` alpha-author with 5 active judgment recurrences). The carve isolated single-variable-per-program testing; this audit examines the alpha-trader leg's playbook for noise-vs-signal candidates that may inflate the M6-DRIFT class (visibility-compliant but mandate-blind substrate writes).

## Frame

The autonomy mechanism is structurally complete post-ADR-303 (visibility-compliance contracts wired for all five posture cells). The operator's thesis — substantiated by the post-deploy 13:01 UTC `29a74c63` wake whose `standing_intent.md` said *"scheduler silence detected... awaiting operator clarification"* without referencing MANDATE — is that the **content** of substrate writes isn't yet mandate-coherent. The visibility pipeline works; the substrate it carries is partially mandate-blind.

This memo treats the playbook (persona-frame + bundle's `_recurrences.yaml` + bundle's `principles.md` + per-recurrence prompts + specs) as the system surface that produces the substrate. Where the playbook elicits mandate-coherent reasoning, the output is M1/M7 (ideal cells). Where the playbook elicits structurally-shaped-but-mandate-orthogonal reasoning, the output drifts to M3/M5/M6.

The audit identifies **eight noise-vs-signal candidates** — playbook features that may be producing M6-DRIFT output **by design** rather than by accident. Each candidate names: (a) what it currently produces, (b) the M-cell drift risk, (c) the recommended Hat-A change (if any), (d) the measurement gate that would justify the change.

**Discipline**: this is a Hat-B memo. It recommends Hat-A changes; it does not make them. Each recommendation requires either operator sign-off or a measurement-justified trigger (first mandate-coherence measurement showing the predicted drift class is real). No persona-frame or bundle edits are landed by this memo.

---

## Candidate 1 — Persona-frame's "almost always an action" framing produces M3/M6 risk on judgment-mode mechanical-state wakes

**Surface**: `api/agents/reviewer_agent.py` `_compute_persona_frame` body, lines 355-366:

> The answer is almost always an action — fire a recurrence to refresh data, submit a proposal because conditions are met, write a note to your own substrate to track a pattern, schedule a follow-up cycle. The answer is NEVER "ask the operator what to do."
>
> Standing down is structurally rare. It is the verdict only when no available action moves the operation forward.

**What it produces**: a strong action-bias prior. Every wake → the Reviewer is primed to produce SOMETHING — fire, propose, write, or schedule.

**M-cell drift risk**: M3 (substrate-write claims advance but doesn't ground in mandate) and M5 (substrate-chain reasoning without explicit mandate cite). When the Reviewer is told "almost always an action" without paired emphasis on "and that action's grounding traces to MANDATE," it produces writes that look forward-looking but are framework-internal — e.g., a `standing_intent.md` entry like *"Watching for next track-universe mirror fire to refresh tickers"* satisfies "an action" (scheduled cycle) but says nothing about the trading mandate the cycle exists to advance.

**Recommended Hat-A change**: add a one-paragraph clause to `_compute_persona_frame` that pairs the action-bias with explicit mandate-grounding requirement. Suggested wording:

> Every action's grounding should trace to a MANDATE clause. "Fire a refresh" because data is stale → name WHY stale data blocks the mandate's Primary Action. "Submit a proposal" because conditions are met → name which signal in `_operator_profile.md` (derived from MANDATE's Rules of Operation) is firing. "Write a note" → name which mandate-success-criterion the note's pattern would advance or threaten. Action without mandate-grounding produces visibility-compliant substrate that operators cannot audit for direction.

**Measurement gate**: first mandate-coherence measurement (post ~2026-06-03) showing M3 + M6 combined > 15% of P1+P2 wakes. If M6 specifically > 5% of P1+P2 wakes, the action-bias-without-grounding hypothesis is supported and the persona-frame amendment lands.

**Risk of premature change**: if measurement shows M1+M7 already > 65% with M6 < 5%, the persona-frame as-stated is producing the predicted distribution and amendment adds noise. Wait for measurement.

---

## Candidate 2 — `signal-evaluation` prompt is rich in mandate-grounding; `outcome-reconciliation` prompt is mandate-bare

**Surface**: `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml` lines 146-223 (signal-evaluation) vs lines 281-308 (outcome-reconciliation).

**signal-evaluation prompt** explicitly references: operator-profile signal definitions, `_regime.yaml` portfolio scalar (mandate Boundary Condition #2 — var budget), principles.md hard exit triggers (mandate Position Lifecycle exit-phase rule), per-signal sizing math. Every step is grounded in declared rules. **Predicted to produce high M1-IDEAL fraction.**

**outcome-reconciliation prompt** is purely process-narrative: pulls fills, recovers attribution, folds outcomes, regenerates summary, writes standing_intent + ReturnVerdict. **The prompt instructs the substrate WRITE but doesn't instruct mandate-grounded REASONING about what the reconciliation tells the operator.** Predicted to produce M5 or M6 output — substrate-cited (`_money_truth.md`) but mandate-orthogonal in the standing-intent text.

**M-cell drift risk**: M5 inflation specifically on `outcome-reconciliation` wakes. The Reviewer mechanically folds outcomes and writes the prescribed substrate, but the standing-intent text is likely to be "watching for next reconciliation window" rather than "rolling 90-day expectancy now +0.32R, holds above the +0.0R growth floor declared in MANDATE Success Criteria #1; my next watch is for the IH-3 cluster's expectancy stability to mature past 20 samples."

**Recommended Hat-A change**: extend `outcome-reconciliation` prompt with a mandate-grounding cycle-close section. Suggested addition after "Close the cycle":

> Before writing standing_intent, read MANDATE.md Success Criteria. The reconciliation's job is not just to fold fills — it is to surface, in standing_intent.md, what the new reconciled data tells the operator about mandate satisfaction. Frame: which success criterion is currently above/below threshold, which signals are advancing/decaying against the declared edge hypothesis, what mandate-clause-bounded watch the next cycle inherits.

**Measurement gate**: per-slug mandate-coherence breakdown showing `outcome-reconciliation` wakes M5+M6 > 50% while `signal-evaluation` wakes M1+M7 > 60%. If both slugs distribute similarly, the prompt difference isn't the operative variable.

**Companion observation**: `outcome-reconciliation` is also the top spend line MTD ($8.69, 33 wakes). If a per-recurrence prompt enrichment can move this slug from M5/M6 toward M1/M7, it's the highest-leverage single-prompt change in the playbook.

---

## Candidate 3 — `pre-market-brief` removed from `_recurrences.yaml` per ADR-275; cadence is now Reviewer-authored, but the spec still exists

**Surface**: `_recurrences.yaml` lines 254-263 explicitly DELETE pre-market-brief from bundle scaffolding ("Reviewer-authored cadence per FOUNDATIONS v8.5 Axiom 4"). But the spec at `docs/programs/alpha-trader/reference-workspace/specs/pre-market-brief.md` is still detailed (60 lines, 5 required sections, quality criteria).

**What this means structurally**: per ADR-275, the Reviewer should read `_preferences.yaml`, observe the operator wants a pre-market-brief deliverable cadence, and author a `Schedule(action="create", slug="pre-market-brief", ...)` call. The spec is the contract for what to produce; the cadence is the Reviewer's call.

**Current substrate state**: kvkthecreator workspace has `pre-market-brief` ACTIVE in `tasks` table with schedule `@market_open - 30min` and next_run `2026-05-27 13:00:00 UTC`. So the Reviewer has authored the cadence (or it was forked from the bundle pre-ADR-275). The post-deploy 13:01 UTC cycle produced the 5-section brief observed in `workspace_file_versions`.

**M-cell drift risk**: if the Reviewer never *re-reads* `_preferences.yaml` against current `_recurrences.yaml` to verify the cadence still serves the operator's declared preference, the cadence drifts from operator intent. The cycle keeps firing on its old schedule even if operator preference shifted. This is a M5 drift class — substrate-chain reasoning (cycle reads spec, produces deliverable) without grounding in current operator preference.

**Recommended Hat-A change**: none yet. ADR-275's mechanism (Reviewer reads `_preferences.yaml` at every wake + DiffRevisions to detect drift) addresses this structurally. Wait for first mandate-coherence measurement to show whether the pre-market-brief cycle actually surfaces preference-drift in standing_intent.md or whether it produces brief-section-output without ever referencing the cadence decision.

**Measurement gate**: per-slug substrate audit on `pre-market-brief` wakes — do standing_intent entries cite `_preferences.yaml` or MANDATE.md? If zero out of N wakes do, the ADR-275 mechanism is structurally complete but behaviorally inert. Then candidate becomes "extend persona-frame to require periodic preference-revalidation."

---

## Candidate 4 — `weekly-performance-review` is in `tasks` table but no spec exists in the bundle

**Surface**: `tasks` table for kvkthecreator shows `weekly-performance-review` ACTIVE with schedule `0 18 * * 0` (Sundays 18:00 UTC). Bundle has `specs/weekly-performance-review.md` referenced in the `_recurrences.yaml` comment block but I didn't read it — verify it exists.

**Risk**: if the Reviewer fires the cycle without a spec to ground deliverable shape, the output is unstructured prose. Even if mandate-cited (M1-shape), the brief becomes an idiosyncratic per-wake artifact rather than a comparable-across-weeks performance review.

**Recommended action before measurement**: verify the spec exists. If yes, read it for mandate-grounding language similar to Candidate 2. If no, that's a Hat-A gap to fix before the spec drift becomes the measurement noise floor.

---

## Candidate 5 — `principles.md` Bootstrap-phase clauses are mandate-grounded; Steady-state clauses are framework-internal

**Surface**: `review/principles.md` lines 15-37 (Bootstrap + Steady-state phase definitions).

**Bootstrap phase prose** (line 22):
> Author cadence + standing intent when upstream substrate is missing AND you would otherwise stand down waiting for it... The MANDATE designates you as the active principal — but the active principal does NOT short-circuit cron + substrate-event hooks.

This is explicitly mandate-grounded — names "MANDATE designates you as the active principal" + grounds the rule against MANDATE Position Lifecycle authority. **Bootstrap-phase wakes should produce high M1 ratio.**

**Steady-state phase prose** (lines 35-36):
> Capital-EV reasoning per the Capital-EV thresholds section below. Propose when EV positive and within edge; defer when EV ambiguous; reject when EV negative or hard rule violates.

This is framework-internal — capital-EV thresholds defined in principles.md, referenced by principles.md. No explicit MANDATE cite. **Steady-state wakes may produce M5 (framework-cited but mandate-indirect) rather than M1.**

**Asymmetry hypothesis**: the playbook is mandate-coherence-strong in Bootstrap phase (where the operator's mandate-vs-passivity tension is most acute) and mandate-coherence-thin in Steady-state phase (where the framework feels self-sufficient). This may be appropriate (Steady-state = trust the framework you authored from MANDATE) OR may be a drift surface (the framework can detach from MANDATE if framework-internal reasoning loops over time without re-grounding).

**Recommended Hat-A change**: none until measurement. The asymmetry might be exactly right — Bootstrap is the high-friction moment requiring mandate-cite, Steady-state is the framework executing cleanly. Premature mandate-cite enforcement in Steady-state would add noise to clean signals.

**Measurement gate**: cross-phase mandate-coherence breakdown. If Bootstrap-phase wakes produce M1 > 60% and Steady-state-phase wakes produce M1 + M5 ≈ same total but with M5-dominant, the asymmetry is by design. If Steady-state-phase wakes produce M6 > 10%, the framework has detached from MANDATE and re-grounding is needed.

---

## Candidate 6 — Persona-frame's Self-Improvement Posture (principles.md lines 43-67) bears on mandate-coherence indirectly but produces a different observable class

**Surface**: `review/principles.md` Self-Improvement Posture section. Five evidence patterns govern when the Reviewer edits operator-canon files (`_operator_profile.md`, `_risk.md`, `IDENTITY.md`, `principles.md`, `_preferences.yaml`, etc.).

**Why this matters for the mandate-coherence audit**: when the Reviewer DOES edit operator-canon (Candidate 6 is per ADR-295 evidence-thresholded), those edits should themselves be mandate-grounded — the revision message must cite mandate-clause that the edit serves (e.g., loosening RSI band serves MANDATE Edge Hypothesis #3 if 6-day persistence pattern shows the original threshold was too tight for current regime).

**M-cell drift risk**: if Reviewer edits operator-canon during the measurement window, those edits' revision messages produce a separate audit class — not directly mandate-coherence (which measures judgment cycle output substrate), but mandate-coherence-of-amendment which the criterion's §1.4 Q3 flagged as an open question. The two classes should not be conflated.

**Recommended action before measurement**: extend the mandate-coherence criterion's §1.2 operationalization to explicitly treat operator-canon edits as a separate observable class with the same A/B axis classification but tracked distinctly. Per-edit Axis-A/B tags would compose with the existing ADR-295 message-format checklist (already in `docs/evaluations/README.md` "Edit Checklist" section).

**Risk of not addressing**: first mandate-coherence measurement conflates standing_intent.md drift with operator-canon-edit drift, producing muddy aggregate numbers.

---

## Candidate 7 — Wake envelope's MANDATE.md preamble is structurally distant from the substrate-write moment

**Surface**: `api/agents/reviewer_agent.py` line 1183: `parts += ["## MANDATE.md — Operation's primary intent", "", ctx["mandate_md"], ""]` — MANDATE is in the wake envelope, pre-loaded as a substrate read.

**Distance problem**: the wake envelope is constructed once at wake-start. MANDATE.md appears at the top of the user message. The Reviewer then runs through tool rounds — ReadFile, ListRevisions, evaluate signals, compose ProposeAction, etc. By the time the cycle reaches the standing_intent.md write moment (often 3-5 rounds in), MANDATE.md has been displaced from the model's recent attention by intervening tool I/O.

**M-cell drift risk**: M5 inflation across all slugs. The Reviewer has all the context to cite MANDATE but the cite-distance produces substrate-chain reasoning instead (cites `_money_truth.md`, `_voice.md`, etc. — files seen more recently in the tool I/O stream).

**Recommended Hat-A change** (only if measurement supports): inject a mid-loop MANDATE reminder. Two options:

- **Option A** (lightweight): add MANDATE.md content to the persona-frame `_compute_standing_intent_contract` section so it's structurally adjacent to the standing-intent write instructions. Trade-off: increases token count, may reduce the prescription's relative weight.
- **Option B** (heavier): inject a system reminder when the model is about to write to `standing_intent.md` or `judgment_log.md`, citing the MANDATE Primary Action + Success Criteria. Trade-off: requires modifying the loop-level write-path code, not just prompt text.

**Measurement gate**: if first measurement shows A1 (explicit MANDATE cite) < 30% across all wakes but A2 (substrate-chain cite) > 50%, distance is the operative variable. If A1 is already > 50%, distance isn't the bottleneck.

**Risk of premature change**: Option B is loop-level code, not bundle data — it changes Reviewer behavior across ALL programs (alpha-trader, alpha-author, future programs). Premature deployment could over-fit alpha-trader's specific cite-pattern at the expense of programs where substrate-chain reasoning is preferable.

---

## Candidate 8 — Token-budget and round-budget pressure may be producing M6-DRIFT via attentional starvation

**Surface**: persona-frame's standing-intent contract is ~30K characters; bundle prompts add another 5-15K; substrate reads add another 30-50K (universe tickers, position state, principles, money truth). Total wake envelope is regularly 100K+ input tokens.

**Cycle dynamics**: with 100K+ input + 5K cap on standing_intent.md content + persona-frame's "almost always an action" prior, the model under attentional pressure may produce structurally-shaped output that satisfies all the visibility contracts but skips the mandate-cite step that would compete with the action-execution step for output-token budget.

**M-cell drift risk**: M6 specifically (visibility-compliant, mandate-blind) on wakes that reach max_rounds or near-max output tokens. The dispatcher safety net (Phase 3 fallback) catches the visibility miss but cannot retroactively make the model's already-written substrate mandate-coherent.

**Recommended Hat-A change**: none yet, this candidate is the highest-uncertainty in the audit. The hypothesis is structural but possibly wrong — the model may have plenty of attention left for mandate-citation; the persona-frame text just isn't prescribing it strongly enough (Candidate 1) is the simpler explanation.

**Measurement gate**: if first measurement shows M6 specifically concentrated on high-input-token cycles (>120K) or high-tool-round cycles (>10 rounds) — i.e., a correlation between attentional pressure and M6 — the candidate is supported. If M6 distributes uniformly across cycle lengths, attention isn't the operative variable.

---

## Recommendations summary

| # | Candidate | Recommendation | Measurement gate |
|---|---|---|---|
| 1 | Persona-frame action-bias without mandate-grounding pair | **Conditional**: add mandate-grounding clause to `_compute_persona_frame` | M3+M6 > 15% of P1+P2 wakes |
| 2 | `outcome-reconciliation` prompt is mandate-bare | **Conditional**: extend prompt with mandate-grounding cycle-close section | outcome-reconciliation M5+M6 > 50% |
| 3 | pre-market-brief cadence-drift risk under ADR-275 | **Wait**: structural mechanism should suffice, measure first | Zero wakes cite `_preferences.yaml` |
| 4 | `weekly-performance-review` spec verification | **Pre-measurement**: verify spec exists, check mandate-grounding language | N/A — diagnostic |
| 5 | Bootstrap vs Steady-state mandate-coherence asymmetry | **Wait**: may be by design, measure first | Steady-state M6 > 10% |
| 6 | Operator-canon edits as separate observable class | **Criterion extension**: amend mandate-coherence criterion's §1.2 before first measurement | N/A — methodological |
| 7 | Wake envelope MANDATE preamble distance | **Conditional + heavy**: only after measurement supports | A1 < 30% across all wakes |
| 8 | Attentional starvation on long cycles | **Lowest priority**: measure correlation first | M6 concentrates on >120K input cycles |

**Bias toward measurement-first**: 7 of 8 candidates recommend waiting for measurement before any Hat-A change. The exception (Candidate 4) is diagnostic verification, not a change. The remaining one Candidate 6 — extending the mandate-coherence criterion to distinguish judgment-cycle output from operator-canon-edit class — is a Hat-B methodological refinement, not a Hat-A code change.

This is intentional. The operator's thesis is well-formed but unmeasured. Landing playbook changes pre-measurement risks fitting the playbook to anticipated-but-unconfirmed drift patterns, exactly the failure mode the criterion-declaration discipline (`docs/evaluations/README.md` rule 0) exists to prevent.

---

## Streamlining opportunities (orthogonal to mandate-coherence)

Two playbook simplifications surfaced during the audit that aren't directly about mandate-coherence but reduce cognitive load on the Reviewer:

**S1**: `signal-evaluation` prompt is 75 lines of step-by-step instructions. Some steps (Step 1 signal evaluation logic, Step 4 ProposeAction templates) are mechanically derivable from substrate (signal definitions in `_operator_profile.md`, ProposeAction schema in primitive registry). Persona-frame already requires reading these substrates; the prompt repetition adds tokens without adding instruction. **Potential reduction**: 30-40 lines if the prompt becomes thin orchestration + "see substrate" pointers. Trade-off: makes the prompt less self-contained for cold-read debugging.

**S2**: `outcome-reconciliation` prompt is 28 lines describing what `services.outcomes.reconciler.reconcile_user` does internally. The Reviewer doesn't execute the reconciler — the deterministic Python does. The prompt's job is to wake the Reviewer to write standing_intent + ReturnVerdict; the procedural description is informational but uses tokens that could carry mandate-grounding instead. **Potential reduction**: 15-20 lines if reconciler description is replaced with "the reconciler runs; your job is to read the resulting `_money_truth.md` and write standing_intent + verdict, mandate-grounded per [add Candidate 2's grounding section]."

These are bundled with Candidate 2's recommendation if measurement gates trigger Candidate 2's prompt amendment — landing one prompt revision rather than two.

---

## What this audit does NOT do

1. **Does not land any Hat-A changes.** Every recommendation has a measurement gate or operator sign-off.
2. **Does not claim alpha-trader's playbook is broken.** It may be performing well; the audit identifies risk candidates so first measurement has hypothesis structure.
3. **Does not address alpha-author's playbook.** Cross-program comparison is a separate audit after both programs have ≥1 week of post-deploy substrate.
4. **Does not specify acceptance criteria for "playbook streamlined."** Streamlining is a side-effect of the measurement-gated changes if they land, not a goal in itself.

---

## Cross-references

- Mandate-coherence criterion: [`docs/evaluations/2026-05-27-000919-mandate-coherence-criterion/findings.md`](../evaluations/2026-05-27-000919-mandate-coherence-criterion/)
- Visibility-compliance criterion (companion): [`docs/evaluations/2026-05-26-163000-posture-criterion-declaration/findings.md`](../evaluations/2026-05-26-163000-posture-criterion-declaration/)
- Persona-frame source: `api/agents/reviewer_agent.py` `_compute_persona_frame` (lines 320-385), `_compute_standing_intent_contract` (lines 414-572), `_compute_judgment_discipline` (lines 387-411) at commit `bc40aff`.
- Bundle source: `docs/programs/alpha-trader/reference-workspace/` — `_recurrences.yaml`, `context/_shared/MANDATE.md`, `review/principles.md`, `specs/*.md`.
- ADR-274 (Trigger-authoring authority), ADR-275 (Introspection cadence Reviewer-authored), ADR-295 (Self-amendment evidence thresholds), ADR-303 (posture-cell taxonomy) — the canon governing what the playbook produces.
- Workspace carve enabling clean measurement: same-session DB changes (no separate finding file; the substrate is the receipt — `tasks` table + `auth.users` table reflect the carve).

---

## Status

**OPEN** — recommendations are measurement-gated, not actionable until ≥1 week of post-deploy substrate accumulation produces first mandate-coherence measurement (estimated 2026-06-03 earliest).

## Last updated

2026-05-27T00:20Z — initial draft post-workspace-carve.
