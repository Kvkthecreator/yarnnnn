# Falsify-Signals Spec

Schema for the per-signal research findings files written to
`/workspace/research/findings/{signal_id}.md`.

ADR-272: findings are now written by the **`morning-reflection`
recurrence's bootstrap precondition**, not a dedicated `falsify-signals`
recurrence (which was dissolved). The filename "falsify-signals.md"
remains as the schema reference for both the spec and the work it
describes. The work shape is unchanged; only the writer changed.

## Why this file exists

`_operator_profile.md` declares signals with target baselines marked
"(to establish)". The operator inherits those baselines from external
research, but the system has no first-cycle evidence to reason against.
The bootstrap precondition in `morning-reflection` walks 90 days of
historical bars through each declared signal and writes per-signal
findings the Reviewer reads at proposal time.

This is **bootstrap research substrate**, not ongoing money-truth.
Findings here carry `source: replay` in frontmatter — synthetic outcomes
against historical bars, not broker-confirmed fills. The Reviewer
weights these lower than real outcomes accumulated in
`/workspace/context/trading/_money_truth.md`, but they are better than
empty substrate for the first cycle.

## File format

One markdown file per signal at
`/workspace/research/findings/{signal_id}.md`. `signal_id` matches the
operator-declared signal slug (e.g. `signal-1-momentum-breakout`).

## Required frontmatter

```yaml
---
signal_id: signal-1-momentum-breakout
source: replay                              # NOT broker-confirmed; synthetic outcomes from historical bars
computed_at: 2026-05-13T22:05:00Z           # when the bootstrap precondition wrote this
lookback_days: 90                           # historical window walked
universe: [AAPL, MSFT, NVDA, SPY, TSLA]     # tickers walked (subset that returned data)

# Aggregate across all triggers
sample_size: 47                              # total triggered occurrences across universe
win_rate: 0.38                               # fraction with positive R-multiple
avg_win_R: 1.6                               # average R-multiple of winning trades
avg_loss_R: -1.0                             # average R-multiple of losing trades
expectancy_R: -0.013                         # win_rate * avg_win_R + (1 - win_rate) * avg_loss_R

# Compare to declared baseline (from _operator_profile.md)
declared_baseline:
  win_rate_min: 0.45
  avg_win_to_loss_ratio_min: 1.5
  sharpe_min: 0.8
baseline_status: below                      # below | within | above
---
```

## Body structure

```markdown
# {Signal display name} — Historical Falsification

## Summary

One paragraph: what the numbers say about whether the signal had edge
in the 90-day window. Quantitative, no narrative beyond what the numbers
support.

## Per-Ticker Breakdown

Table or list per ticker showing trigger count + win rate + expectancy.
Skip tickers with insufficient bar data; note them as `data-insufficient`.

## Notable Triggers

Sample of 3-5 representative triggered occurrences with entry / stop /
target / exit details. Pick a mix of wins and losses so the Reviewer
can see what triggered + how it resolved.

## Caveats

Honest list of fidelity gaps:
- No slippage model — fills are assumed at the bar high/low/close per
  order type.
- No spread cost.
- No survivorship-bias correction (universe is current; some tickers
  may not have traded the full lookback).
- No regime conditioning — falsification treats all triggers equally
  regardless of VIX state at the time.
```

## Quality criteria

- Every required frontmatter field populated; `null` not acceptable for
  the aggregate metrics
- `source: replay` MUST be present — the Reviewer's principles.md gate
  weights replay-source findings lower than live `_money_truth.md`
- `baseline_status` derived deterministically from the comparison; not
  a judgment call
- Numerical values are unquoted YAML numbers (R-multiples can be
  fractional, e.g. `1.6` not `"1.6"`)
- Body length: 300-800 words per signal. Quantitative frame only.

## What this is NOT

- **Not money-truth.** `/workspace/context/trading/_money_truth.md`
  is broker-confirmed outcomes from live (paper or real) trading.
  These findings are synthetic.
- **Not a permanent research function.** `falsify-signals` is a
  bootstrap recurrence (ADR-270) — fires once on activation, then only
  on explicit operator `FireInvocation`. If observation shows ongoing
  falsification matters, a future bundle revision adds a periodic
  schedule. The decision is earned by evidence, not authored
  pre-emptively.
- **Not Reviewer judgment.** The Reviewer reads these findings + live
  `_money_truth.md` at proposal time and weighs both per principles.md.
  Findings are evidence, not verdicts.
