# ADR-458 — The Studio hover layer and the one settings home

> **Amended by [ADR-481](ADR-481-the-flow-chrome-rebuild-a-blank-document-is-a-blank-page.md) D2**
> (2026-07-22): the hover gutter is **`paged`-only** — on `flow` layouts it is DELETED, not
> hidden. The gutter answers *"insert **here**"*, which was meaningful when blocks were
> enclosures with gaps between them and became meaningless once ADR-480 made the caret the
> insertion point: an affordance that points at a place answers a question a continuous
> writing surface never asks. Insert on flow is `/` at the caret + right-click (ADR-456 W2 +
> ADR-462), both already built. The gutter's row-geometry work (`rowAt`, the 64px lane) is
> untouched and still governs every `paged` surface.

> **Status**: **Accepted** (2026-07-14, operator-ratified — "aligned in proceed" — from the
> Notion-screenshot interaction discourse). Ships in one commit; in-frame block DRAG rides the new
> handle as a named follow-on; the slash-anywhere refactor stays the post-stabilization item
> (ADR-456 W2 banner).

**Date**: 2026-07-14
**Dimension**: Channel (Axiom 6 — the affordance layer between the member's pointer and the
grains) + Mechanism (no new write path; every act routes through existing ops)

**Extends**: ADR-446 (direct edit), ADR-453 (the Design tab + click-grain ladder), ADR-456 W2
(the slash palette — gains a second entrance).
**Amends**: **ADR-455** (placement reversal — the surface-bar ⋯ "file grain" decision; the file
verbs move into the Design tab's document scope, the "File actions" SurfaceAction is deleted).
**Preserves**: ADR-444/446 one-door mutation, ADR-400 organize flows (`useFileOrganizeVerbs` —
same shared implementation, new chrome), the ADR-436 mount contract.

---

## 1. Context — selection-gated vs hover-gated

The operator's Notion screenshots named the gap precisely: in Notion, the `+` and `⋮⋮` gutter
handles surface on **hover** over any block, with no selection; in the Studio, every affordance
was **selection-gated** (click → toolbar chip + Design tab). Two consequences: block verbs sat
two hops away, and the ADR-456 W2 slash palette — triggered only in empty contexts *while
editing* — was effectively unreachable. Separately: the surface bar's "File actions" button (a
context menu wearing a dropdown costume at a hardcoded right-edge offset) was earning nothing.

## 2. Decisions

### D1 — The hover gutter

A third piece of injected canvas chrome (the format-bar pattern: body-appended, never inside a
block, invisible to commits): hovering any `[data-block]` surfaces a small gutter at the block's
left edge — **no selection needed**:

- **`+`** → opens the **same slash palette** anchored at the block (it posts the existing
  `yarnnn-slash-open` message — one palette, two entrances, the ADR-456 W2 routing unchanged:
  an empty block converts in place, a non-empty one inserts after).
- **`⋮⋮`** → **selects the block and flips the right column to the Design tab** — the verbs' one
  home. Deliberately NOT an in-frame mini-menu: that would be a second implementation of verbs
  the Design tab owns (Singular Implementation). The handle marks the selection in-frame through
  the pointer runtime's own `window.__yarnnnSelect` (one selection state, not two).
- Desktop-pointer only (`matchMedia('(hover: hover)')`); mobile keeps tap-select. The gutter
  hides for the block currently being edited (the format bar owns that space). The pointer
  runtime ignores gutter clicks (the `.yarnnn-fmt` precedent — required, since the pointer's
  document listener runs in the capture phase).
- **Drag is the named follow-on**: the handle is where ADR-453 D7.4's in-frame block drag lands
  (all inside the iframe — it never crosses the boundary), as its own commit once the gutter
  has stabilized.

### D2 — Slash reachability is solved by the gutter, not by widening the trigger

The `+` gutter makes the palette a hover-away for every block — which is what Notion's `+`
actually is (their `/` is a shortcut *on top of* the hover affordance). The W2 empty-context
trigger stays as-is ("Enter, then /" works on any empty line inside an editing block); the full
Notion slash-anywhere (char lands, typing filters, Escape keeps) remains the post-stabilization
refactor — it needs the uncommitted-buffer design W2 deliberately avoided, and a naive widening
would break literal slashes.

### D3 — The one settings home (the ADR-455 placement reversal)

The Design tab's **document scope** becomes the artifact's one settings home. The coherence
argument: Notion's page `⋯` is typography + file verbs — ADR-455 already migrated the typography
half (the Ag chips) into the document scope; this completes the consolidation:

- Document scope gains a **File** section: **Copy link · Duplicate · Rename… · Move… · Trash**
  — consuming the SAME shared implementation the Files surface uses (`useFileOrganizeVerbs` +
  the existing copy-link/duplicate handlers). No second write path, no forked flows; trash
  already falls back to the Studio landing (`onAfterMutate` → `studio.file` cleared).
- The surface-bar **"File actions" SurfaceAction is deleted**, along with the Studio's
  `FileContextMenu` mount; the Studio's surface bar is crumb-only until an action earns a place
  (the ADR-442 seam is unchanged — this removes a tenant, not the wall).

### D4 — The interaction model, in one sentence

**Hover reveals (the gutter) · click selects (the grain ladder) · double-click edits (in place)
· `+`/slash insert (one palette) · the Design tab is the one home for verbs and settings.**

## 3. Cascade

`web/components/workspace/viewers/projection.ts` (gutter runtime + CSS, pointer ignore +
`__yarnnnSelect`) · `StudioCanvas` (`design` flag passthrough on the point payload) ·
`StudioSurface` (onPoint flips to Design on the flag; File-actions button + menu deleted;
`fileVerbs` passed down) · `StudioDesignTab` (the File section) · `docs/design/STUDIO.md` ·
ADR-455 (amendment banner) · gate `api/test_adr458_studio_hover_layer.py` (+ the ADR-455 gate's
placement pins updated). No backend change, no posture change, no CHANGELOG entry (nothing
LLM-facing moves).

## 4. The one-line statement

**The missing layer was hover: a gutter that reveals `+` and `⋮⋮` on any block without a
selection, both feeding the affordances we already have — one palette, one Design tab, one
shared set of file verbs now living in the one settings home.**
