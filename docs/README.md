# YARNNN v5 Documentation

**The source of truth for YARNNN development.**

## Current Architecture (as of 2026-02-23)

> **Active ADRs:**
> - [ADR-072: Unified Content Layer](adr/ADR-072-unified-content-layer-tp-execution-pipeline.md) — `platform_content` with retention-based accumulation
> - [ADR-073: Unified Fetch Architecture](adr/ADR-073-unified-fetch-architecture.md) — Single fetch path, all consumers read from `platform_content`
> - [ADR-063: Four-Layer Model](adr/ADR-063-activity-log-four-layer-model.md) — Memory / Activity / Context / Work
> - [ADR-064: Unified Memory Service](adr/ADR-064-unified-memory-service.md) — Implicit memory, nightly extraction
>
> The system follows a **Four-Layer Model**: Memory (`user_context`), Activity (`activity_log`), Context (`platform_content`), and Work (`deliverable_versions`). Platform content flows through a single fetch path (sync worker only) and accumulates based on significance.

## Quick Links

| Document | Purpose |
|----------|---------|
| [ESSENCE.md](ESSENCE.md) | Core product spec - domain model, agents, data flow |
| [architecture/primitives.md](architecture/primitives.md) | **Canonical** — Universal TP primitives specification |
| [ADR-072](adr/ADR-072-unified-content-layer-tp-execution-pipeline.md) | **Current** — Unified Content Layer (`platform_content`) |
| [ADR-073](adr/ADR-073-unified-fetch-architecture.md) | **Current** — Unified Fetch Architecture |
| [ADR-063](adr/ADR-063-activity-log-four-layer-model.md) | **Current** — Four-Layer Model |
| [integrations/RENDER-SERVICES.md](integrations/RENDER-SERVICES.md) | Render service infrastructure + env var parity |
| [integrations/PLATFORM-INTEGRATIONS.md](integrations/PLATFORM-INTEGRATIONS.md) | Platform sync pipeline + per-platform specs |
| [database/ACCESS.md](database/ACCESS.md) | Database connection strings and credentials |
| [adr/](adr/) | Architecture Decision Records |

## Folder Structure

```
docs/
├── ESSENCE.md           # Product bible - domain model, agents, constraints
├── README.md            # This file
│
├── adr/                 # Architecture Decision Records
│   ├── README.md        # ADR template and index
│   ├── ADR-001-*.md     # Numbered decisions
│   └── ...
│
├── architecture/        # Canonical architecture specifications
│   ├── primitives.md    # TP primitives (Read, Write, Edit, etc.)
│   └── mcp-integration-system.md
│
├── analysis/            # Research and comparative analysis
│   └── *.md             # Cross-repo learnings, technical research
│
├── database/            # Database documentation
│   ├── ACCESS.md        # Connection strings, credentials
│   ├── SCHEMA.md        # Table descriptions and relationships
│   └── MIGRATIONS.md    # Migration history and notes
│
├── development/         # Developer guides
│   ├── SETUP.md         # Local environment setup
│   └── ...
│
├── testing/             # Testing documentation
│   ├── README.md        # Testing philosophy and links
│   ├── TESTING-ENVIRONMENT.md  # Environment setup and patterns
│   └── ...
│
├── features/            # Feature specifications
│   └── *.md             # Per-feature documentation
│
└── operations/          # Ops and troubleshooting
    └── TROUBLESHOOTING.md
```

## Documentation Standards

### When to Write Docs

1. **ADRs**: Any significant architectural decision (new library, pattern change, trade-off)
2. **Analysis**: Research that informs future work (cross-repo learnings, spikes)
3. **Features**: Before implementing non-trivial features
4. **Operations**: After encountering and solving production issues

### ADR Format

See [adr/README.md](adr/README.md) for template.

### Naming Conventions

- **ADRs**: `ADR-NNN-short-title.md` (e.g., `ADR-001-memory-architecture.md`)
- **Analysis**: Descriptive title in SCREAMING_SNAKE_CASE
- **Features**: Feature name in SCREAMING_SNAKE_CASE

## Current State

| Component | Status | Doc |
|-----------|--------|-----|
| Domain Model | Defined | [ESSENCE.md](ESSENCE.md) |
| Context System | `platform_content` with retention (ADR-072) | [features/context.md](features/context.md) |
| Sync Pipeline | Single fetch path, Worker + Scheduler (ADR-073) | [integrations/PLATFORM-INTEGRATIONS.md](integrations/PLATFORM-INTEGRATIONS.md) |
| Memory | Implicit, nightly extraction (ADR-064) | [features/memory.md](features/memory.md) |
| Infrastructure | 4 Render services (API, Worker, Scheduler, MCP Gateway) | [integrations/RENDER-SERVICES.md](integrations/RENDER-SERVICES.md) |
| Frontend | Chat-first, Context page, System admin page | - |

## Related Repos (Reference Only)

These repos contain patterns we learned from but are not part of v5:

- `yarnnn-app-fullstack` - Block state machine, governance layer (over-engineered)
- `chat_companion` - Memory extraction, pgvector embeddings, temporal expiry
