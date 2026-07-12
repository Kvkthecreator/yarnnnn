# ADR-447 — The arrangement layer: composition as a first-class, per-type, nested grammar

> **Status**: **Proposed** (2026-07-12, doc-first — awaiting operator ratification; NO code this
> commit). The operator, from the Word / PowerPoint / Wix galleries, named a missing *fundamental*
> layer and scoped it precisely: not the design system (palette/type/mood — a separate decision),
> but the **spatial-composition layer** — page/slide masters, sections, grids, overlays, sizings —
> at **both the whole-page and the sub-region grain, nested**. This ADR promotes the Studio's
> deck-only `STUDIO_CONTAINERS` (ADR-444's slide masters) to a first-class **arrangement** layer:
> per-document-type, nested (page → section → slot), kernel-seeded, applied as the same free
> CAS-guarded mechanical reflow that already moves blocks between slots. Derivation:
> `docs/analysis/the-composition-layer-arrangements-as-a-first-class-grammar-2026-07-12.md`. Living
> design doc: `docs/design/STUDIO.md`.

**Date**: 2026-07-12
**Dimension**: Substrate (Axiom 1 — the artifact carries its own composition semantics as
`data-*` annotations) + Channel (the Arrange affordance) + Mechanism (the reflow is deterministic;
the lane still authors content).

**Amends**: ADR-443 (adds a fourth layer to the axiomatic model beside layouts; the seven
operations are unchanged — arrangement is a facet of TRANSFORM/COMPOSE, not an eighth op) ·
ADR-444 (`STUDIO_CONTAINERS` → `STUDIO_ARRANGEMENTS`, generalized from deck-only slide masters to
per-type nested arrangements; the container reflow becomes the arrangement reflow) · ADR-446 (the
heading-block reflow guard generalizes to slot-fill discipline).
**Preserves**: the DOM is the model / no shadow layer (ADR-443 R1) · grammar-not-schema (R4) ·
Studio authors one type (R5) · the ONE mechanical write door + CAS + free-no-LLM (ADR-444/396) ·
block ids preserved across a reflow (ADR-446) · no widget ABI (arrangements are semantic HTML +
grid CSS, never embedded editors).

---

## D1 — Arrangement is the Studio's fourth fundamental layer

The Studio composes an artifact from four orthogonal layers. Three exist; this ADR promotes the
fourth from a deck-only afterthought:

| Layer | Answers | Annotation |
|---|---|---|
| **Layout** | what kind of artifact | `data-template` (document/deck/article) |
| **Arrangement** *(this ADR)* | **where content goes on a page/section** | `data-arrange` + `data-slot` |
| **Block** | what a content unit is | `data-block` + `data-block-id` |
| **Skin** | how it looks (design system) | `<style>` — **out of scope** (a separate decision) |

Arrangement answers exactly one question — *where do things go* (grids, slots, overlays, sizings) —
orthogonal to *what the content is* (block) and *how it looks* (skin). A "Two Content" slide and a
"Comparison" slide differ only in arrangement, identically themed and blocked.

## D2 — The nested slot model (page → section → slot → block)

An arrangement is a **recursive tree of slots**:

- A **page/slide** carries a page-grain arrangement (`data-arrange="comparison"` on
  `<section class="slide">` | `<main>` | `<article>`) declaring its top-level `[data-slot]` regions.
- A page may **contain section-grain bands** in its flow (`data-arrange="two-column"` on a `<div>`),
  and a section band's slots may themselves hold sub-bands — the recursion (the Wix section-stack).
- **Blocks fill slots**; slots may hold sub-arrangement bands. `data-slot="main|left|right|media|…"`.
- **Grid / overlay / sizing** is CSS in the arrangement's skin fragment (`display:grid`,
  positioned overlay slots, `aspect-ratio` media slots) — HTML-native, no layout DSL, no JSON tree
  (R1 preserved). "Both, nested" (the operator's choice) is the minimal model covering the
  PowerPoint page grain AND the Wix section grain with one recursion.

## D3 — `STUDIO_ARRANGEMENTS`: the kernel-seeded, per-type registry

`STUDIO_CONTAINERS` is renamed and generalized to `STUDIO_ARRANGEMENTS`, keyed by layout-type,
each row `{slug, label, description, grain: 'page'|'section', slots, skin (grid CSS), fragment}`.

- The deck's existing `title/content/two-column/quote` become the deck's **page** arrangements
  (byte-compatible — same fragments, richer metadata).
- **Section-grain** arrangements are cross-type: `two-column`, `three-grid`, `image-overlay`,
  `sidebar`, `full-bleed-band`.
- **document/article gain page arrangements** (today's empty rows fill).
- Served via `GET /studio/vocabulary` (already carries `containers`). Grammar not schema (R4): an
  unknown `data-arrange` renders as generic flow; the trace witnesses, nothing policies.

## D4 — Applying an arrangement is the existing mechanical reflow, generalized

Re-arranging is a deterministic FE DOM transform landed through the ONE mechanical write door
(`POST /studio/artifacts/write`, CAS, `authored_by="operator"`, free) — the ADR-444/446 path,
unchanged. The reflow that today moves a slide's blocks into a container's first slot
(`applySlideLayout`) is generalized: blocks move INTACT into the target arrangement's slots (ids
preserved, ADR-446), heading blocks anchor rather than flow (the ADR-446 guard, generalized to
per-slot fill rules). **Zero new write machinery, no schema, no new meter, no new principal.**
Switching an arrangement is an attributed revision — `trace` shows blocks moving between slots, a
compositional history no benchmark competitor has.

## D5 — The chrome: "Arrange" (operator word, ADR-443 D3)

The deck-only "Slide" toolbar menu generalizes to **"Arrange"**: for the whole canvas it offers
page arrangements (the PowerPoint New-Slide grain); at a selection it offers section bands to drop
in. Same executor (`applyOp` + reflow). The seven operations are unchanged — "Arrange" is TRANSFORM
(re-lay) + COMPOSE (drop a band), surfaced in one operator word. A template becomes
**layout × page-arrangement × starter blocks** (`build_skeleton` composes from the arrangement row).

## D6 — Scope: v1 spine ships / deferred

**v1 spine (the implementation this ADR authorizes once ratified)**: `STUDIO_ARRANGEMENTS`
generalized + page-grain arrangements across all three types (the PowerPoint parity cut) + the
"Arrange" menu + `build_skeleton` from arrangement rows + the served vocabulary + the gate.

**Phase 2 (deferred)**: sub-region section-band nesting (the reflow targets a *selected slot*, not
just the page's first slot — a modest change; selection already reports `blockId`, add
slot-awareness) + the richer cross-type section-band set.

**Out of scope (named so it never re-litigates)**: the design-system/skin layer (palette, type,
mood — a separate ADR when demanded; the operator scoped it out) · responsive breakpoints
(v1 arrangements are fixed like today's deck) · a widget/plugin ABI (R5 — arrangements are
semantic HTML + grid CSS) · a JSON layout model (R1 — the DOM is the model).

## Consequences

- **Positive**: the composition layer becomes first-class and per-type; PowerPoint's slide-master
  grain and Wix's section-stack grain unify as one nested grammar; document/article gain real
  layouts; re-arranging is a traceable, id-preserving, free revision; the manifesto's
  "object-processing system" ambition gains its spatial dimension without a design-system decision,
  a layout DSL, or a widget platform.
- **Cost**: the *mechanism* is small (generalize one reflow, rename+extend one registry, extend one
  served endpoint, rename one menu); the *content* is craft (designing good arrangements per type,
  phased). Sub-region nesting is a phase-2 slot-selection change.
- **Risk**: low — additive annotations (un-arranged artifacts stay valid); the deck migration is
  byte-compatible; no schema/migration; reuses the CAS write door.

## The one-line statement

**Arrangement is the Studio's fourth layer: a per-document-type, nested tree of slots
(page → section → slot) that says where content goes — grids, bands, overlays, sizings — as
`data-arrange` + `data-slot` + grid CSS on real HTML (the DOM is still the model), kernel-seeded
grammar that teaches without validating, applied as the same free CAS-guarded reflow that already
moves blocks between slots today; PowerPoint's New-Slide grain and Wix's section-stack grain become
one recursion, and re-arranging a page is an attributed, id-preserving revision that gives
composition a trace no competitor has.**
