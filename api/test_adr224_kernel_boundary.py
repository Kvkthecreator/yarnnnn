"""ADR-224 — Kernel/Program Boundary Refactor — boundary enforcement tests.

These tests assert that program-specific templates (trading-*, portfolio-*,
revenue-*, customers/, etc.) do NOT live in the kernel registries. They live
in program bundle MANIFEST.yaml files and are surfaced via bundle_reader.

If a future change re-introduces a program-specific entry into a kernel
registry, these tests fail loudly. That is the regression guard the
boundary needs.

The positive tests verify that bundle-sourced templates remain reachable
through the kernel-side helper APIs (get_task_type, get_directory,
_resolve_capability) — the fallback contract from ADR-224 §2.
"""

import sys
from pathlib import Path

# Ensure the api/ directory is on sys.path so `services.*` imports resolve
# regardless of where pytest is invoked from.
_API_ROOT = Path(__file__).resolve().parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))


# =============================================================================
# Negative tests — kernel registries must NOT contain program-specific entries
# =============================================================================

def test_kernel_task_types_have_no_program_residue():
    """ADR-224 §1: revenue-report / trading-signal / portfolio-review live in
    program bundle MANIFEST.yaml files, not in kernel TASK_TYPES."""
    from services.task_types import TASK_TYPES
    program_keys = {"trading-signal", "portfolio-review", "revenue-report"}
    leaked = program_keys & set(TASK_TYPES.keys())
    assert not leaked, (
        f"Program-specific TASK_TYPES leaked into kernel: {leaked}. "
        f"Per ADR-224, these must live in program bundle MANIFEST.yaml."
    )


def test_kernel_directories_have_no_program_residue():
    """ADR-224 §1: trading / portfolio / customers / revenue context domains
    live in program bundle MANIFEST.yaml files, not in kernel
    WORKSPACE_DIRECTORIES."""
    from services.directory_registry import WORKSPACE_DIRECTORIES
    program_keys = {"trading", "portfolio", "customers", "revenue"}
    leaked = program_keys & set(WORKSPACE_DIRECTORIES.keys())
    assert not leaked, (
        f"Program-specific directories leaked into kernel: {leaked}. "
        f"Per ADR-224, these must live in program bundle MANIFEST.yaml."
    )


def test_kernel_capabilities_have_no_program_residue():
    """ADR-224 §1: read/write_trading and read/write_commerce are
    program-specific (oracle-shape-bound) and live in program bundle
    MANIFEST.yaml files. read/write_slack, read/write_notion, read_github
    STAY in kernel — they are platform-integration capabilities, not
    program-specific."""
    from services.orchestration import CAPABILITIES
    program_keys = {
        "read_trading", "write_trading",
        "read_commerce", "write_commerce",
    }
    leaked = program_keys & set(CAPABILITIES.keys())
    assert not leaked, (
        f"Program-specific capabilities leaked into kernel: {leaked}. "
        f"Per ADR-224 §1, these must live in program bundle MANIFEST.yaml."
    )

    # Sanity: platform-integration capabilities DO stay in kernel
    platform_kept = {"read_slack", "write_slack", "read_notion",
                     "write_notion", "read_github"}
    missing = platform_kept - set(CAPABILITIES.keys())
    assert not missing, (
        f"Platform-integration capabilities missing from kernel: {missing}. "
        f"Per ADR-224 §1, these stay kernel-side."
    )


# =============================================================================
# Positive tests — bundle templates surface via kernel-side helpers
# =============================================================================

def test_alpha_trader_bundle_supplies_trading_signal_template():
    """ADR-224 §2: get_task_type('trading-signal') falls through to active
    bundles when the kernel registry doesn't have the key. alpha-trader's
    MANIFEST.yaml declares the template."""
    from services.task_types import get_task_type
    tt = get_task_type("trading-signal")
    assert tt is not None, "trading-signal not reachable through bundle fallback"
    assert tt.get("_program_slug") == "alpha-trader"
    assert tt.get("output_kind") == "produces_deliverable"
    assert tt.get("context_reads") == ["trading", "portfolio"]
    # Process block built from the `instruction` field
    process = tt.get("process", [])
    assert len(process) == 1
    assert "WriteFile: update /workspace/context/trading" in process[0]["instruction"]


def test_alpha_trader_bundle_supplies_portfolio_review_template():
    from services.task_types import get_task_type
    tt = get_task_type("portfolio-review")
    assert tt is not None, "portfolio-review not reachable through bundle fallback"
    assert tt.get("_program_slug") == "alpha-trader"
    # Page structure preserved from kernel pre-deletion
    pages = tt.get("page_structure") or []
    assert any(p.get("kind") == "trend-chart" for p in pages)


def test_alpha_trader_bundle_supplies_trading_directory():
    """ADR-224 §2: get_directory('trading') falls through to bundles."""
    from services.directory_registry import get_directory, get_synthesis_content, get_authored_substrate
    d = get_directory("trading")
    assert d is not None, "trading directory not reachable through bundle fallback"
    assert d.get("_program_slug") == "alpha-trader"
    assert d.get("type") == "context"
    # Authored substrate (ADR-220) preserved
    authored = get_authored_substrate("trading")
    assert "_operator_profile.md" in authored
    assert "_risk.md" in authored
    assert "_performance.md" in authored
    # Synthesis preserved
    syn = get_synthesis_content("trading")
    assert syn is not None
    assert syn[0] == "overview.md"


def test_alpha_trader_bundle_supplies_read_trading_capability():
    """ADR-224 §2: capability resolution falls through to active bundles."""
    from services.orchestration import _resolve_capability, get_capability_requirement
    cap = _resolve_capability("read_trading")
    assert cap is not None, "read_trading not reachable through bundle fallback"
    assert cap.get("_program_slug") == "alpha-trader"
    assert cap.get("category") == "tool"
    req = get_capability_requirement("read_trading")
    assert req == {"platform": "trading", "status": "active"}


def test_build_task_md_works_for_bundle_sourced_type():
    """End-to-end: bundle-sourced task type builds a full TASK.md identically
    to a kernel-sourced task type. This is the singular-implementation
    contract — callers see one API."""
    from services.task_types import build_task_md_from_type
    md = build_task_md_from_type("trading-signal", title="Daily Signals", slug="daily-signals")
    assert md is not None
    # Mode + schedule + objective sections present
    assert "**Type:** trading-signal" in md
    assert "Daily trading signal report" in md  # default_objective.deliverable
    # Process step uses the bundle's `instruction` text
    assert "WriteFile: update /workspace/context/trading" in md


# =============================================================================
# Active-program semantics tests
# =============================================================================

def test_alpha_commerce_bundle_is_deferred_not_active():
    """ADR-224 §3: alpha-commerce bundle has status='deferred'. Its templates
    are NOT surfaced to composition reasoning until status flips to active."""
    from services.bundle_reader import _load_manifest, all_active_bundles, _all_slugs
    # Bust caches in case other tests primed them
    _load_manifest.cache_clear()
    _all_slugs.cache_clear()

    m = _load_manifest("alpha-commerce")
    assert m is not None, "alpha-commerce bundle missing from docs/programs/"
    assert m.get("status") == "deferred"

    active_slugs = [b.get("slug") for b in all_active_bundles()]
    assert "alpha-commerce" not in active_slugs


def test_deferred_bundle_capabilities_do_not_resolve():
    """ADR-224 §3: capabilities from deferred bundles are NOT surfaced.
    read_commerce belongs to alpha-commerce (deferred), so it should not
    resolve through the bundle fallback."""
    from services.bundle_reader import _load_manifest, _all_slugs
    _load_manifest.cache_clear()
    _all_slugs.cache_clear()

    from services.orchestration import _resolve_capability
    cap = _resolve_capability("read_commerce")
    assert cap is None, (
        "read_commerce should not resolve — alpha-commerce bundle is "
        "status='deferred' and its capabilities should not surface."
    )


def test_deferred_bundle_directories_do_not_resolve():
    """ADR-224 §3: directories from deferred bundles are NOT surfaced.
    customers/revenue belong to alpha-commerce (deferred), so they should
    not resolve through bundle fallback."""
    from services.bundle_reader import _load_manifest, _all_slugs
    _load_manifest.cache_clear()
    _all_slugs.cache_clear()

    from services.directory_registry import get_directory
    assert get_directory("customers") is None, "customers should not resolve — alpha-commerce is deferred"
    assert get_directory("revenue") is None, "revenue should not resolve — alpha-commerce is deferred"
