"""ADR-338 D4.4 + IA Move A gate — budget runway + launcher register grouping.

Item 5 (D4.4): GET /api/budget now frames balance + observed burn → time
remaining. daily_burn = window_spend / days-elapsed; runway_days = remaining /
daily_burn; both null until there's spend signal. Tested behaviorally in
Python (the computation is backend).

Item 6 (IA Move A): the Launcher splits the kernel tier by `register` into
three groups — Constitution (intent) / Applications (application) /
System Settings (os-config) — making the management plane cohere as a plane
in the surface index. Source-assertion (the grouping is FE render logic).

Usage:
    cd api
    python test_adr338_runway_launcher.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent
_WEB = _API_ROOT.parent / "web"

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


def _read(rel: str, root: Path = _WEB) -> str:
    p = root / rel
    return p.read_text() if p.exists() else ""


# ---------------------------------------------------------------------------
# Item 5 — runway computation (behavioral, backend)
# ---------------------------------------------------------------------------

def test_runway_computation() -> None:
    print("\n[runway] window_elapsed_days + route burn/runway math")
    sys.path.insert(0, str(_API_ROOT))
    try:
        from services.budget import window_elapsed_days
    except Exception as exc:  # pragma: no cover
        check("services.budget imports window_elapsed_days", False, str(exc))
        return
    check("services.budget imports window_elapsed_days", True)

    # Elapsed days is positive and clamped to a small floor (never zero).
    for w in ("daily", "weekly", "monthly"):
        elapsed = window_elapsed_days(w)
        check(f"{w}: elapsed-days positive + >= 1h floor", elapsed >= (1.0 / 24.0) - 1e-9,
              f"got {elapsed}")
    # daily window elapsed <= 1 day; weekly <= 7; monthly <= 31.
    check("daily elapsed <= 1.0", window_elapsed_days("daily") <= 1.0 + 1e-6)
    check("weekly elapsed <= 7.0", window_elapsed_days("weekly") <= 7.0 + 1e-6)
    check("monthly elapsed <= 31.0", window_elapsed_days("monthly") <= 31.0 + 1e-6)

    # Replicate the route's runway math to assert the contract shape.
    def runway(amount: float, spent: float, window: str):
        remaining = max(0.0, amount - spent)
        daily_burn = None
        runway_days = None
        if spent > 0.005:
            elapsed = window_elapsed_days(window)
            burn = spent / elapsed if elapsed > 0 else None
            if burn and burn > 0:
                daily_burn = round(burn, 4)
                runway_days = round(min(remaining / burn, 999.0), 1)
        return daily_burn, runway_days

    # Zero spend → no burn signal (null runway).
    b0, r0 = runway(50.0, 0.0, "monthly")
    check("zero spend → null daily_burn + null runway", b0 is None and r0 is None)
    # Real spend → positive burn + finite runway.
    b1, r1 = runway(50.0, 5.0, "monthly")
    check("real spend → positive daily_burn", b1 is not None and b1 > 0)
    check("real spend → finite runway_days", r1 is not None and r1 > 0)
    # Runway caps at 999.
    b2, r2 = runway(50.0, 0.01, "monthly")
    check("tiny burn → runway capped at 999", r2 is not None and r2 <= 999.0)


def test_runway_response_shape() -> None:
    print("\n[runway] BudgetResponse + FE types carry runway fields")
    route = _read("routes/budget.py", root=_API_ROOT)
    check("BudgetResponse declares daily_burn_usd", "daily_burn_usd: Optional[float]" in route)
    check("BudgetResponse declares runway_days", "runway_days: Optional[float]" in route)
    check("route computes runway from window_elapsed_days",
          "window_elapsed_days" in route and "remaining / burn" in route)
    check("route guards zero-spend (no signal)", "spent > 0.005" in route)

    client = _read("lib/api/client.ts")
    check("FE budget() type carries daily_burn_usd + runway_days",
          "daily_burn_usd: number | null" in client and "runway_days: number | null" in client)
    shape = _read("lib/content-shapes/budget.ts")
    check("BudgetUtilization carries runway fields",
          "daily_burn_usd" in shape and "runway_days" in shape)
    card = _read("components/workspace-concepts/BudgetCard.tsx")
    check("BudgetCard renders a runway line", "runwayLine" in card)
    check("runway phrased as time-remaining", "days left at this pace" in card)
    check("runway null-safe (no signal → renders nothing)",
          "runway_days == null" in card)


# ---------------------------------------------------------------------------
# Item 6 — launcher register grouping
# ---------------------------------------------------------------------------

def test_launcher_register_grouping() -> None:
    print("\n[launcher] kernel tier splits by register (management plane coheres)")
    src = _read("components/shell/Launcher.tsx")
    check("KERNEL_REGISTER_GROUPS declared", "KERNEL_REGISTER_GROUPS" in src)
    check("Constitution group (intent)", "'Constitution'" in src and "register: 'intent'" in src)
    check("Applications group (application)", "'Applications'" in src and "register: 'application'" in src)
    check("System Settings group (os-config)", "'System Settings'" in src and "register: 'os-config'" in src)
    check("kernel surfaces routed by register", "kernelRegisterGroupFor" in src)
    check("unregistered kernel surface defaults to Applications (no silent drop)",
          "Applications" in src and "?? { key: 'kernel:application'" in src)
    # Old flat 'Workspace' kernel group label is gone (now three register groups).
    check("old flat 'Workspace' kernel label removed",
          "groupLabel = 'Workspace'" not in src)


def main() -> int:
    print("=" * 70)
    print("ADR-338 D4.4 + IA Move A — runway + launcher register grouping gate")
    print("=" * 70)
    test_runway_computation()
    test_runway_response_shape()
    test_launcher_register_grouping()
    print("\n" + "=" * 70)
    print(f"  {PASSED} passed, {FAILED} failed")
    print("=" * 70)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
