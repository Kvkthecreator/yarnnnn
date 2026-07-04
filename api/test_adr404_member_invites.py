"""ADR-404 step 5 — member-invite regression gate.

Locks the provisioning contract that makes the `member` role live:

1. create_invite — email normalized, token minted, re-invite refreshes
   (prior pending revoked), member-only role.
2. accept_invite — email must match the JWT identity; expired invites
   flip to expired; accepting mints the grant via the ADR-386 lifecycle
   helper (ensure_principal_grant) and marks the invite accepted; the
   owner can't accept into their own workspace.
3. Route wiring — owner-only manage verbs, accept status-code map,
   X-Workspace-Id FE binding exists (source inspection).
4. Migration 199 — invites table + the apply-order guard + the legacy
   UNIQUE(user_id, path) retirement + replacement index.

Run: .venv/bin/python api/test_adr404_member_invites.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
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


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, client, table):
        self._c = client
        self._t = table
        self._op = "select"
        self._row = None
        self._filters = {}

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

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a):
        return self

    def execute(self):
        self._c.calls.append((self._t, self._op, self._row, dict(self._filters)))
        key = (self._t, self._op)
        rows = self._c.responses.get(key)
        if callable(rows):
            rows = rows(self._filters)
        if rows is None:
            rows = [dict(self._row)] if self._row is not None else []
        return _Result(rows)


class FakeClient:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.calls = []

    def table(self, name):
        return _Query(self, name)


def test_create_invite() -> None:
    print("\n[1] create_invite")
    import services.workspace_invites as wi

    c = FakeClient(responses={("workspace_invites", "update"): []})
    with patch.object(wi, "_svc", return_value=c):
        inv = wi.create_invite(workspace_id="ws1", email="  Kim@Team.COM ", invited_by="owner-1")
    _assert(inv["email"] == "kim@team.com", "email normalized (trim + lowercase)")
    _assert(len(inv["token"]) > 20, "opaque token minted")
    _assert(inv["role"] == "member" and inv["status"] == "pending", "member role, pending status")
    revokes = [x for x in c.calls if x[0] == "workspace_invites" and x[1] == "update"]
    _assert(
        revokes and revokes[0][2] == {"status": "revoked"},
        "re-invite path: prior pending invite for the email revoked first",
    )

    with patch.object(wi, "_svc", return_value=FakeClient()):
        try:
            wi.create_invite(workspace_id="ws1", email="not-an-email", invited_by="o")
            _assert(False, "invalid email rejected")
        except wi.InviteError as e:
            _assert(e.code == "invalid_email", "invalid email rejected")
        try:
            wi.create_invite(workspace_id="ws1", email="a@b.co", invited_by="o", role="owner")
            _assert(False, "non-member role rejected")
        except wi.InviteError as e:
            _assert(e.code == "invalid_role", "non-member role rejected")


def _pending_invite(**over):
    base = {
        "id": "inv1", "workspace_id": "ws1", "email": "kim@team.com",
        "role": "member", "status": "pending", "invited_by": "owner-1",
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
    }
    base.update(over)
    return base


def test_accept_invite() -> None:
    print("\n[2] accept_invite")
    import services.workspace_invites as wi

    def client_with(invite):
        return FakeClient(responses={
            ("workspace_invites", "select"): [invite],
            ("workspaces", "select"): [{"name": "Acme Ops", "owner_id": "owner-1"}],
            ("workspace_invites", "update"): [invite],
        })

    # email mismatch → rejected, no grant
    c = client_with(_pending_invite())
    with patch.object(wi, "_svc", return_value=c):
        try:
            wi.accept_invite(token="t", user_id="u9", user_email="other@x.com")
            _assert(False, "email mismatch rejected")
        except wi.InviteError as e:
            _assert(e.code == "email_mismatch", "email mismatch rejected")

    # expired → flips to expired
    c = client_with(_pending_invite(
        expires_at=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    ))
    with patch.object(wi, "_svc", return_value=c):
        try:
            wi.accept_invite(token="t", user_id="u9", user_email="kim@team.com")
            _assert(False, "expired invite rejected")
        except wi.InviteError as e:
            _assert(e.code == "expired", "expired invite rejected")
    _assert(
        any(x[1] == "update" and (x[2] or {}).get("status") == "expired" for x in c.calls),
        "expiry recorded on the invite row",
    )

    # owner accepting own workspace → rejected
    c = client_with(_pending_invite(email="own@er.com"))
    with patch.object(wi, "_svc", return_value=c):
        try:
            wi.accept_invite(token="t", user_id="owner-1", user_email="own@er.com")
            _assert(False, "owner self-accept rejected")
        except wi.InviteError as e:
            _assert(e.code == "already_owner", "owner self-accept rejected")

    # happy path → grant minted via ADR-386 helper + invite accepted
    c = client_with(_pending_invite())
    grant_calls = []

    def fake_grant(**kw):
        grant_calls.append(kw)
        return {"id": "g-new", **kw}

    with patch.object(wi, "_svc", return_value=c), \
         patch("services.principal_grants.ensure_principal_grant", side_effect=fake_grant):
        result = wi.accept_invite(token="t", user_id="u9", user_email="Kim@Team.com ")
    _assert(result["workspace_id"] == "ws1", "accept returns the commons workspace id")
    _assert(
        grant_calls and grant_calls[0]["principal_id"] == "u9"
        and grant_calls[0]["role"] == "member"
        and grant_calls[0]["workspace_id"] == "ws1",
        "grant minted via ensure_principal_grant (ADR-386 lifecycle)",
    )
    _assert(
        any(x[1] == "update" and (x[2] or {}).get("status") == "accepted" for x in c.calls),
        "invite marked accepted with the accepting principal",
    )


def test_route_wiring() -> None:
    print("\n[3] route + FE wiring (source inspection)")
    src = (_API_ROOT / "routes" / "workspace.py").read_text()
    _assert(
        "_require_owner_workspace" in src
        and "Only the workspace owner can manage invites" in src,
        "invite-manage verbs are owner-only",
    )
    _assert(
        '"/workspace/members/invite"' in src
        and '"/workspace/invites"' in src
        and '"/invites/{token}/accept"' in src,
        "invite routes registered",
    )
    _assert(
        '"email_mismatch": 403' in src and '"expired": 410' in src,
        "accept maps lifecycle errors to honest status codes",
    )

    fe = (_API_ROOT.parent / "web" / "lib" / "api" / "client.ts").read_text()
    _assert(
        "X-Workspace-Id" in fe and "ACTIVE_WORKSPACE_KEY" in fe,
        "FE binds the commons via X-Workspace-Id (sweep spine)",
    )
    accept_page = (
        _API_ROOT.parent / "web" / "app" / "(authenticated)" / "invite" / "[token]" / "page.tsx"
    )
    _assert(accept_page.exists(), "invite-accept page exists")


def test_migration_199() -> None:
    print("\n[4] migration 199")
    mig = _API_ROOT.parent / "supabase" / "migrations" / "199_adr404_member_invites.sql"
    _assert(mig.exists(), "199_adr404_member_invites.sql exists")
    if mig.exists():
        src = mig.read_text()
        _assert("CREATE TABLE IF NOT EXISTS workspace_invites" in src, "invites table")
        _assert("APPLY ORDER GUARD" in src, "apply-order guard documented")
        _assert(
            "DROP CONSTRAINT IF EXISTS workspace_files_user_id_path_key" in src
            and "idx_ws_files_user_path" in src,
            "legacy UNIQUE(user_id,path) retires with a replacement index",
        )


def main() -> int:
    print("=" * 72)
    print("ADR-404 step 5 — member invites gate")
    print("=" * 72)

    test_create_invite()
    test_accept_invite()
    test_route_wiring()
    test_migration_199()

    print("\n" + "=" * 72)
    print(f"RESULT: {_passed} passed, {_failed} failed")
    print("=" * 72)
    return 1 if _failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
