# Architecture Documentation Index

> **Last updated**: 2026-04-01 (cleanup sweep — stale docs archived, ADR-153 updates)

---

## Canonical Docs (`docs/architecture/`)

Start with SERVICE-MODEL.md — it's the single entry point for how the system works.

| Document | Covers |
|----------|--------|
| [**SERVICE-MODEL.md**](SERVICE-MODEL.md) | End-to-end system description — entities, execution, services, primitives, perception |
| [**FOUNDATIONS.md**](FOUNDATIONS.md) | First-principles axioms — all ADRs derive from these |
| [agent-framework.md](agent-framework.md) | Agent type registry (v4 domain-steward model), capabilities, runtimes |
| [agent-execution-model.md](agent-execution-model.md) | 3-layer execution model (mechanical scheduling, LLM generation, TP orchestration) |
| [backend-orchestration.md](backend-orchestration.md) | 4 Render services, scheduler phase map, LLM cost surface, env var matrix |
| [workspace-conventions.md](workspace-conventions.md) | Filesystem layout, directory registry, lifecycle conventions |
| [registry-matrix.md](registry-matrix.md) | Agent types × task types × output categories — the full registry catalog |
| [task-type-orchestration.md](task-type-orchestration.md) | Task type registry, mode semantics, pipeline integration |
| [output-substrate.md](output-substrate.md) | Three-registry architecture (ADR-130), HTML-native output, compose engine |
| [naming-conventions.md](naming-conventions.md) | Naming strategy: user-facing → developer → architecture tiers |

## Reading Order

For someone new to the codebase:

1. **[SERVICE-MODEL.md](SERVICE-MODEL.md)** — how the system works (start here)
2. **[FOUNDATIONS.md](FOUNDATIONS.md)** — why it works this way
3. **[agent-framework.md](agent-framework.md)** — agent types and capabilities
4. **[workspace-conventions.md](workspace-conventions.md)** — the filesystem model
5. **[backend-orchestration.md](backend-orchestration.md)** — how everything runs
6. **[registry-matrix.md](registry-matrix.md)** — the full type catalog

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
