# YARNNN Documentation

**The source of truth for YARNNN product narrative, architecture, and implementation decisions.**

## Current Canon

**Start here**: [architecture/FOUNDATIONS.md](architecture/FOUNDATIONS.md) — the six-dimensional axiomatic model (v9.x and moving; read the doc for its live version). Every mechanic in YARNNN occupies a cell in six orthogonal dimensions (Substrate / Identity / Purpose / Trigger / Mechanism / Channel). This is the first-principles frame from which every other doc derives.

**For end-to-end system description**: [architecture/SERVICE-MODEL.md](architecture/SERVICE-MODEL.md) — entities, execution flow, services, primitives, perception.

The current product story:

- YARNNN is an autonomous agent platform for recurring knowledge work
- Users author a team through conversation and supervise it running; switching cost compounds from the first Agent
- Filesystem is the substrate (Axiom 1); everything else is stateless computation over it

## Quick Links

| Document | Purpose |
|----------|---------|
| [architecture/FOUNDATIONS.md](architecture/FOUNDATIONS.md) | **First principles — six-dimensional axiomatic model** |
| [architecture/SERVICE-MODEL.md](architecture/SERVICE-MODEL.md) | **How the system works end-to-end** |
| [architecture/GLOSSARY.md](architecture/GLOSSARY.md) | Canonical terminology (one word, one concept, one layer) |
| [architecture/YARNNN-DESIGN-PRINCIPLES.md](architecture/YARNNN-DESIGN-PRINCIPLES.md) | Design principles including Spectrum A/B (substrate strict, runtime flexible) |
| [ESSENCE.md](ESSENCE.md) | Product narrative and value proposition |
| [NARRATIVE.md](NARRATIVE.md) | External storytelling beats and vocabulary rules |
| [architecture/orchestration.md](architecture/orchestration.md) | Agent taxonomy and type registry |
| [architecture/agent-execution-model.md](architecture/agent-execution-model.md) | Execution model and trigger taxonomy |
| [architecture/WORKSPACE.md](architecture/WORKSPACE.md) | Workspace (layers · filesystem · bootstrap · autonomy threshold) — paired with [design/WORKSPACE.md](design/WORKSPACE.md) |
| [architecture/output-substrate.md](architecture/output-substrate.md) | Output capabilities and rendering |
| [architecture/primitives-matrix.md](architecture/primitives-matrix.md) | Primitive surface (substrate × mode × capability) |
| [architecture/DOMAIN-STRESS-MATRIX.md](architecture/DOMAIN-STRESS-MATRIX.md) | Agnostic-thesis conscience — gate for every new ADR |
| [adr/](adr/) | Architecture Decision Records — see [adr/README.md](adr/README.md) for the index |

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
│   ├── orchestration.md
│   └── ...
│
├── analysis/            # Research and comparative analysis
│   └── *.md             # Cross-repo learnings, technical research
│
├── database/            # Database documentation
│   ├── ACCESS.md        # Connection strings, credentials
│   └── SCHEMA.md        # Table descriptions and relationships
│                        # (migration history: supabase/migrations/ is authoritative —
│                        #  the hand-kept MIGRATIONS.md was retired 2026-08-05)
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
├── programs/            # Program bundles (.app-equivalents: manifest + reference-workspace)
├── evaluations/         # Hat-B: scenarios, captures, findings (not shipped to operators)
├── design/              # Surface contracts and design specs
├── monetization/        # Pricing and packaging
├── integrations/        # Per-platform integration notes
├── gitbook/             # Published external docs
├── infrastructure/      # Deploy and service topology
├── alpha/               # alpha-persona operating notes
└── working_docs/        # Investor/GTM working material (binaries — not canon)
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
| **First principles** | **Current — six-dimensional model** | [architecture/FOUNDATIONS.md](architecture/FOUNDATIONS.md) |
| **Service model** | **Current** | [architecture/SERVICE-MODEL.md](architecture/SERVICE-MODEL.md) |
| Glossary | Current | [architecture/GLOSSARY.md](architecture/GLOSSARY.md) |
| Design principles | Current | [architecture/YARNNN-DESIGN-PRINCIPLES.md](architecture/YARNNN-DESIGN-PRINCIPLES.md) |
| Product narrative | Current | [ESSENCE.md](ESSENCE.md) |
| External narrative | Current | [NARRATIVE.md](NARRATIVE.md) |
| Agent taxonomy | Current | [architecture/orchestration.md](architecture/orchestration.md) |
| Execution model | Current (ADR-141) | [architecture/agent-execution-model.md](architecture/agent-execution-model.md) |
| Workspace | Current (consolidated 2026-05-12) | [architecture/WORKSPACE.md](architecture/WORKSPACE.md) |
| Output substrate | Phase 1 shipped (ADR-130) | [architecture/output-substrate.md](architecture/output-substrate.md) |
| Primitives | Shipped (ADR-168) | [architecture/primitives-matrix.md](architecture/primitives-matrix.md) |
| Approval loop | Shipped (ADR-193) | [adr/ADR-193-propose-action-approval-loop.md](adr/ADR-193-propose-action-approval-loop.md) |
| Reviewer layer | Phase 1-2a shipped (ADR-194 v2) | [adr/ADR-194-pluggable-reviewer-and-impersonation.md](adr/ADR-194-pluggable-reviewer-and-impersonation.md) |
| Money-truth substrate | Phases 1-3 shipped (ADR-195 v2) | [adr/ADR-195-outcome-attribution-substrate.md](adr/ADR-195-outcome-attribution-substrate.md) |

## Related Repos (Reference Only)

These repos contain patterns we learned from but are not part of v5:

- `yarnnn-app-fullstack` - Block state machine, governance layer (over-engineered)
- `chat_companion` - Memory extraction, pgvector embeddings, temporal expiry
