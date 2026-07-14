"""Regression gate — Studio single-click-to-caret + Esc-to-block-select.

The felt bug (ADR audit F4): typing needed TWO gestures — a single click only
selected the block (outline), a double-click was required to edit, and the
native double-click word-selected so the first keystroke replaced a word. Notion
is click = caret, always; block-select is the escape UP (Esc), not the step in.

The fix (all in the injected projection runtimes — no boundary change):
  1. enter(blockId, caretX, caretY): places the caret at the click point via
     caretRangeFromPoint (guarded to inside the editable block, never a citation
     island); exposed as window.__yarnnnEnter for the pointer runtime.
  2. The pointer runtime: a single click on a TEXT block (TEXT_KINDS) enters
     edit-at-caret + posts the point payload + yarnnn-edit-entered; media/data
     blocks stay select-only; a click on a citation island selects, never edits.
  3. The while-editing click guard now allows switching to a DIFFERENT block
     (Notion caret-follows-click) — only a click in the SAME editing block
     returns early for native caret placement.
  4. Esc lifts the caret back to block-select (commits, exits, re-selects).

Static/structural checks (no DB, no LLM):

Run:  cd api && python3 test_studio_click_to_caret.py
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

    # ── 1. enter() places a caret at a point ─────────────────────────────
    _check(
        "enter() accepts caret coords",
        "function enter(blockId, caretX, caretY)" in proj,
    )
    _check(
        "caret placed via caretRangeFromPoint / caretPositionFromPoint",
        "document.caretRangeFromPoint" in proj
        and "document.caretPositionFromPoint" in proj,
    )
    _check(
        "the caret is guarded to inside the editable block (never a citation island)",
        "closest('[contenteditable=\"false\"]')" in proj
        and "el.contains(range.startContainer)" in proj,
    )
    _check(
        "enter-at-point is exposed as window.__yarnnnEnter",
        "window.__yarnnnEnter = function (blockId, x, y)" in proj,
    )

    # ── 2. single click on a TEXT block enters at caret ──────────────────
    _check(
        "the pointer runtime carries the TEXT_KINDS set",
        "var TEXT_KINDS = " in proj
        and "'prose'" in proj and "'callout'" in proj and "'heading'" in proj,
    )
    _check(
        "a single click on a TEXT block calls __yarnnnEnter with the click point",
        "TEXT_KINDS.indexOf(blkKind) !== -1" in proj
        and "window.__yarnnnEnter(bid, e.clientX, e.clientY)" in proj,
    )
    _check(
        "a click on a citation island does NOT enter edit (onIsland guard)",
        "onIsland" in proj and "!onIsland" in proj,
    )
    _check(
        "entering via single click still posts the point payload + edit-entered",
        bool(re.search(r"parent\.postMessage\(payload, '\*'\);\s*\n\s*var bid", proj))
        and "type: 'yarnnn-edit-entered', blockId: bid" in proj,
    )

    # ── 3. switching blocks while editing ────────────────────────────────
    _check(
        "clicking a DIFFERENT block while editing does NOT early-return (only same block does)",
        "if (inSameBlock) return;" in proj
        and "click INSIDE that same" in proj,
    )

    # ── 4. Esc lifts to block-select ─────────────────────────────────────
    _check(
        "Esc commits + exits + re-selects the block (lift to block-select)",
        "if (e.key !== 'Escape' || !editingEl) return;" in proj
        and "window.__yarnnnSelect(el)" in proj,
    )
    _check(
        "Esc yields to the link input first (closes it, not the edit)",
        bool(re.search(r"Escape.*\n.*fmtInput.*display !== 'none'\) return", proj)),
    )

    # ── 5. dblclick is now a guarded fallback (no pure-media edit) ────────
    _check(
        "dblclick skips a pure-citation block (onlyRef guard)",
        "var onlyRef = blk.querySelector('[data-ref]') && !hasText;" in proj,
    )

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
