"""ADR-619 — the block menu groups by family, and the judged act has two entrances.

Two invariants, each of which fails silently if it drifts.

  1. FAMILY. Copy · Duplicate · Delete all take THIS BLOCK and do something to
     it or to a copy of it. Copy used to sit above `Paste here`, which reads as
     a clipboard pair — but Paste's subject is the clipboard, not the block, so
     the pairing split a family of three and put the odd one in. Copy is also
     NOT tier-gated the way the other two are (ADR-525 D5: on flow, Duplicate
     and Delete are enclosure verbs the platform owns; copying a paragraph is
     always meaningful), so "grouped" must not become "gated with them".

  2. ONE WRITE PATH. The floating gesture (ADR-612/613) and this menu's Rewrite
     row are deliberately the SAME workflow — the operator's reason: a member
     may open the menu and then decide to rewrite. That is safe only while both
     doors compose their seed at ONE site. Two producers would be two acts
     wearing one name, and nothing at build time would say so.

     The menu reads its own context target, never the selection RECT: the rect
     arrives from the runtime asynchronously, so a row keyed on it would be
     inert depending on message timing — the silent no-op class this same
     session fixed in the in-canvas "+ Add".

ADR-613's substance is unchanged and still gated in its own file: the four-hop
ladder, the `meter` discriminator, and the second-menu route stay deleted. What
this ADR amends is the ACT'S REACHABILITY, never its plumbing.

Run: python3 test_adr619_menu_families.py   (from api/)
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


def strip_comments(src: str) -> str:
    """Read CODE. Every deletion site here carries a tombstone comment naming
    what it deleted ("the UPDATE tier is DELETED"), so a comment-blind grep
    would find the word `Update` and read the explanation as the thing."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    return re.sub(r"^\s*//.*$", "", src, flags=re.MULTILINE)


AUTH = WEB / "components/authoring"
menu = strip_comments((AUTH / "StudioBlockMenu.tsx").read_text())
surface = strip_comments((AUTH / "StudioSurface.tsx").read_text())


# ── 1. The unit verbs are ONE contiguous family ─────────────────────────────
for row in ("Copy", "Duplicate", "Delete"):
    check(f"the menu still offers {row}", f"run(on{row})" in menu)

_i = {r: menu.index(f"run(on{r})") for r in ("Copy", "Duplicate", "Delete") if f"run(on{r})" in menu}
check(
    "Copy · Duplicate · Delete read in that order",
    len(_i) == 3 and _i["Copy"] < _i["Duplicate"] < _i["Delete"],
)
# The defect's exact shape: Paste BETWEEN Copy and the pair it belongs to.
# Paste keeps its place in the menu — it simply must not split the family.
if len(_i) == 3 and "run(onPaste)" in menu:
    _p = menu.index("run(onPaste)")
    check(
        "Paste does not sit inside the family",
        not (_i["Copy"] < _p < _i["Delete"]),
        "Paste's subject is the clipboard, not this block",
    )

# Grouped, but NOT gated together: Copy must stay outside the text-tier guard
# that correctly withholds the two enclosure verbs.
_gate = menu.find("{!isTextTier && (")
check("the text-tier guard still exists", _gate != -1)
if _gate != -1 and len(_i) == 3:
    check(
        "Copy renders OUTSIDE the text-tier guard",
        _i["Copy"] < _gate,
        "copying a paragraph is always meaningful (ADR-525 D5 gates only the enclosure verbs)",
    )
    check(
        "Duplicate and Delete stay INSIDE it",
        _i["Duplicate"] > _gate and _i["Delete"] > _gate,
    )


# ── 2. The Update tier is gone, and its rows survive FLAT ───────────────────
check(
    "no tier named Update survives",
    "updateOpen" not in menu
    and '<span className="truncate">Update</span>' not in menu,
)
# Deleting the tier must not delete its rows — they are three real families
# that simply had no business under one label.
for row, call in (
    ("Turn into", "onTurnInto("),
    ("Move up", "run(onMoveUp)"),
    ("Move down", "run(onMoveDown)"),
    ("Bring forward", "run(onBringForward)"),
    ("Bring backward", "run(onBringBackward)"),
):
    check(f"{row} survived the tier's deletion", call in menu)
# The inline housing re-clamps off a scalar key; a stale member keeps a deleted
# tier alive in the dependency and is exactly how `askOpen` outlived its rows.
_key = re.search(r"inlineTiers\s*\?\s*`([^`]*)`", menu)
check("the inline re-clamp key is still derived from live tiers", _key is not None)
if _key:
    check(
        "the deleted tier left the re-clamp key",
        "updateOpen" not in _key.group(1) and "askOpen" not in _key.group(1),
    )


# ── 3. ONE write path under two entrances ───────────────────────────────────
#
# The invariant is the PRODUCER COUNT, not which doors exist. A future third
# entrance is fine; a second place that composes a rewrite seed is not.
check(
    "the surface composes the rewrite seed at exactly ONE site",
    surface.count("seedComposer('', {") == 1,
    f"found {surface.count(chr(39) + chr(39) + ', {')} — two producers is two acts under one name",
)
check(
    "that site is the shared producer both doors call",
    "const seedRewrite = useCallback(" in surface,
)
for door in ("rewriteSelection", "menuRewrite"):
    check(f"{door} routes through it", f"{door} = useCallback(" in surface)
_body = re.search(r"const menuRewrite = useCallback\((.*?)\n  \);", surface, flags=re.DOTALL)
check("menuRewrite is still readable by the gate", _body is not None)
if _body:
    check(
        "the menu door calls the shared producer rather than composing its own",
        "seedRewrite(" in _body.group(1) and "seedComposer" not in _body.group(1),
    )
    # The timing rule: the menu reads its OWN target. Keying on the rect makes
    # the row inert depending on when the runtime's message lands.
    check(
        "the menu door reads its context target, never the selection rect",
        "ctxMenu" in _body.group(1)
        and "selRect" not in _body.group(1)
        and "gestureTarget" not in _body.group(1),
        "a rect-keyed row is inert on message timing — the silent no-op class",
    )
# And the menu may only reach it through the prop — never by importing or
# re-implementing a seed of its own.
check(
    "the menu offers Rewrite only as a callback it was handed",
    ("Rewrite" not in menu) or ("onRewrite" in menu and "seedComposer" not in menu),
)
check(
    "the surface actually wires it",
    "onRewrite={menuRewrite}" in surface,
)


# ── 4. ADR-613's deletions are untouched ────────────────────────────────────
check(
    "the meter discriminator stays deleted (ADR-613 D2)",
    "meter" not in menu.replace("metered", "").replace("MECHANICAL", ""),
)
check(
    "Check and Ask stay deleted (ADR-613 D1)",
    "Check this" not in menu and "Ask about this" not in menu and "askOpen" not in menu,
)
check(
    "the second-menu route stays deleted (ADR-613 D5)",
    "initialOpen" not in menu and "ctxInitialOpen" not in surface,
)


if failures:
    print(f"FAIL ({len(failures)}):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("PASS — one family per group, one write path under two entrances")
