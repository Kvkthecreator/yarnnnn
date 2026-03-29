# YARNNN Documentation

**The source of truth for YARNNN product narrative, architecture, and implementation decisions.**

## Current Canon (as of 2026-03-29)

**Start here**: [architecture/SERVICE-MODEL.md](architecture/SERVICE-MODEL.md) — the single end-to-end description of how YARNNN works. Entities, execution flow, services, primitives, perception.

The current product story:

- YARNNN is an autonomous agent platform for recurring knowledge work
- Persistent agents + accumulated context = the value proposition
- Users supervise a running system instead of repeatedly operating prompts
- Task types are the product surface — deliverable-first, not agent-first

## Quick Links

| Document | Purpose |
|----------|---------|
| [architecture/SERVICE-MODEL.md](architecture/SERVICE-MODEL.md) | **How the system works end-to-end** |
| [ESSENCE.md](ESSENCE.md) | Product narrative and value proposition |
| [architecture/FOUNDATIONS.md](architecture/FOUNDATIONS.md) | First-principles cognitive architecture |
| [architecture/agent-framework.md](architecture/agent-framework.md) | Agent taxonomy and type registry |
| [architecture/agent-execution-model.md](architecture/agent-execution-model.md) | Execution model and trigger taxonomy |
| [architecture/task-type-orchestration.md](architecture/task-type-orchestration.md) | Task type registry and process execution |
| [architecture/workspace-conventions.md](architecture/workspace-conventions.md) | Workspace filesystem (4 roots) |
| [architecture/output-substrate.md](architecture/output-substrate.md) | Output capabilities and rendering |
| [adr/](adr/) | Architecture Decision Records (65 ADRs) |

## Folder Structure

```
docs/
├── ESSENCE.md           # Canonical product narrative
├── README.md            # This file
│
├── adr/                 # Architecture Decision Records
│   ├── README.md        # ADR template and index
│   ├── archive/         # Superseded ADRs
│   └── ADR-*.md
│
├── architecture/        # Canonical architecture specifications
│   ├── FOUNDATIONS.md
│   ├── agent-framework.md
│   └── ...
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
| **Service model** | **Canonical** | [architecture/SERVICE-MODEL.md](architecture/SERVICE-MODEL.md) |
| Product narrative | Current | [ESSENCE.md](ESSENCE.md) |
| First principles | Current (v4.2) | [architecture/FOUNDATIONS.md](architecture/FOUNDATIONS.md) |
| Agent taxonomy | Current | [architecture/agent-framework.md](architecture/agent-framework.md) |
| Task type registry | Shipped (ADR-145) | [architecture/task-type-orchestration.md](architecture/task-type-orchestration.md) |
| Execution model | Current (ADR-141) | [architecture/agent-execution-model.md](architecture/agent-execution-model.md) |
| Workspace filesystem | Shipped (ADR-142) | [architecture/workspace-conventions.md](architecture/workspace-conventions.md) |
| Output substrate | Phase 1 shipped (ADR-130) | [architecture/output-substrate.md](architecture/output-substrate.md) |
| Primitives | Shipped (ADR-146) | `api/services/primitives/registry.py` |

## Related Repos (Reference Only)

These repos contain patterns we learned from but are not part of v5:

- `yarnnn-app-fullstack` - Block state machine, governance layer (over-engineered)
- `chat_companion` - Memory extraction, pgvector embeddings, temporal expiry
