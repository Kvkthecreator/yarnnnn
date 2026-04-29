# Alpha-1 Scope — trading-only, money-truth + cost-truth as success contract

> **Status**: Canonical scope decision for Alpha-1 testing. Locks in 2026-04-30.
> **Read after**: [INDEX.md](./INDEX.md) and before any other alpha doc.
> **Rule**: This doc names what alpha-1 *is* and *isn't*. If a request lands that conflicts with this scope, defer it (don't quietly absorb).

---

## What alpha-1 is

A test of the YARNNN agent OS — its substrate, dispatcher, primitive matrix, cockpit, and persona/program registry — under one operator class: **a systematic retail trader running on Alpaca paper, with strategy variation across personas**.

Alpha-1 deliberately does *not* test the agent OS for a second domain (commerce, prediction markets, DeFi, content ops) until it passes the trading test. Why: a single domain run end-to-end with money-truth + cost-truth is harder than two domains run halfway, and the failure modes are sharper.

---

## The success contract

The agent OS passes alpha-1 when **two truths converge**:

1. **Money-truth** — accumulated trading P&L net of broker commissions is positive over a rolling 90-day window across at least one persona, with per-signal attribution that survives Reviewer Check 4 (recent expectancy guardrail per ADR-194 v2). `_performance.md` is the substrate that carries this; ADR-195 v2 defines its shape; `back-office-outcome-reconciliation` writes it.

2. **Cost-truth** — the platform cost (LLM tokens + render service calls + DB IO) of running the operator's loop is **less than the money-truth gain over the same window**. If the loop costs $40/month in API + render and produces $30/month in net trading P&L, the OS is not yet a viable agent OS for this operator class — it's a more expensive trading desk. Cost-truth needs a per-workspace daily rollup that the operator can read alongside `_performance.md`.

Both truths are required. Either one alone is unfalsifiable: positive P&L without cost-truth lets us hide a money-losing platform behind a winning trader; cost-truth without money-truth lets us hide an unprofitable trader behind an efficient platform.

The 90-day window is the floor — the early phases (observation, paper discipline) per `docs/programs/alpha-trader/MANIFEST.yaml` accumulate the substrate that makes the 90-day measurement meaningful. The contract evaluates at end of paper-discipline phase, not before.

---

## Persona variation discipline

Trading-only ≠ one persona. The current registry has two, and both are valid alpha-1 stress tests:

| Persona | Strategy | Rationale |
|---|---|---|
| `alpha-trader` | Simons-inspired systematic (5-8 signals, mechanical execution, no narrative) | Hardest stress test for the discretion ladder — the persona forbids most operator overrides. |
| `alpha-trader-2` | Stat-arb pairs (cointegration-driven, longer holding periods) | Different signal cadence, different risk model, same OS infrastructure. Tests that the OS isn't accidentally fitted to one strategy. |

Both run `program=alpha-trader` per ADR-230 D1 — same bundle, different operator personas. This is the OS-agnosticism test: if we have to fork the bundle for each strategy, the OS isn't actually agnostic; if both run from the same bundle and produce different valid loops, it is.

Future trading personas may be added (e.g., options-overlay, momentum-only, regime-switching). Each lands as a row in `personas.yaml` with `program: alpha-trader`. The bundle does *not* fork until a strategy genuinely needs different substrate (different oracle, different recurrence shape) — at which point the question is whether to fork to a sibling bundle (`alpha-trader-options`) or extend the existing one. That decision waits.

---

## What's parked

- **`alpha-commerce` activation** — bundle stays `status: deferred` per ADR-224. We have a real KVK commerce hypothesis and a fully-shipped substrate, but activating it now competes with trading attention and dilutes the success contract. Re-evaluate after alpha-1 closes.
- **Cross-program operators** — one operator running both `alpha-trader` and `alpha-commerce` in the same workspace. Architecturally supported per ADR-230 (one workspace, multiple `personas.yaml` rows mapped to different programs). Not exercised in alpha-1.
- **Live capital flip** — Phase 2 of the program manifest's phase progression. Locked behind paper-discipline phase gate; not in alpha-1 scope.

These are *parked*, not abandoned. The bundle/manifest/persona machinery for each remains in the repo and the registry. We're choosing where attention lands, not deleting capability.

---

## What this changes about prior alpha docs

Nothing structurally. ALPHA-1-PLAYBOOK.md already centers on trading; this doc names the *exclusive* commitment + adds cost-truth to the success contract. Specifically:

- **ALPHA-1-PLAYBOOK §3B** (alpha-commerce persona spec) stays in the doc as preserved intent — it'll be the starting point if/when commerce reactivates.
- **DUAL-OBJECTIVE-DISCIPLINE.md** Objective B (product/persona) framing remains valid; cost-truth is a third objective dimension that lives alongside, not replaces.
- **personas.yaml** retains the `alpha-commerce` row (the commerce workspace exists, has a connected platform, has YARNNN scaffolded). The row's `expected:` invariants document the unactivated state; we don't maintain them as a green-bar requirement.

---

## Cost-truth — gap to close

Naming this so it's a known commitment, not a footnote:

The `token_usage` table (ADR-171 universal ledger) records every LLM call with a `caller` field and token counts at billing rates (2× Anthropic API). What's missing for alpha-1:

1. A per-workspace daily rollup that an operator can read — by workspace, by day, totaled across all callers (`recurrence`, `chat`, `reviewer`, `back-office`).
2. A per-recurrence rollup so the operator can see which recurrences are expensive (e.g., `signal-evaluation` running 5 tool rounds × 5 tickers vs. `pre-market-brief` running 1 round once).
3. A surface that carries this — a CLI flag on `verify.py` is the cheapest first step; a cockpit element is the eventual home, but not blocking for alpha-1.

Render service calls (ADR-118 `render_usage` table) and Supabase IO are smaller cost contributors but should land in the same rollup for honesty. The thin shape: one number per workspace per day, broken down by source, expressed in dollars.

This gap is named here. The commit closing it ships the rollup; this doc points at it once it lands.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-30 | v1 — Initial scope decision. Trading-only + money-truth + cost-truth contract + alpha-commerce parked. Authored after the post-refactor-wave readiness pass (2026-04-29 observation note + Pass 1–4 alpha-doc refresh + Bug 1 + Bug 2 fixes). |
