# ADR-409: Per-Seat Type-B Pricing — fixed sub outside, meter inside, BYOK as the tier lever

**Status**: Proposed (2026-07-06) — doc-first; shape operator-aligned in the ADR-408 discourse. Implementation is demand-gated to the seat lane going GA (member invites are live; billing re-cut lands when a second paid seat is real). Numbers remain launch-test hypotheses per the ADR-396 discipline.
**Date**: 2026-07-06
**Dimension**: Purpose (Axiom 3 — what the operation pays for) over the ADR-391 cost architecture
**Relates to**: ADR-408 (three altitudes + lanes — the consumption model this prices), ADR-391 (balance/allocation/ledger architecture — preserved), ADR-404 (commons-scale named the candidate successor gate — this ADR is that successor)
**Amends / supersedes**: ADR-396 (the workspace-flat tier shape is superseded by the per-seat shape; ALL of ADR-396's machinery — `TIER_CONFIG`, allowance grant + banking rule, balance top-ups, the single meter, hide-dollars display, hard-stop — is PRESERVED and re-keyed, not rebuilt). ADR-334 remains superseded (no per-agent seat pricing; Altitude-3 agents are priced by a future ADR when that tier builds).

---

## 1. The model in one paragraph

The workspace pays **per human seat, per month, tiered** — a fixed
subscription, never a usage bill. Each seat **grants a usage allowance**; the
workspace's pool is the **sum of its seats' allowances** (one pool, the
existing ADR-396 mechanics — allowance expires monthly, top-ups survive).
Internalized model calls and steward work draw the pool invisibly; the user
sees **usage-%, never dollars** (transparency of action, opacity of dollars —
ADR-396 discipline). At pool-zero the edge is **hard-stop + optional top-up,
never automatic overage billing** — the user chooses to top up or wait for
the cycle (the Claude rate-limit psychology; no surprise bills). **BYOK is a
tier privilege, not a metering mode**: on BYOK-enabled tiers a seat's model
calls route to the customer's own keys and **draw nothing** (zero cost = zero
draw, the ADR-391 rule) — the seat price is the entire monetization of a BYOK
seat. There is **no usage tax on BYOK** (rejected: margin-on-their-own-key
optics, weak enforceability, invites bypass).

## 2. Decisions

**D1 — Seat = human member.** Billing counts active human grants
(owner + members). Foreign-LLM connections, connectors, and the steward are
not seats. Altitude-3 persona agents are NOT seats — priced by their own
future ADR. First seat is free-tier-eligible; **additional seats are always
paid** (the invite moment is the natural paywall — value is proven exactly
when a second human joins).

**D2 — The pool is per-workspace, sized by seats.** `workspaces.balance_usd`
+ allowance stay the single pool (ADR-391 D1 / ADR-407 Phase 0 unchanged);
the monthly grant becomes `Σ(seat allowance by tier)`. Any member's
internalized usage and all steward/system usage draw the one pool. The
double-charge invariant stands: `execution_events` is the sole ledger; the
router *reports*, the ledger *records*; BYOK calls land as rows with our
cost = 0 (activity stays legible, billing stays single-source).

**D3 — The steward always meters.** Freddie, embeddings, and system judgment
run on platform keys on every tier including BYOK — platform infrastructure
a customer key cannot substitute. This keeps the meter honest and non-zero on
BYOK accounts.

**D4 — Tier axes**: allowance size per seat · **BYOK / BYO-endpoint access**
(top tier — this is the solo-vs-enterprise segmentation: low tiers are
internalized-only = fastest setup + usage margin; the enterprise tier buys
key custody + the on-prem lane) · retention (ADR-392 machinery) · premium
model access (candidate). Do NOT double-charge on people: per-seat replaces
any commons-scale cap as the growth axis (resolving ADR-404's deferred
successor-gate question).

**D5 — Over-use behavior**: hard-stop at pool-zero + top-up (existing
`balance_usd` machinery). Explicitly rejected: automatic overage billing,
credit currencies (ADR-396's rejection stands), soft-limit surprise
invoices.

## 3. Both segments, one model

- **Solo**: 1 seat, internalized, allowance covers typical use, top-up if
  heavy — byte-identical to today's Type-B experience; zero-config setup
  preserved.
- **Enterprise**: N seats × top tier, BYOK for seat-model usage (their
  procurement/compliance preference), on-prem endpoint lanes included,
  steward metered on the pool. Pays for people, not tokens.

## 4. Implementation notes (when demand-gated work lands)

Grant computation in `platform_limits.grant_allowance` takes seat count ×
tier allowance; `billing_tiers.TIER_CONFIG` gains per-seat semantics + a
`byok` flag; LS products move to quantity-based subscriptions (seat count);
the router (ADR-408 D4 spike) reports per-key usage mirrored into
`execution_events` with `billable` semantics = cost-to-us. Display surfaces
already show usage-% — unchanged. Regression gate: N=1 free workspace stays
byte-identical; a BYOK seat's calls never decrement the pool; steward calls
always do.

## 5. Open (deliberately)

Numbers (seat prices, allowance sizes) — set at implementation as
launch-test values against UNIT-ECONOMICS, changed freely on evidence.
Annual/volume discounts, seat proration, and the Altitude-3 agent pricing
ADR — all later.
