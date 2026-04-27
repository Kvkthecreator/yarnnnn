# ADR-223: Program Bundle Specification

> **Status:** Proposed (spec only — zero code)
> **Date:** 2026-04-27
> **Authors:** KVK, Claude
> **Implements:** ADR-222 implementation roadmap, ADR 1
> **Related:** ADR-222 (OS framing), ADR-198 (surface archetypes), ADR-214 (4-tab nav), ADR-188 (registries as templates), ADR-176 (universal agent roster), FOUNDATIONS Principle 16
> **Depended on by:** Compositor Layer ADR (forthcoming), Kernel/Program Boundary Refactor ADR (forthcoming), Reference-Workspace Activation Flow ADR (forthcoming)

---

## Context

ADR-222 canonized the agent-native operating system framing. `docs/programs/` already hosts three program bundles: `alpha-trader/` (primary, actively built), `alpha-prediction/` and `alpha-defi/` (reference SPECs). Each has organic shape — frontmatter-with-related-links, Oracle Profile, OS stress points, hypothetical scaffolding, activation preconditions, success bar, phase milestones, OS dependencies. The shape converged before being formalized.

This ADR formalizes the bundle layout so:

1. Future bundles share consistent structure (the litmus triangle stays comparable).
2. The forthcoming **Compositor Layer** (ADR forthcoming) has a stable contract to read against — it must know where to find the composition manifest, what schema to expect, what substrate paths it can bind.
3. The forthcoming **Kernel/Program Boundary Refactor** (ADR forthcoming) has a stable target — when program-specific declarations move out of `directory_registry.py` / `task_types.py` / `platform_tools.py`, they must move *into* a known bundle location with a known format.
4. The **Reference-Workspace Activation Flow** (ADR forthcoming) has a stable source — the bundle is what `workspace_init.py` reads when scaffolding a program-bound userspace.

This is a spec-only ADR. No code changes. The three existing bundles will be retroactively brought into compliance in a follow-up commit (sized small) once the spec is ratified.

---

## Decision

### 1. Bundle root and identity

A program bundle lives at `docs/programs/{program-slug}/`. The slug is the canonical program identifier — referenced by `MANDATE.md`, by future `tasks.program_slug` annotations, by activation flows.

Slug rules:
- Lowercase ASCII, hyphens permitted, no underscores.
- Stable for the program's lifetime — a slug rename is a breaking change requiring deprecation discipline (kept in tandem with ADR-209 authored substrate principles).
- Globally unique across the `docs/programs/` directory.

Existing slugs (validated): `alpha-trader`, `alpha-prediction`, `alpha-defi`.

### 2. Required files

A compliant bundle has exactly these files at the root:

| File | Format | Purpose | Status field expected |
|---|---|---|---|
| `MANIFEST.yaml` | YAML | Machine-readable program declaration: identity, status, oracle profile, dependencies, capabilities | `active \| reference \| deferred \| archived` |
| `README.md` | Markdown | Operator-and-architect-facing prose: positioning, narrative, success bar, phase milestones, open questions | (free-form) |
| `SURFACES.yaml` | YAML | Composition manifest — declarative spec the compositor reads to render program-bound cockpit surfaces | (none) |
| `reference-workspace/` | Directory | Bundled starter substrate operators fork on activation. File formats per substrate-native conventions (markdown for `*.md`, etc.) — no bundle-specific format constraint here | (per-file) |

Files outside this set are **not** part of the bundle contract (the compositor and activation flow ignore them). They may be present for archival or convenience (e.g., a program's design discourse linked from the README).

**Why split MANIFEST.yaml from README.md.** Today the three bundles use a single `README.md` (or `SPEC.md`) carrying both prose and structured fields in YAML frontmatter. The structured fields belong in a separate machine-readable file because:
- The compositor and activation flow read the structured fields without needing a markdown parser.
- Frontmatter creates a coupling between operator-facing prose and machine-readable contract — changing one tempts changing the other.
- Singular implementation (Principle 7): one file, one purpose.

The existing bundles' frontmatter migrates to MANIFEST.yaml; the prose stays in README.md.

**Why SPEC.md vs README.md is collapsed.** Two of the three current bundles use `SPEC.md`, one uses `README.md`. The split was historical — `SPEC.md` connoted "reference-only" and `README.md` connoted "active program." Under this ADR, `MANIFEST.yaml`'s `status` field carries the active/reference distinction; the prose file is `README.md` for all bundles. The current `alpha-prediction/SPEC.md` and `alpha-defi/SPEC.md` rename to `README.md` in the alignment commit.

### 3. MANIFEST.yaml schema

```yaml
# docs/programs/{slug}/MANIFEST.yaml — machine-readable program declaration
schema_version: 1
slug: alpha-trader
title: alpha-trader
status: active                # active | reference | deferred | archived
date_created: 2026-04-26
date_updated: 2026-04-27

# Brief one-line program description. Used for cockpit chrome, activation UI.
tagline: Equities + options operator workflow with continuous-price oracle.

# Oracle profile — structural property the OS uses to reason about the program.
# Mirrors the prose Oracle table in README.md but typed.
oracle:
  shape: continuous_price       # continuous_price | terminal_binary | onchain_settled | other
  source: alpaca + alpha_vantage
  latency: intraday_marks_daily_settles
  irreversibility: reversible   # reversible | capped | irreversible
  custody: brokerage_held       # brokerage_held | self_custody | platform_held | other
  capital_threshold_usd: 5000

# OS dependencies — what the program needs from the kernel to function.
# Each entry references an ADR or a primitive name. Activation flow
# verifies all required dependencies are shipped before allowing activation.
dependencies:
  required:
    - adr: ADR-209          # authored substrate
    - adr: ADR-195          # OutcomeProvider abstraction
    - adr: ADR-194          # Reviewer with capital-EV reasoning
    - adr: ADR-217          # AUTONOMY.md delegation
    - capability: read_trading
    - capability: write_trading
  lean:                      # depended-on but acceptable to activate without
    - thesis_section: substrate_replay_primitive
    - thesis_section: mandate_outcome_signal_hardening

# Context domains the program scaffolds at activation.
# Each domain is a path under /workspace/context/. Naming follows
# directory_registry.py conventions (post-boundary-refactor, declared here).
context_domains:
  - path: trading            # → /workspace/context/trading/
    purpose: per-instrument entities + signals + universe
    entities:
      - kind: ticker
        files: [_signals.md, _thesis.md]
  - path: portfolio          # → /workspace/context/portfolio/
    purpose: account-level state + performance + risk
    entities:
      - kind: account
        files: [_positions.md, _performance.md, _risk_state.md]

# Task types the program scaffolds.
# Each entry maps to a task type that today lives in task_types.py;
# under the boundary refactor, program-specific types move here.
task_types:
  - key: trading-digest
    output_kind: accumulates_context
    cadence: daily
    purpose: sweep universe, update entity files
  - key: trading-signal
    output_kind: produces_deliverable
    cadence: daily            # or hourly per operator
    purpose: evaluate signals, emit proposal envelope
  - key: trading-execute
    output_kind: external_action
    cadence: reactive
    purpose: Reviewer-approved order submission
  - key: portfolio-review
    output_kind: produces_deliverable
    cadence: weekly
    purpose: performance attribution, regime check, expectancy decay

# Capability bundles the program declares.
# These bind to platform_connections at runtime; if the operator hasn't
# connected the platform, capabilities are inactive (per ADR-207 P3).
capabilities:
  - key: read_trading
    requires_connection: alpaca
  - key: write_trading
    requires_connection: alpaca

# Activation preconditions — what must be true before this bundle can
# graduate from {reference,deferred} to active. Empty list for already-active.
activation_preconditions: []

# Phase milestones — operator-visible lifecycle states inside the program.
# The current_phase value points the cockpit at the right scaffolding.
phases:
  - key: observation
    label: Phase 0 — Observation
  - key: paper_discipline
    label: Phase 1 — Paper Discipline
  - key: live_float
    label: Phase 2 — Live Float
  - key: calibrated_autonomy
    label: Phase 3 — Calibrated Autonomy
  - key: self_funding
    label: Phase 4 — Self-Funding Validated
current_phase: observation

# Cross-references — discovery-only metadata, not load-bearing.
references:
  - docs/alpha/ALPHA-1-PLAYBOOK.md
  - docs/alpha/personas/alpha-trader/MANDATE.md
  - docs/analysis/external-oracle-thesis-2026-04-26.md
```

**Schema discipline:**

- `schema_version: 1` is required and enables future versioned migrations without breaking older bundles in flight.
- `status` values are exhaustive: `active` (program with code), `reference` (SPEC-only litmus), `deferred` (intent recorded, not active), `archived` (retired).
- `oracle.shape` is enumerated. New shapes require an ADR justifying why the existing four don't fit. This is the same anti-vocabulary-proliferation discipline applied to `output_kind` (ADR-166).
- `dependencies.required` blocks activation if any item is unshipped; `dependencies.lean` is informational only.
- `context_domains[*].path` is a relative segment under `/workspace/context/`, never absolute. The kernel registry contains universal directories (`memory`, `uploads`, `review`, `_shared`, `agents`, `tasks`); program-specific domains are declared here and union-loaded at runtime per the boundary refactor.
- `task_types[*].output_kind` is one of the four canonical values (ADR-166): `accumulates_context | produces_deliverable | external_action | system_maintenance`.
- `capabilities[*].requires_connection` references a `platform_connections.platform` value (`slack | notion | github | alpaca | lemon_squeezy | ...`).

### 4. SURFACES.yaml — composition manifest

The composition manifest is the program's declarative cockpit shape. The compositor reads it; nothing else does. Schema:

```yaml
# docs/programs/{slug}/SURFACES.yaml — declarative composition manifest
schema_version: 1

# Per-tab composition. Tabs follow ADR-214's shipped 4-tab nav:
# /chat | /work | /agents | /context. The /chat ambient rail is OS-managed
# and not program-composable; programs may declare quick-ask chips via the
# `chat_chips` field below.
tabs:
  work:
    # The /work tab is list/detail per ADR-167 v2. Programs can:
    # - declare a featured/pinned task (rendered prominent in list mode)
    # - declare task-detail middle overrides for kinds the program owns
    list:
      pinned_tasks: [trading-signal, portfolio-review]
      group_default: output_kind     # output_kind | agent | status | schedule
      filters_default:
        output_kind: produces_deliverable
    detail:
      # Program may register middle-pane overrides keyed on (output_kind, task_slug).
      # If declared, the compositor uses the override; otherwise the universal
      # KindMiddle (Deliverable/Tracking/Action/Maintenance) renders.
      middles:
        - match: { task_slug: portfolio-review }
          archetype: dashboard       # one of ADR-198's five
          # Substrate paths the dashboard binds. Each binding is a path
          # under /workspace/ that the compositor reads at render time.
          bindings:
            performance: /workspace/context/portfolio/_performance.md
            positions: /workspace/context/portfolio/_positions.md
            risk: /workspace/context/portfolio/_risk_state.md
          # Universal components from web/components/library/ used to render.
          components:
            - kind: PerformanceSnapshot
              source: performance
            - kind: PositionsTable
              source: positions
            - kind: RiskBudgetGauge
              source: risk

  agents:
    # /agents shows roster + per-agent detail (ADR-214). Programs can declare
    # featured agents and per-class scaffolding. Reviewer is a synthesized
    # systemic agent — programs may declare `reviewer.principles_default`
    # which ships in reference-workspace/principles.md.
    list:
      featured: [trading-bot, reviewer]
    reviewer:
      principles_default: reference-workspace/review/principles.md

  context:
    # /context is the workspace-substrate browser. Programs declare which
    # domains to feature on the home view; the file browser reads
    # /workspace/context/* universally.
    list:
      featured_domains: [trading, portfolio]

# Program-specific quick-ask chips for the ambient YARNNN rail empty state
# (operator hasn't typed anything yet). Helpful during early activation.
chat_chips:
  - "Walk me through today's signals"
  - "What's my risk budget right now?"
  - "Did anything trigger overnight?"

# Phase-aware overlay — different phases may surface different things.
# The compositor merges base + phase overlay (phase-overlay wins where present).
phase_overlays:
  observation:
    tabs:
      work:
        list:
          banner: "Paper-only. Live trading gated on AUTONOMY.md flip."
  live_float:
    tabs:
      work:
        list:
          banner: "Live capital active. Every order requires Reviewer approval."
```

**Composition manifest discipline:**

- **No HTML, no React, no JSX.** The manifest is declarative — it names archetypes from ADR-198 and components from `web/components/library/`. The compositor is the only place that turns names into rendered output.
- **No dynamic logic.** No conditionals beyond `phase_overlays` (which is a shallow merge, not a runtime expression). If a program needs runtime decision logic, it lives in a back-office task or pipeline, not in the manifest.
- **All bindings are filesystem paths.** No DB queries, no service calls. The compositor reads files; the manifest names which files.
- **Components must exist in the library.** Referencing a component that doesn't exist is a manifest error caught at validation time (compositor pre-flight check). Programs may not ship components in the bundle (per FOUNDATIONS Principle 16's additive-only system component library rule); a program needing a new component contributes it to the library first.
- **Archetypes are exhaustive.** `dashboard | document | queue | briefing | stream` per ADR-198 §3. No other archetype values permitted.
- **Tabs are exhaustive.** `chat | work | agents | context` per ADR-214's shipped 4-tab nav. Future tab additions require an ADR to extend the nav itself.

### 5. reference-workspace/ — bundled starter substrate

The reference workspace is the program's opinion about what a fresh workspace looks like once the program is selected. At activation time, `workspace_init.py` (extension forthcoming in ADR 5) copies these files into the operator's `/workspace/`.

Layout mirrors the post-activation workspace:

```
docs/programs/alpha-trader/reference-workspace/
├── context/
│   └── _shared/
│       ├── IDENTITY.md              # operator-authored — empty placeholder with prompts
│       ├── BRAND.md                 # operator-authored — empty placeholder
│       ├── CONVENTIONS.md           # may include program-typical conventions
│       ├── MANDATE.md               # operator-authored — template with program-specific prompts
│       └── AUTONOMY.md              # delegation file with program-typical defaults
├── review/
│   ├── IDENTITY.md                  # Reviewer persona (e.g., Simons-style for alpha-trader)
│   └── principles.md                # program-typical principles (sizing, signal attribution)
├── memory/
│   └── awareness.md                 # YARNNN orchestration state, empty
└── tasks/                           # NOT scaffolded here — tasks are operator/YARNNN-created
                                     # post-activation; the reference doesn't pre-author tasks
```

**Reference-workspace discipline:**

- **Templates, not prescriptions.** Files contain prompts and structural placeholders, not authored content the operator must accept. The activation conversation (ADR 5) walks the operator through fork-then-author.
- **No tasks pre-scaffolded.** Tasks are created by the operator (via the CreateTask modal) or by YARNNN at the operator's request. The reference doesn't ship tasks — it ships the substrate context tasks will reference.
- **No agents pre-scaffolded.** Per ADR-205, signup scaffolds exactly one agent (YARNNN). User-authored Agents are created post-activation. The reference may ship a `review/IDENTITY.md` opinion (Reviewer is systemic, one per workspace).
- **Redaction discipline.** Reference workspaces are public — they ship as part of the repo. No real numbers, no real customer data, no API keys. ADR 6 (Reference-Reflexive Loop) covers the graduation discipline that keeps the reference clean as lived workspaces feed it.

### 6. Lifecycle states

| Status | Meaning | Cockpit visibility | Activation allowed? |
|---|---|---|---|
| `active` | Program with code paths shipped; an operator may run it today | Visible in any cockpit affordance that lists programs | Yes |
| `reference` | SPEC-only litmus; constrains kernel decisions, no code | Hidden from operator activation UIs; visible to architects (in repo) | No (precondition: graduates to active via ADR) |
| `deferred` | Intent recorded; not active, not actively constraining | Hidden | No |
| `archived` | Retired; preserved as historical artifact | Hidden | No |

Transitions between states are governed by ADRs, not by editing MANIFEST.yaml directly. A `reference` → `active` transition requires the activation_preconditions to be met (each precondition typically references an ADR that has shipped) and an explicit ADR ratifying the activation.

The current registry under this discipline:

| Slug | Status | Rationale |
|---|---|---|
| `alpha-trader` | `active` | Code shipped via ADR-187, ADR-194 v2, ADR-195 v2; primary program |
| `alpha-prediction` | `reference` | SPEC only; activation preconditions listed in its README |
| `alpha-defi` | `reference` | SPEC only; activation preconditions listed in its README |

### 7. Validation rules

A bundle is **compliant** if:

1. `MANIFEST.yaml` parses, has `schema_version: 1`, and all required fields present.
2. `README.md` exists and is non-empty.
3. `SURFACES.yaml` parses, has `schema_version: 1`, and references only known archetypes / known tabs / known components.
4. `reference-workspace/` exists; if `status: active`, it is non-empty.
5. All `dependencies.required` entries reference shipped ADRs or known capabilities.
6. All `context_domains[*].path` and `task_types[*].key` are unique within the bundle.

Validation runs as a CI check (forthcoming) — `python scripts/validate_bundles.py` walks `docs/programs/*/` and asserts each bundle compliant. Failure blocks merge.

### 8. What this ADR does NOT specify

Deferred to subsequent ADRs:

- **Compositor implementation.** How `SURFACES.yaml` is loaded, parsed, resolved against substrate, rendered. ADR forthcoming (Compositor Layer).
- **System component library schema.** What every component must expose, prop conventions, accessibility expectations. ADR forthcoming (System Component Library Convention) — may fold into Compositor ADR.
- **Boundary refactor.** Moving `directory_registry.py` / `task_types.py` / `platform_tools.py` program-specific entries into bundles. ADR forthcoming (Kernel/Program Boundary Refactor).
- **Activation flow.** How an operator selects a program at signup; how `workspace_init.py` reads the bundle and forks the reference workspace. ADR forthcoming (Reference-Workspace Activation Flow).
- **Reflexive loop.** How lived workspace patterns graduate back to the reference. ADR forthcoming (Reference-Reflexive Loop).
- **Workspace overlay.** How operator-authored `/workspace/SURFACES.yaml` overrides interact with the bundle's manifest. Folded into Compositor ADR.
- **Cross-program bundle composition.** Operator running two programs simultaneously. Deferred to second-program activation per the OS roadmap.

---

## Why the format choices

Auditing each format decision against axiomatic fit:

| File | Format | Rationale |
|---|---|---|
| `MANIFEST.yaml` | YAML | Machine-readable contract. Compositor + activation flow + validation script all parse it. Markdown frontmatter was rejected because it couples machine-readable contract to operator-facing prose (singular implementation discipline — Principle 7). |
| `README.md` | Markdown | Operator + architect prose. Native substrate format; same discipline as TASK.md / AGENT.md / MANDATE.md. |
| `SURFACES.yaml` | YAML | Declarative composition spec. Hierarchical, parseable, no executable logic. JSON considered and rejected (less legible for operators reading the file); markdown-with-blocks considered and rejected (parsing complexity for no clarity gain over YAML). |
| `reference-workspace/*.md` | Markdown | Per substrate-native conventions. Whatever format the corresponding live workspace file uses, the reference uses too — the reference IS a workspace, just shipped from the bundle instead of accumulated. |

The principle is: **format follows axiomatic fit**, not bundle uniformity. Files whose primary consumer is humans use markdown; files whose primary consumer is machines use YAML. A future bundle might ship a CSV of fixture data (e.g., `reference-workspace/context/competitors/_seed.csv`) — that's fine; CSV fits its use.

---

## Consequences

### Positive

- **Stable contract for forthcoming infrastructure.** The Compositor, boundary refactor, and activation flow ADRs all have a known target shape to reason against.
- **Bundle structure is enforceable.** The validation script catches drift; CI failure blocks bundles that violate the contract.
- **Existing bundles align cleanly.** `alpha-trader/`, `alpha-prediction/`, `alpha-defi/` all map onto this spec with one straightforward alignment commit (split frontmatter → MANIFEST.yaml; rename SPEC.md → README.md; add SURFACES.yaml; add reference-workspace/ skeleton).
- **Adding a new program is mechanical.** Copy the alpha-trader bundle, edit MANIFEST.yaml, edit README.md, edit SURFACES.yaml, populate reference-workspace/. No kernel touch.
- **Vocabulary discipline holds.** The spec uses **substrate** / **primitive** / **workspace** / **archetype** as architectural canon (already in code and in axioms); the OS-mapping vocabulary (kernel / syscall ABI / userspace / shell) stays in the explainer/GTM register where it earns its keep without burdening implementation.

### Negative / costs

- **Three bundles need an alignment commit.** Mechanical work — split frontmatter, rename one file, add two empty placeholders. ~30 minutes.
- **CI validation script is new infrastructure.** Small Python script (~100 lines) but real to maintain.
- **New file count per bundle.** Three required files + one directory replacing one file. The cost is offset by the contract clarity each file gains by carrying one purpose.

### Risks

- **Schema lock-in too early.** Mitigation: `schema_version: 1` is explicit, and the spec covers only what the current three bundles + the alpha-trader execution path actually need. Future programs with new shapes (e.g., alpha-defi's custody dimension) extend via additive fields, not breaking changes.
- **SURFACES.yaml never gets used because the Compositor doesn't ship.** Mitigation: this ADR commits the *contract*; the Compositor ADR is sequenced next. If the Compositor stalls, the bundle still has a valid MANIFEST.yaml + README.md that future infrastructure can target.
- **Operators eventually want to edit SURFACES.yaml directly.** That's the workspace overlay concern (deferred to Compositor ADR). Bundle-level SURFACES.yaml is platform-authored and ships in the repo; per-workspace overrides are a separate substrate concern.

---

## Migration plan (alignment commit)

After this ADR is ratified, a follow-up commit brings the three existing bundles into compliance. Sized to land in one PR:

1. **`alpha-trader/`**:
   - Split current `README.md` frontmatter → `MANIFEST.yaml`.
   - Trim `README.md` to operator + architect prose only (drop frontmatter).
   - Add `SURFACES.yaml` (initial draft based on the surfaces table currently in README.md §"Surfaces the program needs").
   - Add `reference-workspace/` with the templates listed in §5 above.

2. **`alpha-prediction/`**:
   - Rename `SPEC.md` → `README.md`.
   - Split frontmatter → `MANIFEST.yaml` with `status: reference`.
   - Add `SURFACES.yaml` (sketch only — reference SPECs may ship minimal SURFACES per "no code" discipline).
   - Add `reference-workspace/` skeleton (mostly empty, per `status: reference`).

3. **`alpha-defi/`**: same as alpha-prediction.

4. **`docs/programs/README.md`**: update the program registry table to reference MANIFEST.yaml as the source of truth for status.

5. **`docs/architecture/os-framing-implementation-roadmap.md`**: mark ADR 1 as drafted; flag the alignment commit as the immediate follow-up.

The alignment commit is plain documentation work — no code touched, no schemas changed, no DB migrations. It's the visible payoff of this ADR.

---

## Open questions

Explicitly deferred — none gate ratification.

- **Operator workspace overlay format.** When operators override program defaults (`/workspace/SURFACES.yaml`), is it the same schema as bundle SURFACES.yaml (full override) or a delta schema (sparse patch)? Decided in the Compositor ADR.
- **Bundle versioning when an operator's lived workspace is on bundle v1 and the platform ships bundle v2.** Migration semantics — automatic, opt-in, or operator-approved diff? Decided when the second bundle version actually ships (not before).
- **Marketing-facing rendering of bundles.** Public pages on yarnnn.com/programs/alpha-trader rendered from MANIFEST.yaml + README.md. Real opportunity, deferred until marketing pressure.
- **Bundle dependency graph.** Programs may share components (e.g., all three alpha-* programs would share Reviewer principles patterns). Whether to express dependency-between-bundles or whether shared content lives in the system component library only — decided when the second bundle activates.

---

## Decision

**Adopt the program bundle specification as defined above.** Bundle root at `docs/programs/{slug}/`; required files `MANIFEST.yaml`, `README.md`, `SURFACES.yaml`, `reference-workspace/`. YAML for machine-readable, markdown for prose, native conventions for reference workspace contents. Lifecycle states `active | reference | deferred | archived`. The three current bundles align to this spec via a follow-up commit. Subsequent ADRs (Compositor Layer, Boundary Refactor, Activation Flow, Reflexive Loop) target this contract.
