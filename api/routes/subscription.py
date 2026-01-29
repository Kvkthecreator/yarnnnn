"""
Subscription management API routes (Lemon Squeezy integration)

Endpoints:
- GET /status - Get current subscription status
- POST /checkout - Create checkout session
- GET /portal - Get customer portal URL

Webhook:
- POST /webhooks/lemonsqueezy - Handle LS webhook events
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

# Lemon Squeezy configuration
LEMONSQUEEZY_API_KEY = os.getenv("LEMONSQUEEZY_API_KEY")
LEMONSQUEEZY_STORE_ID = os.getenv("LEMONSQUEEZY_STORE_ID")
LEMONSQUEEZY_WEBHOOK_SECRET = os.getenv("LEMONSQUEEZY_WEBHOOK_SECRET")
LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID = os.getenv("LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID")
LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID = os.getenv("LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID")
CHECKOUT_SUCCESS_URL = os.getenv("CHECKOUT_SUCCESS_URL", "https://yarnnn.com/dashboard?subscription=success")


# ============== Pydantic Models ==============

class CheckoutRequest(BaseModel):
    """Request to create a checkout session."""
    billing_period: Optional[str] = "monthly"  # 'monthly' or 'yearly'


class CheckoutResponse(BaseModel):
    """Response with checkout URL."""
    checkout_url: str


class SubscriptionStatus(BaseModel):
    """Current subscription status."""
    status: str  # 'free', 'pro'
    expires_at: Optional[str] = None
    customer_id: Optional[str] = None
    subscription_id: Optional[str] = None


class PortalResponse(BaseModel):
    """Response with customer portal URL."""
    portal_url: str


# ============== Status Endpoint ==============

@router.get("/status", response_model=SubscriptionStatus)
async def get_subscription_status(auth: UserClient):
    """Get current user's subscription status."""
    # Get workspace for this user
    result = auth.client.table("workspaces")\
        .select("subscription_status, subscription_expires_at, lemonsqueezy_customer_id, lemonsqueezy_subscription_id")\
        .eq("owner_id", auth.user_id)\
        .single()\
        .execute()

    if not result.data:
        return SubscriptionStatus(status="free")

    ws = result.data
    return SubscriptionStatus(
        status=ws.get("subscription_status") or "free",
        expires_at=ws.get("subscription_expires_at"),
        customer_id=ws.get("lemonsqueezy_customer_id"),
        subscription_id=ws.get("lemonsqueezy_subscription_id"),
    )


# ============== Checkout Endpoint ==============

@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(request: CheckoutRequest, auth: UserClient):
    """Create a Lemon Squeezy checkout session for the current user."""
    if not LEMONSQUEEZY_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment service not configured",
        )

    # Select variant based on billing period
    if request.billing_period == "yearly":
        variant_id = LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID
    else:
        variant_id = LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID

    if not variant_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Product variant not configured",
        )

    # Get workspace ID for this user
    ws_result = auth.client.table("workspaces")\
        .select("id")\
        .eq("owner_id", auth.user_id)\
        .single()\
        .execute()

    workspace_id = ws_result.data["id"] if ws_result.data else None

    if not workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No workspace found for user",
        )

    checkout_data = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": {
                    "custom": {
                        "user_id": auth.user_id,
                        "workspace_id": workspace_id,
                    }
                },
                "product_options": {
                    "redirect_url": CHECKOUT_SUCCESS_URL,
                },
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
            headers={
                "Authorization": f"Bearer {LEMONSQUEEZY_API_KEY}",
                "Content-Type": "application/vnd.api+json",
                "Accept": "application/vnd.api+json",
            },
            json=checkout_data,
            timeout=30.0,
        )

        if response.status_code != 201:
            log.error(f"LS checkout error: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to create checkout session",
            )

        data = response.json()
        checkout_url = data["data"]["attributes"]["url"]

        log.info(f"Created checkout for user {auth.user_id}")
        return CheckoutResponse(checkout_url=checkout_url)


# ============== Customer Portal ==============

@router.get("/portal", response_model=PortalResponse)
async def get_customer_portal(auth: UserClient):
    """Get Lemon Squeezy customer portal URL for managing subscription."""
    if not LEMONSQUEEZY_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment service not configured",
        )

    result = auth.client.table("workspaces")\
        .select("lemonsqueezy_customer_id")\
        .eq("owner_id", auth.user_id)\
        .single()\
        .execute()

    customer_id = result.data.get("lemonsqueezy_customer_id") if result.data else None

    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found. Subscribe first to manage your subscription.",
        )

    async with httpx.AsyncClient() as http:
        response = await http.get(
            f"https://api.lemonsqueezy.com/v1/customers/{customer_id}",
            headers={
                "Authorization": f"Bearer {LEMONSQUEEZY_API_KEY}",
                "Accept": "application/vnd.api+json",
            },
            timeout=30.0,
        )

        if response.status_code != 200:
            log.error(f"LS portal error: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to get customer portal",
            )

        data = response.json()
        portal_url = data["data"]["attributes"]["urls"]["customer_portal"]

        return PortalResponse(portal_url=portal_url)


# ============== Webhook Handler ==============

def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify Lemon Squeezy webhook signature."""
    if not LEMONSQUEEZY_WEBHOOK_SECRET:
        log.error("LEMONSQUEEZY_WEBHOOK_SECRET not configured")
        return False

    expected = hmac.new(
        LEMONSQUEEZY_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature, expected)


def parse_iso_date(date_str: Optional[str]) -> Optional[str]:
    """Parse and normalize ISO date string."""
    if not date_str:
        return None
    try:
        # Normalize Z suffix to +00:00
        if date_str.endswith("Z"):
            date_str = date_str[:-1] + "+00:00"
        # Validate format
        datetime.fromisoformat(date_str)
        return date_str
    except (ValueError, TypeError):
        log.warning(f"Failed to parse date: {date_str}")
        return None


@webhook_router.post("/lemonsqueezy")
async def handle_lemonsqueezy_webhook(request: Request):
    """Handle Lemon Squeezy webhook events."""
    body = await request.body()
    signature = request.headers.get("X-Signature", "")

    if not verify_webhook_signature(body, signature):
        log.warning("Invalid webhook signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    event_name = payload.get("meta", {}).get("event_name", "")
    log.info(f"Received LS webhook: {event_name}")

    # Extract identifiers from custom data
    custom_data = payload.get("meta", {}).get("custom_data", {})
    workspace_id = custom_data.get("workspace_id")
    user_id = custom_data.get("user_id")

    # Extract subscription data
    attrs = payload.get("data", {}).get("attributes", {})
    subscription_id = str(payload.get("data", {}).get("id", ""))
    customer_id = str(attrs.get("customer_id", ""))

    # Use service client for webhook updates (bypasses RLS)
    client = get_service_client()

    # Try to find workspace by customer_id if not in custom_data
    if not workspace_id and customer_id:
        result = client.table("workspaces")\
            .select("id")\
            .eq("lemonsqueezy_customer_id", customer_id)\
            .single()\
            .execute()
        if result.data:
            workspace_id = result.data["id"]

    if not workspace_id:
        log.warning(f"No workspace_id found for event: {event_name}")
        return {"status": "ok", "message": "No workspace_id found"}

    # Log event for audit
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

    # Handle specific events
    if event_name == "subscription_created":
        renews_at = parse_iso_date(attrs.get("renews_at"))
        status_value = attrs.get("status", "active")
        sub_status = "pro" if status_value in ("active", "on_trial") else "free"

        client.table("workspaces").update({
            "subscription_status": sub_status,
            "subscription_expires_at": renews_at,
            "lemonsqueezy_customer_id": customer_id,
            "lemonsqueezy_subscription_id": subscription_id,
        }).eq("id", workspace_id).execute()

        log.info(f"Activated pro subscription for workspace {workspace_id}")

    elif event_name == "subscription_updated":
        renews_at = parse_iso_date(attrs.get("renews_at"))
        status_value = attrs.get("status", "active")
        sub_status = "pro" if status_value in ("active", "on_trial", "past_due") else "free"

        client.table("workspaces").update({
            "subscription_status": sub_status,
            "subscription_expires_at": renews_at,
            "lemonsqueezy_subscription_id": subscription_id,
        }).eq("id", workspace_id).execute()

        log.info(f"Updated subscription for workspace {workspace_id}: {sub_status}")

    elif event_name in ("subscription_cancelled", "subscription_expired"):
        client.table("workspaces").update({
            "subscription_status": "free",
            "subscription_expires_at": None,
        }).eq("id", workspace_id).execute()

        log.info(f"Downgraded workspace {workspace_id} to free tier")

    elif event_name == "subscription_resumed":
        renews_at = parse_iso_date(attrs.get("renews_at"))

        client.table("workspaces").update({
            "subscription_status": "pro",
            "subscription_expires_at": renews_at,
            "lemonsqueezy_subscription_id": subscription_id,
        }).eq("id", workspace_id).execute()

        log.info(f"Resumed subscription for workspace {workspace_id}")

    elif event_name == "subscription_payment_failed":
        log.warning(f"Payment failed for workspace {workspace_id}")

    elif event_name == "subscription_payment_success":
        renews_at = parse_iso_date(attrs.get("renews_at"))
        if renews_at:
            client.table("workspaces").update({
                "subscription_expires_at": renews_at,
            }).eq("id", workspace_id).execute()
        log.info(f"Subscription renewed for workspace {workspace_id}")

    return {"status": "ok"}
