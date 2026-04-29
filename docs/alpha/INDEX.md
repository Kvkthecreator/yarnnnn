# docs/alpha/ — Index

Single-source-of-truth folder for Alpha-1 alpha testing. Everything
alpha-related is here or linked from here.

## Canonical terminology (ADR-222 + ADR-230)

When working on alpha + program code/docs, use these terms exactly:

| Term | Meaning |
|---|---|
| **Program** | Platform-shipped opinion about how an operation should run (`alpha-trader`, `alpha-commerce`). The unit of "what an alpha persona is dogfooding." |
| **Program bundle** | The on-disk artifact at `docs/programs/{slug}/` that ships a program. |
| **Reference workspace** | The bundle's substrate template at `docs/programs/{slug}/reference-workspace/`. Forked into operator workspaces at activation per ADR-226. |
| **Operator** | Real human running a workspace. Includes alpha personas + post-launch users. |
| **Alpha operator** (or **alpha persona**) | Operator dogfooding a program. Registry row in `personas.yaml`. |
| **Program-activated workspace** | A workspace that has activated a program (the bundle was forked into it). Per ADR-222: workspaces don't have *types*; they *run programs*. |

**Banned terms** (do not use in code/docs/commits going forward per ADR-230):
- "workspace type" / "workspace kind" — workspaces don't have types; they run programs.
- "alpha workspace" used to mean a *kind* of workspace — alpha is an operator-status property.
- "scaffold trader" / "scaffold commerce" used as if these were dedicated programs — the unit is the program; alpha personas activate one.

## Activation harness (post-ADR-230)

`api/scripts/alpha_ops/activate_persona.py` is the program-agnostic
activation entry point. Replaced the deleted `scaffold_trader.py`.

```bash
.venv/bin/python api/scripts/alpha_ops/activate_persona.py --persona alpha-trader-2 --dry-run
.venv/bin/python api/scripts/alpha_ops/activate_persona.py --persona alpha-trader-2
```

The harness runs the 7-step ADR-230 D5 sequence: load + validate persona,
fork bundle reference-workspace per ADR-226, apply persona overrides per
ADR-230 D6, ensure specialist agent rows, POST default tasks from
`docs/programs/{program}/tasks.yaml`, optional platform connect.


## Canonical docs (read in this order for fresh sessions)

| Doc | Purpose | Read when |
|---|---|---|
| [SCOPE.md](./SCOPE.md) | Trading-only commitment, money-truth + cost-truth success contract, persona variation discipline, what's parked | Always first — names what alpha-1 is and isn't |
| [ALPHA-1-PLAYBOOK.md](./ALPHA-1-PLAYBOOK.md) | Rules of engagement, persona specs, phases, governance | After SCOPE — the operating playbook scoped by it |
| [DUAL-OBJECTIVE-DISCIPLINE.md](./DUAL-OBJECTIVE-DISCIPLINE.md) | Two objectives (A-system + B-product), three-axis observation schema, dual weekly report templates, anti-drift rules | Before writing any observation or report |
| [CLAUDE-OPERATOR-ACCESS.md](./CLAUDE-OPERATOR-ACCESS.md) | Three access modes (Headless / Cockpit / Conversational); per-mode auth + discretion + future connection paths | First thing a new Claude session reads |
| [OPERATOR-HARNESS.md](./OPERATOR-HARNESS.md) | Mode 1 machinery: `verify.py`, `mint_jwt.py`, `connect.py`, `reset.py` | When running commands |
| [E2E-EXECUTION-CONTRACT.md](./E2E-EXECUTION-CONTRACT.md) | Pre-E2E alignment: Simons posture, feedback-loop orchestration, Claude acting-on-behalf rules, stop conditions, success criteria | Before running any persona E2E; re-read each run to prevent drift |
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
| 2026-04-30 | v2 — SCOPE.md added as canonical first-read. Locks in trading-only + money-truth + cost-truth contract + alpha-commerce parked. |
