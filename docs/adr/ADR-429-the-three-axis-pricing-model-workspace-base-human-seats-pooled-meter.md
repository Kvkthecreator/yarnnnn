# ADR-429 — The Three-Axis Pricing Model: Workspace Base · Human Seats · Pooled Meter

**Status**: Accepted (2026-07-09, operator-ratified in discourse — the model shape [three axes + the seat=access carve], the "launch-test placeholder numbers" approach, and the **ship-dormant-activate-by-config** sequencing were each confirmed; the operator anchored the model on "what Anthropic/OpenAI Team does"). **This commit is doc-first — no code.** The build follows: **Phases 1–2 are approved to build now** (per-member usage FE + the dormant seat mechanism); **Phases 3–4 (marketing coherence + per-member caps) are held for the numbers/activation discourse** (§9). Each build seam is its own follow-on commit (the ADR-391/416 pattern). This ADR RATIFIES the pricing model and DECIDES the three revenue axes + their carve + the dormant-activation shape; the *numbers* and the *activation moment* are the reversible layer (§5/§5a/§9). It supersedes no built code — the balance layer, the Type-B tier, and the per-principal attribution stand; this ADR names what they *mean together* and closes the seams they left open.
**Date**: 2026-07-09
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A (system canon — real-operator-facing)
**Dimension**: Purpose (Axiom 3 — what the price is *for*, across three axes) + Identity (Axiom 2 — who pays [workspace], who holds a seat [human], who spends [any principal]) + Substrate (Axiom 1 — where billing state lives, at which scope)
**Relates to**: ADR-416 (the workspace as billing unit — this ADR keeps its root and resolves the D2 seat-scaling it left vague), ADR-396 (the Type-B allowance+meter model — this ADR adds the base/seat axes above its meter, preserving its one-meter carve), ADR-391 (the three-layer cost model — this ADR gives Layer ② [per-principal allocation] its first concrete consumer: the per-member spend cap), ADR-334 (per-operation trust-tiered seats — confirmed retired, its "seat" word disambiguated here), ADR-373/386/404 (multi-principal grants + member invites — the seat primitive this bills), ESSENCE v15 (the moat = the workspace commons — the reason the base is per-workspace)
**Supersedes/Amends**: **amends ADR-416 D2** (its "human seats scale the tier" is replaced by an explicit three-axis model with the seat=access carve made precise — no longer a tier *multiplier* but a distinct *access* line); **amends ADR-396** (its flat Free/Starter/Pro tiers gain a seat axis + become the per-workspace *base*; the one-meter carve + launch numbers stand as the base-tier + N=1-seat case); **confirms ADR-334 retired** (autonomy is not the pricing axis; "seat" here = human access, not a trust tier). Does NOT change the ADR-396 metering carve, the balance mechanics, or the double-charge invariant.

---

## 1. Context — the model was fragmented across three ADRs and the marketing page

The 2026-06→07 band shipped a working billing layer but split its *meaning* across
three decisions that never fully agreed. The operator, trying to place the
Billing/Usage panes, surfaced the real problem: **there is no single, cohesive
answer to "what am I buying."** An audit (2026-07-09) found three overlapping
models live at once:

| # | Model | Where it lives | State |
|---|---|---|---|
| **1** | **Per-workspace flat plan** (Free/Starter/Pro = allowance + 2 gates) | `billing_tiers.py::TIER_CONFIG`, the migrations, the marketing page | **BUILT + shipped** — the real product |
| **2** | **Per-workspace plan that scales by human seat** | ADR-416 D2 / Phase 3 (prose only) | **DECIDED, never built** — no seat math anywhere in code |
| **3** | **Per-operation trust-tiered seats** ($149/$299/$499, autonomy-as-price) | ADR-334 | **RETIRED** by ADR-416 — but its word "seat" leaked into Model 2 |

The fragmentation is felt three ways:
- **In code**: `TierSpec` has no seat dimension; the marketing page says "invite your
  team into the same shared workspace" with **no per-seat price**; canon (ADR-416 D2)
  says price scales by seat. The public face tells Model 1; the canon says Model 2.
- **In the abuse question the operator raised**: under a flat per-workspace plan, an
  owner amortizes unlimited guests over one price — a guest draws the owner's pool
  and burns LLM spend the owner pays for, with no per-guest control.
- **In the "seat" word itself**: Model 2 borrowed it from the dead Model 3, so "seat"
  carried a retired trust-tier connotation that never fit human access.

The operator's resolution anchor: **"do what Anthropic/OpenAI Team does."** That model
resolves all three tensions — and, crucially, it is ~80% the shape already built.

## 2. The reference model (Anthropic/OpenAI Team), mapped to what exists

Both major LLM players converge on the same shape, and it maps 1:1 onto YARNNN's
substrate:

| Reference concept | YARNNN equivalent | Audit verdict |
|---|---|---|
| Organization = billing account | **the workspace** (`workspaces.balance_usd` + `subscription_tier`) | BUILT |
| Seats billed per human (access + baseline) | **human members** (`principal_grants role ∈ {owner, member}`; invites ship) | member primitive BUILT; seat *as a priced unit* UNBUILT |
| Pooled usage, metered | **the workspace balance, one meter** (`execution_events`, ~$0.08/judgment call) | BUILT |
| Per-member usage breakdown | **`spend_by_principal(workspace_id)`** RPC + `GET /spend-by-principal` | backend BUILT, **zero FE** |
| Per-member spend limits (admin abuse control) | **per-principal allocation cap** (`agents/{slug}/_budget.yaml`, ADR-391 Layer ②) | UNBUILT (reserved sidecar) |
| "Who may pay" | **`billing` grant scope** (`has_billing_authority`, ADR-416 D1) | BUILT |
| Leave org → usage doesn't follow | workspace-keyed balance | BUILT |

The insight this table makes concrete: **the operator's instinct is not a new model —
it is the per-workspace pooled model plus per-member attribution + per-member caps,
which is exactly the LLM-player Team shape.** The gaps are precise and small (§7).

## 3. The root decision — three orthogonal revenue axes, one carve that keeps them honest

Pricing has **three axes**, each charging for a distinct thing. The whole coherence
of the model rests on keeping them orthogonal (the fragmentation was fusing them):

### Axis ① — Base (per workspace, per tier) — *the asset*
The workspace subscribes to a tier (Free/Starter/Pro). The base buys the **durable
memory asset served everywhere** + the two scale gates (retention window, connector
count). It is **per workspace, not ×headcount** — because value accumulates in the
workspace commons (ESSENCE v15), and that is what the base monetizes. The
UNIT-ECONOMICS finding: the base is where the business is (it converts a $3-gross
Light user into a ~$13–16-gross one by pricing the asset, not the tokens).

### Axis ② — Seats (per human) — *access*
Each **human** member of the workspace is a seat, billed per head (the OpenAI-Team
model). A seat buys a person **the right to act in the commons** — not a token bucket.
The first seat is included in the base (the owner); additional humans add a seat fee.
**AI principals (`role ∈ {foreign-llm, a2a, own-agent}`) add FREE** — they are not
humans buying access; their compute is already metered as Axis ③.

### Axis ③ — Metered usage (pooled, all principals draw) — *the compute*
LLM judgment (~$0.08/call) is the one meter (ADR-396's carve, unchanged: substrate
writes / perception sync / recall+trace reads are free; retention + connectors are
gates). Every principal — human or AI — draws the **one shared workspace pool**
(allowance → top-up balance → hard-stop at zero). Usage is **attributed per principal**
(`execution_events.principal_id`).

### The carve that keeps the axes from double-charging (the load-bearing rule)

> **A seat buys access, NOT usage. Usage is a separate, shared, metered pool.**

This is the exact thing OpenAI/Anthropic get right and the thing that makes the model
un-confusing:
- Adding a human costs a **seat fee** (Axis ②) — but their spend still draws the
  **shared pool** (Axis ③), not a per-seat token allotment. No per-seat usage bucket.
- Adding an AI costs **no seat** (it is not a human buying access) — but its spend
  **draws the pool** (Axis ③). This preserves ADR-396's "one meter, no double-charge":
  an AI connection's cost is captured once, as metered judgment; a per-AI seat fee
  would double-charge it (ADR-416 D2's original reasoning, kept).

**The abuse control is Axis ②-adjacent but distinct: the per-member spend cap.** The
seat fee is a *revenue* lever; the per-member spend cap ("this member may draw ≤ $X of
the pool") is the *safety* lever — the admin's abuse control, exactly like an OpenAI
org admin capping a member/key. **Conflating "charge per seat" with "control abuse"
was part of the fragmentation.** Seats are revenue; caps are safety; the pool
hard-stop is the backstop. Three distinct mechanisms.

## 4. What each launch buyer experiences (both first-class, ADR-396's dual buyer)

- **Solo / personal workspace (N=1)**: one workspace, one seat (themselves, included
  in the base), the base allowance, one pool. Seats are invisible — it reads as a flat
  plan. This is Model 1 exactly; the seat axis is dormant at N=1.
- **Team / shared workspace**: workspace base + (additional humans × seat fee) + one
  shared metered pool. The admin **sees per-member usage** (`spend_by_principal`) and
  can **cap or revoke** any member. AIs are free to add. This is the OpenAI-Team shape
  a team already understands.

The same code path serves both: N=1 is the one-seat case of the seat axis. No branch,
no separate "personal vs team" model — a difference of seat count, not of kind.

## 5. Launch-test placeholder numbers (hypotheses, not claims — the ADR-396 discipline)

Per the operator's ruling, the ADR sets **launch-test placeholders** — "test, not be
right, reversible," exactly as ADR-396 §7 framed its own numbers. These are grounded in
UNIT-ECONOMICS (base band ~$15–25; a judgment call ~$0.08; a Light user ~$6/mo, Active
~$34/mo) but are **hypotheses a first paying customer resolves.** They live in one place
(`billing_tiers.py::TIER_CONFIG`, extended with the seat field) and everything derives
from there.

| Tier | Base (per workspace) | Seats included | Additional human seat | Monthly allowance | Retention | Connectors |
|---|---|---|---|---|---|---|
| **Free** | $0 | 1 | *(no team on Free — invite-gated to paid)* | $0 (top-up to use) | 7d | 1 |
| **Starter** | $19 / mo | 1 | **+$12 / human / mo** | $15 | 30d | 3 |
| **Pro** | $49 / mo | 1 | **+$12 / human / mo** | $45 | 90d | ∞ |

- **AI principals**: free to add on every tier (they meter Axis ③; they are not seats).
- **The additional-seat fee is placeholder** ($12) — the felt-value of a teammate's
  access is the unvalidated number, like the base. Tune against first team customer.
- **Free-tier team**: proposed invite-gated to paid tiers (a shared commons is a paid
  capability; a free workspace is single-seat). *Open — see §9.*
- **Per-member spend cap**: an admin control, not a price. Default = uncapped (draw the
  whole pool); the admin may set a per-member ceiling. Shipped in Phase 4 (§7).

**These numbers change freely against evidence.** The ADR ratifies the *shape* (three
axes + carve); the numbers are the reversible layer.

### 5a — Activation: ship dormant, flip on by config (operator ruling 2026-07-09)

The seat axis is an **architectural slot the numbers drop into**, not a number baked
into the plumbing — so the build ships it **dormant**: the seat mechanism exists end to
end (the `TierSpec` seat field, checkout quantity, webhook `seats × unit`, the seat FE),
but `additional_seat_usd` **defaults to `0` / inactive**, so:

- **N=1 and every existing workspace is byte-identical** — nobody is charged for a seat
  on deploy; a multi-human workspace that exists today is not retroactively billed.
- **Activation is one config change** — the operator sets the real seat number *and*
  flips the axis on, in `TIER_CONFIG`, when the number + the activation policy are
  decided. No code change, no migration, no redeploy of logic.

This is the same ship-dormant-activate-by-config pattern the connector-capture lane
(`CONNECTOR_CAPTURE_ENABLED`) and the ADR-396 launch numbers already use — a proven
launch-gating shape in this codebase, not a new risk. **The architecture is decided
now; the number and the activation moment (grandfathering, free-tier team gating,
trial-on-new-seat) are the deferred discourse (§9).** The build is instructed to make
the *dormant* path the default and the *active* path a pure config flip — the seat=access
carve (§3) and the double-charge invariant hold identically in both states.

The load-bearing architectural commitments that are NOT deferred (they shape the code
regardless of the number): **a seat is a human** (`role ∈ {owner, member}`; the count is
that filter), **AI principals are free** (never counted as seats), and **the meter stays
one shared pool** (a seat never carries its own usage bucket — the §3 carve). Those are
locked here; only the price and the on-switch defer.

## 6. The autonomy/witness reframe is unaffected (and confirms the direction)

ADR-416 §4 settled that "Autonomy" is the per-principal **witness dial** (when an act
binds), not capital authority or a price tier. This ADR keeps that intact: the witness
dial is orthogonal to all three pricing axes. A seat is *access*; the witness dial is
*when your acts bind*; metering is *what you spend*. Three per-actor properties, cleanly
separated — the un-fusing ADR-416 §4 began, completed at the pricing layer here.

## 7. The build seams as phases (implementation — NOT this commit)

Grounded in the 2026-07-09 audit. Each phase is its own commit + gate, ordered by
dependency and launch value. The foundation is further along than the fragmentation
suggested: **attribution is done, the member/seat primitive exists, "who may fund" is
already a grant.**

- **Phase 1 — Per-member usage FE (the legibility unlock; backend BUILT).** Give the
  built `spend_by_principal(workspace_id)` RPC + `GET /spend-by-principal` route their
  first FE home: a "who spent what" breakdown on the Usage pane (per-member rows over
  the shared pool, activity-not-dollars per ADR-396). Ensure `principal_id` is stamped
  with the *acting* principal (not defaulted to `user_id`) on the member + foreign-LLM
  paths (`telemetry.py:302`). **Gate**: at N>1 the breakdown attributes correctly.
  **Value: the multi-principal commons becomes honest — "who spent what" is visible.**
  *Zero backend build — pure FE + a stamping check.*

- **Phase 2 — The seat as a priced unit (the model's new axis) — SHIPPED DORMANT
  (§5a).** Extend `TierSpec` with a seat dimension (`included_seats`,
  `additional_seat_usd`), **defaulting `additional_seat_usd = 0` (dormant)**. Extend
  checkout (`subscription.py`) + the LS webhook to carry a seat **quantity** (a seat LS
  variant with `quantity = human_count − included`, or the webhook computing
  `seats × unit`) — the quantity math is built and correct, but with a $0 unit it bills
  nothing. The human-seat count is the trivial `role ∈ {owner, member}` filter (audit
  §5). Reconcile with the ADR-396 flat tiers (they become the 1-seat row). **Gate**:
  with the seat fee dormant ($0) N=1 AND existing multi-human workspaces are
  byte-identical (no seat charge); with a non-zero seat fee set in test, adding a human
  member changes the computed invoice and adding an AI principal does not. **Value: the
  team-growth revenue axis, built and dormant — activation is a config flip (§5a).**

- **Phase 3 — The marketing + in-app coherence pass (the story, told once).** Rewrite
  `web/app/pricing/page.tsx` + the landing/FAQ/llms.txt to the three-axis story: *free
  workspace + memory; a plan for the operation (base + allowance); per-seat for your
  team; usage metered from a shared pool; see every action, cap any member.* Update the
  Billing pane (base + seats + top-ups) + the Usage pane (per-member breakdown from
  Phase 1) + the UserMenu Budget glance so the public face and the product tell **one**
  story. Resolve the Billing/Usage/Budget **placement** here (§8). **Gate**: the
  pricing page, the Billing pane, and the canon agree on the three axes. **Value: the
  fragmentation the operator felt is gone from every surface.**

- **Phase 4 — Per-member spend caps (the admin safety lever; ADR-391 Layer ②).** Build
  the reserved `agents/{slug}/_budget.yaml` (generalized: per-*principal*) sidecar into
  a live per-member draw ceiling on the shared pool. Add the admin UI (a per-member cap
  field beside the per-member usage from Phase 1). The gate reads the per-principal
  rollup (built) against the per-principal ceiling (new). **Gate**: a member at their
  cap is blocked from further draw while the pool is non-zero for others; owner
  uncapped by default. **Value: the abuse control the operator raised — bounded guests
  without per-user billing.** *(Sequenced last: its first real consumer is an owner
  bounding a specific member/agent; the pool hard-stop + revocation cover the interim.)*

**Interim abuse control (pre-Phase 4)**: the pool hard-stop (a guest can only drain the
shared allowance, then everyone stops) + per-member attribution visibility (Phase 1) +
grant revocation (ADR-386, built — the owner removes an abusing member). Phase 4 adds
the *bounded* cap on top; it is not a launch blocker.

## 8. The Billing/Usage/Budget placement (the question that started this)

The three-axis model makes the placement decision derivable rather than contested. All
three surfaces are **workspace-account** concerns (they read/manage the *workspace's*
money — base, seats, pool, per-member usage):

- **Billing** (base + seats + tier + top-ups + who-may-fund) and **Usage** (per-member
  breakdown) manage a *workspace's* money. They render wherever the workspace's account
  lives — and each pane **names the workspace it bills** (as `BillingPaneBody` already
  does), which is what makes the placement *safe* regardless of which door hosts it (the
  ambiguity ADR-416 flagged — "looks like one personal plan, swaps silently on switch" —
  is closed by the workspace-naming, not by the door choice).
- **Budget glance** (UserMenu) stays the model's exemplar: a workspace-scoped read under
  the WORKSPACE section header, next to the switcher — unambiguous.

**Decision**: the *door* (Workspace Settings vs User Settings vs UserMenu) is a
**rendering choice the model has now made safe**, and it is resolved in **Phase 3's
coherence pass** — not by this ADR's fiat, and no longer a scope contradiction. The
operator's stated preference (move Billing/Usage toward the account door / UserMenu,
"like Budget") is *compatible* with the model **iff every pane names its workspace**
(which the model requires anyway). Phase 3 lands the placement + the workspace-naming
together. This ADR unblocks that choice; it does not pre-empt it. *(This closes ADR-416
§9's deferred "UserMenu scope surface" discourse.)*

## 9. Open questions (deliberately not decided here)

- **Free-tier team**: §5 proposes a shared commons is a paid capability (Free =
  single-seat, invites gated to paid). Whether Free allows a limited team (e.g. 1 guest)
  is a growth/funnel question for the Phase 3 numbers pass.
- **Seat number** ($12 placeholder) and **whether the base includes >1 seat**: felt-value
  questions a first team customer resolves (ADR-396's standing numbers-deferral).
- **Per-member cap default + granularity** (per-member $ vs % of pool; whether AIs get
  caps too): Phase 4's design discourse.
- **Billing authority beyond owner** (a first-class "co-owner" role vs granting the
  `billing` scope to a member): the membership-model question ADR-416 §9 already parked.

## 10. The canon cascade (owed with the phases, not this commit)

- **`billing_tiers.py`**: `TierSpec` gains the seat fields (Phase 2).
- **`scope_manifest.yaml`**: `workspaces` (balance + tier + seats) stays content-scoped
  (per-workspace) — this ADR reaffirms ADR-416's ruling. The seat count is derived from
  `principal_grants`, not a new store.
- **GLOSSARY**: add "Seat" (= a human member's access, per-head billed), "Pricing axis"
  (base/seat/meter), "Per-member spend cap" (the admin safety lever); correct any
  "seat" entry still carrying the ADR-334 trust-tier connotation.
- **ESSENCE / FOUNDATIONS**: no axiom change — this is a Purpose-layer settling the
  existing axioms permit (the workspace is the billing unit; a seat is a human grant; the
  meter is Trigger-layer). A one-line note that price has three axes (asset/access/
  compute) may be worth adding to the ESSENCE moat section; derivable, not new.
- **Supersede banners**: ADR-416 D2 (seat-scaling → this three-axis model), ADR-396
  (tiers → the base axis; numbers stand as the N=1 case).

## 11. What this ADR does NOT do

- **No code** (doc-first; the four phases are each their own commit).
- **No change to the ADR-396 metering carve** (one meter = LLM judgment; free reads;
  gates = retention + connectors). The seat axis sits *above* the meter, never inside it.
- **No change to the balance mechanics** (allowance→balance→hard-stop, top-ups persist,
  no credit currency). Axis ③ is unchanged.
- **No double-charge** (ADR-396 invariant preserved — the seat=access carve exists
  precisely to protect it: a seat never buys tokens the meter also bills).
- **No autonomy-as-price** (ADR-334 stays retired; "seat" here is human access).
- **No pane moved yet** (the placement resolves in Phase 3, workspace-named).
