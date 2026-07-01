# ADR-391 — Budget, Balance, and the Three-Layer Cost Model: per-principal allocation over a per-workspace balance, with a per-workspace subscription on top

> **Status**: **Accepted (cost ARCHITECTURE stands; pricing D4/D6 SUPERSEDED by ADR-396)** — 2026-06-30. Ratifies the *target* cost/pricing **architecture** the Freddie shift (ADR-380/381/383) + the multi-principal direction (ADR-373/378) call for. The **architecture** (D1–D3 — three layers: balance=workspace, allocation=per-principal `_budget.yaml`, metering=`execution_events` + `principal_id`) is sound, load-bearing, and the substrate ADR-396 rides on. The **pricing SHAPE** (D4/D6 — a per-workspace subscription tiered on *commons-scale headcount*) is **superseded by [ADR-396](ADR-396-the-pricing-model-type-b-subscription-over-the-metered-balance.md), Implemented 2026-07-01**: the tier axis is not commons-scale headcount but the ADR-396 meter/gate carve (LLM-invocation meter + retention/connector gates). Every change is byte-identical at N=1.
> **⚠️ Pricing-model note (2026-06-30, same day)**: the cost **architecture** below (D1–D3 — three layers, principal-attributed ledger) is **sound and stands.** But the *pricing* decisions (**D4/D6 per-workspace subscription on commons-scale**, and **D2 "mechanical = free principal"**) are **REOPENED** by [`../analysis/value-based-pricing-the-action-surface-matrix-2026-06-30.md`](../analysis/value-based-pricing-the-action-surface-matrix-2026-06-30.md). That analysis found D2 conflated *our cost* with *our price* (mechanical/substrate actions cost ~$0 but are HIGH-value — the moat — and are currently unpriced; the interop face is served at a small un-recovered loss). Its pre-assessment recommendation is a **value-derived simplified model** — *"free to remember, pay to operate"*: a flat workspace base on the durable substrate (free unlimited recall/interop) + metered operations on top. This is the *same two-object shape* as D4 (base + metered) but priced on **substrate value**, not **commons-scale**. **Do not treat D4/D6's commons-scale axis as the settled price** — it is one candidate; the value analysis is the live derivation. A successor ADR amends D2/D4/D6 once a direction is chosen against evidence.
> **Date**: 2026-06-30
> **Authors**: KVK (operator) + Claude (collaborator)
> **Hat**: A (system canon — real-operator-facing)
> **Discourse base**: live screenshot-walk of `?agents.agent=freddie` → GRANT → Budget (2026-06-30) + [`../analysis/budget-balance-and-pricing-after-freddie-2026-06-30.md`](../analysis/budget-balance-and-pricing-after-freddie-2026-06-30.md) (the full derivation; this ADR is its ratification). Operator decisions captured in-thread: (1) budget↔spend must be directly correlated; (2) the priced axis is a **per-workspace subscription**; (3) the live term is **"balance"** (not "funds").

**Amends:**
- [ADR-172](ADR-172-usage-first-billing.md) (balance as single gate) — **re-scoped, not replaced**: `balance_usd` becomes the **per-workspace** balance (Layer ①) and the metered floor beneath the subscription. Hard-stop-at-zero, grants, top-ups, `get_effective_balance`, "subscription = refill + predictability, not an access tier", and the deleted capability gates all **preserved**.
- [ADR-291](ADR-291-unified-cost-ledger.md) — the `execution_events` ledger gains a `principal_id` attribution column (Layer ③). Reader behavior unchanged; the column makes spend *attributable* rather than only `user_id`-summed. (Schema add; no semantic change to existing readers, which sum the same rows.)
- [ADR-327](ADR-327-budget-and-the-self-improving-loop.md) — `_budget.yaml` (the attention envelope) generalizes from **one-per-`user_id`** to **one-per-principal** (Layer ②). The self-governed-envelope semantics, the wake-gate behavior (D3/D4), the governance-lock (operator-set, agent-locked), and the calibration loop (D6) are all **preserved**; only the binding unit widens.
- [ADR-334](ADR-334-per-operation-pricing.md) — the deferred per-*operation* seat model is **subsumed**: the AUTONOMY ceiling it priced becomes a **tier gate of the per-workspace subscription**, not a parallel seat price. ADR-334 stays Deferred; if a per-principal seat axis ever re-opens, it lives *within* a workspace subscription (a higher tier unlocks more / higher-autonomy acting agents), not as a second pricing system.

**Builds on / preserves:** [ADR-373](ADR-373-multi-principal-workspace-and-the-re-key.md) (the `user_id→workspace_id` re-key — Layer ① rides it; principals are the allocation unit) · [ADR-378](ADR-378-the-workspace-as-the-outermost-unit.md) (the workspace is the outermost unit — so the balance binds there) · [ADR-380](ADR-380-the-activation-ladder-and-the-judgment-deferral-line.md) (Rung-1 Freddie is stakeless — why autonomy can't be priced at Rung-1, §5) · [ADR-383](ADR-383-the-consistent-agent-framework-and-mandate-as-purpose.md) (`_budget.yaml` is agent-universal — one per agent; Layer ② is the realization of that classification at N>1) · [ADR-387](ADR-387-agent-governance-on-the-agent-pane.md) (Budget renders on Freddie's GRANT pane — confirmed correct, §4) · [ADR-366](ADR-366-autonomy-mode-as-execution-breadth.md) (`governance/` = the GRANT; the allocation is operator-set, agent-locked).

**Dimensional classification** (Axiom 0): **Substrate** (Axiom 1 — the cost ledger + the per-principal envelope file) over **Identity** (Axiom 2 — spend attributes to a principal; allocation binds to a principal) + **Channel** (Axiom 6 — the balance reflects on Billing, the allocation on each principal's pane).

---

## 1. The problem — two systems called "budget", a frozen N=1 snapshot

The codebase has **two separate cost systems** that casual speech conflates as "budget":

| | **`_budget.yaml`** (the attention envelope) | **`balance_usd`** (the workspace balance) |
|---|---|---|
| What it is | A self-governed dollar **spend envelope over a window** the agent allocates its wakes within (ADR-327) | **Real money** — grants + top-ups; hard-stops all execution at zero (ADR-172/291) |
| Lives at | `governance/_budget.yaml` | `workspaces.balance_usd` (DB column) |
| Read by | `services/budget.py::load_budget` + `window_spend` | `services/platform_limits.py::check_balance` + `get_effective_balance` |
| Who sets it | Operator only (agent locked — `governance/` GRANT root, ADR-320/366) | Operator (top-ups / subscription) |
| Surfaced | Freddie's pane → **GRANT → Budget** (ADR-387) | Account → **Billing** |
| Gate behavior | Past envelope → skip scheduled wakes, warn-but-fire reactive (ADR-327 D4) | Past balance (zero) → hard-stop all LLM execution (ADR-172) |

**They already share one ledger** (`execution_events.cost_usd`) but as **two gates summed two ways** (`window_spend` over the budget window vs. `get_effective_balance` since last refill), both keyed on `user_id`. The FE already states the relationship (`BudgetCard.tsx`: *"The balance that funds this envelope lives on your account"*) — so Freddie's spend already deducts real money. The error is **conceptual under-statement**, not wiring.

The root cause: today there is **one principal** (`user_id`) and **one agent** (Freddie) per workspace, so `_budget.yaml` (per-agent, ADR-383) and the balance (per-user) *coincide*. The current model is a frozen snapshot of N=1. The multi-principal future (ADR-373/378 — human members, the operator's agents, persona-agents Freddie creates per ADR-382, foreign LLMs over MCP, platform connectors some mechanical/$0) breaks N=1 and forces three questions N=1 let us blur into one:

1. **Is there money?** (balance)
2. **Who/what may spend how much of it?** (allocation)
3. **What was actually spent, by whom?** (metering)

---

## 2. Decisions — the three-layer model

### D1 — Three layers, each bound to its correct scope

| Layer | Question | Binds to | Today | Target |
|---|---|---|---|---|
| **① Balance** | "Is there money?" | **The workspace** | `balance_usd` per `user_id` | `balance_usd` on the **workspace** (rides the ADR-373 re-key). One balance per workspace; every principal's spend deducts it. |
| **② Allocation** | "Who/what may spend how much?" | **Each principal** | one `_budget.yaml` per `user_id` | **per-principal** allocation within the shared balance (`_budget.yaml` is agent-universal, ADR-383). |
| **③ Metering** | "What was spent, by whom?" | **Each invocation → a principal** | `execution_events.cost_usd` summed per `user_id` | `execution_events` + `principal_id` → attributed spend. |

**The unifying claim**: *the balance is the workspace's; the envelopes are the principals'; the ledger attributes every dollar to a principal.* Budget and spend are directly correlated because they are **the same ledger read at two scopes** — balance-scope (workspace balance remaining across all principals) and principal-scope (this agent's allocation remaining). There is one spend stream; the balance and the envelopes are two windows onto it. This is the operator's "shouldn't they be correlated" satisfied *structurally*.

### D2 — Mechanical / no-LLM principals are free, with no special-casing

A connector that is mechanical or MCP-with-no-LLM-cost **costs $0 and simply does not draw** — already true (mechanical recurrences are out of budget scope, ADR-327 D4; mechanical foreign reads are unmetered, ADR-335). It falls out of the model as a **free principal** with an allocation it never touches. No carve-out, no special path: zero cost = zero draw = free, by construction.

### D3 — "Budget" is a per-principal allocation; "balance" is the workspace's money; they reflect in two homes

The surface answer to *"how to re-reflect budget for both the workspace and Freddie"*:
- **The workspace balance** (Layer ①) reflects on **Account → Billing** — it is not an agent concern. (Where it already is.)
- **The allocation** (Layer ②) reflects on **each principal's pane** — Freddie's **GRANT → Budget** (ADR-387, confirmed correct), and each future persona-agent's own GRANT pane.

Two different objects, two correct homes — **not one concept shown twice.** The existing `BudgetCard` footer (*"the balance that funds this envelope lives on your account"*) is the correct seam; it is promoted from footnote to *stated model*.

### D4 — The priced product is a per-workspace subscription over the balance

Pricing derives cleanly once the layers are separated — "subscription vs seat vs pay-as-you-go" dissolves because they operate at **different layers**:

- **The floor is always pay-as-you-go** — `balance_usd`, re-keyed to the workspace (Layer ①). This is what makes a multi-principal workspace fair (everyone draws the same metered ledger at 2× cache-inclusive Anthropic cost), makes no-LLM connectors free, and scales to any number of principals without a pricing renegotiation. **Non-negotiable infrastructure; already exists.**
- **The priced product sits on top: a per-workspace subscription** — a flat plan per workspace, tiered by **scale of the commons** (# principals/members, # connectors, the autonomy ceiling the workspace may run at), with metered balance usage drawn underneath.

```
WORKSPACE SUBSCRIPTION   $X/mo (flat, per workspace)
  tier gates:  commons scale — # principals / connectors / autonomy ceiling
  └ everything inside draws the ONE shared workspace balance
  └ balance usage billed pay-as-you-go on top (2× metered)

Price  =  one workspace subscription tier  +  metered usage
Multi-principal  =  a higher tier, not more seats
```

A layman reads it as *"$X/month for your workspace; usage on top."* Adding a teammate, an agent, or a connector is *"a bigger workspace tier,"* not a per-seat invoice.

### D5 — The discipline: no capability-gate revival

ADR-172 §3 already conceived subscription as *"optional auto-refill — a commitment discount + predictability, not an access tier,"* and **deliberately deleted** capability gates (task counts, source limits, message caps). The per-workspace subscription **must not silently revive those.** The honest tier axis is **commons-scale** (how many principals/connectors/how much autonomy the workspace is entitled to run) — priced because that scale is where value concentrates in a multi-principal workspace — *not* a feature matrix bolted back on. The subscription is a **workspace-scoped commitment plan over the balance**, sized by the commons it governs.

### D6 — The autonomy axis is a subscription tier gate, not a seat price (ADR-334 subsumed)

ADR-334's per-*operation* seats priced the **AUTONOMY dial** ($149/$299/$499). The Freddie shift partially invalidated its premise: at **Rung-1 (Freddie)**, autonomy/mandate are **degenerate** — Freddie is a reversible steward that moves no capital (ADR-380 D3). There is no consequential autonomy to price at Rung-1; seats only ever made sense at **Rung-2** (persona-agents that *act*, ADR-382). Under D4, the autonomy ceiling becomes a **tier gate of the workspace subscription** (how much delegation the commons may run). ADR-334 stays Deferred; a per-principal seat axis, if reopened, lives *within* a workspace subscription, not as a parallel system.

---

## 3. The N=1 safety invariant

Every change is **byte-identical for a solo operator** with one Freddie and no members/agents:
- Layer ① at N=1 = today's per-user balance (the re-key's 1:1 backfill, ADR-373).
- Layer ② at N=1 = Freddie's `_budget.yaml` *is* the workspace's only allocation.
- Layer ③ at N=1 = every `execution_events` row attributes to the one principal; the per-`user_id` sum and the per-`principal_id` sum are the same number.

The payoff is **forward-looking** — this is the cost model the multi-principal commons needs, built so the N=1 case is its trivial instance (the same discipline as the ADR-373 re-key: the 1:1 world is the N=1 case).

---

## 4. What this ADR deliberately does NOT do

- **Does not change any gate behavior at N=1.** The wake-envelope gate (ADR-327 D3/D4) and the balance hard-stop (ADR-172) behave identically; only their binding units generalize.
- **Does not wire the subscription / checkout.** Demand-gated (the ADR-334 discipline): no LS products, no `/pricing` rewrite, no `seatCheckout` un-nulling until real external demand proves the axis.
- **Does not revive ADR-172's deleted capability gates** (D5).
- **Does not touch the autonomy mechanism** (`_autonomy.yaml`, the witness dial, ADR-307/345/366). Budget gates cost/when; autonomy gates what-binds — orthogonal (ADR-327 §3).
- **Does not build persona-agent seats** (ADR-382 — this ADR gives their allocation its home, but lifecycle/trust is ADR-382's).
- **Does not change `_budget.yaml`'s self-governance** — it stays operator-set + agent-locked (the GRANT, ADR-366); per-principal means *one envelope per principal*, not *the principal sets its own*.

---

## 5. Implementation scope (downstream — NOT in this commit)

Doc-first; the code lands after, each in its own commit, each green + render-parity (CLAUDE.md §5). Sequenced so the prerequisite (the re-key) leads:

1. **Re-key the balance to the workspace** — `balance_usd` → `workspaces` (ADR-373 Phase-1; prerequisite, already planned). *Layer ①.*
2. **Attribute the ledger** — add `principal_id` to `execution_events`; existing readers unchanged (same rows summed). *Layer ③.*
3. **Generalize `_budget.yaml` to per-principal** — one allocation per principal; byte-identical at N=1. *Layer ②.*
4. **State the balance↔allocation relationship in the model + UI** — balance on Account/Billing, allocation on each principal's GRANT pane; promote the `BudgetCard` footer to stated seam. *Channel.*
5. **The per-workspace subscription layer** — workspace-scoped commitment plan over the balance; LS products keyed `(workspace_id, plan_tier)`; D5 discipline. **Demand-gated — do not wire checkout speculatively.**

**Doc cascade** (accompanies the corresponding code commit, or lands now as canon): `docs/monetization/STRATEGY.md` (the three-layer model + the per-workspace-subscription direction; ADR-334 banner cross-ref), GLOSSARY (Balance / Allocation / Workspace subscription entries; "budget" disambiguated into the two systems), CLAUDE.md ADR index, the analysis doc → referenced as the derivation.

---

## 6. Rejected alternatives

- **Per-principal seats** (ADR-334 re-cut to per-principal). Rejected as the *headline* axis (kept as a within-tier future, D6): per-seat math is the wrong cognitive load for a layperson at a multi-principal workspace; "a bigger workspace" reads better than "another invoice line." Also premature on the desire axis (ADR-334's own demotion logic).
- **Usage-only (no priced layer).** Rejected as the *committed* model (it remains the live floor): margin on 2× metering alone underprices the value of the commons + judgment the workspace concentrates; the subscription is where commons-scale value is captured. (If the subscription axis fails against real demand, usage-only is the fallback — same posture as ADR-334.)
- **Keep "budget" as one undifferentiated concept.** Rejected (§1) — it is two systems; the multi-principal future makes the conflation actively wrong (you cannot answer "who spent it" from a per-user sum).
- **Call Layer ① "funds" / "wallet".** Rejected (operator decision) — the live term is **balance** (`balance_usd`, "Balance & billing" in the FE). Canon uses **workspace balance**; "wallet" may appear only as an informal gloss.
