"""Powerbox read gate + empty-set polarity — regression gate (2026-07-10).

ADR-373 shipped multi-principal grants + a `narrow` verb; the gate consult
(`_is_path_locked_for_principal`) enforced them on WRITES only. A narrowed
principal still READ the whole commons, because read-only primitives short-
circuit APPLY in `resolve_permission` before any consult runs. This is the
powerbox debt — `access(2)`'s read check for `principal_grants`, which existed
only on the write path.

Half A closes it, at ROOT granularity (object-scoping is Half B), with the
read⊇write model (the same `scopes` list governs both axes; no separate
read-scope field yet). Two mechanisms, because the gate is binary but reads split:
  - ReadFile (single object) → a WHOLESALE DENY in resolve_permission.
  - ListFiles/SearchFiles/QueryKnowledge (result sets) → a FILTER in the handler
    (a wholesale deny would leak an out-of-scope file's existence as an error).

What this gate pins:
  1. POLARITY — scopes:[] is DENY-ALL (an explicit empty allow-list), distinct
     from scopes:NULL → class default. On BOTH axes.
  2. THE SAFETY INVARIANT — owner / NULL scopes read everything, byte-identical
     to the pre-powerbox world (the 15 live grants are all NULL-scoped).
  3. THE READ GATE — a narrowed principal's ReadFile of an out-of-scope path
     resolves DENY; an in-scope path resolves APPLY (read_only).
  4. THE FILTER — the set helper drops out-of-scope rows and NEVER leaks their
     count (the returned list IS the count).
  5. AGENT-SCOPE READS are not commons reads — the gate does not fire on them.

Run: cd api && python -m pytest test_powerbox_read_gate.py -q
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
    grant_read_roots,
    _is_path_readable_for_principal,
    _is_path_locked_for_principal,
    _resolve_read_gate_path,
    path_readable_under_roots,
    filter_results_by_read_scope,
)
from services.primitives.permission import resolve_permission, PermissionDecision  # noqa: E402


# ---------------------------------------------------------------------------
# Fakes — reuse the ADR-373 shape (a service client returning a chosen grant).
# ---------------------------------------------------------------------------

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
        return SimpleNamespace(data=self._rows)


class _FakeServiceClient:
    def __init__(self, grant_rows):
        self._rows = grant_rows

    def table(self, name):
        assert name == "principal_grants", f"unexpected table {name}"
        return _FakeQuery(self._rows)


@pytest.fixture(autouse=True)
def _clear_grant_cache():
    if hasattr(ws._grant_cache, "store"):
        ws._grant_cache.store = {}
    yield
    if hasattr(ws._grant_cache, "store"):
        ws._grant_cache.store = {}


def _patch_grant(monkeypatch, grant_rows):
    fake = _FakeServiceClient(grant_rows)
    monkeypatch.setattr("services.supabase.get_service_client", lambda: fake)


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


_SAMPLE_PATHS = [
    "governance/_autonomy.yaml",
    "constitution/MANDATE.md",
    "persona/IDENTITY.md",
    "operation/reports/q3.md",
    "system/notes.md",
    "agents/x/memory/n.md",
]


# ===========================================================================
# 1. POLARITY — [] is deny-all on BOTH axes; NULL is class default
# ===========================================================================

def test_null_scopes_read_everything(monkeypatch):
    """The safety invariant: NULL scopes → grant_read_roots None → read-all.
    This is the 15 live grants. Byte-identical to the pre-powerbox world."""
    _patch_grant(monkeypatch, [{"scopes": None}])
    auth = _auth(principal_id="u-owner")
    assert grant_read_roots(auth) is None
    for p in _SAMPLE_PATHS:
        assert _is_path_readable_for_principal(auth, p) is True


def test_no_grant_row_reads_everything(monkeypatch):
    """No grant row at all → read-all (class default). Same as NULL."""
    _patch_grant(monkeypatch, [])
    auth = _auth(principal_id="u-owner")
    assert grant_read_roots(auth) is None
    for p in _SAMPLE_PATHS:
        assert _is_path_readable_for_principal(auth, p) is True


def test_empty_scopes_read_nothing(monkeypatch):
    """POLARITY: scopes:[] is an EXPLICIT empty allow-list → read NOTHING.
    grant_read_roots returns the empty set (NOT None). Every path unreadable."""
    _patch_grant(monkeypatch, [{"scopes": []}])
    auth = _auth(principal_id="p-locked")
    assert grant_read_roots(auth) == set()
    for p in _SAMPLE_PATHS:
        assert _is_path_readable_for_principal(auth, p) is False


def test_empty_scopes_write_nothing(monkeypatch):
    """The write-axis half of the same polarity fix: scopes:[] → EVERY write
    locked (deny-all), not the class default. (This is the assertion the ADR-373
    gate's test_empty_scopes_list_is_deny_all also pins — proven here on the
    read module's own entry point for completeness.)"""
    _patch_grant(monkeypatch, [{"scopes": []}])
    auth = _auth(principal_id="p-locked")
    for p in _SAMPLE_PATHS:
        assert _is_path_locked_for_principal(auth, p) is True


# ===========================================================================
# 2. NARROWED READ — a granted root reads; others don't
# ===========================================================================

def test_narrowed_read_honors_granted_root(monkeypatch):
    """scopes:['operation/'] → read operation/, deny everything else."""
    _patch_grant(monkeypatch, [{"scopes": ["operation/"]}])
    auth = _auth(principal_id="p-member")
    assert grant_read_roots(auth) == {"operation/"}
    assert _is_path_readable_for_principal(auth, "operation/reports/q3.md") is True
    assert _is_path_readable_for_principal(auth, "governance/_autonomy.yaml") is False
    assert _is_path_readable_for_principal(auth, "persona/IDENTITY.md") is False


def test_narrowed_read_multi_root(monkeypatch):
    _patch_grant(monkeypatch, [{"scopes": ["operation/", "uploads/"]}])
    auth = _auth(principal_id="p-member")
    assert _is_path_readable_for_principal(auth, "operation/x.md") is True
    assert _is_path_readable_for_principal(auth, "uploads/doc.md") is True
    assert _is_path_readable_for_principal(auth, "agents/x/n.md") is False


def test_read_gate_normalizes_absolute_and_workspace_prefix(monkeypatch):
    """The read consult normalizes '/workspace/...' + 'workspace/...' the same
    way the write consult does, so a granted root matches regardless of form."""
    _patch_grant(monkeypatch, [{"scopes": ["operation/"]}])
    auth = _auth(principal_id="p-member")
    for form in ("operation/x.md", "/operation/x.md", "workspace/operation/x.md",
                 "/workspace/operation/x.md"):
        assert _is_path_readable_for_principal(auth, form) is True


# ===========================================================================
# 3. THE READFILE WHOLESALE GATE (resolve_permission)
# ===========================================================================

@pytest.mark.asyncio
async def test_readfile_in_scope_applies(monkeypatch):
    _patch_grant(monkeypatch, [{"scopes": ["operation/"]}])
    auth = _auth(principal_id="p-member")
    decision, reason = await resolve_permission(
        auth, "ReadFile", {"scope": "workspace", "path": "operation/reports/q3.md"})
    assert decision == PermissionDecision.APPLY
    assert reason == "read_only"


@pytest.mark.asyncio
async def test_readfile_out_of_scope_denies(monkeypatch):
    _patch_grant(monkeypatch, [{"scopes": ["operation/"]}])
    auth = _auth(principal_id="p-member")
    decision, reason = await resolve_permission(
        auth, "ReadFile", {"scope": "workspace", "path": "governance/_autonomy.yaml"})
    assert decision == PermissionDecision.DENY
    assert reason.startswith("read_scope_denied:")


@pytest.mark.asyncio
async def test_readfile_null_scopes_applies_everything(monkeypatch):
    """The safety invariant at the gate: NULL scopes → every ReadFile APPLYs
    (read_only). Byte-identical for the live grants."""
    _patch_grant(monkeypatch, [{"scopes": None}])
    auth = _auth(principal_id="u-owner")
    for p in _SAMPLE_PATHS:
        decision, _ = await resolve_permission(
            auth, "ReadFile", {"scope": "workspace", "path": p})
        assert decision == PermissionDecision.APPLY


@pytest.mark.asyncio
async def test_readfile_agent_scope_not_gated(monkeypatch):
    """An agent reading its OWN workspace (scope='agent') is a different topology
    — the commons read gate does not fire. Even a deny-all commons grant does not
    block an agent-scope read."""
    _patch_grant(monkeypatch, [{"scopes": []}])  # deny-all in the commons
    auth = _auth(principal_id="p-locked")
    decision, reason = await resolve_permission(
        auth, "ReadFile", {"scope": "agent", "path": "thesis.md"})
    assert decision == PermissionDecision.APPLY
    assert reason == "read_only"


def test_resolve_read_gate_path_skips_agent_scope():
    """The gate-path resolver returns None for agent scope (no commons gate)."""
    assert _resolve_read_gate_path({"scope": "agent", "path": "x.md"}) is None
    assert _resolve_read_gate_path({"scope": "workspace", "path": "operation/x.md"}) == "operation/x.md"
    # absent scope → treated as workspace (the Reviewer default)
    assert _resolve_read_gate_path({"path": "operation/x.md"}) == "operation/x.md"


# ===========================================================================
# 4. THE SET FILTER — drops out-of-scope rows, never leaks their count
# ===========================================================================

def test_filter_drops_out_of_scope_rows(monkeypatch):
    _patch_grant(monkeypatch, [{"scopes": ["operation/"]}])
    auth = _auth(principal_id="p-member")
    rows = [
        {"path": "operation/reports/q3.md"},
        {"path": "governance/_autonomy.yaml"},
        {"path": "operation/notes.md"},
        {"path": "persona/IDENTITY.md"},
    ]
    kept = filter_results_by_read_scope(auth, rows)
    kept_paths = {r["path"] for r in kept}
    assert kept_paths == {"operation/reports/q3.md", "operation/notes.md"}
    # No count leak: the returned list IS the count. Nothing signals "2 hidden".
    assert len(kept) == 2


def test_filter_null_scopes_returns_unchanged(monkeypatch):
    """The safety invariant on the filter: NULL scopes → the list is returned
    verbatim (same object contents, no filtering)."""
    _patch_grant(monkeypatch, [{"scopes": None}])
    auth = _auth(principal_id="u-owner")
    rows = [{"path": "governance/x.md"}, {"path": "operation/y.md"}]
    kept = filter_results_by_read_scope(auth, rows)
    assert kept == rows


def test_filter_empty_scopes_returns_nothing(monkeypatch):
    """Deny-all grant → the filter returns an empty list (reads nothing)."""
    _patch_grant(monkeypatch, [{"scopes": []}])
    auth = _auth(principal_id="p-locked")
    rows = [{"path": "operation/x.md"}, {"path": "uploads/y.md"}]
    assert filter_results_by_read_scope(auth, rows) == []


def test_path_readable_under_roots_pure_predicate():
    """The pure predicate the handlers filter with — None = read-all."""
    assert path_readable_under_roots("operation/x.md", None) is True
    assert path_readable_under_roots("operation/x.md", {"operation/"}) is True
    assert path_readable_under_roots("governance/x.md", {"operation/"}) is False
    assert path_readable_under_roots("operation/x.md", set()) is False  # deny-all
    # normalization: absolute + workspace-prefixed forms match too
    assert path_readable_under_roots("/workspace/operation/x.md", {"operation/"}) is True


# ===========================================================================
# 5. THE THREE LAYERS AGREE — read helpers are the read analog of the write one
# ===========================================================================

def test_read_is_the_inverse_polarity_of_write(monkeypatch):
    """_is_path_readable_for_principal is the polarity inverse of
    _is_path_locked_for_principal under the read⊇write model: for the same
    narrowing grant, readable(path) == not locked-for-write(path)."""
    _patch_grant(monkeypatch, [{"scopes": ["operation/", "agents/"]}])
    auth = _auth(principal_id="p-member")
    for p in _SAMPLE_PATHS:
        readable = _is_path_readable_for_principal(auth, p)
        locked = _is_path_locked_for_principal(auth, p)
        assert readable == (not locked), (
            f"read/write polarity mismatch at {p}: readable={readable} locked={locked}"
        )
