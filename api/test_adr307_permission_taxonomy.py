"""ADR-307 regression gate — Unified Permission Taxonomy.

Phase 1 (this commit): the uniform gate exists at execute_primitive; every
read/narration primitive is declared read_only; the consequential default is
fail-closed; behavior is preserved (capital queues at dispatch, substrate
errors inside handle_write_file — unchanged this phase).

Later phases extend this file:
  - Phase 2: substrate writes QUEUE (not error); workspace.write_file action_type.
  - Phase 3: Schedule/RuntimeDispatch/etc. pass the gate.
"""

from __future__ import annotations

import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


# ---------------------------------------------------------------------------
# D1 — uniform gate exists at the single chokepoint
# ---------------------------------------------------------------------------

def test_permission_module_exists_with_decision_enum():
    from services.primitives.permission import PermissionDecision, resolve_permission  # noqa: F401

    assert PermissionDecision.APPLY.value == "apply"
    assert PermissionDecision.QUEUE.value == "queue"
    assert PermissionDecision.DENY.value == "deny"


def test_execute_primitive_consults_the_gate():
    """The single execute-by-name chokepoint must call resolve_permission
    before dispatching to a handler (ADR-307 D1 — uniform gate, above all
    primitives)."""
    import inspect
    from services.primitives import registry

    src = inspect.getsource(registry.execute_primitive)
    assert "resolve_permission" in src, (
        "execute_primitive must consult resolve_permission (the uniform gate) "
        "before dispatching — ADR-307 D1"
    )


# ---------------------------------------------------------------------------
# D2 — read_only declared per primitive, fail-closed
# ---------------------------------------------------------------------------

def test_every_read_primitive_is_read_only():
    """Reads + narration must be declared read_only (never gate, never queue)."""
    from services.primitives.permission import is_read_only

    must_be_read_only = [
        # entity reads
        "LookupEntity", "ListEntities", "SearchEntities",
        # file reads
        "ReadFile", "ListFiles", "SearchFiles", "ReadAgentFile",
        # revision reads
        "ListRevisions", "ReadRevision", "DiffRevisions",
        # semantic-query read
        "QueryKnowledge",
        # introspection
        "GetSystemState", "DiscoverAgents", "list_integrations",
        # external read
        "WebSearch",
        # narration
        "Clarify", "ReturnVerdict",
    ]
    for name in must_be_read_only:
        assert is_read_only(name), (
            f"{name} must be declared read_only per ADR-307 D2 "
            "(reads/narration never gate)"
        )


def test_consequential_default_is_fail_closed():
    """A primitive NOT declared read_only is consequential (Claude-Code
    'assume writes' default, ADR-307 D2). Unknown names are consequential."""
    from services.primitives.permission import is_read_only

    for name in ("WriteFile", "Schedule", "RuntimeDispatch", "DispatchSpecialist",
                 "ManageHook", "ManageAgent", "ManageDomains", "ProposeAction",
                 "ExecuteProposal", "FireInvocation", "InferContext",
                 "InferWorkspace", "Compose", "RepurposeOutput", "EditEntity",
                 "SyncPlatformState", "__nonexistent_primitive__"):
        assert not is_read_only(name), (
            f"{name} must be treated as consequential (fail-closed) per ADR-307 D2"
        )


def test_read_only_set_partitions_the_handler_registry():
    """Every primitive in HANDLERS is classified — read_only XOR consequential.
    No primitive is unclassified (the partition is total)."""
    from services.primitives.registry import HANDLERS
    from services.primitives.permission import is_read_only

    # Pure structural check: is_read_only is total over all handler names
    # (returns a bool for every name; consequential is the complement).
    for name in HANDLERS:
        decision = is_read_only(name)
        assert isinstance(decision, bool), f"{name} not classifiable"


# ---------------------------------------------------------------------------
# action_class mapping (ADR-307 D5 / ADR-293 D4)
# ---------------------------------------------------------------------------

def test_action_class_mapping():
    from services.primitives.permission import action_class_for

    assert action_class_for("ExecuteProposal") == "capital"
    # Everything consequential-but-not-capital is substrate.
    for name in ("WriteFile", "Schedule", "RuntimeDispatch", "ManageHook"):
        assert action_class_for(name) == "substrate", (
            f"{name} should map to substrate action_class"
        )


# ---------------------------------------------------------------------------
# Phase 1 behavior-preservation: read-only resolves APPLY; non-reviewer APPLY
# ---------------------------------------------------------------------------

def test_read_only_resolves_apply():
    import asyncio
    from types import SimpleNamespace
    from services.primitives.permission import resolve_permission, PermissionDecision

    auth = SimpleNamespace(reviewer_caller=True, user_id="u", client=None)
    decision, _ = asyncio.run(resolve_permission(auth, "ReadFile", {}))
    assert decision == PermissionDecision.APPLY


def test_non_reviewer_caller_resolves_apply():
    import asyncio
    from types import SimpleNamespace
    from services.primitives.permission import resolve_permission, PermissionDecision

    auth = SimpleNamespace(reviewer_caller=False, user_id="u", client=None)
    decision, reason = asyncio.run(resolve_permission(auth, "WriteFile", {}))
    assert decision == PermissionDecision.APPLY
    assert reason == "non_reviewer_caller"


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
