"""Gate: a trashed file leaves the surfaces that promise removal.

Delete is trash-not-erase (ADR-329/ADR-400/ADR-209): it writes a new attributed
revision with lifecycle='archived'. The row, the chain, and the blob all
survive — deletion is a WRITE. What must change is VISIBILITY.

The file-lifecycle audit (2026-07-20) found that visibility was enforced
per-caller, and two consequential readers didn't:

  • the SEARCH RPCs — so a trashed file stayed searchable and its content kept
    reaching agent reasoning. Fixed in SQL (migration 218), because a
    Python-side filter cannot reach inside an RPC.
  • the STUDIO LANDING — so a trashed artifact stayed in Recents. Newly
    load-bearing after ADR-470 D5 made Trash the only cleanup path for
    untitled artifacts.

POLARITY is the thing to protect: the predicate must be NULL-tolerant
(`lifecycle IS NULL OR lifecycle <> 'archived'`). A bare `<> 'archived'` drops
every row whose lifecycle is NULL — a silent, worse regression than the bug.

Run: python3 test_trash_visibility.py   (check()-style, NOT pytest)
"""

import pathlib
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
    root = pathlib.Path(__file__).parent.parent
    studio = (root / "api/routes/studio.py").read_text()
    workspace = (root / "api/routes/workspace.py").read_text()
    docs = (root / "api/routes/documents.py").read_text()
    mig = (root / "supabase/migrations/218_search_excludes_archived.sql").read_text()

    NULL_TOLERANT = "lifecycle.is.null,lifecycle.neq.archived"
    SQL_PRED = "wf.lifecycle IS NULL OR wf.lifecycle <> 'archived'"

    print("── 1. Delete stays trash-not-erase (nothing here erases) ──────")
    _check(
        "delete writes an ARCHIVED REVISION, not a row deletion",
        'lifecycle="archived"' in docs and "write_revision(" in docs,
    )
    _check(
        "restore writes an ACTIVE revision (symmetric, reversible)",
        'lifecycle="active"' in docs and "Restored from trash" in docs,
    )
    _check(
        "no hard-delete of workspace_files in the documents routes",
        'table("workspace_files").delete()' not in docs,
    )

    print("\n── 2. SEARCH excludes archived — in SQL, unbypassable ─────────")
    _check("migration 218 exists and patches both RPCs", mig.count(SQL_PRED) == 2)
    _check(
        "it redefines search_workspace AND search_workspace_semantic",
        "FUNCTION public.search_workspace(" in mig
        and "FUNCTION public.search_workspace_semantic(" in mig,
    )
    # The signatures must be replayed verbatim — a changed signature would
    # create a SECOND overload and leave the old, unfiltered one callable.
    _check(
        "signatures replayed verbatim (no new overload)",
        mig.count("p_allowed_prefixes text[] DEFAULT NULL::text[]") == 2
        and mig.count("p_workspace_id uuid") == 2,
    )
    _check(
        "the powerbox read-scope predicate is preserved, not dropped",
        mig.count("p_allowed_prefixes IS NULL") == 2,
    )

    print("\n── 3. The STUDIO LANDING excludes archived ────────────────────")
    landing = studio.split("async def list_artifacts")[1].split("return {")[0]
    _check("the landing query carries the predicate", NULL_TOLERANT in landing)
    _check(
        "it matches the Files tree's own predicate (one rule, not a variant)",
        NULL_TOLERANT in workspace,
    )

    print("\n── 4. POLARITY — NULL-tolerant everywhere ─────────────────────")
    # A bare .neq (no is.null companion) silently drops NULL-lifecycle rows.
    _check(
        "no bare .neq('lifecycle','archived') anywhere in the routes",
        'neq("lifecycle", "archived")' not in studio
        and 'neq("lifecycle", "archived")' not in workspace,
    )
    # Count the PREDICATE (wf.-qualified), not the prose — the polarity note in
    # the migration header mentions the unqualified form and would inflate this.
    _check(
        "the SQL predicate is NULL-tolerant in both RPCs",
        mig.count(f"AND ({SQL_PRED})") == 2,
    )
    _check(
        "archived stays READABLE by exact path (Trash lists, Restore reads)",
        "eq(\"lifecycle\", \"archived\")" in docs,  # the Trash listing
    )

    print(f"\n{'PASS' if _fail == 0 else 'FAIL'}: {_pass}/{_pass + _fail} checks")
    return 1 if _fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
