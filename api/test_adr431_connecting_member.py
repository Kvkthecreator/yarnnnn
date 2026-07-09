"""ADR-431 regression gate — the connecting member owns the MCP grant.

The relational unit of a foreign-LLM grant moves from (provider, workspace) to
(provider, connecting-member, workspace). The must-pass properties:

  1. MULTI-MEMBER COEXISTENCE — two members connecting the same provider produce
     TWO grants, not one (the second no longer no-ops onto the first).
  2. MEMBER-FIRST CONSULT — the gate resolves a member's OWN grant; falls back
     to a provider-wide (connected_by NULL) grant when the member has none.
  3. SCOPED REVOKE — revoking one member's connection leaves a co-member's
     same-provider connection (and its tokens) intact.
  4. D5 CASCADE — evicting a human member revokes the AI connections THEY
     authorized.
  5. N=1 BYTE-IDENTICAL — the owner/human path (connected_by None) behaves
     exactly as pre-431.

Run: cd api && venv/bin/python -m pytest test_adr431_connecting_member.py -q

Refs: docs/adr/ADR-431-the-connecting-member-owns-the-mcp-grant.md,
      supabase/migrations/209_adr431_connected_by.sql.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent))


# ---------------------------------------------------------------------------
# A fake supabase client that honors eq / is_ / in_ AND the widened active-
# uniqueness (principal_id, workspace_id, COALESCE(connected_by, principal_id))
# so an insert that collides is rejected the way Postgres would.
# ---------------------------------------------------------------------------

class _Exec:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, table, store, rec):
        self._t, self._store, self._rec = table, store, rec
        self._op = None
        self._payload = None
        self._eq = {}
        self._null = set()
        self._in = {}

    def select(self, *a, **k):
        self._op = "select"; return self

    def insert(self, payload):
        self._op, self._payload = "insert", payload; return self

    def update(self, payload):
        self._op, self._payload = "update", payload; return self

    def delete(self):
        self._op = "delete"; return self

    def eq(self, c, v):
        self._eq[c] = v; return self

    def is_(self, c, _n):
        self._null.add(c); return self

    def in_(self, c, vals):
        self._in[c] = list(vals); return self

    def limit(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def _match(self, r):
        if not all(r.get(k) == v for k, v in self._eq.items()):
            return False
        if any(r.get(c) is not None for c in self._null):
            return False
        if any(r.get(c) not in vals for c, vals in self._in.items()):
            return False
        return True

    @staticmethod
    def _active_key(r):
        cb = r.get("connected_by")
        coalesced = cb if cb is not None else r.get("principal_id")
        return (r.get("principal_id"), r.get("workspace_id"), coalesced)

    def execute(self):
        rows = self._store.setdefault(self._t, [])
        if self._op == "select":
            return _Exec([r for r in rows if self._match(r)])
        if self._op == "insert":
            row = dict(self._payload)
            row.setdefault("id", f"g{len(rows)}")
            # Enforce the widened partial-unique on active rows.
            if row.get("status", "active") == "active":
                for r in rows:
                    if r.get("status") == "active" and self._active_key(r) == self._active_key(row):
                        raise RuntimeError("duplicate active grant (uq_principal_grant_active)")
            rows.append(row)
            self._rec.append((self._t, "insert", row))
            return _Exec([row])
        if self._op == "update":
            matched = [r for r in rows if self._match(r)]
            for r in matched:
                r.update(self._payload)
            return _Exec(matched)
        if self._op == "delete":
            deleted = [r for r in rows if self._match(r)]
            self._store[self._t] = [r for r in rows if not self._match(r)]
            self._rec.append((self._t, "delete", dict(self._eq)))
            return _Exec(deleted)
        return _Exec([])


class _Client:
    def __init__(self, store):
        self.store, self.recorder = store, []

    def table(self, name):
        return _Query(name, self.store, self.recorder)


@pytest.fixture
def store(monkeypatch):
    data: dict = {"principal_grants": [], "mcp_oauth_access_tokens": [], "mcp_oauth_refresh_tokens": []}
    client = _Client(data)
    import services.principal_grants as pg
    monkeypatch.setattr(pg, "_svc", lambda: client)
    # client_ids_for_provider returns [] in these tests (no oauth_clients rows) →
    # eviction falls back to deleting by principal_id, which is fine for the
    # token-scoping assertions that seed tokens keyed on the provider id.
    return data


# ---------------------------------------------------------------------------
# 1. Multi-member coexistence
# ---------------------------------------------------------------------------

def test_two_members_same_provider_coexist(store):
    from services.principal_grants import ensure_principal_grant
    ensure_principal_grant("chatgpt", "ws-1", "foreign-llm", connected_by="owner-1")
    ensure_principal_grant("chatgpt", "ws-1", "foreign-llm", connected_by="member-2")
    active = [r for r in store["principal_grants"] if r["status"] == "active"]
    assert len(active) == 2, "two members' ChatGPT connections must be two grants"
    assert {r["connected_by"] for r in active} == {"owner-1", "member-2"}


def test_same_member_reconnect_is_idempotent(store):
    from services.principal_grants import ensure_principal_grant
    ensure_principal_grant("chatgpt", "ws-1", "foreign-llm", connected_by="owner-1")
    ensure_principal_grant("chatgpt", "ws-1", "foreign-llm", connected_by="owner-1")
    active = [r for r in store["principal_grants"] if r["status"] == "active"]
    assert len(active) == 1, "the same member reconnecting must be a no-op"


def test_null_connected_grant_is_singleton(store):
    """A provider-wide (connected_by NULL) grant stays a singleton — the human/
    legacy path is unchanged."""
    from services.principal_grants import ensure_principal_grant
    ensure_principal_grant("claude.ai", "ws-1", "foreign-llm")
    ensure_principal_grant("claude.ai", "ws-1", "foreign-llm")
    active = [r for r in store["principal_grants"] if r["status"] == "active"]
    assert len(active) == 1


# ---------------------------------------------------------------------------
# 2. Member-first consult (gate)
# ---------------------------------------------------------------------------

def _mcp_auth(user_id, provider="claude.ai"):
    return SimpleNamespace(
        caller_identity=f"yarnnn:mcp:{provider}", user_id=user_id,
        workspace_id="ws-1", principal_id=None, freddie_caller=False, client=None,
    )


def test_consult_prefers_members_own_grant(store, monkeypatch):
    from services.primitives import workspace as ws
    from services.primitives.workspace import _is_path_locked_for_principal
    from services.principal_grants import ensure_principal_grant, narrow_grant

    # Two members' claude.ai grants; member-2 is narrowed to operation/ only.
    ensure_principal_grant("claude.ai", "ws-1", "foreign-llm", connected_by="owner-1")
    ensure_principal_grant("claude.ai", "ws-1", "foreign-llm", connected_by="member-2")
    narrow_grant("claude.ai", "ws-1", ["operation/"], connected_by="member-2")

    # Point the gate's grant lookup at our fake store.
    import services.supabase as sb
    client = _Client(store)
    monkeypatch.setattr(sb, "get_service_client", lambda: client)
    monkeypatch.setattr(sb, "resolve_owner_workspace_id", lambda uid: "ws-1")
    if hasattr(ws._grant_cache, "store"):
        ws._grant_cache.store = {}

    # member-2 (narrowed) — governance denied, operation allowed.
    auth2 = _mcp_auth("member-2")
    assert _is_path_locked_for_principal(auth2, "operation/x.md") is False
    assert _is_path_locked_for_principal(auth2, "governance/x.md") is True

    # owner-1 (NOT narrowed — NULL scopes = class default) — the foreign-llm
    # class default is broader than member-2's narrow; governance still locked
    # by class default, but agents/ is writable at class default. The point:
    # owner-1 is NOT subject to member-2's narrow.
    ws._grant_cache.store = {}
    auth1 = _mcp_auth("owner-1")
    # foreign-llm class default locks governance/constitution/persona/system;
    # operation + agents + contract are writable. So owner-1 CAN write agents/,
    # proving member-2's operation-only narrow did NOT bind owner-1.
    assert _is_path_locked_for_principal(auth1, "agents/x/m.md") is False


# ---------------------------------------------------------------------------
# 3. Scoped revoke
# ---------------------------------------------------------------------------

def test_revoke_one_member_leaves_comember(store):
    from services.principal_grants import ensure_principal_grant, evict_principal
    ensure_principal_grant("chatgpt", "ws-1", "foreign-llm", connected_by="owner-1")
    ensure_principal_grant("chatgpt", "ws-1", "foreign-llm", connected_by="member-2")

    evict_principal("chatgpt", "ws-1", connected_by="member-2")

    active = [r for r in store["principal_grants"] if r["status"] == "active"]
    assert len(active) == 1
    assert active[0]["connected_by"] == "owner-1", "the owner's ChatGPT survives"
    revoked = [r for r in store["principal_grants"] if r["status"] == "revoked"]
    assert revoked and revoked[0]["connected_by"] == "member-2"


def test_scoped_revoke_deletes_only_that_members_tokens(store):
    from services.principal_grants import ensure_principal_grant, evict_principal
    ensure_principal_grant("chatgpt", "ws-1", "foreign-llm", connected_by="owner-1")
    ensure_principal_grant("chatgpt", "ws-1", "foreign-llm", connected_by="member-2")
    # Tokens keyed on the provider client_id (fallback path) + user_id.
    store["mcp_oauth_access_tokens"] = [
        {"client_id": "chatgpt", "user_id": "owner-1"},
        {"client_id": "chatgpt", "user_id": "member-2"},
    ]
    evict_principal("chatgpt", "ws-1", connected_by="member-2")
    remaining = store["mcp_oauth_access_tokens"]
    assert len(remaining) == 1 and remaining[0]["user_id"] == "owner-1", \
        "only member-2's tokens are swept; the owner's ChatGPT stays authenticated"


# ---------------------------------------------------------------------------
# 4. D5 cascade
# ---------------------------------------------------------------------------

def test_member_eviction_cascades_to_their_ai(store):
    from services.principal_grants import ensure_principal_grant, cascade_member_ai_connections
    # member-2 connected both ChatGPT and Claude; owner connected ChatGPT.
    ensure_principal_grant("chatgpt", "ws-1", "foreign-llm", connected_by="owner-1")
    ensure_principal_grant("chatgpt", "ws-1", "foreign-llm", connected_by="member-2")
    ensure_principal_grant("claude.ai", "ws-1", "foreign-llm", connected_by="member-2")

    results = cascade_member_ai_connections("member-2", "ws-1")
    assert len(results) == 2, "both of member-2's AI connections are revoked"

    active = [r for r in store["principal_grants"] if r["status"] == "active"]
    # only the owner's ChatGPT remains active
    assert len(active) == 1 and active[0]["connected_by"] == "owner-1"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
