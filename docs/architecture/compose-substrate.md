# Architecture: Compose Substrate

> **Status:** Canonical (ADR-170). Proposed — not yet implemented.
> **Date:** 2026-04-10
> **Rule:** All output assembly, filesystem-to-output binding, and revision routing decisions should be consistent with this document.
> **Related:**
> - [ADR-170: Compose Substrate](../adr/ADR-170-compose-substrate.md) — governing ADR
> - [ADR-148: Output Architecture](../adr/ADR-148-output-artifact-architecture.md) — output pipeline (extended)
> - [ADR-151/152: Context Domains / Directory Registry](../adr/ADR-152-unified-directory-registry.md) — scope declarations that drive assembly
> - [ADR-157: Fetch-Asset Skill](../adr/ADR-157-fetch-asset-skill.md) — asset discovery (absorbed)
> - [ADR-166: Registry Coherence](../adr/ADR-166-registry-coherence-pass.md) — output_kind for revision routing
> - [output-surfaces.md](output-surfaces.md) — surface types, section kinds, export pipeline
> - [output-substrate.md](output-substrate.md) — capability + rendering architecture
> - [workspace-conventions.md](workspace-conventions.md) — filesystem path conventions

---

## What the Compose Substrate Is

The compose substrate is the **binding layer** between YARNNN's accumulating filesystem and rendered output. It converts accumulated workspace state — context domains, entity files, assets, prior outputs — into a structured deliverable expressed as an output folder.

It is a **function**, not a document. There is no separate `sys_compose.md` playbook file per task (ADR-170 RD-1). The structural knowledge lives where it already exists: the `page_structure` field in the task type registry (surface type + section kinds), agent methodology playbooks, and DELIVERABLE.md. The compose function reads these at execution time and produces the output folder.

Three concerns it addresses that no other layer owns:

1. **Structural awareness.** What sections should this output have, given its task type's `page_structure` and the current filesystem state? What surface type determines arrangement? What section kinds determine component rendering? What directories does each section draw from? What assets are available?
2. **Reference binding.** How do filesystem entities (competitor profiles, market data, signal timelines) and assets (charts, logos, diagrams) become concrete content placed in the output folder?
3. **Revision targeting.** When feedback arrives, what's the minimum scope of change? Is it a surface revision (recompose index.html), section revision (regenerate partial), asset revision (re-render), or root context revision (re-sync upstream)?

Without this layer, every output is generated from scratch with no structural memory of what was built before. With it, output is a *projection* of the filesystem through the lens of the task type's structure and the surface type's arrangement rules.

---

## Naming Convention: `sys_` Prefix

Compose substrate runtime artifacts in output folders use the `sys_` prefix to signal **system-managed infrastructure** — distinct from user-authored content (TASK.md, DELIVERABLE.md) and agent-authored content (output.md, memory/*.md):

| Prefix | Meaning | Examples |
|--------|---------|---------|
| (none) | User-authored or agent-authored | TASK.md, DELIVERABLE.md, output.md, memory/*.md |
| `_` | System hidden (existing convention) | `_tracker.md`, `_playbook.md` |
| `sys_` | System-managed compose infrastructure | `sys_manifest.json` |

The user can inspect `sys_` files but doesn't need to touch them in normal operation. They follow the same workspace_files storage as all other files.

> **Note:** `sys_` as a broader workspace-wide governance rule is a parked concern (ADR-170). Currently only `sys_manifest.json` uses this prefix.

---

## Structural Knowledge Sources

The compose function reads structural knowledge from existing sources at execution time. No separate playbook file is maintained per task (ADR-170 RD-1).

### What the compose function reads

| Source | What it provides | Who writes it |
|---|---|---|
| **Task type registry** (`task_types.py`) | `surface_type` (visual paradigm) + `page_structure` (section kinds, scopes, asset expectations) | System (curated registry) |
| **DELIVERABLE.md** (per task) | Quality contract: audience, quality criteria, format preferences, inferred user preferences | TP/user (ADR-149) |
| **Agent playbooks** (`_playbook-*.md`) | Craft methodology: how this agent type approaches content production | System + feedback distillation |
| **Filesystem state** | What entities exist, what assets are available, what's stale since last run | Accumulated by agents over time |
| **Prior output folder** (if exists) | What sections were produced, when, from what sources — enables revision-as-composition | Previous compose run |

### Surface types and section kinds

The `page_structure` field declares the output's structure using a vocabulary of **surface types** (visual paradigms) and **section kinds** (typed components). Full catalog in [output-surfaces.md](output-surfaces.md).

Surface types determine arrangement (how sections are laid out). Section kinds determine rendering (what each section looks like). The compose function resolves both.

### Relationship to DELIVERABLE.md

| Source | Purpose | What it controls |
|---|---|---|
| `DELIVERABLE.md` | Quality contract | What the output should *achieve* — audience, quality criteria, format preferences |
| `page_structure` (task type registry) | Structural template | What the output is *made of* — section kinds, scopes, asset expectations |

DELIVERABLE.md can override or extend the task type's `page_structure` when user preferences diverge from the default template. The compose function merges both: registry provides the structural template, DELIVERABLE.md provides the quality lens.

---

## Output as Folder

The output is not a single `output.html` file. It is a **folder** — an `index.html` entry point that includes section partials, references assets, and can in theory be served as a standalone page.

```
/tasks/{slug}/outputs/{date}/
├── index.html                 # entry point — assembles partials + assets
├── sections/                  # section partials (one per compose playbook section)
│   ├── executive-summary.html
│   ├── competitor-cards.html
│   └── signal-timeline.html
├── assets/                    # bound assets (root + derivative)
│   ├── tam-chart.svg          # derivative: rendered from data
│   ├── acme-favicon.png       # root: scraped, durable
│   └── market-pos.png         # derivative: rendered chart
├── data/                      # structured data backing derivative assets
│   └── metrics.json
├── output.md                  # source markdown (preserved for reference)
└── sys_manifest.json          # provenance, asset status, run metadata
```

The output folder IS the deliverable. The frontend renders from it. Email delivery packages it. Export flattens it.

---

## Two Kinds of Assets

| | Root Assets | Derivative Assets |
|---|---|---|
| **What** | Durable entities fetched/created independently | Generated from source data during render |
| **Examples** | Logos, screenshots, user-uploaded images | Charts, diagrams, mermaid SVGs |
| **Where they live (source)** | `/workspace/context/{domain}/assets/` | Generated fresh into output folder `assets/` |
| **Change frequency** | Rarely — fetched once, updated on re-scrape | Every render when source data changes |
| **Revision** | Re-fetch/re-scrape (external operation) | Re-render from updated source data (mechanical) |
| **Can refresh without prose regen?** | Yes | Yes |

### Static vs live derivative assets

The spectrum from static document to live dashboard:

- **Static:** derivative assets are rendered images (SVG/PNG), frozen at compose time. The output folder is a complete snapshot.
- **Live:** derivative assets are data specs (JSON) + render instructions. The frontend interprets them client-side. Like a BI dashboard — the output folder contains data + instructions, not finished images.

The compose playbook declares per-asset whether it's `static` (default, compose-time render) or `live` (view-time render). Phase 6 implementation.

---

## Three Operations

### 1. Scaffold

**When:** First run of a task (or task creation for pre-computation).
**Input:** Task type `page_structure` + `surface_type` from `task_types.py`.
**Output:** Internal structural plan (in-memory, not persisted as a file). Determines what sections to generate, what directory scopes to query, what assets to look for.

### 2. Assemble

**When:** Before and after generation in `execute_task()`.

**Pre-generation assembly:**
- Read task type's `page_structure` — resolve section kinds and scopes.
- Resolve `surface_type` — determines how section kinds will be arranged.
- Query filesystem for scoped directories — list entities, list assets.
- Detect new entities (not in previous output), updated entities (content changed since last run).
- Flag stale sections (source `updated_at` > section `produced_at` in `sys_manifest.json`).
- Build **generation brief**: "write these sections; these entities exist; these assets are available; these sections are stale." (ADR-170 RD-2: the generation brief is the compose function's highest-value output.)

**Post-generation assembly:**
- Parse LLM output → write section partials to `output/sections/`.
- Copy root assets from domain `assets/` folders → `output/assets/`.
- Trigger derivative asset rendering (data → charts, mermaid → SVGs) → `output/assets/`.
- Render each section partial with surface-type-appropriate HTML treatment per its section kind.
- Compose `index.html` from rendered partials + asset references, arranged per surface type.
- Write `sys_manifest.json` with provenance per section and asset status.

### 3. Revise

**When:** TP steers (`ManageTask(action="steer")`), user feedback arrives, or TP evaluates output.
**Input:** Revision signal + task type's `page_structure` + current output folder + `sys_manifest.json`.

Revision is composition with diff — the same function, richer input (ADR-170 RD-3). The compose function detects staleness by comparing `sys_manifest.json` provenance (which run produced each section, from what source files, when) against current filesystem state.

**Revision classification:**

| Type | Signal pattern | Action | LLM cost |
|------|---------------|--------|----------|
| **Surface** | "reorder sections", "change layout" | Recompose `index.html` — rearrange partials | Zero |
| **Section** | "competitive section is weak", feedback targets specific content | Regenerate affected partial(s) only | Sonnet (scoped) |
| **Asset** | "chart is outdated", "logo is wrong" | Re-render derivative or re-fetch root | Zero (mechanical) |
| **Root context** | "data is stale", "missing competitor" | Route upstream to domain re-sync → cascade to sections (ADR-170 RD-5: TP handles upstream orchestration) | Sonnet (upstream gather) |

---

## Layer Placement in Service Model

```
execute_task(slug)
  → Read TASK.md + DELIVERABLE.md + steering.md + feedback.md
  → Read task type's page_structure + surface_type from registry
  → SCAFFOLD (first run): resolve structural plan from page_structure
  → ASSEMBLE (pre-gen): query filesystem, discover assets, build generation brief
  → GENERATE: agent writes section prose guided by assembly brief
  → ASSEMBLE (post-gen): build output folder (section partials + assets + index.html)
  → RENDER: derivative assets (tables → charts, mermaid → SVGs)
  → COMPOSE: apply surface-type arrangement + section-kind rendering → final HTML
  → Save output folder to /tasks/{slug}/outputs/{date}/
  → Deliver (with delivery channel transform if needed)
```

**Housing:** `api/services/compose/` package within the API service.

```
api/services/compose/
├── __init__.py
├── scaffold.py      # structural plan from task type page_structure + surface_type
├── assembly.py      # filesystem query, asset discovery, generation brief, folder build
├── revision.py      # revision classification + routing (staleness detection via manifest)
├── surfaces.py      # surface type arrangement rules (section layout per paradigm)
├── sections.py      # section kind rendering (HTML templates per kind per surface type)
└── manifest.py      # sys_manifest.json schema, provenance, asset status
```

---

## Evaluation Is a Separate Concern

The compose substrate handles *structural binding* — what goes where, what references what. It does **not** handle *quality judgment*.

Quality evaluation remains in ADR-149:
- TP evaluates output against DELIVERABLE.md → produces steering signals.
- User provides feedback → routed to task feedback.md.
- Agent self-reflects → writes to memory/reflections.md.

The compose substrate *consumes* these signals as revision inputs. It does not *produce* quality judgments. This preserves the boundary: compose = deterministic Python, evaluation = TP intelligence (LLM).

Recursive improvement of the output structure itself (should sections change? is the surface type right?) is a developmental concern belonging to the agent's learning loop. A tenured agent accumulates preferences about what works — that feeds back into DELIVERABLE.md via TP inference or user editing, not via the compose substrate judging itself.

---

## The Human Analogy

A knowledge worker building an IR deck:

1. **Scaffolds** — sections: market size, competitive landscape, financials, team. Each section maps to a folder in their files.
2. **Gathers** — market size section needs the TAM chart. Competitive landscape needs competitor logos and the positioning matrix.
3. **Binds** — places references into structure. Chart here, logo grid here, narrative wraps the data.
4. **Writes** — fills narrative for each section, knowing what data and assets are already positioned.
5. **Revises** — boss says "competitive section needs depth." They go to their competitor folder, research more, update that section. If the chart is stale, they refresh the chart from updated data — no rewrite needed. If the logo is wrong, they swap just the logo.

Steps 1–3 and 5 are the compose substrate. Step 4 is the LLM. The render service formats the final product. The boss's evaluation is the separate evaluation concern — it identifies *what* needs revision; the compose substrate determines *how*.

---

## Relationship to Other Architecture

| Component | Relationship |
|---|---|
| **Output Pipeline (ADR-148)** | Extended — SCAFFOLD + ASSEMBLE steps added; output evolves from single file to folder |
| **Output Surfaces (ADR-170 RD-6/7/8/9)** | Defines the vocabulary — surface types + section kinds + export pipeline. Compose function operates on this vocabulary. See [output-surfaces.md](output-surfaces.md). |
| **Task Lifecycle (ADR-149)** | Extended — DELIVERABLE.md (quality) + task type `page_structure` (structure) as complementary sources. Evaluation remains ADR-149, compose consumes its signals. |
| **Context Domains (ADR-151/152)** | Extended — `context_reads`/`context_writes` become compose substrate's scope index |
| **Fetch-Asset Skill (ADR-157)** | Absorbed — asset discovery is first-class compose operation; root/derivative distinction formalized |
| **Registry Coherence (ADR-166)** | Extended — `output_kind` drives revision routing semantics; `surface_type` replaces `layout_mode` on task types |
| **Workspace Conventions** | Extended — `sys_` naming convention; output-as-folder structure |
| **Service Model** | Extended — compose substrate is a named domain within Layer 2 |
| **FOUNDATIONS Axiom 2** | Extended — composition is the corollary that makes accumulation manifest |
