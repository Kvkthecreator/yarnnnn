---
tier: canon
note: "Program-typical delegation defaults. Operator may tighten or widen as Phase progression earns calibration data — but defaults match the program's risk posture."
---

# Autonomy — alpha-trader

> Per ADR-217: this file declares operator-to-role delegation. Not Reviewer-owned; operator-owned. Reviewer reads it to understand its delegation ceiling.

## Trading actions

**Default for fresh workspace**: every order requires manual operator approval. AUTONOMY remains conservative until the operator has accumulated calibration data.

```yaml
trading-execute:
  approval_required: manual_operator
  ceiling_usd_per_order: 0
  ceiling_usd_per_day: 0
```

## Phase progression

- **Phase 0-1 (Observation, Paper Discipline)**: paper account only. AUTONOMY may permit `bounded_autonomous` (Reviewer-approved auto-execute) for paper orders to exercise the loop.
- **Phase 2 (Live Float)**: AUTONOMY flips trading-execute to `manual_operator` for live orders, regardless of paper-account autonomy.
- **Phase 3 (Calibrated Autonomy)**: operator-authored thresholds for selective auto-approval, e.g., reversible orders below $X notional may auto-approve when expectancy data justifies.

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
