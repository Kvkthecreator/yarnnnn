# Proposals — 1 new

## trading.submit_order — status=pending
- **id**: `2a666593-c4e7-4343-8dfb-260cd39c801c`
- **created**: 2026-05-20T01:14:35.923559+00:00
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
