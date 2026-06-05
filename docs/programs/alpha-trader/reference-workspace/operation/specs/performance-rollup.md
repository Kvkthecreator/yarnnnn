# Performance Rollup Spec

Schema for `/workspace/operation/{domain}/_money_truth.md` rolling-window
money-truth substrate. Written by the `outcome-reconciliation` recurrence
after fills are reconciled against proposals.

## File format

Markdown with YAML frontmatter. The frontmatter carries machine-parsed
metrics; the body carries narrative summaries the Reviewer reads.

## Required structure

```markdown
---
last_reconciled: 2026-05-10T05:00:00Z
windows:
  7d:
    realized_pnl_usd: 1240.50
    fills: 12
    win_rate: 0.583
    avg_win_usd: 215.80
    avg_loss_usd: -125.30
    expectancy_usd: 89.25
    sharpe: 1.42
  30d:
    realized_pnl_usd: 5215.20
    fills: 48
    win_rate: 0.604
    avg_win_usd: 198.40
    avg_loss_usd: -118.10
    expectancy_usd: 73.10
    sharpe: 1.58
  90d:
    realized_pnl_usd: 18420.40
    fills: 132
    win_rate: 0.621
    avg_win_usd: 215.80
    avg_loss_usd: -130.20
    expectancy_usd: 84.50
    sharpe: 1.61

per_signal:
  IH-1:
    fills_30d: 18
    expectancy_usd_30d: 95.20
    sharpe_30d: 1.78
  IH-2:
    fills_30d: 14
    expectancy_usd_30d: 62.40
    sharpe_30d: 1.21
  # ... one block per active signal
---

# Performance — Trading

## Headline (last 7 days)
Net P&L: +$1,240.50 across 12 fills. Win rate 58% — within band.
Expectancy stable at +$89/trade.

## By signal
- **IH-1** carrying the book (+$520/30d, sharpe 1.78). No decay flag.
- **IH-2** flat-to-down vs declared baseline; first decay watch entry.
- **IH-3** through **IH-5** within tolerance.

## Recent notable
- 2026-05-08 NVDA IH-3 long: +$310 (target hit; rule worked clean)
- 2026-05-07 AMD IH-2 short: -$190 (stopped out; signal misfired
  on overnight gap — flagged for IH-2 decay watch)
```

## Quality criteria

- Frontmatter `windows.{7d,30d,90d}` ALL present; null fills/expectancy
  only when no fills in window
- `per_signal.{signal_id}` present for every signal that fired in 90d
- `last_reconciled` matches the recurrence fire time (UTC)
- Body sections (`Headline`, `By signal`, `Recent notable`) are 1-3
  paragraphs each — quantitative, signal-attributed
- Never editorialize beyond what the numbers support
- The Reviewer reads this file at every calibration + reflection — keep
  it scannable, not narrative-heavy
