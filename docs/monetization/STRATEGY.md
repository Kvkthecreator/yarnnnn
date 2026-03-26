# yarnnn Monetization Strategy

> **Status**: Updated for subscription + work credits model. See [COST-MODEL.md](COST-MODEL.md) for per-task economics.
> **Date**: 2026-03-26 (revised)
> **Related**: ADR-100, [UNIFIED-CREDITS.md](./UNIFIED-CREDITS.md), [LIMITS.md](./LIMITS.md)

## Overview

Two-tier model (Free + Pro) with subscription + work credits hybrid pricing.

**Key Insight**: Subscription buys access + unlimited chat (Pro). Work credits meter autonomous work (task runs, renders). Chat is the product onramp — don't gate it for paying users.

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
- **Chat messages**: 150/month
- **Work credits**: 20/month
- **Active tasks**: 2
- **Sources**: 5 Slack / 10 Notion
- **Sync frequency**: 1x/day

**Rationale**: Generous enough to experience value. 150 messages = ~5/day. 20 credits = ~6 task runs. Users hit upgrade triggers when autonomous work proves valuable.

### Pro Tier ($19/month standard, $9/month Early Bird)

**Limits**:
- **Chat messages**: Unlimited
- **Work credits**: 500/month
- **Active tasks**: 10
- **Sources**: Unlimited
- **Sync frequency**: Hourly

**Rationale**: Single paid tier. Chat unlimited = no meter anxiety. Work credits bound the real cost variable. Early Bird at $9/mo for beta users.

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

## Cost Analysis

| Tier | Chat Cost/Mo | Work Cost/Mo | Price | Margin |
|------|-------------|-------------|-------|--------|
| Free (active) | ~$1.50 | ~$0.50 | $0 | Loss leader |
| Pro (moderate) | ~$4 | ~$4 | $19 | ~$11 (58%) |
| Pro (heavy chat) | ~$10 | ~$3 | $19 | ~$6 (32%) |
| Pro (heavy automation) | ~$1 | ~$11 | $19 | ~$7 (37%) |
| Pro Early Bird | ~$4 | ~$4 | $9 | ~$1 (11%) |

With prompt caching (deployed 2026-03-26), chat cost per message drops to ~$0.005-0.01. Work credits bound autonomous spend.

### Break-Even

At $19 standard pricing with ~$2/mo blended free user cost:
- Need ~10% conversion for net-positive
- Prompt caching significantly improves unit economics

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

## Post-Launch Considerations

### ADR-113 Impact on Activation and Upgrade Velocity (2026-03-16)

Auto source selection (ADR-113) removes the manual gate between platform connection and first value. This changes the **activation speed**, not the consumption ceiling. Users reach tier limits faster because there is no configuration step slowing them down.

**What this means for monetization:**

1. **Faster upgrade triggers.** Free users hit 2 agents sooner (bootstrap auto-creates one per platform, Composer may suggest a second). The upgrade prompt arrives while the user is engaged, not during a dead state where they haven't seen value. This is good — upgrade prompts in context convert better than upgrade prompts during setup friction.

2. **No new cost exposure.** All auto-creation paths (bootstrap, Composer) check `check_agent_limit()` before creating. `compute_smart_defaults()` respects tier source limits. Sync frequency is unchanged. The gates hold.

3. **Current tier limits are well-sized for the wedge ICP.** Free (2 agents, 50 messages, daily sync) is enough to experience value, not enough to live on. Pro ($19/mo, 10 agents, unlimited messages, hourly sync) covers the solo consultant use case with healthy margins at moderate usage.

**Deferred decisions — optimize with data, not in advance:**

| Signal to watch | What it means | Possible response |
|----------------|--------------|-------------------|
| Free users hit 2 agents and don't upgrade | Upgrade friction or insufficient perceived value | Improve first-run quality, adjust free agent limit, or add intermediate nudges |
| Pro users hit 10 agents and churn | Missing higher tier | Add Team/Business tier ($49-99/mo, 25+ agents, team features) |
| Heavy Pro users cost >$19/mo in LLM | Margin compression at scale | Usage-based pricing layer or higher tier with metered overages |
| Composer auto-creates agents users don't want | Wasted LLM spend on unwanted runs | Tighten Composer confidence thresholds, add "suggested but not created" mode |

**Architecture readiness:** The enforcement infrastructure supports tier expansion without structural changes. `TIER_LIMITS` is a dict, `get_user_tier()` is a function, Lemon Squeezy supports multiple variants. Adding a tier is a config + migration change, not an architectural one.

**Recommendation:** Ship with current 2-tier model. Measure activation-to-upgrade funnel post-ADR-113. Revisit tier structure after 50+ active users provide usage distribution data.

---

## See Also

- [ADR-100: Simplified Monetization](../adr/ADR-100-simplified-monetization.md)
- [ADR-053: Platform Sync Monetization](../adr/ADR-053-platform-sync-monetization.md)
- [LIMITS.md](./LIMITS.md) - Detailed limit enforcement
- [api/routes/subscription.py](../../api/routes/subscription.py) - Backend implementation
