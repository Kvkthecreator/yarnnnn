# Autonomy — alpha-trader

> Per ADR-254: **machine-parsed delegation config lives in `_autonomy.yaml` (sibling file)**. This file is prose documentation for human and LLM reading. Edit `_autonomy.yaml` to change delegation ceilings.

## What autonomy controls

`_autonomy.yaml` declares the delegation ceiling: how much the Reviewer's approve verdict binds automatically vs. routes to your Queue for a click.

**Levels:**
- `manual` — every order surfaces for your click, regardless of Reviewer verdict
- `assisted` — AI recommends; you click
- `bounded_autonomous` — Reviewer auto-executes within `ceiling_cents`; defers above
- `autonomous` — Reviewer auto-executes all approvals within scope

**`ceiling_cents`** — the notional threshold for `bounded_autonomous`. Orders above this always surface to Queue.

**`never_auto`** — action types that always route to Queue regardless of level. Hard safety list.

## Phase progression

- **Phase 0-1 (Observation, Paper)**: `bounded_autonomous` at `ceiling_cents: 20000` ($200). Exercises the loop without large exposure.
- **Phase 2 (Live Float)**: tighten to `manual` for live orders until calibration justifies loosening.
- **Phase 3 (Calibrated)**: raise ceiling as approve-correct rate accumulates in `calibration.md`.

## Reviewer-written pause (ADR-248 D3)

The Reviewer's periodic reflection can write `paused_until` and `pause_reason` into `_autonomy.yaml` when it detects structural drift. While set, all proposals queue for your click regardless of level. Expires automatically at the timestamp. You can remove it via chat at any time.

## Heartbeat triggers

`heartbeat_triggers` in `_autonomy.yaml` declares which substrate changes wake the Reviewer proactively (ADR-253 D5). After signal-evaluation or outcome-reconciliation completes, the Reviewer reads the fresh output and decides: propose / directive / stand-down.

## What AUTONOMY does NOT control

- Reviewer's evaluation framework (principles.md + _principles.yaml)
- Risk rules (_risk.md)
- Operator strategy and persona (MANDATE.md, IDENTITY.md, _operator_profile.md)
