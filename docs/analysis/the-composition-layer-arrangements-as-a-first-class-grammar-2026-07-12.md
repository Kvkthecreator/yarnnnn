# The composition layer: arrangements as a first-class, per-type, nested grammar (2026-07-12)

> Derivation for ADR-447. The operator, looking at Word's New gallery, PowerPoint's New-Slide
> flyout, and Wix's template gallery, named a missing *fundamental* layer that "sets the tone for
> the fundamental way each page, slide, or block and thus sub-layouts are handled." On
> clarification he scoped it precisely: **not** the design-system layer (palette/type/mood — a
> separate architectural decision), but the **spatial-composition layer** — "closer to page
> layout, master-slides design… text overlays, sizings, grids or sections (title, subtitle,
> two-grid, three-grid)," operating at **both** the whole-page/slide grain AND the sub-region
> grain, **nested**. This doc works out that layer against yarnnn's HTML-native, DOM-is-the-model
> handling. Receipts under every load-bearing claim.

---

## 1. What the three screenshots share (and what they don't)

- **Word New gallery** — finished-artifact starting points (Resume, Report, Calendar). A
  *template gallery* over the other layers; not itself a new axis.
- **PowerPoint New-Slide flyout (Facet theme)** — *Title Slide · Title+Content · Section Header ·
  Two Content · Comparison · Title Only · Blank · Content-with-Caption · Picture-with-Caption ·
  Title-and-Caption · Quote-with · Name Card*. **This is the purest reference.** Each is a
  **spatial arrangement of slots** — where the title goes, whether there are one/two/three content
  regions, whether a picture leads. All share one theme; the theme is the tone, the arrangement is
  the *composition*. They are orthogonal.
- **Wix gallery (Cafe, Chef, Pub, VOID)** — whole-site *design systems* (the scoped-out layer)
  **plus** section-stack composition (hero band, two-column band, image-overlay band) — the
  sub-region grain.

The operator's correction is decisive: **the commonality is the composition/arrangement grammar,
NOT the design system.** A "Two Content" slide and a "Comparison" slide differ in *arrangement*,
identically themed. A Wix page is a *stack of arranged section bands*, independent of the palette.
So the layer we are promoting answers one question: **where do things go on this page/section** —
grids, slots, overlays, sizings — separate from *what* the content is (blocks) and *how* it looks
(skin).

## 2. The four-layer model (three exist; the fourth is being promoted)

yarnnn's Studio already has three orthogonal layers. The fourth — **arrangement** — exists today
only as a deck-only afterthought.

| Layer | Answers | Grain | Annotation | Today (receipts) |
|---|---|---|---|---|
| **Layout** | What *kind* of artifact? | whole artifact | `data-template` | ✅ `STUDIO_LAYOUTS` document/deck/article (`services/studio.py:131`) |
| **Arrangement** | *Where do things go* on this page/section? | **page → section → slot (nested)** | `data-arrange` (new) / today `data-container` | ⚠️ `STUDIO_CONTAINERS`, deck-only (`document:{}`,`article:{}` empty), 4 rows, framed as "slide masters" (`services/studio.py:229`) |
| **Block** | What *is* this content unit? | one content unit | `data-block` + `data-block-id` | ✅ `STUDIO_BLOCKS` 8 kinds + `heading` (`services/studio.py:48`) |
| **Skin** | How does it *look*? | whole artifact | `<style>` in the file | design-system layer — **out of scope** (operator's call, §1) |

**The claim**: arrangement is not a new *concept* to invent — it is `STUDIO_CONTAINERS`
**promoted** from a deck-specific, thin, mis-framed afterthought to the first-class,
per-document-type, nested composition grammar that sets the spatial tone of every page and section.
The mechanism already exists in embryo (§4); what's missing is the *framing*, the *per-type
generality*, the *nesting*, and a *richer arrangement set*.

## 3. The nesting model (the load-bearing idea)

An **arrangement is a recursive tree of slots**:

```
PAGE arrangement       data-arrange on <section class="slide"> | <main> | <article>
  └─ SECTION arrangement   data-arrange on a <div> band dropped into the page flow
       └─ SLOT               data-slot="main" | "left" | "right" | "media" | "aside"
            └─ BLOCK           data-block="prose|figure|metrics|heading|…" (+ id)
```

- A **page/slide** carries a page-grain arrangement (`data-arrange="comparison"`) declaring its
  top-level slots. PowerPoint's flyout = the page-grain set.
- A page may **contain section-grain bands** mid-flow (`data-arrange="two-column"` on a `<div>`) —
  the Wix stack. Bands nest inside the page's flow (or inside a page slot).
- Every arrangement declares its **slots**; **blocks fill slots**; **slots may hold sub-arrangement
  bands** (the recursion).
- **Grid / overlay / sizing** is expressed as CSS in the arrangement's own skin fragment
  (`display:grid; grid-template-columns:…`, absolute-positioned overlay slots, `aspect-ratio`
  media slots) — HTML-native, no layout DSL.

**Why nested and not flat**: the operator chose "both, nested." A flat page-only model can't
express a two-column band *inside* a title-and-content slide; a flat section-only model can't
express "this whole slide is a Comparison." The nested tree is the minimal model that covers both
the PowerPoint grain (page arrangement) and the Wix grain (section band) with one recursion.

## 4. Why this is HTML-native + yarnnn-specific (the mechanism already exists)

1. **The DOM stays the model (ADR-443 R1).** An arrangement is `data-arrange` + `data-slot`
   annotations + CSS grid in the skin — pure annotations on real HTML. No JSON layout tree, no
   shadow model, no second source of truth. This is the same discipline that makes blocks work.
2. **Kernel-seeded grammar, served, teaches-not-validates (ADR-443 R4).** `STUDIO_ARRANGEMENTS`
   sits beside `STUDIO_BLOCKS`/`STUDIO_LAYOUTS`. Served via `GET /studio/vocabulary` (which already
   serves `containers`, `services/studio.py:104`). An unknown arrangement renders as generic flow;
   the trace witnesses, nothing polices. Growth = a row.
3. **Applying/switching an arrangement is a mechanical TRANSFORM (ADR-444 + ADR-446).** The reflow
   already exists: `applySlideLayout` moves every `[data-block]` intact into the new arrangement's
   `[data-slot]`, ids preserved, and lands ONE CAS-guarded operator revision through the write door
   (`artifactOps.ts:135-154`; the door `POST /studio/artifacts/write`, `routes/studio.py:121`).
   Generalizing "slide master" → "arrangement" is generalizing THIS one function; the write
   machinery is unchanged (free, ADR-396).
4. **`data-slot` + `data-container` are already the seed** (`artifactOps.ts:59,108,147`). The reflow
   targets `slide.querySelector('[data-slot]')` today; the generalization is (a) target a *selected*
   slot for nesting, (b) key arrangements by type, (c) fill the empty `document`/`article` rows.
5. **The trace differentiator carries over.** Because blocks keep their ids across a
   re-arrangement, `trace` shows "moved block b7 from slot `main`→`left`" — a *compositional*
   history no benchmark competitor (PowerPoint, Wix, Claude Design) has. Re-arranging is an
   attributed revision, not a destructive re-layout.

## 5. What changes structurally (the shape, not the code — code is ADR-447's implementation)

- **`STUDIO_CONTAINERS` → `STUDIO_ARRANGEMENTS`**, generalized: keyed by layout-type, each row
  `{slug, label, description, grain: 'page'|'section', slots: [...], skin (grid CSS), fragment}`.
  The deck's existing `title/content/two-column/quote` become the deck's *page* arrangements
  (byte-compatible migration — same fragments, richer metadata).
- **Section-grain arrangements** (available across types): `two-column`, `three-grid`,
  `image-overlay`, `sidebar`, `full-bleed-band`. Dropped into a page flow or a page slot.
- **Document/article gain page arrangements** (the empty rows fill): document → `title+lede`,
  `two-column`, `hero`; article → `title-block`, `lead-image`, `pull-quote-aside`.
- **The toolbar's deck-only "Slide" menu generalizes to "Arrange"** — page arrangements for the
  whole canvas + section bands to drop at the selection. Same executor (`applyOp` + reflow); the
  operator word is **"Arrange"** (or "Layout of this slide/section"), per ADR-443 D3.
- **A template becomes `layout × page-arrangement × starter blocks`** — the PowerPoint New-Slide
  gallery and richer starting points fall out; `build_skeleton` composes from the arrangement row.
- **Block-fill discipline**: the heading-block reflow guard from ADR-446 (`artifactOps.ts:188` —
  headings don't sweep into a slot) generalizes: an arrangement declares which slots accept flowed
  content vs which carry structural headings.

## 6. Scope boundary + honest cost

- **The mechanism is small**: generalize one reflow function, rename+extend one registry, extend
  `GET /studio/vocabulary` (already serves containers), rename one toolbar menu. Reuses the ADR-446
  write door verbatim.
- **The content is the real work**: designing ~6–10 good arrangements per type with honest grid
  CSS is craft, phased. v1 spine = page-grain across all three types (the PowerPoint parity cut);
  **sub-region section-band nesting is phase 2** (needs the reflow to target a *selected slot*, a
  modest change — selection already reports `blockId`, we add slot-awareness).
- **What this is NOT**: not the design system (palette/type/mood — separate ADR when demanded); not
  responsive breakpoints (a later concern — v1 arrangements are print/screen-fixed like the current
  deck); not a widget ABI (ADR-443 R5 — arrangements are semantic HTML + grid CSS, never embedded
  editors); not a JSON layout model (R1 — the DOM is the model).

## 7. The canon this touches (doc-first, ADR-447)

- **ADR-443** — adds a fourth layer to the axiomatic model (the seven operations are unchanged;
  arrangement is a *dimension of TRANSFORM/COMPOSE*, not an eighth operation). D5 (layouts) gains a
  sibling: arrangements. The DOM-is-the-model (R1) + grammar-not-schema (R4) refinements extend
  verbatim to `data-arrange`.
- **ADR-444** — `STUDIO_CONTAINERS` (the slide-master grain) is *renamed and generalized* to
  `STUDIO_ARRANGEMENTS` (per-type, nested). The container reflow becomes the arrangement reflow.
  The deck-only framing is superseded; the mechanism is preserved.
- **ADR-446** — the heading-block reflow guard generalizes to slot-fill discipline; direct editing
  is unaffected (blocks still edit in place regardless of which slot they sit in).
- **STUDIO.md** — the operator-word table gains "Arrange"; the four-layer model is documented.

## The one-line statement

**The Studio's fourth fundamental layer is the arrangement: a per-document-type, nested tree of
slots (page → section → slot) that says where content goes — grids, bands, overlays, sizings —
expressed as `data-arrange` + `data-slot` + grid CSS on real HTML (the DOM is still the model),
seeded as kernel grammar that teaches without validating, applied as the same free CAS-guarded
mechanical reflow that already moves blocks between slots today — so PowerPoint's New-Slide grain
and Wix's section-stack grain are one recursion, and re-arranging a page is an attributed revision
that keeps every block's id, giving composition a trace no competitor has.**
