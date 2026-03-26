# yarnnn Monetization Documentation

## Overview

This directory contains documentation for yarnnn's monetization strategy. Payment processing via Lemon Squeezy (same account as episode-0, separate products).

## Documents

| Document | Description |
|----------|-------------|
| [STRATEGY.md](./STRATEGY.md) | Business strategy, pricing tiers, Lemon Squeezy setup |
| [UNIFIED-CREDITS.md](./UNIFIED-CREDITS.md) | **Subscription + Work Credits** — hybrid pricing model (decided) |
| [COST-MODEL.md](./COST-MODEL.md) | Per-task cost breakdown and unit economics |
| [LIMITS.md](./LIMITS.md) | Platform resource limits and enforcement framework |
| [IMPLEMENTATION.md](./IMPLEMENTATION.md) | Technical implementation guide (Lemon Squeezy integration) |

## Quick Reference

### Pricing Model (Subscription + Work Credits)

| | Free | Pro ($19/mo) |
|--|------|-------------|
| Chat (TP) | 50 messages/mo | **Unlimited** |
| Work credits | 20/mo | 500/mo |
| Overage | Hard stop | $5/100 credits |
| Sync frequency | 1x/day | Hourly |
| Active tasks | 2 | 10 |

**Work credit costs**: Task execution = 3 credits, Render = 1 credit. Chat is not credited — it's covered by the subscription.

### Key Environment Variables

```bash
LEMONSQUEEZY_API_KEY=xxx
LEMONSQUEEZY_STORE_ID=xxx
LEMONSQUEEZY_WEBHOOK_SECRET=xxx
LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID=xxx
LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID=xxx
LEMONSQUEEZY_PRO_EARLYBIRD_VARIANT_ID=xxx
CHECKOUT_SUCCESS_URL=https://yarnnn.com/settings?subscription=success
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/subscription/status` | GET | Get current subscription status |
| `/api/subscription/checkout` | POST | Create checkout session |
| `/api/subscription/portal` | GET | Get customer portal URL |
| `/api/webhooks/lemonsqueezy` | POST | Webhook receiver |
| `/api/user/limits` | GET | Get tier limits + usage |

## See Also

- [ADR-100: Simplified Monetization](../adr/ADR-100-simplified-monetization.md)
- [ADR-138: Agents as Work Units](../adr/) — tasks as the unit of autonomous work
