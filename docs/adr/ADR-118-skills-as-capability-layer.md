# ADR-118: Skills as Capability Layer

> **Status**: Implemented (Phase A+B+C). All three phases shipped.
> **Date**: 2026-03-17
> **Authors**: KVK, Claude
> **Supersedes**: None
> **Related**: ADR-106 (Workspace), ADR-109 (Agent Framework), ADR-117 (Feedback Substrate), ADR-066 (Delivery-First), ADR-028 (Exporters), ADR-111 (Composer)

## Decision

Extend yarnnn agents from text-only outputs to general-purpose artifact production via a runtime dispatch layer. The architecture follows a developmental model derived from FOUNDATIONS.md axioms.

### Core Principles

1. **Capabilities are explicit and curated** — each requires an adapter, cost model, feedback mechanism, and capability guide. Not a marketplace or buffet.
2. **Runtime dispatch is an agent capability** — invoked during agent runs, not a system-wide post-processing step. Sits alongside WriteWorkspace, QueryKnowledge, WebSearch.
3. **Templates before generative rendering** (Axiom 3) — template parameterization is ungated (available from day one). Generative runtime dispatch is earned through demonstrated quality.
4. **Feedback loop depth over runtime breadth** (Axiom 4) — one adapter with working feedback > five adapters with static output.
5. **Zero-config via Composer** (Axiom 6) — users never configure delivery or rendering. Composer scaffolds agents with appropriate capabilities.
6. **Outputs re-enter the perception substrate** (Axiom 2) — every rendered output gets a workspace_files row with metadata, regardless of where the binary lives.

### Infrastructure Model: Hybrid Render Service

One self-hosted Render web service (`yarnnn-render`) for lightweight transformations, with delegation to third-party APIs for heavy compute.

**Local handlers** (bundled in Docker image, fixed cost):
- Documents (pandoc): markdown → .pdf/.docx
- Presentations (python-pptx): spec → .pptx
- Spreadsheets (openpyxl): spec → .xlsx
- Charts (matplotlib/plotly): data → .png/.svg
- Images (pillow): template → .png

**Delegated** (per-call cost, Phase 3+):
- Video rendering (Remotion Cloud / Shotstack)
- AI image generation (Replicate / Together)

**Routing heuristic**: <256MB RAM and <5s render → local. Otherwise → delegated.

### Capability Model

| Concept | What | Where | Created by |
|---------|------|-------|------------|
| Capability | Runtime adapter | Registry config | Engineering |
| AGENT.md | Agent identity + capability authorizations | Agent workspace | Composer + user |
| Capability guide | How to use a capability | `/capabilities/{name}/guide.md` | Engineering |
| Template | Pre-built output structure | `/templates/{name}/` | Engineering + user |

### Glossary

| Term | Definition |
|------|-----------|
| **Capability** | A registered, platform-level runtime adapter with defined I/O contracts |
| **Capability guide** | Shared documentation teaching agents how to use a specific capability |
| **Template** | Pre-built output structure parameterized by agents |
| **Runtime adapter** | Code that dispatches a spec to an execution service and returns a result |
| **Runtime registry** | Config mapping capability types to adapter classes |
| **Capability gating** | Feedback-earned progression from text → template → generative rendering |

Note: "Skill" in ADR-109 (digest, monitor, etc.) remains distinct from runtime capabilities.

### Delivery-First Principle

Before building rich output rendering, agents must deliver to where users already are. Bootstrap and Composer-created agents default to email delivery (Resend). The user's first experience is receiving an output, not configuring delivery.

## Implementation Phases

### Phase A: Invisible → Visible (delivery by default)
- Bootstrap agents set email destination automatically
- Composer-created agents include destination
- Skill prompts adapted for email delivery context
- No new infrastructure

### Phase B: Text → Rich Outputs (render service)
- `content_url` column on workspace_files for binary references
- Supabase Storage for binary file storage
- `yarnnn-render` web service (5th Render service) with local handlers
- `RuntimeDispatch` primitive for headless agents
- Email delivery extended with rendered attachments/links
- Template convention in workspace

### Phase C: Composer + Agent Config Awareness
- Composer awareness of available capabilities
- Agent creation with capability hints
- Frontend rendered output display (download buttons, preview)

### Phase 3+ (Deferred)
- Delegated adapters (video, AI images)
- Automated capability gating (threshold tracking)
- A2A/MCP ecosystem delegation

## Analysis Reference

Full analysis with axiom derivation, stress testing, cost model, and scalability assessment: `docs/analysis/skills-as-capability-layer-2026-03-17.md`

## Open Questions

1. **Runtime cost model**: Tier-gated rendering? Free tier = N renders/month, Pro = unlimited?
2. **Feedback for non-text outputs**: How does a user "edit" a PDF? Annotate, reject with comments, text-level edits?
3. **Cross-agent capability metadata**: Should ReadAgentContext expose template/feedback data?
4. **Template authoring UX**: File upload via chat? Dashboard? TP-assisted creation?
