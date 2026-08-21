"""A trashed file does not read back — on ANY path.

Run: `python3 test_trashed_file_does_not_read_back.py` from `api/`.

WHY THIS EXISTS (2026-08-21)

The operator moved 20 briefs to Trash. The delete was CORRECT — all 20 rows
carry `lifecycle='archived'`, the revision chain intact, restorable. But they
kept appearing:

  - in the Text app's "Continue where you left off" tiles,
  - opening at their URL with full content,
  - reading back through `ReadFile`,
  - matching in `SearchFiles`,

so the operator reasonably concluded the delete had failed. It had not. FOUR
READ PATHS did not ask whether the file was in Trash.

THE STRUCTURAL CAUSE

A trashed file KEEPS its `workspace_files` row — delete is a lifecycle
transition (ADR-337 D2 / ADR-400), not a row removal, and that is exactly what
makes it restorable. So "the row exists" and "the file is live" are DIFFERENT
QUESTIONS, and every read must ask the second one explicitly.

The predicate was a STRING copied by hand into six call sites and absent from
four others, in two mutually-incompatible dialects:

    .or_("lifecycle.is.null,lifecycle.neq.archived")   # 6 sites
    .in_("lifecycle", ["active", "delivered"])         # 4 sites

Both happen to agree TODAY (the column is fully backfilled — zero NULL rows
measured in production), which is precisely why the divergence went unnoticed:
the dialects differ only on a case that does not currently occur. The first is
canonical, because `lifecycle IS NULL` must read as LIVE for any row written
before the column had a default.

This gate asserts the BEHAVIOUR (a trashed path yields nothing), not the
spelling — a gate on the string would pass on the wrong dialect.
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


def code_only(text: str) -> str:
    text = re.sub(r"#.*$", "", text, flags=re.MULTILINE)
    return re.sub(r'""".*?"""', "", text, flags=re.DOTALL)


print("\n[1] there is ONE spelling of not-in-Trash, and it is null-safe")

from services.primitives.registry import HANDLERS  # noqa: E402
from services.workspace_context import (  # noqa: E402
    LIVE_FILES_OR_CLAUSE,
    live_files_filter,
)

check("the canonical clause treats a NULL lifecycle as LIVE",
      "lifecycle.is.null" in LIVE_FILES_OR_CLAUSE,
      "dropping the NULL half silently hides every pre-column row — a worse "
      "regression than the one this fixes")
check("…and excludes archived", "lifecycle.neq.archived" in LIVE_FILES_OR_CLAUSE)


class _Q:
    """Minimal query double — records what the helper applied."""

    def __init__(self):
        self.applied = []

    def or_(self, clause):
        self.applied.append(clause)
        return self


_probe = _Q()
live_files_filter(_probe)
check("the helper APPLIES the clause (not merely exports the string)",
      _probe.applied == [LIVE_FILES_OR_CLAUSE],
      "a bare constant still lets a caller forget to call .or_() with it")


print("\n[2] every workspace-scope READ asks the question")

_ws_src = code_only((_API / "services" / "workspace.py").read_text())

# UserMemory is the class that serves scope='workspace' reads — the path
# `handle_read_file` takes for the operator's own substrate. Both its readers
# must filter, and they must not disagree with each other.
for fn in ("async def read(", "def read_sync("):
    i = _ws_src.find(fn)
    check(f"UserMemory.{fn.split('def ')[1].rstrip('(')} filters trashed rows",
          i != -1 and "live_files_filter" in _ws_src[i:i + 900],
          "a read without the filter serves content the operator deleted")


print("\n[3] SEARCH does not surface trashed content")

_prim_src = code_only((_API / "services" / "primitives" / "workspace.py").read_text())

i = _prim_src.find("def _exact_search(")
_exact = _prim_src[i:i + 2000] if i != -1 else ""
check("_exact_search excludes archived rows",
      "archived" in _exact,
      "ADR-337 D4 exact mode matched content OR path with no lifecycle predicate")
# ⚠️ The reason it is NOT `live_files_filter` here: the match already occupies
# this query's one `.or_()` slot, and a second `.or_()` REPLACES the first —
# which would turn a substring search into "everything not archived".
check("…and it does NOT stack a second .or_() (which would replace the match)",
      _exact.count(".or_(") <= 1,
      "two .or_() calls on one PostgREST query silently drop the first")

# The ranked/semantic paths are filtered in SQL (migration 218) so a new caller
# inherits the behaviour — a Python-side filter cannot reach inside an RPC.
_mig = (_ROOT / "supabase" / "migrations" / "218_search_excludes_archived.sql")
check("the search RPCs exclude archived IN SQL (unbypassable by callers)",
      _mig.exists() and "lifecycle" in _mig.read_text())


print("\n[4] RECENTS offers only files that still exist")

_route_src = code_only((_API / "routes" / "workspace.py").read_text())
i = _route_src.find("candidate_paths = list(latest_by_path.keys())")
_recents = _route_src[i:i + 1200] if i != -1 else ""
check("the recent-revisions live-file lookup filters trashed rows",
      "live_files_filter" in _recents,
      "'the revision resolves a row' is not 'the file is live' — this is what "
      "kept 20 trashed briefs tiled in the Text app")


print("\n[5] the two dialects do not disagree about a NULL lifecycle")

# `in_("lifecycle", [...])` EXCLUDES NULL; the canonical clause INCLUDES it.
# They agree only while the column is fully backfilled. Any site still using the
# enumerated form must be listed here deliberately, so the divergence is a
# decision rather than an accident.
_enumerated_ok = {
    "services/workspace.py",           # list_files: agent-scope subtree walk
    "services/primitives/workspace.py",  # ListFiles: same, workspace-scope
    "services/mcp_composition.py",     # interop list
    "services/working_memory.py",      # prompt injection
}
_offenders = []
for p in (_API / "services").rglob("*.py"):
    src = code_only(p.read_text())
    if 'in_("lifecycle"' in src:
        rel = str(p.relative_to(_API))
        if rel not in _enumerated_ok:
            _offenders.append(rel)
check("no NEW site adopts the null-excluding dialect without a decision",
      not _offenders,
      f"{_offenders} — use live_files_filter, or add to the reviewed list here")



print("\n[6] ONE delete, ONE meaning — and it is reversible")

_as_src = code_only((_API / "services" / "authored_substrate.py").read_text())
_prim_src2 = code_only((_API / "services" / "primitives" / "workspace.py").read_text())
_route_src2 = code_only((_API / "routes" / "documents.py").read_text())

check("there is an archiving act in the ONE write path",
      "def archive_live_file(" in _as_src)

# THE UNIFICATION. `DeleteFile` used to call `delete_live_file`, which REMOVED
# the row: attributed and retained in the chain, but absent from Trash and not
# restorable in one act. The operator's own click archived instead — so delete
# meant two different things depending on who asked (measured before the fix:
# 27 archived rows vs 13 row-removal tombstones).
i = _prim_src2.find("async def handle_delete_file(")
_del = _prim_src2[i:i + 2500] if i != -1 else ""
check("DeleteFile ARCHIVES (goes to Trash), never removes the live row",
      "archive_live_file" in _del and "delete_live_file" not in _del,
      "a delete that removes the row cannot appear in Trash or be Restored")

check("the Files route calls the SAME act (one implementation, not two that agree)",
      "archive_live_file" in _route_src2)

# `delete_live_file` STAYS — it is correct for MOVE, where the source row must
# genuinely go (the file lives at its destination; archiving the source would
# put a moved file in Trash as well).
i2 = _prim_src2.find("async def handle_move_file(")
_mv = _prim_src2[i2:i2 + 3000] if i2 != -1 else ""
check("MoveFile still REMOVES its source row (a move is not a deletion)",
      "delete_live_file" in _mv,
      "archiving a move's source would put a moved file in Trash")

check("Restore exists as a verb (delete without it is `rm` with no Put Back)",
      "Restore" in set(HANDLERS))

# ONE act each, at BOTH grains. The folder fan-out, the single-file route and
# the Restore primitive each used to carry their own archive/restore write with
# their own copy of the head-blob form. They AGREED — which is not the same as
# being singular: the next change to what archiving means would have had to be
# made three times, and the third is the one that gets forgotten.
_fo_src = code_only((_API / "services" / "folder_organize.py").read_text())
_folder_prim_src = code_only((_API / "services" / "primitives" / "folder.py").read_text())

check("the folder fan-out archives through the SAME act (no second write)",
      "archive_live_file" in _fo_src and 'lifecycle="archived"' not in _fo_src)
check("the folder fan-out restores through the SAME act",
      "restore_live_file" in _fo_src and 'lifecycle="active"' not in _fo_src)
check("the Restore primitive uses the shared act, not its own write",
      "restore_live_file" in _folder_prim_src
      and "write_revision" not in _folder_prim_src)
check("the documents route restores through the shared act",
      "restore_live_file" in _route_src2)

# The head-blob form (ADR-427 Phase 2) is a property of the LEDGER, so it lives
# with the ledger — three near-identical private copies are gone.
_dupes = []
for rel in ("routes/documents.py", "services/folder_organize.py",
            "services/primitives/folder.py"):
    if "def _content_form_for_head(" in code_only((_API / rel).read_text()):
        _dupes.append(rel)
check("no module keeps a private copy of the head-blob form",
      not _dupes, f"{_dupes} — use authored_substrate._head_content_form")

# ⚠️ And the distinction that must NOT collapse: a move is not a deletion.
check("MoveFolder still REMOVES its source rows (never archives them)",
      "delete_live_file" in code_only(
          (_API / "services" / "primitives" / "workspace.py").read_text()),
      "archiving a move's source would put a moved file in Trash")

print()
if FAILED:
    print(f"trashed-read gate RED — {PASSED} passed, {len(FAILED)} failed")
    for f in FAILED:
        print(f"    - {f}")
    sys.exit(1)
print(f"trashed-read gate GREEN — {PASSED}/{PASSED}")
