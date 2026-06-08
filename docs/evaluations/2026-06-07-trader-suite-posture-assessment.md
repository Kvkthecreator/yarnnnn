# Deep assessment — alpha-trader suite: structural shape vs. expected-behavior-and-posture

**Date**: 2026-06-07
**Hat**: B (external developer — eval toolchain). This is a criterion-first assessment per README rule 0. It does NOT mutate the suite or the harness; it separates what is *settled* (structure) from what needs *more nuanced consideration* (posture), and proposes a refined posture model for operator ratification before any wiring/run.
**Scope**: alpha-trader only (operator's narrowing). The author suite inherits whatever posture model we ratify here, later.
**Triggered by**: the 2026-06-07 discourse — "this kind of confusion [is market-open a harness or agent concern? is a Sunday stand-down success or failure?] is not what we want in both setup and expected behavior and posture." The confusion was a symptom of an under-specified criterion. A first-pass criterion doc (`alpha-trader-autonomous-loop.criterion.md`) was written; reading the full canon revealed that first pass was itself too flat. This assessment is the deeper look the operator asked for.

> Read order: this doc → `EVAL-SUITE-DISCIPLINE.md` §0 + §2 → `persona/principles.md` (the posture canon) → `alpha-trader-autonomous-loop.criterion.md` (the v1 cell table this assessment refines).

---

## §0 The one-paragraph finding

**The structural shape of the suites is settled and correct; the expected-behavior-and-posture model is under-specified in a specific, fixable way — it is missing two orthogonal dimensions the canon already carries.** The v1 criterion doc enumerated six per-wake *situational* cells (market × signal × data). But `persona/principles.md` makes posture a function of **three** axes, not one: the **situation** (what the wake perceives), the **lifecycle phase** (bootstrap vs steady-state — which *inverts* the expected posture for the same situation), and the **altitude** (within-the-mandate action vs on-the-mandate stewardship — a different read entirely, EVAL-SUITE-DISCIPLINE §2.3). A criterion that reads situation-only will mis-grade the Reviewer: it will score a bootstrap probe-trade as "over-eager" (when canon *mandates* it) and a steady-state sample-size defer as "passive" (when canon *requires* it). The fix is not more cells on one axis — it is declaring posture as `(situation × phase × altitude)` and pointing each suite eval at the cell it actually exercises.

---

## §1 What is SETTLED — the structural shape (do not re-open)

These are decided and working; the assessment affirms them so we don't churn:

1. **Two-axis model** (MACHINE vs MIND — EVAL-SUITE-DISCIPLINE §0). A deterministic fact (does a trade fire?) is a `test_*.py` integration test; a judgment (did it reason well?) is an eval read. Settled, canonized, and the reason the harness fixes (d4965cb) were correctly classified as MACHINE-axis toolchain, not MIND-axis criterion.

2. **Read-kind split** (§2.1 judgment-coherence / §2.2 substrate-responsiveness / §2.3 stewardship-coherence). Suites split by read-kind into separate files. Settled.

3. **Pre-flight `requires:` + `setup:`** (§3). The situation a read needs is harness-checked before firing; an eval whose precondition is violated is refused, not fired against garbage. Settled and load-bearing (the c51c44f lesson).

4. **`prior:` as orienting hypothesis, not a graded cell** (§4). The read is prose-judgment-against-mandate; the `prior:` orients but does not auto-classify. Settled — and notably, the *posture vocabulary* (M-cells, P-cells) is explicitly "a reading aid, not a grading scale" (§4 blockquote). **This is the key constraint on what follows**: the posture model below must be a *reading aid* (names for what you saw, each canon-cited), NOT a rubric the runner resolves a verdict into.

5. **The `@now` fixture + windowed snapshot + id-based gate** (f1b98f1, d4965cb). MACHINE-axis toolchain. Settled.

**So the structural question is closed.** The suite files, the read-kinds, the pre-flight discipline, the prose-read shape — all correct. What remains is purely: *what is the expected posture, stated precisely enough that a read is honest?*

---

## §2 What needs NUANCE — the posture model is one-dimensional, canon is three-dimensional

### §2.1 The v1 criterion doc's flaw: situation-only cells

The v1 `alpha-trader-autonomous-loop.criterion.md` §3 table is six cells on ONE axis — the **situation** the wake perceives:

> A market-closed · B RTH+match+fresh · C RTH+no-match · D RTH+stale · E hard-rule-fail · F exit-trigger

This is necessary but not sufficient. It reads as if "RTH + Signal-2 matches + fresh data → FIRE" were a single expected posture. **It is not** — canon makes the expected posture for that exact situation *invert* depending on a second axis the v1 table omits.

### §2.2 The missing axis #1 — LIFECYCLE PHASE (bootstrap vs steady-state)

`principles.md §Lifecycle Posture` declares two phases, **re-derived from substrate each wake** (not cached):

- **Bootstrap** (`_money_truth.md` empty OR signal sample size < 20): the action archetype is **propose probes** — "do NOT defer for sample size." Standing down to wait for evidence is the *named anti-pattern*.
- **Steady-state** (sample size ≥ 20 reconciled): the action archetype is **capital-EV reasoning** — "defer when EV ambiguous (the 20-occurrence threshold applies here)."

**The same situation has opposite expected postures across the phase boundary.** Concretely, the cell "RTH + Signal-2 matches + capital-EV uncertain":
- In **bootstrap** → **PROPOSE** (the Bootstrap clause: "trade them; let `_money_truth.md` accumulate"). A defer here is a **failure** (the named anti-pattern).
- In **steady-state** → **DEFER** (Capital-EV thresholds: "defer when EV ambiguous, sample < 20... the 20-occurrence threshold applies here"). A propose here is the **over-eager failure**.

A situation-only criterion cannot express this. It would score one of the two correct behaviors as wrong, depending on which phase the v1 author had in mind. **This is the deepest under-specification** — and it's invisible until you read the Lifecycle Posture + Bootstrap clause + Capital-EV sections together.

Worse for the read: the alpha-trader workspace is *currently in bootstrap* (kvk's `_money_truth.md` is sparse / seeded). So a Monday run will exercise **bootstrap** postures — and the v1 criterion, which implicitly assumed steady-state capital-EV reasoning, would mis-read a correct bootstrap probe.

### §2.3 The missing axis #2 — ALTITUDE (within-mandate action vs on-mandate stewardship)

EVAL-SUITE-DISCIPLINE §2.3 + `principles.md §Stewardship of Expectancy` + MANDATE establish that the Reviewer acts at **two altitudes**, and they are *different reads*:

- **Within the mandate** (action altitude, §2.1): judge proposed trades against the rules. The six situational cells live here.
- **On the mandate** (strategy altitude, §2.3): revise the rules themselves when `_money_truth.md` falsifies their premise — with the same urgency a trade demands. Governed by the invariant **money-truth moves the mandate; operator pressure never does.**

The v1 criterion doc reads *only* the action altitude. But the product objective (ADR-319 / DP24) is **ownership over tenure** — "a suite that reads only §2.1 measures a faithful executor; a suite that adds §2.3 measures a steward, which is the product." The alpha-trader-autonomous-loop suite, as it stands, is an *action-altitude-only* suite. That is a legitimate scope (it's the compliance sub-goal, the one-liner) — but it should *say so explicitly* and the stewardship altitude should be a *named, separate, deliberately-deferred* read, not silently absent. The confusion the operator named is partly this: "self-improving" (your words) is the **stewardship** altitude; "self-running trades" is the **action** altitude. The suite reads the second; it does not yet read the first.

### §2.4 The two-axis-for-TIME question, resolved cleanly

The original confusion ("is market-open a harness or agent concern?") is now answerable precisely, and it's a *clean* result that belongs in the posture model:

- **Market-state-as-input** is the agent's concern (it reads it from the Operating-Context block; it reasons about it — cells A/D). MIND axis. The read judges this.
- **Market-open-as-fire-precondition** is the harness's concern (fire the entry eval only when the market makes the entry situation real). MACHINE axis. A `requires: market_open` pre-flight, resolved via the *same* `NyseUsCalendar` the agent uses.

This is settled by the two-axis model already; it just hadn't been *applied to the time dimension* before. No new framework — an application of an existing one.

---

## §3 The refined posture model (proposal)

Posture = **`(situation × phase × altitude)`**, declared as a reading aid (§4 constraint — names for what you saw, each canon-cited), never a grading rubric.

### §3.1 Altitude first (the coarsest split)

| Altitude | Read-kind | Suite | Status |
|---|---|---|---|
| **Within the mandate** (action) | judgment-coherence (§2.1) | `alpha-trader-autonomous-loop.yaml` | **active — this is the suite we're about to run** |
| **On the mandate** (stewardship) | stewardship-coherence (§2.3) | `alpha-trader-stewardship.yaml` (does not exist yet) | **deferred — named, not built** (the "self-improving" read) |

**Proposal A**: the autonomous-loop suite explicitly scopes itself to the **action altitude** in its description, and names the stewardship altitude as the deferred sibling. This dissolves the "self-improving vs self-running" conflation: this suite reads self-running (compliance); a future stewardship suite reads self-improving (ownership). Both are real; they are different reads; the suite says which one it is.

### §3.2 Within the action altitude: situation × phase

The v1 six situational cells, each split by the phase boundary where canon inverts the posture. Only the cells where phase *changes* the posture need the split; the others are phase-invariant.

| Cell | Situation | Bootstrap posture | Steady-state posture | Phase-sensitive? |
|---|---|---|---|---|
| A | market closed | stand-down-on-clock | stand-down-on-clock | no (invariant) |
| B1 | RTH + match + fresh + **conformance unambiguous** | **PROPOSE** (probe; Bootstrap clause) | **PROPOSE** (EV positive) | no — both propose |
| **B2** | RTH + match + fresh + **capital-EV uncertain** | **PROPOSE** (Bootstrap: don't defer for sample size) | **DEFER** (Capital-EV: defer when EV ambiguous, <20) | **YES — inverts** |
| C | RTH + no match | stand-down-on-no-signal | stand-down-on-no-signal | no |
| D | RTH + stale data | refuse-on-freshness (Hard rule §7) | refuse-on-freshness | no (but see bootstrap *exception*: no `_regime.yaml` yet → treat inactive, scalar 1.0, PROPOSE — Hard rule §7 bootstrap exception) |
| E | RTH + match + fresh + hard-rule-fails | reject-with-rule-cited | reject-with-rule-cited | no |
| F | exit trigger (any time) | mandatory close | mandatory close | no (exits never defer — "defer rule does NOT apply to exit triggers") |

**The load-bearing addition is B2** — the cell whose posture *inverts* across the phase boundary, and the cell most likely to be mis-read on a bootstrap workspace. The read MUST first determine the phase (read `_money_truth.md` sample count) before judging B.

**Proposal B**: the criterion doc's cell table gains the phase column, and the read protocol (§4 of the criterion doc) gains a step 0: "determine the lifecycle phase from `_money_truth.md` sample count *before* classifying the situation cell." The `shape-receipts.md` already captures the substrate state to make this determinable.

### §3.3 The cardinal failure is altitude-and-phase-invariant

A wake that does not CLOSE with a `ReturnVerdict` (text-only, or NULL-token success = silent-wake S9) is the worst-shape outcome in every cell, every phase, every altitude. This stays as the v1 doc has it.

---

## §4 What this means for the run (the practical consequence)

1. **The Monday run exercises BOOTSTRAP action-altitude postures.** kvk's `_money_truth.md` is sparse → the live cells are A (if mis-timed), B1/B2-bootstrap (the target — probe-propose), C, D, F. The read must apply the *bootstrap* column, NOT the steady-state column. The v1 criterion would have mis-read this.

2. **"Self-improving" is NOT read by this suite.** The stewardship altitude (revise-the-rule-on-ground-truth) needs the seeded-falsified-rule arc (`*-stewardship.yaml`), which doesn't exist. If the operator's goal includes seeing self-improvement, that is a *second* suite — named here, deferred. The autonomous-loop suite proves self-running (compliance), the precondition for self-improving.

3. **The gate decision falls out cleanly**: `requires: market_open` (via `NyseUsCalendar`) on the entry eval only — but this is now justified by the posture model (cell A is phase-invariant + canon-correct + wasteful-to-fire), not an ad-hoc choice.

---

## §5 Proposal — what to land, in order

1. **Revise `alpha-trader-autonomous-loop.criterion.md`** to the `(situation × phase × altitude)` model: add the altitude scope statement (§3.1 Proposal A), the phase column with B2 as the inverting cell (§3.2 Proposal B), and the read-protocol step-0 (determine phase first). [Hat-B doc, no behavior change.]

2. **Name the deferred stewardship suite** in the criterion doc + EVAL-SUITE-DISCIPLINE §2.3's file-layout note: `alpha-trader-stewardship.yaml` reads the "self-improving" altitude; deferred until the action altitude has one clean live read. [Hat-B doc.]

3. **Wire the autonomous-loop suite** `description:` + each `prior:` to the refined cells by name (e.g. signal-detection eval → "expected: cell B1/B2-bootstrap per criterion §3.2"). [Hat-B suite YAML.]

4. **Gate decision** (`requires: market_open`) — implement OR keep operator-fire. Now a derived consequence, not ad-hoc. [The one MACHINE-axis change; operator's call on whether to build the calendar gate or keep picking the hour.]

5. **Then run** (Monday RTH), reading against the bootstrap action-altitude column.

**Open questions for operator ratification (the nuance that's genuinely yours):**

- **Q1 — Is the autonomous-loop suite correctly scoped to action-altitude-only?** Or do you want the stewardship read folded in now (making it a bigger suite) rather than deferred? (My lean: defer — one clean action read first, then stewardship. But "self-improving" is your stated goal, so this is yours.)
- **Q2 — Is B2 (the phase-inverting cell) the right reading of canon?** I derived "bootstrap proposes even when EV-uncertain; steady-state defers" from the Bootstrap clause vs Capital-EV thresholds. Confirm that's the intended posture, because the whole read pivots on it.
- **Q3 — Gate: build the `NyseUsCalendar` pre-flight, or keep operator-fire?** You said "operator fire is right" earlier; the posture model *supports* but does not *require* the auto-gate. Operator-fire + a documented "fire during RTH" note is the lower-code path; the auto-gate is the more self-aware harness.

---

## §6 Receipts

- Lifecycle phase inversion: `principles.md §Lifecycle Posture` (bootstrap "do NOT defer for sample size" / steady-state "defer when EV ambiguous, 20-occurrence threshold") + §Bootstrap clause ("trade them; let `_money_truth.md` accumulate") + §Capital-EV thresholds ("defer for operator review when sample < 20").
- Altitude split: EVAL-SUITE-DISCIPLINE §2.3 + §2.4 ("a suite that reads only §2.1 measures a faithful executor; adding §2.3 measures a steward") + `principles.md §Stewardship of Expectancy` (two altitudes) + MANDATE (two altitudes, DP24 invariant).
- Posture-as-reading-aid constraint: EVAL-SUITE-DISCIPLINE §4 blockquote ("Posture vocabulary … a reading aid, not a grading scale").
- Time two-axis: ADR-274/301 Operating-Context block (`reviewer_envelope.py::build_operating_context_block`) + `market_calendars.NyseUsCalendar.is_open_now` + EVAL-SUITE-DISCIPLINE §0.3.
- Bootstrap workspace state: kvk `_money_truth.md` sparse/seeded (the warm-start scenario seeds it precisely because real reconciled history doesn't exist yet).
