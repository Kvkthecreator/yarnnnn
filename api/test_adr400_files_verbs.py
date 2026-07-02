"""
ADR-400 Amendment 1 — the operator's organize reach. Route topology guards.

The corrected boundary: the operator can move/rename/trash/restore their WHOLE
workspace EXCEPT (a) system/ (runtime state) and (b) _*.yaml/_*.json machine-
config (read by exact path). It's the operator's filesystem; delete is
reversible, so this is safe. The prior uploads/-only scope was a misread of
ADR-320's foreign-principal lock as an operator lock (Amendment 1 corrects it).

These tests drive the real route handlers with the corrected scope guard.
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


# ── operator_can_organize — the single source of truth ──────────────────────

@pytest.mark.parametrize("path,ok", [
    # The operator's authored substrate — ALL organizable (Amendment 1).
    ("/workspace/constitution/PRECEDENT.md", True),
    ("/workspace/persona/IDENTITY.md", True),
    ("/workspace/governance/AUTONOMY.md", True),   # governance PROSE → theirs
    ("/workspace/operation/report.md", True),
    ("/workspace/inbound/uploads/operator/a.pdf", True),
    ("/workspace/uploads/x.md", True),
    # Carve 1: system/ runtime state → locked.
    ("/workspace/system/_recent_execution.md", False),
    # Carve 2: _*.yaml/_*.json machine-config (read by exact path) → locked.
    ("/workspace/governance/_budget.yaml", False),
    ("/workspace/persona/_principles.yaml", False),
    ("/workspace/operation/_universe.json", False),
    # A non-underscore .yaml is NOT machine-config by our rule → organizable.
    ("/workspace/operation/notes.yaml", True),
])
def test_operator_can_organize(path, ok):
    from services.workspace_paths import operator_can_organize
    assert operator_can_organize(path) is ok


# ── Move / rename scope (corrected) ─────────────────────────────────────────

@pytest.mark.parametrize("src,dst,ok", [
    # constitution prose → operation: now ALLOWED (it's the operator's).
    ("/workspace/constitution/PRECEDENT.md", "/workspace/operation/PRECEDENT.md", True),
    ("/workspace/uploads/x.md", "/workspace/uploads/y.md", True),
    # source in system/: 403.
    ("/workspace/system/_x.md", "/workspace/uploads/x.md", False),
    # source is machine-config: 403 (renaming breaks the reader).
    ("/workspace/governance/_budget.yaml", "/workspace/governance/budget.yaml", False),
    # destination in system/: 403 (can't move INTO runtime state).
    ("/workspace/uploads/a.pdf", "/workspace/system/a.pdf", False),
    # destination would become machine-config: 403.
    ("/workspace/uploads/a.md", "/workspace/persona/_a.yaml", False),
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


# ── Restore scope (corrected) ───────────────────────────────────────────────

def test_restore_rejects_system_path():
    from routes.documents import restore_document, RestoreRequest
    with pytest.raises(HTTPException) as ei:
        _run(restore_document(RestoreRequest(path="/workspace/system/_x.md"), _Auth()))
    assert ei.value.status_code == 403


def test_restore_rejects_machine_config():
    from routes.documents import restore_document, RestoreRequest
    with pytest.raises(HTTPException) as ei:
        _run(restore_document(RestoreRequest(path="/workspace/governance/_budget.yaml"), _Auth()))
    assert ei.value.status_code == 403


# ── Delete scope (corrected) ────────────────────────────────────────────────

def test_delete_rejects_machine_config():
    from routes.documents import delete_document
    with pytest.raises(HTTPException) as ei:
        _run(delete_document(_Auth(), "/workspace/governance/_budget.yaml"))
    assert ei.value.status_code == 403


# ── FE/BE agreement: the carve constants ────────────────────────────────────

def test_operator_lock_is_system_plus_machine_config():
    """The operator's carve is exactly system/ + _*.yaml/_*.json. The FE
    ownership.ts operatorCanOrganize mirrors this — keep them in lockstep."""
    from services.workspace_paths import operator_can_organize, _MACHINE_CONFIG_EXTS
    assert _MACHINE_CONFIG_EXTS == (".yaml", ".yml", ".json")
    # system/ locked; a normal prose root open.
    assert operator_can_organize("/workspace/system/anything.md") is False
    assert operator_can_organize("/workspace/constitution/MANDATE.md") is True
