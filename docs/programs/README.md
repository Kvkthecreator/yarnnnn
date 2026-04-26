---
title: Programs — OS / Program Separation
date: 2026-04-26
status: canonical
related:
  - docs/architecture/SERVICE-MODEL.md
  - docs/architecture/FOUNDATIONS.md
  - docs/analysis/external-oracle-thesis-2026-04-26.md
---

# Programs

> **YARNNN-the-OS** is the substrate (authored substrate, primitive matrix, task pipeline, Reviewer machinery, narrative + layered context, money-truth substrate, source-agnostic feedback, prompt profiles, FOUNDATIONS axioms, the four-tab cockpit, the universal agent roster). Domain-agnostic by construction.
>
> **A program** is a serious application built on top — opinionated about its own surfaces, scaffolding, success bar, and iteration cycle. Programs are allowed to be vertical in ways the OS cannot be.
>
> The OS doesn't change when you commit to a program. macOS doesn't become "Photoshop OS" when Adobe ships Photoshop — the OS keeps its general-purpose contract; the program is allowed its specific shape.

## Why this folder exists

To separate program-layer commitments from OS-layer commitments. Mixing them is how horizontal platforms accidentally over-fit to one customer and how vertical products accidentally bloat the substrate.

When an architectural decision comes up, the program docs are the **litmus test**:

- *Does this OS change generalize across all reference programs?* → OS-layer work, ship.
- *Does it only serve one program?* → program-layer work, lives inside that program's surfaces.

## Program registry

| Program | Status | Oracle shape | Capital threshold | Folder |
|---|---|---|---|---|
| **alpha-trader** | **Primary — actively built** | Continuous price (equities + options) | $5K+ paper, then live | [alpha-trader/](alpha-trader/) |
| **alpha-prediction** | Reference — design test only, no code | Binary terminal outcome (Polymarket / Kalshi) | $100-stakes | [alpha-prediction/](alpha-prediction/) |
| **alpha-defi** | Reference — design test only, no code | On-chain settled state + token prices | $1K+custody | [alpha-defi/](alpha-defi/) |

**Only alpha-trader is being built right now.** The other two exist as committed-but-uncoded SPECs. Their job is to keep the OS honest about what it claims to support, and to prevent the OS from accidentally becoming alpha-trader-shaped.

## How the triangle works

The three programs span the oracle-shape space without redundancy:

| Dimension | alpha-trader | alpha-prediction | alpha-defi |
|---|---|---|---|
| Oracle | Continuous price | Binary terminal outcome | On-chain settled state |
| Latency | Minutes-days | Hours-weeks (known expiry) | Seconds-minutes (24/7) |
| Action irreversibility | Reversible (cancel/close) | Capped per-position | Irreversible (on-chain) |
| Action space | Bounded (buy/sell/size) | Narrow (yes/no/size) | Wide (swap + LP + stake + lend) |
| Knowledge edge | Financial fundamentals | Domain knowledge (politics/sports/science) | Mechanism design + on-chain mechanics |
| Capital to validate | $5K+ | $100-stakes | $1K + custody infra |
| Regulatory frame | Standard brokerage | Mixed (CFTC for Kalshi) | Self-custody / permissionless |

A primitive that only serves one of these is program-layer. A primitive that serves all three is OS-layer. This is the OS contract the reference programs enforce.

## What rejected the triangle

These were considered as the third or fourth program and rejected:

- **FX** — oracle shape and execution profile are too similar to alpha-trader. Pairing it would over-fit the OS toward one shape. Better treated as a future expansion of alpha-trader (Oanda/IB capability bundle on the same program).
- **Sports betting** — fragmented sportsbook APIs, state-by-state regulatory mess. Polymarket / Kalshi give a single API, single oracle shape, clean settlement. Subsumed into alpha-prediction.
- **Pure yield farming** — too narrow as a reference. Subsumed into alpha-defi as one of its action modes.

## Program-layer artifacts vs persona-layer artifacts

- **`docs/programs/{program}/`** — what *YARNNN is building*. Product surfaces, scaffolding, OS dependencies, success bars. Stable across operators of that program.
- **`docs/alpha/personas/{persona}/`** — what a *specific operator workspace* looks like. Mandate, operator profile, risk file, principles. Per-operator.

A program supports many personas. The persona layer is where the workspace lives; the program layer is where the platform commits to supporting that workspace shape.

## Discipline

The OS/program separation is enforced by:

1. **OS-layer ADRs do not name programs.** They name primitives and dimensions.
2. **Program docs do not propose OS changes.** When a program needs an OS change, it goes through the ADR process and must be justified across all reference programs.
3. **Only alpha-trader has implementation under it.** alpha-prediction and alpha-defi are SPECs, not roadmaps. They activate (graduate to programs-with-code) when their preconditions land.
