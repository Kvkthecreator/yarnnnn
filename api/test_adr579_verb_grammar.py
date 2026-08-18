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
_check(
    "BOTH Studio mounts import the ONE grouping (the one-list rule, extended)",
    "groupBlockRows" in palette and "groupBlockRows" in insert_menu,
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
_check(
    "Update and Ask section headers render",
    ">\n            Update\n          </div>" in menu
    and ">\n            Ask\n          </div>" in menu,
)
# Structural order: Rewrite (Update's colleague row) must come BEFORE the Ask
# header; Check/Ask must come AFTER it — Check writes nothing and may not sit
# in a write section.
ask_at = menu.index(">\n            Ask\n          </div>")
# Anchor on the WIRED handlers, not the labels — a label also appears in the
# file's own doc comments, and an assertion matching a comment is the recorded
# failure class this suite exists to avoid.
_check(
    "Rewrite sits under Update (before Ask); Check/Ask sit under Ask",
    menu.index("run(onRewrite)") < ask_at
    and menu.index("run(onCheck)") > ask_at
    and menu.index("run(onAsk)") > ask_at,
)
_check(
    "the creation row speaks the grammar (New block…), wired to onInsert",
    re.search(r"onClick=\{\(\) => run\(onInsert\)\}>[\s\S]{0,40}New block…", menu)
    is not None,
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
recurrences = (API / "routes/recurrences.py").read_text()
_check(
    "the /repurpose route is gone — control: /export route still present",
    "repurpose" not in recurrences.lower() and "/export" in recurrences,
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
