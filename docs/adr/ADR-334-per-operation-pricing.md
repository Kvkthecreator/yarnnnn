# ADR-334 — Per-Operation Pricing: Delegation-Tiered Seats over the Cost Ledger

**Status:** **Ratified (direction)** — 2026-06-10. Tier prices + free-tier shape + trial mechanics operator-ratified in-session; implementation phased (§8), `/pricing` page rewrite lands with the marketing refactor.
**Date:** 2026-06-10
**Deciders:** KVK (operator) + Claude (collaborator)
**Hat:** A (system canon)

> **Discourse base:** [`cumulative-workspace-product-formulation-2026-06-10.md`](../analysis/cumulative-workspace-product-formulation-2026-06-10.md) §5 (pricing direction ratified: per-operation seat, delegation-tiered, ledger as floor, Layer-1 trojan) + GTM_POSITIONING v4 §5 (high-ACV expansion-led motion). Grounded against the live monetization stack: `docs/monetization/STRATEGY.md` (ADR-172/291 balance model), `COST-MODEL.md` (per-task economics), the LS product inventory.

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

## 8. Implementation phases (build-lane work, post-ratification)

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
