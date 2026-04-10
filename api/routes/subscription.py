"""
Subscription management API routes — ADR-172: Usage-First Billing

Endpoints:
- GET /status  — current subscription status
- POST /checkout — create checkout (subscription or top-up)
- GET /portal  — Lemon Squeezy customer portal URL

Webhooks:
- POST /webhooks/lemonsqueezy — subscription events + order_created (top-up)

Checkout types:
  subscription: 'monthly' ($19/mo) or 'yearly' ($180/yr)
  topup: $10 / $25 / $50 one-time purchase

Webhook events handled:
  subscription_created / subscription_updated / subscription_resumed →
    activate pro, grant subscription_refill balance ($20)
  subscription_cancelled / subscription_expired →
    downgrade to free (balance unchanged — they keep what they bought)
  subscription_payment_success →
    recurring billing cycle: grant $20 subscription_refill balance
  order_created →
    one-time top-up purchase: grant balance by variant ID amount
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

from services.supabase import UserClient, get_service_client

log = logging.getLogger(__name__)

router = APIRouter(prefix="/subscription", tags=["Subscription"])
webhook_router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# ── Lemon Squeezy configuration ───────────────────────────────────────────────
LEMONSQUEEZY_API_KEY = os.getenv("LEMONSQUEEZY_API_KEY")
LEMONSQUEEZY_STORE_ID = os.getenv("LEMONSQUEEZY_STORE_ID")
LEMONSQUEEZY_WEBHOOK_SECRET = os.getenv("LEMONSQUEEZY_WEBHOOK_SECRET")

# Subscription variants
LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID = os.getenv("LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID")
LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID = os.getenv("LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID")

# Top-up variants (one-time purchases) — fill after LS product creation
LEMONSQUEEZY_TOPUP_10_VARIANT_ID = os.getenv("LEMONSQUEEZY_TOPUP_10_VARIANT_ID")
LEMONSQUEEZY_TOPUP_25_VARIANT_ID = os.getenv("LEMONSQUEEZY_TOPUP_25_VARIANT_ID")
LEMONSQUEEZY_TOPUP_50_VARIANT_ID = os.getenv("LEMONSQUEEZY_TOPUP_50_VARIANT_ID")

# Variant → top-up amount mapping (populated when env vars are set)
TOPUP_AMOUNTS: dict[str, float] = {}
if LEMONSQUEEZY_TOPUP_10_VARIANT_ID:
    TOPUP_AMOUNTS[LEMONSQUEEZY_TOPUP_10_VARIANT_ID] = 10.0
if LEMONSQUEEZY_TOPUP_25_VARIANT_ID:
    TOPUP_AMOUNTS[LEMONSQUEEZY_TOPUP_25_VARIANT_ID] = 25.0
if LEMONSQUEEZY_TOPUP_50_VARIANT_ID:
    TOPUP_AMOUNTS[LEMONSQUEEZY_TOPUP_50_VARIANT_ID] = 50.0

CHECKOUT_SUCCESS_URL = os.getenv("CHECKOUT_SUCCESS_URL", "https://yarnnn.com/settings?subscription=success")


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


# ── Variant helpers ───────────────────────────────────────────────────────────

def get_plan_from_variant_id(variant_id: str) -> str:
    """Subscription variant → plan label for display."""
    if variant_id == LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID:
        return "pro_yearly"
    return "pro"


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

    checkout_type: 'subscription' (monthly/yearly) or 'topup' ($10/$25/$50)
    billing_period: 'monthly' | 'yearly' — for subscriptions only
    topup_amount: 10 | 25 | 50 — for top-ups only
    """
    checkout_type: str = "subscription"  # 'subscription' | 'topup'
    billing_period: Optional[str] = "monthly"
    topup_amount: Optional[int] = None  # 10 | 25 | 50


class CheckoutResponse(BaseModel):
    checkout_url: str


class SubscriptionStatus(BaseModel):
    status: str           # 'free' | 'pro'
    plan: Optional[str] = None  # 'pro' | 'pro_yearly'
    expires_at: Optional[str] = None
    customer_id: Optional[str] = None
    subscription_id: Optional[str] = None


class PortalResponse(BaseModel):
    portal_url: str


# ── Status endpoint ───────────────────────────────────────────────────────────

@router.get("/status", response_model=SubscriptionStatus)
async def get_subscription_status(auth: UserClient):
    result = auth.client.table("workspaces")\
        .select("subscription_status, subscription_plan, subscription_expires_at, lemonsqueezy_customer_id, lemonsqueezy_subscription_id")\
        .eq("owner_id", auth.user_id)\
        .limit(1)\
        .execute()
    rows = result.data or []
    if not rows:
        return SubscriptionStatus(status="free")
    ws = rows[0]
    raw_status = ws.get("subscription_status") or "free"
    norm_status = "pro" if raw_status in ("starter", "pro") else "free"
    return SubscriptionStatus(
        status=norm_status,
        plan=ws.get("subscription_plan"),
        expires_at=ws.get("subscription_expires_at"),
        customer_id=ws.get("lemonsqueezy_customer_id"),
        subscription_id=ws.get("lemonsqueezy_subscription_id"),
    )


# ── Checkout endpoint ─────────────────────────────────────────────────────────

@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(request: CheckoutRequest, auth: UserClient):
    """Create Lemon Squeezy checkout — subscription or top-up."""
    if not LEMONSQUEEZY_API_KEY:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Payment service not configured")

    ws_result = auth.client.table("workspaces").select("id").eq("owner_id", auth.user_id).limit(1).execute()
    ws_rows = ws_result.data or []
    workspace_id = ws_rows[0]["id"] if ws_rows else None
    if not workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No workspace found")

    if request.checkout_type == "topup":
        amount = request.topup_amount
        topup_variant_map = {10: LEMONSQUEEZY_TOPUP_10_VARIANT_ID, 25: LEMONSQUEEZY_TOPUP_25_VARIANT_ID, 50: LEMONSQUEEZY_TOPUP_50_VARIANT_ID}
        variant_id = topup_variant_map.get(amount)
        if not variant_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Top-up variant for ${amount} not configured yet")
    else:
        billing = request.billing_period or "monthly"
        variant_id = LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID if billing == "yearly" else LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID
        if not variant_id:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Subscription variant not configured for {billing}")

    checkout_data = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": {
                    "custom": {"user_id": auth.user_id, "workspace_id": workspace_id}
                },
                "product_options": {"redirect_url": CHECKOUT_SUCCESS_URL},
            },
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
    """Handle Lemon Squeezy webhook events.

    Subscription events: activate/deactivate pro status
    subscription_payment_success: grant $20 subscription_refill balance
    order_created: grant top-up balance ($10/$25/$50)
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

    # ── Subscription events ────────────────────────────────────────────────────
    if event_name in ("subscription_created", "subscription_updated", "subscription_resumed"):
        renews_at = parse_iso_date(attrs.get("renews_at"))
        status_value = attrs.get("status", "active")
        variant_id = str(attrs.get("variant_id", ""))

        if status_value in ("active", "on_trial", "past_due"):
            sub_status = "pro"
            sub_plan = get_plan_from_variant_id(variant_id)
        else:
            sub_status = "free"
            sub_plan = None

        update_data = {
            "subscription_status": sub_status,
            "subscription_plan": sub_plan,
            "subscription_expires_at": renews_at,
            "lemonsqueezy_subscription_id": subscription_id,
        }
        if customer_id:
            update_data["lemonsqueezy_customer_id"] = customer_id
        client.table("workspaces").update(update_data).eq("id", workspace_id).execute()
        log.info(f"Subscription {event_name}: workspace {workspace_id} → {sub_status} ({sub_plan})")

    elif event_name in ("subscription_cancelled", "subscription_expired"):
        client.table("workspaces").update({
            "subscription_status": "free",
            "subscription_plan": None,
            "subscription_expires_at": None,
        }).eq("id", workspace_id).execute()
        log.info(f"Subscription {event_name}: workspace {workspace_id} → free (balance unchanged)")

    elif event_name == "subscription_payment_success":
        # Recurring billing cycle — grant $20 balance reset (ADR-172)
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

        from services.platform_limits import grant_balance
        grant_balance(
            client,
            workspace_id=workspace_id,
            amount_usd=20.0,
            kind="subscription_refill",
            lemon_subscription_id=subscription_id,
            metadata={"event": "subscription_payment_success"},
        )
        log.info(f"Subscription refill: $20 balance reset for workspace {workspace_id}")

    elif event_name == "subscription_payment_failed":
        log.warning(f"Payment failed for workspace {workspace_id}")

    elif event_name == "order_created":
        # One-time top-up purchase — grant balance by variant amount (ADR-172)
        order_id = str(payload.get("data", {}).get("id", ""))
        first_item = (attrs.get("first_order_item") or {})
        variant_id = str(first_item.get("variant_id", ""))
        amount = TOPUP_AMOUNTS.get(variant_id)

        if amount:
            from services.platform_limits import grant_balance
            grant_balance(
                client,
                workspace_id=workspace_id,
                amount_usd=amount,
                kind="topup",
                lemon_order_id=order_id,
                metadata={"variant_id": variant_id, "amount": amount},
            )
            log.info(f"Top-up: ${amount} for workspace {workspace_id} (order {order_id})")
        else:
            log.warning(f"order_created: unknown variant_id {variant_id} — no balance granted")

    return {"status": "ok"}
