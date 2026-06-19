# yarnnn Platform Billing Strategy

> **Status**: Updated for ADR-291 unified cost ledger (2026-05-18). **This is the sole active pricing model (as of 2026-06-19).** The balance gate below — pay-as-you-go: $3 signup grant, top-ups, hard stop at zero, no tiers, no seats — is what ships and what charges. [ADR-334](../adr/ADR-334-per-operation-pricing.md) (per-operation delegation-tiered seats, $149/$299/$499) was **demoted 2026-06-19 from "Ratified direction" to "Deferred hypothesis"** — parked as one candidate, evidence-gated (zero external users + the desire axis unvalidated; see ADR-334 Amendment 2026-06-19). The balance model is therefore NOT re-scoped to a sub-layer; it stands alone as the whole model until the seat hypothesis clears its unblock conditions.
> **Supersedes**: Previous 2-tier subscription + work credits model (ADR-100)
> **Related**: ADR-334 (per-operation seats — **deferred hypothesis**, not active), ADR-171 (token spend metering, amended by ADR-291), ADR-172 (usage-first billing — **the active model**, amended by ADR-291), ADR-250 (execution telemetry), ADR-291 (unified cost ledger)

---

## Billing Model: Balance as Single Gate (ADR-172 + ADR-291)

One concept: **balance**. Every workspace has a `balance_usd`. Every LLM call deducts the cache-inclusive `cost_usd`. Hard stop at zero. No tiers, no capability gates.

### Balance Sources

| Kind | Amount | Trigger |
|---|---|---|
| `signup_grant` | $3.00 | Workspace creation (one-time) |
| `topup` | $10 / $25 / $50 | User purchases via Lemon Squeezy one-time order |
| `subscription_refill` | $20.00 | Pro subscription billing cycle (reset, not accumulate) |
| `admin_grant` | any | Admin manually credits balance |

### Subscription Is Optional Auto-Refill

Pro subscription ($19/mo or $180/yr) = $20 balance reset each billing cycle. No capability difference vs. a top-up user. Subscription is a commitment discount + predictability, not an access tier.

---

## Cost Computation (ADR-291)

**Single substrate, single function, single multiplier.**

Every LLM call writes one row to `execution_events` via `services.telemetry.record_execution_event()`. Cost is computed by `services.telemetry.compute_cost_usd_inclusive()` — cache-aware, 2x Anthropic markup. The multiplier is the durable rule: any future Anthropic optimization (cache discount changes, prompt compression, new model tiers) flows through this single function with no second pricing decision.

### Billing Rates (2× Anthropic published rates)

Defined in [`api/services/telemetry.py`](../../api/services/telemetry.py) — single source of truth.

```python
_BILLING_RATES = {
    "claude-sonnet-4-6":         {"input_per_mtok": 6.00,  "output_per_mtok": 30.00},
    "claude-opus-4-6":           {"input_per_mtok": 30.00, "output_per_mtok": 150.00},
    "claude-haiku-4-5-20251001": {"input_per_mtok": 1.60,  "output_per_mtok": 8.00},
}
```

### Cost Formula (cache-inclusive)

```
cost_usd = input_tokens          × input_rate
         + cache_read_tokens     × input_rate × 0.10   # Anthropic charges 10% for cache_read
         + cache_create_tokens   × input_rate × 1.25   # Anthropic charges 125% for cache_creation
         + output_tokens         × output_rate
```

The cache discount **is** passed through to the user — it lives in the formula. Effective markup on real Anthropic invoice cost is exactly 2× across cached and uncached calls alike. No hidden margin on cache-heavy workloads (which was the structural leak pre-ADR-291).

### Anthropic Cost View (derivable)

If we need to surface "what Anthropic invoiced us" separately from "what we billed the user," the math is `anthropic_cost_usd = cost_usd / 2.0`. Today this is computed on demand; no separate column.

---

## Substrate: `execution_events` (ADR-291)

The sole canonical cost ledger. Every LLM call across all 7 callers writes here.

| Caller | `execution_events.slug` |
|---|---|
| Reviewer addressed turn (chat) | `addressed` |
| Reviewer reflection / proposal arrival | recurrence slug (e.g., `morning-reflection`) |
| Specialist sub-LLM calls | `specialist:<role>` |
| Web search | `web-search` |
| Recurrence prompt inference | `recurrence-prompt-inference` |
| Workspace inference (first-act) | `infer-workspace` |
| Context inference | `infer-context:<target>` |
| Session summary | `session-summary` |

Columns: `slug`, `mode`, `trigger_type`, `status`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_create_tokens`, `cost_usd`, `model`, `duration_ms`, `tool_rounds`, `agent_run_id`, `envelope_load_ms`. Schema is rich enough to support per-recurrence analytics, per-mode rollups, cost-truth admin dashboards — all without JSONB joins.

### Effective Balance

```sql
effective_balance = workspace.balance_usd
                  - SUM(execution_events.cost_usd) since subscription_refill_at
```

Computed by the `get_effective_balance(user_id)` Postgres RPC. Read at the balance gate in `services/feed.py` (chat) and `services/invocation_dispatcher.py` (recurrence dispatch). Same effective balance across all surfaces; Reviewer reflection spend now debits it like every other call (was the structural leak pre-ADR-291).

---

## What Was Removed

### ADR-172 (2026-04-15)

- `active_tasks` limit (was 2 free / 10 pro)
- `monthly_messages` limit (was 150 free / unlimited pro)
- `sync_frequency` tier gate
- Source limits (Slack channels, Notion pages)
- Work credits (replaced by `cost_usd` metering)
- Early Bird pricing
- `TIER_LIMITS`, `CREDIT_COSTS`, `PlatformLimits` — all deleted

### ADR-291 (2026-05-18)

- `token_usage` table — dropped (migration 176)
- `services.platform_limits.compute_cost_usd` (cache-agnostic) — deleted
- `services.platform_limits.BILLING_RATES` (duplicate) — deleted
- `services.platform_limits.record_token_usage` — deleted
- `services.platform_limits.check_spend_budget` (legacy alias) — deleted
- `get_monthly_spend_usd` Postgres RPC — deleted (now a direct table read)

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

## Unit Economics

Production data informing these estimates is dated; see [TOKEN-ECONOMICS-ANALYSIS.md](./TOKEN-ECONOMICS-ANALYSIS.md) for the historical audit context. Post-ADR-291, cost computation is uniform across all callers (no more cache-heavy under-billing), which marginally reduces margin compression on Reviewer-heavy workloads.

| User profile | Tasks | Est. monthly LLM cost | Revenue | Margin |
|---|---|---|---|---|
| Casual (3 tasks, weekly) | ~12 runs/mo | ~$0.75 | $3 top-up or $19 sub | 75-96% |
| Active (6 tasks, mixed) | ~60 runs/mo | ~$3.80 | $19 subscription | 80% |
| Power (10 tasks, daily) | ~200 runs/mo | ~$8.00 | $19 subscription | 58% |

ADR-182 (pre-gather pipeline optimization) reduced per-task cost ~50% for `produces_deliverable` tasks.

---

## See Also

- [ADR-171: Token Spend Metering](../adr/ADR-171-token-spend-metering.md) — amended by ADR-291
- [ADR-172: Usage-First Billing](../adr/ADR-172-usage-first-billing.md) — amended by ADR-291
- [ADR-250: Execution Telemetry](../adr/ADR-250-execution-telemetry.md) — `execution_events` substrate
- [ADR-291: Unified Cost Ledger](../adr/ADR-291-unified-cost-ledger.md) — substrate collapse
- [COST-MODEL.md](./COST-MODEL.md) — per-task cost breakdown
- [TOKEN-ECONOMICS-ANALYSIS.md](./TOKEN-ECONOMICS-ANALYSIS.md) — full-stack audit (snapshot 2026-03-30)
- [ADR-183: Commerce Substrate](../adr/ADR-183-commerce-substrate.md) — content commerce (separate surface)
