"""ADR-445 §6 gate — the launch prices live in ONE place.

WHY (the audit finding, 2026-07-21): ADR-445 §6 says the numbers "live in one
place (`billing_tiers.py::TIER_CONFIG`)". The frontend had NINE independent
hardcoded copies of $20/$15 (plus $3 and $5) across the pricing page, landing,
FAQ, llms.txt, metadata, and the usage helpers. All were correct at the time —
which is exactly the danger: §6 also says these are launch-test values that
"change freely against evidence", so the first price tune silently desynchronises
the marketing surface from what the backend actually charges.

The FE now mirrors the backend once (`lib/subscription/usage.ts`:
TIER_SEAT_PRICE_USD / TIER_ALLOWANCE_USD / SIGNUP_GRANT_USD / TOPUP_MIN_USD) and
copy interpolates `PRICE_COPY`. This gate enforces both halves:

  (a) the FE mirror still AGREES with billing_tiers.py (the real drift risk —
      a backend tune that the FE never learns about); and
  (b) no marketing surface re-types a bare price literal.

Usage:
    cd api
    python test_adr445_price_single_source.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PASSED = 0
FAILED = 0

WEB = Path("../web")
USAGE_TS = WEB / "lib/subscription/usage.ts"

# Copy surfaces that must interpolate, never re-type a price.
COPY_SURFACES = [
    "app/pricing/page.tsx",
    "app/faq/page.tsx",
    "app/llms.txt/route.ts",
    "lib/metadata.ts",
]

# Prices that must never appear as bare literals in copy. ($0 is fine — it is a
# concept ("free"), not a tunable price.)
BANNED = [r"\$20\b", r"\$15\b", r"\$45\b"]


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        print(f"  ✓ {label}")
        PASSED += 1
    else:
        print(f"  ✗ {label}{(' — ' + detail) if detail else ''}")
        FAILED += 1


def _ts_number(src: str, const: str, key: str) -> float | None:
    """Pull `key: <number>` out of a `const NAME: Record<...> = { ... }` block."""
    m = re.search(rf"export const {const}[^=]*=\s*\{{(.*?)\}};", src, re.S)
    if not m:
        return None
    km = re.search(rf"\b{key}\s*:\s*([0-9.]+)", m.group(1))
    return float(km.group(1)) if km else None


def test_fe_mirror_matches_backend() -> None:
    print("\n[mirror] the FE constants equal billing_tiers.py TIER_CONFIG")
    from services.billing_tiers import TIER_CONFIG
    src = USAGE_TS.read_text()
    for tier in ("free", "starter", "pro"):
        fe_seat = _ts_number(src, "TIER_SEAT_PRICE_USD", tier)
        be_seat = TIER_CONFIG[tier]["additional_seat_usd"]
        check(f"{tier}: seat price {fe_seat} == backend {be_seat}", fe_seat == be_seat)
        fe_allow = _ts_number(src, "TIER_ALLOWANCE_USD", tier)
        be_allow = TIER_CONFIG[tier]["monthly_allowance_usd"]
        check(f"{tier}: allowance {fe_allow} == backend {be_allow}", fe_allow == be_allow)


def test_copy_has_no_bare_price_literals() -> None:
    print("\n[copy] marketing surfaces interpolate; they never re-type a price")
    for rel in COPY_SURFACES:
        p = WEB / rel
        if not p.exists():
            check(f"{rel} exists", False)
            continue
        offenders = []
        for i, line in enumerate(p.read_text().split("\n"), 1):
            stripped = line.strip()
            # Comments may quote a number for explanation.
            if stripped.startswith(("//", "*", "/*")):
                continue
            for pat in BANNED:
                if re.search(pat, line):
                    offenders.append(f"{i}: {stripped[:70]}")
        check(f"{rel} has no bare $ price literal", not offenders,
              "; ".join(offenders[:3]))


def test_price_copy_is_derived_not_typed() -> None:
    print("\n[source] PRICE_COPY is built FROM the constants, not hand-typed")
    src = USAGE_TS.read_text()
    m = re.search(r"export const PRICE_COPY\s*=\s*\{(.*?)\}\s*as const;", src, re.S)
    check("PRICE_COPY exists", m is not None)
    if m:
        body = m.group(1)
        # Strip doc comments before checking: each field documents its rendered
        # output (/** "$20" — the per-seat price */), which is genuinely useful.
        # Only the VALUES must be interpolated.
        code = "\n".join(
            l for l in body.split("\n")
            if not l.strip().startswith(("//", "*", "/*"))
        )
        check("every field interpolates a constant",
              "${" in code and not re.search(r'"\$\d', code),
              "a hardcoded value here would defeat the whole point")
        for const in ("TIER_SEAT_PRICE_USD", "TIER_ALLOWANCE_USD",
                      "SIGNUP_GRANT_USD", "TOPUP_MIN_USD"):
            check(f"derives from {const}", const in body)


def test_surfaces_import_the_source() -> None:
    print("\n[wiring] each copy surface imports PRICE_COPY")
    for rel in COPY_SURFACES:
        p = WEB / rel
        if not p.exists():
            continue
        src = p.read_text()
        check(f"{rel} imports PRICE_COPY",
              "PRICE_COPY" in src and "lib/subscription/usage" in src)


def main() -> int:
    print("=" * 74)
    print("ADR-445 §6 — launch prices have a single source")
    print("=" * 74)
    test_fe_mirror_matches_backend()
    test_copy_has_no_bare_price_literals()
    test_price_copy_is_derived_not_typed()
    test_surfaces_import_the_source()
    print("\n" + "=" * 74)
    print(f"  {PASSED} passed, {FAILED} failed")
    print("=" * 74)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
