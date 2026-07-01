# YARNNN Monetization — Master Index

> **Updated**: 2026-07-01 — rewritten as the single index of all pricing canon (the pricing discourse spans `docs/monetization/`, `docs/adr/`, and `docs/analysis/`; this is the one entry point so the fragmentation is navigable). Prior index was ADR-291-era (2026-05-18) and predated the Freddie/pricing arc.

## TL;DR — where pricing stands (2026-07-01)

- **The MODEL is decided — [ADR-396](../adr/ADR-396-the-pricing-model-type-b-subscription-over-the-metered-balance.md)**: a **Type-B subscription over the metered balance** (plan tier + included allowance + overage; activity transparent, dollars not shown — the Claude pattern). **One meter** (LLM judgment invocations), **two gates** (connector retention [built] + count [candidate]), the **moat's reads free**. Overage = hard-stop + top-up the existing `balance_usd`; **no credit currency.** Ships on existing machinery (subscription_refill + top-up + hard-stop) — only new build is a plan-tier record + showing balance as a usage quantity.
- **What ships + charges TODAY (until an ADR-396 tier ships)**: **balance as the single gate** (ADR-172/291) — pay-as-you-go, $3 grant, top-ups, 2× Anthropic, hard-stop at zero. The live gate remains this until the first tier ships.
- **The one thing NOT decided**: the tier NUMBERS (base price + allowance size). Economics bound the base to ~$15–25/mo; the felt-value number is **customer-gated** — set against a first paying user, not ahead of one.
- **Deferred**: delegation-tiered seats (ADR-334) — a Rung-2/Phase-2 layer over ADR-396, not the launch.

## Two commerce surfaces (unchanged)

| Surface | Flow | Docs |
|---|---|---|
| **Platform billing** (YARNNN → User) | balance model, subscriptions + top-ups | this directory |
| **Content commerce** (User → User's customers) | commerce provider integration, subscriber delivery | [architecture/commerce-substrate.md](../architecture/commerce-substrate.md), [features/commerce.md](../features/commerce.md) |

*This index covers **Platform billing** only.*

---

## The pricing canon, mapped (live · forward · historical · archived)

### 🟢 LIVE — what is true and charges today
| Doc | What it is |
|---|---|
| [STRATEGY.md](./STRATEGY.md) | **The live model** — balance as single gate, subscription-as-optional-refill, top-ups, the 2× cost formula. |
| [COST-MODEL.md](./COST-MODEL.md) | Unit economics. *Figures are historical guidance; cost unit is now the wake, not the task (ADR-260/261).* |
| [IMPLEMENTATION.md](./IMPLEMENTATION.md) | **How Lemon Squeezy is wired** (mechanism — current; the *products* extend when a new model ratifies). |

### 🔵 THE DECIDED MODEL — ratified by ADR-396 (numbers demand-gated)
| Doc | What it is |
|---|---|
| [**PRICING-CONSOLIDATION-2026-07-01.md**](./PRICING-CONSOLIDATION-2026-07-01.md) | **The synthesis** — threads every scattered artifact into the two-objects framework + implementation seams + the 6 decisions that would end the delay. *Start here for the forward model.* |
| [analysis/value-based-pricing-the-action-surface-matrix-2026-06-30.md](../analysis/value-based-pricing-the-action-surface-matrix-2026-06-30.md) | The value matrix — every action valued by *worth*, not *cost*; derives "free to remember, pay to operate." |
| [analysis/budget-balance-and-pricing-after-freddie-2026-06-30.md](../analysis/budget-balance-and-pricing-after-freddie-2026-06-30.md) | The three-layer cost *architecture* (balance/allocation/ledger) — ratified as [ADR-391](../adr/ADR-391-budget-balance-and-the-three-layer-cost-model.md). |
| [analysis/phase-1-packaging-open-scoping-rung-2-pricing-2026-06-29.md](../analysis/phase-1-packaging-open-scoping-rung-2-pricing-2026-06-29.md) | The note that named the gap ("Phase-1 has no pricing thesis") — *closed by the consolidation.* |

### 🟣 ARCHITECTURE + DEFERRED MODELS — the ADRs
| ADR | Role |
|---|---|
| [ADR-172: Usage-First Billing](../adr/ADR-172-usage-first-billing.md) | **The live floor** — balance model, all tiers dissolved. |
| [ADR-291: Unified Cost Ledger](../adr/ADR-291-unified-cost-ledger.md) | `execution_events` = the sole cost substrate; 2× cache-inclusive. |
| [ADR-327: Budget & the Self-Improving Loop](../adr/ADR-327-budget-and-the-self-improving-loop.md) | `_budget.yaml` = the self-governed attention envelope (distinct from `balance_usd`). |
| [ADR-391: Three-Layer Cost Model](../adr/ADR-391-budget-balance-and-the-three-layer-cost-model.md) | **The cost architecture** (balance=workspace, allocation=principal, ledger=attributed). *Pricing decisions D2/D4/D6 reopened by the value analysis.* |
| [**ADR-396: The Pricing Model**](../adr/ADR-396-the-pricing-model-type-b-subscription-over-the-metered-balance.md) | **THE RATIFIED MODEL** — Type-B subscription over the metered balance; one meter, two gates, no credit currency. Numbers demand-gated. |
| [ADR-392: The Connector Lane](../adr/ADR-392-the-connector-lane.md) §D8 | **Retention window** — built pricing-ready (`connector_retention.py`); the model's first non-LLM tier gate. |
| [ADR-334: Per-Operation Pricing](../adr/ADR-334-per-operation-pricing.md) | **Deferred** — delegation-tiered seats; a Rung-2/Phase-2 layer over ADR-396, not the launch. |
| [ADR-171: Token Spend Metering](../adr/ADR-171-token-spend-metering.md) | Universal `cost_usd` meter (amended by ADR-291). |

### ⚪ HISTORICAL / ARCHIVED — kept for reference, not current
| Doc | Status |
|---|---|
| [TOKEN-ECONOMICS-ANALYSIS.md](./TOKEN-ECONOMICS-ANALYSIS.md) | Point-in-time (Mar 2026) audit; taxonomy instructive, figures superseded. |
| [archive/LIMITS.md](./archive/LIMITS.md) | Tier-limit model — dissolved by ADR-172. |
| [archive/UNIFIED-CREDITS.md](./archive/UNIFIED-CREDITS.md) | Work-credits model — dissolved by ADR-171/172. |

---

## Quick reference — the live model (ADR-172/291)

### Balance as single gate
| Source | Amount | Trigger |
|---|---|---|
| Signup grant | $3.00 | Workspace creation (one-time) |
| Top-up | $10 / $25 / $50 | Lemon Squeezy one-time order |
| Subscription refill | $20.00 | Pro billing cycle (reset, not accumulate) |
| Admin grant | any | Manual credit |

**Hard stop at zero balance.** No tier limits, no capability gates. Cost is the only gate.

### Billing rates (2× Anthropic, cache-inclusive)
```
Sonnet:  $6.00/MTok input,  $30.00/MTok output
Haiku:   $1.60/MTok input,   $8.00/MTok output
```
Cache discount **is** passed through (ADR-291): `compute_cost_usd_inclusive` bills cache_read at 10% and cache_create at 125% of the input rate → effective markup exactly 2× across cached and uncached calls. (`telemetry.py::_BILLING_RATES` is the single source of truth.)

### Key environment variables
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

### API endpoints
| Endpoint | Method | Description |
|---|---|---|
| `/api/subscription/status` | GET | Subscription status + balance |
| `/api/subscription/checkout` | POST | Create checkout session (subscription or top-up) |
| `/api/subscription/portal` | GET | Customer portal URL |
| `/api/webhooks/lemonsqueezy` | POST | Webhook receiver |
| `/api/user/limits` | GET | Balance + spend summary |

---

## See also (adjacent canon)
- [ADR-183: Commerce Substrate](../adr/ADR-183-commerce-substrate.md) — content commerce (the *other* surface).
- [ADR-184: Product Health Metrics](../adr/ADR-184-product-health-metrics.md) — revenue as first-class perception.
- [ADR-380: The Activation Ladder](../adr/ADR-380-the-activation-ladder-and-the-judgment-deferral-line.md) — Rung-0/1/2, the frame the pricing layers map onto.
