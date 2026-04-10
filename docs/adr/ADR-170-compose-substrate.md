# ADR-170: Compose Substrate — Filesystem-to-Output Assembly Layer

**Date:** 2026-04-10
**Status:** In Progress (Phase 4)
**Authors:** KVK, Claude
**Supersedes:** None (new architectural domain)
**Extends:** ADR-148 (Output Architecture), ADR-151/152 (Context Domains / Directory Registry), ADR-157 (Fetch-Asset Skill), ADR-166 (Registry Coherence)
**Evolves:** ADR-130 (HTML-Native Output Substrate — Phase 2 compose integration)

---

## Context

YARNNN's output pipeline has three well-defined layers: **generation** (LLM produces prose + inline data), **rendering** (mechanical transformation — tables→charts, mermaid→SVGs), and **display** (frontend shows `output.html` in iframe). What's missing is the layer between "the filesystem has accumulated context and assets" and "a structured output exists that references that context and those assets."

Today, that binding happens implicitly: the LLM is instructed to write prose, the prose happens to reference things in the filesystem, `render_inline_assets()` extracts chartable data, and `compose_html()` wraps it in a layout. There is no explicit representation of *what the output should structurally contain given the current filesystem state*. This means:

- **Revision is full regeneration.** When feedback points at one section, the entire output is regenerated because there's no structural map from sections to their filesystem sources.
- **Assets are invisible until composed.** An agent may have fetched a competitor logo (ADR-157) or generated a chart in a prior run, but the compose step doesn't know these exist unless the LLM happens to reference them in prose. Assets are first-class in the filesystem but second-class in composition.
- **Task types differ only cosmetically.** `layout_mode` picks a CSS wrapper (document, dashboard, digest, email). The structural difference between a competitive tracker and a market report — what directories they draw from, what entity structures they expect, how assets bind — is expressed only in prompts, not in a queryable structure.
- **Cross-run continuity is accidental.** Each run produces a fresh `output.md` with no structural awareness of what the previous run produced. A tenured agent's output isn't structurally richer than a first-run agent's — it's just longer prose because the prompt is longer.

The compose substrate is the architectural domain that addresses all four gaps.

---

## Decision

### The Compose Substrate is a distinct architectural domain

The compose substrate is the **binding layer** between the accumulating filesystem and rendered output. It sits between generation (LLM) and rendering (mechanical), and its job is to answer: *given this task's compose playbook and the current filesystem state, what is the structure of the deliverable, what goes where, and what references need resolving?*

It is housed **within the API service** (`api/services/compose/`), not as a separate render service. The render service (`yarnnn-render`) remains correctly separated for mechanical transformation (pandoc, matplotlib, mermaid-cli). The compose substrate needs deep awareness of the filesystem, task type registry, directory registry, and scope declarations — concerns that belong in the API.

### Naming convention: `sys_` prefix

Compose substrate runtime artifacts in output folders use the `sys_` prefix to signal **system-managed infrastructure** — files the pipeline reads and writes, distinct from user-authored content (TASK.md, DELIVERABLE.md) and agent-authored content (output.md, memory/*.md). The user can inspect `sys_` files but doesn't need to touch them in normal operation.

> **RD-1 revision:** The originally proposed `sys_compose.md` per-task playbook file was dissolved during stress testing. See RD-1 below. The compose substrate is a function, not a document — structural knowledge lives in the task type registry's `page_structure` field, agent playbooks, and DELIVERABLE.md. The only `sys_`-prefixed file that persists is `sys_manifest.json` in output folders.

```
/tasks/{slug}/
├── TASK.md                    # user-authored: operational charter
├── DELIVERABLE.md             # user-authored: quality contract (ADR-149)
├── memory/
│   ├── run_log.md
│   ├── feedback.md
│   └── steering.md
└── outputs/{date}/            # output folder IS the deliverable ← CHANGED
    ├── index.html             # entry point (the "page") — surface-type-aware
    ├── sections/              # section partials (one per section kind)
    │   ├── executive-summary.html
    │   ├── competitor-cards.html
    │   └── signal-timeline.html
    ├── assets/                # bound assets (root + derivative)
    │   ├── tam-chart.svg      # derivative: generated from data
    │   ├── acme-favicon.png   # root: scraped, durable
    │   └── market-pos.png     # derivative: rendered chart
    ├── data/                  # structured data backing derivative assets
    │   └── metrics.json
    ├── output.md              # source markdown (preserved)
    └── sys_manifest.json      # system: provenance + asset status
```

### Core concept: Compose as Function

> **RD-1 revision:** The originally proposed `sys_compose.md` playbook was dissolved during stress testing. This section describes the final model.

The compose substrate is a **capability layer** — a function that reads existing structural knowledge at execution time and produces the output folder. There is no separate compose playbook file per task. The structural knowledge lives where it already exists:

- **Task type registry** — `surface_type` (visual paradigm: report, deck, dashboard, digest, workbook, preview, video) + `page_structure` (section kinds with scopes and asset expectations). See [output-surfaces.md](docs/architecture/output-surfaces.md).
- **DELIVERABLE.md** — quality contract (audience, criteria, format preferences). Can override or extend the task type's structural template.
- **Agent playbooks** — craft methodology for content production.
- **Filesystem state** — what entities, assets, and prior outputs actually exist.

The compose function reads these sources, resolves the section kinds against the surface type's arrangement rules, and produces the generation brief + output folder.

#### Structural template example

```python
# In task_types.py — the structural knowledge lives here, not in a per-task file
"competitive-brief": {
    "surface_type": "report",
    "page_structure": [
        {"kind": "narrative", "title": "Executive Summary",
         "reads_from": ["competitors/_synthesis.md"]},
        {"kind": "entity-grid", "title": "Competitor Profiles",
         "entity_pattern": "competitors/*/",
         "assets": [{"type": "root", "pattern": "competitors/assets/*-favicon.png"}]},
        {"kind": "timeline", "title": "Signal Timeline",
         "reads_from": ["signals/_tracker.md"]},
        {"kind": "trend-chart", "title": "Market Position",
         "reads_from": ["competitors/*/analysis.md"],
         "assets": [{"type": "derivative", "render": "chart"}]},
    ],
}
```

### Output as folder — the deliverable is a directory

The output is not a single `output.html` file. It is a **folder** — an `index.html` entry point that includes section partials, references assets, and can in theory be served as a standalone page. The output folder IS the deliverable.

This reframes what revision means:

- **Section-scoped revision:** "competitive section is weak" → regenerate `sections/competitor-cards.html` only. The `index.html` already includes it by reference.
- **Asset revision:** "chart is stale" → re-render `assets/market-pos.png` from updated source data. `index.html` already references it by path. No regeneration of any section's prose.
- **Presentation revision:** feedback targets layout, ordering, or styling — not content or data. Change the `index.html` assembly or section ordering without regenerating any section content.
- **Root context revision:** feedback traces back to upstream data (entity file is incomplete, domain synthesis is stale). Route upstream: re-run the `update-context` step to refresh the domain, then re-derive affected sections.

The folder structure makes these revision types structurally distinct rather than all collapsing into "regenerate everything."

### Two kinds of assets: root and derivative

**Root assets** — durable entities that change rarely and are fetched or created independently of any single output. Logos, screenshots, user-uploaded images, scraped visuals. They live in domain `assets/` folders (`/workspace/context/{domain}/assets/`) and are *copied or linked into* output folders at compose time.

**Derivative assets** — generated from source data during the render step. Charts from tabular data, diagrams from mermaid specs, visualizations from metrics. They are produced fresh (or from cache when source hasn't changed) and written to the output folder's `assets/` directory.

The distinction matters for revision:
- Root asset stale → fetch/scrape again (external operation, may require render service).
- Derivative asset stale → re-render from updated source data (mechanical, zero LLM).
- Both can be refreshed without regenerating prose sections.

The distinction also matters for the spectrum from **static document** to **live dashboard**:
- Static: derivative assets are rendered images, frozen at compose time.
- Live: derivative assets are data specs (JSON) + render instructions that the frontend interprets client-side. The output folder contains data + instructions, not finished images. Like a BI dashboard.
- The folder structure accommodates both — the compose playbook declares whether each derivative asset is `static` (render at compose time) or `live` (render at view time).

### Three operations on the compose substrate

**1. Scaffold** — Given a task type definition (from `task_types.py`), produce the initial compose playbook (`sys_compose.md`). This determines what sections the output will have, what directory scopes each section reads from, and what asset types are expected. Scaffolding happens at task creation and is stored in the task workspace.

**2. Assemble** — Given a compose playbook + current filesystem state, resolve all references. Discover assets in scoped directories. Detect new entities since last assembly. Identify stale sections (source data updated since section was last generated). This runs before generation to tell the LLM *what* to write about and *what assets are available*, and after generation to bind the LLM's output into the folder structure (section partials, asset references, `index.html` assembly).

**3. Revise** — Given a compose playbook + revision signal (user feedback, TP steering, filesystem diff), determine the minimum regeneration scope and route it:

- **Presentation revision** → recompose `index.html` (no regeneration, no re-render).
- **Section revision** → regenerate affected section partial(s) only, rebind into `index.html`.
- **Asset revision** → re-render derivative asset from updated data, or re-fetch root asset. No section regeneration unless prose references changed data.
- **Root context revision** → route upstream to domain re-sync, then cascade: updated domain files → stale sections flagged → section regeneration → asset re-render if data changed.

Revision routing by `output_kind` (ADR-166):

| output_kind | Revision means | Scope |
|-------------|---------------|-------|
| `accumulates_context` | Re-sync source data → update entity files → re-derive affected context | Source → filesystem → section |
| `produces_deliverable` | Section-scoped regeneration, presentation recomposition, or asset refresh | Section / asset / presentation |
| `external_action` | Follow-up action (re-send, amend) | Action-scoped |
| `system_maintenance` | N/A — deterministic executors | None |

### Evaluation is a separate concern

The compose substrate handles *structural binding* — what goes where, what references what. It does **not** handle *quality judgment* — whether the output is good, whether sections are strong enough, whether the overall deliverable meets the DELIVERABLE.md quality contract.

Quality evaluation remains in the existing ADR-149 feedback/evaluation/reflection framework:
- **TP evaluates** output quality against DELIVERABLE.md → produces steering.md directives.
- **User provides feedback** → routed to task feedback.md.
- **Agent self-reflects** → writes to memory/reflections.md.

The compose substrate *consumes* evaluation signals as revision inputs (steering notes identify which sections need work), but it does not *produce* quality judgments. This separation preserves the clean boundary: compose substrate = deterministic Python, evaluation = TP intelligence (LLM).

Recursive improvement of the compose substrate itself (are the section structures right? should the playbook evolve?) is a developmental concern that belongs to the agent's learning loop, not to the compose layer. A tenured agent may accumulate preferences about what sections work well — that feeds back into the compose playbook via TP inference, not via the compose substrate judging itself.

### The filesystem is the data model

The compose substrate does not introduce a new storage layer. The filesystem (`workspace_files`) is the data model. Assets live in domain `assets/` folders (ADR-157). Entity files live in domain entity subfolders (ADR-151). Task outputs live in `/tasks/{slug}/outputs/`. The compose substrate *queries* this structure — it does not duplicate it.

Directory scope declarations on task types (`context_reads`, `context_writes` from ADR-151) are the compose substrate's primary index. A task that reads `[competitors, signals]` will have its compose playbook scoped to those directories. A task that reads `[competitors, market, relationships, signals]` gets a wider scope and more sections. Scope determines composition breadth.

### The human analogy

A knowledge worker building an IR deck doesn't write it top to bottom in one pass. They:

1. **Scaffold** — decide the sections: market size, competitive landscape, financials, team. Each section has an implicit scope in their files.
2. **Gather** — go to their folders. Market size section needs the TAM chart from last month's analysis. Competitive landscape needs competitor logos and the positioning matrix. Financials needs the model output.
3. **Bind** — place references into the structure. The chart goes here. The logo grid goes here. The narrative wraps around the data.
4. **Write** — fill in the narrative for each section, knowing what data and assets are already positioned.
5. **Revise** — boss says "competitive section needs more depth." They don't rewrite the deck. They go to their competitor folder, see what's shallow, research more, update that section's files, and rebind. If the logo is wrong, they just swap the logo — no rewrite. If the chart is stale, they refresh the chart from updated data — no rewrite.

Steps 1–3 and 5 are the compose substrate. Step 4 is the LLM. The render service formats the final product. The boss's evaluation (step 5 trigger) is the separate evaluation concern — it identifies *what* needs revision, but the compose substrate determines *how* to route that revision.

---

## Architecture

### Layer placement

```
┌──────────────────────────────────────────────────────────┐
│  Layer 3 — TP Intelligence (user-present, orchestration)  │
│  Evaluates output → produces steering/feedback signals    │
│  (Evaluation is TP's concern, NOT compose substrate's)    │
└──────────────────┬───────────────────────────────────────┘
                   │ steering/feedback signals
┌──────────────────▼───────────────────────────────────────┐
│  Layer 2 — Task Execution (Sonnet per task)               │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  SCAFFOLD (task creation)                            │  │
│  │  sys_compose.md from task type page_structure        │  │
│  └──────────────────┬──────────────────────────────────┘  │
│                     │                                     │
│  ┌──────────────────▼──────────────────────────────────┐  │
│  │  ASSEMBLE (pre-generation)                           │  │
│  │  Read sys_compose.md → query filesystem →            │  │
│  │  asset discovery → staleness detection →             │  │
│  │  generation brief for LLM                            │  │
│  └──────────────────┬──────────────────────────────────┘  │
│                     │                                     │
│  ┌──────────────────▼──────────────────────────────────┐  │
│  │  GENERATE (LLM — Sonnet)                             │  │
│  │  Agent writes section prose guided by assembly brief │  │
│  └──────────────────┬──────────────────────────────────┘  │
│                     │                                     │
│  ┌──────────────────▼──────────────────────────────────┐  │
│  │  ASSEMBLE (post-generation)                          │  │
│  │  Bind LLM output → section partials in output folder │  │
│  │  Resolve asset refs → copy/render into output/assets │  │
│  │  Compose index.html from partials + assets           │  │
│  │  Write sys_manifest.json with provenance             │  │
│  └──────────────────┬──────────────────────────────────┘  │
│                     │                                     │
│  ┌──────────────────▼──────────────────────────────────┐  │
│  │  RENDER (mechanical — yarnnn-render)                  │  │
│  │  Derivative assets: tables → charts, mermaid → SVGs  │  │
│  └──────────────────┬──────────────────────────────────┘  │
│                     │                                     │
│  ┌──────────────────▼──────────────────────────────────┐  │
│  │  COMPOSE (mechanical — yarnnn-render)                 │  │
│  │  Final HTML styling + layout application              │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  REVISE (on feedback/steering)                       │  │
│  │  Classify revision type:                             │  │
│  │    presentation → recompose index.html               │  │
│  │    section → regenerate partial(s)                   │  │
│  │    asset → re-render/re-fetch                        │  │
│  │    root context → route upstream to domain re-sync   │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                           │
└───────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────┐
│  Layer 1 — Mechanical Scheduling (zero LLM)                │
│  SQL: tasks WHERE next_run_at <= NOW() → execute_task()    │
└───────────────────────────────────────────────────────────┘
```

### File structure (API service)

```
api/services/compose/
├── __init__.py
├── scaffold.py      # sys_compose.md generation from task type page_structure
├── assembly.py      # filesystem query, asset discovery, ref resolution, folder build
├── revision.py      # revision classification + routing (presentation/section/asset/root)
├── playbook.py      # compose playbook parsing + serialization (markdown ↔ structured)
└── manifest.py      # sys_manifest.json schema, provenance tracking, asset status
```

### Integration with task type registry

Task types in `task_types.py` gain a `page_structure` field consumed by the scaffold operation:

```python
"competitive-brief": {
    "output_kind": "produces_deliverable",
    "layout_mode": "document",
    "context_reads": ["competitors", "signals"],
    "context_writes": ["competitors"],
    "page_structure": [
        {"kind": "narrative", "title": "Executive Summary",
         "reads_from": ["competitors/_synthesis.md"]},
        {"kind": "entity_cards", "title": "Competitor Profiles",
         "entity_pattern": "competitors/*/",
         "assets": [{"type": "root", "pattern": "competitors/assets/*-favicon.png"}]},
        {"kind": "narrative", "title": "Signal Analysis",
         "reads_from": ["signals/_tracker.md"]},
        {"kind": "chart", "title": "Market Position",
         "reads_from": ["competitors/*/analysis.md"],
         "assets": [{"type": "derivative", "render": "chart"}]},
    ],
    # ... existing fields preserved
}
```

Tasks with `output_kind: accumulates_context` have simple page structures (single narrative wrapping domain synthesis). Tasks with `output_kind: produces_deliverable` have richer structures with entity cards, charts, and cross-domain narratives. `external_action` and `system_maintenance` tasks don't use compose playbooks.

---

## Impact Radius

### Documents that need downstream updates

| Document | Update needed | Priority |
|----------|--------------|----------|
| `docs/architecture/SERVICE-MODEL.md` | Add compose substrate as named domain in Execution Flow; update pipeline to show SCAFFOLD + ASSEMBLE steps | High — canonical (done: Phase 1) |
| `docs/architecture/FOUNDATIONS.md` | Extend Axiom 2 with composition corollary — accumulation projected into output | High — axiomatic (done: Phase 1) |
| `docs/architecture/output-substrate.md` | Integrate compose substrate as structural layer; update pipeline diagram | High — adjacent (done: Phase 1) |
| `docs/architecture/compose-substrate.md` | New canonical reference for the compose domain | High — new (done: Phase 1) |
| `docs/architecture/output-surfaces.md` | New canonical reference for surface types, section kinds, export pipeline | High — new (done: Phase 1) |
| `docs/architecture/workspace-conventions.md` | Remove dissolved sys_compose.md; update output-as-folder structure; root vs derivative assets | Medium |
| `docs/architecture/registry-matrix.md` | Add `page_structure` field to task type catalog | Medium |
| `docs/architecture/task-type-orchestration.md` | Show how compose playbook flows through multi-step task processes | Medium |
| `docs/features/agent-playbook-framework.md` | Compose playbook as a new playbook type alongside task process and agent playbooks | Medium |

### ADRs with status implications

| ADR | Relationship |
|-----|-------------|
| ADR-148 | Extended — SCAFFOLD + ASSEMBLE steps added to pipeline; output folder structure evolves |
| ADR-149 | Extended — DELIVERABLE.md (quality) + task type `page_structure` (structure) as complementary sources (RD-1: sys_compose.md dissolved). Evaluation remains ADR-149's concern, compose substrate consumes its signals. |
| ADR-151/152 | Extended — `context_reads`/`context_writes` become compose substrate's scope index; `sys_` naming convention added to workspace conventions |
| ADR-157 | Absorbed — asset discovery becomes first-class compose operation; root asset distinction formalized |
| ADR-130 | Evolved — Phase 2 (compose integration) is now the compose substrate |
| ADR-166 | Extended — revision routing by `output_kind` formalized in `compose/revision.py` |

### Code files affected (implementation, not this ADR)

| File | Change |
|------|--------|
| `api/services/task_pipeline.py` | Insert scaffold + assembly steps; output folder build |
| `api/services/task_types.py` | Add `page_structure` field to task type definitions |
| `api/services/workspace.py` | Asset discovery helpers; `sys_` file conventions |
| `api/services/agent_execution.py` | `_compose_output_html` evolves to folder-based composition |
| `render/compose.py` | Accept compose playbook structure for folder-aware composition |
| `api/services/directory_registry.py` | Root vs derivative asset conventions |
| `api/services/primitives/manage_task.py` | Scaffold compose playbook on task creation |
| `web/components/work/details/DeliverableMiddle.tsx` | Render from output folder `index.html` instead of flat `output.html` |

---

## Phases

### Phase 1: Foundation (this ADR + architecture docs)
- Create `docs/architecture/compose-substrate.md` (canonical reference) ✓
- Create `docs/architecture/output-surfaces.md` (surface types + section kinds + export) ✓
- Update SERVICE-MODEL.md execution flow ✓
- Update FOUNDATIONS.md Axiom 2 with composition corollary ✓
- Update output-substrate.md with compose substrate integration ✓
- Update workspace-conventions.md (dissolve sys_compose.md per RD-1, update output folder) ✓

### Phase 2: Compose Function + Surface Types ✓ Implemented (2026-04-10)
- ✓ `layout_mode` deleted from all task types. `surface_type` + `page_structure` added to all `produces_deliverable` tasks (all 8, not just 2-3 — pre-launch, no legacy to support).
- ✓ `render/compose.py`: `ComposeRequest` + `compose_html()` renamed to `surface_type`. `_SURFACE_CSS` / `_SURFACE_FN` maps replace `_LAYOUT_CSS` / `_LAYOUT_FN`. 7-surface vocabulary active.
- ✓ `render/main.py`: validates 7-value `surface_type` enum. `/health` updated.
- ✓ `api/services/task_pipeline.py`: parses `**Surface:**` from TASK.md, passes `surface_type` to compose. `build_task_md_from_type()` serializes `**Surface:**` line.
- ✓ All callers updated: `agent_execution.py`, `delivery.py`, `repurpose.py`.

### Phase 3: Assembly + Output Folder Build ✓ Implemented (2026-04-10)
- ✓ `api/services/compose/assembly.py` — `build_generation_brief()`: queries workspace_files per domain, builds per-section briefs (entity counts, asset inventory, staleness signals, kind output contracts, surface formatting guidance)
- ✓ `api/services/compose/manifest.py` — `SysManifest`, `SectionProvenance`, `AssetRecord` dataclasses; `read_manifest()` + `make_manifest()`; `is_section_stale()` staleness detection
- ✓ `api/services/compose/assembly.py` — `parse_draft_into_sections()`: splits LLM draft on `##` headers into per-section content partials; empty placeholders for missing sections
- ✓ `api/services/compose/assembly.py` — `build_post_generation_manifest()`: builds `SysManifest` from parsed sections + live domain state; source provenance per section
- ✓ `api/services/task_pipeline.py` step 12b: both single-step and `_execute_pipeline` paths write `sections/{slug}.md` + `sys_manifest.json` to output folder; `latest/sys_manifest.json` kept current
- ✓ Generation brief wired into `build_task_execution_prompt()` user message; `prior_manifest` read for staleness signals
- ✓ `api/test_compose.py` — 24 tests (16 Phase 3, 8 Phase 4)

### Phase 4: Revision Routing ✓ Implemented (2026-04-10)
- ✓ `api/services/compose/revision.py` — `classify_revision_scope()`: reads prior manifest + current domain state, classifies as `full | section | asset | none`; domain freshness delta check catches domain-level updates not reflected in per-section provenance
- ✓ `build_revision_brief()`: emits targeted LLM instruction for section-scoped runs (rewrite these / preserve these verbatim)
- ✓ `RevisionScope` dataclass: `needs_generation`, `is_full_run`, `is_section_scoped`, `is_current` property shortcuts
- ✓ Wired into single-step execute path (step 6d) and `_execute_pipeline` derive-output step; revision preamble prepended to generation brief for section-scoped runs
- ✓ Logged: `[COMPOSE] {task_slug}: revision_type=section stale=[...] current=[...]` on every produces_deliverable run

### Phase 5: Asset Lifecycle — **DROPPED (2026-04-10)**

Dropped indefinitely. Root asset provenance is already tracked in `sys_manifest.json` (`AssetRecord` with `content_url`, `fetched_at`). The `fetch-asset` render skill (ADR-157) already exists for manual use. Automated re-fetch adds complexity to an unvalidated code path. Revisit if user demand surfaces.

### Phase 6: View-Time Rendering (deferred — separate ADR)
- Frontend interprets output folder structure directly
- React components per section kind
- Live derivative assets (data + render spec, client-side rendering)
- The "runnable app" evolution — output folder as self-contained page application

---

## Resolved Decisions (Stress Test, 2026-04-10)

Five scenarios were stress-tested: simple context task (`track-competitors`), single-domain synthesis (`competitive-brief`), cross-domain synthesizer (`investor-update`), cross-task operational synthesis (`daily-update`), and cascading revision (feedback → section → domain → upstream task). Full scenarios in `docs/analysis/managed-agents-handoff-compute-perimeter-2026-04-09.md` §6.

### RD-1: Compose is a function, not a document

**`sys_compose.md` is dissolved.** The compose substrate does not maintain a separate playbook file per task. The structural knowledge lives where it already exists: `page_structure` field in the task type registry, agent methodology playbooks, and DELIVERABLE.md. The compose function reads these at execution time and produces the output folder. No fourth playbook, no ambiguity about which file is authoritative.

The compose substrate is a **capability layer** that reads existing sources (task type registry + agent playbooks + DELIVERABLE.md + filesystem state) and produces a folder. The only new runtime artifact is `sys_manifest.json` in the output folder (provenance per section + asset status).

### RD-2: The generation brief is the primary output

The compose function's highest-value output is not the folder itself — it's the **generation brief** it gives the LLM before generation. The brief tells the LLM: which sections to write, what data exists per section, what entities are present, what assets are available, what's stale vs. current since last run.

This is where tenure compounds. A tenured workspace has richer domains → the generation brief is richer → the LLM produces more targeted, structured output. Without the compose function, the LLM receives a flat context dump and organizes everything itself.

### RD-3: Revision is composition with diff — no separate workflow

Revision and composition are the same operation with different inputs. First run: compose receives gathered context + `page_structure` → produces folder from scratch. Subsequent runs: compose receives gathered context + `page_structure` + existing output folder + staleness signals → produces updated folder, regenerating only stale sections.

The provenance metadata in `sys_manifest.json` (which run produced each section, what source files it read, when) enables the diff. Compose detects: section X was produced from file Y at time T₁; file Y was updated at T₂ > T₁; therefore section X is stale and needs regeneration.

**Approaches A and B collapse.** There is no separate revision workflow because revision IS composition against a richer input (existing folder + what changed). The four revision types (presentation, section, asset, root context) are still valid as classifications, but they're all handled by the same compose function — they just result in different scopes of regeneration within the output folder.

### RD-4: Compose enhances existing context gathering, doesn't replace it

The pipeline's `gather_task_context()` does the heavy lifting of reading domain files. The compose function operates on already-gathered context and structures it per the task type's `page_structure`. Compose does not need its own filesystem query layer — it adds structural awareness to the existing context-gathering output.

### RD-5: Upstream orchestration stays with TP

When compose detects that upstream data is missing, wrong, or insufficient for a section, it returns a structured diagnosis: which section is affected, which domain/file is the source, which task last wrote it, and what action is recommended. TP receives this and orchestrates the fix (steer upstream task, trigger re-run). The compose function does not reach across task boundaries.

### Impact on Phases

Phase 2 revised: no `sys_compose.md` generation. Instead, add `page_structure` to task type definitions and implement the compose function that reads it. Phase 3 revised: generation brief construction becomes the central implementation concern. Phase 4 revised: no separate revision routing module — revision is handled by the compose function detecting staleness against existing output folder.

### Impact on prior sections

The "Compose Playbook" section above describes the pre-stress-test model. Per RD-1, `sys_compose.md` is dissolved. The `page_structure` on task type definitions remains as the structural template. The compose function reads it at execution time. The "Three Operations" section remains valid: scaffold (on first run, from registry), assemble (compose function proper), revise (compose function with existing folder as additional input).

---

## Resolved Decisions (Output Surfaces, 2026-04-10)

The compose function produces output. But "output" conflates structure (what's in it) with surface (how it looks). A second discourse resolved the output surface model — how the compose substrate handles the wide range of visual paradigms users expect (reports, decks, dashboards, data views, videos).

### RD-6: Surface types are visual paradigms, not file formats

YARNNN is HTML-native (ADR-130). All output is HTML. But HTML that *looks like* a deck, *looks like* a dashboard, *looks like* a data table. The word "slides" describes a visual paradigm (discrete full-screen frames, one idea per frame), not a `.pptx` file. Export to `.pptx` is a separate, lossy, derivative operation.

**Surface types** are the user-facing vocabulary for how information is consumed. Seven surface types:

| Surface Type | Visual Paradigm | Consumption Model | Interaction |
|---|---|---|---|
| **report** | Flowing narrative document | Sequential reading, start to finish | Scroll, section anchors |
| **deck** | Discrete full-screen frames | One idea per frame, presented | Navigate frame-to-frame |
| **dashboard** | Single-canvas overview | At-a-glance, spatial scanning | Grid arrangement, optional drill-down |
| **digest** | Grouped/chronological stream | Quick triage — what matters, what changed | Scan, expand/collapse |
| **workbook** | Tabular-first, data-dense | Analysis, comparison, filtering | Sort, filter, pivot |
| **preview** | In-context mockups | Content shown as it would appear elsewhere | Platform-framed cards |
| **video** | Sequential animated frames | Temporal, narrated, presented | Play/pause, timeline scrub |

Each surface type maps to a distinct HTML experience. The compose function arranges section kinds differently per surface type: a `metric-card` section in a dashboard is a grid tile; in a deck it's a hero slide; in a report it's an inline callout; in a video it's an animated entrance frame.

The `layout_mode` field on task types becomes `surface_type`. Current mapping:

| Current layout_mode | Becomes surface_type | Affected task types |
|---|---|---|
| `document` | `report` (most), `dashboard` (track-*), `deck` (updates) | Split by task type intent |
| `email` | `digest` | daily-update |
| `digest` | `digest` | slack-digest, notion-digest, github-digest |
| `message` | N/A (external_action, no surface) | slack-respond |
| `comment` | N/A (external_action, no surface) | notion-update |
| `presentation` | `deck` | (available but unused until now) |
| `dashboard` | `dashboard` | (available but unused until now) |
| `data` | `workbook` | (available but unused until now) |

### RD-7: Section kinds are the component vocabulary (Palantir/Foundry model)

Section kinds are **typed components** — semantic building blocks the compose function understands. Not arbitrary HTML. A constrained vocabulary with rendering contracts per surface type.

**11 section kinds:**

| Kind | Data Contract | Example |
|---|---|---|
| `narrative` | Prose paragraph(s), optional pullquote/highlight | Executive summary, analysis section |
| `metric-cards` | 2-4 KPI tiles: number + label + delta + optional sparkline | Revenue metrics, health indicators |
| `entity-grid` | Cards: image/icon + title + one-liner + optional badge | Competitor profiles, team roster |
| `comparison-table` | Entities as columns, attributes as rows, optional RAG coloring | Feature comparison, vendor evaluation |
| `trend-chart` | Time-series line/area chart from structured data | Revenue over time, signal frequency |
| `distribution-chart` | Bar/pie/treemap for categorical breakdown | Market share, category split |
| `timeline` | Chronological event list: date + description + source | Signal timeline, changelog |
| `status-matrix` | Entities × criteria with status indicators (red/amber/green) | Competitor health, project status |
| `data-table` | Raw tabular data with headers | Financial data, raw metrics |
| `callout` | Highlighted insight, warning, or recommendation | Key finding, risk alert |
| `checklist` | Action items or criteria with status | Next steps, review criteria |

The section kind is a **rendering contract**: the compose function knows what HTML structure + CSS to produce per kind per surface type. The LLM's generation brief says "produce a `metric-cards` section with these 4 KPIs" — the post-generation assembly parses the output, matches it to the component template, and renders with surface-appropriate treatment.

This is the Palantir Foundry / Tableau "widget" model applied to knowledge work output. The power comes from the constraint: because every component follows a known contract, the platform can render it consistently, theme it across the workspace, and export it to multiple formats without losing structure.

**Section kinds live in the `page_structure` field** on task type definitions — the same field RD-1 established as the structural template. Example:

```python
"competitive-brief": {
    "surface_type": "report",
    "page_structure": [
        {"kind": "narrative", "title": "Executive Summary", ...},
        {"kind": "entity-grid", "title": "Competitor Profiles", ...},
        {"kind": "timeline", "title": "Signal Timeline", ...},
        {"kind": "trend-chart", "title": "Market Position", ...},
    ],
}
```

### RD-8: Export is derivative — completely separate from compose

Three clean layers:

1. **Surface type** — how the user *thinks* about the output (Layer 1: visual paradigm)
2. **Section kinds** — the typed components that compose within any surface (Layer 2: component vocabulary)
3. **Export pipeline** — mechanical, lossy transformation to file formats (Layer 3: interoperability)

Export transforms:

| Export | Input | Output | Valid surface types | Fidelity |
|---|---|---|---|---|
| `pdf` | Any HTML surface | .pdf | All | High (print CSS) |
| `pptx` | Deck surface | .pptx | deck | Medium (structure preserved, styling lossy) |
| `xlsx` | Workbook surface | .xlsx | workbook, dashboard | Medium (data preserved, layout lossy) |
| `docx` | Report surface | .docx | report | Medium (prose preserved, assets flattened) |
| `mp4` | Video surface | .mp4 | video | High (Remotion render) |
| `png` | Any HTML surface | .png | All | Snapshot (single frame) |

Export is NOT part of the compose substrate. It's a downstream mechanical transformation handled by `yarnnn-render`. The compose function produces an output folder with HTML + section partials + assets. Export reads that folder and converts it.

### RD-9: Video is a first-class surface type

Video follows the same model as all other surface types: section kinds compose within it, the compose function arranges them, the output folder contains the specification.

For video, the output folder contains:
- `index.html` — a playable HTML experience (CSS animations, scroll-triggered transitions)
- `spec.json` — a Remotion-compatible scene graph (sections → scenes, data → animated elements)
- `assets/` — static frames, data files for animated charts, audio tracks
- Export to `.mp4` via the `node_remotion` runtime (ADR-130 Runtime Registry)

Section kinds in a video surface: `metric-cards` animate in with number counters. `trend-chart` animates data points appearing over time. `narrative` appears as text overlays or lower-thirds. `entity-grid` sequences cards one by one. The section kind data contract is the same — the surface type determines the temporal treatment.

Video is Phase 6+ but the architecture accommodates it now because surface types and section kinds are the stable abstractions.

### Impact on Architecture Docs

A new canonical reference document, `docs/architecture/output-surfaces.md`, governs the surface type vocabulary, section kind catalog, and export pipeline. `compose-substrate.md` references it for the vocabulary the compose function operates on. `output-substrate.md` references it for the pipeline's surface-type-aware rendering step.

The `layout_mode` field on task types and in `compose.py` evolves to `surface_type`. The CSS in `compose.py` evolves from 5 monolithic layout stylesheets to a matrix: section kind × surface type rendering rules. This is an implementation concern (Phase 2+), not an architectural one.

---

## What This Is Not

- **Not a separate service.** The compose substrate lives in the API service. It needs filesystem access, task type awareness, and directory registry — all API-resident concerns.
- **Not a replacement for the render service.** `yarnnn-render` stays for mechanical transformation (pandoc, matplotlib, mermaid-cli, final HTML styling). The compose substrate produces the *structural plan* and *output folder*; the render service produces *derivative assets* and *styled HTML*.
- **Not a new storage layer.** The filesystem (`workspace_files`) is the data model. The compose substrate queries it, it doesn't duplicate it.
- **Not LLM-driven composition.** Assembly and revision routing are deterministic Python. The only LLM call is generation (writing prose for sections). Zero LLM cost for compose operations.
- **Not a quality evaluator.** The compose substrate binds structure; it does not judge quality. Evaluation remains in ADR-149's feedback/evaluation/reflection framework. The compose substrate consumes evaluation signals as revision inputs.

---

## Parked Concerns (Documented, Deferred)

These broader architectural concerns surfaced during compose substrate discourse. They are related but not blocking, and each deserves independent treatment.

### 1. `sys_` as System-Wide Naming Governance

The `sys_` prefix introduced here for compose artifacts (`sys_compose.md`, `sys_manifest.json`) is actually a **system-wide governance rule** — a naming tier alongside existing `UPPERCASE.md` (charter), `lowercase.md` (content), and `_prefixed.md` (hidden infrastructure). `sys_` signals "system-managed, inspectable but not user-authored."

**Scope:** All workspace conventions, frontend explorer visibility rules (grey-out or collapse `sys_` files alongside hiding `_` files).
**Action:** Workspace-conventions.md version bump or lightweight ADR. Not blocking compose substrate.

### 2. Evaluation as Independent Entity

The compose substrate explicitly does not evaluate quality — it consumes evaluation signals. But the broader thesis is stronger: **evaluation should be structurally independent of the system it evaluates**, like an external audit firm auditing a corporation. This means:
- Evaluation criteria managed independently of both compose playbook and DELIVERABLE.md.
- Evaluation results in their own namespace (not just appended to feedback.md).
- Potentially a distinct evaluation agent or evaluation concern on TP.

**Scope:** New architectural domain. Extends ADR-149 (feedback/evaluation/reflection) into a first-class independent entity.
**Action:** Separate ADR. Not blocking compose substrate — compose consumes evaluation signals regardless of where they originate.

### 3. Output as Runnable App

The output-as-folder model's logical endpoint: when the folder contains enough structure (HTML partials, data files, styles, render instructions), it's a self-contained application that agents could build from a task instruction. This means:
- Output folders with their own package manifests.
- Client-side rendering of live derivative assets (data + render spec, not frozen images).
- The BI dashboard spectrum: static snapshot → interactive page → live app.

**Scope:** Phase 6 of ADR-170. Large enough for its own ADR.
**Action:** Separate ADR when compose substrate Phases 2-4 are implemented and the folder model is proven.

---

## Axiom Claim

The compose substrate is **axiomatic** to YARNNN's architecture because it is the layer that makes the accumulation thesis (FOUNDATIONS Axiom 2) manifest in output. Without it, the filesystem accumulates but output doesn't structurally reflect that accumulation — each run starts fresh with no structural memory of what's been built. With it, output is a *projection* of the filesystem through the lens of the task's compose playbook, and revision is a *targeted response* to filesystem changes rather than a full regeneration gamble.

The filesystem has gravity (things accumulate, net direction is growth). The compose substrate is what converts that gravity into deliverable quality that compounds with tenure. The output folder — with its section partials, root assets, derivative assets, and assembly index — is the physical manifestation of that compound value.
