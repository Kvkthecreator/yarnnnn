"""ADR-293 regression gate — Governance / Operational substrate taxonomy +
uniform AUTONOMY-mode gating + _token_budget.yaml governance file.

Phase 1 invariants:

D1 — Canonical taxonomy: every substrate file is either governance or
     operational. Governance files locked from Reviewer runtime regardless
     of AUTONOMY mode. Operational files Reviewer-writable + AUTONOMY-gated.
D2 — Governance file set: exactly 3 paths (AUTONOMY.md, _autonomy.yaml,
     _token_budget.yaml).
D3 — Lock surface collapses to 1-layer governance-set check.
D4 — should_auto_apply covers both action classes uniformly.
D5 — never_auto extends to support path: prefix.
D6 — _locks.yaml DELETED (no live readers).
D7 — Token budget enforced at scheduler fire boundary.
D14 — Phase 1.d: Reviewer substrate writes apply under autonomous;
      bounded/manual return structured error.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent
REPO_ROOT = API_DIR.parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _file(*parts: str) -> Path:
    return API_DIR.joinpath(*parts)


def _bundle(*parts: str) -> Path:
    return REPO_ROOT.joinpath(
        "docs", "programs", "alpha-trader", "reference-workspace", *parts
    )


# -----------------------------------------------------------------------------
# D2 — Governance file set
# -----------------------------------------------------------------------------

# NOTE (ADR-320): test_default_reviewer_write_locks_is_governance_only DELETED.
# The DEFAULT_REVIEWER_WRITE_LOCKS flat-list collapsed into the five-root
# CALLER_WRITE_POLICY (governance/ locked from the reviewer caller). Coverage moved
# to test_adr320_permission_topology.py::test_governance_locked_from_all_llm_callers.


def test_shared_token_budget_path_constant_exists():
    """D2 invariant (a governance cost-ceiling path constant exists),
    re-homed by ADR-327: GOVERNANCE_TOKEN_BUDGET_PATH → GOVERNANCE_BUDGET_PATH."""
    from services.workspace_paths import GOVERNANCE_BUDGET_PATH
    assert GOVERNANCE_BUDGET_PATH == "governance/_budget.yaml"
    # Retired constant must be gone (Singular Implementation).
    import services.workspace_paths as wp
    assert not hasattr(wp, "GOVERNANCE_TOKEN_BUDGET_PATH")
    assert not hasattr(wp, "GOVERNANCE_PACE_PATH")


# NOTE (ADR-320): test_operational_paths_not_locked DELETED.
# The DEFAULT_REVIEWER_WRITE_LOCKS flat-list collapsed into CALLER_WRITE_POLICY.
# "Operational paths writable by the reviewer" coverage moved to
# test_adr320_permission_topology.py (operation/ writable by every caller).


# -----------------------------------------------------------------------------
# D3 — Lock surface collapse + dead helper deletion
# -----------------------------------------------------------------------------

# NOTE (ADR-320): test_is_path_locked_for_reviewer_collapsed DELETED.
# _is_path_locked_for_reviewer no longer exists — collapsed into the single
# _is_path_locked(caller_class, path) reading CALLER_WRITE_POLICY. The
# "no legacy 4-layer composition" intent is now structurally guaranteed (one
# prefix-policy dict, no workspace_guide/bundle_reader/_locks.yaml reads).


def test_path_zone_locks_helpers_deleted():
    """D3: the dead helper functions get_path_zone_locks and
    get_path_zone_locks_for_workspace must be deleted from
    workspace_guide.py and bundle_reader.py."""
    wg_src = _read(_file("services", "workspace_guide.py"))
    br_src = _read(_file("services", "bundle_reader.py"))
    assert "def get_path_zone_locks(" not in wg_src, (
        "get_path_zone_locks() in workspace_guide.py must be DELETED per ADR-293 D3"
    )
    assert "def get_path_zone_locks_for_workspace(" not in br_src, (
        "get_path_zone_locks_for_workspace() in bundle_reader.py must be "
        "DELETED per ADR-293 D3"
    )


# -----------------------------------------------------------------------------
# D4 — Uniform should_auto_apply gate
# -----------------------------------------------------------------------------

def test_should_auto_apply_exists_with_action_class_branch():
    """D4: should_auto_apply must exist and accept action_class parameter
    covering both 'capital' and 'substrate' branches."""
    from services.review_policy import should_auto_apply
    import inspect
    sig = inspect.signature(should_auto_apply)
    assert "action_class" in sig.parameters, (
        "should_auto_apply must accept action_class parameter per ADR-293 D4"
    )
    # Capital branch — autonomous mode, approve verdict → True
    ok, _ = should_auto_apply(
        autonomy_policy={"delegation": "autonomous"},
        action_class="capital",
        verdict="approve",
    )
    assert ok is True, "autonomous + approve capital should auto-apply"
    # Substrate branch — autonomous mode → True
    ok, _ = should_auto_apply(
        autonomy_policy={"delegation": "autonomous"},
        action_class="substrate",
        substrate_path="constitution/MANDATE.md",
    )
    assert ok is True, "autonomous substrate write should auto-apply"
    # Substrate branch — bounded mode → False (queue)
    ok, reason = should_auto_apply(
        autonomy_policy={"delegation": "bounded", "ceiling_cents": 5000000},
        action_class="substrate",
        substrate_path="constitution/MANDATE.md",
    )
    assert ok is False, "bounded substrate write should NOT auto-apply"
    assert "bounded" in reason.lower(), f"reason should mention bounded: {reason}"
    # Substrate branch — manual mode → False
    ok, _ = should_auto_apply(
        autonomy_policy={"delegation": "manual"},
        action_class="substrate",
        substrate_path="constitution/MANDATE.md",
    )
    assert ok is False, "manual substrate write should NOT auto-apply"


def test_should_auto_execute_verdict_renamed():
    """D4: the old name should not exist as a live exported function."""
    import services.review_policy as mod
    assert not hasattr(mod, "should_auto_execute_verdict"), (
        "should_auto_execute_verdict must be renamed to should_auto_apply per ADR-293 D4"
    )


# -----------------------------------------------------------------------------
# D5 — never_auto path: prefix
# -----------------------------------------------------------------------------

def test_never_auto_action_type_match():
    """D5 backward-compat: action_type substring matches still work."""
    from services.review_policy import should_auto_apply
    ok, reason = should_auto_apply(
        autonomy_policy={
            "delegation": "autonomous",
            "never_auto": ["close_position_market"],
        },
        action_class="capital",
        verdict="approve",
        action_type="close_position_market",
    )
    assert ok is False, "never_auto action-type match should block"
    assert "never_auto" in reason


def test_never_auto_substrate_path_match():
    """D5: new `path:` prefix supports substrate-path patterns."""
    from services.review_policy import should_auto_apply
    # Exact path match
    ok, reason = should_auto_apply(
        autonomy_policy={
            "delegation": "autonomous",
            "never_auto": ["path:operation/trading/_universe.yaml"],
        },
        action_class="substrate",
        substrate_path="operation/trading/_universe.yaml",
    )
    assert ok is False, "never_auto path-match should block substrate write"
    assert "never_auto" in reason
    # Directory-prefix match (ADR-320: domain context relocated context/ → operation/)
    ok, _ = should_auto_apply(
        autonomy_policy={
            "delegation": "autonomous",
            "never_auto": ["path:operation/trading"],
        },
        action_class="substrate",
        substrate_path="operation/trading/_operator_profile.md",
    )
    assert ok is False, "never_auto path-prefix should block descendant paths"


# -----------------------------------------------------------------------------
# D6 — _locks.yaml deletion (no live readers)
# -----------------------------------------------------------------------------

# NOTE (ADR-320): test_locks_yaml_not_read_by_lock_function DELETED.
# _is_path_locked_for_reviewer no longer exists; the collapsed
# _is_path_locked(caller_class, path) is a pure prefix check over
# CALLER_WRITE_POLICY with no file reads at all. The "no legacy _locks.yaml read"
# intent is structurally satisfied.


# -----------------------------------------------------------------------------
# D7 — Token budget governance + scheduler enforcement
# -----------------------------------------------------------------------------

def test_token_budget_module_loads_with_fallback():
    """D7 invariant (a cost-governance module with kernel-default fallback
    exists), re-homed by ADR-327: token_budget → budget. Detailed
    loader coverage lives in test_adr327_phase1.py; here we assert the
    module exists with the budget shape and the old module is gone."""
    from services.budget import Budget, DEFAULT_BUDGET_YAML, load_budget  # noqa: F401
    assert hasattr(Budget, "min_interval_for")
    assert "amount_usd" in DEFAULT_BUDGET_YAML
    # Retired module must be gone (Singular Implementation).
    import importlib
    try:
        importlib.import_module("services.token_budget")
        raise AssertionError("services.token_budget must be deleted per ADR-327")
    except ImportError:
        pass


def test_scheduler_imports_token_budget_module():
    """D7 invariant (cost governance gate on the dispatch path) PRESERVED,
    re-homed by ADR-327: token_budget → budget. wake.py imports
    services.budget (load_budget + window_spend); the daily-ceiling +
    judgment-cap concepts retire into the dollar window budget."""
    src = _read(_file("services", "wake.py"))
    assert "from services.budget import" in src, (
        "wake.py must import the budget module per ADR-327 (supersedes ADR-293 D7 token_budget)"
    )
    assert "load_budget" in src
    assert "window_spend" in src
    assert "seconds_since_last_fire" in src
    # Retired concepts must be gone.
    assert "load_token_budget" not in src
    assert "count_judgment_fires_today" not in src
    assert "DAILY_SPEND_CEILING_USD" not in src


def test_workspace_init_seeds_token_budget():
    """D7 invariant (kernel-universal cost-governance scaffold) PRESERVED,
    re-homed by ADR-327: workspace_init seeds _budget.yaml (collapsed
    _token_budget + _pace)."""
    src = _read(_file("services", "workspace_init.py"))
    assert "GOVERNANCE_BUDGET_PATH" in src, (
        "workspace_init.py must seed _budget.yaml per ADR-327 (supersedes ADR-293 D7)"
    )
    assert "DEFAULT_BUDGET_YAML" in src
    assert "GOVERNANCE_TOKEN_BUDGET_PATH" not in src


# -----------------------------------------------------------------------------
# D14 — Phase 1.d Reviewer substrate write gating
# -----------------------------------------------------------------------------

def test_substrate_autonomy_gate_lives_at_permission_layer():
    """ADR-293 D14's substrate gate (should_auto_apply, action_class='substrate')
    is PRESERVED but RELOCATED by ADR-307: it moved out of handle_write_file
    (which is now the pure execution arm) UP into the uniform permission gate
    (services/primitives/permission.py, consulted by execute_primitive). The
    bounded/manual outcome changed from a hard error to QUEUE (ADR-307 D4)."""
    src = _read(_file("services", "primitives", "permission.py"))
    assert "should_auto_apply" in src, (
        "the permission gate must invoke should_auto_apply for Reviewer "
        "substrate writes (relocated from handle_write_file per ADR-307)"
    )
    assert 'action_class="substrate"' in src, (
        "the permission gate must specify action_class='substrate'"
    )
    # ADR-307: the inline error is gone; bounded/manual now QUEUEs.
    wf_src = _read(_file("services", "primitives", "workspace.py"))
    assert "substrate_write_requires_autonomous" not in wf_src, (
        "handle_write_file must NOT carry the inline gate/error any longer "
        "(moved to the permission layer; bounded/manual now QUEUEs per ADR-307)"
    )


# NOTE (ADR-320): test_governance_lock_is_deny_tier_at_permission_layer DELETED.
# The permission gate no longer consults the per-reviewer helper by name; it routes
# through the collapsed _is_path_locked(caller_class, path). The DENY-tier governance
# lock is covered by test_adr320_permission_topology.py
# (test_governance_locked_from_all_llm_callers).


# -----------------------------------------------------------------------------
# Bundle alpha-trader carries the token_budget governance file
# -----------------------------------------------------------------------------

def test_cockpit_awareness_prompt_envelope_aligned_with_adr293():
    """ADR-293 write-taxonomy alignment, ADR-323 form. ADR-323 DELETED
    `_OPERATING_POSTURE` (and `build_filesystem_block`) from cockpit_awareness —
    per Derived Principle 22 the write-authority posture is rules-of-judgment +
    interface, not system-prompt prose. The ADR-293 concerns this gate guarded
    are now satisfied by deletion + relocation:
      - stale `_locks.yaml` / operator-authorship references → absent (block gone).
      - the write boundary (governance/ + system/ locked; everything else
        author-able) → migrated to the MINIMAL PERSONA FRAME (reviewer_agent.py),
        in its topological ADR-320 form (which supersedes ADR-293's flat 3-file
        taxonomy).
    """
    src = _read(_file("agents", "cockpit_awareness.py"))

    # The deleted carriers must stay deleted (ADR-323).
    assert "_OPERATING_POSTURE = " not in src and "def build_filesystem_block" not in src, (
        "cockpit_awareness.py must not re-add _OPERATING_POSTURE / "
        "build_filesystem_block (ADR-323 — DP22)."
    )
    # Stale lock-policy references stay absent (ADR-293 D6 + ADR-323).
    assert "operator-authored access policy" not in src
    assert "operator-authorship territory" not in src
    assert "Governance / Operational taxonomy" not in src, (
        "The ADR-293 flat taxonomy prose is gone — superseded by ADR-320 "
        "topology, which lives in the minimal frame, not cockpit_awareness."
    )
    # The surviving tool block still frames not-in-surface as tool-curation.
    assert "curated tool surface" in src.lower() or "curated for the" in src.lower()

    # The write boundary now lives in the minimal persona frame, topological form.
    frame_src = _read(_file("agents", "reviewer_agent.py"))
    assert "EXCEPT two roots" in frame_src and "governance/" in frame_src and "system/" in frame_src, (
        "The write boundary (author everything EXCEPT governance/ + system/) must "
        "live in the minimal persona frame post-ADR-323 (migrated up from the "
        "deleted filesystem block, in ADR-320 topological form)."
    )


def test_reviewer_agent_invoke_docstring_aligned():
    """ADR-293 Work 1 follow-up: invoke_reviewer's docstring previously cited
    `operator-authored _locks.yaml` as part of the safety story. Post-Work-1
    rewritten to cite 3-file governance lock + uniform AUTONOMY gate."""
    src = _read(_file("agents", "reviewer_agent.py"))
    # Find the invoke_reviewer docstring region
    idx = src.find("async def invoke_reviewer")
    assert idx > -1
    docstring_region = src[idx:idx + 3000]
    assert "operator-authored _locks.yaml" not in docstring_region, (
        "invoke_reviewer docstring must not cite `_locks.yaml` as a live "
        "safety-story component (deleted per ADR-293 D6)."
    )
    # ADR-320 made the lock root-based (governance/ root, not a 3-file
    # enumeration); ADR-327 collapsed _token_budget + _pace into _budget.yaml.
    assert "root-based governance lock" in docstring_region, (
        "invoke_reviewer docstring must reference the root-based governance "
        "lock (ADR-320 + ADR-327) in its safety story."
    )


def test_alpha_trader_bundle_ships_token_budget():
    """Bundle reference-workspace MUST include _budget.yaml (ADR-327,
    collapsed _token_budget + _pace) so program-activated workspaces
    inherit it via Phase 5 fork."""
    bundle_path = _bundle("governance", "_budget.yaml")
    assert bundle_path.exists(), (
        f"alpha-trader bundle must ship _budget.yaml at {bundle_path} "
        f"per ADR-327 (supersedes ADR-293 D7 _token_budget.yaml)"
    )
    content = _read(bundle_path)
    assert "amount_usd:" in content
    assert "window:" in content
    assert "min_interval_between_recurrence_fires_seconds:" in content
    assert "tier: canon" in content  # bundle frontmatter discipline
    # Retired bundle file must be gone.
    assert not _bundle("governance", "_token_budget.yaml").exists()


# -----------------------------------------------------------------------------
# Test runner
# -----------------------------------------------------------------------------

def main() -> int:
    # NOTE (ADR-320): the DEFAULT_REVIEWER_WRITE_LOCKS-based governance-set tests
    # (D2 lock-set, D1/D3 operational-not-locked, D3 collapse, D6 _locks.yaml read,
    # D2 deny-tier) were DELETED — the flat-list lock model collapsed into the
    # five-root CALLER_WRITE_POLICY; coverage moved to
    # test_adr320_permission_topology.py.
    tests = [
        ("D2→ADR-327: GOVERNANCE_BUDGET_PATH constant", test_shared_token_budget_path_constant_exists),
        ("D3: path_zone_locks helpers deleted", test_path_zone_locks_helpers_deleted),
        ("D4: should_auto_apply with action_class", test_should_auto_apply_exists_with_action_class_branch),
        ("D4: should_auto_execute_verdict renamed", test_should_auto_execute_verdict_renamed),
        ("D5: never_auto action-type match", test_never_auto_action_type_match),
        ("D5: never_auto path: prefix match", test_never_auto_substrate_path_match),
        ("D7→ADR-327: budget module + old gone", test_token_budget_module_loads_with_fallback),
        ("D7→ADR-327: wake.py imports budget", test_scheduler_imports_token_budget_module),
        ("D7→ADR-327: workspace_init seeds _budget.yaml", test_workspace_init_seeds_token_budget),
        ("D14: substrate autonomy gate at permission layer", test_substrate_autonomy_gate_lives_at_permission_layer),
        ("Bundle alpha-trader ships _budget.yaml (ADR-327)", test_alpha_trader_bundle_ships_token_budget),
        # Work 1 follow-up — prompt envelope alignment
        ("Work 1: cockpit_awareness.py aligned with ADR-293", test_cockpit_awareness_prompt_envelope_aligned_with_adr293),
        ("Work 1: invoke_reviewer docstring aligned", test_reviewer_agent_invoke_docstring_aligned),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  ✓ {name}")
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {name}")
            print(f"      {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ {name} — unexpected error")
            print(f"      {type(e).__name__}: {e}")
            failed += 1

    print()
    print(f"ADR-293 regression gate: {passed}/{passed+failed} assertions passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
