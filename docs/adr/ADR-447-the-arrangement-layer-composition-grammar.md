# ADR-447 — The arrangement layer: composition as a first-class, per-type, nested grammar

> **Amended by [ADR-481](ADR-481-the-flow-chrome-rebuild-a-blank-document-is-a-blank-page.md) D1**
> (2026-07-22): arrangements become **`paged`-only**. The registry's `document` and `article`
> rows are DELETED and their scaffolds go flat. The grammar below is unchanged wherever a
> page-grain unit actually exists (`deck`, `page`) — what ADR-481 denies is that a FLOWING
> document has such a unit. Evidence: across all 4 live flow artifacts every arrangement was
> the scaffold's own and **zero** were member-authored, while the scaffold's own
> `<section data-arrange>` wrapping an empty `<div data-slot>` rendered as a dead vertical
> void (a slot is a PowerPoint placeholder / Wix band region — a paged concept). Two columns
> inside a document would be a **block kind**, not a page arrangement.

> **Amended by ADR-455** (2026-07-13): the D7.2 navigator becomes **collapsible** (toolbar
> toggle) and the document/article outline becomes **navigational** (click a heading → select
> its block + scroll the canvas, via the D7.7 scroll bridge generalized to
> `yarnnn-scroll-to-block`).

> **Amended by ADR-453** (2026-07-13): D7.2's "no inspector column" is revised — the inspector
> returns as the right column's **Design tab** (Chat | Design; never a fourth column) because the
> ratified scope grew to property editing; D7.1's derived wireframe thumbnails land (the New
> ‹slide|section› flyout + the Design tab's Re-arrange gallery); D5's single "Arrange" operator
> word splits by grain into **New ‹slide|section›** / **Re-arrange**; the registry becomes the
> canvas's INTERACTION CONTRACT (slot roles gate adds; slots outline + select; the click-grain
> ladder block → slot → page un-defers D7.3's drill in its minimal form).

> **Status**: **Accepted** (2026-07-12, operator-ratified — "the model holds"; the operator then
> widened v1 to include the **front-end UX** (D7). Doc-first; implementation delegated as ADR-447
> v1 = model + UX together). The operator, from the Word / PowerPoint / Wix galleries, named a
> missing *fundamental* layer and scoped it precisely: not the design system (palette/type/mood —
> a separate decision), but the **spatial-composition layer** — page/slide masters, sections,
> grids, overlays, sizings — at **both the whole-page and the sub-region grain, nested**. This ADR
> promotes the Studio's deck-only `STUDIO_CONTAINERS` (ADR-444's slide masters) to a first-class
> **arrangement** layer: per-document-type, nested (page → section → slot), kernel-seeded, applied
> as the same free CAS-guarded mechanical reflow that already moves blocks between slots — AND
> restructures the workbench UX so composition is spatial (thumbnail pickers, a right-side
> inspector, click-to-drill, empty-slot affordances). Derivation:
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
| **Skin** | how it looks (design system) | `<style>` — a **separate, complementary layer** (ADR-449 shipped it: a marked, cited `data-skin` style element); orthogonal to arrangement |

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

## D7 — The workbench UX: composition is spatial (operator-widened, 2026-07-12)

The operator widened v1 to make the composition UX itself first-class — "the toolbar is text-list
dropdowns, but composition is spatial." Four decisions:

- **D7.1 — Visual thumbnails, not text rows.** An arrangement picker renders a small **wireframe
  thumbnail** of the arrangement's slot shape (title bar, two columns, media region) — the
  PowerPoint New-Slide grain. The thumbnail is **derived from the arrangement's own `slots` + grid
  CSS** (a scaled structural render), NOT a hand-drawn asset — so adding an arrangement is still one
  registry row (grammar not schema, R4; the preview comes free). Blocks may stay text-labelled
  (a "callout" is known by name); arrangements are shown by shape.
- **D7.2 — Three columns: navigator · canvas · chat (operator-refined, 2026-07-12).** The
  workbench is three columns with distinct jobs: **navigator (left — a PER-TYPE navigator: a slide
  strip for a deck [PowerPoint's left thumbnails], an outline for a document/article)** · **canvas
  (center — see + touch/direct-manipulation), with the Add/Arrange toolbar over it** · **the bound
  chat LANE (right)**. The chat moved to the RIGHT because Freddie's floating rail is suppressed on
  the Studio surface (D7.6) — so the Studio's own chat owns the right edge and reads as the one chat
  affordance. The *compose* controls (arrangement thumbnails, selection actions) live in the toolbar
  (the "Arrange" menu, D5) rather than a fourth inspector column — a leaner realization of the
  Keynote model than the original "inspector on the right" sketch. **SHIPPED**, and the deck
  navigator renders **visual slide previews** (2026-07-13): the artifact is projected once (citations
  resolved, no runtime), each slide sliced into a scaled `sandbox=""` iframe — a real miniature of
  the slide, PowerPoint/Preview.app style. Honest ceiling: one preview iframe per slide, re-rendered
  on each edit (fine for normal decks; per-slide memoization is a later optimization if large decks
  feel slow). Arrangement-picker wireframe thumbnails (the *Arrange menu*, distinct from the
  navigator) still ride the remaining Phase-2 thumbnail work.
- **D7.3 — Double-click-to-edit + empty-slot affordances (Phase 4, SHIPPED 2026-07-13).** Two
  direct-manipulation gestures on the canvas: **(a) double-click a block to edit its text in place**
  — the natural gesture (every editor since 1984), replacing the toolbar's chip "Edit" button
  (deleted). The edit runtime enters edit mode itself on `dblclick` and posts `yarnnn-edit-entered`
  so the surface's `editingBlockId` stays in sync. **(b) empty slots render an on-canvas
  `+ Add here`** so the member sees where content goes; clicking posts `{slot, slideIndex}` and the
  surface inserts a text block into that slot (`insertBlockInSlot`). Both flow through the same free
  CAS door. **Click-to-drill across grains (block → slot → section → page) is DEFERRED to phase 2's
  section-band nesting** — until sections exist there is nothing between block and page to drill
  through; it ships when nesting does. Selection grain flows canvas→parent; actions flow
  parent→canvas — the established postMessage bridge (the runtime is the only code in the sandboxed
  opaque-origin frame).
- **D7.4 — Drag-and-drop is deferred.** Dragging a block into a slot across the sandboxed
  opaque-origin iframe is genuinely hard (HTML5 DnD does not cross the frame; it needs a
  pointer-event bridge). v1 composes by click-select + toolbar actions + (Phase 4) empty-slot add.
  DnD is phase 2+ if demand warrants.
- **D7.5 — The type-switcher ("Change layout") is DELETED (operator, 2026-07-12).** Morphing a whole
  artifact from a deck into a document (or vice versa) was a legacy misread — not an operation the
  member wants. The artifact's TYPE is fixed at creation; **composition happens WITHIN the type** via
  the Arrange menu (re-lay the current page/slide). The surface-bar "Change layout" action, its
  picker, and `switchLayout` are removed. (The `layouts` registry is still served — the creation
  picker uses it — but there is no in-artifact type switch.) **SHIPPED.**
- **D7.6 — Freddie's floating rail is suppressed on the Studio surface (operator, 2026-07-12).** Like
  `/chat`, the Studio owns a first-class chat (the bound lane, now the right column); the global
  Freddie summon FAB floating over it would read as two competing chat affordances. The existing
  ADR-412 own-chat carve (`Desktop.tsx`, `foregrounded === 'chat'`) generalizes to
  `foregrounded === 'chat' || 'studio'`. Freddie stays addressable from every other surface; only
  the redundant summon hides here. **SHIPPED.**
- **D7.7 — Navigator→canvas scroll, canvas zoom, and mobile (operator, 2026-07-13; SHIPPED).**
  (a) **Selecting a slide in the navigator scrolls the center canvas to it** — the pointer runtime
  handles `yarnnn-scroll-to-slide` and `scrollIntoView`s the Nth slide (the earlier navigator only
  set the Arrange anchor; it didn't move the display). (b) **Canvas zoom is a VIEW control** — a
  −/%/+ control commands `yarnnn-zoom` and the runtime sets `document.body.style.zoom`; it scales
  the rendered document on screen and **never touches the file** (artifact dimensions are unchanged;
  aspect-ratio/page-width editing stays a separate later thing). (c) **Mobile** — below the `md`
  breakpoint the three columns collapse to **one pane at a time** (nav · canvas · chat) switched by
  a bottom tab bar; the canvas is primary (selecting a slide jumps to it). The Canva/Keynote-mobile
  pattern: canvas-first, navigator + chat as summonable panes.
- **D7.7 fixes (2026-07-13, same-day):** first-use surfaced two regressions. (i) **Slide shape** —
  the deck slide skin was `min-height: 92vh` (portrait/tall), so slides AND their previews looked
  letter-size, not landscape. The skin is now a fixed **landscape 16:9** page (`aspect-ratio: 16/9`,
  centered, boxed), and the navigator thumbnail renders the same markup at a 16:9 box — previews are
  no longer distorted. (ii) **Blank canvas after an edit** — the projection effect keyed on the
  whole `file` object, which `useFileLoad` returns fresh on every reload even when the content is
  byte-identical, needlessly reloading the iframe and flashing it blank; it now keys on
  `file.content`. (The content was verified valid in the DB — not a data corruption; the compact
  16:9 slide + the edit runtime's focus-scroll-into-view keep the edited slide visible after a
  reload.)

The mutation contract is unchanged: every compositional act (re-lay, add band, fill slot) is a
deterministic reflow through the ONE mechanical write door (ADR-444/446), free, CAS-guarded,
id-preserving. The UX makes composition *legible and direct*; it adds no write path.

## D6 — Scope: v1 ships / deferred

**v1 (the implementation this ADR authorizes — MODEL + UX together, per the operator's widening)**:
- **Model**: `STUDIO_ARRANGEMENTS` generalized + **page-grain** arrangements across all three types
  (the PowerPoint parity cut) + `build_skeleton` from arrangement rows + the served vocabulary
  (with derived thumbnails) + the reflow generalized from `applySlideLayout`.
- **UX**: the three-column workbench (lane · canvas · inspector) + thumbnail arrangement picker +
  the contextual inspector (outline folded in) + click-to-drill grain navigation + breadcrumb +
  empty-slot `+ Add here` + the "Arrange" operator word replacing the deck-only "Slide" menu.
- **The gate** covers both (registry/reflow shape + the FE UX receipts).

**Phase 2 (deferred)**: sub-region **section-band nesting** (the reflow targets a *selected slot*,
not just the page's first slot — a modest change; selection already reports `blockId`/grain) + the
richer cross-type section-band set + **drag-and-drop** into slots (the iframe pointer-bridge).

**Out of scope (named so it never re-litigates)**: the design-system/skin layer (palette, type,
mood — the operator scoped it out; a **complementary** layer, now shipped by ADR-449 as a marked
`data-skin` cited style element — orthogonal to arrangement: Skin is *how it looks*, Arrangement is
*where content goes*) · responsive breakpoints
(v1 arrangements are fixed like today's deck) · a widget/plugin ABI (R5 — arrangements are
semantic HTML + grid CSS) · a JSON layout model (R1 — the DOM is the model).

## Consequences

- **Positive**: the composition layer becomes first-class and per-type; PowerPoint's slide-master
  grain and Wix's section-stack grain unify as one nested grammar; document/article gain real
  layouts; re-arranging is a traceable, id-preserving, free revision; the workbench becomes a
  coherent three-column story (*think · see/touch · compose*) where composition is spatial and
  direct; the manifesto's "object-processing system" ambition gains its spatial dimension without a
  design-system decision, a layout DSL, or a widget platform.
- **Cost**: the model *mechanism* is small (generalize one reflow, rename+extend one registry,
  extend one served endpoint); the *UX* is a real workbench restructure (the inspector, thumbnail
  pickers, click-to-drill, empty-slot affordances — the largest FE lift since the Studio shipped);
  the *content* is craft (designing good arrangements per type, phased). Thumbnails derive from
  arrangement data (no per-arrangement asset work).
- **Risk**: low-moderate — model side is additive (un-arranged artifacts stay valid; deck migration
  byte-compatible; no schema; reuses the CAS door); UX side carries the postMessage-sync complexity
  between the inspector and the sandboxed canvas runtime (the established bridge, now bidirectional
  for selection-grain + actions) — the one place to get right.

## The one-line statement

**Arrangement is the Studio's fourth layer: a per-document-type, nested tree of slots
(page → section → slot) that says where content goes — grids, bands, overlays, sizings — as
`data-arrange` + `data-slot` + grid CSS on real HTML (the DOM is still the model), kernel-seeded
grammar that teaches without validating, applied as the same free CAS-guarded reflow that already
moves blocks between slots today; PowerPoint's New-Slide grain and Wix's section-stack grain become
one recursion, re-arranging a page is an attributed, id-preserving revision that gives composition
a trace no competitor has — and because composition is spatial, v1 restructures the workbench into
three jobs (lane thinks · canvas shows and is touched · a right-side inspector composes) with
shape-showing thumbnail pickers, click-to-drill grain navigation, and empty-slot affordances, so
the member sees where content goes and puts it there directly.**
