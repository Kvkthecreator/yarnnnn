# Lemon Squeezy Integration — Technical Assessment

> **Date**: 2026-04-15 (widened after founder discourse — LS is a full digital commerce surface, not just subscriptions)
> **Parent**: [README.md](README.md)

---

## What Lemon Squeezy Is

Lemon Squeezy is a merchant-of-record (MoR) platform for digital products and SaaS. MoR means Lemon Squeezy is the legal seller — they handle all tax compliance (EU VAT, US sales tax, GST) automatically. The user gets payouts; Lemon Squeezy handles invoicing, tax remittance, refunds, and chargebacks.

**Why MoR matters**: Without a MoR, a SaaS product selling internationally needs to register for VAT in each EU country where they have customers, file quarterly returns, handle reverse-charge mechanisms, manage US sales tax nexus across states, etc. Stripe can process payments but doesn't handle tax compliance. Lemon Squeezy eliminates this entire burden.

**Fees**: 5% + $0.50 per transaction (standard plan). Higher than Stripe (~2.9% + $0.30) but includes all tax compliance.

---

## Five Product/Payment Models — All API-Accessible

LS is not a subscription platform. It's a full digital commerce API. Five product models map to YARNNN agent output:

| Model | LS mechanism | What YARNNN agents produce & sell |
|-------|-------------|----------------------------------|
| **Recurring subscriptions** | Monthly/yearly billing, auto-renewal | Newsletters, intelligence briefs, signal trackers, market reports |
| **One-time digital downloads** | Pay once, get file(s) | Research reports, industry analyses, data compilations, strategy guides, templates |
| **License keys** | Key issued on purchase, validated by app | Gated content access, premium dashboard access, workspace export credentials |
| **Tiered variants** | Same product, multiple price/access tiers | Free (summary) vs. paid (full analysis + data + charts) |
| **File delivery** | LS hosts files, delivers post-purchase | PDFs, XLSX exports, PPTX decks, data packages |

**Critical alignment**: YARNNN's render service (8 skills: pdf, pptx, xlsx, chart, mermaid, html, data, image) already produces every file format LS can deliver. The output gateway is the production line; LS is the storefront.

### The checkout URL as universal distribution

LS checkout URLs are plain links: `https://yourstore.lemonsqueezy.com/checkout/buy/abc123`

No website required. No app required. No storefront required. The user puts the link anywhere:

| Distribution surface | Effort |
|---------------------|--------|
| Instagram bio / Linktree | Paste link |
| X/Twitter bio or post | Paste link |
| LinkedIn featured section | Paste link |
| Email signature | Paste link |
| YouTube description | Paste link |
| Blog/landing page | Embed button |
| Newsletter itself (free→paid upsell) | Include in delivery |
| Notion public page | Paste link |

This dramatically lowers the barrier. The minimum viable distribution for a YARNNN-powered digital product is a link in an Instagram bio.

---

## API Surface Assessment

Lemon Squeezy exposes a REST API (JSON:API spec) with comprehensive coverage:

### Products & Variants

| Endpoint | Purpose | YARNNN relevance |
|----------|---------|-----------------|
| `POST /v1/products` | Create a product | Agent creates the paid offering (subscription, download, or license) |
| `POST /v1/variants` | Create pricing/tier variants | Agent configures tiers (free summary vs. paid full report) |
| `GET /v1/products` | List products | TP reads product catalog |
| `PATCH /v1/variants` | Update pricing | Agent adjusts pricing based on performance analytics |

### Files

| Endpoint | Purpose | YARNNN relevance |
|----------|---------|-----------------|
| `POST /v1/files` | Upload file to variant | Attach render service output (PDF, XLSX, PPTX) to a product for delivery |
| `GET /v1/files` | List files | TP verifies current product files |
| `DELETE /v1/files/{id}` | Remove file | Replace outdated file on product update |

Files attached to a variant are automatically delivered to purchasers. Updating the file updates what all future (and existing) customers can download.

### Checkouts

| Endpoint | Purpose | YARNNN relevance |
|----------|---------|-----------------|
| `POST /v1/checkouts` | Generate checkout session URL | Embeddable anywhere — emails, bios, landing pages |
| Checkout URL | Direct link to hosted payment page | The universal distribution primitive — no website needed |

### Subscriptions & Orders

| Endpoint | Purpose | YARNNN relevance |
|----------|---------|-----------------|
| `GET /v1/subscriptions` | List all subscriptions | Track subscriber count, MRR |
| `GET /v1/subscriptions/{id}` | Subscription details | Individual subscriber status |
| `PATCH /v1/subscriptions/{id}` | Update subscription | Upgrade/downgrade handling |
| `DELETE /v1/subscriptions/{id}` | Cancel subscription | Churn management |
| `GET /v1/orders` | List all orders | Track one-time purchases, revenue |
| `GET /v1/order-items` | Order line items | Which products/variants sold |

### License Keys

| Endpoint | Purpose | YARNNN relevance |
|----------|---------|-----------------|
| `GET /v1/license-keys` | List issued keys | Track active licenses |
| `POST /v1/licenses/activate` | Activate a key | Gate access to premium content/exports |
| `POST /v1/licenses/validate` | Validate a key | Check if access is current |
| `POST /v1/licenses/deactivate` | Revoke a key | Handle cancellation |

### Webhooks

| Event | Purpose | YARNNN relevance |
|-------|---------|-----------------|
| `subscription_created` | New subscriber | Add to delivery list, update customer context |
| `subscription_updated` | Plan change | Update subscriber tier |
| `subscription_cancelled` | Churn event | Remove from delivery, trigger re-engagement task |
| `subscription_payment_failed` | Failed payment | Flag for follow-up |
| `subscription_payment_recovered` | Payment recovered after failure | Restore delivery |
| `order_created` | One-time purchase completed | Deliver file, update revenue tracking |
| `license_key_created` | New license issued | Grant access |

### Analytics

| Endpoint | Purpose | YARNNN relevance |
|----------|---------|-----------------|
| `GET /v1/subscriptions` + filtering | MRR calculation | Tracker agent monitors recurring revenue |
| `GET /v1/orders` + filtering | Revenue history | Analyst tracks total revenue, product mix |
| `GET /v1/customers` | Customer list | Subscriber/buyer management |
| `GET /v1/discount-redemptions` | Promo tracking | Campaign effectiveness |

---

## Render Service × LS Product Matrix

The output gateway already produces the formats LS can sell. The mapping is direct:

| Render skill | LS product type | Example |
|-------------|----------------|---------|
| `pdf` | One-time download or subscription attachment | "Q2 Fintech Landscape Report" — $49 download |
| `pptx` | One-time download | "Market Entry Strategy Deck" — $199 download |
| `xlsx` | One-time download or subscription attachment | "Competitor Pricing Database" — $29/month data subscription |
| `chart` | Embedded in subscription deliverables | Charts in weekly intelligence brief |
| `html` | Subscription email body | The newsletter itself, delivered via Resend |
| `data` | One-time download (JSON/CSV) | Raw signal data export |
| `image` | Embedded in products or standalone | Infographics, charts, visual assets |
| `mermaid` | Embedded in products | Architecture diagrams, process maps |

Every render skill maps to at least one LS product type. No new render skills needed.

---

## Architecture Fit

### Integration pattern

Lemon Squeezy would follow the same pattern as Slack, Notion, and GitHub integrations:

```
User provides API key → stored encrypted in platform_connections
→ Agents use key during task execution to call LS API
→ Webhook events received at /api/webhooks/lemonsqueezy
→ Events update subscriber state in YARNNN workspace
```

**Key difference from other integrations**: Slack/Notion/GitHub use OAuth. Lemon Squeezy's API uses API keys (simpler). No OAuth flow needed. The user generates an API key in their Lemon Squeezy dashboard and pastes it into YARNNN.

### Platform connection model

| Field | Value |
|-------|-------|
| `platform` | `lemonsqueezy` |
| `auth_type` | `api_key` (not OAuth) |
| `credentials` | Encrypted API key (Fernet, same as existing) |
| `status` | `connected` / `disconnected` |

### New infrastructure required

| Component | Effort | Notes |
|-----------|--------|-------|
| `api/integrations/core/lemonsqueezy_client.py` | Medium | REST client wrapping LS API. Pattern matches `github_client.py`. |
| Webhook endpoint | Low | `/api/webhooks/lemonsqueezy` — receives subscription events, writes to workspace context |
| Platform tools for TP | Low | `platform_lemonsqueezy_list_products`, `platform_lemonsqueezy_get_subscribers`, etc. Same pattern as GitHub tools (ADR-147) |
| Task types | Low | `ls-subscriber-digest` (accumulates_context), `ls-revenue-report` (produces_deliverable) |
| Directory registry entry | Trivial | `/workspace/context/subscribers/` temporal directory |
| Subscriber context files | Low | Per-subscriber entity files or aggregate tracker files in context domain |

### What is NOT needed

- No new database tables — subscriber data lives in workspace files (`/workspace/context/subscribers/`), same as all other platform data post-ADR-153
- No new primitives — existing `ManageTask`, `ReadFile`, `WriteFile`, `SearchFiles` cover all operations
- No new agent types — existing Tracker agent handles monitoring, existing Analyst handles synthesis
- No OAuth flow — API key auth is simpler than existing integrations
- No changes to task pipeline — standard execution flow

---

## Build Cost Estimate

### Phase 1: Read-only integration (minimum viable)

| Task | Effort | Dependency |
|------|--------|-----------|
| LS API client (products, variants, subscriptions, orders, customers, files, license-keys) | 3-4 hours | None |
| Connection flow (API key input, validation, encrypted storage) | 1-2 hours | Client |
| 5 platform tools (list_products, get_subscribers, get_revenue, get_orders, get_customers) | 2-3 hours | Client |
| Task types: `ls-revenue-report`, `ls-customer-digest` | 30 min | None |
| Directory registry: `/workspace/context/customers/` | 15 min | None |
| **Total Phase 1** | **~8 hours** | |

### Phase 2: Webhook-driven customer management

| Task | Effort | Dependency |
|------|--------|-----------|
| Webhook endpoint + signature verification | 1-2 hours | Phase 1 |
| Event → workspace file writes (subscriber/buyer added/removed/updated) | 1-2 hours | Phase 1 |
| Subscriber list as delivery target (Resend integration) | 2-3 hours | Phase 1 |
| **Total Phase 2** | **~6 hours** | |

### Phase 3: Agent-driven commerce operations

| Task | Effort | Dependency |
|------|--------|-----------|
| Checkout URL generation tool | 1 hour | Phase 1 |
| Product/variant creation tools (subscriptions + one-time + tiered) | 2-3 hours | Phase 1 |
| File upload tool (attach render output to product variant) | 1-2 hours | Phase 1 |
| Discount code creation tool | 30 min | Phase 1 |
| Re-engagement task type (triggered by churn webhook) | 1-2 hours | Phase 2 |
| **Total Phase 3** | **~7 hours** | |

**Total build: ~21 hours across three phases.**

Slightly larger than initial estimate (was ~17h) due to file upload, license key, and order endpoints. Still a single-day build per phase. The integration is architecturally clean because post-ADR-153, all platform data flows through workspace context domains. Lemon Squeezy is just another data source feeding into `/workspace/context/customers/`.

---

## The Per-User Account Requirement

The thread correctly identifies that each YARNNN user needs their own Lemon Squeezy account. This is a legitimate tax/payout identity requirement:

- Lemon Squeezy is the MoR — they need to know who they're paying out to
- Tax forms (W-9, W-8BEN) are tied to the individual/business receiving payouts
- This is the same requirement Stripe Connect has for marketplace sellers

**Implication for YARNNN**: YARNNN doesn't need a Lemon Squeezy account of its own. Each user connects their LS account via API key. YARNNN agents operate the user's LS account on their behalf. This is the same delegated-authority pattern as the existing Slack/Notion integrations — YARNNN acts as the user's agent (in the legal sense), operating tools the user has authorized.

**No ToS risk**: Unlike the Beehiiv concern (where YARNNN would be programmatically posting content to a publishing platform, potentially violating automation policies), Lemon Squeezy's API is explicitly designed for programmatic access. Creating products, generating checkouts, and managing subscriptions via API is a supported use case.

---

## Timing Assessment

### Arguments for building now
- Moderate build cost (~21 hours)
- Clean architecture fit — same pattern as Slack/Notion/GitHub
- Validates the autonomous business thesis with real infrastructure
- Signals ambition in investor conversations
- The checkout URL as distribution mechanism is a powerful demo — "put this link in your bio and earn money from what you know"
- Widens YARNNN from "agent platform" to "autonomous digital commerce" in a single integration

### Arguments for deferring
- No validated ICP for the knowledge monetizer persona yet
- Building infrastructure for an unvalidated use case is premature optimization
- The reference implementation (proof-of-thesis) can be done manually first — Kevin uses his own LS account, YARNNN produces the content, manual checkout link embedding. This validates the thesis without building the integration.

### Recommendation

**Defer Phase 2-3 to after reference implementation. Consider Phase 1 (read-only) earlier** — even during the reference implementation, having TP able to read revenue and customer data from LS enriches the Tracker/Analyst agents' context. The read-only integration (~8 hours) could be built alongside the reference implementation to give agents business intelligence about the product they're producing for.

The sequence:
1. Start reference implementation manually (YARNNN produces content, Kevin handles LS manually)
2. Build Phase 1 (read-only) during the reference implementation — agents can see revenue, customers, product performance
3. Validate quality floor + subscriber acquisition
4. If validated, build Phase 2 (webhooks) + Phase 3 (agent-driven commerce) — automate the last mile

---

## The Patreon Analogy

LS in this framing is less "payment infrastructure" and more **auto-Patreon**:

| Patreon | YARNNN + Lemon Squeezy |
|---------|----------------------|
| Creator makes content manually | Agents produce content autonomously |
| Tiers (free / $5 / $10) | LS variants (free email / paid report / premium data) |
| Patreon hosts the page | LS hosts the checkout, user links from anywhere |
| Creator posts to Patreon feed | Agents deliver via Resend + file attachments |
| Patrons get access to content | Customers get delivered products |
| Creator is the labor | Creator is the director; agents are the labor |

The critical difference: Patreon requires the creator to keep creating. YARNNN + LS runs autonomously. The agents produce, the delivery fires, the billing recurs. The creator's job is direction and audience — not production.

**It's Patreon where the content creates itself.**

This framing also explains why LS is the right MoR over Stripe: LS is built for exactly this pattern — digital creators selling digital products with no infrastructure. Stripe is built for developers building custom payment flows. The YARNNN user isn't a developer — they're a domain expert who wants a link that earns money.
