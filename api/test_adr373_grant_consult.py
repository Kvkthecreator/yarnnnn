"""ADR-373 D2/D3 regression gate — the per-principal GRANT-CONSULT at the gate.

The grant-consult brings AUTHORIZATION to principal granularity (the granularity
attribution already has, ADR-288). The gate resolves the caller's
`principal_grants` row → uses its `scopes` (allow-list) when present, else falls
back to the caller-class default (`_is_path_locked` / CALLER_WRITE_POLICY).

THE SAFETY INVARIANT (the must-pass): a principal with no grant or NULL scopes
inherits its class default = TODAY'S EXACT BEHAVIOR. Every live workspace is N=1
owner with scopes NULL, so the owner must behave BYTE-IDENTICALLY after the
consult. `test_fallback_identity_*` is what earns the right to ship.

Also gates the ADJACENT MCP fix (audit §6): the live MCP caller_identity is
ROOM-QUALIFIED (`yarnnn:mcp:<client>`), which the pre-2026-06-29 exact
`== "yarnnn:mcp"` matcher MISSED — leaving the MCP topology lock dormant. The
matcher is fixed to `startswith`; `test_mcp_*` proves the lock now engages.

Run: cd api && python -m pytest test_adr373_grant_consult.py -q

Refs: docs/adr/ADR-373-multi-principal-workspace-and-the-re-key.md (D2/D3/D6),
      docs/analysis/adr373-grant-consult-AUDIT-FINDINGS-2026-06-29.md.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

API_DIR = Path(__file__).parent
sys.path.insert(0, str(API_DIR))

from services.primitives import workspace as ws  # noqa: E402
from services.primitives.workspace import (  # noqa: E402
    _caller_class,
    _is_path_locked,
    _is_path_locked_for_principal,
    path_under_scopes,
)
from services.supabase import resolve_principal_id  # noqa: E402
from services.workspace_paths import (  # noqa: E402
    CALLER_WRITE_POLICY,
    GOVERNANCE_ROOT,
    CONSTITUTION_ROOT,
    PERSONA_ROOT,
    OPERATION_ROOT,
    SYSTEM_ROOT,
    CONTRACT_ROOT,
)


# ---------------------------------------------------------------------------
# Fakes — a configurable service client returning a chosen grant row.
# ---------------------------------------------------------------------------

class _FakeExec:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        return _FakeExec(self._rows)


class _FakeServiceClient:
    """Returns the configured grant rows for any principal_grants query."""

    def __init__(self, grant_rows):
        self._rows = grant_rows

    def table(self, name):
        assert name == "principal_grants", f"unexpected table {name}"
        return _FakeQuery(self._rows)


@pytest.fixture(autouse=True)
def _clear_grant_cache():
    """Each test starts with a clean per-request grant memo."""
    if hasattr(ws._grant_cache, "store"):
        ws._grant_cache.store = {}
    yield
    if hasattr(ws._grant_cache, "store"):
        ws._grant_cache.store = {}


def _auth(caller_identity="operator", user_id="u-owner", workspace_id="ws-1",
          principal_id=None, freddie_caller=False):
    return SimpleNamespace(
        caller_identity=caller_identity,
        user_id=user_id,
        workspace_id=workspace_id,
        principal_id=principal_id,
        freddie_caller=freddie_caller,
        client=None,
    )


def _patch_grant(monkeypatch, grant_rows):
    """Make _lookup_grant_scopes see the given principal_grants rows."""
    fake = _FakeServiceClient(grant_rows)
    monkeypatch.setattr("services.supabase.get_service_client", lambda: fake)


# The full root × caller-class cross-product, to prove byte-identity exhaustively.
_ROOTS = [GOVERNANCE_ROOT, CONSTITUTION_ROOT, PERSONA_ROOT, OPERATION_ROOT,
          SYSTEM_ROOT, CONTRACT_ROOT]
_SAMPLE_PATHS = [r + "file.md" for r in _ROOTS] + [
    "agents/x/memory/notes.md",   # under the agents/ home, no semantic root
    "operation/specs/acme.md",    # nested under operation
    "/workspace/governance/_autonomy.yaml",  # leading-slash + workspace prefix
]
_CLASSES = ["operator", "freddie", "mcp", "agent", "system"]


# ===========================================================================
# 1. THE SAFETY INVARIANT — fallback identity (owner / NULL scopes = TODAY)
# ===========================================================================

def test_fallback_identity_no_grant_row_is_byte_identical(monkeypatch):
    """No grant row at all → _is_path_locked_for_principal == _is_path_locked
    for every caller-class × path. This is the pre-consult world, unchanged."""
    _patch_grant(monkeypatch, [])  # zero rows
    for klass in _CLASSES:
        ci = {
            "operator": "operator",
            "freddie": "freddie:ai:test",
            "mcp": "yarnnn:mcp:claude.ai",
            "agent": "agent:research",
            "system": "system:reconciler",
        }[klass]
        auth = _auth(caller_identity=ci, freddie_caller=(klass == "freddie"))
        assert _caller_class(auth) == klass, f"class resolve drift for {klass}"
        for path in _SAMPLE_PATHS:
            expected = _is_path_locked(klass, path)
            actual = _is_path_locked_for_principal(auth, path)
            assert actual == expected, (
                f"BYTE-IDENTITY VIOLATION (no-grant): class={klass} path={path} "
                f"expected={expected} actual={actual}"
            )


def test_fallback_identity_null_scopes_is_byte_identical(monkeypatch):
    """An owner grant WITH NULL scopes (the live backfill shape) → identical to
    _is_path_locked. This is EXACTLY the 11 live rows."""
    _patch_grant(monkeypatch, [{"scopes": None}])
    auth = _auth(caller_identity="operator", principal_id="u-owner")
    for path in _SAMPLE_PATHS:
        expected = _is_path_locked("operator", path)
        actual = _is_path_locked_for_principal(auth, path)
        assert actual == expected, (
            f"BYTE-IDENTITY VIOLATION (null-scopes): path={path} "
            f"expected={expected} actual={actual}"
        )


def test_empty_scopes_list_is_deny_all(monkeypatch):
    """POLARITY AMENDMENT (the powerbox, 2026-07-10). An empty scopes list ([])
    is an EXPLICIT allow-list of nothing → DENY-ALL, NOT the class default.

    This REVERSES the pre-powerbox assertion (which pinned the `if raw:` bug:
    `[]` collapsed into the NULL branch and resolved to class-default =
    write-capable, so "this principal may touch nothing" was unrepresentable).
    The fix (`if raw is not None:`) splits [] from NULL: [] is a deliberate,
    representable locked-down grant. NULL still → class default (the test above).
    See test_powerbox_read_gate.py for the full polarity + read-gate coverage."""
    _patch_grant(monkeypatch, [{"scopes": []}])
    auth = _auth(caller_identity="operator", principal_id="u-owner")
    # Every path is locked — an empty allow-list grants nothing.
    for path in _SAMPLE_PATHS:
        assert _is_path_locked_for_principal(auth, path) is True, (
            f"[] must deny {path} (deny-all), not fall to class default"
        )


def test_fallback_when_principal_unresolvable(monkeypatch):
    """No principal_id AND no workspace_id → cannot key the grant → class
    default. Never blocks on resolution failure."""
    _patch_grant(monkeypatch, [{"scopes": ["operation/"]}])  # would narrow IF keyed
    auth = _auth(caller_identity="operator", user_id=None, workspace_id=None, principal_id=None)
    # Falls back to class default (operator: only system/ locked).
    assert _is_path_locked_for_principal(auth, "governance/x.md") is False
    assert _is_path_locked_for_principal(auth, "system/x.md") is True


def test_grant_lookup_failure_fails_safe_to_class_default(monkeypatch):
    """A DB error in the grant lookup → None → class default, never a block/widen."""
    class _Boom:
        def table(self, *a, **k):
            raise RuntimeError("db down")
    monkeypatch.setattr("services.supabase.get_service_client", lambda: _Boom())
    auth = _auth(caller_identity="agent:research", principal_id="research")
    # agent class default: locked from governance/, allowed operation/.
    assert _is_path_locked_for_principal(auth, "governance/x.md") is True
    assert _is_path_locked_for_principal(auth, "operation/x.md") is False


# ===========================================================================
# 2. GRANT-HONORED — an explicit narrowing grant actually narrows (allow-list)
# ===========================================================================

def test_grant_honored_narrows_to_granted_root(monkeypatch):
    """A grant scopes=['operation/'] → ALLOW operation/, DENY everything else —
    even roots the class default would allow. Proves the consult does something."""
    _patch_grant(monkeypatch, [{"scopes": ["operation/"]}])
    # Use an OWNER auth: class default allows almost everything; the grant must
    # narrow it to operation/ only.
    auth = _auth(caller_identity="operator", principal_id="u-owner")
    assert _is_path_locked_for_principal(auth, "operation/specs/x.md") is False  # granted
    assert _is_path_locked_for_principal(auth, "operation/x.md") is False         # granted
    # These are class-default-ALLOWED for owner, but NOT in the grant → DENY:
    assert _is_path_locked_for_principal(auth, "governance/x.md") is True
    assert _is_path_locked_for_principal(auth, "constitution/x.md") is True
    assert _is_path_locked_for_principal(auth, "persona/x.md") is True


def test_grant_honored_multi_root(monkeypatch):
    """scopes=['operation/','agents/'] → both allowed, others denied."""
    _patch_grant(monkeypatch, [{"scopes": ["operation/", "agents/"]}])
    auth = _auth(caller_identity="operator", principal_id="u-owner")
    assert _is_path_locked_for_principal(auth, "operation/x.md") is False
    assert _is_path_locked_for_principal(auth, "agents/x/memory/n.md") is False
    assert _is_path_locked_for_principal(auth, "governance/x.md") is True


def test_grant_honored_normalizes_trailing_slash(monkeypatch):
    """scopes without trailing slash ('operation') still matches 'operation/...'."""
    _patch_grant(monkeypatch, [{"scopes": ["operation"]}])
    auth = _auth(caller_identity="operator", principal_id="u-owner")
    assert _is_path_locked_for_principal(auth, "operation/x.md") is False
    assert _is_path_locked_for_principal(auth, "governance/x.md") is True


def test_grant_honored_strips_workspace_prefix(monkeypatch):
    """The allow-list path normalization matches _is_path_locked: a
    /workspace/-prefixed path is stripped before the root compare."""
    _patch_grant(monkeypatch, [{"scopes": ["operation/"]}])
    auth = _auth(caller_identity="operator", principal_id="u-owner")
    assert _is_path_locked_for_principal(auth, "/workspace/operation/x.md") is False
    assert _is_path_locked_for_principal(auth, "workspace/governance/x.md") is True


def test_path_under_scopes_matcher():
    # The powerbox matcher (arbitrary depth) replaces _grant_root_set (top-level
    # roots). None → not narrowing (True); [] → deny-all (False); [..] → prefix.
    assert path_under_scopes("operation/x.md", None) is True          # not narrowing
    assert path_under_scopes("operation/x.md", []) is False           # deny-all
    assert path_under_scopes("operation/x.md", ["operation/"]) is True
    assert path_under_scopes("agents/y.md", ["operation/", "agents/"]) is True
    assert path_under_scopes("governance/z.md", ["operation/"]) is False
    # arbitrary depth — the future-proof capability the roots model lacked
    assert path_under_scopes("operation/marketing/q3.md", ["operation/marketing/"]) is True
    assert path_under_scopes("operation/finance/x.md", ["operation/marketing/"]) is False
    assert path_under_scopes("operation/reports/q3.md", ["operation/reports/q3.md"]) is True  # exact file
    assert path_under_scopes("operation/reports/q4.md", ["operation/reports/q3.md"]) is False


# ===========================================================================
# 3. resolve_principal_id — the uniform mapping across principal classes
# ===========================================================================

def test_resolve_principal_id_explicit_wins():
    assert resolve_principal_id(_auth(principal_id="explicit-id")) == "explicit-id"


def test_resolve_principal_id_owner_is_user_id():
    assert resolve_principal_id(_auth(caller_identity="operator", user_id="u-1",
                                      principal_id=None)) == "u-1"


def test_resolve_principal_id_mcp_is_client_room_when_no_explicit():
    # Derivation safety-net: qualified caller_identity → the room name.
    assert resolve_principal_id(_auth(caller_identity="yarnnn:mcp:claude.ai",
                                      user_id="u-1", principal_id=None)) == "claude.ai"


def test_resolve_principal_id_mcp_bare_falls_to_user():
    assert resolve_principal_id(_auth(caller_identity="yarnnn:mcp", user_id="u-1",
                                      principal_id=None)) == "u-1"


def test_resolve_principal_id_agent_is_slug():
    assert resolve_principal_id(_auth(caller_identity="agent:research", user_id="u-1",
                                      principal_id=None)) == "research"
    assert resolve_principal_id(_auth(caller_identity="specialist:writer", user_id="u-1",
                                      principal_id=None)) == "writer"


# ===========================================================================
# 3a. ADR-373 D2.a — the MCP principal is the PROVIDER host-id, not client_id
# ===========================================================================

def test_d2a_mcp_resolves_to_host_id_over_explicit_client_id():
    """The D2.a change: for an MCP caller, the PROVIDER host-id wins over the
    explicit client_id. (For NON-MCP callers, explicit still wins — test below.)
    A connector's churning client_id no longer keys the grant."""
    auth = _auth(caller_identity="yarnnn:mcp:claude.ai", user_id="u-1",
                 principal_id="some-churning-client-uuid")
    assert resolve_principal_id(auth) == "claude.ai"  # host-id, NOT the uuid


def test_d2a_reconnect_resolves_to_same_provider():
    """Two DIFFERENT client_ids for the same provider resolve to ONE principal —
    so a reconnect maps to the same grant (the unbounded-tail fix)."""
    a = _auth(caller_identity="yarnnn:mcp:ChatGPT", user_id="u-1", principal_id="client-A")
    b = _auth(caller_identity="yarnnn:mcp:ChatGPT", user_id="u-1", principal_id="client-B")
    assert resolve_principal_id(a) == resolve_principal_id(b) == "chatgpt"


def test_d2a_unknown_provider_falls_back_to_room_then_client():
    """An MCP caller whose provider the registry doesn't know keeps a stable
    best-effort key (the room name), so it's still legible + revocable."""
    auth = _auth(caller_identity="yarnnn:mcp:weirdclient", user_id="u-1", principal_id="c-id")
    assert resolve_principal_id(auth) == "weirdclient"


def test_d2a_non_mcp_explicit_still_wins():
    """SAFETY: the D2.a reorder must NOT change non-MCP callers. An explicit
    principal_id on a non-MCP caller still wins (byte-identical)."""
    assert resolve_principal_id(_auth(principal_id="explicit-id")) == "explicit-id"


def test_d2a_owner_path_byte_identical():
    """SAFETY INVARIANT: the owner branch is untouched by D2.a — owner resolves
    to user_id exactly as before (the 99/0 proof basis)."""
    assert resolve_principal_id(_auth(caller_identity="operator", user_id="u-owner",
                                      principal_id="u-owner")) == "u-owner"
    assert resolve_principal_id(_auth(caller_identity="operator", user_id="u-owner",
                                      principal_id=None)) == "u-owner"


def test_resolve_principal_id_system_is_actor():
    assert resolve_principal_id(_auth(caller_identity="system:reconciler", user_id="u-1",
                                      principal_id=None)) == "reconciler"


def test_resolve_principal_id_reviewer_is_owner():
    # The seat acts for the workspace owner; key on user_id.
    assert resolve_principal_id(_auth(caller_identity="freddie:ai:v8", user_id="u-1",
                                      principal_id=None)) == "u-1"


# ===========================================================================
# 4. ADJACENT FIX — the MCP class matcher (was dormant on the room-qualified form)
# ===========================================================================

def test_caller_class_recognizes_room_qualified_mcp():
    """The live MCP caller_identity is room-qualified; it MUST classify as mcp,
    not fall through to agent. (The pre-2026-06-29 exact-match bug.)"""
    assert _caller_class(_auth(caller_identity="yarnnn:mcp:claude.ai")) == "mcp"
    assert _caller_class(_auth(caller_identity="yarnnn:mcp:chatgpt")) == "mcp"
    assert _caller_class(_auth(caller_identity="yarnnn:mcp")) == "mcp"  # bare still works


def test_mcp_topology_lock_now_engages_for_qualified_caller(monkeypatch):
    """With no grant row, a room-qualified MCP caller falls to the mcp class
    default — which LOCKS governance/persona/constitution/contract/system and
    ALLOWS operation/. The dormant lock is now live."""
    _patch_grant(monkeypatch, [])
    auth = _auth(caller_identity="yarnnn:mcp:claude.ai", principal_id="client-uuid")
    # Locked (the previously-dormant escalation paths):
    assert _is_path_locked_for_principal(auth, "governance/_autonomy.yaml") is True
    assert _is_path_locked_for_principal(auth, "persona/IDENTITY.md") is True
    assert _is_path_locked_for_principal(auth, "constitution/MANDATE.md") is True
    assert _is_path_locked_for_principal(auth, "contract/_preferences.yaml") is True
    assert _is_path_locked_for_principal(auth, "system/x.md") is True
    # Allowed (the foreign-LLM commons):
    assert _is_path_locked_for_principal(auth, "operation/memory/note.md") is False


# ===========================================================================
# 5. Per-request memoization — one DB round-trip per (principal, workspace)
# ===========================================================================

def test_grant_lookup_is_memoized_per_request(monkeypatch):
    """Two gate paths in one request (e.g. MoveFile src+dst) → ONE grant query."""
    calls = {"n": 0}

    class _CountingQuery(_FakeQuery):
        def execute(self):
            calls["n"] += 1
            return super().execute()

    class _CountingClient:
        def table(self, name):
            return _CountingQuery([{"scopes": ["operation/"]}])

    monkeypatch.setattr("services.supabase.get_service_client", lambda: _CountingClient())
    auth = _auth(caller_identity="operator", principal_id="u-owner")
    _is_path_locked_for_principal(auth, "operation/a.md")
    _is_path_locked_for_principal(auth, "operation/b.md")
    assert calls["n"] == 1, f"expected 1 memoized lookup, got {calls['n']}"
