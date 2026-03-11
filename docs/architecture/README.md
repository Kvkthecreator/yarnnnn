# Architecture Documentation Index

> **Last updated**: 2026-03-03 (ADR-087 workspace architecture + canonical docs)

---

## Architecture Docs (`docs/architecture/`)

| Document | Status | Last Updated | Covers |
|----------|--------|-------------|--------|
| [backend-orchestration.md](backend-orchestration.md) | **Hardened** (v3.1) | 2026-02-27 | 4 Render services (ADR-083), 10 background features (F1–F10), scheduler phase map, env var matrix |
| [agent-model-comparison.md](agent-model-comparison.md) | **Canonical** | 2026-03-03 | YARNNN's agent model vs Claude Code (tool) vs OpenClaw (agent). Position, conviction, decision tests. |
| [naming-conventions.md](naming-conventions.md) | **Canonical** | 2026-03-03 | Full naming strategy: Tier 1 (user-facing) → Tier 2 (developer) → Tier 3 (architecture). Dev ↔ frontend ↔ GTM alignment. Naming debt. |
| [agent-execution-model.md](agent-execution-model.md) | Current | 2026-02-26 | Unified agent (chat + headless modes), mode-gated primitives (ADR-080) |
| [context-pipeline.md](context-pipeline.md) | Current | 2026-02-27 | Four-layer model, platform_content, memory, sync frequency, TP access patterns |
| [agents.md](agents.md) | Current | 2026-02-26 | Agent lifecycle, 8 active types (ADR-082), execution model, delivery routing |
| [four-layer-model.md](four-layer-model.md) | Current | 2026-02-26 | Memory / Activity / Context / Work conceptual model |
| [primitives.md](primitives.md) | Current | 2026-02-27 | 9 TP primitives, reference syntax, entity schemas |
| [signal-taxonomy.md](signal-taxonomy.md) | Current | 2026-02-27 | Signal types, agent type mapping, 8 active types (ADR-082) |
| [supervision-model.md](supervision-model.md) | Current | 2026-02-26 | UI/UX supervision model (product framing) |
| [tp-prompt-guide.md](tp-prompt-guide.md) | Current | 2026-02-27 | TP prompt versioning (v1–v6.1), design decisions, platform tool docs |
| [mcp-integration-system.md](mcp-integration-system.md) | **Archived** | 2026-02-27 | Redirect stub — MCP Gateway deleted per ADR-076 |

## Feature Docs (`docs/features/`)

| Document | Status | Last Updated | Covers |
|----------|--------|-------------|--------|
| [activity.md](../features/activity.md) | Current | 2026-02-26 | activity_log table, event types, write/read paths |
| [context.md](../features/context.md) | Current | 2026-02-25 | platform_content table, retention semantics, sync methods |
| [memory.md](../features/memory.md) | Current | 2026-02-20 | user_memory table, three write paths, working memory format |
| [sessions.md](../features/sessions.md) | Current | 2026-02-27 | Session lifecycle (ADR-067), inactivity boundary, compaction |
| [email-notifications.md](../features/email-notifications.md) | Current | 2026-02-27 | Resend email delivery, templates, preferences |
| [tp-configuration.md](../features/tp-configuration.md) | **Archived** | 2026-02-27 | Redirect stub — superseded by tp-prompt-guide.md |

## Analysis Docs (`docs/analysis/`)

| Document | Status | Last Updated | Covers |
|----------|--------|-------------|--------|
| [workspace-architecture-landscape.md](../analysis/workspace-architecture-landscape.md) | **Living** | 2026-03-03 | Compass for ADR-087/088/089. Implementation sequence, architecture mapping, naming debt, decision log |
| [workspace-architecture-analysis-2026-03-02.md](../analysis/workspace-architecture-analysis-2026-03-02.md) | **Archive** | 2026-03-03 | Full v1–v5 analysis: FK-scoping → JSONB → typed files → OpenClaw comparison → consolidation |

## Key ADRs (Workspace Architecture)

| ADR | Status | Covers |
|-----|--------|--------|
| [ADR-087: Agent Scoped Context](../adr/ADR-087-workspace-scoping-architecture.md) | Proposed | `agent_instructions` + `agent_memory` on agents, `agent_id` on chat_sessions |
| [ADR-088: Unified Input Processing](../adr/ADR-088-input-gateway-work-serialization.md) | Proposed | `process_agent_input()` — graduated response routing. Implements as ADR-087 Phase 2 |
| [ADR-089: Agent Autonomy](../adr/ADR-089-agent-autonomy-context-aware-triggers.md) | Parked | Heartbeats, context-aware triggers, lighter-than-generation actions. Gated by ADR-088 validation |

## Archived (`docs/architecture/previous_versions/`)

Historical documents preserved for reference. Do not use for current architecture decisions.

- `mcp-integration-system.md` — pre-ADR-076 MCP Gateway architecture
- `tp-configuration.md` — pre-v3 TP prompt configuration (Jan–Feb 2025)
- `DECISION-001-platform-sync-strategy.md` — early platform sync decision
- `INTEGRATION_FIRST_POSITIONING.md` — early product positioning
- `YARNNN_STRATEGIC_DIRECTION.md` — early strategic direction
- `activity-log-implementation-plan.md` — activity log implementation plan
- `primitives-analogy.md` — primitives conceptual analogy

## Reading Order

For someone new to the codebase:

1. **[agent-model-comparison.md](agent-model-comparison.md)** — why YARNNN's model exists (start here)
2. **[naming-conventions.md](naming-conventions.md)** — the vocabulary
3. **[four-layer-model.md](four-layer-model.md)** — conceptual foundation
4. **[backend-orchestration.md](backend-orchestration.md)** — how everything runs
5. **[context-pipeline.md](context-pipeline.md)** — how data flows
6. **[agent-execution-model.md](agent-execution-model.md)** — how the agent works
7. **[agents.md](agents.md)** — the core product output

## Database

- [SCHEMA.md](../database/SCHEMA.md) — complete table definitions, four-layer model, working memory format
- [ACCESS.md](../database/ACCESS.md) — connection strings and psql commands
