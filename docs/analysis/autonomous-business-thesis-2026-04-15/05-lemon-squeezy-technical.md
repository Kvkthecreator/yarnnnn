# Lemon Squeezy Integration — Technical Assessment

> **Date**: 2026-04-15
> **Parent**: [README.md](README.md)

---

## What Lemon Squeezy Is

Lemon Squeezy is a merchant-of-record (MoR) platform for digital products and SaaS. MoR means Lemon Squeezy is the legal seller — they handle all tax compliance (EU VAT, US sales tax, GST) automatically. The user gets payouts; Lemon Squeezy handles invoicing, tax remittance, refunds, and chargebacks.

**Why MoR matters**: Without a MoR, a SaaS product selling internationally needs to register for VAT in each EU country where they have customers, file quarterly returns, handle reverse-charge mechanisms, manage US sales tax nexus across states, etc. Stripe can process payments but doesn't handle tax compliance. Lemon Squeezy eliminates this entire burden.

**Fees**: 5% + $0.50 per transaction (standard plan). Higher than Stripe (~2.9% + $0.30) but includes all tax compliance.

---

## API Surface Assessment

Lemon Squeezy exposes a REST API (JSON:API spec) with comprehensive coverage:

### Products & Variants

| Endpoint | Purpose | YARNNN relevance |
|----------|---------|-----------------|
| `POST /v1/products` | Create a product | Agent creates the paid offering |
| `POST /v1/variants` | Create pricing variants (monthly/annual/tiers) | Agent configures subscription options |
| `GET /v1/products` | List products | TP reads product catalog |
| `PATCH /v1/variants` | Update pricing | Agent adjusts pricing based on analytics |

### Checkouts

| Endpoint | Purpose | YARNNN relevance |
|----------|---------|-----------------|
| `POST /v1/checkouts` | Generate checkout session URL | Embeddable in emails, landing pages |
| Checkout URL | Direct link to payment page | Agent includes in newsletter signup flows |

### Subscriptions

| Endpoint | Purpose | YARNNN relevance |
|----------|---------|-----------------|
| `GET /v1/subscriptions` | List all subscriptions | Track subscriber count, MRR |
| `GET /v1/subscriptions/{id}` | Subscription details | Individual subscriber status |
| `PATCH /v1/subscriptions/{id}` | Update subscription | Upgrade/downgrade handling |
| `DELETE /v1/subscriptions/{id}` | Cancel subscription | Churn management |

### Webhooks

| Event | Purpose | YARNNN relevance |
|-------|---------|-----------------|
| `subscription_created` | New subscriber | Add to delivery list |
| `subscription_updated` | Plan change | Update subscriber tier |
| `subscription_cancelled` | Churn event | Remove from delivery, trigger re-engagement task |
| `subscription_payment_failed` | Failed payment | Flag for follow-up |
| `subscription_payment_recovered` | Payment recovered after failure | Restore delivery |
| `order_created` | One-time purchase | For non-subscription products |

### Analytics

| Endpoint | Purpose | YARNNN relevance |
|----------|---------|-----------------|
| `GET /v1/subscriptions` + filtering | MRR calculation | Tracker agent monitors revenue |
| `GET /v1/orders` | Revenue history | Analyst agent tracks growth |
| `GET /v1/customers` | Customer list | Subscriber management |
| `GET /v1/discount-redemptions` | Promo tracking | Campaign effectiveness |

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
| LS API client | 2-3 hours | None |
| Connection flow (API key input, validation, encrypted storage) | 1-2 hours | Client |
| 3 platform tools (list_products, get_subscribers, get_revenue) | 1-2 hours | Client |
| Task type: `ls-revenue-report` | 30 min | None |
| Directory registry: `/workspace/context/subscribers/` | 15 min | None |
| **Total Phase 1** | **~6 hours** | |

### Phase 2: Webhook-driven subscriber management

| Task | Effort | Dependency |
|------|--------|-----------|
| Webhook endpoint + signature verification | 1-2 hours | Phase 1 |
| Event → workspace file writes (subscriber added/removed/updated) | 1-2 hours | Phase 1 |
| Subscriber list as delivery target (Resend integration) | 2-3 hours | Phase 1 |
| **Total Phase 2** | **~6 hours** | |

### Phase 3: Agent-driven business operations

| Task | Effort | Dependency |
|------|--------|-----------|
| Checkout URL generation tool | 1 hour | Phase 1 |
| Product/variant creation tools | 1-2 hours | Phase 1 |
| Discount code creation tool | 30 min | Phase 1 |
| Re-engagement task type (triggered by churn webhook) | 1-2 hours | Phase 2 |
| **Total Phase 3** | **~5 hours** | |

**Total build: ~17 hours across three phases.**

This is not large. The integration is architecturally clean because post-ADR-153, all platform data flows through workspace context domains. Lemon Squeezy is just another data source feeding into `/workspace/context/subscribers/`.

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
- Low build cost (~17 hours)
- Clean architecture fit
- Validates the autonomous business thesis with real infrastructure
- Signals ambition in investor conversations

### Arguments for deferring
- No validated ICP for the business-builder persona
- Building infrastructure for an unvalidated use case is premature optimization
- The reference implementation (proof-of-thesis) can be done manually first — Kevin uses his own LS account, YARNNN produces the content, manual checkout link embedding. This validates the thesis without building the integration.
- Other integrations have higher validated demand (GitHub delivery, Notion publishing)

### Recommendation

**Defer to after reference implementation validation.** The build is small enough that it can be done in a single session when the time is right. Building it now creates infrastructure for a use case that hasn't been validated. Building it after the reference implementation proves the thesis converts "this could work" into "this works, now automate the last mile."

The right sequence:
1. Run a reference implementation manually (YARNNN produces content, Kevin handles LS manually)
2. Validate that the quality floor is sufficient for paying subscribers
3. Validate that subscriber acquisition is achievable
4. If 1-3 succeed, build the integration (Phase 1 first, expand as needed)
