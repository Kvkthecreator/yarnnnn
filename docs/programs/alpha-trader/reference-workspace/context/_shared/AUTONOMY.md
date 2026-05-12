# Autonomy — alpha-trader

> Per ADR-254: **machine-parsed delegation config lives in `_autonomy.yaml` (sibling file)**. This file is prose documentation for human and LLM reading. Edit `_autonomy.yaml` to change delegation ceilings.

## What autonomy controls

`_autonomy.yaml` declares the delegation ceiling: how much the Reviewer's approve verdict binds automatically vs. routes to your Queue for a click.

**Levels (canonical 3-value enum per ADR-261 D5):**
- `manual` — every order surfaces for your click, regardless of Reviewer verdict
- `bounded` — Reviewer auto-executes within `ceiling_cents`; defers above
- `autonomous` — Reviewer auto-executes all approvals within scope

**`ceiling_cents`** — the *notional* threshold for `bounded`. Orders whose dollar value exceeds this surface to the Queue regardless of approve verdict.

**`never_auto`** — action types that always route to Queue regardless of level. Hard safety list. Note: `never_auto` overrides `autonomous` — e.g., with `delegation: autonomous` and `never_auto: [close_position_market]`, stop-hit close proposals still route to the Queue. This is by design for paper-mode safety; tune `never_auto` once Phase 2+ live-account confidence is established.

## The honest math: ceiling vs. position notional

`ceiling_cents` is checked against the order's **notional value** (`shares × price`), not its risk-dollar (the loss-if-stop-hits amount).

For the operator's signal sizing math (`account × risk_percent / stop_distance`), the notional is `risk_percent × account / (stop_distance / price)`. On the paper-seed default ($25k account, 1% risk, 2% stop), notional ≈ `$250 / 2% = $12,500` per Signal-1 position — far above the $200 ceiling.

**This is by design at Phase 0.** With `ceiling_cents: 20000` ($200), every signal-fired entry queues for operator click. The Reviewer's approve verdict is rendered (visible in the Queue), but execution waits on you. This is the deliberate paper-seed posture: the loop runs, the Reviewer judges, you observe-and-confirm before any capital moves. As you accumulate confidence in the Reviewer's calibration, raise the ceiling to admit larger notional.

## Phase progression

- **Phase 0 — Paper-seed (default)**: `bounded` at `ceiling_cents: 20000` ($200). **Every signal-sized position exceeds this — queues to Queue by design.** Reviewer's approve verdict is visible but advisory; you click before execution. The loop runs end-to-end (signal → Reviewer judgment → Queue → your click → broker → reconciliation) without large autonomous exposure. Stay here until you've watched ~10 closed-loop cycles and trust the Reviewer's reasoning shape.
- **Phase 1 — Calibrated paper**: raise `ceiling_cents` to admit Signal-1 notional (e.g., `1500000` = $15,000). Reviewer's approve verdict now binds for paper-account entries within sizing rules. Queue still receives anything above the new ceiling. Stay here until your `_performance.md` shows positive expectancy across at least 20 closed paper trades for at least one signal.
- **Phase 2 — Live float**: tighten back to `manual` the moment you switch to a live account. Live execution requires explicit operator click for every order until you've calibrated against live (not paper) outcomes for 30+ trades.
- **Phase 3 — Calibrated live**: re-raise ceiling per the live `_performance.md` calibration. The morning-calibration recurrence is your guardrail; raise only when it consistently shows no material divergence between declared and realized expectancy.

## Reviewer-written pause (ADR-248 D3)

The Reviewer's periodic reflection can write `paused_until` and `pause_reason` into `_autonomy.yaml` when it detects structural drift. While set, all proposals queue for your click regardless of level. Expires automatically at the timestamp. You can remove it via chat at any time.

## What AUTONOMY does NOT control

- Reviewer's evaluation framework (principles.md + _principles.yaml)
- Risk rules (_risk.md)
- Operator strategy and persona (MANDATE.md, IDENTITY.md, _operator_profile.md)
- **Whether a recurrence wakes the Reviewer** — that's the recurrence's `mode` field per ADR-263 (`judgment` | `mechanical`), declared at authoring time in `_recurrences.yaml`.
