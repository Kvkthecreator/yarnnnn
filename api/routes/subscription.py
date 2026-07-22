"""
Subscription management API routes — ADR-396: Type-B subscription over the metered balance.

The plan tier grants a monthly INCLUDED ALLOWANCE; the topped-up balance is the
OVERAGE pool beneath it. Draw order (ADR-396 §3): allowance → balance → hard-stop
at zero. Tiers + numbers are the single source of truth in services.billing_tiers.

Endpoints:
- GET /status  — current subscription tier + billing state
- POST /checkout — create checkout (subscription tier or dynamic top-up)
- GET /portal  — Lemon Squeezy customer portal URL

Webhooks:
- POST /webhooks/lemonsqueezy — subscription events + order_created (top-up)

Checkout types:
  subscription: tier ∈ {starter, pro} → the tier's LS subscription variant
  topup: a custom dollar amount → one LS top-up variant with LS custom_price

Webhook events handled:
  subscription_created / subscription_updated / subscription_resumed →
    set subscription_tier from the LS variant → tier map; grant the tier's
    monthly allowance (allowance expires each cycle, top-ups survive)
  subscription_cancelled / subscription_expired →
    downgrade to free (balance + allowance unchanged — they keep what they bought)
  subscription_payment_success →
    recurring billing cycle: grant the tier's monthly allowance
  order_created →
    one-time top-up: grant balance by the ACTUAL PAID TOTAL from the order payload
    (NOT a variant→amount lookup — the amount is operator-chosen via custom_price)
"""

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from services.billing_tiers import (
    PAID_TIERS,
    normalize_tier,
    tier_allowance_usd,
    tier_for_variant_id,
    variant_id_for_tier,
)
from services.supabase import UserClient, get_service_client

log = logging.getLogger(__name__)

router = APIRouter(prefix="/subscription", tags=["Subscription"])
webhook_router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# ── Lemon Squeezy configuration ───────────────────────────────────────────────
LEMONSQUEEZY_API_KEY = os.getenv("LEMONSQUEEZY_API_KEY")
LEMONSQUEEZY_STORE_ID = os.getenv("LEMONSQUEEZY_STORE_ID")
LEMONSQUEEZY_WEBHOOK_SECRET = os.getenv("LEMONSQUEEZY_WEBHOOK_SECRET")

# One top-up variant — the dollar amount is set per-checkout via LS custom_price
# (the LS product must have price-override / "pay what you want" enabled). The
# webhook reads the actual paid total from the order, so no variant→amount map.
LEMONSQUEEZY_TOPUP_VARIANT_ID = os.getenv("LEMONSQUEEZY_TOPUP_VARIANT_ID")

# Subscription tier variant ids resolve from services.billing_tiers via the tier's
# ls_variant_env (LEMONSQUEEZY_STARTER_VARIANT_ID / LEMONSQUEEZY_PRO_VARIANT_ID).

CHECKOUT_SUCCESS_URL = os.getenv("CHECKOUT_SUCCESS_URL", "https://yarnnn.com/settings?subscription=success")

# Dynamic top-up bounds (dollars) — a sane floor + ceiling on the custom amount.
TOPUP_MIN_USD = 5
TOPUP_MAX_USD = 500


# ── Billing-authority resolution (ADR-416 D1) ─────────────────────────────────

def _resolve_billing_workspace(auth: "UserClient") -> str:
    """Resolve the workspace this billing act targets AND authorize the caller to
    fund it — ADR-416 D1: billing authority is a grant, not an owner-hardcode.

    Replaces the pre-ADR-416 `.eq("owner_id", auth.user_id)` pattern, which
    conflated "which workspace" with "am I authorized" (owner-only). Now the two
    are split:
      1. the acting workspace = the balance gate's resolution (contextvar /
         owner fallback — `effective_workspace_id`), so a member's billing act
         targets the workspace they operate, not their own singleton;
      2. authorization = `has_billing_authority` (owner by default; any principal
         whose grant carries the `billing` scope).

    Owner path is byte-identical: an owner with no X-Workspace-Id resolves their
    own workspace and is authorized by role='owner'. A plain member (spend-yes,
    fund-no) gets 403. Raises 404 if no workspace resolves.
    """
    from services.workspace_context import effective_workspace_id
    from services.supabase import resolve_principal_id
    from services.principal_grants import has_billing_authority

    ws = effective_workspace_id(auth.user_id, getattr(auth, "workspace_id", None))
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No workspace found")

    principal_id = resolve_principal_id(auth) or auth.user_id
    if not has_billing_authority(principal_id, ws):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have billing authority for this workspace",
        )
    return ws


# ── LS HTTP helpers ───────────────────────────────────────────────────────────

def _ls_headers(include_content_type: bool = False) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {LEMONSQUEEZY_API_KEY}",
        "Accept": "application/vnd.api+json",
    }
    if include_content_type:
        headers["Content-Type"] = "application/vnd.api+json"
    return headers


def _extract_customer_portal_url(payload: dict) -> Optional[str]:
    return (
        payload.get("data", {})
        .get("attributes", {})
        .get("urls", {})
        .get("customer_portal")
    )


def _extract_customer_id(payload: dict) -> Optional[str]:
    attrs = payload.get("data", {}).get("attributes", {})
    if attrs.get("customer_id"):
        return str(attrs["customer_id"])
    rel_customer = (
        payload.get("data", {})
        .get("relationships", {})
        .get("customer", {})
        .get("data", {})
    )
    if rel_customer.get("id"):
        return str(rel_customer["id"])
    return None


async def _get_subscription_payload(http: httpx.AsyncClient, subscription_id: str) -> Optional[dict]:
    response = await http.get(
        f"https://api.lemonsqueezy.com/v1/subscriptions/{subscription_id}",
        headers=_ls_headers(), timeout=30.0,
    )
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        log.error(f"LS subscription lookup failed: {response.status_code}")
        return None
    return response.json()


def _record_seat_sync_failure(
    client: Any, workspace_id: str, sub_id: Any, quantity: int,
    humans: int, reason: str, detail: str = "",
) -> None:
    """Persist a failed seat-quantity sync (ADR-445 §7 P2 reconciliation).

    `sync_seat_quantity` is intentionally best-effort — a billing hiccup must
    never block a member joining or leaving. But best-effort without a record is
    just silence: LS keeps billing the stale quantity while /subscription/status
    reports the new one, forever, with no signal. This is the signal.
    """
    try:
        client.table("subscription_events").insert({
            "workspace_id": workspace_id,
            "event_type": "seat_sync_failed",
            "event_source": "yarnnn",
            "ls_subscription_id": str(sub_id) if sub_id else None,
            "payload": {
                "intended_quantity": quantity,
                "human_seats": humans,
                "reason": reason,
                "detail": detail,
            },
        }).execute()
    except Exception as exc:  # noqa: BLE001
        log.warning("[SEAT_SYNC] could not record sync failure for %s: %s", workspace_id, exc)


async def sync_seat_quantity(workspace_id: str) -> None:
    """Sync the LS subscription's seat quantity to the workspace's current headcount
    (ADR-445 §7 Phase 2). Called when a human member is added or removed so the
    recurring invoice tracks the team. Best-effort — never raises into the member
    lifecycle. No-op for free/exempt workspaces or when there is no LS subscription
    (a solo owner who hasn't taken the paid plan).

    Quantity = max(1, billable_seats) = additional humans beyond the base, floored at
    1 (the taking-owner's own seat). The pooled usage allowance is unchanged — this
    touches only the seat AXIS (Axis ①), never the meter (Axis ②).
    """
    if not LEMONSQUEEZY_API_KEY:
        return
    try:
        from services.supabase import get_service_client
        from services.billing_tiers import (
            PAID_TIERS,
            billable_seats,
            count_human_seats,
            normalize_tier,
        )

        svc = get_service_client()
        rows = (
            svc.table("workspaces")
            .select("subscription_tier, billing_exempt, lemonsqueezy_subscription_id")
            .eq("id", workspace_id)
            .limit(1)
            .execute()
        ).data or []
        if not rows:
            return
        ws = rows[0]
        tier = normalize_tier(ws.get("subscription_tier"))
        sub_id = ws.get("lemonsqueezy_subscription_id")
        # Only a paid, non-exempt workspace with a live LS subscription is synced.
        if ws.get("billing_exempt") or tier not in PAID_TIERS or not sub_id:
            return

        humans = count_human_seats(svc, workspace_id)
        quantity = max(1, billable_seats(tier, humans))

        # PATCH the subscription-item quantity. LS updates the quantity on the
        # subscription's first (and only) item; the subscription id resolves it.
        body = {
            "data": {
                "type": "subscriptions",
                "id": str(sub_id),
                "attributes": {"quantity": quantity},
            }
        }
        async with httpx.AsyncClient() as http:
            resp = await http.patch(
                f"https://api.lemonsqueezy.com/v1/subscriptions/{sub_id}",
                headers=_ls_headers(include_content_type=True),
                json=body, timeout=30.0,
            )
            if resp.status_code not in (200, 202):
                log.warning(
                    f"[SEAT_SYNC] LS quantity update failed for ws {workspace_id} "
                    f"(sub {sub_id}): {resp.status_code} {resp.text[:200]}"
                )
                # ADR-445 §7 P2 — a swallowed PATCH failure used to be invisible:
                # the member lifecycle succeeded, LS kept billing the old count,
                # and nothing recorded it. Land a durable row so the gap is
                # attributable instead of living only in a log line.
                _record_seat_sync_failure(
                    svc, workspace_id, sub_id, quantity, humans,
                    f"http_{resp.status_code}", resp.text[:200],
                )
            else:
                log.info(f"[SEAT_SYNC] ws {workspace_id} → {quantity} seats (sub {sub_id})")
    except Exception as e:  # noqa: BLE001 — best-effort; never break the member lifecycle
        log.warning(f"[SEAT_SYNC] failed for ws {workspace_id}: {e}")
        # Same discipline as the non-2xx branch: swallowing is right, staying
        # silent is not. Guarded so a failure here can't re-raise into the caller.
        try:
            from services.supabase import get_service_client
            _record_seat_sync_failure(
                get_service_client(), workspace_id, None, -1, -1, "exception", str(e)[:200],
            )
        except Exception:  # noqa: BLE001
            pass


def _ls_quantity(attrs: dict) -> Optional[int]:
    """The seat quantity LS reports on a subscription payload, or None.

    LS carries it on `first_subscription_item.quantity`. Absent on some event
    shapes (and on legacy non-quantity variants), which is not an error — it just
    means this event cannot speak to seat drift.
    """
    item = attrs.get("first_subscription_item")
    if not isinstance(item, dict):
        return None
    q = item.get("quantity")
    try:
        return int(q) if q is not None else None
    except (TypeError, ValueError):
        return None


def _reconcile_seat_quantity(
    client: Any, workspace_id: str, tier: str, attrs: dict, event_name: str
) -> None:
    """Compare what LS is billing against what the roster says, and RECORD any gap.

    ADR-445 §7 Phase 2. Deliberately observe-only: it never PATCHes LS (an owner
    may legitimately set quantity in the customer portal, and a webhook that
    fought the portal would loop). It writes a `seat_quantity_drift` row to
    `subscription_events` so the divergence is durable, attributable, and
    queryable — the reconciliation half that `sync_seat_quantity`'s best-effort
    PATCH never had. Best-effort itself: never raises into webhook handling.
    """
    try:
        billed = _ls_quantity(attrs)
        if billed is None:
            return
        from services.billing_tiers import billable_seats, count_human_seats
        humans = count_human_seats(client, workspace_id)
        expected = max(1, billable_seats(tier, humans))
        if billed == expected:
            return
        log.warning(
            "[SEAT_DRIFT] ws %s: LS bills %s seat(s), roster implies %s "
            "(%s humans, tier %s) — event %s",
            workspace_id, billed, expected, humans, tier, event_name,
        )
        client.table("subscription_events").insert({
            "workspace_id": workspace_id,
            "event_type": "seat_quantity_drift",
            "event_source": "yarnnn",   # derived by us, not reported by LS
            "payload": {
                "billed_quantity": billed,
                "expected_quantity": expected,
                "human_seats": humans,
                "tier": tier,
                "observed_on": event_name,
            },
        }).execute()
    except Exception as exc:  # noqa: BLE001 — observation must never break billing
        log.warning("[SEAT_DRIFT] reconciliation failed for ws %s: %s", workspace_id, exc)


async def _get_customer_payload(http: httpx.AsyncClient, customer_id: str) -> Optional[dict]:
    response = await http.get(
        f"https://api.lemonsqueezy.com/v1/customers/{customer_id}",
        headers=_ls_headers(), timeout=30.0,
    )
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        log.error(f"LS customer lookup failed: {response.status_code}")
        return None
    return response.json()


async def _lookup_customer_by_email(http: httpx.AsyncClient, email: Optional[str]) -> Optional[str]:
    if not email or not LEMONSQUEEZY_STORE_ID:
        return None
    response = await http.get(
        "https://api.lemonsqueezy.com/v1/customers",
        headers=_ls_headers(),
        params={"filter[email]": email, "filter[store_id]": LEMONSQUEEZY_STORE_ID, "page[size]": 1},
        timeout=30.0,
    )
    if response.status_code != 200:
        return None
    data = response.json().get("data") or []
    if not data:
        return None
    return str(data[0]["id"]) if data[0].get("id") else None


def parse_iso_date(date_str: Optional[str]) -> Optional[str]:
    if not date_str:
        return None
    try:
        if date_str.endswith("Z"):
            date_str = date_str[:-1] + "+00:00"
        datetime.fromisoformat(date_str)
        return date_str
    except (ValueError, TypeError):
        return None


# ── Pydantic models ───────────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    """Request to create a checkout session.

    checkout_type: 'subscription' | 'topup'
    tier: 'starter' | 'pro' — for subscriptions only
    topup_amount: dollars (int) — for top-ups only; a custom operator-chosen amount
                  bounded by TOPUP_MIN_USD..TOPUP_MAX_USD, priced via LS custom_price.
    """
    checkout_type: str = "subscription"  # 'subscription' | 'topup'
    tier: Optional[str] = None           # 'starter' | 'pro'
    topup_amount: Optional[int] = None   # dollars, e.g. 10 / 25 / 50 / any custom


class CheckoutResponse(BaseModel):
    checkout_url: str


class SubscriptionStatus(BaseModel):
    tier: str                            # 'free' | 'starter' | 'pro'
    expires_at: Optional[str] = None
    customer_id: Optional[str] = None
    subscription_id: Optional[str] = None
    # ── ADR-445 Axis ① — the seat state (LIVE) ────────────────────────────────
    # The seat math, surfaced for legibility. Seat 1 (the owner) is free; each
    # additional human is a priced seat. `seat_billing_active` = the workspace has
    # billable seats beyond the owner (a paid team). A solo workspace reads 0
    # billable seats (only usage bills).
    human_seats: int = 1                 # active human members (owner + members)
    included_seats: int = 1              # billing baseline (humans covered before the seat fee)
    billable_seats: int = 0              # additional humans beyond the base (the billed seats)
    seat_fee_usd: float = 0.0            # billable_seats × additional_seat_usd (the seat-axis total)
    seat_billing_active: bool = False    # billable_seats > 0 on a paid, non-exempt tier
    # ADR-445 §12.3a — the comp/exempt override. When true the workspace pays
    # nothing (seats + usage forced to $0); the operator's test workspaces are
    # exempt. Surfaced so the FE can show a "comped" state instead of a bill.
    billing_exempt: bool = False


class PortalResponse(BaseModel):
    portal_url: str


# ── Status endpoint ───────────────────────────────────────────────────────────

@router.get("/status", response_model=SubscriptionStatus)
async def get_subscription_status(auth: UserClient):
    # ADR-416 D1 — target the ACTING workspace, authorized by billing grant
    # (owner-default). A member with billing authority sees the commons' tier;
    # a plain member gets 403 (they draw the pool but don't manage its funding).
    workspace_id = _resolve_billing_workspace(auth)
    result = auth.client.table("workspaces")\
        .select("subscription_tier, subscription_expires_at, lemonsqueezy_customer_id, lemonsqueezy_subscription_id, billing_exempt")\
        .eq("id", workspace_id)\
        .limit(1)\
        .execute()
    rows = result.data or []
    if not rows:
        return SubscriptionStatus(tier="free")
    ws = rows[0]
    tier = normalize_tier(ws.get("subscription_tier"))
    exempt = bool(ws.get("billing_exempt", False))
    # ADR-445 — the seat state (Axis ①, LIVE). Seat 1 (the owner) is free; each
    # additional human is a priced seat. `seat_billing_active` is True when the
    # workspace has billable seats beyond the owner (a paid team); a solo workspace
    # reads inactive (0 billable seats). Never raises — seat helpers fail-safe to
    # (1 human, $0).
    from services.billing_tiers import (
        count_human_seats,
        tier_included_seats,
        billable_seats as _billable_seats,
        seat_fee_usd as _seat_fee_usd,
    )
    # The seat count is BILLING-AUTHORITATIVE, so it reads through the service
    # client — the same path seat-sync + the webhook drift check already use
    # (this route once passed auth.client, whose RLS visibility of
    # principal_grants is the caller's own membership view; migration 221 makes
    # that view correct for a member, but a billing count must not depend on the
    # request's RLS scope being complete — one client, one behavior, no under- or
    # over-billing on a visibility edge). The old under-count read "1 seat — just
    # you" on a 3-human workspace whose avatar menu correctly read "3 people".
    from services.supabase import get_service_client
    humans = count_human_seats(get_service_client(), workspace_id)
    # ADR-445 §12.3a — an exempt workspace pays nothing: force the seat fee to $0
    # and mark seat billing inactive. Otherwise `seat_billing_active` means the
    # workspace has billable seats beyond the free owner-seat (a paid team) — a
    # solo paid workspace has 0 billable seats and reads inactive.
    n_billable = 0 if exempt else _billable_seats(tier, humans)
    fee = 0.0 if exempt else _seat_fee_usd(tier, humans)
    seat_active = (not exempt) and n_billable > 0
    return SubscriptionStatus(
        tier=tier,
        expires_at=ws.get("subscription_expires_at"),
        customer_id=ws.get("lemonsqueezy_customer_id"),
        subscription_id=ws.get("lemonsqueezy_subscription_id"),
        human_seats=humans,
        included_seats=tier_included_seats(tier),
        # Use the exempt-aware value. This re-called `_billable_seats` WITHOUT the
        # exempt override while `n_billable` (which has it) went unused — so a
        # comped 3-human workspace reported "2 billable seats" beside "$0.00" and
        # "seat billing inactive", contradicting itself on one payload.
        billable_seats=n_billable,
        seat_fee_usd=fee,
        seat_billing_active=seat_active,
        billing_exempt=exempt,
    )


# ── Checkout endpoint ─────────────────────────────────────────────────────────

@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(request: CheckoutRequest, auth: UserClient):
    """Create Lemon Squeezy checkout — subscription tier or dynamic top-up."""
    if not LEMONSQUEEZY_API_KEY:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Payment service not configured")

    # ADR-416 D1 — fund the ACTING workspace, authorized by billing grant.
    workspace_id = _resolve_billing_workspace(auth)

    # custom_price (integer cents) is set only for top-ups.
    custom_price_cents: Optional[int] = None
    # ADR-445 §7 Phase 2 (+ the 2026-07-21 solo-checkout amendment) — the seat
    # QUANTITY for a subscription checkout. The paid plan is seat-priced (variant
    # unit price × quantity); quantity = billable_seats = max(0, humans −
    # included_seats), floored at 1 because LS rejects a 0-quantity subscription.
    #
    # A SOLO owner therefore checks out at quantity 1 and pays one unit. That is
    # ratified, not a rounding artifact: the free→paid boundary governs when a
    # workspace MUST pay (the 2nd human), not whether a solo owner MAY. What the
    # unit buys them is the pooled allowance + the higher gates — NOT a second seat.
    # The copy contract that follows from this (no surface tells a paying solo owner
    # "your seat is free") is enforced FE-side in lib/subscription/usage.ts.
    seat_quantity: Optional[int] = None

    if request.checkout_type == "topup":
        amount = request.topup_amount
        if amount is None or amount < TOPUP_MIN_USD or amount > TOPUP_MAX_USD:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Top-up amount must be between ${TOPUP_MIN_USD} and ${TOPUP_MAX_USD}",
            )
        variant_id = LEMONSQUEEZY_TOPUP_VARIANT_ID
        if not variant_id:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Top-up variant not configured")
        custom_price_cents = int(amount) * 100
    else:
        tier = normalize_tier(request.tier)
        if tier not in PAID_TIERS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown subscription tier: {request.tier}")
        variant_id = variant_id_for_tier(tier)
        if not variant_id:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Subscription variant not configured for {tier}")
        # Seat quantity = additional humans beyond the base, floored at 1 (the plan
        # always bills at least the taking-owner's seat). AI principals excluded.
        # Service client: this quantity is the CHARGE — it must count every human,
        # never just the ones the caller's RLS can see (a 3-human team billed for
        # 1 seat was the exact under-count this replaced). Matches seat-sync +
        # the webhook drift check, which have always used the service client.
        from services.billing_tiers import billable_seats, count_human_seats
        from services.supabase import get_service_client
        humans = count_human_seats(get_service_client(), workspace_id)
        seat_quantity = max(1, billable_seats(tier, humans))

    attributes: dict = {
        "checkout_data": {
            "custom": {"user_id": auth.user_id, "workspace_id": workspace_id}
        },
        "product_options": {"redirect_url": CHECKOUT_SUCCESS_URL},
    }
    if custom_price_cents is not None:
        # LS reads custom_price at the checkout root (integer cents).
        attributes["custom_price"] = custom_price_cents
    if seat_quantity is not None:
        # LS sets the initial subscription quantity via variant_quantities on the
        # checkout_data (keyed by variant id). This is the seat count the recurring
        # invoice multiplies the unit price by.
        attributes["checkout_data"]["variant_quantities"] = [
            {"variant_id": int(variant_id), "quantity": seat_quantity}
        ]

    checkout_data = {
        "data": {
            "type": "checkouts",
            "attributes": attributes,
            "relationships": {
                "store": {"data": {"type": "stores", "id": LEMONSQUEEZY_STORE_ID}},
                "variant": {"data": {"type": "variants", "id": variant_id}},
            },
        }
    }

    async with httpx.AsyncClient() as http:
        response = await http.post(
            "https://api.lemonsqueezy.com/v1/checkouts",
            headers=_ls_headers(include_content_type=True),
            json=checkout_data, timeout=30.0,
        )
        if response.status_code != 201:
            log.error(f"LS checkout error: {response.status_code} - {response.text}")
            # An upstream auth failure (expired/invalid LEMONSQUEEZY_API_KEY) is OUR
            # config problem, not a gateway fault — surface it as a clean, honest
            # 503 the FE can show as "billing temporarily unavailable" rather than a
            # scary 502. Any other LS failure stays a 502 (genuine upstream error).
            if response.status_code in (401, 403):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Billing is temporarily unavailable. Please try again shortly.",
                )
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to create checkout session")

        checkout_url = response.json()["data"]["attributes"]["url"]
        log.info(f"Created {request.checkout_type} checkout for user {auth.user_id}")
        return CheckoutResponse(checkout_url=checkout_url)


# ── Customer portal ───────────────────────────────────────────────────────────

@router.get("/portal", response_model=PortalResponse)
async def get_customer_portal(auth: UserClient):
    if not LEMONSQUEEZY_API_KEY:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Payment service not configured")

    # ADR-416 D1 — manage the ACTING workspace's billing, authorized by grant.
    workspace_id = _resolve_billing_workspace(auth)
    result = auth.client.table("workspaces")\
        .select("id, lemonsqueezy_customer_id, lemonsqueezy_subscription_id")\
        .eq("id", workspace_id).limit(1).execute()
    rows = result.data or []
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No workspace found")

    workspace = rows[0]
    customer_id = workspace.get("lemonsqueezy_customer_id")
    subscription_id = workspace.get("lemonsqueezy_subscription_id")

    async with httpx.AsyncClient() as http:
        if customer_id:
            customer_payload = await _get_customer_payload(http, str(customer_id))
            portal_url = _extract_customer_portal_url(customer_payload or {})
            if portal_url:
                return PortalResponse(portal_url=portal_url)

        if subscription_id:
            subscription_payload = await _get_subscription_payload(http, str(subscription_id))
            if subscription_payload:
                portal_url = _extract_customer_portal_url(subscription_payload)
                if portal_url:
                    resolved_cid = _extract_customer_id(subscription_payload)
                    if resolved_cid:
                        auth.client.table("workspaces").update({"lemonsqueezy_customer_id": resolved_cid}).eq("id", workspace_id).execute()
                    return PortalResponse(portal_url=portal_url)

        email_customer_id = await _lookup_customer_by_email(http, auth.email)
        if email_customer_id:
            auth.client.table("workspaces").update({"lemonsqueezy_customer_id": email_customer_id}).eq("id", workspace_id).execute()
            customer_payload = await _get_customer_payload(http, email_customer_id)
            portal_url = _extract_customer_portal_url(customer_payload or {})
            if portal_url:
                return PortalResponse(portal_url=portal_url)

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing portal unavailable. If you recently subscribed, wait a moment and retry.")


# ── Webhook handler ───────────────────────────────────────────────────────────

def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    if not LEMONSQUEEZY_WEBHOOK_SECRET:
        log.error("LEMONSQUEEZY_WEBHOOK_SECRET not configured")
        return False
    expected = hmac.new(LEMONSQUEEZY_WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


@webhook_router.post("/lemonsqueezy")
async def handle_lemonsqueezy_webhook(request: Request):
    """Handle Lemon Squeezy webhook events (ADR-396).

    Subscription events: set tier + grant the tier's monthly allowance
    subscription_payment_success: grant the tier's monthly allowance (cycle renewal)
    order_created: grant top-up balance by the ACTUAL PAID TOTAL from the order
    """
    body = await request.body()
    signature = request.headers.get("X-Signature", "")

    if not verify_webhook_signature(body, signature):
        log.warning("Invalid webhook signature")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    event_name = payload.get("meta", {}).get("event_name", "")
    log.info(f"LS webhook: {event_name}")

    custom_data = payload.get("meta", {}).get("custom_data", {})
    workspace_id = custom_data.get("workspace_id")
    attrs = payload.get("data", {}).get("attributes", {})
    subscription_id = str(payload.get("data", {}).get("id", ""))
    customer_id = str(attrs.get("customer_id", ""))

    client = get_service_client()

    # Resolve workspace from customer_id if not in custom_data
    if not workspace_id and customer_id:
        result = client.table("workspaces").select("id").eq("lemonsqueezy_customer_id", customer_id).limit(1).execute()
        ws_rows = result.data or []
        if ws_rows:
            workspace_id = ws_rows[0]["id"]

    if not workspace_id:
        log.warning(f"No workspace_id for event: {event_name}")
        return {"status": "ok", "message": "No workspace_id found"}

    # Resolve the owner user_id for allowance grants (grant_allowance keys on both).
    user_id: Optional[str] = None
    ws_owner = client.table("workspaces").select("owner_id").eq("id", workspace_id).limit(1).execute()
    if ws_owner.data:
        user_id = ws_owner.data[0].get("owner_id")

    # Audit log
    try:
        client.table("subscription_events").insert({
            "workspace_id": workspace_id,
            "event_type": event_name,
            "event_source": "lemonsqueezy",
            "ls_subscription_id": subscription_id,
            "ls_customer_id": customer_id,
            "payload": payload,
        }).execute()
    except Exception as e:
        log.warning(f"Failed to log subscription event: {e}")

    # ── Subscription lifecycle events ──────────────────────────────────────────
    if event_name in ("subscription_created", "subscription_updated", "subscription_resumed"):
        renews_at = parse_iso_date(attrs.get("renews_at"))
        status_value = attrs.get("status", "active")
        variant_id = str(attrs.get("variant_id", ""))
        resolved_tier = tier_for_variant_id(variant_id)

        if status_value in ("active", "on_trial", "past_due") and resolved_tier:
            tier = resolved_tier
        else:
            tier = "free"

        update_data = {
            "subscription_tier": tier,
            "subscription_expires_at": renews_at,
            "lemonsqueezy_subscription_id": subscription_id,
        }
        if customer_id:
            update_data["lemonsqueezy_customer_id"] = customer_id
        client.table("workspaces").update(update_data).eq("id", workspace_id).execute()
        log.info(f"Subscription {event_name}: workspace {workspace_id} → tier {tier}")

        # ADR-445 §7 Phase 2 — SEAT RECONCILIATION. The webhook is the only place
        # that learns what LS is ACTUALLY billing. Without reading quantity here,
        # nothing could ever detect drift: `sync_seat_quantity` is doubly
        # best-effort (a non-2xx only logs), so a failed PATCH left LS billing the
        # old count while /subscription/status reported the new computed fee — a
        # silent, permanent under-bill on the axis that carries team revenue.
        # This does not CORRECT drift (the operator may legitimately change
        # quantity in the LS portal); it makes drift VISIBLE and attributable.
        _reconcile_seat_quantity(client, workspace_id, tier, attrs, event_name)

        # Grant the tier's monthly allowance on activation. subscription_created
        # fires with the first payment; payment_success covers renewals. Guarding
        # on tier != free avoids granting a $0 allowance no-op.
        if tier in PAID_TIERS and user_id:
            from services.platform_limits import grant_allowance
            grant_allowance(
                client,
                workspace_id=workspace_id,
                user_id=user_id,
                allowance_usd=tier_allowance_usd(tier),
                lemon_subscription_id=subscription_id,
                metadata={"event": event_name, "tier": tier},
                period_anchor=renews_at,
            )
            log.info(f"Allowance grant: ${tier_allowance_usd(tier)} ({tier}) for workspace {workspace_id}")

    elif event_name in ("subscription_cancelled", "subscription_expired"):
        client.table("workspaces").update({
            "subscription_tier": "free",
            "subscription_expires_at": None,
        }).eq("id", workspace_id).execute()
        log.info(f"Subscription {event_name}: workspace {workspace_id} → free (balance + allowance unchanged)")

    elif event_name == "subscription_payment_success":
        # Recurring billing cycle — grant the tier's monthly allowance (ADR-396).
        renews_at = parse_iso_date(attrs.get("renews_at"))
        update_data = {}
        if renews_at:
            update_data["subscription_expires_at"] = renews_at
        if customer_id:
            update_data["lemonsqueezy_customer_id"] = customer_id
        if subscription_id:
            update_data["lemonsqueezy_subscription_id"] = subscription_id
        if update_data:
            client.table("workspaces").update(update_data).eq("id", workspace_id).execute()

        # Read the current tier to size the allowance.
        tier_row = client.table("workspaces").select("subscription_tier").eq("id", workspace_id).limit(1).execute()
        tier = normalize_tier(tier_row.data[0].get("subscription_tier")) if tier_row.data else "free"

        if tier in PAID_TIERS and user_id:
            from services.platform_limits import grant_allowance
            grant_allowance(
                client,
                workspace_id=workspace_id,
                user_id=user_id,
                allowance_usd=tier_allowance_usd(tier),
                lemon_subscription_id=subscription_id,
                metadata={"event": "subscription_payment_success", "tier": tier},
                period_anchor=renews_at,
            )
            log.info(f"Cycle allowance: ${tier_allowance_usd(tier)} ({tier}) for workspace {workspace_id}")

    elif event_name == "subscription_payment_failed":
        log.warning(f"Payment failed for workspace {workspace_id}")

    elif event_name == "order_created":
        # One-time top-up — grant balance by the ACTUAL PAID TOTAL (ADR-396). The
        # amount is operator-chosen via custom_price, so we read the order total
        # (cents) rather than mapping a variant → fixed amount.
        order_id = str(payload.get("data", {}).get("id", ""))
        total_cents = attrs.get("total")
        if total_cents is None:
            # Fallback fields some LS payloads use for the order total.
            total_cents = attrs.get("total_usd") or attrs.get("subtotal")

        if total_cents:
            amount = round(int(total_cents) / 100, 2)
            from services.platform_limits import grant_balance
            grant_balance(
                client,
                workspace_id=workspace_id,
                amount_usd=amount,
                kind="topup",
                lemon_order_id=order_id,
                metadata={"order_id": order_id, "total_cents": int(total_cents)},
            )
            log.info(f"Top-up: ${amount} for workspace {workspace_id} (order {order_id})")
        else:
            log.warning(f"order_created: no total on order {order_id} — no balance granted")

    return {"status": "ok"}
