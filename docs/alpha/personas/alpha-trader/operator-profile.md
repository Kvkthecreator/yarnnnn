# Operator Profile — alpha-trader (5 declared signals)

> **Purpose**: seed content for `/workspace/context/trading/_operator_profile.md` in the alpha-trader workspace. Pasted verbatim via `UpdateContext(target="context", domain="trading")` during E2E setup.
> **Framing**: declared, mechanical signals with explicit entry/exit/sizing rules + per-signal expectancy tracking. Option B scope per ALPHA-1-PLAYBOOK §3A: 5–8 signals, full entry/exit rules, not lighter (rule-following discretion), not heavier (mini-Medallion).

---

## Operator identity (trading context)

Systematic paper trader exercising mechanical rule-following on a $25,000 Alpaca paper account. Universe: 12–15 liquid US equities + 2 sector ETFs. Hold periods: 1–20 trading days typical. No intra-day scalping, no quarterly theses. Every trade has a declared signal; no discretionary setups.

**Declared edge**: sustained mechanical application of five declared signals with quarterly retire-flag audits. Not prediction; not insight; **rule-following + expectancy measurement**.

---

## Signal 1 — Momentum breakout (trend-following, long-only)

**Entry conditions (all must pass)**:
- Price closes above 50-day high
- 50-day SMA > 200-day SMA (confirmed uptrend)
- 20-day ADX ≥ 25 (trending, not choppy)
- Daily volume ≥ 1.5× 20-day average (volume confirmation)
- Universe filter: stock is in current universe AND market cap > $5B

**Exit conditions (first to trigger)**:
- Stop: price drops below 20-day low (trailing, updated daily)
- Target: 2R profit (from entry minus initial stop distance)
- Time stop: 20 trading days — exit regardless of price

**Sizing**:
- `risk_percent: 0.010` (1% of account per trade)
- `stop_distance: entry_price − 20_day_low_at_entry`
- Scaled by regime_scalar from Signal 5

**Retire flag**: rolling 20-trade expectancy below **-0.3R** for two consecutive quarters.

**Current typical expectancy**: +0.4R to +0.8R in trending regimes, -0.3R in choppy/mean-reverting regimes. Regime-dependent by design.

---

## Signal 2 — Oversold bounce (mean-reversion, long-only)

**Entry conditions (all must pass)**:
- RSI(14) < 25 (oversold)
- Price within 5% of 200-day SMA (long-term support zone)
- NOT in confirmed downtrend (50-day SMA > 200-day SMA OR the 50-day has not crossed below for at least 10 trading days)
- Universe filter: stock is in current universe AND has historical mean-reversion character (checked: S&P 500 constituent for 2+ years)

**Exit conditions (first to trigger)**:
- Stop: 1.5 × ATR(14) below entry
- Target: 1R profit (mean-reversion bounces are modest)
- Time stop: 5 trading days — if no bounce within 5 days, exit flat/loss

**Sizing**:
- `risk_percent: 0.0075` (0.75% of account)
- `stop_distance: 1.5 × ATR(14)`
- Scaled by regime_scalar

**Retire flag**: rolling 20-trade expectancy below **-0.5R** for one quarter.

**Current typical expectancy**: +0.3R in low-VIX regimes, -0.2R in high-VIX regimes.

---

## Signal 3 — 52-week high pullback (continuation, long-only)

**Entry conditions (all must pass)**:
- Stock made 52-week high within last 20 trading days
- Current price pulled back 5–15% from that high
- 50-day SMA > 200-day SMA (uptrend intact)
- RSI(14) between 40 and 60 (neither overbought nor oversold; healthy pullback)
- Universe filter: stock is in current universe

**Exit conditions**:
- Stop: 10% below entry (fixed)
- Target: price returns to within 2% of prior 52-week high
- Time stop: 15 trading days

**Sizing**:
- `risk_percent: 0.010`
- `stop_distance: 0.10 × entry_price`
- Scaled by regime_scalar

**Retire flag**: rolling 20-trade expectancy below **-0.4R** for two consecutive quarters.

**Current typical expectancy**: +0.5R in strong bull regimes; -0.2R in market corrections.

---

## Signal 4 — Sector-ETF rotation (long-only)

**Entry conditions (all must pass)**:
- Sector ETF relative strength vs SPY is in the top 2 of 11 sectors over trailing 20 trading days
- Sector ETF's 50-day SMA > 200-day SMA (sector uptrend)
- Market regime NOT flagged as defensive (VIX < 25 per Signal 5)

**Exit conditions**:
- Stop: 8% below entry (sector ETFs are less volatile than single stocks)
- Target: sector relative strength drops out of top 4
- Time stop: 30 trading days

**Sizing**:
- `risk_percent: 0.0075`
- `stop_distance: 0.08 × entry_price`
- Scaled by regime_scalar

**Retire flag**: rolling 20-trade expectancy below **-0.3R** for two consecutive quarters.

**Current typical expectancy**: +0.4R in normal regimes; -0.1R during regime transitions.

---

## Signal 5 — Regime scalar (sizing modifier, not an entry signal)

**Regime detection**:
- VIX < 15: "low-vol" regime, regime_scalar = 1.0 (full sizing)
- VIX 15–25: "normal" regime, regime_scalar = 1.0
- VIX 25–35: "elevated" regime, regime_scalar = 0.5 (half sizing on all new positions)
- VIX > 35: "crisis" regime, regime_scalar = 0.0 (no new positions; existing positions trailed tight or closed)

**Drawdown overlay** (applied in addition to VIX scalar):
- Account drawdown from peak < 5%: no additional scalar adjustment
- Drawdown 5–10%: multiply regime_scalar by 0.5 (half sizing again)
- Drawdown > 10%: regime_scalar = 0.0 (no new positions until drawdown recovers below 5%)

**This is a mechanical volatility + drawdown filter, not a prediction.** The operator does not override it ("VIX is high but this signal feels strong"). Signal 5 fires automatically; the Reviewer verifies its current state against every proposal.

**Retire flag**: Signal 5 is infrastructure. It is audited but not retirable — if the regime detection itself fails to protect drawdown, the operator updates thresholds, not retires the signal.

---

## Universe (current, 12–15 names)

Large-cap liquid US equities + 2 sector ETFs:

| Ticker | Name | Sector | Market cap |
|---|---|---|---|
| AAPL | Apple | Technology | $3T |
| MSFT | Microsoft | Technology | $3T |
| GOOGL | Alphabet | Technology | $2T |
| AMZN | Amazon | Consumer discretionary | $2T |
| META | Meta Platforms | Communication | $1.5T |
| NVDA | NVIDIA | Technology | $3T |
| JPM | JPMorgan | Financials | $600B |
| JNJ | Johnson & Johnson | Healthcare | $400B |
| XOM | Exxon Mobil | Energy | $500B |
| V | Visa | Financials | $550B |
| UNH | UnitedHealth | Healthcare | $500B |
| HD | Home Depot | Consumer discretionary | $400B |
| XLK | Technology Select Sector SPDR | Sector ETF | — |
| XLF | Financial Select Sector SPDR | Sector ETF | — |

Universe refreshes at quarterly signal audit. Adds: market cap > $100B, liquidity > 5M avg daily volume, 3+ years public. Removes: material corporate event (M&A, spin-off) that invalidates historical signal behavior.

---

## Quarterly audit cadence

Every 90 calendar days, operator runs:

1. Per-signal rolling 20-trade expectancy check against retire-flag thresholds above.
2. Regime scalar calibration: compare actual drawdown vs. declared-threshold drawdowns; recalibrate if reality diverges.
3. Universe refresh.
4. Reviewer calibration review: compare AI-occupant verdicts vs retrospective human-occupant judgment from `/workspace/review/calibration.md`; adjust `modes.md` autonomy thresholds.

Audit produces one of: no action (signals performing within tolerance), retire a signal (expectancy below threshold for two quarters), recalibrate regime scalar (drawdown data diverged), or operator edits to this file + `_risk.md`.
