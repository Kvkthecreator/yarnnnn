# Weekly Performance Review Spec

Spec for the weekly `weekly-performance-review` recurrence. The Reviewer
reads this spec when producing the report at 18:00 ET on Sundays.

## Purpose

Sunday-night planning surface for the operator. Compute per-signal P&L,
win rate, expectancy, and Sharpe; flag any signal whose decay guardrail
was crossed; surface candidates for the quarterly audit retirement list.

## Output target

`/workspace/operation/reports/weekly-performance-review/{date}/output.md`

## Required sections (in order)

### 1. `## Portfolio Totals`
- Week's net P&L (USD) with comparison to prior week + 4-week average.
- Total fills this week.
- Open positions at week end (count + dollar exposure).
- Cash on margin.

### 2. `## Per-Signal Attribution`
- One sub-section per active signal (IH-1 through IH-5).
- Format per signal:
  ```
  ### IH-N — {signal_name}
  - Fills this week: {n}
  - Realized P&L this week: {usd}
  - Win rate this week: {pct} (vs declared baseline {baseline_pct})
  - Expectancy-20: {usd} | Expectancy-40: {usd}
  - Sharpe-lifetime: {value} (vs declared baseline {baseline_value})
  - Decay assessment: {within tolerance | watch | guardrail crossed}
  ```

### 3. `## Decay Flags`
- Each signal whose 40-trade Sharpe is approaching or has crossed the
  retirement guardrail in `_risk.md`.
- Quantitative reasoning: the metric, the threshold, the gap.
- Empty section ("No decay flags this week.") when none.

### 4. `## Regime History`
- This week's regime changes (date + VIX bucket transition + trend
  regime transition).
- Comment on whether any signal underperformed in a specific regime.

### 5. `## Quarterly-Audit Flags`
- Signals that deserve discussion at the next quarterly audit (whether
  for retirement, retune, or just close monitoring).
- One bullet per flag: `**IH-N**: {reason} ({metric vs baseline})`.

## Quality criteria

- Per-signal expectancy-20, expectancy-40, Sharpe-lifetime ALL surfaced
  for every active signal — no skipping signals that "didn't fire much."
- Signals flagged for decay are listed in BOTH section 2 (per-signal
  detail) AND section 3 (decay-flag callout).
- Reference `/workspace/operation/trading/_money_truth.md` as the single
  numerical source. Do not recompute from raw fills.
- Length: ~1,200–2,000 words.
- Section partials in
  `/workspace/operation/reports/weekly-performance-review/{date}/sections/`:
  `1-portfolio-totals.md`, `2-per-signal-attribution.md`,
  `3-decay-flags.md`, `4-regime-history.md`,
  `5-quarterly-audit-flags.md`.
