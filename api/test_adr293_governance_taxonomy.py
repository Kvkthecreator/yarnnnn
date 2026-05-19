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

def test_default_reviewer_write_locks_is_governance_only():
    """D2 + D3: exactly three governance paths; no operator-canon
    operational paths in the lock set."""
    from services.workspace_paths import (
        DEFAULT_REVIEWER_WRITE_LOCKS,
        SHARED_AUTONOMY_PATH,
        SHARED_AUTONOMY_YAML_PATH,
        SHARED_TOKEN_BUDGET_PATH,
    )
    assert set(DEFAULT_REVIEWER_WRITE_LOCKS) == {
        SHARED_AUTONOMY_PATH,
        SHARED_AUTONOMY_YAML_PATH,
        SHARED_TOKEN_BUDGET_PATH,
    }, (
        f"DEFAULT_REVIEWER_WRITE_LOCKS must contain exactly the 3 governance "
        f"files per ADR-293 D2. Got: {sorted(DEFAULT_REVIEWER_WRITE_LOCKS)}"
    )


def test_shared_token_budget_path_constant_exists():
    """D2: SHARED_TOKEN_BUDGET_PATH constant must be exported."""
    from services.workspace_paths import SHARED_TOKEN_BUDGET_PATH
    assert SHARED_TOKEN_BUDGET_PATH == "context/_shared/_token_budget.yaml"


def test_operational_paths_not_locked():
    """D1 + D3: paths that were locked pre-ADR-293 (MANDATE, IDENTITY,
    BRAND, CONVENTIONS, PRECEDENT, _preferences, _locks) MUST NOT appear
    in the governance set. They're operational."""
    from services.workspace_paths import DEFAULT_REVIEWER_WRITE_LOCKS
    must_not_be_locked = {
        "context/_shared/MANDATE.md",
        "context/_shared/IDENTITY.md",
        "context/_shared/BRAND.md",
        "context/_shared/CONVENTIONS.md",
        "context/_shared/PRECEDENT.md",
        "context/_shared/_preferences.yaml",
        "context/_shared/_locks.yaml",  # D6: deleted from governance
    }
    overlap = set(DEFAULT_REVIEWER_WRITE_LOCKS) & must_not_be_locked
    assert not overlap, (
        f"Pre-ADR-293 lock paths must NOT be in the new governance set: "
        f"{sorted(overlap)} (they are operational; Reviewer-writable per D4)"
    )


# -----------------------------------------------------------------------------
# D3 — Lock surface collapse + dead helper deletion
# -----------------------------------------------------------------------------

def test_is_path_locked_for_reviewer_collapsed():
    """D3: the function must NOT reference the old 4-layer composition
    sources (workspace_guide.get_path_zone_locks, bundle_reader.
    get_path_zone_locks_for_workspace, /workspace/_shared/_locks.yaml read).
    """
    src = _read(_file("services", "primitives", "workspace.py"))
    func_start = src.find("async def _is_path_locked_for_reviewer")
    assert func_start > -1, "_is_path_locked_for_reviewer must still exist"
    # Take ~80 lines after func definition as the function body
    func_body = src[func_start:func_start + 4000]
    for legacy in [
        "workspace_guide",
        "get_path_zone_locks",
        "bundle_reader",
        "/workspace/_shared/_locks.yaml",
        "_reviewer_locks_cache",
    ]:
        assert legacy not in func_body, (
            f"_is_path_locked_for_reviewer must not reference legacy "
            f"lock-composition source: {legacy!r}"
        )


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
        substrate_path="context/_shared/MANDATE.md",
    )
    assert ok is True, "autonomous substrate write should auto-apply"
    # Substrate branch — bounded mode → False (queue)
    ok, reason = should_auto_apply(
        autonomy_policy={"delegation": "bounded", "ceiling_cents": 5000000},
        action_class="substrate",
        substrate_path="context/_shared/MANDATE.md",
    )
    assert ok is False, "bounded substrate write should NOT auto-apply"
    assert "bounded" in reason.lower(), f"reason should mention bounded: {reason}"
    # Substrate branch — manual mode → False
    ok, _ = should_auto_apply(
        autonomy_policy={"delegation": "manual"},
        action_class="substrate",
        substrate_path="context/_shared/MANDATE.md",
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
            "never_auto": ["path:context/trading/_universe.yaml"],
        },
        action_class="substrate",
        substrate_path="context/trading/_universe.yaml",
    )
    assert ok is False, "never_auto path-match should block substrate write"
    assert "never_auto" in reason
    # Directory-prefix match
    ok, _ = should_auto_apply(
        autonomy_policy={
            "delegation": "autonomous",
            "never_auto": ["path:context/trading"],
        },
        action_class="substrate",
        substrate_path="context/trading/_operator_profile.md",
    )
    assert ok is False, "never_auto path-prefix should block descendant paths"


# -----------------------------------------------------------------------------
# D6 — _locks.yaml deletion (no live readers)
# -----------------------------------------------------------------------------

def test_locks_yaml_not_read_by_lock_function():
    """D6: _is_path_locked_for_reviewer no longer READS
    /workspace/_shared/_locks.yaml (legacy file-content read deleted).
    Allow historical-context mentions in the function's docstring.
    """
    src = _read(_file("services", "primitives", "workspace.py"))
    func_start = src.find("async def _is_path_locked_for_reviewer")
    func_body = src[func_start:func_start + 4000]
    # The legacy read pattern: querying workspace_files for /workspace/_shared/_locks.yaml
    legacy_read_patterns = [
        '.eq("path", "/workspace/_shared/_locks.yaml")',
        ".eq('path', '/workspace/_shared/_locks.yaml')",
        "yaml.safe_load(content)",  # the old _locks.yaml parser
        "locked_paths",  # field-name read from old _locks.yaml schema
        "unlocked_paths",  # field-name read from old _locks.yaml schema
    ]
    for pat in legacy_read_patterns:
        assert pat not in func_body, (
            f"_is_path_locked_for_reviewer must not contain legacy "
            f"_locks.yaml read-pattern: {pat!r}"
        )


# -----------------------------------------------------------------------------
# D7 — Token budget governance + scheduler enforcement
# -----------------------------------------------------------------------------

def test_token_budget_module_loads_with_fallback():
    """D7: load_token_budget returns kernel defaults when file absent."""
    from services.token_budget import load_token_budget
    from unittest.mock import MagicMock
    # Mock client returning empty result
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    budget = load_token_budget(mock_client, "test-user")
    assert budget.daily_spend_ceiling_usd > 0, "Must have a positive default"
    assert budget.max_judgment_recurrences_per_day > 0
    assert budget.min_interval_between_recurrence_fires_seconds > 0


def test_token_budget_module_parses_workspace_yaml():
    """D7: load_token_budget parses an actual workspace yaml correctly."""
    from services.token_budget import load_token_budget
    from unittest.mock import MagicMock
    yaml_content = """
daily_spend_ceiling_usd: 2.50
max_judgment_recurrences_per_day: 20
min_interval_between_recurrence_fires_seconds: 300
overrides:
  signal-evaluation:
    min_interval_seconds: 900
"""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"content": yaml_content}
    ]
    budget = load_token_budget(mock_client, "test-user")
    assert budget.daily_spend_ceiling_usd == 2.50
    assert budget.max_judgment_recurrences_per_day == 20
    assert budget.min_interval_between_recurrence_fires_seconds == 300
    assert budget.min_interval_for("signal-evaluation") == 900
    assert budget.min_interval_for("some-other-recurrence") == 300


def test_token_budget_default_yaml_schema():
    """D7: DEFAULT_TOKEN_BUDGET_YAML must contain the three required keys."""
    from services.token_budget import DEFAULT_TOKEN_BUDGET_YAML
    assert "daily_spend_ceiling_usd:" in DEFAULT_TOKEN_BUDGET_YAML
    assert "max_judgment_recurrences_per_day:" in DEFAULT_TOKEN_BUDGET_YAML
    assert "min_interval_between_recurrence_fires_seconds:" in DEFAULT_TOKEN_BUDGET_YAML


def test_scheduler_imports_token_budget_module():
    """D7: invocation_dispatcher.py imports and uses load_token_budget,
    not the legacy DAILY_SPEND_CEILING_USD constant from telemetry."""
    src = _read(_file("services", "invocation_dispatcher.py"))
    assert "from services.token_budget import" in src, (
        "invocation_dispatcher.py must import token_budget module per ADR-293 D7"
    )
    assert "load_token_budget" in src
    assert "count_judgment_fires_today" in src
    assert "seconds_since_last_fire" in src
    # Legacy import should be gone
    assert "DAILY_SPEND_CEILING_USD" not in src, (
        "invocation_dispatcher.py must not import legacy DAILY_SPEND_CEILING_USD "
        "(now per-workspace governance per ADR-293 D7)"
    )


def test_workspace_init_seeds_token_budget():
    """D7 + workspace_init Phase 2: kernel-universal scaffold includes
    _token_budget.yaml."""
    src = _read(_file("services", "workspace_init.py"))
    assert "SHARED_TOKEN_BUDGET_PATH" in src, (
        "workspace_init.py must seed _token_budget.yaml per ADR-293 D7"
    )
    assert "DEFAULT_TOKEN_BUDGET_YAML" in src


# -----------------------------------------------------------------------------
# D14 — Phase 1.d Reviewer substrate write gating
# -----------------------------------------------------------------------------

def test_handle_write_file_has_autonomy_gate():
    """D14: handle_write_file routes Reviewer substrate writes through
    should_auto_apply with action_class='substrate'."""
    src = _read(_file("services", "primitives", "workspace.py"))
    # The Reviewer-caller branch must invoke should_auto_apply
    assert "should_auto_apply" in src, (
        "handle_write_file must invoke should_auto_apply for Reviewer "
        "substrate writes per ADR-293 D14"
    )
    assert 'action_class="substrate"' in src, (
        "handle_write_file must specify action_class='substrate' for "
        "Reviewer writes per ADR-293 D14"
    )
    # The structured error code per D14
    assert "substrate_write_requires_autonomous" in src, (
        "handle_write_file must return structured error "
        "substrate_write_requires_autonomous when AUTONOMY blocks the write"
    )


def test_handle_write_file_governance_error_distinct():
    """D14: governance-locked rejection uses governance_locked error code,
    distinct from substrate_write_requires_autonomous (D14 operational gate)."""
    src = _read(_file("services", "primitives", "workspace.py"))
    assert "governance_locked" in src, (
        "handle_write_file must return governance_locked error for the "
        "3-file governance set per ADR-293 D2"
    )


# -----------------------------------------------------------------------------
# Bundle alpha-trader carries the token_budget governance file
# -----------------------------------------------------------------------------

def test_alpha_trader_bundle_ships_token_budget():
    """Bundle reference-workspace MUST include _token_budget.yaml so
    program-activated workspaces inherit it via Phase 5 fork."""
    bundle_path = _bundle("context", "_shared", "_token_budget.yaml")
    assert bundle_path.exists(), (
        f"alpha-trader bundle must ship _token_budget.yaml at {bundle_path} "
        f"per ADR-293 D7"
    )
    content = _read(bundle_path)
    assert "daily_spend_ceiling_usd:" in content
    assert "max_judgment_recurrences_per_day:" in content
    assert "min_interval_between_recurrence_fires_seconds:" in content
    assert "tier: canon" in content  # bundle frontmatter discipline


# -----------------------------------------------------------------------------
# Test runner
# -----------------------------------------------------------------------------

def main() -> int:
    tests = [
        ("D2: governance set is exactly 3 paths", test_default_reviewer_write_locks_is_governance_only),
        ("D2: SHARED_TOKEN_BUDGET_PATH constant", test_shared_token_budget_path_constant_exists),
        ("D1/D3: operational paths not locked", test_operational_paths_not_locked),
        ("D3: _is_path_locked_for_reviewer collapsed", test_is_path_locked_for_reviewer_collapsed),
        ("D3: path_zone_locks helpers deleted", test_path_zone_locks_helpers_deleted),
        ("D4: should_auto_apply with action_class", test_should_auto_apply_exists_with_action_class_branch),
        ("D4: should_auto_execute_verdict renamed", test_should_auto_execute_verdict_renamed),
        ("D5: never_auto action-type match", test_never_auto_action_type_match),
        ("D5: never_auto path: prefix match", test_never_auto_substrate_path_match),
        ("D6: _locks.yaml not read", test_locks_yaml_not_read_by_lock_function),
        ("D7: token_budget fallback to kernel defaults", test_token_budget_module_loads_with_fallback),
        ("D7: token_budget parses workspace yaml", test_token_budget_module_parses_workspace_yaml),
        ("D7: DEFAULT_TOKEN_BUDGET_YAML schema", test_token_budget_default_yaml_schema),
        ("D7: scheduler imports token_budget", test_scheduler_imports_token_budget_module),
        ("D7: workspace_init seeds _token_budget.yaml", test_workspace_init_seeds_token_budget),
        ("D14: handle_write_file has AUTONOMY gate", test_handle_write_file_has_autonomy_gate),
        ("D14: governance_locked distinct from substrate gate", test_handle_write_file_governance_error_distinct),
        ("Bundle alpha-trader ships token_budget", test_alpha_trader_bundle_ships_token_budget),
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
