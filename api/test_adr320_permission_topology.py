"""Regression gate — ADR-320: five-root workspace permission topology.

The SINGULAR home for permission-topology assertions. Supersedes the
old-mechanism tests in:
  - test_adr293_governance_taxonomy.py (DEFAULT_FREDDIE_WRITE_LOCKS flat-list,
    _is_path_locked_for_reviewer)
  - test_adr310_mcp_write_gate.py (_is_path_locked_for_mcp,
    DEFAULT_MCP_WRITE_LOCK_PREFIXES)
  - test_adr280_phase1.py path_zone_locks / 4-layer composition
The behavioral intent those encoded (governance locked from the seat;
operational writable; MCP locked from operator-canon) is re-asserted here
against the new topology.

Proves:
  1. The five roots exist as constants; context/_shared/ + review/ + memory/
     are gone from workspace_paths.
  2. CALLER_WRITE_POLICY derives every (caller_class, root) cell with no
     filename — the access(2) property.
  3. The two old lock functions are deleted; one _is_path_locked survives.
  4. governance/ locked from reviewer/mcp/agent; constitution/ persona/ locked
     from mcp/agent but writable by reviewer; operation/ writable by all;
     system/ locked from everyone but system.
  5. constitution/ holds NO IDENTITY (operator-identity collapse → persona/).

Run: cd api && python -m pytest test_adr320_permission_topology.py -q
"""

import pathlib


WS_PATHS = pathlib.Path(__file__).parent / "services" / "workspace_paths.py"
WORKSPACE_PY = pathlib.Path(__file__).parent / "services" / "primitives" / "workspace.py"
PERMISSION_PY = pathlib.Path(__file__).parent / "services" / "primitives" / "permission.py"


# ---------------------------------------------------------------------------
# 1. Five roots exist; legacy roots gone
# ---------------------------------------------------------------------------

def test_five_root_constants_exist():
    from services import workspace_paths as wp
    assert wp.GOVERNANCE_ROOT == "governance/"
    assert wp.CONSTITUTION_ROOT == "constitution/"
    assert wp.PERSONA_ROOT == "persona/"
    assert wp.OPERATION_ROOT == "operation/"
    assert wp.SYSTEM_ROOT == "system/"


def test_legacy_constants_deleted():
    """SHARED_* / MEMORY_* / REVIEW_* / DEFAULT_*_LOCKS are gone (singular impl)."""
    from services import workspace_paths as wp
    for dead in (
        "SHARED_MANDATE_PATH", "SHARED_IDENTITY_PATH", "SHARED_AUTONOMY_PATH",
        "MEMORY_AWARENESS_PATH", "REVIEW_IDENTITY_PATH", "REVIEW_PRINCIPLES_PATH",
        "DEFAULT_FREDDIE_WRITE_LOCKS", "DEFAULT_MCP_WRITE_LOCK_PREFIXES",
    ):
        assert not hasattr(wp, dead), f"legacy constant {dead} must be deleted"


def test_governance_paths_under_governance_root():
    # ADR-366: governance/ is the GRANT only (authority + spend). _preferences +
    # _expected_output moved to contract/ (mode-governed). _token_budget/_pace
    # were deleted by ADR-327.
    from services import workspace_paths as wp
    for p in (wp.GOVERNANCE_AUTONOMY_PATH, wp.GOVERNANCE_AUTONOMY_YAML_PATH,
              wp.GOVERNANCE_BUDGET_PATH):
        assert p.startswith("governance/"), p


def test_constitution_is_pure_intent_no_identity():
    """ADR-320 operator-identity collapse: constitution = MANDATE + PRECEDENT only."""
    from services import workspace_paths as wp
    assert wp.CONSTITUTION_MANDATE_PATH == "constitution/MANDATE.md"
    assert wp.CONSTITUTION_PRECEDENT_PATH == "constitution/PRECEDENT.md"
    assert not hasattr(wp, "CONSTITUTION_IDENTITY_PATH"), \
        "operator identity collapsed into persona/IDENTITY.md — no constitution IDENTITY"
    assert set(wp.CONSTITUTION_FILES) == {wp.CONSTITUTION_MANDATE_PATH, wp.CONSTITUTION_PRECEDENT_PATH}


def test_persona_identity_is_singular_reasoning_character():
    from services import workspace_paths as wp
    assert wp.PERSONA_IDENTITY_PATH == "persona/IDENTITY.md"
    assert wp.PERSONA_PRINCIPLES_PATH == "persona/principles.md"
    # the legacy review/ + context/_shared/ IDENTITY both collapse here
    for f in wp.PERSONA_FILES:
        assert f.startswith("persona/"), f


def test_system_paths_under_system_root():
    from services import workspace_paths as wp
    for p in (wp.SYSTEM_AWARENESS_PATH, wp.SYSTEM_PLAYBOOK_PATH,
              wp.SYSTEM_NOTES_PATH, wp.SYSTEM_SCHEDULE_INDEX_PATH):
        assert p.startswith("system/"), p


# ---------------------------------------------------------------------------
# 2 + 4. CALLER_WRITE_POLICY derives every cell — the access(2) property
# ---------------------------------------------------------------------------

def _locked(caller, path):
    from services.primitives.workspace import _is_path_locked
    return _is_path_locked(caller, path)


def test_governance_locked_from_all_llm_callers():
    # ADR-366: governance/ = the GRANT (authority + spend) — locked from every
    # LLM caller, every mode. A grant the grantee can rewrite is not a grant.
    for caller in ("reviewer", "mcp", "agent"):
        assert _locked(caller, "governance/AUTONOMY.md"), caller
        assert _locked(caller, "governance/_autonomy.yaml"), caller
        assert _locked(caller, "/workspace/governance/_budget.yaml"), caller


def test_constitution_writable_by_reviewer_locked_from_mcp_and_agent():
    assert not _locked("reviewer", "constitution/MANDATE.md")
    assert not _locked("reviewer", "constitution/PRECEDENT.md")
    assert _locked("mcp", "constitution/MANDATE.md")
    assert _locked("agent", "constitution/MANDATE.md")


def test_persona_writable_by_reviewer_locked_from_mcp_and_agent():
    assert not _locked("reviewer", "persona/IDENTITY.md")
    assert not _locked("reviewer", "persona/principles.md")
    assert not _locked("reviewer", "persona/standing_intent.md")
    assert _locked("mcp", "persona/IDENTITY.md")
    assert _locked("agent", "persona/principles.md")


def test_operation_writable_by_all():
    # ADR-432 D1c: operation/BRAND.md retired — use CONVENTIONS.md as the loose
    # operation/-root example (the claim is about the root's topology, not the file).
    for caller in ("reviewer", "mcp", "agent", "operator", "system"):
        assert not _locked(caller, "operation/CONVENTIONS.md"), caller
        assert not _locked(caller, "operation/trading/_risk.md"), caller
        assert not _locked(caller, "operation/reports/x/output.md"), caller


def test_system_locked_from_non_system_callers():
    for caller in ("reviewer", "mcp", "agent", "operator"):
        assert _locked(caller, "system/awareness.md"), caller
    assert not _locked("system", "system/awareness.md")


def test_operator_writes_everything_except_system():
    assert not _locked("operator", "governance/AUTONOMY.md")
    assert not _locked("operator", "constitution/MANDATE.md")
    assert not _locked("operator", "persona/IDENTITY.md")
    assert not _locked("operator", "operation/CONVENTIONS.md")  # ADR-432 D1c: was BRAND.md
    assert _locked("operator", "system/notes.md")


def test_no_filename_in_policy():
    """The access(2) property: CALLER_WRITE_POLICY contains only root prefixes."""
    from services.workspace_paths import CALLER_WRITE_POLICY
    for caller, prefixes in CALLER_WRITE_POLICY.items():
        for p in prefixes:
            assert p.endswith("/") and p.count("/") == 1, \
                f"{caller}: {p!r} is not a bare root prefix — no filenames in the gate"


# ---------------------------------------------------------------------------
# 3. The two old lock functions are deleted; one survives
# ---------------------------------------------------------------------------

def test_old_lock_functions_deleted_one_survives():
    src = WORKSPACE_PY.read_text()
    assert "def _is_path_locked(" in src, "the unified gate must exist"
    assert "async def _is_path_locked_for_reviewer" not in src, \
        "legacy reviewer lock fn must be deleted"
    assert "def _is_path_locked_for_mcp" not in src, \
        "legacy mcp lock fn must be deleted"


def test_permission_gate_consults_unified_lock():
    src = PERMISSION_PY.read_text()
    # ADR-373 (2026-06-29): the gate now consults the GRANT-AWARE wrapper
    # `_is_path_locked_for_principal`, which resolves the caller's per-principal
    # grant and falls back to the unified `_is_path_locked` class default. The
    # intent is unchanged — ONE unified lock consult, the two legacy lock
    # functions stay deleted.
    assert "_is_path_locked_for_principal(" in src, \
        "the gate must consult the grant-aware unified lock (ADR-373)"
    assert "_is_path_locked_for_reviewer" not in src
    assert "_is_path_locked_for_mcp" not in src
