# Agent Capability & Output Substrate

> **Status**: Canonical (ADR-130 + ADR-170). Phase 1 implemented. Phase 2 (compose integration) proposed.
> **Date**: 2026-04-10 (revised; output-surfaces.md merged in 2026-05-04)
> **Rule**: All capability, output, and rendering decisions should be consistent with this document.
> **Related**: [compose-substrate.md](compose-substrate.md) — compose function architecture.

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

Multi-agent coordination: projects are teams (1 PM + 1..N contributors). Lean start at scaffold (1 contributor), team grows via Composer/YARNNN/user request. PM orchestrates via work plan.

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

## Output Pipeline (ADR-148, extended by ADR-170)

Five production phases. SCAFFOLD and ASSEMBLE (the compose substrate) are deterministic Python — zero LLM cost. They are the binding layer between the accumulating filesystem and rendered output. See [compose-substrate.md](compose-substrate.md).

```
┌─────────────────────────────────────────────────────┐
│      PHASE 0: SCAFFOLD (first run only)              │
│                                                      │
│  Create page_spec.json from task type definition:    │
│  ├── Declared sections with kinds and scopes         │
│  ├── Expected asset types per section                │
│  ├── Directory scope from context_reads              │
│  Zero LLM cost. Deterministic.                       │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│      PHASE 1a: ASSEMBLE — pre-generation             │
│                                                      │
│  Query filesystem state for scoped directories:      │
│  ├── Discover assets in domain assets/ folders       │
│  ├── Enumerate entities matching section patterns    │
│  ├── Flag stale sections (source newer than content) │
│  └── Build generation brief for LLM                  │
│                                                      │
│  Zero LLM cost. Deterministic filesystem queries.    │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│      PHASE 1b: GENERATE (LLM)                        │
│                                                      │
│  Agent produces prose guided by assembly brief:      │
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
│      PHASE 1c: ASSEMBLE — post-generation            │
│                                                      │
│  Bind LLM output into page_spec sections:            │
│  ├── Resolve asset references to filesystem paths    │
│  ├── Update provenance (run ID, timestamp)           │
│  └── Persist updated page_spec.json                  │
│                                                      │
│  Zero LLM cost. Deterministic binding.               │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│      PHASE 2: RENDER (mechanical)                    │
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
│      PHASE 3: COMPOSE (mechanical)                   │
│                                                      │
│  POST /compose with page spec + rendered assets:     │
│  ├── Apply surface type arrangement (report/deck/    │
│  │   dashboard/digest/workbook/preview/video)        │
│  ├── Render section kinds per surface type rules     │
│  └── Store output folder (index.html + partials)     │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│              WORKSPACE STORAGE                       │
│                                                      │
│  /tasks/{slug}/outputs/{date}/                       │
│  ├── index.html       (entry point — assembles       │
│  │                     section partials + assets)     │
│  ├── output.md        (structured source, preserved) │
│  ├── sections/        (section partials per kind)    │
│  ├── assets/          (root + derivative)            │
│  │   ├── *.svg        (charts, diagrams)             │
│  │   ├── *.png        (images, logos)                │
│  │   ├── *.mp4        (video) [future]               │
│  │   └── *.json       (structured data)              │
│  ├── data/            (structured data backing       │
│  │                     derivative assets)             │
│  └── sys_manifest.json (provenance, asset status)    │
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

## Surface Types, Section Kinds & Export Pipeline (ADR-170 RD-6/7/8/9)

### Core Principle

**Output is always HTML. Surface types are visual paradigms, not file formats. Export is derivative.**

YARNNN is HTML-native (ADR-130). Every output is an HTML experience that *looks like* a deck, *looks like* a dashboard, etc. Export to `.pptx`, `.pdf`, `.xlsx` is downstream mechanical transformation for interoperability — not part of the output model.

---

### Layer 1: Surface Types

A surface type is a **visual paradigm** — a distinct way humans consume information. `layout_mode` → `surface_type` (ADR-170 RD-6). Surface type is decoupled from agent type.

| Surface Type | Paradigm | Consumption Model | Layout System | Interaction |
|---|---|---|---|---|
| **`report`** | Flowing narrative document | Sequential reading | Single column, reading-optimized | Scroll, section anchors |
| **`deck`** | Discrete full-screen frames | One idea per frame, presented | Full-viewport sections, scroll-snap | Navigate frame-to-frame |
| **`dashboard`** | Single-canvas overview | At-a-glance, spatial scanning | CSS grid, responsive tiles | Grid arrangement |
| **`digest`** | Grouped/chronological stream | Quick triage | Stacked groups, expand/collapse | Scan headers |
| **`workbook`** | Tabular-first, data-dense | Analysis, comparison | Tables as primary content | Sort, filter, pivot |
| **`preview`** | In-context mockups | Content as it appears elsewhere | Platform-framed cards | Scroll between mockups |
| **`video`** | Sequential animated frames | Temporal, narrated | Timeline-driven scene graph | Play/pause (Phase 6+) |

**What surface types are NOT:** not file formats, not layout CSS classes, not delivery channels. "Deck" ≠ `.pptx`; email is a delivery channel not a surface type.

**Surface type selection by task category:**

| Task Type | Natural Surface Type | Why |
|---|---|---|
| `track-*` (context accumulation) | `dashboard` | Entity monitoring is spatial |
| `*-brief`, `*-report` (analysis) | `report` | Research is narrative |
| `*-update` (stakeholder) | `deck` | Updates are presented |
| `*-digest` (operational awareness) | `digest` | Digests are triage |
| `daily-update` | `digest` | Morning briefing |
| `meeting-prep` | `report` | Prep docs are sequential |
| `content-*` | `preview` | Show how it looks on-platform |

---

### Layer 2: Section Kinds

Section kinds are **typed components** — semantic building blocks. Each has a defined data contract and rendering rules per surface type.

| Kind | Data Contract | Use Case |
|---|---|---|
| **`narrative`** | Prose paragraph(s); optional: pullquote, highlight, source_refs | Executive summaries, analysis, explanations |
| **`metric-cards`** | Array of 2–4 KPIs: `{label, value, delta?, sparkline_data?, unit?}` | Revenue metrics, KPI panels |
| **`entity-grid`** | Array of entities: `{icon?, title, subtitle, badge?, detail_ref?}` | Competitor profiles, team roster |
| **`comparison-table`** | Entities × attributes: `{entities[], attributes[], values[][], rag_colors?}` | Feature comparison, vendor evaluation |
| **`trend-chart`** | Time-series: `{series[], x_label, y_label, annotations?}` | Revenue over time, growth curves |
| **`distribution-chart`** | Categorical: `{categories[], values[], chart_type: bar/pie/treemap}` | Market share, category breakdown |
| **`timeline`** | Events: `{date, title, description, source?, severity?}[]` | Signal timeline, changelog |
| **`status-matrix`** | Entities × criteria with indicators: `{entities[], criteria[], statuses[][]}` | Competitor health, risk assessment |
| **`data-table`** | Tabular: `{headers[], rows[][], sort_by?, highlight_rules?}` | Financial data, detailed comparisons |
| **`callout`** | Single insight: `{severity: info/warning/critical, title, body, source?}` | Key finding, risk alert |
| **`checklist`** | Items with status: `{text, status: done/pending/blocked, assignee?}[]` | Next steps, action items |

**Rendering per surface type** — the same kind produces different HTML per paradigm:

| Kind | `report` | `deck` | `dashboard` | `digest` | `video` |
|---|---|---|---|---|---|
| `narrative` | Full-width prose | Text overlay on frame | Wide card, abbreviated | Collapsed paragraph | Lower-third text overlay |
| `metric-cards` | Inline stat boxes | Hero metrics, one per frame | Grid tiles | Compact stat row | Animated counter entrance |
| `entity-grid` | Vertical card list | One entity per frame | Responsive card grid | One-line entity rows | Sequential card reveal |
| `comparison-table` | Full-width table | Simplified highlight table | Card with scroll | Hidden (too dense) | Row-by-row animation |
| `trend-chart` | Inline chart | Full-frame chart | Chart tile in grid | Sparkline only | Animated line draw |
| `timeline` | Vertical timeline | One event per frame | Timeline card | Grouped event list | Sequential appearance |
| `callout` | Bordered callout | Full-frame callout | Alert tile | Highlighted row | Fade-in overlay |

**Section kinds in `page_structure`** — declared in task type definitions, read by compose function:

```python
"competitive-brief": {
    "surface_type": "report",
    "page_structure": [
        {"kind": "narrative", "title": "Executive Summary",
         "reads_from": ["competitors/_synthesis.md"]},
        {"kind": "entity-grid", "title": "Competitor Profiles",
         "entity_pattern": "competitors/*/"},
        {"kind": "timeline", "title": "Recent Signals",
         "reads_from": ["signals/_tracker.md"]},
        {"kind": "trend-chart", "title": "Market Position",
         "assets": [{"type": "derivative", "render": "chart"}]},
    ],
}
```

**Extending the section kind vocabulary:** new kinds require (1) data contract definition, (2) rendering rules per surface type, (3) compose function update, (4) SKILL.md docs. Section kinds are curated — the constraint IS the value.

---

### Layer 3: Export Pipeline

Export converts an HTML output folder into a file format for interoperability. Export is **derivative, mechanical, separate, and on-demand**.

| Export Format | Primary Source | Valid Surface Types | Fidelity | Runtime |
|---|---|---|---|---|
| **PDF** | HTML → print CSS | All | High | `python_render` |
| **PPTX** | Deck sections → slides | `deck` | Medium | `python_render` (python-pptx) |
| **XLSX** | Data tables + chart data | `workbook`, `dashboard` | Medium | `python_render` (openpyxl) |
| **DOCX** | Report prose + assets | `report` | Medium | `python_render` (python-docx) |
| **MP4** | Video spec → Remotion | `video` | High | `node_remotion` |
| **PNG** | HTML → screenshot | All | Snapshot | `python_render` |

Export is NOT part of compose. The compose function outputs an HTML folder; the export pipeline reads that folder and converts it independently.

**Delivery channel transforms** (constraint, not surface type change):

| Channel | Constraint | Adaptation |
|---|---|---|
| **Web (iframe)** | None | Serve index.html directly |
| **Email** | Inline CSS, 600px, no JS | Email-safe CSS transform |
| **Slack** | No HTML rendering | Extract summary + link to web |
| **Notion** | Block-based | Convert sections to Notion blocks |

---

### Video Surface Type Detail

A video surface is first an **HTML experience** (CSS animations, scroll-triggered transitions), then optionally an MP4 export via Remotion. Output folder:

```
/tasks/{slug}/outputs/{date}/
├── index.html           # Playable HTML — CSS animations, auto-advance
├── spec.json            # Remotion-compatible scene graph
├── sections/            # Section partials (same pattern as other surface types)
├── assets/charts/       # Animated chart data (JSON + render instructions)
└── assets/frames/       # Static keyframes
```

Video section kind animations: `metric-cards` → number counters; `trend-chart` → animated line draw; `entity-grid` → staggered card reveal; `narrative` → lower-third typographic treatment.

Video is architecturally accommodated now via surface type + section kind abstractions. Implementation requires the `node_remotion` runtime (Phase 6+ of ADR-170).

---

### The Static → Live Spectrum

| Level | Output folder contents | Frontend behavior |
|---|---|---|
| **Static** | Rendered HTML + frozen assets | Display as-is |
| **Refreshable** | HTML + data files + render instructions | Re-render client-side |
| **Live** | HTML + data binding spec + API endpoints | Fetch fresh data in real-time |
| **Interactive** | HTML + JS components + event handlers | User filter/sort/drill-down |

The compose function always produces **Static** level. Higher levels are Phase 6+ (ADR-170 "output as runnable app").

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
  "surface_type": "dashboard",
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
| **Agent Framework (ADR-109/176)** | Agent Type Registry replaces `SKILL_ENABLED_ROLES` + `ROLE_PORTFOLIOS` seniority tiers. Pulse cadence absorbed into type definitions. |
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
