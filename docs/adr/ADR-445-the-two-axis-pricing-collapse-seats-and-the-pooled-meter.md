# ADR-445 — The Two-Axis Pricing Collapse: Seats + the Pooled Meter

**Status**: Implemented (2026-07-12 — model ratified + all four phases landed in one pass). RATIFIES a simpler pricing model than ADR-429 and **supersedes ADR-429's Axis ① (the per-workspace base fee)**. **Phases 1–4 SHIPPED**: (1) `billing_tiers.py` config re-tune (seats LIVE, `included_seats` = billing baseline not a cap, free = solo) + the invite gate reworked to fire ONLY on the free→paid boundary (`upgrade_required`, 402) + seat-awareness in `GET /workspace/members` (paid grows freely); (2) checkout carries the seat `quantity` + a best-effort `sync_seat_quantity` on invite-accept/member-revoke keeps the LS subscription in step; (3) the coherence pass — SubscriptionCard, WorkspaceMembersCard, the pricing page, landing, FAQ, and llms.txt all tell the two-axis story; (4) per-member spend caps — a `governance/_member_caps.yaml` sidecar (`services/member_caps.py`) + a gate in the addressed path + the owner UI (a "Set spend cap" verb + chip on the members card). Regression gate `api/test_adr445_two_axis_pricing.py` 37/37 (replaces the deleted `test_adr429_seat_axis.py`); FE `tsc --noEmit` clean; ADR-373/404 sibling gates green. **Operator LS-dashboard step remaining (not code):** make the `starter` LS variant a per-seat subscription (unit = $20/seat) so `quantity` bills correctly. The three-axis model (base · seats · meter) collapses to **two axes: seats · meter** — the paid subscription IS the per-seat price, not a separate base fee sitting above seats. Anchored, at the operator's instruction, on what OpenAI and Anthropic actually charge for (evaluated in §3), and re-derived from the ground rather than accepted from ADR-429. The seat fee is set to a **real launch price** (not dormant, reversing ADR-429 §5a's dormant-launch decision) because in the two-axis model seats ARE the team-revenue path, not a secondary add-on. It supersedes no built substrate — the workspace-as-billing-unit (ADR-416), the pooled meter + allowance mechanics (ADR-396), and the per-principal attribution (ADR-373/291) all stand; this ADR changes what the tier's price *means* and where the free→paid boundary falls.

**Date**: 2026-07-12
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A (system canon — real-operator-facing; ships through Render → live billing)
**Dimension**: Purpose (Axiom 3 — what the price is *for*, now across two axes) + Identity (Axiom 2 — who pays [the workspace owner], who holds a seat [a human], who spends [any principal]) + Substrate (Axiom 1 — billing state stays at the workspace scope)
**Relates to**: ADR-429 (the three-axis model — this ADR collapses its Axis ① into the seat axis and keeps its seat=access carve + its meter carve), ADR-416 (the workspace as billing unit — reaffirmed, unchanged), ADR-396 (the Type-B allowance + one-meter model — the meter axis stands verbatim; the tier's `price_usd` is re-meant), ADR-373/386/404 (multi-principal grants + human invites — the seat primitive this bills), ADR-439 (BYOK/enterprise capability tier — orthogonal, unaffected)
**Supersedes/Amends**: **supersedes ADR-429 Axis ① (the per-workspace base fee)** — there is no standalone base charge; the paid subscription is the seat price. **Amends ADR-429 §5a** (seats ship *live-priced* at launch, not dormant — the two-axis model makes seats the revenue path). **Amends ADR-429 §12.3c** (the free→paid boundary is re-derived: solo owner = free, the 2nd human makes the workspace paid). **Reaffirms** ADR-416 (workspace = billing unit), ADR-396 (the one-meter carve + balance mechanics + no-double-charge invariant), and ADR-429's seat=access carve (a seat buys access, not a usage bucket). Does NOT touch the metering carve, the balance mechanics, the double-charge invariant, or the autonomy/witness reframe.

---

## 1. Context — the model was internally contradictory, and the contradiction reached the operator's screen

The operator, placing the Billing and Workspace-Members surfaces side by side, hit two
screens that told opposite stories about the same concept:

- **Workspace Members** (a paid `starter` team of 3 humans): *"3 of 1 seat used — seat
  limit reached — **upgrade to invite more people**."* A hard block (HTTP 402) on a
  workspace that is **already on the top paid plan** — there is nothing to upgrade to,
  and the paid plan is supposed to be the thing that *opens* the team.
- **Billing** (a solo `starter`): *"1 of 1 seat used · **seats aren't billed yet** ·
  your whole workspace draws one shared allowance."* The dormant-seat, pooled-meter
  story — correct per ADR-429 §5a.

This is not two data sources disagreeing (both read the same `principal_grants` seat
math). It is **one model contradicting itself**, surfaced three ways:

1. **The config fought the copy.** `starter.included_seats: 1` + the invite route
   treating `included_seats` as a HARD CEILING (`workspace_invites.py`) meant a paid
   team's 2nd human was refused with an "upgrade" message — while the pricing page copy
   already said *"the paid plan opens the workspace to your whole team"* (uncapped).
   The public face had drifted to a two-axis, seat-inclusive story; the plumbing was
   still enforcing ADR-429's three-axis, base-plus-capped-seats shape. They never agreed.

2. **`included_seats` carried two incompatible meanings.** It was simultaneously (a) the
   *billing baseline* ("humans covered before the per-seat fee") and (b) a *hard
   headcount ceiling* ("you physically cannot invite past this"). ADR-429 only ever
   intended (a); the invite gate wired it as (b), and applied it to the paid tier where
   no ceiling belongs.

3. **The three-axis model itself was heavier than what was being sold.** ADR-429 posited
   a per-workspace BASE fee (Axis ①) *distinct from and above* the seat fee (Axis ②).
   But the launch collapse (ADR-429 §12) had already stripped the base's differentiators
   (retention + connectors gate the dormant capture lane), leaving the "base" as just
   *a number attached to the workspace* — indistinguishable, in what the buyer
   experiences, from "the price of the first paid seat + its allowance." The third axis
   was doing no work the buyer could feel.

The operator's resolution, pressed to the reference: **"we are charging for seats — per
workspace — and metered usage. Two things, not three."** This ADR ratifies that.

## 2. The re-frame the operator brought (stated precisely)

> A user spawns as many workspaces as they want (capping is an abuse concern, deferred).
> Per workspace, two charges: **seats** (seat 1 = the owner = free; seat 2+ priced per
> head) and **metered usage** (pooled). The **owner** manages the seat payment; usage is
> a shared, metered pool.

Two refinements this ADR makes to that frame, after the §3 evaluation:

- **The meter is owner-paid, not per-member-paid.** The operator's first framing had
  "usage managed by the individual users." §3 shows neither reference bills a member for
  their own usage inside someone else's workspace — the value and the cost accrue to the
  workspace, so the workspace's payer (the owner) covers the pooled meter. The
  legitimate need behind "members manage their usage" is **abuse control**, which both
  references solve with **per-member visibility + owner-set caps** on the shared pool,
  not a per-member billing relationship. This ADR adopts that (§5, §7).

- **The free→paid boundary is the 2nd human.** A solo workspace (1 human) is free; the
  moment a 2nd human joins, that workspace is paid (seat-billed). This is the OpenAI /
  Anthropic Team funnel exactly, and it is derivable from "seat 1 free, seat 2+ priced."

## 3. The evaluation — what OpenAI and Anthropic actually charge for (the two suffice)

The operator asked not merely to check alignment but to *evaluate whether this is the
right model* against the reference players. Both converge on the identical shape:

| | **ChatGPT / Claude (consumer)** | **OpenAI / Anthropic Team** | **API / Platform** |
|---|---|---|---|
| Billing unit | the **person** (account follows them) | the **workspace/org** | the **org** |
| Paid unit | per-person subscription (~$20/mo) | **per-seat, by headcount** (~$25–30/seat/mo, min seats) | **metered usage** (pooled) |
| Workspace/org creation | — | **free to create** | free to create |
| Usage | rate-limited (bundled into the sub) | **bundled into the seat** (rate-limited) | **metered, pooled, org-paid** |
| Who pays | the individual | the **org admin** (all seats + the shared bill) | the **org** |

**The three load-bearing facts, and how they judge each candidate model:**

1. **The seat price IS the subscription — there is no separate "org base fee" above
   seats.** A Team plan is literally `seats × price`. → **ADR-429's Axis ① (a
   per-workspace base fee distinct from seats) has no analogue in either reference.**
   The two-axis model matches; the three-axis model invents a charge the references
   don't have.

2. **The workspace/org is free to create; the paid unit is the human's access (the
   seat).** → matches the operator's "unlimited workspaces, seat 1 free, seat 2+ paid"
   exactly.

3. **Nobody bills a member for their own usage inside a shared workspace.** Usage is
   bundled-into-the-seat (Team) or pooled-and-org-paid (API). → **rejects the
   "each member pays their own meter" variant**; adopts owner-paid pooled meter +
   per-member caps as the abuse lever.

**Verdict:** the operator's two-axis instinct is *closer to the reference than ADR-429
was.* ADR-429's third axis (the per-workspace base) was the divergence; collapsing it is
a *correction toward the anchor*, not a novel invention. The one place the operator's
frame diverged from the reference — per-member usage billing — this ADR corrects back to
owner-paid-pooled, keeping the intent (member spend control) via the reference's own
mechanism (caps).

**The one strategic cost this model accepts (named, not hidden):** under two axes, a
**solo power-user with a rich, valuable workspace pays little** — they are seat 1 (free)
and pay only via metered usage (their own allowance/top-ups). ADR-429's entire Axis ①
existed to monetize exactly that user ("the base is where the business is"). By
collapsing the base, this ADR **accepts solo = low-revenue by design** and bets revenue
on **teams (seats) + heavy usage (top-ups)** — which is precisely the ChatGPT/Claude
funnel (a large free/cheap solo tier; money from Team seats + Plus subscribers + API
usage). This is a deliberate strategic bet, ratified here, reversible against evidence
(a solo *paid* tier — seat 1 becoming a paid seat above a usage/feature line, the
ChatGPT-Plus shape — remains a future option if solo monetization proves necessary; §9).

## 4. The decision — two orthogonal pricing axes, one payer, one carve

Pricing has **two axes**. The workspace is the billing unit (ADR-416, unchanged). The
**owner** is the payer for both axes.

### Axis ① — Seats (per human) — *access, and the subscription itself*
Each **human** member of a workspace is a seat. **Seat 1 — the owner — is free.** Each
**additional human** is a priced seat (per head, per month). **The per-seat price IS the
paid subscription** — there is no separate base fee beneath it. A workspace with one
human is **free**; a workspace with two or more humans is **paid**, at `(humans − 1) ×
seat_price`. AI principals (`role ∈ {foreign-llm, a2a, own-agent, platform}`) are
**never seats** and **never charged** — their compute is metered as Axis ② and a seat
fee would double-charge it.

### Axis ② — Metered usage (pooled, owner-paid) — *the compute*
LLM judgment (~$0.08/call) draws **one shared workspace pool** (allowance → top-up
balance → hard-stop at zero — ADR-396, unchanged). Every principal (human or AI) draws
the same pool; usage is **attributed per principal** (`execution_events.principal_id`).
**The owner pays the pooled meter** (its allowance is granted with the paid plan; its
top-ups sit beneath). The ADR-396 carve is unchanged: the meter is LLM judgment only —
substrate writes / perception sync / recall+trace reads are free; retention + connectors
are gates, not meters.

### The carve that keeps the two axes honest (unchanged from ADR-429 §3)

> **A seat buys access. Usage is a separate, shared, metered pool.**

A new teammate costs a **seat fee** (①) for their access; their *work* still draws the
**shared pool** (②), not a per-seat token allotment. An AI costs **no seat** but draws
the pool. This is exactly the no-double-charge invariant of ADR-396, preserved.

### The abuse control (the operator's "members manage their usage," done right)
The owner does not want a member draining the shared pool unbounded. The lever is
**per-member usage visibility** (`spend_by_principal`, backend built) **+ an owner-set
per-member spend cap** on the shared pool (ADR-391 Layer ②, unbuilt) — NOT a per-member
billing relationship. Seats are revenue; caps are safety; the pool hard-stop is the
backstop. Three distinct mechanisms (ADR-429's separation, kept).

## 5. What each buyer experiences

- **Solo (N=1)**: one free workspace, one seat (themselves, free), their own metered
  usage (a small signup allowance + top-ups; the pooled meter hard-stops without a paid
  allowance — a natural self-limit). Reads as *"free forever for one person."* No
  subscription until a 2nd human joins.
- **Team (N≥2)**: the workspace is paid at `(humans − 1) × seat_price`; the paid plan
  grants a shared usage allowance the whole workspace draws; the owner pays seats + the
  pooled meter; the owner **sees per-member usage and can cap or revoke** any member;
  AIs are free to add. This is the OpenAI/Anthropic Team shape a team already understands.

The same code path serves both: **N=1 is the zero-additional-seat case.** No "personal
vs team" branch — a difference of headcount, not of kind.

## 6. Launch numbers (hypotheses, reversible — the ADR-396 discipline)

Grounded in UNIT-ECONOMICS (a judgment call ~$0.08; a Light user ~$6/mo usage; the
reference Team band ~$25–30/seat/mo) and set as **launch-test values a first paying
customer resolves.** They live in one place (`billing_tiers.py::TIER_CONFIG`).

| | **Free** | **Paid (per additional human seat)** |
|---|---|---|
| Price | $0 | **$20 / additional human / mo** (seat 2+) |
| Seat 1 (owner) | free | free |
| Included with a paid seat | signup grant only | a **shared monthly usage allowance** (workspace-wide) |
| Monthly allowance | $0 (top-up to use) | **$15** (the whole workspace draws one pool) |
| Metered usage | pooled, owner-paid | pooled, owner-paid |
| AI connections | free, unlimited | free, unlimited |
| Retention / connectors | 7d / 1 | 30d / 3 *(these become real gates only when the capture lane ships — ADR-404)* |

Notes on the numbers (each reversible):
- **Seat price = $20/human/mo** — the low end of the reference Team band, chosen to make
  the 2nd-human step feel proportionate at launch. The allowance ($15) is granted at the
  workspace level with the paid plan, not per-seat (the meter is pooled — §4).
- **Free = solo (1 human).** ADR-429 §12.3c's "owner + 1 guest" is **superseded**: in
  the two-axis model the free→paid boundary is the 2nd human, so Free is single-seat. A
  "try a teammate free" allowance (e.g. a 14-day team trial) is a **growth-funnel
  option, deferred to §9** — it is a trial mechanic, not a pricing axis.
- **The old `starter` allowance ($15) + retention/connector gates carry over** onto the
  paid plan unchanged; only the *meaning of the price* changes (seat, not base).
- **`pro` / `enterprise` stay as they are** — `pro` dormant (`hidden`, returns with the
  capture lane), `enterprise` sales-led (ADR-439). Neither is affected by the collapse;
  when `pro` returns it returns as a second *seat-priced* plan with richer gates, not a
  base-fee tier.

**These numbers change freely against evidence.** This ADR ratifies the *shape* (two
axes, seat-priced, owner-paid pooled meter, free→paid at the 2nd human); the numbers are
the reversible layer.

## 7. The build seams as phases (implementation — NOT this commit)

The substrate is already ~90% shaped for two axes — the workspace-as-billing-unit, the
pooled owner-paid meter, the seat math over `principal_grants`, and the per-principal
attribution all exist. The collapse is a re-tune + a gate fix + a coherence pass, not a
re-architecture.

- **Phase 1 — The config + the invite gate (the bug the operator hit; the load-bearing
  fix).** In `billing_tiers.py`: activate the seat fee (`starter.additional_seat_usd =
  20.0`, no longer dormant), set `free.included_seats = 1` (solo = free; the 2nd human
  is paid) and `starter.included_seats = 1` (the owner is the one free seat; seat 2+
  billed). **Remove the hard-cap semantics from `included_seats`**: it is the *billing
  baseline* only. In `workspace_invites.py` + `routes/workspace.py`: the invite gate
  fires **only where a tier declares no paid path** — i.e. a **Free** workspace inviting
  a 2nd human returns an `upgrade_required` response (upgrade to the paid plan), and a
  **paid** workspace **never hard-blocks** an invite (each new human accrues a billed
  seat). **Gate**: a paid team of N can invite the (N+1)th human with no 402; a Free
  workspace's 2nd human invite returns upgrade-required; adding an AI never touches the
  seat count. *This phase alone resolves the two conflicting screenshots.*

- **Phase 2 — Checkout + webhook carry the seat quantity (the live seat charge).**
  Extend `subscription.py` checkout + the LS webhook so the subscription quantity is
  `human_count − 1` (the billed seats) at `additional_seat_usd` each. The quantity math
  (`billable_seats`, `seat_fee_usd`) is already built and correct — Phase 1 makes the
  unit non-zero, this phase makes the invoice reflect it. Reconcile the `starter` LS
  variant to a per-seat subscription. Grandfather existing workspaces with a notice
  window (`workspaces.seat_pricing_effective_at`, the ADR-429 §12.3b rail, already
  scoped). **Gate**: a 3-human paid workspace's computed invoice = `2 × $20 + the
  pooled allowance`; a solo workspace that has NOT taken the plan = $0 subscription
  (usage-only); adding an AI does not change the invoice.

  **Amendment (2026-07-21, operator-ratified — the solo-checkout question).** The
  original gate line read "a solo workspace = $0 subscription (usage-only)" without
  qualification, which contradicted the shipped checkout (`billable_seats` floored at
  1, so a solo owner who *takes* the plan pays one unit). The operator resolved in
  favour of the code: **a solo workspace may take the paid plan, and pays $20.** The
  free→paid boundary (§4) governs when a workspace *must* pay — the 2nd human — not
  whether a solo owner may choose to. What that $20 buys a solo owner is the **pooled
  allowance + the higher gates**, NOT a second seat; §4's "seat 1 is free" remains
  true as a *seat-axis* statement (they are never charged for a teammate they do not
  have). It is also the only solo monetization path in a model that otherwise accepts
  solo = near-zero revenue (§3), so it is retained deliberately. **Copy constraint
  this imposes**: no surface may tell a paying solo owner "your seat is free" — the
  upgrade CTA reads `$20/mo` (not `$20/seat/mo`) and the paid-solo seat row names the
  allowance, not the seat. Enforced by
  `web/lib/subscription/usage.ts::tierUpgradeLabel`; the seat-unit label
  `tierPriceLabel` was DELETED (it had exactly one caller — the CTA — where it was
  wrong).

- **Phase 3 — The coherence pass (the story, told once).** Rewrite the two panels
  (SubscriptionCard: "seats aren't billed yet" → the live per-seat line; WorkspaceMembers:
  drop the paid-tier "limit reached / upgrade" copy — it fires only on Free now) + the
  pricing page + landing/FAQ/llms.txt to the **two-axis story**: *free for one person +
  your memory; a paid seat per teammate; usage metered from a shared pool the owner
  funds; see every action, cap any member.* Reconcile the pricing-page header comment
  (which still says "three axes") to two. **Gate**: the pricing page, both panels, and
  this ADR agree on two axes.

- **Phase 4 — Per-member spend caps (the abuse lever; ADR-391 Layer ②).** Build the
  reserved per-principal `_budget.yaml` sidecar into a live per-member draw ceiling on
  the shared pool + the owner UI (a cap field beside the per-member usage from the
  built `spend_by_principal`). **Gate**: a member at their cap is blocked from further
  draw while the pool is non-zero for others; owner uncapped by default. *(Sequenced
  last; the pool hard-stop + revocation cover the interim.)*

**Interim abuse control (pre-Phase 4)**: the pool hard-stop + per-member attribution
visibility + grant revocation (ADR-386, built). Phase 4 adds the bounded cap; not a
launch blocker.

## 8. The canon cascade (owed with the phases, not this commit)

- **`billing_tiers.py`**: the seat fields re-meant (`additional_seat_usd` live;
  `included_seats` = billing baseline, never a hard cap); comments updated from
  three-axis to two-axis; the ADR-429 §5a "dormant" comments corrected.
- **GLOSSARY**: "Pricing axis" entry corrected to two axes (seats / meter); the "base
  fee" concept retired; "Seat" (= a human, seat 1 free, seat 2+ priced, owner-paid);
  "Per-member spend cap" (the owner's abuse lever) retained.
- **ESSENCE / FOUNDATIONS**: no axiom change (the workspace is the billing unit — Axiom
  1; a seat is a human grant — Axiom 2; the meter is Trigger-layer). If ESSENCE's moat
  section names "three pricing axes," correct to two.
- **Supersede banners**: ADR-429 (Axis ① collapsed into the seat axis; §5a dormant →
  live-priced; §12.3c free-boundary re-derived to the 2nd human). ADR-396's meter carve
  + balance mechanics stand.

## 9. Open questions (deliberately not decided here)

- **Solo paid tier**: whether to monetize the solo power-user with a paid seat-1 above a
  usage/feature line (the ChatGPT-Plus shape). Deferred; the two-axis model's accepted
  bet is solo = low-revenue (§3), revisited only if evidence demands.
- **Team trial**: whether Free gets a time-boxed "invite one teammate free" trial (a
  growth funnel), distinct from the pricing axis. A Phase-3 numbers question.
- **Seat price + allowance size** ($20 / $15): felt-value numbers a first team customer
  resolves (ADR-396's standing numbers-deferral).
- **Per-member cap default + granularity** (per-member $ vs % of pool; whether AIs get
  caps): Phase 4's design discourse.
- **Billing authority beyond owner** (a co-owner role vs granting a `billing` scope): the
  membership-model question ADR-416 §9 + ADR-429 §9 already parked.

## 10. What this ADR does NOT do

- **No code** (doc-first; the four phases are each their own commit + gate).
- **No change to the ADR-396 metering carve** (one meter = LLM judgment; free reads;
  gates = retention + connectors). The seat axis sits above the meter, never inside it.
- **No change to the balance mechanics** (allowance → balance → hard-stop; top-ups
  persist; no credit currency).
- **No double-charge** (the seat=access carve is preserved precisely to protect it).
- **No re-key of the billing unit** (the workspace stays the billing unit — ADR-416; the
  meter stays pooled + owner-paid; NO per-member balance, which would undo ADR-416/396).
- **No autonomy-as-price** (ADR-334 stays retired; a seat is human access).
