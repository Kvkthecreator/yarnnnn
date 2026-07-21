"""ADR-445 §7 P2 amendment gate — the solo-checkout copy contract (2026-07-21).

THE RATIFIED POSITION: a solo workspace MAY take the paid plan and pays $20
(checkout floors `billable_seats` at 1 — LS rejects quantity 0). The free→paid
boundary governs when a workspace MUST pay (the 2nd human), not whether a solo
owner may choose to. What the $20 buys a solo owner is the POOLED ALLOWANCE +
the higher gates — NOT a second seat.

THE COPY CONTRACT that follows, and what this gate locks:
  • the upgrade CTA reads "$20/mo", never "$20/seat/mo" — it is only ever shown
    to a free (therefore solo) workspace, so a per-seat label told a solo owner
    they were buying a seat while the same card said "Your seat is free";
  • no surface tells a PAYING solo owner their seat is free;
  • the seat-unit label (`tierPriceLabel`) stays DELETED — it had exactly one
    caller, the CTA, where it was wrong (Singular Implementation).

This is a TEXT gate over the FE source (the copy is the artifact under test).
Per the repo lesson that gates must exercise what they claim, the *behavioural*
half — that checkout actually floors quantity at 1 — is asserted against the
backend below.

Usage:
    cd api
    python test_adr445_solo_checkout_copy.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PASSED = 0
FAILED = 0

WEB = Path("../web")
USAGE_TS = WEB / "lib/subscription/usage.ts"
CARD_TSX = WEB / "components/subscription/SubscriptionCard.tsx"


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        print(f"  ✓ {label}")
        PASSED += 1
    else:
        print(f"  ✗ {label}{(' — ' + detail) if detail else ''}")
        FAILED += 1


def test_upgrade_label_is_not_per_seat() -> None:
    print("\n[cta] the upgrade label is $X/mo, not $X/seat/mo")
    src = USAGE_TS.read_text()
    m = re.search(r"export function tierUpgradeLabel[\s\S]*?\n}", src)
    check("tierUpgradeLabel exists", m is not None)
    if m:
        body = m.group(0)
        check("it renders a bare /mo price", "/mo`" in body and "/seat/mo" not in body,
              "an upgrade CTA must not imply a seat purchase")


def test_seat_unit_label_stays_deleted() -> None:
    print("\n[singular] the seat-unit CTA label is not resurrected")
    src = USAGE_TS.read_text()
    check("tierPriceLabel is not re-exported",
          "export function tierPriceLabel" not in src,
          "deleted 2026-07-21 — its one caller (the CTA) was wrong")
    # No FE file may call it.
    callers = [
        p for p in WEB.rglob("*.ts*")
        if "node_modules" not in str(p) and re.search(r"\btierPriceLabel\s*\(", p.read_text())
    ]
    check("no call sites anywhere in web/", not callers, f"callers={callers}")


def test_paid_solo_is_not_told_their_seat_is_free() -> None:
    print("\n[card] a PAYING solo owner is never told 'your seat is free'")
    src = CARD_TSX.read_text()
    check("the paid-solo branch is distinguished from free-solo",
          'humanSeats === 1 && tier !== "free"' in src,
          "the seat row must branch on tier, else a paying solo reads 'free'")
    # The free-seat sentence must be reachable ONLY on the free/exempt path.
    idx_paid = src.find('humanSeats === 1 && tier !== "free"')
    idx_free_copy = src.find("Your seat is free")
    check("the 'seat is free' copy sits AFTER the paid-solo branch",
          idx_paid != -1 and idx_free_copy != -1 and idx_paid < idx_free_copy,
          "ordering proves the paid case is caught first")


def test_descriptor_does_not_lead_with_free_for_you() -> None:
    print("\n[descriptor] the paid-plan descriptor doesn't open with 'Free for you'")
    src = USAGE_TS.read_text()
    m = re.search(r'case "starter":\s*\n\s*return "([^"]+)"', src)
    check("starter descriptor found", m is not None)
    if m:
        text = m.group(1)
        check("it does not claim 'Free for you'", "Free for you" not in text, f"got: {text}")
        check("it names the pooled allowance", "pooled" in text, f"got: {text}")


def test_checkout_floors_quantity_at_one() -> None:
    print("\n[behaviour] checkout floors the seat quantity at 1 (the ratified charge)")
    from services.billing_tiers import billable_seats
    check("a solo workspace computes 0 billable seats", billable_seats("starter", 1) == 0)
    # The floor is what makes a solo checkout bill one unit.
    src = Path("routes/subscription.py").read_text()
    check("checkout applies max(1, billable_seats(...))",
          re.search(r"seat_quantity\s*=\s*max\(1,\s*billable_seats", src) is not None,
          "LS rejects quantity 0; the floor is deliberate, not a bug")
    check("a 3-human team bills 2 seats", billable_seats("starter", 3) == 2)


def main() -> int:
    print("=" * 74)
    print("ADR-445 §7 P2 amendment — the solo-checkout copy contract")
    print("=" * 74)
    test_upgrade_label_is_not_per_seat()
    test_seat_unit_label_stays_deleted()
    test_paid_solo_is_not_told_their_seat_is_free()
    test_descriptor_does_not_lead_with_free_for_you()
    test_checkout_floors_quantity_at_one()
    print("\n" + "=" * 74)
    print(f"  {PASSED} passed, {FAILED} failed")
    print("=" * 74)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
