"""ADR-407 Phase 5, amended — the workspace switcher PINS what the member picked.

The defect this gate closes
---------------------------
`UserMenu.handleSwitchWorkspace` branched on the ROLE:

    if (m.role === 'owner') clearActiveWorkspace();
    else setActiveWorkspace(m.workspace_id);

with the comment "absent header = server resolves the owner workspace". That
is true only for a principal owning EXACTLY ONE workspace. Ownership has never
been capped (there is no unique constraint on `workspaces.owner_id`) and since
deliberate genesis a principal can own several — at which point clearing the
pin resolves their OLDEST workspace, not the one they clicked.

So picking a second OWNED workspace put the member straight back into the
first. The switcher showed the new name and a checkmark, every read served the
old workspace, and a document created "in" the new one was written to the old.

Receipted on prod 2026-09-13: after clicking "SK Personal" in the switcher,
`localStorage['yarnnn.active-workspace']` was still `null`, and
`/api/workspace/file` resolved `d5b9029b` (yarnnn workspace) rather than
`9dc80079` (SK Personal).

This shipped ALONGSIDE the ADR-548 D9 write-binding defect — two independent
bugs presenting as one symptom ("nothing exists at operation/…"), which is why
fixing the write path alone did not fix the flow. Whenever two layers can
disagree about the acting workspace, expect BOTH to be wrong before believing
either is right.

Why the existing gates could not see it: `test_adr407_phase5_binding_ux.py`
asserts `"clearActiveWorkspace" in menu or "setActiveWorkspace" in menu` — an
OR that passes on either spelling, so it is green for the bug AND the fix.
`test_adr499_stale_workspace_pin.py` only reads `client.ts`. A check that
cannot fail is not a check.

Falsified against the real pre-fix source before landing.

Run: python3 test_adr407_switcher_pins_the_pick.py   (script-style, like its
neighbours — note `pytest` reports "no tests ran" on these files.)
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(REPO, "web")

_passed = 0
_failed = 0


def record(name: str, ok: bool, why: str = "") -> None:
    global _passed, _failed
    if ok:
        _passed += 1
        print(f"PASS  {name}")
    else:
        _failed += 1
        print(f"FAIL  {name}  {why}")


menu_path = os.path.join(WEB, "components/shell/UserMenu.tsx")
record("UserMenu.tsx exists", os.path.exists(menu_path), "re-point this gate")
menu = open(menu_path).read() if os.path.exists(menu_path) else ""

# Isolate the handler, so a `clearActiveWorkspace` mentioned anywhere ELSE in
# the file (a comment, a different affordance) cannot make this pass or fail
# by accident. Comments are stripped FIRST: a substring check that matches its
# own explanatory prose is a recurring failure in this repo, and the comment
# above the fix quotes the buggy line verbatim.
body = ""
start = menu.find("const handleSwitchWorkspace")
if start != -1:
    depth, i, started = 0, start, False
    while i < len(menu):
        if menu[i] == "{":
            depth += 1
            started = True
        elif menu[i] == "}":
            depth -= 1
            if started and depth == 0:
                break
        i += 1
    body = menu[start : i + 1]

record("handleSwitchWorkspace found", bool(body), "the handler was renamed — re-point")

code = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
code = re.sub(r"//[^\n]*", "", code)

record(
    "the switcher PINS the picked workspace",
    "setActiveWorkspace(m.workspace_id)" in code,
    "the member's explicit pick must be pinned, never inferred",
)
record(
    "the switcher never CLEARS the pin on a switch",
    "clearActiveWorkspace" not in code,
    "clearing resolves the OLDEST owned workspace, not the one clicked — "
    "a member owning two workspaces cannot reach the second",
)
record(
    "the pin does not branch on the role",
    "role ===" not in code and "role!==" not in code.replace(" ", ""),
    "which workspace is pinned is the member's PICK, never their species "
    "(ADR-405: permission is a grant, never a species rule)",
)

# Deletion still clears — the workspace is gone, so there is nothing to pin.
# Asserted so the fix above is not over-applied to the one case where clearing
# IS correct.
del_path = os.path.join(WEB, "components/workspace-concepts/WorkspaceDeleteCard.tsx")
if os.path.exists(del_path):
    record(
        "deleting a workspace still CLEARS the pin",
        "clearActiveWorkspace" in open(del_path).read(),
        "a deleted workspace has nothing to pin to",
    )
else:
    record("WorkspaceDeleteCard.tsx exists", False, "re-point this gate")

print("=" * 62)
print(f"ADR-407 switcher-pin gate: {_passed}/{_passed + _failed} passed, {_failed} failed")
print("=" * 62)
sys.exit(1 if _failed else 0)
