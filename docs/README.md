# YARNNN v5 Documentation

**The source of truth for YARNNN development.**

## Quick Links

| Document | Purpose |
|----------|---------|
| [ESSENCE.md](ESSENCE.md) | Core product spec - domain model, agents, data flow |
| [database/ACCESS.md](database/ACCESS.md) | Database connection strings and credentials |
| [development/SETUP.md](development/SETUP.md) | Local development setup |
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
│   ├── ARCHITECTURE.md  # System architecture overview
│   └── DEPLOYMENT.md    # Deployment procedures
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
| Database Schema | 8 tables, RLS complete | [database/](database/) |
| API Routes | Scaffolded, context routes implemented | - |
| Agents | Stubs only | - |
| Frontend | Scaffolded | - |

## Related Repos (Reference Only)

These repos contain patterns we learned from but are not part of v5:

- `yarnnn-app-fullstack` - Block state machine, governance layer (over-engineered)
- `chat_companion` - Memory extraction, pgvector embeddings, temporal expiry
