# yarnnn Monetization Documentation

> **Updated**: 2026-04-15 (ADR-171/172 balance model, ADR-183/184 commerce substrate)

## Two Commerce Surfaces

YARNNN has two distinct commerce surfaces:

| Surface | Flow | Docs |
|---|---|---|
| **Platform billing** (YARNNN → User) | Token spend metering, balance model, subscriptions + top-ups | This directory |
| **Content commerce** (User → User's customers) | Commerce provider integration, subscriber delivery, product health metrics | [docs/architecture/commerce-substrate.md](../architecture/commerce-substrate.md), [docs/features/commerce.md](../features/commerce.md) |

## Platform Billing Documents

| Document | Description |
|----------|-------------|
| [STRATEGY.md](./STRATEGY.md) | Billing model: balance as single gate, subscriptions as optional auto-refill, top-ups |
| [COST-MODEL.md](./COST-MODEL.md) | Per-task cost breakdown and unit economics |
| [IMPLEMENTATION.md](./IMPLEMENTATION.md) | Technical implementation (Lemon Squeezy for YARNNN's own billing) |
| [TOKEN-ECONOMICS-ANALYSIS.md](./TOKEN-ECONOMICS-ANALYSIS.md) | Full-stack LLM cost audit (production data) |

## Quick Reference — Platform Billing (ADR-171/172)

### Billing Model: Balance as Single Gate

| Source | Amount | Trigger |
|---|---|---|
| Signup grant | $3.00 | Workspace creation (one-time) |
| Top-up | $10 / $25 / $50 | User purchases via Lemon Squeezy one-time order |
| Subscription refill | $20.00 | Pro subscription billing cycle (reset, not accumulate) |
| Admin grant | any | Admin manually credits balance |

**Hard stop at zero balance.** No tier limits, no capability gates. Cost is the only gate.

### Billing Rates (2x Anthropic API rates)

```
Sonnet:  $6.00/MTok input,  $30.00/MTok output
Haiku:   $1.60/MTok input,   $8.00/MTok output
```

Cache discount not passed through — cache efficiency is platform margin.

### Key Environment Variables

```bash
LEMONSQUEEZY_API_KEY=xxx
LEMONSQUEEZY_STORE_ID=xxx
LEMONSQUEEZY_WEBHOOK_SECRET=xxx
LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID=xxx
LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID=xxx
LEMONSQUEEZY_TOPUP_10_VARIANT_ID=xxx
LEMONSQUEEZY_TOPUP_25_VARIANT_ID=xxx
LEMONSQUEEZY_TOPUP_50_VARIANT_ID=xxx
CHECKOUT_SUCCESS_URL=https://yarnnn.com/settings?subscription=success
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/subscription/status` | GET | Subscription status + balance |
| `/api/subscription/checkout` | POST | Create checkout session (subscription or top-up) |
| `/api/subscription/portal` | GET | Customer portal URL |
| `/api/webhooks/lemonsqueezy` | POST | Webhook receiver |
| `/api/user/limits` | GET | Balance + spend summary |

## Archived Documents

| Document | Status | Superseded by |
|---|---|---|
| ~~UNIFIED-CREDITS.md~~ | Archived | ADR-171 (token spend metering) |
| ~~LIMITS.md~~ | Archived | ADR-172 (balance as single gate — all tier limits dissolved) |

## See Also

- [ADR-171: Token Spend Metering](../adr/ADR-171-token-spend-metering.md) — universal `cost_usd` meter
- [ADR-172: Usage-First Billing](../adr/ADR-172-usage-first-billing.md) — balance model, tiers dissolved
- [ADR-183: Commerce Substrate](../adr/ADR-183-commerce-substrate.md) — content commerce (user → user's customers)
- [ADR-184: Product Health Metrics](../adr/ADR-184-product-health-metrics.md) — revenue as first-class perception
