# DESIGN — the compressed-tenure rig (author, operator-attested ground-truth curve, real high-frequency wakes, IMPROVING target)

**Date**: 2026-06-25. **Hat**: B (evaluation instrument). **Subject**: funded `yarnnn-author` (`U=0b7a852d…`, WS=`e58ecdec…`). **Status**: BUILT + RUN — see the result in `2026-06-25-compressed-tenure-rig-stewardship-deferral-FINDING.md`. The rig works (FREE gate caught 2 measurement artifacts before spend); the SEEDED run surfaced a clean DP24 stewardship-deferral (perceive-and-escalate, not perceive-and-own) with a clean negative control. **Decided in discourse with the operator this session.**

> **The one-line thesis the rig tests.** A long-standing, fully-autonomous author agent, fired at high real cadence over a compressed window, *sustains* its loop AND *measurably improves* its judgment as its operator-attested ground-truth ledger accumulates — read as the `IMPROVING` rung of the TENURE-READ verdict ladder, off a curve that is **earned, not faked**, because operator-attestation is the author program's genuine ground-truth mechanism (ADR-330 `custody: operator_authored`).

---

## §1 The two design corrections this session made (why the rig is what it is)

**Correction 1 — operator-attested ground truth is REAL ground truth, not a simulated stand-in.** The first instinct ("the trader is the only program with a *real* earned outcome, because the market reconciles it") was wrong. ADR-330 (Ground-Truth Intake generalized beyond platform APIs; `attestation: platform | operator | agent` first-class) + the alpha-author MANIFEST `oracle: custody: operator_authored` + ADR-345 (Expected Output as workspace canon) establish that **a workspace's expected-output contract IS that workspace's ground-truth canon.** The trader's externally-reconciled outcome and the author's operator-attested outcome are the *same kind of thing* — an outcome the agent is held to by an adjudicator outside its own narration — differing only in **attestation source**, not legitimacy. `ledger.py:447` confirms it in code: `attestation: operator` rows are counted first-class in `by_attestation`.

**Why the author was the deliberate subject.** *Because* the author's outcome is internally dictatable (operator-attested, not gated on an external market or a broker reconciler), it is the program where a **controlled, fast, genuinely-attested** ground-truth gradient can be driven without waiting weeks for an external adjudicator. That is a feature for a compressed-tenure rig, not a compromise.

**Correction 2 — compress the CLOCK FREQUENCY, never fake the clock.** LONGITUDINAL-TRACKING §5 rule 5 forbids a *Claude-driven synthetic clock* (hand-advancing `@now`, fabricating trails to pretend time passed). The rig does NOT do that. It fires **real scheduler-shaped wakes at high real cadence** (1-minute-level — already an in-canon trader cadence, `@every 1min during regular_hours`), and Claude plays the §4.1 role: the *thin observer that checks whether the long-running thing is done* (like Claude Code polling a multi-step job), then reads the battery. Real fires → real earned substrate (ships, reflection, self-amendment). The only thing the rig *controls* is the **operator-attested outcome gradient** — which is the author program's actual ground-truth mechanism, attested honestly (`attestation: operator`), not a fabricated event stream.

> **The honesty line, stated precisely.** EARNED at high cadence: the wakes, the ships, the reflection-loop closes, the self-amendment trail, the intent-coherence carry. CONTROLLED (and honest): the operator-attested outcome grades feeding the curve — because operator-attestation *is* how the author's ground truth is established (there is no author reconciler, by design — the author's adjudicator is the operator, not a market). This is `attestation: operator`, the program's true contract — **not** the §5-rule-5 forbidden synthetic clock.

## §2 What "no author outcome provider" actually means (the architectural fact, correctly read)

`DEFAULT_PROVIDERS = [TradingOutcomeProvider, CommerceOutcomeProvider]` — there is no `AuthorOutcomeProvider`. **Correctly read, this is not a gap — it is the design.** The author's ground truth is `custody: operator_authored`; there is nothing to *reconcile from an external system* because the adjudicator is the operator. The rig supplies operator attestations the way the live product would: the operator (here, the harness acting as operator-proxy, ADR-294) grades shipped pieces and those grades land as `attestation: operator` events in `_signal.md`. That is the author's real loop, compressed in interval.

(Contrast: the *trader's* missing `_money_truth.md` IS a real defect — its adjudicator is external and the reconciler that folds it is orphaned. See `2026-06-25-trader-money-truth-orphaned-reconciler-AUDIT.md`. The author has no analogous defect; it has no reconciler *because it needs none*.)

## §3 The rig shape (fresh single script — operator's call)

`api/scripts/operator/probe_compressed_tenure_rig.py` — self-contained, re-fireable. Per the operator: a fresh single entry point, not a thin wrapper over the existing instruments (those stay as the disciplined library the rig's reads borrow query-shapes from).

**Phase 1 — FREE offline gate (no spend):**
- Materialize the author `_signal.md` at the canonical events-array shape (`{events:[{executed_at, action_type, value_cents, attestation:"operator", proposal_id}], last_reconciled_at, domain}`).
- **Validate `tenure_curve.py` renders a non-empty curve off the author events-array shape.** OPEN RISK: `tenure_curve.ledger_size()` counts integer, sample-keyword frontmatter leaves; the author events-array flattens to `events[i].value_cents` (a magnitude, not a sample-count key). The trader `_money_truth` carries explicit `total_reconciled_trades` counters that trigger `ledger_size`; the author shape may NOT. **If the author curve renders BOOTSTRAP-EMPTY despite real events, that is a `tenure_curve` shape-gap to fix (add an events-array length → ledger-size path), found FREE before any spend.** This is the §0 measurement-artifact trap caught in the act.
- Assert the gap-fact + curve climb across the seeded outcome gradient (2→4→6→8) and stay flat under the control (0 outcomes), reusing the verified `_reflection_gap_fact` join.

**Phase 2 — funded compressed-tenure burst (real high-cadence wakes, no reset):**
- N accumulating wakes fired in a tight loop (the genuine fire path, `_invoke_recurrence_wake` / the soak's fire body), **no reset between fires, persona memory carrying forward** — real accumulation.
- Between wakes, fold the *next* operator-attested outcome grade into `_signal.md` (the controlled gradient — the operator-proxy grading the just-shipped work), so the ledger genuinely accumulates as the agent produces.
- At each checkpoint (and at the end), run the **full TENURE-READ battery**: Read 1 (`tenure_curve.py` ground-truth curve), Read 2 (self-amendment trail — `reviewer:`-authored writes to `_voice.md`/`principles.md`/`_recurrences.yaml`), Read 3 (intent coherence — `standing_intent.md` evolution), plus the SURVIVAL machine axis (S9 closure, no silent/failed wakes, no thrash, floor-held).
- Deploy-marker stamped (local HEAD), per §3 paradox-resolution discipline.

**The verdict the rig targets:** `IMPROVING` — the curve bends right (operator-attested outcomes improve as the agent revises toward what its declared voice/editorial bar rewards) AND the self-amendment trail tracks the curve (amendments are ground-truth-cited, floor held). With the honest stamp: **earned wakes + earned amendments + operator-attested (controlled-interval) outcomes** — the author program's true ground-truth mechanism, compressed in cadence, not faked.

**The negative control (causation):** same rig, outcomes withheld (curve stays flat) → no amendments → confirms the improvement is caused by the agent perceiving the accumulating attested ground truth, not drift.

## §4 What the rig is NOT (the standing caveats, stamped on every output)

- It is **compressed-cadence real fires**, not a multi-week lived run. Per LONGITUDINAL-TRACKING §2 it proves the **mechanism sustains + improves under a real-but-fast clock**; the *organic* weeks-long curve (real operator grading pieces over real weeks) remains the live longitudinal soak's job. The rig is the *gate-before-tenure* for `IMPROVING`, exercised at speed — the strongest compressed-time evidence, explicitly not a substitute for the lived soak.
- The outcome *interval* is controlled (operator-proxy grades on the rig's schedule, not on a human's real reading pace). The outcome *attestation* is honest (`attestation: operator`, the author's true ground-truth source). Every rig output names this split.

## §5 Build order

1. Write `probe_compressed_tenure_rig.py`.
2. Run Phase 1 FREE — including the `tenure_curve` author-shape validation (the open risk). Fix any shape-gap found.
3. Pause non-test workspace recurrences (the held-all-session safety pattern — Render cron else spends).
4. Confirm author balance + autonomy (already `autonomous`, $16.65 effective — top up before the burst).
5. Run Phase 2 funded burst + battery; then the control.
6. Write the FINDING + the deploy-marker-stamped tracking-log entry.
