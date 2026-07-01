# Cost Capture First, Pricing Second — the separation, and the consolidated pricing candidates on top

> **Status**: Consolidation / discourse-of-record (Hat A). **RE-FRAMED 2026-07-01** around the capture-vs-pricing separation (operator's correction). The task splits in two: **(1) capture** — measure and *surface* every action + cost accurately and transparently (a truth/legibility problem, built first) and **(2) pricing** — a commercial model layered *on top* of a complete honest capture (a strategy problem, decided second). Prior draft led with "group the matrix and decide what to price in/out" — that motion lets pricing bend capture, which corrupts the measurement and contradicts the product's legibility soul. This version leads with capture; the pricing framework below is preserved as **Layer-2 candidates**, not a decision. Ratifies no numbers, no model.
> **Date**: 2026-07-01
> **Authors**: KVK (operator) + Claude (collaborator)
> **Supersedes the "owed scoping item" status of** [`phase-1-packaging-open-scoping-rung-2-pricing-2026-06-29.md`](../analysis/phase-1-packaging-open-scoping-rung-2-pricing-2026-06-29.md).
> **Consolidates**:
> - **The live model**: `STRATEGY.md` / `README.md` / `COST-MODEL.md` — balance-as-single-gate, 2× Anthropic (ADR-172/291). *The floor, kept.*
> - **The architecture**: [ADR-391](../adr/ADR-391-budget-balance-and-the-three-layer-cost-model.md) — balance (workspace) · allocation (principal) · metering (ledger). *Sound, kept — this is the capture substrate.*
> - **The value analysis**: [`value-based-pricing-the-action-surface-matrix-2026-06-30.md`](../analysis/value-based-pricing-the-action-surface-matrix-2026-06-30.md) — the action matrix. *Re-cast here as "what to SURFACE," not "what to price."*
> - **The retention axis**: [ADR-392](../adr/ADR-392-the-connector-lane.md) D8 — `connector_retention.py::resolve_retention_days(tier_max_days=...)`. *A built Layer-2 seam.*
> - **Deferred**: [ADR-334](../adr/ADR-334-per-operation-pricing.md) — delegation seats. *Rung-2 / Phase-2, not launch.*

---

## 1. The separation (the load-bearing correction)

The pricing question has been stuck because **two motions were being done at once**: capturing what happens (accurately) and deciding what to charge for (commercially) — as one act. That fusion is the bug. Deciding "this action is free, this one is margin" *while* instrumenting means pricing bends the measurement: you shape what you *count* around what you want to *charge*, and you can never un-bend it.

**Split them, and order them:**

| Layer | What it is | Problem type | When |
|---|---|---|---|
| **① Capture** | measure + **surface** every action, every principal, every cost — transparently, as-is | **truth / legibility** | **build first** |
| **② Pricing** | a commercial model layered on a complete honest capture | **strategy** | **decide second, on top** |

**Why this ordering is strategically stronger, not just cleaner:**

1. **A complete honest capture supports *any* pricing model later** — base, usage, per-value-unit, wallet-draws — without re-instrumenting. A pricing-shaped capture permanently bends your measurement to a commercial guess you haven't validated.
2. **Transparency IS the wedge, and it's the only pricing philosophy coherent with the product.** YARNNN's moat is *attributed, legible, `trace`-able substrate — you see who did what, when, with full provenance.* A cost model that hides costs and bundles actions away contradicts the product's soul. A cost surface that shows the operator exactly what every principal did and drew is **the same legibility principle applied to spend — the `trace` of your money.** Freddie is a transparent steward of your substrate; the cost surface is a transparent steward of your spend. Same value, one domain over.
3. **It dissolves the premature forks.** Base-early vs base-late, meter-cost vs meter-value — all become **Layer-2 decisions made *after* you can see the full honest picture** (possibly with real usage data, possibly with the user in the loop), not guesses made in the dark.

**Legible, not raw (the transparency discipline).** "Surface everything" does NOT mean a raw AWS-style token firehose (anxiety-inducing; why nobody shows laypeople raw metering). It means the **substrate's own legibility grammar applied to spend**: a calm human-rendered rollup ("Freddie tidied your substrate 12×, served your memory to ChatGPT 40×, made 2 trades") with drill-down to the underlying `execution_events` for anyone who wants it — exactly the compact-index-then-drill model the substrate itself uses (ADR-159/221/289/340). Completeness underneath, legibility on top.

## 2. Layer 1 — the Cost & Activity Surface (build first)

The capture layer is an **honest, complete rendering of every action across every principal with its real cost** — every row of the [action-surface matrix](../analysis/value-based-pricing-the-action-surface-matrix-2026-06-30.md) *surfaced*, not grouped-for-pricing. It reads what already exists (`execution_events` = the ADR-291 cost ledger; the ADR-209 authored-substrate revision chain for non-LLM actions; `principal_grants` for the who) and renders it legibly. Mechanical/$0 actions are shown *at $0, honestly* — not hidden. This is capture + legibility, and it needs **no pricing decision to build.**

*(Surface scope — where it lives, what it renders, what it reads — is its own scoping pass; named here, not designed. It is the natural sibling of the balance/budget panes and the Channels activity lens.)*

## 3. Layer 2 — the pricing candidates (decide later, ON TOP of Layer 1)

Everything below is **preserved Layer-2 analysis** — the shape a commercial model *could* take once Layer 1 makes the full picture legible. **None of it is decided.** It is here so the pricing session inherits worked candidates, not a blank page. The consolidated candidate is **two priced objects over one metered floor**:

```
 ┌──────────────────────────────────────────────────────────────────────┐
 │  ① THE FLOOR — pay-as-you-go workspace balance  (ADR-172/291/391)    │
 │     balance_usd on the workspace · 2× Anthropic · hard-stop at zero  │
 │     every principal draws it · mechanical/no-LLM = $0 draw           │
 │     KEPT UNCHANGED. This is the metering substrate under everything. │
 └──────────────────────────────────────────────────────────────────────┘
                                   ▲ metered usage draws down
 ┌──────────────────────────────────────────────────────────────────────┐
 │  ② THE BASE — the WORKSPACE PLAN  ("your durable memory, kept+served")│
 │     a flat monthly price for the SUBSTRATE LAYER (matrix rows A·B·C)  │
 │     • accumulate · recall · trace · serve to any LLM (interop)       │
 │     • Freddie keeps it coherent                                      │
 │     • CONNECTOR RETENTION WINDOW is a dimension of this base (§3.2)   │
 │     the moat IS the product you pay a base for                       │
 └──────────────────────────────────────────────────────────────────────┘
                                   +  (only when you run work)
 ┌──────────────────────────────────────────────────────────────────────┐
 │  ③ THE OPERATION — metered, per running operation  (Rung-2, deferred) │
 │     LLM judgment + consequential acts (matrix rows D·E)              │
 │     ADR-334 delegation seats live HERE, at Phase-2. Not the launch.  │
 └──────────────────────────────────────────────────────────────────────┘
```

**Layman reading**: *"A small monthly fee keeps your memory alive and usable everywhere. Usage runs off a balance you top up. You pay more only when you put an agent to work."*

The launch (Rungs 0–1) sells **① + ②**. ③ is Phase-2 (ADR-334, when Rung-2 ships). This is the Phase-1 thesis the packaging note said was missing: **the base on the substrate-OS, not a delegation funnel.**

### 3.1 What each prior artifact resolves to (the consolidation table)

| Prior artifact | Its status now | Where it lives in the framework |
|---|---|---|
| ADR-172/291 balance | **Kept, unchanged** | ① The floor — the metering substrate |
| ADR-391 three-layer architecture | **Kept** — balance/allocation/ledger | the substrate *under* ①②③ (how price binds to workspace vs principal vs invocation) |
| ADR-391 D4/D6 "commons-scale subscription" | **Reframed** — the subscription is ②, but priced on **substrate value**, not commons-scale headcount | ② The base |
| Value matrix "free to remember, pay to operate" | **Adopted as the launch thesis** | ② (free recall/interop) + ③ (pay to operate) |
| ADR-392 D8 retention window | **A dimension of ②** (not a separate axis) — see §3.2 | ② The base |
| ADR-334 delegation seats | **Confirmed Rung-2 / Phase-2** | ③ The operation (deferred) |
| phase-1-packaging "OPEN" gap | **Closed** — ② is the Phase-1 thesis | this doc |

### 3.2 Retention is a dimension of the base, not a new axis (the ADR-392 fold)

ADR-392 D8 called retention "a natural commons-scale tier axis parallel to # principals / # connectors / autonomy-ceiling." That was the ADR-391-D4 framing — the one the value analysis reopened. **Consolidated correctly, retention is not a parallel axis; it is a dimension of the substrate base (②).** The reasoning:

- Retention governs **how much raw connector history the substrate keeps** — pure **substrate-layer** (matrix row C, perception/intake). It is literally "how big/durable is your kept memory."
- `connector_retention.py` already homes it in `governance/_retention.yaml`, explicitly *"kin to `_budget.yaml`… a spend/storage envelope in the GRANT root."* Storage envelope = a property of the base, not the operation.
- So the base ② is not one flat number — it has **substrate dimensions**: how much is kept (retention window), how many connectors feed it, how much interop reach (ADR-379 host count). These are the *honest* tier axis for ②: **depth/breadth of the durable substrate**, not headcount.

This resolves the D4-vs-value-model tension cleanly: **"commons-scale" was a proxy; the real tier axis for the base is substrate depth+breadth, and retention is its first concrete, already-built dimension.**

**The built seam (implementation-ready, receipts):** `services/connector_retention.py::resolve_retention_days(client, user_id, *, tier_max_days=None)` (line 52) reads `governance/_retention.yaml` and **clamps the operator's declared window to `tier_max_days`** (line 87-88). Today every caller passes `None` (operator's value stands). **The pricing layer's entire retention integration is: pass the tier's ceiling as `tier_max_days`.** No GC change, no new mechanism. This is the template for how *every* substrate-base dimension plugs in — a `tier_max_*` clamp at a read-one-value seam.

### 3.3 From framework to implementation considerations (Layer-2 seams)

The framework is decidable; these are the concrete build questions, ordered. **None requires inventing new mechanism** — the seams exist (balance, `_budget.yaml`, `_retention.yaml`, the ADR-391 architecture). The work is *deciding the numbers + wiring the tier clamps*.

### 3.3.1 The base object (②) — what a "Workspace Plan" IS, concretely
- **Substrate**: a per-workspace subscription record `(workspace_id, plan_tier, status, period)` — the ADR-391 §5 line-item, now the base. Lemon Squeezy product per tier (the IMPLEMENTATION.md LS integration extends; no new payment stack).
- **What the tier gates** = substrate depth/breadth dimensions, each a `tier_max_*` clamp:
  - retention window (`resolve_retention_days(tier_max_days=…)` — **built**),
  - # connectors (a count check at connect time),
  - interop host reach (ADR-379 host-profile count),
  - *(candidate)* substrate size / # principals.
- **Discipline (ADR-391 D5, binding)**: these are *depth/breadth of the asset*, NOT ADR-172-deleted capability gates (no task counts, no message caps). The line is: gate *how much substrate*, never *which features*.
- **Open**: the number of tiers (recommend **2**: a free/floor tier + one paid base — resist a matrix), the base price, and which dimensions are v1 (recommend: retention + connector count only; interop reach + size are v2).

### 3.3.2 The floor (①) — one honest-margin fix
- **Keep balance/2×/hard-stop.** But if ② carries the margin, **① can drop toward 1×** — the "we don't mark up your tokens, we price the memory" wedge (value matrix §5 Q5). **Decision needed**: does the base let us cut the token markup? This is a *margin-relocation* choice, not a mechanism change (`telemetry.py::_BILLING_RATES` is the one dial).
- **Doc-hygiene blocker**: `README.md` says *"cache discount not passed through — platform margin"*; `STRATEGY.md` says it **is** passed through (exactly 2×). **Contradiction — resolve before any pricing copy ships.** (STRATEGY is newer/ADR-291-aligned; README is stale.)

### 3.3.3 The operation (③) — confirmed deferred, one label fix
- ADR-334 = the Rung-2/Phase-2 model. **Action**: add the one-line status note the packaging doc recommended (ADR-334 → "Rung-2/Phase-2 delegation pricing; not the Phase-1 launch model"). Not built at launch.

### 3.3.4 The interop question (still the sharpest open item)
- `recall`/`trace` are served free **and at a small un-recovered OpenAI-embedding loss** (value matrix §5; enumeration receipt). Under ② the base *covers* this (the loss becomes a COGS line under a paid base — resolved). **But confirm**: is unlimited free recall/interop the right lever even under a base, or does very-high-volume interop need its own metered ceiling (a `tier_max_interop_calls`)? Lean: **free under base at launch** (the distribution flywheel > the embedding COGS), revisit if interop volume COGS becomes material. Name it; don't over-build it.

### 3.3.5 The felt-value dependency (the go-to-market blocker)
- The base only sells if *"durable memory served everywhere"* is **felt** before the paywall (value matrix §5 Q2). This couples to the trial/harvest wince (ADR-330/331). **Not a pricing-code question** — but the pricing model's success depends on it, so it's named as the paired GTM work.

## 4. The recommended decisions (re-framed by capture-first)

The re-frame changes what is *decided now* vs *deferred*. Only the capture-order decision is live; the pricing-shape decisions are explicitly deferred to Layer 2.

**Decide now (capture-first):**
1. **Build Layer 1 (the Cost & Activity Surface) BEFORE deciding any pricing model** (§1–§2). A complete, transparent, legible-not-raw capture of every action + cost, across every principal. This is the load-bearing decision — it unblocks a surface that needs no pricing call.
2. **Transparency is the pricing philosophy** (§1) — the cost surface is the `trace` of spend, coherent with the product's legibility moat. Whatever Layer 2 becomes, it is layered *on* a surface that already tells the whole truth.

**Deferred to Layer 2 (do NOT decide here — preserved as candidates in §3):**
3. *(candidate)* two-objects-over-a-floor as the pricing shape (§3); base priced on substrate depth/breadth not headcount (§3.2, §3.3.1); two tiers not a matrix (§3.3.1); ③ operations/seats stays Phase-2 (§3.3.3). **These are the worked candidates the pricing session inherits — not decisions.**
4. **Numbers are the last mile** — against COST-MODEL real economics + a first paying user + Layer-1 usage data. Demand-gated (the ADR-334 discipline). This doc sets no price.

**Hygiene (already landed 2026-07-01):** the README↔STRATEGY cache-passthrough contradiction (§3.3.2) and the ADR-334 Rung-2 status note (§3.3.3) — both fixed + committed.

## 5. The two successor ADRs (capture, then pricing)

The re-frame splits the ratification into two, in order:

**Near — the Cost & Activity Surface ADR (capture, build first).** Ratifies Layer 1: what the surface renders (every action × principal × cost), what it reads (`execution_events` + the ADR-209 revision chain + `principal_grants`), the legible-not-raw grammar (rollup + drill-down), where it lives. **No pricing content.** This is the buildable next step and needs no commercial decision. *(ADR number TBD — NOT ADR-393, which is already the connector capture-pipeline lane.)*

**Later — the Pricing Model ADR (strategy, on top).** When Layer 1 is live and a demand signal exists: ratifies the pricing shape from the §3 candidates (amending ADR-391 D4/D6 if the two-objects/substrate-depth candidate wins), folds ADR-392 D8 retention as a tier dimension, re-labels ADR-334 as Phase-2/Rung-2, rewrites `STRATEGY.md`. Numbers demand-gated (no LS wiring until a price is set against a real buyer).

**This doc is the separation + the preserved candidates. The capture surface is the buildable now; the pricing model is the deferred second layer.** The delay it ends is the *conflation* — capture no longer waits on a pricing decision it never needed.
