"""ADR-445 gate — the TWO-AXIS pricing model (supersedes ADR-429's three axes).

Locks the model's load-bearing invariants so a future edit can't silently drift:
  (a) SEATS are LIVE — the paid plan has a non-zero per-seat fee (ADR-445 reverses
      ADR-429 §5a's dormant launch); free never charges a seat.
  (b) Seat 1 (the owner) is free — billable_seats(tier, 1) == 0 on every tier, so a
      solo workspace pays $0 subscription (usage-only).
  (c) The seat=HUMAN carve — AI principal roles are never counted as seats.
  (d) `included_seats` is the BILLING BASELINE, not a hard cap — the free→paid
      boundary is the ONLY headcount gate, and it is FREE-only (a paid tier grows
      its team freely). This asserts the config that makes the invite gate behave.
  (e) No per-workspace base fee survives — the tier's price IS the seat price.

Usage:
    cd api
    python test_adr445_two_axis_pricing.py
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


def test_seats_live() -> None:
    print("\n[live] the paid plan charges a per-seat fee; free never does (ADR-445 §4/§6)")
    from services.billing_tiers import tier_additional_seat_usd

    check("free: additional_seat_usd == 0 (free never charges a seat)",
          tier_additional_seat_usd("free") == 0.0)
    check("starter: additional_seat_usd > 0 (seats are LIVE, not dormant)",
          tier_additional_seat_usd("starter") > 0.0,
          f"got ${tier_additional_seat_usd('starter')} — the paid seat must be priced")


def test_owner_seat_free() -> None:
    print("\n[owner] seat 1 (the owner) is free on every tier — solo pays $0 (ADR-445 §5)")
    from services.billing_tiers import billable_seats, seat_fee_usd

    for tier in ("free", "starter", "pro", "enterprise"):
        check(f"{tier}: billable_seats(x1) == 0 (owner is the free seat)",
              billable_seats(tier, 1) == 0)
        check(f"{tier}: seat_fee_usd(x1) == $0 (solo subscription is usage-only)",
              seat_fee_usd(tier, 1) == 0.0)


def test_seat_math() -> None:
    print("\n[math] a team bills (humans − 1) × the seat fee (ADR-445 §4)")
    from services.billing_tiers import billable_seats, seat_fee_usd, tier_additional_seat_usd

    unit = tier_additional_seat_usd("starter")
    for humans, want_billable in [(1, 0), (2, 1), (3, 2), (5, 4), (10, 9)]:
        check(f"starter, {humans} humans → {want_billable} billable seats",
              billable_seats("starter", humans) == want_billable,
              f"got {billable_seats('starter', humans)}")
        check(f"starter, {humans} humans → ${want_billable * unit} seat fee",
              seat_fee_usd("starter", humans) == round(want_billable * unit, 2))


def test_seat_is_human() -> None:
    print("\n[carve] a seat is a HUMAN; AI principal roles are never counted (ADR-445 §3)")
    from services.billing_tiers import HUMAN_SEAT_ROLES

    check("HUMAN_SEAT_ROLES == {owner, member}", set(HUMAN_SEAT_ROLES) == {"owner", "member"})
    for ai_role in ("foreign-llm", "a2a", "own-agent", "platform"):
        check(f"AI role '{ai_role}' is NOT a seat role", ai_role not in HUMAN_SEAT_ROLES)


def test_baseline_not_a_cap() -> None:
    print("\n[baseline] included_seats is the billing baseline, not a hard cap (ADR-445 §4)")
    from services.billing_tiers import tier_included_seats, PAID_TIERS

    # Free is SOLO (the owner alone); the 2nd human is the free→paid boundary.
    check("free included_seats == 1 (solo)", tier_included_seats("free") == 1)
    # The paid plan's owner is the one free seat; additional humans bill.
    check("starter included_seats == 1 (owner; additional humans billed)",
          tier_included_seats("starter") == 1)
    # The paid tiers are the in-tier resolution for a growing team — so the invite
    # gate (workspace_invites) must fire ONLY on non-paid tiers. Assert 'free' is
    # not paid (it gates) and 'starter' is paid (it does not).
    check("free is NOT a paid tier (it gates the 2nd human)", "free" not in PAID_TIERS)
    check("starter IS a paid tier (grows freely, never hard-capped)", "starter" in PAID_TIERS)


def test_no_base_fee_concept() -> None:
    print("\n[collapse] the price is the seat price — no standalone base fee (ADR-445 §4)")
    from services.billing_tiers import TIER_CONFIG, tier_additional_seat_usd

    # On each SELF-SERVE paid tier the per-seat fee equals the plan's price_usd —
    # proving the subscription IS the seat price (not price_usd base + a separate
    # seat fee). Enterprise is excluded: it is a sales-led custom bundle whose
    # price_usd is a $0 placeholder (no self-serve checkout price), seat-priced like
    # every paid tier but not on the self-serve ladder.
    for tier in ("starter", "pro"):
        spec = TIER_CONFIG[tier]
        check(f"{tier}: price_usd == additional_seat_usd (price IS the seat price)",
              spec["price_usd"] == tier_additional_seat_usd(tier),
              f"price_usd=${spec['price_usd']} seat=${tier_additional_seat_usd(tier)}")


def test_tier_structure() -> None:
    print("\n[structure] launch = Free + one paid plan; pro dormant; enum kept")
    from services.billing_tiers import (
        TIER_CONFIG,
        tier_hidden,
        offered_paid_tiers,
        public_tier_ladder,
    )

    check("pro is hidden (dormant tier)", tier_hidden("pro") is True)
    check("free is NOT hidden", tier_hidden("free") is False)
    check("starter is NOT hidden", tier_hidden("starter") is False)
    check("offered_paid_tiers() == ('starter',) — one paid plan at launch",
          offered_paid_tiers() == ("starter",))
    ladder_tiers = [r["tier"] for r in public_tier_ladder()]
    check("public ladder == [free, starter] (no pro)", ladder_tiers == ["free", "starter"])
    # The 4 enum values survive (product decision, not schema change).
    check("all tier keys present (enum kept)",
          {"free", "starter", "pro"}.issubset(set(TIER_CONFIG.keys())))


def main() -> int:
    print("=" * 70)
    print("ADR-445 — the two-axis pricing model (seats live · owner free · pooled meter)")
    print("=" * 70)
    test_seats_live()
    test_owner_seat_free()
    test_seat_math()
    test_seat_is_human()
    test_baseline_not_a_cap()
    test_no_base_fee_concept()
    test_tier_structure()
    print("\n" + "=" * 70)
    print(f"  {PASSED} passed, {FAILED} failed")
    print("=" * 70)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
