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
from typing import Optional

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


class PortalResponse(BaseModel):
    portal_url: str


# ── Status endpoint ───────────────────────────────────────────────────────────

@router.get("/status", response_model=SubscriptionStatus)
async def get_subscription_status(auth: UserClient):
    result = auth.client.table("workspaces")\
        .select("subscription_tier, subscription_expires_at, lemonsqueezy_customer_id, lemonsqueezy_subscription_id")\
        .eq("owner_id", auth.user_id)\
        .limit(1)\
        .execute()
    rows = result.data or []
    if not rows:
        return SubscriptionStatus(tier="free")
    ws = rows[0]
    return SubscriptionStatus(
        tier=normalize_tier(ws.get("subscription_tier")),
        expires_at=ws.get("subscription_expires_at"),
        customer_id=ws.get("lemonsqueezy_customer_id"),
        subscription_id=ws.get("lemonsqueezy_subscription_id"),
    )


# ── Checkout endpoint ─────────────────────────────────────────────────────────

@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(request: CheckoutRequest, auth: UserClient):
    """Create Lemon Squeezy checkout — subscription tier or dynamic top-up."""
    if not LEMONSQUEEZY_API_KEY:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Payment service not configured")

    ws_result = auth.client.table("workspaces").select("id").eq("owner_id", auth.user_id).limit(1).execute()
    ws_rows = ws_result.data or []
    workspace_id = ws_rows[0]["id"] if ws_rows else None
    if not workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No workspace found")

    # custom_price (integer cents) is set only for top-ups.
    custom_price_cents: Optional[int] = None

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

    attributes: dict = {
        "checkout_data": {
            "custom": {"user_id": auth.user_id, "workspace_id": workspace_id}
        },
        "product_options": {"redirect_url": CHECKOUT_SUCCESS_URL},
    }
    if custom_price_cents is not None:
        # LS reads custom_price at the checkout root (integer cents).
        attributes["custom_price"] = custom_price_cents

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

    result = auth.client.table("workspaces")\
        .select("id, lemonsqueezy_customer_id, lemonsqueezy_subscription_id")\
        .eq("owner_id", auth.user_id).limit(1).execute()
    rows = result.data or []
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No workspace found")

    workspace = rows[0]
    workspace_id = workspace["id"]
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
