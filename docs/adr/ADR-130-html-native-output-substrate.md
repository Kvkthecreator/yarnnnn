# ADR-130: HTML-Native Output Substrate

> **Status**: Proposed
> **Date**: 2026-03-22
> **Authors**: KVK, Claude
> **Supersedes**: ADR-118 Phase D skills-as-format-builders model (partially)
> **Extends**: ADR-106 (Workspace Architecture), ADR-118 (Skills as Capability Layer), ADR-119 (Workspace Filesystem), ADR-120 (Project Execution), ADR-128 (Multi-Agent Coherence)
> **Implements**: FOUNDATIONS.md Axiom 2 (recursive perception), Axiom 4 (accumulated attention), Axiom 6 (autonomy)

---

## Context

YARNNN's output gateway (ADR-118) currently implements 8 skills organized as **format builders**: each skill takes a constrained JSON spec and produces a specific file format (PDF, PPTX, XLSX, chart PNG, etc.). The agent's LLM must express its output through each format's input schema — a different DSL per format.

### Problems with the current model

1. **Format-specific impedance mismatch.** The PPTX skill accepts `{title, slides: [{title, content}]}` — a schema so constrained that outputs are visually blank. The LLM cannot express visual richness through a limited JSON DSL. Meanwhile, Claude Code producing PPTX inline writes full python-pptx code with custom colors, shapes, and positioning — because it has the full expressiveness of a programming language, not a constrained schema.

2. **Skill-per-format scaling problem.** Each output format requires its own skill with its own input schema, rendering code, and maintenance. Adding visual richness means expanding each skill's DSL independently — an N×M matrix of features × formats.

3. **Multi-agent composition friction.** When a researcher finds logos, a data agent produces charts, and a content agent writes narrative — assembling these into a PPTX requires understanding python-pptx's object model (slide layouts, placeholder indices, shape positioning). Each format has its own composition semantics. The PM's assembly step must speak every format's language.

4. **Agent-to-agent consumption blocked.** A PPTX file is opaque to downstream agents. An agent cannot reason over another agent's slide deck. The output format serves human consumption at the expense of agent consumption — violating the recursive perception substrate (Axiom 2).

5. **Paradigm misalignment.** File formats (PPTX, XLSX, DOCX) are containers designed for desktop editing applications. Agent output is not authored iteratively in an editor — it arrives complete. The consumption pattern is view-and-evaluate, not open-in-app-and-edit. Optimizing for file formats optimizes for a workflow that doesn't exist in agent-produced work.

### The axiomatic ground

The simplest composition primitive that accommodates the widest range of expression will produce the best outputs. HTML is that primitive:

- It is the universal render target (browsers display it natively)
- It can express anything from a memo to a dashboard with charts, tables, images, and data
- It composes by concatenation with structure (images are `<img>`, charts are inline SVG, tables are `<table>`)
- It converts mechanically to every legacy format (PDF via print/puppeteer, images via screenshot)
- It IS the email format (zero-conversion delivery)
- Agents can read it (structured text with semantic markup)
- Claude is exceptionally good at generating it

This is not a bet on market direction. It is a structural truth about the nature of the problem: multi-agent, heterogeneous-asset composition into rich visual output. HTML eliminates the impedance mismatch that makes every other format harder.

---

## Decision

### HTML as the primary output substrate

Agent output is **structured content** (markdown with embedded data references, images, and semantic annotations) that the platform renders as **styled HTML**. HTML is the canonical visual representation. All other formats are **mechanical exports** from HTML, not independent rendering pipelines.

```
Agent produces: structured content (markdown + asset references)
     ↓
Workspace stores: source content + referenced assets (images, SVGs, data files)
     ↓
Render layer: source → styled HTML (with brand CSS, embedded assets, layout)
     ↓
Surfacing: HTML rendered in-app (outputs tab, meeting room, email)
     ↓
Export: HTML → PDF / HTML → image / structured data → XLSX (mechanical)
```

### Skills reframed: cognitive capabilities, not format builders

Skills stop being "format builders" and become "cognitive capabilities" — what agents can *do*, not what file format they produce. The output of every skill is workspace content (text, data, images) that flows into the HTML rendering pipeline.

| Old model (format-builder) | New model (cognitive capability) |
|---|---|
| `presentation` skill → PPTX file | Agent produces structured sections + assets → HTML renders as presentation-style layout → export to PDF/PPTX |
| `spreadsheet` skill → XLSX file | `data-analysis` capability → structured data tables + computations → HTML renders as interactive tables → export to XLSX |
| `chart` skill → PNG file | `visualization` capability → SVG/canvas charts as workspace assets → embedded in HTML output |
| `document` skill → PDF file | Agent produces markdown → HTML renders as document → export to PDF |
| `image` skill → composed PNG | `asset-acquisition` capability → images as workspace files → embedded in HTML output |

### The render service becomes an export service

The output gateway (yarnnn-render) evolves from 8 format-specific skill renderers to:

1. **HTML composition engine** — takes structured content + assets from workspace → produces styled, self-contained HTML with embedded assets, brand CSS, and layout intelligence
2. **Export pipeline** — mechanical conversion from HTML to legacy formats:
   - HTML → PDF (via puppeteer/playwright, high fidelity)
   - HTML → image/PNG (via screenshot, for thumbnails and previews)
   - Structured data → XLSX (direct from data, not from HTML)
   - HTML → email (already native — zero conversion)
3. **Asset rendering** — chart generation (matplotlib/d3 → SVG), diagram rendering (mermaid → SVG) — these produce assets that embed into HTML, not standalone files

### Multi-agent composition via HTML

The critical unlock: multi-agent composition becomes **structural**, not format-specific.

**Current model** (format-specific composition):
```
Researcher output (text) ─┐
Data agent output (JSON) ──┤── PM must understand python-pptx to compose
Content agent output (text)┤   into a PPTX with images, charts, narrative
Brand assets (images) ─────┘
```

**New model** (HTML composition):
```
Researcher output (markdown + images) ─┐
Data agent output (data tables + SVGs) ─┤── PM arranges HTML sections
Content agent output (markdown) ────────┤   All assets embed naturally
Brand assets (CSS + logos) ─────────────┘   via <img>, <svg>, <table>
```

The PM's assembly prompt already composes text from multiple contributors. With HTML as the substrate, it composes **rich visual content** with the same ease — because HTML composition is just arranging blocks of structured content, not manipulating format-specific object models.

### Workspace conventions for assets

Assets (images, charts, data files) contributed by agents live in the workspace filesystem and are referenced by path in the HTML output:

```
/agents/{slug}/outputs/{date}/
├── output.md          # structured content (primary)
├── output.html        # rendered HTML (generated by render layer)
├── manifest.json      # metadata (unchanged)
├── assets/
│   ├── chart-revenue.svg
│   ├── logo-competitor.png
│   └── data-metrics.json
└── style.css          # optional brand/layout overrides

/projects/{slug}/assembly/{date}/
├── output.md          # composed content from contributors
├── output.html        # rendered HTML
├── manifest.json
└── assets/            # aggregated from contributor assets
```

### Presentation-style layouts in HTML

The concern "but I need it to look like a presentation" is addressed by **layout modes** in the HTML rendering, not by producing PPTX files:

- **Document mode** — flowing text, headings, tables, charts. Default for reports, digests, analysis.
- **Presentation mode** — slide-like sections with full-bleed backgrounds, large type, image placement. Each `## Heading` or `---` delimiter becomes a "slide." Renders as a scrollable/navigable HTML presentation (like reveal.js or Slidev).
- **Dashboard mode** — grid layout with metric cards, charts, KPIs. For recurring operational outputs.
- **Data mode** — structured tables with sort/filter affordances. For data-heavy outputs.

The agent (or PM during assembly) specifies the layout mode. The render engine applies the appropriate CSS/structure. The same content can be re-rendered in different modes without regeneration.

### Brand application

User brand assets (logo, colors, fonts) stored in workspace (`/brand/` or project-level) are applied as CSS overrides during HTML rendering. This is structurally simpler than template-based branding in PPTX/DOCX (which requires manipulating slide masters, style definitions, etc.).

```
/brand/
├── logo.png
├── brand.css          # colors, fonts, spacing overrides
└── brand.json         # structured brand metadata
```

### In-app surfacing

Project outputs pages render the HTML directly. No download required for viewing. The output IS the interface:

- **Outputs tab** — rendered HTML inline (iframe or sanitized injection)
- **Meeting room** — output previews as rich cards with expandable HTML view
- **Email delivery** — HTML is the email body (zero conversion)
- **External sharing** — public URL renders the HTML; download buttons offer PDF/PPTX exports

### RuntimeDispatch evolution

The `RuntimeDispatch` primitive evolves:

**Current**: `RuntimeDispatch(type="presentation", input={slide_spec}, output_format="pptx")`

**New**: Two-phase approach:
1. **Asset rendering** (during generation): `RenderAsset(type="chart", input={data_spec})` → produces SVG/PNG in workspace assets folder. Used by agents to create visual assets during their generation step.
2. **Export** (post-generation, on-demand): `ExportOutput(format="pdf")` → mechanical conversion of the output HTML to a downloadable file. Triggered by delivery config or user request, not during generation.

This separates **creation** (agent produces content + assets) from **formatting** (platform renders HTML + exports to legacy formats).

---

## Relationship to ADR-118

ADR-118's core thesis — "Claude Code online," two-filesystem architecture, skills as curated capabilities — **remains valid**. What changes:

| ADR-118 concept | Status under ADR-130 |
|---|---|
| Two-filesystem architecture (capability + content) | **Preserved** — capability filesystem is skills/assets on render service; content filesystem is workspace |
| Skills follow SKILL.md conventions | **Preserved** — but SKILL.md describes cognitive capabilities, not format-specific rendering |
| Skill auto-discovery | **Preserved** — render service still discovers skills from folder structure |
| 8 format-builder skills | **Superseded** — dissolves into: asset renderers (chart, mermaid, image) + HTML composition engine + export pipeline |
| RuntimeDispatch primitive | **Evolved** — splits into RenderAsset (creation-time) + ExportOutput (delivery-time) |
| `content_url` on workspace_files | **Preserved** — rendered HTML and exported files stored in Supabase Storage |
| Render service Docker container | **Preserved** — gains puppeteer/playwright for HTML→PDF, keeps matplotlib/mermaid for asset rendering |

### Skills that survive as asset capabilities

- **chart** → asset renderer (data spec → SVG/PNG), embedded in HTML output
- **mermaid** → asset renderer (diagram spec → SVG), embedded in HTML output
- **image** → asset acquisition/composition (Pillow), produces workspace files
- **data** → data export (structured data → CSV/JSON), for XLSX export path

### Skills that dissolve into the HTML pipeline

- **pdf** → becomes an export from HTML (puppeteer), not a separate skill
- **pptx** → becomes an export from presentation-mode HTML, or deprecated
- **xlsx** → becomes an export from structured data tables, not from HTML
- **html** → becomes the primary render path, not a separate skill

---

## Impact Analysis

### Upstream (agent generation)

- **Agent pipeline prompts** (`agent_pipeline.py`): Role prompts gain awareness of asset capabilities. Agents told to produce structured markdown with asset references, not format-specific specs.
- **Assembly prompt** (`agent_pipeline.py` composition section): PM told to compose HTML sections from contributor markdown, not format-specific assembly.
- **SKILL.md injection**: Asset capability SKILLs injected (chart, mermaid, image specs). Format-builder SKILLs removed from context.
- **Headless primitives**: `RenderAsset` replaces `RuntimeDispatch` for creation-time asset generation.

### Midstream (workspace + render)

- **Workspace conventions** (`workspace-conventions.md`): Output folders gain `assets/` subfolder and `output.html` alongside `output.md`.
- **Render service** (`render/main.py`): New `/compose` endpoint (markdown + assets → HTML). `/render` endpoint simplified to asset rendering only. New `/export` endpoint (HTML → PDF/image).
- **Manifest schema**: `manifest.json` gains `layout_mode` field and `assets[]` array.

### Downstream (delivery + surfacing)

- **Delivery** (`delivery.py`): `deliver_from_output_folder()` sends `output.html` as email body (currently converts markdown→HTML — simpler with pre-rendered HTML).
- **Frontend outputs**: Outputs tab renders HTML directly instead of showing download links.
- **Export buttons**: "Download as PDF" / "Download as PPTX" triggers export service on-demand.

### Render service Docker

Gains: `puppeteer` or `playwright` (HTML→PDF, HTML→image)
Keeps: `matplotlib`, `mermaid-cli`, `pillow` (asset rendering)
Drops: `python-pptx` (PPTX export from HTML is a different path — or deprecated entirely)
Keeps: `openpyxl` (XLSX export from structured data)

---

## Phases

### Phase 1: HTML composition engine
- New `/compose` endpoint on render service: markdown + asset URLs → styled, self-contained HTML
- Layout modes: document (default), presentation, dashboard
- Brand CSS injection (from workspace `/brand/` files)
- `output.html` written alongside `output.md` in output folders

### Phase 2: In-app HTML surfacing
- Outputs tab renders `output.html` inline (sanitized iframe)
- Meeting room output cards show HTML preview
- Remove download-only UX for outputs

### Phase 3: Asset rendering pipeline
- `RenderAsset` primitive replaces `RuntimeDispatch` for charts/diagrams/images
- Assets written to `outputs/{date}/assets/` subfolder
- Agent pipeline prompts updated: produce markdown with `![](assets/chart.svg)` references
- Assembly prompt updated: compose HTML sections, reference contributor assets

### Phase 4: Export pipeline
- `/export` endpoint: HTML → PDF (via puppeteer), HTML → image
- Structured data → XLSX (direct, not via HTML)
- Export buttons in frontend (outputs tab, meeting room)
- Email delivery uses `output.html` directly

### Phase 5: Dissolve format-builder skills
- Remove `pptx`, `pdf`, `html` skills from render service (replaced by compose + export)
- Keep `chart`, `mermaid`, `image` as asset renderers
- Keep `data` for structured export
- Update RuntimeDispatch → RenderAsset in all primitives and prompts
- Update SKILL.md files to reflect cognitive capability framing

### Phase 6: Presentation-mode + brand system
- Presentation-mode HTML: slide-like sections, transitions, full-bleed layouts
- Brand system: `/brand/` workspace folder, CSS injection, logo placement
- Dashboard-mode HTML: metric cards, grid layouts
- Data-mode HTML: interactive tables with sort/filter (client-side JS)

---

## Trade-offs

### Accepted trade-offs

1. **PPTX export fidelity** — An HTML-to-PPTX export will not produce natively editable slides with slide masters, transitions, and PowerPoint-specific features. We accept this because: (a) agent output is viewed and evaluated, not edited in PowerPoint; (b) the visual quality of HTML-rendered content exceeds the quality of our current constrained PPTX skill; (c) PDF export from HTML is high-fidelity and covers most "share externally" needs.

2. **XLSX from data, not HTML** — Spreadsheets with formulas and filters are genuinely more useful as native XLSX than as HTML tables. We keep the structured-data-to-XLSX path as a direct export, not routed through HTML. This is the one case where the legacy format adds real value over HTML rendering.

3. **Puppeteer/playwright dependency** — HTML→PDF requires a headless browser in the Docker container. This increases image size and memory. Accepted because: the render service is already a heavy Docker image (pandoc, LaTeX, matplotlib, mermaid-cli), and puppeteer is the industry standard for high-fidelity HTML→PDF.

### Rejected alternatives

1. **Code-as-input model** — Let agents pass python-pptx/openpyxl code to the render service for execution. Rejected: solves the expressiveness problem but introduces security risk (arbitrary code execution), doesn't solve the multi-agent composition problem, and doesn't address agent-to-agent consumption.

2. **Rich JSON DSL per format** — Expand each skill's input schema to support more visual features. Rejected: N×M scaling problem (features × formats), doesn't solve composition, doesn't help agent consumption.

3. **Keep format-builder skills alongside HTML** — Dual approach. Rejected: violates FOUNDATIONS Derived Principle 7 (singular implementation). Two output paths means two sets of prompts, two composition strategies, two delivery paths.

---

## Axiom Alignment

| Foundation | Alignment |
|---|---|
| **Axiom 2 (Recursive Perception)** | HTML output is readable by downstream agents — structured text with semantic markup. PPTX/PDF output is opaque. HTML closes the recursive loop. |
| **Axiom 3 (Developing Entities)** | Agents can produce increasingly rich output as they develop — HTML's expressiveness ceiling is much higher than constrained JSON DSLs. Senior agents can produce dashboards; new agents produce simple documents. Same substrate. |
| **Axiom 4 (Accumulated Attention)** | Output quality compounds with tenure. HTML allows richer expression of accumulated domain knowledge (charts, cross-references, visual hierarchy) without format-specific friction. |
| **Axiom 6 (Autonomy)** | End-to-end autonomous flow: agent generates → HTML renders → delivers via email (HTML-native) or in-app. No human intervention to "open the file." |
| **Derived Principle 7 (Singular Implementation)** | One output substrate (HTML), one composition language, one rendering pipeline. No parallel format-specific paths. |

---

## Open Questions

1. **Presentation-mode navigation** — Should presentation-mode HTML be a scrollable page with visual slide breaks, or an interactive presenter view with keyboard navigation (like reveal.js)? Scrollable is simpler; presenter view is more "presentation-like."

2. **Client-side interactivity** — Dashboard-mode and data-mode benefit from client-side JS (sort/filter tables, hover tooltips on charts). How much JS is acceptable in output HTML? Zero-JS is safest for email delivery; rich-JS enables better in-app experience. Possible: two renders (email-safe static + in-app interactive).

3. **PPTX export priority** — Is PPTX export worth building at all? PDF covers "share externally." If specific users need PPTX, it could be a later phase or community contribution. Deferring saves significant effort.

4. **Brand system scope** — How sophisticated should brand application be? Minimum: logo + color palette + font. Maximum: full design system with component variants. Start minimum, expand based on user demand.

5. **Puppeteer vs. alternatives** — Puppeteer is heavy. Alternatives: `weasyprint` (Python, lighter, less fidelity), `wkhtmltopdf` (deprecated but light), `playwright` (similar to puppeteer, multi-browser). Evaluate during Phase 4.
