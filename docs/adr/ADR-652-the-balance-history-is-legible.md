# ADR-652 — The balance history is legible

**Status**: Accepted + Implemented · 2026-09-16 (operator ask: *"can you check anyway we can show the
payment historical like information on our billing workspace settings pane."*, with a screenshot of
Claude's own billing pane — its Invoices table as the reference shape).
**Amends** [ADR-396](ADR-396-the-pricing-model-type-b-subscription-over-the-metered-balance.md) §10
— the purchase-dollars carve-out extends from the balance FIGURE to the balance's HISTORY.
**Relates to** ADR-172 (`balance_transactions`, where the ledger came from), ADR-416 D1 (billing
authority), ADR-490 §1③ (the retired allowance layer), ADR-491 D2 (the member gate).
**Hat**: A. **Gate**: `api/test_adr652_balance_history.py` (script-shaped — read the count).

---

## 1. The audit — a ledger written for four months and read by nothing

The billing pane had exactly one history door: a **"Payment method & invoices"** button that bounces
to the Lemon Squeezy customer portal. That door is honest about what the processor owns (the card on
file, tax receipts) and useless to almost everyone, because `GET /subscription/portal` 404s
— *"Billing portal unavailable"* — for any workspace with no LS customer id.

Read-only probe of live prod, 2026-09-16:

| receipt | value |
|---|---|
| workspaces with an LS customer/subscription (portal reachable) | **1** |
| workspaces with neither (portal 404s) | **18** |
| workspaces holding ledger rows but **no** portal | **8** |
| `balance_transactions` rows | 24, spanning 2026-05-18 → 2026-09-07 |

Meanwhile `balance_transactions` — created by ADR-172 in May, with `created_at`, `kind`,
`amount_usd`, `lemon_order_id` and a `metadata` reason per row, and an RLS policy already scoping it
to the owner — had accumulated every credit the platform ever granted and was read by **one** thing:
the undelivered-top-up check (`_undelivered_topup`). Nothing surfaced it.

So the member could see what they hold (the balance figure, ADR-396 §10) and never where it came
from. The data was already captured; only the door was missing.

## 2. Decisions

**D1 — The history is served from our own ledger, not the processor's portal.**
`GET /api/subscription/transactions` returns the workspace's credits, newest-first, billing-authority
gated by `_resolve_billing_workspace` exactly as `/status` is (ADR-416 D1) and read through the
CALLER's client, so RLS is a second gate behind the first rather than a bypass of it. The LS portal
door **stays**: it owns the payment instrument and the tax receipts, which we do not hold. In-app
history complements it.

**D2 — Credits only, and that is the point.** The ledger holds no debits. Spend lives in
`execution_events` and stays activity-shaped per ADR-396 §1's standing ban on a running cost ticker.
Every row here IS a purchase or a grant — the same class of figure §10 already permits dollars for.
This is the amendment's whole scope: §10 ruled the prepaid *balance* is shown in dollars because it is
the purchase quantity; its *history* is the same quantity over time. §1's bans are untouched.

**D3 — The member-facing label is resolved server-side.** The raw kinds are internal accounting
vocabulary: `signup_grant` → "Welcome credit", `allowance_grant` → "Plan credit", `admin_grant` →
"Credit from yarnnn", `topup` → "Top-up". An unknown kind falls back to a neutral **"Credit"**, never
the slug — a kind added to the CHECK constraint must not turn the pane into a schema dump. One home
for the mapping so every surface says one word for a kind.

**D4 — A zero-dollar row never renders.** The ADR-490 allowance retirement wrote a `$0.0000`
`allowance_grant` to mark the layer's end. It is a true bookkeeping artifact and not an event in the
member's financial life; showing it invites *"what was that, and why did nothing happen?"*.

**D5 — One purchase delivered twice reads as one credit.** Lemon Squeezy fires
`subscription_created`, `subscription_updated` and `subscription_payment_success` for a single
purchase. On workspace `d5b9029b`, 2026-07-02, `grant_allowance` banked all three — 33 seconds
apart, same subscription `2308204`, same `$15`, same `banked_topups_usd: 44.6` — because its
idempotency guard keys on `allowance_period`, which was NULL on the first write and so matched
nothing.

**The money was never wrong**: `grant_allowance` **sets** `allowance_usd` rather than adding to it,
so the allowance stood at $15 throughout. Only the ledger has three rows. Rendering them verbatim
would have told the member they received **$45**.

Two rows of the same kind and amount within **300 seconds** collapse to one, on the READ side
deliberately. The rows are a true record of what the webhook did, and rewriting history to tidy a
display destroys the evidence. The allowance layer is retired, so no new cluster of this kind can
form — but a processor retrying a webhook is a permanent condition, and a top-up delivered twice must
never read as two purchases.

## 3. ⭐ What the drive found that reading could not

The first cut was structurally complete and collapsed **nothing** on live data.

`_parse_ledger_ts` used a bare `datetime.fromisoformat`. This API runs on **Python 3.9**, whose
implementation accepts only 3 or 6 fractional digits — and Postgres trims trailing zeros, so a real
live value like `2026-07-02T01:42:18.19472+00:00` (5 digits) raised `ValueError`. The function
returned `None` for exactly the rows the dedupe existed to compare, the comparison was skipped, and
the Jul-2 triple rendered as three $15 credits.

Every structural check passed. Only driving the real route against the real ledger printed
`entries=9` where 7 was correct. The parser now normalises the fraction to 6 digits before parsing;
check ⑦ of the gate keeps the `None` fallback honest (an unparseable timestamp forgoes the
comparison) rather than silently permissive.

**Receipt**: workspace `d5b9029b`, 10 ledger rows → **7** rendered entries (one $0 marker dropped,
the Jul-2 triple collapsed). Gate proven RED at check ① with the pre-fix parser: 3 rows instead of 1.

## 4. Implementation

| Concern | Path |
|---|---|
| Endpoint, labels, dedupe window, timestamp parser | `api/routes/subscription.py` (`get_balance_history`) |
| Served types | `web/types/index.ts` (`BalanceEntry`, `BalanceHistoryResponse`) |
| Client method | `web/lib/api/client.ts` (`subscription.getTransactions`) |
| Fetch, kept off the status path | `web/hooks/useSubscription.ts` (`history`, `historyHasMore`) |
| The History section | `web/components/subscription/SubscriptionCard.tsx` |
| Gate | `api/test_adr652_balance_history.py` — 15/15, script-shaped |

The ledger read is best-effort and independent of `/status`: a slow or failed history must never hold
up or break the plan and balance the pane exists to show. The section renders only when there is
history to show, so a new workspace sees no empty furniture.

## 5. Not done, named

- **`has_more` has no second page.** The limit is 50; the busiest live workspace holds 12 rows, so
  nothing is truncated today. The pane says "Showing the most recent N credits" rather than offering
  a pager that no live data would exercise.
- **Real paid invoices are N=1.** One workspace has ever had an LS subscription. When more do, the
  question of whether to render LS invoice lines in-app (rather than only the credits they produced)
  reopens — the portal covers it until then.
- **`admin_grant` metadata is not shown.** The reasons are internal Hat-B notes
  (*"ADR-640 eval harness drained prod pool"*); the row says "Credit from yarnnn" and its amount. If
  operator-visible reasons are ever wanted, they need member-facing wording written for the purpose.
