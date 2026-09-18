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

Rule 3 (HARD): a flex CHILD that contains a width-bounded block (max-w-*)
must be allowed to shrink — it needs min-w-0 (or an explicit basis/shrink).
A flex item defaults to min-width:auto and REFUSES to shrink below its
content's intrinsic width, so the bounded block pushes the row past the
viewport. Scoped to the marketing surfaces, whose pages all carry
overflow-x-hidden and therefore CLIP the excess silently instead of
scrolling it.

Trigger (2026-09-18): an operator's contact screenshotted /how-it-works on
a phone with the step-03 replica sliced mid-word. StepFlow's step content
column was a bare `<div className="pt-2">` inside `<li className="flex
gap-6">`, holding product replicas at max-w-xl. Measured on the deployed
page at 390px: every step column ran 301-379px wide, 77 elements past the
right edge — while document.scrollWidth === clientWidth (390), because
overflow-x-hidden ate the evidence. Adding min-w-0 took it to 1.

Scope: web/components/library/ (rules 1-2, the README's own convention)
and web/components/landing/ (rule 3, the marketing surfaces). Widen scope
via this file if a future finding shows a bug class elsewhere.

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
_LANDING = _API_ROOT.parent / "web" / "components" / "landing"

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


# ---------------------------------------------------------------- rule 3

# A flex container: `flex` (not inline-flex-only, not `flex-1`/`flex-col`
# as the sole token) laid out in a ROW. A column flex parent does not
# create the horizontal-shrink hazard, so `flex-col` with no `md:flex-row`
# style sibling is exempt.
_FLEX_ROW = re.compile(r"(?<![:\w-])flex(?![-\w])")
_FLEX_COL = re.compile(r"(?:^|[\s:])flex-col(?![-\w])")
_FLEX_ROW_BP = re.compile(r"(?:sm|md|lg|xl|2xl):flex-row(?![-\w])")
# A width-bounded block whose bound can EXCEED a phone viewport (~390px)
# and so refuses to shrink inside an auto-min flex child. Tailwind: xl=576px
# and up are over budget; md=448/lg=512 already crowd a 390px screen once the
# row's gutter and any sibling node are paid for. Smaller bounds (sm=384,
# xs=320), percentage bounds and arbitrary pixel bounds under ~390px are NOT
# hazards — StudioReplica's max-w-[280px] canvas and max-w-[90%] chat bubble
# both fit, and both measured zero overflow at 390px.
_BOUNDED = re.compile(r"(?<![:\w-])max-w-(?:md|lg|xl|2xl|3xl|4xl|5xl|6xl|7xl)(?![-\w])")
# The escapes that permit shrinking.
_SHRINKABLE = re.compile(r"(?<![:\w-])(?:min-w-0|basis-0|w-0|overflow-x-auto|overflow-auto|overflow-hidden|truncate)")


def _tags(src: str):
    """Yield (line_no, depth, className) for every JSX opening tag.

    Coarse structural scan: tracks nesting by counting opening vs closing
    JSX tags. Sufficient because these components are hand-written JSX with
    one element per logical block and className on the opening tag."""
    out = []
    depth = 0
    # element-ish: <div ...>, <li ...>, </div>, <Foo />
    token = re.compile(r"<(/?)([A-Za-z][\w.]*)([^>]*?)(/?)>", re.S)
    # Work on the whole source so multi-line tags are seen as one token.
    for m in token.finditer(src):
        closing, name, attrs, selfclose = m.groups()
        line_no = src.count("\n", 0, m.start()) + 1
        if closing:
            depth -= 1
            continue
        cls = ""
        cm = re.search(r'className=(?:"([^"]*)"|\{`([^`]*)`\}|\{([^}]*)\})', attrs, re.S)
        if cm:
            cls = cm.group(1) or cm.group(2) or cm.group(3) or ""
        out.append((line_no, depth, cls, name))
        if not selfclose:
            depth += 1
    return out


def test_rule3_flex_children_can_shrink() -> None:
    print("\n[rule 3 · HARD] a flex child holding a max-w-* block carries min-w-0")
    violations: list[str] = []
    checked = 0
    for path in sorted(_LANDING.rglob("*.tsx")):
        src = path.read_text()
        tags = _tags(src)
        for idx, (line_no, depth, cls, _name) in enumerate(tags):
            if not _FLEX_ROW.search(cls):
                continue
            # The hazard is horizontal, and only at PHONE width — the page
            # clips what overflows a ~390px viewport. A row that stacks on
            # phones and only becomes a row from sm:/md:/lg: up has room for
            # its bounded child by the time it is a row, so it is exempt.
            # (AppShowcase's `flex flex-col ... lg:flex-row` measured zero
            # overflow at 390px for exactly this reason.)
            if _FLEX_COL.search(cls):
                continue
            # Direct children are the next tags at depth+1 before depth returns.
            for c_line, c_depth, c_cls, _c_name in tags[idx + 1:]:
                if c_depth <= depth:
                    break
                if c_depth != depth + 1:
                    continue
                # Does this child SUBTREE hold a width-bounded block?
                bounded = False
                for d_line, d_depth, d_cls, _d in tags[tags.index((c_line, c_depth, c_cls, _c_name)) :]:
                    if d_depth < c_depth:
                        break
                    if _BOUNDED.search(d_cls):
                        bounded = True
                        break
                if not bounded:
                    continue
                checked += 1
                if _SHRINKABLE.search(c_cls) or "shrink-0" in c_cls:
                    continue
                rel = path.relative_to(_LANDING.parent.parent)
                violations.append(
                    f"{rel}:{c_line}  flex child holds a max-w-* block but has no min-w-0"
                    f'  (className="{c_cls.strip()[:70]}")'
                )
    if violations:
        for v in violations:
            fail("flex child cannot shrink", v)
    else:
        ok(f"all {checked} bounded flex child(ren) in landing/ can shrink")


def test_convention_documented() -> None:
    print("\n[doc] the convention is written in the library README")
    readme = (_LIBRARY / "README.md").read_text()
    ok_doc = "Responsive convention" in readme and "grid-cols-1 sm:grid-cols" in readme
    if ok_doc:
        ok("README documents the responsive convention + gate")
    else:
        fail("README missing the Responsive convention section")


def main() -> int:
    print("Responsive convention gate (components/library/ + components/landing/)")
    test_rule1_mobile_first_grids()
    test_rule2_justify_between_wrap()
    test_rule3_flex_children_can_shrink()
    test_convention_documented()
    print(f"\n{PASSED} passed, {FAILED} failed, {WARNINGS} advisory warning(s)")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
