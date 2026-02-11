# yarnnn Monetization Documentation

## Overview

This directory contains documentation for yarnnn's monetization strategy using Lemon Squeezy for payment processing. The implementation reuses the same Lemon Squeezy account as episode-0 (fantazy/chat_companion) but with separate yarnnn-specific products.

## Documents

| Document | Description |
|----------|-------------|
| [STRATEGY.md](./STRATEGY.md) | Business strategy, pricing tiers, and Lemon Squeezy setup |
| [IMPLEMENTATION.md](./IMPLEMENTATION.md) | Technical implementation guide with code examples |
| [LIMITS.md](./LIMITS.md) | Platform resource limits and enforcement framework |

## Quick Reference

### Pricing Tiers (Proposed)

| Tier | Price | Key Features |
|------|-------|--------------|
| Free | $0 | 1 project, 50 memories, 5 sessions/mo |
| Pro | $19/mo | Unlimited projects, scheduled agents |
| Enterprise | Custom | High limits, custom integrations, SLA |
| Team | $49/seat/mo | Collaboration, SSO (future) |

### Platform Resource Limits

| Resource | Free | Pro | Enterprise |
|----------|------|-----|------------|
| Slack channels | 5 | 20 | 100 |
| Gmail labels | 3 | 10 | 50 |
| Notion pages | 5 | 25 | 100 |
| Calendar events | 3 | 10 | 50 |
| Total platforms | 3 | 10 | 50 |

### Key Environment Variables

```bash
# Backend
LEMONSQUEEZY_API_KEY=xxx
LEMONSQUEEZY_STORE_ID=xxx
LEMONSQUEEZY_WEBHOOK_SECRET=xxx
LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID=xxx
LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID=xxx
CHECKOUT_SUCCESS_URL=https://yarnnn.com/dashboard?subscription=success
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/subscription/status` | GET | Get current subscription status |
| `/api/subscription/checkout` | POST | Create checkout session |
| `/api/subscription/portal` | GET | Get customer portal URL |
| `/api/webhooks/lemonsqueezy` | POST | Webhook receiver |

### Database Tables

- `workspaces`: Subscription fields added
- `subscription_events`: Audit log for all events

## Implementation Status

### Subscription System (Lemon Squeezy)
- [ ] Lemon Squeezy store setup
- [ ] Product/variant configuration
- [x] Backend subscription routes (`api/routes/subscription.py`)
- [x] Database migrations (`supabase/migrations/010_subscription_fields.sql`)
- [ ] Frontend subscription components
- [ ] Pricing page content
- [ ] End-to-end testing
- [ ] Production deployment

### Platform Resource Limits
- [x] Backend limit enforcement (`api/services/platform_limits.py`)
- [x] Frontend limit display (platform detail page)
- [x] Inline source selection with limit checking
- [x] Upgrade prompts for free tier users at limit
- [ ] Usage tracking dashboard
- [ ] Overage handling/notifications

## Shared Account Notes

yarnnn uses the same Lemon Squeezy account as episode-0. Key implications:

1. **Separation**: Create separate store or products for yarnnn
2. **Webhooks**: Configure separate webhook endpoints
3. **Reporting**: Use LS tags or filters for revenue attribution
4. **Customer IDs**: Account-wide, but subscriptions are product-specific

See [STRATEGY.md](./STRATEGY.md) for detailed shared account considerations.
