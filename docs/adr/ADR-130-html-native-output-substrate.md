# ADR-130: Agent-Native Output & Capability Substrate

> **Status**: Proposed
> **Date**: 2026-03-22
> **Authors**: KVK, Claude
> **Supersedes**: ADR-118 Phase D (format-builder skills model)
> **Extends**: ADR-106 (Workspace), ADR-109 (Agent Framework), ADR-117 (Feedback & Development), ADR-118 (Skills Layer), ADR-119 (Workspace Filesystem), ADR-120 (Project Execution), ADR-128 (Coherence)
> **Implements**: FOUNDATIONS Axiom 2 (recursive perception), Axiom 3 (developing entities), Axiom 4 (accumulated attention), Axiom 6 (autonomy)

---

## Context

YARNNN agents produce work. That work needs to be:
1. **Consumable by humans** — visually rich, contextually appropriate, deliverable
2. **Consumable by other agents** — structured, parseable, composable into larger work
3. **Composable across agents** — a researcher's findings, a data analyst's charts, and a writer's narrative assemble into a coherent deliverable without format-specific glue
4. **Progressively capable** — as agents develop (Axiom 3), their output expressiveness and capability repertoire should expand

The current system fails on all four. ADR-118's 8 format-builder skills (pdf, pptx, xlsx, chart, mermaid, html, data, image) define capabilities as "what file format can you produce." This creates:

- **Constrained expressiveness** — agents must express through rigid JSON DSLs per format. A PPTX skill that only accepts `{title, slides: [{title, content}]}` produces blank templates.
- **Format-specific composition** — assembling multi-agent output requires format-specific knowledge (python-pptx object model, openpyxl cell formatting). The PM must speak every format's language.
- **Opaque agent-to-agent handoff** — binary files (PPTX, PDF) are unreadable by downstream agents. The recursive perception loop (Axiom 2) breaks.
- **Static capability model** — `SKILL_ENABLED_ROLES` hardcodes which roles get RuntimeDispatch by role name, not by seniority or earned capability. A new agent and a senior agent have identical capabilities.
- **No capability discovery** — agents can't discover what other agents can do, can't request new capabilities, can't negotiate output format with consumers.

### The deeper problem

The format-builder model conflates three separate concerns:

1. **What can this agent do?** (capability — research, analyze, visualize, coordinate)
2. **How should the output look?** (presentation — document, dashboard, slides, data table)
3. **What file do you need?** (export — PDF, XLSX, PNG for external sharing)

By fusing all three into "skills = format builders," the system can't evolve any concern independently. An agent that gains data analysis capability shouldn't need a new XLSX skill — it should be able to produce structured data that the platform renders appropriately and exports on demand.

---

## Decision

### 1. Structured content as the universal output primitive

Agent output is **structured content** — markdown with embedded data references, images, and semantic annotations. This is the agent-native format: readable by humans (via rendering), readable by agents (via parsing), and composable across agents (via concatenation with structure).

The platform renders structured content visually. The rendering is a platform concern, not an agent concern. Agents produce knowledge; the platform presents it.

```
Agent capability  → produces structured content + assets to workspace
                         ↓
Workspace stores  → source content + assets (images, data, SVGs)
                         ↓
Platform renders  → styled HTML for human consumption (layout mode + brand)
                         ↓
Platform exports  → legacy formats on demand (PDF, XLSX, image)
                         ↓
Agents consume    → downstream agents read structured source, not rendered HTML
```

### 2. Capabilities separated from presentation separated from export

| Concern | Owner | Examples |
|---|---|---|
| **Capability** | Agent (earned via seniority) | research, data-analysis, visualization, monitoring, coordination |
| **Presentation** | Platform (layout mode on output) | document, presentation, dashboard, data, interactive |
| **Export** | Platform (on-demand, mechanical) | PDF, XLSX, PNG, email (HTML-native) |

Agents never think about format. They think about what they know and what they can produce. The platform handles how it looks and how it ships.

### 3. Capability as a first-class concept in the agent model

Currently, capabilities are implicit — derived from role name via `SKILL_ENABLED_ROLES`. This ADR makes capabilities explicit, earned, and composable:

**Capability registry** — each capability defines:
- What it enables (primitives, tools, asset production)
- Prerequisites (seniority, prior capabilities, feedback thresholds)
- Output types it produces (structured data, narrative, visual assets, actions)

**Capability progression** — aligns with Axiom 3 (developing entities):
- **New agents**: core capabilities for their role (read, search, synthesize)
- **Associate agents**: earned capabilities via feedback (visualize, cross-reference)
- **Senior agents**: full capability portfolio for their role track (coordinate, investigate, act)

**Capability metadata in workspace** — `AGENT.md` gains a `## Capabilities` section that reflects current earned capabilities. This is readable by other agents (enabling capability discovery) and updated by the Composer on promotion.

### 4. HTML as the rendering substrate (not the output format)

HTML is not what agents produce — it's how the platform renders agent output for humans. The distinction matters:

- **Agent produces**: markdown + asset references (structured, agent-readable)
- **Platform renders**: HTML (human-viewable, styled, layout-aware)
- **Platform exports**: PDF, XLSX, etc. (for external consumption)
- **Other agents read**: the markdown source, not the HTML

HTML is chosen because it is the simplest composition primitive that accommodates the widest visual expressiveness. But agents don't write HTML — they write structured content that the platform composes into HTML.

### 5. Layout modes as platform intelligence

The platform applies visual treatment based on the output's nature, not agent instruction:

- **Document** — flowing text, tables, charts. Default. For reports, digests, analysis.
- **Presentation** — sectioned, full-screen, large type. For executive summaries, review decks.
- **Dashboard** — grid layout, metric cards, KPIs. For operational outputs.
- **Data** — tabular, sortable, dense. For data-heavy outputs.
- **Interactive** (future) — stateful, filterable, explorable. For complex analysis.

Layout mode can be:
- Inferred from content structure (tables → data mode, few sections with metrics → dashboard)
- Specified by the agent in output metadata
- Specified by the PM during assembly
- Overridden by the user in the UI

### 6. Multi-agent composition in one language

All agents produce structured content. Composition is structural:

```markdown
<!-- Researcher's contribution (from workspace) -->
## Market Analysis
![Competitor landscape](assets/competitor-chart.svg)
Key findings from Q2...

<!-- Data agent's contribution (from workspace) -->
## Performance Metrics
| Metric | Q1 | Q2 | Change |
|--------|----|----|--------|
| Revenue | $2.1M | $2.8M | +33% |
![Revenue trend](assets/revenue-trend.svg)

<!-- Writer's contribution (from workspace) -->
## Executive Summary
Based on the analysis above...
```

The PM arranges these sections. The platform renders them. No format-specific knowledge required at any layer.

### 7. Asset capabilities as workspace-native producers

Asset capabilities (charts, diagrams, images) produce workspace files that agents reference in their output:

- `RenderAsset(type="chart", input={data_spec})` → SVG in `assets/` folder
- `RenderAsset(type="diagram", input={mermaid_spec})` → SVG in `assets/` folder
- Agent references: `![Revenue Trend](assets/revenue-trend.svg)`

Assets are workspace files — visible to other agents, versionable, composable. Not opaque binary blobs uploaded to storage.

---

## Capability Architecture

### Capability tiers

**Tier 1: Core capabilities** (all agents, from creation)
- Read workspace, knowledge base, platform content
- Search and cross-reference
- Synthesize narrative from sources
- Produce structured markdown output

**Tier 2: Domain capabilities** (role-specific, available from creation)
- **Research**: web search, source investigation, citation
- **Monitoring**: change detection, threshold alerting, pattern tracking
- **Data analysis**: structured data processing, metric computation
- **Coordination**: freshness tracking, contributor steering, assembly (PM only)
- **Preparation**: agenda building, context gathering, stakeholder profiling

**Tier 3: Expressive capabilities** (earned via seniority progression)
- **Visualization**: chart generation, diagram creation (via RenderAsset)
- **Rich composition**: multi-section outputs with embedded assets
- **Cross-agent reference**: citing and building on other agents' outputs
- **Layout specification**: agent can specify layout mode based on content awareness

**Tier 4: Autonomous capabilities** (senior+ with explicit user authorization)
- **Write-back**: post to external platforms (Slack, email, Notion)
- **Action**: take consequential actions in external systems
- **Self-direction**: propose and execute investigations without user prompt

### Capability → agent framework wiring

```python
# In agent_framework.py (proposed evolution)
CAPABILITY_TIERS = {
    "core": ["read", "search", "synthesize", "produce_markdown"],
    "research": ["web_search", "investigate", "cite"],
    "monitor": ["detect_change", "alert", "track_pattern"],
    "data_analysis": ["process_data", "compute_metrics", "structured_output"],
    "coordination": ["check_freshness", "steer_contributor", "assemble"],
    "visualization": ["render_chart", "render_diagram"],  # Tier 3: earned
    "rich_composition": ["embed_assets", "multi_section", "layout_hint"],
    "cross_agent": ["read_agent_context", "cite_agent_output"],
    "write_back": ["post_slack", "send_email", "update_notion"],
}

ROLE_BASE_CAPABILITIES = {
    "digest": ["core"],
    "research": ["core", "research"],
    "monitor": ["core", "monitor"],
    "synthesize": ["core", "data_analysis"],
    "pm": ["core", "coordination"],
    ...
}

SENIORITY_UNLOCKS = {
    "associate": ["visualization", "rich_composition"],
    "senior": ["cross_agent", "layout_hint"],
}
```

### Capability metadata in workspace

`AGENT.md` evolves:

```markdown
# Agent: Weekly Slack Recap

## Role
digest

## Capabilities
- core: read, search, synthesize, produce_markdown
- visualization: render_chart (earned at associate)
- rich_composition: embed_assets, multi_section (earned at associate)

## Instructions
...
```

This is readable by:
- The agent itself (self-awareness of what it can do)
- Other agents via `ReadAgentContext` (capability discovery)
- The PM (knowing what contributors can produce)
- The Composer (deciding what capabilities are missing in a project)

---

## Workspace & Filesystem Implications

### Output folder structure (extended)

```
/agents/{slug}/outputs/{date}/
├── output.md          # structured source (agent writes)
├── manifest.json      # metadata: layout_mode, capabilities_used, assets
├── assets/            # visual assets produced by agent capabilities
│   ├── *.svg          # charts, diagrams
│   ├── *.png          # images
│   └── *.json         # structured data (for downstream agents + XLSX export)
└── (output.html)      # rendered by platform, not by agent — may be cached here
```

### Manifest schema (extended)

```json
{
  "version": 1,
  "agent_id": "uuid",
  "run_number": 5,
  "layout_mode": "dashboard",
  "capabilities_used": ["core", "visualization", "data_analysis"],
  "files": [
    {"path": "output.md", "role": "source", "content_type": "text/markdown"},
    {"path": "assets/revenue-chart.svg", "role": "asset", "content_type": "image/svg+xml"}
  ],
  "structured_data": [
    {"path": "assets/metrics.json", "schema": "tabular", "export_hint": "xlsx"}
  ],
  "delivery": {"channel": "email", "status": "pending"}
}
```

### Agent-to-agent consumption

Downstream agents read `output.md` (structured source), not `output.html` (rendered view). This preserves the recursive perception loop:

- Agent B reads Agent A's `output.md` via `ReadAgentContext`
- Agent B can parse sections, extract data from tables, reference charts
- Agent B produces its own output that builds on Agent A's knowledge
- The platform renders both outputs for human viewing

### Capability manifest in AGENT.md

Capabilities are workspace metadata — readable, versionable, agent-discoverable:

```markdown
## Capabilities
- core: read, search, synthesize, produce_markdown
- visualization: render_chart, render_diagram (earned: 2026-03-15, associate promotion)
- rich_composition: embed_assets, multi_section (earned: 2026-03-15)
```

Updated by Composer on duty promotion. Read by PM for assembly planning.

---

## Impact on Existing Systems

### Agent framework (`agent_framework.py`)
- `SKILL_ENABLED_ROLES` → evolves to `ROLE_BASE_CAPABILITIES` + `SENIORITY_UNLOCKS`
- `ROLE_PORTFOLIOS` → duties gain `capabilities_required` field
- `classify_seniority()` → also returns unlocked capabilities
- New: `get_agent_capabilities(role, seniority, earned_duties)` function

### Agent creation (`agent_creation.py`)
- AGENT.md seeded with `## Capabilities` section based on role
- No longer checks `SKILL_ENABLED_ROLES` — checks capability tiers instead

### Agent execution (`agent_execution.py`)
- `_fetch_skill_docs()` → `_fetch_capability_docs()` — fetches relevant SKILL.md based on agent's current capabilities, not role name
- `RuntimeDispatch` → `RenderAsset` for asset production (Tier 3 capability)
- System prompt injection: capabilities-aware, not role-hardcoded

### Agent pipeline (`agent_pipeline.py`)
- Role prompts updated: agents told to produce structured markdown, reference assets
- Assembly prompt updated: PM composes markdown sections, specifies layout mode
- Capability awareness in prompts: "You have visualization capability" vs. "You have RuntimeDispatch"

### Render service (`render/main.py`)
- `/compose` endpoint (Phase 1 — implemented): markdown + assets → HTML
- `/render` → retained for asset rendering (chart, mermaid, image)
- Future `/export` → HTML → PDF/image, data → XLSX

### Delivery (`delivery.py`)
- `deliver_from_output_folder()` → sends composed HTML as email body
- Attachment model → structured data files offered as XLSX downloads

### Frontend
- Outputs tab → renders HTML inline
- Meeting room → rich output cards
- Export buttons → on-demand format conversion

---

## Phases

### Phase 1: HTML composition engine (IMPLEMENTED)
- `/compose` endpoint on render service
- Layout modes: document, presentation, dashboard, data
- Brand CSS injection
- Asset URL resolution

### Phase 2: In-app HTML surfacing + agent pipeline integration
- Outputs tab renders composed HTML inline
- `agent_execution.py` calls `/compose` after generation to produce `output.html`
- Email delivery uses composed HTML
- Meeting room shows rich output previews

### Phase 3: Capability model in agent framework
- `ROLE_BASE_CAPABILITIES` + `SENIORITY_UNLOCKS` replace `SKILL_ENABLED_ROLES`
- `get_agent_capabilities()` function
- AGENT.md `## Capabilities` section seeded at creation, updated on promotion
- Capability-aware primitive injection (replace role-based skill injection)

### Phase 4: Asset rendering as earned capability
- `RenderAsset` primitive (replaces `RuntimeDispatch` for asset production)
- Gated by Tier 3 capability (associate+ seniority)
- Assets written to `outputs/{date}/assets/`
- Agent prompts reference assets via markdown image syntax

### Phase 5: Export pipeline
- `/export` endpoint: HTML → PDF (via puppeteer/playwright), HTML → image
- Structured data → XLSX (direct from manifest `structured_data`)
- Export buttons in frontend
- Email delivery uses composed HTML directly

### Phase 6: Dissolve format-builder skills
- Remove `pptx`, `pdf`, `html` skills from render service
- Keep `chart`, `mermaid`, `image` as asset renderers
- Update all prompts and primitives to capability model
- Delete `SKILL_ENABLED_ROLES`

### Phase 7: Capability discovery + marketplace foundation
- Agents can query "who has capability X" via `DiscoverAgents` enhancement
- PM selects contributors based on capability match to project objective
- Composer evaluates capability gaps when deciding what agents to create
- Foundation for external capability import (MCP tools as capabilities)

---

## Trade-offs

### Accepted

1. **Legacy format export fidelity** — Exports from HTML (PDF, image) are high-fidelity for viewing. Natively editable formats (PPTX with slide masters, XLSX with formulas) are lower fidelity or deferred. We accept this because agent output is viewed and evaluated, not edited in desktop apps.

2. **XLSX from data, not HTML** — Spreadsheets with formulas and filters are genuinely more useful as native XLSX. We keep a direct structured-data-to-XLSX path. This is the one case where the legacy format adds real value.

3. **Incremental capability migration** — Existing `RuntimeDispatch` + `SKILL_ENABLED_ROLES` continue working during migration. Singular implementation achieved at Phase 6 completion.

### Rejected

1. **Code-as-input model** — Agents pass python-pptx code to render service. Rejected: security risk, doesn't solve composition, doesn't enable capability progression.

2. **Rich JSON DSL per format** — Expand each skill's schema. Rejected: N×M scaling, doesn't solve any of the four requirements.

3. **Keep format-builders alongside capabilities** — Dual approach. Rejected: violates Derived Principle 7 (singular implementation).

---

## Axiom Alignment

| Foundation | Alignment |
|---|---|
| **Axiom 2 (Recursive Perception)** | Structured content is agent-readable. Downstream agents consume `output.md`, not opaque binaries. Capability metadata in AGENT.md enables cross-agent discovery. |
| **Axiom 3 (Developing Entities)** | Capabilities are earned via seniority. New agents produce simple markdown; senior agents produce rich multi-asset compositions. The substrate accommodates the full developmental range. |
| **Axiom 4 (Accumulated Attention)** | Capability progression compounds with tenure. A senior agent with visualization + cross-reference capabilities produces fundamentally richer output than a new agent — same substrate, more expressiveness. |
| **Axiom 6 (Autonomy)** | End-to-end autonomous flow: agent generates structured content → platform renders → delivers. No human intervention to "open the file" or "convert the format." |
| **Derived Principle 7 (Singular)** | One output substrate, one composition language, one capability model. No parallel format-specific paths. |
| **Derived Principle 9 (Agent-Native)** | Output optimized for agent production and consumption first, human viewing second, legacy export third. |

---

## Open Questions

1. **Capability prerequisite graph** — Should capabilities have dependencies (e.g., "visualization requires data_analysis")? Or is role-based portfolio sufficient? Dependencies add precision but complexity.

2. **Interactive outputs** — Can agents produce outputs with client-side interactivity (filterable tables, explorable charts)? Requires JS in HTML. Tension with email delivery (no JS). Solution: two renders (static for email, interactive for in-app)?

3. **External capability import** — How do MCP tools map to capabilities? If a user connects an MCP server with new tools, do those become agent capabilities? This is the marketplace question — deferred but architecturally important.

4. **Capability versioning** — When a capability's implementation changes (e.g., chart rendering improves), do existing agents benefit automatically? Or do they need to "re-earn" the capability?

5. **Structured data as primary output** — Some agents (data analysts) produce structured data (JSON/CSV) as their primary contribution, not narrative. How does this flow through the composition pipeline? Manifest `structured_data` field is a start, but the agent prompt model is markdown-first.
