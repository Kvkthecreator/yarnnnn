"""
ADR-242 Phase 1 regression gate — backend + bundle manifest extension.

Asserts six invariants for the platform-live MoneyTruth endpoint and the
alpha-trader SURFACES.yaml extension landed in ADR-242 Phase 1.

Phase 2 (bundle components + face dispatch + SnapshotModal fold-in) will
have its own gate (`api/test_adr242_phase2_face_dispatch.py`).

Same Python-test-over-source pattern as ADR-237 / ADR-238 / ADR-239 /
ADR-240 / ADR-241 (no JS test runner; see ADR-236 Rule 3).

Run via:
    python -m pytest api/test_adr242_phase1_cockpit_money_truth.py -v

Or as a standalone script:
    python api/test_adr242_phase1_cockpit_money_truth.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

API_COCKPIT_ROUTE = REPO_ROOT / "api" / "routes" / "cockpit.py"
API_MAIN = REPO_ROOT / "api" / "main.py"
API_ALPACA_CLIENT = REPO_ROOT / "api" / "integrations" / "core" / "alpaca_client.py"
ALPHA_TRADER_SURFACES = REPO_ROOT / "docs" / "programs" / "alpha-trader" / "SURFACES.yaml"


def _read(p: Path) -> str:
    if not p.exists():
        raise AssertionError(f"Missing file: {p.relative_to(REPO_ROOT)}")
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Test gate
# ---------------------------------------------------------------------------

def test_cockpit_route_exists_and_exports_router():
    """Assertion #1: api/routes/cockpit.py exists and exports `router` per
    the FastAPI router pattern (paralleling other routes/*.py files)."""
    src = _read(API_COCKPIT_ROUTE)
    assert "router = APIRouter()" in src, (
        "cockpit.py must instantiate a FastAPI router per ADR-242 D1."
    )
    assert "@router.get(\"/money-truth/{user_id}\"" in src, (
        "cockpit.py must declare GET /money-truth/{user_id} per ADR-242 D1."
    )


def test_money_truth_response_shape():
    """Assertion #2: MoneyTruthResponse declares the documented shape —
    `live: bool`, fallback fields, numeric fields. Regression guard
    against drifting the contract the FE depends on."""
    src = _read(API_COCKPIT_ROUTE)
    assert "class MoneyTruthResponse(BaseModel)" in src, (
        "cockpit.py must define MoneyTruthResponse model per ADR-242 D1."
    )
    # Required field on every response
    assert "live: bool" in src, (
        "MoneyTruthResponse must declare `live: bool` per ADR-242 D1."
    )
    # Live-shape numeric fields
    for field in ("equity", "cash", "buying_power", "day_pnl", "positions_count"):
        assert f"{field}:" in src, (
            f"MoneyTruthResponse must declare `{field}` field per ADR-242 D1."
        )
    # Fallback shape
    assert "fallback_reason:" in src, (
        "MoneyTruthResponse must declare `fallback_reason` for live=False shape per ADR-242 D1."
    )


def test_main_registers_cockpit_router():
    """Assertion #3: main.py imports + registers the cockpit router under
    /api/cockpit. Regression guard against the new endpoint being
    unreachable."""
    src = _read(API_MAIN)
    assert "cockpit" in src, (
        "main.py must import the cockpit module."
    )
    assert "/api/cockpit" in src, (
        "main.py must register cockpit.router under /api/cockpit per ADR-242 D1."
    )


def test_alpha_trader_declares_money_truth_live_source():
    """Assertion #4: alpha-trader's SURFACES.yaml declares
    cockpit.money_truth.live_source: alpaca per ADR-242 D3. The FE's
    MoneyTruthFace dispatch branch (Phase 2) keys on this binding."""
    src = _read(ALPHA_TRADER_SURFACES)
    assert "live_source: alpaca" in src, (
        "alpha-trader SURFACES.yaml must declare cockpit.money_truth.live_source: alpaca per ADR-242 D3."
    )


def test_alpha_trader_declares_performance_components():
    """Assertion #5: alpha-trader's SURFACES.yaml declares
    cockpit.performance.components[] with TraderSignalExpectancy entry
    per ADR-242 D3."""
    src = _read(ALPHA_TRADER_SURFACES)
    assert "TraderSignalExpectancy" in src, (
        "alpha-trader SURFACES.yaml must declare cockpit.performance.components with TraderSignalExpectancy entry per ADR-242 D3."
    )


def test_alpha_trader_declares_tracking_operational_state():
    """Assertion #6: alpha-trader's SURFACES.yaml declares
    cockpit.tracking.operational_state with TraderPositions kind per
    ADR-242 D3. AND alpaca_client.get_account + get_positions still
    exist (Phase 1's runtime depends on them)."""
    src = _read(ALPHA_TRADER_SURFACES)
    assert "TraderPositions" in src, (
        "alpha-trader SURFACES.yaml must declare cockpit.tracking.operational_state with TraderPositions kind per ADR-242 D3."
    )
    # Regression guard against alpaca_client losing methods we depend on
    alpaca_src = _read(API_ALPACA_CLIENT)
    assert "async def get_account" in alpaca_src, (
        "alpaca_client.py must continue to export get_account (Phase 1 dependency)."
    )
    assert "async def get_positions" in alpaca_src, (
        "alpaca_client.py must continue to export get_positions (Phase 1 dependency)."
    )


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

def _run_all() -> int:
    tests = [
        test_cockpit_route_exists_and_exports_router,
        test_money_truth_response_shape,
        test_main_registers_cockpit_router,
        test_alpha_trader_declares_money_truth_live_source,
        test_alpha_trader_declares_performance_components,
        test_alpha_trader_declares_tracking_operational_state,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {fn.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} ADR-242 Phase 1 assertions passed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(_run_all())
