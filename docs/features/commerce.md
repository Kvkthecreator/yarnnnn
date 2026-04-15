# Commerce — Sell What Your Agents Produce

> Connect a commerce provider, link a task to a product, deliver to paying subscribers.
> Architecture: [docs/architecture/commerce-substrate.md](../architecture/commerce-substrate.md)
> ADRs: [ADR-183](../adr/ADR-183-commerce-substrate.md), [ADR-184](../adr/ADR-184-product-health-metrics.md)

---

## How It Works

1. **Connect a commerce provider** — paste your Lemon Squeezy API key in Settings > Platforms. YARNNN stores it encrypted, same as Slack/Notion/GitHub credentials.

2. **Commerce Bot activates** — a new agent joins your roster, scoped to your commerce data. It runs a daily `commerce-digest` task that writes subscriber and revenue data to `/workspace/context/customers/` and `/workspace/context/revenue/`.

3. **Link a task to a product** — any `produces_deliverable` task can link to a commerce product via the `**Commerce:**` field in TASK.md. TP can help set this up.

4. **Deliver to subscribers** — tasks with `delivery: subscribers` send output to all active subscribers of the linked product. Delivered via Resend. Subscriber list is read live from your commerce provider at delivery time.

5. **Revenue informs everything** — your daily update shows business health alongside agent activity. TP reasons about product performance. Revenue trends feed back into task quality assessment.

---

## What You Can Sell

Your render service already produces every format Lemon Squeezy can deliver:

| What agents produce | Commerce product type | Example |
|---|---|---|
| Weekly reports (HTML email) | Recurring subscription | "Competitive Intelligence Brief" — $19/mo |
| Research reports (PDF) | One-time download | "Q2 Fintech Landscape" — $49 |
| Data compilations (XLSX) | Subscription attachment | "Competitor Pricing Database" — $29/mo |
| Strategy decks (PPTX) | One-time download | "Market Entry Strategy" — $199 |
| Signal trackers (HTML email) | Recurring subscription | "AI Startup Tracker" — $9/mo |

---

## Commerce Provider Support

| Provider | Auth | Status |
|---|---|---|
| **Lemon Squeezy** | API key | First provider (MoR — handles tax, invoicing, payouts) |
| Stripe Connect | OAuth | Future (when scale justifies) |
| Paddle | API key | Future |

YARNNN's commerce layer is provider-agnostic. Your workspace data, task pipeline, and delivery service don't change when you switch providers.

---

## Context Domains

Commerce creates two canonical workspace domains:

### `/workspace/context/customers/`
Per-customer entity files — subscriber status, purchase history, LTV, engagement signals. Written by Commerce Bot daily + webhook events in real-time.

### `/workspace/context/revenue/`
Aggregate business metrics — MRR, growth rate, product performance, monthly snapshots. Written by Commerce Bot daily. Browseable in Context surface.

---

## Task Types

| Task | What it does | Runs |
|---|---|---|
| **commerce-digest** | Reads commerce API, writes customer + revenue data to workspace | Daily (automatic) |
| **revenue-report** | Produces a business intelligence deliverable from accumulated revenue data | Weekly (configurable) |
| **commerce-create-product** | Creates a product in your commerce store, attaches rendered output | On demand (TP-triggered) |
| **commerce-update-product** | Updates product files with latest rendered output | On demand (TP-triggered) |

---

## Product Health in Daily Update

When commerce is connected and products exist, your daily update shifts from "what agents did" to "how your business is doing":

- Revenue snapshot (MRR, subscriber count, growth trend)
- Product-level callouts (per-product revenue, new/churned subscribers)
- Correlation signals ("gained 2 subscribers the week you added trend charts")

---

## See Also

- [Commerce Substrate Architecture](../architecture/commerce-substrate.md) — how it works under the hood
- [Platform Integrations](../integrations/PLATFORM-INTEGRATIONS.md) — connection patterns
- [Task Types](task-types.md) — full task type catalog
- [Output Substrate](../architecture/output-substrate.md) — render service producing sellable formats
