# yarnnn Monetization Strategy

> **Status**: Updated for ADR-053
> **Date**: 2026-02-12
> **Related**: ADR-053 (Platform Sync Monetization), LIMITS.md

## Overview

This document outlines the monetization strategy for yarnnn, leveraging the same Lemon Squeezy account used for episode-0 (fantazy/chat_companion) but with yarnnn-specific products and pricing.

**Key Insight (ADR-053)**: Platform sync is the **base monetization layer**. Sync is cheap (~$0.003/user/day), highly profitable, and directly correlates with value delivered.

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

## Pricing Model (ADR-053 Aligned)

### Free Tier ($0)

**Limits**:
- **Platforms**: 2 connected
- **Sources per platform**:
  - 1 Slack channel
  - 1 Gmail label (INBOX)
  - 1 Notion page
  - 1 Calendar
- **Sync frequency**: 2x/day (8am, 6pm user timezone)
- **TP conversations**: 20/month
- **Active deliverables**: 3

**Rationale**: "1 source per platform" - enough to experience value, fast onboarding, clear upgrade path.

### Starter Tier ($9/month)

**Limits**:
- **Platforms**: 4 connected
- **Sources per platform**:
  - 5 Slack channels
  - 5 Gmail labels
  - 5 Notion pages
  - 3 Calendars
- **Sync frequency**: 4x/day (every 6 hours)
- **TP conversations**: 100/month
- **Active deliverables**: 10

**Rationale**: Solo users who want "enough" - multiple sources per platform, comparable to Notion/Slack premium.

### Pro Tier ($19/month)

**Limits**:
- **Platforms**: 4 connected
- **Sources per platform**:
  - 20 Slack channels
  - 15 Gmail labels
  - 25 Notion pages
  - 10 Calendars
- **Sync frequency**: Hourly
- **TP conversations**: Unlimited
- **Active deliverables**: Unlimited

**Rationale**: Power users with multiple active projects, near real-time sync.

### Yearly Discount
- **Starter**: $90/year (2 months free = 17% off)
- **Pro**: $190/year (2 months free = 17% off)

---

## Lemon Squeezy Product Configuration

### Products to Create/Update

| Product | Variant ID Env Var | Price | Billing |
|---------|-------------------|-------|---------|
| YARNNN Starter Monthly | `LEMONSQUEEZY_STARTER_MONTHLY_VARIANT_ID` | $9/mo | Monthly |
| YARNNN Starter Yearly | `LEMONSQUEEZY_STARTER_YEARLY_VARIANT_ID` | $90/yr | Yearly |
| YARNNN Pro Monthly | `LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID` | $19/mo | Monthly |
| YARNNN Pro Yearly | `LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID` | $190/yr | Yearly |

### Migration from Current Setup

Current setup only has Pro tier. Need to:

1. **Create Starter products** in Lemon Squeezy dashboard
2. **Update env vars** with new variant IDs
3. **Update webhook handler** to distinguish starter vs pro
4. **Update frontend** for 3-tier pricing display

---

## Environment Variables

### Backend (api/.env)

```bash
# Lemon Squeezy Configuration
LEMONSQUEEZY_API_KEY=your_api_key_here
LEMONSQUEEZY_STORE_ID=your_yarnnn_store_id
LEMONSQUEEZY_WEBHOOK_SECRET=your_webhook_secret

# Product Variants (ADR-053 aligned)
LEMONSQUEEZY_STARTER_MONTHLY_VARIANT_ID=starter_monthly_variant
LEMONSQUEEZY_STARTER_YEARLY_VARIANT_ID=starter_yearly_variant
LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID=pro_monthly_variant
LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID=pro_yearly_variant

# Checkout Configuration
CHECKOUT_SUCCESS_URL=https://yarnnn.com/settings?subscription=success
```

### Webhook Endpoint

```
POST https://api.yarnnn.com/webhooks/lemonsqueezy
```

Events to enable:
- `subscription_created`
- `subscription_updated`
- `subscription_cancelled`
- `subscription_expired`
- `subscription_resumed`
- `subscription_payment_failed`
- `subscription_payment_success`

---

## Backend Implementation

### Tier Detection from Variant ID

```python
# In subscription.py webhook handler

def get_tier_from_subscription(attrs: dict) -> str:
    """
    Determine tier from subscription attributes.

    Uses variant_id to distinguish Starter from Pro.
    """
    variant_id = str(attrs.get("variant_id", ""))

    starter_variants = {
        LEMONSQUEEZY_STARTER_MONTHLY_VARIANT_ID,
        LEMONSQUEEZY_STARTER_YEARLY_VARIANT_ID,
    }
    pro_variants = {
        LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID,
        LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID,
    }

    if variant_id in pro_variants:
        return "pro"
    elif variant_id in starter_variants:
        return "starter"
    else:
        return "free"
```

### Database Schema

Existing `workspaces.subscription_status` field supports string values:
- `"free"` - Default, no subscription
- `"starter"` - Starter tier subscription
- `"pro"` - Pro tier subscription

No migration needed - just update values.

---

## Frontend Implementation

### Checkout Flow

```typescript
// Updated to support tier selection
async function createCheckout(tier: "starter" | "pro", billing: "monthly" | "yearly") {
  const response = await api.subscription.createCheckout({
    tier,
    billing_period: billing,
  });
  window.location.href = response.checkout_url;
}
```

### Pricing Display (3-tier)

```tsx
<PricingTable>
  <PricingTier
    name="Free"
    price="$0"
    features={[
      "2 platforms",
      "1 source per platform",
      "2x/day sync",
      "20 TP conversations/mo",
      "3 active deliverables",
    ]}
  />
  <PricingTier
    name="Starter"
    price="$9/mo"
    features={[
      "4 platforms",
      "5 sources per platform",
      "4x/day sync",
      "100 TP conversations/mo",
      "10 active deliverables",
    ]}
    cta="Upgrade to Starter"
    highlighted
  />
  <PricingTier
    name="Pro"
    price="$19/mo"
    features={[
      "4 platforms",
      "15-25 sources per platform",
      "Hourly sync",
      "Unlimited TP conversations",
      "Unlimited deliverables",
    ]}
    cta="Upgrade to Pro"
  />
</PricingTable>
```

---

## Cost Analysis (ADR-053)

| Tier | Sync Cost/Mo | LLM Cost/Mo (est) | Price | Margin |
|------|--------------|-------------------|-------|--------|
| Free | ~$0.05 | ~$0.50 | $0 | Loss leader |
| Starter | ~$0.15 | ~$2 | $9 | ~$6.85 (76%) |
| Pro | ~$0.50 | ~$5 | $19 | ~$13.50 (71%) |

Platform sync (no LLM) is extremely profitable. LLM usage is the variable cost controlled by conversation/deliverable limits.

---

## User Flow

### Upgrade Flow

1. User clicks "Upgrade" on pricing page or settings
2. Selects tier (Starter or Pro) and billing period (monthly/yearly)
3. Frontend calls `POST /subscription/checkout` with tier + billing
4. Backend creates LS checkout session with `user_id`, `workspace_id`, `tier` in custom data
5. User redirected to Lemon Squeezy hosted checkout
6. User completes payment
7. LS sends `subscription_created` webhook with variant_id
8. Backend determines tier from variant_id, updates workspace
9. User redirected to success URL
10. Frontend reloads, shows new tier features

### Manage Subscription Flow

1. User clicks "Manage Subscription" in settings
2. Frontend calls `GET /subscription/portal`
3. Backend fetches portal URL from LS API
4. Frontend opens portal in new tab
5. User can cancel, pause, upgrade, downgrade, update payment
6. LS sends webhook on any changes
7. Backend updates workspace status accordingly

### Downgrade Flow

If user downgrades from Pro to Starter or cancels:

1. LS sends `subscription_updated` or `subscription_cancelled` webhook
2. Backend updates `subscription_status` to new tier or "free"
3. User retains access until `subscription_expires_at`
4. At expiry, features downgrade to new tier
5. **Grace period**: Sources over limit are kept but not synced until limit complied

---

## Checkout URLs

Direct checkout links for manual sharing/testing:

| Product | Direct Checkout URL |
|---------|---------------------|
| Starter Monthly | https://kvklabs.lemonsqueezy.com/checkout/buy/a4f4838a-fe39-4920-8fd9-8637b4d2767a |
| Starter Yearly | https://kvklabs.lemonsqueezy.com/checkout/buy/4a1ae29c-e95a-4b13-a59f-512e12493ab1 |
| Pro Monthly | (via dashboard checkout) |
| Pro Yearly | (via dashboard checkout) |

---

## Implementation Checklist

### Lemon Squeezy Setup

- [x] Create Starter Monthly product ($9/mo) - Variant ID: 1301254
- [x] Create Starter Yearly product ($90/yr) - Variant ID: 1301257
- [x] Verify Pro Monthly product ($19/mo)
- [x] Verify Pro Yearly product ($190/yr)
- [x] Get variant IDs for all 4 products
- [x] Update environment variables on Render
- [ ] Verify webhook endpoint in LS dashboard

### Backend Updates

- [x] Webhook handler exists (`api/routes/subscription.py`)
- [x] Update checkout endpoint to accept `tier` parameter
- [x] Update webhook handler to detect tier from variant_id (`get_tier_from_variant_id()`)
- [x] Update status endpoint to return tier name

### Frontend Updates

- [x] SubscriptionCard component exists
- [x] Update for 3-tier pricing display
- [x] Add tier selection to checkout flow
- [x] Update upgrade prompts to mention Starter option

### Testing

- [ ] Test Starter monthly checkout flow
- [ ] Test Starter yearly checkout flow
- [ ] Test Pro monthly checkout flow
- [ ] Test Pro yearly checkout flow
- [ ] Test tier detection from webhook
- [ ] Test downgrade handling
- [ ] Test cancel flow

---

## Migration Path

### Existing Pro Subscribers

Existing Pro subscribers remain Pro. No changes needed.

### New Signups

New users start on Free tier and can upgrade to Starter or Pro.

### Pricing Page

Update pricing page to show 3-tier comparison with value emphasis on Starter as "best value for solo users".

---

## See Also

- [ADR-053: Platform Sync Monetization](../adr/ADR-053-platform-sync-monetization.md)
- [LIMITS.md](./LIMITS.md) - Detailed limit enforcement
- [api/routes/subscription.py](../../api/routes/subscription.py) - Backend implementation
