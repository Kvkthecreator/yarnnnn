# Agent passivity: mandate-ownership vs rule-literalism when perception is structurally insufficient

**Date**: 2026-06-22
**Status**: RESOLVED — see [ADR-354](../adr/ADR-354-recurrence-prompt-collapse-and-perception-field-discipline.md) + [the validation finding](../evaluations/2026-06-22-full-autonomy-resolution-VALIDATION.md). The operator's reframe (it's over-engineering, not a missing forcing function) was correct: the obstruction was two competing instruction layers (a fat re-scripted recurrence prompt vs the thin frame) + a signal rule whose vocabulary didn't match the perception field. The fix was *less* (collapse the prompt, match the rule to emitted fields), not more. The agent then originated → approved → executed a capital action autonomously, blocked only by the off-hours hard floor. This discourse is preserved as the diagnosis that led there.
**Empirical trigger**: `docs/evaluations/2026-06-22-full-autonomy-probe-trader-never-acts-FINDING.md` — five `signal-evaluation` runs on a clean autonomous alpha-trader workspace (seulkim88), zero proposals, including under a fully-satisfiable Signal-2 state.
**Canon touched**: DP24 (stewardship, ADR-319), DP30 (the standing obligation, ADR-344), ADR-345 (expected output), ADR-318 (agentic wake posture), agent-composition.md §3.2.1 (the principles-vs-frame partition).

---

## The operator's framing (verbatim intent)

> "Right now it seems to still be passive in nature, AND the expected outcomes and mandate seem to be lower priority than 'following orders or rules', which isn't the right posture. … these tracking metrics are arbitrary fundamentally aren't they? so I can't tell if that's a set-up issue or an expected-behavior issue (probably some two-way consideration) which I think is more axiomatic in nature."

The operator has named the thing precisely. There are two layers and they must not be conflated:
- **Set-up layer** (which metrics, which fields, which rule) — partly arbitrary, fixable, Hat-A. This is Finding 1 (Signal 1 references substrate fields the mirror never emits) and Finding 3 (the scan isn't exhaustive across the universe) in the evaluation.
- **Axiomatic layer** — *how should the agent weight its mandate / expected-output against literal rule-compliance when its own perception apparatus is structurally insufficient to confirm a rule?* This document is about that layer only.

## The observation that forces the question

Run #3 (the cleanest): the floor was genuinely satisfied from the agent's perspective (a trustworthy, mirror-attributed SPY breakout snapshot, RSI 64.2, injection-tell removed). Two of Signal 1's four conditions ("20-day high", "volume > 1.5× avg") reference fields the snapshot schema **structurally never contains**. Faced with "I cannot confirm 2 of 4 from my substrate," the occupant:

1. **Deferred to the next scheduled fire** — "the scheduled RTH refresh will populate everything required." It will not: the RTH fire writes the identical schema. The agent modeled a *permanent structural gap* as a *transient timing gap*.
2. **Rated the decision "High confidence."**
3. **Served the rule over the mandate.** Signal 1 says 4/4 must verify; the mandate says compound capital; the standing obligation (DP30) says *a mandate you cannot reach is itself the thing to act on*. It chose 4/4-literalism and let the mandate wait.

## The sharp point: the canon already forbids this. It didn't fire.

DP30 / ADR-344 was ratified **four days before this probe** (2026-06-18) and its diagnostic test is almost verbatim the observed behavior:

> "a Reviewer that audits an empty production queue, writes coherent standing_intent, and sleeps — indefinitely, without ever surfacing that its mandate is structurally unreachable — is failing this principle (articulate inaction, the autonomy-in-costume)."

ADR-344's case **(B) structurally-can't** is *exactly* the Signal-1 schema gap: "a declared flow with no organ that originates it … the operation as configured cannot produce what it owes regardless of world state." The prescribed move is to **author the missing organ within the floor, or surface the structural gap + Clarify** — never serene waiting. The occupant did none of that. It classified an obvious case (B) as a case (A)-shaped "quiet pre-market, wait for data."

So the discourse is **not** "we lack a principle." It is: **DP30 is canonized but did not manifest in the trader occupant's run-time behavior.** That is the interesting, and more uncomfortable, finding. Three candidate explanations, not mutually exclusive:

### Hypothesis 1 — DP30's *stance* never reached the trader occupant's frame → **REJECTED (verified 2026-06-22)**
Verified against live substrate: DP30 is **fully present** on the trader. The live `principles.md` (line 117–126) has §"The standing obligation — what you owe, and whether your loop can deliver it (ADR-344)", including the (A)/(B) classifier. The kernel frame (`reviewer_agent.py:363`) has the stance ("You hold a **standing obligation** — what your budget, mandate, and quality bar put you on the hook to produce…"). The bundle template ships it. **So this is not "canon absent" — it is "canon present but inert."** The occupant read the principle (it's in its frame and its principles file) and still defaulted to rule-literalism + wait. That moves the whole finding into Hypothesis 2/3 territory and makes it the *ADR-352 shape*: a posture left to model preference is stochastic/wrong until structurally forced.

### Hypothesis 1b — the (B)-classifier's *examples* don't cover this failure mode → **CONFIRMED (the located mechanism)**
The decisive detail. The trader's live case-(B) definition (principles.md:126) enumerates structural-failure as: *"every declared signal retired with none replacing it … `signal-evaluation` archived, or the universe emptied."* These are all **organ-missing** cases. The failure the occupant actually faced is different: **organ-present-but-its-rule-is-unverifiable-from-substrate** (Signal 1 exists, fires nominally, but 2/4 conditions reference fields the snapshot schema never emits). That case is **not in the (B) example list.** So the occupant pattern-matched its situation against (B)'s examples, found none matched (signals aren't retired, eval isn't archived, universe isn't empty), and fell through to (A)/quiet-world → "wait for the refresh." **The classifier didn't misfire at random — it correctly applied a (B) definition whose enumerated cases are too narrow.** This is a concrete, fixable defect in the *derivation* (principles-resident per §3.2.1), and it generalizes: "a rule whose verifying fields are structurally absent from the perception field" is a (B) case the kernel-level DP30 framing should name program-neutrally, so every program's principles inherit it rather than each having to enumerate it.

### Hypothesis 2 — the standing-obligation check is gated on the wrong signal
DP30's runtime check reasons over "recent fires + ground-truth file + what exists." In bootstrap, `_money_truth.md` is empty and the agent correctly treats empty-money-truth as *not* a defer trigger (principles.md bootstrap clause). But the check may not be wired to notice "my signal rule references a field my mirror doesn't emit" as a **(B) structural** condition — because nothing in the substrate *says* the schema is short; the agent has to *infer* the permanence from the rule-vs-schema mismatch. The occupant did infer the mismatch ("cannot be verified from snapshots") — but then drew the *transient* conclusion ("wait for RTH") instead of the *structural* one. The inference machinery is present; the **classification step (A vs B) misfired toward (A)**. This points at the classifier thresholds in principles.md, or the frame stance being too weak to force the classification.

### Hypothesis 3 — rule-literalism is the stronger attractor than mandate-ownership, by default
Even setting aside DP30, the deeper pull: a rule with a crisp boolean ("4/4 conditions") is a **stronger behavioral attractor** for an LLM occupant than a diffuse mandate ("compound capital, own the reachability"). The crisp rule gives a clean, defensible, High-confidence stand-down; the mandate-ownership move (recognize structural unreachability → author/surface) requires a harder, less-scripted inference and produces a less-comfortable output (an escalation, an admission the operation can't do what it claims). **Absent a strong counter-weight, the occupant will reliably pick the crisp rule.** This is the same shape as the ADR-352 finding (ask-vs-act was model-whim until the gate forced it) — *a posture left to model preference defaults to the lower-effort, more-defensible move.* If true, the implication is structural: mandate-ownership-over-rule-literalism may need a **gate-like or frame-forced** mechanism, not prose persuasion, exactly as ask-vs-act did.

## Why "the metrics are arbitrary" is the right instinct — and where it bottoms out

The operator's "these tracking metrics are fundamentally arbitrary" is correct at the set-up layer and clarifying at the axiomatic layer:

- **Set-up**: *which* fields a signal keys on is a bundle-authoring choice (arbitrary in the sense of "could have been otherwise"). "20-day high" vs "price > sma_20" is a judgment call. That's Finding 1; fix the mismatch.
- **Axiomatic**: but the *arbitrariness* is exactly why rule-literalism is dangerous as the dominant posture. **If the rule is an arbitrary proxy for the mandate, then a rule the substrate can't evaluate is not a reason to stop — it's a signal that the proxy has detached from the thing it proxies, and the mandate must reassert.** A trader whose instruments can't confirm its entry rule does not have "no trade today"; it has "my instruments are broken relative to my strategy" — a (B)-class structural defect to surface, not a quiet day to sleep through. The arbitrariness of the metric is the argument *for* mandate-supremacy when the metric fails, not against acting.

This is the two-way consideration the operator named: the **set-up** must be fixed (the rule should be evaluable), AND the **posture** must be such that when a rule *isn't* evaluable, the agent escalates the structural gap rather than treating rule-non-evaluability as licence to wait.

## The axiomatic question, stated for decision

> When a Reviewer's declared rule cannot be evaluated from the substrate its own perception field produces, what is the correct posture — and is the current canon (DP30) sufficient to produce it, or does mandate-ownership-over-rule-literalism need a frame-forced / gate-like mechanism the way ask-vs-act did (ADR-352)?

Sub-questions:
1. **Manifestation**: is DP30's stance actually in the trader frame + a §Standing-Obligation derivation in the trader `principles.md`? (Verify before concluding anything — Hypothesis 1.) If absent, the first move is to land it on the trader, then re-probe.
2. **Classifier**: does the (A)-quiet-world vs (B)-structurally-can't classifier have enough signal to fire on a rule-vs-schema mismatch? The occupant *detected* the mismatch but classified it (A). What would make it classify (B)? (Hypothesis 2.)
3. **Attractor strength**: is prose ever enough, or does the LLM occupant's bias toward crisp-defensible-stand-down mean mandate-supremacy needs the ADR-352 treatment — moved from frame-persuasion into a structural forcing function? (Hypothesis 3 — the most consequential.) Note the precedent: ADR-352 concluded that a posture left to model preference (ask-vs-act) was stochastic until governance *derived* the outcome. Passivity-vs-ownership may be the same class of problem.
4. **Scope**: this surfaced on the trader because a *signal rule* was structurally broken. But the general form — "a declared obligation whose verifying substrate is structurally absent" — is program-neutral (an author whose quality bar references a metric no tool computes; a commerce op whose trigger needs a field the connector doesn't sync). Should the resolution be kernel-level (a general "structural-unreachability detector" feeding the DP30 classifier) rather than per-program?

## What this is NOT

- **Not** a claim the agent is broken at judgment. The substrate-integrity moat *worked* (run #2 caught a constructed bar). The agent is a strong *steward of conditions* and an honest *refuser of bad data*. The gap is the opposite pole: it does not *originate* action under its mandate when the rule-path is structurally obstructed.
- **Not** a prompt-nudge candidate. ADR-344 §10 and §3.2.1 are explicit that the stance is frame-resident and the derivation is principles-resident; if the fix is "tell it harder in the prompt," that violates the persona-frame collapse (DP22) and likely won't survive the attractor in Hypothesis 3. The resolution should be structural.
- **Not** resolved by fixing Finding 1 alone. Closing the schema gap makes Signal 1 evaluable — but the *posture* finding (run #3's "wait for the schedule" under structural unreachability; run #4–5's incomplete scan + non-action under a fireable signal) would still be latent, just harder to trip. The set-up fix removes *this instance*; the axiomatic fix is what makes "the agent originates action under its mandate" a property rather than a coincidence.

## Recommended next steps (sequenced)

1. **Manifestation verified (Hypothesis 1 → rejected; 1b → confirmed).** DP30 is present-but-inert on the trader; the located mechanism is that the (B)-classifier's *examples* (principles.md:126) cover organ-missing but not organ-present-rule-unverifiable. Done this session.
2. **Two candidate fixes, decide between them (or both):**
   - **(a) Widen the (B) examples** — add "a rule whose verifying fields are structurally absent from the perception field (the snapshot/observation schema never emits them)" to the (B) case. *Cheapest.* But it's per-program enumeration, and Hypothesis 3 warns prose may not survive the rule-literalism attractor.
   - **(b) Lift it to the kernel + consider a forcing function** — name "declared-rule-unverifiable-from-substrate" as a program-neutral (B) condition in the DP30 frame, and weigh whether mandate-supremacy-under-structural-obstruction needs the **ADR-352 treatment** (moved from frame-persuasion to a derived/structural forcing function), given the precedent that ask-vs-act was stochastic until governed. *The consequential one.* Draft as an ADR extending DP30.
3. **Fix Findings 1 + 3 (Hat-A) in parallel** — independent of the posture fix; make the workspace able to fire on real data (the precondition for the eventual end-to-end paper-fill proof). F1: reconcile Signal 1's rule with the snapshot schema + conformance check. F3: make `signal-evaluation` execute the full {ticker × signal} matrix.
4. **Re-probe on the trader** after (2)+(3) with a real RTH organic trigger (or a trustworthy construction on a *fixed* signal) and confirm the agent originates a proposal under a satisfied floor — the still-open "all the way to a paper fill" milestone.

## Receipts (for traceability)

Workspace `2be30ac5-b3cf-46b1-aeb8-af39cd351af4` (alpha-trader/seulkim88), autonomous, Alpaca paper X4DJ. Five `signal-evaluation` execution_events: `c993bbc3`, `6649cada`, `b50b8510`, `d7fb53da`, `7cc01a3d` (all success, 0 proposals, 0 `signals/` entries). Construction revisions: SPY `f4e11f3a` (`system:track-universe`), NVDA `1c8907c0` (Signal-2, all three conditions verified true). Schema gap: `api/services/primitives/track_universe.py::_write_ticker_yaml` emits no 20-day-high or current-volume field; locked by `test_trading_pipeline_architecture.py`.
