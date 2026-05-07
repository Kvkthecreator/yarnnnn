---
tier: authored
prompt: "What are YOUR hard rejection rules and capital-EV thresholds? The defaults are the program's typical shape; tune them to your edge."
---

# Reviewer Principles — alpha-trader

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

- **Auto-approve below threshold**: reversible orders below `auto_approve_below_cents` AND signal expectancy positive over rolling 30 days. My approve verdict then binds execution when AUTONOMY.md ceiling also permits (ADR-253 D1).
- **Defer for operator review**: when capital-EV is positive but uncertain (sample size < 20 occurrences of the signal).
- **Reject**: when capital-EV is negative or signal expectancy has decayed below retire-flag threshold. Rejection is unconditional — AUTONOMY does not gate my rejects.

```yaml
auto_approve_below_cents: 20000   # $200 — paper mode default (ADR-253 D1).
                                   # Approve verdict binds execution for reversible paper
                                   # orders under this threshold when AUTONOMY also permits.
                                   # Set to 0 to require operator Queue click for all orders.
```

## Defer posture — what I commission when I defer for evidence gap (ADR-253 D2)

When deferring because a signal has < 20 closed-loop samples in `_performance.md`:
- Directive: fire `track-universe` to accumulate more data

When deferring because `_performance.md` is empty (no reconciled outcomes yet):
- Directive: clarify to operator — "No closed-loop outcomes exist for [signal]. Approve a minimum-size paper seed trade to begin calibration."

When deferring because a signal spec is ambiguous:
- Directive: write a note to `/workspace/review/notes.md` flagging the spec gap

I do not issue proposals to myself (no `task.create` proposals). Directives execute immediately via the System Agent — no second Reviewer pass.

## Directive posture (ADR-253 D2)

What I can instruct directly: fire existing recurrences, write to `/workspace/review/` substrate, clarify to operator.
What I cannot instruct: external platform writes (those are proposals), infrastructure changes, operator configuration.

## Calibration loop

Reviewer's verdict + reasoning + outcome (when reconciler closes the loop) accumulate in `decisions.md`. Calibration aggregates approve-correct vs approve-incorrect over rolling windows. If approve-incorrect rate climbs, principles tighten.

## What this file is NOT

- Not the operator's personal beliefs about markets. Beliefs live in `_operator_profile.md`.
- Not Reviewer's persona. Persona lives in `IDENTITY.md`.
- Not delegation ceilings or heartbeat triggers. Those live in `/workspace/context/_shared/AUTONOMY.md`.
