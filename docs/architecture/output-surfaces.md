# Architecture: Output Surfaces

> **Status:** Canonical (ADR-170 RD-6/7/8/9). Proposed — not yet implemented.
> **Date:** 2026-04-10
> **Rule:** All output visual paradigm, section kind, and export decisions should be consistent with this document.
> **Related:**
> - [ADR-170: Compose Substrate](../adr/ADR-170-compose-substrate.md) — governing ADR (RD-6 through RD-9)
> - [ADR-130: HTML-Native Output Substrate](../adr/ADR-130-html-native-output-substrate.md) — HTML-native bet
> - [compose-substrate.md](compose-substrate.md) — the compose function that operates on these abstractions
> - [output-substrate.md](output-substrate.md) — production pipeline (rendering, asset production)

---

## Core Principle

**Output is always HTML. Surface types are visual paradigms, not file formats. Export is derivative.**

YARNNN is HTML-native (ADR-130). Every output the platform produces is an HTML experience. But HTML that *looks like* a deck, *looks like* a dashboard, *looks like* a data table, *looks like* a video. The user thinks in paradigms ("I want a dashboard"), not in formats ("I want an HTML file with CSS grid"). Export to `.pptx`, `.pdf`, `.xlsx` is a downstream, lossy, mechanical transformation for interoperability — not part of the output model.

This document governs three layers:

1. **Surface types** — the visual paradigms (how humans consume the output)
2. **Section kinds** — the component vocabulary (typed building blocks that compose within any surface)
3. **Export pipeline** — mechanical format conversion (separate concern, separate service)

---

## Layer 1: Surface Types

A surface type is a **visual paradigm** — a distinct way humans consume information. Each maps to a complete HTML experience with its own interaction model, layout system, and consumption pattern.

### The Catalog

| Surface Type | Paradigm | Consumption Model | Layout System | Interaction |
|---|---|---|---|---|
| **`report`** | Flowing narrative document | Sequential reading, start to finish | Single column, max-width, reading-optimized | Scroll, section anchors |
| **`deck`** | Discrete full-screen frames | One idea per frame, presented | Full-viewport sections, scroll-snap | Navigate frame-to-frame, arrow keys |
| **`dashboard`** | Single-canvas overview | At-a-glance, spatial scanning | CSS grid, responsive tiles | Grid arrangement, optional drill-down |
| **`digest`** | Grouped/chronological stream | Quick triage — what matters, what changed | Stacked groups, expand/collapse | Scan headers, expand detail |
| **`workbook`** | Tabular-first, data-dense | Analysis, comparison, filtering | Tables as primary content, derived charts | Sort, filter, pivot (future: interactive) |
| **`preview`** | In-context mockups | Content shown as it would appear elsewhere | Platform-framed cards (phone, inbox, feed) | Scroll between mockups |
| **`video`** | Sequential animated frames | Temporal, narrated, presented | Timeline-driven scene graph | Play/pause, timeline scrub |

### What surface types are NOT

- **Not file formats.** "Deck" ≠ `.pptx`. "Workbook" ≠ `.xlsx`. The surface type is the visual paradigm; the file format is a lossy export derivative.
- **Not layout CSS classes.** The current `compose.py` implements surface types as CSS mode selectors (`.document`, `.presentation`, etc.). That's an implementation detail. The architectural concept is the visual paradigm + section-kind arrangement rules.
- **Not delivery channels.** Email is a delivery channel, not a surface type. A digest surface type can be delivered via email (with inline CSS constraints) or displayed on the web (with full CSS). The delivery transform adapts the surface to the channel.

### Surface type selection

The `surface_type` field on task type definitions (in `task_types.py`) determines which visual paradigm the compose function targets. This replaces the current `layout_mode` field.

| Task Type Category | Natural Surface Type | Why |
|---|---|---|
| `track-*` (context accumulation) | `dashboard` | Entity monitoring is spatial — at-a-glance status, side-by-side comparison |
| `*-brief`, `*-report` (analysis) | `report` | Research is narrative — sequential reading, supporting evidence inline |
| `*-update` (stakeholder communication) | `deck` | Updates are presented — one point per frame, visual anchors |
| `*-digest` (operational awareness) | `digest` | Digests are triage — what happened, what matters, quick scan |
| `daily-update` (heartbeat artifact) | `digest` | Morning briefing = triage, not deep reading |
| `meeting-prep` (preparation) | `report` | Prep docs are read sequentially with reference material |
| `content-*` (creative/marketing) | `preview` | Content is consumed in-platform — show how it looks there |
| Future: data analysis tasks | `workbook` | Analysis is tabular-first with derived visualizations |
| Future: video briefing tasks | `video` | Temporal presentation of information, animated data |

### The PPT-killer / Excel-killer analogy

The startup wave Kevin references — Gamma (deck), Tome (narrative), Beautiful.ai (deck), Rows (spreadsheet), Hex (notebook) — all prove the same thesis: the output IS HTML, it just *looks like* the paradigm it replaces. YARNNN's surface types follow the same model. A `deck` surface type produces an HTML experience with scroll-snap sections, large typography, and visual anchors. Export to `.pptx` is available for compatibility, but the primary artifact is the HTML experience.

The architectural advantage: because the primary artifact is always HTML, the platform owns the rendering. Brand theming, interactive elements, live data binding, accessibility — all controlled by the platform, not delegated to a file format's constraints.

---

## Layer 2: Section Kinds

Section kinds are **typed components** — semantic building blocks the compose function understands. Each kind has a defined data contract (what data it takes) and rendering rules per surface type (how it looks in each paradigm).

### The Catalog

| Kind | Data Contract | Use Case |
|---|---|---|
| **`narrative`** | Prose paragraph(s); optional: pullquote, highlight, source_refs | Executive summaries, analysis sections, explanations |
| **`metric-cards`** | Array of 2-4 KPIs: `{label, value, delta?, sparkline_data?, unit?}` | Revenue metrics, health indicators, KPI panels |
| **`entity-grid`** | Array of entities: `{icon?, title, subtitle, badge?, detail_ref?}` | Competitor profiles, team roster, portfolio companies |
| **`comparison-table`** | Entities × attributes matrix: `{entities[], attributes[], values[][], rag_colors?}` | Feature comparison, vendor evaluation, scoring rubric |
| **`trend-chart`** | Time-series: `{series[], x_label, y_label, annotations?}` | Revenue over time, signal frequency, growth curves |
| **`distribution-chart`** | Categorical: `{categories[], values[], chart_type: bar/pie/treemap}` | Market share, category breakdown, resource allocation |
| **`timeline`** | Events: `{date, title, description, source?, severity?}[]` | Signal timeline, changelog, milestone tracker |
| **`status-matrix`** | Entities × criteria with indicators: `{entities[], criteria[], statuses[][]}` | Competitor health, project status, risk assessment |
| **`data-table`** | Tabular: `{headers[], rows[][], sort_by?, highlight_rules?}` | Financial data, raw metrics, detailed comparisons |
| **`callout`** | Single insight: `{severity: info/warning/critical, title, body, source?}` | Key finding, risk alert, recommendation |
| **`checklist`** | Items with status: `{text, status: done/pending/blocked, assignee?}[]` | Next steps, review criteria, action items |

### How section kinds render per surface type

The same section kind produces different HTML per surface type. This is the Palantir/Foundry insight: the widget is reusable, the canvas determines arrangement.

| Kind | `report` | `deck` | `dashboard` | `digest` | `video` |
|---|---|---|---|---|---|
| `narrative` | Full-width prose | Text overlay on frame | Wide card, abbreviated | Collapsed paragraph | Lower-third text overlay |
| `metric-cards` | Inline stat boxes | Hero metrics, one per frame | Grid tiles | Compact stat row | Animated counter entrance |
| `entity-grid` | Vertical card list | One entity per frame, or 2x2 grid | Responsive card grid | One-line entity rows | Sequential card reveal |
| `comparison-table` | Full-width table | Simplified highlight table | Card with horizontal scroll | Hidden (too dense) | Row-by-row build animation |
| `trend-chart` | Inline chart (svg/png) | Full-frame chart | Chart tile in grid | Sparkline only | Animated line draw |
| `timeline` | Vertical timeline | One event per frame | Timeline card | Grouped event list | Sequential event appearance |
| `callout` | Bordered callout box | Full-frame callout | Alert tile | Highlighted row | Fade-in overlay |

### Section kinds in `page_structure`

Section kinds are declared in the `page_structure` field on task type definitions. The compose function reads this structure and uses it to: (a) build the generation brief (telling the LLM what to write per section), (b) parse the LLM's output into section partials, and (c) render each partial with surface-appropriate HTML.

```python
# In task_types.py
"competitive-brief": {
    "surface_type": "report",
    "page_structure": [
        {"kind": "narrative", "title": "Executive Summary",
         "reads_from": ["competitors/_synthesis.md"]},
        {"kind": "entity-grid", "title": "Competitor Profiles",
         "entity_pattern": "competitors/*/",
         "assets": [{"type": "root", "pattern": "competitors/assets/*-favicon.png"}]},
        {"kind": "timeline", "title": "Recent Signals",
         "reads_from": ["signals/_tracker.md"]},
        {"kind": "trend-chart", "title": "Market Position",
         "reads_from": ["competitors/*/analysis.md"],
         "assets": [{"type": "derivative", "render": "chart"}]},
    ],
}

"daily-update": {
    "surface_type": "digest",
    "page_structure": [
        {"kind": "callout", "title": "Top Priority",
         "reads_from": ["signals/_tracker.md"]},
        {"kind": "metric-cards", "title": "Workspace Health",
         "reads_from": ["_system/health"]},
        {"kind": "entity-grid", "title": "What Changed",
         "reads_from": ["*/latest"]},
        {"kind": "checklist", "title": "Next Steps",
         "reads_from": ["tasks/*/steering.md"]},
    ],
}

"investor-update": {
    "surface_type": "deck",
    "page_structure": [
        {"kind": "narrative", "title": "Opening",
         "reads_from": ["workspace/IDENTITY.md"]},
        {"kind": "metric-cards", "title": "Key Metrics",
         "reads_from": ["market/_synthesis.md", "relationships/_synthesis.md"]},
        {"kind": "trend-chart", "title": "Growth",
         "reads_from": ["market/*/analysis.md"]},
        {"kind": "entity-grid", "title": "Competitive Landscape",
         "reads_from": ["competitors/*/profile.md"]},
        {"kind": "narrative", "title": "Roadmap & Ask",
         "reads_from": ["projects/_synthesis.md"]},
    ],
}
```

### Extending the section kind vocabulary

New section kinds can be added to the catalog when a genuine need emerges that existing kinds can't serve. The protocol:

1. Define the data contract (what structured data the kind takes)
2. Define rendering rules per surface type (how it looks in each paradigm)
3. Add to the compose function's rendering engine
4. Add skill documentation (SKILL.md) so the LLM knows how to produce output for this kind

Section kinds are **curated, not arbitrary**. The constraint IS the value — a finite vocabulary enables consistent rendering, reliable theming, and deterministic export. Adding a new kind is a deliberate architectural decision, not a casual extension.

---

## Layer 3: Export Pipeline

Export converts an HTML output folder into a file format for interoperability with legacy tools. Export is:

- **Derivative** — the HTML surface is the primary artifact. The export is a lossy transformation.
- **Mechanical** — zero LLM cost. Deterministic conversion.
- **Separate** — handled by `yarnnn-render` service, not by the compose substrate.
- **On-demand** — generated when the user requests it or when delivery requires it (e.g., email attachment).

### Export transforms

| Export Format | Primary Source | Valid Surface Types | Fidelity | Runtime |
|---|---|---|---|---|
| **PDF** | HTML → print CSS → PDF | All | High — print stylesheet preserves layout | `python_render` (weasyprint/puppeteer) |
| **PPTX** | Deck sections → slides | `deck` | Medium — structure preserved, CSS styling lossy | `python_render` (python-pptx) |
| **XLSX** | Data tables + chart data | `workbook`, `dashboard` | Medium — data preserved, layout lossy | `python_render` (openpyxl) |
| **DOCX** | Report prose + inline assets | `report` | Medium — prose preserved, assets flattened | `python_render` (python-docx) |
| **MP4** | Video spec → Remotion render | `video` | High — frame-accurate render | `node_remotion` |
| **PNG** | HTML → screenshot | All | Snapshot — single frame, no interactivity | `python_render` (puppeteer) |

### Export is NOT part of compose

The compose function's output is an HTML folder (index.html + section partials + assets + manifest). The export pipeline reads that folder and converts it. The compose function never needs to know whether export will happen or to which format. This separation means:

- Adding a new export format doesn't change the compose function
- The same output folder can be exported to multiple formats
- Export quality improves independently of compose quality

### Delivery channel transforms

Delivery channels impose constraints on the HTML surface but don't change the surface type:

| Channel | Constraint | Adaptation |
|---|---|---|
| **Web (iframe)** | None — full CSS/JS | Serve index.html directly |
| **Email** | Inline CSS, 600px max, no JS, images as CID attachments | Email-safe CSS transform, image inlining |
| **Slack** | No HTML rendering | Extract summary text + link to web view |
| **Notion** | Block-based, no custom CSS | Convert sections to Notion blocks via API |

Delivery channel transforms are a concern of `delivery.py`, not of the compose substrate or the export pipeline.

---

## Video Surface Type (Detail)

Video warrants expanded treatment because it extends the model furthest from static HTML.

### What video means in the HTML-native model

A video surface type is first an **HTML experience** — a page with CSS animations, scroll-triggered transitions, and timed sequences. The output folder contains:

```
/tasks/{slug}/outputs/{date}/
├── index.html           # Playable HTML — CSS animations, auto-advance
├── spec.json            # Remotion-compatible scene graph (sections → scenes)
├── sections/            # Section partials (same as other surface types)
│   ├── opening.html
│   ├── metrics.html
│   └── closing.html
├── assets/
│   ├── charts/          # Animated chart data (JSON + render instructions)
│   ├── frames/          # Static keyframes (PNG/SVG)
│   └── audio/           # Narration track, music (future)
├── data/
│   └── scene-data.json  # Per-scene data bindings
└── sys_manifest.json
```

### Two consumption modes

1. **HTML playback** — the `index.html` is a self-contained animated presentation. CSS `@keyframes`, `scroll-timeline`, and `animation-timeline` create a temporal experience in the browser. No video file needed.

2. **MP4 export** — `spec.json` is a Remotion-compatible scene graph. The `node_remotion` runtime reads it and renders a frame-accurate `.mp4`. This is the export derivative — same relationship as deck → PPTX.

### Section kinds in video

Section kinds animate according to their data contract:

| Kind | Video Treatment |
|---|---|
| `metric-cards` | Number counters animate from 0 to final value; delta arrows slide in |
| `trend-chart` | Line draws left-to-right; data points appear sequentially |
| `entity-grid` | Cards reveal one by one with stagger delay |
| `narrative` | Text fades in as lower-third overlay or full-frame typographic treatment |
| `timeline` | Events appear chronologically with scroll-triggered entrance |
| `comparison-table` | Rows build one at a time; winning cells highlight |
| `callout` | Pulse animation on entrance; holds for emphasis |

### Video as future phase

Video is architecturally accommodated now — the surface type and section kind abstractions support it without special-casing. Implementation requires the `node_remotion` runtime (listed in ADR-130 Runtime Registry as future). Phase 6+ of ADR-170.

---

## The Static → Live Spectrum

Surface types and section kinds naturally accommodate a spectrum from static snapshot to live application:

| Level | What's in the output folder | Frontend behavior | Use case |
|---|---|---|---|
| **Static** | Rendered HTML + frozen assets (SVG/PNG) | Display as-is | Email delivery, PDF export, archival |
| **Refreshable** | HTML + data files + render instructions | Re-render assets client-side from data files | Dashboard with stale-until-refresh data |
| **Live** | HTML + data binding spec + API endpoints | Fetch fresh data, re-render in real-time | Operational dashboard, monitoring |
| **Interactive** | HTML + JS components + event handlers | User interaction (filter, sort, drill-down) | Data exploration, workbook analysis |
| **Application** | HTML + full client-side logic + state management | Standalone page application | BI dashboard, runnable report |

The compose function always produces the **static** level. Higher levels require frontend capabilities declared in the section kind's data contract and enabled by the surface type. This is the Phase 6 "output as runnable app" trajectory from ADR-170 — deferred but structurally anticipated.

---

## Relationship to Other Architecture

| Component | Relationship |
|---|---|
| **Compose Substrate (ADR-170)** | Compose function reads `page_structure` (surface type + section kinds) and produces output folder. This doc defines the vocabulary; compose-substrate.md defines the function. |
| **Output Substrate (ADR-130/148)** | Production pipeline renders section kinds into HTML. Phase 3 (COMPOSE) applies surface-type-specific arrangement. This doc defines what; output-substrate.md defines how. |
| **Task Type Registry** | `surface_type` and `page_structure` fields replace `layout_mode`. Section kinds in `page_structure` are the structural template the compose function reads. |
| **Render Service** | Produces derivative assets (charts, mermaid SVGs, video frames). Handles export transforms (HTML → PDF/PPTX/XLSX/MP4). Separate from compose. |
| **Delivery Service** | Adapts surface type for delivery channel (email inline CSS, Slack summary extraction). Separate from compose and export. |
| **SKILL.md conventions (ADR-118)** | Section kind rendering can reference skill documentation for asset production (chart SKILL.md, mermaid SKILL.md). LLM generation brief references skill docs for section-kind-specific output formatting. |
| **FOUNDATIONS Axiom 2** | Surface types make the accumulation thesis visible — accumulated context is projected through section kinds into a visual paradigm the user recognizes. |

---

## Revision History

| Date | Version | Change |
|---|---|---|
| 2026-04-10 | v1 | Initial — 7 surface types, 11 section kinds, 6 export transforms, video detail, static→live spectrum. |
