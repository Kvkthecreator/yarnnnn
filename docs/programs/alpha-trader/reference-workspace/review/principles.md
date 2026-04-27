---
tier: authored
prompt: "What are YOUR hard rejection rules and capital-EV thresholds? The defaults are the program's typical shape; tune them to your edge."
---

# Reviewer Principles — alpha-trader (template)

> Operator authors. The Reviewer applies these principles to every trading proposal. Persona (IDENTITY.md) determines *how* the Reviewer reasons; principles determine *what* it tests.

## Hard rejection rules

These produce immediate reject verdicts regardless of any other consideration:

1. **Position sizing**: rejected if size violates `account × risk_percent / stop_distance` formula.
2. **Signal attribution**: rejected if proposal does not name a signal, or names a signal not in `_signals.md`.
3. **Stop**: rejected if no stop, or stop distance not justified by instrument volatility.
4. **Var budget**: rejected if accepting this position would push total open risk above `_risk.md` var budget.
5. **Discretionary vocabulary**: rejected if reasoning contains "feels right", "intuition", "I think it's going to" or equivalent.

## Capital-EV thresholds

Reviewer reasons about expected value using `_performance.md` history:

- **Auto-approve below threshold**: reversible orders below `auto_approve_below_cents` (commented out by default — operator must uncomment to enable any auto-action) AND signal expectancy positive over rolling 30 days.
- **Defer for operator review**: when capital-EV is positive but uncertain (sample size < 20 occurrences of the signal).
- **Reject**: when capital-EV is negative or signal expectancy has decayed below retire-flag threshold.

```yaml
# auto_approve_below_cents: 0  # uncomment to enable AI auto-action under threshold
```

## Calibration loop

Per ADR-211: Reviewer's verdict + reasoning + outcome (when reconciler closes the loop) accumulate in `decisions.md`. Calibration aggregates approve-correct vs approve-incorrect over rolling windows. If approve-incorrect rate climbs, principles tighten.

## What this file is NOT

- Not the operator's personal beliefs about markets. Beliefs live in `_operator_profile.md`.
- Not Reviewer's persona. Persona lives in `IDENTITY.md`.
- Not delegation ceilings. Those live in `/workspace/context/_shared/AUTONOMY.md`.
