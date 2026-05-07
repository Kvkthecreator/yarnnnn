---
tier: canon
note: "Program-typical delegation defaults. Operator may tighten or widen as Phase progression earns calibration data — but defaults match the program's risk posture."
---

# Autonomy — alpha-trader

> Per ADR-217: this file declares operator-to-role delegation. Not Reviewer-owned; operator-owned. Reviewer reads it to understand its delegation ceiling.

## Trading actions

**Default for fresh workspace (Phase 0-1, paper)**:

```yaml
default:
  level: bounded_autonomous
  ceiling_cents: 20000             # $200 — paper orders only
  never_auto:
    - close_position_market        # always requires operator click
    - cancel_other_orders

heartbeat_triggers:
  - after: signal_evaluation       # Reviewer wakes when signal-evaluation executor completes
  - after: outcome_reconciliation  # Reviewer wakes after daily reconciliation writes _performance.md
  - cron: "10 8 * * 1-5"          # Morning review at 08:10 ET (after 08:05 signal-evaluation)
```

`heartbeat_triggers` (ADR-253 D5): declares what substrate changes wake the Reviewer proactively. When a recurrence matching a trigger slug completes, the Reviewer runs `heartbeat_turn()` — reads the fresh output, applies principles, decides: propose / directive / stand-down.

## Phase progression

- **Phase 0-1 (Observation, Paper Discipline)**: `bounded_autonomous` at $200 ceiling. heartbeat_triggers active. Reviewer wakes on signal-evaluation output, proposes paper orders when conditions met, auto-executes within ceiling.
- **Phase 2 (Live Float)**: tighten `level: manual` for live orders. Recalibrate from zero on the live account. Paper ceiling preserved for paper-mode validation.
- **Phase 3 (Calibrated Autonomy)**: raise ceiling as expectancy data accumulates. `principles.md` `auto_approve_below_cents` should track the ceiling.

## Reviewer-written pause fields (ADR-248 D3)

The Reviewer's periodic reflection can write two optional fields to the `default:` block when it detects structural drift (consistent capital loss, win rate below defensible threshold):

```yaml
default:
  level: bounded_autonomous
  ceiling_cents: 150000
  paused_until: "2026-05-10T00:00:00Z"   # ISO-8601 UTC — Reviewer-written
  pause_reason: "Win rate dropped below 35% over 7d. Reviewer auto-paused."
```

**When set**: `should_auto_execute_verdict()` routes all proposals to the operator Queue until `paused_until` expires — regardless of delegation level.

**When expired**: the fields are silently ignored on the next evaluation. Autonomy resumes automatically. No second write needed.

**Operator override**: remove `paused_until` via YARNNN chat at any time (`WriteFile scope=workspace path=context/_shared/AUTONOMY.md`).

The operator always retains authority over this file. The Reviewer's pause is advisory-with-teeth (it gates execution) but the operator can lift it instantly.

## What AUTONOMY does NOT do

- Does not declare operator preferences or values (those live in `IDENTITY.md` + `MANDATE.md`).
- Does not declare risk rules (those live in `_risk.md`).
- Does not declare Reviewer's evaluation framework (that lives in `/workspace/review/principles.md`).

AUTONOMY answers exactly one question per role: *what's the operator's delegation ceiling for this kind of action?*
