"""
ADR-242 Phase 2 regression gate — bundle components + face dispatch.

Asserts seven invariants for the alpha-trader bundle component layer
landed in ADR-242 Phase 2.

Phase 1 (backend endpoint + manifest extension) shipped first; its gate
at `api/test_adr242_phase1_cockpit_money_truth.py` continues to enforce
the backend contract.

Item 10 (cockpit ↔ snapshot convergence) is **Deferred** per ADR-242 D5
implementation-time finding — SnapshotModal and cockpit faces have
legitimately different surface roles (briefing vs dashboard); forced
convergence would degrade either. Substrate truth holds (both surfaces
read the same files); surface truth diverges legitimately. No test
gate assertion for SnapshotModal in Phase 2.

Same Python-test-over-source pattern as ADR-237/238/239/240/241 per
ADR-236 Rule 3.

Run via:
    python -m pytest api/test_adr242_phase2_face_dispatch.py -v

Or as a standalone script:
    python api/test_adr242_phase2_face_dispatch.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

WEB_LIBRARY_DIR = REPO_ROOT / "web" / "components" / "library"
WEB_REGISTRY = WEB_LIBRARY_DIR / "registry.tsx"
WEB_TRADER_MONEY_TRUTH = WEB_LIBRARY_DIR / "TraderMoneyTruth.tsx"
WEB_TRADER_SIGNAL_EXPECTANCY = WEB_LIBRARY_DIR / "TraderSignalExpectancy.tsx"
WEB_TRADER_POSITIONS = WEB_LIBRARY_DIR / "TraderPositions.tsx"
WEB_MONEY_TRUTH_FACE = WEB_LIBRARY_DIR / "faces" / "MoneyTruthFace.tsx"
WEB_PERFORMANCE_FACE = WEB_LIBRARY_DIR / "faces" / "PerformanceFace.tsx"
WEB_TRACKING_FACE = WEB_LIBRARY_DIR / "faces" / "TrackingFace.tsx"
WEB_API_CLIENT = REPO_ROOT / "web" / "lib" / "api" / "client.ts"


def _read(p: Path) -> str:
    if not p.exists():
        raise AssertionError(f"Missing file: {p.relative_to(REPO_ROOT)}")
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Test gate
# ---------------------------------------------------------------------------

def test_three_trader_components_exist():
    """Assertion #1: the three alpha-trader bundle component files
    exist with the expected exports per ADR-242 D2."""
    money_src = _read(WEB_TRADER_MONEY_TRUTH)
    expectancy_src = _read(WEB_TRADER_SIGNAL_EXPECTANCY)
    positions_src = _read(WEB_TRADER_POSITIONS)

    assert "export function TraderMoneyTruth" in money_src, (
        "TraderMoneyTruth.tsx must export `TraderMoneyTruth` per ADR-242 D2."
    )
    assert "export function TraderSignalExpectancy" in expectancy_src, (
        "TraderSignalExpectancy.tsx must export `TraderSignalExpectancy` per ADR-242 D2."
    )
    assert "export function TraderPositions" in positions_src, (
        "TraderPositions.tsx must export `TraderPositions` per ADR-242 D2."
    )


def test_components_registered_in_library():
    """Assertion #2: the three trader components are registered in
    LIBRARY_COMPONENTS so the dispatcher can route bundle declarations
    to them per ADR-225 I1."""
    src = _read(WEB_REGISTRY)
    for kind in ("TraderMoneyTruth", "TraderSignalExpectancy", "TraderPositions"):
        # Match the registry entry pattern (kind name appears as a key).
        # Tolerant: matches `TraderMoneyTruth: () => ...` or `TraderMoneyTruth: (props) => ...`.
        assert f"{kind}:" in src, (
            f"{kind} must be registered in LIBRARY_COMPONENTS per ADR-242 D2."
        )


def test_money_truth_face_dispatch_branch():
    """Assertion #3: MoneyTruthFace has a dispatch branch that routes to
    TraderMoneyTruth when bundle declares `live_source: alpaca` per
    ADR-242 D4."""
    src = _read(WEB_MONEY_TRUTH_FACE)
    assert "TraderMoneyTruth" in src, (
        "MoneyTruthFace.tsx must reference TraderMoneyTruth in its "
        "dispatch branch per ADR-242 D4."
    )
    assert "live_source" in src, (
        "MoneyTruthFace.tsx must read the bundle's `live_source` declaration "
        "to decide dispatch."
    )


def test_performance_face_dispatch_branch():
    """Assertion #4: PerformanceFace has a dispatch branch that renders
    bundle-declared components AFTER the universal Reviewer calibration
    per ADR-242 D4."""
    src = _read(WEB_PERFORMANCE_FACE)
    assert "dispatchComponent" in src, (
        "PerformanceFace.tsx must import dispatchComponent for bundle "
        "sub-component dispatch per ADR-242 D4."
    )
    assert "components" in src and "performance" in src, (
        "PerformanceFace.tsx must read bundle's "
        "`cockpit.performance.components` declaration."
    )


def test_tracking_face_dispatch_branch():
    """Assertion #5: TrackingFace's OperationalState region has a
    dispatch branch that routes to bundle component when
    `cockpit.tracking.operational_state` is declared per ADR-242 D4."""
    src = _read(WEB_TRACKING_FACE)
    assert "operational_state" in src, (
        "TrackingFace.tsx must read bundle's "
        "`cockpit.tracking.operational_state` declaration per ADR-242 D4."
    )
    assert "dispatchComponent" in src, (
        "TrackingFace.tsx OperationalState must import dispatchComponent."
    )


def test_api_client_exposes_money_truth_method():
    """Assertion #6: api.cockpit.moneyTruth() exists in the FE client per
    ADR-242 D2 (TraderMoneyTruth's data dependency)."""
    src = _read(WEB_API_CLIENT)
    assert "cockpit:" in src, (
        "client.ts must define api.cockpit namespace per ADR-242 Phase 2."
    )
    assert "moneyTruth:" in src, (
        "api.cockpit.moneyTruth method must exist per ADR-242 D2."
    )
    assert "/api/cockpit/money-truth" in src, (
        "api.cockpit.moneyTruth must call /api/cockpit/money-truth."
    )


def test_singular_implementation_one_dispatch_path():
    """Assertion #7: Singular Implementation regression guard. Each face
    has exactly one bundle dispatch path (not two parallel paths). The
    pattern: dispatch when bundle declares; fall through to kernel-default
    render otherwise."""
    money_src = _read(WEB_MONEY_TRUTH_FACE)
    perf_src = _read(WEB_PERFORMANCE_FACE)
    tracking_src = _read(WEB_TRACKING_FACE)

    # No legacy "TraderMoneyTruthOld" / "...V2" / shim variant
    for src, name in (
        (money_src, "MoneyTruthFace"),
        (perf_src, "PerformanceFace"),
        (tracking_src, "TrackingFace"),
    ):
        assert "_LEGACY" not in src and "_OLD" not in src and "_V1" not in src, (
            f"{name}.tsx must not carry legacy/V1/old dispatch variants — "
            "Singular Implementation per ADR-242."
        )


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

def _run_all() -> int:
    tests = [
        test_three_trader_components_exist,
        test_components_registered_in_library,
        test_money_truth_face_dispatch_branch,
        test_performance_face_dispatch_branch,
        test_tracking_face_dispatch_branch,
        test_api_client_exposes_money_truth_method,
        test_singular_implementation_one_dispatch_path,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {fn.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} ADR-242 Phase 2 assertions passed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(_run_all())
