"""ADR-589 — Update is a door over the selection matrix.

What this gate defends
======================
1. D1 — Update is ONE DOOR, not a selection fork. The rail is DERIVED from the
   selection ladder (scopeOf + the reported region), never a hand list.
2. D2 — the ladder is never SUBSET: every rung renders every open, and a rung
   that cannot be entered carries a `reason` and is not clickable.
3. D3 — `document` is always the top rung and always reachable; the toolbar's
   old no-selection branch (the slide-arrangement gallery) is DELETED, and the
   button is no longer hidden/disabled when nothing is selected.
4. D4 — arity adds NO rung (inherited from ADR-519 D4.1: the set is STATE).
5. D5 — the door is an ENTRANCE: every act routes to an op the pane also calls;
   every rung routes to an op or the dwell pane (ADR-613 removed the object
   rung's second-MENU route — the only rung that mounted one).
6. Cleanup — the moved gallery is not COPIED: the toolbar keeps no dead panel,
   no orphaned arrangement props, and no dismissal effect for a panel it no
   longer owns.
7. Falsifiers — comment-stripped sources, wired expressions.

Run from api/:  python3 test_adr589_update_matrix.py     (NOT pytest)
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web/components/authoring"
LADDER = (WEB / "updateLadder.ts").read_text()
DOOR = (WEB / "StudioUpdateMenu.tsx").read_text()
TOOLBAR = (WEB / "StudioToolbar.tsx").read_text()
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


LADDER_NC = strip_comments(LADDER)
DOOR_NC = strip_comments(DOOR)
TOOLBAR_NC = strip_comments(TOOLBAR)
SURFACE_NC = strip_comments(SURFACE)

print("=== 1. D1 — one door, a DERIVED rail ===")

t("the ladder is its own module (one derivation, not inline in the door)",
  (WEB / "updateLadder.ts").exists() and "export function buildLadder" in LADDER_NC)
t("the door RENDERS the derived ladder (never its own rung list)",
  "buildLadder({" in DOOR_NC and "rungs.map(" in DOOR_NC)
t("the rail reads scopeOf's answer — it does not re-derive the scope",
  "scope: PaneScope" in LADDER_NC and "scopeOf(" not in LADDER_NC)
t("the surface hands the door scopeOf's live answer",
  re.search(r"scope=\{scopeOf\(", SURFACE_NC) is not None)
t("Update opens the DOOR (the old fork's block branch is gone from the toolbar)",
  "onUpdateBlock={openUpdateDoor}" in SURFACE_NC
  and "openUpdateForSelection" not in SURFACE_NC)

print("=== 2. D2 — the ladder is never subset ===")

# Every rung the builder can emit must be pushed unconditionally OR pushed on
# both branches of a fork — never dropped. Assert the reason-carrying shape.
t("unreachable rungs carry a REASON (they are stated, not filtered)",
  LADDER_NC.count("reason:") >= 3)
t("the door renders greyed-and-unclickable, never hidden",
  "aria-disabled={!!r.reason}" in DOOR_NC
  and re.search(r"if \(r\.reason\) return;", DOOR_NC) is not None)
# The rail must map the ladder WHOLE. A `.filter(` between `rungs` and `.map(`
# is exactly the D2 violation. Written to FAIL rather than crash when the
# expression is absent — a gate that raises aborts the run and hides every
# check after it, which reads as a broken suite instead of a red assertion.
_rail = re.search(r"\{rungs([\s\S]{0,60}?)\.map\(", DOOR_NC)
t("the rail maps the ladder WHOLE (no filter before render)",
  _rail is not None and ".filter(" not in _rail.group(1))

print("=== 3. D3 — document is always present, always reachable ===")

# Brace-bound buildLadder and assert the document push is UNCONDITIONAL: it must
# precede any `if` in the function body.
_i = LADDER_NC.index("export function buildLadder")
_depth, _end = 0, _i
for _k in range(_i, len(LADDER_NC)):
    if LADDER_NC[_k] == "{":
        _depth += 1
    elif LADDER_NC[_k] == "}":
        _depth -= 1
        if _depth == 0:
            _end = _k
            break
BUILD = LADDER_NC[_i:_end]
_doc_at = BUILD.index("scope: 'document'")
_first_if = BUILD.index("if (") if "if (" in BUILD else len(BUILD)
t("the document rung is pushed UNCONDITIONALLY (before any branch)",
  _doc_at < _first_if)
t("the document rung never carries a reason (it is always enterable)",
  not re.search(r"scope: 'document'[\s\S]{0,200}?reason:", BUILD))
t("the empty case opens on the artifact, not a page gallery",
  "initialRung" in DOOR_NC and "export function initialRung" in LADDER_NC)
t("the toolbar's Update is no longer hidden/disabled with no selection",
  "{onUpdateBlock && (" in TOOLBAR_NC
  and "disabled={!!planning}" in TOOLBAR_NC
  and "!hasBlockSelection && !hasPageAnchor" not in TOOLBAR_NC)

print("=== 4. D4 — arity adds no rung (ADR-519 D4.1, inherited) ===")

# The claim is that NO rungs.push is CONDITIONED on the set. Assert per-push:
# no push statement mentions setCount in its own expression.
_pushes = re.findall(r"rungs\.push\(\{[\s\S]*?\}\);", BUILD)
t("no rung is built from the set (per-push, not a window)",
  len(_pushes) >= 4 and all("setCount" not in p for p in _pushes))
t("the set shows as the WITHDRAWAL, on the pane",
  "setCount > 1" in DOOR_NC and "one object at a time" in DOOR_NC)

print("=== 5. D5 — the door is an entrance, never a second write path ===")

t("the object rung routes to the DWELL like every other rung (ADR-613)",
  "onBlockActs" not in DOOR_NC
  and "openBlockActs" not in SURFACE_NC
  and "ctxInitialOpen" not in SURFACE_NC)
t("no rung mounts a second MENU (the door opens the pane, or acts)",
  "onBlockActs" not in DOOR_NC and "BlockMenu" not in DOOR_NC)
t("every other rung's act opens the pane (the dwell), not a private control",
  DOOR_NC.count("onOpenPane") >= 2 and "setRightTab('design')" in SURFACE_NC)
t("re-arrange still calls the SAME apply op",
  "onApplyArrangement={handleApplyArrangement}" in SURFACE_NC
  and "onApplyArrangement(a)" in DOOR_NC)

print("=== 6. Cleanup — moved, not copied ===")

t("the toolbar's layout PANEL is deleted (no second gallery)",
  "open === 'layout'" not in TOOLBAR_NC and "ArrangementThumb" not in TOOLBAR_NC)
t("the toolbar's panel state + dismissal effect are deleted with it",
  "setOpen" not in TOOLBAR_NC and "yarnnn-canvas-press" not in TOOLBAR_NC)
# Bound to the COMPONENT's props interface — `carriedCount`/`groupCount` are
# also parameters of `arrangementCarryNote`, the helper that rightly still lives
# here and is imported BY the door. A file-wide absence check called that a
# violation; the claim is about the toolbar's own surface.
_props = re.search(r"interface StudioToolbarProps \{[\s\S]*?\n\}", TOOLBAR_NC)
t("the toolbar's PROPS keep no orphaned gallery surface",
  _props is not None and all(p not in _props.group(0) for p in
      ("currentArrange", "carriedCount", "groupCount", "onApplyArrangement")))
t("the gallery has exactly ONE render home now (the door)",
  DOOR_NC.count("<ArrangementThumb") == 1 and "<ArrangementThumb" not in TOOLBAR_NC)
t("the door carries its own dismissal, including the iframe bridge",
  "yarnnn-canvas-press" in DOOR_NC)

print("=== 7. Falsifiers ===")

t("F1 the rung set is really walked (not an empty match passing vacuously)",
  BUILD.count("rungs.push") >= 4)
t("F2 the reason assertion tests the ASSIGNMENT, not the identifier",
  re.search(r"reason:\s*'[^']+'", LADDER_NC) is not None)
t("F3 strip_comments removes a token appearing only in a comment",
  "open === 'layout'" not in strip_comments("// open === 'layout' was here\nconst a = 1;"))

print(f"\n{PASS}/{PASS + FAIL} passed")
sys.exit(0 if FAIL == 0 else 1)
