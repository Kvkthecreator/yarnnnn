"""
ADR-242 Phase 1 regression gate — alpha-trader brokerage route + manifest.

Originally asserted the platform-live MoneyTruth endpoint under the
`/api/cockpit/*` namespace (ADR-242 Phase 1). ADR-312 D9 folded that route
into the program-data namespace: the trader-data endpoints now live in
`api/routes/alpha_trader.py` mounted at `/api/programs/alpha-trader/*`. The
ADR-273 Phase 6 SURFACES.yaml rewrite replaced the per-face bindings
(`cockpit.money_truth.live_source`, `cockpit.performance.components`,
`cockpit.tracking.operational_state`) with `home.program_sections` — this
gate is updated to the post-ADR-273/312 reality.

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

# ADR-312 D9: trader-data route renamed cockpit.py → alpha_trader.py.
API_TRADER_ROUTE = REPO_ROOT / "api" / "routes" / "alpha_trader.py"
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

def test_trader_route_exists_and_exports_router():
    """Assertion #1: api/routes/alpha_trader.py exists and exports `router`
    (the cockpit.py route folded here per ADR-312 D9)."""
    src = _read(API_TRADER_ROUTE)
    assert "router = APIRouter()" in src, (
        "alpha_trader.py must instantiate a FastAPI router per ADR-242 D1 / ADR-312 D9."
    )
    assert "@router.get(\"/money-truth\"" in src, (
        "alpha_trader.py must declare GET /money-truth (auth-scoped, no path param)."
    )


def test_money_truth_response_shape():
    """Assertion #2: MoneyTruthResponse declares the documented shape —
    `live: bool`, fallback fields, numeric fields. Regression guard
    against drifting the contract the FE depends on."""
    src = _read(API_TRADER_ROUTE)
    assert "class MoneyTruthResponse(BaseModel)" in src, (
        "alpha_trader.py must define MoneyTruthResponse model per ADR-242 D1."
    )
    assert "live: bool" in src, (
        "MoneyTruthResponse must declare `live: bool` per ADR-242 D1."
    )
    for field in ("equity", "cash", "buying_power", "day_pnl", "positions_count"):
        assert f"{field}:" in src, (
            f"MoneyTruthResponse must declare `{field}` field per ADR-242 D1."
        )
    assert "fallback_reason:" in src, (
        "MoneyTruthResponse must declare `fallback_reason` for live=False shape per ADR-242 D1."
    )


def test_main_registers_trader_router():
    """Assertion #3: main.py imports + registers the alpha_trader router under
    /api/programs/alpha-trader per ADR-312 D9. No legacy /api/cockpit mount."""
    src = _read(API_MAIN)
    assert "alpha_trader" in src, (
        "main.py must import the alpha_trader module."
    )
    assert "/api/programs/alpha-trader" in src, (
        "main.py must register alpha_trader.router under /api/programs/alpha-trader per ADR-312 D9."
    )
    # No live /api/cockpit mount survives (comments naming the old path OK).
    for line in src.splitlines():
        if line.strip().startswith("#"):
            continue
        assert "/api/cockpit" not in line, (
            f"ADR-312 D9: no live /api/cockpit mount may survive (found: {line.strip()!r})"
        )


def test_alpha_trader_declares_program_sections():
    """Assertion #4: alpha-trader's SURFACES.yaml declares the Home program
    section stack (ADR-273 Phase 6 + ADR-312 D2 — the per-face bindings
    `live_source`/`performance.components`/`tracking.operational_state` were
    superseded by `home.program_sections`)."""
    src = _read(ALPHA_TRADER_SURFACES)
    assert "program_sections" in src, (
        "alpha-trader SURFACES.yaml must declare home.program_sections per ADR-273 Phase 6."
    )
    assert "home:" in src, (
        "alpha-trader SURFACES.yaml must use the `home` composition key (renamed from cockpit) per ADR-312 D2."
    )


def test_alpha_trader_declares_trader_section_kinds():
    """Assertion #5: the program section stack names the canonical trader
    components — TraderMoneyTruth (ground-truth hero binding), TraderExpectancy
    (by_signal), TraderPositions (live entities)."""
    src = _read(ALPHA_TRADER_SURFACES)
    for kind in ("TraderMoneyTruth", "TraderExpectancy", "TraderPositions"):
        assert kind in src, (
            f"alpha-trader SURFACES.yaml must declare {kind} in home.program_sections."
        )


def test_alpaca_client_methods_present():
    """Assertion #6: alpaca_client.get_account + get_positions still exist —
    the trader route's live-brokerage runtime depends on them."""
    alpaca_src = _read(API_ALPACA_CLIENT)
    assert "async def get_account" in alpaca_src, (
        "alpaca_client.py must continue to export get_account (trader-route dependency)."
    )
    assert "async def get_positions" in alpaca_src, (
        "alpaca_client.py must continue to export get_positions (trader-route dependency)."
    )


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

def _run_all() -> int:
    tests = [
        test_trader_route_exists_and_exports_router,
        test_money_truth_response_shape,
        test_main_registers_trader_router,
        test_alpha_trader_declares_program_sections,
        test_alpha_trader_declares_trader_section_kinds,
        test_alpaca_client_methods_present,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {fn.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} ADR-242 Phase 1 (post-ADR-312) assertions passed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(_run_all())
