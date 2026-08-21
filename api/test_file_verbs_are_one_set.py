"""The file-verb set is ONE SET, whoever holds it — standing discipline gate.

Run: `python3 test_file_verbs_are_one_set.py` from `api/`.

WHY THIS EXISTS (2026-08-21)

A member asked their chat lane to delete two config files and was told:

    "as an AI within this workspace, my available file tools (ReadFile,
     EditFile, WriteFile, SearchFiles, ListFiles) do not include a file
     deletion (rm) primitive."

True of that surface, and false of the system. `DeleteFile` and `MoveFile` had
shipped in ADR-337 and were live in THREE other rosters — `CHAT_PRIMITIVES`,
`FREDDIE_PRIMITIVES`, and (as `delete`/`move`) the MCP interop surface bound by
ADR-545. The net effect: **a foreign LLM connected over MCP could delete a file
in the member's workspace while the member's own lane could not.**

Nothing caught it because no gate compared the rosters. Each was internally
consistent; the DIVERGENCE was the defect, and a divergence has no home unless
something asserts across the surfaces.

THE DISCIPLINE

The file-verb family (`ReadFile` · `WriteFile` · `EditFile` · `DeleteFile` ·
`MoveFile` · `SearchFiles` · `ListFiles`) is ONE SET. Any surface that reaches
the workspace filesystem on a principal's behalf holds the WHOLE family, or the
narrowing is a deliberate, stated decision with a reason recorded here — never
an accident of which roster someone remembered to edit.

This is a COMPARISON gate, deliberately: it derives both sides and asserts they
agree, rather than pinning either to a literal. A hand-kept expected list would
reproduce the very failure it guards (the ADR-584 lesson: a pinned count reads
growth as a violation).
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


#: The family. Membership is a KERNEL fact (each has a primitive in
#: services/primitives/workspace.py); this names it once so every assertion
#: below derives from the same set.
FILE_VERBS = {
    "ReadFile", "WriteFile", "EditFile", "DeleteFile", "MoveFile",
    "SearchFiles", "ListFiles",
}

#: The MUTATING half — the verbs whose absence is a capability gap rather than
#: a convenience. These are what an asymmetry actually costs a member.
MUTATING_FILE_VERBS = {"WriteFile", "EditFile", "DeleteFile", "MoveFile"}


print("\n[1] every file verb is a real kernel primitive")

from services.primitives import workspace as ws_primitives  # noqa: E402

_defined = {
    t["name"]
    for name in dir(ws_primitives)
    if name.endswith("_TOOL")
    for t in [getattr(ws_primitives, name)]
    if isinstance(t, dict) and t.get("name")
}
check("all seven file verbs have a primitive definition",
      FILE_VERBS <= _defined,
      f"missing: {sorted(FILE_VERBS - _defined)}")


print("\n[2] the LANE surface holds the whole family")

from services.lane_runner import (  # noqa: E402
    LANE_TOOL_NAMES,
    lane_tool_names,
    lane_tools_openai,
)

_lane = set(LANE_TOOL_NAMES)
check("the lane's file half IS the family (no verb missing)",
      FILE_VERBS <= _lane,
      f"the lane cannot: {sorted(FILE_VERBS - _lane)}")
check("the lane's file half carries ONLY file verbs",
      _lane <= FILE_VERBS,
      f"unexpected: {sorted(_lane - FILE_VERBS)}")

# ADR-467 D4's three-way agreement, restated over the widened set: the DECLARED
# payload, the EXECUTION allowlist, and the PROMPT prose all derive from
# `lane_tool_names`. Asserting the payload covers the declared/allowlist pair;
# the prose interpolates the same call, so it cannot drift.
_declared = {t["function"]["name"] for t in lane_tools_openai()}
check("declared payload == allowlist (ADR-467 D4 agreement)",
      _declared == set(lane_tool_names()),
      f"payload∖allow={sorted(_declared - set(lane_tool_names()))} "
      f"allow∖payload={sorted(set(lane_tool_names()) - _declared)}")


print("\n[3] the CHAT + STEWARD rosters hold the whole family")

from services.primitives.registry import (  # noqa: E402
    CHAT_PRIMITIVES,
    FREDDIE_PRIMITIVES,
)

for label, roster in (("CHAT_PRIMITIVES", CHAT_PRIMITIVES),
                      ("FREDDIE_PRIMITIVES", FREDDIE_PRIMITIVES)):
    names = {t["name"] for t in roster if t.get("name")}
    check(f"{label} holds every mutating file verb",
          MUTATING_FILE_VERBS <= names,
          f"missing: {sorted(MUTATING_FILE_VERBS - names)}")


print("\n[4] ⚠️  THE COMPARISON — no surface is narrower than MCP")

# The MCP interop surface binds kernel verbs (ADR-543/545). Derive which kernel
# primitives it can reach from the composition module's own dispatches, so this
# side of the comparison cannot go stale either.
_mcp_src = (_API / "services" / "mcp_composition.py").read_text()
_mcp_reaches = {
    m for m in re.findall(r'execute_primitive\(\s*[^,]+,\s*"(\w+)"', _mcp_src)
}
_mcp_file_verbs = _mcp_reaches & FILE_VERBS
check("the MCP surface reaches mutating file verbs (the comparison is live)",
      bool(_mcp_file_verbs & MUTATING_FILE_VERBS),
      "if this fails the gate is comparing against nothing — fix the derivation")

# THE ASSERTION THIS FILE EXISTS FOR.
_gap = _mcp_file_verbs - _lane
check("a foreign LLM cannot do to the member's files what the member's own "
      "lane cannot (no MCP-over-lane gap)",
      not _gap,
      f"MCP can {sorted(_gap)}; the member's lane cannot — the 2026-08-21 defect")


print("\n[5] a mutating verb the member can call is one they can SEE")

from services.lane_runner import LANE_ARTIFACT_VERBS, artifact_path_from  # noqa: E402

_labels = (_ROOT / "web" / "components" / "chat-surface" / "toolLabels.ts").read_text()
for verb in sorted(MUTATING_FILE_VERBS & _lane):
    check(f"{verb} has an operator-facing spelling (no camelCase leak)",
          f"{verb}:" in _labels)

# DeleteFile is deliberately NOT an artifact verb: a card is a deep link to a
# file to OPEN, and after a delete there is nothing there. It still shows as a
# labelled tool row. This asserts the REASONING, not merely the absence.
check("DeleteFile is not carded (a card would deep-link a deleted path)",
      "DeleteFile" not in LANE_ARTIFACT_VERBS)
check("…and it resolves no artifact path even on success",
      artifact_path_from("DeleteFile",
                         {"success": True, "path": "/workspace/x.md"}) is None)

# MoveFile IS carded, but must point where the file now LIVES. Its result
# carries both paths and `path` is the source, which no longer exists.
check("MoveFile is carded at its DESTINATION, not its source",
      artifact_path_from(
          "MoveFile",
          {"success": True, "path": "/workspace/a.md", "new_path": "/workspace/b.md"},
      ) == "/workspace/b.md")


print()
if FAILED:
    print(f"file-verb parity gate RED — {PASSED} passed, {len(FAILED)} failed")
    for f in FAILED:
        print(f"    - {f}")
    sys.exit(1)
print(f"file-verb parity gate GREEN — {PASSED}/{PASSED}")
