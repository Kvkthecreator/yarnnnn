# Budget, Balance, and Pricing after Freddie — the three-layer cost model for a multi-principal workspace

> **Status**: Analysis / conceptual framing (Hat A — system canon, doc-first). **Ratified by [ADR-391](../adr/ADR-391-budget-balance-and-the-three-layer-cost-model.md)** (2026-06-30) — this doc is the derivation; ADR-391 is the decision record. **No code in either.** This derives the *target* cost/pricing setup that the Freddie shift (ADR-380/381/383) + the multi-principal direction (ADR-373/378) call for, and names what changes from today.
> **Date**: 2026-06-30
> **Authors**: KVK (operator) + Claude (collaborator)
> **Discourse base**: live screenshot-walk of `?agents.agent=freddie` (Freddie detail → GRANT → Budget), 2026-06-30. Operator read: *"we now have the substrate layer and on top of it the Freddie system agent — a shift from the legacy knit reviewer+substrate model. Should budget be both in architecture and the FE surface; is budget a workspace concept; how to re-reflect it for both the workspace and Freddie? Shouldn't budget and actual spending be directly correlated — Freddie's spend deducts the workspace balance? Given the vision (multi-user, multi-principal incl. AI agents, 3rd-party connectors some mechanical/no-LLM), we need a pricing model that accommodates this."*
> **Builds on**: [ADR-172](../adr/ADR-172-usage-first-billing.md) (balance as single gate, pay-as-you-go) · [ADR-291](../adr/ADR-291-unified-cost-ledger.md) (`execution_events` = the one cost ledger) · [ADR-327](../adr/ADR-327-budget-and-the-self-improving-loop.md) (`_budget.yaml` = the self-governed attention envelope) · [ADR-334](../adr/ADR-334-per-operation-pricing.md) (seat pricing — **deferred**) · [ADR-366](../adr/ADR-366-autonomy-mode-as-execution-breadth.md) (governance/ = the GRANT) · [ADR-373](../adr/ADR-373-multi-principal-workspace-and-the-re-key.md) (the `user_id→workspace_id` re-key + principals) · [ADR-380](../adr/ADR-380-the-activation-ladder-and-the-judgment-deferral-line.md) (the activation ladder — Freddie is Rung-1, reversible, stakeless) · [ADR-383](../adr/ADR-383-the-consistent-agent-framework-and-mandate-as-purpose.md) (`_budget.yaml` is agent-universal — one per agent) · [ADR-387](../adr/ADR-387-agent-governance-on-the-agent-pane.md) (Budget renders on Freddie's GRANT pane).

---

## 1. The two things called "budget" today (the audit)

The codebase has **two separate cost systems** that casual speech conflates as "budget." Naming them is the prerequisite for everything below.

| | **`_budget.yaml`** (the attention envelope) | **`balance_usd`** (the workspace balance) |
|---|---|---|
| What it is | A self-governed dollar **spend envelope over a window** the agent allocates its wakes within (ADR-327) | **Real money** — grants + top-ups; hard-stops all execution at zero (ADR-172/291) |
| Lives at | `governance/_budget.yaml` (`workspace_files`) | `workspaces.balance_usd` (DB column) |
| Read by | `services/budget.py::load_budget` + `window_spend` | `services/platform_limits.py::check_balance` + `get_effective_balance` |
| Keyed on | `user_id` (today) | `user_id`/workspace (today) |
| Who sets it | Operator only (Freddie locked out — `governance/` GRANT root, ADR-320/366) | Operator (top-ups / subscription) |
| Surfaced | Freddie's pane → **GRANT → Budget** (ADR-387) | Account → **Billing** |
| Gate behavior | Past envelope → **skip scheduled wakes**, warn-but-fire reactive (ADR-327 D4) | Past balance (zero) → **hard stop all LLM execution** (ADR-172) |

**They already share one ledger** — both read `execution_events.cost_usd` — but as **two gates summed two ways**: `window_spend()` over the budget window vs. `get_effective_balance` since last refill. The FE already states the relationship (`BudgetCard.tsx`: *"The balance that funds this envelope lives on your account"*) — but the model presents them as two unrelated dials when they are two readings of one spend stream.

**The operator's correction is right**: budget and spending *should* be directly correlated, and Freddie's spend *does* already deduct real money. What is wrong is conceptual under-statement, not the wiring. The fix is to name the correct relationship — which the multi-principal future forces anyway.

---

## 2. The error in the current frame, and why the multi-principal future forces the fix

Today there is **one principal per workspace** (the operator, via `user_id`) and **one agent** (Freddie). So `_budget.yaml` (per-agent, per ADR-383) and the workspace balance (per-user) *coincide* — the N=1 case hides the distinction. The current model is a frozen snapshot of N=1.

The vision (ADR-373/378) breaks N=1: a workspace becomes a **multi-principal commons** — the operator, human members, the operator's own agents, **persona-agents Freddie creates** (ADR-382), foreign LLMs over MCP, platform connectors (some **mechanical / no-LLM, $0 cost**). The moment a second spending principal exists, "the workspace's budget" and "this agent's budget" are no longer the same thing, and "who spent the money" stops being answerable by a per-`user_id` sum.

So the cost model must answer three questions that N=1 let us blur into one:

1. **Is there money?** (balance)
2. **Who/what may spend how much of it?** (allocation)
3. **What was actually spent, by whom?** (metering)

---

## 3. The target frame — three layers, cleanly separated

The fix is to recognize that "budget" was doing two jobs and "balance" a third, and to bind each to its correct scope:

| Layer | Question | Binds to | Today | Target |
|---|---|---|---|---|
| **① Balance (the workspace balance)** | "Is there money?" | **The workspace** (the commons everyone draws) | `balance_usd` keyed per `user_id` | `balance_usd` on the **workspace** (the ADR-373 `user_id→workspace_id` re-key). One balance per workspace; every principal's spend deducts it. |
| **② Allocation (the envelopes)** | "Who/what may spend how much of the workspace balance?" | **Each principal** | One `_budget.yaml` per `user_id` | **Per-principal** allocation within the shared workspace balance (`_budget.yaml` is already "agent-universal" — one per agent, ADR-383). |
| **③ Metering (the ledger)** | "What was actually spent, by whom?" | **Each invocation, attributed to a principal** | `execution_events.cost_usd` summed per `user_id` | `execution_events` gains a `principal_id` → spend is *attributable*, not just summed. |

**The unifying claim**: *the balance is the workspace's; the envelopes are the principals'; the ledger attributes every dollar to a principal.* Budget and spend become directly correlated because they are **the same ledger read at two scopes** — balance-scope (workspace balance remaining across all principals) and principal-scope (this agent's allocation remaining). The operator's "shouldn't they be correlated" is satisfied structurally: there is one spend stream; the workspace balance and the envelopes are two windows onto it.

This is the multi-principal vision rendered as economics:
- A **workspace** holds **one balance**.
- Inside it, **N principals** each hold an **allocation** — "Freddie gets $X/mo of attention; the trader persona-agent $Y; a human teammate's chat draws $Z; this MCP connector is capped at $W."
- **Mechanical / no-LLM connectors cost $0 and simply don't draw** — already true (mechanical recurrences are out of budget scope, ADR-327 D4; mechanical foreign reads are unmetered, ADR-335). A "potentially mechanical or MCP with no LLM cost" connector falls out as a **free principal** with no special-casing.

### 3.1 What this means for the Freddie surface (the screenshot)

The placement you walked is **already correct for this model** and needs no FE change to be coherent:
- Budget on Freddie's **GRANT** pane = *Freddie's allocation* (the envelope it runs under, operator-set, Freddie-locked). Correct: it is a per-principal allocation, displayed where you think about that principal.
- When persona-agents arrive (Rung-2, ADR-382), **each gets its own allocation pane** — the `_budget.yaml`-is-agent-universal classification (ADR-383 §2) was already pointing here.
- The **workspace balance** is *not* an agent concern — it belongs in **Account → Billing**, exactly where it is. The FE's existing *"the balance that funds this envelope lives on your account"* footer is the correct seam; it just needs to become the *stated model*, not a footnote.

So the surface answer to *"how to re-reflect budget for both the workspace and Freddie"* is: **the balance reflects on the workspace/account (Billing); the allocation reflects on each principal's pane (Freddie's GRANT, and each future agent's).** Two different objects, two correct homes — not one concept shown twice.

---

## 4. Pricing — the priced layer sits ON TOP of the workspace balance (per-workspace subscription)

With the three layers separated, pricing derives cleanly and the "subscription vs seat vs pay-as-you-go" question dissolves — they operate at **different layers**, not as competing choices:

### 4.1 The floor is always pay-as-you-go (the workspace balance)

`balance_usd` is the metered floor, re-keyed to the workspace. It is what makes:
- a multi-principal workspace **fair** (everyone draws the same metered ledger at 2× cache-inclusive Anthropic cost),
- **no-LLM connectors free** (they don't draw),
- the model **scale to any number of principals** without a pricing renegotiation (more principals = more metered draw, the margin scales with it).

**Keep `balance_usd`; re-key it to the workspace** (the ADR-373 re-key already plans this). This is non-negotiable infrastructure and already exists. Hard-stop-at-zero, grants, top-ups all preserved.

### 4.2 The priced product is a per-workspace subscription (operator's decision, 2026-06-30)

On top of the workspace balance sits a **per-workspace subscription** — a flat plan per workspace, tiered by **scale/capability of the commons**, with metered balance usage drawn underneath. Chosen over per-principal seats and usage-only because it is **simplest for laymen** and **absorbs the multi-principal complexity into a tier, not per-seat math**:

```
WORKSPACE SUBSCRIPTION   $X/mo (flat, per workspace)
  tier gates:  scale of the commons — e.g. # principals / members,
               # connectors, the autonomy ceiling the workspace may run at
  └ everything inside draws the ONE shared workspace balance
  └ balance usage billed pay-as-you-go on top (2× metered)

Price  =  one workspace subscription tier  +  metered usage
Multi-principal  =  a higher tier, not more seats
```

**A layman reads it as**: *"$X/month for your workspace; usage on top."* Adding a teammate, an agent, or a connector is *"a bigger workspace tier,"* not a per-seat invoice. The trader persona-agent, the author persona-agent, three human members, two connectors — all live in one priced workspace, drawing one workspace balance.

### 4.3 The discipline this must honor (don't revive what ADR-172 deleted)

ADR-172 §3 already conceived subscription as **"optional auto-refill of the workspace balance — a commitment discount + predictability, not an access tier,"** and it **deliberately deleted capability gates** (task counts, source limits, message caps). The per-workspace subscription must not silently revive those. The honest tier axis is **scale of the commons** (how many principals / connectors / how much autonomy the workspace is entitled to run), priced because that scale is where real value concentrates in a multi-principal workspace — *not* a feature matrix bolted back on. The subscription is a **workspace-scoped commitment plan over the workspace balance**, sized by the commons it governs.

### 4.4 Where the deferred seat model (ADR-334) lands

ADR-334's per-*operation* seats priced the **AUTONOMY dial** ($149/$299/$499). The Freddie shift partially invalidated its premise: on **Freddie (Rung-1)**, autonomy/mandate are **degenerate** — Freddie is a reversible steward that moves no capital (ADR-380 D3). So there is no consequential autonomy to price at Rung-1; seats only ever made sense at **Rung-2** (persona-agents that *act*). Under the per-workspace-subscription choice, **the autonomy ceiling becomes a tier gate of the workspace plan** (how much delegation the commons may run), not a separate per-seat price. ADR-334 stays deferred; if a per-principal seat axis ever re-opens, it would be *within* a workspace subscription (a higher tier unlocks more/higher-autonomy acting agents), not a parallel pricing system.

---

## 5. What changes from today (the delta, named — not built here)

Doc-first; this names the target. Each line is a future ADR/implementation decision, not a commitment in this doc:

1. **Re-key the balance to the workspace** (ADR-373 Phase-1 re-key; `balance_usd` → `workspaces`). *Prerequisite — already planned.*
2. **Attribute the ledger** — add `principal_id` to `execution_events` so spend is per-principal, not per-`user_id` sum. *(Enables both per-principal allocation read-out and per-principal billing legibility.)*
3. **Generalize `_budget.yaml` to per-principal allocation** — today one file per `user_id`; target one allocation per principal (the agent-universal classification, ADR-383, made real when N>1). At N=1 this is byte-identical to today (Freddie's file = the workspace's only allocation).
4. **State the balance↔allocation relationship in the model + UI** — the workspace balance on Account/Billing, the allocation on each principal's GRANT pane; promote the existing `BudgetCard` footer from footnote to stated seam.
5. **The per-workspace subscription layer** — a workspace-scoped commitment plan over the workspace balance, tiered by commons-scale; LS products keyed `(workspace_id, plan_tier)`; honoring the ADR-172 "no capability-gate revival" discipline. *Gated behind real external demand, like ADR-334 — do not wire checkout speculatively.*

**N=1 safety**: every change above is byte-identical for a solo operator with one Freddie and no members/agents. The payoff is **forward-looking** — it is the cost model the multi-principal commons needs, built so the N=1 case is the trivial instance of it (the same discipline as the ADR-373 re-key: the 1:1 world is the N=1 case).

---

## 6. The one-line answers to the operator's questions

- **"Should budget be in architecture AND the FE surface?"** — Yes; it already is, and the Freddie GRANT-pane placement is correct (it is the principal's *allocation*).
- **"Is budget a workspace concept?"** — The **workspace balance** is the workspace's; the **allocation** (`_budget.yaml`) is the *principal's*. Two objects. N=1 makes them look like one.
- **"How to re-reflect for both workspace and Freddie?"** — Workspace balance on Account/Billing; allocation on each principal's pane. Not one concept shown twice — two correct homes.
- **"Shouldn't budget and spending be correlated — Freddie's spend deducts the workspace balance?"** — Yes, and it does (shared `execution_events` ledger). The target makes it *structurally* one spend stream read at two scopes: workspace-balance-remaining and allocation-remaining.
- **"What pricing model accommodates multi-principal + connectors?"** — **Pay-as-you-go workspace balance (the floor, re-keyed to the workspace) + a per-workspace subscription on top (tiered by commons-scale).** Connectors with no LLM cost are free principals. More principals = a higher workspace tier, not a per-seat invoice. Layman framing: *"$X/mo for your workspace, usage on top."*
