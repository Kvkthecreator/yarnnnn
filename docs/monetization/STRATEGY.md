# yarnnn Platform Billing Strategy

> **Status**: Updated for ADR-171/172 balance model (2026-04-15)
> **Supersedes**: Previous 2-tier subscription + work credits model (ADR-100)
> **Related**: ADR-171 (token spend metering), ADR-172 (usage-first billing)

---

## Billing Model: Balance as Single Gate (ADR-172)

One concept: **balance**. Every workspace has a `balance_usd`. All LLM calls deduct `cost_usd`. Hard stop at zero. No tiers, no capability gates.

### Balance Sources

| Kind | Amount | Trigger |
|---|---|---|
| `signup_grant` | $3.00 | Workspace creation (one-time) |
| `topup` | $10 / $25 / $50 | User purchases via Lemon Squeezy one-time order |
| `subscription_refill` | $20.00 | Pro subscription billing cycle (reset, not accumulate) |
| `admin_grant` | any | Admin manually credits balance |

### Subscription Is Optional Auto-Refill

Pro subscription ($19/mo or $180/yr) = $20 balance reset each billing cycle. No capability difference vs. a top-up user. Subscription is a commitment discount + predictability, not an access tier.

### What Was Removed (ADR-172)

- `active_tasks` limit (was 2 free / 10 pro)
- `monthly_messages` limit (was 150 free / unlimited pro)
- `sync_frequency` tier gate
- Source limits (Slack channels, Notion pages)
- Work credits (replaced by `cost_usd` metering)
- Early Bird pricing ($9/mo variant — existing subscribers grandfathered)
- `TIER_LIMITS`, `CREDIT_COSTS`, `PlatformLimits` — all deleted

---

## Token Spend Metering (ADR-171)

Universal unit: `cost_usd = (input_tokens × rate) + (output_tokens × rate)`.

### Billing Rates (2x Anthropic API)

```python
BILLING_RATES = {
    "claude-sonnet-4-6":         {"input_per_mtok": 6.00,  "output_per_mtok": 30.00},
    "claude-opus-4-6":           {"input_per_mtok": 30.00, "output_per_mtok": 150.00},
    "claude-haiku-4-5-20251001": {"input_per_mtok": 1.60,  "output_per_mtok": 8.00},
}
```

Cache discount not passed through — cache efficiency is platform margin.

### All LLM Call Sites Metered

| Surface | Caller tag |
|---|---|
| TP chat turns | `chat` |
| Task execution | `task_pipeline` |
| WebSearch synthesis | `web_search` |
| Context inference | `inference` |
| Task deliverable inference | `inference` |
| ManageTask evaluate | `evaluation` |
| Session continuity | `session_summary` |

---

## Payment Stack

### Lemon Squeezy (for YARNNN's own billing)

- **Role**: Merchant of record for YARNNN subscriptions + top-ups
- **Auth**: YARNNN's own API key (not user's)
- **Handles**: Tax compliance, invoicing, payouts, chargebacks

**Note**: This is YARNNN billing its users. Distinct from content commerce (ADR-183) where users bill their customers through their own LS account.

### Lemon Squeezy Products

| Product | LS type | Env var |
|---|---|---|
| Pro Monthly ($19/mo) | Subscription | `LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID` |
| Pro Yearly ($180/yr) | Subscription | `LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID` |
| Top-up $10 | One-time | `LEMONSQUEEZY_TOPUP_10_VARIANT_ID` |
| Top-up $25 | One-time | `LEMONSQUEEZY_TOPUP_25_VARIANT_ID` |
| Top-up $50 | One-time | `LEMONSQUEEZY_TOPUP_50_VARIANT_ID` |

---

## Unit Economics (Post-ADR-182)

| User profile | Tasks | Est. monthly LLM cost | Revenue | Margin |
|---|---|---|---|---|
| Casual (3 tasks, weekly) | ~12 runs/mo | ~$0.75 | $3 top-up or $19 sub | 75-96% |
| Active (6 tasks, mixed) | ~60 runs/mo | ~$3.80 | $19 subscription | 80% |
| Power (10 tasks, daily) | ~200 runs/mo | ~$8.00 | $19 subscription | 58% |

ADR-182 (pre-gather pipeline optimization) reduced per-task cost ~50% for `produces_deliverable` tasks. See [TOKEN-ECONOMICS-ANALYSIS.md](./TOKEN-ECONOMICS-ANALYSIS.md) for production data.

---

## See Also

- [ADR-171: Token Spend Metering](../adr/ADR-171-token-spend-metering.md)
- [ADR-172: Usage-First Billing](../adr/ADR-172-usage-first-billing.md)
- [COST-MODEL.md](./COST-MODEL.md) — per-task cost breakdown
- [TOKEN-ECONOMICS-ANALYSIS.md](./TOKEN-ECONOMICS-ANALYSIS.md) — full-stack audit
- [ADR-183: Commerce Substrate](../adr/ADR-183-commerce-substrate.md) — content commerce (separate surface)
