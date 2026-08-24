"""The streaming step seam: a tool round names its SUBJECT, not just its verb
(2026-08-25).

Script-style (python3, from api/). Guards three things that were each a real
defect before this seam existed:

  1. `tool_subject_from` exposes ONE named key per verb — never the raw
     argument dict. A future primitive gaining a field must not be able to
     reach a member's transcript just by existing.
  2. The subject is read from ARGUMENTS (the call was asked for) rather than
     the result (the call succeeded), because the step frame is emitted BEFORE
     the call runs. `artifact_path_from` keeps the opposite rule for the
     opposite reason, and the two must not be conflated.
  3. Long free text is clipped ON THE WIRE, not in the renderer.

Falsification record — every assertion below was run against deliberately
broken code and observed to FAIL before being kept (a green gate that was
never made to fail tests the room, not the doorway).
"""

import sys

sys.path.insert(0, ".")

from services.lane_runner import (  # noqa: E402
    LANE_TOOL_NAMES,
    LANE_SURFACE_EXTRA,
    _SUBJECT_MAX,
    artifact_path_from,
    tool_subject_from,
)

failures: list = []


def check(label: str, cond: bool) -> None:
    if cond:
        print(f"  ok   {label}")
    else:
        print(f"  FAIL {label}")
        failures.append(label)


print("1. the subject is the one named key, never the argument dict")
# A read names its path.
check(
    "ReadFile names its path",
    tool_subject_from("ReadFile", {"path": "Documents/memo.md"}) == "Documents/memo.md",
)
# An UNNAMED sibling field is not exposed, even though it is in the same dict.
# ⚠️ The unnamed key is FIRST in insertion order and the named one second: an
# implementation that walked `arguments.keys()` instead of the rule's own tuple
# would return the token here. With the order reversed this assertion passed
# vacuously against exactly that break (observed 2026-08-25) — a dict probe is
# only a leak test if the leak would be reached first.
check(
    "an unnamed argument is not exposed",
    tool_subject_from("ReadFile", {"secret_token": "sk-live-xyz", "path": "a.md"})
    == "a.md",
)
# A verb with no subject key returns None rather than guessing.
check(
    "list_integrations has no subject",
    tool_subject_from("list_integrations", {"anything": "here"}) is None,
)
# An unknown verb returns None rather than reaching into its arguments.
check(
    "an unknown verb yields no subject",
    tool_subject_from("SomeFutureVerb", {"path": "x.md"}) is None,
)
# Non-dict arguments must not raise.
check("non-dict arguments are safe", tool_subject_from("ReadFile", None) is None)
check("string arguments are safe", tool_subject_from("ReadFile", "path=x") is None)
# An empty / whitespace value is no subject at all.
check(
    "an empty path is no subject",
    tool_subject_from("ReadFile", {"path": "   "}) is None,
)

print("2. a move names its DESTINATION (as the artifact card does)")
check(
    "MoveFile prefers new_path",
    tool_subject_from("MoveFile", {"path": "old/a.md", "new_path": "new/a.md"})
    == "new/a.md",
)
check(
    "MoveFile falls back to path when it is the only key",
    tool_subject_from("MoveFile", {"path": "old/a.md"}) == "old/a.md",
)

print("3. arguments, not results — the two functions read different sources")
# The step frame is emitted BEFORE the call runs, so a FAILED call still leaves
# an honest row naming what was attempted...
check(
    "a subject exists for a call with no result yet",
    tool_subject_from("WriteFile", {"path": "reports/q3.md"}) == "reports/q3.md",
)
# ...while the artifact card, reading the RESULT, correctly yields nothing for
# an unsuccessful write. Conflating the two would card a file that never landed.
check(
    "artifact_path_from still refuses a failed write",
    artifact_path_from("WriteFile", {"success": False, "path": "reports/q3.md"}) is None,
)

print("4. free text is clipped on the wire")
long_query = "x" * (_SUBJECT_MAX + 50)
clipped = tool_subject_from("SearchFiles", {"query": long_query})
check("a long query is clipped", clipped is not None and len(clipped) <= _SUBJECT_MAX)
check("a clipped subject is marked", clipped is not None and clipped.endswith("…"))
short_query = "Q3 pricing"
check(
    "a short query is untouched",
    tool_subject_from("SearchFiles", {"query": short_query}) == short_query,
)

print("5. the roster the member can actually see is covered")
# Every lane verb that TAKES a path or a query must name one. This is the
# assertion that catches a roster addition landing with no subject rule: the
# member would silently get the bare verb back.
_SUBJECTLESS = {"list_integrations"}
for name in LANE_TOOL_NAMES + LANE_SURFACE_EXTRA:
    if name in _SUBJECTLESS:
        continue
    probe = {"path": "p/x.md", "query": "q", "prompt": "pr", "new_path": "p/y.md"}
    check(f"{name} names a subject", tool_subject_from(name, probe) is not None)

print()
if failures:
    print(f"FAILED ({len(failures)}): " + " · ".join(failures))
    sys.exit(1)
print("PASS — the step seam names its subject and exposes nothing else")
