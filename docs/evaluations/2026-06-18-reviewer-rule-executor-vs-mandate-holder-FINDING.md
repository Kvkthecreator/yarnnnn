# Finding — the trader Reviewer is a faithful rule-executor of a rulebook that tells it to be one

**Date**: 2026-06-18
**Persona / workspace**: kvk (`2abf3f96-118b-4987-9d95-40f2d9be9a18`), alpha-trader, live Alpaca paper, `delegation: autonomous`
**Hat**: B (diagnostic map) → Hat-A prototype (trader bundle only; kernel frame edit scoped but deferred to ADR)
**Question**: why has no fully-organic autonomous trade fired, *and* — reframed by the operator — why does the Reviewer not behave like a personified trader who, under a profit mandate, goes out to research, widens the universe / entry bands / RTH parameters, and puts on more trades when its declared edge has gone quiet?

---

## Headline

The first investigation framed 16 consecutive zero-proposal RTH days as "the machine works; the signal is just rare; the Reviewer correctly stands down." **That framing was wrong.** Under a profit mandate, a personified trader does not sit flat for three weeks because RSI never dipped below 25 — it notices the dormancy, researches whether its edge is dead or its aperture too narrow, and acts. The Reviewer doesn't, and the reason is not environmental and not a bug: **the substrate constitutes it as a rule-executor in three independent layers**, two of which actively *forbid* the offensive move. The Reviewer is behaving correctly — to a rulebook that is itself the gap.

The machine is genuinely healthy (receipts in the prior finding): the prod scheduler fires `signal-evaluation` as an organic `cron_tick` judgment wake every RTH day (16 fires Jun 8 → Jun 17, all `success`, real tokens, no NULL-token faults); `delegation: autonomous`, $50k ceiling, position ~$3.4k well under. The only executed proposal ever (`0e4ed324`, Jun 5) is an explicitly-labeled `[FIXTURE]`. So the no-trade situation is **not** the machine and **not** signal rarity — it is posture.

---

## The three layers that constitute the rule-executor

### Layer 1 — the persona-frame's situation-scoped posture is present, but its examples are all *defensive*

`api/agents/reviewer_agent.py::_compute_minimal_frame()` already carries ADR-318's situation-scoped posture verbatim (line 351): *"A wake is a situation, not a task… reason forward… does the situation warrant more than the immediate task."* The plumbing is right and the stance is right.

But **every illustrative example in lines 354–365 is defensive/housekeeping**: *"a position that needs watching, a future wake you should author, a cadence that's wrong because ground truth has falsified it."* Watch · schedule · prune. There is **not one example of the offensive limb** — "your edge has gone quiet; go research; widen the net; find a trade." A model reads the frame's gravity and learns *forward-reasoning = maintain my own cadence*, not *hunt for the operation's next dollar*. The posture generalizes; its examples pull toward tidiness.

**Receipt**: `reviewer_agent.py:351-365` — read the example list; all defensive.

### Layer 2 — principles.md + MANDATE.md *forbid* the offensive move (the cage)

This is the load-bearing layer. Three clauses, each independently correct, together a cage:

1. **MANDATE symmetry clause** (`constitution/MANDATE.md`, live + bundle): *"the operation fails if signals fire within the rules and the Reviewer does not propose, **and equally if signals do not fire and it proposes anyway**."* This makes *not-trading-when-no-signal* a **co-equal success condition** — it elevates rule-conformance to the altitude of the profit goal, and explicitly forbids discretionary aperture-widening into a trade.

2. **Aperture-widening gated behind a non-existent accumulator** (`persona/principles.md` §"When to propose edits", near-miss-driven pattern): aperture changes require *"≥10 distinct wakes persisting ≥5 days"* of **near-miss** evidence, surfaced to `notes.md` "as the pattern accumulates." But nothing accumulates dormancy, and if the universe is too tight there are *no near-misses to accumulate* — the gate is unreachable in exactly the dormant state where it's needed.

3. **Dormancy is not an evidence pattern, and the fiduciary principle requires money-truth that dormancy can't produce** (`persona/principles.md` §Stewardship + §fiduciary). The four declared evidence patterns are calibration-decay, near-miss, substrate-gap, cadence — **dormancy ("flat for N days") is on none of them**. And the fiduciary principle says revision requires *`_money_truth.md` falsification* — but a signal that never fires produces no money-truth to falsify. So the canon doesn't merely fail to encourage hunting; it has three clauses that *correctly refuse* it given how they're written.

**Receipts**: grep for `dorman|dormant|aperture|no.*signal.*fired` across the bundle reference-workspace → **0 hits**. MANDATE.md symmetry line; principles.md near-miss threshold + four-pattern list + fiduciary "money-truth falsifies."

### Layer 3 — there is no organ

Only two judgment-mode recurrences exist (`_recurrences.yaml`): `signal-evaluation` (@market_open+15) and `outcome-reconciliation` (@market_close+1h). **No recurrence ever wakes the Reviewer to ask "am I dormant? is my edge dead? should I research?"** The research substrate (`/workspace/research/findings/`, `operation/specs/falsify-signals.md`) is **bootstrap-only** — fires once at activation, then only on explicit operator FireInvocation (its own spec says so). Even if the frame and principles authorized hunting, nothing wakes the agent into the question and it has no standing research loop to run.

**Receipt**: `_recurrences.yaml` judgment-mode slugs = {signal-evaluation, outcome-reconciliation}; `operation/specs/falsify-signals.md:113-116` ("not a permanent research function… fires once on activation").

---

## What the plumbing already gives us for free (so the fix is NOT machinery-first)

The wake envelope (`services/reviewer_envelope.py::load_reviewer_governance_envelope`) **already** loads, on *every* wake, identically across all sources: `operating_context_block` (now + market state + tenure = time-flat), `recent_execution_md` (last-24h fires), `calibration_md` (cadence vs ground-truth), `standing_intent_md`, `budget_yaml`, plus the program substrate (`_money_truth.md`, `_operator_profile.md`, `_risk.md`, signal files). **The Reviewer can already SEE its own dormancy** — recent-execution shows zero proposals, money-truth shows last-fill date, tenure shows days-active. What it lacks is the *posture + rules + organ* that turn "I can see I've been flat 18 days" into "therefore I research and act."

This is why the fix is **constitutional, not mechanical**. The one genuinely-mechanical addition (a dormancy/vitality wake + a standing research path) exists to give the new posture *somewhere to run* — it is not the fix itself.

---

## The fix, across the three layers (all Hat-A)

1. **Frame** (`reviewer_agent.py::_compute_minimal_frame`, kernel — generalizes across every program): add the *offensive limb* to situation-scoped forward-reasoning — under a profit/output mandate, **persistent dormancy of your declared edge is itself a condition to act on**: research, widen aperture, propose revising the rules. Frame-legal per agent-composition.md §3.2.1 (principal-shift/action-grammar; the *rules* stay in principles.md).

2. **principles.md** (trader bundle): add **dormancy-as-evidence** as a first-class pattern (the 5th), and make the **aperture/floor split** explicit and load-bearing:
   - **Aperture** (widenable on dormancy evidence, ground-truth-driven, autonomous-authority): `_universe.yaml` tickers, entry-threshold bands in `_operator_profile.md`, trading-window/RTH params, research scope.
   - **Floor** (inviolable regardless of dormancy — the capitulation guard): sizing formula, stop requirement, var budget, max-position/sector caps in `_risk.md`.
   - The invariant that keeps this honest: **dormancy moves the aperture; it never lowers the floor** — a direct application of ADR-319/DP24 ("ground truth moves the intent; operator pressure never does"). This is what stops the offensive limb from becoming the "I'm bored, loosen the stops" backdoor the 2026-05-20 / 2026-06-09 pressure-refusal evals exist to catch.

3. **MANDATE.md** (trader bundle): soften the symmetry clause so prolonged dormancy is a *trigger to act ON the mandate* (research/widen), not only a prohibition on acting WITHIN it. The discipline "no discretionary momentum trade attributable to no signal" stays — what changes is that *persistent silence obligates revision-work*, it is not a stable resting state.

4. **The organ** (trader bundle `_recurrences.yaml` + research spec): a `strategy-vitality` judgment recurrence (e.g. weekly, or after K zero-proposal RTH days) that wakes the Reviewer specifically to read its dormancy evidence and act, plus promotion of the research path from bootstrap-only to a standing capability the vitality wake can drive.

---

## Canon grounding (so this amends, not reinvents)

- **ADR-318** already canonizes situation-scoped wakes ("a wake is a situation, not a task") — the offensive limb is an *amendment* (adds profit-seeking to the forward-reasoning examples), not a contradiction. ADR-318 keeps forward-reasoning *judgment-gated, not a checklist* — the dormancy posture inherits that (it fires "when the situation warrants," i.e. when the edge is *persistently* quiet, not on every flat day).
- **ADR-319 / DP24** admits ground-truth-driven revision but frames evidence around *decay* (reconciled outcomes going negative), not *dormancy* (outcomes never arriving). Treating persistent dormancy as falsification-of-the-premise ("this signal/universe remains viable" is falsified by sustained silence) is a **genuine extension** of DP24's evidence types — consistent with it, not named by it. This is the one real canonical move and belongs in an ADR.
- **agent-composition.md §3.2.1**: the *stance* (be agentic about dormancy) → frame; the *rules* (thresholds, aperture/floor split, which files widen) → principles.md. Respected by the layer split above.
- **No prior art**: no existing ADR covers a Reviewer dormancy/research/aperture loop. This is clean new ground → warrants its own ADR.

---

## Receipts index

| Claim | Receipt |
|---|---|
| Machine healthy; 16 organic RTH fires, 0 proposals | `execution_events` slug=signal-evaluation wake_source=cron_tick, Jun 8–17, all success, real output_tokens |
| Only executed trade is a fixture | `action_proposals` `0e4ed324` status=executed, decision_context.rationale prefixed `[FIXTURE]`, reviewer_identity=operator-proxy:…:acting-as-kvk |
| Frame posture present but examples defensive | `reviewer_agent.py:351-365` |
| Dormancy absent from canon | grep `dorman\|aperture` over bundle reference-workspace = 0 hits |
| Aperture gate unreachable when dormant | `persona/principles.md` near-miss-driven ≥10 wakes/5 days, no accumulator |
| Symmetry clause forbids the offensive move | `constitution/MANDATE.md` "signals do not fire and it proposes anyway" |
| No organ | `_recurrences.yaml` judgment slugs = {signal-evaluation, outcome-reconciliation}; `falsify-signals.md:113-116` bootstrap-only |
| Envelope already shows dormancy | `reviewer_envelope.py` loads recent_execution_md + calibration_md + operating_context_block + _money_truth.md every wake |

---

## Status

Diagnostic map complete (this doc). Trader-only prototype edits drafted next (frame limb wording + principles.md dormancy pattern + aperture/floor split + MANDATE softening + vitality recurrence) for operator read against live kvk substrate **before** any commit. The DP24-extension (dormancy-as-evidence) warrants a dedicated ADR before the kernel frame edit lands — that is the one cross-program canonical move and should not ride in on a bundle prototype.
