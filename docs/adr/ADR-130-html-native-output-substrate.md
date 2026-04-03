# ADR-130: HTML-Native Output Substrate — Three-Registry Architecture

> **Status**: Phases 1-2 Implemented. Phase 3 partially implemented (skill dissolution done; export pipeline + multi-runtime deferred).
> **Date**: 2026-03-23 (revised from 2026-03-22)
> **Authors**: KVK, Claude
> **Supersedes**: ADR-118 Phase D (format-builder skills model), ADR-117 Phase 3 seniority-gated capabilities
> **Extends**: ADR-106 (Workspace), ADR-109 (Agent Framework), ADR-118 (Skills Layer), ADR-119 (Workspace Filesystem), ADR-120 (Project Execution)

---

## Context

YARNNN agents produce work. That work requires capabilities — tools, compute, and external integrations.

### The capability problem (solved in Phase 1)

The original system conflated three concerns: what agents can do, where compute runs, and how capabilities are gated. Seniority-based capability progression created cold-start problems and pipeline complexity without quality benefit. Phase 1 resolved this with three static registries and deterministic type-scoped capabilities.

### The output problem (Phase 2)

Agents produce markdown + binary assets (charts, diagrams). The platform delivers this as basic HTML email or plain text. There is no styled, interactive output format. The compose engine exists (`POST /compose` on yarnnn-render) but is not wired into the agent execution pipeline.

### The bet: HTML-native

Agent output should be **HTML-native** — viewable, styled, interactive. HTML is the first-class output substrate:

1. **Agents produce content** — structured markdown + asset references (SVG, PNG, JSON)
2. **The platform composes** — markdown + assets → styled HTML with layout modes
3. **Export is derivative** — HTML → PDF, data → XLSX are mechanical, on-demand, not creative acts

The agent never thinks about file formats. The compose engine handles presentation. Format-specific skills (pptx, xlsx builders) dissolve — they were bottom-up ("what tools can we give agents?") when the right approach is top-down ("what should the user see?").

### The compute problem (Phase 3)

Not all capabilities run in one service. Charts need Python + matplotlib. Video needs Node.js + Remotion. Platform write-backs need OAuth + external APIs. Marketplace skills have their own runtimes. The three-registry architecture accommodates heterogeneous compute without framework changes.

### Skills as a capability pipeline

SKILL.md is the format — Claude Code compatible, marketplace-importable. Skills can be:
- **Built-in**: our own render service (chart, mermaid, image, compose)
- **Imported**: Claude Code marketplace, MCP tools, external APIs
- **Compute-backed**: Python render, Node.js Remotion, external APIs

The agent doesn't care where the capability lives. The registry routes it. This is the "internet Claude Code" — the same skill convention, but running on web infrastructure with multi-agent, multi-step collaborative execution.

---

## Decision

### Three registries, cleanly separated

#### 1. Agent Type Registry — the product catalog

Each agent type is a "hire" — a role the user adds to their project team. Type = deterministic capability set + display identity. 8 user-facing types + PM infrastructure.

Capabilities are fixed at creation. No earning, no progression. Personification comes from instructions (user-configurable, prompt-level), not from capability gating.

```python
AGENT_TYPES = {
    "briefer":    [read_platforms, summarize, produce_markdown, compose_html],
    "monitor":    [read_platforms, detect_change, alert, produce_markdown, compose_html],
    "researcher": [read_platforms, web_search, investigate, produce_markdown, chart, mermaid, compose_html],
    "drafter":    [read_platforms, produce_markdown, chart, mermaid, compose_html],
    "analyst":    [read_platforms, data_analysis, cross_reference, chart, mermaid, produce_markdown, compose_html],
    "writer":     [read_platforms, produce_markdown, compose_html],
    "planner":    [read_platforms, produce_markdown, compose_html],
    "scout":      [read_platforms, web_search, produce_markdown, chart, compose_html],
    "pm":         [read_workspace, check_freshness, steer_contributors, trigger_assembly, manage_work_plan],
}
```

Legacy roles (digest, synthesize, research, prepare, custom) mapped via `resolve_role()` + `LEGACY_ROLE_MAP`.

New types added by extending the registry + deploying runtimes. No framework changes required.

#### 2. Capability Registry — what each capability resolves to

Each capability maps to: category, runtime, tool (if any), skill docs (if any).

```
Cognitive (prompt-driven, no tool):
├── read_platforms, summarize, detect_change, cross_reference
├── data_analysis, alert, investigate
└── produce_markdown

Tool-backed (internal primitives):
├── web_search       → tool: WebSearch
└── read_workspace   → tool: ReadWorkspace

Asset production (compute runtimes):
├── chart            → runtime: python_render, tool: RuntimeDispatch, docs: chart/SKILL.md
├── mermaid          → runtime: python_render, tool: RuntimeDispatch, docs: mermaid/SKILL.md
├── image            → runtime: python_render, tool: RuntimeDispatch, docs: image/SKILL.md
└── video_render     → runtime: node_remotion, tool: RuntimeDispatch, docs: video/SKILL.md [future]

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
- **Imported**: SKILL.md from Claude Code marketplace, MCP tools, external APIs

Both registered identically. The agent doesn't know or care which sourcing mode a capability uses.

#### 3. Runtime Registry — where compute happens

```
internal:        In-process, no HTTP call
python_render:   yarnnn-render service (Docker: Python + matplotlib + pandoc + pillow + mermaid-cli)
node_remotion:   yarnnn-video service (Docker: Node.js + Remotion + Chrome) [future]
external:slack:  Slack API via user OAuth token
external:notion: Notion API via user OAuth token
```

---

## Three-concern separation

| Concern | Owner | Mechanism |
|---|---|---|
| **Capability** | Agent type (deterministic at creation) | Agent Type Registry defines capability set |
| **Presentation** | Platform (layout modes) | Compose engine: markdown + assets → styled HTML |
| **Export** | Platform (on-demand, mechanical) | HTML → PDF, data → XLSX, HTML → image |

Agents produce structured content (markdown + asset references). The platform handles how it looks and how it ships.

### Layout modes (platform-owned)

| Mode | Visual treatment | Best for |
|---|---|---|
| **document** | Flowing text, max-width, reading-optimized | Reports, digests, analysis |
| **presentation** | Full-screen sections, large type, slide breaks at `##`/`---` | Executive reviews, team updates |
| **dashboard** | CSS grid, metric cards, KPI panels | Operational summaries, status |
| **data** | Dense tables, tabular nums, sticky headers | Data-heavy outputs, comparisons |

Layout mode is decoupled from agent type. Any agent's output can be rendered in any mode.

---

## Output Pipeline

```
┌─────────────────────────────────────────────────────┐
│                 AGENT GENERATION                     │
│                                                      │
│  Agent type determines available capabilities.       │
│  Agent produces:                                     │
│  ├── Structured markdown (output.md)                 │
│  ├── Asset references via RuntimeDispatch (if type   │
│  │   has chart/mermaid/image capabilities)            │
│  └── Structured data (JSON for tables/metrics)       │
│                                                      │
│  RuntimeDispatch calls:                              │
│  ├── python_render → chart/mermaid/image → SVG/PNG   │
│  └── node_remotion → video → MP4 [future]            │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│        POST-GENERATION COMPOSE (Phase 2)            │
│                                                      │
│  If agent type has compose_html capability:           │
│  ├── Call POST /compose with output.md + asset URLs   │
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
│  ├── output.md        (structured source — feedback  │
│  │                      surface, agent-readable)     │
│  ├── output.html      (composed — human-readable,    │
│  │                      email body, web preview)     │
│  ├── manifest.json    (type, capabilities, assets)   │
│  └── assets/                                         │
│      ├── *.svg        (charts, diagrams)             │
│      ├── *.png        (images)                       │
│      └── *.json       (structured data)              │
└──────────────────┬──────────────────────────────────┘
                   │
          ┌────────┼─────────────────┐
          ▼        ▼                 ▼
     ┌─────────┐ ┌───────────┐ ┌──────────┐
     │ Agent   │ │ Platform  │ │ Export   │
     │ Consume │ │ Deliver   │ │ (Phase 3)│
     │         │ │           │ │          │
     │ Read    │ │ Send      │ │ HTML→PDF │
     │ output  │ │ output    │ │ data→XLS │
     │ .md via │ │ .html as  │ │ HTML→img │
     │ Read-   │ │ email or  │ │          │
     │ Agent-  │ │ display   │ │ On-demand│
     │ Context │ │ in app    │ │ download │
     └─────────┘ └───────────┘ └──────────┘
```

---

## What was implemented (Phase 1)

### Phase 1a: Registries + seniority deletion
- Three registries (`AGENT_TYPES`, `CAPABILITIES`, `RUNTIMES`) in `agent_framework.py`
- Deleted: `classify_seniority()`, `ROLE_PORTFOLIOS`, `get_promotion_duty()`, `get_eligible_duties()`, `SKILL_ENABLED_ROLES`
- Deleted: `_execute_promote_duty()` in composer.py, `promote_duty` action from Composer prompt (→ v3.0)
- Deleted: Tier 2 seniority gate in agent_pulse.py (all agents eligible)
- Deleted: `test_adr117_p3_duties.py`
- Helper functions: `get_type_capabilities()`, `has_asset_capabilities()`, `has_capability()`, `get_type_skill_docs()`
- Composer maturity signals: `senior_agents` → `proven_agents` (run count + approval heuristic)

### Phase 1b: v2 types + full caller migration
- 8 user-facing types + PM: briefer, monitor, researcher, drafter, analyst, writer, planner, scout
- `LEGACY_ROLE_MAP` + `resolve_role()` for backward compatibility
- `display_name`, `tagline`, `default_frequency` per type
- `list_agent_types()`, `get_type_display()` helpers
- All LLM-facing prompts migrated: Composer (v3.0, superseded by ADR-156), TP ManageAgent, TP behaviors, ManageAgent primitive, commands
- All code callers migrated: agent_creation, agent_pipeline, agent_execution, agent_pulse, composer, working_memory
- `VALID_ROLES` derived from `AGENT_TYPES` registry (single source of truth)
- `infer_scope()` uses `ROLE_TO_SCOPE` for all types
- `ROLE_PULSE_CADENCE` covers all v2 types + legacy mappings

### What stays from pre-ADR-130
- `RuntimeDispatch` tool — works, no rename needed. Type-scoping achieved via `has_asset_capabilities()` gating which SKILL.md gets injected.
- `_fetch_skill_docs()` — fetches all discovered skills. Acceptable cost (~4 SKILL.md files). Type-scoped selective fetch deferred.
- Output folder conventions (ADR-119) — unchanged
- Delivery pipeline — unchanged
- Feedback distillation (ADR-117 Phase 1) — agents still learn from user edits
- Coherence protocol (ADR-128) — self-assessments continue

---

## What's next (Phases 2-3)

### Phase 2: HTML-native output pipeline

The compose engine exists (`render/compose.py`, `POST /compose`) but is not wired into agent execution. This phase makes it a post-generation pipeline step.

**Implementation:**
1. After `generate_draft_inline()` completes, if agent type has `compose_html` capability:
   - Call `POST /compose` with `output.md` content + asset URLs from `pending_renders`
   - Apply layout mode (default: `document`; inferrable from content structure or project objective)
   - Store `output.html` in output folder alongside `output.md`
2. Update `deliver_from_output_folder()` to send composed HTML as email body (instead of basic Resend template)
3. Update manifest.json to include `output.html` with role `composed`
4. Frontend: render `output.html` inline in outputs tab / meeting room

**What this changes for users:**
- Agent output looks polished — styled, responsive, brand-consistent
- Same content, better presentation
- `output.md` remains the feedback/edit surface (users edit markdown, not HTML)
- HTML regenerated on next run or on edit

**What this does NOT do:**
- Does not add a new tool for agents to call (compose is a pipeline step, not an agent decision)
- Does not change what agents produce (still markdown + assets)
- Does not require agents to know about HTML

### Phase 3: Export pipeline + skill dissolution + multi-runtime

**Export pipeline (derivative, on-demand):**
- HTML → PDF (pandoc/wkhtmltopdf, from composed HTML)
- Data → XLSX (from structured JSON in assets/)
- HTML → image (screenshot, for social/preview)
- Triggered by user action ("Download as PDF"), not during generation

**Skill dissolution:**
- `render/skills/pptx/` → deleted (presentation layout mode replaces)
- `render/skills/html/` → absorbed into compose engine
- `render/skills/data/` → absorbed into compose engine
- `render/skills/pdf/` → retained as export step only (not agent-facing)
- `render/skills/xlsx/` → retained as export step only (not agent-facing)
- `render/skills/chart/` → retained (asset renderer, compute primitive)
- `render/skills/mermaid/` → retained (asset renderer, compute primitive)
- `render/skills/image/` → retained (asset renderer, compute primitive)

**Multi-runtime support:**
- Node.js Remotion service for video generation (validates architecture)
- External API runtimes for platform write-backs (Slack, Notion, Linear)
- Marketplace SKILL.md imports for new capabilities
- Adding a new runtime requires: registry entry + deployed service + SKILL.md. No framework changes.

---

## Trade-offs

### Accepted

1. **No capability progression** — Agent types have fixed capability sets. Development is knowledge depth, not capability breadth.
2. **HTML as primary output** — Export fidelity (PDF, PPTX) may be lower than native format tools. Accepted because agent output is viewed, not edited in desktop apps.
3. **RuntimeDispatch not renamed** — The tool works. Type-scoping achieved via capability gating. Cosmetic rename deferred indefinitely.
4. **All-or-nothing skill doc fetch** — Current `_fetch_skill_docs()` fetches all discovered skills (~4 files, ~2K tokens). Acceptable cost. Selective fetch deferred.

### Rejected

1. **Seniority-gated capabilities** — Cold-start problems, subjective LLM judgment, pipeline complexity.
2. **Format-specific agent tools** (pptx builder, xlsx builder) — Bottom-up approach. Compose engine + export pipeline is top-down and more correct.
3. **Agents deciding layout mode** — Layout is a presentation concern, not an agent concern. Platform owns it.

---

## Axiom Alignment

| Foundation | Alignment |
|---|---|
| **Axiom 1 (Two Layers)** | Agent types are domain-cognitive with fixed capabilities. TP/Composer creates agents of known types. |
| **Axiom 2 (Recursive Perception)** | Structured markdown is agent-readable. Composed HTML is human-readable. Same source, two consumers. |
| **Axiom 3 (Developing Entities)** | Development is knowledge depth: memory, preferences, domain thesis. Not capability breadth. |
| **Axiom 4 (Accumulated Attention)** | Value compounds through domain knowledge. A tenured agent produces better output because it knows more, not because it has more tools. |
| **Axiom 6 (Autonomy)** | End-to-end autonomous flow. User authorization for consequential actions is explicit, not earned. |
