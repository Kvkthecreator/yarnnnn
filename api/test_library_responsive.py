"""Library responsive convention gate — mobile-safe layout in components/library/.

Python file-assertion gate (no JS test runner, per ADR-236 Rule 3). The
suite has no render-at-width test, so responsive overflow bugs are
invisible to gates unless a static convention is enforced. This gate
pins the convention documented in web/components/library/README.md
§"Responsive convention".

Trigger: the TraderMoneyTruth grid-cols-3 collision (operator screenshot
2026-06-12) — a fixed 3-column metric grid with text-2xl currency values
overflowed its cells at ~390px. The fix made it grid-cols-1 sm:grid-cols-3;
this gate keeps the next one from regressing.

Rule 1 (HARD): every `grid-cols-N` with N >= 2 in a library component
must pair with a phone fallback — either it is itself a responsive
breakpoint (`sm:`/`md:`/`lg:`/`xl:` prefix) or a `grid-cols-1` /
`sm:grid-cols-` sibling appears in the same className. A bare
`grid-cols-3` fails.

Rule 2 (ADVISORY): justify-between rows with a right-side metric cluster
should use flex-wrap. Reported as a warning, never fails the gate —
flex-wrap is recommended, not universal.

Scope: web/components/library/ only (the kernel + program component
library the README owns). Widen scope via this file if a future finding
shows the bug class elsewhere.

Usage:
    cd api
    python test_library_responsive.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent
_LIBRARY = _API_ROOT.parent / "web" / "components" / "library"

PASSED = 0
FAILED = 0
WARNINGS = 0

# Matches grid-cols-N (N=2..9) that is NOT itself prefixed by a
# responsive breakpoint. Tailwind variant prefixes attach with a colon
# (sm:grid-cols-3); a bare token has no alnum/colon immediately before.
_BARE_GRID = re.compile(r"(?<![:\w-])grid-cols-([2-9])\b")
_RESPONSIVE_GRID = re.compile(r"(?:sm|md|lg|xl|2xl):grid-cols-[1-9]")
_GRID_COLS_1 = re.compile(r"(?<![:\w-])grid-cols-1\b")


def fail(label: str, detail: str = "") -> None:
    global FAILED
    print(f"  ✗ {label}{(' — ' + detail) if detail else ''}")
    FAILED += 1


def ok(label: str) -> None:
    global PASSED
    print(f"  ✓ {label}")
    PASSED += 1


def warn(label: str, detail: str = "") -> None:
    global WARNINGS
    print(f"  ⚠ {label}{(' — ' + detail) if detail else ''}")
    WARNINGS += 1


def _classname_blocks(src: str) -> list[tuple[int, str]]:
    """Return (line_no, className-string) for every className in the file.
    Handles className="..." and className={cn('...', ...)} by scanning each
    line for grid-cols / flex tokens — coarse but sufficient: Tailwind
    classes are colocated on one logical className per element, and these
    components keep className on a single line or a cn() call."""
    blocks: list[tuple[int, str]] = []
    for i, line in enumerate(src.splitlines(), start=1):
        if "grid-cols-" in line or "justify-between" in line:
            blocks.append((i, line))
    return blocks


def test_rule1_mobile_first_grids() -> None:
    print("\n[rule 1 · HARD] grid-cols-N (N>=2) pairs with a phone fallback")
    violations: list[str] = []
    checked = 0
    for path in sorted(_LIBRARY.rglob("*.tsx")):
        src = path.read_text()
        for line_no, line in _classname_blocks(src):
            bare = _BARE_GRID.search(line)
            if not bare:
                continue
            checked += 1
            has_responsive = bool(_RESPONSIVE_GRID.search(line))
            has_col1 = bool(_GRID_COLS_1.search(line))
            if not (has_responsive or has_col1):
                rel = path.relative_to(_LIBRARY.parent.parent)
                violations.append(f"{rel}:{line_no}  grid-cols-{bare.group(1)} (no grid-cols-1 / sm: fallback)")
    if violations:
        for v in violations:
            fail("bare fixed grid", v)
    else:
        ok(f"all {checked} multi-column grid(s) are mobile-first (0 bare)")


def test_rule2_justify_between_wrap() -> None:
    print("\n[rule 2 · ADVISORY] justify-between rows with metrics should wrap")
    # Advisory only: flag justify-between rows that carry tabular-nums
    # (a metric cluster) but no flex-wrap on the same element line.
    flagged = 0
    for path in sorted(_LIBRARY.rglob("*.tsx")):
        src = path.read_text()
        for line_no, line in _classname_blocks(src):
            if "justify-between" not in line:
                continue
            if "flex-wrap" in line:
                continue
            # Heuristic: a justify-between row likely carrying right-side
            # metrics. We can't see siblings cheaply, so only warn when the
            # SAME line hints at metric content (rare) — keep noise low.
            if "tabular-nums" in line:
                rel = path.relative_to(_LIBRARY.parent.parent)
                warn("justify-between + metrics without flex-wrap", f"{rel}:{line_no}")
                flagged += 1
    if flagged == 0:
        ok("no justify-between metric rows missing flex-wrap (heuristic)")


def test_convention_documented() -> None:
    print("\n[doc] the convention is written in the library README")
    readme = (_LIBRARY / "README.md").read_text()
    ok_doc = "Responsive convention" in readme and "grid-cols-1 sm:grid-cols" in readme
    if ok_doc:
        ok("README documents the responsive convention + gate")
    else:
        fail("README missing the Responsive convention section")


def main() -> int:
    print("Library responsive convention gate (components/library/)")
    test_rule1_mobile_first_grids()
    test_rule2_justify_between_wrap()
    test_convention_documented()
    print(f"\n{PASSED} passed, {FAILED} failed, {WARNINGS} advisory warning(s)")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
