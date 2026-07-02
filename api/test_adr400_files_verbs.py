"""
ADR-400 — the two-principal Files surface. Route topology guards.

The load-bearing safety property: the operator can move/rename/delete/restore
ONLY operator-owned files (uploads/ + inbound/uploads/). A verb aimed at
system-owned substrate (governance/persona/operation/...) must 403 — the human
does not reorganize what the agents authored. These tests drive the real route
handlers with the scope guard, mocking at the DB boundary.
"""

import asyncio
from unittest.mock import patch

import pytest
from fastapi import HTTPException


class _Auth:
    user_id = "user-1234"
    class client:  # noqa: N801
        pass


def _run(coro):
    return asyncio.run(coro)


# ── Move / rename scope ─────────────────────────────────────────────────────

@pytest.mark.parametrize("src,dst,ok", [
    # operator-owned → operator-owned: allowed (reaches the primitive)
    ("/workspace/inbound/uploads/operator/a.pdf", "/workspace/inbound/uploads/operator/b.pdf", True),
    ("/workspace/uploads/x.md", "/workspace/uploads/y.md", True),
    # source system-owned: 403
    ("/workspace/governance/AUTONOMY.md", "/workspace/uploads/x.md", False),
    ("/workspace/persona/IDENTITY.md", "/workspace/inbound/uploads/operator/x.md", False),
    # destination system-owned: 403 (can't move INTO a locked root)
    ("/workspace/inbound/uploads/operator/a.pdf", "/workspace/governance/a.pdf", False),
])
def test_move_scope_guard(src, dst, ok):
    from routes.documents import move_document, MoveRequest

    async def _fake_exec(auth, name, inp):
        assert name == "MoveFile"
        return {"success": True, "path": inp["new_path"]}

    with patch("services.primitives.registry.execute_primitive", _fake_exec):
        body = MoveRequest(path=src, new_path=dst)
        if ok:
            r = _run(move_document(body, _Auth()))
            assert r["success"] is True
        else:
            with pytest.raises(HTTPException) as ei:
                _run(move_document(body, _Auth()))
            assert ei.value.status_code == 403


# ── Restore scope ───────────────────────────────────────────────────────────

def test_restore_rejects_system_path():
    from routes.documents import restore_document, RestoreRequest
    with pytest.raises(HTTPException) as ei:
        _run(restore_document(RestoreRequest(path="/workspace/governance/AUTONOMY.md"), _Auth()))
    assert ei.value.status_code == 403


# ── The FE/BE topology must agree ───────────────────────────────────────────

def test_operator_prefixes_are_the_canonical_two():
    """The operator-owned roots are exactly uploads/ + inbound/uploads/ — the
    single scope the delete/move/restore routes all share. If this changes, the
    FE ownership.ts OPERATOR_OWNED_PREFIXES must change in lockstep."""
    from routes.documents import _OPERATOR_ARCHIVABLE_PREFIXES
    assert _OPERATOR_ARCHIVABLE_PREFIXES == (
        "/workspace/uploads/", "/workspace/inbound/uploads/",
    )
