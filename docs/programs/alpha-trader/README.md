---
title: alpha-trader — Program Spec
date: 2026-04-26
status: primary program — actively built
related:
  - docs/programs/README.md
  - docs/alpha/personas/alpha-trader/MANDATE.md
  - docs/alpha/ALPHA-1-PLAYBOOK.md
  - docs/adr/ADR-187-trading-integration.md
  - docs/adr/ADR-194-reviewer-layer.md
  - docs/adr/ADR-195-money-truth-substrate.md
  - docs/analysis/external-oracle-thesis-2026-04-26.md
---

# alpha-trader

> The first serious program built on top of YARNNN-the-OS. Equities + options operator workflow, validated via the operator's own capital (paper → live). Self-funding by design.

## Position relative to OS

alpha-trader is **the program**. The OS is everything else. This document describes the program — its surfaces, scaffolding, success bar — not the substrate underneath.

When this program needs work that would also serve alpha-prediction or alpha-defi, that work ships as OS-layer. When it needs work that only alpha-trader benefits from, that work ships under this folder or under `docs/alpha/personas/alpha-trader/`.

## Oracle profile

| Property | Value |
|---|---|
| Oracle source | Equity prices (Alpaca + Alpha Vantage), broker-confirmed fills |
| Latency | Intraday marks, daily settles |
| Attribution | Per-position P&L; per-strategy via signal attribution in proposal |
| Action space | Buy / sell / size / hold; stop + target on every order |
| Action irreversibility | Reversible (cancel before fill, close after) |
| Capital threshold | $5K+ paper; live posture gated on AUTONOMY.md flip |
| Stationarity | Mostly stable question ("did this trade make money over horizon H"); regime drift is real but second-order |

This is the cleanest oracle in the triangle and the reason the program exists. Every part of YARNNN's flywheel — Reviewer judgment grounded in `_performance.md`, principle-evolution from outcome divergence, capital-EV reasoning, expectancy decay — relies on a tight oracle loop. Alpha-trader gives that loop hours-to-days latency.

## Surfaces the program needs

These are program-layer commitments — the OS hosts them but does not claim them as universal cockpit features.

| Surface | What it is | Hosting tab |
|---|---|---|
| **P&L-first Overview pane** | When alpha-trader is the active program, Overview leads with `_performance.md` snapshot (rolling P&L, win rate, by-signal expectancy) before generic queue/temporal slices | Overview |
| **Backtest harness** | Substrate-replay primitive (OS-layer) + a trader-shaped consumer that re-runs strategies against past revisions of the workspace + market data | Work / dedicated route TBD |
| **Portfolio dashboard** | Live read of `/workspace/context/portfolio/` — positions, gross/net exposure, sector concentration, var budget consumed, regime indicator | Work task-detail or new pane |
| **Signal-attribution review queue** | Reviewer queue scoped to trading proposals, surfacing the named signal + sized stop + expectancy alongside approve/reject — not just "approve this action" | Review |
| **Daily-discipline checklist** | Renders the MANDATE Daily Discipline boxes against the day's actual proposals + fills | Overview, surfaced 5pm ET |

The OS provides the cockpit shell, narrative substrate, primitive surface. The program provides the trader-shaped reads on top.

## Scaffolding

What the program brings to a workspace, beyond what the OS scaffolds at signup.

### Capability bundles (already shipped, ADR-187)
- `read_trading` — Alpaca account, positions, orders, portfolio history, market data (OHLCV)
- `write_trading` — submit / cancel / close orders, paper or live
- **Gap to wire**: `get_fundamentals` exists in [alpaca_client.py:718](api/integrations/core/alpaca_client.py:718) but isn't exposed as a tool. 30-minute fix per the thesis §7 #5.

### Context domains
- `/workspace/context/trading/` — per-instrument entities (one folder per ticker), `_signals.md`, `_universe.md`
- `/workspace/context/portfolio/` — account-level state, `_positions.md`, `_performance.md`, `_risk_state.md`

### Task types (ADR-187 + program-specific)
- `trading-digest` (accumulates_context, daily) — sweep universe, update entity files
- `trading-signal` (produces_deliverable, daily/hourly) — evaluate declared signals against current state, emit proposal envelope
- `trading-execute` (external_action, reactive) — Reviewer-approved order submission
- `portfolio-review` (produces_deliverable, weekly) — performance attribution, regime check, signal expectancy decay

### Agent roster (universal roles, contextual application)
- Researcher, Analyst, Writer, Tracker, Designer, Reporting — the universal six
- Trading Bot — capability bundle, not a persona-bearing Agent
- Reviewer — Simons-persona principles, capital-EV reasoning over `_performance.md`

### Principles content (program guidance, operator authors)
- Position sizing formula required (`account × risk_percent / stop_distance`), no conviction sizing
- Signal attribution required on every proposal
- Expectancy decay enforcement (auto-defer signals below retire-flag threshold)
- Var budget never exceeded — hard reject
- Discretionary vocabulary blocked at Reviewer

The program ships these as **author-yourself templates** for operators. Operators fork their own MANDATE / `_operator_profile.md` / `_risk.md` / `principles.md` from these. The program does not author them; the OS doesn't either.

## OS dependencies

The OS work this program depends on. All listed are either shipped or in the lean from the thesis §7.

| Dependency | OS ADR | Status |
|---|---|---|
| Authored substrate (revision chain on every workspace_files mutation) | ADR-209 | Shipped |
| OutcomeProvider abstraction | ADR-195 v2 | TradingOutcomeProvider Phase 5a shipped |
| `_performance.md` as canonical money-truth substrate | ADR-195 v2 | Shipped |
| Source-agnostic feedback (`system_outcome` source) | ADR-181 | Shipped |
| Reviewer with capital-EV reasoning | ADR-194 v2 | Phases 1-3 shipped |
| Action proposal queue with approval / rejection / reasoning | ADR-194 v2 + ADR-202 | Shipped |
| AUTONOMY.md delegation file | ADR-217 | Shipped |
| Substrate-replay primitive (foundation for backtest harness) | TBD — proposed in thesis §4.1 | Lean |
| Mandate hardening with `## Outcome Signal` | TBD — proposed in thesis §2.4 | Lean |

## OS stress points

What this program asks of the OS that the OS must deliver cleanly. These are the litmus tests other programs (alpha-prediction, alpha-defi) will mirror:

1. **Replay determinism** — substrate-replay must reconstruct any past revision deterministically; non-determinism in the task pipeline (model drift, tool latency) becomes advisory only for backtests.
2. **Outcome reconciliation idempotency** — duplicate webhook events from the broker must not double-credit P&L. `processed-event-keys` in `_performance.md` frontmatter handles this today.
3. **Reviewer separation under operator-grades-self pressure** — alpha-trader's operator and Reviewer can be the same person early on. Reviewer machinery must stay structurally separate even when occupied by the same identity.

## Success bar

The program is validated when:

1. **Paper Phase**: 90 consecutive days of process obedience under MANDATE Daily Discipline. P&L is variance, not the bar. Daily discipline is the bar.
2. **Phase transition**: Reviewer-approved phase flip to live, AUTONOMY.md updated, small live float.
3. **Live Phase**: Sharpe > 1.0 over rolling 90-day window with var budget honored. Drawdown < 8%. No discretionary overrides logged.
4. **Self-funding milestone**: Live trading P&L pays for the operator's YARNNN platform usage in a billing cycle. This is the structural validation — alpha-trader running on top of YARNNN, paying for YARNNN, with surplus.

These are bars, not promises. Failure of any one is signal about the program; failure of all is signal about the thesis.

## Phase milestones

- **Phase 0 — Observation** (current) — paper account, AUTONOMY.md `bounded_autonomous` carve-out, Reviewer reasoning logged but no live capital
- **Phase 1 — Paper Discipline** — 90 days of MANDATE compliance + signal expectancy data accumulates in `_performance.md`
- **Phase 2 — Live Float** — small live capital ($5–10K), AUTONOMY.md flipped to manual approval, every order operator-approved in Queue
- **Phase 3 — Calibrated Autonomy** — selective auto-approval per principles.md thresholds (e.g., low-notional reversible orders), expanded based on Phase 2 calibration data
- **Phase 4 — Self-Funding Validated** — live P&L sustains platform cost over rolling 90 days

## Relationship to the persona layer

Operator workspace artifacts (`docs/alpha/personas/alpha-trader/`) are operator-authored, per-workspace. Program artifacts (this folder) are platform-authored, stable across operators of the program. The persona layer evolves; the program layer commits.

When a new operator adopts alpha-trader, they fork the persona-layer artifacts from the alpha-trader template. They do not fork program-layer artifacts — those are inherited from the platform.

## Open program-layer questions

Tracked here, not in OS ADRs:

- What's the minimum viable backtest UI vs. CLI-only? (Surface decision, not OS decision.)
- Should the P&L-first Overview pane be a feature flag tied to the program, or always-on for any workspace with `read_trading` connected? (Program-layer surface decision.)
- Pricing model for the program-layer surfaces — bundled into platform usage, or program-tier above the OS billing model? Defer until Phase 2.
- Multi-program operators (alpha-trader + future alpha-commerce) — does Overview switch contexts, multiplex, or land on a chooser? Defer until second program activates.
