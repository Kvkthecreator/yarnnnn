"""Subscription tier config — the TWO-AXIS pricing model (ADR-445, supersedes ADR-429).

The single source of truth for the plan tiers. Pricing has TWO axes, both paid by
the workspace OWNER (ADR-445 §4):

  ① SEATS (per human) — seat 1 (the owner) is FREE; each additional human is a
     priced seat (`additional_seat_usd`/mo). The per-seat price IS the paid
     subscription — there is NO separate per-workspace "base fee" (that was
     ADR-429's Axis ①, collapsed here). A workspace with 1 human is free; a
     workspace with ≥2 humans is paid at (humans − 1) × the seat fee. AI principals
     (foreign-llm/a2a/own-agent/platform) are NEVER seats and NEVER charged.

  ② METERED USAGE (pooled) — the workspace draws one shared pool (monthly allowance
     → topped-up balance → hard-stop at zero, ADR-396). Every principal draws the
     same pool; usage is attributed per principal (execution_events, ADR-291). The
     owner funds it. This module never touches cost math — it only reads/derives the
     tier, its allowance, and its two connector gates (retention window + count).

The carve that keeps the axes honest (ADR-445 §4, from ADR-429 §3): **a seat buys
ACCESS, not usage** — a seat never carries its own token bucket; usage is the shared
pool. No double-charge (ADR-396 invariant preserved).

The draw order (ADR-396 §3): monthly allowance → topped-up balance → hard-stop at
zero. The allowance is granted on each billing cycle (grant_allowance); top-ups are
the overage pool and are NEVER reset by a refill. "Balance IS the currency" — no
credit unit.

`monthly_allowance_usd` is the WORKSPACE-wide pooled allowance the paid plan grants
(not per-seat — the meter is pooled). `additional_seat_usd` is the LIVE seat price
(ADR-445 reverses ADR-429 §5a's dormant launch — in the two-axis model seats ARE the
team-revenue path). `included_seats` is the BILLING BASELINE only (humans covered
before the per-seat fee); it is NOT a hard headcount cap — a paid workspace grows its
team freely, each new human accruing a billed seat (the only headcount gate is the
free→paid boundary at the invite route: a Free workspace's 2nd human requires the
paid plan — ADR-445 §7 Phase 1).

NUMBERS (ADR-445 §6, ADR-396 §7 discipline): the seat price + allowance sizes below
are LAUNCH-TEST values a first paying team resolves, NOT claimed correct. The seat
price sits at the low end of the reference Team band (~$25–30/seat, OpenAI/Anthropic);
reversible against evidence. They are the only place numbers live — checkout, the
retention gate, and the FE all derive from here.

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
    # ── ADR-445 Axis ① — SEATS (per human; the paid subscription itself) ──────
    # A seat = a HUMAN member's access (role ∈ {owner, member}); AI principals are
    # free (never counted). `included_seats` = the BILLING BASELINE — humans covered
    # before the per-seat fee (seat 1 = the owner = free). Each additional human
    # bills `additional_seat_usd`/mo. This IS the paid subscription (no separate base
    # fee — ADR-429's Axis ① collapsed, ADR-445 §4). `included_seats` is NOT a hard
    # cap: a paid workspace grows freely (each new human = a billed seat); the only
    # headcount gate is the free→paid boundary (a Free workspace's 2nd human needs a
    # paid plan — enforced at the invite route, ADR-445 §7 Phase 1). The seat=access
    # carve (ADR-445 §4): a seat NEVER carries a usage bucket — usage is the shared
    # pooled meter (Axis ②).
    included_seats: int              # billing baseline: humans covered before the seat fee (owner-inclusive)
    additional_seat_usd: float       # $/additional human/mo (LIVE at launch — ADR-445 §6)
    # ── ADR-429 §12 — the tier structure collapse ─────────────────────────────
    # `hidden` marks a tier that is NOT offered at launch (not on the pricing page,
    # not an upgrade target, not in the ladder) — its config survives so it can be
    # un-hidden with one flag. `pro` is hidden until the connector-capture lane
    # ships (its retention/connector ceilings become real differentiators again,
    # ADR-429 §12.1); launch offers Free + one paid plan (`starter`) only. A live
    # `starter`/`free` workspace is unaffected; only which tiers are *offered*.
    hidden: bool                     # not offered at launch (§12.1); config retained
    # ── ADR-439 — BYOK availability (enterprise capability) ────────────────────
    # True iff this tier MAY turn on BYOK (the customer's own LLM key powers the
    # member chat lanes; ADR-439 §3). Availability is the tier capability;
    # ENGAGEMENT is a per-workspace default-OFF toggle (`workspaces.byok_enabled`).
    # Only `enterprise` is True — BYOK is enterprise-only but optional within it.
    byok_available: bool


# ── The tiers ────────────────────────────────────────────────────────────────
# ADR-445 — the two-axis model. LAUNCH is Free + ONE paid plan. The paid plan is
# SEAT-priced (the subscription IS the per-additional-human seat fee; no separate
# base fee) + a shared pooled allowance. The free→paid boundary is the 2nd human:
#   • `free`    — the floor: SOLO (included_seats: 1 = the owner alone), no
#                 allowance (top-up/signup-grant to use). Inviting a 2nd human
#                 requires the paid plan (the free→paid boundary, ADR-445 §6). A
#                 time-boxed "try a teammate" trial is a deferred growth funnel
#                 (ADR-445 §9), NOT a pricing change.
#   • `starter` — THE single paid plan. $20/additional human/mo (seat 2+) + a $15
#                 workspace-wide pooled allowance. Seat 1 (owner) is free; the plan
#                 grows the team freely, each new human a billed seat. Its display
#                 NAME is a Phase-3 marketing decision (keep-the-slug, name-at-render
#                 — working name "Paid"). The `starter` KEY is kept (no data
#                 migration: the 1 live starter row stays valid).
#   • `pro`     — DORMANT (`hidden: True`). Returns as a 2nd seat-priced plan with
#                 richer connector gates when the capture lane ships
#                 (CONNECTOR_CAPTURE_ENABLED). Config survives (one-flag un-hide);
#                 not offered, not on the pricing page, not an upgrade target.
# The 3 enum values are KEPT in the CHECK constraint — this is a PRODUCT decision
# (which tiers are offered + what the price MEANS), not a schema change.

TIER_CONFIG: dict[str, TierSpec] = {
    "free": {
        "label": "Free",
        "price_usd": 0.0,
        "monthly_allowance_usd": 0.0,
        "retention_max_days": 7,
        "connector_max": 1,
        "ls_variant_env": None,
        # ADR-445 §6 — Free is SOLO (the owner alone). Inviting a 2nd human is the
        # free→paid boundary (requires the paid plan; gated at the invite route).
        # A "try a teammate" trial is a deferred growth funnel (§9), not this.
        "included_seats": 1,
        "additional_seat_usd": 0.0,  # free tier never charges a seat
        "hidden": False,
        "byok_available": False,  # ADR-439 — BYOK is enterprise-only
    },
    "starter": {
        # ADR-445 §6 — THE single paid plan, SEAT-priced (the subscription IS the
        # per-additional-human fee; no separate base). $20/additional human/mo +
        # a $15 workspace-wide pooled allowance (~190 judgment calls; clears a
        # Light user's ~$6/mo with headroom). $20/seat sits at the low end of the
        # reference Team band (~$25–30). A real launch number, still reversible.
        # Display name is Phase-3 copy (working name "Paid").
        "label": "Starter",
        # price_usd = the per-seat unit price. It is NOT a standalone base fee — a
        # solo owner (1 human) pays $0 subscription (usage-only); a team pays
        # (humans − 1) × price_usd. Kept named `price_usd` for the LS variant + FE
        # derivation; its MEANING is the seat price (ADR-445 §4).
        "price_usd": 20.0,
        "monthly_allowance_usd": 15.0,   # workspace-wide pooled allowance (not per-seat)
        "retention_max_days": 30,
        "connector_max": 3,
        "ls_variant_env": "LEMONSQUEEZY_STARTER_VARIANT_ID",
        # ADR-445 §4/§6 — seat fee is LIVE at launch. included_seats: 1 = the owner
        # (seat 1 free); each additional human bills additional_seat_usd. NOT a hard
        # cap — the team grows freely, each new human a billed seat.
        "included_seats": 1,
        "additional_seat_usd": 20.0,
        "hidden": False,
        "byok_available": False,  # ADR-439 — BYOK is enterprise-only
    },
    "pro": {
        # ADR-445 — DORMANT (hidden). Returns as a 2nd SEAT-priced plan with richer
        # connector gates when the capture lane ships. Config retained (one-flag
        # un-hide); NOT offered at launch. `additional_seat_usd` set to match the
        # launch seat price so an un-hide is coherent (the tier ladder differentiates
        # on gates/allowance, not seat price); the base numbers are placeholders.
        "label": "Pro",
        "price_usd": 20.0,       # per-seat unit (matches starter; ladder splits on gates)
        "monthly_allowance_usd": 45.0,
        "retention_max_days": 90,
        "connector_max": None,  # unlimited
        "ls_variant_env": "LEMONSQUEEZY_PRO_VARIANT_ID",
        "included_seats": 1,
        "additional_seat_usd": 20.0,
        "hidden": True,  # ADR-445 — not offered until capture ships
        "byok_available": False,  # ADR-439 — BYOK is enterprise-only
    },
    "enterprise": {
        # ADR-439 §9 P1 — the enterprise tier. Its reason to exist is the
        # CAPABILITY BUNDLE (BYOK availability · on-prem lane · custody controls ·
        # support · scale/seats), NOT a fake retention/connector axis. BYOK is a
        # default-OFF toggle INSIDE this tier (byok_available: True), not the tier's
        # definition (ADR-439 §3) — a managed enterprise runs on our keys + meter,
        # byte-identical to lower tiers on the key path.
        #
        # NUMBERS ARE LAUNCH-TEST HYPOTHESES (ADR-396 §7 discipline, as ADR-445's):
        # base + allowance below are placeholders to make the tier real, NOT the
        # decided price. The enterprise price is a per-seat + custody bundle that a
        # first enterprise customer resolves — change freely on evidence. Seat fee
        # is live like every paid tier (ADR-445 §4). Retention/connectors set
        # generous (the bundle isn't sold
        # on them). `hidden: True` — enterprise is SALES-LED, not a self-serve
        # upgrade target on the public ladder (contact-us, not a checkout button).
        "label": "Enterprise",
        "price_usd": 0.0,       # placeholder — sales-led custom pricing, not a checkout price
        "monthly_allowance_usd": 0.0,  # placeholder — sized per contract
        "retention_max_days": 90,
        "connector_max": None,  # unlimited
        "ls_variant_env": "LEMONSQUEEZY_ENTERPRISE_VARIANT_ID",  # unset until a self-serve enterprise checkout exists
        "included_seats": 1,
        "additional_seat_usd": 20.0,  # seat-priced like every paid tier (ADR-445 §4)
        "hidden": True,  # sales-led — not on the self-serve public ladder
        "byok_available": True,  # ADR-439 — THE tier where BYOK may be enabled
    },
}

DEFAULT_TIER = "free"
# PAID_TIERS = every tier with a paid price + LS variant (used by the webhook
# reverse-map). `pro` stays here (its variant still resolves if an old checkout
# exists), but it is `hidden` so it is never OFFERED — see `offered_paid_tiers()`.
PAID_TIERS = ("starter", "pro", "enterprise")


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


# ── ADR-429 §12.1 — offered vs hidden tiers (the launch collapse) ─────────────

def tier_hidden(tier: str) -> bool:
    """True if a tier is NOT offered at launch (dormant config, §12.1). `pro` is
    hidden until the capture lane ships; `free`/`starter` are live."""
    return tier_spec(tier).get("hidden", False)


def offered_paid_tiers() -> tuple[str, ...]:
    """Paid tiers actually OFFERED at launch (not hidden) — the upgrade targets.
    Launch: ('starter',) only (pro is hidden, §12.1). Un-hiding pro restores the
    Starter/Pro split with zero call-site change (this is the single source)."""
    return tuple(t for t in PAID_TIERS if not tier_hidden(t))


# ── ADR-445 Axis ① — seat math (LIVE at launch) ───────────────────────────────
# A seat is a HUMAN member (role ∈ {owner, member}). AI principals (foreign-llm,
# a2a, own-agent, platform) are free — never counted. Seat 1 (the owner) is free;
# each additional human bills `additional_seat_usd`. `billable_seats` = the LS
# subscription quantity. N=1 (solo) always bills $0 seats (only usage); a team pays
# (humans − 1) × the seat fee.

HUMAN_SEAT_ROLES = ("owner", "member")


def tier_included_seats(tier: str) -> int:
    """Billing baseline — humans covered before the per-seat fee (owner-inclusive).

    This is NOT a hard headcount cap (ADR-445 §4): a paid workspace grows its team
    freely, each additional human accruing a billed seat. The only headcount gate is
    the free→paid boundary, enforced at the invite route (a Free workspace's 2nd
    human requires the paid plan)."""
    return tier_spec(tier)["included_seats"]


def tier_additional_seat_usd(tier: str) -> float:
    """$/additional human seat/mo for a tier (the LIVE seat price, ADR-445 §6)."""
    return tier_spec(tier)["additional_seat_usd"]


# ── ADR-439 — BYOK availability (enterprise capability) ───────────────────────

def tier_byok_available(tier: str) -> bool:
    """True iff this tier MAY enable BYOK (ADR-439 §3 — enterprise-only). This is
    the CAPABILITY gate (availability); the per-workspace ENGAGEMENT toggle is
    `workspaces.byok_enabled`. A managed enterprise (toggle OFF) is byte-identical
    to lower tiers on the key path — BYOK-ON is the one added resolution branch."""
    return tier_spec(tier).get("byok_available", False)


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
    """Additional humans billed beyond the base's included seats — the LS
    subscription quantity (ADR-445 §7 Phase 2).

    `max(0, human_count − included_seats)`. At N=1 (solo) this is 0 — the owner is
    the one free seat, so a solo workspace pays $0 subscription (usage-only)."""
    return max(0, human_count - tier_included_seats(tier))


def seat_fee_usd(tier: str, human_count: int) -> float:
    """Total monthly seat fee for a workspace: billable_seats × additional_seat_usd.

    LIVE at launch (ADR-445 §6): a solo owner pays $0 (billable_seats = 0); a team
    pays (humans − 1) × the seat price. This is the seat AXIS total; the pooled
    usage meter (Axis ②) is billed separately as the allowance/balance draw."""
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
    for tier in ("free", "starter", "pro", "enterprise"):
        spec = TIER_CONFIG[tier]
        # ADR-429 §12.1 — hidden (dormant) tiers are not offered; skip pro until
        # the capture lane ships. ADR-439 — enterprise is `hidden` (sales-led, not a
        # self-serve upgrade target), so it is skipped here too. Launch ladder =
        # Free + the one paid plan.
        if spec.get("hidden", False):
            continue
        ladder.append({
            "tier": tier,
            "label": spec["label"],
            "price_usd": spec["price_usd"],
            "monthly_allowance_usd": spec["monthly_allowance_usd"],
            "retention_max_days": spec["retention_max_days"],
            "connector_max": spec["connector_max"],
            # ADR-445 Axis ① — seat info for the pricing page (Phase 3). The page
            # reads `additional_seat_usd` (the live per-additional-human price) to
            # render the seat line: free tier = $0 (solo), paid = the seat fee.
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
    # ADR-445 Axis ① — seat helpers (live)
    "HUMAN_SEAT_ROLES",
    "tier_included_seats",
    "tier_additional_seat_usd",
    "count_human_seats",
    "billable_seats",
    "seat_fee_usd",
    # ADR-429 §12.1 — offered vs hidden tiers (the launch collapse)
    "tier_hidden",
    "offered_paid_tiers",
    # ADR-439 — BYOK availability (enterprise capability)
    "tier_byok_available",
]
