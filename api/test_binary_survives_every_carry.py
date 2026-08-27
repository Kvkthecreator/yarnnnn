"""A file's BYTES survive every verb that carries it forward (2026-08-27).

THE DEFECT THIS GATE EXISTS FOR
===============================
`MoveFile` carried a file to its new path by reading the `content` TEXT COLUMN
and writing it back:

    .select("path, content")
    content = by_path[abs_src].get("content") or ""
    write_revision(..., path=abs_dst, content=content)

A binary file's text denorm is `''` BY CONTRACT (ADR-427 D4 — the bytes live in
the CAS, addressed by the head revision's `blob_sha`). So moving a .png wrote an
empty-string revision at the head of a binary chain and the image was gone.

Observed in production 2026-08-27: two images were emptied by a RENAME on
2026-08-20, and the emptiness then rode a second move a week later. Their bytes
are unrecoverable — no prior revision of either path holds a real blob.

ONE DEFECT, SIX DOORS. The mover is the widest-reach verb in the substrate:

    POST /api/documents/move          the browser's move + rename door
    routes/studio.py rename_artifact  renames an artifact's whole folder
    MCP `move`                        an agent moving a file
    folder_organize.move_folder       THE FAN-OUT — one folder drag could
    primitives/folder MoveFolder      empty every binary beneath it
    tree drag / grid drag             both funnel through the route above

WHY IT SURVIVED A CONSOLIDATION. `_head_content_form` (authored_substrate.py)
is the canonical fix and ALREADY EXISTED — its docstring names this exact
hazard ("would put an empty TEXT revision at the head of a binary chain"), and
archive + restore + duplicate all adopted it. The mover was the one lifecycle
verb that never did. The existing gate in `test_trashed_file_does_not_read_back`
checked a HAND-SPELLED LIST OF THREE FILES for a duplicated helper; `MoveFile`
was not on the list, so nothing asked the question that matters.

SO THIS GATE IS DERIVED, NOT SPELLED. It reads the source, finds every verb
that carries a file's content forward, and requires each to use a byte-safe
form. A verb added tomorrow is caught by construction rather than by someone
remembering to add it here.

Run directly: `python3 test_binary_survives_every_carry.py` from `api/`.
"""

import re
import sys
from pathlib import Path

_API = Path(__file__).resolve().parent
_passed = True


def check(label: str, cond: bool, detail: str = "") -> None:
    global _passed
    print(f"  {'ok  ' if cond else 'FAIL'} {label}" + (f"  [{detail}]" if detail and not cond else ""))
    if not cond:
        _passed = False


def code_only(src: str) -> str:
    """Strip comments + docstrings so prose about a defect never satisfies a check."""
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    src = re.sub(r"'''[\s\S]*?'''", "", src)
    return re.sub(r"(^|\s)#[^\n]*", " ", src)


_ws_src = code_only((_API / "services" / "primitives" / "workspace.py").read_text())
_as_src = code_only((_API / "services" / "authored_substrate.py").read_text())

print("\n── the mover carries BYTES, not the text denorm ──")

# The defect, stated exactly. `handle_move_file` must not re-write the source's
# text column at the destination — that is the empty-string carry.
_move = re.search(
    r"async def handle_move_file\(.*?(?=\nasync def |\ndef )", _ws_src, re.DOTALL
)
check("handle_move_file is readable", _move is not None)
if _move:
    body = _move.group(0)
    check(
        "the mover uses the shared head-blob form (not the text denorm)",
        "_head_content_form" in body,
    )
    # The FALSIFIER: the literal defect shape must be absent. Asserted on the
    # write, not on the select — a select may legitimately carry `content` for
    # other reasons, but passing it to write_revision as `content=` is the bug.
    check(
        "[FALSIFIER] the mover never writes the carried text as `content=`",
        not re.search(r"write_revision\((?:[^()]|\([^()]*\))*?\bcontent=content\b", body, re.DOTALL),
        "content=content in the destination write is the empty-string carry",
    )
    # It cannot ask for the head blob without selecting the column that names it.
    check(
        "the mover selects head_version_id (the form needs it)",
        "head_version_id" in body,
    )

print("\n── the head-blob form REFUSES rather than emptying a binary ──")

_form = re.search(r"def _head_content_form\(.*?(?=\ndef )", _as_src, re.DOTALL)
check("_head_content_form is readable", _form is not None)
if _form:
    fbody = _form.group(0)
    check(
        "it returns content_ref when the head blob resolves",
        'return {"content_ref"' in fbody,
    )
    # The latent bug: the `except` path fell through to the denorm, converting a
    # TRANSIENT read failure into PERMANENT data loss for a binary row.
    check(
        "[FALSIFIER] the fallback RAISES for a binary row instead of emptying it",
        "raise" in fbody and "content_type" in fbody,
        "a binary row whose blob lookup fails must refuse, not write ''",
    )
    # A refusal is only reachable if the callers actually supply the column it
    # keys on — otherwise the guard passes vacuously on every row.
    check(
        "[FALSIFIER] archive + restore SELECT content_type (else the guard is vacuous)",
        _as_src.count("head_version_id, content_type") >= 2,
        f"selects carrying content_type={_as_src.count('head_version_id, content_type')} (need >= 2)",
    )

print("\n── DERIVED: every content-carrying verb is byte-safe ──")

# THE ANTI-HAND-SPELLED-LIST ASSERTION.
#
# Find every write_revision(...) call in the primitive + substrate layer that
# passes `content=<a variable>` — i.e. carries a body forward from somewhere —
# and require each to be justified. A bare literal (`content=""`) is a fresh
# write, not a carry. A carried variable must either come from the shared form
# or be a site explicitly recorded as text-by-construction below.
#
# TEXT-BY-CONSTRUCTION, each with its reason. These are NOT exemptions granted
# for convenience — each writes a body it composed or must rewrite, where
# content_ref (a verbatim blob copy) could not do the job:
_TEXT_BY_CONSTRUCTION = {
    "_move_projection_sibling":
        "rewrites the derived_from: citation, so it NEEDS the text; the "
        "projection is .extracted.md by construction",
}

_carriers = []
for m in re.finditer(r"(?:async )?def (\w+)\(.*?(?=\n(?:async )?def |\Z)", _ws_src, re.DOTALL):
    name, body = m.group(1), m.group(0)
    if "write_revision(" not in body:
        continue
    # a carried body: content= followed by an identifier, not a literal
    if re.search(r"write_revision\((?:[^()]|\([^()]*\))*?\bcontent=(?!['\"])\w+", body, re.DOTALL):
        _carriers.append(name)

_unjustified = [c for c in _carriers if c not in _TEXT_BY_CONSTRUCTION]
check(
    "[FALSIFIER] every verb carrying a body forward is byte-safe or justified",
    not _unjustified,
    f"unjustified carriers: {_unjustified} — use _head_content_form, or record why text is required",
)
print(f"       (carriers found: {_carriers or 'none'})")

# The fan-out doors delegate to the ONE mover rather than re-implementing it.
# If any of these grew its own move, the fix above would not reach it.
_fo = code_only((_API / "services" / "folder_organize.py").read_text())
check(
    "the folder fan-out moves through the SAME mover (no second implementation)",
    '"MoveFile"' in _fo and "content=content" not in _fo,
)

print("\n" + ("binary-carry gate GREEN" if _passed else "binary-carry gate RED"))
sys.exit(0 if _passed else 1)
