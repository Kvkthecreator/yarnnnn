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

# ADR-053: Product variant IDs for 3-tier pricing
LEMONSQUEEZY_STARTER_MONTHLY_VARIANT_ID = os.getenv("LEMONSQUEEZY_STARTER_MONTHLY_VARIANT_ID")
LEMONSQUEEZY_STARTER_YEARLY_VARIANT_ID = os.getenv("LEMONSQUEEZY_STARTER_YEARLY_VARIANT_ID")
LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID = os.getenv("LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID")
LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID = os.getenv("LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID")

CHECKOUT_SUCCESS_URL = os.getenv("CHECKOUT_SUCCESS_URL", "https://yarnnn.com/settings?subscription=success")


def _ls_headers(include_content_type: bool = False) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {LEMONSQUEEZY_API_KEY}",
        "Accept": "application/vnd.api+json",
    }
    if include_content_type:
        headers["Content-Type"] = "application/vnd.api+json"
    return headers


def _extract_customer_portal_url(payload: dict) -> Optional[str]:
    """Extract customer portal URL from Lemon Squeezy object payload."""
    return (
        payload.get("data", {})
        .get("attributes", {})
        .get("urls", {})
        .get("customer_portal")
    )


def _extract_customer_id(payload: dict) -> Optional[str]:
    """Extract customer ID from a Lemon Squeezy payload."""
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
        headers=_ls_headers(),
        timeout=30.0,
    )
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        log.error(f"LS subscription lookup failed: {response.status_code} - {response.text}")
        return None
    return response.json()


async def _get_customer_payload(http: httpx.AsyncClient, customer_id: str) -> Optional[dict]:
    response = await http.get(
        f"https://api.lemonsqueezy.com/v1/customers/{customer_id}",
        headers=_ls_headers(),
        timeout=30.0,
    )
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        log.error(f"LS customer lookup failed: {response.status_code} - {response.text}")
        return None
    return response.json()


async def _lookup_customer_by_email(http: httpx.AsyncClient, email: Optional[str]) -> Optional[str]:
    if not email or not LEMONSQUEEZY_STORE_ID:
        return None

    response = await http.get(
        "https://api.lemonsqueezy.com/v1/customers",
        headers=_ls_headers(),
        params={
            "filter[email]": email,
            "filter[store_id]": LEMONSQUEEZY_STORE_ID,
            "page[size]": 1,
        },
        timeout=30.0,
    )
    if response.status_code != 200:
        log.error(f"LS customer search failed: {response.status_code} - {response.text}")
        return None

    data = response.json().get("data") or []
    if not data:
        return None
    customer_id = data[0].get("id")
    return str(customer_id) if customer_id else None


def get_tier_from_variant_id(variant_id: str) -> str:
    """
    ADR-053: Determine subscription tier from Lemon Squeezy variant ID.

    Returns 'pro', 'starter', or 'free'.
    """
    pro_variants = {
        LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID,
        LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID,
    }
    starter_variants = {
        LEMONSQUEEZY_STARTER_MONTHLY_VARIANT_ID,
        LEMONSQUEEZY_STARTER_YEARLY_VARIANT_ID,
    }

    if variant_id in pro_variants:
        return "pro"
    elif variant_id in starter_variants:
        return "starter"
    else:
        # Unknown variant - log and default to starter for safety
        log.warning(f"Unknown variant_id: {variant_id}, defaulting to starter")
        return "starter"


# ============== Pydantic Models ==============

class CheckoutRequest(BaseModel):
    """Request to create a checkout session."""
    tier: Optional[str] = "starter"  # ADR-053: 'starter' or 'pro'
    billing_period: Optional[str] = "monthly"  # 'monthly' or 'yearly'


class CheckoutResponse(BaseModel):
    """Response with checkout URL."""
    checkout_url: str


class SubscriptionStatus(BaseModel):
    """Current subscription status."""
    status: str  # ADR-053: 'free', 'starter', 'pro'
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
    """
    Create a Lemon Squeezy checkout session for the current user.

    ADR-053: Supports both Starter and Pro tiers.
    """
    if not LEMONSQUEEZY_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment service not configured",
        )

    # ADR-053: Select variant based on tier + billing period
    tier = request.tier or "starter"
    billing = request.billing_period or "monthly"

    variant_map = {
        ("starter", "monthly"): LEMONSQUEEZY_STARTER_MONTHLY_VARIANT_ID,
        ("starter", "yearly"): LEMONSQUEEZY_STARTER_YEARLY_VARIANT_ID,
        ("pro", "monthly"): LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID,
        ("pro", "yearly"): LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID,
    }

    variant_id = variant_map.get((tier, billing))

    if not variant_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Product variant not configured for {tier}/{billing}",
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
            headers=_ls_headers(include_content_type=True),
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
        .select("id, lemonsqueezy_customer_id, lemonsqueezy_subscription_id")\
        .eq("owner_id", auth.user_id)\
        .single()\
        .execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No workspace found for this user.",
        )

    workspace = result.data
    workspace_id = workspace["id"]
    customer_id = workspace.get("lemonsqueezy_customer_id")
    subscription_id = workspace.get("lemonsqueezy_subscription_id")

    async with httpx.AsyncClient() as http:
        # 1) Preferred path: direct customer lookup when we have customer_id.
        if customer_id:
            customer_payload = await _get_customer_payload(http, str(customer_id))
            portal_url = _extract_customer_portal_url(customer_payload or {})
            if portal_url:
                return PortalResponse(portal_url=portal_url)

        # 2) Fallback path: resolve via subscription_id (works when customer_id wasn't persisted).
        if subscription_id:
            subscription_payload = await _get_subscription_payload(http, str(subscription_id))
            if subscription_payload:
                portal_url = _extract_customer_portal_url(subscription_payload)
                if portal_url:
                    resolved_customer_id = _extract_customer_id(subscription_payload)
                    if resolved_customer_id:
                        auth.client.table("workspaces").update({
                            "lemonsqueezy_customer_id": resolved_customer_id,
                        }).eq("id", workspace_id).execute()
                    return PortalResponse(portal_url=portal_url)

                resolved_customer_id = _extract_customer_id(subscription_payload)
                if resolved_customer_id:
                    auth.client.table("workspaces").update({
                        "lemonsqueezy_customer_id": resolved_customer_id,
                    }).eq("id", workspace_id).execute()
                    customer_payload = await _get_customer_payload(http, resolved_customer_id)
                    portal_url = _extract_customer_portal_url(customer_payload or {})
                    if portal_url:
                        return PortalResponse(portal_url=portal_url)

        # 3) Last fallback: find customer by authenticated user email in this store.
        email_customer_id = await _lookup_customer_by_email(http, auth.email)
        if email_customer_id:
            auth.client.table("workspaces").update({
                "lemonsqueezy_customer_id": email_customer_id,
            }).eq("id", workspace_id).execute()
            customer_payload = await _get_customer_payload(http, email_customer_id)
            portal_url = _extract_customer_portal_url(customer_payload or {})
            if portal_url:
                return PortalResponse(portal_url=portal_url)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=(
            "Billing portal is unavailable for this account right now. "
            "If you recently subscribed, wait a minute and retry. "
            "If it persists, contact support to re-link your Lemon Squeezy customer record."
        ),
    )


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
        variant_id = str(attrs.get("variant_id", ""))

        # ADR-053: Determine tier from variant ID
        if status_value in ("active", "on_trial"):
            sub_status = get_tier_from_variant_id(variant_id)
        else:
            sub_status = "free"

        client.table("workspaces").update({
            "subscription_status": sub_status,
            "subscription_expires_at": renews_at,
            "lemonsqueezy_customer_id": customer_id,
            "lemonsqueezy_subscription_id": subscription_id,
        }).eq("id", workspace_id).execute()

        log.info(f"Activated {sub_status} subscription for workspace {workspace_id}")

    elif event_name == "subscription_updated":
        renews_at = parse_iso_date(attrs.get("renews_at"))
        status_value = attrs.get("status", "active")
        variant_id = str(attrs.get("variant_id", ""))

        # ADR-053: Determine tier from variant ID
        if status_value in ("active", "on_trial", "past_due"):
            sub_status = get_tier_from_variant_id(variant_id)
        else:
            sub_status = "free"

        update_data = {
            "subscription_status": sub_status,
            "subscription_expires_at": renews_at,
            "lemonsqueezy_subscription_id": subscription_id,
        }
        if customer_id:
            update_data["lemonsqueezy_customer_id"] = customer_id

        client.table("workspaces").update(update_data).eq("id", workspace_id).execute()

        log.info(f"Updated subscription for workspace {workspace_id}: {sub_status}")

    elif event_name in ("subscription_cancelled", "subscription_expired"):
        client.table("workspaces").update({
            "subscription_status": "free",
            "subscription_expires_at": None,
        }).eq("id", workspace_id).execute()

        log.info(f"Downgraded workspace {workspace_id} to free tier")

    elif event_name == "subscription_resumed":
        renews_at = parse_iso_date(attrs.get("renews_at"))
        variant_id = str(attrs.get("variant_id", ""))

        # ADR-053: Determine tier from variant ID
        sub_status = get_tier_from_variant_id(variant_id)

        update_data = {
            "subscription_status": sub_status,
            "subscription_expires_at": renews_at,
            "lemonsqueezy_subscription_id": subscription_id,
        }
        if customer_id:
            update_data["lemonsqueezy_customer_id"] = customer_id

        client.table("workspaces").update(update_data).eq("id", workspace_id).execute()

        log.info(f"Resumed {sub_status} subscription for workspace {workspace_id}")

    elif event_name == "subscription_payment_failed":
        log.warning(f"Payment failed for workspace {workspace_id}")

    elif event_name == "subscription_payment_success":
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
        log.info(f"Subscription renewed for workspace {workspace_id}")

    return {"status": "ok"}
