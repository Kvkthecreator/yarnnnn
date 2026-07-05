"""Regression gate for ADR-407 Phase 3 — member_state, the member-experience home.

Migration 202: member_state keyed (workspace_id, principal_id, key) — the
first store in the MEMBER-EXPERIENCE scope. Routes: GET/PUT /api/member-state/
{key}, scoped to (acting workspace, caller). Presentation state only — never
substrate, never authorization.

Run:
    cd api && python test_adr407_phase3_member_state.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_PASS: list[str] = []
_FAIL: list[tuple[str, str]] = []


def _ok(name):
    _PASS.append(name); print(f"  ✓ {name}")


def _bad(name, reason):
    _FAIL.append((name, reason)); print(f"  ✗ {name}\n      {reason}")


WS = "00000000-0000-0000-0000-00000000aaaa"
USER = "00000000-0000-0000-0000-000000000001"


class _FakeQuery:
    def __init__(self, sink, table, rows):
        self._sink, self._table, self._rows = sink, table, rows

    def select(self, *a, **k): return self
    def eq(self, col, val):
        self._sink.setdefault("filters", []).append((self._table, col, val)); return self
    def limit(self, *a): return self
    def upsert(self, row, **kw):
        self._sink.setdefault("upserts", []).append((self._table, row, kw)); return self
    def execute(self):
        class R: pass
        r = R(); r.data = self._rows
        return r


class _FakeClient:
    def __init__(self, rows=None):
        self.sink = {}; self._rows = rows or []
    def table(self, name):
        return _FakeQuery(self.sink, name, self._rows)


class _FakeAuth:
    def __init__(self, client):
        self.client = client; self.user_id = USER


def test_migration_shape() -> None:
    path = REPO_ROOT / "supabase/migrations/202_adr407_phase3_member_state.sql"
    if not path.exists():
        _bad("migration 202 exists", str(path)); return
    sql = path.read_text()
    checks = [
        ("PK is (workspace, principal, key)", "PRIMARY KEY (workspace_id, principal_id, key)" in sql),
        ("jsonb value", "value         jsonb NOT NULL" in sql),
        ("RLS service-role only", "member_state_service_only" in sql and "TO service_role" in sql),
        ("workspace FK cascades", "REFERENCES workspaces(id) ON DELETE CASCADE" in sql),
        ("documented as NOT substrate / NOT authorization", "never consulted for authorization" in sql.lower() or "NEVER consulted for authorization" in sql),
    ]
    for name, cond in checks:
        _ok(f"migration: {name}") if cond else _bad(f"migration: {name}", "pattern missing")


def test_routes() -> None:
    from routes import member_state as ms
    from services import workspace_context as wc

    loop = asyncio.get_event_loop()

    # GET scopes by (workspace, principal, key)
    client = _FakeClient(rows=[{"value": {"a": 1}, "updated_at": "2026-07-05T00:00:00Z"}])
    token = wc.set_request_workspace(WS)
    try:
        out = loop.run_until_complete(ms.get_member_state("shell", _FakeAuth(client)))
    finally:
        wc.reset_request_workspace(token)
    f = client.sink.get("filters", [])
    scoped = (
        ("member_state", "workspace_id", WS) in f
        and ("member_state", "principal_id", USER) in f
        and ("member_state", "key", "shell") in f
    )
    if scoped and out["value"] == {"a": 1}:
        _ok("routes: GET scoped (workspace, principal, key)")
    else:
        _bad("routes: GET scoped (workspace, principal, key)", f"filters={f} out={out}")

    # GET unset key → value None
    client = _FakeClient(rows=[])
    token = wc.set_request_workspace(WS)
    try:
        out = loop.run_until_complete(ms.get_member_state("attention", _FakeAuth(client)))
    finally:
        wc.reset_request_workspace(token)
    if out == {"key": "attention", "value": None, "updated_at": None}:
        _ok("routes: GET unset → null value")
    else:
        _bad("routes: GET unset → null value", str(out))

    # PUT upserts on the composite key
    client = _FakeClient()
    token = wc.set_request_workspace(WS)
    try:
        out = loop.run_until_complete(ms.put_member_state("shell", _FakeAuth(client), {"open": []}))
    finally:
        wc.reset_request_workspace(token)
    ups = client.sink.get("upserts", [])
    good = (
        ups
        and ups[0][1]["workspace_id"] == WS
        and ups[0][1]["principal_id"] == USER
        and ups[0][1]["key"] == "shell"
        and ups[0][2].get("on_conflict") == "workspace_id,principal_id,key"
    )
    if good and out == {"key": "shell", "saved": True}:
        _ok("routes: PUT upserts on the composite key")
    else:
        _bad("routes: PUT upserts on the composite key", f"upserts={ups}")

    # Invalid key rejected
    from fastapi import HTTPException
    try:
        loop.run_until_complete(ms.get_member_state("Bad Key!", _FakeAuth(_FakeClient())))
        _bad("routes: invalid key rejected", "no exception")
    except HTTPException as e:
        _ok("routes: invalid key rejected") if e.status_code == 400 else _bad("routes: invalid key rejected", str(e.status_code))

    # No workspace → 403 fail-closed
    orig = wc.effective_workspace_id
    wc.effective_workspace_id = lambda *a, **k: None  # type: ignore
    try:
        loop.run_until_complete(ms.get_member_state("shell", _FakeAuth(_FakeClient())))
        _bad("routes: no workspace → 403", "no exception")
    except HTTPException as e:
        _ok("routes: no workspace → 403") if e.status_code == 403 else _bad("routes: no workspace → 403", str(e.status_code))
    finally:
        wc.effective_workspace_id = orig  # type: ignore


def test_registered() -> None:
    text = (ROOT / "main.py").read_text()
    if "member_state" in text and 'include_router(member_state.router, prefix="/api"' in text:
        _ok("main: member_state router registered")
    else:
        _bad("main: member_state router registered", "registration missing")


def main() -> int:
    print("ADR-407 Phase 3 — member_state regression")
    print("=" * 60)
    test_migration_shape()
    test_routes()
    test_registered()
    print("=" * 60)
    print(f"{len(_PASS)} passed, {len(_FAIL)} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
