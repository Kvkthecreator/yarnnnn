# Skills Reframe: Cognitive Capabilities, Not Format Builders

> **Status**: Design Decision
> **Date**: 2026-03-22
> **Implements**: ADR-130 (HTML-Native Output Substrate)
> **Supersedes**: ADR-118's implicit "one skill = one file format" model

---

## The Reframe

**Before**: A "skill" is a rendering function that takes a constrained JSON spec and produces a specific file format. The skill library is organized by output format (pdf, pptx, xlsx, chart, html, data, image, mermaid).

**After**: A "skill" is a cognitive capability that an agent can exercise. Skills are organized by *what they enable agents to do*, not by what file format they produce. Output format is a rendering/export concern, orthogonal to capabilities.

---

## Why This Matters

### The format-builder model creates false constraints

When skills are defined by output format, agents must decide *what format* before they decide *what to say*. A data analyst agent shouldn't think "I need to make an XLSX" — it should think "I need to analyze this data and present the findings." The format is a downstream concern.

The constrained JSON DSLs per format also limit expressiveness. The PPTX skill can only express `{title, content}` per slide — Claude Code writing python-pptx inline produces dramatically better output because it has the full expressiveness of code, not a limited schema.

### The capability model matches how agents think

Agents have roles (digest, research, monitor, analyze, synthesize). These map to *what they do*, not *what file they produce*. A researcher researches. A monitor monitors. Their output is knowledge — structured content with data, images, and narrative. How that knowledge is rendered (document? presentation? dashboard?) is a separate decision made by the layout mode, not the skill.

### Multi-agent composition requires format-agnostic assets

When multiple agents contribute to a project:
- Researcher contributes findings + competitor logos
- Data agent contributes analysis + charts
- Content agent contributes narrative + executive summary

These are **assets and content**, not files. The PM composes them into a unified output. The layout mode determines how it looks. The export format determines how it ships. None of these decisions should live in the individual agent's skill invocation.

---

## Skill Taxonomy (New)

### Tier 1: Asset Production Skills (render service)

These produce workspace files that embed into HTML output. They run on the render service.

| Skill | Description | Input | Output | Workspace path |
|---|---|---|---|---|
| `chart` | Data visualization | Data spec (labels, values, type) | SVG or PNG | `assets/chart-{name}.svg` |
| `diagram` | Structural diagrams | Mermaid spec | SVG | `assets/diagram-{name}.svg` |
| `image` | Image composition | Layer/text spec | PNG | `assets/{name}.png` |

**Invocation**: `RenderAsset(type="chart", input={...})` — produces a file in the output's `assets/` folder, returns the asset path for markdown embedding.

### Tier 2: Cognitive Skills (agent intelligence)

These are capabilities exercised during agent generation. They're not render service calls — they're primitives available to agents during their headless execution.

| Capability | Description | Primitives used |
|---|---|---|
| Research | Web search, source investigation, cross-referencing | WebSearch, QueryKnowledge, ReadWorkspace |
| Data analysis | Process structured data, compute metrics, identify trends | QueryKnowledge, structured reasoning |
| Monitoring | Track changes, detect patterns, evaluate thresholds | QueryKnowledge, workspace comparison |
| Synthesis | Compose narrative from multiple sources | ReadAgentContext, QueryKnowledge |
| Coordination | Track freshness, steer contributors, assemble | PM primitives (CheckFreshness, etc.) |

These are already implemented as role-specific primitives and prompts. The reframe makes explicit that these ARE the skills — not the format-builder functions.

### Tier 3: Export Skills (mechanical, on-demand)

These convert HTML output to legacy formats. They run on the render service but are triggered by delivery config or user action, not by agents during generation.

| Export | Method | Trigger | Notes |
|---|---|---|---|
| PDF | HTML → puppeteer | Delivery, download button | High fidelity from HTML |
| XLSX | Structured data → openpyxl | Download button (data-mode outputs) | Direct from data, not HTML |
| Image | HTML → screenshot | Thumbnail generation, sharing | For previews and cards |
| Email | HTML → email body | Delivery config | Zero conversion (HTML is email) |

---

## Migration from Current Skills

### Skills that become asset producers

| Current | New role | Change |
|---|---|---|
| `chart` skill | Asset producer | Minimal change — output goes to `assets/` folder instead of standalone file |
| `mermaid` skill | Asset producer (diagram) | Same — SVG to `assets/` |
| `image` skill | Asset producer | Same — PNG to `assets/` |

### Skills that dissolve

| Current | Disposition | Rationale |
|---|---|---|
| `pdf` skill | Becomes export from HTML | pandoc markdown→PDF replaced by puppeteer HTML→PDF (higher fidelity) |
| `pptx` skill | Deprecated, replaced by presentation layout mode | HTML with presentation layout > constrained PPTX. Export to PPTX deferred. |
| `html` skill | Becomes the primary render path | No longer a "skill" — HTML composition is the platform's core output pipeline |
| `xlsx` skill | Becomes data export | Direct from structured data, triggered on-demand |
| `data` skill | Merged into XLSX export path | CSV/JSON export from structured data tables |

### RuntimeDispatch evolution

**Current primitive**: `RuntimeDispatch(type, input, output_format)` — dispatches to a format-builder skill.

**New primitives**:
- `RenderAsset(type, input)` — produces a visual asset during generation. Returns asset path for markdown embedding. Types: `chart`, `diagram`, `image`.
- Export is not a primitive — it's triggered by delivery config or user action via the API.

---

## Impact on Agent Prompts

### Role prompts (agent_pipeline.py)

Current prompts tell agents about available output skills (RuntimeDispatch). New prompts:

1. Tell agents to produce **structured markdown** with semantic sections
2. Tell agents about **asset capabilities** (RenderAsset for charts/diagrams)
3. Tell agents to reference assets via markdown image syntax: `![Caption](assets/filename.svg)`
4. Tell agents about **layout hints** they can specify (document, presentation, dashboard, data)
5. Remove format-specific rendering instructions

### Assembly prompt

Current assembly prompt tells PM to use RuntimeDispatch for binary outputs. New prompt:

1. PM composes contributor markdown sections into unified output
2. PM selects layout mode based on project objective format preference
3. PM references contributor assets (already in workspace)
4. No RuntimeDispatch needed at assembly time — composition is structural

### SKILL.md injection

Current: All 8 SKILL.md files injected into agent context when RuntimeDispatch is available.

New: Only asset SKILL.md files injected (chart, diagram, image) — smaller context, more focused.

---

## Example: Before and After

### Before (format-builder model)

Agent generates a weekly report:
1. Agent writes text content
2. Agent calls `RuntimeDispatch(type="chart", input={data}, output_format="png")` → chart file in storage
3. Agent calls `RuntimeDispatch(type="presentation", input={title, slides: [{title, content}]}, output_format="pptx")` → PPTX file in storage
4. PPTX is the deliverable (with blank template styling)
5. Text content written to output.md
6. Delivery emails PPTX as attachment

### After (HTML-native model)

Agent generates a weekly report:
1. Agent writes structured markdown with sections, tables, key metrics
2. Agent calls `RenderAsset(type="chart", input={data})` → SVG in `assets/`
3. Agent references chart in markdown: `![Revenue Trend](assets/revenue-trend.svg)`
4. Output.md saved to workspace
5. Compose engine: output.md + assets + layout_mode="presentation" + brand CSS → output.html
6. In-app: renders HTML directly (presentation-style sections)
7. Email delivery: sends HTML as email body
8. User clicks "Download PDF": export service converts HTML → PDF

Result: visually rich presentation rendered natively, no PPTX limitations, same content viewable in-app and via email, PDF export for external sharing.

---

## Relationship to Claude Code Skills Ecosystem

ADR-118's thesis — ride the Claude Code skills ecosystem — was predicated on importing skills from the marketplace. The reframe preserves this for **asset capabilities** (charts, diagrams, images) where ecosystem tools are directly useful. It pivots away from it for **format builders** where the ecosystem's format-specific approach conflicts with our HTML-native thesis.

The ecosystem alignment:
- **Asset tools** (matplotlib, mermaid, pillow, d3) — fully aligned, import and use
- **Format converters** (python-pptx, openpyxl, pandoc) — still available as export utilities, but not as primary skills
- **Cognitive capabilities** (web search, data analysis, code execution) — aligned, these are agent primitives
- **Layout/rendering** (HTML/CSS frameworks, tailwind, chart.js) — new alignment opportunity for the composition engine

The bet: the ecosystem will increasingly produce tools for agent capabilities (what agents can do), not format conversion (what files they produce). We align with that trajectory.
