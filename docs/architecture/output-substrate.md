# Output Substrate Architecture

> **Status**: Canonical (ADR-130)
> **Date**: 2026-03-22
> **Rule**: All output-related architecture should be consistent with this document.

---

## Core Principle

**Agent output is structured content, not files.** The platform renders it visually for humans and exposes it structurally for agents. Legacy file formats are mechanical exports for external sharing.

---

## The Output Pipeline

```
┌─────────────────────────────────────────────────┐
│                AGENT GENERATION                  │
│                                                  │
│  Agent produces:                                 │
│  ├── Structured markdown (output.md)             │
│  ├── Asset references (charts, images, diagrams) │
│  └── Layout hint (document | presentation |      │
│       dashboard | data)                          │
│                                                  │
│  Assets produced via RenderAsset primitive:       │
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
│  ├── manifest.json    (metadata, asset refs)     │
│  └── assets/                                     │
│      ├── chart-revenue.svg                       │
│      ├── logo.png                                │
│      └── data-summary.json                       │
│                                                  │
│  /projects/{slug}/assembly/{date}/               │
│  ├── output.md        (composed from contribs)   │
│  ├── manifest.json                               │
│  └── assets/          (aggregated)               │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│            HTML COMPOSITION ENGINE               │
│         (render service /compose endpoint)        │
│                                                  │
│  Input: output.md + assets + layout_mode + brand │
│  Output: self-contained HTML                     │
│                                                  │
│  Layout modes:                                   │
│  ├── document   — flowing text, tables, charts   │
│  ├── presentation — slide-like sections          │
│  ├── dashboard  — metric cards, grid layout      │
│  └── data       — structured tables              │
│                                                  │
│  Brand injection:                                │
│  ├── /brand/brand.css (colors, fonts)            │
│  ├── /brand/logo.png  (header placement)         │
│  └── defaults if no brand configured             │
└──────────────────┬──────────────────────────────┘
                   │
          ┌────────┼────────┐
          ▼        ▼        ▼
     ┌─────────┐ ┌──────┐ ┌───────┐
     │ In-App  │ │Email │ │Export │
     │ Render  │ │      │ │       │
     │         │ │HTML  │ │HTML   │
     │ Outputs │ │body  │ │→ PDF  │
     │ tab,    │ │(zero │ │→ image│
     │ meeting │ │conv) │ │→ PPTX │
     │ room    │ │      │ │data   │
     │         │ │      │ │→ XLSX │
     └─────────┘ └──────┘ └───────┘
```

---

## Multi-Agent Composition

The key architectural advantage: multi-agent composition operates in **one language** regardless of output complexity.

### Before (format-specific composition)

Each output format required format-specific assembly logic:
- PPTX: understand slide layouts, placeholder indices, shape positioning
- PDF: understand LaTeX templates, pandoc options
- XLSX: understand sheet structures, cell formatting
- The PM assembly step needed format-specific knowledge per output type

### After (HTML composition)

All agents produce structured markdown with asset references. Composition is structural:

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

<!-- Content agent's contribution -->
## Executive Summary
Based on the analysis above...
```

The PM arranges these sections, adds transitions, selects layout mode. The render engine handles visual presentation. No format-specific knowledge required at the composition layer.

---

## Capability Architecture (Skills Reframe)

### Asset capabilities (produce workspace files)

| Capability | Tool | Input | Output | When used |
|---|---|---|---|---|
| **chart** | matplotlib | Data spec (labels, datasets, chart_type) | SVG or PNG in `assets/` | Agent needs data visualization |
| **diagram** | mermaid-cli | Mermaid spec (flowchart, sequence, etc.) | SVG in `assets/` | Agent needs structural diagrams |
| **image** | Pillow | Composition spec (layers, text, shapes) | PNG in `assets/` | Agent needs composed images |

### Cognitive capabilities (agent intelligence, not render service)

These are capabilities the agent exercises during generation — they're about *what the agent can do*, not what the render service produces:

| Capability | Description | Available to |
|---|---|---|
| **research** | Web search, source investigation | research role, senior agents |
| **data-analysis** | Cross-reference data, compute metrics, produce structured tables | analyst role, senior agents |
| **content-synthesis** | Compose narrative from multiple sources | all roles (core capability) |
| **monitoring** | Detect changes, track patterns, alert on thresholds | monitor role |
| **coordination** | Track freshness, steer contributors, trigger assembly | PM role |

### Export capabilities (mechanical, on-demand)

| Export | Method | Trigger |
|---|---|---|
| **PDF** | HTML → puppeteer/playwright | Delivery config, user download |
| **Image** | HTML → screenshot | Thumbnail generation, sharing |
| **XLSX** | Structured data → openpyxl | User download (data-mode outputs) |
| **Email** | HTML → email body | Delivery config (zero conversion) |

---

## Surfacing Model

### In-app (primary)

The platform renders output HTML directly. This is the primary consumption path:

- **Outputs tab**: Full HTML render (iframe or sanitized). Layout mode determines visual treatment.
- **Meeting room**: Output preview cards with expandable HTML view. Rich visual inline, not just text summaries.
- **Dashboard**: Output status cards with thumbnail previews (HTML → image thumbnail).

### Email delivery

HTML IS email. The `output.html` becomes the email body with zero conversion. Asset images referenced by URL. This is structurally simpler and higher fidelity than the current markdown→HTML conversion in delivery.py.

### External sharing

- **Public URL**: Renders the HTML (authenticated or public link).
- **Download buttons**: "Download as PDF" triggers export service. "Download data as XLSX" for data-mode outputs.
- **PPTX export**: Deferred — evaluate user demand before building. PDF covers most "share externally" needs.

---

## Workspace Conventions (ADR-119 extension)

### Output folder structure (updated)

```
/agents/{slug}/outputs/{date}/
├── output.md          # structured source (agent writes this)
├── output.html        # rendered HTML (compose engine generates this)
├── manifest.json      # metadata (extended with layout_mode, assets)
├── assets/            # visual assets produced during generation
│   ├── *.svg          # charts, diagrams
│   ├── *.png          # images, screenshots
│   └── *.json         # structured data (for XLSX export)
└── exports/           # on-demand exports (generated when requested)
    ├── *.pdf
    └── *.xlsx
```

### Manifest schema (extended)

```json
{
  "version": 1,
  "agent_id": "uuid",
  "run_number": 5,
  "layout_mode": "presentation",
  "files": [
    {"path": "output.md", "role": "source", "content_type": "text/markdown"},
    {"path": "output.html", "role": "rendered", "content_type": "text/html", "content_url": "..."},
    {"path": "assets/revenue-chart.svg", "role": "asset", "content_type": "image/svg+xml"}
  ],
  "assets": [
    {"path": "assets/revenue-chart.svg", "type": "chart", "caption": "Q2 Revenue Trend"}
  ],
  "delivery": {
    "channel": "email",
    "status": "pending"
  }
}
```

### Brand folder

```
/brand/                    # user-level brand assets
├── brand.css              # color palette, fonts, spacing
├── logo.png               # primary logo
├── logo-dark.png          # dark-mode variant (optional)
└── brand.json             # structured brand metadata
    {
      "name": "Acme Corp",
      "primary_color": "#1a56db",
      "font_family": "Inter, sans-serif"
    }
```

---

## Layout Modes

### Document (default)

Flowing text with headings, paragraphs, tables, charts, blockquotes. Optimized for reading. Print-friendly. This is what most digests, analyses, and reports use.

### Presentation

Each `## Heading` or `---` delimiter becomes a visual "slide." Large headings, full-width images, generous whitespace. Navigable sections (scroll or click-through). Background colors per section. This replaces PPTX for agent-produced presentations — the content is presentation-ready, the HTML renders it presentation-style, and PDF export preserves the visual treatment.

### Dashboard

Grid layout with metric cards, KPI panels, charts arranged in columns. Numbers prominent, trends visible. For recurring operational outputs (weekly metrics, status dashboards, monitoring summaries).

### Data

Structured tables as the primary element. Sort/filter affordances (client-side JS in in-app render, static in email). Row highlighting, conditional formatting. For data-heavy outputs where the table IS the deliverable. XLSX export available for this mode.

---

## Relationship to Other Architecture

| Component | Relationship |
|---|---|
| **Workspace (ADR-106, 119)** | Output folders gain `assets/` and `output.html`. Manifest extended. |
| **Skills (ADR-118)** | Skills reframed: asset renderers (chart, mermaid, image) survive. Format builders (pdf, pptx, xlsx, html) dissolve into compose + export. |
| **Assembly (ADR-120, 121)** | PM composition produces markdown sections from contributors. Render engine composes HTML. PM specifies layout mode. |
| **Coherence (ADR-128)** | Self-assessments stripped from output.md before HTML rendering (unchanged). Cognitive files are not output. |
| **Delivery (ADR-118 D.3)** | `deliver_from_output_folder()` sends `output.html` as email body. Attachments become export downloads, not primary output. |
| **Meeting Room (ADR-124)** | Output previews rendered as rich HTML cards in the chat stream. |
