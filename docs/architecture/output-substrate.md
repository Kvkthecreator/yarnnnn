# Agent Capability & Output Substrate

> **Status**: Canonical (ADR-130)
> **Date**: 2026-03-22 (revised)
> **Rule**: All capability, output, and rendering decisions should be consistent with this document.

---

## Core Principle

**Agent types determine capabilities. Capabilities are deterministic. The platform renders output.**

Three concerns, separated:
1. **Capability** — what can this agent do? (determined by agent type, fixed at creation)
2. **Presentation** — how should the output look? (platform-owned, layout modes)
3. **Export** — what file format is needed externally? (platform-owned, on-demand)

---

## Three-Registry Architecture

### 1. Agent Type Registry

Each agent type is a deterministic capability bundle. Type = capability set. Personification comes from instructions (user-configurable), not capability gating.

```
digest:     [read_platforms, synthesize, produce_markdown, compose_html]
monitor:    [read_platforms, detect_change, alert, produce_markdown, compose_html]
research:   [read_platforms, web_search, investigate, produce_markdown,
             chart, mermaid, compose_html]
synthesize: [read_platforms, cross_reference, data_analysis, chart, mermaid,
             produce_markdown, compose_html]
prepare:    [read_platforms, calendar_access, profile_attendees,
             produce_markdown, compose_html]
pm:         [read_workspace, check_freshness, steer_contributors,
             trigger_assembly, manage_work_plan]
```

Each type also defines: default instructions, pulse cadence, prompt template.

New types (video, slack_writer, etc.) are added by extending this registry + deploying runtimes. No framework changes required.

### 2. Capability Registry

Each capability maps to: a runtime, a tool (if any), skill docs (if any), and an output type.

```
Cognitive (prompt-driven, no tool):
├── read_platforms, synthesize, detect_change, cross_reference
├── data_analysis, alert, investigate, calendar_access, profile_attendees
└── produce_markdown

Tool-backed (internal tools):
├── web_search       → tool: WebSearch
└── read_workspace   → tool: ReadWorkspace

Asset production (compute runtimes):
├── chart            → runtime: python_render, tool: RenderAsset, docs: chart/SKILL.md
├── mermaid          → runtime: python_render, tool: RenderAsset, docs: mermaid/SKILL.md
├── image            → runtime: python_render, tool: RenderAsset, docs: image/SKILL.md
└── video_render     → runtime: node_remotion, tool: RenderAsset, docs: video/SKILL.md

Composition (post-generation pipeline step):
└── compose_html     → runtime: python_render, post_generation: true

Platform skills (external APIs, SKILL.md importable from marketplace):
├── write_slack      → runtime: external:slack, tool: SlackWrite, requires_auth
└── write_notion     → runtime: external:notion, tool: NotionWrite, requires_auth

PM coordination (internal):
├── check_freshness     → tool: CheckContributorFreshness
├── steer_contributors  → tool: WriteWorkspace
├── trigger_assembly    → (pipeline action)
└── manage_work_plan    → tool: UpdateWorkPlan
```

**Two sourcing modes** for skill knowledge:
- **Built-in**: SKILL.md authored by us (chart, mermaid, image, compose)
- **Imported**: SKILL.md from Claude Code skills marketplace (platform write-backs, MCP tools)

### 3. Runtime Registry

```
internal:        In-process, no HTTP call
python_render:   yarnnn-render service (Docker: Python + matplotlib + pandoc + pillow + mermaid-cli)
node_remotion:   yarnnn-video service (Docker: Node.js + Remotion + Chrome) [future]
external:slack:  Slack API via user OAuth token
external:notion: Notion API via user OAuth token
```

### Resolution path

```
Agent type → capabilities → for each capability:
  → resolve tool definition (what the LLM calls)
  → resolve skill docs (what enters the prompt)
  → resolve runtime (where it executes)
```

---

## Output Pipeline

```
┌─────────────────────────────────────────────────────┐
│                 AGENT GENERATION                     │
│                                                      │
│  Agent type determines available capabilities.       │
│  Agent produces:                                     │
│  ├── Structured markdown (output.md)                 │
│  ├── Asset references via RenderAsset (if type has   │
│  │   chart/mermaid/image/video capabilities)          │
│  └── Structured data (JSON for tables/metrics)       │
│                                                      │
│  RenderAsset calls:                                  │
│  ├── python_render → chart/mermaid/image → SVG/PNG   │
│  └── node_remotion → video → MP4 [future]            │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│            POST-GENERATION PIPELINE                  │
│                                                      │
│  If agent type has compose_html capability:           │
│  ├── Call POST /compose with output.md + assets       │
│  ├── Apply layout mode (document/presentation/        │
│  │   dashboard/data)                                  │
│  └── Store output.html alongside output.md            │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│              WORKSPACE STORAGE                       │
│                                                      │
│  /agents/{slug}/outputs/{date}/                      │
│  ├── output.md        (structured source)            │
│  ├── output.html      (composed, platform-rendered)  │
│  ├── manifest.json    (type, capabilities, assets)   │
│  └── assets/                                         │
│      ├── *.svg        (charts, diagrams)             │
│      ├── *.png        (images)                       │
│      ├── *.mp4        (video) [future]               │
│      └── *.json       (structured data)              │
└──────────────────┬──────────────────────────────────┘
                   │
          ┌────────┼─────────────────┐
          ▼        ▼                 ▼
     ┌─────────┐ ┌───────────┐ ┌──────────┐
     │ Agent   │ │ Platform  │ │ Platform │
     │ Consume │ │ Display   │ │ Export   │
     │         │ │           │ │          │
     │ Read    │ │ Render    │ │ HTML→PDF │
     │ output  │ │ output    │ │ data→XLS │
     │ .md via │ │ .html in  │ │ HTML→img │
     │ Read-   │ │ app, send │ │          │
     │ Agent-  │ │ via email │ │ On-demand│
     │ Context │ │           │ │ download │
     └─────────┘ └───────────┘ └──────────┘
```

---

## Multi-Agent Composition

All agents produce structured content. Composition operates in one language:

```markdown
<!-- Researcher's contribution -->
## Market Analysis
![Competitor landscape](assets/competitor-chart.svg)
Key findings from Q2...

<!-- Data agent's contribution -->
## Performance Metrics
| Metric | Q1 | Q2 | Change |
|--------|----|----|--------|
| Revenue | $2.1M | $2.8M | +33% |
![Revenue trend](assets/revenue-trend.svg)

<!-- Writer's contribution -->
## Executive Summary
Based on the analysis above...
```

PM arranges sections, specifies layout mode. Platform composes HTML. No format-specific knowledge at any layer.

---

## Layout Modes (platform-owned)

| Mode | Visual treatment | Best for | How specified |
|---|---|---|---|
| **document** | Flowing text, max-width, reading-optimized | Reports, digests, analysis | Default |
| **presentation** | Full-screen sections, large type, slide breaks at `##`/`---` | Executive reviews, team updates | PM or agent metadata |
| **dashboard** | CSS grid, metric cards, KPI panels | Operational summaries, status reports | PM or content detection |
| **data** | Dense tables, tabular nums, sticky headers | Data-heavy outputs, comparisons | Content detection |

Layout mode is decoupled from agent type. Any agent's output can be rendered in any mode.

---

## Workspace Conventions (ADR-119 extension)

### Output folder structure

```
/agents/{slug}/outputs/{date}/
├── output.md          # structured source (agent writes)
├── output.html        # composed by platform (post-generation)
├── manifest.json      # metadata
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
  "agent_type": "synthesize",
  "run_number": 5,
  "layout_mode": "dashboard",
  "capabilities_used": ["chart", "data_analysis"],
  "files": [
    {"path": "output.md", "role": "source", "content_type": "text/markdown"},
    {"path": "output.html", "role": "composed", "content_type": "text/html"},
    {"path": "assets/revenue-chart.svg", "role": "asset", "content_type": "image/svg+xml"}
  ],
  "structured_data": [
    {"path": "assets/metrics.json", "schema": "tabular", "export_hint": "xlsx"}
  ],
  "delivery": {"channel": "email", "status": "pending"}
}
```

### AGENT.md type and capabilities

```markdown
# Agent: Weekly Slack Recap

## Type
digest

## Capabilities
- read_platforms, synthesize, produce_markdown, compose_html

## Instructions
Recap all activity across connected Slack channels...
```

---

## Relationship to Other Architecture

| Component | Relationship |
|---|---|
| **Agent Framework (ADR-109)** | Agent Type Registry replaces `SKILL_ENABLED_ROLES` + `ROLE_PORTFOLIOS` seniority tiers. Pulse cadence absorbed into type definitions. |
| **Workspace (ADR-106, 119)** | Output folders gain `output.html` + `assets/`. Manifest gains `agent_type` + `capabilities_used`. AGENT.md gains `## Type` + `## Capabilities`. |
| **Skills (ADR-118)** | Format-builder skills dissolved. Asset renderers (chart, mermaid, image) preserved as compute primitives. Two-filesystem architecture preserved. SKILL.md convention preserved for skill knowledge. |
| **Assembly (ADR-120, 121)** | PM composes structured markdown sections. Layout mode specified at assembly level. |
| **Coherence (ADR-128)** | Self-assessments continue for knowledge development. Not gated by seniority. |
| **Delivery (ADR-118 D.3)** | Composed HTML as email body. Exports as download attachments. |
| **Meeting Room (ADR-124)** | Rich HTML output previews in chat stream. |
| **Composer (ADR-111)** | Creates agents of known types. Capability gap analysis: "this project needs data_analysis — create a synthesize agent." |
| **Pulse (ADR-126)** | Simplified: no Tier 2 seniority self-assessment. Pulse remains as sense→decide cycle. |
| **Feedback (ADR-117)** | Feedback distillation preserved (edits → preferences.md). Seniority progression deleted. |
