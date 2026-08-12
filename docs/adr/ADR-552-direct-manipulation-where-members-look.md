# ADR-552 — Direct manipulation where members actually look

> **Status**: Implemented (2026-08-12). Phase 3 of the arrival/move proposal. **No new law** — this closes a deferral ADR-400 named.
> **Closes**: [ADR-400](ADR-400-the-two-principal-files-surface.md)'s deferral — *"Grid drag-drop remains a later fast-follow (tree is the primary folder-structure target)"*
> **Preserves**: ADR-400 Wave B's drag rules verbatim (a file drags, a folder receives) · ADR-551 D3 (a dropped OS file imports into the folder it landed on) · ADR-550 (the move path carries the projection)
> **Derivation**: the 2026-08-12 arrival/move audit

---

## 1. The defect

Drag existed **only in the left tree**, files only. The folder listing and the
Recents grid — the surface members actually browse — carried **zero**
`draggable`. Measured: `FileTile.tsx` and `FileListView.tsx` both returned a
grep count of 0.

ADR-400 knew, and said so: *"Grid drag-drop remains a later fast-follow."* It is
a fast-follow that never followed. The result was a surface where the primary
view is inert and the narrow secondary pane is the only place organisation
happens.

## 2. Decisions

### D1 — The grid and the details list drag, using the tree's grammar

Both renderers gain the same drag/drop props the tree already had. **The tree's
rule is inherited verbatim, not re-derived:**

- a **file** is draggable iff the member can organize it;
- a **folder** is the drop target;
- a folder is **never** draggable — there is no backend folder-move (folders are
  implicit in paths, so moving one is N row moves);
- a file is **never** a drop target — dropping onto a file has no meaning.

`FileTile` is already the singular tile for both the folder listing and Recents
(Singular Implementation, 2026-07-09), so one change reaches both grids.

### D2 — One MIME token, declared once and imported

This is the load-bearing decision, and the first draft got it wrong: the tile
declared `'application/x-yarnnn-path'` and the tree declared **the same literal
independently**. Two spellings of one token — a rename of either would break
dragging *across* panes while every per-module check stayed green.

`TILE_DRAG_MIME` is exported from the tile module; the list and the tree import
it. The gate asserts the token is declared in **exactly one** module rather than
that the strings match — matching strings is what the broken version also had.

### D3 — One move path, one import path

The listing wires the **same handlers** the tree uses: `commitMove` for an
internal drop, `openUpload(files, folder)` for an OS-file drop. A second mover
would drift from the first — and would miss ADR-550's projection carry, which
lives in the primitive beneath both.

The listing keeps its **own** drop-target highlight state, so the two panes
never fight over one highlight.

## 3. What is deliberately not built

- **No folder drag.** There is no backend folder-move; building one is its own
  decision (N row moves, partial-failure semantics, and the ADR-550 sibling
  carry per row). Smuggling it in here would have been the larger change wearing
  the smaller one's clothes.
- **No paste.** The natural sibling, and cheap once drag proves the gesture —
  but nothing in the audit shows a member reaching for it, and ADR-400 never
  specified it.
- **No multi-select.** Phase 4; it touches every verb signature and inherits
  ADR-519's inescapable-multi-select trap.
- **No drop onto breadcrumbs, sidebar items, or "up one level".** One drop
  target shape at a time.

## 4. Falsifiers

1. Drag a file tile in a folder listing onto a folder tile → it moves.
2. Drag a row in the details list onto a folder row → it moves.
3. Drag a file from the **tree** onto a **grid folder tile** → it moves (the
   one-token invariant).
4. A folder tile cannot be picked up.
5. A file tile is not a drop target.
6. Drop an OS file onto a folder tile → it imports **there** (ADR-551 D3).
7. Dragging in the listing does not highlight a tree row, and vice versa.

## 5. The one-line statement

**The surface members actually look at drags the same way the tree always
did — one grammar, one token, one move path.**
