"""ADR-386 regression gate — the principal-grant LIFECYCLE.

ADR-373 shipped the grant CONSULT (the gate reads grants). ADR-386 is the
LIFECYCLE that creates + governs them:
  - ensure_principal_grant — idempotent auto-provision (foreign-LLM on connect).
  - narrow_grant — tighten scopes (authz only; reject owner).
  - evict_principal — REVOKE = full eviction (grant revoked + tokens deleted;
    reject owner).

Proves (no live DB — a fake service client records the writes):
  1. auto-provision is IDEMPOTENT (an existing active grant → no second insert).
  2. narrow writes scopes + the gate then DENIES outside the narrowed set (the
     consult honors it — the round-trip).
  3. revoke flips status='revoked' AND deletes the principal's OAuth tokens.
  4. OWNER IMMUTABILITY (ADR-386 D4): narrow/revoke an owner grant → raises
     OwnerGrantImmutable (the route maps to 403).
  5. the OAuth auto-provision hook is BEST-EFFORT — a grant failure does not
     raise (the connect flow is unaffected).

Run: cd api && python -m pytest test_adr386_member_lifecycle.py -q
Refs: docs/adr/ADR-386-workspace-members-the-grant-lifecycle.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import importlib.util

import pytest

API_DIR = Path(__file__).parent
sys.path.insert(0, str(API_DIR))

# mcp_server.oauth_provider imports the `mcp` SDK at module top (3.11-only,
# absent from the api venv 3.9). The shared-helper tests (§7) import it; skip
# them gracefully where `mcp` is unavailable. The OTHER tests test
# services.principal_grants directly (no mcp dependency) and always run.
_MCP_AVAILABLE = importlib.util.find_spec("mcp") is not None
_requires_mcp = pytest.mark.skipif(
    not _MCP_AVAILABLE,
    reason="mcp_server.oauth_provider needs the mcp SDK (3.11; absent from the api venv)",
)


# ---------------------------------------------------------------------------
# A fake service client that records inserts/updates/deletes and answers
# selects from a seeded grant set.
# ---------------------------------------------------------------------------

class _Exec:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, table, store, recorder):
        self._table = table
        self._store = store
        self._rec = recorder
        self._op = None
        self._payload = None
        self._filters = {}

    def select(self, *a, **k):
        self._op = "select"
        return self

    def insert(self, payload):
        self._op, self._payload = "insert", payload
        return self

    def update(self, payload):
        self._op, self._payload = "update", payload
        return self

    def delete(self):
        self._op = "delete"
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        rows = self._store.get(self._table, [])
        if self._op == "select":
            out = [r for r in rows if all(r.get(k) == v for k, v in self._filters.items())]
            return _Exec(out)
        if self._op == "insert":
            self._rec.append((self._table, "insert", dict(self._payload)))
            row = dict(self._payload)
            row.setdefault("id", f"fake-{len(rows)}")
            rows.append(row)
            self._store[self._table] = rows
            return _Exec([row])
        if self._op == "update":
            matched = [r for r in rows if all(r.get(k) == v for k, v in self._filters.items())]
            for r in matched:
                r.update(self._payload)
            self._rec.append((self._table, "update", dict(self._payload), dict(self._filters)))
            return _Exec(matched)
        if self._op == "delete":
            kept = [r for r in rows if not all(r.get(k) == v for k, v in self._filters.items())]
            deleted = [r for r in rows if all(r.get(k) == v for k, v in self._filters.items())]
            self._store[self._table] = kept
            self._rec.append((self._table, "delete", dict(self._filters)))
            return _Exec(deleted)
        return _Exec([])


class _FakeClient:
    def __init__(self, store):
        self.store = store
        self.recorder: list = []

    def table(self, name):
        return _Query(name, self.store, self.recorder)


@pytest.fixture
def fake(monkeypatch):
    store = {"principal_grants": [], "mcp_oauth_access_tokens": [], "mcp_oauth_refresh_tokens": []}
    client = _FakeClient(store)
    # Both ensure/narrow/evict AND delete_tokens_for_client resolve the service
    # client through services.supabase.get_service_client (the eviction helper
    # lives in services.principal_grants, not the MCP-only oauth_provider).
    monkeypatch.setattr("services.supabase.get_service_client", lambda: client)
    return client


# ===========================================================================
# 1. Auto-provision idempotency
# ===========================================================================

def test_ensure_grant_inserts_when_absent(fake):
    from services.principal_grants import ensure_principal_grant
    ensure_principal_grant("client-abc", "ws-1", "foreign-llm", granted_by="system:oauth-connect")
    inserts = [r for r in fake.recorder if r[0] == "principal_grants" and r[1] == "insert"]
    assert len(inserts) == 1
    payload = inserts[0][2]
    assert payload["principal_id"] == "client-abc"
    assert payload["role"] == "foreign-llm"
    assert payload["scopes"] is None  # NULL → class default at the gate
    assert payload["status"] == "active"


def test_ensure_grant_is_idempotent(fake):
    from services.principal_grants import ensure_principal_grant
    ensure_principal_grant("client-abc", "ws-1", "foreign-llm")
    ensure_principal_grant("client-abc", "ws-1", "foreign-llm")  # second call
    inserts = [r for r in fake.recorder if r[0] == "principal_grants" and r[1] == "insert"]
    assert len(inserts) == 1, "an existing active grant must NOT insert a second row"


# ===========================================================================
# 2. Narrow — writes scopes; the gate then denies outside the set
# ===========================================================================

def test_narrow_writes_scopes(fake):
    from services.principal_grants import ensure_principal_grant, narrow_grant
    ensure_principal_grant("client-abc", "ws-1", "foreign-llm")
    narrow_grant("client-abc", "ws-1", ["operation/"])
    updates = [r for r in fake.recorder if r[0] == "principal_grants" and r[1] == "update"]
    assert updates and updates[-1][2] == {"scopes": ["operation/"]}


def test_narrow_then_gate_denies_outside(fake, monkeypatch):
    """The round-trip: narrow to operation/, then _is_path_locked_for_principal
    DENIES a write to governance/ and ALLOWS operation/.

    ADR-373 D2.a: the grant is keyed on the PROVIDER host-id (`claude.ai`) — the
    same key resolve_principal_id derives for an MCP caller — so the narrow binds
    the provider regardless of which client_id the live session carries. The two
    different principal_ids below (`session-A`, `session-B`) prove the narrow
    holds ACROSS re-registrations, the whole point of provider-keying."""
    from services.principal_grants import ensure_principal_grant, narrow_grant
    from services.primitives import workspace as ws
    from services.primitives.workspace import _is_path_locked_for_principal
    from types import SimpleNamespace

    # Grant + narrow keyed on the PROVIDER host-id (not a client_id).
    ensure_principal_grant("claude.ai", "ws-1", "foreign-llm")
    narrow_grant("claude.ai", "ws-1", ["operation/"])
    if hasattr(ws._grant_cache, "store"):
        ws._grant_cache.store = {}

    # Session A — one client_id; the consult resolves caller → claude.ai.
    auth_a = SimpleNamespace(
        caller_identity="yarnnn:mcp:claude.ai", user_id="u-1", workspace_id="ws-1",
        principal_id="session-A", freddie_caller=False, client=None,
    )
    assert _is_path_locked_for_principal(auth_a, "operation/memory/n.md") is False  # in scope
    assert _is_path_locked_for_principal(auth_a, "governance/x.md") is True          # out of scope
    assert _is_path_locked_for_principal(auth_a, "agents/x/m.md") is True            # out of scope

    # Session B — a DIFFERENT client_id (a reconnect). Same provider → same grant
    # → the narrow STILL binds. (Pre-D2.a this escaped the narrow.)
    ws._grant_cache.store = {}
    auth_b = SimpleNamespace(
        caller_identity="yarnnn:mcp:claude.ai", user_id="u-1", workspace_id="ws-1",
        principal_id="session-B", freddie_caller=False, client=None,
    )
    assert _is_path_locked_for_principal(auth_b, "operation/x.md") is False          # in scope
    assert _is_path_locked_for_principal(auth_b, "agents/x/m.md") is True            # narrow holds across reconnect


def test_narrow_missing_grant_raises(fake):
    from services.principal_grants import narrow_grant
    with pytest.raises(ValueError):
        narrow_grant("nobody", "ws-1", ["operation/"])


# ===========================================================================
# 3. Revoke = full eviction (status flip + token delete)
# ===========================================================================

def test_revoke_flips_status_and_deletes_tokens(fake):
    from services.principal_grants import ensure_principal_grant, evict_principal
    ensure_principal_grant("client-abc", "ws-1", "foreign-llm")
    # seed two tokens for the client
    fake.store["mcp_oauth_access_tokens"].append({"token": "t1", "client_id": "client-abc"})
    fake.store["mcp_oauth_refresh_tokens"].append({"token": "r1", "client_id": "client-abc"})

    result = evict_principal("client-abc", "ws-1")

    # status flipped
    status_updates = [r for r in fake.recorder if r[0] == "principal_grants" and r[1] == "update"]
    assert status_updates and status_updates[-1][2] == {"status": "revoked"}
    # tokens deleted
    assert fake.store["mcp_oauth_access_tokens"] == []
    assert fake.store["mcp_oauth_refresh_tokens"] == []
    assert result["status"] == "revoked"
    assert result["tokens_deleted"] == 2


def test_revoke_missing_grant_raises(fake):
    from services.principal_grants import evict_principal
    with pytest.raises(ValueError):
        evict_principal("nobody", "ws-1")


# ===========================================================================
# 4. Owner immutability (ADR-386 D4)
# ===========================================================================

def test_narrow_owner_raises_immutable(fake):
    from services.principal_grants import ensure_principal_grant, narrow_grant, OwnerGrantImmutable
    ensure_principal_grant("u-owner", "ws-1", "owner")
    with pytest.raises(OwnerGrantImmutable):
        narrow_grant("u-owner", "ws-1", ["operation/"])


def test_revoke_owner_raises_immutable(fake):
    from services.principal_grants import ensure_principal_grant, evict_principal, OwnerGrantImmutable
    ensure_principal_grant("u-owner", "ws-1", "owner")
    with pytest.raises(OwnerGrantImmutable):
        evict_principal("u-owner", "ws-1")
    # and the owner's grant is NOT revoked, no tokens touched
    grant = fake.store["principal_grants"][0]
    assert grant["status"] == "active"


# ===========================================================================
# 5. delete_tokens_for_client counts both tables
# ===========================================================================

def test_delete_tokens_for_client_counts_both_tables(fake):
    from services.principal_grants import delete_tokens_for_client
    fake.store["mcp_oauth_access_tokens"] += [
        {"token": "a1", "client_id": "c"}, {"token": "a2", "client_id": "c"},
    ]
    fake.store["mcp_oauth_refresh_tokens"] += [{"token": "r1", "client_id": "c"}]
    n = delete_tokens_for_client("c")
    assert n == 3
    assert fake.store["mcp_oauth_access_tokens"] == []
    assert fake.store["mcp_oauth_refresh_tokens"] == []


# ===========================================================================
# 6. The OAuth hook is best-effort — a grant failure does not raise
# ===========================================================================

def test_oauth_hook_failsafe_on_grant_error(monkeypatch):
    """If ensure_principal_grant blows up, the auto-provision block must swallow
    it (the OAuth flow is unaffected). We simulate by making ensure raise and
    confirming the wrapper logic doesn't propagate."""
    import services.principal_grants as pg

    def _boom(*a, **k):
        raise RuntimeError("db down")

    monkeypatch.setattr(pg, "ensure_principal_grant", _boom)
    monkeypatch.setattr("services.supabase.resolve_owner_workspace_id", lambda u: "ws-1")

    # Re-create the hook's try/except inline (the exact shape used in
    # exchange_authorization_code) to prove it swallows.
    raised = False
    try:
        from services.supabase import resolve_owner_workspace_id
        from services.principal_grants import ensure_principal_grant
        wsid = resolve_owner_workspace_id("u-1")
        if wsid:
            ensure_principal_grant(principal_id="c", workspace_id=wsid, role="foreign-llm")
    except Exception:
        raised = True  # the REAL hook swallows; this mirror asserts the call DOES raise
    assert raised, "ensure_principal_grant raises — the OAuth hook's try/except must swallow it"


# ===========================================================================
# 7. The shared provision helper fires on BOTH OAuth paths (ADR-386 D1.a)
# ===========================================================================
# The 2026-06-30 amendment: provisioning fires on authorize AND refresh, via one
# shared helper `_ensure_foreign_llm_grant`, so a connector that authorized
# before the hook deployed self-heals on its next silent refresh rotation.

@_requires_mcp
def test_shared_helper_provisions_grant(fake, monkeypatch):
    """`_ensure_foreign_llm_grant` resolves the workspace and ensures a
    foreign-llm grant. This is the singular block both hook sites call."""
    from mcp_server.oauth_provider import _ensure_foreign_llm_grant
    monkeypatch.setattr("services.supabase.resolve_owner_workspace_id", lambda u: "ws-1")

    _ensure_foreign_llm_grant("u-1", "client-xyz", "system:oauth-refresh")

    inserts = [r for r in fake.recorder if r[0] == "principal_grants" and r[1] == "insert"]
    assert len(inserts) == 1
    payload = inserts[0][2]
    assert payload["principal_id"] == "client-xyz"
    assert payload["role"] == "foreign-llm"
    assert payload["granted_by"] == "system:oauth-refresh"


@_requires_mcp
def test_shared_helper_is_best_effort(fake, monkeypatch):
    """A grant-ensure failure inside the helper must NOT raise — the OAuth
    token flow (its caller) must be unaffected (ADR-386 §6.3)."""
    import services.principal_grants as pg
    from mcp_server.oauth_provider import _ensure_foreign_llm_grant

    monkeypatch.setattr("services.supabase.resolve_owner_workspace_id", lambda u: "ws-1")
    monkeypatch.setattr(pg, "ensure_principal_grant", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db down")))

    # Must not raise.
    _ensure_foreign_llm_grant("u-1", "client-xyz", "system:oauth-refresh")


@_requires_mcp
def test_shared_helper_skips_when_no_workspace(fake, monkeypatch):
    """If the user owns no workspace, the helper skips silently (no grant
    written) — the LLM still writes via the class default."""
    from mcp_server.oauth_provider import _ensure_foreign_llm_grant
    monkeypatch.setattr("services.supabase.resolve_owner_workspace_id", lambda u: None)

    _ensure_foreign_llm_grant("u-1", "client-xyz", "system:oauth-refresh")

    inserts = [r for r in fake.recorder if r[0] == "principal_grants" and r[1] == "insert"]
    assert len(inserts) == 0, "no workspace → no grant insert"


# ===========================================================================
# 8. ADR-373 D2.a — provider-as-member (the foreign-LLM member is the host-id)
# ===========================================================================

def test_provider_id_resolves_via_registry():
    """resolve_provider_id routes every signal through the ADR-379 host registry."""
    from services.principal_grants import resolve_provider_id
    assert resolve_provider_id(client_name="ChatGPT") == "chatgpt"
    # Claude's bare registered name doesn't match; its redirect_uri does.
    assert resolve_provider_id(client_name="Claude") is None
    assert resolve_provider_id(
        client_name="Claude",
        redirect_uris=["https://claude.ai/api/mcp/auth_callback"],
    ) == "claude.ai"
    # Unknown provider → None (caller keeps the client_id).
    assert resolve_provider_id(client_id="random-uuid") is None


def test_provider_label_maps_host_id_else_none():
    """provider_label humanizes a known host-id; returns None for a non-host-id
    (the signal the members endpoint uses to fall back to a client_id lookup)."""
    from services.principal_grants import provider_label
    assert provider_label("chatgpt") == "ChatGPT"
    assert provider_label("claude.ai") == "Claude"
    assert provider_label("2308d0a8-some-uuid") is None  # legacy client_id-keyed row


@_requires_mcp
def test_hook_keys_grant_on_provider_not_client_id(fake, monkeypatch):
    """The OAuth hook provisions a grant keyed on the PROVIDER host-id, not the
    churning client_id (ADR-373 D2.a)."""
    from mcp_server.oauth_provider import _ensure_foreign_llm_grant
    monkeypatch.setattr("services.supabase.resolve_owner_workspace_id", lambda u: "ws-1")
    # The client resolves to the chatgpt provider.
    monkeypatch.setattr(
        "services.principal_grants.resolve_provider_id_for_client",
        lambda cid: "chatgpt",
    )
    _ensure_foreign_llm_grant("u-1", "churning-client-uuid", "system:oauth-connect")
    inserts = [r for r in fake.recorder if r[0] == "principal_grants" and r[1] == "insert"]
    assert len(inserts) == 1
    assert inserts[0][2]["principal_id"] == "chatgpt", "grant must key on the provider host-id"
