# yarnnn Monetization Strategy

## Overview

This document outlines the monetization strategy for yarnnn, leveraging the same Lemon Squeezy account used for episode-0 (fantazy/chat_companion) but with yarnnn-specific products and pricing.

---

## Payment Stack

### Lemon Squeezy
- **Why**: Handles all payment processing, PCI compliance, tax collection, and subscription management
- **Shared Account**: Same Lemon Squeezy account as episode-0, but separate products/stores
- **Integration**: REST API v1 with webhook-based status updates

### Key Benefits
1. No PCI compliance burden (LS handles all card data)
2. Built-in customer portal for subscription management
3. Global tax handling (VAT, sales tax)
4. Webhook-driven architecture (real-time sync)
5. Multiple product support (subscriptions + one-time purchases)

---

## Pricing Model (Proposed)

### Free Tier
- **Cost**: $0
- **Limits**:
  - 1 project
  - 50 memories per project
  - 5 chat sessions per month
  - No scheduled agents
  - Community support

### Pro Tier
- **Cost**: $19/month (or $190/year - 2 months free)
- **Features**:
  - Unlimited projects
  - Unlimited memories
  - Unlimited chat sessions
  - 5 scheduled agents per project
  - 100 agent executions per month
  - Priority support

### Team Tier (Future)
- **Cost**: $49/month per seat
- **Features**:
  - Everything in Pro
  - Team collaboration
  - Shared projects
  - Admin controls
  - SSO integration

---

## Usage-Based Considerations

### Agent Executions
yarnnn's scheduled agents are the key differentiator. Consider:
- Base quota included in Pro tier
- Overage pricing for additional executions
- Or: separate execution packs (similar to episode-0's Spark packs)

### Document Storage
- Track storage usage per user
- Include reasonable limits in each tier
- Charge for overage or offer storage add-ons

---

## Implementation Requirements

### Lemon Squeezy Setup

1. **Create yarnnn Store** (or use existing store with separate products)
   - Store ID: `<to be configured>`
   - Products: yarnnn Pro Monthly, yarnnn Pro Yearly

2. **Configure Products**
   - Create subscription product in LS dashboard
   - Set up billing intervals (monthly/yearly)
   - Configure trial period if desired (e.g., 7-day trial)
   - Get Variant IDs for each plan

3. **Webhook Configuration**
   - Endpoint: `https://api.yarnnn.com/webhooks/lemonsqueezy`
   - Events to enable:
     - `subscription_created`
     - `subscription_updated`
     - `subscription_cancelled`
     - `subscription_expired`
     - `subscription_resumed`
     - `subscription_payment_failed`
     - `subscription_payment_success`
   - Signing secret: Use strong random string

---

## Environment Variables

### Backend (api/.env)
```bash
# Lemon Squeezy Configuration
LEMONSQUEEZY_API_KEY=your_api_key_here
LEMONSQUEEZY_STORE_ID=your_yarnnn_store_id
LEMONSQUEEZY_WEBHOOK_SECRET=your_webhook_secret
LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID=variant_id_for_monthly
LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID=variant_id_for_yearly

# Checkout Configuration
CHECKOUT_SUCCESS_URL=https://yarnnn.com/dashboard?subscription=success
```

### Frontend (web/.env.local)
```bash
# No LS-specific vars needed on frontend
# API handles all payment interactions
NEXT_PUBLIC_API_URL=https://api.yarnnn.com
```

---

## User Flow

### Upgrade Flow
1. User clicks "Upgrade" on pricing page or settings
2. Frontend calls `POST /subscription/checkout`
3. Backend creates LS checkout session with `user_id` in custom data
4. User redirected to Lemon Squeezy hosted checkout
5. User completes payment
6. LS sends `subscription_created` webhook
7. Backend verifies signature, updates user status
8. User redirected to success URL
9. Frontend reloads user data, shows premium features

### Manage Subscription Flow
1. User clicks "Manage Subscription" in settings
2. Frontend calls `GET /subscription/portal`
3. Backend fetches portal URL from LS API
4. Frontend opens portal in new tab
5. User can cancel, pause, update payment method
6. LS sends webhook on any changes
7. Backend updates user status accordingly

### Cancellation Flow
1. User cancels via LS customer portal
2. LS sends `subscription_cancelled` webhook
3. Backend sets `subscription_status = 'free'`
4. User retains access until `subscription_expires_at`
5. At expiry, features downgrade to free tier

---

## Database Schema Changes

### Users Table Additions
```sql
-- Add subscription fields to existing users/workspaces
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'free';
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS subscription_expires_at TIMESTAMPTZ;
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS lemonsqueezy_customer_id TEXT;
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS lemonsqueezy_subscription_id TEXT;

-- Indexes for lookups
CREATE INDEX IF NOT EXISTS idx_workspaces_ls_customer
  ON workspaces(lemonsqueezy_customer_id);
CREATE INDEX IF NOT EXISTS idx_workspaces_ls_subscription
  ON workspaces(lemonsqueezy_subscription_id);
```

### Subscription Events Audit Log
```sql
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

-- Indexes
CREATE INDEX idx_subscription_events_workspace ON subscription_events(workspace_id);
CREATE INDEX idx_subscription_events_type ON subscription_events(event_type);
CREATE INDEX idx_subscription_events_created ON subscription_events(created_at DESC);

-- RLS: Users can read their own events, only backend can write
ALTER TABLE subscription_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY subscription_events_select_own ON subscription_events
    FOR SELECT USING (
        workspace_id IN (
            SELECT id FROM workspaces WHERE owner_id = auth.uid()
        )
    );
```

---

## Feature Gating

### Backend Checks
```python
async def check_subscription_limit(workspace_id: str, feature: str) -> bool:
    """Check if workspace has access to a feature based on subscription."""
    workspace = await get_workspace(workspace_id)

    if workspace.subscription_status == "premium":
        return True  # Premium has all features

    # Free tier limits
    FREE_LIMITS = {
        "projects": 1,
        "memories_per_project": 50,
        "sessions_per_month": 5,
        "scheduled_agents": 0,
    }

    current_usage = await get_usage(workspace_id, feature)
    return current_usage < FREE_LIMITS.get(feature, 0)
```

### Frontend Gating
```typescript
// useSubscription hook
export function useSubscription() {
  const { workspace } = useWorkspace();

  const isPremium = workspace?.subscription_status === "premium";
  const canCreateAgent = isPremium; // Only premium can schedule agents

  return { isPremium, canCreateAgent, ... };
}
```

---

## Verification Checklist

Before launch, verify:

- [ ] Lemon Squeezy store configured with yarnnn products
- [ ] Webhook endpoint accessible and verified
- [ ] Signature verification working
- [ ] Test subscription flow end-to-end
- [ ] Test cancellation flow
- [ ] Test renewal webhooks
- [ ] Customer portal accessible
- [ ] Free tier limits enforced
- [ ] Premium features unlocked correctly
- [ ] Audit log capturing events

---

## Shared Account Implications

Using the same Lemon Squeezy account for both episode-0 and yarnnn:

### Advantages
- Single dashboard for revenue overview
- Shared customer support settings
- One payout destination
- Unified tax settings

### Separation Requirements
- **Separate Products**: Create distinct products for yarnnn
- **Webhook Routing**: Use different webhook endpoints per product/store
- **Customer IDs**: LS customer IDs are account-wide, but subscriptions are product-specific
- **Reporting**: Use LS tags or separate stores to filter revenue by product

### Recommendation
Create a **separate store** within the same LS account for yarnnn:
- Cleaner product separation
- Easier revenue attribution
- Independent webhook configuration
- Can still share account-level settings

---

## Next Steps

1. [ ] Create yarnnn store in Lemon Squeezy
2. [ ] Configure Pro Monthly and Pro Yearly products
3. [ ] Set up webhook endpoint in LS dashboard
4. [ ] Implement backend subscription routes (see IMPLEMENTATION.md)
5. [ ] Add database migrations for subscription fields
6. [ ] Implement frontend subscription components
7. [ ] Add pricing page content
8. [ ] Test full flow in test mode
9. [ ] Go live
