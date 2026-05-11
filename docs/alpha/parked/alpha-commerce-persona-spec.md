---
title: alpha-commerce persona spec — PARKED
date: 2026-04-15 (original) / 2026-05-11 (parked)
status: PARKED — persona is `deferred` per SCOPE.md; content is preserved verbatim from ALPHA-1-PLAYBOOK §3B as it stood pre-archival
canonical_reference: docs/alpha/SCOPE.md (deferred-persona list); docs/programs/alpha-commerce/MANIFEST.yaml (bundle stub)
---

# alpha-commerce persona spec (parked)

> **Why this lives in `parked/`:** Per [SCOPE.md](../SCOPE.md), Alpha-1 ships **alpha-trader only**. alpha-commerce is named in the Alpha-1 charter but explicitly deferred — no Lemon Squeezy connect, no commerce-bot activation, no commerce recurrences fired during the alpha. The 430-line persona spec below was authored 2026-04-15 in the original playbook §3B as a placeholder for the eventual Alpha-2 work, but accumulated drift against ADR-260/261/262 (single `_recurrences.yaml`, no `output_kind` enum, no per-shape natural-home paths) that wasn't worth fixing while the persona is parked.
>
> **What to do with this file:**
> - **Reader looking for current alpha-trader canon:** wrong file — read [ALPHA-1-PLAYBOOK.md §3A](../ALPHA-1-PLAYBOOK.md#3a-alpha-trader--simons-inspired-systematic-retail-trader).
> - **Reader scoping Alpha-2 commerce work:** read this for *intent* (mandate, rule set, success criteria, six-check Reviewer adaptation). Treat any concrete substrate paths, `task_types` references, or `output_kind` mentions as *stale* — re-derive against current canon (ADR-261 single `_recurrences.yaml`, ADR-262 CONVENTIONS.md slug-templated topology, ADR-264 mechanical mirror executors).
> - **Reader cleaning up:** when alpha-commerce graduates from `deferred` (currently a `deferred` bundle at [docs/programs/alpha-commerce/](../../programs/alpha-commerce/)), the right move is to **rewrite** the persona-spec content directly into ALPHA-1-PLAYBOOK as a new live §3B — not unparking this file. Treat this as historical input, not canonical successor.
>
> **Authoritative sources for any current alpha-commerce reasoning:**
> - [docs/programs/alpha-commerce/MANIFEST.yaml](../../programs/alpha-commerce/MANIFEST.yaml) — bundle status `deferred`
> - [SCOPE.md](../SCOPE.md) — Alpha-1 deferred-persona policy
> - [ADR-183](../../adr/ADR-183-commerce-substrate.md) — Commerce Substrate (Lemon Squeezy provider, customers + revenue domains, original task types — note: registry-as-template-library per ADR-188 means these are starting points, not validation gates)
>
> The content below is preserved verbatim from the playbook §3B as it stood when parked. **No edits below this line.**

---

## 3B. `alpha-commerce` — Korea↔USA international commerce operator

### 3B.1 Identity (`/workspace/IDENTITY.md`)

KVK's voice. This persona is not fictional — it's an operator hypothesis about whether international product arbitrage between Seoul and LA can fund a dual-city life. Seeded into the workspace during the first YARNNN conversation as rich input.

```markdown
# Alpha Commerce — Korea↔USA dual-directional operator (KVK voice)

## Who I am
I live between Seoul and Los Angeles. I want this bilocation to be
economically self-funding, not just personally meaningful. The
operator hypothesis I'm testing is that my positional advantage —
being present in both markets, speaking both languages, reading both
cultures — is arbitrageable through carefully-declared product
sourcing and pricing rules, across both directions simultaneously.

I am not a retail generalist. I am a two-market-specialist. My edge
is not scale; it's discernment about what transfers between markets
and at what margin. I'd rather move 20 SKUs with 40% gross margin
and controlled inventory risk than 200 SKUs with 15% margin and
tied-up cash across a warehouse.

I treat commerce like Jim Simons treats trading: declared rules,
measurable per-product performance, no impulse stocking, rigorous
retirement of products that stop working. My edge decays when I
chase narrative instead of margin.

## My book (unit economics frame)
Starting capital: $10,000 operating budget (split between US and
KR inventory + shipping floats). Target: 15–30 SKUs in rotation
across both directions. Per-SKU target net margin ≥ 30% after
shipping + payment processing + FX. Target inventory turnover
≥ 6x/year per SKU (no SKU sits more than 2 months).

Two directions, tracked separately:
- KR→US: Korean products (beauty, fashion, K-snack, craft goods,
  niche lifestyle) sold to US buyers
- US→KR: US products (specialty brands, fitness/wellness niche,
  particular media + collectibles) sold to Korean buyers

## What I want YARNNN to do
- Track each declared product in rotation: inventory levels in
  source country, listing status in destination country, pricing
  vs. declared margin target, competitor reference prices.
- Surface sourcing opportunities that match my declared rules:
  Korean trend signals (Naver shopping trends, Coupang bestseller
  shifts) pointing at arbitrage-ready categories, and US equivalents
  (Reddit trend chatter, relevant subreddit spikes) for the reverse
  direction. Propose, never stock autonomously.
- Enforce my unit-economic rules religiously. If a proposal doesn't
  clear declared margin thresholds after all real costs, reject.
  "Close enough" is how margin erodes.
- Weekly unit-economic review: per-SKU margin achieved vs. target,
  turnover, return rate, direction-level aggregated performance
  (KR→US vs. US→KR). Which SKUs should be retired, which should be
  reordered, which need price adjustment.
- Currency regime awareness: track USD/KRW; flag when FX volatility
  or directional drift crosses a threshold that materially shifts
  per-SKU economics.
- Quarterly direction-level audit: is KR→US outperforming US→KR or
  vice versa? Should capital allocation shift? Are the declared
  sourcing rules decaying?

## What I don't want
- Autonomous product creation or listing. Every product that enters
  the catalog is proposed → human-reviewed → approved. Every price
  change is proposed → reviewed → approved.
- Narrative-driven sourcing ("this is trending on TikTok so let's
  stock it"). Only sourcing proposals that map to my declared rules
  plus a margin calculation.
- Over-diversification. 15–30 SKUs actively managed is the ceiling.
  Any proposal that pushes over should retire an underperformer first.
- Currency gambling. If FX is the reason a SKU is suddenly
  "profitable," that's a transient window, not an edge. Flag, don't
  chase.
- Autonomous communication with buyers. I approve every campaign,
  every refund, every bulk message to my list.

## My operator hypothesis
Bilocation + bilingual + bicultural = declared edge in cross-market
arbitrage. That edge is real only if I run it systematically. If I
run it discretionarily (chasing narrative, over-stocking favorites,
ignoring FX signals), it collapses into generic noise competing with
actual scale operators. YARNNN's job is to keep me systematic
through the friction — especially when I'm jet-lagged and tempted
to "just ship it this time."
```

### 3B.2 Operator profile (`/workspace/context/commerce/_operator_profile.md`)

Commerce analog to the trader's signals — declared rules for sourcing, pricing, stocking, and retirement.

```markdown
# Operator profile — Alpha Commerce (Korea↔USA, Option B)

## Declared strategy
Dual-directional product arbitrage between Korea (source) and USA
(market), and vice versa. Small-catalog discipline: 15–30 SKUs
actively managed. Per-SKU unit-economic targets enforced mechanically.

## Declared universe (initial categories; refined quarterly)

### KR→US direction (sourced in Korea, sold in US)
- Korean beauty / skincare (niche brands not yet distributed at scale in US)
- Korean-specific food + snacks (shelf-stable only; no cold chain for Alpha-1)
- Korean craft goods (hanji, hanbok-adjacent fashion, artisan homeware)
- Korean stationery + small lifestyle (Muji-adjacent but Korean-brand)

### US→KR direction (sourced in US, sold in Korea)
- US specialty supplements + wellness (brands with US-authenticity cachet)
- Fitness / outdoor niche products (e.g., specific climbing gear brands)
- Collectible + media (vinyl, limited-edition print, niche books)
- US-specific cosmetics (brands unavailable or heavily marked-up in KR)

## Declared sourcing + stocking rules (the equivalent of trading signals)

### Rule 1: Margin-floor stocking
- **Trigger:** product candidate has verified source-country cost + all
  landed costs (shipping, customs, FX at current spot, payment processing,
  platform fees) producing ≥30% gross margin at declared retail price
- **Volume check:** minimum demand signal in destination market
  (e.g., ≥20 searches/month for KR→US, ≥10/month for US→KR — thresholds tuned)
- **Entry:** initial order of 10–20 units; re-order only if velocity warrants
- **Retirement:** if velocity < 2 units/month for 2 consecutive months, retire

### Rule 2: Trend-confirmed sourcing
- **Trigger:** category is showing trend signal (Naver shopping top-100
  for KR sourcing; Reddit subreddit surge + Amazon bestseller movement
  for US sourcing) AND margin-floor rule is satisfied
- **Entry:** scaled initial order (20–40 units) if category signal is
  strong; normal 10–20 otherwise
- **Retirement:** trend decay (signal reversed for 2+ weeks) + any
  inventory remaining → price-reduction cycle to clear

### Rule 3: Reorder discipline
- **Trigger:** inventory on existing SKU drops below 30-day forward demand
  AND per-SKU performance is tracking to target (margin + turnover)
- **Entry:** reorder at current source cost, verify landed margin still clears
  30% floor (FX may have moved)
- **Retirement:** if FX movement has eroded landed margin below 22%
  (margin decay buffer), do not reorder; clear existing inventory

### Rule 4: Price-adjustment discipline
- **Trigger:** per-SKU turnover has dropped below 6x/year pace for 4
  consecutive weeks
- **Entry:** evaluate whether price-cut closes the gap (run unit
  economics at proposed new price; if landed margin stays ≥25%, propose
  5–10% price drop); if price-cut doesn't help, Rule 5 applies
- **Entry alternative:** if competitor reference price has moved, match
  the directional shift (up or down)

### Rule 5: Retirement discipline
- **Trigger:** either (a) Rule 4 price adjustment failed to lift
  turnover in 4 more weeks, OR (b) margin fell below 22% floor due to
  cost or FX movement, OR (c) category signal collapsed
- **Entry:** mark SKU for retirement — halt reorders, run clearance
  cycle (staged price drops over 30 days), de-list once inventory
  cleared
- **Post-retirement:** write retirement attribution to `_performance.md`
  so future sourcing decisions reference what worked vs. didn't

### Rule 6: FX regime scalar (not a sourcing rule — a global filter)
- **Purpose:** when USD/KRW has moved >5% in a 30-day window, apply a
  sourcing-pause scalar to the direction adversely affected
- **Action:** for the adversely-affected direction, do not accept new
  Rule 1 or Rule 2 proposals for 2 weeks; reorders continue if they
  still clear margin floor
- **Deactivation:** FX stabilizes (moving <2% in a 14-day window)

(Rules 7–8 reserved for Alpha-1.5 additions — candidates: shipping-
consolidation rule, multi-market-launch rule. Do not add ad-hoc.)

## Declared edge
Dual-market presence + systematic discipline. Not wholesale scale,
not brand-building, not social-media-driven. The edge is in:
- Sourcing discrimination (only products clearing margin floor)
- Turnover enforcement (no SKU sits; clearance cycles run)
- FX awareness (don't mistake FX wins for sourcing wins)
- Retirement discipline (signals that decay are retired, not rehabilitated)

## Success criteria — year-over-year
- Blended net margin (across both directions, after all costs) ≥ 22%
- Inventory turnover across active catalog ≥ 6x/year
- Zero SKUs retained past the 4-week-turnover-failure + 4-week-price-cut
  window (discipline enforced)
- Per-direction transparency: KR→US and US→KR each reported separately
- Zero products added without rule-attribution

## What I'm NOT trying to do
- Not trying to compete with Amazon aggregators on scale or price
- Not trying to build brand equity in either market (I sell; I don't
  own marketing IP for these products)
- Not trying to own warehousing — 3PL on both sides, always
- Not trying to maximize revenue; maximizing net margin × turnover
- Not trying to run ads at scale — organic + platform-native discovery only
```

### 3B.3 Risk parameters (`/workspace/context/commerce/_risk.md`)

```markdown
# Risk parameters — Alpha Commerce (Korea↔USA, Option B)

## Capital exposure limits
max_total_inventory_tied_up_usd: 5000       # 50% of $10k operating budget
max_inventory_per_sku_usd: 500              # single-SKU concentration
max_simultaneous_active_skus: 30
max_inventory_per_direction_usd: 3500       # no direction exceeds 70% of deployed capital

## Per-SKU economic limits
min_landed_gross_margin_percent: 30         # Rule 1 stocking floor
margin_decay_reorder_floor_percent: 22      # reorder halt (Rule 3 retirement trigger)
min_projected_turnover_per_year: 6          # velocity floor (Rule 4 trigger)

## Per-direction concentration
max_single_category_percent_per_direction: 40  # no category > 40% of direction's inventory

## FX exposure
fx_regime_scalar_trigger_percent: 5         # 30-day move triggers Rule 6 pause
fx_regime_scalar_deactivation_percent: 2    # 14-day stabilization deactivates
max_fx_unhedged_inventory_days: 60          # no SKU sits longer than 60 days as FX-unhedged exposure

## Discipline gates (enforced by Reviewer)
allowed_universe_only: true                 # reject proposals outside declared categories
require_rule_attribution: true              # every proposal names Rule 1–5
require_margin_calculation: true            # proposal must show landed-margin math
require_turnover_projection: true           # proposal must project 90-day turnover
require_stop_loss_plan: true                # retirement trigger declared at entry

## Communication limits
max_email_campaign_recipients: 2000
min_days_between_campaigns: 14
require_human_for_refunds_over_usd: 100
require_human_for_all_bulk_sends: true

## Signal-decay guardrails (auto-flag, not auto-halt)
flag_sku_for_review_if_turnover_pace_below: 3  # units/month (target is 6 implied)
retire_sku_recommendation_after_30_days_below_margin_floor: true
```

### 3B.4 Reviewer principles (`/workspace/review/principles.md`)

*Same file path as trader account — each workspace has its own principles.md. The structure mirrors §3A.4 but the checks operate on commerce-domain substrate.*

```markdown
# Reviewer principles — Alpha Commerce (Korea↔USA, Option B)

## Auto-approve policy
Auto-approve = NONE for Alpha-1. Every sourcing decision, every price
change, every campaign passes through human operator review. The AI
Reviewer evaluates and recommends; the human decides.

## Always-escalate-to-human
- All commerce.create_product (new SKU stocking)
- All commerce.update_product when price_cents change ≥ 10%
- All commerce.create_discount
- All commerce.refund when amount > $100
- All email.send_bulk regardless of recipient count
- All rule-definition edits (these touch _operator_profile.md, a persona-identity file)

## Capital-EV evaluation framework (commerce-adapted six-check chain)

For each proposal, the AI Reviewer executes these checks in order.
Each check produces a one-line verdict. Full chain written to
decisions.md as reviewer_reasoning.

### Check 1: Rule attribution
- Does the proposal specify which rule generated it (Rule 1–5)?
- No → reject: "no rule attribution"
- Yes → continue

### Check 2: Rule compliance
- Read the rule's conditions from _operator_profile.md
- Does the proposal satisfy every declared condition (category in
  declared universe, trigger met, minimum volumes met)?
- Any condition fails → reject with specific rule-clause citation
- All match → continue

### Check 3: Unit-economic floor
- Read _risk.md thresholds + current USD/KRW spot
- Does the proposal's landed-margin calculation clear the floor
  (30% for new stocking, 22% for reorder)?
- Verify all costs present: source cost, shipping, customs (if
  applicable), payment processing, platform fees, FX conversion
- Any cost missing or margin below floor → reject with specific gap
- All clear → continue

### Check 4: Category + direction concentration
- Does the proposal push any category > 40% of its direction's inventory?
- Does it push one direction > 70% of total deployed capital?
- Does SKU count exceed max_simultaneous_active_skus (30)?
- Any limit exceeded → reject with specific concentration math
- Clean → continue

### Check 5: Turnover projection + signal-decay check
- Read recent performance from _performance.md (by-SKU attribution
  if schema supports; by-direction and by-category aggregates
  otherwise)
- Is the proposed SKU's category currently in a decay state (recent
  30-day turnover at category level below 3/month pace)?
  - If decay → flag as defer with reason: "category decay — review needed"
  - If healthy → continue
- Is the proposed SKU's trend signal (if invoked via Rule 2) still active?
  - If trend reversed → reject: "trend signal reversed before entry"
  - If active → continue

### Check 6: FX regime
- Read USD/KRW 30-day move + current regime state
- Is the proposal's direction in active FX-regime pause (Rule 6)?
  - If yes → reject unless proposal is a reorder (Rule 3) that still
    clears margin floor
  - If no → continue
- Is current FX unfavorable (>3% adverse move in 14 days) even
  without full regime activation?
  - If yes → flag as defer with reason: "FX softening — operator verify"
  - If no → approve

### Final verdict
- All checks pass → recommend APPROVE with summary:
  "Rule N fired. Margin <X>% after costs. Category concentration <Y>%.
  FX stable. Turnover projection: <Z>/month."
- Any rejection reason → recommend REJECT with that reason
- Any defer reason → recommend DEFER with flag

## Tone
Quantitative. Specific. Every verdict references the check and the
numeric threshold. If a proposal is rejected because landed margin
is 27% (below 30% floor), the verdict says exactly that, with the
cost breakdown that produced 27%.

## Anti-override discipline
No "but this product is special" approvals. Special doesn't exist
here. Margin clears or it doesn't. Rule attribution is present or
it isn't. FX regime is active or it isn't.

## When checks conflict
If two checks pull opposite (e.g., rule compliance passes but
unit-economic floor fails), Check 3 (economic floor) takes
precedence. Operator decides edge cases.
```

### 3B.5 Task scaffolding target

| Task | Kind | Cadence | Purpose |
|---|---|---|---|
| `track-catalog` | accumulates_context | 2× daily (9am KST / 5pm PT) | Updates current inventory + listing + price state for each active SKU across both platforms. Feeds `/workspace/context/commerce/skus/{sku-slug}.md`. |
| `track-trends` | accumulates_context | Daily (8am KST) | Pulls category signals from Korea-side (Naver shopping trends, Coupang bestseller shifts) and US-side (Reddit/Amazon signals for US→KR direction). Feeds `/workspace/context/commerce/trends/`. |
| `track-fx` | accumulates_context | Daily (market open, USD side) | USD/KRW spot + 30-day move + regime state. Feeds `/workspace/context/commerce/fx.md`. |
| `rule-evaluation` | accumulates_context | Daily (9am KST, after tracking) | **Commerce analog to signal-evaluation.** For each Rule 1–5, evaluates current state across catalog + trend context + FX: which SKUs hit reorder triggers, which hit retirement triggers, which new sourcing candidates pass margin-floor math. Writes rule-state to `/workspace/context/commerce/rules/{rule-slug}.md`. |
| `daily-commerce-brief` | produces_deliverable | Daily 10am KST | Composed from rule-evaluation output. Human-readable morning brief: which rules fired, per-direction inventory status, FX regime, any SKUs flagged for retirement. Cockpit surface; email is expository pointer. |
| `sourcing-proposal` | reactive (event-triggered by rule-evaluation) | On-demand | When rule-evaluation detects a Rule 1 or Rule 2 trigger, emits ProposeAction with full rule attribution + margin math. AI Reviewer → cockpit Queue. |
| `reorder-proposal` | reactive (Rule 3 trigger) | On-demand | Inventory reorder with re-verified margin at current FX. |
| `price-adjustment-proposal` | reactive (Rule 4 trigger) | On-demand | Turnover-decay price action. |
| `retirement-proposal` | reactive (Rule 5 trigger) | On-demand | SKU retirement + clearance-cycle plan. |
| `weekly-commerce-review` | produces_deliverable | Sunday 18:00 KST | Per-SKU + per-direction + per-rule performance. Flags decay. Compares against declared baselines. |
| `quarterly-direction-audit` | goal (4-week bounded, end of quarter) | Quarterly | Reviews direction-level capital allocation (KR→US vs. US→KR), retires/retunes rules, evaluates candidates for Rules 7–8 slots. |

### 3B.6 Money-truth substrate expectations (`_performance.md` shape, commerce variant)

Commerce analog to §3A.6. Reconciler populates per-SKU + per-direction + per-rule attribution.

```markdown
---
domain: commerce
last_reconciled_at: <iso>
base_currency: USD

totals:
  reconciled_event_count: <n>
  net_revenue_cents: <n>          # revenue - refunds - returns
  aggregate_gross_margin_percent: <float>
  aggregate_inventory_tied_up_cents: <n>
  turnover_30d: <float>            # aggregate across catalog

by_direction:
  kr_to_us:
    active_skus: <n>
    net_revenue_cents_30d: <n>
    gross_margin_percent_30d: <float>
    turnover_30d: <float>
  us_to_kr:
    active_skus: <n>
    net_revenue_cents_30d: <n>
    gross_margin_percent_30d: <float>
    turnover_30d: <float>

by_rule:
  rule-1-margin-floor:
    triggered_30d: <n>
    proposals_approved: <n>
    proposals_rejected: <n>
    skus_resulting_active: <n>
    avg_realized_margin_percent: <float>
    state: "active" | "flagged" | "retirement-recommended"
  rule-2-trend-confirmed: ...
  rule-3-reorder-discipline: ...
  rule-4-price-adjustment: ...
  rule-5-retirement-discipline: ...

by_sku:
  {sku-slug}:
    direction: "kr_to_us" | "us_to_kr"
    category: <string>
    sourced_via_rule: <string>
    stocked_at: <iso>
    units_sold_lifetime: <n>
    units_sold_30d: <n>
    net_revenue_cents_lifetime: <n>
    realized_margin_percent: <float>
    turnover_pace_implied_per_year: <float>
    state: "active" | "flagged" | "price-cut-cycle" | "retirement-cycle"

fx_state:
  usd_krw_spot: <float>
  usd_krw_30d_move_percent: <float>
  regime_pause_active_direction: null | "kr_to_us" | "us_to_kr"

---

# Commerce performance

Narrative body regenerated on each reconciler run:
- Top-performing SKUs by margin × turnover (past 30 days)
- Underperformers approaching Rule 4 or 5 triggers
- Direction-level health (which direction is carrying which)
- FX regime state + any adverse moves flagged
- Rule-level: which rules are generating approvals vs. rejections
```

**Known substrate gap (same as trader):** backend reconciler may not currently support per-SKU / per-direction / per-rule attribution. This is Phase-3 verification. If the schema is gap-friendly (reconciler writes what it can, missing fields degrade gracefully), not blocking. If strict-schema failure, log as structural-gap ADR candidate.
