# yarnnn Subscription Implementation Guide

## Overview

This document provides the technical implementation details for integrating Lemon Squeezy subscriptions into yarnnn, based on the proven pattern from episode-0 (chat_companion).

---

## File Structure

```
api/
├── routes/
│   └── subscription.py      # Subscription endpoints + webhooks
├── services/
│   └── subscription.py      # Business logic (optional)
└── main.py                   # Mount subscription router

web/
├── app/
│   └── (authenticated)/
│       └── settings/
│           └── page.tsx     # Billing tab with subscription card
├── components/
│   └── subscription/
│       ├── SubscriptionCard.tsx
│       └── PricingTable.tsx
├── hooks/
│   └── useSubscription.ts
├── lib/
│   └── api/
│       └── client.ts        # Add subscription endpoints
└── types/
    └── subscription.ts
```

---

## Backend Implementation

### 1. Subscription Routes

**File: `api/routes/subscription.py`**

```python
"""Subscription management API routes (Lemon Squeezy integration)."""

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime
from typing import Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from services.supabase import get_service_client
from dependencies import get_current_user

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


class CheckoutRequest(BaseModel):
    """Request to create a checkout session."""
    variant_id: Optional[str] = None  # Use monthly default if not provided
    billing_period: Optional[str] = "monthly"  # 'monthly' or 'yearly'


class CheckoutResponse(BaseModel):
    """Response with checkout URL."""
    checkout_url: str


class SubscriptionStatus(BaseModel):
    """Current subscription status."""
    status: str  # 'free', 'pro', 'cancelled'
    expires_at: Optional[str] = None
    customer_id: Optional[str] = None
    subscription_id: Optional[str] = None


# ============== Status Endpoint ==============

@router.get("/status", response_model=SubscriptionStatus)
async def get_subscription_status(user=Depends(get_current_user)):
    """Get current user's subscription status."""
    client = get_service_client()

    # Get workspace for user
    result = client.table("workspaces")\
        .select("subscription_status, subscription_expires_at, lemonsqueezy_customer_id, lemonsqueezy_subscription_id")\
        .eq("owner_id", str(user.id))\
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
async def create_checkout(request: CheckoutRequest, user=Depends(get_current_user)):
    """Create a Lemon Squeezy checkout session for the current user."""
    if not LEMONSQUEEZY_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment service not configured",
        )

    # Select variant based on billing period
    if request.variant_id:
        variant_id = request.variant_id
    elif request.billing_period == "yearly":
        variant_id = LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID
    else:
        variant_id = LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID

    if not variant_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Product variant not configured",
        )

    # Get workspace ID for this user
    client = get_service_client()
    ws_result = client.table("workspaces")\
        .select("id")\
        .eq("owner_id", str(user.id))\
        .single()\
        .execute()

    workspace_id = ws_result.data["id"] if ws_result.data else None

    checkout_data = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": {
                    "custom": {
                        "user_id": str(user.id),
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

        log.info(f"Created checkout for user {user.id}")
        return CheckoutResponse(checkout_url=checkout_url)


# ============== Customer Portal ==============

@router.get("/portal")
async def get_customer_portal(user=Depends(get_current_user)):
    """Get Lemon Squeezy customer portal URL for managing subscription."""
    if not LEMONSQUEEZY_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment service not configured",
        )

    client = get_service_client()
    result = client.table("workspaces")\
        .select("lemonsqueezy_customer_id")\
        .eq("owner_id", str(user.id))\
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

        return {"portal_url": portal_url}


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
    # Keep as string for Supabase, just validate format
    try:
        if date_str.endswith("Z"):
            date_str = date_str[:-1] + "+00:00"
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

    # Extract identifiers
    custom_data = payload.get("meta", {}).get("custom_data", {})
    workspace_id = custom_data.get("workspace_id")
    user_id = custom_data.get("user_id")

    attrs = payload.get("data", {}).get("attributes", {})
    subscription_id = str(payload.get("data", {}).get("id", ""))
    customer_id = str(attrs.get("customer_id", ""))

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
    client.table("subscription_events").insert({
        "workspace_id": workspace_id,
        "event_type": event_name,
        "event_source": "lemonsqueezy",
        "ls_subscription_id": subscription_id,
        "ls_customer_id": customer_id,
        "payload": payload,
    }).execute()

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
```

### 2. Register Routes

**Update: `api/main.py`**

```python
from routes import subscription

# ... existing includes ...

# Subscription routes
app.include_router(subscription.router, prefix="/api")
app.include_router(subscription.webhook_router, prefix="/api")
```

---

## Database Migration

**File: `supabase/migrations/XXX_subscription_fields.sql`**

```sql
-- Add subscription fields to workspaces table
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'free';
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS subscription_expires_at TIMESTAMPTZ;
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS lemonsqueezy_customer_id TEXT;
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS lemonsqueezy_subscription_id TEXT;

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_workspaces_ls_customer
  ON workspaces(lemonsqueezy_customer_id);
CREATE INDEX IF NOT EXISTS idx_workspaces_ls_subscription
  ON workspaces(lemonsqueezy_subscription_id);

-- Subscription events audit log
CREATE TABLE IF NOT EXISTS subscription_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    event_source TEXT NOT NULL DEFAULT 'lemonsqueezy',
    ls_subscription_id TEXT,
    ls_customer_id TEXT,
    payload JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscription_events_workspace
  ON subscription_events(workspace_id);
CREATE INDEX IF NOT EXISTS idx_subscription_events_type
  ON subscription_events(event_type);
CREATE INDEX IF NOT EXISTS idx_subscription_events_created
  ON subscription_events(created_at DESC);

-- RLS policies
ALTER TABLE subscription_events ENABLE ROW LEVEL SECURITY;

-- Users can read their own subscription events
CREATE POLICY subscription_events_select_own ON subscription_events
    FOR SELECT USING (
        workspace_id IN (
            SELECT id FROM workspaces WHERE owner_id = auth.uid()
        )
    );

-- Service role can insert (webhooks)
CREATE POLICY subscription_events_insert_service ON subscription_events
    FOR INSERT WITH CHECK (true);
```

---

## Frontend Implementation

### 1. Types

**File: `web/types/subscription.ts`**

```typescript
export interface SubscriptionStatus {
  status: "free" | "pro" | "cancelled";
  expires_at: string | null;
  customer_id: string | null;
  subscription_id: string | null;
}

export interface CheckoutResponse {
  checkout_url: string;
}

export interface PortalResponse {
  portal_url: string;
}
```

### 2. API Client

**Update: `web/lib/api/client.ts`**

```typescript
import type { SubscriptionStatus, CheckoutResponse, PortalResponse } from "@/types/subscription";

// Add to api object
subscription: {
  getStatus: () => request<SubscriptionStatus>("/api/subscription/status"),

  createCheckout: (billingPeriod: "monthly" | "yearly" = "monthly") =>
    request<CheckoutResponse>("/api/subscription/checkout", {
      method: "POST",
      body: JSON.stringify({ billing_period: billingPeriod }),
    }),

  getPortal: () => request<PortalResponse>("/api/subscription/portal"),
},
```

### 3. useSubscription Hook

**File: `web/hooks/useSubscription.ts`**

```typescript
"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api/client";
import type { SubscriptionStatus } from "@/types/subscription";

export function useSubscription() {
  const [status, setStatus] = useState<SubscriptionStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await api.subscription.getStatus();
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Failed to fetch status"));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const isPro = status?.status === "pro";

  const upgrade = async (billingPeriod: "monthly" | "yearly" = "monthly") => {
    try {
      setIsLoading(true);
      const { checkout_url } = await api.subscription.createCheckout(billingPeriod);
      window.location.href = checkout_url;
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Failed to create checkout"));
      setIsLoading(false);
    }
  };

  const manageSubscription = async () => {
    try {
      setIsLoading(true);
      const { portal_url } = await api.subscription.getPortal();
      window.open(portal_url, "_blank");
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Failed to open portal"));
    } finally {
      setIsLoading(false);
    }
  };

  return {
    status,
    isPro,
    isLoading,
    error,
    upgrade,
    manageSubscription,
    refresh: fetchStatus,
  };
}
```

### 4. SubscriptionCard Component

**File: `web/components/subscription/SubscriptionCard.tsx`**

```typescript
"use client";

import { useSubscription } from "@/hooks/useSubscription";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Check, Loader2 } from "lucide-react";

export function SubscriptionCard() {
  const { status, isPro, isLoading, upgrade, manageSubscription } = useSubscription();

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return null;
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  };

  if (isLoading && !status) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Subscription</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {isPro ? (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <div className="px-3 py-1 bg-primary text-primary-foreground rounded-full text-sm font-medium">
                Pro
              </div>
            </div>
            {status?.expires_at && (
              <p className="text-sm text-muted-foreground">
                Renews on {formatDate(status.expires_at)}
              </p>
            )}
            <Button
              variant="outline"
              onClick={manageSubscription}
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : null}
              Manage Subscription
            </Button>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Free vs Pro comparison */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 border rounded-lg">
                <h3 className="font-medium mb-2">Free</h3>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>1 project</li>
                  <li>50 memories</li>
                  <li>5 sessions/month</li>
                </ul>
              </div>
              <div className="p-4 border rounded-lg border-primary">
                <h3 className="font-medium mb-2">Pro - $19/mo</h3>
                <ul className="text-sm space-y-1">
                  <li className="flex items-center gap-1">
                    <Check className="w-3 h-3 text-green-500" />
                    Unlimited projects
                  </li>
                  <li className="flex items-center gap-1">
                    <Check className="w-3 h-3 text-green-500" />
                    Unlimited memories
                  </li>
                  <li className="flex items-center gap-1">
                    <Check className="w-3 h-3 text-green-500" />
                    Scheduled agents
                  </li>
                </ul>
              </div>
            </div>

            <div className="flex gap-2">
              <Button onClick={() => upgrade("monthly")} disabled={isLoading}>
                {isLoading ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : null}
                Upgrade to Pro
              </Button>
              <Button
                variant="outline"
                onClick={() => upgrade("yearly")}
                disabled={isLoading}
              >
                Yearly (Save 16%)
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

---

## Testing

### Test Mode
1. Use Lemon Squeezy test mode API keys
2. Use test card numbers (4242 4242 4242 4242)
3. Verify webhook delivery in LS dashboard
4. Check subscription_events table for audit trail

### Webhook Testing
```bash
# Use ngrok for local webhook testing
ngrok http 8000

# Update webhook URL in LS dashboard to ngrok URL
# https://xxxxx.ngrok.io/api/webhooks/lemonsqueezy
```

### Manual Verification
1. Create checkout → complete payment
2. Verify `subscription_created` webhook received
3. Check workspace.subscription_status = "pro"
4. Cancel via customer portal
5. Verify `subscription_cancelled` webhook
6. Check workspace.subscription_status = "free"

---

## Security Considerations

1. **Webhook Signature**: Always verify HMAC signature
2. **Service Role**: Use service client for webhook DB updates (bypasses RLS)
3. **Audit Trail**: Log all subscription events
4. **Rate Limiting**: Add rate limits to checkout endpoint
5. **Idempotency**: Handle duplicate webhooks gracefully
