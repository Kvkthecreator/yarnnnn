"""ADR-514 D1 — the DuplicateFile kernel verb.

Run: python3 test_adr514_duplicate_verb.py  (from api/)

The pre-514 duplicate lived in the browser (Studio's `duplicateArtifact` +
`duplicateRecent`): it probed for a free `-copy` name over N round trips
(TOCTOU-racy), was `.html`-only by construction, capped at 5, and wrote NO
`derived_from` — so every duplicate was an attribution orphan. This gate pins
the properties that fix ARE the ADR, and it EXECUTES the suffix resolver rather
than grepping for it (the ADR-513 header gate passed while the behavior was
broken precisely because it grepped — see feedback_gates_grep_text_not_execution).

Asserts:
  1. Suffix resolution EXECUTES correctly: format-agnostic (any extension or
     none), double-extension safe, collision-walking, and bounded.
  2. The primitive is registered + reachable, and the write is a DERIVATION
     citing the source (the correctness fix).
  3. The permission gate sees it (topology locks still refuse a locked root).
  4. Singular Implementation: no client-side duplicate survives in the FE.
"""

import ast
import inspect
import pathlib
import sys

WEB = pathlib.Path(__file__).resolve().parents[1] / "web"

results: list[tuple[str, bool, str]] = []


def _check(label: str, ok: bool, detail: str = "") -> tuple[str, bool, str]:
    return (label, bool(ok), detail)


# ── 1. the suffix resolver, EXECUTED ─────────────────────────────────────────
from services.primitives.workspace import (  # noqa: E402
    _duplicate_target_path,
    _DUPLICATE_SUFFIX_LIMIT,
)

SRC = "/workspace/operation/notes.md"
results.append(_check(
    "1a first copy takes the -copy suffix, extension preserved",
    _duplicate_target_path(SRC, {SRC}) == "/workspace/operation/notes-copy.md"))

results.append(_check(
    "1b collision walks to -copy-2",
    _duplicate_target_path(SRC, {SRC, "/workspace/operation/notes-copy.md"})
    == "/workspace/operation/notes-copy-2.md"))

# The .html-only bug: a yaml MUST duplicate as yaml, not as `_watch.yaml-copy`.
results.append(_check(
    "1c format-agnostic — a .yaml duplicates as .yaml (the .html-only bug)",
    _duplicate_target_path("/workspace/operation/_watch.yaml", set())
    == "/workspace/operation/_watch-copy.yaml"))

results.append(_check(
    "1d no extension is handled (no stray dot)",
    _duplicate_target_path("/workspace/operation/README", set())
    == "/workspace/operation/README-copy"))

# partition() on the FIRST dot keeps a double extension intact.
results.append(_check(
    "1e double extension stays whole (archive.tar.gz, not archive.tar-copy.gz)",
    _duplicate_target_path("/workspace/operation/archive.tar.gz", set())
    == "/workspace/operation/archive-copy.tar.gz"))

# Bounded: a saturated directory returns None rather than looping forever.
saturated = {SRC, "/workspace/operation/notes-copy.md"} | {
    f"/workspace/operation/notes-copy-{i}.md" for i in range(2, _DUPLICATE_SUFFIX_LIMIT + 2)
}
results.append(_check(
    "1f saturated directory is bounded (returns None, no infinite loop)",
    _duplicate_target_path(SRC, saturated) is None))

# The resolver must never hand back a name already taken — the whole point of
# resolving server-side in ONE read instead of probing.
_taken = {SRC} | {f"/workspace/operation/notes-copy-{i}.md" for i in range(2, 12)}
_taken.add("/workspace/operation/notes-copy.md")
results.append(_check(
    "1g never returns a taken path",
    _duplicate_target_path(SRC, _taken) not in _taken))


# ── 2. registration + the derivation contract ────────────────────────────────
from services.primitives.registry import HANDLERS, PRIMITIVES, CHAT_PRIMITIVES  # noqa: E402

results.append(_check(
    "2a DuplicateFile registered in HANDLERS",
    "DuplicateFile" in HANDLERS))
results.append(_check(
    "2b exposed as a tool (PRIMITIVES + CHAT_PRIMITIVES)",
    any(t["name"] == "DuplicateFile" for t in PRIMITIVES)
    and any(t["name"] == "DuplicateFile" for t in CHAT_PRIMITIVES)))

_dup_src = inspect.getsource(HANDLERS["DuplicateFile"])
results.append(_check(
    "2c the write CITES the source — derived_from=[abs_src] (the orphan fix)",
    "derived_from=[abs_src]" in _dup_src))
results.append(_check(
    "2d recorded as a derivation, not an authored clone (ADR-423)",
    'revision_kind="derivation"' in _dup_src))
# content_ref re-references the existing blob by sha: a binary duplicate must
# not round-trip bytes, and must not re-hash the (empty) text denorm.
results.append(_check(
    "2e binaries duplicate by blob reference, not byte copy (content_ref)",
    "content_ref=" in _dup_src and "content_bytes" not in _dup_src))
results.append(_check(
    "2f goes through write_revision — no second write door (ADR-209)",
    "write_revision(" in _dup_src))


# ── 3. the permission gate sees it ───────────────────────────────────────────
from services.primitives.permission import _PATH_ADDRESSED_QUEUEABLE  # noqa: E402
from services.primitives.workspace import _resolve_gate_paths  # noqa: E402

results.append(_check(
    "3a gate treats DuplicateFile as path-addressed",
    "DuplicateFile" in _PATH_ADDRESSED_QUEUEABLE))
results.append(_check(
    "3b the gate resolves its target path (locked roots stay refused)",
    _resolve_gate_paths("DuplicateFile", {"path": "governance/_budget.yaml"})
    == ["governance/_budget.yaml"]))


# ── 4. Singular Implementation — the client-side copies are GONE ─────────────
# The ADR deletes rather than mirrors. A surviving browser-side suffix probe
# would silently keep producing orphaned duplicates on that surface.
_studio = (WEB / "components/authoring/StudioSurface.tsx").read_text()
results.append(_check(
    "4a no client-side -copy suffix probe survives in Studio",
    "-copy.html" not in _studio and "-copy-${i}" not in _studio))
results.append(_check(
    "4b Studio's duplicate routes through the shared verb",
    _studio.count("organizeVerbs.onDuplicate") >= 2))

# Every surface reaches duplicate through the ONE hook, so a fix reaches all.
_hook = (WEB / "hooks/useFileOrganizeVerbs.tsx").read_text()
results.append(_check(
    "4c the shared hook owns duplicate (api.documents.duplicate)",
    "api.documents.duplicate" in _hook and "onDuplicate" in _hook))

# The menu must actually OFFER it — a wired verb no surface renders is invisible.
_menu = (WEB / "components/workspace/FileContextMenu.tsx").read_text()
results.append(_check(
    "4d the shared context menu renders Duplicate",
    "onDuplicate" in _menu and ">\n          Duplicate\n        <" in _menu))

_files_page = (WEB / "app/(authenticated)/files/page.tsx").read_text()
results.append(_check(
    "4e the Files verb bundle wires it (the surface the audit found bare)",
    "onDuplicate: organizeVerbs.onDuplicate" in _files_page))

# Exactly one FE caller of the duplicate endpoint — the hook. A second caller
# would be a fork of the verb (the pre-514 failure mode: Studio-local copies).
_callers = [
    p for p in WEB.rglob("*.tsx")
    if "node_modules" not in str(p) and "api.documents.duplicate(" in p.read_text()
]
results.append(_check(
    "4f exactly ONE FE caller of the duplicate endpoint (no fork)",
    len(_callers) == 1, str([c.name for c in _callers])))


# ── report ───────────────────────────────────────────────────────────────────
failed = 0
for label, ok, detail in results:
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    if not ok:
        failed += 1

total = len(results)
print()
if failed:
    print(f"FAILED — {total - failed}/{total}")
    sys.exit(1)
print(f"ALL PASS — {total}/{total}")
