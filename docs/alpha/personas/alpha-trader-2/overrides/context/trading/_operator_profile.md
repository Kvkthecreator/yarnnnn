# Operator Profile — alpha-trader-2 stat-arb pairs

> Hourly evaluation during RTH. Pair-based, not single-ticker.
> Each pair declares its cointegration evidence + entry/exit math.

## Universe

**Six declared cointegrated pairs**, selected for:
- Public cointegration history (academic + practitioner reference)
- High historical correlation (>0.70 60-day rolling)
- Liquid (both legs daily volume > 5M shares)
- Distinct sector logic (each pair is a different "story")

| Pair Slug | Leg A (long when z<0) | Leg B (short when z<0) | Sector logic |
|---|---|---|---|
| msft-aapl | MSFT | AAPL | Mega-cap tech duopoly |
| nvda-amd | NVDA | AMD | Semiconductor leadership |
| spy-qqq | SPY | QQQ | Broad market vs tech-heavy |
| xlk-xle | XLK | XLE | Tech sector vs energy sector (regime) |
| googl-meta | GOOGL | META | Digital ad-rev duopoly |
| gld-slv | GLD | SLV | Metals pair (low equity-correlation diversifier) |

The β coefficient (hedge ratio) for each pair is computed from a
rolling 60-day OLS regression of leg-A returns on leg-B returns.
β is recomputed daily by the track-universe task.

## Statistical signal: rolling z-score on spread

For each pair, every 1-Hour bar:

1. **Compute β** (hedge ratio):
   `β = OLS(returns_A ~ returns_B, window=60d)`
2. **Compute spread**: `s_t = price_A_t - β × price_B_t`
3. **Rolling stats over last 30 days** of hourly bars:
   - μ = mean(s_t over 30d)
   - σ = stdev(s_t over 30d)
4. **Z-score**: `z_t = (s_t - μ) / σ`

## Cointegration validation

A pair is **eligible** for trades only if:
- 60-day rolling correlation between leg returns > 0.70
- Augmented Dickey-Fuller (ADF) test on 90-day spread series
  has p-value < 0.10 (mean-reverting at 90% confidence)
- No "structural break" detected in last 30 days (no day where
  |spread - prior spread| > 5σ)

If any of the above fails for a pair, that pair is FLAGGED in its
state file (state: `flagged`) and trade-proposal will not fire for
it until quarterly-signal-audit re-validates or operator manually
unflags.

## Entry conditions (all must hold)

- Pair is `state: active` (cointegration validation passed)
- |z_current| > 2.0
- Pair has no currently-open position in alpaca paper
- Aggregate open-pair var budget across portfolio ≤ 1.5%
- Daily loss tracker < 1.5% session loss
- Time is during RTH (13:30-21:00 UTC)

## Trade direction

- z > +2.0 → spread is unusually wide (A overvalued relative to B):
  - **SHORT leg A** (short shares of A)
  - **LONG leg B** (β × position_dollars / price_B shares)
- z < -2.0 → spread is unusually narrow (A undervalued relative to B):
  - **LONG leg A** (position_dollars / price_A shares)
  - **SHORT leg B** (β × position_dollars / price_B shares)

## Sizing (mechanical, no override)

```
position_dollars = current_equity × 0.005 / σ_spread_30d
shares_A = round(position_dollars / price_A)
shares_B = round((position_dollars × β) / price_B)
```

The 0.5% target is per *pair*, not per leg. Both legs together
constitute one bet on the spread reversion.

## Exit conditions (any one triggers full pair close)

1. **Take profit (mean reversion)**: |z_current| < 0.5
2. **Stop loss (statistical breakdown)**: |z_current| > 3.5
3. **Time stop**: 5 trading days since entry
4. **Daily session stop**: workspace daily loss > 1.5% → flat all pairs

## Decay & retirement

Per pair, evaluate quarterly via quarterly-signal-audit task:
- 20-trade expectancy_R over last 20 closed trades
- Win rate over last 20 closed trades
- Statistical breakdown rate (% of trades hitting z > 3.5 stop)

Retire-flag thresholds (any one triggers `state: flagged`):
- 20-trade expectancy < +0.0R (no edge)
- Win rate < 50%
- Stop-out rate (z > 3.5 hits) > 25%

A flagged pair stops trading until operator review or auto-recovery
(next quarterly audit shows recovery to thresholds).

## Pair state files

Each pair has a state file at:
`/workspace/context/trading/pairs/{slug}.md`

Frontmatter shape:
```yaml
pair_slug: msft-aapl
leg_a: MSFT
leg_b: AAPL
state: active|flagged|retired
beta_60d: 1.0234
spread_mu_30d: 5.21
spread_sigma_30d: 1.83
z_current: -0.45
correlation_60d: 0.87
adf_pvalue_90d: 0.03
last_updated: 2026-04-28T15:00:00Z
trade_count_lifetime: 0
expectancy_r_20: null
win_rate_20: null
stop_rate_20: null
decay_flagged: false
```

