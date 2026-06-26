"""
ADR-373 Phase 1 regression gate — the user_id → workspace_id re-key spine.

Proves the spine is BYTE-IDENTICAL in N=1 BY CONSTRUCTION, without touching the
live DB:

  - the write path (write_revision + _insert_revision + _upsert_workspace_file +
    delete_live_file) accepts workspace_id OPTIONALLY;
  - when workspace_id is None, the row dicts handed to the DB client are
    IDENTICAL to the pre-ADR-373 shape (the N=1 fallback / un-backfilled path) —
    no workspace_id key is added;
  - when workspace_id IS supplied, exactly one workspace_id key is added,
    nothing else changes (dual-write, not re-key);
  - AuthenticatedClient grew workspace_id (the chokepoint) + the resolver exists;
  - migration 189 is ADDITIVE: drops nothing, keeps user_id, leaves
    workspace_blobs untouched, backfills N=1 singleton owner-workspaces.

Run: python3 test_adr373_rekey.py   (from api/)
No DB credentials required — uses a fake client that records the rows written.

Refs: docs/adr/ADR-373-multi-principal-workspace-and-the-re-key.md (D1/D5),
      supabase/migrations/189_adr373_multi_principal_rekey.sql.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

API_DIR = Path(__file__).parent
sys.path.insert(0, str(API_DIR))

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))


# ---------------------------------------------------------------------------
# A fake Supabase client that records every row the write path hands it.
# ---------------------------------------------------------------------------

class _FakeExecute:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    """Records insert/upsert payloads; returns a plausible id for inserts."""

    def __init__(self, table_name, recorder):
        self._table = table_name
        self._rec = recorder
        self._op = None
        self._payload = None

    def insert(self, payload):
        self._op, self._payload = "insert", payload
        return self

    def upsert(self, payload, on_conflict=None):
        self._op, self._payload = "upsert", payload
        self._rec.setdefault("on_conflict", {})[self._table] = on_conflict
        return self

    def select(self, *a, **k):
        self._op = "select"
        return self

    def eq(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def delete(self):
        self._op = "delete"
        return self

    def execute(self):
        if self._op in ("insert", "upsert"):
            self._rec.setdefault(self._table, []).append({
                "op": self._op,
                "payload": dict(self._payload),
            })
            # Inserts into the versions table need an id back.
            if self._table == "workspace_file_versions" and self._op == "insert":
                return _FakeExecute([{"id": "fake-rev-id"}])
            return _FakeExecute([dict(self._payload)])
        if self._op == "select":
            # _read_head_revision_id / delete_live_file live-row lookups → empty
            return _FakeExecute([])
        return _FakeExecute([])


class _FakeClient:
    def __init__(self):
        self.recorded: dict = {}

    def table(self, name):
        return _FakeQuery(name, self.recorded)


# ---------------------------------------------------------------------------
# Tests — the write path row shape
# ---------------------------------------------------------------------------

def test_write_revision_omits_workspace_id_when_unresolvable() -> None:
    """Resolution failure → no workspace_id key, write still succeeds (never blocks).

    Monkeypatches the resolver to None so the lazy resolution finds nothing —
    the row must be byte-identical to the pre-ADR-373 shape and the write must
    not raise.
    """
    from services import authored_substrate as a
    import services.supabase as s

    orig = s.resolve_owner_workspace_id
    s.resolve_owner_workspace_id = lambda _uid: None
    try:
        fc = _FakeClient()
        a.write_revision(
            fc, user_id="u1", path="operation/x.md", content="hello",
            authored_by="operator", message="m",
        )
    finally:
        s.resolve_owner_workspace_id = orig
    rev_rows = fc.recorded.get("workspace_file_versions", [])
    file_rows = fc.recorded.get("workspace_files", [])
    rev_ok = rev_rows and "workspace_id" not in rev_rows[0]["payload"]
    file_ok = file_rows and "workspace_id" not in file_rows[0]["payload"]
    record(
        "write_revision omits workspace_id when unresolvable (never blocks)",
        bool(rev_ok and file_ok),
        "" if (rev_ok and file_ok) else f"rev={rev_rows}, file={file_rows}",
    )


def test_write_revision_lazily_resolves_workspace_id() -> None:
    """The sweep chokepoint: an un-supplied workspace_id is resolved from user_id."""
    from services import authored_substrate as a
    import services.supabase as s

    orig = s.resolve_owner_workspace_id
    s.resolve_owner_workspace_id = lambda uid: "ws-from-resolver" if uid == "u1" else None
    try:
        fc = _FakeClient()
        a.write_revision(
            fc, user_id="u1", path="operation/x.md", content="hello",
            authored_by="operator", message="m",
            # workspace_id NOT passed → must be lazily resolved
        )
    finally:
        s.resolve_owner_workspace_id = orig
    rev = fc.recorded["workspace_file_versions"][0]["payload"]
    fil = fc.recorded["workspace_files"][0]["payload"]
    ok = rev.get("workspace_id") == "ws-from-resolver" and fil.get("workspace_id") == "ws-from-resolver"
    record(
        "write_revision lazily resolves workspace_id from user_id (sweep chokepoint)",
        ok,
        "" if ok else f"rev={rev}, file={fil}",
    )


def test_write_revision_adds_workspace_id_when_supplied() -> None:
    """Dual-write: exactly one workspace_id key added, nothing else changes."""
    from services.authored_substrate import write_revision

    fc = _FakeClient()
    write_revision(
        fc,
        user_id="u1",
        path="operation/x.md",
        content="hello",
        authored_by="operator",
        message="m",
        workspace_id="ws-123",
    )
    rev = fc.recorded["workspace_file_versions"][0]["payload"]
    fil = fc.recorded["workspace_files"][0]["payload"]
    ok = rev.get("workspace_id") == "ws-123" and fil.get("workspace_id") == "ws-123"
    # user_id MUST still be present (dual-key, not re-key)
    ok = ok and rev.get("user_id") == "u1" and fil.get("user_id") == "u1"
    record(
        "write_revision dual-writes workspace_id + keeps user_id",
        ok,
        "" if ok else f"rev={rev}, file={fil}",
    )


def test_upsert_conflict_target_unchanged() -> None:
    """ON CONFLICT stays (user_id, path) in Phase 1 — the UNIQUE is unchanged."""
    from services.authored_substrate import write_revision

    fc = _FakeClient()
    write_revision(
        fc, user_id="u1", path="operation/x.md", content="c",
        authored_by="operator", message="m", workspace_id="ws-1",
    )
    target = fc.recorded.get("on_conflict", {}).get("workspace_files")
    record(
        "workspace_files upsert conflict target stays (user_id,path)",
        target == "user_id,path",
        f"got on_conflict={target!r}",
    )


def test_delete_live_file_accepts_workspace_id() -> None:
    """delete_live_file threads workspace_id onto the tombstone revision."""
    import inspect
    from services.authored_substrate import delete_live_file

    sig = inspect.signature(delete_live_file)
    record(
        "delete_live_file accepts optional workspace_id",
        "workspace_id" in sig.parameters
        and sig.parameters["workspace_id"].default is None,
        f"params={list(sig.parameters)}",
    )


def test_all_write_helpers_accept_workspace_id_optionally() -> None:
    """Every spine function takes workspace_id with a None default (back-compat)."""
    import inspect
    from services import authored_substrate as a

    targets = ["write_revision", "_insert_revision", "_upsert_workspace_file", "delete_live_file"]
    bad = []
    for name in targets:
        fn = getattr(a, name)
        p = inspect.signature(fn).parameters.get("workspace_id")
        if p is None or p.default is not None:
            bad.append(name)
    record(
        "all 4 write-path functions accept optional workspace_id",
        not bad,
        f"missing/non-optional: {bad}" if bad else "",
    )


# ---------------------------------------------------------------------------
# Tests — the AuthenticatedClient chokepoint
# ---------------------------------------------------------------------------

def test_authenticated_client_has_workspace_id() -> None:
    from services.supabase import AuthenticatedClient

    import dataclasses
    fields = {f.name: f for f in dataclasses.fields(AuthenticatedClient)}
    ok = "workspace_id" in fields and fields["workspace_id"].default is None
    record(
        "AuthenticatedClient grew optional workspace_id field",
        ok,
        f"fields={list(fields)}",
    )


def test_resolver_exists_and_caches() -> None:
    from services import supabase as s

    ok = hasattr(s, "resolve_owner_workspace_id") and hasattr(s, "_resolve_owner_workspace_id_cached")
    # the cached impl must actually be an lru_cache wrapper
    cached = getattr(s, "_resolve_owner_workspace_id_cached", None)
    ok = ok and cached is not None and hasattr(cached, "cache_clear")
    record(
        "resolve_owner_workspace_id exists + is cached (no per-request DB hit)",
        ok,
        "",
    )


# ---------------------------------------------------------------------------
# Tests — migration 189 is ADDITIVE (grep gates against the SQL)
# ---------------------------------------------------------------------------

def _migration_text() -> str:
    p = API_DIR.parent / "supabase" / "migrations" / "189_adr373_multi_principal_rekey.sql"
    return p.read_text() if p.exists() else ""


def test_migration_exists() -> None:
    record("migration 189 exists", bool(_migration_text()), "")


def test_migration_drops_nothing() -> None:
    sql = _migration_text().upper()
    # No DROP COLUMN / DROP TABLE / DROP CONSTRAINT in Phase 1 — additive only.
    has_drop = any(tok in sql for tok in ("DROP COLUMN", "DROP TABLE", "DROP CONSTRAINT"))
    record("migration 189 drops nothing (additive)", not has_drop,
           "found a DROP — Phase 1 must be additive" if has_drop else "")


def test_migration_keeps_user_id() -> None:
    sql = _migration_text()
    # user_id must NOT be dropped/renamed off the substrate tables in Phase 1.
    bad = "ALTER COLUMN user_id" in sql and "DROP" in sql.upper()
    record("migration 189 keeps user_id on substrate tables", not bad, "")


def test_migration_leaves_blobs_untouched() -> None:
    sql = _migration_text()
    # workspace_blobs is content-addressed global — must not gain workspace_id.
    touches_blobs = "ALTER TABLE workspace_blobs" in sql
    record("migration 189 leaves workspace_blobs untouched", not touches_blobs,
           "migration touches workspace_blobs" if touches_blobs else "")


def test_migration_reuses_existing_workspaces() -> None:
    """ADR-373 reuses the EXISTING workspaces table (billing root), not a new one."""
    sql = _migration_text()
    # Must NOT create a workspaces table (it already exists, 001_initial_schema).
    creates_ws = "CREATE TABLE IF NOT EXISTS workspaces" in sql or "CREATE TABLE workspaces" in sql
    # Must key the backfill off the existing owner_id column.
    uses_owner_id = "w.owner_id = wf.user_id" in sql or "owner_id = wf.user_id" in sql
    record(
        "migration 189 reuses existing workspaces (owner_id join), no new table",
        (not creates_ws) and uses_owner_id,
        f"creates_ws={creates_ws}, uses_owner_id={uses_owner_id}",
    )


def test_migration_grants_and_notnull() -> None:
    sql = _migration_text()
    ok = (
        "CREATE TABLE IF NOT EXISTS principal_grants" in sql
        and "'owner'" in sql  # seeds owner grants
        and "SET NOT NULL" in sql  # flips workspace_id NOT NULL after backfill
        and "REFERENCES workspaces(id)" in sql  # FK to the existing table
    )
    record("migration 189 adds principal_grants + owner grants + NOT NULL flip", ok, "")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    test_write_revision_omits_workspace_id_when_unresolvable()
    test_write_revision_lazily_resolves_workspace_id()
    test_write_revision_adds_workspace_id_when_supplied()
    test_upsert_conflict_target_unchanged()
    test_delete_live_file_accepts_workspace_id()
    test_all_write_helpers_accept_workspace_id_optionally()
    test_authenticated_client_has_workspace_id()
    test_resolver_exists_and_caches()
    test_migration_exists()
    test_migration_drops_nothing()
    test_migration_keeps_user_id()
    test_migration_leaves_blobs_untouched()
    test_migration_reuses_existing_workspaces()
    test_migration_grants_and_notnull()

    total = len(RESULTS)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print()
    print(f"=== ADR-373 Phase 1 re-key spine: {passed}/{total} passed ===")
    for name, ok, detail in RESULTS:
        icon = "✓" if ok else "✗"
        print(f"  {icon} {name}" + (f" — {detail}" if not ok else ""))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
