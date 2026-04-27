# alpha-prediction (Reference)

> Reference program SPEC under the agent-native operating system framing canonized by [ADR-222](../../adr/ADR-222-agent-native-operating-system-framing.md), bundle layout per [ADR-223](../../adr/ADR-223-program-bundle-specification.md). This bundle exists to constrain kernel-layer decisions (the litmus triangle), not to ship as an active program. Activation graduates this SPEC to a built program bundle.
>
> Machine-readable contract: [MANIFEST.yaml](MANIFEST.yaml). Sketch composition manifest: [SURFACES.yaml](SURFACES.yaml). Bundled starter substrate (sketch only until activation): [reference-workspace/](reference-workspace/).

> **Status: SPEC only. Zero code. Zero implementation.** This document exists to constrain OS-layer decisions, not to ship a program. When an OS change is proposed, it must hold under this SPEC's oracle profile or be reclassified as program-layer (alpha-trader-specific) work.

## Why this document exists

The OS is at risk of accidentally fitting alpha-trader's shape. alpha-prediction's oracle is meaningfully different (binary terminal outcome, known expiry, narrow action space, non-financial knowledge edge). If an OS primitive doesn't generalize across both alpha-trader and alpha-prediction, it is program-layer.

This SPEC is the litmus test. The activation preconditions at the end say when this graduates to a built program.

A more detailed implementation-shape proposal already exists at [docs/alpha/personas/alpha-polymarket-PROPOSAL.md](../../alpha/personas/alpha-polymarket-PROPOSAL.md). That doc is at the persona/operator layer. This doc is at the program/platform layer.

## Oracle profile

| Property | Value |
|---|---|
| Oracle source | Settled binary outcomes (Polymarket / Kalshi) + market odds |
| Latency | Hours (sports) to weeks-months (politics, science) |
| Attribution | Per-position, terminal — outcome resolved Yes/No, no ambiguity |
| Action space | Buy / sell / size; mostly Yes-side or No-side, with limit/market |
| Action irreversibility | Capped per-position (max loss = entry cost) |
| Capital threshold | $100-stakes can validate; $1K reasonable for honest signal |
| Stationarity | Per-market is stable (the question doesn't drift); aggregate edge requires regime tracking (politics ≠ sports ≠ crypto markets) |

**The defining property: terminal binary outcomes.** alpha-trader's positions can drift indefinitely on continuous prices; alpha-prediction's positions resolve. Time-to-resolution is a first-class property of every position. The principle-evolution loop has cleaner signal here than equities — you don't have to handle "this trade is up 2%, was it skill or noise?" The trade either won or lost.

## OS stress points (the litmus)

These are the questions OS-layer ADRs must answer affirmatively if they claim generality. If the answer is "only alpha-trader needs this," the work is program-layer.

1. **OutcomeProvider abstraction** (ADR-195 v2) — must accommodate `terminal_binary` outcome shape, not just continuous price marks. A `PredictionOutcomeProvider` writes per-resolution to `_performance.md` with binary settlement; `_performance.md` aggregates across markets.
2. **Time-to-resolution as a first-class task field** — TASK.md should accommodate `**Resolution Window:**` for tasks attached to positions with known expiry. alpha-trader doesn't natively need this (option expiries borrow it); alpha-prediction does. Pure equity wouldn't push this; alpha-prediction is the reason this lives in the OS.
3. **Substrate-replay primitive** — must work for week-to-month replay windows, not just intraday. ADR-209's revision chain supports this; substrate-replay's API surface must not assume short replay windows.
4. **Knowledge-domain agents under universal roles** — the Researcher role serves financial fundamentals (alpha-trader) and politics/sports/science domain knowledge (alpha-prediction) without role-class proliferation. If "we need a politics-researcher role" enters discussion, ADR-188 (universal roles, contextual application) has failed its own test.
5. **Action proposal envelope** — must carry market metadata (resolution criteria, expiry, market type) without bloating the envelope schema. Per-program metadata extension is fine; per-program envelope shape is not.
6. **Capped-downside risk math** — Reviewer principles must accommodate "max loss = entry cost" without bespoke trading-domain risk math. Reviewer's reasoning shape stays domain-neutral; principles.md content goes domain-specific.

## Hypothetical scaffolding (if/when activated)

Sketch only. None of this is built.

### Capability bundles
- `read_prediction` — markets, odds, positions, historical settlement (Polymarket CLOB + Gamma + Data API; Kalshi REST API)
- `write_prediction` — submit / cancel orders (signed for Polymarket, REST for Kalshi)

### Context domains
- `/workspace/context/markets/` — per-market entities (one folder per active position or watched market), `_resolution_criteria.md`, `_liquidity.md`
- `/workspace/context/portfolio/` — same shape as alpha-trader's, accommodates discrete-outcome positions
- `/workspace/context/news_mappings/` — only for operators using news→market causal mapping

### Task types
- `prediction-digest` (accumulates_context, daily) — sweep watched markets, update entity files
- `prediction-signal` (produces_deliverable, varies) — evaluate edge against current odds + Kelly sizing
- `prediction-execute` (external_action, reactive) — Reviewer-approved order
- `resolution-reconcile` (back-office, on resolution) — write settlement to `_performance.md`

### Principles content (operator authors per persona)
- Kelly fraction or fractional-Kelly required on every proposal
- Resolution risk explicitly named (does the market resolve as the operator believes? regulatory / counterparty / data-source dispute risks)
- Liquidity check — proposal must show market depth supports proposed size without > X% slippage
- Time-to-resolution declared and budgeted

## Differences from alpha-trader the OS must absorb

| Concern | alpha-trader | alpha-prediction | OS implication |
|---|---|---|---|
| Outcome shape | Continuous P&L | Binary settlement | OutcomeProvider must accommodate both |
| Settlement timing | T+1 cash | On-resolution (variable) | Reconciler must handle long resolution windows |
| Custody | Brokerage holds funds | On-chain wallet (Polymarket) or Kalshi-held (CFTC) | Custody primitives — the same architectural concern alpha-defi raises, escalated |
| Authentication | API key + secret | EIP-712 wallet signing (Polymarket) | Auth subsystem must accommodate signed transactions |
| Knowledge edge | Financial fundamentals | Politics, sports, science, crypto-market mechanics | Universal Researcher role must serve all without proliferation |

The custody concern at item 3 overlaps with alpha-defi. If both reference programs raise the same OS need, that's signal it's an OS-layer primitive, not program-layer.

## Activation preconditions

This SPEC graduates to a built program when **all** of the following land:

1. alpha-trader Phase 1 (Paper Discipline) completes successfully
2. Substrate-replay primitive ships at OS-layer (depended on for any backtest-style validation)
3. OutcomeProvider abstraction is generalized to accommodate terminal binary outcomes (currently TradingOutcomeProvider only)
4. A real operator (not the kvk operator) is willing to author honest principles.md and supervise the workspace
5. Custody / signed-transaction primitives are designed (jointly with alpha-defi's needs)

Until then: this SPEC stays a litmus test. ADRs that propose OS changes are reviewed against it.

## What this SPEC explicitly does NOT do

- **Does not propose OS changes.** Changes happen via ADRs, justified across all reference programs.
- **Does not commit timeline.** Activation is gated on alpha-trader validation, not on calendar.
- **Does not commit to Polymarket vs Kalshi as the canonical platform.** That choice is downstream; either platform expresses the same oracle shape.
- **Does not duplicate the Polymarket implementation analysis** at [docs/alpha/personas/alpha-polymarket-PROPOSAL.md](../../alpha/personas/alpha-polymarket-PROPOSAL.md). That doc covers technical details (CLOB API, EIP-712 signing, py-clob-client, gas/float monitoring, security escalation paths) at the persona layer. This SPEC stays at the program-platform layer.

## Review cadence

This SPEC is reviewed when:
- A new OS-layer ADR is proposed (the litmus check)
- alpha-trader passes a phase milestone (the activation precondition check)
- A new finance vertical surfaces that might subsume or replace this reference (the triangle integrity check)
