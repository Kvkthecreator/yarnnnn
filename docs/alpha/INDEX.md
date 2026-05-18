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

The harness runs the ADR-230 D5 sequence: load + validate persona,
fork bundle reference-workspace per ADR-226 (which includes the bundle's
`_recurrences.yaml` per ADR-261 D2 — the single canonical recurrence
declaration substrate; per-shape `_spec.yaml`/`_action.yaml`/`_recurring.yaml`/
`tasks.yaml` files no longer exist), apply persona overrides per ADR-230 D6,
ensure specialist agent rows lazy-create on dispatch, optional platform connect.

**Operator-initiated versioned updates (ADR-292).** Once a workspace is
activated, kernel + bundle updates reach it via the Claude Code
`claude --update` model — versioned platform releases, operator-initiated
adoption. The platform versions substrate (KERNEL_VERSION + MANIFEST.yaml
`version:`); the workspace records its adopted version in MANDATE.md
frontmatter (`activated_bundle_version`, `activated_kernel_version`). When
canon advances, the Settings → Workspace surface (per ADR-244) renders an
"Update available" affordance with the diff summary. The operator clicks
Update; backend invokes `apply_substrate_update(scope=...)`. Files where
the operator has taken authorship are skipped via `is_skeleton_content`
(the same gate `fork_reference_workspace` uses). Audit trail at
`/workspace/_shared/substrate-update-log.md`. NOT a daily cron — the
operator decides when. See
[ADR-292](../adr/ADR-292-continuous-substrate-reapply.md) for the discipline.


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
| [parked/](./parked/) | Content lifted out of the canonical playbook when it's no longer alpha-current but worth preserving (alpha-commerce persona spec, pre-Bucket-C BOOTSTRAP runbook). Read banners on each file before quoting from them — substrate vocabulary may be stale. |

## Alpha-operator subagent (Claude Code)

The recurring rituals (daily sanity check, end-of-day decisions/outcomes
scan, weekly performance + cost report, observation note triage, phase-
transition readiness check) have a dedicated subagent at
[.claude/agents/alpha-operator.md](../../.claude/agents/alpha-operator.md).
Invoke via `Agent(subagent_type="alpha-operator", ...)` from any Claude
Code session. The subagent is narrow: it reads, drafts, reports — it
does not approve proposals, edit operator substrate, flip phases, or
commit. High-stakes actions explicitly defer back to the main session.

## Session-start ritual (any Claude session, any operator)

```bash
cd /Users/macbook/yarnnn
python -m api.scripts.alpha_ops.verify --all
```

If green (29/29 per alpha-trader-program persona post-Bucket-A invariants), workspaces are healthy on Objective-A invariants. The expected fail mode pre-Alpaca-connect is `platform_connections count: got 0, expected 1` — 28/29 with that single FAIL is the healthy state after `reset.py` and before `connect.py`. alpha-commerce is parked per SCOPE.md; only alpha-trader-program personas (`alpha-trader`, `alpha-trader-2`, `kvk`) run during Alpha-1. For Objective-B state, read `_money_truth.md` directly via harness DB query or cockpit Context surface. See DUAL-OBJECTIVE-DISCIPLINE.md for don't-drift checklist before substantive work begins.

## Iterative-by-design

This folder will grow. New docs land here if they're alpha-scoped;
architectural patterns move to `docs/architecture/` or ADRs when
they generalize. Update this INDEX when new docs land.

## Revision history

| Date | Change |
|------|--------|
| 2026-04-21 | v1 — Initial index. Five canonical docs + two substrate subdirectories. Created alongside DUAL-OBJECTIVE-DISCIPLINE.md. |
| 2026-04-30 | v2 — SCOPE.md added as canonical first-read. Locks in trading-only + money-truth + cost-truth contract + alpha-commerce parked. |
| 2026-04-30 | v3 — Alpha-operator subagent ([.claude/agents/alpha-operator.md](../../.claude/agents/alpha-operator.md)) shipped. Recurring rituals delegate to it; high-stakes actions still route through main session. |
| 2026-05-11 | v4 — Bucket C alpha-doc cleanup. Adds `parked/` substrate subdirectory. Updates activation-harness blurb to reflect ADR-261/262 substrate (single `_recurrences.yaml`, no `tasks.yaml`). Updates session-start ritual numerics for post-Bucket-A invariants (29/29 with Alpaca connected, 28/29 pre-connect). Pairs with: ALPHA-1-PLAYBOOK §3A.5/§3A.5b unification + §3B alpha-commerce parking; BOOTSTRAP.md archived to `parked/`; E2E-EXECUTION-CONTRACT v4 covering ADR-260/261/262 substrate. |
