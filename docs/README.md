# YARNNN Documentation

**The source of truth for YARNNN product narrative, architecture, and implementation decisions.**

## Current Canon (as of 2026-04-20)

**Start here**: [architecture/FOUNDATIONS.md](architecture/FOUNDATIONS.md) — v6.0, the six-dimensional axiomatic model. Every mechanic in YARNNN occupies a cell in six orthogonal dimensions (Substrate / Identity / Purpose / Trigger / Mechanism / Channel). This is the first-principles frame from which every other doc derives.

**For end-to-end system description**: [architecture/SERVICE-MODEL.md](architecture/SERVICE-MODEL.md) — entities, execution flow, services, primitives, perception. v1.5, aligned with FOUNDATIONS v6.0.

The current product story:

- YARNNN is an autonomous agent platform for recurring knowledge work
- Four cognitive layers (YARNNN / Specialists / Agents / Reviewer) + accumulated context + money-truth reconciliation = the value proposition
- Users author a team through conversation and supervise it running; switching cost compounds from the first Agent
- Task types are the product surface — deliverable-first, not agent-first
- Filesystem is the substrate (Axiom 1); everything else is stateless computation over it

## Quick Links

| Document | Purpose |
|----------|---------|
| [architecture/FOUNDATIONS.md](architecture/FOUNDATIONS.md) | **First principles — six-dimensional axiomatic model (v6.0)** |
| [architecture/SERVICE-MODEL.md](architecture/SERVICE-MODEL.md) | **How the system works end-to-end** |
| [architecture/GLOSSARY.md](architecture/GLOSSARY.md) | Canonical terminology (one word, one concept, one layer) |
| [architecture/YARNNN-DESIGN-PRINCIPLES.md](architecture/YARNNN-DESIGN-PRINCIPLES.md) | Design principles including Spectrum A/B (substrate strict, runtime flexible) |
| [ESSENCE.md](ESSENCE.md) | Product narrative and value proposition |
| [NARRATIVE.md](NARRATIVE.md) | External storytelling beats and vocabulary rules |
| [architecture/agent-framework.md](architecture/agent-framework.md) | Agent taxonomy and type registry |
| [architecture/agent-execution-model.md](architecture/agent-execution-model.md) | Execution model and trigger taxonomy |
| [architecture/task-type-orchestration.md](architecture/task-type-orchestration.md) | Task type registry and process execution |
| [architecture/workspace-conventions.md](architecture/workspace-conventions.md) | Workspace filesystem conventions |
| [architecture/output-substrate.md](architecture/output-substrate.md) | Output capabilities and rendering |
| [architecture/primitives-matrix.md](architecture/primitives-matrix.md) | Primitive surface (substrate × mode × capability) |
| [architecture/DOMAIN-STRESS-MATRIX.md](architecture/DOMAIN-STRESS-MATRIX.md) | Agnostic-thesis conscience — gate for every new ADR |
| [adr/](adr/) | Architecture Decision Records (87 active, 116 archived) |

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
| **First principles** | **Current (v6.0 — six-dimensional model)** | [architecture/FOUNDATIONS.md](architecture/FOUNDATIONS.md) |
| **Service model** | **Current (v1.5)** | [architecture/SERVICE-MODEL.md](architecture/SERVICE-MODEL.md) |
| Glossary | Current (v1.3) | [architecture/GLOSSARY.md](architecture/GLOSSARY.md) |
| Design principles | Current | [architecture/YARNNN-DESIGN-PRINCIPLES.md](architecture/YARNNN-DESIGN-PRINCIPLES.md) |
| Product narrative | Current (v12.2) | [ESSENCE.md](ESSENCE.md) |
| External narrative | Current (v4) | [NARRATIVE.md](NARRATIVE.md) |
| Agent taxonomy | Current | [architecture/agent-framework.md](architecture/agent-framework.md) |
| Task type registry | Shipped (ADR-145) | [architecture/task-type-orchestration.md](architecture/task-type-orchestration.md) |
| Execution model | Current (ADR-141) | [architecture/agent-execution-model.md](architecture/agent-execution-model.md) |
| Workspace filesystem | Shipped (ADR-142) | [architecture/workspace-conventions.md](architecture/workspace-conventions.md) |
| Output substrate | Phase 1 shipped (ADR-130) | [architecture/output-substrate.md](architecture/output-substrate.md) |
| Primitives | Shipped (ADR-168) | [architecture/primitives-matrix.md](architecture/primitives-matrix.md) |
| Approval loop | Shipped (ADR-193) | [adr/ADR-193-propose-action-approval-loop.md](adr/ADR-193-propose-action-approval-loop.md) |
| Reviewer layer | Phase 1-2a shipped (ADR-194 v2) | [adr/ADR-194-pluggable-reviewer-and-impersonation.md](adr/ADR-194-pluggable-reviewer-and-impersonation.md) |
| Money-truth substrate | Phases 1-3 shipped (ADR-195 v2) | [adr/ADR-195-outcome-attribution-substrate.md](adr/ADR-195-outcome-attribution-substrate.md) |

## Related Repos (Reference Only)

These repos contain patterns we learned from but are not part of v5:

- `yarnnn-app-fullstack` - Block state machine, governance layer (over-engineered)
- `chat_companion` - Memory extraction, pgvector embeddings, temporal expiry
