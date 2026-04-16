# Architecture: Commerce Substrate

> **Status:** Canonical (ADR-183).
> **Date:** 2026-04-15
> **Rule:** All commerce integration, product delivery, and revenue data flow decisions should be consistent with this document.
> **Related:**
> - [ADR-183: Commerce Substrate](../adr/ADR-183-commerce-substrate.md) — governing ADR
> - [ADR-184: Product Health Metrics](../adr/ADR-184-product-health-metrics.md) — intelligence layer over commerce data
> - [PLATFORM-INTEGRATIONS.md](../integrations/PLATFORM-INTEGRATIONS.md) — platform connection patterns
> - [workspace-conventions.md](workspace-conventions.md) — filesystem path conventions
> - [registry-matrix.md](registry-matrix.md) — domain ↔ task ↔ agent matrix
> - [output-substrate.md](output-substrate.md) — render service that produces sellable assets

---

## What the Commerce Substrate Is

The commerce substrate is the **business layer** that enables a YARNNN workspace to function as a revenue-generating content product business. It connects agent-produced output to paying customers through a commerce provider.

Three concerns it addresses that no other layer owns:

1. **Commerce connection.** How does the user's commerce account (Lemon Squeezy, future: Stripe Connect, Paddle) connect to the workspace? API key auth, encrypted storage, same `platform_connections` pattern as Slack/Notion/GitHub.

2. **Revenue and customer perception.** How do revenue signals, subscriber behavior, and product performance flow into the workspace as accumulated context? Two canonical domains: `customers/` (per-customer entities) and `revenue/` (aggregate business metrics).

3. **Product delivery.** How do agent-produced deliverables reach paying subscribers? Subscriber list as delivery target — live-read from commerce provider API at delivery time, delivered via Resend.

Without this layer, YARNNN produces content but can't sell it. With it, the full loop closes: agents produce → render formats → delivery sends → subscribers pay → revenue accumulates → metrics inform next cycle.

---

## Commerce as Fourth Platform Class

| Class | Platforms | Auth | Data direction |
|---|---|---|---|
| Communication | Slack | OAuth | Read |
| Document | Notion | OAuth | Read + write (notion-update) |
| Work artifact | GitHub | OAuth | Read |
| **Commerce** | **Lemon Squeezy** (first) | **API key** | **Read + write + webhook inbound** |

Commerce is the first platform class with all three data directions:
- **Read**: agents query revenue, subscriber lists, product catalog
- **Write**: agents create products, attach rendered files, generate checkout URLs
- **Webhook inbound**: subscription/order events write customer and revenue data to workspace

---

## Two Distinct Commerce Surfaces

YARNNN has two commerce surfaces that must never be conflated:

| Surface | What it does | ADRs | User sees it as |
|---|---|---|---|
| **Platform billing** | YARNNN charges users for platform usage | ADR-171, ADR-172 | "My YARNNN bill" — Settings > Billing |
| **Content commerce** | Users sell products to their customers | ADR-183 | "My business revenue" — Context > revenue/ |

Platform billing (`token_usage`, `balance_transactions`, Lemon Squeezy for YARNNN's own subscriptions) is entirely separate from content commerce (user's Lemon Squeezy account, user's products, user's subscribers).

The user's Lemon Squeezy account is **theirs** — YARNNN agents operate it on their behalf via delegated API key, same legal model as Slack/Notion OAuth delegation.

---

## Provider Abstraction

```
CommerceProvider (abstract)
├── LemonSqueezyClient     ← first implementation
├── StripeConnectClient    ← future (when LS dependency risk materializes)
└── PaddleClient           ← future
```

The abstraction boundary: task pipeline, delivery service, context domains, and TP tools reference `CommerceProvider` methods — never LS-specific API shapes. Provider swap is a client implementation change, not a pipeline change.

**Key files:**
- `api/integrations/core/commerce_provider.py` — abstract interface
- `api/integrations/core/lemonsqueezy_client.py` — first implementation
- `api/services/platform_tools.py` — `platform_commerce_*` tools (provider-agnostic names)

---

## Context Domains

### `/workspace/context/customers/`

Canonical domain (not temporal). Per-customer entity structure:

```
customers/
├── _tracker.md         # Coverage: total, active, churned, segments
├── _analysis.md        # Cross-customer synthesis (cohorts, LTV distribution)
├── {customer-slug}/
│   ├── profile.md      # Status, plan, LTV, dates, email
│   └── history.md      # Event timeline (subscribed, upgraded, cancelled, purchased)
```

Written by: Commerce Bot (`commerce-digest` task) + webhook events.
Read by: Analyst (revenue-report), TP (product judgment), daily update.

### `/workspace/context/revenue/`

Canonical domain (not temporal). Aggregate business metrics:

```
revenue/
├── _tracker.md         # MRR, ARR, subscriber count, churn rate, growth rate
├── _analysis.md        # Trends, product mix analysis, pricing effectiveness
├── monthly/
│   └── {YYYY-MM}.md    # Monthly snapshot (revenue, new/churned, by-product breakdown)
└── products/
    └── {product-slug}.md  # Per-product: subscribers, revenue, conversion, churn
```

Written by: Commerce Bot (`commerce-digest` task) + webhook events.
Read by: Analyst (revenue-report), TP (product judgment), daily update.

---

## Commerce Bot

The 11th agent. Same class as Slack/Notion/GitHub bots (`platform-bot`).

| Field | Value |
|---|---|
| `role` | `commerce_bot` |
| `class` | `platform-bot` |
| `title` | Commerce Bot |
| Scaffolded at | Commerce provider connection (NOT signup) |
| Owns directories | `customers/`, `revenue/` |

Commerce Bot is NOT in the default signup roster. It's created when the user connects a commerce provider — same lazy-creation pattern as context domains (ADR-176: created by work demand).

---

## Task Types

| Type key | Output kind | Agent | Default schedule | Reads | Writes |
|---|---|---|---|---|---|
| `commerce-digest` | `accumulates_context` | Commerce Bot | Daily | (commerce API live) | `customers/`, `revenue/`, `signals/` |
| `revenue-report` | `produces_deliverable` | Analyst + Writer | Weekly | `revenue/`, `customers/`, `signals/` | (output folder) |
| `commerce-create-product` | `external_action` | Commerce Bot | Reactive | `revenue/`, `customers/` | (commerce API write) |
| `commerce-update-product` | `external_action` | Commerce Bot | Reactive | `revenue/` | (commerce API write) |
| `commerce-create-discount` | `external_action` | Commerce Bot | Reactive | `revenue/`, `customers/` | (commerce API write) |

---

## Delivery to Subscribers

When a task's TASK.md specifies `delivery: subscribers`:

```
execute_task() → delivery.py
  → read TASK.md delivery config
  → delivery target = "subscribers"
  → read product_id from TASK.md **Commerce:** field
  → call commerce provider: get_subscribers(product_id)
  → filter: status = "active"
  → deliver via Resend to each subscriber email
  → log delivery count in run metadata
```

**Live read, no cached list.** Subscriber list is always fresh from the commerce provider API at delivery time. No `subscribers` table in YARNNN — the commerce provider is the source of truth.

---

## Product Link on Tasks

Optional. A task producing a deliverable can link to a commerce product:

```markdown
## Task: Competitive Brief
**Mode:** recurring
**Schedule:** weekly
**Delivery:** subscribers
**Commerce:** product_id=abc123, checkout_url=https://store.lemonsqueezy.com/checkout/buy/abc123
```

When present: delivery targets subscribers, TP correlates output quality with product metrics.
When absent: task operates normally, no commerce integration.

---

## Webhook Flow

```
Commerce provider event (e.g., subscription_created)
  → POST /api/webhooks/commerce/lemonsqueezy
  → Verify signature
  → Resolve workspace from API key
  → Write to workspace files:
      customers/{slug}/profile.md (create/update)
      customers/{slug}/history.md (append event)
      revenue/_tracker.md (update aggregates)
  → Log activity_log event (commerce_webhook)
```

Events are workspace file mutations — no intermediate staging table (ADR-153 principle). All agents see the updated data on their next run.

---

## See Also

- [ADR-183: Commerce Substrate](../adr/ADR-183-commerce-substrate.md) — governing ADR
- [ADR-184: Product Health Metrics](../adr/ADR-184-product-health-metrics.md) — intelligence layer
- [output-substrate.md](output-substrate.md) — render service producing sellable formats
- [registry-matrix.md](registry-matrix.md) — full domain ↔ task ↔ agent matrix
- [PLATFORM-INTEGRATIONS.md](../integrations/PLATFORM-INTEGRATIONS.md) — platform connection patterns
