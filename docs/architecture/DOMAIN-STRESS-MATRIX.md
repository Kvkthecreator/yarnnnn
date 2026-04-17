# Domain Stress Matrix

> **Status**: Canonical (living document)
> **Date**: 2026-04-17
> **Authors**: KVK, Claude
> **Ratified by**: ADR-191 (Polymath Operator ICP + Domain Stress Discipline)
> **Purpose**: The agnostic thesis conscience. Every ADR, prompt change, and surface design is gated by a matrix check.

---

## Purpose

YARNNN's architecture is **agnostic by design** (ADR-188 / 189 / 190). This document prevents *verticalization by stealth* — the slow drift that happens when every feature request from whichever alpha operator shouts loudest nudges the product toward one domain.

**Gate rule for every new ADR, feature, or prompt change:**

Before shipping, the author adds one row to the *Impact* table in the ADR stating how the change affects each active alpha domain. Acceptable patterns:

- **"Helps all columns"** → green-light.
- **"Helps most, neutral on others"** → green-light.
- **"Helps one, neutral elsewhere"** → **verticalization warning**. Requires explicit justification or design revision.
- **"Helps one, hurts others"** → **reject or rescope**. Verticalizing by stealth.

This document is append-only. Each alpha domain row expands with lived experience. New domains are added when a fifth/sixth alpha spins up. Retired domains (if any) stay in the doc as historical context with an archival banner.

---

## Alpha domains

Four domains covering a broad structural spread of recurring knowledge work + external action work. Two active, two scheduled.

| # | Domain | Status | Integration | First operator |
|---|--------|--------|-------------|----------------|
| 1 | **E-commerce operator** | Active (priority 1) | Commerce (Lemon Squeezy via ADR-183) | Close network, TBD |
| 2 | **Day trader** | Active (priority 2) | Alpaca (ADR-187) | Close network, TBD |
| 3 | **AI influencer** | Scheduled | TBD (content platform integration) | Close network, TBD |
| 4 | **International trader** | Scheduled | TBD (trade/logistics data integration) | Close network, TBD |

---

## Domain 1: E-commerce operator

### Operator shape
Solo or 1–3 person e-commerce business. Direct-to-consumer via Lemon Squeezy, Shopify, or similar. 1–N products. Recurring revenue from subscriptions + one-time sales + discounts. Customer base is relatively small (100–10,000) but each customer is known well enough to segment.

### Identity shape (what `IDENTITY.md` encodes)
- Business name, what they sell, who they sell to, price points
- Platform connections (LS, Shopify, email provider, analytics)
- Goals (revenue growth, churn reduction, new product launches)
- Current work patterns (how often they ship updates, run campaigns)

### Rich input typical (Day 1)
- Store URL (LS/Shopify) — YARNNN fetches product list, tone, imagery
- Past email campaigns — voice + audience signal
- Product description docs — terminology + brand
- Customer feedback / reviews — audience sentiment

### Entities typical
- **Customers** (segmented: active / churning / churned / high-LTV / new)
- **Products** (active / drafts / archived / top-performing / underperforming)
- **Orders** (recent / disputed / refunded / subscription-renewing-soon)
- **Campaigns** (past sends / planned / performance by segment)
- **Competitors** (pricing + positioning + product launches)

### Work intent typical
- **Recurring**: weekly sales brief, monthly customer health review, campaign performance report
- **Reactive**: churn alert (customer hasn't ordered in N days), abandoned-cart trigger, competitor price-drop signal, low-inventory flag
- **Goal**: new product launch (4–6 week bounded objective)

### Deliverable shape
- **Weekly sales brief** — revenue by product, new vs. returning, top customers, week-over-week (document OR dashboard)
- **Churn alerts** — individual customer cards with recommended action (operational pane)
- **Campaign briefs** — upcoming email content drafted from performance data + brand voice (document)
- **Product performance report** — monthly, identifies underperformers + next-action recs (document)

### Surface archetype needs
- **Document** — weekly brief, monthly report, campaign drafts (current yarnnn strength)
- **Dashboard** — revenue-by-product, customer cohort view, subscription MRR trend, live-sales counter
- **Operational pane** — churn alerts, abandoned-cart triggers, product-update proposals, price-match alerts

All three archetypes needed. Operational pane is load-bearing for autonomy.

### Write primitives needed (for trusted autonomy)

Currently shipped (ADR-183):
- `create_product`, `update_product`, `create_discount`

Additional needed for alpha autonomy:
- `issue_refund` — reverse an order on user-approved trigger
- `update_inventory` / `set_stock_level` — adjust inventory on signals
- `bulk_price_update` — apply pricing change across SKUs
- `archive_product` — retire SKU
- `send_campaign_email` — transactional/marketing email via connected provider
- `respond_to_customer_inquiry` — reply to support email on approved template
- `create_product_variant` — expand SKU portfolio
- `tag_customer` / `segment_customer` — mutate customer metadata for targeting

~8 new write primitives to close the gap. Scope for ADR-192.

### Autonomous decisions (where TP should propose action via ADR-193)
- "Competitor X dropped price 10% on matching SKU — match price or hold?"
- "SKU Y sold out — promote sibling SKU or mark back-in-stock waitlist?"
- "Customer segment Z at churn risk (no orders 45 days) — send re-engagement campaign?"
- "12 abandoned carts ≥48h old — send recovery email with discount?"
- "Product X underperforming 30d — archive, re-price, or run promo?"
- "New customer from segment with high LTV pattern — add to VIP segment?"

### Revenue signal (feeds ADR-184 product-health)
- MRR from subscriptions
- AOV (average order value)
- Subscriber count (growth + churn)
- Revenue-per-product
- Campaign conversion rate
- Customer LTV by segment

### Failure modes (where YARNNN could embarrass itself)
- Updates wrong product (SKU mismatch, description swapped between products)
- Sends campaign to wrong segment (targeting error)
- Misreads inventory (oversells out-of-stock product)
- Applies discount to wrong SKU
- Responds to customer with stale/wrong information
- Archives active product accidentally
- Misattributes revenue to wrong campaign

**Error cost profile:** moderate. Most writes are reversible within hours. Customer-facing errors (wrong email copy sent) are harder to reverse and higher reputational cost. Pricing errors mid-revenue are short-term but recoverable.

---

## Domain 2: Day trader

### Operator shape
Retail or small-fund trader (prop shop, 1–3 person). Active manager running discretionary or rules-based strategies. Holds equity, options, or a mix. Uses Alpaca (or similar) for execution. Small-to-medium portfolio ($10K–$500K). Risk tolerance defined, strategy defined or evolving.

### Identity shape
- Trader's strategy description (value, momentum, thematic, technical, etc.)
- Risk parameters (max position size, stop-loss discipline, max drawdown)
- Account size + account type (paper / live, cash / margin)
- Sectors / instruments of focus
- Time horizon (intraday / swing / position)

### Rich input typical (Day 1)
- Connect Alpaca account — YARNNN fetches positions + watchlist
- Thesis doc or strategy notes — captures decision framework
- Paper-trading history — past decisions + outcomes
- Preferred data sources (research subscriptions, feeds)

### Entities typical
- **Instruments** (equities / options / ETFs, with sector / thesis tags)
- **Positions** (open / closed / pending / stop-loss set / at-risk)
- **Watchlist items** (tracked for entry signal, by thesis)
- **Trades** (entry + exit log with rationale)
- **Strategies** (named decision frameworks with performance history)

### Work intent typical
- **Recurring**: daily pre-market brief, end-of-day P&L + position review, weekly strategy performance
- **Reactive**: stop-loss triggered alert, thesis-trigger entry signal, unusual volume alert, earnings approaching
- **Goal**: thesis validation window (e.g., "hold position until Q2 earnings")

### Deliverable shape
- **Daily pre-market brief** — market overnight summary, positions snapshot, watchlist triggers (document OR dashboard)
- **EOD review** — P&L, trades taken, rationale captured (document)
- **Trade signal card** — "Enter AAPL at $X, size Y, stop Z — approve?" (operational pane)
- **Weekly strategy report** — Sharpe, drawdown, win rate per strategy (document + dashboard)

### Surface archetype needs
- **Document** — daily brief, weekly review (medium strength here; most traders live in dashboards)
- **Dashboard** — positions + P&L + watchlist + market-state, updated on refresh. This is the **primary surface** for a trader. Without it, yarnnn is a tourist.
- **Operational pane** — trade signal cards, stop-loss triggers, position-sizing proposals, rebalance suggestions

Dashboard and operational pane are load-bearing. Document is secondary.

### Write primitives needed

Currently shipped (ADR-187 — Alpaca basic):
- Place basic orders (market / limit)
- Read positions + watchlist

Additional needed for alpha autonomy:
- `place_stop_loss_order` / `update_stop_loss` — tight stop management
- `place_bracket_order` — entry + target + stop in one call
- `place_trailing_stop` — dynamic stop following price
- `close_position` — with sizing (partial or full)
- `cancel_order` — mid-flight cancellation
- `rebalance_to_target` — portfolio rebalancing to target weights
- `add_watchlist` / `remove_watchlist` — mutate watchlist
- `set_risk_limit` — enforce max position size / max daily loss as pre-trade gate
- `get_account_metrics` — realtime margin, buying power, day-trade count

~9 new write primitives + 1 risk-gating logic layer. Scope for ADR-192.

**Risk-gating is critical.** Unlike e-commerce where wrong-writes are reversible, trading writes are not. Need a pre-trade gate: before any order executes, validate against `set_risk_limit` parameters. This gate is a primitive of its own, not just a wrapper.

### Autonomous decisions (ADR-193)
- "Position X hit stop-loss — close at market or wait?"
- "Thesis Y triggered on ticker Z (entry criteria met) — enter at size N?"
- "Portfolio drift >10% from target weights — rebalance?"
- "Unusual volume on watchlist instrument — flag for review?"
- "Earnings in 3 days on position X — reduce size or hold?"
- "Strategy A underperforming strategy B over 30d — shift allocation?"

### Revenue signal
- P&L (daily / MTD / YTD)
- Sharpe ratio (realized + rolling)
- Max drawdown
- Win rate per strategy
- Trades per day (discipline check)
- Alpha vs. benchmark

### Failure modes
- Wrong-sized position (over-leveraging)
- Ignored stop-loss (rides losing trade down)
- Executed stale signal (market moved since trigger)
- Misread market state (applied bull-market logic in bear context)
- Race condition on fast markets (order placed after opportunity gone)
- Incorrectly classified instrument (option vs. equity mistake)

**Error cost profile:** high, irreversible. Every wrong write costs real money and is not undoable. This is why ADR-193's approval loop is non-negotiable for trading autonomy — defaulting to always-on execution would torch the alpha.

---

## Domain 3: AI influencer (scheduled)

> **Status:** stubbed. Populate detailed rows when alpha spins up.

### Operator shape (sketch)
Creator with audience on X / Instagram / TikTok / YouTube in a specific niche. Monetizes via sponsorships, affiliates, own products, subscriptions. Runs content calendar solo or with 1 collaborator.

### Integration gap
No existing platform integration for content / social platforms. Higgsfield was mentioned as candidate for video-generation. Would need wrapper work. TBD which platforms are priority: X, IG, TikTok, YouTube each have distinct APIs.

### Rows to populate at alpha spin-up
- Identity shape
- Rich input typical (past content? audience demographics export?)
- Entities typical (content pieces, audience segments, brand deals, topics, collaborations)
- Work intent (content calendar, trend monitoring, engagement analysis, brand deal briefs)
- Deliverable shape (content calendar, trend reports, drafted posts)
- Surface archetype needs (strong dashboard need for engagement metrics + content calendar)
- Write primitives needed (post scheduling, draft management, analytics export)
- Autonomous decisions (trend alerts, engagement pivots, brand deal matching)
- Revenue signal (follower count, engagement rate, brand deal revenue, affiliate)
- Failure modes (off-brand draft, missed trend window, wrong tone for audience)

---

## Domain 4: International trader (scheduled)

> **Status:** stubbed. Populate detailed rows when alpha spins up.

### Operator shape (sketch)
Small import/export business with multi-country counterparties. Commodity or product portfolio. Compliance-heavy (tariffs, trade regulations, country-specific rules). 1–5 person operation.

### Integration gap
No existing platform integration for trade/logistics data. Candidates: shipping APIs (Flexport, Freightos), tariff/compliance databases, counterparty credit services. TBD.

### Rows to populate at alpha spin-up
- Identity shape
- Rich input typical (shipping manifests, counterparty list, historical trades, compliance docs)
- Entities typical (counterparties by country, products, shipments, tariffs, compliance requirements)
- Work intent (shipment tracking, counterparty risk review, tariff/regulation monitoring, deal briefs)
- Deliverable shape (weekly trade brief, compliance alerts, deal summaries)
- Surface archetype needs (dashboard for active shipments + counterparty scorecard; operational pane for alerts)
- Write primitives needed (TBD, likely thin compared to e-commerce / trading)
- Autonomous decisions (tariff change alerts, counterparty credit signals, shipment delays)
- Revenue signal (gross margin by route / counterparty, DSO, compliance incidents)
- Failure modes (missed tariff change, incorrect compliance flag, stale shipment data)

---

## Cross-domain pattern observations

Patterns visible once you compare the two active domains + scheduled sketches:

### 1. All four domains need all three surface archetypes

No domain is document-only. No domain is dashboard-only. Every domain has a work stream that maps to each of (doc, dashboard, operational pane), just with different weighting.

Implication for ADR-194: surface archetypes are not per-domain specializations; they're first-class product primitives that every workspace uses. The domain shapes *what data lives in each archetype*, not *which archetypes exist*.

### 2. Write-primitive depth correlates with operator risk tolerance

E-commerce writes are reversible (update a product description, archive a SKU). Trading writes are not (place an order). Influencer writes are semi-reversible (delete a post, but engagement is already counted). International-trade writes are slow-reversible (cancel a shipment, but logistics cost is real).

Implication for ADR-193: the approval loop's *strictness setting* needs to be per-domain (or per-primitive). Trading defaults to "always approve." E-commerce may default to "approve above threshold." One size doesn't fit all.

### 3. Autonomous decisions are always signal-gated, never time-gated

Every domain's autonomous decisions surface on *an observed signal in accumulated context* (competitor price drop, churn risk pattern, stop-loss hit, tariff change). No domain wants "run this action every Monday at 9am regardless of state."

Implication for ADR-195: TP's autonomous decision loop is a state-change detector over context domains, not a cron-triggered action generator. The substrate is `/workspace/context/{domain}/` entity change events, not schedule.

### 4. Revenue signal is legible in every domain

Each domain has clear revenue attribution: e-commerce = subscriptions + sales, trading = P&L, influencer = brand deals + affiliate, international trader = gross margin. ADR-184's product-health thesis holds across all four. This is part of why the ICP is polymath operator: operators who run real income-generating businesses all have legible revenue; hobbyists don't.

### 5. Day-1 rich input is always platform-connect + one document

Every domain's fast-path is: connect the primary platform (Alpaca, LS, social API, logistics) + upload one descriptive document (thesis, store description, niche definition, trade history). This is exactly what ADR-190's `UpdateContext(target="workspace")` is designed for.

Validation: the onboarding flow ADR-190 shipped serves all four domains without modification. Only the chips need to be generic enough to accommodate all (current chips pass this check).

---

## Impact table for future ADRs (template)

Every ADR from ADR-192 onward includes a table of this shape:

| Domain | Impact | Notes |
|--------|--------|-------|
| E-commerce | Helps / Neutral / Hurts | Brief explanation |
| Day trader | Helps / Neutral / Hurts | Brief explanation |
| AI influencer | Helps / Neutral / Hurts (or TBD) | Brief explanation |
| International trader | Helps / Neutral / Hurts (or TBD) | Brief explanation |

If any row is **Hurts** or if three out of four are **Neutral** with one **Helps**, the ADR is flagged for verticalization review. Either the justification is strong enough to override (explicit verticalization decision) or the design must be revised.

---

## Matrix evolution protocol

1. **Alpha accounts spin up** → add lived observations to the relevant domain's rows (especially Failure modes and Autonomous decisions — these get richer with use).
2. **New ADR proposed** → author adds the Impact table to the ADR body.
3. **Matrix reviewer** (the founder or delegated) checks for verticalization warnings.
4. **Quarterly review** — scan the matrix for domain-specific rows that have bled into the general architecture; surface any stealth-verticalization.
5. **New alpha domain added** → append as Domain 5+, follow same row structure.
6. **Retired domain** — never delete. Mark with `[ARCHIVED YYYY-MM-DD]` banner; rows stay for historical reference.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-17 | v1 — Initial matrix. 4 alpha domains: e-commerce + day trader active, AI influencer + international trader scheduled. E-commerce and day trader rows populated from ADR-183 + ADR-187 integration specs. Cross-domain pattern observations surfaced (all domains need all archetypes; write-primitive depth correlates with risk tolerance; autonomous decisions are signal-gated; revenue legibility universal; Day-1 rich input pattern universal). Matrix ratified by ADR-191. |
