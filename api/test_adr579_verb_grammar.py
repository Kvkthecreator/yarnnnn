"""ADR-579 — three verbs that write, one act that doesn't (ADD · NEW · UPDATE, ASK).

Checks, script-style (NOT pytest):
  D4  both palettes group the ONE list by provenance, derived from `cites` —
      never a hand-kept kind list — and both Studio mounts import the ONE
      grouping module.
  D5  the right-click menu sections name the VERB, never the mechanism; Check/
      Ask sit outside any write-named section; the creation row says New.
  D9  the fossils are ABSENT — with presence controls beside every absence, so
      an empty file or a moved definition cannot read as compliance.

Run:  cd api && python3 test_adr579_verb_grammar.py
"""

import pathlib
import re
import sys

API = pathlib.Path(__file__).parent
WEB = API.parent / "web"

checks = 0
failures = []


def _check(name: str, ok: bool, detail: str = ""):
    global checks
    checks += 1
    mark = "ok  " if ok else "FAIL"
    print(f"  {mark}  {name}" + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


print("── D4: one provenance grouping, derived from `cites`, two mounts ──")

rows = (WEB / "components/authoring/blockRows.tsx").read_text()
_check(
    "groupBlockRows exists and derives from `cites` (no hand list of kinds)",
    "export function groupBlockRows" in rows
    and "cites ?? 'none'" in rows
    # A hand list would name kinds; the module must not enumerate picker kinds.
    and "'figure'" not in rows.split("export function groupBlockRows")[1]
    and "'gallery'" not in rows.split("export function groupBlockRows")[1],
)
palette = (WEB / "components/authoring/StudioSlashPalette.tsx").read_text()
insert_menu = (WEB / "components/authoring/StudioBlockInsertMenu.tsx").read_text()
menu_src = (WEB / "components/authoring/StudioBlockMenu.tsx").read_text()
_check(
    # ADR-586 re-house: the palette keeps the family grouping (the located
    # fast path); both menus render the CATEGORY tier — all from the ONE
    # module (blockRows), so the doors still cannot drift apart.
    "ALL THREE Studio mounts import the ONE grouping module (the one-list rule, extended)",
    "groupBlockRows" in palette
    and "categorizeBlockRows" in insert_menu
    and "categorizeBlockRows" in menu_src,
)
_check(
    "the palette reports the FLAT grouped order up (keyboard index = rendered order)",
    "groups.flatMap((g) => g.items)" in palette and "onItemsChange(items)" in palette,
)

slash = (WEB / "components/text/SlashMenu.tsx").read_text()
# The Text groups are contiguous in declaration order — parse the actual rows.
groups_seq = re.findall(r"group:\s*'(new|add)'", slash.split("SLASH_ITEMS")[1])
_check(
    "Text SLASH_ITEMS carry groups, contiguous, New leading",
    len(groups_seq) >= 10
    and groups_seq[0] == "new"
    and groups_seq[-1] == "add"
    and "".join(groups_seq).count("newadd".replace("new", "n").replace("add", "a")) <= 1
    # contiguity: once 'add' starts, 'new' never recurs
    and "new" not in groups_seq[groups_seq.index("add"):],
)
_check(
    "the two ADD rows are the picker-backed kinds (image · csvtable)",
    re.search(r"id: 'image'[^\n]*group: 'add'", slash) is not None
    and re.search(r"id: 'csvtable'[^\n]*group: 'add'", slash) is not None,
)
toolbar = (WEB / "components/text/MarkdownToolbar.tsx").read_text()
_check(
    "the Text toolbar's last group is the ADD pair (image · csvtable together)",
    re.search(
        r"\[\s*\{ icon: ImageIcon[^\]]*csvtable[^\]]*\},\s*\]\s*,?\s*\];",
        toolbar,
    )
    is not None,
)

print("── D5: sections name the VERB, never the mechanism ──")

menu = (WEB / "components/authoring/StudioBlockMenu.tsx").read_text()
_check(
    "the mechanism-named header is gone",
    "Write with AI" not in menu,
)
# ADR-613: the ASK tier is DELETED. Every row in it was judged (Check, Ask),
# and the judged act left this menu for the selection-anchored gesture — a tier
# whose whole contents moved is not kept as an empty shell. D5's rule is
# untouched and still gated: the tier that REMAINS names its verb.
_check(
    "Update is the menu's verb TIER (named for the verb, expandable)",
    '<span className="truncate">Update</span>' in menu and "setUpdateOpen" in menu,
)
_check(
    "the Ask tier is gone, state and all (ADR-613)",
    '<span className="truncate">Ask</span>' not in menu and "setAskOpen" not in menu,
)
# ADR-613 replaced the ORDER claim with an ABSENCE claim. The order existed to
# keep Check (which writes nothing) out of a write tier; with all three judged
# verbs gone from this menu there is no ordering left to defend here, and the
# separation it protected now lives in the gesture (one act, no tier at all).
_check(
    "no judged verb is wired in this menu any more",
    "run(onRewrite)" not in menu
    and "run(onCheck)" not in menu
    and "run(onAsk)" not in menu,
)
_check(
    # ADR-586 D4 — the located tiers are the CATEGORIES now; the landing law
    # (per-kind, through the surface's one landing) is what this check pins.
    "the located category tiers render the served vocabulary and land per-kind",
    "categorizeBlockRows(blocks ?? [], 'paged')" in menu
    and "run(() => onInsertKind(b.kind, b.label, b.fragment))" in menu,
)
insert_menu_src = insert_menu
_check(
    # ADR-586 D1 superseded the verb doors: ONE door, categories inside, and
    # the page grain (the Slide gallery) rides INSIDE that one door — the
    # D6.a law (a door opens its own contents) kept one level up.
    "the ONE door carries the page grain inside it (no verb filter survives)",
    "verb" not in insert_menu_src.split("interface StudioBlockInsertMenuProps")[1].split("}")[0]
    and "pageSection" in insert_menu_src
    and "ArrangementThumb" in insert_menu_src,
)

print("── D9: the fossils are absent (with presence controls) ──")

_check(
    "primitives/repurpose.py is deleted",
    not (API / "services/primitives/repurpose.py").exists(),
)
registry = (API / "services/primitives/registry.py").read_text()
_check(
    "RepurposeOutput absent from the registry — control: Compose still present",
    "RepurposeOutput" not in registry
    and "repurpose" not in registry
    and '"Compose"' in registry,  # presence control: the file is the real registry
)
# routes/recurrences.py is DELETED outright (ADR-603 D5, 2026-08-24), which
# subsumes "the /repurpose route is gone" — assert the deletion holds.
_check(
    "the recurrence routes (once /repurpose's home) stay deleted",
    not (API / "routes/recurrences.py").exists(),
)
syscalls = (API / "services/system_calls.py").read_text()
_check(
    'the "repurpose" system-call row is gone — control: web_search_continuation present',
    '"repurpose"' not in syscalls and '"web_search_continuation"' in syscalls,
)
recipes = (API / "services/derive_recipes.py").read_text()
_check(
    "context-brief recipe is gone — control: design-system/prd/deck present",
    "context-brief" not in recipes
    and '"design-system"' in recipes
    and '"prd"' in recipes
    and '"deck"' in recipes,
)

print()
if failures:
    print(f"FAIL: {checks - len(failures)}/{checks} checks")
    sys.exit(1)
print(f"ADR-579 gate GREEN — {checks}/{checks}")
