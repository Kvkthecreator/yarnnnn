"""ADR-396 regression gate — Type-B subscription over the metered balance.

The plan tier grants a monthly INCLUDED ALLOWANCE; the topped-up balance is the
OVERAGE pool beneath it. Draw order: allowance → balance → hard-stop at zero.

Pure-Python structural gate (no DB, no LS API). Asserts:
  1. billing_tiers: free/starter/pro invariants — free is $0/no-allowance/tightest
     ceilings; ceilings widen monotonically; free has no LS variant.
  2. tier resolution: normalize_tier coerces unknown → free; PAID_TIERS = the two
     paid ones; variant round-trips (tier_for_variant_id ∘ variant_id_for_tier).
  3. THE DRAW-ORDER INVARIANT: the grant-time surviving-top-ups formula
     min(old_balance, max(0, effective)) implements "allowance expires, top-ups
     survive" across all spend regimes (S≤A, A<S<A+T, S≥A+T).
  4. migration 194: the RPC draws against (allowance_usd + balance_usd) anchored
     on allowance_granted_at → subscription_refill_at → created_at; the legacy
     $20 subscription_refill RESET is gone from grant_balance; allowance_grant is
     a valid balance_transactions kind.
  5. subscription route: dynamic top-up bounds ($5–$500); custom_price is cents;
     the webhook reads the ACTUAL PAID TOTAL (attributes.total), not a variant map.
  6. retention gate: the GC clamps the declared window to the tier ceiling.
"""

import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)


def _check(label, ok, detail=""):
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}" + (f" — {detail}" if detail and not ok else ""))
    return bool(ok)


def _surviving_topups(old_allowance, old_topups, spend):
    """Reference impl of the grant-time banking rule (mirrors grant_allowance).
    Allowance-first draw: effective = (A + T) − S; surviving = min(T, max(0, eff))."""
    effective = (old_allowance + old_topups) - spend
    return round(min(old_topups, max(0.0, effective)), 4)


def _grant_is_duplicate(granted_period, current_allowance, period_anchor, allowance_usd):
    """Reference impl of the grant idempotency guard (mirrors grant_allowance).
    A grant is a duplicate (no-op, no re-anchor) iff the period was already granted
    AND the allowance amount is unchanged. A moved period or changed amount re-grants.
    When period_anchor is None (top-ups / legacy) the guard is inert (never duplicate)."""
    return (
        period_anchor is not None
        and granted_period is not None
        and granted_period == period_anchor
        and round(current_allowance, 4) == round(allowance_usd, 4)
    )


def main():
    results = []

    # ── 1. Tier config invariants ──────────────────────────────────────────────
    from services import billing_tiers as bt

    free = bt.tier_spec("free")
    starter = bt.tier_spec("starter")
    pro = bt.tier_spec("pro")

    results.append(_check(
        "free tier is the floor: $0 price, $0 allowance",
        free["price_usd"] == 0 and free["monthly_allowance_usd"] == 0,
    ))
    results.append(_check(
        "retention ceiling widens free < starter < pro",
        free["retention_max_days"] < starter["retention_max_days"] < pro["retention_max_days"],
    ))
    results.append(_check(
        "allowance widens free < starter < pro",
        free["monthly_allowance_usd"] < starter["monthly_allowance_usd"] < pro["monthly_allowance_usd"],
    ))
    results.append(_check(
        "connector ceiling: free capped, pro unlimited (None)",
        isinstance(free["connector_max"], int) and pro["connector_max"] is None,
    ))
    results.append(_check(
        "free has no LS subscription variant env; paid tiers do",
        free["ls_variant_env"] is None and starter["ls_variant_env"] and pro["ls_variant_env"],
    ))

    # ── 2. Tier resolution ─────────────────────────────────────────────────────
    results.append(_check(
        "normalize_tier: unknown/None → free; known tiers pass through",
        bt.normalize_tier(None) == "free" and bt.normalize_tier("bogus") == "free"
        and bt.normalize_tier("pro") == "pro"
        # ADR-439 — `enterprise` is now a REAL tier (not an unknown → free).
        and bt.normalize_tier("enterprise") == "enterprise",
    ))
    results.append(_check(
        "PAID_TIERS = (starter, pro, enterprise); DEFAULT_TIER = free",  # ADR-439 adds enterprise
        set(bt.PAID_TIERS) == {"starter", "pro", "enterprise"} and bt.DEFAULT_TIER == "free",
    ))

    # variant round-trip (env-driven — set them for the test window)
    os.environ["LEMONSQUEEZY_STARTER_VARIANT_ID"] = "var_starter_1"
    os.environ["LEMONSQUEEZY_PRO_VARIANT_ID"] = "var_pro_1"
    results.append(_check(
        "variant round-trip: tier_for_variant_id ∘ variant_id_for_tier == identity",
        bt.tier_for_variant_id(bt.variant_id_for_tier("starter")) == "starter"
        and bt.tier_for_variant_id(bt.variant_id_for_tier("pro")) == "pro",
    ))
    results.append(_check(
        "unknown variant id → None (not a paid tier)",
        bt.tier_for_variant_id("var_bogus") is None,
    ))

    # ── 3. THE DRAW-ORDER INVARIANT (allowance expires, top-ups survive) ────────
    A, T = 15.0, 20.0  # allowance, top-ups
    # S≤A: nothing of top-ups consumed → all $20 survive
    results.append(_check(
        "draw order S≤A: full top-ups survive",
        _surviving_topups(A, T, spend=10.0) == 20.0,
    ))
    # A<S<A+T: allowance fully gone, some top-ups eaten → T−(S−A)
    results.append(_check(
        "draw order A<S<A+T: top-ups partially consumed (T−(S−A))",
        _surviving_topups(A, T, spend=25.0) == 10.0,  # 20 − (25−15)
    ))
    # S≥A+T: pool exhausted → 0 survive (hard-stop territory)
    results.append(_check(
        "draw order S≥A+T: pool exhausted → 0 top-ups survive",
        _surviving_topups(A, T, spend=40.0) == 0.0,
    ))
    # zero-allowance (free tier top-up): every dollar of spend eats top-ups
    results.append(_check(
        "free tier (A=0): spend eats top-ups directly",
        _surviving_topups(0.0, 20.0, spend=8.0) == 12.0,
    ))

    # ── 4. Migration 194 structural ────────────────────────────────────────────
    mig_path = os.path.join(_ROOT, "supabase", "migrations", "194_adr396_type_b_subscription.sql")
    mig = open(mig_path).read() if os.path.exists(mig_path) else ""
    results.append(_check("migration 194 exists", bool(mig), mig_path))
    results.append(_check(
        "migration adds subscription_tier + allowance_usd + allowance_granted_at",
        "subscription_tier" in mig and "allowance_usd" in mig and "allowance_granted_at" in mig,
    ))
    results.append(_check(
        "RPC draws against (allowance_usd + balance_usd)",
        re.search(r"allowance_usd\s*\+\s*w\.balance_usd", mig) is not None
        or "w.allowance_usd + w.balance_usd" in mig,
    ))
    results.append(_check(
        "RPC anchor precedence: allowance_granted_at → subscription_refill_at → created_at",
        bool(re.search(r"allowance_granted_at\s*,\s*\n?\s*w?\.?subscription_refill_at\s*,\s*\n?\s*w?\.?created_at", mig, re.DOTALL))
        or ("allowance_granted_at" in mig and "subscription_refill_at" in mig and "created_at" in mig
            and mig.index("allowance_granted_at") < mig.index("w.subscription_refill_at" if "w.subscription_refill_at" in mig else "subscription_refill_at")),
    ))
    results.append(_check(
        "balance_transactions kind CHECK gains allowance_grant",
        "allowance_grant" in mig,
    ))

    # ── 5. platform_limits: legacy reset gone, allowance grant present ──────────
    pl = open(os.path.join(_HERE, "services", "platform_limits.py")).read()
    results.append(_check(
        "grant_allowance() exists (the monthly cycle event)",
        "def grant_allowance(" in pl,
    ))
    results.append(_check(
        "surviving-top-ups formula present: min(old_balance, max(0.0, effective))",
        "min(old_balance, max(0.0, effective))" in pl,
    ))
    results.append(_check(
        "legacy subscription_refill $20 balance-RESET removed from grant_balance",
        'kind="subscription_refill"' not in pl and "balance_usd = $20" not in pl
        and "grant $20 balance" not in pl.lower(),
    ))
    results.append(_check(
        "_spend_anchor helper unifies the RPC anchor precedence",
        "def _spend_anchor(" in pl and "allowance_granted_at" in pl,
    ))

    # ── 6. Subscription route: dynamic top-up + paid-total webhook ─────────────
    sub = open(os.path.join(_HERE, "routes", "subscription.py")).read()
    results.append(_check(
        "top-up bounds declared ($5..$500)",
        "TOPUP_MIN_USD = 5" in sub and "TOPUP_MAX_USD = 500" in sub,
    ))
    results.append(_check(
        "top-up sets custom_price in cents",
        'custom_price_cents = int(amount) * 100' in sub and '"custom_price"' in sub,
    ))
    results.append(_check(
        "webhook reads ACTUAL PAID TOTAL (attributes.total), not a variant→amount map",
        'attrs.get("total")' in sub and "TOPUP_AMOUNTS" not in sub,
    ))
    results.append(_check(
        "subscription checkout resolves tier → LS variant; payment_success grants allowance",
        "variant_id_for_tier(" in sub and "grant_allowance(" in sub,
    ))
    results.append(_check(
        "no legacy fixed top-up variant env vars",
        "LEMONSQUEEZY_TOPUP_10_VARIANT_ID" not in sub
        and "LEMONSQUEEZY_TOPUP_25_VARIANT_ID" not in sub,
    ))

    # ── 7. Retention gate clamps to tier ceiling ───────────────────────────────
    cr = open(os.path.join(_HERE, "services", "connector_retention.py")).read()
    results.append(_check(
        "GC clamps declared window to the tier ceiling",
        "retention_max_days_for_user(" in cr and "tier_max_days=tier_max" in cr,
    ))

    # ── 8. Grant idempotency (multi-event webhook storm) ───────────────────────
    # LS fires created + updated + payment_success for one purchase; only the first
    # may re-anchor. THE INVARIANT: a duplicate event (same period, same amount) is
    # a no-op; a new period or a tier change re-grants.
    P1, P2 = "2026-08-02T00:00:00+00:00", "2026-09-02T00:00:00+00:00"
    results.append(_check(
        "duplicate event (same period + amount) is a no-op",
        _grant_is_duplicate(granted_period=P1, current_allowance=15.0, period_anchor=P1, allowance_usd=15.0) is True,
    ))
    results.append(_check(
        "new billing period re-grants (renews_at moved)",
        _grant_is_duplicate(granted_period=P1, current_allowance=15.0, period_anchor=P2, allowance_usd=15.0) is False,
    ))
    results.append(_check(
        "tier change re-grants (allowance amount differs)",
        _grant_is_duplicate(granted_period=P1, current_allowance=15.0, period_anchor=P1, allowance_usd=45.0) is False,
    ))
    results.append(_check(
        "first grant of an ungranted period re-grants (allowance_period NULL)",
        _grant_is_duplicate(granted_period=None, current_allowance=0.0, period_anchor=P1, allowance_usd=15.0) is False,
    ))
    results.append(_check(
        "top-up path is inert (period_anchor None → never a duplicate)",
        _grant_is_duplicate(granted_period=P1, current_allowance=15.0, period_anchor=None, allowance_usd=15.0) is False,
    ))
    # Source wiring: the guard exists, keys off allowance_period (NOT expires_at),
    # migration 195 adds the column, and both webhook callers pass period_anchor.
    results.append(_check(
        "grant_allowance takes period_anchor + guards on allowance_period",
        "period_anchor" in pl and "allowance_period" in pl
        and 'granted_period == period_anchor' in pl,
    ))
    results.append(_check(
        "guard keys off allowance_period, NOT subscription_expires_at",
        "allowance_period" in pl
        and ".select(\"balance_usd, allowance_usd, allowance_period\")" in pl,
    ))
    mig195_path = os.path.join(_ROOT, "supabase", "migrations", "195_adr396_allowance_period_idempotency.sql")
    mig195 = open(mig195_path).read() if os.path.exists(mig195_path) else ""
    results.append(_check(
        "migration 195 adds workspaces.allowance_period",
        "allowance_period" in mig195 and "ADD COLUMN" in mig195,
    ))
    results.append(_check(
        "both webhook grant calls pass period_anchor=renews_at",
        sub.count("period_anchor=renews_at") >= 2,
    ))

    # ── Summary ────────────────────────────────────────────────────────────────
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"\nADR-396 gate: {passed}/{total} PASS")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
