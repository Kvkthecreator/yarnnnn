"""Regression gate — Studio Enter-makes-a-block + the bottom-append fix.

The felt bug (ADR audit F2): "adding feels displaced." Studio had NO Enter
handler, so Enter fell to native contentEditable and inserted a <br> INSIDE the
block — there was NO keyboard path to a new block; every one needed a mouse
trip. And with nothing selected, insertBlock appended to the END of the
document (the literal "adding on the bottom").

The fix:
  1. EDIT_SCRIPT gains an Enter handler: Enter at a block's END inserts a fresh
     empty prose block after it and moves the caret in (Notion's "writing is
     adding"). Shift+Enter = native soft break; a list block keeps native <li>;
     mid-block Enter falls through to native (split is commit 6). It posts
     yarnnn-enter-block {afterBlockId}; the block-end guard uses a range probe.
  2. The surface's onEnterBlock inserts prose after that block (always present,
     so Enter never hits the end-append path), then sets editingBlockId to the
     new block so the caret lands in it after the reload.
  3. Bottom-append, made structural (ADR-466 D4): there is no un-located insert
     left. Every insert path carries an explicit block anchor — the palette's
     take handshake reports the exact block, the cited-file picker parks and
     reuses that located context — so nothing can fall back to the document
     end. (The old lastCaretBlockId/insertAnchor implicit-anchor mechanism was
     the fix for the un-located toolbar insert; it retired with Media ▾.)

Static/structural checks (no DB, no LLM):

Run:  cd api && python3 test_studio_enter_makes_block.py
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
    proj = (web / "components/workspace/viewers/projection.ts").read_text()
    canvas = (web / "components/studio/StudioCanvas.tsx").read_text()
    surface = (web / "components/studio/StudioSurface.tsx").read_text()

    # ── 1. the Enter handler in the runtime ──────────────────────────────
    _check(
        "EDIT_SCRIPT has an Enter keydown handler",
        "if (e.key !== 'Enter' || e.shiftKey || !editingEl) return;" in proj,
    )
    _check(
        "Enter at the block END appends a new block (caretAtBlockEnd range probe)",
        "function caretAtBlockEnd()" in proj
        and "setEndAfter(editingEl.lastChild" in proj
        # Commit 6 restructured this into if/else: END → append; mid → split.
        and "if (caretAtBlockEnd()) {" in proj,
    )
    _check(
        "Shift+Enter is left native (never a new block)",
        "e.shiftKey" in proj,
    )
    _check(
        "a list/checklist block keeps native <li> creation",
        "function inListBlock()" in proj and "if (inListBlock()) return;" in proj,
    )
    _check(
        "Enter posts yarnnn-enter-block with the afterBlockId",
        "type: 'yarnnn-enter-block', afterBlockId: id" in proj,
    )
    _check(
        "no stray backtick broke the EDIT_SCRIPT template (balanced backticks)",
        proj.count("`") % 2 == 0,
    )

    # ── 2. the canvas forwards it ────────────────────────────────────────
    _check(
        "the canvas forwards yarnnn-enter-block → onEnterBlock",
        "d.type === 'yarnnn-enter-block'" in canvas
        and "onEnterBlock?.(d.afterBlockId)" in canvas
        and "onEnterBlock," in canvas,  # destructured
    )

    # ── 3. the surface inserts + moves the caret in ──────────────────────
    _check(
        "onEnterBlock inserts prose after the block and enters the new one",
        "const onEnterBlock = useCallback(" in surface
        and "insertBlock(liveHtml, proseFragment, { blockId: afterBlockId })" in surface
        and "setEditingBlockId(newId)" in surface,
    )
    # No reload (2026-07-15): the override carries the new block into `file`, the
    # canvas re-projects on that content change, and srcDoc swaps ONCE instead of
    # churning old→new through a refetch. The caret command races that swap
    # (commandEdit fires on the [editingBlockId] render while the frame still
    # holds the OLD document, so enter() finds no block and no-ops) — onLoad
    # re-commands from editingRef once the new document parses, and THAT lands
    # the caret. The race is identical under a reload; onLoad was always the
    # backstop, which is why removing the reload does not break Enter.
    _check(
        "the new block is written WITHOUT a reload — landedId still drives the caret",
        bool(re.search(r"`Studio: add block`,\s*\n\s*false", surface))
        and "if (!r?.landedId) return null;" in surface
        and "newId = r.landedId;" in surface,
    )
    _check(
        "onLoad re-commands the caret once the new document parses (the backstop)",
        "onLoad={commandEdit}" in canvas
        and "const editingRef = useRef<string | null>(editingBlockId ?? null);" in canvas,
    )

    # ── 4. bottom-append, made structural (ADR-466 D4) ───────────────────
    # The implicit-anchor mechanism (lastCaretBlockId + insertAnchor) is GONE
    # with Media ▾ — every insert is located. What must hold now: the palette
    # flow lands at the reported block (never the document end), and the
    # cited-file picker reuses the same parked located context.
    _check(
        "the implicit-anchor mechanism is deleted (no un-located insert left)",
        "lastCaretBlockId" not in surface and "insertAnchor" not in surface,
    )
    _check(
        "the palette's take flow lands at the reported block",
        "insertBlock(html, p.fragment, { blockId })" in surface,
    )
    _check(
        "the picker lands at the SAME parked located context",
        "landAtLocatedPoint" in surface
        and "ctx: { blockId, beforeInner, afterInner, empty: p.empty }" in surface,
    )

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
