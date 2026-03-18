# YARNNN Documentation

**The source of truth for YARNNN product narrative, architecture, and implementation decisions.**

## Current Canon (as of 2026-03-18)

The current product story is:

- YARNNN is an autonomous agent platform for recurring knowledge work
- persistent agents plus accumulated context are the core value proposition
- the user supervises a running system instead of repeatedly operating prompts
- output skills enrich the deliverable, but do not change the service model

The current architecture is anchored by:

- [ESSENCE.md](ESSENCE.md) — canonical product narrative
- [architecture/FOUNDATIONS.md](architecture/FOUNDATIONS.md) — first principles
- [architecture/agent-framework.md](architecture/agent-framework.md) — Scope × Role × Trigger
- [adr/ADR-118-skills-as-capability-layer.md](adr/ADR-118-skills-as-capability-layer.md) — output skills + output gateway
- [adr/ADR-119-workspace-filesystem-architecture.md](adr/ADR-119-workspace-filesystem-architecture.md) — workspace folders + unified outputs

## Quick Links

| Document | Purpose |
|----------|---------|
| [ESSENCE.md](ESSENCE.md) | Canonical product narrative and value proposition |
| [architecture/FOUNDATIONS.md](architecture/FOUNDATIONS.md) | First-principles cognitive architecture |
| [architecture/agent-framework.md](architecture/agent-framework.md) | Canonical agent model |
| [adr/ADR-106-agent-workspace-architecture.md](adr/ADR-106-agent-workspace-architecture.md) | Agent workspace filesystem |
| [adr/ADR-116-agent-identity-inter-agent-knowledge.md](adr/ADR-116-agent-identity-inter-agent-knowledge.md) | Inter-agent identity and reading |
| [adr/ADR-117-agent-feedback-substrate-developmental-model.md](adr/ADR-117-agent-feedback-substrate-developmental-model.md) | Feedback and learned preferences |
| [adr/ADR-118-skills-as-capability-layer.md](adr/ADR-118-skills-as-capability-layer.md) | Output skills and output gateway |
| [adr/ADR-119-workspace-filesystem-architecture.md](adr/ADR-119-workspace-filesystem-architecture.md) | Output folders, lifecycle, project folders |
| [integrations/RENDER-SERVICES.md](integrations/RENDER-SERVICES.md) | Service topology and env var parity |
| [adr/](adr/) | ADR index and archive |

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
| Product narrative | Current | [ESSENCE.md](ESSENCE.md) |
| First principles | Current | [architecture/FOUNDATIONS.md](architecture/FOUNDATIONS.md) |
| Agent taxonomy | Current | [architecture/agent-framework.md](architecture/agent-framework.md) |
| Workspace filesystem | Shipped | [adr/ADR-106-agent-workspace-architecture.md](adr/ADR-106-agent-workspace-architecture.md) |
| Feedback substrate | Shipped | [adr/ADR-117-agent-feedback-substrate-developmental-model.md](adr/ADR-117-agent-feedback-substrate-developmental-model.md) |
| Output skills / gateway | Shipped and expanding | [adr/ADR-118-skills-as-capability-layer.md](adr/ADR-118-skills-as-capability-layer.md) |
| Output folders / lifecycle | Phase 1 shipped | [adr/ADR-119-workspace-filesystem-architecture.md](adr/ADR-119-workspace-filesystem-architecture.md) |
| Public marketing surface | Needs continual alignment | `web/app/page.tsx`, `web/app/about/page.tsx`, `web/app/faq/page.tsx` |

## Related Repos (Reference Only)

These repos contain patterns we learned from but are not part of v5:

- `yarnnn-app-fullstack` - Block state machine, governance layer (over-engineered)
- `chat_companion` - Memory extraction, pgvector embeddings, temporal expiry
