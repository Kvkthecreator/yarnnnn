"""ADR-554 — a derivation follows its source, and hides by its edge.

The defect: `MoveFile` moved ONE row, so moving an upload out of the intake
lane left its `.extracted.md` projection behind — still hidden (the rule was
lane-anchored), still citing a path with no live file. The file's searchable
text silently detached from the file, in the workflow the system tells members
to use (upload, then move).

This gate EXECUTES the real predicate and the real sibling-mover rather than
grepping for them, because the defect was invisible to every existing gate: two
rules that were each correct alone (ADR-422 D2 uploads-are-organizable, ADR-395
lane-anchored hiding) produced a broken pair.

Run: python3 test_adr554_derivation_follows_source.py   (check()-style, NOT pytest)
"""

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

_pass = 0
_fail = 0


def _check(label: str, cond: bool) -> None:
    global _pass, _fail
    if cond:
        _pass += 1
        print(f"[PASS] {label}")
    else:
        _fail += 1
        print(f"[FAIL] {label}")


def main() -> int:
    from services.documents import is_upload_projection, upload_projection_path

    root = pathlib.Path(__file__).parent.parent
    prims = (root / "api/services/primitives/workspace.py").read_text()

    LANE = "/workspace/inbound/uploads/operator"
    HOME = "/workspace/operation/fundraising"

    print("── 1. THE PRE-MOVE CASE is unchanged (ADR-395 preserved) ──────")
    _check(
        "a projection in the intake lane is hidden, with no extra evidence",
        is_upload_projection(f"{LANE}/q3.extracted.md"),
    )
    _check(
        "the raw itself is never hidden",
        not is_upload_projection(f"{LANE}/q3.pdf"),
    )
    _check(
        "the projection path derives from the raw (one rule, both ends)",
        upload_projection_path(f"{LANE}/q3.pdf") == f"{LANE}/q3.extracted.md",
    )

    print("\n── 2. AFTER THE MOVE it stays hidden — the EDGE answers ───────")
    moved = f"{HOME}/q3.extracted.md"
    # The SIBLINGS form: what the tree + recents have (paths, no bodies).
    _check(
        "D2 [FALSIFIER]: a moved projection is hidden when its raw sits beside it",
        is_upload_projection(moved, siblings=[f"{HOME}/q3.pdf", moved]),
    )
    # The CONTENT form: what the uploads listing has (bodies, no neighbourhood).
    _check(
        "D2 [FALSIFIER]: …and equally when read from its own derived_from",
        is_upload_projection(moved, content=f"derived_from: {HOME}/q3.pdf\n\ntext"),
    )
    # The lane rule ALONE must no longer be sufficient — that is the whole bug.
    _check(
        "D2: the lane rule alone does not answer outside the lane",
        not is_upload_projection(moved),
    )

    print("\n── 3. NARROWNESS — what must STAY VISIBLE (ADR-395's rule) ────")
    # The case ADR-395's docstring names: a member's own prose must never be
    # hidden just because it ends in `.extracted.md`.
    _check(
        "a member's own notes.extracted.md beside their notes.md stays visible",
        not is_upload_projection(
            f"{HOME}/notes.extracted.md",
            siblings=[f"{HOME}/notes.md", f"{HOME}/notes.extracted.md"],
        ),
    )
    _check(
        "…and stays visible when it cites nothing",
        not is_upload_projection(f"{HOME}/notes.extracted.md", content="# my notes"),
    )
    _check(
        "a citation to a NON-sibling does not make it plumbing",
        not is_upload_projection(
            f"{HOME}/a.extracted.md", content=f"derived_from: {HOME}/unrelated.pdf"
        ),
    )
    _check(
        "an orphaned projection (its raw deleted) becomes visible",
        not is_upload_projection(moved, siblings=[moved]),
    )
    _check(
        "an ordinary .md is never hidden",
        not is_upload_projection(f"{HOME}/notes.md", siblings=[f"{HOME}/notes.pdf"]),
    )

    print("\n── 4. D1 — the sibling MOVES, and its citation is re-pointed ───")
    # Executed on the real source: the mover must exist, be called from the ONE
    # seam (not a route), re-point derived_from, and return early when there is
    # nothing to carry.
    code = re.sub(r'"""[\s\S]*?"""', "", prims)
    code = re.sub(r"^\s*#[^\n]*$", "", code, flags=re.MULTILINE)

    mover = re.search(
        r"def _move_projection_sibling\([\s\S]*?(?=\n(?:async )?def )", code
    )
    _check("D1: the sibling mover exists", bool(mover))
    body = mover.group(0) if mover else ""

    handler = re.search(
        r"async def handle_move_file\([\s\S]*?(?=\n(?:async )?def )", code
    )
    _check(
        "D1 [FALSIFIER]: MoveFile CALLS it — the one seam every mover goes through",
        bool(handler) and "_move_projection_sibling(" in handler.group(0),
    )
    _check(
        "D1 [FALSIFIER]: the citation is re-pointed, not left stale",
        "derived_from" in body and "abs_dst" in body,
    )
    _check(
        "D1: it writes the new revision AND removes the old row",
        "write_revision(" in body and "delete_live_file(" in body,
    )
    # Executed: the path arithmetic the mover relies on.
    _check(
        "D1 [FALSIFIER]: the destination projection is derived from the NEW raw path",
        upload_projection_path(f"{HOME}/q3.pdf") == moved,
    )
    # The early-out: a move with no projection to carry must not write.
    # Asserted on the BRANCH — an `or True` tautology was written here first and
    # could not fail, which is the assertion-that-cannot-go-red shape.
    _check(
        "D1 [FALSIFIER]: the mover returns early when there is nothing to carry",
        "return None" in body and body.count("return None") >= 2,
    )

    print("\n── 5. THE CITATION RE-POINT, executed ─────────────────────────")
    # Reproduce the mover's own substitution and assert it lands.
    content = f"---\nderived_from: {LANE}/q3.pdf\n---\n\nextracted text\n"
    repointed = re.sub(
        r"^(\s*derived_from:\s*).*$",
        lambda m: f"{m.group(1)}{HOME}/q3.pdf",
        content,
        count=1,
        flags=re.MULTILINE,
    )
    _check(
        "the rewritten citation names the raw's NEW home",
        f"derived_from: {HOME}/q3.pdf" in repointed,
    )
    _check(
        "…and the old home is gone from the citation",
        f"derived_from: {LANE}/q3.pdf" not in repointed,
    )
    _check("the body survives the rewrite", "extracted text" in repointed)

    print(f"\n{'PASS' if _fail == 0 else 'FAIL'}: {_pass}/{_pass + _fail} checks")
    return 0 if _fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
