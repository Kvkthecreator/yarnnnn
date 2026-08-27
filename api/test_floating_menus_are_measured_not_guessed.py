"""Gate — a menu that opens at a pointer is MEASURED against the viewport, never guessed.

Operator-observed (KVK 2026-08-27, screenshot): the Files tree right-click menu
ran off the bottom of the screen. The last verbs (Move to…, Duplicate, Delete)
were in the DOM, invisible and unreachable.

Cause: the clamp used a HARDCODED guess at the menu's own height —
`Math.min(y, window.innerHeight - 240)`. The box reaches ~530px on a folder
(9 conditional rows), so from a click in the lower half of the window it
overflowed by ~100px. No constant can be right for a menu whose rows are
conditional on the target.

Studio had already hit this exact defect and fixed it correctly (ADR-586 D4,
StudioBlockMenu: "The vertical clamp is MEASURED, not assumed"). Two sibling
menus never got the fix and kept two DIFFERENT hand-picked constants (240, 120)
— the same question answered three ways. The repair extracts one hook,
`useViewportClamp`, so the answer stops being a property of whichever menu
someone happened to be looking at.

This gate locks:
  - no floating menu re-introduces a hardcoded `innerHeight - N` clamp,
  - the two repaired menus measure via the shared hook,
  - the hook actually measures (getBoundingClientRect) inside useLayoutEffect,
    so it corrects BEFORE paint rather than flashing,
  - a tall menu stays reachable (max-height + scroll) rather than clipping,
  - the Open-With flyout is viewport-aware on BOTH axes.

Source-assertion gate (the behavior is FE; same Python-over-source pattern as
ADR-237/238/297).

Usage:
    cd api
    python test_floating_menus_are_measured_not_guessed.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"

_passed = 0
_failed = 0


def check(label: str, cond: bool) -> None:
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  ✓ {label}")
    else:
        _failed += 1
        print(f"  ✗ {label}")


def _read(rel: str) -> str:
    return (WEB / rel).read_text(encoding="utf-8")


def _strip_comments(src: str) -> str:
    """Comments DESCRIBE the removed guess; only live code should be asserted on.

    Without this the gate greps its own explanatory prose and reports the defect
    it just fixed — passing (or failing) for the wrong reason.
    """
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    src = re.sub(r"^\s*//.*$", "", src, flags=re.M)
    return src


MENUS = [
    "components/workspace/FileContextMenu.tsx",
    "components/workspace/CanvasContextMenu.tsx",
]


def test_no_guessed_clamp() -> None:
    print("\n[1] no floating menu guesses its own height")
    # Every menu in the tree, not just the two repaired — a NEW menu with a
    # fresh constant is the same defect arriving again.
    roots = [WEB / "components"]
    offenders: list[str] = []
    for root in roots:
        for p in root.rglob("*.tsx"):
            code = _strip_comments(p.read_text(encoding="utf-8"))
            # `innerHeight - <literal>` is the guess. `innerHeight - height`
            # (a measured variable) is the repair, so only literals offend.
            if re.search(r"innerHeight\s*-\s*\d+", code):
                offenders.append(str(p.relative_to(WEB)))
    check(
        f"no `innerHeight - <constant>` clamp anywhere in components/ (found: {offenders or 'none'})",
        not offenders,
    )


def test_repaired_menus_measure() -> None:
    print("\n[2] the two repaired menus measure through the shared hook")
    for rel in MENUS:
        src = _strip_comments(_read(rel))
        name = rel.rsplit("/", 1)[-1]
        check(f"{name} imports useViewportClamp", "useViewportClamp" in src)
        check(f"{name} attaches the measuring ref to its box", "ref={boxRef}" in src)
        # A hook that is called but whose ref is never attached measures
        # nothing and silently returns the raw point — passing by import alone
        # would be vacuous.
        check(
            f"{name} stays reachable when taller than the viewport (max-h + scroll)",
            "max-h-[calc(100vh-16px)]" in src and "overflow-y-auto" in src,
        )


def test_hook_measures_before_paint() -> None:
    print("\n[3] the hook measures the real box, before paint")
    src = _strip_comments(_read("hooks/useViewportClamp.ts"))
    check("reads the real box (getBoundingClientRect)", "getBoundingClientRect" in src)
    check(
        "in useLayoutEffect (corrects BEFORE paint — no visible jump)",
        "useLayoutEffect" in src and "useEffect(" not in src,
    )
    check("clamps BOTH axes", "innerWidth" in src and "innerHeight" in src)
    check(
        "clamps against the MEASURED size, not a constant",
        "innerWidth - width" in src and "innerHeight - height" in src,
    )
    check(
        "keeps a margin off the edge rather than sitting flush",
        "Math.max(MARGIN" in src,
    )


def test_flyout_is_viewport_aware() -> None:
    print("\n[4] the Open-With flyout flips instead of running off-screen")
    src = _strip_comments(_read(MENUS[0]))
    # A flyout is positioned against its PARENT, so the repair is a FLIP, not a
    # clamp — asserted as the flipped classes actually being reachable.
    check("can open leftward at the right edge", "right-full" in src)
    check("can hang upward at the bottom edge", "bottom-0" in src)
    check("decides from the real box", "getBoundingClientRect" in src)
    check(
        "and is no longer pinned to left-full/top-0 unconditionally",
        "absolute left-full top-0" not in src,
    )


def main() -> int:
    print("=" * 70)
    print("floating menus are measured, not guessed (KVK 2026-08-27)")
    print("=" * 70)
    test_no_guessed_clamp()
    test_repaired_menus_measure()
    test_hook_measures_before_paint()
    test_flyout_is_viewport_aware()
    print("\n" + "=" * 70)
    print(f"  {_passed} passed, {_failed} failed")
    print("=" * 70)
    return 1 if _failed else 0


if __name__ == "__main__":
    sys.exit(main())
