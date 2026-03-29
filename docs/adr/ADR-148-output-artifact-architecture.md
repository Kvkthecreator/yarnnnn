# ADR-148: Output Artifact Architecture — Pieces, Composition, Delivery

> **Status**: Proposed — Phase 2 target (not immediate implementation)
> **Date**: 2026-03-29
> **Authors**: KVK, Claude
> **Extends**: ADR-130 (HTML-Native Output Substrate), ADR-145 (Task Type Registry)
> **Prerequisite**: Single-agent quality ceiling validated first (see `docs/analysis/output-quality-first-principles-2026-03-29.md`)
> **Rationale**: Artifact architecture becomes structurally necessary when accumulated agent memory and context window economics force sub-agent delegation (Month 3+). Premature implementation adds coordination cost without proportional quality gain. Phase 0 (single-agent, higher ambition) must validate the quality ceiling first.

---

## Context

Multi-step task processes (ADR-145) produce output that is indistinguishable from single-agent output. A 2-step competitive intelligence brief (research agent investigates, content agent composes) produces 300-700 words of markdown — the same artifact a single agent produces in one shot.

The root cause: **each process step produces a complete `output.md`**, and the compose step rewrites the research step's output rather than contributing additional artifacts. There is no concept of "pieces that assemble into a whole."

The architecture promises layout modes (document, presentation, dashboard) that imply professional-grade deliverables — multi-page reports with charts, slide decks with visuals, data dashboards with KPI cards. But the pipeline produces a few hundred words of markdown regardless of layout mode.

E2E test results (2026-03-29):
- competitive-intel-brief: step 1 = 674 words (research), step 2 = 23 words (compose failed — tool budget consumed by chart attempts)
- stakeholder-update: step 1 = 540 words, step 2 = 683 words (passed, but still plain markdown)

---

## Decision

### Four Domains

**Artifacts** — discrete units of generated content. Each has a type, was produced by a specific agent in a specific process step, and exists independently. Artifacts are ingredients, not the output.

**Output** — the composed deliverable. A single HTML artifact assembled from the process step artifacts according to the layout mode. What the user receives and reads. The output is always HTML — PDF/XLSX/PPTX are mechanical exports derived from it.

**Delivery** — transport. Takes the output and moves it to an external destination. A side effect, not a transformation. Can happen 0 times (app-only), 1 time (email), or N times (email + Slack). Delivery is logged on the output, not stored as a separate entity.

**Surfacing** — what the app shows. The task page always renders the composed output. Independent of delivery — the app shows all outputs whether or not they were delivered anywhere.

### Artifact Type System

Each process step produces one or more typed artifacts:

| Type | What | Format | Producer |
|------|------|--------|----------|
| `text` | Prose analysis, section content, narrative | Markdown (.md) | Any agent |
| `data` | Structured metrics, comparison tables, signal lists | JSON (.json) or markdown table | Research, Marketing |
| `chart` | Data visualization (bar, line, pie, scatter) | SVG/PNG via render service | Agents with chart capability |
| `diagram` | Structural/relational visualization | SVG via mermaid render | Agents with mermaid capability |
| `image` | Generated or sourced visual | PNG/JPG via render service | Agents with image capability |
| `table` | Structured comparison data | Markdown table (composed to rich HTML table) | Any agent |

Artifacts are stored in the step output folder:

```
/tasks/{slug}/outputs/{date}/
  step-1/
    analysis.md          (type: text)
    competitor_matrix.md  (type: table)
    funding_data.json     (type: data)
  step-2/
    executive_summary.md  (type: text)
    implications.md       (type: text)
    market_share.svg      (type: chart)
    positioning.svg       (type: diagram)
  manifest.json           (artifact inventory for composition)
  output.html             (composed final output)
  output.md               (text-only fallback)
```

### Process Steps Produce Artifacts, Not Outputs

The key change: a process step's instruction tells the agent **what artifacts to produce**, not "write a report." The research step produces research artifacts. The compose step produces presentation artifacts (summaries, visuals, interpretations). Neither step produces the final output.

Example — competitive-intel-brief:

```
Step 1 (research/investigate):
  Produce:
  - analysis.md: Competitive landscape analysis (1500+ words, per-competitor sections)
  - competitor_matrix.md: Feature comparison table (markdown table)
  - signal_log.md: Recent moves with dates and sources

Step 2 (content/compose):
  Produce:
  - executive_summary.md: 3-sentence insight summary
  - implications.md: Strategic implications for our positioning
  - market_share.svg: Chart from any quantified data in analysis
  - positioning.svg: Mermaid competitive positioning diagram
```

### Composition as a Mechanical Phase

Composition is NOT an agent step. It's a mechanical post-process phase that:
1. Reads all artifacts from all process steps
2. Assembles them per a layout template
3. Calls the compose service to produce styled HTML

Layout templates define artifact assembly order:

**Document template**:
```
[executive_summary] → [analysis with inline charts/diagrams] → [tables] → [implications] → [sources]
```

**Presentation template**:
```
[title slide from task title] → [executive_summary as slide] → [each major finding as slide with chart] → [positioning diagram slide] → [implications slide] → [next steps]
```

**Dashboard template**:
```
[KPI cards from data artifacts] → [trend charts] → [signal cards from signal_log] → [comparison tables] → [narrative sections]
```

The compose service already supports these layout modes (document, presentation, dashboard, data). The change is feeding it structured artifacts instead of a single markdown blob.

### Output/Delivery Separation

**Output** exists whether or not delivery happens:
- Stored in workspace: `/tasks/{slug}/outputs/{date}/output.html` + `output.md`
- Always browsable in the app
- Carries metadata: process steps completed, artifacts used, composition mode, generation tokens

**Delivery** is a transport action logged on the output:
- Email: sends output.html with optional PDF attachment
- Slack: posts condensed summary (executive_summary artifact) with link to full output
- Notion: writes structured page from artifact tree
- Delivery failures don't invalidate the output — the deliverable exists, transport just failed

---

## Consequences

### What changes
- Process step instructions rewritten around artifact production, not "write a report"
- Task type registry gains `artifact_spec` per step (what each step should produce)
- Pipeline saves artifacts with type metadata in the manifest
- Compose service accepts artifact inventory instead of single markdown blob
- Compose templates per layout_mode define assembly order
- Output and delivery are distinct pipeline phases

### What stays the same
- Agent type registry (capabilities unchanged)
- Task type registry structure (process steps, layout_mode)
- Compose service API (/compose endpoint)
- Delivery service (deliver_from_output_folder)
- Frontend task page (reads output.html via iframe)
- Workspace file storage model

### Risks
- **Complexity**: Artifact-aware composition is more complex than single-markdown composition
- **Agent compliance**: Agents may not reliably produce separate named artifacts (vs one blob)
- **Template maintenance**: Layout templates are a new artifact to maintain per layout mode

---

## Implementation Phases

### Phase 1: Artifact-aware manifest + composition template
- Extend manifest.json to inventory artifacts by type
- Compose service reads artifact list, assembles by template
- Process instructions updated for 1-2 task types as proof of concept
- Validate: competitive-intel-brief produces a 10-page-equivalent HTML report with charts

### Phase 2: All task types migrated to artifact model
- All 13 task type process instructions rewritten around artifact production
- Artifact validation (step produced expected artifact types)
- Dashboard and presentation templates validated

### Phase 3: Delivery separation
- Delivery reads composed output, adapts for channel
- Slack delivery uses executive_summary artifact for condensed post
- Notion delivery writes structured page from artifact tree
- Export (PDF/XLSX) derives from composed HTML

### Phase 4: Extended artifact types
- Video composition (artifact tree → Remotion template → MP4)
- Platform-native writes (Notion blocks, Slack canvas)
- Interactive dashboard (HTML with JS charts)

---

## Relationship to Existing ADRs

| ADR | Relationship |
|-----|-------------|
| ADR-130 (Output Substrate) | Extended — artifact types formalize what was implicit (chart/mermaid/image capabilities) |
| ADR-145 (Task Type Registry) | Extended — process steps gain artifact_spec |
| ADR-118 (Skills/Output Gateway) | Preserved — render service produces chart/diagram/image artifacts |
| ADR-141 (Execution Architecture) | Extended — composition becomes explicit pipeline phase after all steps |
| ADR-138 (Agents as Work Units) | Aligned — agents produce artifacts, tasks compose deliverables |
