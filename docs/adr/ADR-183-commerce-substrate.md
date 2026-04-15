# ADR-183: Commerce Substrate — Provider-Agnostic Business Layer

> **Status**: Phase 1-2 Implemented
> **Date**: 2026-04-15
> **Related**: ADR-138 (Agents as Work Units), ADR-141 (Unified Execution), ADR-151/152 (Context Domains / Directory Registry), ADR-153 (Platform Content Sunset — same principle: no mirrored cache, live API reads), ADR-158 (Platform Bot Ownership), ADR-171/172 (Token Spend Metering / Usage-First Billing), ADR-176 (Work-First Agent Model)
> **Extends**: `docs/analysis/autonomous-business-thesis-2026-04-15/05-lemon-squeezy-technical.md` (LS technical assessment — absorbed, not superseded)
> **Supersedes**: `docs/monetization/STRATEGY.md` (stale: references old tiers/credits), `docs/monetization/LIMITS.md` (stale: superseded by ADR-172), `docs/monetization/UNIFIED-CREDITS.md` (stale: superseded by ADR-171), `docs/monetization/README.md` (stale: references old model)

---

## Context

### Two commerce surfaces, one system

YARNNN has two structurally different commerce surfaces:

| Surface | Flow | What it does | Status |
|---|---|---|---|
| **Platform billing** | YARNNN → User | Charges users for platform usage (token spend, subscriptions, top-ups) | Implemented (ADR-171/172) |
| **Content commerce** | User → User's customers | Enables users to sell content products their agent team produces | **Missing** |

ADR-171/172 solved platform billing. This ADR addresses content commerce — the layer that makes a YARNNN workspace function as a business.

### Why this is load-bearing

The agent-native product thesis (`docs/analysis/autonomous-business-thesis-2026-04-15/09-agent-native-product-thesis.md`) commits YARNNN to Product B: "AI agent team you hire to run a content product business." A content product business requires commerce infrastructure. Without it:

- Users can produce content but can't sell it
- The moat story ("switching means revenue drops") can't be measured or proven
- The seven-layer operational stack (thesis doc) has layers 1-4 built, layers 5-7 (commerce, analytics, growth) absent
- "Autonomous business" is aspirational positioning, not product reality

### Why provider-agnostic

Lemon Squeezy is the right first provider (MoR, tax compliance, API-key auth, file delivery, checkout URLs). But LS is a dependency risk at scale:

- 5% + $0.50/tx fees compress margins as revenue grows
- Single-vendor lock-in on the commerce layer of an autonomous business platform
- If LS changes terms, pricing, or API, every user's business is affected

The architecture must treat LS the same way it treats Slack/Notion/GitHub — a connected platform, not a hard dependency. Commerce provider is a connection, not the commerce layer itself.

### What already exists

The LS technical assessment (doc 05) maps the full API surface and estimates ~21h build across 3 phases. It recommends deferring Phase 2-3 until reference implementation validates. This ADR absorbs that assessment and places it within the architectural framework.

---

## Decisions (all locked)

### 1. Commerce is the fourth platform class

Three platform classes exist today:

| Class | Platforms | Auth | Data flow |
|---|---|---|---|
| **Communication** | Slack | OAuth | Live reads during task execution |
| **Document** | Notion | OAuth | Live reads during task execution |
| **Work artifact** | GitHub | OAuth | Live reads during task execution |

Commerce adds a fourth:

| Class | Platforms | Auth | Data flow |
|---|---|---|---|
| **Commerce** | Lemon Squeezy (first) | API key | Live reads + webhook-driven writes |

Same `platform_connections` table. Same encrypted credential storage. Same `platform_tools.py` pattern for TP access. Same agent-mediated observation pattern (ADR-158).

**Key difference**: Commerce platforms have a write-back path that other platforms don't. Agents read subscriber/revenue data (like reading Slack messages), but they also create products, generate checkout URLs, and attach rendered files to products. This is the `external_action` output_kind — same pattern as `slack-respond` and `notion-update`.

### 2. Commerce data lives in workspace context domains

Post-ADR-153, all platform data flows through tasks into workspace context domains. Commerce is no exception.

Two commerce-specific context domains:

| Domain | Type | Contains | Written by |
|---|---|---|---|
| `customers/` | canonical | Per-customer entity files (subscriber status, purchase history, LTV, engagement signals) | Commerce bot + Tracker |
| `revenue/` | canonical | Aggregate revenue files (MRR tracker, product performance, churn log, revenue timeline) | Commerce bot + Analyst |

Both registered in `directory_registry.py` as canonical domains (not temporal like `slack/`, `notion/`, `github/`). Commerce data is canonical because it's the user's business data — it persists, accumulates, and informs strategy. Platform chat is temporal; revenue is permanent.

**Entity structure (customers/):**
```
/workspace/context/customers/
├── _tracker.md              # Coverage: total customers, active subscribers, churn rate
├── _analysis.md             # Cross-customer synthesis (segments, cohorts, trends)
├── {customer-slug}/
│   ├── profile.md           # Name, email, plan, status, LTV, first purchase, last activity
│   └── history.md           # Purchase/subscription events timeline
```

**Entity structure (revenue/):**
```
/workspace/context/revenue/
├── _tracker.md              # MRR, ARR, subscriber count, churn rate, growth rate
├── _analysis.md             # Revenue trends, product mix, pricing effectiveness
├── monthly/
│   └── {YYYY-MM}.md         # Monthly revenue snapshot (revenue, new/churned, product breakdown)
└── products/
    └── {product-slug}.md    # Per-product performance (subscribers, revenue, conversion rate)
```

### 3. Commerce bot owns the commerce context

Same pattern as platform bots (ADR-158): one bot, one platform, one directory.

| Agent | Platform | Directory | Task types |
|---|---|---|---|
| Slack Bot | Slack | `/workspace/context/slack/` | `slack-digest` |
| Notion Bot | Notion | `/workspace/context/notion/` | `notion-digest` |
| GitHub Bot | GitHub | `/workspace/context/github/` | `github-digest` |
| **Commerce Bot** | Lemon Squeezy (first) | `/workspace/context/customers/`, `/workspace/context/revenue/` | `commerce-digest`, `revenue-report` |

Commerce Bot is the 11th agent in the roster (ADR-176 currently specifies 9 + TP = 10). Added to `AGENT_TEMPLATES` and `DEFAULT_ROSTER` in `agent_framework.py`.

**However**: Commerce Bot is NOT scaffolded at signup. Unlike platform bots (which are scaffolded because platform connections are available from day one), Commerce Bot is scaffolded when the user connects a commerce provider. Same lazy-creation pattern as context domains — created by work demand, not pre-scaffolded.

### 4. Four commerce task types

| Task type | Output kind | Agent | Schedule | Domains |
|---|---|---|---|---|
| `commerce-digest` | `accumulates_context` | Commerce Bot | Daily | writes: `customers/`, `revenue/`, `signals/` |
| `revenue-report` | `produces_deliverable` | Analyst + Writer | Weekly | reads: `revenue/`, `customers/`, `signals/` |
| `commerce-create-product` | `external_action` | Commerce Bot | Reactive (TP-triggered) | reads: task output folder → creates LS product + attaches files |
| `commerce-update-product` | `external_action` | Commerce Bot | Reactive (TP-triggered) | reads: task output folder → updates LS product files |

`commerce-digest` follows the same pattern as `slack-digest` / `notion-digest` — bot reads from platform API, writes structured observations to context domain. Revenue and customer data flows into workspace the same way Slack messages and Notion pages do.

`commerce-create-product` and `commerce-update-product` are the write-back path. When a `produces_deliverable` task has output ready for sale, TP (or user) triggers product creation. The Commerce Bot reads the rendered output (PDF, XLSX, HTML), calls the commerce provider API to create/update the product, and returns the checkout URL.

### 5. Delivery target: subscriber list

Current delivery targets: email (Resend), Slack channel, Notion page, in-app.

Commerce adds: **subscriber list**. A task with `delivery: subscribers` delivers to all active subscribers of a linked commerce product. The delivery service reads the subscriber list from the commerce provider API at delivery time (live read, no cached list).

**Delivery flow:**
```
Task output ready
  → delivery.py reads task TASK.md delivery config
  → delivery target = "subscribers"
  → reads linked product_id from TASK.md
  → calls commerce provider API: GET subscribers for product_id
  → filters: status = active
  → delivers via Resend to each subscriber email
  → logs delivery count to run metadata
```

This closes the loop: agents produce → render service formats → delivery sends to paying subscribers → commerce provider bills them.

### 6. Product link on tasks (optional, not a new entity)

Tasks can optionally link to a commerce product. No new `product` entity — the link is a field in TASK.md:

```markdown
**Commerce:** product_id=abc123, checkout_url=https://store.lemonsqueezy.com/checkout/buy/abc123
```

When present:
- Delivery can target subscribers of this product
- TP and Analyst can correlate task output quality with product revenue/churn
- Commerce Bot can update the product's files when new output is rendered

When absent: task operates normally with no commerce integration.

### 7. Provider abstraction layer

`api/integrations/core/commerce_provider.py` — abstract interface:

```python
class CommerceProvider(ABC):
    """Provider-agnostic commerce operations."""
    
    @abstractmethod
    async def list_products(self) -> list[Product]: ...
    
    @abstractmethod
    async def get_subscribers(self, product_id: str) -> list[Subscriber]: ...
    
    @abstractmethod
    async def get_revenue_summary(self, period: str) -> RevenueSummary: ...
    
    @abstractmethod
    async def create_product(self, name: str, price: int, interval: str) -> Product: ...
    
    @abstractmethod
    async def attach_file(self, product_id: str, file_path: str) -> None: ...
    
    @abstractmethod
    async def create_checkout(self, product_id: str) -> str: ...  # returns URL
    
    @abstractmethod
    async def list_customers(self) -> list[Customer]: ...
```

`api/integrations/core/lemonsqueezy_client.py` — first implementation. Same pattern as `slack_client.py`, `notion_client.py`, `github_client.py`.

When a second provider is needed (Stripe Connect, Paddle, etc.), add a new client implementing `CommerceProvider`. The task pipeline, delivery service, and context domains don't change.

### 8. Webhook endpoint for commerce events

`/api/webhooks/commerce/{provider}` — receives subscription/order events, writes to workspace context.

| Event | Effect |
|---|---|
| `subscription_created` | Write customer profile to `customers/{slug}/profile.md` |
| `subscription_cancelled` | Update customer profile status, write to churn log in `revenue/` |
| `subscription_payment_failed` | Flag customer, surface in daily update |
| `order_created` | Write purchase to customer history, update revenue tracker |
| `subscription_payment_recovered` | Clear flag, update customer status |

Webhook events write directly to workspace files — no intermediate staging table (same principle as ADR-153). Events are workspace mutations, visible to all agents on their next run.

### 9. TP platform tools for commerce

Same pattern as existing platform tools (`platform_slack_*`, `platform_notion_*`, `platform_github_*`):

| Tool | Purpose | When available |
|---|---|---|
| `platform_commerce_list_products` | List products in commerce store | Commerce connected |
| `platform_commerce_get_subscribers` | Get subscriber list for a product | Commerce connected |
| `platform_commerce_get_revenue` | Get revenue summary (MRR, total, by product) | Commerce connected |
| `platform_commerce_create_checkout` | Generate a checkout URL for a product | Commerce connected |
| `platform_commerce_get_customers` | List all customers | Commerce connected |

Tools are provider-agnostic in name and interface. The underlying client dispatches to the connected provider.

---

## What Does Not Change

- Task pipeline (`task_pipeline.py`) — commerce tasks flow through the same `execute_task()` path
- Agent execution model — Commerce Bot is just another agent with `role='commerce_bot'` and `class='platform-bot'`
- Workspace filesystem — commerce domains follow existing conventions (ADR-152)
- Delivery service — subscriber delivery is an extension of existing email delivery via Resend
- Working memory — commerce signals surface to TP via existing compact index pattern (ADR-159)
- Token metering — commerce bot task runs metered via existing `token_usage` (ADR-171)
- Balance model — commerce bot runs consume balance like any other task (ADR-172)

---

## Implementation Phases

### Phase 1: Read-only integration (~8h)

**Build during reference implementation.** Agents can see revenue and customer data even while Kevin handles LS manually.

- `lemonsqueezy_client.py` (REST client, API key auth, rate limiting)
- `commerce_provider.py` (abstract interface)
- Connection flow (API key input → encrypted storage in `platform_connections`)
- 5 platform tools (list_products, get_subscribers, get_revenue, get_customers, create_checkout)
- Directory registry entries (`customers/`, `revenue/`)
- Task types: `commerce-digest` (accumulates_context), `revenue-report` (produces_deliverable)
- Commerce Bot agent template (scaffolded on commerce connection, not at signup)

### Phase 2: Webhook-driven customer management (~6h)

**Build after reference implementation validates quality + subscriber acquisition.**

- Webhook endpoint (`/api/webhooks/commerce/lemonsqueezy`) + signature verification
- Event → workspace file writes (customer profiles, revenue tracker, churn log)
- Subscriber list as delivery target in `delivery.py`
- Commerce product link in TASK.md (`**Commerce:**` field)
- `commerce-digest` task type gains webhook-event context (recent events injected into generation)

### Phase 3: Agent-driven commerce operations (~7h)

**Build when users need autonomous commerce management.**

- Product creation tools (`commerce-create-product` task type)
- File attachment tools (attach render output to LS product variant)
- Product update tools (`commerce-update-product` task type)
- Discount/promo code creation tool
- Re-engagement task type (triggered by churn webhook — Tracker observes, TP recommends action)

### Phase 4: Provider abstraction validation (deferred)

**Build when LS dependency risk materializes or second provider is needed.**

- Stripe Connect implementation of `CommerceProvider`
- Provider selection in connection flow
- Migration path for existing LS connections

---

## Monetization Docs Cleanup (same commit as this ADR)

The `docs/monetization/` directory is stale. Four files reference the old tier/credits model superseded by ADR-171/172:

| File | Status | Action |
|---|---|---|
| `README.md` | Stale (references tiers, credits, Early Bird) | Rewrite to reflect balance model + commerce substrate |
| `STRATEGY.md` | Stale (references 2-tier, work credits, Early Bird) | Rewrite to reflect ADR-172 balance model |
| `LIMITS.md` | Stale (references TIER_LIMITS, CREDIT_COSTS, work_credits) | Rewrite to reflect ADR-172 (balance is single gate) |
| `UNIFIED-CREDITS.md` | Dead (explicitly superseded by ADR-171) | Delete or archive |
| `COST-MODEL.md` | Partially stale (per-task estimates outdated by ADR-182) | Update cost figures |
| `IMPLEMENTATION.md` | Partially stale | Update to reflect current subscription.py |
| `TOKEN-ECONOMICS-ANALYSIS.md` | Live analysis, mostly current | Keep, update Section 6+8 per ADR-182 |

---

## Revision History

| Date | Change |
|---|---|
| 2026-04-15 | v1.0 — Initial proposal. All decisions locked. Commerce as fourth platform class, provider-agnostic abstraction, two context domains, Commerce Bot, four task types, subscriber delivery target, product link on tasks. |
| 2026-04-15 | v1.1 — **Phase 1 Implemented.** `CommerceProvider` abstract interface + `LemonSqueezyClient` (LS REST API v1, retry, pagination). 5 platform tools (list_products, get_subscribers, get_revenue, get_customers, create_checkout). Commerce Bot in `AGENT_TEMPLATES` + `DEFAULT_ROSTER`. `customers/` + `revenue/` context domains in directory registry (v4.0). `commerce-digest` + `revenue-report` task types. Commerce connect endpoint (`POST /integrations/commerce/connect`, API key auth). Migration 147: `commerce_bot` added to `agents_role_check`. |
| 2026-04-15 | v1.2 — **Phase 2 Implemented.** Webhook endpoint (`POST /webhooks/commerce/lemonsqueezy`) — subscription_created/cancelled/payment events write customer profiles + history to workspace files (ADR-153 principle: no staging table). Subscriber delivery target (`delivery: subscribers` in TASK.md) — live-reads subscriber list from commerce API at delivery time, sends individually via Resend. `**Commerce:**` field parsed from TASK.md (product_id, checkout_url). Product_id injected into delivery destination for subscriber filtering. |
