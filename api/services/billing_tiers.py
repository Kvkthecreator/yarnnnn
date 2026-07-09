"""Subscription tier config — ADR-396 (Type-B subscription over the metered balance).

The single source of truth for the plan tiers. A tier is a plan the operator
subscribes to; it grants a monthly INCLUDED ALLOWANCE (dollars, drawn before the
topped-up balance) and sets two ceilings: connector retention window + connector
count (ADR-396's "two gates"). The metered spend itself lives in execution_events
(ADR-291) — this module never touches cost math; it only reads/derives the tier
and its ceilings.

The draw order (ADR-396 §3): monthly allowance → topped-up balance → hard-stop at
zero. The allowance is granted on each billing cycle (see grant_balance's
`allowance_grant` kind); top-ups are the overage pool and are NEVER reset by a
refill. "Balance IS the currency" — no credit unit.

NUMBERS (ADR-396 §7, relaxed 2026-07-01): the base prices + allowance sizes below
are LAUNCH-TEST values, set to test in front of a first user, NOT claimed correct.
The economics (docs/monetization/UNIT-ECONOMICS) bound the paid base to a ~$15–25
band; these sit at/above that band and are reversible against first-customer
evidence. They are the only place numbers live — checkout, retention gate, and the
FE all derive from here.

File-format note (ADR-254): this is Python code config, not a workspace file — the
tier→ceiling mapping is machine dispatch, kept in one module per Singular
Implementation. The per-operator overrides (declared retention) still live in
governance/_retention.yaml; this module supplies only the tier CEILING that clamps
it.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, TypedDict

logger = logging.getLogger(__name__)


class TierSpec(TypedDict):
    """One subscription tier. `ls_variant_env` names the Lemon Squeezy variant-id
    env var for the paid tiers (None for free — free has no checkout)."""
    label: str
    price_usd: float                 # monthly subscription price (0 for free)
    monthly_allowance_usd: float     # included allowance granted each cycle
    retention_max_days: int          # connector raw-lane retention ceiling (gate 1)
    connector_max: Optional[int]     # connector count ceiling; None = unlimited (gate 2)
    ls_variant_env: Optional[str]    # env var holding the LS subscription variant id
    # ── ADR-429 Axis ② — the seat axis (SHIPPED DORMANT, §5a) ─────────────────
    # A seat = a HUMAN member's access (role ∈ {owner, member}); AI principals are
    # free (never counted). `included_seats` humans are covered by the base;
    # additional humans bill `additional_seat_usd` each. DORMANT at launch:
    # `additional_seat_usd = 0` → billable-seat math runs and returns $0, so N=1
    # and existing multi-human workspaces are byte-identical. Activation = set a
    # non-zero fee here (one config change, no code). The seat=access carve
    # (ADR-429 §3): a seat NEVER carries a usage bucket — usage is the shared meter.
    included_seats: int              # humans covered by the base (owner-inclusive)
    additional_seat_usd: float       # $/additional human/mo (0 = dormant, ADR-429 §5a)


# ── The tiers ────────────────────────────────────────────────────────────────
# free → starter → pro. Free is the floor: no allowance (top-up to use), the
# tightest ceilings. The $3 signup grant (Postgres trigger) lands in balance_usd
# and lets a free workspace try the product before topping up.

TIER_CONFIG: dict[str, TierSpec] = {
    "free": {
        "label": "Free",
        "price_usd": 0.0,
        "monthly_allowance_usd": 0.0,
        "retention_max_days": 7,
        "connector_max": 1,
        "ls_variant_env": None,
        # ADR-429 §5a — seat axis DORMANT ($0). Free is single-seat by design
        # (a shared commons is a paid capability — §5/§9 open question); the
        # additional-seat fee is $0 everywhere until activation.
        "included_seats": 1,
        "additional_seat_usd": 0.0,
    },
    "starter": {
        "label": "Starter",
        "price_usd": 19.0,
        "monthly_allowance_usd": 15.0,
        "retention_max_days": 30,
        "connector_max": 3,
        "ls_variant_env": "LEMONSQUEEZY_STARTER_VARIANT_ID",
        # ADR-429 §5a — DORMANT. Placeholder activation value would be ~$12
        # (the ADR-429 §5 launch-test hypothesis); $0 until the operator flips it.
        "included_seats": 1,
        "additional_seat_usd": 0.0,
    },
    "pro": {
        "label": "Pro",
        "price_usd": 49.0,
        "monthly_allowance_usd": 45.0,
        "retention_max_days": 90,
        "connector_max": None,  # unlimited
        "ls_variant_env": "LEMONSQUEEZY_PRO_VARIANT_ID",
        # ADR-429 §5a — DORMANT ($0).
        "included_seats": 1,
        "additional_seat_usd": 0.0,
    },
}

DEFAULT_TIER = "free"
PAID_TIERS = ("starter", "pro")


def normalize_tier(raw: Optional[str]) -> str:
    """Coerce a stored tier string to a known tier, defaulting to free.

    Legacy note: pre-ADR-396 the `subscription_status` column carried
    'free'/'pro'/'starter' (an LS-variant flag, not a plan tier). This reads the
    NEW `subscription_tier` column; unknown/None → free (the safe floor)."""
    if raw in TIER_CONFIG:
        return raw  # type: ignore[return-value]
    return DEFAULT_TIER


def get_tier(client: Any, user_id: str) -> str:
    """The workspace's active subscription tier ('free'|'starter'|'pro').

    Reads workspaces.subscription_tier (migration 194) for the ACTING workspace
    (ADR-407 Phase 0 — a member's ceilings follow the granted workspace's tier,
    not their own singleton; owner-resolution fallback is byte-identical N=1).
    Fail-safe to free on any error — free never grants an allowance or widens a
    ceiling, so an unknown state can't over-provision."""
    try:
        from services.workspace_context import effective_workspace_id
        ws = effective_workspace_id(user_id)
        query = client.table("workspaces").select("subscription_tier")
        query = query.eq("id", ws) if ws else query.eq("owner_id", user_id)
        result = query.limit(1).execute()
        rows = result.data or []
        if rows:
            return normalize_tier(rows[0].get("subscription_tier"))
        return DEFAULT_TIER
    except Exception as e:
        logger.warning(f"[TIER] get_tier failed for {user_id}: {e}")
        return DEFAULT_TIER


def tier_spec(tier: str) -> TierSpec:
    """The spec for a tier string (normalized)."""
    return TIER_CONFIG[normalize_tier(tier)]


def tier_allowance_usd(tier: str) -> float:
    """Monthly included allowance in dollars for a tier."""
    return tier_spec(tier)["monthly_allowance_usd"]


def tier_retention_max_days(tier: str) -> int:
    """Connector-retention window ceiling (days) for a tier — ADR-396 gate 1,
    passed to connector_retention.resolve_retention_days(tier_max_days=)."""
    return tier_spec(tier)["retention_max_days"]


def tier_connector_max(tier: str) -> Optional[int]:
    """Connector-count ceiling for a tier (None = unlimited) — ADR-396 gate 2."""
    return tier_spec(tier)["connector_max"]


# ── ADR-429 Axis ② — seat math (SHIPPED DORMANT, §5a) ─────────────────────────
# A seat is a HUMAN member (role ∈ {owner, member}). AI principals (foreign-llm,
# a2a, own-agent, platform) are free — never counted. The math runs live but with
# a $0 additional-seat fee it bills nothing, so N=1 + existing workspaces are
# byte-identical (§5a). Activation = a non-zero `additional_seat_usd` in TIER_CONFIG.

HUMAN_SEAT_ROLES = ("owner", "member")


def tier_included_seats(tier: str) -> int:
    """Humans covered by the base (owner-inclusive) for a tier."""
    return tier_spec(tier)["included_seats"]


def tier_additional_seat_usd(tier: str) -> float:
    """$/additional human seat/mo for a tier (0.0 = DORMANT, ADR-429 §5a)."""
    return tier_spec(tier)["additional_seat_usd"]


def count_human_seats(client: Any, workspace_id: str) -> int:
    """Count active HUMAN members of a workspace (role ∈ {owner, member}).

    The seat axis bills humans; AI principals (foreign-llm/a2a/own-agent/platform)
    are free and excluded. Reads active `principal_grants` — the same roster the
    members surface + the UserMenu people-count derive from (audit §5). Fail-safe
    to 1 (a workspace always has at least its owner) so a read error can never
    over-count and over-bill."""
    try:
        result = (
            client.table("principal_grants")
            .select("principal_id, role")
            .eq("workspace_id", workspace_id)
            .eq("status", "active")
            .in_("role", list(HUMAN_SEAT_ROLES))
            .execute()
        )
        rows = result.data or []
        # Distinct principals (defensive — a principal should hold one active grant).
        humans = {r.get("principal_id") for r in rows if r.get("principal_id")}
        return max(1, len(humans))
    except Exception as e:
        logger.warning(f"[SEATS] count_human_seats failed for {workspace_id}: {e}")
        return 1


def billable_seats(tier: str, human_count: int) -> int:
    """Additional humans billed beyond the base's included seats.

    `max(0, human_count − included_seats)`. At N=1 (solo) or when a tier includes
    every human present, this is 0 — the seat axis is invisible."""
    return max(0, human_count - tier_included_seats(tier))


def seat_fee_usd(tier: str, human_count: int) -> float:
    """Total monthly seat fee for a workspace: billable_seats × additional_seat_usd.

    DORMANT (§5a): with `additional_seat_usd = 0` this is always $0.0 — the seat
    math is exercised and correct, but nothing is charged until activation."""
    return round(billable_seats(tier, human_count) * tier_additional_seat_usd(tier), 2)


def retention_max_days_for_user(client: Any, user_id: str) -> int:
    """Resolve the retention ceiling for a user via their active tier. The one
    call the retention GC + FE read route use to clamp the declared window."""
    return tier_retention_max_days(get_tier(client, user_id))


def variant_id_for_tier(tier: str) -> Optional[str]:
    """Resolve the Lemon Squeezy subscription variant id for a paid tier from its
    env var. Returns None for free or when the env var is unset (checkout should
    then 500 with a clear 'not configured' error, matching the existing pattern)."""
    import os
    spec = tier_spec(tier)
    env = spec["ls_variant_env"]
    if not env:
        return None
    return os.getenv(env)


def tier_for_variant_id(variant_id: str) -> Optional[str]:
    """Reverse map an LS subscription variant id → tier, for the webhook. Returns
    None if the variant matches no configured paid tier."""
    import os
    for tier in PAID_TIERS:
        env = TIER_CONFIG[tier]["ls_variant_env"]
        if env and os.getenv(env) == variant_id:
            return tier
    return None


def public_tier_ladder() -> list[dict]:
    """The tier ladder for the public pricing page + the billing pane. Dollar
    prices are shown on the PUBLIC pricing page (a catalog, not a bill — ADR-396's
    hide-$ contract governs the in-app ACTIVITY surfaces, not the price list).
    Allowance is expressed as an included-usage descriptor, not a raw $ meter."""
    ladder = []
    for tier in ("free", "starter", "pro"):
        spec = TIER_CONFIG[tier]
        ladder.append({
            "tier": tier,
            "label": spec["label"],
            "price_usd": spec["price_usd"],
            "monthly_allowance_usd": spec["monthly_allowance_usd"],
            "retention_max_days": spec["retention_max_days"],
            "connector_max": spec["connector_max"],
            # ADR-429 Axis ② — seat info for the pricing page (Phase 3). Dormant
            # while additional_seat_usd = 0; the page reads `additional_seat_usd`
            # to decide whether to show per-seat pricing at all (§5a).
            "included_seats": spec["included_seats"],
            "additional_seat_usd": spec["additional_seat_usd"],
        })
    return ladder


__all__ = [
    "TIER_CONFIG",
    "DEFAULT_TIER",
    "PAID_TIERS",
    "TierSpec",
    "normalize_tier",
    "get_tier",
    "tier_spec",
    "tier_allowance_usd",
    "tier_retention_max_days",
    "tier_connector_max",
    "retention_max_days_for_user",
    "variant_id_for_tier",
    "tier_for_variant_id",
    "public_tier_ladder",
    # ADR-429 Axis ② — seat helpers (dormant §5a)
    "HUMAN_SEAT_ROLES",
    "tier_included_seats",
    "tier_additional_seat_usd",
    "count_human_seats",
    "billable_seats",
    "seat_fee_usd",
]
