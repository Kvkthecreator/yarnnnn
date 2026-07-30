"""Regression gate — the gutter STAYS DELETED + cross-block arrow nav.

Two halves, and the first one INVERTED by ADR-489 D4.

  The gutter (was F5 — gutter pointer-tracking): the hover gutter is DELETED on
  every mode. ADR-481 D2 removed it on `flow` (the caret IS the insertion point);
  ADR-489 D4 removed the `paged` remainder — it was a third insert route behind
  `/` and the New-‹page› gallery, and web-page editors do not have one. Deleted
  with it: the `⋮⋮` drag-to-reorder and its drop-line (reorder is cut/paste in
  prose on `document`, Move up/down in the menu on `deck`/`web`).

  The checks below are therefore NEGATIVE — they assert the affordance has not
  come back, and that its deletion did not take the shared pointer primitive
  (`bindGesture`) or deck's object grammar with it. That grammar lived in a
  constant NAMED `GUTTER_SCRIPT` while being ~92% object chrome; the rename to
  `OBJECT_SCRIPT` is asserted here because the stale name is what made "delete
  the gutter" look like a 1,167-line deletion.

  F6 (arrow traversal): ArrowUp on the first visual line / ArrowDown on the last
  enters the adjacent TEXT block (caret at end / start) — pure in-iframe caret
  motion, no write door. Mid-block arrows stay native. UNCHANGED and still live
  on `paged`, where a block is an enclosure.

Static/structural checks (no DB, no LLM):

Run:  cd api && python3 test_studio_no_gutter_and_arrows.py
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

    # ── The gutter stays deleted (ADR-489 D4) ───────────────────────────
    _check(
        "no gutter bar is built (the `+` / ⋮⋮ rail)",
        "yarnnn-gutter" not in proj and "yg-handle" not in proj,
    )
    _check(
        "no row-band hover geometry (rowAt / the 64px gutter lane)",
        "function rowAt(" not in proj and "BAND_LEFT_REACH" not in proj,
    )
    _check(
        "no ⋮⋮ drag-to-reorder: no bindDrag, no drop-line, no yarnnn-reorder",
        "function bindDrag(" not in proj
        and "yarnnn-dropline" not in proj
        and "yarnnn-dragging" not in proj
        and "yarnnn-reorder" not in proj,
    )
    _check(
        "the parent has no reorder consumer left (no onReorder / handleReorder)",
        "onReorder" not in (web / "components/studio/StudioCanvas.tsx").read_text()
        and "handleReorder"
        not in (web / "components/studio/StudioSurface.tsx").read_text(),
    )
    # The deletion must NOT have taken the shared primitive or the object chrome.
    _check(
        "bindGesture SURVIVES (the shared pointer primitive, ADR-461 D2)",
        "function bindGesture(" in proj,
    )
    _check(
        "deck's object grammar survives (bounding box + handles + group resize)",
        "yarnnn-selbox" in proj
        and "yarnnn-geometry" in proj
        and "yarnnn-geometry-many" in proj,
    )
    _check(
        "the script is named for what it IS (OBJECT_SCRIPT, not GUTTER_SCRIPT)",
        "const OBJECT_SCRIPT = " in proj and "const GUTTER_SCRIPT = " not in proj,
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
