# Value-Based Pricing — modelling the full action surface, decoupled from our cost

> **Status**: Analysis / open exploration (Hat A). **Not ratified. Not a model — the work that produces a model.** This builds the action × channel × layer matrix the operator asked for (2026-06-30), values each cell by *what it's worth to the operator*, not *what it costs us*, and derives candidate price objects from where value concentrates. The output is candidates + the evidence, for the operator to choose from — numbers stay hypothesis ahead of customers.
> **Date**: 2026-06-30
> **Authors**: KVK (operator) + Claude (collaborator)
> **Owes-from**: [ADR-391](../adr/ADR-391-budget-balance-and-the-three-layer-cost-model.md) (the cost *architecture* — three layers; this doc questions ADR-391 D2 "mechanical = free" and D4/D6 "commons-scale subscription", which rested on an unexamined cost-equals-price assumption) + the discourse that produced it.
> **Operator framing (verbatim, 2026-06-30)**: *"even within the substrate layer actions, those types, shouldn't they be modeled in? close or near-0 isn't a good way to set up our pricing model. separately, I'd argue if that is our margin where we can make money as a company — given many other companies charge per API or alike, not that we have to follow that — and since we probably only charge right now for LLM calls."*

---

## 1. The two findings that reframe the whole question

### Finding 1 — We charge for exactly one thing, and it is the commodity.

Today's only revenue mechanism is **`balance_usd` debited by LLM `cost_usd` at 2× Anthropic** (ADR-172/291). The debit sites are *all* LLM callers (STRATEGY.md "Substrate: `execution_events`" table): `addressed` (chat), reflection / proposal-arrival, `specialist:<role>`, `web-search`, `recurrence-prompt-inference`, `infer-workspace`, `infer-context:*`, `session-summary`. **Seven LLM callers. Zero non-LLM revenue.**

Every non-LLM line in COST-MODEL.md is `~$0` and **generates nothing**:
- Delivery (email/Slack/Notion) — `~$0`, not billed.
- Render (PDF/chart/pptx) — `~$0.005`, not billed as a line.
- Mechanical scheduling, mechanical sync, perception reads — `$0`, not billed.
- **Every substrate write** (place, derive-and-cite, attribute, the authored-substrate moat floor) — `$0`, not billed.

So our margin (COST-MODEL: 54–87%) is a **markup on a commodity input we resell.** Anthropic cuts prices → our absolute 2× shrinks. We are a reseller with a margin, not a product with a price.

### Finding 2 — The moat is served free AND unmetered.

The interop face (MCP — `remember` / `recall` / `trace`, ADR-368/372; served to ChatGPT, Claude, any LLM) is the **distribution of the moat** (durable attributed memory, ADR-310/311). The MCP server path (`api/mcp_server/`) contains **zero** references to `balance` / `execution_events` / `cost` — confirmed by grep. When an external LLM calls `recall`/`remember`/`trace` against a YARNNN workspace:
- It **costs the operator nothing** (no balance draw).
- It **earns us nothing** (no revenue).
- It is **pure substrate** (no embedding/compose LLM on the serving path per the ADR-368 design) — so there is no LLM cost to even hang a 2× markup on.

**We give away the differentiator and bill the resold tokens.** This is the strategic inversion the operator named.

### The conclusion these force

"Near-0 cost" was never a reason to price at near-0 — that conflates **our cost** with **our price** (cost-plus pricing on the cheapest input; the classic SaaS mistake). Stripe does not price a charge at its compute cost; it prices the *value of moving money*. The substrate action *types* must be **modeled as value lines**, even if some end up deliberately free as an acquisition lever — but that must be a *choice*, not a fallout of "it costs us nothing."

**ADR-391's D2 ("mechanical/no-LLM = free principal") was a cost statement masquerading as a pricing decision.** This doc reopens it.

---

## 2. The action × value × cost matrix (the core artifact)

The system's actions, grouped by class, scored by **value to the operator** (not cost to us), with our cost beside it to show the inversion. *(The exhaustive primitive/channel enumeration is in §6; this is the value-bearing grouping.)*

| # | Action class | Concrete actions | Channel(s) | **Our cost** | **Value to operator** | Priced today? |
|---|---|---|---|---|---|---|
| **A** | **Substrate accumulation** | WriteFile, place intake, derive-and-cite, attribute, EditFile — the authored asset growing | in-app, MCP | **~$0** | **HIGH** — the compounding asset; the moat *floor*; valuable even with no agent running | ❌ free |
| **B** | **Substrate recall / provenance (interop)** | recall, trace, ReadFile, SearchFiles, QueryKnowledge, ListRevisions — durable memory + history served anywhere | **MCP (any LLM)**, in-app | **~$0** | **HIGHEST** — the thing no commodity LLM has; `trace` is the literal differentiator; served to ChatGPT/Claude = distribution | ❌ free, **unmetered** |
| **C** | **Perception / intake** | TrackWebSources, connector sync, watches, ledger-intake — reality entering as attributed observation | connectors, MCP | **~$0** (mechanical) | **MEDIUM-HIGH** — the feedstock of all judgment; the perception field (ADR-335) | ❌ free |
| **D** | **LLM judgment (substrate-layer / Rung-1)** | Freddie wakes, chat turns, reflection, inference, steward reasoning | in-app | **REAL $** | **MEDIUM** — valuable, but *commodity-adjacent* (any LLM reasons; the value is the substrate it reasons over, which is A/B/C) | ✅ the only billed thing |
| **E** | **Consequential operation (Rung-2)** | a trade, a publish, an irreversible external send — the value-moving act through the ADR-307 gate | external channels | **REAL $ + RISK** | **HIGHEST** — the act you'd pay a human operator for; where delegation value lives | ⚠️ ADR-334 deferred |

### The diagonal is the whole strategic story

**We bill row D — the one row where our cost is high and the value is commodity-adjacent — and give away rows A, B, C, where our cost is ~0 and the value is the moat.** A value-based model *inverts the diagonal*: price the **durable asset (A/B)** and the **consequential act (E)**; treat **LLM tokens (D)** as the thin pass-through floor (which is all a markup-on-commodity deserves to be).

This is the matrix arguing for its own price object: **value concentrates at the asset and the act, not the compute.**

---

## 3. Candidate price objects (derived, not assumed)

Each candidate is a different answer to "what is the priced object," read off where §2's value concentrates. None is chosen here — they are the menu the matrix produces, with the honest trade for each.

### Candidate 1 — Substrate-asset base + thin LLM pass-through
- **Price object**: the *workspace as a durable, served asset* (rows A+B+C). A base price for holding + accumulating + serving the substrate (incl. interop). LLM judgment (D) metered near-cost on top (drop the markup toward 1×; the base is the margin).
- **Why the matrix supports it**: prices the moat directly; the unmonetized interop face (Finding 2) becomes the *reason to pay*, not a giveaway. Margin decouples from Anthropic's price moves.
- **Trade**: must justify a base price for something operators currently get free — needs the value of "durable memory served everywhere" to be *felt* (the trial/wince, ADR-330/331). Hardest to land cold; strongest moat-alignment.

### Candidate 2 — Per-value-class metering (the "per-API, but on value not compute")
- **Price object**: the *action class*, priced by value-tier. A `trace`/`recall` (row B) carries a price because it's worth it, not because it costs us; a consequential operation (E) carries a higher one; commodity LLM turns (D) are floor-priced. This is the operator's "per-API" instinct, re-based from *compute* to *value-class*.
- **Why the matrix supports it**: directly prices the high-value/low-cost rows (B, E) that are free today. Naturally meters the interop face.
- **Trade**: metering *reads* (row B) is unusual and can feel hostile ("charged to remember?") — the same reflex ADR-327 D4 protects against for chat. Risk: taxes the moat's *usage* and suppresses the distribution flywheel. Per-class taxonomy adds cognitive load (against the layman-simplicity goal).

### Candidate 3 — Consequential-operation seat (ADR-334, re-cut to the act)
- **Price object**: the *consequential operation* (row E) — price the act that moves value/carries risk; everything else (A–D) is free or floor-metered. This is ADR-334's original instinct, scoped to the one row where it's unambiguously right.
- **Why the matrix supports it**: E is the highest-value/highest-risk row; the thing you'd pay a human for. Clean story: "free to remember and think; you pay when it *acts*."
- **Trade**: the desire-axis problem ADR-334 was demoted on (operators least want to delegate the consequential act, ADR-380) — pricing E bets on the thing least validated. And at Rung-1 (Freddie-only, no consequential acts) there's *nothing to charge* — so this can't be the *only* model or the substrate business is free forever.

### Candidate 4 — Composite: substrate base + consequential metering (1 + 3)
- **Price object**: a **workspace base** (row A/B/C — the asset, the floor that monetizes Rung-1 + interop) **+ metered consequential operations** (row E — the Rung-2 act). LLM judgment (D) is the thin floor between them.
- **Why the matrix supports it**: monetizes *both* poles where value sits (the asset AND the act), with the commodity (D) as pass-through. Covers the Rung-1-only world (base) and the Rung-2 world (base + acts).
- **Trade**: most expressive, most complex — two price mechanisms. Must prove the complexity earns its keep for a layman (the ADR-340/391 simplicity bar). Likely the *right end-state*, possibly not the *right v1*.

---

## 4. How this lands against ADR-391 (the relationship, honest)

ADR-391's **architecture survives intact** — three layers (balance / allocation / metering), principal-attributed ledger. That substrate supports *any* candidate here; nothing in §3 needs a different ledger.

What §1–§3 **reopens** is ADR-391's *pricing* decisions, which rested on the cost-equals-price assumption this doc rejects:
- **D2 ("mechanical = free principal")** — reframed: mechanical = *our cost is $0*, NOT *price is $0*. Free becomes a deliberate lever (acquisition), not a fallout. Rows A/B/C are now *candidate revenue*, not definitionally free.
- **D4/D6 ("per-workspace subscription on commons-scale")** — still viable, but now it's *one* candidate (closest to Candidate 1/4's base), not the settled axis. "Commons-scale" (# principals/connectors) was a *proxy* for value; this doc says model the *value* directly and let the tier axis fall out — it may be asset-depth or consequential-act-volume, not headcount.

**Net**: ADR-391 = the cost architecture (sound, keep). This doc = the value model that picks the *price* on top of it. A successor ADR amends ADR-391 §D2/D4/D6 once a candidate is chosen against evidence.

---

## 5. The honest open questions (what a model still needs before it's real)

1. **Is metering reads (row B) acceptable or hostile?** The interop flywheel (distribution of the moat) may be worth more free than metered. Candidate 1 (base, reads-free) vs Candidate 2 (meter reads) hinge on this.
2. **Can a substrate base price be *felt* cold?** Candidate 1/4 need the durable-memory value to land in a trial wince (ADR-330/331). Untested.
3. **The numbers.** Every $ in §3 is deliberately absent. They come *after* a candidate is chosen and *against* COST-MODEL.md real per-action economics — not before.
4. **The desire axis (carried from ADR-334/380).** Candidate 3/4's consequential-metering bets on the act operators least want to delegate. Still unvalidated; still the deepest risk.
5. **Where does the markup go?** If the base (A/B) carries margin, LLM (D) can drop toward 1× — a *cheaper-compute* story that competitors reselling at 2×+ can't match. Is "we don't mark up your tokens, we price the memory" a wedge? Worth testing.

---

## 6. The recommended direction — simplified Candidate 4 (operator lean, 2026-06-30)

The operator's steer: keep all four as *analysis*, but lean toward **Candidate 4 or a simplified version — intentional opt-out on some classes, margin on others — landing on a model users "get intuitively and easily."** This section derives that simplified model from the matrix; it is a *pre-assessment recommendation*, not a ratified model (no numbers committed; the next step is to pick + price against evidence).

### 6.1 The intuitive shape: "Free to remember. Pay to operate."

Two priced objects, each mapping to one thing a layperson already understands:

```
  ┌─────────────────────────────────────────────────────────────┐
  │  WORKSPACE PLAN  —  "your durable memory, kept and served"   │
  │  a flat monthly base for the substrate layer (rows A·B·C)    │
  │  • accumulate · recall · trace · serve to any LLM (interop)  │
  │  • Freddie keeps it coherent                                 │
  │  the moat IS the product you pay a base for                  │
  └─────────────────────────────────────────────────────────────┘
                              +
  ┌─────────────────────────────────────────────────────────────┐
  │  OPERATION  —  "when an agent does real work for you"        │
  │  metered, per running operation (rows D·E)                   │
  │  • LLM judgment + consequential acts, drawn from balance     │
  │  • free to hold; you pay when it WORKS                       │
  └─────────────────────────────────────────────────────────────┘
```

A layperson reads the whole thing as: **"A small monthly fee keeps your memory alive and usable everywhere. You pay more only when you put an agent to work."** No per-token math, no per-API-call ledger to reason about, no seat arithmetic. Two concepts, both intuitive.

### 6.2 The deliberate opt-out / margin split (the operator's "intentional opt-out on some, margin on others")

| Action class (§2) | Decision | Rationale |
|---|---|---|
| **A — substrate accumulation** | **Margin** (in the base) | the asset; what they're paying the base for |
| **B — recall / trace / interop** | **Deliberate opt-out → FREE** (covered by base) | metering reads is hostile + suppresses the distribution flywheel (§5 Q1). Free *unlimited* recall is the lever; the base already paid for the asset. **This also fixes the un-recovered embedding loss** (§5 / enumeration §6): once a base exists, the small OpenAI-embedding COGS on `recall`/`trace` is covered by it instead of being a pure loss. |
| **C — perception / intake** | **Margin** (in the base) | the feedstock; bundled into "keep my memory current" |
| **D — LLM judgment** | **Metered, thin** (operation usage) | commodity-adjacent; pass-through near cost. The base carries the margin, so D's markup can drop toward 1× — a *"we don't mark up your tokens"* wedge (§5 Q5) |
| **E — consequential operation** | **Metered, in the operation** | the value-moving act; priced as part of running an operation, not a separate seat |

**The intentional opt-out is row B** — the moat's *usage* is free-by-design (the base monetizes its *existence*, not each read). The margin sits on **A/C (the base)** and is *light* on **D (usage)**. This is the inversion of today: margin moves from the commodity (D) to the asset (A/B/C-as-base).

### 6.3 Why this is future-proof, scalable, and profitable (the operator's three criteria)

- **Future-proof**: rides ADR-391's three-layer architecture unchanged (base = the per-workspace plan over Layer ①; operation usage = Layer ②/③ metering). Works at N=1 (one base, one operation) and at the multi-principal commons (one base, N operations/agents drawing the shared balance) without a repricing.
- **Scalable**: the base is per-workspace (not per-principal) → adding members/agents/connectors doesn't multiply invoices; it's "a bigger operation footprint," metered. The interop flywheel is unthrottled (free recall) → distribution scales without a usage tax fighting it.
- **Profitable — and this is the real shift**: margin decouples from Anthropic. Today profit = the 2× token markup (shrinks as Anthropic cuts prices, §1). Here profit = the **base on the durable asset** — a thing only YARNNN has (durable attributed memory + provenance, served anywhere). We stop being a token reseller and start being a memory utility with metered labor on top. **The moat finally carries the margin.**

### 6.4 What still has to be decided (this is pre-assessment, not the model)

1. **The base number + what (if anything) it gates.** Must honor the no-capability-gate-revival discipline (ADR-391 D5) — the base buys *the asset + Freddie*, not a feature matrix.
2. **Does "Operation" = the ADR-332 program activation, or a looser unit?** The metered-operation object needs a crisp definition (likely: an activated program = a priced operation; ADR-391 D6 / ADR-334's "operation" concept).
3. **D's markup toward 1×** — is the "we don't mark up your tokens" wedge worth the margin given up? Test against COST-MODEL real economics.
4. **Trial / felt-value** — the base only sells if "durable memory served everywhere" is *felt* cold (§5 Q2; ADR-330/331 harvest wince).
5. **Rung-1-only worlds** (Freddie, no operation) pay only the base — confirm that's a coherent, sellable product on its own (the substrate-utility tier).

> **Net**: the simplified-Candidate-4 model — **a flat workspace base on the durable substrate (free unlimited recall/interop) + metered operations on top** — is the pre-assessment recommendation. It is intuitive ("free to remember, pay to operate"), inverts margin from commodity to moat, and is the same two-object shape as ADR-391's balance+subscription, now *value-derived* rather than commons-scale-assumed. Candidates 1–3 remain on record as the alternatives this was chosen against.

---

## 7. Appendix — the exhaustive action / channel enumeration (ground-truth receipts)

From `primitives-matrix.md` + `registry.py` (primitives), FOUNDATIONS Axiom 6 + ADR-198/202 (channels), ADR-380/381/383 (layer split), `platform_limits.py` / `telemetry.py` / `wake.py` / `mcp_composition.py` (economics). Verified read-only.

### 7.1 Primitive surface, by cost/permission class

**READS** (`read_only`, never gated, zero-LLM — matrix:10): `LookupEntity`, `ListEntities`, `SearchEntities`, `ReadFile`, `SearchFiles`, `ListFiles`, `QueryKnowledge`, `ReadAgentFile`, `ListRevisions`, `ReadRevision`, `DiffRevisions`, `DiscoverAgents`, `GetSystemState`, `list_integrations`, `WebSearch` (read-shaped but external — cost lands on the LLM round it runs in), `ReturnVerdict`.

**WRITES** (`consequential`, gate-queueable to `action_proposals` family=`substrate`; substrate-layer / Rung-1): `WriteFile`, `EditFile`, `DeleteFile`, `MoveFile`, `EditEntity`, `InferContext`, `Embed` (ADR-325), `ManageAgent`, `Schedule`, `ManageHook`, `ManageDomains`, `FireInvocation`, `SyncPlatformState`, `RepurposeOutput`, `RuntimeDispatch`, `Compose`. — All ~$0 LLM *as writes*; the LLM round that *decided* the write is what's costed.

**CONSEQUENTIAL — external/capital** (the sharp end of the ADR-307 gate; operation-layer / Rung-2): `ProposeAction` (headless's only external path — proposes, can't bind), `ExecuteProposal` (binds operator-approved capital action; gates at `review_proposal_dispatch`), `RejectProposal`, `DispatchSpecialist` (Reviewer-only, delegation-gated), `platform_*` dynamic (Slack/Notion/Alpaca/Lemon-Squeezy — capability-gated per `platform_connections`), `Clarify` (gate-owned, ADR-352).

**Caller-class totals** (matrix:281–286): Chat 31 · Reviewer/Freddie 24 · Headless 29 + `platform_*` · **MCP exactly 4** (`QueryKnowledge`, `WriteFile`, `InferContext` + composition; tool surface = the 3 intent verbs) · Operator = surface actions + chat-mediated.

### 7.2 Channel surface (FOUNDATIONS Axiom 6) + cost shape

| Channel | Consumer | Cost shape |
|---|---|---|
| In-app surfaces (Chat/Home/Files/Channels/Agents/Queue) | Operator | $0 to render (compose-on-read mirrors); producing LLM round costed separately |
| Chat / addressed turn | Operator | **LLM-costed (Sonnet)**, balance-gated (`feed.py:1302`) |
| **MCP interop** (`remember`/`recall`/`trace`) | Foreign LLM | tool call **$0, no balance check in mcp_server**; `remember` triggers a downstream costed Freddie wake |
| Email (ADR-299/304) | Operator | send is system infra ($0 via Resend); content was LLM-produced upstream |
| Slack/Notion/GitHub write-back | Platform | mechanical API ($0 transport); deciding LLM round costed |
| Platform connectors (intake) | Substrate | **$0 zero-LLM** (`mechanical`-mode recurrences, matrix:276) |

Key split: **Channel ≠ Mechanism** (FOUNDATIONS:516–522) — delivery routing is always ~$0; cost lives in the LLM that produced the artifact.

### 7.3 Layer split (ADR-380 ladder)

- **Substrate / Rung-1 (Freddie, reversible, ships)**: derive-and-cite + placement · reversible substrate writes (every one an attributed revision, ADR-209) · attribution + intake (`retain+attribute+cite`, DP32) · MCP reads/writes · perception (mechanical, zero-LLM) · lifecycle authoring (`Schedule`/`ManageHook`/`ManageDomains`) · multi-principal arbitration + persona-agent governance (ADR-381 D5). *Harness honesty: budget/pace live, mandate/autonomy DEGENERATE (ADR-380 D3).*
- **Operation / Rung-2 (persona-agents, consequential, deferred)**: `ProposeAction`→`ExecuteProposal` · `platform_*` consequential writes · exogenous track-record clock · accountability split (judgment→persona agent, system→Freddie; DP24/DP30 relocate, ADR-382/383).

### 7.4 The economics receipts (the load-bearing facts)

- **Metering rate**: 2× Anthropic, cache-inclusive, single source `telemetry.py::_BILLING_RATES` (`STRATEGY.md:34-55`). Anthropic cost derivable = `cost_usd / 2`.
- **Model-by-trigger** (`freddie_agent.py:1384`): addressed/reactive → **Sonnet** (expensive); recurrence fires → **Haiku** (~4× cheaper input). A chat turn costs materially more than a scheduled wake.
- **The 4 production balance gates** (the *only* revenue lever): `feed.py:1302` (chat) · `wake.py:378` (recurrence/reflection) · `wake.py:1566` (substrate_event / `remember`-triggered derive-and-cite) · `runtime_dispatch.py:94` (asset render). Spend = `balance_usd − SUM(execution_events.cost_usd)`; recording an execution_event IS the debit. **No per-seat/per-connector/per-MCP/per-action charge exists.**
- **Interop economics (the moat-served-free receipt)**: `mcp_server/` has **zero** cost/balance/telemetry code. `recall`/`trace` = pure substrate reads, **no Anthropic call**, but the fuzzy path eats an **OpenAI `text-embedding-3-small` cost (~$0.00002/query) that never touches `balance_usd`** → served at a small **un-recovered loss**. `remember` write = $0, but fires a `substrate_event` Freddie wake (Sonnet, balance-gated, charged to the *writer's* balance). **Revenue from interop: none direct.**

**The one-line ground truth**: the single revenue lever today is Anthropic LLM-call metering at 2× invoice netted against a hard-stop `balance_usd`. Every substrate read, MCP read, mechanical connector, perception, scheduling, and delivery is served at $0 and earns nothing; the interop face is served at a small un-recovered loss.
