"""ADR-429 Phase 2 gate — the seat axis ships DORMANT ($0), math correct on activation.

The seat axis (Axis ②) is built end-to-end but must bill NOTHING until the operator
deliberately activates it (ADR-429 §5a: ship-dormant-activate-by-config). This gate
locks two invariants so a future edit can't:
  (a) accidentally activate seat billing (a non-zero additional_seat_usd in TIER_CONFIG
      would be a silent price change — this gate FAILS loudly if any tier is non-zero);
  (b) break the seat math so activation would compute the wrong fee.

It also asserts the seat=HUMAN carve (AI principals are never counted) at the code level.

Usage:
    cd api
    python test_adr429_seat_axis.py
"""

from __future__ import annotations

import sys

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


def test_dormant_invariant() -> None:
    print("\n[dormant] every tier bills $0 for seats at any headcount (ADR-429 §5a)")
    from services.billing_tiers import (
        TIER_CONFIG,
        seat_fee_usd,
        tier_additional_seat_usd,
    )

    for tier in ("free", "starter", "pro"):
        check(
            f"{tier}: additional_seat_usd == 0 (DORMANT)",
            tier_additional_seat_usd(tier) == 0.0,
            f"got ${tier_additional_seat_usd(tier)} — seat billing was ACTIVATED without intent",
        )
        # $0 at every plausible headcount — teams are byte-identical to solo.
        for humans in (1, 2, 3, 5, 10, 50):
            check(
                f"{tier}: seat_fee_usd(x{humans}) == $0",
                seat_fee_usd(tier, humans) == 0.0,
                f"got ${seat_fee_usd(tier, humans)}",
            ) if humans in (1, 10) else _silent(seat_fee_usd(tier, humans) == 0.0)

    # every tier declares the seat fields (the TypedDict contract)
    for tier in ("free", "starter", "pro"):
        spec = TIER_CONFIG[tier]
        check(f"{tier}: declares included_seats + additional_seat_usd",
              "included_seats" in spec and "additional_seat_usd" in spec)


def test_activation_math() -> None:
    print("\n[activation] the math is correct when a fee is set (billable = humans − included)")
    from services.billing_tiers import (
        TIER_CONFIG,
        billable_seats,
        seat_fee_usd,
    )

    # Simulate activation WITHOUT persisting — mutate a copy's effect via the live
    # dict, then restore, so the dormant invariant above is not disturbed for reruns.
    original = TIER_CONFIG["starter"]["additional_seat_usd"]
    try:
        TIER_CONFIG["starter"]["additional_seat_usd"] = 12.0
        cases = [(1, 0, 0.0), (2, 1, 12.0), (3, 2, 24.0), (5, 4, 48.0)]
        for humans, want_billable, want_fee in cases:
            check(
                f"starter@${12}/seat, {humans} humans → {want_billable} billable → ${want_fee}",
                billable_seats("starter", humans) == want_billable
                and seat_fee_usd("starter", humans) == want_fee,
                f"billable={billable_seats('starter', humans)} fee=${seat_fee_usd('starter', humans)}",
            )
        # included_seats humans are always free (owner-inclusive base)
        check("the first (included) human is never billed",
              seat_fee_usd("starter", 1) == 0.0)
    finally:
        TIER_CONFIG["starter"]["additional_seat_usd"] = original


def test_seat_is_human() -> None:
    print("\n[carve] a seat is a HUMAN; AI principal roles are never counted (ADR-429 §3)")
    from services.billing_tiers import HUMAN_SEAT_ROLES

    check("HUMAN_SEAT_ROLES == {owner, member}", set(HUMAN_SEAT_ROLES) == {"owner", "member"})
    for ai_role in ("foreign-llm", "a2a", "own-agent", "platform"):
        check(f"AI role '{ai_role}' is NOT a seat role", ai_role not in HUMAN_SEAT_ROLES)


def test_ladder_exposes_seats() -> None:
    print("\n[ladder] public_tier_ladder exposes seat info for the pricing page (Phase 3)")
    from services.billing_tiers import public_tier_ladder

    for row in public_tier_ladder():
        check(
            f"{row['tier']}: ladder row carries included_seats + additional_seat_usd",
            "included_seats" in row and "additional_seat_usd" in row,
        )
        # dormant in the ladder too
        check(f"{row['tier']}: ladder additional_seat_usd == 0 (dormant)",
              row["additional_seat_usd"] == 0.0)


def test_tier_collapse() -> None:
    print("\n[§12] launch = Free + one paid plan; pro dormant; Free = owner + 1 guest")
    from services.billing_tiers import (
        TIER_CONFIG,
        tier_hidden,
        offered_paid_tiers,
        public_tier_ladder,
        tier_included_seats,
    )

    # §12.1 — pro is hidden (dormant); free + starter are offered.
    check("pro is hidden (dormant, §12.1)", tier_hidden("pro") is True)
    check("free is NOT hidden", tier_hidden("free") is False)
    check("starter is NOT hidden", tier_hidden("starter") is False)
    check("offered_paid_tiers() == ('starter',) — one paid plan at launch",
          offered_paid_tiers() == ("starter",))
    ladder_tiers = [r["tier"] for r in public_tier_ladder()]
    check("public ladder == [free, starter] (no pro)", ladder_tiers == ["free", "starter"])

    # §12.2 — the one paid plan repriced to $20 / $15.
    check("starter base == $20 (§12.2)", TIER_CONFIG["starter"]["price_usd"] == 20.0)
    check("starter allowance == $15 (§12.2)", TIER_CONFIG["starter"]["monthly_allowance_usd"] == 15.0)

    # §12.3c — Free = owner + 1 guest (included_seats: 2).
    check("free included_seats == 2 (owner + 1 guest, §12.3c)", tier_included_seats("free") == 2)
    check("starter included_seats == 1 (owner; additional humans bill)", tier_included_seats("starter") == 1)

    # The 3 enum values are KEPT (product collapse, not schema change).
    check("all 3 tier keys still present (enum kept, §12.1)",
          set(TIER_CONFIG.keys()) == {"free", "starter", "pro"})


def _silent(cond: bool) -> None:
    """Count a silent assertion (no line printed) — keeps the dormant sweep terse."""
    global PASSED, FAILED
    if cond:
        PASSED += 1
    else:
        FAILED += 1
        print("  ✗ (silent dormant check failed)")


def main() -> int:
    print("=" * 70)
    print("ADR-429 Phase 2 — the seat axis (dormant $0, math correct on activation)")
    print("=" * 70)
    test_dormant_invariant()
    test_activation_math()
    test_seat_is_human()
    test_ladder_exposes_seats()
    test_tier_collapse()
    print("\n" + "=" * 70)
    print(f"  {PASSED} passed, {FAILED} failed")
    print("=" * 70)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
