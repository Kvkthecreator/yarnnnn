# ADR-148: Output Architecture — Assets, Composition, Repurpose

> **Status**: Implemented (Phases 1-3), Phase 4 proposed
> **Date**: 2026-03-29 (v4 — 2026-03-30)
> **Authors**: KVK, Claude
> **Extends**: ADR-130 (HTML-Native Output Substrate), ADR-145 (Task Type Registry)
> **Supersedes**: RuntimeDispatch-during-generation, dual rendering paths, `generate_email_html` fallback
> **Analysis**: `docs/analysis/output-quality-first-principles-2026-03-29.md`

---

## Context

Output quality testing revealed three architectural gaps:
1. Visual assets (charts, diagrams) never made it into outputs — agents competed for tool rounds between research and asset generation
2. Two redundant rendering paths (compose service vs MarkdownRenderer fallback) produced inconsistent results
3. No model for adapting outputs to different formats or platforms (LinkedIn, PDF, slides) — this requires editorial judgment for some targets and mechanical conversion for others

---

## Decision

### Domain Definitions

**Asset** — a single produced content element within an output. Types: text (markdown), chart (SVG/PNG), diagram (mermaid → SVG), table (markdown), image (PNG/JPG), video (MP4). Assets are atomic.

**Output** — the primary composed deliverable from a task run. One output per run. Always HTML (composed from markdown + rendered assets). Stored at `/tasks/{slug}/outputs/{date}/output.html`. This is what the user sees in the app and receives via email.

**Repurpose** — any adaptation of the output for a different format, channel, or audience. Two execution paths:
- **Mechanical** (backend): format conversion that preserves content structure. PDF, XLSX, markdown download.
- **Editorial** (agent): content adaptation that requires judgment. LinkedIn post, slide deck, executive summary, restructured PDF.

**Transport** — moving a finished artifact (output or repurpose) to an external destination. Email send, Slack post, LinkedIn publish. Mechanical. No content change.

### The Complete Chain

```
Task execution
  → GENERATE: Agent writes prose + inline data tables + mermaid blocks
  → RENDER: Extract tables→charts, mermaid→SVGs (mechanical, zero LLM)
  → COMPOSE: Markdown + rendered assets → styled HTML (composition mode)
  → OUTPUT: output.html stored in task workspace

Output actions:
  → VIEW: App shows output.html in iframe
  → TRANSPORT: Email sends output.html, Slack posts summary + link
  → REPURPOSE (mechanical): PDF, XLSX, DOCX — backend converts
  → REPURPOSE (editorial): LinkedIn post, slide deck — agent adapts
```

### Production Phases (Implemented)

**Phase 1: Generate** — LLM produces prose with inline data. No RuntimeDispatch during generation. All tool rounds for research + writing. SKILL.md removed from system prompt.

**Phase 2: Render** — `render_inline_assets()` extracts:
- Markdown tables with numeric data → chart render (bar/line/pie inferred)
- Mermaid code blocks → SVG diagram render
Zero LLM cost. Mechanical extraction.

**Phase 3: Compose** — Always runs (no capability gate). Markdown + rendered asset URLs → styled HTML per composition mode (document/presentation/dashboard/data). Handles all asset types:
- Mermaid → interactive SVG via mermaid.js
- Images → figure + figcaption
- Video → `<video>` element
- Tables → styled HTML (dashboard mode → KPI cards)
- Dark mode via CSS variables + `prefers-color-scheme`

### Singular Rendering Path (Implemented)

One path. No fallbacks. No branching by agent type.

- **App display**: Always `output.html` via iframe (`allow-same-origin allow-scripts`)
- **Email delivery**: Always composed HTML
- **Markdown fallback**: Loading state only, not a rendering path

### Repurpose Model (Proposed — Phase 4)

**User-facing concept**: "Repurpose" — one button, multiple options. User doesn't see mechanical vs editorial distinction.

**Mechanical repurposes** (backend, no agent):
| Target | Input | Method |
|--------|-------|--------|
| PDF (same layout) | output.html | pandoc HTML→PDF |
| XLSX | output.md tables | openpyxl extraction |
| DOCX | output.html | pandoc HTML→DOCX |
| Markdown download | output.md | Direct file |

**Editorial repurposes** (agent, requires LLM):
| Target | Input | What Agent Does |
|--------|-------|----------------|
| LinkedIn post | output as context | Write 150-word hook, platform-native format |
| Slide deck (PPTX) | output as context | Restructure for 1-idea-per-slide format |
| Executive summary | output as context | Condense to 3-paragraph summary |
| Platform article (Medium) | output as context | Adapt tone for public audience |

**Storage**: Repurposed outputs live under the parent task output:
```
/tasks/{slug}/outputs/{date}/
  output.md           (primary source)
  output.html         (composed primary)
  repurpose/
    linkedin.md       (agent-written)
    linkedin.html     (composed)
    slides.md         (agent-written)
    slides.html       (composed, presentation mode)
    summary.md        (agent-written)
```

**Routing logic**: The system determines mechanical vs editorial based on the target:
```python
MECHANICAL_REPURPOSE = {"pdf", "xlsx", "docx", "markdown"}
EDITORIAL_REPURPOSE = {"linkedin", "medium", "slides", "summary", "twitter"}
```

Mechanical → call render service directly, return file URL.
Editorial → call agent with output as context + repurpose instruction → generate → render → compose → store.

### Upstream Dependencies (Phase 4)

This model impacts multiple layers. All must be updated coherently:

**1. Agent Capabilities**
- No new capability needed. Every agent that can produce an output can repurpose one — it's the same cognitive skill (write content given context). The repurpose instruction tells the agent what format/audience to target.
- `write_slack` and `write_notion` remain as transport capabilities (posting to platforms), not editorial capabilities.

**2. Task Process**
- Repurpose is NOT a process step. It's an on-demand action on an existing output.
- Task process defines how the primary output is produced. Repurpose happens after.
- No changes to task type registry or process definitions.

**3. TP Orchestration**
- TP needs to handle: "publish this to LinkedIn" → identify the task + output → determine mechanical vs editorial → route accordingly.
- New TP capability: `RepurposeOutput` — takes task_slug, output_date, target_format. TP resolves routing.
- This is a new primitive, not a process step.

**4. Output Storage**
- Repurposed outputs stored under `repurpose/` subfolder of the parent output.
- Manifest updated to track repurpose history.

**5. Delivery/Transport**
- After editorial repurpose produces the adapted content, transport sends it to the platform.
- LinkedIn/Medium transport requires OAuth (same pattern as Slack/Notion).
- Transport is a separate step from repurpose — repurpose produces content, transport sends it.

**6. Frontend**
- "Repurpose" button replaces current "Export" buttons.
- Shows available targets (PDF, XLSX, LinkedIn, Slides, etc.).
- Mechanical targets return immediately (file URL). Editorial targets show progress indicator.

---

## Implementation Status

### Phase 1: Render phase + agent simplification ✓
- `render_inline_assets()` — tables→charts, mermaid→SVGs
- RuntimeDispatch removed from headless
- SKILL.md removed from system prompt

### Phase 2: Compose-always + singular rendering ✓
- Compose runs for every output regardless of agent type
- Dark mode + mermaid.js + full asset type handling
- MarkdownRenderer → loading state only

### Phase 3: Mechanical export ✓
- PDF (HTML→pandoc), XLSX (table extraction), DOCX
- Export API endpoint: `GET /tasks/{slug}/export?format=pdf|xlsx|docx`
- Export buttons on task page

### Phase 4: Repurpose model (proposed)
- Unify export + editorial adaptation under "Repurpose"
- `RepurposeOutput` primitive for TP
- Editorial repurpose via agent (LinkedIn, slides, summary)
- Platform transport (LinkedIn API, Medium API) via OAuth
- Frontend: single "Repurpose" button with target options

---

## Relationship to Existing ADRs

| ADR | Relationship |
|-----|-------------|
| ADR-130 (Output Substrate) | Extended — singular rendering, full asset types, repurpose model |
| ADR-145 (Task Type Registry) | Unchanged — repurpose is on-demand, not a process step |
| ADR-118 (Skills/Output Gateway) | Evolved — render service for charts/diagrams (post-gen), PDF/XLSX (export) |
| ADR-141 (Execution Architecture) | Extended — render phase between generate and compose |
| ADR-138 (Agents as Work Units) | Aligned — agents produce, platform transports. Editorial repurpose is production. |
| FOUNDATIONS Derived Principle 9 | Aligned — agents produce structured content, platform renders and transports. Repurpose (editorial) is content production. Repurpose (mechanical) is platform rendering. |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-03-29 | v1 — Artifact types, composition templates |
| 2026-03-29 | v2 — Output types as acceptance criteria, production phases |
| 2026-03-29 | v3 — Simplified: assets + render phase + domain separation |
| 2026-03-30 | v4 — Complete: repurpose model (mechanical + editorial), upstream dependency map, singular rendering path, full asset type handling. Phases 1-3 implemented, Phase 4 proposed. |
