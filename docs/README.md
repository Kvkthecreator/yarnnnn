# YARNNN v5 Documentation

**The source of truth for YARNNN development.**

## Current Architecture (as of 2026-02-13)

> **Active ADRs:**
> - [ADR-058: Knowledge Base Architecture](adr/ADR-058-knowledge-base-architecture.md) — Two-layer context model (Filesystem + Knowledge)
> - [ADR-036: Two-Layer Architecture](adr/ADR-036-two-layer-architecture.md) — Foundational framework (Interaction + Infrastructure)
> - [ADR-037: Chat-First Surface Architecture](adr/ADR-037-chat-first-surface-architecture.md) — Frontend manifestation (Chat = Home)
>
> The system follows a **Two-Layer Architecture**: Chat-first interaction layer backed by structured infrastructure. Context is organized as **Filesystem** (raw synced data) + **Knowledge** (inferred narrative), with Working Memory injected into TP's prompt.

## Quick Links

| Document | Purpose |
|----------|---------|
| [ESSENCE.md](ESSENCE.md) | Core product spec - domain model, agents, data flow |
| [architecture/primitives.md](architecture/primitives.md) | **Canonical** — Universal TP primitives specification |
| [ADR-058](adr/ADR-058-knowledge-base-architecture.md) | **Current** — Knowledge Base Architecture (Filesystem + Knowledge) |
| [ADR-036](adr/ADR-036-two-layer-architecture.md) | **Current** — Two-Layer Architecture framework |
| [ADR-037](adr/ADR-037-chat-first-surface-architecture.md) | **Current** — Chat-First Surface Architecture |
| [database/ACCESS.md](database/ACCESS.md) | Database connection strings and credentials |
| [development/SETUP.md](development/SETUP.md) | Local development setup |
| [testing/TESTING-ENVIRONMENT.md](testing/TESTING-ENVIRONMENT.md) | Testing patterns and environment |
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
| Database Schema | ADR-058 schema (Filesystem + Knowledge tables) | [database/](database/) |
| Context System | Filesystem + Knowledge + Working Memory | [ADR-058](adr/ADR-058-knowledge-base-architecture.md) |
| API Routes | Complete (integrations, context, deliverables, chat) | - |
| Agents | ThinkingPartner, Synthesizer, Deliverable, Report | - |
| Frontend | Chat-first with surfaces, Context page | - |

## Related Repos (Reference Only)

These repos contain patterns we learned from but are not part of v5:

- `yarnnn-app-fullstack` - Block state machine, governance layer (over-engineered)
- `chat_companion` - Memory extraction, pgvector embeddings, temporal expiry
