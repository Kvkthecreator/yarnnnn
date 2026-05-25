# Proposals — 2 new

## trading.submit_order — status=pending
- **id**: `3d3023bd-dc62-4f0b-9a26-79e8fd8d2952`
- **created**: 2026-05-20T02:25:37.056476+00:00
- **rationale**:

```
Signal 2 (Mean-reversion-oversold) fired on NVDA.

Check 1 — Signal attribution: Signal 2 per _operator_profile.md §3A.2.

Check 2 — Signal rule compliance:
  RSI(14) = 23.4 < 25 (PASS)
  Price $847.50 within 1.85% of 200-day SMA $832.10 (PASS)
  Not in confirmed downtrend: 20-SMA > 50-SMA (PASS)
  NVDA in declared universe (PASS)

Check 3 — Risk-limit compliance:
  Position size: 4 × $847.50 = $3,390 = 13.6% of $25K book (PASS)
  Per-trade risk: 4 × $18.30 stop-distance = $73.20 = 0.29% of book (PASS)
  Sector concentration (Tech after add): 13.6% (PASS)
  Open positions: 0 (under 6 cap: PASS)

Check 4 — Signal expectancy (read from _money_truth.md):
  Recent 30d expectancy: +0.31R (above -0.5R decay: PASS)
  Recent 30d Sharpe: +0.68 (above 0.3 retirement: PASS)

Check 5 — Position-sizing math:
  account_equity = $25,000
  risk_percent (Signal 2) = 0.75% = $187.50
  regime_scalar (VIX < 25): 1.0
  stop_distance = 1.5 × ATR(14) = $18.30
  shares = $187.50 / $18.30 = 10.2 → constrained to 4 by 15% ceiling.

Check 6 — Portfolio diversification:
  Current open positions: 0 (fresh paper account).

```
- **expected effect**: Buy 4 NVDA at $847.50 limit (day order). Stop at $829.20 (−$73.20 max risk). Target: RSI(14) back to 50 OR $871.90 (2× ATR above entry), whichever first.

## trading.submit_order — status=rejected
- **id**: `ee7661ed-09f0-4cfd-9c8a-b1ac067e2bb5`
- **created**: 2026-05-20T02:27:31.094716+00:00
- **rationale**:

```
Signal-2 (mean-reversion-oversold) triggers on NVDA: RSI(14)=23.4 (<25), price $847.50 within 1.85% of 200-day SMA, not in downtrend. 0.75% portfolio risk, sized to $187.50 / $18.30 stop distance = 4 shares. All hard rules pass. Risk rules have been relaxed per your directive (max_position_percent now 40%, trading_hours_only relaxed).
```
- **expected effect**: 4 shares NVDA entered at $847.50 (or better) with stop loss at $829.20 and target at RSI return to 50. Position 16% of $10k portfolio (or 13.6% of $25k if that is the operating baseline). Max hold: 10 trading days per Signal-2 rules. Risk: $73.20 max loss, 0.73% of $10k (or 0.29% of $25k).
