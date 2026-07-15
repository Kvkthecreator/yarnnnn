"""Regression gate — Studio ⋮⋮ block drag (real reorder).

The felt bug (ADR audit F1): "moving doesn't follow the mouse." The ⋮⋮ handle
had cursor:grab but did NOTHING on drag — it only clicked (select + Design tab).
"Move" was Up/Down buttons a whole column away in the Design tab: to move a
block 3 positions you selected it, found the tab, clicked Down 3× (3 revisions).

The fix (all in-frame — the drag never crosses the sandbox boundary):
  1. artifactOps: moveBlockTo(html, blockId, beforeBlockId) — the general reorder
     (before a sibling, or end of parent when null); no-op guards (self / already
     in place / v1 same-parent-only). moveBlock (Design-tab Up/Down) reimplemented
     ON TOP of it (Singular Implementation).
  2. GUTTER_SCRIPT: pointer-events drag on .yg-handle — threshold, the block dims
     (.yarnnn-dragging), a drop-line (.yarnnn-dropline) follows the cursor between
     same-parent siblings, release posts ONE yarnnn-reorder; edge auto-scroll;
     a click WITHOUT a drag still selects + opens the Design tab
     (gestureSuppressClick disambiguates). cursor:grab → grabbing.

  ADR-461 D2 (2026-07-15): the pointer plumbing moved into `bindGesture`, the
  ONE gesture primitive — bindDrag is now its first caller and its proof. The
  checks below assert INVARIANTS rather than the old inline spellings, so the
  second caller (resize) inherits them.
  3. Canvas forwards yarnnn-reorder → surface handleReorder → applyOp(moveBlockTo)
     = ONE revision.

Static/structural checks (no DB, no LLM):

Run:  cd api && python3 test_studio_block_drag.py
Exit code is authoritative (0 = pass).
"""

import re
import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


def run() -> bool:
    web = Path(__file__).resolve().parent.parent / "web"
    ops = (web / "components/studio/artifactOps.ts").read_text()
    proj = (web / "components/workspace/viewers/projection.ts").read_text()
    canvas = (web / "components/studio/StudioCanvas.tsx").read_text()
    surface = (web / "components/studio/StudioSurface.tsx").read_text()

    # ── 1. moveBlockTo + moveBlock delegation ────────────────────────────
    _check(
        "moveBlockTo(html, blockId, beforeBlockId) exists",
        "export function moveBlockTo(" in ops
        and "beforeBlockId: string | null," in ops,
    )
    _check(
        "moveBlockTo no-ops on self / already-in-place",
        "if (beforeBlockId === blockId) return null;" in ops
        and "block.nextElementSibling === target) return null;" in ops,
    )
    _check(
        "moveBlockTo v1 is same-parent only (target.parentElement !== parent → null)",
        "target.parentElement !== parent) return null;" in ops,
    )
    _check(
        "moveBlockTo appends to end when beforeBlockId is null",
        "parent.appendChild(block)" in ops
        and "parent.lastElementChild === block) return null;" in ops,
    )
    _check(
        "moveBlock (Design-tab Up/Down) is reimplemented on top of moveBlockTo",
        "return moveBlockTo(html, blockId, prev.getAttribute('data-block-id'));" in ops
        and "moveBlockTo(html, blockId, after ? after.getAttribute('data-block-id') : null)" in ops,
    )

    # ── 2. the drag runtime ──────────────────────────────────────────────
    _check(
        "the ⋮⋮ handle binds a pointer drag (bindDrag)",
        "function bindDrag(handle)" in proj and "bindDrag(handle);" in proj,
    )
    _check(
        "drag uses Pointer Events + setPointerCapture (not HTML5 DnD)",
        "handle.setPointerCapture(e.pointerId)" in proj
        and "addEventListener('pointerdown'" in proj
        and "addEventListener('pointermove'" in proj,
    )
    # ADR-461 D2: the threshold moved into `bindGesture`, the one pointer-gesture
    # primitive — it is no longer inline in bindDrag. Assert the INVARIANT (a
    # press under the threshold is still a click, and the axis decides what
    # "movement" means), not the old spelling, so the next gesture caller
    # inherits the check instead of breaking it.
    _check(
        "a movement threshold separates a gesture from a click",
        "var travel = axis === 'xy'" in proj and "if (travel < threshold) return;" in proj,
    )
    _check(
        "the threshold lives in the ONE gesture primitive (not per-gesture)",
        "function bindGesture(handle, subject, opts)" in proj
        and "bindGesture(handle, function () { return curBlock; }" in proj,
    )
    _check(
        "the dragged block dims + a drop-line follows the cursor",
        "classList.add('yarnnn-dragging')" in proj
        and ".yarnnn-dropline" in proj
        and "ensureDropline()" in proj,
    )
    _check(
        "edge auto-scroll (in-frame — window.scrollBy, never the parent)",
        "window.scrollBy(0, -12)" in proj and "window.scrollBy(0, 12)" in proj,
    )
    _check(
        "release posts ONE yarnnn-reorder {blockId, beforeBlockId}",
        "type: 'yarnnn-reorder', blockId: id, beforeBlockId: beforeId" in proj,
    )
    # The leak that made a second gesture source unsafe: the old flag stayed
    # true after a drop and reset on the NEXT click, so two gesture sources
    # sharing it would cross-talk ("resize sometimes eats a click"). One flag,
    # one setter (the primitive), consumed on read.
    _check(
        "click-suppression is consumed on read, never left set for the next click",
        "gestureSuppressClick = false; return; }" in proj
        and "draggedPastThreshold" not in proj,
    )
    _check(
        "a click WITHOUT a drag still selects + opens the Design tab (drag suppresses it)",
        "if (gestureSuppressClick) { gestureSuppressClick = false; return; }" in proj
        and "design: true }" in proj,
    )
    _check(
        "cursor is honest: grab on the handle, grabbing while dragging",
        "cursor: grab" in proj and ".yg-handle:active { cursor: grabbing; }" in proj,
    )
    _check(
        "no stray backtick broke the runtime templates (balanced)",
        proj.count("`") % 2 == 0,
    )

    # ── 3. canvas + surface wiring ───────────────────────────────────────
    _check(
        "the canvas forwards yarnnn-reorder → onReorder",
        "d.type === 'yarnnn-reorder'" in canvas
        and "onReorder?.(d.blockId" in canvas
        and "onReorder," in canvas,
    )
    _check(
        "the surface lands the drag as ONE revision via applyOp(moveBlockTo)",
        "const handleReorder = useCallback(" in surface
        and "moveBlockTo(html, blockId, beforeBlockId)" in surface
        and "onReorder={handleReorder}" in surface,
    )

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
