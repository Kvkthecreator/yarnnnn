# Pricing Consolidation — from the value matrix + connector retention to an implementation-facing framework

> **Status**: Consolidation / decision-driving (Hat A). **Threads the scattered pricing surface into ONE framework and shifts the discourse toward implementation considerations.** Ratifies no numbers; names the model shape, the concrete seams already built, and the sequence to harden it. Supersedes the "owed scoping item" status of [`phase-1-packaging-open-scoping-rung-2-pricing-2026-06-29.md`](../analysis/phase-1-packaging-open-scoping-rung-2-pricing-2026-06-29.md) — this IS that session.
> **Date**: 2026-07-01
> **Authors**: KVK (operator) + Claude (collaborator)
> **Consolidates**:
> - **The live model**: `STRATEGY.md` / `README.md` / `COST-MODEL.md` — balance-as-single-gate, 2× Anthropic (ADR-172/291). *The floor, kept.*
> - **The architecture**: [ADR-391](../adr/ADR-391-budget-balance-and-the-three-layer-cost-model.md) — balance (workspace) · allocation (principal) · metering (ledger). *Sound, kept.*
> - **The value model**: [`value-based-pricing-the-action-surface-matrix-2026-06-30.md`](../analysis/value-based-pricing-the-action-surface-matrix-2026-06-30.md) — the matrix + "free to remember, pay to operate." *The Phase-1 thesis.*
> - **The open gap**: [`phase-1-packaging-open-scoping-2026-06-29.md`](../analysis/phase-1-packaging-open-scoping-rung-2-pricing-2026-06-29.md) — "Phase-1 has no pricing thesis; ADR-334 is Rung-2." *Closed by this doc.*
> - **The new axis**: [ADR-392](../adr/ADR-392-the-connector-lane.md) D8 — connector **retention window**, built pricing-ready (`connector_retention.py::resolve_retention_days(tier_max_days=...)`). *Folded in as a substrate-base dimension.*
> - **Deferred**: [ADR-334](../adr/ADR-334-per-operation-pricing.md) — delegation-tiered seats. *Confirmed Rung-2 / Phase-2; not the launch model.*

---

## 1. Why this doc exists (the delay, named)

The pricing decision has been deferred at least five times, each for a *good* reason at the time:
- ADR-172 dissolved tiers → "balance is the only gate" (correct, but that's a *floor*, not a *model*).
- ADR-334 proposed seats → **demoted** (no external users; desire-axis unvalidated).
- ADR-380 §6 → "Phase-1 needs its own thesis; out of scope here."
- The phase-1-packaging note (2026-06-29) → "OPEN, owed its own session."
- ADR-391 → decided the *architecture*, flagged the *pricing* reopened.
- ADR-392 D8 → built retention "pricing-ready," mapping "deferred to the pricing session."

**Every deferral pointed at the same owed session. This is it.** The inputs are now all present: the value matrix (what's worth pricing), the three-layer architecture (where price binds), the retention seam (a concrete built-and-waiting axis), and the vision boundary (Rung-2 out of the launch — ADR-380 §5). Nothing else is blocking. The task now is to *consolidate to a decidable framework and move to implementation considerations*, not to derive more theory.

## 2. The consolidated framework (one picture)

Everything above collapses into **two priced objects over one metered floor** — the value-model shape (Candidate 4, simplified), now with retention folded in and the architecture beneath it named:

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
 │     • CONNECTOR RETENTION WINDOW is a dimension of this base (§4)     │
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

## 3. What each layer resolves (the consolidation table)

| Prior artifact | Its status now | Where it lives in the framework |
|---|---|---|
| ADR-172/291 balance | **Kept, unchanged** | ① The floor — the metering substrate |
| ADR-391 three-layer architecture | **Kept** — balance/allocation/ledger | the substrate *under* ①②③ (how price binds to workspace vs principal vs invocation) |
| ADR-391 D4/D6 "commons-scale subscription" | **Reframed** — the subscription is ②, but priced on **substrate value**, not commons-scale headcount | ② The base |
| Value matrix "free to remember, pay to operate" | **Adopted as the launch thesis** | ② (free recall/interop) + ③ (pay to operate) |
| ADR-392 D8 retention window | **A dimension of ②** (not a separate axis) — see §4 | ② The base |
| ADR-334 delegation seats | **Confirmed Rung-2 / Phase-2** | ③ The operation (deferred) |
| phase-1-packaging "OPEN" gap | **Closed** — ② is the Phase-1 thesis | this doc |

## 4. Retention is a dimension of the base, not a new axis (the ADR-392 fold)

ADR-392 D8 called retention "a natural commons-scale tier axis parallel to # principals / # connectors / autonomy-ceiling." That was the ADR-391-D4 framing — the one the value analysis reopened. **Consolidated correctly, retention is not a parallel axis; it is a dimension of the substrate base (②).** The reasoning:

- Retention governs **how much raw connector history the substrate keeps** — pure **substrate-layer** (matrix row C, perception/intake). It is literally "how big/durable is your kept memory."
- `connector_retention.py` already homes it in `governance/_retention.yaml`, explicitly *"kin to `_budget.yaml`… a spend/storage envelope in the GRANT root."* Storage envelope = a property of the base, not the operation.
- So the base ② is not one flat number — it has **substrate dimensions**: how much is kept (retention window), how many connectors feed it, how much interop reach (ADR-379 host count). These are the *honest* tier axis for ②: **depth/breadth of the durable substrate**, not headcount.

This resolves the D4-vs-value-model tension cleanly: **"commons-scale" was a proxy; the real tier axis for the base is substrate depth+breadth, and retention is its first concrete, already-built dimension.**

**The built seam (implementation-ready, receipts):** `services/connector_retention.py::resolve_retention_days(client, user_id, *, tier_max_days=None)` (line 52) reads `governance/_retention.yaml` and **clamps the operator's declared window to `tier_max_days`** (line 87-88). Today every caller passes `None` (operator's value stands). **The pricing layer's entire retention integration is: pass the tier's ceiling as `tier_max_days`.** No GC change, no new mechanism. This is the template for how *every* substrate-base dimension plugs in — a `tier_max_*` clamp at a read-one-value seam.

## 5. From framework to implementation considerations

The framework is decidable; these are the concrete build questions, ordered. **None requires inventing new mechanism** — the seams exist (balance, `_budget.yaml`, `_retention.yaml`, the ADR-391 architecture). The work is *deciding the numbers + wiring the tier clamps*.

### 5.1 The base object (②) — what a "Workspace Plan" IS, concretely
- **Substrate**: a per-workspace subscription record `(workspace_id, plan_tier, status, period)` — the ADR-391 §5 line-item, now the base. Lemon Squeezy product per tier (the IMPLEMENTATION.md LS integration extends; no new payment stack).
- **What the tier gates** = substrate depth/breadth dimensions, each a `tier_max_*` clamp:
  - retention window (`resolve_retention_days(tier_max_days=…)` — **built**),
  - # connectors (a count check at connect time),
  - interop host reach (ADR-379 host-profile count),
  - *(candidate)* substrate size / # principals.
- **Discipline (ADR-391 D5, binding)**: these are *depth/breadth of the asset*, NOT ADR-172-deleted capability gates (no task counts, no message caps). The line is: gate *how much substrate*, never *which features*.
- **Open**: the number of tiers (recommend **2**: a free/floor tier + one paid base — resist a matrix), the base price, and which dimensions are v1 (recommend: retention + connector count only; interop reach + size are v2).

### 5.2 The floor (①) — one honest-margin fix
- **Keep balance/2×/hard-stop.** But if ② carries the margin, **① can drop toward 1×** — the "we don't mark up your tokens, we price the memory" wedge (value matrix §5 Q5). **Decision needed**: does the base let us cut the token markup? This is a *margin-relocation* choice, not a mechanism change (`telemetry.py::_BILLING_RATES` is the one dial).
- **Doc-hygiene blocker**: `README.md` says *"cache discount not passed through — platform margin"*; `STRATEGY.md` says it **is** passed through (exactly 2×). **Contradiction — resolve before any pricing copy ships.** (STRATEGY is newer/ADR-291-aligned; README is stale.)

### 5.3 The operation (③) — confirmed deferred, one label fix
- ADR-334 = the Rung-2/Phase-2 model. **Action**: add the one-line status note the packaging doc recommended (ADR-334 → "Rung-2/Phase-2 delegation pricing; not the Phase-1 launch model"). Not built at launch.

### 5.4 The interop question (still the sharpest open item)
- `recall`/`trace` are served free **and at a small un-recovered OpenAI-embedding loss** (value matrix §5; enumeration receipt). Under ② the base *covers* this (the loss becomes a COGS line under a paid base — resolved). **But confirm**: is unlimited free recall/interop the right lever even under a base, or does very-high-volume interop need its own metered ceiling (a `tier_max_interop_calls`)? Lean: **free under base at launch** (the distribution flywheel > the embedding COGS), revisit if interop volume COGS becomes material. Name it; don't over-build it.

### 5.5 The felt-value dependency (the go-to-market blocker)
- The base only sells if *"durable memory served everywhere"* is **felt** before the paywall (value matrix §5 Q2). This couples to the trial/harvest wince (ADR-330/331). **Not a pricing-code question** — but the pricing model's success depends on it, so it's named as the paired GTM work.

## 6. The recommended decisions (to ratify, or push back on)

A tight set, so this session *ends* the delay rather than extending it:

1. **Adopt the two-objects-over-a-floor framework** (§2) as the consolidated pricing model. It absorbs every prior artifact (§3).
2. **The base (②) is priced on substrate depth/breadth** (retention + connector count v1), NOT commons-scale headcount and NOT a feature matrix (§4, §5.1). Retention folds in via the built `tier_max_days` seam.
3. **Two tiers, not a matrix** — a free floor + one paid base at launch (§5.1). Resist ADR-100/172-era tier proliferation.
4. **③ (operations/seats) stays Phase-2** — ADR-334 re-labeled Rung-2, not built at launch (§5.3).
5. **Numbers are the LAST step, against COST-MODEL real economics + a first paying user** — the framework ratifies now; the price tags wait for the demand signal (the ADR-334 discipline preserved). This doc does NOT set the base price.
6. **Two hygiene fixes ride along**: the README↔STRATEGY cache-passthrough contradiction (§5.2), and the ADR-334 Rung-2 status note (§5.3).

## 7. What a successor ADR would ratify (when these decisions land)

An ADR-393 (or an ADR-391 amendment) would:
- Ratify the two-objects framework + the substrate-depth tier axis (amending ADR-391 D4/D6 — replacing "commons-scale" with "substrate depth/breadth").
- Fold ADR-392 D8 retention as the first base dimension (the `tier_max_days` wiring).
- Re-label ADR-334 as Phase-2/Rung-2.
- Rewrite `docs/monetization/STRATEGY.md` to the consolidated model (README + COST-MODEL follow).
- Leave numbers demand-gated (no LS product wiring until a base price is set against a real buyer).

**This doc is the framework + the implementation considerations. The successor ADR is the ratification. The numbers are the demand-gated last mile.** The delay ends when §6 is decided.
