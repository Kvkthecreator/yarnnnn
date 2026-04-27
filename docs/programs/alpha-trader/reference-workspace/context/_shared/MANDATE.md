---
tier: authored
prompt: "What is the Primary Action this workspace produces? What's your edge — and what would falsify it?"
---

# Mandate — alpha-trader (template)

> **Operator**: author this file. Keep what serves you, delete what doesn't, and add what's missing for your edge. The platform reads this as the gate for task creation (per ADR-207).

## Primary Action

Submit equity / option orders to broker, sized per declared risk rule, attributed to a named signal.

This is the value-moving external write your operation produces. Everything else in the workspace orbits this.

## Edge hypothesis

> Author here: in 2-4 sentences, name the edge. Why does this edge exist? Who is on the other side of your trades? What would falsify the edge?

Example shape (overwrite with your own):
- *"I trade momentum continuation in liquid US equities, 2-10 day holds. The edge exists because most retail and short-horizon algos chase recent winners at insufficient size; I size larger when expectancy data supports it. Falsified if rolling 90-day expectancy goes negative across all declared signals simultaneously."*

## Rules of operation

1. **Position sizing**: `account × risk_percent / stop_distance`. No conviction sizing. Risk percent declared in `_operator_profile.md`.
2. **Signal attribution**: Every proposal names the signal it's expressing. No "this looks good" trades.
3. **Stop required**: Every order has a stop. Distance derived from instrument volatility, not preference.
4. **Var budget**: Total open risk at any time bounded by var budget in `_risk.md`. Hard reject at Reviewer if exceeded.
5. **Discretionary vocabulary blocked at Reviewer**: words like "feels right", "intuition", "I think it's going to" trigger automatic rejection. Edge is named or absent.

## Daily Discipline

- Pre-market: review overnight, check signal triggers, decide universe.
- Mid-day: monitor open positions against stops, no impulse adds.
- Post-market: log fills, update `_performance.md`, note regime observations.

## Outcome Signal

> Author here: how do you know the operation worked? What's the leading indicator vs the lagging indicator?

Example shape:
- Leading: signal expectancy stable or rising over rolling 90 days; var budget honored; stop discipline respected.
- Lagging: rolling Sharpe > 1.0; max drawdown < 8%; live P&L pays for platform cost.

## What is OUT of scope

- Discretionary momentum trades not attributable to a declared signal.
- Position sizes derived from "I have high conviction this time."
- Holding past stop because "the thesis hasn't changed."
- Adding to losing positions.
