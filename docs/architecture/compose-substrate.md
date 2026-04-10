# Architecture: Compose Substrate

> **Status:** Canonical (ADR-170). Phases 2–4 implemented 2026-04-10.
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

The output is not a single `output.html` file. It is a **folder** — a collection of section partials, a composed HTML file, and a provenance manifest.

**Current state (Phases 2–4 implemented):**

```
/tasks/{slug}/outputs/{date}/
├── output.md                  # source markdown (full draft, agent-authored)
├── output.html                # composed HTML (surface-type-aware, from render service)
├── sections/                  # section partials (one per page_structure section)
│   ├── executive-summary.md   # markdown content for this section
│   ├── competitor-profiles.md
│   └── recent-signals.md
├── manifest.json              # run metadata: version_id, tokens, agent_slug
└── sys_manifest.json          # compose provenance: produced_at, source_files,
                               #   source_updated_at per section; domain_freshness;
                               #   root asset records (content_url, fetched_at)
```

**Target state (Phase 6 — view-time rendering, future ADR):**

```
/tasks/{slug}/outputs/{date}/
├── output.md
├── output.html                # flat composed HTML (current — iframe target)
├── index.html                 # section-aware entry point (Phase 6 — assembles partials)
├── sections/
│   ├── executive-summary.md   # markdown partial (current)
│   └── executive-summary.html # rendered HTML partial (Phase 6)
├── assets/
│   ├── acme-favicon.png       # root: from domain assets/ folder
│   └── market-pos.svg         # derivative: rendered chart (Phase 6)
├── data/
│   └── metrics.json           # structured data backing derivative assets (Phase 6)
└── sys_manifest.json
```

The frontend currently renders `output.html` via iframe. Phase 6 will consume the folder structure directly with React components per section kind.

---

## Two Kinds of Assets

| | Root Assets | Derivative Assets |
|---|---|---|
| **What** | Durable entities fetched/created independently | Generated from source data during render |
| **Examples** | Logos, screenshots, user-uploaded images | Charts, diagrams, mermaid SVGs |
| **Where they live (source)** | `/workspace/context/{domain}/assets/` | Generated into output folder `assets/` |
| **Tracked in** | `sys_manifest.json` → `AssetRecord(kind="root", content_url, fetched_at)` | `sys_manifest.json` → `AssetRecord(kind="derivative", render_skill, produced_at)` |
| **Can refresh without prose regen?** | Yes | Yes |

**Current state:** Root assets are discovered from domain `assets/` folders and recorded in `sys_manifest.json` with their `content_url`. The LLM is told about them in the generation brief ("embed using their content_url"). Derivative assets are rendered inline by `render_inline_assets()` (tables → charts, mermaid → SVGs) as part of the existing render pipeline.

**Phase 5 (dropped — decision recorded below):** Automated re-fetch of stale root assets and cross-run derivative asset caching were planned here. Deferred indefinitely — no production evidence of this being a pain point, and the `fetch-asset` skill already exists for manual agent use when needed.

---

## Three Operations

### 1. Scaffold

**Input:** Task type `page_structure` + `surface_type` from `task_types.py`.
**Output:** In-memory structural plan. Determines what sections to generate, what directory scopes to query, what assets to look for. Happens at the start of every `execute_task()` call — no file persisted (ADR-170 RD-1).

### 2. Assemble ✓ Implemented

**Pre-generation — `build_generation_brief()` in `assembly.py`:**
- Reads task type `page_structure` + `surface_type` from registry.
- Reads `outputs/latest/sys_manifest.json` for prior provenance (first run: none).
- Calls `classify_revision_scope()` (revision.py) — determines full/section/none scope.
- Queries `workspace_files` for each domain in `context_reads`: entities, synthesis files, assets.
- Builds per-section briefs: entity counts, data sources with freshness dates, asset inventory, kind output contracts, staleness signals.
- For section-scoped re-runs: prepends revision preamble (which sections to rewrite, which to preserve verbatim).
- Injects into `build_task_execution_prompt()` user message.

**Post-generation — `parse_draft_into_sections()` + `build_post_generation_manifest()` in `assembly.py`:**
- Splits LLM draft on `##` headers → per-section content partials.
- Writes `outputs/{date}/sections/{slug}.md` for each section.
- Queries domain state for provenance: which source files each section drew from, their `updated_at`.
- Writes `sys_manifest.json` to `outputs/{date}/` and `outputs/latest/` (for next-run reads).
- Root assets discovered from domain state → recorded in manifest `AssetRecord` entries.

### 3. Revise ✓ Implemented

**When:** Every `execute_task()` re-run reads `outputs/latest/sys_manifest.json` and classifies scope before generating.

Revision is composition with diff — same function, richer input (ADR-170 RD-3). `classify_revision_scope()` in `revision.py` compares manifest provenance against current domain state:

| Scope | When | Action | LLM cost |
|-------|------|--------|----------|
| `none` | All sections current, domain freshness unchanged | Skip generation entirely | Zero |
| `section` | 1..N sections stale, rest current | Regenerate stale partials; LLM told to preserve current verbatim | Sonnet (scoped) |
| `full` | No manifest, or all sections stale | Full regeneration | Sonnet (full) |
| `asset` | Asset stale but no section prose change | Re-render/re-fetch only | Zero (future Phase 6) |

**TP → compose revision loop (pending — see gaps below):** TP steering notes currently contain free-text instructions. The loop will be complete when TP can target a specific section slug in steering, and the compose function routes that to section-scoped regeneration without a full re-run.

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
├── __init__.py      # exports: build_generation_brief, parse_draft_into_sections,
│                   #   build_post_generation_manifest, classify_revision_scope,
│                   #   build_revision_brief, read_manifest, make_manifest, SysManifest
├── assembly.py      # filesystem query, generation brief, section parsing, manifest build
├── revision.py      # revision classification (full/section/none) + LLM revision preamble
└── manifest.py      # sys_manifest.json schema: SysManifest, SectionProvenance, AssetRecord
```

**Test coverage:** `api/test_compose.py` — 24 tests covering section parsing, manifest round-trip, staleness detection, revision classification (full/section/none/domain-freshness-triggered), revision brief generation.

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
| **Output Surfaces (ADR-170 RD-6/7/8/9)** | Defines the vocabulary — surface types + section kinds + export pipeline. See [output-surfaces.md](output-surfaces.md). |
| **Task Lifecycle (ADR-149)** | Extended — DELIVERABLE.md (quality) + task type `page_structure` (structure) as complementary sources. Evaluation remains ADR-149, compose consumes its signals. |
| **Context Domains (ADR-151/152)** | Extended — `context_reads`/`context_writes` become compose substrate's scope index |
| **Fetch-Asset Skill (ADR-157)** | Absorbed — asset discovery is first-class compose operation; root/derivative distinction formalized |
| **Registry Coherence (ADR-166)** | Extended — `output_kind` drives revision routing semantics; `surface_type` replaces `layout_mode` on task types |
| **Workspace Conventions** | Extended — `sys_` naming convention; output-as-folder structure |
| **Service Model** | Extended — compose substrate is a named domain within Layer 2 |
| **FOUNDATIONS Axiom 2** | Extended — composition is the corollary that makes accumulation manifest |

---

## Open Gaps (as of 2026-04-10)

### Gap 1: TP section-level steering awareness

**Current state:** TP steers via free-text notes written to `memory/steering.md`. The compose substrate reads these notes and injects them into the LLM prompt, but it cannot route them to specific section partials. TP has no knowledge of what sections exist for a given task type.

**What's needed:**
- TP working memory injection should include the task's `page_structure` section titles when a `produces_deliverable` task is in context (compact index addition in `working_memory.py`).
- `ManageTask(action="steer")` should optionally accept a `target_section` field (slug or title) alongside the existing `steering_notes` string.
- When `target_section` is set, the revision preamble marks only that section as stale (`revision_type=section`, `stale_sections=[target_section]`), bypassing the manifest-based staleness check.
- This closes the ADR-149 evaluate → steer → compose revision loop end-to-end.

**Files:** `api/services/working_memory.py`, `api/services/primitives/manage_task.py`, `api/services/compose/revision.py`.

### Gap 2: Frontend view-time rendering (Phase 6)

**Current state:** `DeliverableMiddle.tsx` renders `output.html` in an iframe. The section partials (`sections/{slug}.md`) and `sys_manifest.json` written by the compose substrate are invisible to the frontend.

**What's needed (future ADR):**
- Read `sys_manifest.json` from the task's latest output folder via a new API endpoint or workspace file read.
- Render each section partial with a React component per `kind` (narrative, entity-grid, metric-cards, timeline, comparison-table, etc.) rather than a monolithic iframe.
- `index.html` (current single output) either becomes the fallback or is deprecated in favor of section-component rendering.
- Surface type determines layout (report = scroll, deck = full-screen slides, dashboard = grid, digest = list).

**Prerequisite:** Real users using the product and generating output. The iframe is a valid interim. Don't build the component library before there's production output to validate it against.

**Files:** `web/components/work/details/DeliverableMiddle.tsx`, new `web/components/work/sections/` directory.

### Gap 3: Phase 5 dropped (decision record)

**Decision (2026-04-10):** Phase 5 (asset lifecycle — automated stale root asset re-fetch, cross-run derivative asset caching, static vs live derivative distinction) is **dropped indefinitely**.

**Rationale:** The `fetch-asset` render skill (ADR-157) already exists for manual agent use when needed. Root assets (favicons, logos) change rarely. Automated re-fetch adds complexity to a code path that hasn't been exercised in production yet. The manifest already records asset provenance — if automated re-fetch becomes a pain point, that record is sufficient to build on. Revisit when there's a concrete user complaint.
