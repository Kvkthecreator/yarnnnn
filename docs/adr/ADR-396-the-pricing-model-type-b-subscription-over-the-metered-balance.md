# ADR-396 — The Pricing Model: a Type-B subscription over the metered balance (one meter, two gates, no credit currency)

> **Status**: **Implemented (model + code) — 2026-07-01.** Ratifies the pricing MODEL decided across this session, and (updated) ships the code. **The numbers-deferral was consciously relaxed at implementation** (see §7): the launch-test tiers are **Free ($0) / Starter ($19) / Pro ($49)** with included allowances **$0 / $15 / $45** and retention ceilings **7 / 30 / 90 days** — set to *test in front of a first user, not to be right*, reversible against first-customer evidence. Code: `services/billing_tiers.py` (the single source of truth), migration 194 (`subscription_tier` + `allowance_usd` + `allowance_granted_at`; `get_effective_balance` draws against the allowance+balance pool), `grant_allowance()` (the monthly cycle; allowance expires, top-ups survive — replaces the legacy $20 `subscription_refill` reset), dynamic top-ups (LS `custom_price`, webhook reads the actual paid total), tier-based subscription checkout, and the FE hide-$/show-usage transparency contract. Gate `api/test_adr396_type_b_billing.py` 28/28; migration applied to prod (12/12 workspaces default free/$0 → N=1 byte-identical; RPC + banking rule verified on live data). **Still customer-gated:** whether these launch-test numbers are the *right* numbers (only a paying user resolves felt value); whether connector-count is a v1 gate. **Operator dashboard setup remaining (not code):** create the LS products (one "Top up balance" with price-override enabled; Starter/Pro subscription products) + set the variant-id env vars on API + Scheduler.
> **Date**: 2026-07-01
> **Authors**: KVK (operator) + Claude (collaborator)
> **Hat**: A (system canon — real-operator-facing)
> **Dimensional classification** (Axiom 0): **Purpose** (Axiom 3 — why the operator pays) over **Substrate** (Axiom 1 — the balance ledger it rides).

> **Discourse base**: this session's pricing arc — [`value-based-pricing-the-action-surface-matrix-2026-06-30.md`](../analysis/value-based-pricing-the-action-surface-matrix-2026-06-30.md) (the action matrix) → [`UNIT-ECONOMICS-2026-07-01.md`](../monetization/UNIT-ECONOMICS-2026-07-01.md) (real per-invocation economics) → [`METERING-CARVE-2026-07-01.md`](../monetization/METERING-CARVE-2026-07-01.md) (the meter/gate/free carve + overage/currency decision). This ADR is their ratification.

**Amends:**
- [ADR-172](ADR-172-usage-first-billing.md) (balance as single gate) — **re-scoped, not replaced.** The balance model becomes the *overage + metering substrate* beneath a subscription plan. `balance_usd`, hard-stop-at-zero, grants, top-ups, `get_effective_balance`, `subscription_refill` — all preserved and load-bearing. What changes: the subscription is no longer "optional auto-refill with no capability difference" — it becomes a **plan tier** with an included allowance + tier gates (retention, connectors). ADR-172's deleted capability gates (task counts, source/message limits) **stay deleted**; the only tier axes are the ones §2 names.
- [ADR-334](archive/ADR-334-per-operation-pricing.md) (per-operation seats) — **confirmed Rung-2 / Phase-2, superseded as the launch model.** ADR-334's delegation-tiered seats price the autonomy dial (degenerate at Rung-1 per ADR-380 D3); they are NOT the Phase-1 launch pricing. This ADR is the Phase-1 (Rung 0–1) model. Seats, if ever revived, live as a Phase-2 layer over this one.
- [ADR-391](ADR-391-budget-balance-and-the-three-layer-cost-model.md) D4/D6 — the "per-workspace subscription on commons-scale" pricing shape is **superseded by this ADR's carve.** ADR-391's cost *architecture* (balance=workspace, allocation=principal, ledger=attributed) is preserved and is the substrate this model rides. Its *pricing* decisions (which it flagged reopened) are settled here: the tier axis is not "commons-scale headcount" but the §2 meter/gate carve.

**Preserves:** [ADR-291](ADR-291-unified-cost-ledger.md) (`execution_events` = the one cost ledger; the single meter) · [ADR-327](ADR-327-budget-and-the-self-improving-loop.md) (`_budget.yaml` self-governance — orthogonal to billing) · [ADR-392](ADR-392-the-connector-lane.md) D8 (the retention gate — the built tier seam) · [ADR-391](ADR-391-budget-balance-and-the-three-layer-cost-model.md) three-layer architecture.

---

## 1. The model (decided)

**A Type-B subscription over the metered balance.** "Type-B" (vs Type-A flat-access like Netflix/Notion) = a paid plan with an **included allowance + overage** — the OpenAI/Anthropic shape. The operator subscribes to a tier; the tier includes an allowance of metered usage and sets scale gates; past the allowance they hard-stop and can top up.

**The defining experience choice: activity is transparent, dollar amounts are NOT shown to the user** — the Claude-settings pattern. The operator sees *what happened* and *how much allowance remains* (as a usage quantity), never a running dollar meter. The dollars exist in the backend (`execution_events`) for our accounting; the user reasons in *allowance*, not *cost*. This resolves the capture-first (show everything) ↔ hide-the-$ tension: **transparency of action, opacity of dollars.**

## 2. The metering carve — one meter, two gates, the rest free

A Type-B plan meters what costs *per-use*, gates what costs to *hold/scale*, and frees what costs nothing (or is the acquisition flywheel):

```
  METER  (draws the included allowance, per-use):
    • LLM judgment invocations (Freddie wakes, chat, reflection, the
      LLM round deciding a consequential act) — ~$0.08 billed/invocation,
      recorded in execution_events. THE ONLY per-use meter.

  GATE   (tier ceilings, not per-use):
    • Connector retention window   — resolve_retention_days(tier_max_days=)  [BUILT, ADR-392 D8]
    • Connector count / breadth    — candidate, demand-gated

  FREE   (no meter, no gate):
    • Substrate writes             — the write is $0; its judgment is already the D-meter
    • Perception / connector sync  — mechanical, zero-LLM, $0
    • Recall / trace reads         — the moat's distribution flywheel, free by design
    • The recall embedding COGS    — ~$0.00002/query OpenAI, absorbed by the base
```

**Headline: we meter compute, gate scale, give away the moat's usage.** This maps 1:1 onto the unit economics (the metered floor = the D-invocation; the base monetizes the asset + the gates; free reads are the flywheel).

**Consequential acts (E) are metered via the deciding LLM round, not as a separate meter** at launch. Seat-pricing the *act itself* is the deferred Phase-2 (ADR-334) question.

## 3. Overage + currency — balance IS the currency, no credit layer

Past the included allowance:
- **Hard-stop at zero**, then **top-up the same `balance_usd`** to keep going (existing machinery: top-ups $10/$25/$50). Closer to the Claude model — a hard stop, buy more usage.
- **No separate credit currency.** `balance_usd` (real dollars, 1:1 with COGS) *is* the "usage you can buy more of." A credit unit with its own exchange rate would be a **second ledger + a balance-sheet liability (unspent credits owed) + a reversal of the ADR-171/172 work-credits deletion** — and it is **not needed**: the "show usage not $" contract (§1) already hides the dollar at the *display* layer; hiding it at the *ledger* layer too is redundant complexity (`balance → COGS` does the job of `credits → $ → COGS` with one fewer layer and zero liability).
- **"Credits" as a UI word is acceptable** (a friendly label for the balance); a credit *currency* (separate unit, exchange rate, second ledger) is what we avoid. **The currency question is resolved — we do not introduce one — not merely deferred.**

## 4. The plan structure (shape decided; numbers not)

- **The plan** = a monthly `subscription_refill` into `balance_usd` (the included allowance) + the tier's scale gates (retention window; connector count if gated).
- **Tiers**: keep it minimal — a free floor + one (or few) paid tiers. **Resist ADR-100/172-era tier proliferation and feature matrices** (ADR-172's deletions stay deleted; the only tier axes are the §2 gates + allowance size).
- **The free floor** = the resting state: the substrate + Freddie + interop reads, on the $3 signup grant, no active paid allowance. Program/heavy use is the paywall moment.
- **Included-allowance display unit**: shown as a usage quantity (invocation-count or an "activity" quantity), NOT dollars (§1). The *underlying* unit is the real $ balance (§3); this is purely presentation. (Exact display form finalized at build.)

## 5. Double-charge invariant (verified, must hold)

The billing ledger is **singular**: `get_effective_balance` nets `balance_usd` against `SUM(execution_events.cost_usd)` since last refill — one ledger, one sum. The legacy `token_usage` table is dropped (ADR-291). **Every LLM call writes exactly one `execution_events` row and is charged exactly once.** Any future change that introduces a second spend ledger or a parallel debit path violates this ADR. (Verified clean 2026-07-01.)

## 6. What ships on existing machinery vs. what's new

**Already exists (no build):** `balance_usd`, `subscription_refill`, top-ups, hard-stop-at-zero, `get_effective_balance`, the single `execution_events` meter, the retention gate (`resolve_retention_days(tier_max_days=)`), `principal_id` attribution (this session).

**New build (when a number is set):**
1. A **plan-tier record** — `(workspace_id, tier, status, period)` — and the tier→(allowance, retention_max, connector_max) mapping. Lemon Squeezy product per tier (extends the existing LS integration; no new payment stack).
2. **Wire the retention gate to the tier** — pass `tier_max_days` from the plan (the seam is built; only the plumbing is new).
3. **Display balance as a usage quantity** (not dollars) — the transparency contract (§1).

That is the entire implementation surface. **No new currency, no new ledger, no money-model migration.**

## 7. The numbers — relaxed to launch-test values (2026-07-01, implementation)

The original §7 deferred the tier numbers entirely (customer-gated). **At implementation the operator consciously relaxed that deferral** — you cannot put a subscription in front of a first user with no price. The distinction the anti-speculation discipline actually protects is *test vs be-right*, not *set vs unset*: numbers set **to test** (reversible, held as hypotheses) are honest; numbers advertised **as correct** (load-bearing on a valuation or a roadmap) are the drift. The launch-test tiers are:

| Tier | Base | Included allowance | Retention ceiling | Connectors |
|------|------|--------------------|-------------------|------------|
| Free | $0 | $0 (top-up to use) | 7 days | 1 |
| Starter | $19/mo | $15 | 30 days | 3 |
| Pro | $49/mo | $45 | 90 days | unlimited |

These sit at/above the UNIT-ECONOMICS ~$15–25 base band. They are the **single source of truth** in `services/billing_tiers.py::TIER_CONFIG` — one edit re-prices checkout + the retention gate + the FE. **They are hypotheses, not claims:** the felt-value number is still the one thing analysis cannot supply — only a first paying user resolves whether $19/$49 clears. Change them freely against evidence.

**Still genuinely undecided:**
- **The exact allowance display unit** (§4) — the FE renders allowance-consumed % + run counts today; a friendlier unit (e.g. "judgment calls") is a later polish.
- **Whether connector-count is a v1 gate** — the ceiling exists in `TIER_CONFIG` but is not yet enforced at connector-add time; demand-gated.
- **Phase-2 seats** (ADR-334) — revived only against the desire-axis evidence ADR-334's amendment names.

## 8. Rejected alternatives
- **Pure usage-metering as the whole model** — the unit economics falsify it: a Light user nets ~$3 gross/mo (below a support ticket), a Heavy workspace underprices the value (pays for our tokens, not their memory). Fine as the floor; insufficient as the model.
- **Type-A flat/unlimited (Notion-style)** — loses the metered-compute cost control and the activity-legibility story; a runaway multi-principal workspace could cost more than the flat fee with no governor.
- **A credit currency** — a second ledger + balance-sheet liability + reversal of ADR-171/172; not needed once display-as-usage hides the $ (§3).
- **Per-operation seats at launch** (ADR-334) — prices the autonomy dial, degenerate at Rung-1 (ADR-380 D3); Phase-2.
- **Commons-scale headcount tiers** (ADR-391 D4/D6) — a proxy for value; the §2 meter/gate carve prices the actual cost mechanics instead.

## 9. Doc cascade
- `docs/monetization/STRATEGY.md` + `README.md` — reconciled to the implemented Type-B tiers (2026-07-01).
- `docs/monetization/IMPLEMENTATION.md` — the LS-dashboard setup checklist (products + variant-id env vars) + the code map.
- CLAUDE.md ADR index — ADR-396 entry updated (numbers set as launch-test values).
- `docs/database/ACCESS.md` — the new `workspaces` columns noted.
- The three session analysis docs (matrix / unit-economics / carve) — the derivation; unchanged.

**The model is decided and shipped. The launch-test numbers (Free/$19/$49) are set to test, not to be right — reversible against the first paying user.**

---

## 10. Amendment (2026-07-29) — the prepaid balance is legible in dollars

**Status**: Accepted (operator-ratified in discourse — the billing-pane audit).
**Amends**: §1's display posture, narrowly. §2's carve, §3's no-credit-currency
ruling, and §5's double-charge invariant are untouched.

### What went wrong

§1 ruled "activity is transparent, dollar amounts are NOT shown" and gave the
operator a substitute quantity to reason in: **allowance remaining**. That
substitute was load-bearing — the contract works because the operator reads
*something* that tells them where they stand.

ADR-490 §1③ retired the allowance layer. The substitute quantity ceased to
exist, but the hide-dollars rule stayed, and the billing pane kept rendering a
percentage. With no allowance to measure against, the FE meter fell back to
`spend / (spend + topups)` labelled **"% of balance used"** — a denominator with
no fixed meaning for a prepaid pool, because `spend` is anchored to
`allowance_granted_at` and the banking cycle re-stamps that anchor monthly. The
percentage rebases on its own.

Live receipt (workspace `d5b9029b`, tier `starter`, 2026-07-29): $36.93
effective balance, $0.156 spent since a one-day-old anchor → the pane rendered
**"0% used"** and, beneath it, a chooser asking the operator to pick between $5
and $50. The pane also told a paying `starter` workspace it was "on the free
plan" — the surviving meter branch's copy was hardcoded for free.

### The amendment

**A prepaid balance is shown as remaining dollars.** The rest of §1 stands
unchanged.

The reasoning is §1's own: dollars are permitted *at the moment of purchase*. A
prepaid balance is topped up in dollars, from a chooser denominated in dollars,
and hard-stops at a dollar boundary the operator must fund. It **is** the
purchase quantity — the same class of figure as the seat price, not the running
cost meter §1 hides. Asking someone to choose a top-up amount while refusing to
tell them what they hold is not opacity-of-dollars; it is an information gap at
the decision point, and it makes the hard-stop unpredictable.

**What stays activity-shaped** (the §1 contract, intact):
- Per-member attribution — a %-share of the pool, never per-member dollars.
- The activity trend — relative bars, no $ axis. *(Superseded by §11.)*
- The runway — days, not dollars-per-day.
- No running cost ticker anywhere; no per-invocation price surfaced.

**The one dollar figure is the balance itself** — on the Billing pane, the
Workspace Settings → Usage pane, and the UserMenu glance. All three read it
from one model (`web/lib/subscription/usage.ts::deriveBalance`), which prefers
the server's netted `balance_usd` — the same number `check_draw` enforces — so
what the operator sees is what the gate will do.

### Implementation note

The three-mode meter (`allowance` | `overage` | `balance`) is **deleted**, not
flagged off: two of its branches required `allowance > 0`, which no tier grants
post-ADR-490, and the surviving branch's copy contradicted the model it ran
under. Dead branches whose copy lies are worse than no branches (Singular
Implementation).

Also corrected in the same pass: `int(amount) * 100` in the top-up checkout
truncated fractional dollars (a $12.99 request charged $12.00) — now rounds; and
the "How it works" block offered *"Upgrade or top up to resume"* on an exhausted
balance, which is false under ADR-490 where the paid plan buys **seats only**.

## 11. Amendment (2026-08-19) — the consumption trend carries its dollars

**Status**: Accepted (operator-ratified in discourse — the usage-pane audit).
**Amends**: §10's carve-out list, narrowly. §1's ban on a *running cost ticker*
and a *per-invocation price* stands; §2, §3 and §5 are untouched.

### What went wrong

§10 kept the trend activity-shaped on §1's reasoning: dollars are permitted at
the moment of *purchase*, and a trend is consumption, not purchase. That reads
correctly and was wrong in practice for the same reason §10 itself diagnosed —
**the substitute quantity was never built.**

The chart was labelled "Activity trend" but plotted `cost_usd`. So it was
already a dollar chart; it simply refused to print the number. The operator got
the shape of their spending with the magnitude withheld — the §10 failure mode
exactly ("an information gap at the decision point"), one surface over.

Three defects follow from the same root, all verified on live data
(workspace `d5b9029b`, 2026-08-19):

1. **The window disagreed with its own header.** `by_work` and `activity` sum
   the anchor window; the trend was hardcoded to 14 days. The pane claimed
   **249 runs** and plotted **230** — 19 events dropped silently, with no label
   distinguishing the two windows.
2. **Worked days rendered as empty.** Aug 15–16 each ran 4 radar sweeps at zero
   billable draw. Plotting cost alone drew them flat, so days that did work read
   as days with none. The render gate compounded it: `trend.some(cost > 0)`
   removed the entire chart from any workspace with activity but no spend.
3. **Two denominators fused into one row.** `{runs} runs · {pct}%` put a run
   count beside a *spend* share — hence `lane` reading `175 runs · 97%` when it
   is 97% of spend but 70% of runs.

### The amendment

**The consumption trend is denominated in dollars, and each of its buckets
reports its own figure.** What §1 forbids is a *running* ticker — a live meter
that prices each invocation as it happens, turning every action into a
transaction. A retrospective, day-bucketed record of a pool the operator funds
in dollars is the same class of figure as the balance itself: it answers "where
did my money go", which is the question a prepaid pool creates and owes an
answer to.

**What stays activity-shaped** (§1, still intact):
- Per-member attribution — a %-share of the pool, never per-member dollars.
  *(A member's personal spend is a different disclosure; unchanged here.)*
- The runway — days, not dollars-per-day.
- No per-invocation price at the moment of acting; no live cost ticker on the
  working surfaces. The dollar lives in the Usage pane, after the fact.

**A bucket states its denominator.** Where a bar encodes spend share, its
caption says so, and a run count is never presented as a spend percentage.

### Implementation note

`get_usage_detail` now returns `trend[{date, cost_usd, runs, failed}]` over the
**anchor window** (`trend_days`, capped at 60), the same window `by_work` and
`activity` sum — so the header's run count and the chart's bars are arithmetically
forced to agree; both invariants are asserted against production rows. Added
`by_model` (spend by engine — the cost driver of ADR-556/559, and the one lever
a member can pull) and `activity.spend_usd`; `by_work` rows carry `pct_runs`
beside `pct`. A zero-draw day that did work renders in a muted tone and reads
"no billable draw" rather than vanishing. Display rounds sub-cent figures to
four places instead of flooring them to `$0.00` — `formatUsd` remains the shared
model for the balance, wrapped for the small figures it was not built for.
