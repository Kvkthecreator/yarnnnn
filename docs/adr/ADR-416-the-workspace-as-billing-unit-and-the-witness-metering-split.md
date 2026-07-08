# ADR-416 — The Workspace as the Billing Unit, and the Witness/Metering Split

**Status**: Accepted (2026-07-08, operator-ratified — the billing-unit question was put to the operator, who delegated the recommendation; the three baked-in mechanics [billing-authority-as-grant, human-seat-scaling-with-AI-meter-only, phased seams] were each confirmed). **Doc-first — no code in this commit; the three implementation seams are each gated to their own follow-on commit (the ADR-391 pattern).** This ADR RATIFIES the framing and DECIDES the billing unit; it SCOPES the fixes to the three seams the audit exposed. It supersedes no built code — the balance layer and the Type-B tier stand; this ADR names what they *mean* and closes the seams they left open.
**Date**: 2026-07-08
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A (system canon — real-operator-facing)
**Dimension**: Purpose (Axiom 3 — what the price is *for*) + Identity (Axiom 2 — who pays, who spends, who may fund) + Substrate (Axiom 1 — where billing state lives, at which scope) + Trigger (Axiom 4 — the witness dial as the gate on *when* an act binds)
**Relates to**: ADR-391 (budget/balance/three-layer cost model — this ADR completes its Layer ②/③ framing and confirms Layer ①), ADR-396 (the Type-B pricing model — this ADR names its binding unit, which ADR-396 left implicit), ADR-405 (the witness dial — this ADR adopts its autonomy reframe as the settled meaning of the "Autonomy" surface), ADR-373 (the multi-principal re-key — the workspace-as-binding-unit is the root this ADR bills against), ADR-407 (the three-scope taxonomy — this ADR resolves the content/account billing tension the manifest named), ADR-334 (per-operation/seat pricing — confirmed deferred to Rung-2, its trust-axis reframed here), ADR-380/381/382 (the activation ladder — A3-agent billing is deferred to their runtime), ESSENCE v15 (the moat = the workspace commons — the reason the workspace is the billing unit)
**Supersedes/Amends**: amends ADR-391 (Layer ②/③ get a settled binding-unit + a build sequence), ADR-396 (its binding unit is named per-workspace + human-seat-scaled; the flat launch tiers stand as the N=1 case of seat-scaling), ADR-334 (its "autonomy IS the pricing axis" is retired — autonomy is the witness dial, not a price tier; trust-as-price is a deferred Rung-2 layer). Does NOT amend the ADR-396 numbers, the metering carve, or the balance mechanics — those are preserved.

---

## 1. Context — the pivot re-keyed the balance but not the billing

The 2026-06→07 band re-founded YARNNN as a **multi-principal commons**: the
substrate's binding unit moved `user_id → workspace_id` (ADR-373), N principals
(humans, their AIs, external LLMs) attribute into one judged workspace, and the
money followed — `balance_usd` re-keyed to `workspaces`, drawn by every
principal, spend stamped `workspace_id` (migrations 189/194/200). The Type-B
pricing model shipped (ADR-396): Free/Starter/Pro, an included allowance, a
metered balance, one meter (LLM judgment) and two gates (retention, connector
count).

But an audit of the live code against the ADRs (2026-07-08) found the re-key
went **halfway**. Three layers were decided together in ADR-391; only one was
built to the new binding unit:

| Layer | Decided (ADR-391) | Built | Binding unit in code |
|---|---|---|---|
| ① **Balance** (the money pool) | per-workspace | ✅ built | `workspaces.balance_usd`; `get_effective_balance(p_workspace_id)`; `execution_events.workspace_id` |
| ② **Allocation** (`_budget.yaml` envelope) | per-principal | ❌ **not built** | one file per workspace, read `.eq("user_id", …)` — `budget.py:128`; the per-principal file is *"GRANT SIDECAR — reserved, not yet shipped"* (`workspace_paths.py:102`, zero readers) |
| ③ **Metering** (attributed spend) | per-principal | ⚠️ **column-only** | `execution_events.principal_id` exists (migration 192) but **no gate/rollup consumes it** — it defaults to `user_id` at insert (`telemetry.py:289`) and spend is summed by `workspace_id` or `user_id`, never `principal_id` |

And a **fourth seam the ADRs never named**: every billing *route* keys on
`.eq("owner_id", auth.user_id)` (`subscription.py:206/229/311`). The balance is
a workspace commons, but **the right to fund it is an owner-only privilege** — a
member cannot subscribe, top up, view, or manage the tier of the commons they
draw from. `scope_manifest.yaml:31` declares `workspaces` (balance + tier)
**content-scoped (per-workspace)**, yet the account-scope definition claims
"billing **identity**" with no account-scoped billing store to hold it. The
manifest resolves the tension by fiat; the code contradicts it.

Two questions fell out, and they were tangled:
- **Who pays?** (the billing unit — per-user or per-workspace?)
- **Who spends what, and is it gated per-actor?** (metering + allocation)

The operator also observed, correctly, that the **"Autonomy" framing is now
wrong**: once the system agent (Freddie) is a stakeless Rung-1 steward
(reversible substrate, no consequential external write — ADR-380/381), the
autonomy dial no longer governs *capital authority*. It is a per-actor
approval-gating mechanism, and ADR-405 already reframed it as such — but the
surface still speaks the old language.

This ADR settles all of it.

## 2. The root decision — the workspace is the billing unit

**The billing unit is the workspace, not the user. Human seats scale the tier;
the account is free.**

This is not a Notion/Slack copy (though it converges with their model). It is
**forced by YARNNN's own service model**:

1. **You bill what accumulates value. Value accumulates in the workspace.**
   ESSENCE v15: YARNNN is "the system of record where human and AI work
   settles" — the moat is the workspace commons, keyed by `workspace_id`. The
   human *account* carries no accumulated value (auth + identity + theme;
   `scope_manifest` already classifies it free-scope). Pricing the user would be
   pricing the wrong noun. The billing axis and the value axis must name the
   same thing — and the value axis is the workspace.

2. **The balance is already a shared workspace pool, and that is correct.** The
   audit confirms Layer ① is built right: one `balance_usd` per workspace, every
   principal draws it, spend stamps `workspace_id`. That *is* the commons. The
   operator's worry — "shouldn't spend be per-actor?" — is a **metering**
   concern (who spent what), not a **billing-unit** concern (who pays). Answer:
   one shared pool, every draw attributed to the acting principal. Two
   questions, two clean answers — the wallet is not sharded.

3. **The multi-workspace case only stays sane under per-workspace.** A human in
   three workspaces: under per-user billing, one plan straddles three commons
   with different owners, balances, and tiers — with no clean answer to "which
   workspace's spend counts against my personal allowance?" Under per-workspace,
   it is trivial and already how the code behaves (contextvar / `X-Workspace-Id`
   routes a member's spend to the right pool — `supabase.py:368`,
   `workspace_context.py:60`): **the same human is a separately-funded seat in
   each workspace, funded by that workspace.** Identity is global (one login);
   cost is local to each commons.

4. **Autonomy confirms the direction.** Once autonomy is the witness dial
   (ADR-405, §4 below) and not capital authority, there is nothing
   "operational" left to price at the user level. The economically weighted
   things — accumulated substrate + metered LLM judgment — are both
   workspace-scoped. Pricing axis and value axis agree.

**The answer to "what IS shared workspace pricing?"**: the workspace is the
billing unit; it pays for its principals; the same human in two workspaces is
two separately-billed seats; the account is free.

## 3. The three decisions that follow

### D1 — Billing authority is a grant, not an owner-hardcode

The seam the audit named — members are billing-invisible — is closed by
treating **the right to fund the commons as a grant scope**, owner-default,
extendable to co-owners/admins. This is decoupled from **who may spend** (any
member with a write grant draws the pool). "Who may fund/subscribe" is a grant,
exactly like "who may write where" (ADR-373) and "when does an act bind"
(ADR-405) — **authority is a grant, never a species or a role-enum**. This keeps
billing coherent with the whole permission model and fixes the
member-billing-invisible constraint without making every member a payer.

*(Today: `subscription.py` routes key `.eq("owner_id", …)`. The build re-points
them to a billing-authority grant check — owner holds it by default; the grant
is extensible. Phase 3 below.)*

### D2 — Human seats scale the tier; AI principals add free but meter

The subscription tier scales with **human** seats (the team). **AI principals
(foreign-LLMs, A3 agents) cost nothing to *add*** — but their LLM spend draws
the metered balance. This is the YARNNN-specific twist away from Notion's
strict per-human-seat model, and it is **required to preserve ADR-396's "one
meter, never double-charge"**: an AI connection's cost is already captured as
metered LLM invocations against the balance; a per-AI-connection seat fee would
double-charge it. So:

- **Tier price** scales with human principal count (owner + members).
- **AI principals** (`role ∈ {foreign-llm, a2a, own-agent}`) add free; their
  spend meters the shared balance like any other principal's.

The ADR-396 flat launch tiers (Free/Starter/Pro) stand as the **N=1 case** of
seat-scaling (one human seat). Seat-scaling is the growth axis; whether it
activates at launch or is staged is an ADR-396-numbers question, not a
binding-unit question — the *shape* is decided here, the *when* rides the
first-customer evidence ADR-396 already defers to.

### D3 — Metering is per-principal-attributed over one shared pool

The `principal_id` column (migration 192) gets its consumer. Every draw on the
balance is attributed to the acting principal, and "who spent what" becomes a
live rollup over `execution_events` grouped by `principal_id` — **not** a
sharded wallet. The pool stays one workspace balance (D-root); the *ledger*
answers the attribution question. This is ADR-391 Layer ③, built at last.

Per-principal **allocation caps** (ADR-391 Layer ②, the reserved
`agents/{slug}/_budget.yaml` sidecar) are a *separate* capability from
attribution: attribution ("who spent what") is needed now for legibility +
the multi-principal commons to be honest; allocation ("cap what this principal
may spend") is needed only when a workspace wants to bound a specific
principal's draw (chiefly A3 agents). Attribution ships first (Phase 1);
allocation is scoped but sequenced after A3-agent runtime (Phase 4), because
its first real consumer is a persona agent the owner wants to bound.

## 4. The autonomy reframe — the witness dial, settled

The "Autonomy" surface is **the per-principal witness dial** (ADR-405 D2): it
governs *when an act binds* — before-witness (the proposal queue, the human sees
before it lands) vs after-witness (it binds and notifies). It does **not**
govern capital authority; a Rung-1 steward has no consequential external write
to gate (ADR-380 D3 — "the autonomy harness is degenerate on Freddie"). The
mechanics are already correct (`permission.py`); this ADR **settles the
vocabulary**: the surface stops saying "how much YARNNN/Freddie decides" (an
operation-authority frame that no longer fits) and says what it does — **who
witnesses which acts before they bind**.

Two consequences:
- **The dial is per-`(principal × act-class)`**, not one global "operation
  autonomy" (ADR-405 D2). Freddie has one; each A3 agent will have one; a member
  binds immediately (their acts are their own — ADR-405/408). The
  Workspace-Settings "Autonomy" pane is *Freddie's* witness dial, and should be
  named as such (or relocated per the deferred UserMenu-scope discourse).
- **Metering is orthogonal to witness.** Every principal's spend meters the
  balance regardless of its witness setting. Witness gates *binding*; metering
  gates *spending*. The two dials that today sit bundled under "Freddie →
  Budget/Autonomy" are two orthogonal per-actor properties (witness-timing +
  spend-metering) that were fused under a workspace-scoped "operation" frame
  that no longer fits. This ADR un-fuses them conceptually; the surface
  un-fusing is the deferred UserMenu-scope discourse's job.

**ADR-334 correction**: its thesis — "autonomy IS the pricing axis" (trust-tiered
seats $149/$299/$499) — is retired as the pricing model. Autonomy is the witness
dial, not a price tier. Trust-as-price may return as an *optional Rung-2 layer*
when A3 agents take consequential action (a workspace paying more to let an
agent bind without witness), but that is downstream of A3 runtime and is not the
launch model. ADR-396's Type-B tier (allowance + metered balance) is the model.

## 5. A3-agent billing — confirmed deferrable

An Altitude-3 persona agent (ADR-382, deferred) is **just another principal that
draws the workspace pool**, its spend attributed via `principal_id` (D3), its
draw optionally bounded by a per-principal allocation cap (D3/Phase 4). The
**workspace's billing authority (D1) is accountable** because it is the
workspace's balance being spent. No new billing primitive is required for A3;
the model here extends to it without amendment. Confirmed deferred to A3
runtime.

## 6. What this does NOT change

- **The ADR-396 metering carve** (one meter = LLM judgment; free = substrate
  writes / perception sync / recall+trace reads / embedding COGS; gates =
  retention + connector count). Untouched.
- **The ADR-396 launch numbers** (Free/Starter/Pro, allowances, retention).
  Untouched — they are the N=1 seat-scaling case.
- **The balance mechanics** (allowance-then-balance draw, expire-allowance/
  survive-topups, hard-stop, dynamic top-ups). Untouched — Layer ① is correct.
- **No new credit currency** (ADR-396 invariant preserved — overage is a balance
  top-up, one ledger).
- **The double-charge invariant** (ADR-396 — one `execution_events` ledger,
  every LLM call charged exactly once). D2's "AI adds free" exists precisely to
  *protect* this invariant.

## 7. The three seams as phases (implementation — NOT this commit)

Each phase is its own commit with its own gate, per the ADR-391 doc-first
pattern. Ordered by dependency and by launch value.

- **Phase 1 — Per-principal metering attribution (D3, the legibility unlock).**
  Wire a consumer for `execution_events.principal_id`: a "who spent what"
  rollup over the shared pool (an admin/legibility read; the balance gate is
  unchanged — it stays workspace-summed). Ensure `principal_id` is stamped with
  the *acting* principal (not defaulted to `user_id`) on the member + foreign-LLM
  paths. Gate: attribution is correct at N>1. **Value: makes the multi-principal
  commons honest — "who spent what" gets a real answer.**

- **Phase 2 — Billing authority as a grant (D1, the member seam).** Re-point the
  owner-keyed billing routes (`subscription.py:206/229/311`) to a
  billing-authority grant check (owner-default; grant extensible). Add the
  billing-authority scope to `principal_grants`. Members without it stay
  spend-enabled but fund-disabled; the grant can be extended. Gate: a granted
  co-owner can subscribe/top-up; a plain member cannot; owner byte-identical.
  **Value: closes the member-billing-invisible incoherence the manifest named.**

- **Phase 3 — Human-seat tier scaling (D2, the growth axis).** Make the tier
  price scale with human principal count; AI principals add free. Reconcile with
  the ADR-396 launch numbers (the flat tiers become the 1-seat row of a scale).
  Gate: adding a human member changes the tier math; adding an AI principal does
  not. **Value: the team-growth revenue axis.** *(Sequencing note: may follow
  first paying customers per ADR-396's numbers-deferral — the shape is decided,
  the activation rides evidence.)*

- **Phase 4 — Per-principal allocation caps (ADR-391 Layer ②, deferred).** Build
  the reserved `agents/{slug}/_budget.yaml` sidecar into a live allocation cap on
  a principal's draw of the shared pool. Sequenced after A3-agent runtime — its
  first real consumer is an owner wanting to bound a persona agent's spend.
  Also fix the **owner-scoped envelope gate** the audit found (`budget.py`'s
  `window_spend`/`seconds_since_last_fire` key raw `user_id` with no workspace
  resolution — the wake-envelope allocation check diverges from the
  workspace-scoped balance hard-stop at N>1). Gate: the two cost gates bind to
  the same unit. **Value: bounded autonomous agents; the two-gate divergence
  closed.**

## 8. The canon cascade (owed, not in this commit)

- **`scope_manifest.yaml`**: `workspaces` (balance + tier) stays content-scoped
  (per-workspace) — this ADR ratifies that, resolving the tension by *keeping*
  the manifest's content classification and fixing the *routes* (D1/Phase 2) to
  match, rather than moving billing to account scope. The account scope's
  "billing identity" note is corrected: the human's billing *identity* (their
  auth) is account-scoped; the billing *unit* (what pays) is the workspace. Add
  the billing-authority grant scope to the grant vocabulary (Phase 2).
- **GLOSSARY**: add "Billing unit" (= the workspace), "Billing authority" (= a
  grant), and correct any "Autonomy" entry that frames it as capital authority →
  the witness dial (per-principal). Fold the ADR-334 "autonomy-as-pricing-axis"
  retirement into its entry.
- **ESSENCE / FOUNDATIONS**: no axiom change — this ADR is a Purpose/Identity
  settling that the existing axioms already permit (the workspace is the binding
  unit; authority is a grant; the witness dial is Trigger-layer). A one-line
  note that the billing unit = the value unit = the workspace may be worth
  adding to the ESSENCE moat section, but it is derivable, not new.

## 9. Open questions (deliberately not decided here)

- **Co-ownership vs billing-authority-grant**: D1 makes billing a grant; whether
  YARNNN also introduces a first-class "co-owner" role (vs just granting billing
  authority to a member) is a membership-model question for a later ADR.
- **The UserMenu scope surface**: the operator flagged that Budget/Autonomy's
  *surface home* (Workspace Settings → System Agent) and the UserMenu's
  scope-mixing want a separate discourse. This ADR decides the *concepts*
  (billing unit, witness dial, metering); *where each control renders* (which
  pane, which menu, which scope band) is that deferred surface discourse's job.
  This ADR deliberately does not move any pane.
- **Seat-scaling activation timing** (Phase 3): shape decided, activation rides
  first-customer evidence (ADR-396's standing numbers-deferral).
