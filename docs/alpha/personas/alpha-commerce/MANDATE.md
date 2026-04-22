# Mandate — alpha-commerce

<!-- Canonical mandate for the alpha-commerce persona (KVK-voice, Korea↔USA
     bilocation arbitrage). Pasted verbatim via
     `UpdateContext(target="mandate")` during the first YARNNN turn, which
     writes it to `/workspace/context/_shared/MANDATE.md`. The hard gate
     in `ManageTask(action="create")` enforces that this content is
     authored (not skeleton) before any task scaffolding is allowed. -->

## Primary Action

Create and adjust commerce-platform listings (Shopify initially — see playbook §3B.0 Option B) that match one of the declared sourcing rules in `_operator_profile.md`, passing every unit-economic rule in `_risk.md` and every Reviewer check in `principles.md`, across both KR→US and US→KR directions.

## Success Criteria

- **Declared-rule sourcing only.** No listing exists without citing which sourcing rule produced it (e.g., "KR→US rule 2: K-beauty trending on Naver + adjacent to 3+ existing rotation SKUs"). "Trending on TikTok" without rule attribution is rejected.
- **Per-SKU margin discipline.** Every listing proposal carries the full cost stack: COGS + shipping + payment processing + FX + platform fees → net margin %. Target floor: **30% net margin after all real costs**. Proposals below threshold reject, regardless of narrative appeal.
- **Turnover discipline.** Target **6× annual turnover per SKU** (no SKU sits more than 2 months). Underperformers retire before new entries get approved — 15–30 SKUs active ceiling across both directions.
- **Currency-regime awareness (not currency gambling).** USD/KRW drift that materially shifts per-SKU economics triggers a flag in `_performance.md` for operator review. FX-driven margin windfalls are surfaced as transient, not as new edge.
- **Direction-level accountability.** KR→US and US→KR tracked as separate books with separate aggregate performance. Quarterly audit compares direction-level expectancy and proposes capital reallocation if one direction's margin-adjusted returns diverge.

## Boundary Conditions

- **Platform scope.** Shopify (Option B committed, playbook §3B.0). No Amazon/eBay/TikTok-Shop during Alpha-1.
- **Capital scope.** $10,000 operating budget, split between US and KR inventory + shipping floats. No expansion until phase transition.
- **Catalog scope.** 15–30 SKUs actively rotated. Both directions (KR→US and US→KR) simultaneously. Additions require corresponding retirement.
- **Category scope.** KR→US — Korean beauty, fashion, K-snack, craft goods, niche lifestyle. US→KR — specialty US brands, fitness/wellness niche, particular media + collectibles. No generic consumer electronics, no regulated goods (supplements/medical devices), no perishables.
- **Autonomy scope.** Every product creation, price change, and bulk buyer communication passes through the cockpit Queue for operator approval. Reviewer can defer/reject autonomously but cannot approve. Claude-as-operator can approve reversible changes (price adjustments within declared bands, low-stock reorder proposals for proven SKUs) within the playbook §6 discretion ladder; KVK-operator fills all non-reversible decisions (new-SKU approval, campaign launches, vendor contract changes).
- **Decision vocabulary.** Allowed: rule name, cost stack, margin %, turnover ratio, FX regime, direction-level P&L, Naver/Coupang/Reddit signal citation. Disallowed: "trending," "it's hot right now," "my friend loves this," "feels like a winner," "just ship it."

## Revision Protocol

Revised by the operator when the operator decides — no forced cadence. Material events that typically trigger a revision (documented for future-me, not enforced by the system):

- Quarterly direction-level audit showing one direction outperforming the other by ≥2× on margin-adjusted returns for two consecutive quarters.
- A SKU class decays — 3+ SKUs in the same category hit the retirement threshold within a cycle, suggesting the sourcing rule is no longer arbitrage-ready.
- FX regime break — USD/KRW moves ≥10% and stays there for a quarter, invalidating the margin assumptions built into existing sourcing rules.
- Phase transition proposal (Shopify → add Amazon; Option B → Option A; single-operator → hire a fulfillment partner).
- Discovery that the operator's actual behavior differed from the declared discipline (any observation note flagging narrative-driven stocking or FX-gambling).

Revisions are authored by KVK via `UpdateContext(target="mandate")` which overwrites the file wholesale. Prior versions live in git once ADR-208 lands; before ADR-208, operator is responsible for preserving history.
