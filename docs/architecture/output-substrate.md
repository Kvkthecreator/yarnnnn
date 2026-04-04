# Agent Capability & Output Substrate

> **Status**: Canonical (ADR-130). Phase 1 implemented. Phase 2 (compose integration) proposed.
> **Date**: 2026-03-23 (revised)
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

Each agent type is a **product offering** — a role the user "hires" for their project team. Type = capability set + display identity. 8 user-facing types + PM infrastructure:

```
briefer:    [read_slack, read_notion, summarize, produce_markdown, compose_html]
            "Keeps you briefed on what's happening"
monitor:    [read_slack, read_notion, read_github, detect_change, alert, produce_markdown, compose_html]
            "Watches for what matters and alerts you"
researcher: [read_slack, read_notion, read_github, web_search, investigate, produce_markdown, chart, mermaid, compose_html]
            "Investigates topics and produces analysis"
drafter:    [read_notion, read_github, produce_markdown, chart, mermaid, compose_html]
            "Produces deliverables and documents for you"
analyst:    [read_slack, read_notion, read_github, data_analysis, cross_reference, chart, mermaid, produce_markdown, compose_html]
            "Tracks metrics and surfaces patterns"
writer:     [read_notion, produce_markdown, compose_html]
            "Crafts communications and content"
planner:    [read_notion, read_github, produce_markdown, compose_html]
            "Prepares plans, agendas, and follow-ups"
scout:      [read_slack, read_notion, read_github, web_search, produce_markdown, chart, compose_html]
            "Tracks competitors and market movements"
pm:         [read_workspace, check_freshness, steer_contributors, trigger_assembly, manage_work_plan]
            Coordinates project team (infrastructure, not user-facing)
```

Each type also defines: display_name, tagline, default instructions, pulse cadence, prompt template.

Multi-agent coordination: projects are teams (1 PM + 1..N contributors). Lean start at scaffold (1 contributor), team grows via Composer/TP/user request. PM orchestrates via work plan.

New types added by extending the registry + deploying runtimes. No framework changes required. Legacy roles (digest, synthesize, research, prepare, custom) mapped to new types via `resolve_role()`.

### 2. Capability Registry

Each capability maps to: a runtime, a tool (if any), skill docs (if any), and an output type.

```
Cognitive (prompt-driven, no tool):
├── synthesize, detect_change, cross_reference
├── data_analysis, alert, investigate, calendar_access, profile_attendees
└── produce_markdown

Tool-backed (internal tools):
├── web_search       → tool: WebSearch
└── read_workspace   → tool: ReadWorkspace

Provider-native external tools:
├── read_slack       → runtime: external:slack, tools: platform_slack_list_channels, platform_slack_get_channel_history
├── write_slack      → runtime: external:slack, tool: platform_slack_send_message
├── read_notion      → runtime: external:notion, tools: platform_notion_search, platform_notion_get_page
├── write_notion     → runtime: external:notion, tool: platform_notion_create_comment
└── read_github      → runtime: external:github, tools: platform_github_list_repos, platform_github_get_issues

Asset production (compute runtimes):
├── chart            → runtime: python_render, tool: RuntimeDispatch, docs: chart/SKILL.md
├── mermaid          → runtime: python_render, tool: RuntimeDispatch, docs: mermaid/SKILL.md
├── image            → runtime: python_render, tool: RuntimeDispatch, docs: image/SKILL.md
└── video_render     → runtime: node_remotion, tool: RuntimeDispatch, docs: video/SKILL.md

Composition (post-generation pipeline step):
└── compose_html     → runtime: python_render, post_generation: true

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
external:github: GitHub API via user OAuth token
```

### Resolution path

```
Agent type → capabilities → for each capability:
  → resolve tool definition (what the LLM calls)
  → resolve skill docs (what enters the prompt)
  → resolve runtime (where it executes)
```

---

## Output Pipeline (ADR-148)

Three production phases, strictly separated:

```
┌─────────────────────────────────────────────────────┐
│           PHASE 1: GENERATE (LLM)                    │
│                                                      │
│  Agent produces prose with inline data:              │
│  ├── Structured markdown (output.md)                 │
│  ├── Data tables (markdown tables with numeric data) │
│  └── Mermaid code blocks (diagrams)                  │
│                                                      │
│  Agent does NOT call RuntimeDispatch.                │
│  All tool rounds reserved for research + context.    │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│           PHASE 2: RENDER (mechanical)               │
│                                                      │
│  render_inline_assets() extracts and renders:        │
│  ├── Numeric data tables → chart via POST /render    │
│  ├── Mermaid code blocks → SVG via POST /render      │
│  └── Rendered URLs inserted into markdown            │
│                                                      │
│  Zero LLM cost. Mechanical extraction + rendering.   │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│           PHASE 3: COMPOSE (mechanical)              │
│                                                      │
│  POST /compose with enriched markdown + asset URLs:  │
│  ├── Apply composition mode (document/presentation/  │
│  │   dashboard/data)                                 │
│  └── Store output.html alongside output.md           │
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
- read_slack, read_notion, synthesize, produce_markdown, compose_html

## Instructions
Recap all activity across connected Slack channels...
```

---

## Relationship to Other Architecture

| Component | Relationship |
|---|---|
| **Agent Framework (ADR-109)** | Agent Type Registry replaces `SKILL_ENABLED_ROLES` + `ROLE_PORTFOLIOS` seniority tiers. Pulse cadence absorbed into type definitions. |
| **Workspace (ADR-106, 119)** | Output folders gain `output.html` + `assets/`. Manifest gains `agent_type` + `capabilities_used`. AGENT.md gains `## Type` + `## Capabilities`. |
| **Skills (ADR-118, ADR-157)** | 7 render skills: chart (matplotlib), mermaid (mermaid-cli), image (Gemini AI generation), video (Remotion slide composition), fetch-asset (favicon fetching), document (pandoc PDF/DOCX), spreadsheet (openpyxl XLSX). Two-filesystem architecture preserved. SKILL.md convention for skill knowledge. |
| **Playbook Framework** | Agent-level methodology (`_playbook-*.md`). Selective loading by task class. Visual production playbook is Marketing-only (Axiom 3). See `docs/features/agent-playbook-framework.md`. |
| **Assembly (ADR-120, 121)** | PM composes structured markdown sections. Layout mode specified at assembly level. |
| **Coherence (ADR-128)** | Self-assessments continue for knowledge development. Not gated by seniority. |
| **Delivery (ADR-118 D.3)** | Composed HTML as email body. Exports as download attachments. |
| **Meeting Room (ADR-124)** | Rich HTML output previews in chat stream. |
| **Composer (ADR-111)** | Creates agents of known types. Capability gap analysis: "this project needs data_analysis — create a synthesize agent." |
| **Pulse (ADR-126)** | Simplified: no Tier 2 seniority self-assessment. Pulse remains as sense→decide cycle. |
| **Feedback (ADR-117)** | Feedback distillation preserved (edits → preferences.md). Seniority progression deleted. |
