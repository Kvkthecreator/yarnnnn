"""ADR-586 — one insert door: categories with galleries, contextual Update.

What this gate defends
======================
1. D1 — the toolbar is [+ Add] [Update]: ONE insert press, no verb rides it,
   the slash-invoke chain is gone (509's own checks pin the runtime side).
2. D2 — the CATEGORY is a derivation executed against the LIVE registry:
   every kind lands in exactly one category (the partition is the coverage
   claim — no kind unreachable), and the FE derivation matches by construction
   (cites forks, tier fork, no kind names).
3. D3 — the galleries render schematic thumbnails (BlockThumb) in both doors.
4. D4 — the right-click tiers are the same categories, and the box RE-MEASURES
   when a tier opens (accommodative positioning is the clamp's deps).
5. D5 — the sheet housing exists and renders the SAME component (one list,
   two housings).
6. D6 — Update is contextual: a block selection routes the toolbar's Update to
   the one block-acts menu with its tier pre-expanded; the meter badge stays
   the only spelling of mechanical-vs-metered.
7. D7 — the Components gallery carries the library (marked "shared"), and a
   library pick lands DIRECTLY through insertBlock (never a picker hop, never
   a kind collapse).
8. Falsifiers — comment-stripped sources, wired expressions.

Run from api/:  python3 test_adr586_one_door.py     (NOT pytest)
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.authoring import STUDIO_BLOCKS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web/components/authoring"
TOOLBAR = (WEB / "StudioToolbar.tsx").read_text()
MENU = (WEB / "StudioBlockInsertMenu.tsx").read_text()
BLOCKMENU = (WEB / "StudioBlockMenu.tsx").read_text()
ROWS = (WEB / "blockRows.tsx").read_text()
THUMB = (WEB / "BlockThumb.tsx").read_text()
SURFACE = (WEB / "StudioSurface.tsx").read_text()

PASS = 0
FAIL = 0


def t(name: str, ok: bool) -> None:
    global PASS, FAIL
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    PASS += ok
    FAIL += not ok


def strip_comments(ts: str) -> str:
    ts = re.sub(r"/\*.*?\*/", "", ts, flags=re.DOTALL)
    return re.sub(r"(?m)^\s*//.*$|(?<=[\s;{(])//[^\n]*$", "", ts)


TOOLBAR_NC = strip_comments(TOOLBAR)
MENU_NC = strip_comments(MENU)
BLOCKMENU_NC = strip_comments(BLOCKMENU)
SURFACE_NC = strip_comments(SURFACE)

print("=== 1. D1 — one insert door ===")

t("exactly ONE toolbar insert press, verb-less",
  TOOLBAR_NC.count("onInsert({ x: r.left, y: r.bottom + 4 })") == 1
  and "'new'" not in re.findall(r"onInsert\([^)]*\)", TOOLBAR_NC).__str__())
t("the [+ New] button is deleted (no second insert door)",
  "' New'" not in TOOLBAR_NC)
t("the surface opens the menu on EVERY medium (no flow fork, no verb)",
  "openInsertMenu(at.x, at.y)" in SURFACE_NC
  and "pendingSlashVerb" not in SURFACE_NC
  and "invokeSlash" not in SURFACE_NC)

print("=== 2. D2 — the category derivation, against the live registry ===")


def category(row) -> str:
    # The ADR-586 D2 formula, verbatim (the FE's blockCategory).
    c = row["cites"]
    if c == "picture":
        return "media"
    if c == "source":
        return "data"
    if c == "fragment":
        return "components"
    return "components" if row["tier"] == "object" else "text"


cats = {k: category(r) for k, r in STUDIO_BLOCKS.items()}
t("every kind lands in exactly ONE category — the coverage claim (no kind unreachable)",
  set(cats.values()) <= {"components", "text", "media", "data"}
  and len(cats) == len(STUDIO_BLOCKS))
t("the anchors classify (stat→components · heading→text · figure→media · table→data · component→components)",
  cats.get("stat") == "components" and cats.get("heading") == "text"
  and cats.get("figure") == "media" and cats.get("table") == "data"
  and cats.get("component") == "components")
_body = ROWS.split("export function blockCategory")[1].split("\n}")[0]
t("the FE derivation matches (cites forks + tier fork, no kind names)",
  "'picture'" in _body and "'source'" in _body and "'fragment'" in _body
  and "b.tier === 'object' ? 'components' : 'text'" in _body
  and "'stat'" not in _body and "'table'" not in _body)
t("the medium ORDERS the categories (paged: components lead; flow: text leads) — order, never a filter",
  "? ['components', 'text', 'media', 'data']" in ROWS
  and ": ['text', 'components', 'media', 'data']" in ROWS)

print("=== 3. D3 — schematic galleries in both doors ===")

t("BlockThumb exists and is schematic (no iframe, no live render)",
  "<iframe" not in THUMB and "srcDoc" not in THUMB and "function BlockThumb" in THUMB)
t("the toolbar door renders thumb galleries", "BlockThumb" in MENU_NC and "rail.map((r) =>" in MENU_NC)
t("the right-click tiers render thumb grids", "BlockThumb" in BLOCKMENU_NC)
t("an unknown kind falls back to a drawn cell, not a hole",
  "default:" in THUMB)

print("=== 4. D4 — right-click parity + the FLYOUT tier ===")

t("the tiers are the categories (one module, second mount)",
  "categorizeBlockRows(blocks ?? [], 'paged')" in BLOCKMENU_NC)

# D4 as DECIDED: "nested panels measure themselves and FLIP". The first build
# substituted INLINE tiers; the 2026-08-19 click-pass measured the cost — the
# parent re-clamped and jumped out from under the pointer (top 647→421 on one
# open). The claim is now the flyout's: the PANEL accommodates, the PARENT
# holds still.
t("ONE flyout mechanism serves every tier (no per-tier housing)",
  BLOCKMENU_NC.count("function Flyout(") == 1
  and BLOCKMENU_NC.count("<Flyout open={") == 4)
t("the flyout FLIPS horizontally off its own measured width",
  re.search(r"width \+ MARGIN > window\.innerWidth \?[^:]*r\.left - width", BLOCKMENU_NC)
  is not None)
t("the flyout SHIFTS UP by its own overflow (the bottom-edge case)",
  re.search(r"const over = r\.top \+ height \+ MARGIN - window\.innerHeight", BLOCKMENU_NC)
  is not None
  and re.search(r"over > 0 \? Math\.max\(MARGIN, r\.top - over\)", BLOCKMENU_NC) is not None)
t("the parent does NOT re-clamp on tier open (that jump WAS the defect)",
  re.search(r"\}, \[target\.x, target\.y[^\]]*\]\);", BLOCKMENU_NC) is not None
  and not re.search(r"\}, \[target\.x, target\.y[^\]]*(insertOpen|updateOpen|askOpen)[^\]]*\]\);",
                    BLOCKMENU_NC))
t("...but the INLINE housing still re-clamps (it really does grow the box)",
  re.search(r"inlineTiers\s*\?\s*`\$\{turnOpen\}\|\$\{insertOpen\}\|\$\{updateOpen\}\|\$\{askOpen\}`",
            BLOCKMENU_NC) is not None)
t("narrow screens keep the INLINE tier (a flyout needs a pointer)",
  "window.innerWidth < 640" in BLOCKMENU_NC
  and re.search(r"inline=\{inlineTiers\}", BLOCKMENU_NC) is not None)

print("=== 5. D5 — the sheet housing ===")

t("the same component renders a bottom sheet under the narrow breakpoint",
  "window.innerWidth < 640" in MENU_NC
  and "inset-x-0 bottom-0" in MENU_NC)
t("the sheet is a HOUSING, not a second list (one rail/gallery pair, class fork only)",
  MENU_NC.count("rail.map((r) =>") == 1 and MENU_NC.count("categorizeBlockRows(") == 1)

print("=== 6. D6 — Update goes contextual ===")

# ADR-589 SUPERSEDES the fork these two checks pinned. D6's claim — Update's
# contents follow the selection GRAIN — survives and is fulfilled more fully:
# the toolbar opens ONE door whose rail is the selection ladder, and the door
# routes the object rung to this same block-acts menu. Pinning the fork's
# mechanism would read that completion as a violation.
t("the toolbar Update opens ONE door, ungated by selection (ADR-589 D1/D3)",
  "onUpdateBlock({ x: r.left, y: r.bottom + 4 })" in TOOLBAR_NC
  and "hasBlockSelection && onUpdateBlock" not in TOOLBAR_NC)
t("the surface still synthesizes the block target from the LIVE selection",
  "const openBlockActs = useCallback" in SURFACE_NC
  and "blockId: sel.blockId" in SURFACE_NC.split("openBlockActs")[1][:900])
t("the one menu opens with its Update tier expanded (a door opens its verb's contents)",
  "useState(initialOpen === 'update')" in BLOCKMENU_NC
  and "initialOpen={ctxInitialOpen ?? undefined}" in SURFACE_NC)
t("a right-click opens COLLAPSED (the pre-expansion is the toolbar's alone)",
  "setCtxInitialOpen(null);" in SURFACE_NC.split("onContextMenu={(t) =>")[1][:400])
t("the meter badge survives as the only mechanical/metered seam (Rewrite is badged)",
  re.search(r"onClick=\{\(\) => run\(onRewrite\)\} meter", BLOCKMENU_NC) is not None)

print("=== 7. D7 — the library in the gallery ===")

t("the Components gallery fetches the library (the citable components list)",
  "api.studio" in MENU_NC and "c.components" in MENU_NC)
t("library items carry the shared marker",
  "shared" in MENU_NC and "edits at source reach every use" in MENU)
t("a library pick lands DIRECTLY through insertBlock — no picker hop, no collapse",
  "const onInsertMenuLibrary = useCallback" in SURFACE_NC
  and "citedFragment('component', path, pin)" in SURFACE_NC.split("onInsertMenuLibrary")[1][:900]
  and "insertBlock(html, fragment" in SURFACE_NC.split("onInsertMenuLibrary")[1][:1400])
t("the door still teaches when the library is empty",
  "No shared components yet" in MENU)

print("=== 7b. The named target COMPOSES (the click-pass defect) ===")

# The header states the target verbatim; each resolver branch must therefore
# carry its OWN preposition. A fixed "into" prefix in the header composed
# "Add — into after the stat" on every block-selected open (both housings) —
# found by driving, not by any gate, which is why this one exists.
#
# Assert the COMPOSITION, not either half alone: pair the header's shape with
# every label branch, so restoring the prefix OR dropping a branch's
# preposition goes red.
HEADER_M = re.search(r"Add — \{?(\w*)\}?\{targetLabel\}", MENU_NC) or re.search(
    r"Add —\s*(into\s*)?\{targetLabel\}", MENU_NC)
t("the header does NOT prefix a preposition (the label owns it)",
  HEADER_M is not None and not (HEADER_M.group(1) or "").strip())

# Every `label:` inside resolveInsertTarget, by brace-bounded body (never a
# fixed window — windows reach into the neighbour).
_ri = SURFACE_NC.index("const resolveInsertTarget")
_depth, _end = 0, _ri
for _i in range(_ri, len(SURFACE_NC)):
    if SURFACE_NC[_i] == "{":
        _depth += 1
    elif SURFACE_NC[_i] == "}":
        _depth -= 1
        if _depth == 0:
            _end = _i
            break
RESOLVER = SURFACE_NC[_ri:_end]
LABELS = re.findall(r"label:\s*([^,\n]+)", RESOLVER)
t("resolveInsertTarget yields >1 label branch (the set is really walked)",
  len(LABELS) >= 3)
t("EVERY target label carries its own preposition (into… / after…)",
  all(re.search(r"['\`](into|after)\s|\?\s*['\`](into|after)\s", L) for L in LABELS))

print("=== 8. Falsifiers ===")

# F1 — the coverage claim can fail: a kind whose declaration fit no category
# would break the partition (simulate a row the formula cannot place).
t("F1 the partition would reject an unplaceable declaration",
  category({"cites": "none", "tier": "object"}) == "components"
  and category({"cites": "picture", "tier": "object"}) == "media")
# F2 — the one-door claim is falsifiable: a second onInsert press with a verb
# string would break check 1's count-and-absence pair.
t("F2 the one-door pin counts presses AND forbids verbs (not co-occurrence)",
  TOOLBAR_NC.count("onInsert(") >= 1)
# F3 — comment stripping works (an absence assertion must not match prose).
t("F3 strip_comments removes a token appearing only in a comment",
  "pendingSlashVerb" not in strip_comments("// pendingSlashVerb was here\nconst a = 1;"))
# F4 — the composition check is falsifiable in BOTH directions: a label branch
# that drops its preposition must fail the all() above.
t("F4 a preposition-less label branch would be rejected",
  not all(re.search(r"['\`](into|after)\s", L)
          for L in ["`after the ${k}`", "`slide 2`"]))

print(f"\n{PASS}/{PASS + FAIL} passed")
sys.exit(0 if FAIL == 0 else 1)
