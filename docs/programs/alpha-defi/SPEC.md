---
title: alpha-defi — Reference Program SPEC
date: 2026-04-26
status: reference program — design test only, no code
related:
  - docs/programs/README.md
  - docs/programs/alpha-trader/README.md
  - docs/programs/alpha-prediction/SPEC.md
  - docs/analysis/external-oracle-thesis-2026-04-26.md
---

# alpha-defi (Reference)

> **Status: SPEC only. Zero code. Zero implementation.** This document exists to constrain OS-layer decisions, not to ship a program. When an OS change is proposed, it must hold under this SPEC's oracle profile or be reclassified as program-layer (alpha-trader-specific) work.

## Why this document exists

Of the three reference programs, alpha-defi stresses the OS hardest. Irreversibility, 24/7 markets, on-chain settled state as alternative perception substrate, custody as a real engineering concern, and the widest action space across the triangle. If the OS handles alpha-defi cleanly, it is genuinely domain-agnostic-within-finance; if it doesn't, the OS is implicitly equity-shaped.

This SPEC is the heaviest litmus test in the registry.

## Oracle profile

| Property | Value |
|---|---|
| Oracle source | On-chain settled state (block-level finality), token prices (DEX + CEX), protocol returns (APY measured) |
| Latency | Block time (seconds-minutes) for execution; continuous price ticks |
| Attribution | Per-position P&L; per-strategy via tx-hash-keyed action attribution; impermanent loss attribution non-trivial |
| Action space | **Wide**: spot swap, limit order, lend, borrow, LP add/remove, stake, unstake, claim rewards, bridge |
| Action irreversibility | **Irreversible** — once a tx confirms, it confirms. No cancel. No "close before fill" |
| Capital threshold | $1K + custody infrastructure (the gating cost) |
| Stationarity | Protocol-mechanics stable; market regime drifts faster than equities (memecoin cycles, narrative shifts, depegs) |

**The defining property: irreversible actions.** alpha-trader can cancel an unfilled order, close an open position. alpha-prediction's positions are bounded by entry cost. alpha-defi's tx, once confirmed, cannot be undone — only offset by a future tx. This changes everything about the proposal-review-execute loop.

## OS stress points (the litmus)

These are the hardest tests of OS generality. If any answer is "alpha-trader doesn't need this, so it's not OS-layer," the OS is implicitly equity-shaped.

1. **Idempotency primitive at the action layer** — duplicate tx submission is catastrophic (double-spend the gas, sometimes double-execute). External-action proposal envelopes must carry an idempotency key (tx hash for confirmed, deterministic-nonce for pre-submission). alpha-trader gets this for free from broker order IDs; alpha-defi forces it to be explicit.
2. **24/7 task scheduling** — alpha-trader's tasks can gate on market hours. alpha-defi has no market close. Scheduler primitives must handle continuous cadence without "session-close compaction" assumptions.
3. **On-chain data as a perception layer** — `/workspace/context/onchain/` is structurally distinct from `/workspace/context/trading/` because it reads from RPC, not REST APIs, and the substrate is block-keyed not date-keyed. Block height as time anchor (alongside or instead of UTC timestamp) must be expressible.
4. **Custody / key management primitives** — Polymarket-style EIP-712 signing is one shape; alpha-defi requires more. Hot wallet, MPC, account abstraction (EIP-4337), or hardware-backed signing — the OS must have a custody abstraction that admits all of these without hardcoding hot-wallet-only. **This is the heaviest OS lift the reference triangle implies.**
5. **MEV / slippage as first-class risk concepts** — Reviewer principles for alpha-defi must reason about slippage tolerance, MEV exposure (front-run risk on swaps), liquidity-pool depth at execution time. This is domain-specific principles.md content; the Reviewer machinery stays domain-neutral.
6. **Substrate-replay determinism under non-deterministic execution** — even with a deterministic substrate snapshot, on-chain tx execution depends on block state at submission time (gas prices, mempool, MEV). Backtest replay must explicitly mark non-deterministic gaps; "this strategy would have entered at $X on block N" is approximate, not exact.
7. **Outcome reconciliation across heterogeneous protocols** — a yield position's outcome blends interest accrual + token rewards + IL + protocol fees + liquidation events. OutcomeProvider must accommodate compound outcome shapes, not just price marks or terminal binaries.

## Hypothetical scaffolding (if/when activated)

Sketch only. None of this is built.

### Capability bundles
- `read_defi` — RPC reads (block state, token balances, position data), DEX aggregator quotes, protocol APIs, on-chain analytics (Dune, DeFiLlama)
- `write_defi` — signed tx submission (swap, lend, LP, stake, claim, bridge); per-tx EIP-712 or EIP-1559 signing

### Context domains
- `/workspace/context/onchain/` — per-protocol entities, `_positions.md`, `_yields.md`, `_risk_state.md` (smart-contract risk, depeg risk, oracle risk)
- `/workspace/context/portfolio/` — wallet-level state across protocols, gas float, base-token balances
- `/workspace/context/markets/` — token/pair-level entities for tradeable assets

### Task types
- `defi-digest` (accumulates_context, daily) — sweep watched protocols and positions
- `defi-signal` (produces_deliverable, varies) — evaluate strategy against current state (yield arbitrage, rebalance trigger, depeg detection, etc.)
- `defi-execute` (external_action, reactive) — Reviewer-approved tx submission
- `gas-float-monitor` (back-office, hourly) — alert before base-token (ETH/MATIC/SOL) balance falls below execution threshold

### Principles content (operator authors per persona)
- Smart-contract risk explicit per protocol (audit history, TVL, age, exploit history)
- Slippage tolerance per asset class (stablecoins ≤ 0.1%, blue-chips ≤ 0.5%, longtail ≤ 2%)
- Maximum exposure to any single protocol / chain / asset
- Bridge risk explicitly named (cross-chain bridges have different risk than swaps)
- Liquidation buffer for borrow positions

## Differences from alpha-trader the OS must absorb

| Concern | alpha-trader | alpha-defi | OS implication |
|---|---|---|---|
| Action irreversibility | Reversible | Irreversible | Idempotency primitive at proposal envelope |
| Action space width | ~5 verbs | ~15+ verbs across protocols | Capability bundle must support per-protocol verb sets without `CAPABILITIES` proliferation |
| Time anchor | UTC date | Block height + UTC | Substrate-replay must accommodate block-keyed reconstruction |
| Custody | Broker-held | Self-custody (or MPC, or AA) | Custody abstraction beyond "API key in Fernet" |
| Outcome shape | Continuous P&L | Compound (yield + price + IL + rewards) | OutcomeProvider must accommodate compound outcomes |
| Risk surface | Position + sector + var | + smart-contract + depeg + oracle + bridge + MEV | Principles.md content extends; Reviewer machinery does not |

The custody concern (item 4 above + this row) is where alpha-defi and alpha-prediction overlap. **Two reference programs raising the same OS need is the strongest signal that need is OS-layer.**

## Activation preconditions

This SPEC graduates to a built program when **all** of the following land:

1. alpha-trader Phase 2 (Live Float) completes successfully — the OS has been validated under real-money pressure on the easier oracle
2. alpha-prediction has activated or is concurrently activating (custody primitives shared)
3. Custody / key-management primitives are designed and shipped at OS-layer
4. Idempotency primitive is shipped on the action proposal envelope
5. Substrate-replay primitive supports block-keyed reconstruction
6. A real operator with on-chain experience and willingness to operate small live capital
7. Security review of the custody design — private key escalation is materially harder than OAuth tokens

Until then: this SPEC stays a litmus test, and arguably the loudest one — when the OS has the most "but this is just for alpha-trader" pull, alpha-defi is the SPEC that breaks the tie toward generalization.

## What this SPEC explicitly does NOT do

- **Does not propose specific protocols** (Aave vs Compound, Uniswap vs Curve, Hyperliquid vs dYdX). Protocol choice is operator-level, not platform-level.
- **Does not commit chain support** (Ethereum vs Solana vs L2s). Multi-chain is implementation work that activates with the program.
- **Does not propose hot wallet vs MPC vs AA at the OS layer.** It says the OS must support any of them; choosing one is program-layer when the program activates.
- **Does not promise the program will activate.** It might not. The SPEC's value as a litmus test is independent of whether it ever ships as code.

## Review cadence

Same as alpha-prediction:
- Reviewed when a new OS-layer ADR is proposed (litmus check)
- Reviewed when alpha-trader passes a phase milestone (activation precondition check)
- Reviewed when custody primitives are designed (concurrent with the design work)

## Note on intentional difficulty

This SPEC is the hardest of the three because it is meant to be. alpha-trader is the easiest oracle. alpha-prediction adds binary outcomes and time-to-resolution. alpha-defi adds irreversibility, custody, and 24/7 cadence. The triangle's geometry is intentional: the hardest reference catches the most over-fitting in the OS. If the OS handles all three SPECs cleanly, it has earned the "domain-agnostic-within-finance" claim.
