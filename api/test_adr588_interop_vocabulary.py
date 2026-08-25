"""The interop surface answers in the vocabulary it taught, and leaks nothing
(2026-08-25).

Script-style (python3, from api/). Four defects, each observed on the live MCP
surface before this gate existed:

  1. `ScopeDenied` was imported by the server and caught NOWHERE (one
     occurrence, zero uses), so an under-scoped connection got a protocol-level
     fault instead of a refusal — on the authorization surface — rendering a
     raw Python list literal (`holds ['(none)']`).
  2. Four sites returned `str(exc)` to an EXTERNAL client. A PostgREST failure
     stringifies to `{'message': 'relation "workspace_files" does not exist',
     'code': '42P01', …}`: our table names and Postgres error codes, handed to
     Claude Desktop / ChatGPT. Disclosure, not diction.
  3. Refusals named tools the caller does not hold — the trashed-file notice
     said "use ListRevisions/ReadRevision", neither of which is on the MCP
     roster (its equivalent is `history`).
  4. ONE connection taught FOUR names for TWO folders: the instructions say
     "Documents"/"Downloads" (ADR-588 D2 told-names), while examples said
     `operation/` and search answered `inbound/`. The told-name was an accepted
     ADDRESS but never a spoken one — `resolve_home_alias` had no inverse.

Falsification record: every assertion below was run against deliberately broken
code and observed to FAIL before being kept.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, ".")

failures: list = []


def check(label: str, cond: bool) -> None:
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        failures.append(label)


SERVER = Path("mcp_server/server.py").read_text()
COMPOSITION = Path("services/mcp_composition.py").read_text()
CONTEXT = Path("services/workspace_context.py").read_text()

print("1. the told-name round-trips — an address in, the same name out")
from services.workspace_paths import (  # noqa: E402
    HOME_ALIASES,
    display_home_alias,
    resolve_home_alias,
)

for told in HOME_ALIASES:
    check(
        f"{told} survives the round trip",
        display_home_alias(resolve_home_alias(f"{told}/x.md")) == f"{told}/x.md",
    )
check(
    "a kernel root is spoken as its told-name",
    display_home_alias("operation/q3.md") == "Documents/q3.md",
)
check(
    "inbound is spoken as Downloads",
    display_home_alias("inbound/slack/a.md") == "Downloads/slack/a.md",
)
# A meaning-named folder is NOT a home and must pass through untouched.
check(
    "a non-home folder is byte-identical",
    display_home_alias("deals/acme/y.md") == "deals/acme/y.md",
)
check("an empty path is safe", display_home_alias("") == "")
# ⚠️ The inverse must be DERIVED from HOME_ALIASES, never a second hand-kept
# dict — two hand-kept directions are how the vocabularies diverged originally.
check(
    "the inverse is derived, not hand-kept",
    "_HOME_ALIAS_DISPLAY = {v: k for k, v in HOME_ALIASES.items()}"
    in Path("services/workspace_paths.py").read_text(),
)

print("2. a scope denial is COMPOSED, not raised through")
check("the server catches ScopeDenied", "except ScopeDenied" in SERVER)
check(
    "it is caught at the one funnel (call_tool), not per verb",
    re.search(r"async def call_tool\(.*?except ScopeDenied", SERVER, re.S) is not None,
)
check(
    "the refusal names the remedy",
    "re-authorize the yarnnn connector" in SERVER.lower(),
)
# The raw list literal is what the operator would have READ. `str(exc)` on a
# ScopeDenied renders `['(none)']`; the composed refusal must not.
# Guarded: with the handler absent this must REPORT a failure, not crash. A
# gate that raises on the very defect it guards hides every assertion after it
# (observed while falsifying F1 — IndexError instead of three clean FAILs).
_refusal = SERVER.split("except ScopeDenied")
check(
    "no raw python list literal in the refusal",
    len(_refusal) > 1 and "['(none)']" not in _refusal[1][:900],
)

print("3. no raw exception text reaches an external client")
# The composers sit behind PostgREST/httpx. `str(exc)` there is disclosure.
# ⚠️ THE DISTINCTION THIS ASSERTS. Not "str(exc) never appears" — a TYPED,
# member-language exception of ours (`ShareError`) SHOULD speak for itself, and
# banning the spelling outright would force it into a worse shape. What must
# never reach an external client is the str() of an UNTYPED catch-all, whose
# class we do not control (PostgREST, httpx). So: every `except Exception`
# handler that returns a client message must use the stable sentence.
def _catchall_leaks(src: str) -> list:
    leaks = []
    for block in re.split(r"\n(?=\s*except )", src):
        head = block.split("\n", 1)[0]
        if "except Exception" not in head:
            continue
        body = block[: 1200]
        if re.search(r'"message":\s*str\(exc\)', body):
            leaks.append(head.strip())
    return leaks


for name, src in (("mcp_composition", COMPOSITION), ("server", SERVER)):
    check(
        f"{name}: no catch-all hands str(exc) to a client",
        not _catchall_leaks(src),
    )
check(
    "there is ONE stable internal-failure sentence",
    "INTERNAL_FAILURE_MESSAGE" in COMPOSITION,
)
check(
    "the server composes that same sentence (not its own spelling)",
    "mcp_composition.INTERNAL_FAILURE_MESSAGE" in SERVER,
)
# A typed, member-language error of OURS must still speak for itself.
check(
    "ShareError keeps its own message",
    "except ShareError" in SERVER and "str(exc)" in SERVER.split("except ShareError")[1][:200],
)

print("4. a refusal names only verbs the caller holds")
_ROSTER = re.search(r"_INTEROP_VERBS[^=]*=\s*\((.*?)\n\)\n", SERVER, re.S)
roster = set(re.findall(r'^\s*"([a-z_]+)",', _ROSTER.group(1), re.M)) if _ROSTER else set()
check("the roster parsed", len(roster) >= 9)
# The interop branch of the trashed notice must not name a kernel primitive.
interop_branch = CONTEXT.split("if interop:")[1].split("else:")[0]
for kernel_verb in ("ListRevisions", "ReadRevision", "WriteFile", "EditFile", "Clarify"):
    check(
        f"the interop trashed notice does not name {kernel_verb}",
        kernel_verb not in interop_branch,
    )
check(
    "it routes to a verb that IS on the roster",
    any(f"`{v}`" in interop_branch for v in roster),
)
check(
    "it says 'the user', not our internal 'operator'",
    "the user" in interop_branch and "the operator" not in interop_branch,
)
# The kernel branch is UNCHANGED — internal callers do hold those primitives.
kernel_branch = CONTEXT.split("if interop:")[1].split("else:")[1]
check(
    "the kernel branch still names the kernel primitives",
    "ListRevisions/ReadRevision" in kernel_branch,
)

print("5. one vocabulary for the two homes, across the connection")
# The instructions teach these names; client-facing prose must not contradict.
for told in HOME_ALIASES:
    check(
        f"the filesystem model still teaches {told}",
        f"**{told}**" in Path("services/workspace_paths.py").read_text(),
    )
# `inbound/` must not be spoken at a participant (the search set-aside did).
search_note = COMPOSITION.split("raw_arrivals")[3] if COMPOSITION.count("raw_arrivals") > 3 else COMPOSITION
check(
    "search does not answer in the kernel root name",
    "under inbound/" not in COMPOSITION,
)
# Client-facing EXAMPLES speak the told-name. (The parse_file_reference
# docstring legitimately explains the kernel mapping and is excluded.)
examples = [
    ln for ln in (COMPOSITION + SERVER).splitlines()
    if "e.g." in ln and "operation/" in ln
]
check("no example teaches the kernel root", not examples)

print()
if failures:
    print(f"FAILED ({len(failures)}): " + " · ".join(failures))
    sys.exit(1)
print(f"PASS — the interop surface speaks one vocabulary and leaks nothing")
