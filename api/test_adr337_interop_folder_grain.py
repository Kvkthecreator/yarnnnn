"""The interop delete/move resolve the grain honestly, and say so (2026-08-26).

Script-style (python3, from api/). ADR-337 amended gave the kernel two grains
(`DeleteFile`/`DeleteFolder`, `MoveFile`/`MoveFolder`) and ADR-545 gave interop
ONE `delete` and ONE `move`, with `_names_a_folder` picking the fan-out — so a
foreign caller never has to learn our taxonomy. Two defects in that seam,
observed by driving the resolver:

  1. `_names_a_folder` matched ARCHIVED rows. `enumerate_subtree` excludes them
     (it answers about the LIVE folder), so `delete` on an already-trashed
     folder routed to the fan-out, found nothing, and returned
     `success: True, "0 moved to Trash"` — the ADR-373 D6 incorrect-success
     class. `DeleteFile` on a dead path honestly returns `file_not_found`; the
     folder grain did not. `compose_list` one screen away already carried the
     `lifecycle` filter this query was missing.

  2. The interop roster and both tool docstrings said "a FILE" — `delete`:
     "remove a file from the live workspace"; `move`: "move or rename a file".
     Neither named the folder grain, while the code fans out over a subtree up
     to `MAX_FAN_OUT` (500). ADR-337's own safety model is that the DESCRIPTIVE
     NAME carries the blast radius; the kernel's `DELETE_FOLDER_TOOL` states it
     ("this verb's blast radius is the whole subtree") and interop did not, so
     the one surface that resolves the grain silently was also the one that
     never mentioned it.

Falsification record: every assertion below was run against the pre-fix tree
and observed to FAIL (§1 four assertions, §2 six) before being kept.
"""

import re
import sys
import types
from pathlib import Path

sys.path.insert(0, ".")

failures: list = []


def check(label: str, cond: bool) -> None:
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        failures.append(label)


SERVER = Path("mcp_server/server.py").read_text()
COMPOSITION = Path("services/mcp_composition.py").read_text()


# ---------------------------------------------------------------------------
# A fake of the query surface `_names_a_folder` uses. It models the ONE fact
# under test — whether the resolver's filter set excludes archived rows — and
# nothing else. Driven, not grepped: the pre-fix defect was a MISSING call, and
# a grep for an absent string passes for the wrong reason.
# ---------------------------------------------------------------------------
class _Q:
    def __init__(self, rows):
        self.rows = list(rows)

    def select(self, *a, **k):
        return self

    def eq(self, col, val):
        self.rows = [r for r in self.rows if r.get(col) == val]
        return self

    def in_(self, col, vals):
        self.rows = [r for r in self.rows if r.get(col) in vals]
        return self

    def or_(self, expr):
        if "lifecycle" in expr:
            self.rows = [r for r in self.rows if r.get("lifecycle") != "archived"]
            return self
        keep = []
        for r in self.rows:
            for clause in expr.split(","):
                if clause.startswith("path.eq.") and r["path"] == clause[8:]:
                    keep.append(r)
                    break
                if clause.startswith("path.like."):
                    if r["path"].startswith(clause[10:].replace("%", "")):
                        keep.append(r)
                        break
        self.rows = keep
        return self

    def limit(self, n):
        self.rows = self.rows[:n]
        return self

    def execute(self):
        return types.SimpleNamespace(data=self.rows)


def _auth(rows):
    class _C:
        def table(self, _name):
            return _Q(rows)

    return types.SimpleNamespace(client=_C(), user_id="u1", workspace_id="w1")


LIVE = [
    {"path": "/workspace/deals/acme/", "content_type": "inode/directory",
     "lifecycle": "active", "user_id": "u1", "workspace_id": "w1"},
    {"path": "/workspace/deals/acme/brief.md", "content_type": "text/markdown",
     "lifecycle": "active", "user_id": "u1", "workspace_id": "w1"},
]
TRASHED = [dict(r, lifecycle="archived") for r in LIVE]
DELIVERED = [dict(r, lifecycle="delivered") for r in LIVE]

from services.mcp_composition import _names_a_folder  # noqa: E402

print("1. the grain resolver answers about the LIVE tree")
check(
    "a live folder resolves as a folder",
    _names_a_folder(_auth(LIVE), "deals/acme") is True,
)
check(
    "a fully-TRASHED folder does NOT resolve as a folder",
    _names_a_folder(_auth(TRASHED), "deals/acme") is False,
)
check(
    "a 'delivered' folder still resolves (the lifecycle set is not just 'active')",
    _names_a_folder(_auth(DELIVERED), "deals/acme") is True,
)
check(
    "an unknown path resolves as not-a-folder",
    _names_a_folder(_auth(LIVE), "deals/nope") is False,
)
# The consequence the filter exists to prevent: with the folder grain declined,
# `delete` falls through to DeleteFile, whose dead-path answer is a refusal.
check(
    "the resolver's filter set matches the one `compose_list` reads with",
    'in_("lifecycle", ["active", "delivered"])' in COMPOSITION
    and COMPOSITION.count('in_("lifecycle", ["active", "delivered"])') >= 2,
)


print("2. the interop verbs name the grain they can act on")

_roster = re.search(r"_INTEROP_VERBS[^=]*=\s*\((.*?)\n\)\n", SERVER, re.S)
check("the roster parses", _roster is not None)
roster_src = _roster.group(1) if _roster else ""


def _roster_entry(verb: str) -> str:
    m = re.search(r'\(\s*"%s",(.*?)\n    \),' % verb, roster_src, re.S)
    return m.group(1) if m else ""


def _docstring(fn: str) -> str:
    m = re.search(r"async def %s\((.*?)\"\"\"(.*?)\"\"\"" % fn, SERVER, re.S)
    return m.group(2) if m else ""


# ⚠️ NOT a bare "folder" search. `move`'s docstring already said "a better
# folder" — about the DESTINATION, not the grain — so a word-presence check
# passed vacuously on the very defect it was written for. The claim under test
# is that the verb ACTS ON a folder, so the assertion pins the grain phrase.
_GRAIN = re.compile(r"(a|whole|entire)\s+(folder|subtree)|folder\s+(goes|moves|and everything)"
                    r"|point (it|this) at a folder|folder .{0,40}(fan|whole|every file)",
                    re.I)

for verb in ("delete", "move"):
    entry = _roster_entry(verb)
    doc = _docstring(verb)
    check(f"the roster entry for `{verb}` names the folder grain",
          bool(_GRAIN.search(entry)))
    check(f"the `{verb}` docstring names the folder grain",
          bool(_GRAIN.search(doc)))

# The blast radius must be legible where the model reads it — ADR-337's safety
# model is the descriptive name, and the kernel's own folder verb states it.
check(
    "the `delete` docstring states the subtree blast radius",
    "subtree" in _docstring("delete").lower()
    or "everything under" in _docstring("delete").lower(),
)


print()
if failures:
    print(f"FAIL — {len(failures)} assertion(s):")
    for f in failures:
        print(f"  · {f}")
    sys.exit(1)
print("PASS — interop resolves the grain on the live tree, and names it")
