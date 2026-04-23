# Operator Profile — alpha-commerce (declared sourcing rules)

> **Purpose**: seed content for `/workspace/context/commerce/_operator_profile.md` in the alpha-commerce workspace. Pasted verbatim via `UpdateContext(target="context", domain="commerce")` during E2E setup.
> **Framing**: KVK-voice, Korea↔USA bilocation arbitrage. 5 declared sourcing rules, bidirectional, cited on every listing proposal.

---

## Operator identity (commerce context)

Bilocational solo commerce operator running Shopify storefronts in both directions: KR→US (Korean goods into the US market) and US→KR (US goods into the Korean market). $10,000 operating budget split across directions + inventory + shipping floats. Target 15–30 active SKUs across both books, 6× annual turnover per SKU, 30% net margin floor after all real costs.

**Declared edge**: bilocation visibility into both markets' trends, language and cultural nuance on both sides, and disciplined mechanical sourcing rules + margin math. Not "I have taste"; not "I know what sells." **Declared rules + declared thresholds + retirement discipline.**

---

## Sourcing Rule 1 — KR→US: Naver trend + adjacency (K-beauty, K-snack, K-fashion)

**Trigger conditions (all must pass)**:
- Product or brand appearing in Naver's trending-products/hot-keywords for 3+ consecutive weeks
- Category overlap with 3+ existing KR→US rotation SKUs (so this SKU benefits from the store's existing traffic + Google/Meta ad account's learned audience)
- Available at wholesale from a Korean supplier the operator has transacted with previously (COGS stability)
- Regulatory clearance: no KFDA-restricted (cosmetics w/o FDA monograph), no age-gated (alcohol-adjacent), no bulky (> 2kg shipping weight adds unfavorable economics)

**Exit conditions** (retire triggers):
- SKU sits > 60 days without 1× turnover (projected 6× annual = 1× per 2 months)
- 3 consecutive monthly reviews show margin compression > 5% (e.g., FX shift, carrier rate increase, competitor undercuts)
- Naver trend faded 3+ weeks (lagging indicator; signal 1's trigger condition inverted)

**Projection basis**: historical comparable-SKU turnover in K-beauty / K-snack / K-fashion categories from `_performance.md`.

**Current typical economics**: 35–45% net margin at $30–70 ASP; 6–10× annual turnover when trend attribution is correct.

---

## Sourcing Rule 2 — KR→US: Craft + lifestyle (niche premium goods)

**Trigger conditions (all must pass)**:
- Korean craft/lifestyle brand with English-language international demand signal (Reddit /r/korea, Instagram tagging of the brand from non-Korean accounts, YouTube reviewer coverage in English)
- Higher price point ($80–200 ASP) that supports 40%+ net margin even with slower turnover
- Product has shelf stability (no perishables, no batch variation that creates SKU-mgmt overhead)
- Brand willingness to ship directly OR operator already has relationship with Korean exporter who can consolidate

**Exit conditions**:
- SKU sits > 75 days without 1× turnover (slightly longer tolerance given ASP support)
- Brand stops responding (supply chain risk concretizes)
- Demand signal decays (Reddit thread activity drops 50%+ sustained, Instagram tagging halves)

**Projection basis**: lower turnover assumption but higher margin — historical comparable in craft/lifestyle from `_performance.md`.

**Current typical economics**: 40–55% net margin at $80–200 ASP; 4–6× annual turnover.

---

## Sourcing Rule 3 — US→KR: Specialty US brands with Korean import demand

**Trigger conditions (all must pass)**:
- US brand or product mentioned in Korean blogging/vlogging ecosystem (Naver Blog, Tistory, YouTube Korean creators) 2+ times in last 30 days
- Category NOT already well-represented by licensed Korean distribution (operator wouldn't be undercutting established import channels — flag if uncertain)
- Hand-carryable or fits within standard international parcel envelope (no large/heavy)
- Dollar-denominated COGS is stable (not a speculative grey-market item)

**Exit conditions**:
- SKU sits > 60 days without 1× turnover (KR market moves faster on Instagram/Naver buzz; 6× annual expected)
- USD/KRW appreciation against baseline > 5% compresses margin below 30% — FX re-eval required
- Korean customs flags repeat items (operator has manual CI docs for each SKU; flagged SKUs get retired immediately)

**Projection basis**: historical comparable US-brand-in-KR turnover from `_performance.md`.

**Current typical economics**: 30–40% net margin at $40–100 ASP; 6–8× annual turnover.

---

## Sourcing Rule 4 — US→KR: Fitness/wellness niche

**Trigger conditions (all must pass)**:
- US fitness/wellness brand with documented Korean wellness-community interest (Korean-language review sites, Kakao group chats screenshotted in Naver blog posts)
- Supplement/wellness category eligible for Korean import (NOT KFDA-restricted; NOT requiring prescription)
- Shelf-stable (no cold-chain requirements)
- US MSRP + inbound shipping + FX gives landed Korean retail price within 1.5× of US MSRP (Korean buyers tolerate premium but revolt at 2.5×+)

**Exit conditions**:
- SKU sits > 90 days without 1× turnover (wellness buyers are more deliberate; longer tolerance)
- KFDA regulatory shift that makes the category restricted
- US brand raises wholesale price making 30% margin floor impossible at current KR retail

**Projection basis**: category comparables from `_performance.md`.

**Current typical economics**: 32–42% net margin at $50–150 ASP; 4–6× annual turnover.

---

## Sourcing Rule 5 — Bidirectional: Seasonal/event-driven

**Trigger conditions (all must pass)**:
- Culturally-specific seasonal event approaching (Chuseok, Korean New Year's Day, Seollal, Christmas-in-Korea, US Thanksgiving from KR perspective, Black Friday from US perspective)
- Product is culturally appropriate for the event AND ships from source country to destination within 4 weeks of event date
- Category has prior-year comparable in the opposing direction (if this is a KR→US Chuseok-themed product, prior US→KR Chuseok product performance applies)
- Inventory commitment is bounded — seasonal SKUs carry explicit retire-after-event date

**Exit conditions**:
- Automatic retire 2 weeks after the target event (seasonal SKUs don't linger as regular catalog items)
- If 70% of units unsold 3 days before event — operator decides between markdown-liquidation or post-event retirement

**Projection basis**: prior-year event comparable (if any). New events without comparable history route to defer automatically — turnover can't be projected.

**Current typical economics**: 35–50% net margin at seasonal-priced ASP; 1–3× event-cycle turnover (i.e., the SKU lives for one cycle and retires).

---

## Category restrictions

Hard-block categories (Reviewer rejects on Check 6 regardless of other passes):

- Generic consumer electronics (phone cases, chargers, cables) — commoditized, no edge
- Regulated medical (supplements requiring prescription, medical devices) — regulatory risk + slow approval
- Firearms, firearms-adjacent (tactical gear, ammunition) — US↔KR both have restrictions
- Perishables requiring cold chain (fresh food, certain cosmetics) — fulfillment overhead kills margin
- Liquids > 100ml (shipping weight + hazmat = margin killer)
- Alcohol, tobacco, vapes — regulatory
- Fashion counterfeits or unlicensed-brand-adjacent — brand risk + platform TOS

---

## Direction-level book separation

KR→US and US→KR run as separate P&L books with separate inventory budgets (typically 60/40 or 50/50 split depending on FX and category signal). Quarterly audit compares:

- Direction-level net margin (revenue × avg margin %)
- Direction-level turnover (cycles per quarter)
- Direction-level capital efficiency (realized margin ÷ avg capital deployed)
- Which direction warrants more budget next quarter

Cross-pollination: KR→US sellouts inform US→KR category signals (if Korean buyers love a US item's availability gap, that gap may reverse into US→KR rule 3 fit).

---

## Quarterly audit cadence

Every 90 calendar days, operator runs:

1. Per-rule turnover check against declared 6× annual target.
2. Per-SKU margin re-eval against current cost-stack reality (FX, shipping rates, platform fees).
3. Catalog ceiling enforcement: at 30 SKUs, audit cuts underperformers before new approvals resume.
4. Direction-level P&L comparison; budget split reallocation if divergence > 20%.
5. Reviewer calibration review: compare AI-occupant judgments vs retrospective human judgment from `/workspace/review/calibration.md`; adjust `modes.md` autonomy thresholds.
6. Rule refinement: if a rule produced 3+ rejects per approve, tighten the trigger conditions; if a rule produced 5+ approves per reject, widen the trigger conditions.

Audit produces: no action, retire rules / SKUs, recalibrate margin floor (if market conditions shift), or operator edits to this file + `_risk.md`.
