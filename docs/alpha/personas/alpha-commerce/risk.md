# Risk Rules — alpha-commerce (portfolio-level floors)

> **Purpose**: seed content for `/workspace/context/commerce/_risk.md` in the alpha-commerce workspace. Pasted verbatim via `UpdateContext(target="context", domain="commerce")` during E2E setup.
> **Framing**: hard floors the Reviewer enforces on every listing / pricing / reorder proposal. These are NOT guidelines — the Reviewer rejects any proposal that would breach any limit when combined with current catalog state.

---

## Account state

- **Operating budget**: $10,000 total (across both directions + inventory floats + ads)
- **Platform**: Shopify (Option B per ALPHA-1-PLAYBOOK §3B.0; no multi-channel during Alpha-1)
- **Markets**: KR→US and US→KR, bidirectional
- **Target catalog**: 15–30 active SKUs

---

## Portfolio-level limits (hard floors)

### Inventory + capital

- **Total inventory deployed**: ≤ 70% of operating budget ($7,000). Remaining $3,000 reserved for: ad spend float, shipping float, unexpected vendor commitments, emergency capital buffer.
- **Per-direction capital cap**: $4,000 inventory per direction (80/20 split across $10K-$7K inventory = $4K + $3K, reserve $1K uncommitted between directions). Reviewer rejects a new KR→US listing if cumulative KR→US inventory at proposed commitment > $4,000.
- **Single-SKU ceiling**: 15% of direction-level budget ($600 per SKU). Reviewer rejects a reorder or bulk commitment above ceiling.
- **New-SKU initial order cap**: 10% of direction-level budget ($400) for a first-time-this-SKU order. Reorder can exceed if turnover history justifies, up to the single-SKU ceiling.

### Catalog size limits

- **Hard cap**: 30 active SKUs across both directions. Reviewer rejects new-SKU creation proposals when count = 30 unless the proposal explicitly names a retiring SKU. One-in-one-out when at cap.
- **Per-direction cap**: 18 SKUs per direction. Reviewer enforces per-direction count.
- **Per-rule cap**: no single sourcing rule holds > 40% of direction-level SKU count. Forces rule diversification within each direction.

### Margin floor (hard reject below)

- **Absolute floor**: 30% net margin after all real costs (per `reviewer-principles.md` Check 3).
- **Margin-marginal band**: 30–35% routes through capital-EV justification (turnover compensation).
- **Target band**: 35–45% (where most approved SKUs should land).
- **Suspicion band**: > 55% margin proposals flag for operator review — either the cost stack is incomplete (common error) OR it's a genuine arbitrage worth preserving (rare).

### Turnover floor

- **Hard reject below**: projected annual turnover < 4× (SKU sits > 3 months on average — ties capital, risks obsolescence in trend-driven categories).
- **Target**: 6× annual (2-month average time-on-shelf).
- **Fast mover band**: 8–12× (typical for event-driven or trend-driven K-beauty SKUs).

---

## Per-rule risk limits

Complements (doesn't replace) per-rule sourcing conditions in `_operator_profile.md`:

### Rule 1 (KR→US Naver trend + adjacency)

- Max cumulative inventory: $1,600 (40% of KR→US direction budget, allows ~4–8 active SKUs at typical $200–400 order size)
- Max concurrent SKUs: 8

### Rule 2 (KR→US Craft + lifestyle)

- Max cumulative inventory: $1,200 (higher ASP = more capital per SKU)
- Max concurrent SKUs: 5

### Rule 3 (US→KR Specialty US brands)

- Max cumulative inventory: $1,600
- Max concurrent SKUs: 8

### Rule 4 (US→KR Fitness/wellness)

- Max cumulative inventory: $1,200
- Max concurrent SKUs: 5

### Rule 5 (Bidirectional seasonal)

- Max cumulative inventory: $800 (seasonal is bounded by event dates)
- Max concurrent SKUs: 5 (3 in the hot direction, 2 in the opposing)
- **Hard retire-after-event date** applied per SKU at creation time — Reviewer enforces on the event date's task cycle.

---

## Price adjustment authorization

Reviewer may (via AI occupant when `modes.md` permits) auto-approve price changes within:

- **Adjustment band**: ±15% from the SKU's baseline list price (set at creation, updated only at quarterly audit)
- **Direction**: both increases and decreases
- **Frequency**: no more than 1 adjustment per SKU per 2 weeks (prevents price-dance / algorithmic thrash)
- **Never auto-approve**: price adjustments that would push margin below the 30% floor, even if within the 15% band. These always defer to human occupant.

---

## Reorder authorization

Reviewer may (via AI occupant when `modes.md` permits) auto-approve:

- Low-stock reorders on proven SKUs (SKU has ≥ 3 months of consistent sell-through, current inventory ≤ 7 days projected demand)
- Reorder size = projected 30-day demand based on trailing 90-day sell rate
- Reorder cost ≤ 10% of direction-level budget ($400)

Always defer to human occupant:

- Reorders on SKUs without 3-month consistent history
- Reorder sizes > $400
- Reorders that would push direction-level inventory above 90% of per-direction cap

---

## Customer-facing action restrictions

Never-auto-approve (always route to human occupant regardless of `modes.md`):

- `create_product` — new-SKU creation
- `update_product_category` — category reclassification
- `cancel_customer_order` — customer impact, requires operator judgment + message
- `refund_over_100` — refunds ≤ $100 can be auto-approved via modes; over $100 always human
- `issue_store_credit` — same logic as refunds
- `bulk_email` / `sms_campaign` — buyer communication, operator authors
- `vendor_contract_change` — supplier relationships always human
- `promotional_discount_over_25_percent` — deeper discounts always human
- `category_expansion` — adding a category outside current catalog always human

---

## FX regime triggers

USD/KRW drift is tracked at every reconciliation cycle:

- **Baseline**: USD/KRW rate at the operator's last quarterly audit. Operator sets. Example: 1 USD = 1350 KRW as of 2026-04-01.
- **±3% drift**: flag in `_performance.md` — operator aware, no auto-action.
- **±5% drift**: Reviewer recalculates margin math on all SKUs using current rate. Any SKU that drops below 30% margin due to FX alone → flagged as pending-retire or pending-price-adjust at next operator review.
- **±10% drift**: mandatory operator review of every direction's capital allocation. FX is driving, not incidental.

---

## Circuit breakers

These trigger notifications but not auto-action — operator decides:

- **Three consecutive rejections by a single sourcing rule**: notify. Rule may be miscalibrated for current market state.
- **A SKU sits 45 days with zero sell-through**: notify. Early retire-flag trigger.
- **Direction-level monthly margin drops 20%+ below trailing-3-month average**: notify. Direction-level recalibration may be needed.
- **Single SKU exceeds 30% of direction-level revenue**: notify. Concentration risk — if that SKU fails, direction suffers disproportionately.

---

## High-impact threshold

```yaml
commerce:
  high_impact_threshold_cents: 100000   # realized margin impact ≥ $1,000 per SKU routes to task feedback.md
```

Examples:
- A K-beauty SKU that sold 50 units at $35 with 40% margin = $700 margin — no feedback routing (under threshold)
- A K-fashion SKU that sold 100 units at $55 with 38% margin = $2,090 margin → feedback on the originating task (which rule 1 SKU fits this well? Why? Category lesson)
- A US→KR wellness SKU that sat 120 days and retired at liquidation = -$350 loss — under threshold
- A bidirectional seasonal Chuseok SKU with unsold $1,500 inventory at event-end → feedback on seasonal rule 5 calibration

---

## Audit trail

- Every Reviewer decision → `/workspace/review/decisions.md` (proposal ID, rule attribution, cost-stack math, verdict, reasoning, occupant)
- Every reconciled outcome → `/workspace/context/commerce/revenue/_performance.md` (aggregate) + `/workspace/context/commerce/customers/{slug}/` (per-customer where material)
- Cross-reference → `/workspace/review/calibration.md` (per-occupant × verdict × outcome rolling windows)

---

## Revision protocol

Revised by the operator at quarterly audit OR under material events (FX regime shift > 10%, direction-level budget reallocation, new category addition, platform TOS change). Revisions via `UpdateContext(target="context", domain="commerce")` overwriting this file. Prior revisions persist in Authored Substrate revision chain.

Reviewer reads this file at every verdict rendering. Changes take effect on the next proposal.
