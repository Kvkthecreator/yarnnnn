# Risk Rules — alpha-trader (portfolio-level floors)

> **Purpose**: seed content for `/workspace/context/trading/_risk.md` in the alpha-trader workspace. Pasted verbatim via `UpdateContext(target="context", domain="trading")` during E2E setup.
> **Framing**: hard floors the Reviewer enforces on every proposal. These are NOT guidelines — the Reviewer rejects any proposal that would breach any limit when combined with current positions. Floors below; capital-EV (per `reviewer-principles.md`) sets the ceiling.

---

## Account state

- **Starting capital**: $25,000 (Alpaca paper account)
- **Phase**: ALPHA-1 paper-only (no live trading until playbook ledger records explicit phase transition)
- **Universe**: per `_operator_profile.md` (12–15 liquid US equities + 2 sector ETFs)

---

## Portfolio-level limits (hard floors)

### Gross + net exposure

- **Max gross exposure**: 100% of account equity. Paper account is long-only in ALPHA-1; no short sleeves during paper phase.
- **Max net long exposure**: 100% of account equity.
- **Cash floor**: minimum 5% of account equity held as cash (reserve for margin buffer + ability to act on Signal 1 entries without forced position liquidation).

### Per-position limits

- **Max single-position exposure**: 15% of account equity. If a proposal would push a single name above 15%, reject. This applies to the cumulative exposure after the proposed trade, not just the new trade.
- **Max shares per order**: calculated via sizing formula in `_operator_profile.md`. Never override.

### Sector concentration

- **Max single-sector exposure**: 35% of account equity. If portfolio currently has 30% in Technology (AAPL + MSFT + NVDA) and a new Signal 1 proposal would add GOOGL bringing Tech to 38%, reject.
- **Sector mapping**: per GICS sector classification in universe table.

### Daily loss limits

- **Daily loss limit**: 3% of account equity. If realized + unrealized losses for the day exceed -$750 (3% of $25K), stop new entries for the rest of the day. Existing positions stay open (their stops manage them).
- **Weekly loss limit**: 6% of account equity. If week-to-date realized + unrealized losses exceed -$1,500, halt new entries for the remainder of the week.

### Drawdown guardrails

- **Drawdown 5–10%**: Signal 5 regime scalar halves per-trade sizing. Reviewer verifies.
- **Drawdown > 10%**: Signal 5 regime scalar → 0. **No new positions** regardless of signal fire. Reviewer rejects any new-entry proposal until drawdown recovers below 5%.
- **Drawdown > 20%**: mandatory phase review. Operator revisits operator-profile declarations, risk thresholds, and whether ALPHA-1 paper has produced sufficient evidence to phase-transition OR de-escalate.

---

## Per-signal risk limits

These complement (don't replace) per-signal `risk_percent` in `_operator_profile.md`:

### Signal 1 (Momentum breakout)

- Max concurrent positions: 4 (higher — momentum signals tend to cluster sector-wise, so limit count not dollar)
- Max cumulative exposure: 40% of account equity
- `risk_percent`: 1.0% per trade (declared in operator-profile)

### Signal 2 (Oversold bounce)

- Max concurrent positions: 2 (mean-reversion is smaller-R, higher-frequency — don't over-stack)
- Max cumulative exposure: 15% of account equity
- `risk_percent`: 0.75% per trade
- **Never at same time**: two oversold-bounce positions in the same sector (correlation risk during sector-wide selloffs)

### Signal 3 (52-week high pullback)

- Max concurrent positions: 3
- Max cumulative exposure: 30% of account equity
- `risk_percent`: 1.0% per trade

### Signal 4 (Sector-ETF rotation)

- Max concurrent positions: 2 (top 2 sectors only per operator-profile)
- Max cumulative exposure: 30% of account equity (ETFs are less risk-per-dollar than single names)
- `risk_percent`: 0.75% per trade

### Signal 5

No per-signal limits — Signal 5 is a sizing modifier on other signals.

---

## Action-class restrictions (Reviewer `never_auto_approve` mapping)

The Reviewer seat's `modes.md` declares these fragments as never-auto-approvable. They always route to the human occupant:

- `submit_order_live` — any non-paper order
- `submit_bracket_order_live` — same
- `submit_trailing_stop_live` — same
- `close_all_positions` — the portfolio kill switch
- `modify_stop_below_entry` — any move of a stop *deeper* into loss territory (only move stops up, never down)
- `cancel_open_stop_without_replacement` — never leave a position unprotected
- `pyramid_entry_without_stop_update` — adding to winning position without moving the stop up first

The rest (paper submits within sizing formula, stops moved up per trailing rules, target-hit exits) may be auto-approved by the AI occupant if `modes.md` autonomy_level permits and the sizing is within auto_approve_below_cents (currently $0 during early E2E — every trade is human-reviewed).

---

## High-impact threshold (routes outcomes to task feedback)

Per ADR-195 Phase 5 + reviewer-principles.md:

```yaml
trading:
  high_impact_threshold_cents: 50000    # realized P&L ≥ $500 routes to task feedback.md
```

$500 realized P&L on a $25K account = 2% single-trade outcome. Material enough that the originating task should see the feedback (win or loss) and the Reviewer's next-cycle calibration should account for it.

---

## Circuit breakers

These trigger notifications but not auto-action — operator decides:

- **Position down 5% in single session**: notify. Operator reviews whether stop was correctly set or whether an unexpected event requires manual action.
- **Three consecutive losing trades on the same signal**: notify. Early expectancy-decay warning; operator checks next `_performance.md` rebuild.
- **VIX > 35 (crisis regime)**: notify. Signal 5 has already zeroed the regime scalar; operator decides whether to close winning positions to cash or trail stops tight.
- **Correlated drawdown**: two or more open positions lose ≥3% each in the same session. Notify. Tests whether sector concentration limits were respected.

---

## Audit trail

Every Reviewer decision writes to `/workspace/review/decisions.md` with:
- Proposal ID
- Signal attribution (which signal the proposal named)
- Mechanical-rule evaluation (which checks passed/failed with exact numbers)
- Sizing-formula output
- Reviewer verdict (approve / reject / defer)
- Reviewer reasoning (2–5 sentences, capital-EV framed)
- Occupant identity (human:<user_id> | ai:<model>)

Every reconciled outcome writes to `/workspace/context/trading/_performance.md` per ADR-195.

Cross-reference lives in `/workspace/review/calibration.md` (auto-generated per ADR-211 D6 by back-office-reviewer-calibration task): per-occupant × verdict × outcome aggregates over rolling 7d/30d/90d windows.

---

## Revision protocol

Revised by the operator at quarterly audit OR under material events (phase transition, drawdown > 20%, universe refresh, regime scalar miscalibration). Revisions are authored by the operator via `UpdateContext(target="context", domain="trading")` which overwrites this file wholesale. Prior revisions persist in the Authored Substrate revision chain (ADR-209).

The Reviewer reads this file at every verdict rendering. Changes take effect on the next proposal.
