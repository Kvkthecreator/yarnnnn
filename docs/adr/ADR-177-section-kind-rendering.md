# ADR-177: Section Kind Rendering — Unified Parse+Render

**Date:** 2026-04-13
**Status:** Implemented (2026-04-13)
**Authors:** KVK, Claude
**Supersedes:** ADR-177 draft (2026-04-13) — integration point and chart rendering approach revised
**Extends:** ADR-170 (Compose Substrate — Phase 3 section partials, Phase 4 revision routing)
**Evolves:** ADR-130 (HTML-Native Output Substrate — compose.py kind-unaware rendering → kind-aware)

---

## Context

ADR-170 established the compose substrate: generation brief → LLM output → `parse_draft_into_sections()` → section partials + `sys_manifest.json`. The 11 section kinds are declared in the task type registry's `page_structure`, the output contracts in `assembly.py` (`_kind_output_contract()`) guide the LLM, and the infrastructure for section-aware processing exists end-to-end.

**The gap:** the rendering layer (`render/compose.py`) is kind-unaware. `compose_html()` receives flat markdown, runs it through `_render_markdown_to_html()`, and applies a surface-type layout. Every section kind gets the same treatment.

**The ordering problem:** the current pipeline compounds this gap by running compose *before* the section parse:

```
Step 12: _compose_output_html()        ← reads output.md, calls render service
                                          with flat markdown, no kind metadata
Step 12b: parse_draft_into_sections()  ← has sections_parsed in memory,
                                          writes section .md files + manifest
```

`sections_parsed` exists in memory at step 12b, but compose has already fired at step 12 without it. The two steps must be collapsed and reordered: parse first, then compose with the pre-parsed result.

Additionally, `_compose_output_html()` in `agent_execution.py` reads from the *agent workspace* and writes output.html back to the *agent workspace*, which then gets copied to the *task workspace*. This agent-workspace intermediary is a seam with no architectural value — the task workspace is the canonical output location.

Three constraints shape the correct solution:

1. **The LLM already follows output contracts.** `_kind_output_contract()` reliably produces parseable structured content. The renderer recognizes and upgrades these patterns — it does not need a different output format from the LLM.

2. **Two rendering mechanisms, not three.** Structured section kinds (metric-cards, entity-grid, tables) need typed HTML components built from parsed content. Chart section kinds (trend-chart, distribution-chart) have structured data in their content; the render service already has matplotlib — charts should be produced server-side, deterministically, without a client-side JS dependency. RuntimeDispatch assets (image, video, mermaid) are already resolved URLs embedded in the markdown before compose runs — they pass through unchanged. These are three different origins requiring three different treatments, not one uniform approach.

3. **The compose step is mechanical.** No LLM calls. Intelligence about what to produce belongs upstream in the generation brief (already handled). The compose function reads typed section content and produces typed HTML.

---

## Decision

### Collapse steps 12 and 12b into one unified operation: `_compose_and_persist()`

A new function `_compose_and_persist()` in `task_pipeline.py` replaces both `_compose_output_html()` and the standalone step 12b. It:

1. Receives `draft`, `page_structure`, `surface_type`, `pending_renders` (RuntimeDispatch assets), and task/agent workspace references
2. Calls `parse_draft_into_sections(draft, page_structure)` → `sections_parsed`
3. Sends a **section-content payload** to `POST /compose` on the render service
4. Receives composed HTML
5. Writes `output.html`, section `.md` partials, and `sys_manifest.json` to the **task workspace** atomically
6. Syncs `outputs/latest/` in one pass

`_compose_output_html()` in `agent_execution.py` is **deleted**. The agent workspace compose path is deleted. Task workspace is the only output path.

### New render service input contract

The `/compose` endpoint on `render/compose.py` gains a `sections` field that replaces the flat markdown approach for structured tasks:

```python
class SectionContent(BaseModel):
    kind: str        # one of 11 section kinds
    title: str
    content: str     # the section's markdown content (## header included)

class ComposeRequest(BaseModel):
    markdown: str              # full LLM output (backward compat — used when sections is empty)
    title: str = "Output"
    surface_type: str = "report"
    assets: list[dict] = []    # [{ref: "hero.png", url: "https://..."}] — RuntimeDispatch assets
    brand_css: Optional[str] = None
    user_id: Optional[str] = None
    sections: list[SectionContent] = []   # NEW — pre-parsed, kind-typed section content
```

When `sections` is provided, the renderer dispatches each section by kind. When empty (backward compat), the renderer falls back to current flat markdown behavior.

**Key architectural point:** The API sends *pre-parsed section content*, not raw markdown + metadata. The API service runs `parse_draft_into_sections()` before calling the render service. The render service never re-parses or re-splits the markdown. This keeps parsing logic in one place (API, `assembly.py`) and keeps the render service purely mechanical.

### Three rendering paths, clearly separated

**Path 1 — Markdown kinds** (`narrative`, `callout`, `checklist`, `timeline`, `status-matrix`):
- LLM output follows the existing contracts; no new format required
- Renderer wraps section in `<section class="kind-{name}">` and applies kind-specific CSS
- No parsing beyond standard markdown → HTML

**Path 2 — Structured-data kinds** (`metric-cards`, `entity-grid`, `comparison-table`, `data-table`):
- LLM output follows structured contracts (bold patterns, `###` headers, markdown tables)
- Renderer parses the structured patterns and produces typed HTML components (grid tiles, card layouts, styled tables with RAG indicators)
- CSS handles layout; HTML structure is what changes

**Path 3 — Chart kinds** (`trend-chart`, `distribution-chart`):
- LLM output is a markdown table following the output contract
- Renderer extracts the table data and calls matplotlib (already available in the render service Docker image) to produce a PNG
- PNG stored to Supabase storage via the render service's existing upload mechanism; URL embedded as `<img>` in the HTML
- **No Chart.js, no client-side rendering.** Server-side PNG is consistent with how `RuntimeDispatch(type="chart")` assets are produced, works in email delivery, works in PDF export, requires no JS dependency in the output document

**Path 4 — RuntimeDispatch assets** (image, video, mermaid SVG — not section kinds but present in output):
- Already resolved: agent called `RuntimeDispatch` during the tool loop, received a URL, embedded `![...](url)` in the markdown
- `pending_renders` carries `{ref, url}` pairs
- `_resolve_asset_urls()` substitutes refs with URLs — **unchanged**
- These are *not* section kind concerns; they pass through the compose step transparently

### How section kinds and RuntimeDispatch assets coexist

A section with `kind: "trend-chart"` and a `RuntimeDispatch` chart in the same output are different things:

- The `trend-chart` section is *structurally declared* in `page_structure` — the compose pipeline knows to expect it, the generation brief tells the LLM to produce a markdown table, and the compose step converts that table to a matplotlib PNG deterministically
- A `RuntimeDispatch(type="chart")` call is the *agent's judgment* during generation — the agent decided that specific data warranted a chart. The result is already a resolved URL embedded in the markdown.

Both can exist in the same output. They don't compete. The section kind renderer handles declared structural charts; `_resolve_asset_urls` handles agent-initiated chart URLs. The distinction is origin: pipeline-declared vs agent-judgment.

### Pipeline reordering in `execute_task()`

Current (broken order):
```
12.  _compose_output_html()          ← agent_execution.py, agent workspace, flat markdown
12b. parse_draft_into_sections()     ← task_pipeline.py, task workspace, has sections but composes already fired
```

After (correct order, single step):
```
12.  _compose_and_persist()          ← task_pipeline.py, task workspace only
       ├── parse_draft_into_sections(draft, page_structure)
       ├── POST /compose {sections, surface_type, assets}
       └── write output.html + sections/*.md + sys_manifest.json atomically
```

The `agent_output_folder` variable in `execute_task()` (currently used to locate the compose input) is no longer needed for the compose path. `task_output_folder` is the single output destination.

---

## Architecture

### Rendering pipeline (after)

```
                    ┌──────────────────────────────────┐
                    │ _compose_and_persist()            │
                    │  draft (LLM output)               │
                    │  page_structure (section kinds)   │
                    │  surface_type                     │
                    │  pending_renders (asset URLs)     │
                    └───────────┬──────────────────────┘
                                │
                    ┌───────────▼──────────────────────┐
                    │ parse_draft_into_sections()       │
                    │ → sections_parsed: {slug: {kind,  │
                    │   title, content}}                │
                    └───────────┬──────────────────────┘
                                │
                    ┌───────────▼──────────────────────┐
                    │ POST /compose                     │
                    │  {sections, surface_type, assets} │
                    └───────────┬──────────────────────┘
                                │
              ┌─────────────────┼──────────────────────┐
              │                 │                       │
   ┌──────────▼──────┐  ┌───────▼─────────┐  ┌────────▼────────┐
   │ Markdown kinds  │  │ Structured kinds │  │ Chart kinds     │
   │ narrative       │  │ metric-cards     │  │ trend-chart     │
   │ callout         │  │ entity-grid      │  │ distribution-   │
   │ checklist       │  │ comparison-table │  │   chart         │
   │ timeline        │  │ data-table       │  │                 │
   │ status-matrix   │  │                 │  │ → extract table │
   │                 │  │ → parse patterns │  │ → matplotlib    │
   │ → md→html       │  │ → component HTML │  │ → PNG → <img>  │
   │ → CSS class     │  │ → CSS class      │  │ → CSS class     │
   └──────────┬──────┘  └───────┬─────────┘  └────────┬────────┘
              │                 │                       │
              └─────────────────┼───────────────────────┘
                                │
                   ┌────────────▼──────────────────────┐
                   │ _resolve_asset_urls()              │
                   │ (RuntimeDispatch assets — refs→URLs)│
                   └────────────┬──────────────────────┘
                                │
                   ┌────────────▼──────────────────────┐
                   │ Surface layout                    │
                   │ (_apply_{surface}_layout)          │
                   │ kind-aware section arrangement    │
                   └────────────┬──────────────────────┘
                                │
                   ┌────────────▼──────────────────────┐
                   │ CSS assembly                      │
                   │ BASE_CSS + SURFACE_CSS + KIND_CSS │
                   │ + brand_css                       │
                   └────────────┬──────────────────────┘
                                │
                   ┌────────────▼──────────────────────┐
                   │ Full HTML document                 │
                   └───────────────────────────────────┘
                                │
                   ┌────────────▼──────────────────────┐
                   │ Atomic write to task workspace    │
                   │ outputs/{date}/output.html        │
                   │ outputs/{date}/sections/{slug}.md │
                   │ outputs/{date}/sys_manifest.json  │
                   │ outputs/latest/* (sync)           │
                   └───────────────────────────────────┘
```

### File changes

| File | Change |
|------|--------|
| `api/services/task_pipeline.py` | New `_compose_and_persist()` function replacing steps 12 + 12b. Collapses `_compose_output_html` call + standalone section parse + manifest write into one atomic operation. `agent_output_folder` variable no longer drives compose path. |
| `api/services/agent_execution.py` | **Delete** `_compose_output_html()`. No other changes. |
| `render/compose.py` | Add `SectionContent` model. Add `sections` field to `ComposeRequest`. Add `_split_by_sections()` dispatcher. Implement kind renderers per path (markdown: CSS wrapper, structured: parse+component, chart: matplotlib→PNG). Add `KIND_CSS`. `compose_html()` dispatches via kind when `sections` provided; falls back to current behavior when empty. |
| `render/main.py` | Validate `sections` field on `/compose` endpoint (optional, backward compat). |
| `api/services/compose/assembly.py` | Tighten output contracts for structured and chart kinds (Appendix). No structural changes. |

### No changes to

| File | Reason |
|------|--------|
| `api/services/task_types.py` | `page_structure` already declares section kinds — no changes needed |
| `api/services/compose/manifest.py` | `sys_manifest.json` schema unchanged — section provenance already tracked |
| `api/services/compose/revision.py` | Revision routing is orthogonal to rendering — staleness classification unchanged |
| `api/services/primitives/runtime_dispatch.py` | RuntimeDispatch produces assets via tool loop — unchanged |
| `api/services/render_assets.py` | `render_inline_assets()` handles mermaid/auto-chart from inline markdown — unchanged |

---

## Implementation Phases

### Phase 1: Pipeline reorder + markdown kind CSS (5 kinds)

Collapse steps 12 + 12b into `_compose_and_persist()`. Delete `_compose_output_html()`. Wire the new render service `/compose` endpoint to accept `sections`. For the 5 markdown kinds, wrap each section in `<section class="kind-{name}">` and add `KIND_CSS`.

**Test:** competitive-brief task with narrative + timeline + callout sections renders with CSS differentiation. `output.html` lands in task workspace directly. Agent workspace compose copy path gone.

**Effort:** ~150 lines in task_pipeline.py, ~80 lines in agent_execution.py (deletion), ~180 lines in compose.py. One session.

### Phase 2: Structured-data kinds (metric-cards, entity-grid, data-table)

Implement parsers and component HTML for the three most common structured kinds. `_parse_metric_cards()` extracts label/value/delta from bold patterns. `_parse_entity_grid()` extracts entity/description/badge from h3 patterns. `_parse_data_table()` post-processes markdown tables with numeric column detection.

**Test:** market-report task with metric-cards section renders as styled grid tiles with large numbers and colored deltas.

**Effort:** ~280 lines in compose.py. One session.

### Phase 3: Comparison-table + chart kinds (matplotlib)

Implement `_parse_comparison_table()` with status indicator post-processing (✓/✗/🟢/🟡/🔴 → styled cells). Implement `_parse_chart_section()` that extracts markdown table data and calls matplotlib to produce a PNG. PNG uploaded to Supabase storage (same upload path as render service skill outputs); URL embedded as `<img>` tag.

**Test:** competitive-brief with trend-chart section renders as an actual PNG chart, not a markdown table. Chart appears correctly in PDF export.

**Effort:** ~220 lines in compose.py + matplotlib chart function. One session.

### Phase 4: Surface × kind overrides

Implement surface-specific rendering overrides for impactful combinations: metric-cards in dashboard (KPI prominence), entity-grid in deck (one per slide), metric-cards in deck (hero metric). `_KIND_RENDERERS` dispatch table routes overrides; `report` is the universal fallback.

**Effort:** ~180 lines. One session.

### Phase 5: Output contract tightening (Appendix)

Tighten `_kind_output_contract()` contracts for structured and chart kinds to ensure mechanical parsability (per Appendix below). This is a prompt layer change — update `api/prompts/CHANGELOG.md`.

---

## Impact Radius

| ADR | Relationship |
|-----|-------------|
| ADR-170 | Extended — Phase 3 section partials now rendered by the compose step itself; output contracts tightened for structured kinds |
| ADR-178 | Aligned — output-driven tasks with `page_structure` declared at creation feed directly into `_compose_and_persist()`; section kinds declared at creation become the compose contract |
| ADR-130 | Evolved — HTML-native bet pays off; kind rendering is pure HTML+CSS+server-side PNG, no file format dependency |
| ADR-149 | Extended — DELIVERABLE.md surface type and section kinds influence `_compose_and_persist()` surface dispatch |
| ADR-173 | Preserved — accumulation-first still applies; compose step reads prior manifest for staleness detection before building generation brief |

### Documents needing updates (after Phase 1 implementation)

| Document | Update |
|----------|--------|
| `docs/architecture/compose-substrate.md` | Phase 5: Unified Parse+Render section (see below) |
| `docs/architecture/output-surfaces.md` | Add "Server-Side Chart Rendering" — matplotlib replaces Chart.js. Status: Proposed → Implemented for phases shipped. |
| `CLAUDE.md` | Add ADR-177 entry with key points: `_compose_output_html` deleted, `_compose_and_persist` in task_pipeline, section-content API contract, server-side matplotlib |
| `api/prompts/CHANGELOG.md` | Phase 5 output contract tightening |

---

## Rejected Alternatives

### A: Re-split markdown in the render service

The render service re-splits the full markdown on `##` boundaries to reconstruct section kinds. Rejected: `parse_draft_into_sections()` already runs in the API service and already handles title matching, case normalization, and unmatched sections. Duplicating this logic across a service boundary creates two parsers that can drift. The API sends pre-parsed content; the render service receives typed sections.

### B: Chart kinds via Chart.js (client-side)

Render `trend-chart`/`distribution-chart` as `<div data-chart-type="..." data-chart="...">` with a Chart.js CDN script. Rejected: (1) Adds a client-side JS dependency to every document containing a chart section. (2) Charts in email delivery (digest surface) require no-JS rendering — would require a parallel fallback path. (3) Charts in PDF export require server-side rendering anyway. (4) The render service already has matplotlib — using it is zero additional infrastructure. Server-side PNG is consistent, email-safe, export-safe.

### C: Section partials as separate compose requests

Each section partial sent as a separate `/compose` call, stitched into `index.html` afterward. Rejected: adds HTTP overhead, complicates surface layout (layout functions need all sections together), makes compose stateful about section ordering. Single call with all sections is simpler and correct.

### D: Chart kinds via RuntimeDispatch during tool loop

LLM detects `trend-chart` section kind in the generation brief and calls `RuntimeDispatch(type="chart")` with extracted data. Rejected: this conflates two different origins. Declared structural charts (from `page_structure`) are pipeline responsibilities — deterministic, no agent judgment needed. Agent-initiated charts during the tool loop are judgment calls. The compose path handles structural charts; RuntimeDispatch handles judgment charts. Keeping them separate preserves the clarity of each.

---

## Appendix: Output Contract Tightening (Phase 5)

Minor changes to `_kind_output_contract()` in `assembly.py` to ensure mechanical parsability of structured and chart kinds:

**metric-cards** (tightened): `2–6 KPI items. One per line, no other prose. Format: **Label:** value (delta). Include units. Delta as +/-% or +/-N.`

**entity-grid** (tightened): `One entry per entity separated by ### headers. Format: ### Entity Name\nOne-line description. Key fact. Optional status in [brackets]. No narrative transitions between entities.`

**trend-chart** (tightened): `Markdown table only — no prose before or after. First column: date (YYYY-MM-DD or YYYY-MM). Remaining columns: numeric metrics. Minimum 4 data points. Platform renders as line chart.`

**distribution-chart** (tightened): `Markdown table only — no prose before or after. First column: category label. Second column: numeric value. 3–10 categories. Platform renders as bar chart.`

**comparison-table** (tightened): `Markdown table. Entities as columns or rows. Use ✓/✗ for binary and 🟢/🟡/🔴 for RAG status cells. No mixed text+status in cells — one or the other.`
