# Autonomy — alpha-trader

> Per ADR-254: **machine-parsed delegation config lives in `_autonomy.yaml` (sibling file)**. This file is prose documentation for human and LLM reading. Edit `_autonomy.yaml` to change delegation ceilings.

## What autonomy controls

**Autonomy is the witness dial, not a ceiling on the agent (ADR-345).** Your Reviewer always works the full job — it is a judgment seat acting in your absence, not an assistant waiting for permission to start. This dial does not decide *whether* it works; it decides **which consequential beats you witness before they bind**. `autonomous` = the whole operation runs subconsciously (you read the trail — `judgment_log.md`, `standing_intent.md` — at your leisure); `bounded`/`manual` = the beats you choose surface to your Queue first. An order that routes to your Queue is the Reviewer having *decided* and *waiting for you to witness it* — never the Reviewer being *blocked from working*.

`_autonomy.yaml` declares which beats surface: how much the Reviewer's approve verdict binds automatically vs. routes to your Queue for a click.

**Levels (canonical 3-value enum per ADR-261 D5):**
- `manual` — every order surfaces for your click, regardless of Reviewer verdict
- `bounded` — Reviewer auto-executes within `ceiling_cents`; defers above
- `autonomous` — Reviewer auto-executes all approvals within scope

**`ceiling_cents`** — the *notional* threshold for `bounded`. Orders whose dollar value exceeds this surface to the Queue regardless of approve verdict.

**`never_auto`** — action types that always route to Queue regardless of level. Hard safety list. Note: `never_auto` overrides `autonomous` — e.g., with `delegation: autonomous` and `never_auto: [close_position_market]`, stop-hit close proposals still route to the Queue. This is by design for paper-mode safety; tune `never_auto` once Phase 2+ live-account confidence is established.

## Current posture (operator-authored 2026-05-13 iter-4)

**`delegation: autonomous`**, **`ceiling_cents: 5000000` ($50,000)**, `never_auto: [close_position_market, cancel_other_orders]`.

The operator explicitly elected full autonomous execution from first signal fire rather than the Phase-0 paper-seed posture documented as the bundle default below. Reasoning: paper account, hard caps in `_risk.md` (max_position_size_usd: 1000, max_daily_loss_usd: 200, max_order_size_shares: 100, trading_hours_only), and risk_gate.py enforces these before any order fires. The goal is to observe a real autonomous closed-loop cycle (Reviewer reasons over substrate → dispatches specialist for bars → signal evaluates → trade-proposal emits → Reviewer judges → broker fires) without operator click in the path, while the hard caps prevent runaway exposure.

**What "autonomous" means here**:
- Every Reviewer approve verdict binds — order fires at Alpaca within the same dispatch loop.
- `ceiling_cents: 5000000` ($50k) is the notional safety net. Signal-1 sized positions (~$12.5k notional on a $25k paper account) fit comfortably below; larger positions would surface to the Queue.
- `never_auto: [close_position_market, cancel_other_orders]` still surfaces those specific actions to the Queue regardless of approve verdict. Stop-hit closes are mandatory per principles.md `Hard exit triggers` but the operator explicitly clicks them.

## The honest math: ceiling vs. position notional

`ceiling_cents` is checked against the order's **notional value** (`shares × price`), not its risk-dollar (the loss-if-stop-hits amount).

For the operator's signal sizing math (`account × risk_percent / stop_distance`), the notional is `risk_percent × account / (stop_distance / price)`. On the paper-seed default ($25k account, 1% risk, 2% stop), notional ≈ `$250 / 2% = $12,500` per Signal-1 position — well under the $50k ceiling.

## Phase progression (reference)

The bundle's documented phase progression, preserved here as historical reference even though the operator has elected to skip directly into Phase 1-equivalent posture. Returning to `bounded @ small ceiling` is one-line YAML edit; if the autonomous posture surfaces a class of error this section's caution describes, revert by editing `_autonomy.yaml`.

- **Phase 0 — Paper-seed (bundle default)**: `bounded` at `ceiling_cents: 20000` ($200). Every signal-sized position queues for operator click. Reviewer's approve verdict is visible but advisory. The loop runs end-to-end without large autonomous exposure. Stay here until you've watched ~10 closed-loop cycles and trust the Reviewer's reasoning shape.
- **Phase 1 — Calibrated paper**: raise `ceiling_cents` to admit Signal-1 notional. Reviewer's approve verdict now binds for paper-account entries within sizing rules. Stay here until your `_money_truth.md` shows positive expectancy across at least 20 closed paper trades for at least one signal.
- **Phase 2 — Live float**: tighten back to `manual` the moment you switch to a live account. Live execution requires explicit operator click for every order until you've calibrated against live (not paper) outcomes for 30+ trades.
- **Phase 3 — Calibrated live**: re-raise ceiling per the live `_money_truth.md` calibration. The morning-calibration recurrence is your guardrail.

## Reviewer-written pause (ADR-248 D3)

The Reviewer's periodic reflection can write `paused_until` and `pause_reason` into `_autonomy.yaml` when it detects structural drift. While set, all proposals queue for your click regardless of level. Expires automatically at the timestamp. You can remove it via chat at any time.

## What AUTONOMY does NOT control

- Reviewer's evaluation framework (principles.md + _principles.yaml)
- Risk rules (_risk.md)
- Operator strategy and persona (MANDATE.md, IDENTITY.md, _operator_profile.md)
- **Whether a recurrence wakes the Reviewer** — that's the recurrence's `mode` field per ADR-263 (`judgment` | `mechanical`), declared at authoring time in `_recurrences.yaml`.
