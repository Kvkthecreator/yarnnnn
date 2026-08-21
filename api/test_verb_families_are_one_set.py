"""A verb FAMILY is one set, whoever holds it — standing discipline gate.

Run: `python3 test_verb_families_are_one_set.py` from `api/`.
(Renamed from `test_file_verbs_are_one_set.py` 2026-08-21 — the discipline is
family-shaped, not file-verb-shaped. One gate, not one per family.)

WHY THIS EXISTS

The same defect landed three times in two days, each time as capability built
for ONE surface while the others silently lacked it:

  1. App exposure — six spellings in two languages; ADR-574 paused Docs and it
     stayed fully reachable for four days (fixed by ADR-592's `stage`).
  2. FILE verbs — `DeleteFile`/`MoveFile` lived in three rosters but not the
     lane, so a foreign LLM over MCP could delete a member's file while the
     member's own lane could not, AND SAID SO OUT LOUD.
  3. FOLDER verbs — the fan-out shipped (`services/folder_organize.py`,
     `360ea4c`) reachable only from the Files surface. A member asked their lane
     to delete a folder, was told the primitives "only operate file-by-file",
     and was advised to run `rm -rf` in a terminal — which would not have
     touched the files at all, the substrate being Postgres rather than disk.

Each roster was internally consistent every time. **The DIVERGENCE was the
defect, and a divergence has no home unless something asserts ACROSS surfaces.**

ADR-337 named the failure mode in advance, in the passage ruling out a `Bash`
primitive: *"it is also why missing verbs hurt so much here — there is no shell
escape hatch — which argues for COMPLETING THE VERB SET, not adding the hatch."*
A missing verb does not degrade gracefully here; it becomes a confident refusal
plus a workaround that corrupts the operator's mental model of where their
substrate lives.

THE DISCIPLINE

A verb FAMILY is one set. Any surface that reaches the workspace on a
principal's behalf holds the WHOLE family — or the narrowing is a deliberate
decision **with its reason recorded in `docs/architecture/primitives-matrix.md`**,
never an accident of which roster someone remembered to edit.

Both sides of every comparison are DERIVED. A hand-kept expected list would
reproduce the failure it guards (ADR-584: a pinned count reads growth as a
violation) — which is exactly what happened to ADR-535's "the five file verbs
are untouched" assertion, red the moment the set legitimately grew.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_API = Path(__file__).parent
_ROOT = _API.parent

PASSED = 0
FAILED: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    global PASSED
    if cond:
        print(f"  ok   {label}")
        PASSED += 1
    else:
        print(f"  FAIL {label}{(' — ' + detail) if detail else ''}")
        FAILED.append(label)


# ─────────────────────────────────────────────────────────────────────────────
# THE FAMILIES. Adding a family here is how the discipline extends: declare its
# members and its mutating half, and every assertion below covers it.
# ─────────────────────────────────────────────────────────────────────────────
FAMILIES: dict[str, dict[str, set[str]]] = {
    "file": {
        "all": {"ReadFile", "WriteFile", "EditFile", "DeleteFile", "MoveFile",
                "SearchFiles", "ListFiles"},
        # The half whose absence is a CAPABILITY GAP rather than a convenience.
        "mutating": {"WriteFile", "EditFile", "DeleteFile", "MoveFile"},
    },
    "folder": {
        "all": {"DeleteFolder", "MoveFolder"},
        "mutating": {"DeleteFolder", "MoveFolder"},
    },
}

#: Narrowings that are DELIBERATE. A verb listed here is exempt on that surface,
#: and the reason must also stand in primitives-matrix.md. An exemption is a
#: decision with a name on it, never a silent gap.
DELIBERATE_NARROWINGS: dict[tuple[str, str], str] = {
    ("lane", "DuplicateFile"):
        "a convenience over ReadFile+WriteFile, which the lane holds",
    ("mcp", "DuplicateFile"):
        "same; the interop roster stays minimal",
}

ALL_VERBS = {v for f in FAMILIES.values() for v in f["all"]}
ALL_MUTATING = {v for f in FAMILIES.values() for v in f["mutating"]}


print("\n[1] every declared verb is a real kernel primitive")

from services.primitives.registry import (  # noqa: E402
    CHAT_PRIMITIVES,
    FREDDIE_PRIMITIVES,
    HANDLERS,
)

for fam, spec in FAMILIES.items():
    missing = spec["all"] - set(HANDLERS)
    check(f"the {fam} family is fully dispatchable", not missing,
          f"no handler for: {sorted(missing)}")


print("\n[2] the LANE surface holds every family whole")

from services.lane_runner import (  # noqa: E402
    LANE_TOOL_NAMES,
    lane_tool_names,
    lane_tools_openai,
)

_lane = set(LANE_TOOL_NAMES)
for fam, spec in FAMILIES.items():
    want = {v for v in spec["all"]
            if ("lane", v) not in DELIBERATE_NARROWINGS}
    check(f"the lane holds the whole {fam} family",
          want <= _lane, f"the lane cannot: {sorted(want - _lane)}")

check("the lane's verb half carries ONLY declared family verbs",
      _lane <= ALL_VERBS, f"unexpected: {sorted(_lane - ALL_VERBS)}")

# ADR-467 D4's three-way agreement: DECLARED payload, EXECUTION allowlist, and
# PROMPT prose all derive from `lane_tool_names`, so they cannot disagree.
_declared = {t["function"]["name"] for t in lane_tools_openai()}
check("declared payload == allowlist (ADR-467 D4 agreement)",
      _declared == set(lane_tool_names()),
      f"payload∖allow={sorted(_declared - set(lane_tool_names()))} "
      f"allow∖payload={sorted(set(lane_tool_names()) - _declared)}")


print("\n[3] the CHAT + STEWARD rosters hold every mutating verb")

for label, roster in (("CHAT_PRIMITIVES", CHAT_PRIMITIVES),
                      ("FREDDIE_PRIMITIVES", FREDDIE_PRIMITIVES)):
    names = {t["name"] for t in roster if t.get("name")}
    check(f"{label} holds every mutating verb, every family",
          ALL_MUTATING <= names, f"missing: {sorted(ALL_MUTATING - names)}")


print("\n[4] ⚠️  THE COMPARISON — no surface is narrower than MCP")

# Derive what MCP can reach from its own dispatches, so this side cannot go
# stale either. `_names_a_folder` routes one interop verb to two grains, so a
# folder primitive appearing here is the binding working.
_mcp_src = (_API / "services" / "mcp_composition.py").read_text()
_mcp_reaches = set(re.findall(r'execute_primitive\(\s*[^,]+,\s*"(\w+)"', _mcp_src))
_mcp_verbs = _mcp_reaches & ALL_VERBS

check("the MCP surface reaches mutating verbs (the comparison is live)",
      bool(_mcp_verbs & ALL_MUTATING),
      "if this fails the gate compares against nothing — fix the derivation")

_gap = {v for v in (_mcp_verbs - _lane) if ("lane", v) not in DELIBERATE_NARROWINGS}
check("a foreign LLM cannot do to a member's substrate what the member's own "
      "lane cannot (no MCP-over-lane gap)",
      not _gap,
      f"MCP can {sorted(_gap)}; the member's lane cannot")

# The inverse also matters: the FILES SURFACE is a principal-facing surface too,
# and the folder fan-out lived only there for a day. Assert the lane reaches the
# same service the FE route does — one act, not two implementations.
_folder_prim = (_API / "services" / "primitives" / "folder.py").read_text()
_fe_route = (_API / "routes" / "documents.py").read_text()
for fn in ("trash_folder", "move_folder"):
    check(f"the lane's folder verb binds the SAME `{fn}` the Files route calls",
          fn in _folder_prim and fn in _fe_route)


print("\n[5] every mutating verb a member can call is one they can SEE")

from services.lane_runner import LANE_ARTIFACT_VERBS, artifact_path_from  # noqa: E402

_labels = (_ROOT / "web" / "components" / "chat-surface" / "toolLabels.ts").read_text()
for verb in sorted(ALL_MUTATING & _lane):
    check(f"{verb} has an operator-facing spelling (no camelCase leak)",
          f"{verb}:" in _labels)

# An artifact card is a deep link to a FILE to open. Verbs that leave no
# openable file must not be carded — the absence is reasoned, not incidental.
for verb, why in (
    ("DeleteFile", "nothing remains at the path"),
    ("DeleteFolder", "nothing remains at the path"),
    ("MoveFolder", "its result names a folder, which the viewer cannot render"),
):
    check(f"{verb} is not carded ({why})", verb not in LANE_ARTIFACT_VERBS)

check("DeleteFile resolves no artifact path even on success",
      artifact_path_from("DeleteFile",
                         {"success": True, "path": "/workspace/x.md"}) is None)
check("MoveFile IS carded, at its DESTINATION (its `path` is the dead source)",
      artifact_path_from(
          "MoveFile",
          {"success": True, "path": "/workspace/a.md", "new_path": "/workspace/b.md"},
      ) == "/workspace/b.md")


print("\n[6] a destructive verb is gated exactly like its file counterpart")

from services.primitives.permission import (  # noqa: E402
    GATE_QUEUEABLE_PRIMITIVES,
    _PATH_ADDRESSED_QUEUEABLE,
)
from services.primitives.workspace import _resolve_gate_paths  # noqa: E402

check("every mutating verb passes the ADR-307 gate",
      ALL_MUTATING <= GATE_QUEUEABLE_PRIMITIVES,
      f"ungated: {sorted(ALL_MUTATING - GATE_QUEUEABLE_PRIMITIVES)}")
check("every mutating verb is path-addressed (governance locks DENY)",
      ALL_MUTATING <= _PATH_ADDRESSED_QUEUEABLE,
      f"not path-addressed: {sorted(ALL_MUTATING - _PATH_ADDRESSED_QUEUEABLE)}")

# A move is dual-path at BOTH grains: a fan INTO locked territory is as much a
# breach as a fan OUT of it.
for verb in ("MoveFile", "MoveFolder"):
    check(f"{verb} lock-checks BOTH source and destination",
          len(_resolve_gate_paths(
              verb, {"path": "/workspace/a", "new_path": "/workspace/b"})) == 2)


print("\n[7] the deliberate narrowings are RECORDED, not merely coded")

_matrix = (_ROOT / "docs" / "architecture" / "primitives-matrix.md").read_text()
for (surface, verb), reason in DELIBERATE_NARROWINGS.items():
    check(f"`{verb}` off {surface} is explained in primitives-matrix.md",
          verb in _matrix,
          "an exemption in code with no reason in canon is a silent gap")


print()
if FAILED:
    print(f"verb-family parity gate RED — {PASSED} passed, {len(FAILED)} failed")
    for f in FAILED:
        print(f"    - {f}")
    sys.exit(1)
print(f"verb-family parity gate GREEN — {PASSED}/{PASSED}")
