# ADR-466 — The mode-native carve: one grammar, N native editors

- **Status**: Accepted (2026-07-20, operator-ratified — "fully aligned on the assessment,
  proposed carve and approach"; implementation delegated in full). Phase statuses tracked in §6.
- **Date**: 2026-07-20
- **Dimension**: Channel (primary — how the member shapes, per document type). No new
  substrate, no new write path, no schema.
- **Derivation**: [the mode-native carve discourse](../analysis/the-studio-mode-native-carve-2026-07-20.md)
- **Amends**:
  - **ADR-453 D4/D5** — the one scope-switching inspector and the one click-grain ladder
    become **mode-scoped**: the ladder's grains and the inspector's leading sections differ
    by the layout's `mode`. The inspector itself, the token model, and the one-home rule
    are preserved.
  - **ADR-458** — the hover gutter + slash layer is recognized as **flow chrome**, primary
    on `flow` layouts, secondary on `paged` (the selection box leads there).
  - **STUDIO.md** — gains the per-mode interaction contracts; `Media ▾` retires per the
    named follow-on ("when the palette can host a picker, the button retires").
- **Preserves**: ADR-443 R1 (the DOM is the model; the block grammar is UNTOUCHED — it is
  the attribution grain and the trace join key, and this ADR explicitly declines the
  "revert the block model" option in favor of carving the chrome) · ADR-444/446 (two write
  paths, one door — no gesture in this ADR is a new write path) · ADR-461 (the geometry
  seam is this carve's spine; D3's bounded-continuous authorization is *enacted*, not
  widened) · ADR-456 stop-lines (no per-breakpoint editing, no second source format) ·
  ADR-406/286 (the revision is the atom; no CRDT) · ADR-417 (no owned render engine —
  export is a projection, never a generator).

---

## 1. Context

Studio shipped mechanism-first across ~20 ADRs — each sound, each canon-clean — but the
chrome stayed generic across document types: one selection ladder, one Properties panel,
one toolbar, one interaction model for deck, document, article, page. The canon had
already drawn the two seams that make types feel native — the **mode seam**
(`paged`/`flow`, the layout registry) and the **geometry seam** (ADR-461: a slide has a
frame, a page has a viewport) — and the FE never enacted them. The result the operator
named: every mechanism present, no document type native; the whole reads as a latch-on.

The ruling: **one shared substrate grammar, N mode-native editors over it.** The block
model is not reverted; the chrome uniformity is.

## 2. Decisions

### D1 — The experience contract is per-mode; the substrate grammar is shared

Three contracts, written into STUDIO.md as the interaction canon:

- **Deck — object-first (the PowerPoint contract).** Click selects an object and shows a
  **selection box with handles on the canvas**. Objects move and resize by direct drag
  *within the slide's 16:9 frame* (D2). The gutter/slash layer remains available for text
  entry but no longer leads. Properties leads with geometry, arrangement, and tone.
- **Flow (document, article) — caret-first (the Notion contract).** The caret, hover
  gutter, slash palette, and format bar ARE the grammar (as built). The click ladder
  **drops the slot and page grains** — a flowing document's margin selects nothing; block
  and document are the only scopes (D3). The inspector is the settings home, not the
  primary surface.
- **Page — band-first (the Wix contract).** The band (section) is the unit: band
  selection, band reordering, per-band background/tone — page-grain mechanisms applied to
  the band stack. Spatial freedom stays refused (a page has a viewport; ADR-461 D4's
  re-open conditions stand). Deep band **nesting** (section arrangements *inside* bands)
  remains the named phase-2 follow-on — this ADR ships the contract, not the nesting.

### D2 — The deck object layer: handles + drag-to-position, inside ADR-461's bound

ADR-461 D3 authorized bounded-continuous geometry where a frame exists; only the width
measure shipped. This ADR enacts the rest, same mechanism, same bound:

- **Selection box**: the selected block on a `paged` canvas renders a visible selection
  rectangle with corner/edge handles (projection-runtime chrome, never serialized).
- **Position**: dragging a selected block on a deck slide sets `data-pos="free"` +
  `--yx`/`--yy` (percent of the slide frame, clamped) — registry-declared **measures**
  (`STUDIO_MEASURES`), kernel CSS pre-declares ONE rule reading the vars
  (`.slide > [data-block][data-pos="free"] { position: absolute; … }`). The value rides
  the element; the selector set stays pre-declared — the ADR-461 invariant holds in
  substance.
- **Resize**: the corner grip drives both axes on framed blocks (`--yw` + `--yh`).
- **The honest remainder (priced by ADR-461 §D3)**: a freely-positioned block exits the
  arrangement's slot contract. It stays attributed, traced, and addressable by id; it
  stops participating in slot reflow. `Re-arrange` treats free blocks as carried content
  (they re-enter flow when an arrangement is applied — `data-pos` cleared, position
  measures dropped: applying an arrangement is an explicit re-flow act).
- **Scope guard**: position measures apply to `block-deck` ONLY. A `grep` showing a
  continuous position value admitted on `article`/`page`/`document` is a red build
  (extends the ADR-461 falsifier).

### D3 — The flow slimming: two grains, caret leads

On `flow` layouts the pointer runtime reports **block or nothing**; slot/page payloads are
not emitted (the mode is served with the vocabulary; the runtime receives it at projection
time). The Properties panel's flow scopes are document and block. Flow arrangements remain
insertable **as blocks** (per the mode row in STUDIO.md) — they are content bands in the
flow, not page units, so nothing is lost with the page grain.

### D4 — Insert is provenance-shaped, in the located palette; `Media ▾` retires

The located palette (gutter `+` / slash) becomes the ONE insert surface. It gains the
picker-backed kinds by **hosting the picker inline**: choosing Image/Table/Gallery swaps
the palette panel to the existing cited-file picker (same components, same citation
stamping); Chart keeps seeding the lane. With no orphan kinds left, **`Media ▾` is
deleted** (the STUDIO.md named follow-on, executed).

The palette's grammar is the provenance question the design-system modal taught ("where
does this come from?"): **from the workspace** (cite — the picker rows), **from thin air**
(the plain block kinds), **from inference** (rows that seed the bound lane — Chart today;
generalizing ADR-450 derive recipes to block grain is a named follow-on, not built here).

### D5 — Arrangement intelligence: pre-filter, resolve, map by role

- **Pre-filter**: the New/Re-arrange galleries know the current page's carried-block count
  and each arrangement's slots. An arrangement that cannot receive the page's content
  (slotless while content exists) renders **disabled with the reason inline** — the click
  that cannot succeed never happens. (New-page galleries never disable — a new page has no
  carried content.)
- **Refusal → resolution**: if the refusal is still reached (stale state), the error offers
  the mechanical resolution — *"Move this slide's content to a new Content slide after
  it"* — one compound op through the same door, never a dead-end banner.
- **Role-aware mapping**: `applyArrangement` maps carried blocks to slots by **role**
  first (media blocks → `media` slots, prose → `flow`), then by slot name, then first-slot
  fallback (the ADR-453 D7 fast-follow, executed).
- **Layout beside New**: on `paged` layouts the toolbar pairs **`New ‹slide|section› ▾`**
  with **`Layout ▾`** (re-arrange the CURRENT page) — the PowerPoint pair, one gallery
  component, two mounts. The Properties page scope keeps its Re-arrange section (the one
  settings home is not diminished; the toolbar is the discoverable mount).

### D6 — Export joins Share in the Properties document scope

- **Print/PDF**: an export is a **projection** (ADR-417 honored — no render engine): the
  resolved artifact HTML plus a print stylesheet (deck → one slide per page, landscape;
  flow → paginated), handed to the browser's print-to-PDF. No new service, no new format.
- **Copy AI reference**: copies the artifact's workspace path in a form any connected LLM
  can use through the interop face (recall/trace) — the AI-native share, complementing the
  `/s/{token}` grant link (ADR-437/465).
- **Markdown export stays ADR-456 Wave 4** (interchange at the boundary), **PPTX/DOCX stay
  refused** (either a betrayal of HTML-native or a rented boundary tool later).
- **ADR-465's genesis phases (join-only, the migration-106 retirement) are explicitly NOT
  ridden in this pass** — invariant-touching backend work ships as its own pass with its
  own gate.

### D7 — The fluidity floor (a budget, not a mechanism)

Declared as the standing bar every Studio change is held to:

1. A member act never visibly reloads the canvas (already true for writes; extended to
   every op).
2. Selection and scroll survive every write, including foreign ones.
3. **A 409 never loses typed text**: ops recompute against the fresh head and auto-retry
   once; a text edit that still conflicts is stashed and offered for one-click re-apply —
   never silently discarded.
4. The deck navigator's per-slide previews are memoized per slide (only the edited slide
   re-renders).

## 3. What this ADR does NOT do

- Does not touch the block grammar, the write door, attribution, or the registries'
  serving contract.
- Does not widen ADR-461 — position ships only where the frame already is (deck; media).
- Does not build page band **nesting** (named phase 2), block-grain derive recipes, md
  export (W4), or ADR-465 Phases B–F.
- Does not add a JSON layout tree, a coordinate model outside `data-*`/CSS vars, or a
  second write path. Gestures compose existing ops (ADR-461 D2).

## 4. Falsifiers

1. Every gesture lands as exactly one attributed revision through `POST
   /studio/artifacts/write`; no new write path appears.
2. Kernel CSS still pre-declares every selector it matches; position values ride elements.
3. `grep` shows no continuous position measure admitted on `article`/`page`/`document`.
4. The slotless-arrangement red banner is unreachable from a fresh gallery (pre-filter),
   and when reached offers a resolution.
5. A deliberately-provoked 409 during a text edit preserves the typed text.

## 5. Key files

FE: `web/components/studio/{StudioSurface,StudioToolbar,StudioDesignTab,StudioSlashPalette,StudioCanvas}.tsx`,
`web/components/studio/artifactOps.ts`, `web/components/workspace/viewers/projection.ts`.
API: `api/services/studio.py` (registries: measures, kernel CSS version bump; posture —
CHANGELOG entry per prompt protocol). Gate: `api/test_adr466_mode_native.py`.
Docs: this ADR · STUDIO.md (mode contracts) · the derivation analysis.

## 6. Phases (each its own commit)

| # | Phase | Workstream | Status |
|---|---|---|---|
| 1 | Docs — derivation + this ADR | — | **Done** (2026-07-20) |
| 2 | Arrangement intelligence (pre-filter · resolution · role mapping · Layout ▾) | C | **Done** (2026-07-20) — implementation refinement on D5: the gallery does not *disable* a slotless thumb; it forewarns (amber note) and the click performs the move-content resolution directly — never a disabled dead-end, never a post-hoc banner |
| 3 | Palette hosts pickers; `Media ▾` deleted | B/D4 | **Done** (2026-07-20) — StudioCitablePicker at the located point; the implicit caret-anchor mechanism (`lastCaretBlockId`/`insertAnchor`) retired with the last un-located insert |
| 4 | Flow slimming (two grains) | A/D3 | **Resolved by verification** (2026-07-20) — D3 as drafted over-reached: the ladder is ALREADY flow-native, because page grain exists only on `[data-arrange]` bands (a plain document's margin selects nothing — `PAGE_SEL` matches slides and arrangement bands only), and slot grain exists only inside an arrangement the member inserted, where its quick-add is legitimate. Suppressing those payloads would have removed the only way to re-arrange or verb a document's two-column band. The caret-first carve is carried by P3 (insert located with no exceptions) + the existing gutter/slash/format-bar grammar. No code shipped for theater |
| 5 | Deck object layer (selection box · drag-position · two-axis resize) | A/D2 | **Done** (2026-07-20), two honest narrowings: (a) the "selection box" is the existing neutral ADR-462 D5 outline *plus* the two grips (move `⠿` top-left, slide-only; resize corner) — no saturated rectangle was added; (b) resize keeps the **width axis** (ADR-461's "one gesture, one intent" note) — height stays registry-available, unwired. Position = `data-x`/`data-y` + `--yx`/`--yy` (kernel v10, one pre-declared rule, deck-only measures 0–95%); re-arrange + the Properties hatch return a positioned block to flow; the posture teaches geometry preservation (CHANGELOG 2026.07.20.1). Gate: `test_adr466_mode_native.py` 20/20 |
| 6 | Export group (print-PDF · AI reference) | D/D6 | Pending |
| 7 | Fluidity: courteous 409 + navigator memoization | E/D7 | Pending |

## 7. The one-line statement

**One substrate grammar — blocks, arrangements, tokens, one write door — carried by three
native editors: a deck you handle like objects in a frame, a document you write at the
caret, a page you stack as bands. The canon drew the seams; this ADR makes the chrome obey
them.**
