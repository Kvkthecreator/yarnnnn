---
title: Programs — OS / Program Separation
date: 2026-04-26 (v2 alignment 2026-04-27 for ADR-222)
status: canonical
related:
  - docs/architecture/SERVICE-MODEL.md
  - docs/architecture/FOUNDATIONS.md
  - docs/architecture/GLOSSARY.md
  - docs/adr/ADR-222-agent-native-operating-system-framing.md
  - docs/analysis/external-oracle-thesis-2026-04-26.md
---

# Programs

> **YARNNN is an agent-native operating system** (canonized by [ADR-222](../adr/ADR-222-agent-native-operating-system-framing.md), [FOUNDATIONS Principle 16](../architecture/FOUNDATIONS.md)). The **kernel** (substrate + primitives + axioms + privileged daemons + filesystem + shell + init system) is domain-agnostic by construction.
>
> A **program** is an application that runs on the YARNNN kernel — opinionated about its own surfaces, scaffolding, success bar, and iteration cycle. Programs are allowed to be vertical in ways the kernel cannot be.
>
> A **program bundle** is the declarative package an application ships: manifest (the program's `README.md`) + reference workspace + composition manifest + dependencies. The bundle root is this folder: `docs/programs/{program}/`. Equivalent to `.app` (macOS), `.deb` (Debian), `.apk` (Android).
>
> The kernel doesn't change when a program is added. macOS doesn't become "Photoshop OS" when Adobe ships Photoshop — the kernel keeps its general-purpose contract; the program ships its bundle.

## Why this folder exists

To separate program-layer commitments from OS-layer commitments. Mixing them is how horizontal platforms accidentally over-fit to one customer and how vertical products accidentally bloat the substrate.

When an architectural decision comes up, the program docs are the **litmus test**:

- *Does this OS change generalize across all reference programs?* → OS-layer work, ship.
- *Does it only serve one program?* → program-layer work, lives inside that program's surfaces.

## Program registry

> Bundle layout per [ADR-223](../adr/ADR-223-program-bundle-specification.md). The `status` field in each bundle's `MANIFEST.yaml` is the source of truth; the table below is a reading aid.

| Program | Status (MANIFEST) | Oracle shape | Capital threshold | Bundle |
|---|---|---|---|---|
| **alpha-trader** | `active` | Continuous price (equities + options) | $5K+ paper, then live | [alpha-trader/](alpha-trader/) — [MANIFEST](alpha-trader/MANIFEST.yaml) · [SURFACES](alpha-trader/SURFACES.yaml) · [reference-workspace](alpha-trader/reference-workspace/) |
| **alpha-prediction** | `reference` | Binary terminal outcome (Polymarket / Kalshi) | $100-stakes | [alpha-prediction/](alpha-prediction/) — [MANIFEST](alpha-prediction/MANIFEST.yaml) · [SURFACES](alpha-prediction/SURFACES.yaml) |
| **alpha-defi** | `reference` | On-chain settled state + token prices | $1K + custody | [alpha-defi/](alpha-defi/) — [MANIFEST](alpha-defi/MANIFEST.yaml) · [SURFACES](alpha-defi/SURFACES.yaml) |

**Only alpha-trader is being built right now.** The other two exist as committed-but-uncoded reference SPECs. Their job is to keep the kernel honest about what it claims to support, and to prevent the kernel from accidentally becoming alpha-trader-shaped. They graduate from `reference` → `active` when activation_preconditions in their MANIFEST hold.

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

A primitive that only serves one of these is program-layer. A primitive that serves all three is kernel-layer. This is the kernel contract the reference programs enforce — the litmus test for any proposed kernel change.

## What rejected the triangle

These were considered as the third or fourth program and rejected:

- **FX** — oracle shape and execution profile are too similar to alpha-trader. Pairing it would over-fit the OS toward one shape. Better treated as a future expansion of alpha-trader (Oanda/IB capability bundle on the same program).
- **Sports betting** — fragmented sportsbook APIs, state-by-state regulatory mess. Polymarket / Kalshi give a single API, single oracle shape, clean settlement. Subsumed into alpha-prediction.
- **Pure yield farming** — too narrow as a reference. Subsumed into alpha-defi as one of its action modes.

## Program bundle structure

Each program bundle declares (or will declare, as forthcoming implementation ADRs land):

| Artifact | Role | Status |
|---|---|---|
| `README.md` | **Program manifest** — what the program is, what kernel features it depends on, what surfaces it commits to, success bar. Equivalent to `Info.plist` (macOS) / `manifest.json` (Chrome). | Convention landed |
| `reference-workspace/` | **Bundled reference substrate** — the starter substrate operators fork on activation. Equivalent to an app's bundled default user-data template. | Convention to land via Reference-Workspace Activation Flow ADR |
| `SURFACES.yaml` *(or equivalent)* | **Composition manifest** — declarative spec of what the cockpit looks like for this program. Read by the compositor. | Format spec to land via Program Bundle Specification ADR |
| Implicit: program-specific context-domain conventions | Domain naming + entity structure conventions specific to this program (e.g., `customers/`, `portfolio/`, `trading/`) | Currently colocated with kernel registries; moves into bundles via Kernel/Program Boundary Refactor ADR |
| Implicit: program-specific task type catalog | Curated task templates program operators commonly fork from (e.g., `trading-digest`, `revenue-report`) | Currently colocated with kernel registries; moves into bundles via Kernel/Program Boundary Refactor ADR |

## Program-layer artifacts vs persona-layer artifacts

- **`docs/programs/{program}/`** — the **program bundle**: what *YARNNN-the-platform commits to support*. Manifest, reference workspace, composition manifest, OS dependencies, success bars. Stable across operators of that program.
- **`docs/alpha/personas/{persona}/`** — what a *specific operator workspace* looks like. Mandate, operator profile, risk file, principles. Per-operator authoring (the lived-loop source for graduation into the program bundle).

A program supports many personas. The persona layer is where the workspace lives; the program-bundle layer is where the platform commits to supporting that workspace shape. Personas fork from the bundle's reference workspace at activation; their authored deltas eventually graduate back to the bundle via the reference-reflexive loop (forthcoming ADR).

## Discipline

The OS/program separation is enforced by:

1. **Kernel-layer ADRs do not name programs.** They name primitives and dimensions.
2. **Program bundles do not propose kernel changes.** When a program needs a kernel change, it goes through the ADR process and must be justified across all reference programs.
3. **Only alpha-trader has implementation under it.** alpha-prediction and alpha-defi are SPECs, not roadmaps. They activate (graduate to programs-with-code) when their preconditions land.
4. **Adding a program is purely additive.** A new bundle, possibly new system component library entries, no kernel touch. Per ADR-222 + FOUNDATIONS Principle 16.
