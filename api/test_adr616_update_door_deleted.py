"""ADR-616 — the Update door is deleted; the re-arrange comes home.

Deleting a door is easy to do HALFWAY: the button goes, a module lingers, a
prop keeps being threaded, and the one act the door actually carried quietly
loses its last mount. This gate defends the two halves that can each fail
silently:

  1. The door is gone WHOLE — module, ladder, button, state, props, the
     gesture's suppression clause. A leftover is a second spelling waiting
     (ADR-592's six spellings; the two `hidden` readers; ADR-613 D2's `meter`).

  2. The re-arrange SURVIVED the deletion, at exactly ONE mount. It had a
     single caller and had already been moved twice (out of the pane in July,
     out of the toolbar by ADR-589 D3). A third move that dropped it would take
     slide re-arrangement — and `planArrangement`, `applyArrangementPlan`,
     `applyArrangementMovingContent` — out of the product, with nothing failing
     at build time to say so.

And the defect that made the door deletable in the first place, kept as a rule
rather than a story: **no surviving row may discard a scope it was handed.**
`onOpenPane` took a `PaneScope` through five rungs of derivation and the mount
answered `void sc`. That is what six "different" rows being one action looks
like in code, and it is the shape to catch next time.

Run: python3 test_adr616_update_door_deleted.py   (from api/)
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"

failures: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{label}{(': ' + detail) if detail else ''}")


def read(rel: str) -> str:
    p = WEB / rel
    if not p.exists():
        failures.append(f"missing file: {rel}")
        return ""
    return p.read_text(encoding="utf-8")


def strip_comments(src: str) -> str:
    """Assertions read CODE. This file's own rationale names every symbol it
    forbids, and so do the tombstone comments left at each deletion site — a
    comment-blind grep would read the explanation of the deletion as the thing
    it deleted."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    return re.sub(r"^\s*//.*$", "", src, flags=re.MULTILINE)


AUTH = "components/authoring/"
surface = strip_comments(read(AUTH + "StudioSurface.tsx"))
toolbar = strip_comments(read(AUTH + "StudioToolbar.tsx"))
pane = strip_comments(read(AUTH + "StudioDesignTab.tsx"))
gesture = strip_comments(read(AUTH + "SelectionGesture.tsx"))


# ── 1. The door is gone WHOLE ───────────────────────────────────────────────
check(
    "D1 both modules are deleted",
    not (WEB / AUTH / "StudioUpdateMenu.tsx").exists()
    and not (WEB / AUTH / "updateLadder.ts").exists(),
)
check(
    "D1 nothing imports them",
    "StudioUpdateMenu" not in surface
    and "updateLadder" not in surface
    and "LadderRung" not in surface,
)
check(
    "D1 the toolbar button and its props are gone",
    "onUpdateBlock" not in toolbar
    and "hasBlockSelection" not in toolbar
    and "hasPageAnchor" not in toolbar,
)
check(
    "D1 the surface holds no door state or rung re-targeter",
    "updateMenu" not in surface
    and "openUpdateDoor" not in surface
    and "retargetToRung" not in surface,
)
# The clause that suppressed the gesture while the door was open must go with
# the door — a guard naming dead state is the half-removal this gate exists for.
check(
    "D1 the gesture's suppression clause dropped the dead door",
    "!slash && !citePicker && !ctxMenu && !seedHeld && gestureTarget" in surface,
)

# The ORIGINAL defect, as a standing rule. `void sc` is the exact spelling that
# proved six rows were one action; it must not reappear on any surviving row.
check(
    "D1 no surviving row discards a scope it was handed",
    "void sc" not in surface and "onOpenPane" not in surface,
    "the ladder's answer was derived through five rungs and thrown away",
)


# ── 2. The re-arrange survived, at exactly ONE mount ─────────────────────────
#
# Counted across the whole authoring tree, not asserted at a known site: a
# second mount reappearing elsewhere is precisely the redundancy the 2026-07-21
# note removed, and a site-specific check cannot see it.
mounts = [
    p.name
    for p in (WEB / AUTH).glob("*.tsx")
    if "onApplyArrangement={" in strip_comments(p.read_text(encoding="utf-8"))
]
check(
    "D2 the re-arrange has exactly ONE mount",
    len(mounts) == 1,
    f"mounted in {mounts or 'nothing'}",
)
check(
    "D2 that mount is the Properties pane",
    mounts == ["StudioSurface.tsx"] and "onApplyArrangement" in pane,
    "the surface passes it; the pane renders it",
)
check(
    "D2 the pane renders the gallery at PAGE scope",
    "arrangements.map(" in pane and "ArrangementThumb" in pane,
)
check(
    "D2 the op is unchanged — no new write path (ADR-462 D1)",
    "onApplyArrangement={handleApplyArrangement}" in surface,
)
# ADR-466 D5 / ADR-519 D2.1: the member is owed both sentences BEFORE the
# gesture. The helper MOVED with its consumer; re-deriving it would be a second
# answer to one question.
check(
    "D2 the carry note moved with the gallery, and is not re-derived",
    "function arrangementCarryNote(" in pane
    and "arrangementCarryNote" not in toolbar,
)
check(
    "D2 the forewarn counts reach the gallery",
    "carriedCount" in pane and "groupCount" in pane,
)
# `planning` dressed the deleted button. If it did not follow the act, the
# member gets no signal during a 2-4s judgment — a silent stall.
check(
    "D2 the Refining… state followed the act it describes",
    "planning" in pane and "Refining" in pane and "Refining" not in toolbar,
)


# ── 3. Add is untouched — a different verb, correctly elsewhere ─────────────
#
# The two galleries render the same thumbs over the same vocabulary. If Add's
# pick ever routed to the re-arrange handler, "insert" and "re-lay" would have
# collapsed into one act and the deletion would have taken the wrong one.
insert_menu = strip_comments(read(AUTH + "StudioBlockInsertMenu.tsx"))
check(
    "Add still INSERTS (onPick), never re-lays",
    "onPick(" in insert_menu and "onApplyArrangement" not in insert_menu,
)
check(
    "the surface keeps the two verbs distinct",
    "handleAddArrangement" in surface and "handleApplyArrangement" in surface,
)


# ── 4. D4 — the sparkle measures against the CANVAS, not the window ─────────
check(
    "D4 the door accepts a housing bound",
    "hostRight" in gesture and "hostLeft" in gesture,
)
# The defect was arithmetic on `window.innerWidth`. Pinned as "the fit test
# prefers the declared bound", not as a literal line: any spelling that derives
# the room from the housing passes, and the bare-viewport one does not.
check(
    "D4 the fit test reads the housing before the viewport",
    re.search(
        r"const vw\s*=\s*typeof anchor\.hostRight === 'number'\s*\?\s*anchor\.hostRight\s*:\s*window\.innerWidth",
        gesture,
    )
    is not None,
    "an undeclared bound still falls back to the viewport, as before",
)
# Both flanks: a left-margin placement clamped at 0 would walk off the far side
# of a column that does not start at the window's edge.
check(
    "D4 the left margin respects the housing's left edge",
    "if (left > vLeft)" in gesture,
)
check(
    "D4 both hosts supply the bound",
    "hostLeft: r.left" in surface
    and "hostLeft: host.left" in strip_comments(read("components/text/ProseCanvas.tsx")),
    "Slides from the canvas column, Text from the editor's scroller",
)


if failures:
    print(f"FAIL ({len(failures)}):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("PASS — the Update door is deleted whole; the re-arrange has one home")
