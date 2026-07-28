# ADR-490 — Two Free Seats + the Pay-As-You-Go Margin: the Allowance Retires

**Status**: Accepted (2026-07-28, operator-ratified in discourse — "aligned on the seats for 2 free + $20 per extra seat … aligned on 30% … following the benchmark Claude or ChatGPT's method"). Implemented same day (config + ledger + migration 224 + gates; FE/marketing coherence rides ADR-491's commit).
**Date**: 2026-07-28
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A (system canon — live billing)
**Dimension**: Purpose (Axiom 3 — what the price is for) + Substrate (Axiom 1 — one ledger, two numbers: cost-truth and billed-draw)
**Relates to**: ADR-445 (two-axis collapse — the axes stand; the boundary and the meter's rate change), ADR-396 (Type-B allowance — the allowance layer retires; the balance mechanics, hard-stop, and display posture stand), ADR-291 (one cost ledger — preserved; `cost_usd` remains provider truth), ADR-408 D4 (router cost-mirror — the reason `cost_usd` must stay unmarked), ADR-416/407 (workspace = billing unit — unchanged), ADR-429 §12.3c (the owner+1-guest boundary this restores)
**Supersedes/Amends**: amends **ADR-445 §4/§6** (free→paid boundary moves from the 2nd human to the 3rd; `included_seats: 2` everywhere; the free tier is a two-person commons). Supersedes **ADR-445's 2026-07-21 solo-checkout amendment** (the solo-$20 path retires with the allowance it bought). Retires **ADR-396's monthly-allowance layer** (Type-B → pure PAYG + seats); ADR-396's balance mechanics, hard-stop-at-zero, no-credit-currency, and hide-dollars display posture all stand. The 2026-07-06 "cost_usd = actual provider cost" ruling is preserved — margin lands in a NEW `billed_usd`, never by doctoring the rate table.

---

## 1. The decision — three moves, one model

**① Seats: two humans free per workspace; every additional human is $20/mo.**
`included_seats: 2` on every tier. The free→paid boundary is the **3rd human**.
This restores ADR-429 §12.3c's owner+1-guest boundary that ADR-445 had narrowed
to solo — and it is the more coherent boundary under the commons-first GTM
(ADR-404): the product's proof moment IS inviting someone into the commons, and
a paywall on the *first* invite taxed exactly that moment. One seat price for
now ($20); tiered seat pricing is a config-level future option (the machinery —
LS quantity, `billable_seats`, drift reconciliation — is price-agnostic).

**② Usage: pay-as-you-go at provider cost × 1.30, for every workspace.**
The meter's rate becomes `cost × USAGE_BILLING_MULTIPLIER` (1.30 — a 30%
platform margin, tunable). Rationale for the floor: payment processing alone
(LS ~5% + $0.50) consumes ~7–11% of small top-ups, so single-digit margins are
net-negative; 30% clears processing + infra with real but thin margin, and sits
far below the 100% (2x) the platform charged until 2026-07-06.

**③ The monthly allowance retires.** `monthly_allowance_usd: 0` on all tiers.
The paid subscription now means exactly one thing: **seats**. There is no
included-usage bundle to sell, so the solo-$20 plan (which bought the $15
allowance + gates) retires with it — a workspace with ≤2 humans has no
subscription and nothing to upgrade to; the upgrade moment is the 3rd-human
invite. Usage is funded by the $3 signup grant (migration 144, unchanged) +
top-ups, drawn at the billed rate, hard-stop at zero.

**Display posture (ratified)**: the benchmark Claude/ChatGPT convention, which
is ADR-396's existing contract — **dollars visible only at the moment of
purchase** (seat price, top-up amounts), **consumption shown as usage-%**,
never a running dollar meter. The 30% is an internal billing rate, not a
billboard; no surface advertises "cost + α" (that would be the OpenRouter
identity and would force dollar-transparency — deliberately not taken).

## 2. Ledger mechanics — one ledger, two numbers

The ADR-291 single ledger gains a second per-row number:

- **`cost_usd`** — unchanged: actual provider list cost (cache-inclusive).
  The 2026-07-06 ruling stands; the ADR-408 D4 router cost-mirror and margin
  analytics depend on it staying truthful.
- **`billed_usd`** (migration 224) — what the pool is debited:
  `round(cost_usd × USAGE_BILLING_MULTIPLIER, 6)`, stamped at the single write
  site (`telemetry.record_execution_event`). BYOK/override rows follow the same
  rule (override 0 → billed 0 — no margin on a customer's own key).
- **Backfill**: historical rows get `billed_usd = cost_usd` — the margin is
  never retroactive; sums are byte-identical at the flip.
- **Every pool draw reads billed**: `get_effective_balance` +
  `spend_by_principal` (RPCs, `COALESCE(billed_usd, cost_usd)`), plus the
  Python readers (`get_lifetime_spend_usd`, `get_usage_detail`,
  `budget.window_spend`, `telemetry.get_today_spend`). Member caps inherit via
  the RPC. Spend + remaining still reconcile by construction — both sides of
  the pool math use billed.
- **No-double-charge invariant preserved**: one ledger, one debit per event;
  `billed_usd` is a derived column of the same row, not a second ledger.

## 3. Allowance retirement semantics

The `grant_allowance` machinery is **kept** — it is the banking/anchor engine
(allowance expiry, top-up survival via `min(old, max(0, effective))`, the
spend-window anchor). With tier allowances at 0 it banks and re-anchors
without granting. Existing granted allowances are **grandfathered**: nothing
claws them back; the next billing cycle grants 0 and the banking rule carries
any unspent value into balance. `allowance_usd`/`allowance_granted_at` columns
stay (pool composition + anchor precedence unchanged).

**Known live consequence — resolved benign (prod receipt, 2026-07-28)**: the
one live `starter` workspace (`d5b9029b`) has **3 humans**, so under this model
its $20/mo subscription correctly bills exactly 1 seat (the 3rd human);
`sync_seat_quantity` → max(1, billable(starter, 3)) = 1 matches the live LS
quantity. Its granted $15 allowance is grandfathered (banks at next cycle).
No operator action required.

## 4. What each buyer experiences

- **1–2 humans**: free workspace, full product, $3 signup grant, then top-up
  PAYG. No subscription exists to buy.
- **3+ humans**: $20/mo per human beyond the first two (LS quantity =
  humans − 2, floored at 1 at checkout — the seat being purchased). Usage stays
  pooled PAYG, owner-funded, per-principal attributed + cappable.
- **AI principals**: free to add, always; their usage draws the pool (billed).

## 5. Reversibility

All three numbers are launch-test values in one place
(`billing_tiers.py`): `included_seats: 2`, `additional_seat_usd: 20.0`,
`USAGE_BILLING_MULTIPLIER: 1.30`. The multiplier applies at write-time only, so
tuning it never rewrites history. Restoring an allowance tier is a config
value + the dormant machinery waking up.

## 6. Gates

`api/test_adr490_payg_margin.py` (behavioural, `python3` check()-style):
multiplier stamped at the write site; backfill parity (billed == cost on
pre-migration rows); RPC coalesce shape; boundary math (2 humans free, 3rd
billable); invite-gate copy names two people; allowance config zeroed.
Sibling ADR-445 gates updated where they asserted the superseded boundary,
solo-checkout copy, and price strings.
