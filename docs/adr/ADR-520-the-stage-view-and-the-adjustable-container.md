# ADR-520 — The stage view, the adjustable container, and the pane as the structure's home

- **Status**: **Accepted** (2026-08-05, operator-directed — live-use friction on a real
  deck, four named asks: *"the slides in more continuous view is confusing — I'd like
  the view to be per slide … the main container is still unadjustable. it should be …
  benchmark Figma even further, from the buttons thumbnails to details per type … the
  fourth within-slides preview hierarchy needs to be absorbed within the properties —
  find the right way"*. Design delegated.)
- **Date**: 2026-08-05
- **Dimension**: Studio canvas view + geometry grain + Design tab presentation. No
  schema change, no new op — every affordance is an existing op reached through a new
  grain or a new presentation (ADR-462 D1 holds).
- **Amends / supersedes**:
  - **ADR-516 D7 (amended)** — "no container measures" is **narrowed to unstaged
    containers**. A structural container on a deck stage becomes measurable (D2
    below); D5's handle-less box was the honest chrome for a grain with no gestures —
    the grain now has one, so the chrome gains exactly that gesture's handles.
  - **ADR-516 D5 (scoped)** — the static container box survives off-stage (web bands,
    unstaged containers); on the stage it becomes the resize variant (handles, still
    no move band — move stays reorder-shaped, Phase 3).
  - **ADR-519 D3/D5 (extended)** — the pane's Identity section grows the structure
    affordances (D4); Phase C's "numeric X/Y/W/H entry" lands here (D3), accelerated
    by the operator's ask.
  - **ADR-511 D3 navigator clause (superseded in part)** — "the navigator grows the
    structure tree" is withdrawn: the structure tree's home moves to the pane; the
    navigator demotes to the sequence filmstrip (D4). One home per fact.
  - **ADR-447 canvas commands (extended)** — the view-command channel gains the
    single-slide regime (D1); zoom's "view state, never the file" rule governs it.

---

## 1. Context

The operator worked a real deck in prod (post ADR-519 Phase A) and hit four walls:

1. **The continuous slide scroll reads as one long page.** Every reference tool
   (PowerPoint, Keynote, Figma slides, Claude Design) shows a deck as ONE slide on a
   stage with a filmstrip for sequence — the stage IS the edit surface; the scroll is
   a document idiom leaking into a staged medium. ADR-505 D1 already named the deck
   the only staged medium; the canvas never followed.
2. **The slide's main container cannot be adjusted.** ADR-511/516 made containers
   selectable with layout presets, but geometry was refused (ADR-516 D7) — so the
   region that visually dominates the slide answers a resize intent with nothing.
   The refusal predates the operator's live friction; the machinery (two-clamp
   measures, frame-relative resize, id-addressed ops) needs no extension — the kernel
   CSS (`.slide [data-w]`) already styles any staged element, and every geometry op
   resolves by id (ADR-511 D5).
3. **The pane's controls are text chips where the benchmark is glanceable.** Figma's
   inspector speaks icon rows (alignment glyphs), numeric fields (X/Y/W/H), and
   per-type detail sections. Ours renders preset text chips and read-only numbers.
4. **The within-slide hierarchy lives in the wrong home.** The navigator's per-page
   structure tree (ADR-511 D3) buries the 4th grain in the sequence rail; the
   operator reads structure while INSPECTING, not while sequencing.

## 2. Decisions

### D1 — The stage view: a deck shows one slide

The deck canvas renders **one slide at a time** — the stage. Mechanism: a view
command (`yarnnn-view-slide`, the ADR-447 channel) toggles a runtime class regime
(`body.yarnnn-stage` + `.yarnnn-current` on the shown slide); pure view state, like
zoom — never serialized, never in the artifact. The surface owns the current index
(it already tracks `selection.slideIndex` and the navigator's active card):

- Navigator card click = show that slide. New slide / duplicate / re-arrange land on
  the stage showing the affected slide. Cross-slide ops (breadcrumb, scroll-to-block)
  switch the stage first.
- Prev/next: on-canvas edge affordances + PgUp/PgDn; the filmstrip remains the
  primary sequence surface.
- **Web stays continuous** — bands are a scroll medium (ADR-505: viewport, not
  stage); **document (Docs) is untouched** (flow has no page unit).
- Scroll-pos restore simplifies on deck to "restore the shown slide index" (the
  anchoring unit the restore machinery already prefers).

### D2 — The staged container is adjustable: measures at the container grain

`isMeasurable` extends: a **structural container inside a `.slide`** is measurable —
w/h only. Its frame is the nearest ancestor container, else the slide (the existing
`measurableFrame` walk, which already resolves ancestors correctly). Consequences,
all mechanical:

- The container's selection box on the stage gains the eight resize handles; the
  move band stays absent (drag = reorder remains the Phase-3 declared cell; a
  container is flow structure, positioning stays refused — x/y measures are NOT
  extended to containers).
- The commit path is unchanged: the drag posts the existing geometry message; the op
  layer is id-addressed and already works on containers (ADR-511 D5); the two-clamp
  rule and the served bounds apply verbatim.
- The pane's container Layout section gains the W/H readback + entry (D3) beside
  Hug | Fill — a chosen width preset and a dragged width are the same CSS fact.
- Off-stage containers (web, document) stay static-boxed: no frame, no measure
  (ADR-461's mode truth is untouched).

### D3 — The pane speaks Figma's detail grammar: numeric fields + icon rows

Within ADR-519's spine and D6/D7 refusals (no raw CSS, no paint literals, no
rotation):

- **Numeric entry** — the readbacks become editable fields clamped to the served
  bounds (two-clamp, keyboard instead of drag): W/H at block + staged-container
  grain; X/Y on positioned blocks. Unit is the measure's own (%). This lands
  ADR-519 Phase C's numeric-entry item.
- **Icon rows** — alignment controls render as the conventional glyph triplets
  (start/center/end, per axis) instead of text chips: container/page `align` +
  `justify` rows first. The mechanism is untouched (`setContainerLayout` presets);
  only the presentation changes. Padding/gap/width keep labeled presets (their
  values are not glyphable).
- **Per-type detail** — sections continue to derive from the served registry
  (`applies`), so a media block shows fit/height, a callout its variant, a staged
  element its geometry: the Figma "details per type" reading is the registry's
  existing shape, presented per the spine.

### D4 — The pane is the structure's home; the navigator is the filmstrip

- The pane's **Identity section** (every scope, ADR-519 D3) gains:
  - **the path** — the ancestor chain as clickable segments (page › container › …),
    the same `climbChain` derivation the canvas breadcrumb uses;
  - **Contents** — the selection's direct children (containers + blocks, operator
    words + text snippet, click-to-select) at page and container scope. Selection
    routes through the existing selection paths (a new reach, not a new op).
- The navigator's per-page structure tree is **deleted** (Singular Implementation —
  the ADR-511 D3 clause is superseded; structure has ONE home now). The navigator
  is the sequence: page cards, reorder, multi-select, add — nothing below the page
  grain.
- The canvas `SelectionBreadcrumb` stays — the at-canvas orientation cue during a
  walk; the pane path is the inspector's copy of the same derivation (one function,
  two mounts, per the label-map precedent).

### D5 — Refusals restated

No positional container (move = reorder, Phase 3) · no container x/y/z · no
rotation/opacity/radius/fill literals (ADR-519 D6) · no per-slide view on web
(bands scroll) · no view state in the artifact (a stage index is never bytes) ·
no second structure tree.

## 3. Phasing

Single pass (this ADR ships it): D1 stage view · D2 container measures · D3 numeric
entry + alignment icons · D4 path/Contents + navigator tree deletion. The remaining
ADR-519 Phase B/C items (multi-select scope, Group/Ungroup, ⌘-click, page identity,
Direction row, align-self, snap guides, drag-reorder) are unchanged and unabsorbed.
