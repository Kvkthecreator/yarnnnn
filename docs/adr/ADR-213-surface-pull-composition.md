# ADR-213: Surface-Pull Composition — Tasks Write Substrate, Surfaces Render

**Status:** Proposed
**Date:** 2026-04-23
**Dimensional classification:** **Channel** (primary, Axiom 6) + **Substrate** (Axiom 1) + **Mechanism** (Axiom 5)

## Context

Today the task pipeline force-calls `_compose_and_persist()` for every `produces_deliverable` run (`api/services/task_pipeline.py:437`, invoked at `:2261`). Composition writes four things to the task workspace:

1. `outputs/{date}/output.html` + `outputs/latest/output.html` — styled HTML artifact
2. `outputs/{date}/sections/{slug}.md` — section partials (kind-labeled markdown)
3. `outputs/{date}/sys_manifest.json` + `outputs/latest/sys_manifest.json` — revision state

Only (2) and (3) are *substrate*. (1) is a **presentation artifact** that the task pipeline produces speculatively — it gets composed on every run regardless of whether anyone will read it, and it's frozen at the moment the task ran even though the underlying substrate (section partials, context domains, brand CSS) may evolve before a reader looks at it.

Three architectural pressures have made this coupling outdated:

1. **ADR-198 canonized five surface archetypes** (Document / Dashboard / Queue / Briefing / Stream). Document is one archetype among five; the task pipeline currently privileges it as *the* output shape.
2. **ADR-202 demoted email to pointer-only.** Composition is no longer shaped by a delivery channel — cockpit is primary. Nothing downstream depends on a pre-composed `output.html` existing at task-run time.
3. **The alpha-trader "daily universe" is a Dashboard, not a Document.** The trader persona (ALPHA-1-PLAYBOOK §3A) wants a live read of `_performance_summary.md` + signal states + portfolio exposure — a Dashboard-archetype surface that should re-render when the substrate updates, not a frozen HTML snapshot composed once at 6am.

The compose engine itself (`render/compose.py`, ADR-130 + ADR-177) is already decoupled — it's a pure section-kind-aware markdown→HTML renderer with `surface_type` support for `report | deck | dashboard | digest | workbook | preview | video`. The coupling lives entirely in the task pipeline owning the `/compose` call site.

## Decision

**Tasks write substrate. Surfaces pull composition on demand. Output HTML becomes a derivative artifact, not a primary output.**

### Decisions locked in

1. **Task pipeline stops writing `output.html`.** `_compose_and_persist()` collapses to `_persist_sections_and_manifest()`: parses the draft into `SectionContent` objects, writes section partials + `sys_manifest.json`. The render service call is deleted from the task pipeline.

2. **New endpoint: `GET /api/tasks/{slug}/outputs/{version}/render?surface_type={kind}`.** Reads section partials + manifest from the task workspace, calls `/compose`, returns `text/html`. `{version}` accepts `latest` or a numeric version. `surface_type` defaults to the task's declared `surface_type` (from TASK.md, ADR-207 P4b).

3. **Content-addressed cache on the render service.** `/compose` computes `sha256(sections + surface_type + assets + brand_css + engine_version)` before any work. Cache backing store: Supabase Storage bucket `composed-html/{hash}.html`. Cache is shared across replicas, survives deploys, auto-invalidates on any input change (ADR-209 revision hashes make substrate changes automatic). No explicit eviction v1; optional 90-day TTL sweep later.

4. **`output_kind=produces_deliverable` reframes semantically** from "task produces HTML" to "task writes sectioned substrate." The pipeline invariant becomes: after a `produces_deliverable` run, `outputs/latest/sections/*.md` and `outputs/latest/sys_manifest.json` are consistent. HTML is not a task output — it's a surface output.

5. **Five-archetype surfaces each own their compose call.** Document surface requests `surface_type=report`, Dashboard requests `surface_type=dashboard`, Briefing requests `surface_type=digest`. Composition becomes a presentation-layer concern. Multiple surfaces can compose the same substrate at different `surface_type` values simultaneously.

6. **Reclassification audit is mandatory in Phase 3.** All 12 current `produces_deliverable` task types in `api/services/task_types.py` are audited against ADR-198 archetypes. Tasks that are structurally live Dashboards (daily-universe, portfolio-review, `_performance_summary.md`-shaped outputs) get reclassified to `accumulates_context` or a new output_kind, and their Sonnet synthesis step is deleted. The Dashboard surface reads the substrate live. This is where LLM cost savings accrue.

### Why content-addressed caching

ADR-209 already commits us to content-addressed identity for substrate (workspace_blobs keyed by sha256). Applying the same pattern to rendered HTML means:

- **No invalidation code.** A section partial edit produces a new revision → new section content → new compose input hash → new cached HTML. Old hash ages out naturally.
- **No brand-CSS invalidation cascades.** Brand CSS is part of the input hash. Operator edits brand → all cached renders that used the old CSS are cold; all new renders populate new hashes. No stale reads, no explicit flush.
- **Deploy-safe engine bumps.** `engine_version` (compose.py version constant) is part of the hash. A compose.py change invalidates all cached renders for free.
- **Cheap miss path.** Compose → write to storage → return. Write failure doesn't block the response (cache is best-effort).

### Why not on-disk or in-memory caching

- **In-memory LRU on render service**: evaporates on deploy, doesn't survive horizontal scaling (the service is single-replica today but the premise leaks architectural debt).
- **Postgres `composed_outputs` table**: stores large HTML blobs in Postgres, exactly what ADR-209 just moved away from.
- **CDN / edge cache**: premature; adds infra surface with no user yet.

## Consequences

### Preserved

- FOUNDATIONS v6.0 axioms (unchanged).
- ADR-130 (HTML-native output substrate) — compose engine unchanged.
- ADR-177 (section kind rendering) — section parsing unchanged, just moves out of the task pipeline.
- ADR-209 (authored substrate) — revision chain unchanged; this ADR layers presentation caching on top.
- ADR-182 (pre-gather pipeline optimization) — produces_deliverable generation cost unchanged.
- ADR-202 (external channel discipline) — email pointer pattern unchanged and reinforced (email never composes; it points).

### Amended

- **ADR-177**: compose call site moves from `task_pipeline._compose_and_persist` to the surface render endpoint. Section parsing happens on the task pipeline side (substrate write); composition happens on the surface side. This finalizes ADR-177's phase D1 intent.
- **ADR-130**: composition becomes on-demand, not task-coupled. `output.html` is no longer a substrate artifact.
- **ADR-166**: `produces_deliverable` sharpens from "task writes HTML" to "task writes sectioned substrate."
- **ADR-198**: surfaces own their compose call. Each archetype picks its `surface_type` when requesting a render.

### New

- `GET /api/tasks/{slug}/outputs/{version}/render` endpoint (new).
- Content-addressed cache layer on the render service.
- Reclassification audit of the 12 `produces_deliverable` task types.

### Deleted

- `_compose_and_persist()` as currently structured — collapses to substrate-write only. The `/compose` POST from the task pipeline is removed.
- `outputs/{date}/output.html` + `outputs/latest/output.html` writes from the pipeline. (Cockpit readers switch to the new render endpoint in Phase 2.)

## Implementation

### Phase 1 — Substrate-only task pipeline (no user-visible change)

- Rename `_compose_and_persist()` → `_persist_sections_and_manifest()`. Keep it writing section partials + `sys_manifest.json`. Delete the `/compose` POST from inside it.
- Add `GET /api/tasks/{slug}/outputs/{version}/render?surface_type={kind}` in `api/routes/tasks.py`. Reads sections + manifest from the task workspace, calls `/compose`, returns HTML.
- Render service: add content-addressed cache at `/compose` entry. `composed-html/{hash}.html` in Supabase Storage. Hit → fetch + return. Miss → compose → write + return.
- **Continuity shim**: keep writing `output.html` at the pipeline for one release so the cockpit's current iframe readers don't break. Mark with `# ADR-213 Phase 1 shim — delete in Phase 2`.

### Phase 2 — Cockpit switches to pull

- Frontend `DeliverableMiddle.tsx` (and other cockpit Document readers) switch their iframe `src` from `/api/workspace/file?path=outputs/latest/output.html` to the new render endpoint.
- **Delete** the `output.html` write from the task pipeline. Delete the shim.
- Permanent CI regression test: grep asserts `output.html` is never written by code under `api/services/task_pipeline.py`.

### Phase 3 — Reclassification audit

- Audit all 12 current `produces_deliverable` task types against the five ADR-198 archetypes.
- Expected reclassifications (candidates, subject to review):
  - `daily-update` — probably Briefing (already pointer-shaped after ADR-202).
  - `portfolio-review` — probably Dashboard (live `_performance_summary.md` read).
  - `revenue-report` — probably Dashboard.
  - Any task whose "generation" is really "synthesize the state of these context domains into prose" is a Dashboard candidate.
- Reclassified tasks get their synthesis step deleted. The Dashboard surface composes substrate live.
- Task types that remain `produces_deliverable` are the ones doing genuine synthesis work that doesn't reduce to substrate read-through (e.g., `competitive-brief`, `meeting-prep`, `stakeholder-update`).

### Phase 4 — Surface-scoped renders (deferred)

- `GET /api/surfaces/overview/render` for Dashboard-archetype surfaces not tied to a specific task.
- Cross-task Dashboard compositions (e.g., "all trackers rollup").

## Rejected alternatives

- **Keep composition task-coupled but cache the output HTML per run.** Doesn't address the architectural mismatch — tasks still frozen-compose a Document regardless of whether anyone reads it as a Document. Dashboard-archetype surfaces still need a separate live read path.
- **Materialize composed HTML for every surface × task combination eagerly.** Combinatorial explosion (5 archetypes × 12 task types × N versions × workspace_count). Content-addressed cache handles this via lazy materialization with zero coordination.
- **Move compose into the API service, drop the render service.** Render service is already isolated infra with matplotlib + pandoc + python-pptx dependencies we don't want in the API process. ADR-118 gave us a clean boundary; keep it.

## Cost / pricing

Composition is 0 LLM tokens — decoupling doesn't directly save LLM spend. Savings come from the second-order effect in Phase 3:

| Source | Mechanism | Estimate |
|---|---|---|
| Dashboard reclassification | Delete Sonnet synthesis on tasks that are really live Dashboard reads | ~$3.00/user/month (2 of ~5 produces_deliverable tasks × ~$1.62/task/month per ADR-182) |
| Cache CPU savings | 95% cache hit on unchanged substrate → compose runs ~20× less | Negligible today, material at scale |
| Avoided cadence re-runs | If substrate hasn't changed since last cadence tick, Dashboard serves cached render; task doesn't need to run | ~$0.50–1.00/user/month |

Phase 1–2 are structural plumbing (no savings). Phase 3 is where alpha cost drops.

## References

- ADR-130: HTML-native output substrate (compose engine)
- ADR-166: Registry coherence pass (output_kind semantics)
- ADR-177: Section kind rendering (parse-then-compose ordering)
- ADR-182: Pre-gather pipeline optimization (produces_deliverable generation cost)
- ADR-198: Surface archetypes (Document / Dashboard / Queue / Briefing / Stream)
- ADR-202: External channel discipline (email pointer pattern)
- ADR-209: Authored substrate (content-addressed identity, revision chains)
- `ALPHA-1-PLAYBOOK.md` §3A — alpha-trader daily-universe as live Dashboard
