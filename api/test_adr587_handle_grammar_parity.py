#!/usr/bin/env python3
"""ADR-587 gate — one file-naming grammar, both sides of the boundary.

    python3 test_adr587_handle_grammar_parity.py

What this defends, and why each check is shaped the way it is:

D1-parity — the TS `parseFileReference` and the Python `parse_file_reference`
     agree on EVERY spelling, including the refusals. This is the whole point of
     the ADR: before it, `yarnnn://` was emitted by the app and parsed only by
     the server, so the app handed out a name it could not read back. The check
     DRIVES both implementations over a shared table rather than eyeballing the
     regexes — two functions can look alike and disagree on `..`, on case, on a
     bare word. The TS runs under node; if node is absent the check FAILS rather
     than skipping (a parity gate that quietly passes when half of it did not run
     is the "green gates test the room, not the doorway" failure).

D2-arrival — the Files arrival door normalizes before opening. A deep-link is
     where an outside name enters, and it previously matched `workspace_files.path`
     verbatim, so a handle or a bare path fell through to an empty selection.

D3-no-bare-param — nothing emits `/files?path=` any more. Surface params are
     slug-namespaced; a bare one is never read, so those links opened Files with
     NO selection — silently, because the surface then renders its Recents and
     looks like a working page.

D4-summary — the tree endpoint drops the machine summary. `Workspace write: {path}`
     is a write-log line, not a description; the API already calls that shape a
     leak and strips it on the Home slot, but the tree served it raw into the
     Files row subtitle.

D5-one-sentence — the AI-reference sentence is built in ONE place and names a
     verb that EXISTS. The two hand-written copies had already drifted: Studio
     said `trace`, which is not on the roster.

D6-share-sheet — the share sheet shows the PATH, not just the leaf. One
     `ShareDialog` serves Files, Studio and Text, so this is asserted once; the
     dialog already HELD `path` (it drives createShare) and displayed only
     `name`, which is the one string that does not identify a file. Also
     asserts the sheet does NOT emit the `yarnnn://` handle — a grant surface
     and an address must not blur (ADR-512 D6 / ADR-587 §4).

D7-every-face — the RULE, not spot-checks: wherever the Files surface shows an
     object, the identifying line under its name is the path — list row, grid
     tile, Properties, and the surface identity HEADER, for BOTH files and
     folders. The faces had drifted to different answers (path / attribution /
     silence for folders), which is what made this a rule question rather than
     a patch. Checked as a matrix so a new face cannot be added silently — the
     header is the face that matrix CAUGHT (D8): the children of a folder named
     themselves while the folder the operator was standing IN did not.

D8-one-copy-mechanism — the inline and boxed CopyField variants differ in
     PRESENTATION only. Both must keep the clipboard-denial fallback; a variant
     that silently no-ops where the other hands over a selection is the
     incorrect-success this component exists to prevent.

Every check here was falsified — broken deliberately, observed to fail, restored.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

API = Path(__file__).parent
REPO = API.parent
WEB = REPO / "web"

sys.path.insert(0, str(API))

failures: list[str] = []
checks = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global checks
    checks += 1
    if ok:
        print(f"  ok   {label}")
    else:
        failures.append(f"{label}: {detail}")
        print(f"  FAIL {label} — {detail}")


def strip_comments(src: str) -> str:
    """Executable source only.

    Twice now a check in this file has read a COMMENT as if it were code: the
    D6 handle-refusal matched the prose explaining the refusal, and D7's first
    cut matched `<FileTile>` inside a doc comment — so the element regex
    captured a comment span instead of the real call and reported the opposite
    of the truth. Prose that DESCRIBES the mechanism lives next to it by design;
    assertions must not read it.
    """
    src = re.sub(r"\{/\*.*?\*/\}", "", src, flags=re.S)   # JSX comment blocks
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)        # block comments
    return "\n".join(
        line for line in src.splitlines() if not line.strip().startswith("//")
    )



# ---------------------------------------------------------------------------
# The shared table. Every row is (input, expected workspace-relative | None).
# `None` means REFUSED — and a refusal is as load-bearing as a parse: it is
# what stops `../../etc/passwd` and an http:// link from being treated as a
# file in this workspace.
# ---------------------------------------------------------------------------
CASES: list[tuple[str, str | None]] = [
    # the three honest spellings of one name (ADR-512 D5)
    ("yarnnn://workspace/marketing/gtm.md", "marketing/gtm.md"),
    ("/workspace/marketing/gtm.md", "marketing/gtm.md"),
    ("marketing/gtm.md", "marketing/gtm.md"),
    # case-insensitive scheme
    ("YARNNN://WORKSPACE/marketing/gtm.md", "marketing/gtm.md"),
    # incidental wrapping the operator's clipboard adds
    ("  marketing/gtm.md  ", "marketing/gtm.md"),
    ('"marketing/gtm.md"', "marketing/gtm.md"),
    ("'marketing/gtm.md'", "marketing/gtm.md"),
    # leading slashes collapse
    ("/marketing/gtm.md", "marketing/gtm.md"),
    # nested paths survive intact
    ("yarnnn://workspace/a/b/c/d.md", "a/b/c/d.md"),
    # refusals
    ("", None),
    ("   ", None),
    ("https://example.com/x.md", None),
    ("file:///etc/passwd", None),
    ("../../etc/passwd", None),
    ("marketing/../../etc/passwd", None),
    ("yarnnn://workspace/../secrets.md", None),
    # a bare word IS a valid relative name (the surface decides what to do
    # with it) — pinned so a future tightening is a deliberate act
    ("notes", "notes"),
]


print("ADR-587 — one file-naming grammar, both sides")
print()
print("D1-parity — TS and Python agree on every spelling, including refusals")

# --- Python half -----------------------------------------------------------
from services.mcp_composition import (  # noqa: E402
    format_file_reference,
    parse_file_reference,
)

py_results = [parse_file_reference(src) for src, _ in CASES]
py_mismatch = [
    f"{src!r} -> {got!r} (expected {exp!r})"
    for (src, exp), got in zip(CASES, py_results)
    if got != exp
]
check(
    "python parse_file_reference matches the table",
    not py_mismatch,
    "; ".join(py_mismatch),
)

# --- TS half, DRIVEN under node --------------------------------------------
node = shutil.which("node") or shutil.which("nodejs")
check("node is available to drive the TS half", bool(node), "no node on PATH")

if node:
    ts_src = (WEB / "lib" / "interop" / "fileHandle.ts").read_text()
    # Strip TS-only syntax so the module runs as plain JS. Narrow + asserted:
    # if the transform stops finding the functions, the harness check below
    # fails loudly rather than silently testing nothing.
    js = ts_src
    js = re.sub(r"^export const ", "const ", js, flags=re.M)
    js = re.sub(r"^export function ", "function ", js, flags=re.M)
    js = re.sub(r":\s*string\s*\|\s*null\s*\|\s*undefined", "", js)
    js = re.sub(r":\s*string\s*\|\s*null", "", js)
    js = re.sub(r"\)\s*:\s*string\s*\{", ") {", js)
    js = re.sub(r"(\w+)\s*:\s*string(?=[,)])", r"\1", js)

    harness = (
        js
        + "\nconst CASES = "
        + json.dumps([src for src, _ in CASES])
        + ";\n"
        + "console.log(JSON.stringify(CASES.map(parseFileReference)));\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as fh:
        fh.write(harness)
        harness_path = fh.name

    proc = subprocess.run(
        [node, harness_path], capture_output=True, text=True, timeout=60
    )
    ran = proc.returncode == 0
    check(
        "the TS module actually executes",
        ran,
        (proc.stderr or "").strip()[:400],
    )
    if ran:
        ts_results = json.loads(proc.stdout.strip().splitlines()[-1])
        ts_mismatch = [
            f"{src!r} -> {got!r} (expected {exp!r})"
            for (src, exp), got in zip(CASES, ts_results)
            if got != exp
        ]
        check(
            "TS parseFileReference matches the table",
            not ts_mismatch,
            "; ".join(ts_mismatch),
        )
        check(
            "TS and Python agree case-for-case",
            ts_results == py_results,
            f"ts={ts_results} py={py_results}",
        )

# emit half
check(
    "python format_file_reference round-trips",
    format_file_reference("/workspace/a/b.md") == "yarnnn://workspace/a/b.md",
    format_file_reference("/workspace/a/b.md"),
)

print()
print("D2-arrival — the Files arrival door normalizes before opening")
files_page = (WEB / "app" / "(authenticated)" / "files" / "page.tsx").read_text()
check(
    "the arrival effect imports the grammar",
    "toWorkspacePath" in files_page and "@/lib/interop/fileHandle" in files_page,
    "no toWorkspacePath import on the Files surface",
)
# The door must not hand the RAW param to openPath — that was the defect.
raw_open = re.search(r"openPathRef\.current\(\s*pathParam\s*\)", files_page)
check(
    "the raw deep-link param is no longer opened verbatim",
    raw_open is None,
    "openPathRef.current(pathParam) still present — the handle spelling cannot resolve",
)

print()
print("D3-no-bare-param — nothing emits the unread `/files?path=`")
emitters: list[str] = []
for path in list(WEB.rglob("*.tsx")) + list(WEB.rglob("*.ts")):
    if "node_modules" in path.parts or ".next" in path.parts:
        continue
    text = path.read_text(errors="ignore")
    for m in re.finditer(r"""['"`]/files\?path=""", text):
        line_no = text[: m.start()].count("\n") + 1
        line = text.splitlines()[line_no - 1].strip()
        # Prose describing the OLD behavior is history worth keeping; only an
        # EMITTER is a defect. (The comments still get the spelling right —
        # they were corrected in the same pass — but the gate must not be the
        # thing that forbids describing a deleted behavior.)
        if line.startswith(("*", "//", "/*")):
            continue
        emitters.append(f"{path.relative_to(REPO)}:{line_no}")
check(
    "no source emits /files?path= (the param is files.path)",
    not emitters,
    ", ".join(emitters),
)

print()
print("D4-summary — the tree endpoint drops the machine summary")
routes_ws = (API / "routes" / "workspace.py").read_text()
check(
    "_plain_summary exists",
    "def _plain_summary(" in routes_ws,
    "no _plain_summary helper",
)
check(
    "the tree endpoint calls it",
    "_plain_summary(row.get(\"summary\"))" in routes_ws,
    "tree rows still carry the raw summary",
)
check(
    "the prefix list is shared (one place to add a prefix)",
    "_MACHINE_SUMMARY_PREFIXES" in routes_ws
    and routes_ws.count("_strip_machine_prefix(") >= 3,
    "prefix handling is not shared between the two readers",
)
# Drive it, don't grep it.
ns: dict = {"Optional": __import__("typing").Optional}
block = routes_ws[
    routes_ws.index("#: Machine prefixes") : routes_ws.index("class RecentArtifact")
]
exec(block, ns)  # noqa: S102 — the module's own source, executed to be tested
plain = ns["_plain_summary"]
drive = [
    ("Workspace write: marketing/creative-brief.md", None),
    ("Workspace edit: marketing/gtm-strategy.md", None),
    ("", None),
    (None, None),
    ("Q3 growth plan", "Q3 growth plan"),
]
bad = [f"{i!r}->{plain(i)!r} want {e!r}" for i, e in drive if plain(i) != e]
check("_plain_summary behaves, driven", not bad, "; ".join(bad))

print()
print("D5-one-sentence — the AI reference is built once, and names a real verb")
handle_ts = (WEB / "lib" / "interop" / "fileHandle.ts").read_text()
check(
    "formatAiReference is defined in the shared module",
    "export function formatAiReference" in handle_ts,
    "no shared builder",
)
# The roster is PARSED from the server, never pinned as a count or a literal.
server_src = (API / "mcp_server" / "server.py").read_text()
roster_block = re.search(
    r"_INTEROP_VERBS[^=]*=\s*\((.*?)\n\)\n", server_src, re.S
)
roster = set(re.findall(r'^\s{8}"([a-z_]+)",\s*$', roster_block.group(1), re.M))
check("the roster parsed", len(roster) >= 5, f"parsed {roster}")
named = set(re.findall(r"`([a-z_]+)`", handle_ts.split("formatAiReference")[-1]))
unknown = named - roster
check(
    "every verb the sentence names is on the roster",
    not unknown,
    f"names verbs that do not exist: {sorted(unknown)} (roster={sorted(roster)})",
)
# And no surface may hand-roll the sentence again.
handrolled: list[str] = []
for path in list(WEB.rglob("*.tsx")) + list(WEB.rglob("*.ts")):
    if "node_modules" in path.parts or ".next" in path.parts:
        continue
    if path.name == "fileHandle.ts":
        continue
    text = path.read_text(errors="ignore")
    if "yarnnn://workspace/${" in text or "yarnnn://workspace/' +" in text:
        handrolled.append(str(path.relative_to(REPO)))
check(
    "no surface interpolates the handle by hand",
    not handrolled,
    ", ".join(handrolled),
)

print()
print("D6-share-sheet — the sheet names the path, and mints grants only")
share_dialog = (WEB / "components" / "workspace" / "ShareDialog.tsx").read_text()
# Assert the COMPOSITION, not the coexistence of two strings. The first cut
# tested `"CopyField" in src and "relPath(target.path)" in src`, which PASSED
# against a deliberately broken version: the falsifier repointed the field at
# `target.name`, and the substring survived in an unrelated `title=` attribute.
# Two strings being present in one file says nothing about one feeding the other.
copyfield_block = re.search(
    r"<CopyField\b(.*?)/>", share_dialog, re.S
)
check(
    "the share sheet renders the path through the shared field",
    bool(copyfield_block)
    and re.search(r"value=\{relPath\(\s*target\.path\s*\)\}", copyfield_block.group(1)),
    "CopyField does not receive the file's path as its value",
)
check(
    "it uses the shared grammar, not a local prefix strip",
    "@/lib/interop/fileHandle" in share_dialog,
    "ShareDialog strips /workspace/ by hand",
)
# The refusal, enforced: a grant surface must not also hand out an address.
#
# Comment lines are STRIPPED before the test. The first cut of this check ran
# over the raw source and went red against CORRECT code — matching the comment
# that EXPLAINS the refusal ("Deliberately NOT the `yarnnn://` handle here").
# An assertion a comment can satisfy — or, as here, break — is not an assertion
# about behavior. Strip first, then assert on what executes.
share_code = strip_comments(share_dialog)
check(
    "the share sheet does NOT emit the yarnnn:// handle",
    "yarnnn://" not in share_code,
    "the grant sheet emits an address — the reach-vs-egress blur ADR-587 §4 refused",
)
# One component, so every mounting surface inherits it — assert they all mount
# the shared dialog rather than rolling their own header.
mounts = []
for rel in (
    "app/(authenticated)/files/page.tsx",
    "components/authoring/StudioSurface.tsx",
    "components/text/TextEditor.tsx",
):
    if "<ShareDialog" in (WEB / rel).read_text():
        mounts.append(rel)
check(
    "Files, Studio and Text all mount the ONE ShareDialog",
    len(mounts) == 3,
    f"only {mounts} mount it — a surface with its own sheet would not inherit the path",
)

print()
print("D7-every-face — the identifying line is the path, on every face, both kinds")
content_viewer_raw = (WEB / "components" / "workspace" / "ContentViewer.tsx").read_text()
files_page_raw = (WEB / "app" / "(authenticated)" / "files" / "page.tsx").read_text()
details_panel = (WEB / "components" / "workspace" / "NodeDetailsPanel.tsx").read_text()


content_viewer = strip_comments(content_viewer_raw)

# The GRID tile: subtext must be the path, not attribution. Assert the
# composition (what the prop receives), never mere co-presence of two strings —
# the D6 lesson.
tile_call = re.search(r"<FileTile\b(.*?)/>", content_viewer, re.S)
check(
    "the grid tile's subtext is the path",
    bool(tile_call)
    and re.search(r"subtext=\{workspaceRelPath\(\s*child\.path\s*\)\}", tile_call.group(1)),
    "the icon view's subtext is not the file's path",
)
check(
    "the grid tile no longer spends its one line on attribution",
    bool(tile_call) and "formatAuthorLabel" not in tile_call.group(1),
    "the tile subtext still carries attribution — which renders EMPTY for folders",
)

# The LIST row: same answer, different face.
row_call = re.search(r"<FileListRow\b(.*?)/>", content_viewer, re.S)
check(
    "the list row's subtitle is the path",
    bool(row_call)
    and re.search(r"subtitle=\{workspaceRelPath\(\s*child\.path\s*\)\}", row_call.group(1)),
    "the details list's subtitle is not the file's path",
)

# PROPERTIES, both kinds. A folder is as addressable as a file; the panel that
# exists to say "what is this" must name it for both.
def _fn_body(src: str, name: str) -> str:
    start = src.index(f"function {name}(")
    nxt = src.find("\nfunction ", start + 1)
    return src[start : nxt if nxt != -1 else len(src)]

for fn, kind in (("FileProperties", "file"), ("FolderDetails", "folder")):
    body = _fn_body(details_panel, fn)
    check(
        f"Properties names the path for a {kind}",
        'PropRow label="Path"' in body and "CopyField" in body
        and re.search(r"value=\{(relPath\(node\.path\)|reference)\}", body),
        f"{fn} does not render a copyable Path row",
    )

# Every path face goes through the ONE field + the ONE grammar. A surface that
# hand-rolls either is how the three faces drifted apart in the first place.
for rel in ("components/workspace/ContentViewer.tsx",
            "components/workspace/NodeDetailsPanel.tsx",
            "components/workspace/ShareDialog.tsx"):
    src = (WEB / rel).read_text()
    check(
        f"{rel.split('/')[-1]} uses the shared grammar",
        "@/lib/interop/fileHandle" in src,
        "strips /workspace/ by hand instead of using the one grammar",
    )

# The HEADER — the fourth face, and the one the operator is standing in.
files_page = strip_comments(files_page_raw)
check(
    "the surface header names the path",
    re.search(r"metadata=\{nodeMetadataNode\(", files_page)
    and re.search(r"CopyField[^>]*value=\{relPath\(\s*node\.path\s*\)\}", files_page, re.S),
    "the header's metadata strip does not carry the object's path",
)

print()
print("D8-one-copy-mechanism — the variants differ in presentation, not behaviour")
copyfield = (WEB / "components" / "workspace" / "CopyField.tsx").read_text()
# One clipboard call, one fallback — shared by both variants, not duplicated
# per branch (a second copy is a second place to forget the fallback).
check(
    "there is exactly ONE clipboard write in CopyField",
    copyfield.count("navigator.clipboard.writeText") == 1,
    f"found {copyfield.count('navigator.clipboard.writeText')} — the variants have diverged",
)
check(
    "the denial fallback selects the text",
    copyfield.count("inputRef.current?.select()") == 1,
    "no shared clipboard-denial fallback",
)
# The inline variant must still mount an input for that fallback to reach.
inline_branch = copyfield[copyfield.index("if (variant === 'inline')") : copyfield.rindex("return (")]
check(
    "the inline variant mounts the input its fallback needs",
    "ref={inputRef}" in inline_branch,
    "inline renders no input — its clipboard-denial fallback would be a no-op",
)

print()
if failures:
    print(f"FAILED {len(failures)}/{checks}")
    for f in failures:
        print(f"  · {f}")
    sys.exit(1)
print(f"PASSED {checks}/{checks}")
