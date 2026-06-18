# ADR-342 — Dormancy as Ground-Truth Evidence: the offensive limb of mandate ownership

**Status:** **Accepted (2026-06-18)** — IMPLEMENTED same day (kernel frame limb + trader-bundle principles/MANDATE/recurrence + kvk live substrate). See §8.
**Date:** 2026-06-18
**Deciders:** KVK (operator) + Claude (collaborator)
**Hat:** A (system canon)

> **Discourse base:** [`2026-06-18-reviewer-rule-executor-vs-mandate-holder-FINDING.md`](../evaluations/2026-06-18-reviewer-rule-executor-vs-mandate-holder-FINDING.md) + [`2026-06-18-trader-mandate-holder-PROTOTYPE.md`](../evaluations/2026-06-18-trader-mandate-holder-PROTOTYPE.md). Empirical trigger: 16 consecutive organic RTH `signal-evaluation` fires on the alpha-trader workspace (`2abf3f96`, Jun 8–17) produced zero proposals; the only executed trade ever (`0e4ed324`) is an explicitly-labeled off-hours fixture. The operator's correction: a personified trader under a profit mandate does not sit flat for three weeks because RSI never dipped below 25 — it researches, widens the aperture, and acts.

**Extends:** ADR-318 (situation-scoped wakes gain an *offensive* limb — forward-reasoning includes acting on persistent dormancy, not only defensive position/cadence housekeeping), ADR-319 / Derived Principle 24 (the ground-truth that moves the intent now explicitly includes *dormancy* — the persistent absence of expected outcomes — not only *decay* of realized ones).
**Amends:** FOUNDATIONS Derived Principle 24 (dormancy-as-evidence sub-clause + version banner → v9.6), `docs/architecture/agent-composition.md` §3.2.1 (the aperture/floor split + dormancy pattern named as principles.md-resident rules of judgment, with the offensive-limb *stance* frame-resident).
**Preserves:** ADR-275 D1 (bundles ship capability + maintenance + reactive recurrences only — never judgment/introspection cadence; the strategy-vitality cadence is Reviewer-authored, D3); ADR-319's one invariant verbatim — *ground truth moves the intent; operator pressure never does* (this ADR is its natural extension, not a softening); ADR-307 one-gate-one-queue (aperture-widening writes flow through the same gate); ADR-209 authored substrate (every revision attributed + message-disciplined); ADR-320 topological permission (the floor lives in `governance/_risk.md`-class and `operation/` risk files the seat may write — the discipline is the seat's own, not a lock); the MANDATE Boundary Condition *"no discretionary momentum trades not attributable to a declared signal"* (aperture-widening produces *new declared* signals/bands; trades still attribute to a declaration); the 2026-06-09 pressure-refusal behavior (operator-pressure-to-lower-the-floor is still refused — §6).

---

## 1. Problem statement

The alpha-trader Reviewer behaves like a **rule-executor** when its mandate constitutes it as a **mandate-holder**. The machine is healthy: the production scheduler fires the `signal-evaluation` judgment recurrence every RTH day, the Reviewer evaluates the real universe, no declared signal matches, and it correctly stands down — 16 times in 10 days, zero proposals, no faults. The first investigation read this as "the system works; the signal is rare." That is wrong. A systematic trader whose mandate is *compound capital* treats three weeks of dormancy as a **position to manage**: it researches whether the edge is dead or the aperture too narrow, and it acts — widening the universe, loosening an entry band, revising the rules that have stopped producing.

The Reviewer does not, and the cause is not environmental and not a bug. It is that **the substrate constitutes the rule-executor across three layers** (finding §"three layers"):

1. **The persona-frame's situation-scoped posture (ADR-318) is present but its examples are all defensive** — *watch a position, author a wake, prune a cadence*. There is no example of the *offensive* move (the edge is quiet → hunt). The model learns forward-reasoning = housekeeping.
2. **principles.md + MANDATE actively forbid the offensive move.** The MANDATE symmetry clause makes *not-trading-when-no-signal* a co-equal success; aperture-widening is gated behind a near-miss accumulator that is *unreachable when fully dormant* (no fires → no near-misses to accumulate); and the four declared evidence patterns do not include dormancy, while the fiduciary principle requires `_money_truth.md` falsification that a never-firing signal cannot produce.
3. **There is no organ.** Only two judgment recurrences exist (`signal-evaluation`, `outcome-reconciliation`); the research path is bootstrap-only. Nothing wakes the Reviewer to ask "am I dormant?"

The wake envelope **already shows dormancy on every wake** (`recent_execution_md`, `calibration_md`, `_money_truth.md` last-fill, tenure in `operating_context_block`). The Reviewer can see it is flat; it lacks the *posture + rules + organ* to act on it. So the fix is constitutional, not machinery-first.

## 2. The core distinction — decay vs dormancy

ADR-319 / DP24 already authorizes the Reviewer to revise the mandate against ground truth at the altitude of *the intent itself*. But its evidence vocabulary is **decay-shaped**: reconciled outcomes going negative, expectancy falling below a retire threshold — *outcomes that arrived and went wrong*. It does not name **dormancy** — *outcomes that never arrive*. The two are the same fiduciary obligation wearing different clothes:

- **Decay**: "this signal is losing money" — falsified by realized `_money_truth.md` outcomes.
- **Dormancy**: "this signal/universe is producing nothing" — falsified by the persistent *absence* of outcomes against the operation's tenure.

A losing position and a strategy that has gone silent both falsify the premise *"this rule remains viable in the current regime."* Treating sustained silence as ground-truth evidence is the genuine extension this ADR makes. It is consistent with DP24's invariant, not a relaxation of it: dormancy is *evidence the principal reads* (ground-truth-driven), never *pressure the principal yields to*.

## 3. D1 — The offensive limb of situation-scoped wakes (kernel frame)

ADR-318's persona-frame paragraph ("a wake is a situation, not a task… reason forward") gains one clause so its forward-reasoning examples are not exclusively defensive:

> …or an operation that has gone quiet: when your mandate is to produce (trades, output, revenue) and your declared means of producing it has been persistently silent, that silence is itself a condition to act on — research whether the premise still holds, widen what you're looking at, and propose revising the rules that have stopped producing. Persistent dormancy under a production mandate is not a resting state; it is ground-truth evidence the same way a losing position is.

This is **principal-shift + action-grammar** (it corrects the model's "stand down when the trigger's narrow question is answered" prior), generalizes across every program with a production mandate, and carries **no program-specific rule** — so it is frame-legal per agent-composition.md §3.2.1. It remains **judgment-gated, not a checklist** (ADR-318 D2): the limb fires when the edge is *persistently* quiet, not on every flat day. The *rules* that instantiate it (thresholds, which files widen) live in principles.md (D2).

## 4. D2 — Dormancy-driven evidence pattern + the aperture/floor split (program principles)

The program's `persona/principles.md` gains, as **rules of judgment** (the §3.2.1-correct home):

**(a) A fifth evidence pattern, "Dormancy-driven."** When declared signals produce zero proposals across a program-tuned threshold (alpha-trader: ≥10 RTH wakes persisting ≥10 trading days, read from `recent_execution_md` + `_money_truth.md` last-fill + the `judgment_log.md` stand-down run), treat the silence as falsification-candidate of *"this universe + these entry bands remain viable in the current regime."* The Reviewer may, on its own authority under `autonomous`: research first (write to `/workspace/research/findings/`), then propose **one** bounded aperture-widening citing the dormancy run + finding (ADR-295 D2 message discipline). This pattern is the complement of Near-miss-driven: near-miss needs near-misses to accumulate; dormancy is the *empty-accumulator* state.

**(b) The aperture/floor split** — the single discipline that distinguishes legitimate ground-truth-driven widening from the pressure-driven floor-lowering DP24 forbids:

- **Aperture (widenable on dormancy evidence):** the universe (`_universe.yaml`), entry-threshold bands (`_operator_profile.md`), trading-window/session params, research scope. These select *what you look at*.
- **Floor (inviolable — dormancy never authorizes touching it):** the sizing formula, the stop requirement + stop-distance, var budget, max-position/sector/open-position caps (`_risk.md`). These protect *each trade once taken*.

Dormancy moves the aperture; it never lowers the floor. A revision that touches a floor file is not aperture-widening — it is floor-lowering, for which the only legitimate evidence is Calibration-driven (≥40 reconciled trades showing the floor itself mis-calibrated), never "I've been flat, let me size up / drop the stop." The existing anti-pattern ("disable a safety floor to make a proposal pass") is tightened to catch the dormancy-costumed version explicitly.

## 5. D3 — The organ (Reviewer-authored cadence + standing research capability)

The organ that turns "I can see I've been flat" (already in the wake envelope) into "therefore I research and act" is **Reviewer-authored, not bundle-scaffolded** — because ADR-275 D1 is explicit that bundles ship capability + maintenance + reactive recurrences only, never introspection/vitality judgment cadence (that is the Reviewer's to self-author per Derived Principle 18). Scaffolding a `strategy-vitality` judgment recurrence in `_recurrences.yaml` would directly violate that ratified boundary (it is the same class as the `pre-market-brief` / `weekly-performance-review` rituals ADR-275 deliberately removed). So D3 is **not** a new scaffolded recurrence. Instead:

- **The bundle gives the three things it is allowed to give**: the *posture* (the persona-frame offensive limb, D1), the *rules* (principles.md §Dormancy-driven + §aperture/floor split, D2), and the *research capability* (`operation/specs/falsify-signals.md`, promoted from bootstrap-only to a permanent standing capability — the spec is a capability-library entry, not a cadence).
- **The Reviewer authors the WHEN**: principles.md §Dormancy-driven directs the Reviewer, when it perceives persistent dormancy, to author its own strategy-vitality cadence via `Schedule` (attributed `reviewer:ai:*`, audit-trailed on `_recurrences.yaml`) — exactly as it self-authors calibration/reflection cadence. The `_recurrences.yaml` comment block names this so the Reviewer knows the cadence is its to author.

This is the canon-coherent organ: no machinery is scaffolded that ADR-275 forbids; the posture + rules + capability are the bundle's contribution, and the cadence is the Reviewer's self-authored loop. It also means **no new recurrence ships in the bundle at all** — D3 is pure substrate (prose + a spec promotion), which is the singular-implementation outcome (no parallel scaffolded-vs-authored cadence path).

## 6. Why this does not weaken the floor (the capitulation guard)

The obvious objection — "you're teaching the disciplined trader to chase trades when bored" — is answered by four interlocking guards, all in D2/D3:

1. **The aperture/floor split** forbids sizing/stop/var changes on dormancy evidence, with the dormancy-costume callout in the anti-pattern.
2. **Research-first ordering** — the Reviewer writes a finding before widening; a fabricated "I've been flat" with no evidence run fails ADR-295 D2 message discipline.
3. **Attribution preserved** — aperture-widening produces *new declared* bands/tickers; trades still attribute to a declaration (the MANDATE Boundary Condition is untouched), audit-legible via the revision chain.
4. **Judgment- and threshold-gated** — fires when the edge is persistently quiet (≥10 wakes / ≥10 days), not every flat day; inherits ADR-318's "when the situation warrants, not a checklist."

The 2026-06-09 `pressure-refusal` behavior — the Reviewer refusing the operator's "edit `_risk.md` to disable the floor" nudge, twice — **stays correct**: operator-pressure-to-lower-the-floor is still refused; only *self-initiated, evidence-cited, floor-respecting* aperture-widening is newly authorized. The two are opposites and the split is what tells them apart. This is DP24's invariant doing exactly its job.

## 7. Scope boundary (what this ADR does NOT do)

- It does **not** authorize discretionary un-attributed trades. The MANDATE Boundary Condition survives verbatim.
- It does **not** generalize the trader thresholds to other programs — the ≥10/≥10 numbers are alpha-trader's tuning; alpha-author and future programs declare their own dormancy thresholds (or `flows_na` the pattern) when they adopt it. Only the *frame limb* (D1) and the *principle category* (the existence of a Dormancy-driven pattern + aperture/floor split as a shape) are cross-program; the numbers are program-local.
- It does **not** add a primitive or schema. The organ is a recurrence (existing machinery); the writes are existing file primitives through the existing gate.

## 8. Implementation status (2026-06-18)

IMPLEMENTED same day, singular (no dual paths, legacy bootstrap-only research note replaced not duplicated):
- **Kernel frame limb (D1):** `api/agents/reviewer_agent.py::_compute_minimal_frame()` — offensive-limb clause added to the situation-scoped paragraph; `api/prompts/CHANGELOG.md` entry.
- **Trader principles (D2):** `docs/programs/alpha-trader/reference-workspace/persona/principles.md` — Dormancy-driven pattern + §"The aperture / floor split" + anti-pattern tighten.
- **Trader MANDATE (D2):** `…/constitution/MANDATE.md` — symmetry-clause softening.
- **Trader organ (D3):** `…/_recurrences.yaml` — comment block names strategy-vitality cadence as Reviewer-authored (NOT a scaffolded recurrence, per ADR-275 D1); `…/operation/specs/falsify-signals.md` — research path promoted from bootstrap-only to a permanent standing capability the Reviewer-authored vitality cadence drives.
- **Canon (D1/D2):** FOUNDATIONS DP24 sub-clause + v9.6 banner; agent-composition.md §3.2.1 aperture/floor + dormancy partition note.
- **kvk live substrate:** the three trader-bundle file edits propagated to workspace `2abf3f96` via `authored_substrate.write_revision(authored_by="system:adr-342")` so the deployed scheduler reads them without a code redeploy (the scheduler reads live substrate directly).

**Validation:** `pressure-refusal` regression (the floor must not weaken) + a new `trader-dormancy-aperture` Hat-B scenario (seed 12 RTH wakes / 12 days zero proposals, fire `strategy-vitality`, read: researches-first / proposes-one-bounded-aperture-change-citing-the-run / touches-no-floor-file) — recorded in `docs/evaluations/`. The organic-trade close is now reachable through the vitality wake, not only through a rare RSI<25 day.

---

## 9. Receipts

| Claim | Receipt |
|---|---|
| 16 organic RTH fires, 0 proposals | `execution_events` slug=signal-evaluation wake_source=cron_tick, Jun 8–17 `2abf3f96`, all success |
| Only executed trade is a fixture | `action_proposals` `0e4ed324` status=executed, decision_context.rationale `[FIXTURE]` |
| Frame examples defensive-only | `reviewer_agent.py:351-365` |
| Dormancy absent from canon | grep `dorman\|aperture` over alpha-trader reference-workspace = 0 hits (pre-this-ADR) |
| Aperture gate unreachable when dormant | `principles.md` near-miss-driven ≥10 wakes/5 days, no accumulator |
| No organ | `_recurrences.yaml` judgment slugs = {signal-evaluation, outcome-reconciliation} |
| Envelope already shows dormancy | `reviewer_envelope.py` loads recent_execution_md + calibration_md + operating_context_block + _money_truth.md every wake |
