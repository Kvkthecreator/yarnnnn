# Agent Capability & Output Substrate

> **Status**: Canonical (ADR-130)
> **Date**: 2026-03-22
> **Rule**: All capability, output, and rendering decisions should be consistent with this document.

---

## Core Principle

**Agent work is structured content, not files.** Capabilities determine what agents can do. The platform renders their work visually for humans and exposes it structurally for other agents. File formats are mechanical exports for external sharing.

Three concerns, separated:
1. **Capability** — what can this agent do? (agent-owned, earned via development)
2. **Presentation** — how should the output look? (platform-owned, layout modes)
3. **Export** — what file format is needed externally? (platform-owned, on-demand)

---

## Capability Model

### Capability tiers

```
Tier 1: Core (all agents, from creation)
├── read — workspace, knowledge base, platform content
├── search — cross-reference sources
├── synthesize — produce narrative from inputs
└── produce_markdown — structured content output

Tier 2: Domain (role-specific, from creation)
├── research — web search, investigation, citation
├── monitor — change detection, alerting, pattern tracking
├── data_analysis — structured data, metrics, computation
├── coordination — freshness, steering, assembly (PM)
└── preparation — agenda, context gathering, profiling

Tier 3: Expressive (earned at associate seniority)
├── visualization — chart/diagram generation via RenderAsset
├── rich_composition — multi-section output with embedded assets
├── cross_agent — reference and build on other agents' outputs
└── layout_hint — specify presentation mode for output

Tier 4: Autonomous (senior+, requires user authorization)
├── write_back — post to external platforms
├── action — consequential external system actions
└── self_direction — propose and execute investigations
```

### Capability → agent wiring

```
Agent creation
  └── Role determines Tier 1 + Tier 2 base capabilities
        └── Seeded in AGENT.md ## Capabilities

Seniority progression (feedback-gated)
  └── Associate: unlocks Tier 3 capabilities
        └── AGENT.md updated by Composer on promotion

  └── Senior: unlocks Tier 4 eligibility
        └── Requires explicit user authorization per capability

Duty promotion (ADR-117)
  └── New duties may add Tier 2 capabilities from other roles
        └── e.g., digest agent earns monitor duty → gains detect_change
```

### Capability metadata in workspace

`AGENT.md` carries a `## Capabilities` section:

```markdown
## Capabilities
- core: read, search, synthesize, produce_markdown
- data_analysis: process_data, compute_metrics, structured_output
- visualization: render_chart, render_diagram (earned: 2026-03-15)
- rich_composition: embed_assets, multi_section (earned: 2026-03-15)
```

This is readable by:
- **The agent itself** — self-awareness of what it can do
- **Other agents** via `ReadAgentContext` — capability discovery
- **PM agents** — knowing what contributors can produce for assembly planning
- **Composer** — identifying capability gaps when creating agents/projects

---

## Output Pipeline

```
┌─────────────────────────────────────────────────┐
│                AGENT GENERATION                  │
│                                                  │
│  Agent produces:                                 │
│  ├── Structured markdown (output.md)             │
│  ├── Asset references (charts, images, diagrams) │
│  ├── Structured data (JSON for tables/metrics)   │
│  └── Manifest with capabilities_used + metadata  │
│                                                  │
│  Assets produced via RenderAsset (Tier 3):       │
│  ├── chart (data → SVG/PNG via matplotlib)       │
│  ├── diagram (mermaid spec → SVG)                │
│  ├── image (composition via Pillow)              │
│  └── stored in outputs/{date}/assets/            │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│              WORKSPACE STORAGE                   │
│                                                  │
│  /agents/{slug}/outputs/{date}/                  │
│  ├── output.md        (structured source)        │
│  ├── manifest.json    (capabilities, assets, etc)│
│  └── assets/                                     │
│      ├── *.svg        (charts, diagrams)         │
│      ├── *.png        (images)                   │
│      └── *.json       (structured data)          │
│                                                  │
│  /projects/{slug}/assembly/{date}/               │
│  ├── output.md        (composed from contribs)   │
│  ├── manifest.json                               │
│  └── assets/          (aggregated)               │
└──────────────────┬──────────────────────────────┘
                   │
          ┌────────┼─────────────────┐
          ▼        ▼                 ▼
     ┌─────────┐ ┌───────────┐ ┌──────────┐
     │ Agent   │ │ Platform  │ │ Platform │
     │ Consume │ │ Render    │ │ Export   │
     │         │ │           │ │          │
     │ Read    │ │ Compose   │ │ HTML→PDF │
     │ output  │ │ markdown  │ │ data→XLS │
     │ .md via │ │ + assets  │ │ HTML→img │
     │ Read-   │ │ → styled  │ │          │
     │ Agent-  │ │ HTML with │ │ On-demand│
     │ Context │ │ layout    │ │ download │
     │         │ │ mode      │ │ buttons  │
     └─────────┘ └─────┬─────┘ └──────────┘
                       │
              ┌────────┼────────┐
              ▼        ▼        ▼
         ┌─────────┐ ┌──────┐ ┌───────┐
         │ In-App  │ │Email │ │Public │
         │         │ │      │ │Share  │
         │ Outputs │ │HTML  │ │       │
         │ tab,    │ │body  │ │URL    │
         │ meeting │ │(zero │ │render │
         │ room    │ │conv) │ │       │
         └─────────┘ └──────┘ └───────┘
```

---

## Multi-Agent Composition

All agents produce structured content. Composition operates in one language regardless of output complexity:

```markdown
<!-- From workspace: /projects/q2-review/contributions/researcher/output.md -->
## Market Analysis
![Competitor landscape](assets/competitor-chart.svg)
Key findings: three new entrants in the mid-market segment...

<!-- From workspace: /projects/q2-review/contributions/data-analyst/output.md -->
## Performance Metrics
| Metric | Q1 | Q2 | Change |
|--------|----|----|--------|
| Revenue | $2.1M | $2.8M | +33% |
![Revenue trend](assets/revenue-trend.svg)

<!-- From workspace: /projects/q2-review/contributions/writer/output.md -->
## Executive Summary
Based on the analysis above, three strategic priorities emerge...
```

PM arranges sections, specifies layout mode, triggers assembly. Platform composes HTML. No format-specific knowledge at any layer.

**Key insight**: the PM doesn't need to know how to make a presentation, a document, or a spreadsheet. It knows how to arrange contributions and specify intent ("this should look like a dashboard" or "this needs to feel like an executive briefing"). The platform translates intent to visual treatment.

---

## Layout Modes

The platform applies visual treatment based on content and intent:

| Mode | Visual treatment | Best for | How specified |
|---|---|---|---|
| **document** | Flowing text, max-width, reading-optimized | Reports, digests, analysis | Default |
| **presentation** | Full-screen sections, large type, slide breaks at `##`/`---` | Executive reviews, team updates | PM or agent metadata |
| **dashboard** | CSS grid, metric cards, KPI panels | Operational summaries, status reports | PM or content detection |
| **data** | Dense tables, tabular nums, sticky headers | Data-heavy outputs, comparisons | Content detection (table-dominant) |
| **interactive** (future) | Client-side JS, filterable, explorable | Complex analysis, drill-down | Tier 4 capability |

Layout mode is decoupled from agent capability. Any agent's output can be rendered in any mode. The same output can be re-rendered in a different mode without regeneration.

---

## Workspace Conventions (ADR-119 extension)

### Output folder structure

```
/agents/{slug}/outputs/{date}/
├── output.md          # structured source (agent writes)
├── manifest.json      # metadata (extended)
└── assets/            # visual assets
    ├── *.svg          # charts, diagrams
    ├── *.png          # images
    └── *.json         # structured data
```

### Manifest schema

```json
{
  "version": 1,
  "agent_id": "uuid",
  "run_number": 5,
  "layout_mode": "dashboard",
  "capabilities_used": ["core", "visualization", "data_analysis"],
  "files": [
    {"path": "output.md", "role": "source"},
    {"path": "assets/revenue-chart.svg", "role": "asset", "content_type": "image/svg+xml"}
  ],
  "structured_data": [
    {"path": "assets/metrics.json", "schema": "tabular", "export_hint": "xlsx"}
  ],
  "delivery": {"channel": "email", "status": "pending"}
}
```

### AGENT.md capabilities section

```markdown
## Capabilities
- core: read, search, synthesize, produce_markdown
- data_analysis: process_data, compute_metrics (role: synthesize)
- visualization: render_chart, render_diagram (earned: 2026-03-15, associate)
```

---

## Relationship to Other Architecture

| Component | Relationship |
|---|---|
| **Agent Framework (ADR-109, 117)** | Capability tiers replace `SKILL_ENABLED_ROLES`. Role portfolios gain capability requirements. Seniority unlocks expressive capabilities. |
| **Workspace (ADR-106, 119)** | Output folders gain `assets/`. Manifest gains `capabilities_used`. AGENT.md gains `## Capabilities`. |
| **Skills (ADR-118)** | Format-builder skills dissolve. Asset renderers (chart, mermaid, image) become Tier 3 capabilities via RenderAsset. Two-filesystem architecture preserved. |
| **Assembly (ADR-120, 121)** | PM composes structured markdown sections. Layout mode specified at assembly level. No format-specific composition. |
| **Coherence (ADR-128)** | Self-assessments include capability usage. PM assessment includes contributor capability evaluation. |
| **Delivery (ADR-118 D.3)** | Composed HTML as email body. Exports as download attachments. |
| **Meeting Room (ADR-124)** | Rich HTML output previews in chat stream. |
| **Composer (ADR-111)** | Capability gap analysis: "this project needs data_analysis but no contributor has it." |
