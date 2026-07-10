"""The Powerbox — read+write, arbitrary-depth, two-axis gate (ADR-434, 2026-07-10).

ADR-373 shipped a write-only, top-level-root, one-axis grant `scopes`. The
powerbox completes it: `read_scopes` + `write_scopes`, each an allow-list of PATH
PREFIXES at ARBITRARY DEPTH, enforced on BOTH reads and writes. It is access(2)'s
read check for principal_grants. Permissions, not runtime.

What this gate pins:
  1. THE MATCHER — path_under_scopes: longest-prefix, arbitrary depth, three-state
     polarity (None=not-narrowing, []=deny-all, [..]=allow-list).
  2. TWO INDEPENDENT AXES — read and write move separately (read-only auditor:
     write=[], read=['operation/']). read ⊇ write is a default, not a constraint.
  3. THE READ GATE — ReadFile wholesale-DENYs out-of-scope; the set-returning
     reads FILTER (never leak an out-of-scope file's existence).
  4. THE SAFETY INVARIANT — no grant / NULL axis → class default (read-all /
     class-default write) = byte-identical (every live grant is NULL-scoped).
  5. OBJECT-DEPTH — operation/marketing/ and operation/reports/q3.md are valid
     scopes and nest correctly (the future-proof capability roots lacked).
  6. AGENT-SCOPE reads are not commons reads — the gate does not fire on them.

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
    path_under_scopes,
    grant_read_scopes,
    read_scope_db_prefixes,
    filter_results_by_read_scope,
    _grant_axis,
    _is_path_readable_for_principal,
    _is_path_locked_for_principal,
    _is_path_locked,
    _resolve_read_gate_path,
)
from services.primitives.permission import resolve_permission, PermissionDecision  # noqa: E402


# ---------------------------------------------------------------------------
# Fakes — a service client returning a chosen grant row (two-axis columns).
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


def _grant(read=None, write=None, legacy=None):
    """One grant row in the two-axis shape. read/write are the new columns;
    legacy is the deprecated `scopes` mirror (used only for the fallback test)."""
    return {"read_scopes": read, "write_scopes": write, "scopes": legacy}


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


_SAMPLE = [
    "governance/_autonomy.yaml",
    "constitution/MANDATE.md",
    "persona/IDENTITY.md",
    "operation/reports/q3.md",
    "system/notes.md",
    "agents/x/memory/n.md",
]


# ===========================================================================
# 1. THE MATCHER — longest-prefix, arbitrary depth, three-state polarity
# ===========================================================================

def test_matcher_polarity():
    assert path_under_scopes("operation/x.md", None) is True    # not narrowing
    assert path_under_scopes("operation/x.md", []) is False     # deny-all
    assert path_under_scopes("operation/x.md", ["operation/"]) is True


def test_matcher_arbitrary_depth():
    # A subtree scope matches itself + everything beneath it.
    assert path_under_scopes("operation/marketing/", ["operation/marketing/"]) is True
    assert path_under_scopes("operation/marketing/q3.md", ["operation/marketing/"]) is True
    # A sibling under the same parent is NOT matched.
    assert path_under_scopes("operation/finance/x.md", ["operation/marketing/"]) is False
    # The parent is not matched by a child scope.
    assert path_under_scopes("operation/other.md", ["operation/marketing/"]) is False


def test_matcher_exact_file_scope():
    assert path_under_scopes("operation/reports/q3.md", ["operation/reports/q3.md"]) is True
    assert path_under_scopes("operation/reports/q4.md", ["operation/reports/q3.md"]) is False
    # a file scope does not act as a directory prefix
    assert path_under_scopes("operation/reports/q3.md/child", ["operation/reports/q3.md"]) is False


def test_matcher_no_sibling_prefix_bleed():
    # 'operation/' must NOT match 'operationX/' (trailing slash guards this).
    assert path_under_scopes("operationX/x.md", ["operation/"]) is False


def test_matcher_normalizes_absolute_and_workspace_prefix():
    for form in ("operation/x.md", "/operation/x.md", "workspace/operation/x.md",
                 "/workspace/operation/x.md"):
        assert path_under_scopes(form, ["operation/"]) is True


# ===========================================================================
# 2. TWO INDEPENDENT AXES — read and write move separately
# ===========================================================================

def test_axes_resolve_independently(monkeypatch):
    _patch_grant(monkeypatch, [_grant(read=["operation/"], write=["operation/drafts/"])])
    auth = _auth(principal_id="p-member")
    assert _grant_axis(auth, "read") == ["operation/"]
    assert _grant_axis(auth, "write") == ["operation/drafts/"]


def test_read_only_auditor(monkeypatch):
    """write=[] (deny-all writes) + read=['operation/'] — a read-only auditor.
    The exact case one-axis scopes could not express."""
    _patch_grant(monkeypatch, [_grant(read=["operation/"], write=[])])
    auth = _auth(principal_id="p-auditor")
    # reads operation/, denied elsewhere
    assert _is_path_readable_for_principal(auth, "operation/reports/q3.md") is True
    assert _is_path_readable_for_principal(auth, "governance/x.md") is False
    # writes NOTHING (deny-all write axis)
    assert _is_path_locked_for_principal(auth, "operation/reports/q3.md") is True
    assert _is_path_locked_for_principal(auth, "operation/drafts/x.md") is True


def test_scoped_writer_broad_reader(monkeypatch):
    """read broader than write: reads all of operation/, writes only drafts/."""
    _patch_grant(monkeypatch, [_grant(read=["operation/"], write=["operation/drafts/"])])
    auth = _auth(principal_id="p-member")
    assert _is_path_readable_for_principal(auth, "operation/reports/q3.md") is True   # readable
    assert _is_path_locked_for_principal(auth, "operation/reports/q3.md") is True     # NOT writable
    assert _is_path_locked_for_principal(auth, "operation/drafts/x.md") is False      # writable


# ===========================================================================
# 3. POLARITY per axis — deny-all vs class default, both axes
# ===========================================================================

def test_null_axes_are_class_default(monkeypatch):
    """The safety invariant: NULL on both axes → read-all + class-default write.
    This is the 15 live grants — byte-identical."""
    _patch_grant(monkeypatch, [_grant(read=None, write=None)])
    auth = _auth(principal_id="u-owner")
    assert grant_read_scopes(auth) is None
    for p in _SAMPLE:
        assert _is_path_readable_for_principal(auth, p) is True
        # write matches the class default (owner: only system/ locked)
        assert _is_path_locked_for_principal(auth, p) == _is_path_locked("operator", p)


def test_no_grant_row_is_class_default(monkeypatch):
    _patch_grant(monkeypatch, [])
    auth = _auth(principal_id="u-owner")
    assert grant_read_scopes(auth) is None
    for p in _SAMPLE:
        assert _is_path_readable_for_principal(auth, p) is True


def test_empty_read_axis_reads_nothing(monkeypatch):
    _patch_grant(monkeypatch, [_grant(read=[], write=[])])
    auth = _auth(principal_id="p-locked")
    assert grant_read_scopes(auth) == []
    for p in _SAMPLE:
        assert _is_path_readable_for_principal(auth, p) is False


def test_legacy_scopes_column_mirrors_both_axes(monkeypatch):
    """A row predating migration 211 (new columns absent, only `scopes` set) →
    the legacy `scopes` mirrors into BOTH axes (read ⊇ write = ADR-373 behavior)."""
    _patch_grant(monkeypatch, [_grant(read=None, write=None, legacy=["operation/"])])
    auth = _auth(principal_id="p-legacy")
    assert _grant_axis(auth, "read") == ["operation/"]
    assert _grant_axis(auth, "write") == ["operation/"]
    assert _is_path_readable_for_principal(auth, "operation/x.md") is True
    assert _is_path_readable_for_principal(auth, "governance/x.md") is False


# ===========================================================================
# 4. THE READFILE WHOLESALE GATE (resolve_permission)
# ===========================================================================

@pytest.mark.asyncio
async def test_readfile_in_scope_applies(monkeypatch):
    _patch_grant(monkeypatch, [_grant(read=["operation/"], write=["operation/"])])
    auth = _auth(principal_id="p-member")
    decision, reason = await resolve_permission(
        auth, "ReadFile", {"scope": "workspace", "path": "operation/reports/q3.md"})
    assert decision == PermissionDecision.APPLY and reason == "read_only"


@pytest.mark.asyncio
async def test_readfile_out_of_scope_denies(monkeypatch):
    _patch_grant(monkeypatch, [_grant(read=["operation/"], write=["operation/"])])
    auth = _auth(principal_id="p-member")
    decision, reason = await resolve_permission(
        auth, "ReadFile", {"scope": "workspace", "path": "governance/_autonomy.yaml"})
    assert decision == PermissionDecision.DENY and reason.startswith("read_scope_denied:")


@pytest.mark.asyncio
async def test_readfile_deep_scope(monkeypatch):
    """Object-depth at the gate: read scope operation/marketing/ denies a sibling."""
    _patch_grant(monkeypatch, [_grant(read=["operation/marketing/"], write=[])])
    auth = _auth(principal_id="p-member")
    d1, _ = await resolve_permission(auth, "ReadFile",
                                     {"scope": "workspace", "path": "operation/marketing/plan.md"})
    d2, _ = await resolve_permission(auth, "ReadFile",
                                     {"scope": "workspace", "path": "operation/finance/plan.md"})
    assert d1 == PermissionDecision.APPLY
    assert d2 == PermissionDecision.DENY


@pytest.mark.asyncio
async def test_readfile_null_scopes_applies_everything(monkeypatch):
    _patch_grant(monkeypatch, [_grant(read=None, write=None)])
    auth = _auth(principal_id="u-owner")
    for p in _SAMPLE:
        decision, _ = await resolve_permission(auth, "ReadFile", {"scope": "workspace", "path": p})
        assert decision == PermissionDecision.APPLY


@pytest.mark.asyncio
async def test_readfile_agent_scope_not_gated(monkeypatch):
    _patch_grant(monkeypatch, [_grant(read=[], write=[])])  # deny-all commons
    auth = _auth(principal_id="p-locked")
    decision, reason = await resolve_permission(
        auth, "ReadFile", {"scope": "agent", "path": "thesis.md"})
    assert decision == PermissionDecision.APPLY and reason == "read_only"


def test_resolve_read_gate_path_skips_agent_scope():
    assert _resolve_read_gate_path({"scope": "agent", "path": "x.md"}) is None
    assert _resolve_read_gate_path({"scope": "workspace", "path": "operation/x.md"}) == "operation/x.md"
    assert _resolve_read_gate_path({"path": "operation/x.md"}) == "operation/x.md"


# ===========================================================================
# 5. THE SET FILTER — drops out-of-scope rows, never leaks their count
# ===========================================================================

def test_filter_drops_out_of_scope_rows(monkeypatch):
    _patch_grant(monkeypatch, [_grant(read=["operation/marketing/"], write=[])])
    auth = _auth(principal_id="p-member")
    rows = [
        {"path": "operation/marketing/q3.md"},
        {"path": "operation/finance/q3.md"},
        {"path": "governance/_autonomy.yaml"},
        {"path": "operation/marketing/plans/2027.md"},  # deeper — still in scope
    ]
    kept = {r["path"] for r in filter_results_by_read_scope(auth, rows)}
    assert kept == {"operation/marketing/q3.md", "operation/marketing/plans/2027.md"}


def test_filter_null_scope_unchanged(monkeypatch):
    _patch_grant(monkeypatch, [_grant(read=None, write=None)])
    auth = _auth(principal_id="u-owner")
    rows = [{"path": "governance/x.md"}, {"path": "operation/y.md"}]
    assert filter_results_by_read_scope(auth, rows) == rows


def test_filter_deny_all_returns_nothing(monkeypatch):
    _patch_grant(monkeypatch, [_grant(read=[], write=[])])
    auth = _auth(principal_id="p-locked")
    rows = [{"path": "operation/x.md"}, {"path": "uploads/y.md"}]
    assert filter_results_by_read_scope(auth, rows) == []


# ===========================================================================
# 6. DB-SIDE SCOPE PREFIXES — absolute form for the search RPCs
# ===========================================================================

def test_read_scope_db_prefixes_absolute(monkeypatch):
    """The search RPCs match wf.path (absolute /workspace/...), so the scopes
    convert to absolute prefixes. This is what makes limit-after-scope work."""
    _patch_grant(monkeypatch, [_grant(read=["operation/marketing/"], write=[])])
    auth = _auth(principal_id="p-member")
    assert read_scope_db_prefixes(auth) == ["/workspace/operation/marketing/"]


def test_read_scope_db_prefixes_null_is_none(monkeypatch):
    """NULL read axis → None → the RPC skips scoping (unscoped, byte-identical)."""
    _patch_grant(monkeypatch, [_grant(read=None, write=None)])
    auth = _auth(principal_id="u-owner")
    assert read_scope_db_prefixes(auth) is None


def test_read_scope_db_prefixes_deny_all_is_empty(monkeypatch):
    """Deny-all read axis → [] → the RPC matches nothing."""
    _patch_grant(monkeypatch, [_grant(read=[], write=[])])
    auth = _auth(principal_id="p-locked")
    assert read_scope_db_prefixes(auth) == []
