# ADR-333 — Compose as a Lazy Projection: Rewiring the Orphaned Production Half

**Status:** **Implemented** (2026-06-10) — operator-approved, all decisions landed. Regression gate `api/test_adr333_compose_projection.py` 9/9 PASS; sibling gate `api/test_adr261_phaseB.py` updated (the ADR-262 D4 auto-compose-present assertion superseded by an absent-assertion) ALL PASS; `api/test_adr330_ground_truth_intake.py` 17/17 PASS (unaffected). Net: `_maybe_auto_compose` (~150 LOC) DELETED from `wake.py`; composer made root-agnostic (one `artifact_kind` param, report default); `authored_*` conventions family added; `routes/authored.py` consumption-pull surface mounted at `/api/authored/*`. One scope note: `test_quality_e2e.py`'s eager-`output.html` assertion was already dead (references the pre-ADR-231 `/tasks/{slug}/outputs/` path) — not resurrected here; left for a separate stale-test cleanup. `content.md` shipping (`status: published` flip, no `ship_piece` action) unchanged — that gap is ADR-283-era, out of this ADR's scope.
**Date:** 2026-06-10
**Deciders:** KVK (operator) + Claude (collaborator)
**Hat:** A (system canon — real-operator-facing)

> **Discourse base:** [`compose-rewiring-the-orphaned-production-half-2026-06-10.md`](../analysis/compose-rewiring-the-orphaned-production-half-2026-06-10.md) (v2 — the axiomatic rewrite after the operator flagged cost-blindness in v1; every load-bearing claim carries a `file:line` receipt re-verified live 2026-06-10). The richness forks this ADR's production spec encodes were settled against [`richness-soak-yarnnn-author/DESIGN-MEMO-rich-piece.md`](../evaluations/richness-soak-yarnnn-author/DESIGN-MEMO-rich-piece.md) (operator sign-off on the four forks 2026-06-10).

**Sibling:** [ADR-330](ADR-330-ground-truth-intake.md) is **flow 3** (outcomes in — the world's verdict on acts). This ADR is the **production / work-out** half — how the artifact an operator publishes gets composed. Complementary; both touch alpha-author; cross-referenced, not merged (proposal §7.4).

**Amends:**
- [ADR-213](ADR-213-surface-pull-composition.md) — ratifies its "surface-pull composition" as the **uniform** axiom and retires the eager auto-compose push that contradicts it. ADR-213 established pull-on-consume for the three report pull surfaces but left `_maybe_auto_compose` pushing eagerly at session-close (the §4 bug). This ADR makes the whole system honor ADR-213's own principle.
- [ADR-262](ADR-262-output-topology-and-specs.md) — D4's "opt-out structural auto-compose at session-close" is retired. Session-close persists *substrate only* (the Reviewer already writes sections + manifest); the render is pulled at consumption, never pushed at session-close. The substrate-shape trigger concept survives; the eager render does not.
- [ADR-283](ADR-283-author-program.md) — gives the authored deliverable (`operation/authored/{slug}/`) a composition topology + pull surface, the production capability the author program was specified to need but never wired. `content.md` stays operator-canonical (preserved).

**Preserves:** FOUNDATIONS Axioms 0–9 · Axiom 1 (substrate is canonical; HTML is a derivative projection, never a source) · [ADR-209](ADR-209-authored-substrate.md) Authored Substrate (every substrate write attributed) · [ADR-148](ADR-148-output-gateway.md)/[ADR-170](ADR-170-section-manifest.md)/[ADR-177](ADR-177-section-kind-rendering.md) compose mechanical pipeline (section-kind rendering, designer dispatch, content-addressed cache — all unchanged) · ADR-320 five-root topology (composition substrate lands under `operation/`).

---

## 1. Problem statement

YARNNN ships a complete multi-modal compose pipeline — `render/compose.py` (section-kind rendering: comparison-table, mermaid, trend-chart, metric-cards, status-matrix, entity-grid, timeline) + the designer specialist (`DispatchSpecialist(role="designer")` → `RuntimeDispatch` chart/image/mermaid assets) + content-addressed caching (ADR-213). It is live, test-covered, and **GREEN**.

It produces rich HTML for exactly one thing: **reports** (`/workspace/operation/reports/{slug}/{date}/`).

It produces nothing for the thing operators actually publish: **author pieces** (`/workspace/operation/authored/{slug}/content.md`) ship as **flat markdown**. They never touch compose. This is why YARNNN's own blog corpus is 102 posts of flat prose, zero images/tables/diagrams — and it would be true for any real author operator.

**Receipts (live, 2026-06-10):**

- `api/services/conventions.py` defines `report_root()` (line 100) and the full `report_*` family (dated folder, output path, sections dir, manifest), but **no `authored_root()`** and no authored-composition helpers. The authored path is hardcoded in `operator_proxy/scenarios.py:1073-1074`, `wake_sources/substrate_event.py`, and `primitives/manage_hook.py` — evidence the production half was never given a home in the conventions module.
- `api/services/compose/task_html.py:54,57` hardcodes `report_root(task_slug)` internally — the composer is structurally bound to the report path. There is no way for an authored piece to be composed by the existing function.
- The pull surfaces — `routes/recurrences.py:603`, `delivery.py:694`, `repurpose.py:142`, the `Compose` primitive (`primitives/compose.py:110`) — are all report-scoped (they pass a `task_slug` that resolves to `report_root`).
- `api/services/wake.py:1271-1414` (`_maybe_auto_compose`) **eagerly calls `compose_task_output_html` at session-close** (line 1373) and persists `output.html` (line 1391) — *whether or not anyone consumes it.* The same artifact is then re-composed on consumption-pull. The storage cache is the only thing preventing fully-duplicated render work.

### Why the seam exists (the archaeology)

Compose was task-pipeline-wired in the prior era (ADR-177 D1: `_compose_and_persist()` lived *in* `task_pipeline.py`). Then ADR-231 deleted `task_pipeline.py` + the task abstraction, and ADR-260/261/262 replaced it with the reviewer-agent loop. Compose got **re-wired, but only halfway** — re-attached (ADR-262 D4) as a session-close auto-trigger scoped to the **report path + sections-shape**. Author pieces live at `operation/authored/` (not `reports/`) and are a flat `content.md` (not a `sections/*.md` folder), so the trigger never matches them. The orphaning is implicit: the reviewer-agent author workflow never writes the `sections/` substrate the trigger keys on, and the authored path isn't even in `conventions.py`. The compose pipeline is an **era-fossil**: re-wired for the report path the reviewer-agent inherited, never given a production path for the artifact operators publish.

## 2. The invariants (the axiom, derived not preferred)

Three invariants, true regardless of trigger preference:

- **Invariant 1 — Compose is a *projection* of substrate, never a *source* of truth.** The substrate (`content.md`, `sections/*.md`, asset URLs) is canonical (Axiom 1; ADR-209; ADR-213). A projection is reproducible from source at any time, so it never needs eager materialization — only production when consumed.
- **Invariant 2 — Cost is incurred at production; value is realized at consumption.** A rich artifact never read cost real render-service-load / LLM / storage-I-O and returned zero value. The correct coupling is **produce-when-(and-only-when)-consumed.** (The render service is a separate Docker instance that can scale-to-zero; a "cache hit" is a cross-service round-trip + storage egress, not a memory lookup — proposal §2. Eager render drives that cost for artifacts no one reads.)
- **Invariant 3 — Two production costs, different economics.** *Rich-substrate production* (LLM structure-judgment + designer sub-LLM + subprocess + storage) changes rarely — a piece's structure is decided once. *HTML render* (cross-service hop + storage I/O) re-incurs on every cache miss, and misses happen on every substrate change.

> **AXIOM:** Compose is a **lazy projection pulled at the consumption boundary.** The expensive half (structure + assets) is produced once, deliberately, idempotently, and persisted as *substrate* (sections + asset URLs) — never as HTML. The cheap half (HTML render) is pulled when a surface actually consumes the artifact. **The render is pulled, never pushed.**

This is not new — it is exactly ADR-213's "surface-pull composition," stated as the axiom it always was. The work is to apply it *uniformly*.

## 3. Decisions

| # | Decision | Shape |
|---|----------|-------|
| **D1** | **Ratify the projection axiom (§2).** Compose is a lazy projection pulled at consumption; the render is pulled, never pushed; rich-substrate production is a separate deliberate substrate-write. "Deliverable" generalizes to *any* audience-facing artifact (published pieces, not only reports). | Framing — load-bearing; everything else is consequence. |
| **D2** | **Retire the eager push, uniformly.** Neuter `_maybe_auto_compose`'s session-close render (`wake.py:1271-1414`). Session-close persists *substrate only* (sections + manifest, already written by the Reviewer); it does **not** call the render service. Render happens on pull, for reports AND pieces. **Singular Implementation: one shape (pull-on-consume), removing code, not adding a parallel path.** | Behavior change on the live report path. Cost win: daily reports stop driving the Docker render service on every fire; they render only when opened/delivered/exported. |
| **D3** | **Make the composer root-agnostic.** `compose_task_output_html` takes the substrate root (or resolves it from artifact-kind) rather than hardcoding `report_root`. One composer, two roots (reports + authored). | Code: ~10-line change to `compose/task_html.py` signature + internal resolution. The Singular-Implementation move — no parallel author-composer. |
| **D4** | **Give the authored deliverable a conventions home.** Add `authored_root(slug)` + dated-folder / sections-dir / sys-manifest helpers to `conventions.py`, mirroring the `report_*` family. The composition substrate lands at `/workspace/operation/authored/{slug}/{date}/sections/`. | Closes the missing-`authored_root()` gap (§1). |
| **D5** | **Structure is native to authoring — no "rich" mode, no enrich step, no trigger.** The Reviewer, when authoring/revising a piece, decides structure *as part of the same act* — emitting `kind:`-tagged sections where its judgment says a kind carries the argument better than prose (the "could this be a paragraph without loss?" gate). The production spec (`operation/specs/piece-composition.md`) teaches this judgment. There is no second production pass and no `make_rich` action. | Collapses the proposal's D4 "deliberate rich-substrate production recurrence" — the new architecture already decides structure during authoring. No new recurrence, no hook. |
| **D6** | **A consumption-pull surface for authored deliverables.** The FE route / delivery / export pulls `compose_task_output_html` for the authored path — mirrors the report pull surfaces. The render fires here, lazily, cached. | Code: an authored-output route (and delivery/export reuse via the root-agnostic composer). |
| **D7** | **`content.md` stays the operator's canonical authored source (ADR-283 preserved).** The composed piece is the *projection* of `{content.md's prose + the produced sections/assets}`; never a competing source of truth. There is no stored HTML artifact — only the pull-rendered view, the storage cache being memoization. | Dissolves the v1 "beside vs replaces" question — there is no stored artifact. |
| **D8** | **Author-first; generalize on demand.** The same axiom serves any non-report deliverable, but only the author program needs it now. Prove it there; generalize when a second program asks (demand-pull, per ADR-327 D6.d). | Scoping. |

## 4. What the axiom dissolves

The two questions the v1 proposal asked were mis-framed artifacts of a push-model assumption:

- **"Trigger shape?"** — dissolved. There is no production trigger for the render (pulled at consumption, Inv 2). The only deliberate act is *authoring the piece* (D5 — structure is native to it). All "operator-invoked / cadenced / ship-hooked" options were eager-projection variants of the §1 bug.
- **"Artifact relationship?"** — dissolved by Inv 1. The HTML is not a stored artifact; it's a view, pulled on demand. `content.md` + `sections/` + asset URLs are substrate (canonical); HTML is the projection.

## 5. The richness forks (encoded in the production spec, not this ADR)

`docs/programs/alpha-author/reference-workspace/operation/specs/piece-composition.md` (landed) encodes the four operator-settled forks:

1. **Richness = argument-fidelity-gain, never asset count.** A section-kind earns its place only when it carries the argument better than prose would ("could this be a paragraph without loss?"). The anti-Goodhart spine, built into the definition.
2. **Palette ranking.** Tier 1 (comparison-table + mermaid + callout) = the spine; Tier 2 (metric-cards / status-matrix / trend-chart) only with real substrate data; Tier 3 (generated images) exceptional, one max, highest Goodhart risk.
3. **Format = composed HTML article, not slides.** The em-dash-fluent connective prose carries the argument; slides would fragment it.
4. **Eval = argument-fidelity vs the flat baseline.** Re-make a strong flat post (control: `money-truth-as-a-file-not-a-dashboard`), A/B the composed vs flat on legibility + voice integrity; track structural-judgment improvement over tenure. Designed so its signal is *not* gameable — which is why it stays separate from and non-contaminating to the alpha-author Goodhart probe.

## 6. Implementation outcome (landed 2026-06-10)

1. **D3 + D4** — `compose_task_output_html` gains an `artifact_kind` param (`"report"` default for back-compat; `"authored"` selects `authored_root` + `surface_type="article"`). All existing report callers unchanged (they pass nothing). Added the `authored_*` conventions family (`authored_root` / `authored_content_path` / `authored_profile_path` / `authored_dated_folder` / `authored_sections_dir` / `authored_sys_manifest_path` / `authored_manifest_path`) mirroring `report_*`, exported in `__all__`. (`api/services/compose/task_html.py`, `api/services/conventions.py`.)
2. **D2** — `_maybe_auto_compose` (~150 LOC) **deleted entirely** from `wake.py` — Singular Implementation favored full removal over a no-op stub, since its whole reason for existing (eager render + idempotency-probe against its own `output.html`) vanishes under the pull model. The session-close call site, the `composed_html_path` result field, and the auto-compose section header are gone. Verified no live consumer reads a pre-existing `output.html` (the only production reader was `_maybe_auto_compose`'s own idempotency probe; `delivery.py` already documents "no pre-rendered output.html exists in the workspace"). (`api/services/wake.py`.)
3. **D6** — new kernel route `routes/authored.py` mounted at `/api/authored/*` — `GET /{slug}` (prose + profile + latest-composition pointer), `GET /{slug}/render` + `/render/{date}` (lazy compose pull, `artifact_kind="authored"`), `GET /{slug}/export`. A kernel route (authored pieces are a kernel deliverable kind), not bundle program data. Delivery-of-authored-pieces (email) deferred per D8 — reuses the same root-agnostic composer when an author program connects publishing capabilities. (`api/routes/authored.py`, `api/main.py`.)
4. **Regression gate** — `api/test_adr333_compose_projection.py` (9 tests): composer is root-agnostic; `_maybe_auto_compose` + `composed_html_path` absent from `wake.py`; the dispatch path imports no compose helper; `authored_*` conventions exist + exported; authored route mounted with the four pull endpoints. Updated the stale ADR-262 D4 present-assertion in `test_adr261_phaseB.py` to an absent-assertion (added `assert_attr_absent` helper).
5. **Docs** — this ADR marked Implemented; CHANGELOG entry `[2026.06.10.N]`; `conventions.py` `__all__` updated; cross-references added in ADR-213 + ADR-262 D4 + ADR-283.

## 7. Open question resolved at sign-off

**Any eager-render consumer that breaks under D2?** Verified at proposal-time: the three report pull surfaces compose on demand; confirm no FE/delivery path reads a pre-existing `output.html` file directly (without going through `compose_task_output_html`) before deletion. The implementation gate (step 4) asserts this.
