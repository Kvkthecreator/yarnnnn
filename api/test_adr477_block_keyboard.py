"""ADR-477 — the block keyboard: an empty block closes, a selected block acts.

Source-guards over the runtime. Each check pins an INVARIANT the ADR decides,
not an implementation line (the ADR-462 gate's note on that failure mode holds
here too — these must survive a correct refactor).

The two defects this gate exists to keep dead:

  1. Backspace emptied a block's text and left the block behind, because the
     merge path required a previous TEXT block and there was no "empty block
     closes" rule at all.
  2. Delete on a selected block did nothing, because selectedBlock() refused
     whenever anything was editing — a guard written when SELECTED and EDITING
     were exclusive, which ADR-466 P11 (the box persists through editing) made
     routinely false.

Run: python3 api/test_adr477_block_keyboard.py   (NOT pytest — see the repo's
check()-gates note; these print and return, they don't assert.)
"""

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"  {'✓' if cond else '✗'} {label}")


def _decommented(src: str) -> str:
    """The code that RUNS: block comments and // lines stripped.

    This gate's whole subject is guard logic, and the guards are surrounded by
    long prose explaining the seams. Greping raw source would count a comment
    describing the OLD guard as evidence the old guard is still installed.
    """
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    src = re.sub(r"^\s*//.*$", "", src, flags=re.M)
    return src


def main() -> bool:
    proj_path = _ROOT / "web/components/workspace/viewers/projection.ts"
    surface_path = _ROOT / "web/components/studio/StudioSurface.tsx"
    canvas_path = _ROOT / "web/components/workspace/viewers/../../studio/StudioCanvas.tsx"
    menu_path = _ROOT / "web/components/studio/StudioBlockMenu.tsx"

    proj = _decommented(proj_path.read_text())
    surface = _decommented(surface_path.read_text())
    canvas = _decommented(canvas_path.read_text())
    menu = _decommented(menu_path.read_text())

    print("\nADR-477 — the block keyboard\n")

    # ── D1: an empty block closes itself ──────────────────────────────────
    print("D1 — Backspace on an empty block removes it")
    # .find() not .index(): a REMOVED rule must report a red check, not raise.
    _empty_at = proj.find("verb: 'delete', blockId: goneId")
    _merge_at = proj.find("adjacentTextBlock('up')")
    _check(
        "the empty case is decided BEFORE the merge path's text-block "
        "requirement (an empty block has nothing to merge, so the "
        "previous-TEXT-block gate must not reach it)",
        _empty_at != -1 and _merge_at != -1 and _merge_at > _empty_at,
    )
    _check(
        "emptiness is judged on TEXT, and a block holding a citation or an "
        "image is never treated as empty",
        "textContent || '').trim() === ''" in proj
        and "querySelector('[data-ref], img')" in proj,
    )
    _check(
        "the sole/first block falls through to native (nothing to fall back to)",
        "here <= 0" in proj,
    )
    _check(
        "the removal detaches SILENTLY — a commit would re-assert the block "
        "and race the delete on one head (the one-gesture-two-ops trap)",
        "exit(false, true)" in proj,
    )
    _check(
        "the member stays located: caret into a text predecessor, else the "
        "non-text predecessor takes the SELECTION",
        "__yarnnnSelect(back)" in proj and "yarnnn-edit-entered', blockId: backId" in proj,
    )

    # ── D2: the guard's seam is the caret's CLAIM, not edit-mode ──────────
    print("\nD2 — a selected block acts, even while a caret exists elsewhere")
    _check(
        "selectedBlock() no longer refuses on the mere existence of an "
        "editing block (the P11 overlap made that guard a dead end)",
        "function selectedBlock()" in proj
        and "if (window.__yarnnnEditingId && window.__yarnnnEditingId() != null) return null;\n    var sel"
        not in proj,
    )
    _check(
        "the caret's claim is scoped to THIS block and requires text to act on",
        "function caretOwnsKeyIn" in proj
        and "!== editing) return false" in proj
        and "textContent || '').trim() !== ''" in proj,
    )
    _check(
        "text keys (⌘C/⌘V) stay with the editor whenever a caret exists — an "
        "empty selected block must not paste a BLOCK where text was meant",
        "k === 'v' || k === 'c'" in proj and "__yarnnnEditingId() != null) return" in proj,
    )

    # ── D3: one body, N entrances (ADR-462 D10's standing rule) ──────────
    print("\nD3 — the key composes an existing verb, never a new op")
    _check(
        "the runtime posts the SAME yarnnn-key-verb the menu path posts; no "
        "second delete implementation appears in the runtime",
        proj.count("type: 'yarnnn-key-verb'") >= 2
        and "deleteBlock(" not in proj,
    )
    _check(
        "the parent routes that message to the shared verb handler",
        "yarnnn-key-verb" in canvas and "onKeyVerb" in canvas,
    )
    _check(
        "delete lands through applyOp — the one write door, CAS-guarded",
        "deleteBlock(html, blockId)" in surface and "applyOp(" in surface,
    )

    # ── D4: falsifier 11 — no row advertises a key that does nothing ──────
    print("\nD4 — every advertised shortcut has a handler (ADR-462 falsifier 11)")
    advertised = set(re.findall(r'shortcut="([^"]+)"', menu))
    _check(
        f"every shortcut the menu renders is listened for (found: "
        f"{sorted(advertised) or 'none'})",
        all(
            ("Delete' || e.key === 'Backspace'" in proj) if s == "⌫"
            else ("k === 'c'" in proj) if s in ("⌘C", "^C")
            else ("k === 'v'" in proj) if s in ("⌘V", "^V")
            else ("k === 'd'" in proj) if s in ("⌘D", "^D")
            else False
            for s in advertised
        ),
    )
    _check(
        # ⌘Z now SHIPS (StudioSurface undo/redo — a session-local stack of
        # whole-op HTML snapshots replayed through the ONE write door as normal
        # CAS revisions; that IS revert-as-write). The invariant this line
        # protects is unchanged and still real: the shortcut lives in the
        # runtime with a live handler, NOT as a dead menu-row hint — advertising
        # a ⌘Z the menu doesn't listen for would be the D10 defect. So the menu
        # still carries no ⌘Z row; the key works from the canvas.
        "⌘Z is not a dead menu hint — it ships as a listened-for runtime key, "
        "not a menu row (a menu row with no handler would be the D10 defect)",
        "⌘Z" not in menu and "yarnnn-undo" in proj,
    )

    print()
    ok = all(c for _, c in _results)
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
