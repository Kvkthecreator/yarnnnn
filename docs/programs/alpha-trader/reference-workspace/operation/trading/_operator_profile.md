# Operator profile — Alpha Trader (Simons, Option B)

## Declared strategy
Systematic equity trading across 5–8 measurable signals. Universe
limited to liquid, high-quality US equities + index proxies.
No options, no crypto, no leverage beyond 1.0x.

## Declared universe
Primary: AAPL, MSFT, GOOGL, NVDA, AMD, META, TSLA, AMZN,
         SMH, SOXX, QQQ, SPY, XLK, XLY, IWM
(Candidates to add/rotate via quarterly signal audit. Not a
trading wishlist — these are the instruments signals operate on.)

## Declared signals (initial set; evolves via quarterly audit)

> **Perception-field discipline (ADR-354).** A signal's trigger may reference
> ONLY fields the perception field actually emits. The `track-universe` mirror
> writes per-ticker snapshots with exactly: `price`, `sma_20`, `sma_50`,
> `sma_200`, `rsi_14`, `atr_14`, `volume_20d_avg` (schema:
> operation/specs/ticker-snapshot.md), and `_regime.yaml` carries the VIX
> regime state. A trigger that names a field outside that set cannot be
> evaluated — it is not "pending data," it is structurally unfireable until
> the perception field is extended to emit the field. Signals 3 and 4 below
> are marked DORMANT for exactly this reason: their feeds do not yet exist.

### Signal 1: Momentum-breakout
- **Trigger:** price > sma_20 + price > sma_50 + RSI(14) between 55–75 + volume_20d_avg ≥ liquidity floor
- **Rationale:** price above both the 20d and 50d SMA in a 55–75 RSI band is the momentum-breakout state the original "20-day high + volume surge" formulation selected for, expressed in fields the perception field emits. Current-bar volume is not emitted, so liquidity is enforced by the 20d-average floor rather than a single-bar surge. (Per ADR-354: the trigger keys only on emitted fields; the breakout intent lives in this rationale, not in an unevaluable field name.)
- **Entry:** next-day open or on-trigger-day close (configurable)
- **Stop-loss:** 2× ATR(14) below entry
- **Target:** 3× ATR(14) above entry OR trailing stop at 1.5× ATR(14) after +2× ATR
- **Position sizing:** 1% portfolio risk (position_size = account_size × 0.01 / stop_distance)
- **Max hold:** 20 trading days; force-exit on day 21 regardless of state
- **Historical baseline (to establish):** target win rate ≥45%, avg win ≥1.5× avg loss, Sharpe ≥0.8

### Signal 2: Mean-reversion-oversold
- **Trigger:** RSI(14) < 25 + price within 5% of 200-day SMA (quality filter) + not in confirmed downtrend (20-day SMA above 50-day SMA)
- **Entry:** next-day open
- **Stop-loss:** 1.5× ATR(14) below entry
- **Target:** RSI returns to 50 OR 2× ATR(14) above entry, whichever first
- **Position sizing:** 0.75% portfolio risk (smaller — mean-reversion has lower expectancy than trend)
- **Max hold:** 10 trading days
- **Historical baseline (to establish):** target win rate ≥55%, avg win ~equal to avg loss, Sharpe ≥0.6

### Signal 3: Post-earnings drift (PEAD) — DORMANT (perception feed absent)
> **DORMANT until an earnings feed is added to the perception field.** This
> trigger needs `earnings_surprise` + `price_gap` fields that `track-universe`
> does not emit. Per ADR-354 this is a STRUCTURAL gap, not "pending data" — do
> not evaluate it every wake expecting it to fire. To activate: extend the
> perception field to emit earnings data, then un-mark this signal.
- **Trigger:** earnings surprise >5% + price gap >3% in surprise direction + hold universe match
- **Entry:** day+1 after earnings at open
- **Stop-loss:** 2× ATR(14) against entry direction
- **Target:** 10-day hold OR 3× ATR(14) profit, whichever first
- **Position sizing:** 1% portfolio risk
- **Max hold:** 10 trading days
- **Historical baseline (to establish):** target win rate ≥50%, asymmetric payoff (avg win ≥1.75× avg loss)

### Signal 4: Sector-rotation-momentum — DORMANT (perception feed absent)
> **DORMANT until a cross-ticker relative-strength feed is added.** This
> trigger needs a `relative_strength_rank` across a 9-sector set that
> `track-universe` (per-ticker, no cross-ticker ranking) does not emit. Per
> ADR-354 this is a STRUCTURAL gap. To activate: add a sector-RS computation
> to the perception field, then un-mark. (The "momentum state per Signal 1
> rules" sub-clause IS evaluable once Signal 1 keys on emitted fields; the
> RS-rank gate is the missing piece.)
- **Trigger:** ETF (SMH/XLK/XLY/XLF) relative-strength rank in top 2 of 9 sectors over 20-day window + sector ETF itself in momentum state per Signal 1 rules
- **Entry:** on ETF (not individual stock)
- **Stop-loss:** 2× ATR(14) below entry
- **Target:** trailing stop at 1.5× ATR after +2× ATR
- **Position sizing:** 1.5% portfolio risk (ETF = lower idiosyncratic; slightly larger sizing)
- **Max hold:** 30 trading days
- **Historical baseline:** Sharpe ≥0.7

### Signal 5: Volatility-regime filter (not a trade signal — a portfolio state)
- **Purpose:** reduce sizing across all signals when VIX > 25 AND VIX > 20-day VIX SMA
- **Action:** multiply all signal position_size by 0.5 while regime is active
- **Deactivation:** VIX < 20 for 5 consecutive days
- **Not a signal that generates trades — a global scalar applied in risk sizing.**

(Signals 6–8 reserved — added through quarterly audits as research identifies candidates. Do not add ad-hoc during Alpha-1.)

## Declared edge
Discipline in signal execution, position-sizing math, and signal
retirement. Not in prediction quality. My edge compounds through:
- Consistent sizing (never over-weighting a "high-conviction" trade)
- Diversification across uncorrelated signals
- Retiring signals that decay (don't hope them back to life)
- Never overriding the model

## Success criteria — year-over-year
- Net Sharpe ≥ 1.0 across portfolio
- Max drawdown ≤ 15%
- Per-signal Sharpe within 1.5x of declared baseline (signals
  performing roughly as expected in their regime)
- Zero trades without signal attribution
- At least one quarterly audit per quarter (operator discipline)

## What I'm NOT trying to do
- Not trying to match pro quants on return
- Not trying to beat the index on any single quarter
- Not trying to call market tops or bottoms
- Not trying to swing-trade narrative plays
- Not trying to hold long-term (this is not a buy-and-hold book)
