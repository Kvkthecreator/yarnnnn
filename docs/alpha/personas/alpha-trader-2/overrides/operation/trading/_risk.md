# Risk parameters — alpha-trader-2

## Per-trade

- Per-pair risk target: 0.50% of current equity
- Position sizing formula: `equity × 0.005 / σ_spread_30d`
  (vol-targeted, NOT flat percentage of equity)
- No leverage beyond Alpaca paper defaults

## Portfolio level

- Max concurrent open pairs: 4 (across the 6-pair universe)
- Max var budget across all open pairs: 1.5% of equity
  (computed as sum of |position_dollars × σ_spread_30d| / equity)
- No two open pairs may share a leg (no AAPL in two pairs simultaneously)

## Daily / session

- Daily loss limit: 1.5% from session-start equity → flat all,
  no new entries until next session
- 3% drawdown from session high: halt for remainder of session
- 5R cumulative drawdown across all closed trades: halt strategy
  entirely pending operator review

## Time stops

- Hard time stop: 5 trading days per pair entry
- No overnight risk on session-end Friday: all pairs flat by 20:55 UTC
  Friday (5 minutes before close)

## Stop-loss (statistical)

- z > 3.5 (statistical breakdown): full pair close
- Pair leaves universe if 3 consecutive z > 3.5 stops in 60 days
  (cointegration is broken)

