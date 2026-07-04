"""ADR-373 Phase 1 (sweep spine, ADR-404 step 4) — regression gate.

Locks the workspace-binding spine that makes member reach possible without
threading a parameter through the ~118 historical call sites:

1. `effective_workspace_id` precedence — explicit > request contextvar >
   owner-resolution > None (legacy user_id scoping).
2. `_substrate_scope` — workspace-keyed when resolvable, user_id fallback.
3. `resolve_workspace_for_principal` — requested workspace honored iff
   reachable (owner or active grant), FAIL-CLOSED otherwise; no request →
   owner workspace; fresh invitee (no owned workspace) → newest grant.
4. Auth wiring — get_user_client accepts X-Workspace-Id, 403s on an
   unreachable request, publishes + resets the contextvar (source
   inspection).
5. The workspace-keyed upsert — updates the existing (workspace_id, path)
   row WITHOUT flipping user_id (the row creator stays; attribution lives
   in the revision chain); inserts with user_id when the row is new.
6. Data-class scoping — UserMemory/AgentWorkspace reads key on
   workspace_id when the request binding is set.
7. Migration 198 — UNIQUE (workspace_id, path) + membership write RLS.
8. N=1 byte-identical — no binding + no resolution → legacy user_id
   scoping everywhere.

Run: .venv/bin/python api/test_adr373_sweep_spine.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import patch

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
# Fakes
# =============================================================================


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    """Records filters; returns programmed rows keyed by (table, op)."""

    def __init__(self, client, table):
        self._c = client
        self._t = table
        self._op = "select"
        self._filters = {}
        self._row = None

    def select(self, *a, **k):
        self._op = "select"
        return self

    def insert(self, row):
        self._op = "insert"
        self._row = row
        return self

    def update(self, row):
        self._op = "update"
        self._row = row
        return self

    def upsert(self, row, **k):
        self._op = "upsert"
        self._row = row
        self._c.calls.append((self._t, "upsert", row, dict(k)))
        return self

    def delete(self):
        self._op = "delete"
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def like(self, *a):
        return self

    def in_(self, *a):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a):
        return self

    def execute(self):
        self._c.calls.append((self._t, self._op, self._row, dict(self._filters)))
        rows = self._c.responses.get((self._t, self._op), [])
        return _Result(rows)


class FakeClient:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.calls = []

    def table(self, name):
        return _Query(self, name)


def _ws_calls(client, table, op):
    return [c for c in client.calls if c[0] == table and c[1] == op]


# =============================================================================
# Group 1 — effective_workspace_id + _substrate_scope
# =============================================================================


def test_effective_workspace_id() -> None:
    print("\n[1] effective_workspace_id precedence")
    from services.workspace_context import (
        effective_workspace_id, reset_request_workspace, set_request_workspace,
    )

    _assert(
        effective_workspace_id("u1", explicit="ws-explicit") == "ws-explicit",
        "explicit wins",
    )

    tok = set_request_workspace("ws-ctx")
    try:
        _assert(effective_workspace_id("u1") == "ws-ctx", "request contextvar second")
        _assert(
            effective_workspace_id("u1", explicit="ws-explicit") == "ws-explicit",
            "explicit still wins over contextvar",
        )
    finally:
        reset_request_workspace(tok)

    with patch("services.supabase.resolve_owner_workspace_id", return_value="ws-own"):
        _assert(effective_workspace_id("u1") == "ws-own", "owner-resolution third")
    with patch("services.supabase.resolve_owner_workspace_id", return_value=None):
        _assert(effective_workspace_id("u1") is None, "unresolvable → None (legacy)")


def test_substrate_scope() -> None:
    print("\n[2] _substrate_scope keying")
    from services.authored_substrate import _substrate_scope

    c = FakeClient()
    q = _substrate_scope(c.table("workspace_file_versions").select("id"), "u1", "ws1")
    q.execute()
    _assert(
        c.calls[-1][3].get("workspace_id") == "ws1" and "user_id" not in c.calls[-1][3],
        "workspace resolvable → keys on workspace_id only",
    )

    c = FakeClient()
    q = _substrate_scope(c.table("workspace_file_versions").select("id"), "u1", None)
    q.execute()
    _assert(
        c.calls[-1][3].get("user_id") == "u1" and "workspace_id" not in c.calls[-1][3],
        "workspace unresolvable → legacy user_id scoping",
    )


# =============================================================================
# Group 2 — resolve_workspace_for_principal
# =============================================================================


def test_resolver() -> None:
    print("\n[3] resolve_workspace_for_principal")
    import services.supabase as sb

    # requested + owner → honored
    with patch.object(sb, "resolve_owner_workspace_id", return_value="ws-own"):
        _assert(
            sb.resolve_workspace_for_principal("u1", "ws-own") == "ws-own",
            "requested own workspace → honored",
        )

    # requested + active grant → honored (grant lookup via service client)
    grant_client = FakeClient(responses={("principal_grants", "select"): [{"id": "g1"}]})
    with patch.object(sb, "resolve_owner_workspace_id", return_value="ws-own"), \
         patch.object(sb, "get_service_client", return_value=grant_client):
        _assert(
            sb.resolve_workspace_for_principal("u1", "ws-other") == "ws-other",
            "requested granted workspace → honored",
        )

    # requested + no reach → None (fail-closed; auth layer 403s)
    no_grant = FakeClient(responses={("principal_grants", "select"): []})
    with patch.object(sb, "resolve_owner_workspace_id", return_value="ws-own"), \
         patch.object(sb, "get_service_client", return_value=no_grant):
        _assert(
            sb.resolve_workspace_for_principal("u1", "ws-stranger") is None,
            "requested unreachable workspace → None (fail-closed)",
        )

    # no request → owner workspace
    with patch.object(sb, "resolve_owner_workspace_id", return_value="ws-own"):
        _assert(
            sb.resolve_workspace_for_principal("u1") == "ws-own",
            "no request → owner workspace (byte-identical N=1)",
        )

    # fresh invitee: no owned workspace → newest grant's workspace
    invitee = FakeClient(
        responses={("principal_grants", "select"): [{"workspace_id": "ws-commons"}]}
    )
    with patch.object(sb, "resolve_owner_workspace_id", return_value=None), \
         patch.object(sb, "get_service_client", return_value=invitee):
        _assert(
            sb.resolve_workspace_for_principal("u2") == "ws-commons",
            "fresh invitee (no owned workspace) → newest grant's workspace",
        )


def test_auth_wiring() -> None:
    print("\n[4] auth wiring (source inspection)")
    src = (_API_ROOT / "services" / "supabase.py").read_text()
    _assert('alias="X-Workspace-Id"' in src, "get_user_client accepts X-Workspace-Id")
    _assert(
        "if x_workspace_id and workspace_id is None" in src and "status_code=403" in src,
        "unreachable requested workspace → 403 (fail-closed)",
    )
    _assert(
        "set_request_workspace(workspace_id)" in src
        and "reset_request_workspace(_ws_token)" in src,
        "contextvar published at auth and reset on teardown",
    )


# =============================================================================
# Group 3 — the workspace-keyed upsert (member write lands on the same row)
# =============================================================================


def test_workspace_keyed_upsert() -> None:
    print("\n[5] workspace-keyed update-or-insert")
    from services.authored_substrate import _upsert_workspace_file

    # existing row → UPDATE without user_id/workspace_id/path in the payload
    c = FakeClient(responses={("workspace_files", "select"): [{"id": "f1"}]})
    _upsert_workspace_file(
        c, user_id="member-1", path="/workspace/x.md", content="c",
        head_version_id="rev-9", workspace_id="ws1",
    )
    updates = _ws_calls(c, "workspace_files", "update")
    _assert(len(updates) == 1, "existing (workspace, path) row → UPDATE")
    if updates:
        row, filters = updates[0][2], updates[0][3]
        _assert(
            "user_id" not in row,
            "UPDATE does not flip user_id (creator stays; chain attributes)",
        )
        _assert(
            filters.get("workspace_id") == "ws1" and filters.get("path") == "/workspace/x.md",
            "UPDATE keyed on (workspace_id, path)",
        )

    # no row → INSERT carries user_id + workspace_id
    c = FakeClient(responses={("workspace_files", "select"): []})
    _upsert_workspace_file(
        c, user_id="member-1", path="/workspace/new.md", content="c",
        head_version_id="rev-1", workspace_id="ws1",
    )
    inserts = _ws_calls(c, "workspace_files", "insert")
    _assert(
        len(inserts) == 1 and inserts[0][2].get("user_id") == "member-1"
        and inserts[0][2].get("workspace_id") == "ws1",
        "new path → INSERT with creator user_id + workspace_id",
    )

    # workspace unresolvable → legacy upsert on (user_id, path)
    c = FakeClient()
    _upsert_workspace_file(
        c, user_id="u1", path="/workspace/x.md", content="c",
        head_version_id="rev-1", workspace_id=None,
    )
    upserts = [x for x in c.calls if x[1] == "upsert" and x[3].get("on_conflict")]
    inserts = _ws_calls(c, "workspace_files", "insert")
    _assert(
        not upserts
        and len(inserts) == 1
        and inserts[0][2].get("user_id") == "u1"
        and "workspace_id" not in inserts[0][2],
        "no workspace → manual (user_id, path)-keyed write, no on_conflict (199-ready)",
    )


# =============================================================================
# Group 4 — data-class scoping under a request binding
# =============================================================================


def test_data_class_scoping() -> None:
    print("\n[6] UserMemory / AgentWorkspace scoping")
    from services.workspace import AgentWorkspace, UserMemory
    from services.workspace_context import (
        reset_request_workspace, set_request_workspace,
    )

    tok = set_request_workspace("ws-bound")
    try:
        c = FakeClient()
        um = UserMemory(c, "member-1")
        asyncio.run(um.read("constitution/MANDATE.md"))
        f = c.calls[-1][3]
        _assert(
            f.get("workspace_id") == "ws-bound" and "user_id" not in f,
            "UserMemory.read keys on the bound workspace",
        )

        c = FakeClient()
        ws = AgentWorkspace(c, "member-1", "alpha")
        asyncio.run(ws.read("thesis.md"))
        f = c.calls[-1][3]
        _assert(
            f.get("workspace_id") == "ws-bound" and "user_id" not in f,
            "AgentWorkspace.read keys on the bound workspace",
        )
    finally:
        reset_request_workspace(tok)

    # no binding + owner-resolution unavailable → legacy user_id scoping
    with patch("services.supabase.resolve_owner_workspace_id", return_value=None):
        c = FakeClient()
        um = UserMemory(c, "u1")
        asyncio.run(um.read("constitution/MANDATE.md"))
        f = c.calls[-1][3]
        _assert(
            f.get("user_id") == "u1" and "workspace_id" not in f,
            "no binding + no resolution → legacy user_id scoping (N=1 identical)",
        )


def test_migration_198() -> None:
    print("\n[7] migration 198")
    mig = _API_ROOT.parent / "supabase" / "migrations" / "198_adr373_member_write_scope.sql"
    _assert(mig.exists(), "198_adr373_member_write_scope.sql exists")
    if mig.exists():
        src = mig.read_text()
        _assert(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_ws_files_wsid_path" in src,
            "UNIQUE (workspace_id, path) — the commons' live-row identity",
        )
        _assert(
            "Members insert workspace files" in src
            and "Members update workspace files" in src
            and "Members delete workspace files" in src
            and "Members insert workspace file versions" in src,
            "membership write RLS policies",
        )


def main() -> int:
    print("=" * 72)
    print("ADR-373 sweep spine — regression gate")
    print("=" * 72)

    test_effective_workspace_id()
    test_substrate_scope()
    test_resolver()
    test_auth_wiring()
    test_workspace_keyed_upsert()
    test_data_class_scoping()
    test_migration_198()

    print("\n" + "=" * 72)
    print(f"RESULT: {_passed} passed, {_failed} failed")
    print("=" * 72)
    return 1 if _failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
