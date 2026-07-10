"""Powerbox BLOB read-gate — regression gate (2026-07-10).

The powerbox (ADR-373 read-scope, ADR-427 seam) gates the file PRIMITIVES
(ReadFile/ListFiles/SearchFiles/QueryKnowledge). But a raw upload's blob is
served OUT-OF-BAND — the FE resolves a stable `content_url` to a fresh signed
URL via `GET /documents/blob` (or downloads via `GET /documents/{path}/download`),
neither of which runs a primitive. That is the blob read-gate hole: a narrowed
principal who cannot ReadFile a path could still fetch its blob by URL.

`routes/documents.py` now consults the SAME read-scope the primitives use
(`_is_path_readable_for_principal`) on both serving endpoints. This gate pins:

  1. THE SAFETY INVARIANT — NULL-scoped grants (the 15 live grants) → read-all →
     the added check is a pure no-op; the blob/download serves byte-identically.
  2. THE GATE — a narrowed principal whose read scope EXCLUDES the blob's
     workspace path is denied (404); a scope that INCLUDES it still serves.
  3. Both serving paths — /documents/blob (storage_path→path mapping) and
     /documents/{path}/download (path is the argument directly).

Fixture style mirrors test_powerbox_read_gate.py: a fake service client returns
a chosen grant row; the blob→path mapping and download row come from a fake
`auth.client`.

Run: cd api && python -m pytest test_powerbox_blob_gate.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

API_DIR = Path(__file__).parent
sys.path.insert(0, str(API_DIR))

from fastapi import HTTPException  # noqa: E402

from services.primitives import workspace as ws  # noqa: E402
from services.documents import blob_content_url  # noqa: E402
import routes.documents as docroutes  # noqa: E402


# ---------------------------------------------------------------------------
# Fakes — grant lookup (service client) + the workspace_files mapping (auth.client)
# ---------------------------------------------------------------------------

class _FakeQuery:
    """Ignores filter args, returns the rows it was seeded with (like the
    read-gate test's fake). Enough for the single-row lookups here."""

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
    """Stands in for the grant-lookup service client — only serves
    principal_grants."""

    def __init__(self, grant_rows):
        self._rows = grant_rows

    def table(self, name):
        assert name == "principal_grants", f"unexpected grant table {name}"
        return _FakeQuery(self._rows)


class _FakeAuthClient:
    """Stands in for `auth.client` — serves the workspace_files row that maps a
    blob's storage_path back to its workspace path."""

    def __init__(self, ws_rows):
        self._ws_rows = ws_rows

    def table(self, name):
        assert name == "workspace_files", f"unexpected auth table {name}"
        return _FakeQuery(self._ws_rows)


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


def _patch_signed_ok(monkeypatch, url="https://signed.example/blob"):
    """The signing wire always succeeds — so any 404/403 in the test is the GATE,
    not a signing failure. Patched on the route module (imported name)."""
    monkeypatch.setattr(
        docroutes, "create_signed_url_for_storage_path",
        lambda service, storage_path, expires_in=3600: url,
    )
    monkeypatch.setattr(docroutes, "get_service_client", lambda: object())


# The upload's storage key + the workspace path its blob belongs to.
STORAGE_PATH = "u-owner/doc-123/original.pdf"
WS_PATH = "/workspace/inbound/uploads/operator/acme-brief.pdf"


def _auth(ws_rows, user_id="u-owner", principal_id="u-owner"):
    """An auth whose `.client` serves the blob→path mapping row(s)."""
    return SimpleNamespace(
        caller_identity="operator",
        user_id=user_id,
        workspace_id="ws-1",
        principal_id=principal_id,
        freddie_caller=False,
        client=_FakeAuthClient(ws_rows),
    )


def _mapping_row():
    """The workspace_files row whose content_url points at STORAGE_PATH."""
    return [{"path": WS_PATH, "content_url": blob_content_url(STORAGE_PATH)}]


# ===========================================================================
# /documents/blob — storage_path → workspace path → read-scope consult
# ===========================================================================

@pytest.mark.asyncio
async def test_blob_null_scope_serves_byte_identical(monkeypatch):
    """SAFETY INVARIANT: NULL-scoped grant → read-all → the gate is a no-op; the
    blob is served exactly as before the powerbox."""
    _patch_grant(monkeypatch, [{"scopes": None}])
    _patch_signed_ok(monkeypatch)
    auth = _auth(_mapping_row())
    resp = await docroutes.get_blob_url(auth=auth, storage_path=STORAGE_PATH)
    assert resp.url == "https://signed.example/blob"
    assert resp.expires_in == 3600


@pytest.mark.asyncio
async def test_blob_no_grant_row_serves(monkeypatch):
    """No grant row at all → class default (read-all) → served."""
    _patch_grant(monkeypatch, [])
    _patch_signed_ok(monkeypatch)
    auth = _auth(_mapping_row())
    resp = await docroutes.get_blob_url(auth=auth, storage_path=STORAGE_PATH)
    assert resp.url == "https://signed.example/blob"


@pytest.mark.asyncio
async def test_blob_out_of_scope_denied(monkeypatch):
    """A narrowed principal whose read scope EXCLUDES the blob's path is denied.
    The blob lives under inbound/uploads/, the grant only reads operation/."""
    _patch_grant(monkeypatch, [{"scopes": ["operation/"]}])
    _patch_signed_ok(monkeypatch)
    auth = _auth(_mapping_row(), principal_id="p-member")
    with pytest.raises(HTTPException) as exc:
        await docroutes.get_blob_url(auth=auth, storage_path=STORAGE_PATH)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_blob_in_scope_serves(monkeypatch):
    """A narrowed principal whose read scope INCLUDES the blob's path serves.
    The grant reads inbound/, which covers inbound/uploads/…"""
    _patch_grant(monkeypatch, [{"scopes": ["inbound/"]}])
    _patch_signed_ok(monkeypatch)
    auth = _auth(_mapping_row(), principal_id="p-member")
    resp = await docroutes.get_blob_url(auth=auth, storage_path=STORAGE_PATH)
    assert resp.url == "https://signed.example/blob"


@pytest.mark.asyncio
async def test_blob_ownership_guard_still_first(monkeypatch):
    """The pre-existing ownership guard (key under the caller's own user_id) still
    fires before the read-scope consult — a foreign-prefix key is 404 regardless
    of scope. (Byte-identical to pre-powerbox.)"""
    _patch_grant(monkeypatch, [{"scopes": None}])
    _patch_signed_ok(monkeypatch)
    auth = _auth(_mapping_row())
    with pytest.raises(HTTPException) as exc:
        await docroutes.get_blob_url(auth=auth, storage_path="someone-else/x/original.pdf")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_blob_unmapped_path_falls_back_to_ownership(monkeypatch):
    """If the blob→path mapping is unavailable (no workspace_files row matches),
    the gate cannot consult a scope — it declines to fabricate a path and serves
    on the ownership guard alone (fail-open to today's behavior, never a hack)."""
    _patch_grant(monkeypatch, [{"scopes": ["operation/"]}])  # would deny if mapped
    _patch_signed_ok(monkeypatch)
    auth = _auth([], principal_id="p-member")  # no mapping row
    resp = await docroutes.get_blob_url(auth=auth, storage_path=STORAGE_PATH)
    assert resp.url == "https://signed.example/blob"


# ===========================================================================
# /documents/{path}/download — the workspace path is the argument directly
# ===========================================================================

def _download_auth(user_id="u-owner", principal_id="u-owner"):
    """Download reads a workspace_files row by path; content_url carries the
    storage_path (ADR-395 raw row)."""
    row = [{"content": "", "content_url": blob_content_url(STORAGE_PATH)}]
    return SimpleNamespace(
        caller_identity="operator",
        user_id=user_id,
        workspace_id="ws-1",
        principal_id=principal_id,
        freddie_caller=False,
        client=_FakeAuthClient(row),
    )


@pytest.mark.asyncio
async def test_download_null_scope_serves_byte_identical(monkeypatch):
    """SAFETY INVARIANT on the download path: NULL grant → served as before."""
    _patch_grant(monkeypatch, [{"scopes": None}])
    _patch_signed_ok(monkeypatch)
    auth = _download_auth()
    resp = await docroutes.download_document(auth=auth, document_path=WS_PATH)
    assert resp.url == "https://signed.example/blob"


@pytest.mark.asyncio
async def test_download_out_of_scope_denied(monkeypatch):
    """A narrowed principal downloading an out-of-scope path is denied (404)."""
    _patch_grant(monkeypatch, [{"scopes": ["operation/"]}])
    _patch_signed_ok(monkeypatch)
    auth = _download_auth(principal_id="p-member")
    with pytest.raises(HTTPException) as exc:
        await docroutes.download_document(auth=auth, document_path=WS_PATH)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_download_in_scope_serves(monkeypatch):
    """A narrowed principal downloading an in-scope path serves."""
    _patch_grant(monkeypatch, [{"scopes": ["inbound/"]}])
    _patch_signed_ok(monkeypatch)
    auth = _download_auth(principal_id="p-member")
    resp = await docroutes.download_document(auth=auth, document_path=WS_PATH)
    assert resp.url == "https://signed.example/blob"
