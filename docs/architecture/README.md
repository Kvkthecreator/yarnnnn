# Architecture Documentation Index

> **Last updated**: 2026-02-27 (consistency sweep)

---

## Architecture Docs (`docs/architecture/`)

| Document | Status | Last Updated | Covers |
|----------|--------|-------------|--------|
| [backend-orchestration.md](backend-orchestration.md) | **Hardened** (v3.0) | 2026-02-27 | 5 Render services, 10 background features (F1–F10), scheduler phase map, env var matrix |
| [agent-execution-model.md](agent-execution-model.md) | Current | 2026-02-26 | Unified agent (chat + headless modes), mode-gated primitives (ADR-080) |
| [context-pipeline.md](context-pipeline.md) | Current | 2026-02-27 | Four-layer model, platform_content, memory, sync frequency, TP access patterns |
| [deliverables.md](deliverables.md) | Current | 2026-02-26 | Deliverable lifecycle, 8 active types (ADR-082), execution model, delivery routing |
| [four-layer-model.md](four-layer-model.md) | Current | 2026-02-26 | Memory / Activity / Context / Work conceptual model |
| [primitives.md](primitives.md) | Current | 2026-02-27 | 9 TP primitives, reference syntax, entity schemas |
| [signal-taxonomy.md](signal-taxonomy.md) | Current | 2026-02-27 | Signal types, deliverable type mapping, 8 active types (ADR-082) |
| [supervision-model.md](supervision-model.md) | Current | 2026-02-26 | UI/UX supervision model (product framing) |
| [tp-prompt-guide.md](tp-prompt-guide.md) | Current | 2026-02-27 | TP prompt versioning (v1–v6.1), design decisions, platform tool docs |
| [mcp-integration-system.md](mcp-integration-system.md) | **Archived** | 2026-02-27 | Redirect stub — MCP Gateway deleted per ADR-076 |

## Feature Docs (`docs/features/`)

| Document | Status | Last Updated | Covers |
|----------|--------|-------------|--------|
| [activity.md](../features/activity.md) | Current | 2026-02-26 | activity_log table, event types, write/read paths |
| [context.md](../features/context.md) | Current | 2026-02-25 | platform_content table, retention semantics, sync methods |
| [memory.md](../features/memory.md) | Current | 2026-02-20 | user_context table, three write paths, working memory format |
| [sessions.md](../features/sessions.md) | Current | 2026-02-27 | Session lifecycle (ADR-067), inactivity boundary, compaction |
| [email-notifications.md](../features/email-notifications.md) | Current | 2026-02-27 | Resend email delivery, templates, preferences |
| [tp-configuration.md](../features/tp-configuration.md) | **Archived** | 2026-02-27 | Redirect stub — superseded by tp-prompt-guide.md |

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

1. **[four-layer-model.md](four-layer-model.md)** — conceptual foundation
2. **[backend-orchestration.md](backend-orchestration.md)** — how everything runs
3. **[context-pipeline.md](context-pipeline.md)** — how data flows
4. **[agent-execution-model.md](agent-execution-model.md)** — how the agent works
5. **[deliverables.md](deliverables.md)** — the core product output

## Database

- [ACCESS.md](../database/ACCESS.md) — connection strings and psql commands
