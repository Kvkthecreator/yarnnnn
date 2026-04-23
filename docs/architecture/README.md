# Architecture Documentation Index

> **Last updated**: 2026-04-23 (THESIS.md + reviewer-substrate.md added as canonical)

---

## Canonical Docs (`docs/architecture/`)

The canon is stacked: **THESIS** (the philosophical claim the architecture exists to express) → **FOUNDATIONS** (the axiomatic structure that must hold) → **substrate canons** (how specific architectural commitments are expressed in files). Start with SERVICE-MODEL.md to understand how the system works today; start with THESIS.md to understand why the system is shaped the way it is.

### Thesis + Axioms

| Document | Covers |
|----------|--------|
| [**THESIS.md**](THESIS.md) | The philosophical thesis — four architectural commitments (declared intent, independent judgment, ground-truth evaluation, authored accumulation), falsifiable predictions, dual-use terminal vision. **Internal canon; not external messaging.** |
| [**FOUNDATIONS.md**](FOUNDATIONS.md) | First-principles axioms — all ADRs derive from these. Six-dimensional model, filesystem-as-substrate, four cognitive layers, money-truth, fourteen Derived Principles. |
| [**GLOSSARY.md**](GLOSSARY.md) | Canonical vocabulary — one word, one concept, one layer. |

### Substrate canons

Parallel deep-dives on the two sharpest architectural substrates — the write path and the judgment seat. Each is sibling to the other and downstream of FOUNDATIONS.

| Document | Covers |
|----------|--------|
| [**authored-substrate.md**](authored-substrate.md) | Content-addressed retention + parent-pointer history + authored-by attribution on every `workspace_files` mutation. Ratified by FOUNDATIONS v6.1 Axiom 1 second clause + ADR-209. |
| [**reviewer-substrate.md**](reviewer-substrate.md) | The Reviewer seat's filesystem expression — seven files at `/workspace/review/`, the prospective-attribution contract, operational modes vocabulary, calibration loop. Ratified by FOUNDATIONS v6.3 + THESIS commitment 2. |

### System operation

| Document | Covers |
|----------|--------|
| [**SERVICE-MODEL.md**](SERVICE-MODEL.md) | End-to-end system description — entities, execution, services, primitives, perception |
| [agent-framework.md](agent-framework.md) | Agent type registry (v4 domain-steward model), capabilities, runtimes |
| [agent-execution-model.md](agent-execution-model.md) | 3-layer execution model (mechanical scheduling, LLM generation, TP orchestration) |
| [**execution-loop.md**](execution-loop.md) | The accumulation cycle — how run N feeds run N+1 (awareness, tracker, feedback, actuation) |
| [backend-orchestration.md](backend-orchestration.md) | 4 Render services, scheduler phase map, LLM cost surface, env var matrix |
| [workspace-conventions.md](workspace-conventions.md) | Filesystem layout, directory registry, lifecycle conventions |
| [registry-matrix.md](registry-matrix.md) | Agent types × task types × output categories — the full registry catalog |
| [primitives-matrix.md](primitives-matrix.md) | Primitives × substrate × mode × capability — the full primitive surface (ADR-168) |
| [task-type-orchestration.md](task-type-orchestration.md) | Task type registry, mode semantics, pipeline integration |
| [output-substrate.md](output-substrate.md) | Three-registry architecture (ADR-130), HTML-native output, compose engine |
| [YARNNN-DESIGN-PRINCIPLES.md](YARNNN-DESIGN-PRINCIPLES.md) | Design principles — Spectrum A/B framing, loosening-with-Reviewer-gate |
| [naming-conventions.md](naming-conventions.md) | Naming strategy: user-facing → developer → architecture tiers |

`registry-matrix.md` and `primitives-matrix.md` are siblings: the former describes **what** the system works on (domains, tasks, agents); the latter describes **how** the system acts on it (primitives, dispatch paths, permission modes).

## Reading Order

For someone new to the codebase:

1. **[SERVICE-MODEL.md](SERVICE-MODEL.md)** — how the system works (start here)
2. **[FOUNDATIONS.md](FOUNDATIONS.md)** — why it works this way, axiomatically
3. **[THESIS.md](THESIS.md)** — the philosophical claim the axioms exist to express (internal canon)
4. **[authored-substrate.md](authored-substrate.md)** + **[reviewer-substrate.md](reviewer-substrate.md)** — the two sharpest architectural substrates (write path + judgment seat)
5. **[agent-framework.md](agent-framework.md)** — agent types and capabilities
6. **[execution-loop.md](execution-loop.md)** — the accumulation cycle (how recurring work compounds)
7. **[workspace-conventions.md](workspace-conventions.md)** — the filesystem model
8. **[backend-orchestration.md](backend-orchestration.md)** — how everything runs
9. **[registry-matrix.md](registry-matrix.md)** — the full type catalog
10. **[primitives-matrix.md](primitives-matrix.md)** — the full primitive surface

## Archived (`docs/architecture/previous_versions/`)

Historical documents preserved for reference. Do not use for current architecture decisions.

- `yarnnn-agent-platform.md` — pre-ADR-138 project/PM investor-facing architecture
- `four-layer-model.md` — ADR-063 Memory/Activity/Context/Work model (superseded by ADR-138/142)
- `agent-model-comparison.md` — ADR-092 era agent model comparison (model has changed 3x since)
- `tp-prompt-guide.md` — TP prompt v6.1 guide (TP rewritten multiple times since)
- `VALUE-CHAIN.md` — ADR-132 era value realization chain (superseded by ADR-138)
- `supervision-model.md` — early UI/UX supervision framing (core insight absorbed into FOUNDATIONS.md Axiom 5)
- `mcp-integration-system.md` — pre-ADR-076 MCP Gateway architecture
- `tp-configuration.md` — pre-v3 TP prompt configuration
- `DECISION-001-platform-sync-strategy.md` — early platform sync decision
- `INTEGRATION_FIRST_POSITIONING.md` — early product positioning
- `YARNNN_STRATEGIC_DIRECTION.md` — early strategic direction
- `activity-log-implementation-plan.md` — activity log implementation plan
- `primitives-analogy.md` — primitives conceptual analogy
- `agents-pre-118.md` — pre-ADR-118 agent architecture

## Database

- [SCHEMA.md](../database/SCHEMA.md) — complete table definitions
- [ACCESS.md](../database/ACCESS.md) — connection strings and psql commands
