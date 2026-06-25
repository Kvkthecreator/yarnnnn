# PARKED — the trader tenure construction surfaced a possible axiomatic tension (learning-mandate vs production-mandate)

**Date**: 2026-06-25. **Hat**: B (evaluation, parked before any probe ran). **Status**: PARKED — documented as a candidate axiomatic discourse, not yet probed. Do **not** rush a probe; the friction may be a hint about the kernel, not a construction inconvenience.

> **Why parked (the operator's call):** when designing the trader symmetric tenure case, the construction wouldn't pick cleanly between two falsification stories and two revision targets without feeling forced. *"If the test setup shows conflicts, most likely it's a fundamental conflict"* — so we did the author setup first and parked the trader as a separate discourse, possibly a hint about something more axiomatic.

---

## The intended construction (the symmetric case)

The proven author tenure eval (calibration-drift on a voice rule) has a clean trader mirror **on paper**:
- **Ground-truth organ**: `_money_truth.md` (reconciled trade outcomes, system-authored, agent-read-only — the trader's `_signal.md`).
- **Aperture** (MAY move on ground truth): `operation/trading/_universe.yaml` (the ticker watch set) + entry bands.
- **Floor** (must NOT move except on calibration evidence): `operation/trading/_risk.md` (sizing/stops/var/caps). The program's own `principles.md` makes the aperture/floor split explicit (ADR-342/343) and declares the calibration threshold (≥40 reconciled trades, expectancy below −0.5R).

The symmetric test: seed N reconciled negative outcomes → PASS = the agent revises the **aperture** (`_universe.yaml`) toward ground truth + **holds the floor** (`_risk.md` unchanged). The probe's `--control` arm is the causation proof.

## The tension that surfaced (why it wouldn't construct cleanly)

Two forks appeared, and neither resolved without forcing — which is the signal worth keeping:

### Fork 1 — TWO falsification stories, different revisions
- **Dormancy** (ADR-342 offensive limb): signals fire but produce *zero proposals* → widen the **aperture**. This is the *empty* state; needs no `_money_truth` curve. `alpha-trader-2`'s live `_calibration.md` already shows it (`signal-evaluation: 9 fires · 0 proposals · ⚠ miscalibrated`).
- **Calibration-drift** (the author-mirror): the agent *trades* and the trades *lose* across ≥40 reconciled outcomes → revise the signal/aperture toward what works (and, if the floor itself is mis-calibrated, `_risk.md`). Needs a *populated* `_money_truth` curve.

"Learning velocity" + "seed an outcome trajectory" points at calibration-drift; but the trader's mandate is built around **selectivity** (high bar, trade rarely, expectancy is king), under which a disciplined systematic trader **correctly does almost nothing** — so "improves over tenure" has nothing to grip, and dormancy (not drift) is the live state.

### Fork 2 — the mandate flip itself
To make tenure grip, the operator's instinct was to **flip the mandate** from money-making/high-bar (rewards inaction) to **learning-velocity** (take many trades, experiment, accumulate reconciled outcomes fast — money becomes a *learning signal*, not the *suppressing gate*). But:
- Flipping to "take many trades" raises the floor question sharply: is `_risk.md` still inviolable? (The arc's whole safety story is "learn to select *within* a fixed floor, never by loosening it.")
- A **production mandate** (selectivity, expectancy) and a **learning mandate** (volume, experimentation) may be **axiomatically different mandate kinds** — and the framework currently has *one* mandate concept. The aperture/floor split (ADR-342/343) and the dormancy limb were derived under the *production* framing; whether they hold identically under a *learning* framing is unexamined.

## The candidate axiomatic hint (what to discourse, not probe)

**The friction is plausibly that "a production mandate" and "a learning/experimentation mandate" are different mandate kinds the kernel does not distinguish** — and several derived principles (DP24 stewardship, ADR-342 dormancy-as-ground-truth, ADR-343 aperture/floor, ADR-344 standing-obligation) were all derived under the production framing. Under a learning mandate:
- "Dormancy" might not be a falsification-candidate at all (zero trades could be *correct* under selectivity but *failing* under learning-velocity).
- The aperture/floor split might need a third category, or the floor's inviolability might interact with mandate-kind.
- "Expected output" (ADR-345) is declared as a contract — does a learning mandate declare a *different shape* of expected output (experiments run, outcomes reconciled) than a production mandate (value-moving writes)?

## Why NOT to probe yet

A probe forces a construction, and forcing a construction here would **bake in an answer to the axiomatic question** (is dormancy a falsification? is the floor in scope? is volume the metric?) before that question is discoursed. The disciplined move is to **discourse the mandate-kind question first** (is "learning mandate" a real kernel concept distinct from "production mandate," and if so what does it change about DP24/342/343/344/345?), *then* construct the trader tenure probe under whichever framing that discourse settles.

## Feasibility notes (for whoever picks this up)

- **`alpha-trader-2`** (`U=29a74c63…`, $20+): the only trader with a populated `_money_truth.md` + all rule organs (`_universe.yaml`, `_risk.md`, `principles.md`). Activated, funded, organ-complete — the natural testbed if the trader case proceeds.
- **`kvk-trader`** (`U=2abf3f96…`, $37+): better funded but **`_money_truth.md` is MISSING** (would need the ground-truth organ built/seeded first). MANDATE is the money-making/high-bar framing — the flip target. **→ AUDITED 2026-06-25** (`2026-06-25-trader-money-truth-orphaned-reconciler-AUDIT.md`): the absence is a real kernel-wiring conflict — the mechanical `reconcile_user` that writes the organ lost its scheduler caller in the ADR-260/261 back-office dissolution, while the `outcome-reconciliation` judgment prompt still asserts the fold "has" happened. Organ existence is currently an accident of bootstrap history. **The trader rig is not usable for a tenure eval until this is fixed (Hat-A).**
- **`alpha-trader`** (`U=2be30ac5…`): purged to bare kernel 2026-05-29, not re-activated; `_money_truth` absent.
- The reflection gap-fact is now tamper-proof for the trader too (ADR-364 D2a, `4df27f6`) — so a trader tenure probe would seed `action_proposals` + `_money_truth` events, same shape as the author testbed.
