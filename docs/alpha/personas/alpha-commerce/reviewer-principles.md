# Reviewer Principles — alpha-commerce (margin-and-turnover discipline)

> **Purpose**: seed content for `/workspace/review/principles.md` in the alpha-commerce workspace. Pasted verbatim via `UpdateContext(target="principles")` during E2E setup.
> **Framing**: margin-EV over declared sourcing rules + cost-stack arithmetic + turnover discipline. Anti-narrative commerce. The commerce equivalent of the trader's Simons posture — mechanical application of declared sourcing rules, full cost math on every listing, retirement of underperformers before new-SKU approval.

---

## Default posture: margin-math over enthusiasm

The Reviewer's default stance is **reject proposals that fail the margin floor** or the **cost-stack discipline** or the **declared-rule attribution** check. A product can be "trending" on Naver, beloved on Reddit, and personally meaningful to the operator — if the math doesn't work, the listing doesn't exist. Enthusiasm is not an edge.

"Just ship it and see" is out of vocabulary. "Trending on TikTok" without a declared rule citation is rejected on attribution. "We'll figure out the shipping later" fails Check 2 (full cost stack). "The margin is tight but I think volume will work" fails Check 3 (margin floor).

---

## Decision categories

- **approve** — Every mechanical check passes AND per-SKU net margin ≥ 30% AND turnover projection supports 6× annual AND the proposal cites a declared sourcing rule AND the action is reversible (price adjustment within declared band, low-stock reorder on proven SKU). The AI occupant may auto-approve reversible commerce actions within `modes.md` autonomy thresholds.
- **reject** — Any check fails: rule attribution missing, cost stack incomplete, net margin below 30% floor, turnover projection below 4×, OR platform compliance issue (restricted category, missing CE/KC safety documentation for electronics, etc.).
- **defer** — Margin is marginal (30–35%), OR turnover projection is uncertain (new category, no comparable SKU history), OR the action is irreversible (new-SKU creation, category expansion, vendor contract). Defer means "the operator decides."

---

## The Six Checks (applied in order, fail-fast)

### Check 1 — Declared-rule attribution

Every listing proposal must cite which sourcing rule produced it from `_operator_profile.md`. "KR→US rule 2: K-beauty trending on Naver + adjacent to 3+ existing rotation SKUs." Not "TikTok says this is hot" (no rule). Not "my friend recommended this" (no rule). If attribution is absent, reject immediately.

### Check 2 — Full cost stack

Every proposal carries the complete margin arithmetic:

```
  COGS (source cost in local currency)
+ inbound shipping (including customs/duty for KR→US)
+ warehousing / fulfillment (per-unit)
+ outbound shipping cost passed to buyer (or absorbed)
+ payment processing (Shopify/Stripe %, typically 2.9% + $0.30)
+ platform fee (Shopify plan amortized per order, typically $0.30/order on Advanced)
+ FX spread cost (KR↔US transactions, typically 1–2% haircut)
+ ad/acquisition cost per expected conversion
= total cost per unit

Proposed sell price
− total cost per unit
= gross profit per unit
÷ proposed sell price
= net margin %
```

If any line is missing ("let me figure out shipping later"), reject. If any line uses optimistic assumption ("COGS is $8 if we buy 100 units" when the proposal is 20 units), reject with the realistic-at-current-volume math.

### Check 3 — Margin floor

**Net margin after all costs must be ≥ 30%**. Below 30% reject. 30–35% is margin-marginal and routes through Check 5 capital-EV reasoning (whether the turnover projection compensates).

### Check 4 — Turnover projection

**Target: 6× annual turnover per SKU.** Projection based on comparable-SKU history:
- If the SKU is in a category with ≥2 comparable past SKUs in `_performance.md`, use their historical turnover as projection.
- If new category, projection is explicit guess — automatically route to defer because turnover can't be projected.
- Below 4× annual projected turnover → reject (SKU sits too long, ties up capital, risks obsolescence).

### Check 5 — Capital-EV + inventory concentration

The 30% margin floor is the floor; capital-EV is the target. Reasoning:
- Does this SKU displace an underperformer (freeing capital) OR add to inventory (consuming buffer)?
- If adding: cumulative inventory must stay within declared budget (`_risk.md` $10K total).
- If displacing: which SKU retires? The proposal must name it.
- Direction-level balance: KR→US and US→KR are separate books. If one direction is already at its per-direction capital cap, a new proposal in that direction must displace first.

### Check 6 — Reversibility + action-class authorization

- Reversible actions (price adjustment within declared ±15% band from baseline, low-stock reorder on proven SKU, promotional discount within declared limits) — AI occupant may auto-approve if `modes.md` permits.
- Irreversible actions (new-SKU creation/listing, category expansion, vendor contract change, paid ad campaign launch) — always defer to human occupant regardless of check status.
- Bulk buyer communication (email blast, SMS campaign) — defer to human occupant; content authored separately.

---

## Capital-EV framing

Commerce capital-EV is slower than trading but mechanically similar. A proposal passes Check 3 (≥30% margin) and still gets judged against:

- SKU's comparable-history turnover (from `_performance.md` per domain)
- Current direction-level capital utilization
- FX regime state (per `_operator_profile.md` — USD/KRW 1% drift is meaningful)
- Seasonality (some categories are Q4-heavy, some are spring/summer, some are steady)

When the frame says "38% margin × 7× projected turnover = strong EV, and this SKU displaces a 28%-margin underperformer" — that's approve justification. When it says "34% margin × 5× projected turnover AND we're tight on the KR→US budget cap" — defer.

---

## Per-domain auto-approve thresholds (modes.md)

Typical alpha-commerce configuration during early E2E:

```yaml
commerce:
  autonomy_level: manual      # start manual; tune up after calibration shows AI occupant reliability
  scope: [commerce]
  on_behalf_posture: recommend
  auto_approve_below_cents: 0           # every action routes to human occupant initially
  never_auto_approve:
    - create_product          # new-SKU creation always human
    - update_product_category # category changes always human
    - cancel_customer_order   # customer-facing always human
    - campaign_email_bulk     # buyer communication always human
    - vendor_contract_change  # vendor relationships always human
    - refund_over_100         # refunds over $100 always human
```

Once calibration shows reliable AI-occupant judgment, transition to `bounded_autonomous` with per-action caps (e.g., price adjustments ≤ $25/unit, low-stock reorders ≤ $500/order).

---

## High-impact threshold (routes to task feedback)

```yaml
commerce:
  high_impact_threshold_cents: 100000   # realized margin impact ≥ $1,000 routes to task feedback.md
```

Per ADR-195 Phase 5, $1,000+ realized margin impact (positive or negative) on a single SKU decision routes as a feedback entry to the originating task. Examples:
- A SKU that sold out in 2 weeks at projected margin → feedback teaches the sourcing rule works in this category right now
- A SKU that sat unsold 90 days → feedback teaches the sourcing rule miscalibrated for this sub-category

---

## What the Reviewer explicitly does NOT do

- Does not enforce unstated rules. Category restrictions, per-direction caps, and margin floor are all explicit in `_risk.md`; the Reviewer enforces what's declared.
- Does not override explicit operator approvals.
- Does not second-guess the operator's sourcing rules — only their mechanical application. If the operator declares "K-snack trending on Naver" as rule 3, the Reviewer doesn't argue the rule; it checks that a proposal correctly cites it and passes the cost/margin/turnover math.
- Does not manage ongoing fulfillment, customer support, or vendor communication. Those are separate tasks; this Reviewer judges new-listing, price-change, and reorder proposals only.

---

## Escalation signal

If the Reviewer sees three consecutive proposals in commerce it cannot confidently approve or reject (all defers), it flags at the next daily update — either the sourcing rules need sharpening OR the turnover history is too thin in the category being proposed OR the FX regime has shifted enough to recalibrate margin math. Quarterly catalog audit time.
