# yarnnn Monetization Strategy

> **Status**: Updated for ADR-100 (2-tier model)
> **Date**: 2026-03-09
> **Related**: ADR-100 (Simplified Monetization), ADR-053 (Platform Sync Monetization)

## Overview

This document outlines the monetization strategy for yarnnn. ADR-100 simplified from 3-tier to 2-tier (Free + Pro) with Early Bird pricing for beta.

**Key Insight (ADR-100)**: Gate on what costs money (LLM usage via monthly messages + agent count). Sync is cheap — don't gate on it beyond source counts.

---

## Payment Stack

### Lemon Squeezy
- **Why**: Handles all payment processing, PCI compliance, tax collection, and subscription management
- **Shared Account**: Same Lemon Squeezy account as episode-0, but separate products/stores
- **Integration**: REST API v1 with webhook-based status updates

---

## Pricing Model (ADR-100)

### Free Tier ($0)

**Limits**:
- **Platforms**: All 4
- **Sources per platform**: 5 Slack / 5 Gmail / 10 Notion / Unlimited Calendar
- **Sync frequency**: 1x/day
- **Monthly messages**: 50
- **Active agents**: 2

**Rationale**: Generous enough to experience value and build habits. 50 messages/month = ~12/week. 2 agents = Recap + one other. Users hit natural upgrade triggers when they want more.

### Pro Tier ($19/month standard, $9/month Early Bird)

**Limits**:
- **Platforms**: All 4
- **Sources per platform**: Unlimited
- **Sync frequency**: Hourly
- **Monthly messages**: Unlimited
- **Active agents**: 10

**Rationale**: Single paid tier — one decision for the user. Early Bird at $9/mo for beta users, locked in while available.

### Early Bird Strategy

- **$9/mo monthly only** — no yearly (limits locked-in loss exposure)
- Separate Lemon Squeezy variant — can stop selling at any time
- Existing $9 subscribers continue billing after variant removed
- Sunset at our discretion: post 100 users, post investment, etc.

### Yearly Discount (Standard only)

- **Pro**: $190/year (2 months free = 17% off)

---

## Lemon Squeezy Product Configuration

| Variant | Price | Env Var |
|---------|-------|---------|
| Pro Monthly (Standard) | $19/mo | `LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID` |
| Pro Yearly (Standard) | $190/yr | `LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID` |
| Pro Monthly (Early Bird) | $9/mo | `LEMONSQUEEZY_PRO_EARLYBIRD_VARIANT_ID` |

**Deprecated** (Starter variants — no longer used in code):
- `LEMONSQUEEZY_STARTER_MONTHLY_VARIANT_ID`
- `LEMONSQUEEZY_STARTER_YEARLY_VARIANT_ID`

---

## Environment Variables

### Backend (api/.env)

```bash
# Lemon Squeezy Configuration
LEMONSQUEEZY_API_KEY=your_api_key_here
LEMONSQUEEZY_STORE_ID=your_yarnnn_store_id
LEMONSQUEEZY_WEBHOOK_SECRET=your_webhook_secret

# Product Variants (ADR-100)
LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID=pro_monthly_variant
LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID=pro_yearly_variant
LEMONSQUEEZY_PRO_EARLYBIRD_VARIANT_ID=early_bird_variant

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

## Cost Analysis (ADR-100)

| Tier | Sync Cost/Mo | LLM Cost/Mo (est) | Price | Margin |
|------|--------------|-------------------|-------|--------|
| Free (active) | ~$0.05 | ~$6 | $0 | Loss leader |
| Free (blended 40% active) | ~$0.02 | ~$3 | $0 | Loss leader |
| Pro (moderate) | ~$0.50 | ~$7 | $19 | ~$11.50 (60%) |
| Pro (heavy) | ~$0.50 | ~$18 | $19 | ~$0.50 (3%) |
| Pro Early Bird (moderate) | ~$0.50 | ~$7 | $9 | ~$1.50 (17%) |

LLM costs are the dominant variable. Monthly message limit on free tier caps exposure.

### Break-Even

At $19 standard pricing with $3/mo blended free user cost:
- Need ~15% conversion for net-positive
- Realistic for B2B productivity tool with good activation

---

## User Flow

### Upgrade Flow

1. User clicks "Upgrade" on pricing page or settings
2. Selects billing period (monthly/yearly)
3. Frontend calls `POST /subscription/checkout` with billing period
4. Backend creates LS checkout session with `user_id`, `workspace_id` in custom data
5. User redirected to Lemon Squeezy hosted checkout
6. User completes payment
7. LS sends `subscription_created` webhook with variant_id
8. Backend sets `subscription_status = "pro"` on workspace
9. User redirected to success URL
10. Frontend reloads, shows Pro features

### Manage Subscription Flow

1. User clicks "Manage Subscription" in settings
2. Frontend calls `GET /subscription/portal`
3. Backend fetches portal URL from LS API
4. Frontend opens portal
5. User can cancel, update payment, etc.
6. LS sends webhook on any changes
7. Backend updates workspace status accordingly

### Downgrade Flow

If user cancels:
1. LS sends `subscription_cancelled` or `subscription_expired` webhook
2. Backend updates `subscription_status` to "free"
3. User retains access until `subscription_expires_at`
4. At expiry, features downgrade to free tier
5. Sources over limit are kept but not synced until limit complied

---

## Legacy Migration

- Existing "starter" subscribers: mapped to "pro" in `get_user_tier()` (ADR-100)
- Starter variant IDs: no longer referenced in code, can be removed from Render env vars
- Database `workspaces.subscription_status` can have "starter" value — handled gracefully

---

## Implementation Checklist

### Lemon Squeezy Setup

- [x] Pro Monthly product ($19/mo)
- [x] Pro Yearly product ($190/yr)
- [ ] Create Early Bird Pro Monthly product ($9/mo)
- [ ] Get Early Bird variant ID
- [ ] Set `LEMONSQUEEZY_PRO_EARLYBIRD_VARIANT_ID` on Render API service
- [ ] Verify webhook endpoint in LS dashboard

### Backend (ADR-100)

- [x] 2-tier constants in `platform_limits.py`
- [x] Monthly message limit enforcement in `chat.py`
- [x] Early Bird variant support in `subscription.py`
- [x] Legacy "starter" → "pro" mapping

### Frontend (ADR-100)

- [x] 2-tier pricing page
- [x] Updated SubscriptionCard
- [x] Updated UpgradePrompt
- [x] Updated hooks and types

### Database

- [x] `get_monthly_message_count()` RPC (migration 094)
- [ ] Run migration 094 on production

---

## See Also

- [ADR-100: Simplified Monetization](../adr/ADR-100-simplified-monetization.md)
- [ADR-053: Platform Sync Monetization](../adr/ADR-053-platform-sync-monetization.md)
- [LIMITS.md](./LIMITS.md) - Detailed limit enforcement
- [api/routes/subscription.py](../../api/routes/subscription.py) - Backend implementation
