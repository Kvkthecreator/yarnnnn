# docs/alpha/ — Index

Single-source-of-truth folder for Alpha-1 alpha testing. Everything
alpha-related is here or linked from here.

## Canonical docs (read in this order for fresh sessions)

| Doc | Purpose | Read when |
|---|---|---|
| [ALPHA-1-PLAYBOOK.md](./ALPHA-1-PLAYBOOK.md) | Rules of engagement, persona specs, phases, governance | Always first |
| [DUAL-OBJECTIVE-DISCIPLINE.md](./DUAL-OBJECTIVE-DISCIPLINE.md) | Two objectives (A-system + B-product), three-axis observation schema, dual weekly report templates, anti-drift rules | Before writing any observation or report |
| [CLAUDE-OPERATOR-ACCESS.md](./CLAUDE-OPERATOR-ACCESS.md) | Three access modes (Headless / Cockpit / Conversational); per-mode auth + discretion + future connection paths | First thing a new Claude session reads |
| [OPERATOR-HARNESS.md](./OPERATOR-HARNESS.md) | Mode 1 machinery: `verify.py`, `mint_jwt.py`, `connect.py`, `reset.py` | When running commands |
| [personas.yaml](./personas.yaml) | Persona registry: slug → email → user_id → workspace_id → invariants | Read by harness scripts; humans read for cross-reference |

## Substrate subdirectories

| Path | Purpose |
|---|---|
| [observations/](./observations/) | One note per friction event. Template + rules in the dir's README. Must classify per DUAL-OBJECTIVE-DISCIPLINE.md schema. |
| [reports/](./reports/) | Dual weekly reports per persona (A-system + B-product). Sunday cadence. |

## Session-start ritual (any Claude session, any operator)

```bash
cd /Users/macbook/yarnnn
.venv/bin/python api/scripts/alpha_ops/verify.py --all
```

If green (23/23 alpha-trader + 20/20 alpha-commerce), workspaces are
healthy on Objective-A invariants. For Objective-B state, read
`_performance.md` directly via harness DB query or cockpit Context
surface. See DUAL-OBJECTIVE-DISCIPLINE.md for don't-drift checklist
before substantive work begins.

## Iterative-by-design

This folder will grow. New docs land here if they're alpha-scoped;
architectural patterns move to `docs/architecture/` or ADRs when
they generalize. Update this INDEX when new docs land.

## Revision history

| Date | Change |
|------|--------|
| 2026-04-21 | v1 — Initial index. Five canonical docs + two substrate subdirectories. Created alongside DUAL-OBJECTIVE-DISCIPLINE.md. |
