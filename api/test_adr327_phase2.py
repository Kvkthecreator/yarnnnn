"""ADR-327 Phase 2 gate — Tier-1 budget gate + D4 priority rule.

Covers:
  - BudgetSignals: window_spend/window_budget fields; judgment_cap fields gone
  - Tier-1: cron_tick budget exhaustion → skip "budget_exhausted"
  - Tier-1: reactive sources escalate unconditionally (never budget-blocked)
  - Tier-1: per-slug min-interval floor preserved
  - wake.py imports from services.budget (not token_budget); judgment cap gone
  - get_daily_spend no longer imported in wake.py

Usage:
    cd api
    python test_adr327_phase2.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))
_REPO_ROOT = _API_ROOT.parent
try:
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
except Exception:
    pass

from services.wake_evaluation import BudgetSignals, tier_1_decision  # noqa: E402

PASSED = 0
FAILED = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        print(f"  ✓ {label}")
        PASSED += 1
    else:
        print(f"  ✗ {label}{(' — ' + detail) if detail else ''}")
        FAILED += 1


class _Rec:
    def __init__(self, mode="judgment", slug="signal-evaluation"):
        self.mode = mode
        self.slug = slug


def test_budget_signals_fields() -> None:
    print("\n[BudgetSignals] field shape")
    ann = BudgetSignals.__annotations__
    check("window_spend field present", "window_spend" in ann)
    check("window_budget field present", "window_budget" in ann)
    check("daily_spend field GONE", "daily_spend" not in ann)
    check("spend_ceiling field GONE", "spend_ceiling" not in ann)
    check("judgment_count_today field GONE", "judgment_count_today" not in ann)
    check("judgment_cap field GONE", "judgment_cap" not in ann)
    check("min_interval_floor_sec preserved", "min_interval_floor_sec" in ann)
    check("seconds_since_last_fire preserved", "seconds_since_last_fire" in ann)


def test_scheduled_budget_gate() -> None:
    print("\n[tier-1] cron_tick (scheduled) budget gate")
    payload = {"recurrence": _Rec()}
    # Under budget → escalate
    under = BudgetSignals(balance_ok=True, window_spend=10.0, window_budget=50.0)
    d, r = tier_1_decision("cron_tick", payload, under)
    check("under budget → escalate", d == "escalate", f"{d}/{r}")
    # At/over budget → skip budget_exhausted
    over = BudgetSignals(balance_ok=True, window_spend=50.0, window_budget=50.0)
    d, r = tier_1_decision("cron_tick", payload, over)
    check("at budget → skip", d == "skip", d)
    check("reason is budget_exhausted", r == "budget_exhausted", r)
    # Reason vocabulary retired
    check("reason NOT spend_ceiling", r != "spend_ceiling")
    check("reason NOT judgment_cap", r != "judgment_cap")


def test_balance_still_gates() -> None:
    print("\n[tier-1] balance gate preserved")
    payload = {"recurrence": _Rec()}
    sig = BudgetSignals(balance_ok=False, window_spend=0.0, window_budget=50.0)
    d, r = tier_1_decision("cron_tick", payload, sig)
    check("balance exhausted → skip", d == "skip", d)
    check("reason balance_exhausted", r == "balance_exhausted", r)


def test_min_interval_preserved() -> None:
    print("\n[tier-1] per-slug min-interval floor preserved")
    payload = {"recurrence": _Rec()}
    sig = BudgetSignals(
        balance_ok=True, window_spend=0.0, window_budget=50.0,
        min_interval_floor_sec=900, seconds_since_last_fire=120,
    )
    d, r = tier_1_decision("cron_tick", payload, sig)
    check("too-soon fire → skip", d == "skip", d)
    check("reason min_interval", r == "min_interval", r)


def test_reactive_unconditional() -> None:
    print("\n[tier-1] reactive sources escalate (never budget-blocked — D4 reactive-warn)")
    over = BudgetSignals(balance_ok=True, window_spend=999.0, window_budget=50.0)
    for src in ("addressed", "proposal_arrival", "manual_fire", "substrate_event"):
        d, _r = tier_1_decision(src, {}, over)
        check(f"{src} → escalate despite over-budget", d == "escalate", d)


def test_mechanical_bypass() -> None:
    print("\n[tier-1] mechanical recurrence bypasses (free)")
    payload = {"recurrence": _Rec(mode="mechanical")}
    over = BudgetSignals(balance_ok=True, window_spend=999.0, window_budget=50.0)
    d, r = tier_1_decision("cron_tick", payload, over)
    check("mechanical → mechanical (never budget-gated)", d == "mechanical", f"{d}/{r}")


def test_wake_py_wiring() -> None:
    print("\n[wake.py] budget wiring")
    src = (_API_ROOT / "services/wake.py").read_text()
    check("imports services.budget", "from services.budget import load_budget" in src)
    check("calls window_spend", "window_spend(client, user_id, budget.window)" in src)
    check("no load_token_budget", "load_token_budget" not in src)
    check("no count_judgment_fires_today", "count_judgment_fires_today" not in src)
    check("no max_judgment_recurrences", "max_judgment_recurrences" not in src)
    check("budget_exhausted error_reason used", 'error_reason="budget_exhausted"' in src)
    check("get_daily_spend import removed", "get_daily_spend" not in src)
    check("Gate 2 judgment cap deleted (comment marks it)", "Gate 2 (judgment-recurrence cap) DELETED" in src)


def main() -> int:
    print("=" * 64)
    print("ADR-327 Phase 2 — Tier-1 budget gate + D4 priority rule")
    print("=" * 64)
    test_budget_signals_fields()
    test_scheduled_budget_gate()
    test_balance_still_gates()
    test_min_interval_preserved()
    test_reactive_unconditional()
    test_mechanical_bypass()
    test_wake_py_wiring()
    print("\n" + "=" * 64)
    print(f"  PASSED={PASSED}  FAILED={FAILED}")
    print("=" * 64)
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
