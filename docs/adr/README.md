# Architecture Decision Records

ADRs document significant architectural decisions made during development.

## Active ADRs

These are the current, active decision records that define yarnnn's architecture. Ordered by concern area.

### Foundation (Schema, Memory, Content)

| ADR | Title | Status |
|-----|-------|--------|
| [059](ADR-059-simplified-context-model.md) | Simplified Context Model | Accepted |
| [064](ADR-064-unified-memory-service.md) | Unified Memory Service | Accepted |
| [067](ADR-067-session-compaction-architecture.md) | Session Compaction & Continuity | Implemented |
| [072](ADR-072-unified-content-layer-tp-execution-pipeline.md) | Unified Content Layer & TP Execution Pipeline | **Superseded by ADR-153** |

### Platform Sync & Integrations

| ADR | Title | Status |
|-----|-------|--------|
| [075](ADR-075-mcp-connector-architecture.md) | MCP Connector Architecture | Implemented |
| [076](ADR-076-eliminate-mcp-gateway.md) | Eliminate MCP Gateway (Direct API) | Implemented |
| [077](ADR-077-platform-sync-overhaul.md) | Platform Sync Overhaul | **Superseded by ADR-153** |
| [085](ADR-085-refresh-platform-content-primitive.md) | RefreshPlatformContent Primitive | **Superseded by ADR-153** |
| [086](ADR-086-sync-failure-visibility.md) | Sync Failure Visibility | Implemented |
| [100](ADR-100-simplified-monetization.md) | Simplified Monetization (2-tier) | Implemented |
| [112](ADR-112-sync-efficiency-concurrency-control.md) | Sync Efficiency & Concurrency Control | Implemented |
| [113](ADR-113-auto-source-selection.md) | Auto Source Selection | Implemented |

### Agent Framework & Execution

| ADR | Title | Status |
|-----|-------|--------|
| [080](ADR-080-unified-agent-modes.md) | Unified Agent Modes | Implemented |
| [081](ADR-081-execution-path-consolidation.md) | Execution Path Consolidation | Implemented |
| [087](ADR-087-workspace-scoping-architecture.md) | Workspace Scoping Architecture | Implemented |
| [088](ADR-088-input-gateway-work-serialization.md) | Input Gateway & Work Serialization | Phase 1 Implemented |
| [090](ADR-090-work-tickets-consolidation.md) | Work Tickets Consolidation | Phases 1-3 Complete |
| [092](ADR-092-agent-intelligence-mode-taxonomy.md) | Agent Intelligence & Mode Taxonomy | Phase 5 Implemented |
| [101](ADR-101-agent-intelligence-model.md) | Agent Intelligence Model | Implemented |
| [102](ADR-102-yarnnn-content-platform.md) | Yarnnn Content Platform | Implemented |
| [103](ADR-103-agentic-framework-reframe.md) | Agentic Framework Reframe | Implemented |
| [104](ADR-104-agent-instructions-unified-targeting.md) | Agent Instructions as Unified Targeting | Implemented |
| [105](ADR-105-instructions-chat-surface-migration.md) | Instructions to Chat Surface Migration | Implemented |
| [109](ADR-109-agent-framework.md) | Agent Framework — Scope × Role × Trigger | Implemented (pending role rename) |

### Workspace, Skills & Output

| ADR | Title | Status |
|-----|-------|--------|
| [106](ADR-106-agent-workspace-architecture.md) | Agent Workspace Architecture | Phase 1 Complete |
| [107](ADR-107-knowledge-filesystem-architecture.md) | Knowledge Filesystem Architecture | Implemented |
| [108](ADR-108-user-memory-filesystem-migration.md) | User Memory Filesystem Migration | Implemented |
| [116](ADR-116-agent-identity-inter-agent-knowledge.md) | Agent Identity & Inter-Agent Knowledge | Implemented |
| [118](ADR-118-skills-as-capability-layer.md) | Skills as Capability Layer | Phase A+B+C Implemented, D Proposed |
| [119](ADR-119-workspace-filesystem-architecture.md) | Workspace Filesystem Architecture | Proposed |

### Composer & Agent Lifecycle

| ADR | Title | Status |
|-----|-------|--------|
| [110](ADR-110-onboarding-bootstrap.md) | Onboarding Bootstrap | Implemented |
| [111](ADR-111-agent-composer.md) | Agent Composer | Implemented (dissolved by ADR-156) |
| [114](ADR-114-composer-substrate-aware-assessment.md) | Composer Substrate-Aware Assessment | **Superseded by ADR-156** |
| [115](ADR-115-composer-workspace-density-model.md) | Composer Workspace Density Model | Proposed |
| [117](ADR-117-agent-feedback-substrate-developmental-model.md) | Agent Feedback Substrate & Developmental Model | Proposed (identity split clarified by ADR-189) |
| [156](ADR-156-composer-sunset-single-intelligence-layer.md) | Composer Sunset — Single Intelligence Layer | Phase 1 Implemented |

### Three-Layer Cognition Evolution (ADR-138 → ADR-189)

The current cognitive architecture evolved through a series of decisions. ADR-189 is the current canonical reference; the preceding ADRs remain as historical record of how we got there.

| ADR | Title | Status |
|-----|-------|--------|
| [138](ADR-138-agents-as-work-units.md) | Agents as Work Units — Project Layer Collapse | Phases 1-4 Implemented |
| [164](ADR-164-back-office-tasks-tp-as-agent.md) | Back Office Tasks — TP as Agent | Phase 4 Implemented |
| [176](ADR-176-work-first-agent-model.md) | Work-First Agent Model | Implemented (Decision 1 superseded by ADR-189) |
| [186](ADR-186-tp-prompt-profiles.md) | TP Prompt Profiles | Phase 1-3 Implemented |
| [188](ADR-188-domain-agnostic-framework.md) | Domain-Agnostic Framework — Registries as Template Libraries | Phases 1-2 Implemented (Phase 3+ completed by ADR-205) |
| [189](ADR-189-three-layer-cognition.md) | Three-Layer Cognition — YARNNN, Specialists, Agents | Proposed — canonical (Phase 2 pragmatic preservation reversed by ADR-205) |
| [205](ADR-205-primitive-collapse.md) | Workspace Primitive Collapse — YARNNN as Sole Persistent Identity | Backend Implemented, F1+F2+F5 Shipped (F2 framing extended by ADR-206) |
| [206](ADR-206-operation-first-scaffolding.md) | Operation-First Scaffolding — Intent / Deliverables / Operation | Phase 1 Backend Implemented — Phases 2+3 Proposed |

### Canonical Terminology

| Document | Purpose |
|----------|---------|
| [GLOSSARY.md](../architecture/GLOSSARY.md) | **Canonical terminology** (ratified by ADR-189). One word, one concept, one layer. |

## Archived ADRs

Decisions from earlier phases of development (ADR-001 through ADR-058, plus superseded decisions from later phases) are in `archive/`. These are preserved for historical reference but describe superseded patterns.

**Recent archival moves (2026-04-17, Phase 5 of ADR-189):**
- `archive/ADR-140-agent-workforce-model.md` — ICP roster model, superseded by ADR-176 and ADR-189
- `archive/ADR-175-generic-roster-model.md` — never implemented, superseded same-day by ADR-176, further clarified by ADR-189

## Canonical Architecture Docs

Beyond ADRs, see [architecture/](../architecture/) for canonical specifications:

| Document | Purpose |
|----------|---------|
| [agent-framework.md](../architecture/agent-framework.md) | Scope × Role × Trigger taxonomy (canonical) |
| [FOUNDATIONS.md](../architecture/FOUNDATIONS.md) | Core axioms and developmental model |
| [primitives.md](../architecture/primitives.md) | Agent primitives reference |
| [workspace-conventions.md](../architecture/workspace-conventions.md) | Workspace path conventions |

## Conventions

- Sequential numbering (don't reuse numbers)
- Mark superseded ADRs with `Status: Superseded by ADR-XXX`
- Archive when fully absorbed by later decisions
- Reference canonical docs (architecture/) for living specifications
