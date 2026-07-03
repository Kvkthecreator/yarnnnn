"""ADR-406 — stale-parent rejection regression gate.

Locks the optimistic-concurrency contract on the singular write path:

1. write_revision precondition semantics — match → write; mismatch →
   StaleWriteError carrying the intervening head's attribution; None
   asserts "no revisions yet"; OMITTED → legacy append (no CAS).
2. D3 unique-violation translation — a precondition caller losing the
   race gets StaleWriteError; an APPEND caller retries on the fresh head
   and succeeds (appends must not fail under the linearity guard).
3. D2 route contract — FileEditRequest.expected_head_version_id, the
   409 translation, GET carrying head_version_id (source inspection).
4. D4 adoption boundary — EditFile threads the head it read; the capture
   lane / mechanical writers do NOT pass the precondition.
5. Migration 197 exists and names the guard index.

Run: .venv/bin/python api/test_adr406_stale_parent.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

_API_ROOT = Path(__file__).resolve().parent

_passed = 0
_failed = 0


def _assert(cond: bool, msg: str) -> None:
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  PASS  {msg}")
    else:
        _failed += 1
        print(f"  FAIL  {msg}")


# =============================================================================
# Fake Supabase client — programmable head + insert behavior
# =============================================================================


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, client, table):
        self._client = client
        self._table = table
        self._op = "select"
        self._row = None

    # chainable no-ops
    def select(self, *a, **k):
        self._op = "select"
        return self

    def eq(self, *a):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a):
        return self

    def insert(self, row):
        self._op = "insert"
        self._row = row
        return self

    def upsert(self, row, **k):
        self._op = "upsert"
        self._row = row
        return self

    def execute(self):
        c = self._client
        if self._table == "workspace_file_versions" and self._op == "select":
            return _Result(list(c.head_rows))
        if self._table == "workspace_file_versions" and self._op == "insert":
            if c.insert_raises:
                exc = c.insert_raises.pop(0)
                if exc is not None:
                    raise exc
            c.inserted.append(self._row)
            return _Result([{"id": f"rev-{len(c.inserted)}"}])
        return _Result([])


class FakeClient:
    def __init__(self, head_rows=None, insert_raises=None):
        # rows returned for every head/summary read (newest first)
        self.head_rows = head_rows or []
        # queue of exceptions for successive inserts (None = succeed)
        self.insert_raises = list(insert_raises or [])
        self.inserted = []

    def table(self, name):
        return _Query(self, name)


_HEAD = {
    "id": "rev-head",
    "authored_by": "operator",
    "message": "moved past you",
    "created_at": "2026-07-03T00:00:00Z",
}


# =============================================================================
# Group 1 — precondition semantics
# =============================================================================


def test_precondition() -> None:
    print("\n[1] write_revision precondition semantics (D1)")
    from services.authored_substrate import StaleWriteError, write_revision

    kw = dict(
        user_id="u1", path="/workspace/x.md", content="c",
        authored_by="operator", message="m", workspace_id="ws1",
    )

    # match → succeeds
    c = FakeClient(head_rows=[_HEAD])
    rev = write_revision(c, expected_parent_version_id="rev-head", **kw)
    _assert(bool(rev) and len(c.inserted) == 1, "matching precondition → write lands")
    _assert(
        c.inserted[0]["parent_version_id"] == "rev-head",
        "new revision parents on the expected head",
    )

    # mismatch → StaleWriteError with attribution, no insert
    c = FakeClient(head_rows=[_HEAD])
    try:
        write_revision(c, expected_parent_version_id="rev-old", **kw)
        _assert(False, "stale precondition raises StaleWriteError")
    except StaleWriteError as e:
        _assert(True, "stale precondition raises StaleWriteError")
        _assert(
            e.current_head.get("authored_by") == "operator",
            "error carries the intervening head's attribution",
        )
        _assert(len(c.inserted) == 0, "no revision inserted on stale write")

    # None asserts "file is new": no head → ok; head present → stale
    c = FakeClient(head_rows=[])
    rev = write_revision(c, expected_parent_version_id=None, **kw)
    _assert(bool(rev), "None precondition on a fresh path → write lands")

    c = FakeClient(head_rows=[_HEAD])
    try:
        write_revision(c, expected_parent_version_id=None, **kw)
        _assert(False, "None precondition on an existing chain → StaleWriteError")
    except StaleWriteError:
        _assert(True, "None precondition on an existing chain → StaleWriteError")

    # omitted → legacy append, no CAS
    c = FakeClient(head_rows=[_HEAD])
    rev = write_revision(c, **kw)
    _assert(bool(rev) and len(c.inserted) == 1, "omitted precondition → legacy append")


# =============================================================================
# Group 2 — D3 unique-violation translation
# =============================================================================


def test_race_translation() -> None:
    print("\n[2] linearity-guard race translation (D3)")
    from services.authored_substrate import StaleWriteError, write_revision

    kw = dict(
        user_id="u1", path="/workspace/x.md", content="c",
        authored_by="operator", message="m", workspace_id="ws1",
    )
    guard_exc = RuntimeError(
        'duplicate key value violates unique constraint '
        '"uq_workspace_file_versions_parent"'
    )

    # precondition caller losing the true race → StaleWriteError
    c = FakeClient(head_rows=[_HEAD], insert_raises=[guard_exc])
    try:
        write_revision(c, expected_parent_version_id="rev-head", **kw)
        _assert(False, "precondition caller losing the race → StaleWriteError")
    except StaleWriteError:
        _assert(True, "precondition caller losing the race → StaleWriteError")

    # append caller losing the race → retry on fresh head, succeeds
    c = FakeClient(head_rows=[_HEAD], insert_raises=[guard_exc, None])
    rev = write_revision(c, **kw)
    _assert(
        bool(rev) and len(c.inserted) == 1,
        "append caller retries on fresh head and succeeds",
    )

    # unrelated insert failure still raises untranslated
    c = FakeClient(head_rows=[_HEAD], insert_raises=[RuntimeError("boom")])
    try:
        write_revision(c, **kw)
        _assert(False, "unrelated failure is NOT swallowed")
    except RuntimeError:
        _assert(True, "unrelated failure is NOT swallowed")
    except StaleWriteError:
        _assert(False, "unrelated failure must not be translated to StaleWriteError")


# =============================================================================
# Group 3 — route + primitive wiring (source inspection)
# =============================================================================


def test_route_contract() -> None:
    print("\n[3] HTTP conflict contract (D2)")
    src = (_API_ROOT / "routes" / "workspace.py").read_text()
    _assert(
        "expected_head_version_id: Optional[str] = None" in src,
        "FileEditRequest carries expected_head_version_id",
    )
    _assert(
        "status_code=409" in src and '"error": "stale_write"' in src,
        "PATCH translates StaleWriteError → 409 stale_write",
    )
    _assert(
        '"current_head": e.current_head' in src,
        "409 detail carries the intervening head's attribution",
    )
    _assert(
        "head_version_id" in src.split("def get_workspace_file")[1].split("def ")[0],
        "GET /workspace/file returns head_version_id",
    )


def test_adoption_boundary() -> None:
    print("\n[4] adoption boundary (D4)")
    prim = (_API_ROOT / "services" / "primitives" / "workspace.py").read_text()
    edit_src = prim.split("async def handle_edit_file")[1].split("async def handle_delete_file")[0]
    _assert(
        "read_head_revision_id" in edit_src
        and "expected_parent_version_id=base_head" in edit_src,
        "EditFile threads the head it read",
    )
    _assert('"error": "stale_write"' in edit_src, "EditFile surfaces stale_write to the model")

    # Mechanical appenders MUST NOT adopt the precondition.
    for rel in (
        "services/capture/lane.py",
        "services/primitives/capture_connector.py",
        "services/outcomes/ledger.py",
    ):
        p = _API_ROOT / rel
        if not p.exists():
            continue
        _assert(
            "expected_parent_version_id" not in p.read_text(),
            f"{rel} does not pass the precondition (append semantics)",
        )


def test_migration() -> None:
    print("\n[5] migration 197 — the linearity guard")
    mig = _API_ROOT.parent / "supabase" / "migrations" / "197_adr406_linear_chain_guard.sql"
    _assert(mig.exists(), "197_adr406_linear_chain_guard.sql exists")
    if mig.exists():
        src = mig.read_text()
        _assert(
            "CREATE UNIQUE INDEX" in src
            and "uq_workspace_file_versions_parent" in src
            and "WHERE parent_version_id IS NOT NULL" in src,
            "partial UNIQUE index on parent_version_id",
        )


def main() -> int:
    print("=" * 72)
    print("ADR-406 — stale-parent rejection gate")
    print("=" * 72)

    test_precondition()
    test_race_translation()
    test_route_contract()
    test_adoption_boundary()
    test_migration()

    print("\n" + "=" * 72)
    print(f"RESULT: {_passed} passed, {_failed} failed")
    print("=" * 72)
    return 1 if _failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
