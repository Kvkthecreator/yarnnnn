#!/usr/bin/env python3
"""The interaction debts named by the 2026-07-31 audit and paid the same day.

Each check defends a defect that was REAL and verified against live source
before it was fixed. They are grouped by the shape of the mistake, because the
shapes recur:

  A. INJECTION SITE vs LIFETIME — an affordance written into one runtime and
     therefore absent from a mode that needs it (undo lived in the paged-only
     OBJECT_SCRIPT, so a document had no undo at all).
  B. THE IFRAME BLIND SPOT — parent-side listeners cannot hear a key, a press
     or a scroll that happened inside the opaque-origin canvas.
  C. THE BROWSER DEFAULT WE INHERIT — Tab moving focus out of a contenteditable
     root ends the writing session; `all: unset` strips a focus ring.

Run:  cd api && python3 test_studio_interaction_debts.py     (NOT pytest)
"""
import re
import sys
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"
PROJ = (WEB / "components/workspace/viewers/projection.ts").read_text()
BLOCKMENU = (WEB / "components/studio/StudioBlockMenu.tsx").read_text()
INSERTMENU = (WEB / "components/studio/StudioBlockInsertMenu.tsx").read_text()

passed = True
count = 0


def _check(label: str, ok: bool) -> None:
    global passed, count
    count += 1
    if not ok:
        passed = False
    print(f"[{'PASS' if ok else 'FAIL'}] {label}")


def _script(name: str) -> str:
    """The body of one injected runtime, so a check can assert WHICH script a
    handler lives in — the distinction the undo defect turned on."""
    m = re.search(rf"const {name} = `([\s\S]*?)\n`;", PROJ)
    return m.group(1) if m else ""


def main() -> int:
    pointer = _script("POINTER_SCRIPT")
    objects = _script("OBJECT_SCRIPT")
    edit = _script("EDIT_SCRIPT")
    _check("the three runtimes are findable", bool(pointer) and bool(objects) and bool(edit))

    print("\n-- A. undo exists on BOTH modes (injection site follows lifetime) --")
    # The defect: the only yarnnn-undo producer sat in OBJECT_SCRIPT, which is
    # injected `paged` only — so ⌘Z did nothing on a document while the parent's
    # undo stack kept filling with snapshots nobody could pop.
    _check(
        "the undo key handler lives in the POINTER runtime (both modes)",
        "yarnnn-undo" in pointer,
    )
    _check(
        "it is GONE from the paged-only object runtime (moved, not copied)",
        "yarnnn-undo" not in objects,
    )
    _check(
        "exactly one undo producer in the file",
        PROJ.count("'yarnnn-undo'") == 1,
    )
    # The guard that makes it safe on flow. __yarnnnEditingId is null on flow
    # WHILE a caret is live (ADR-480 D1), so guarding on it would have stolen
    # ⌘Z mid-sentence and rewound the paragraph to a structural snapshot — the
    # ADR-482 D2 trap. The caret question is __yarnnnCaretLive.
    undo = re.search(r"\(e\.key \|\| ''\)\.toLowerCase\(\) !== 'z'[\s\S]{0,600}?yarnnn-undo", PROJ)
    _check("the undo handler is findable", bool(undo))
    if undo:
        _check(
            "undo yields to a LIVE CARET via __yarnnnCaretLive (not __yarnnnEditingId)",
            "__yarnnnCaretLive" in undo.group(0)
            and "__yarnnnEditingId" not in undo.group(0),
        )

    print("\n-- B. the iframe blind spot: Escape and SCROLL are bridged --")
    _check(
        "the runtime bridges Escape out of the frame",
        "yarnnn-canvas-escape" in pointer,
    )
    for name, src in (("block menu", BLOCKMENU), ("insert menu", INSERTMENU)):
        _check(
            f"the {name} closes on the bridged Escape",
            "yarnnn-canvas-escape" in src,
        )
        # A menu anchored to a page point is a lie once the canvas scrolls, and
        # the parent's own capture-phase scroll listener is deaf to the iframe's
        # scroller. The runtime already reports scroll for the position restore.
        _check(
            f"the {name} closes on in-frame SCROLL (the parent listener is deaf to it)",
            "yarnnn-scroll-pos" in src,
        )

    print("\n-- C. browser defaults we inherit --")
    # Tab took the contenteditable default (move focus OUT), which fired the
    # flow blur handler: commit + caret lost, mid-paragraph. No writing tool
    # ends a session on Tab.
    tab = re.search(r"if \(e\.key !== 'Tab'\) return;[\s\S]{0,400}?\}\);", PROJ)
    _check("flow handles Tab at all", bool(tab))
    if tab:
        _check(
            "Tab is swallowed so it cannot blur-and-commit the flow root",
            "preventDefault()" in tab.group(0),
        )
        _check(
            "Shift+Tab inserts nothing (no outdent exists to pair with it)",
            "e.shiftKey" in tab.group(0),
        )
    # `all: unset` strips the UA focus ring and the buttons stay in tab order.
    fmt = re.search(r"const FMT_CSS = `([\s\S]*?)\n`;", PROJ)
    _check("FMT_CSS is findable", bool(fmt))
    if fmt:
        body = fmt.group(1)
        _check(
            "the format bar's buttons show a focus ring (all:unset removed the UA one)",
            ".yarnnn-fmt button:focus-visible" in body,
        )
        _check(
            "the link input shows one too (it is the field a member types into)",
            ".yarnnn-fmt input:focus-visible" in body,
        )

    print()
    print(f"{'PASS' if passed else 'FAIL'}: {count} checks")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
