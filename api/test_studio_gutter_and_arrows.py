"""Regression gate — Studio gutter pointer-tracking + cross-block arrow nav.

Two polish fixes from the ADR audit:

  F5 (gutter tracking): the hover gutter pinned to the block TOP and only
  repositioned when the pointer crossed to a NEW block — so on a tall block it
  visibly did NOT follow the mouse. Fix: showFor(block, pointerY) centers the
  bar on the cursor clamped to the block's bounds; mousemove repositions on
  EVERY move within the block; the exit grace-timer drops 300ms → 150ms.

  F6 (arrow traversal): only one block edited at a time and the caret couldn't
  leave it. Fix: ArrowUp on the first visual line / ArrowDown on the last enters
  the adjacent TEXT block (caret at end / start) — one continuous flow, pure
  in-iframe caret motion, no write door. Mid-block arrows stay native.

Static/structural checks (no DB, no LLM):

Run:  cd api && python3 test_studio_gutter_and_arrows.py
Exit code is authoritative (0 = pass).
"""

import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


def _no_backticks_in_scripts(src: str) -> bool:
    """No literal backtick may sit inside a *_SCRIPT template body — it would
    terminate the template early (the recurring trap this arc hit twice)."""
    in_script = False
    for line in src.split("\n"):
        s = line.strip()
        if s.endswith("_SCRIPT = `") or "_SCRIPT = `(" in line:
            in_script = True
            continue
        if in_script and s.startswith("`;"):
            in_script = False
            continue
        if in_script and "`" in line:
            return False
    return True


def run() -> bool:
    web = Path(__file__).resolve().parent.parent / "web"
    proj = (web / "components/workspace/viewers/projection.ts").read_text()

    # ── F5: gutter tracks the pointer vertically ─────────────────────────
    _check(
        "showFor takes a pointerY and centers the bar on the cursor",
        "function showFor(block, pointerY)" in proj
        and "pointerY - h / 2" in proj,
    )
    _check(
        "the bar is clamped to the block's own top/bottom",
        "Math.max(pointerY - h / 2, rect.top), rect.bottom - h" in proj,
    )
    _check(
        "mousemove repositions on EVERY move within the block (not only a new block)",
        "showFor(blk, e.clientY);" in proj,
    )
    _check(
        "the exit grace-timer is shortened to 150ms",
        "hideTimer = setTimeout(function () { hideTimer = null; hide(); }, 150)" in proj,
    )
    _check(
        "scroll re-anchors to the block top (no pointer during scroll)",
        "showFor(curBlock, null)" in proj,
    )

    # ── F6: cross-block arrow traversal ──────────────────────────────────
    _check(
        "EDIT_SCRIPT carries TEXT_KINDS for adjacency",
        "var TEXT_KINDS = " in proj and proj.count("var TEXT_KINDS = ") >= 1,
    )
    _check(
        "an ArrowUp/ArrowDown keydown handler exists",
        "if ((e.key !== 'ArrowUp' && e.key !== 'ArrowDown')" in proj,
    )
    _check(
        "ArrowUp fires only on the first visual line (caret rect vs block top)",
        "cr.top - br.top <= LINE" in proj,
    )
    _check(
        "ArrowDown fires only on the last visual line",
        "br.bottom - cr.bottom <= LINE" in proj,
    )
    _check(
        "it enters the adjacent TEXT block (skips media/data blocks)",
        "function adjacentTextBlock(dir)" in proj
        and "TEXT_KINDS.indexOf(k) !== -1) return all[j];" in proj,
    )
    _check(
        "the caret lands at the END going up / START going down",
        "r1.selectNodeContents(prev); r1.collapse(false);" in proj
        and "r2.selectNodeContents(next); r2.collapse(true);" in proj,
    )
    _check(
        "a shift-arrow (selection extension) stays native",
        "|| e.shiftKey) return;" in proj,
    )
    _check(
        "traversal syncs the parent's editing state (yarnnn-edit-entered)",
        "type: 'yarnnn-edit-entered', blockId: pid" in proj
        and "type: 'yarnnn-edit-entered', blockId: nid" in proj,
    )

    # ── the recurring backtick trap ──────────────────────────────────────
    _check(
        "no literal backtick inside any *_SCRIPT body (would break the template)",
        _no_backticks_in_scripts(proj) and proj.count("`") % 2 == 0,
    )

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
