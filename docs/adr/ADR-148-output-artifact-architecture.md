# ADR-148: Assets, Render Phase, and Production Pipeline

> **Status**: Proposed
> **Date**: 2026-03-29 (v3)
> **Authors**: KVK, Claude
> **Extends**: ADR-130 (HTML-Native Output Substrate), ADR-145 (Task Type Registry)
> **Supersedes**: RuntimeDispatch-during-generation pattern
> **Analysis**: `docs/analysis/output-quality-first-principles-2026-03-29.md`

---

## Context

Three iterations of E2E quality testing revealed that the output quality gap is not about agent count or process architecture. It's about **assets never making it into the output**.

Agents have chart/mermaid/image capabilities and RuntimeDispatch as a tool, but:
- RuntimeDispatch competes for tool rounds with web search — agents choose research over charts
- Chart specs require precise JSON construction during generation — error-prone, fails silently
- No validation that assets were produced
- Compose service receives markdown with broken image references
- Result: every output is plain text regardless of composition mode

---

## Decision

### Domain Definitions

**Asset** — a single produced file. Has a type: `text` (markdown), `chart` (SVG/PNG), `diagram` (SVG), `table` (markdown), `image` (PNG/JPG). Assets are atomic units. Each exists as a file.

**Output** — the collection of assets from one task run. Lives in `/tasks/{slug}/outputs/{date}/`. Contains the raw markdown, any rendered assets, and a manifest. An output is not yet composed.

**Composition** — mechanical assembly of an output's assets into a single viewable HTML artifact. Uses a composition mode (document, presentation, dashboard). Already exists in the compose service.

**Delivery** — transport of the composed output to an external destination. A side effect. Separate from production.

### The Core Change: Render Phase

Insert a mechanical render phase between generation and composition:

```
Generate (LLM)  →  Render (mechanical)  →  Compose (mechanical)  →  Deliver (transport)
     |                    |                       |                       |
 Agent writes        Extract data tables     Assemble markdown      Email / Slack /
 prose + inline      → render as charts.     + rendered assets      Notion
 data tables +       Extract mermaid blocks  into styled HTML
 mermaid blocks      → render as SVG.        per composition mode
```

**Generate**: The agent writes prose with data inline. Markdown tables with numeric data. Mermaid code blocks for diagrams. No RuntimeDispatch calls. No JSON chart specs. The agent focuses on thinking, researching, and writing. All tool rounds go to web search and context gathering.

**Render**: Post-generation, a new function `render_inline_assets()` parses the markdown:
- Markdown tables with numeric columns → chart render via render service
- Mermaid code blocks → diagram render via render service
- Rendered SVGs uploaded to storage, references inserted into markdown

**Compose**: Existing compose service takes enriched markdown (with rendered asset URLs) + composition mode → styled HTML. No change to compose service API.

### Asset Extraction Strategies

| Source in Markdown | Detection | Render Call | Type Inference |
|---|---|---|---|
| Table with numeric column | Regex: pipe-delimited rows containing numbers | `POST /render` type=chart | 2 columns → bar; date-like header → line; ≤6 rows + percentages → pie |
| Mermaid code block | ` ```mermaid ` fence | `POST /render` type=mermaid | Self-described by mermaid syntax |

The agent doesn't need to know about rendering. It writes data tables because that's how you present data in markdown. It writes mermaid blocks because that's how you describe relationships. The system recognizes these patterns and renders them.

### What Changes in the Agent's Experience

**Before**: Agent has ~2000 tokens of SKILL.md in system prompt, must construct RuntimeDispatch JSON specs, loses tool rounds to chart generation, often fails to produce any visuals.

**After**: Agent has no SKILL.md, no RuntimeDispatch during headless generation. System prompt is ~2000 tokens shorter. Agent writes naturally — prose, tables, mermaid. The system handles rendering.

Agent instruction includes: "Include markdown tables for numeric data — these are automatically rendered as charts. Include mermaid code blocks for diagrams — these are automatically rendered as visuals."

### Composition Mode Requirements

The existing composition modes (document, presentation, dashboard) already define visual assembly. The render phase ensures they receive actual assets:

- **document**: Rendered charts inserted adjacent to their source tables. Mermaid diagrams rendered inline. Tables styled as HTML tables.
- **presentation**: Each `##` heading = slide. Rendered charts and diagrams placed on their slides. Dense visuals.
- **dashboard**: Metric tables rendered as KPI cards. Trend data rendered as line charts. Dense grid layout.

These are existing compose service behaviors. The only change is that they now receive markdown with real rendered asset URLs instead of broken references.

### Output Validation

After render, before compose, the pipeline checks:
- Word count against process instruction targets
- Number of rendered assets (charts + diagrams produced)
- Warnings logged in manifest — don't block delivery

Validation is informational, not gating. Over time, warning patterns inform process instruction refinement.

### Delivery Separation

Delivery is transport, separate from production:
- Output exists in workspace whether or not delivery happens
- The app always shows all outputs (surfacing)
- Delivery channels: email (HTML + optional PDF), Slack (summary + link), Notion (structured page)
- Delivery status is metadata on the output manifest
- Delivery failure doesn't invalidate the output

---

## Consequences

### What changes
- New `render_inline_assets()` function in task pipeline (post-generation, pre-compose)
- RuntimeDispatch removed from headless generation tool set
- SKILL.md injection removed from task execution system prompt (~2000 token savings)
- Process instructions updated: "include markdown tables for data, mermaid for diagrams"
- Output validation added between render and compose (warnings in manifest)

### What stays the same
- Agent type registry and capabilities
- Task type registry structure (process steps, layout_mode)
- Compose service API (`POST /compose`)
- Render service API (`POST /render` — now called by pipeline, not by agents)
- Delivery service
- Frontend (reads output.html)
- Workspace storage

### What's removed
- RuntimeDispatch tool from headless primitive set
- SKILL.md fetch + injection during task execution
- `has_asset_capabilities()` gating for SKILL.md injection
- `has_capability(role, "compose_html")` gating — compose always runs
- `generate_email_html()` fallback in delivery — one rendering path
- MarkdownRenderer as primary output display — now loading state only

### Singular rendering path
Every task output goes through: generate → render → compose → `output.html`.
No branching based on agent capabilities. No fallback renderers.
- **Task page**: Always shows `output.html` via iframe
- **Email**: Always sends composed HTML
- **MarkdownRenderer**: Used only for chat messages and loading state, never for task outputs

---

## Implementation

### Phase 1: Render phase + agent simplification ✓
- `render_inline_assets()` — extract tables and mermaid, render via render service
- RuntimeDispatch removed from `HEADLESS_PRIMITIVES`
- SKILL.md injection removed from task execution system prompt
- Process instructions updated: "include data tables and mermaid diagrams"
- Render phase wired into both single-step and multi-step paths

### Phase 2: Compose-always + singular rendering ✓
- Compose runs for every task output regardless of agent type
- `has_capability(role, "compose_html")` gate removed
- Delivery uses composed HTML only (no `generate_email_html` fallback)
- Frontend MarkdownRenderer downgraded to loading state indicator

---

## Relationship to Existing ADRs

| ADR | Relationship |
|-----|-------------|
| ADR-130 (Output Substrate) | Extended — assets formalized, render phase makes the three-concern separation real |
| ADR-145 (Task Type Registry) | Unchanged — process instructions updated but registry structure same |
| ADR-118 (Skills/Output Gateway) | Evolved — render service called by pipeline post-processing, not by agents during generation |
| ADR-141 (Execution Architecture) | Extended — render phase added as explicit pipeline step |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-03-29 | v1 — Artifact types, composition templates, multi-agent assembly |
| 2026-03-29 | v2 — Output types as acceptance criteria, production phases, inline asset extraction |
| 2026-03-29 | v3 — Simplified: dropped output type registry (requirements belong in process instructions + composition modes). Focused on assets as first-class concept, render phase, and domain separation (assets/output/composition/delivery). |
