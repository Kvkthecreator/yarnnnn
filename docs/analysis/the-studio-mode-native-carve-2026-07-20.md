# The Studio mode-native carve — one grammar, N native editors (2026-07-20)

> Discourse capture. The operator's five-point usability assessment of the Make surface,
> cross-examined against canon (ADR-443/447/453/456/457/458/461/465, STUDIO.md, ESSENCE v16)
> and a code-level sweep of the live implementation. Ratified in full by the operator
> 2026-07-20, implementation delegated. The decisions live in
> [ADR-466](../adr/ADR-466-the-mode-native-carve-one-grammar-n-native-editors.md); this note
> is the derivation.

## The operator's five points (verbatim intent)

1. Object selection → fills/resizing/relocation feels like a latch-on, not native. Wants
   web-editor mechanics (Squarespace/Wix) translated to feel like PowerPoint (deck) or
   Notion (document). Willing to revert the Notion-vs-slides block separation *if* that is
   what makes each document type truly native.
2. Export/Share missing as first-class in Properties — including AI-native sharing (MCP),
   thesis: URL-link-like handling.
3. `Media ▾` demoted or upgraded; `+ New` should gain the design-system creation shape
   (inference AND existing-files provenance), possibly living with/через the chat.
4. `Re-arrange` placement; the "Title slide has no place for this slide's content" refusal
   needs smarter handling.
5. Editing/importing/navigation still clunky overall.

## The diagnosis

**Studio was built mechanism-first, bottom-up.** ~20 ADRs, each individually sound and
canon-clean (one write door, DOM-is-the-model, tokens-not-pixels, grain ladder, gutter,
slash, arrangements, bounded geometry). But the chrome is **generic across modes**: one
selection ladder, one Properties inspector, one toolbar, one interaction model serving a
deck, a document, an article and a landing page identically. That is why it feels
latched-on:

- A **deck** member gets Notion affordances (hover gutter, slash palette, turn-into) on a
  spatial object. PowerPoint's primary grammar — *select an object → see handles →
  move/resize it* — does not exist: no selection box, no drag-to-position, width-only
  resize.
- A **document** member gets deck residue: the ladder selects "slot" and "page" scopes that
  mean nothing in a flowing document; the ever-present inspector is the panel Notion
  deliberately doesn't have.
- A **page** member gets neither the Wix band-stack model (section arrangements are still
  phase 2) nor spatial editing (correctly refused — a page reflows).

**The canon had already drawn the seams; the FE never enacted them:**

- **The mode seam** (STUDIO.md layer table): `paged` (deck, page — the container is the
  unit) vs `flow` (document, article — blocks are the unit). Served on
  `GET /studio/vocabulary`; used by the FE only to toggle the New-slide button and the
  navigator style.
- **The geometry seam** (ADR-461): *a slide has a frame; a page has a viewport.*
  Bounded-continuous geometry is authorized on deck + media; enumerated tokens everywhere
  else. Shipped only partially (width measure, ratio stops, row reorder).

**The answer to the operator's revert question**: do NOT revert the block substrate — the
block grammar is load-bearing beyond editing (attribution grain, trace join key, citation
carrier; ADR-461 §2 showed the moat rides on `data-block-id`). What gets reverted is the
**chrome uniformity**: one shared grammar, N mode-native editors over it — the same
kernel/app pattern the whole OS runs on.

Three distinct root causes, not one:
(a) the missing experience carve — design debt (points 1, 3, 4-placement);
(b) known-but-deferred mechanisms already named in canon — role-based slot mapping,
picker-in-palette, courteous 409 (points 4, 5);
(c) genuinely missing features — export; the rest of share (point 2).

## Code facts that anchored the carve (2026-07-20 sweep)

- Selection: strict ladder block→slot→page→document (`StudioDesignTab.tsx` scope derivation);
  spatial gestures = row-reorder drag, ratio-stop divider, width-only corner grip on
  measured blocks. No handles, no positioning.
- The refusal: `applyArrangement` returns null when the page carries content but the target
  arrangement has **no `data-slot`** — exactly the slotless set (title, section-header,
  closing, hero, cta). Mapping is name-based with first-slot fallback; role-aware mapping
  is a named ADR-453 D7 fast-follow. The failure surfaces *after* the click, as a red
  banner dead-end.
- `Media ▾` carries only the picker-backed kinds (figure/table/gallery/chart) — the
  slash-excluded set; STUDIO.md already names its retirement ("when the palette can host a
  picker, the button retires").
- Share shipped 2026-07-19 (`00156b3`): Properties document scope mints `/s/{token}`;
  ADR-465 (membership primitive, MCP `share` verb, join-only genesis) is Proposed.
  **No export path of any kind exists** (no PDF/MD/PPTX/download).
- Fluidity: member writes no longer reload (local override, 2026-07-15); but 409 recovery
  is destructive (`setLocalOverride(null)` + reload — in-flight state discarded), foreign
  writes hard-reload, the deck navigator renders one live iframe per slide re-rendered per
  edit.

## The carve (ratified)

| Workstream | What | Shape |
|---|---|---|
| A — Mode-native experience carve | Per-mode interaction contracts: deck=object-first, flow=caret-first, page=band-first | ADR-466 + phased FE |
| B — Insert unification | Media ▾ retires into the located palette; provenance-shaped insert (workspace/inference/blank) | rides A |
| C — Arrangement intelligence | Gallery pre-filter + refusal→resolution + role-aware mapping; Layout beside New slide | independent, immediate |
| D — Share/Export | Export group (print-PDF, AI reference; md = ADR-456 W4); ADR-465 stays its own pass | small FE + the 465 phases |
| E — Fluidity floor | Courteous 409, foreign-write grace, navigator memoization — a budget, not a mechanism | checklist |

Sequencing: C + E regret-free; B lands inside A's insert phase; D's ADR-465 genesis phases
(B/C — invariant-touching) are explicitly NOT ridden in a UX pass.

## The one-line statement

**The canon already drew the seams (mode, frame-vs-viewport, one grammar); the FE built one
generic editor across them — the fix is enacting the seams as per-mode experience
contracts, not adding more mechanisms.**
