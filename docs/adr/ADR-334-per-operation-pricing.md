# ADR-334 — Per-Operation Pricing: Delegation-Tiered Seats over the Cost Ledger

**Status:** **Deferred (hypothesis, evidence-gated)** — demoted 2026-06-19 from "Ratified (direction)". The seat model below is **parked as one candidate, not committed canon.** The **sole active pricing model is the ADR-172/291 balance gate** (pay-as-you-go: $3 signup grant, top-ups, hard stop at zero, no tiers, no seats). Seats unblock only against the evidence named in the Amendment below. No code shipped on this ADR; nothing is mischarging (the `/pricing` page never wired seat checkout — `cta.ts::seatCheckout` is `null`).
> **Rung mapping (2026-07-01)**: this ADR prices the **autonomy/delegation dial** — a **Rung-2 (Phase-2)** axis per the [activation ladder](ADR-380-the-activation-ladder-and-the-judgment-deferral-line.md) (the dial is *degenerate at Rung-1* — Freddie has no consequential external write, so an autonomy tier over Freddie prices nothing). It is therefore **NOT the Phase-1 launch pricing model.** The Phase-1 (Rung 0–1) pricing thesis is the substrate-base model consolidated in [`docs/monetization/PRICING-CONSOLIDATION-2026-07-01.md`](../monetization/PRICING-CONSOLIDATION-2026-07-01.md) — where these seats live as the deferred **③ Operation** layer. See also [`phase-1-packaging-open-scoping-rung-2-pricing-2026-06-29.md`](../analysis/phase-1-packaging-open-scoping-rung-2-pricing-2026-06-29.md).
**Date:** 2026-06-10 (ratified-direction) · 2026-06-19 (demoted to deferred)
**Deciders:** KVK (operator) + Claude (collaborator)
**Hat:** A (system canon)

> **Discourse base:** [`cumulative-workspace-product-formulation-2026-06-10.md`](../analysis/cumulative-workspace-product-formulation-2026-06-10.md) §5 (the pricing direction this ADR sprang from) + GTM_POSITIONING v4 §5 (high-ACV expansion-led motion). Grounded against the live monetization stack: `docs/monetization/STRATEGY.md` (ADR-172/291 balance model — **now the sole active model**), `COST-MODEL.md` (per-task economics), the LS product inventory.
> **Demotion discourse:** [`os-as-product-vs-capability-and-the-validatable-autonomy-spectrum-2026-06-19.md`](../analysis/os-as-product-vs-capability-and-the-validatable-autonomy-spectrum-2026-06-19.md) §11 — the second scissor (value vs willingness-to-be-absent) and the founder-non-reliance receipt.

---

## Amendment 2026-06-19 — Demoted to deferred hypothesis (pay-as-you-go is the sole active model)

**What changed.** This ADR was "Ratified (direction)" on 2026-06-10. As of 2026-06-19 it is **Deferred (hypothesis)**. The per-operation seat model ($149/$299/$499, tiered by the AUTONOMY dial) is **not** the committed pricing model. The full §1–§9 analysis below is **preserved as the parked candidate** — it is good thinking worth keeping on record — but it does not bind product, copy, or roadmap.

**The sole active pricing model is pay-as-you-go (ADR-172 + ADR-291), unchanged and unre-scoped:**
- `balance_usd` is the single gate. $3 signup grant · top-ups ($10/$25/$50) · 2× cache-inclusive Anthropic rates via the `execution_events` ledger · **hard stop at zero**.
- **No seats, no tiers, no feature gates, no subscription commitment.** (Pro $19/mo, which this ADR proposed to retire, is *also* effectively dormant — there is no live subscriber base to migrate; the balance model stands alone.)
- The free workspace IS the resting state. Programs run on the same balance — usage simply draws it down. This is the model already in production.

**Why demote (the evidence, not a preference).** The seat model's entire logic is *"price the autonomy dial — pay more as you trust more."* Three live conditions make committing that axis premature:

1. **Zero external users.** Every assumption in §1–§9 (WTP, expansion motion, ~90–97% margin, trial calibration) is *theory narrated*. Committing an opinionated paid model in canon ahead of a single paying user is speculation, not decision — and the repo's own discipline (ADR-334 §5 "anti-speculation") cuts against it.
2. **The desire axis is unvalidated, and may be the wrong axis.** The 2026-06-19 discourse (§11) surfaces a *second scissor*: **value and willingness-to-be-absent are anti-correlated.** The Autonomous tier — this ADR's top price — is exactly the judgment a principal *least* wants to delegate, because it's consequential and it's the thing they're paid for. Every eval to date validates that the seat *can* judge (capability); none validates that a principal *wants to be absent* from the judgment (desire). Pricing the autonomy dial bets the business on the unvalidated axis.
3. **Founder non-reliance.** The loudest receipt: as of 2026-06-19 nobody — including the operator — is absent from a consequential judgment because of this system. The alpha-trader loop produced 16 organic wakes → 0 acted-on proposals → 1-ever-trade (an off-hours fixture); the "clean" author domain validated at rung-1 *advisory*, i.e. judgment assistance, not judgment autonomy. When the most-motivated user alive won't yet lean on the strong form, pricing the strong form at a premium is ahead of the evidence.

**Unblock conditions (what would re-promote this ADR, or supersede it).** Re-open the seat question only when there is evidence on the *desire* axis, not just the capability axis:
- **N ≥ a few real external users** running operations on real (non-dogfood) substrate, AND
- a passed **forcing test** from the 2026-06-19 discourse §12 — minimally the *absence test* (the intended buyer can write the literal list of decisions they actively want to NOT be in the room for) and the *founder-reliance test* (one consequential call the operator lets stand without checking), AND
- a willingness-to-pay signal that the priced axis (delegation level) is the axis buyers actually value — not assumed from the architecture.

If those land, this ADR is re-promoted (possibly with a different axis — e.g. usage-tier or value-share rather than autonomy-tier). If they fail, a successor ADR formalizes pay-as-you-go (and/or a simple usage tier) as the permanent model and supersedes this one. **Until then: do not advertise, wire, or roadmap seats.** The `/pricing` page, FAQ, homepage, and `llms.txt` reflect pay-as-you-go (the demotion landed those surfaces in the same change).

**What this amendment does NOT do.** It does not delete the seat analysis (§1–§9 stand as the parked candidate). It does not touch the billing substrate (ADR-172/291 were always the live floor; they are now simply the whole model). It does not re-introduce any of ADR-172's deleted gates (capability tiers, source limits, message counts stay deleted). It does not retire the *value thesis* underneath seats — "value-priced judgment over commodity compute" remains the long-run aspiration; this only declines to *price* it before the desire evidence exists.

---

### Original ratified-direction content (2026-06-10) — preserved as the parked candidate

> Everything below §1 is the 2026-06-10 ratified-direction text, **retained verbatim** for the record. Read it as *the hypothesis*, not as active canon. The Amendment above governs.

**Amends:**
- [ADR-172](ADR-172-usage-first-billing.md) (balance as single gate) — **re-scoped, not replaced**: the balance model becomes the Layer-1 tier AND the usage layer beneath every seat. Hard-stop-at-zero, grants, top-ups, `get_effective_balance` — all preserved.
- [ADR-291](ADR-291-unified-cost-ledger.md) — unchanged as substrate; the 2× cache-inclusive ledger is the **transparency + floor layer**, no longer the price.
- ADR-249/307 (autonomy gate) — gains one read: the settable AUTONOMY ceiling is plan-entitled (§4).

**Supersedes:** Pro $19/mo (subscription-as-refill) as the paid offer. The v3.0-era "$19/mo full palette" external copy was already retired by GTM v4; this retires its billing substrate.

**Preserves:** ADR-327 budget substrate (`_budget.yaml` — plan seeds its defaults) · Lemon Squeezy as merchant of record · top-up products · the signup grant machinery · Direction A (the free tier IS the resting state).

---

## 1. The principle

**The unit of value is the operation; the axis of price is trust.** An *operation* = an activated program on a workspace (ADR-332: a program is a flow-declaration set; activation is when the four flows go live). The operator pays per running operation, tiered by **how much delegation the operation is entitled to run** — the AUTONOMY dial they already control becomes the pricing axis: pay more as you trust more. Compute is metered honestly underneath (ADR-291 ledger) but is the floor, not the price: the product's value is the call made correctly and the asset that compounds, not tokens.

## 2. The tiers (ratified)

| Tier | Price / operation / month | Entitlement (settable AUTONOMY ceiling) | Included usage (monthly refill) |
|---|---|---|---|
| **Supervised** | **$149** | `manual` only — every consequence operator-approved | $15 |
| **Delegated** | **$299** | + `bounded` — acts within declared ceilings | $30 |
| **Autonomous** | **$499** | + `autonomous` — acts within the declared framework | $60 |

- **Annual = 10×** (two months free), per tier.
- **Entitlement enforcement is one read at the existing gate**: the ADR-307 uniform permission gate (and the AUTONOMY-write path) consults the operation's plan tier; AUTONOMY values above the entitled ceiling are not settable. No parallel permission system — the tier gates the *dial*, the dial gates the *actions*, exactly as today.
- **Included usage** ships as the existing `subscription_refill` balance kind, sized per tier (reset, not accumulate — unchanged semantics). Overage = existing top-ups ($10/$25/$50). `_budget.yaml` defaults are seeded from the tier at activation (ADR-327's substrate is the enforcement; this ADR only sets its defaults). Hard stop at zero preserved.

**Unit economics (grounded in COST-MODEL.md):** an active operation bills single-digit-to-low-tens of $/month in ledger usage → ~90–97% gross margin at seat prices. The margin is the point: value-priced judgment over commodity-priced compute. Hundreds of operations at these prices is a real business (GTM v4 motion).

## 3. The free tier (ratified): Layer-1 = the existing model, re-scoped

**The bare workspace is free, forever** — substrate, uploads, Files, MCP interop, chat — running on the **unchanged ADR-172 machinery**: $3 signup grant, balance gate, top-ups for continued Layer-1 usage. **No active program on free.** This is Direction A rendered as pricing: the free tier IS the resting state, the Layer-1 portable-context floor, and the interop trojan. Program activation is the paywall moment — which is also exactly where ADR-331's `/setup` sequence already stands.

Zero new build: the current billing model doesn't get deleted; it gets a narrower job.

## 4. Trial (ratified shape)

**14 days · one operation · any tier · no card.** A `trial_grant` ($10) through the existing grant machinery covers trial usage; `_budget.yaml` seeded at the trial tier's defaults. The activation contract this imposes on product: the **retrospective audit** (ADR-330 retrospective intake + ADR-331 harvest) must land its wince inside the window — the trial's job is a felt calibration trail, not a feature tour. Trial ends → seat subscription or the operation deactivates (workspace and substrate remain — free tier; nothing is deleted, per the sovereignty posture).

## 5. Expansion + multi-operation

Flat per-operation pricing in v1 — the second operation on a workspace is the *expansion motion*, full price. Bundling/discounts deferred until evidence (anti-speculation discipline). Seat tier is per-operation, not per-workspace: a trader operation may run Autonomous while an author operation runs Supervised on the same workspace.

## 6. Lemon Squeezy mapping

Three new subscription products (×2 for annual): `SEAT_SUPERVISED_{M,Y}`, `SEAT_DELEGATED_{M,Y}`, `SEAT_AUTONOMOUS_{M,Y}` — subscription metadata carries `(workspace_id, program_slug)`. Top-up products unchanged. Pro Monthly/Yearly variants retired (no live subscriber migration burden at alpha stage; any existing subscriber migrated by hand with a grant). Webhook handler extends the existing LS integration — no new payment stack.

## 7. Anti-goals (binding)

- **No feature-matrix tiers.** The ONLY thing tiers gate is the AUTONOMY ceiling (+ included usage). No capability gates, no source limits, no message counts — ADR-172's deletions stay deleted.
- **No work-credits revival** (UNIFIED-CREDITS stays archived).
- **No per-user seat pricing** — the operator is one principal; the unit is the operation.
- **No compute-anchored pricing** — the ledger is floor + transparency. Repricing the seats against token costs would re-commit v3.0's category error.

## 8. Implementation phases (PARKED — do not start; gated behind the Amendment's unblock conditions)

> **Status note (2026-06-19):** none of these phases are active build-lane work. They are the implementation sketch *if* the seat hypothesis is re-promoted. The CHECKOUT GUARD they reference (`cta.ts::seatCheckout = null`) stays in place; P4's `/pricing` rewrite already happened in reverse (the demotion swung the page to pay-as-you-go). Do not begin P1–P5 until the unblock conditions in the Amendment are met.

1. **P1 — entitlement substrate**: operation-seat record (thin DB: `(workspace, program_slug, tier, status, trial_ends_at)`), activation check in `/setup` + program-activate path, AUTONOMY-ceiling read at the gate/write-path.
2. **P2 — LS products + webhooks**: six variants, metadata mapping, subscription lifecycle → seat status.
3. **P3 — tier plumbing**: `subscription_refill` sizing per tier; `_budget.yaml` seeding at activation; trial grant kind.
4. **P4 — `/pricing` page**: lands inside the marketing-refactor copy spec (this ADR is its content).
5. **P5 — `docs/monetization/STRATEGY.md` rewrite** to this model (banner added now; full rewrite when P1–P3 land).

Gates per repo norms; render-parity check at P1/P3 (scheduler reads budget; API reads entitlement).

## 9. Open questions (carried)

1. **Value-share experiments** for ground-truth-clean programs (priced on reconciled outcomes) — explicitly future; requires tenure data.
2. **Multi-operation bundling** — at evidence.
3. **Enterprise/team shape** — out of scope until the solo-operator motion proves.
4. **Trial-tier default** — trial at Delegated (recommended default: shows bounded autonomy without the scariest dial) vs operator-choice; finalize at P1.
