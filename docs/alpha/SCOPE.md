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

## Authority + authorization (operator-on-behalf invariant)

A note on how Claude (main session OR alpha-operator subagent) interacts with these workspaces, since smoke tests + recurring rituals will both surface state-mutating actions:

**Architectural authority** (the levers that exist) lives in [CLAUDE-OPERATOR-ACCESS.md §"Mode-to-discretion mapping"](./CLAUDE-OPERATOR-ACCESS.md#mode-to-discretion-mapping). Mode 1 (headless API + service key) carries broad capability — including approve/reject + chat-initiated invocation + harness mutation.

**Invocation authorization** (which lever Claude pulls when) is gated separately. Two paths to invoke a state-mutating capability without per-turn confirmation:

1. The capability has a **standing authorization** entry in [CLAUDE-OPERATOR-ACCESS.md §"Standing authorizations"](./CLAUDE-OPERATOR-ACCESS.md#standing-authorizations). KVK explicitly grants these; they're tracked with date, subject (which Claude session — main vs subagent), capability, and revocation pattern. Standing grants are read literally — Claude does not extend their scope, broaden their subject, or carve out exclusions the granter did not author. As of 2026-04-30 there's one active grant: the alpha-operator subagent's order-approval authority on alpha accounts.
2. KVK gives an **explicit per-turn imperative** in the current message ("fire trade-proposal-2", "approve proposal abc-123").

A diagnostic statement about what Claude *can* do (architectural authority) does NOT constitute invocation authorization. This distinction was hardened into the docs after a 2026-04-30 smoke-test exchange where Claude conflated the two; the §axiom in CLAUDE-OPERATOR-ACCESS.md is now the canonical resolution.

For state-mutating action chains, gate against the chain's max-mutation level, not the immediate HTTP call. Firing `trade-proposal-2/run` is one HTTP call but the chain can end at "real paper Alpaca order" if Reviewer auto-approves under `bounded_autonomous` — gate against the broker order. The 2026-04-30 grant covers approve actions taken by the alpha-operator subagent; it does not cover firing recurrences from any session, and it does not cover any action by the main Claude Code session.

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

## Cost-truth — minimum viable rollup

The `token_usage` table (ADR-171 universal ledger) records every LLM call with a `caller` field, `metadata->>'slug'`, and token counts at billing rates (2× Anthropic API).

**Shipped (2026-04-30, alongside this doc)**: `verify.py --cost [--cost-days N]` reads `token_usage` for a persona and prints a three-section rollup:

1. **Window total** — total cost + token counts over the window, daily average, projected monthly cost.
2. **By day** — calendar-day breakdown so spikes are visible.
3. **By caller × recurrence × shape** — which recurrences are the cost drivers, ranked by total spend.

The rollup function lives at `api/scripts/alpha_ops/_shared.py::fetch_cost_rollup()`. It's the single source of cost-truth. Anything else that needs this number — a future cockpit element, a future `/api/workspace/cost` endpoint, the alpha-operator subagent — reads it. Singular implementation: don't reimplement the SQL anywhere.

**What's not in the rollup yet** (deliberately deferred; named so they're not lost):

- **Render service calls** (ADR-118). The `yarnnn-render` Docker service tracks per-call usage but isn't writing to a queryable table the way `token_usage` is. Render calls are a smaller cost contributor than LLM tokens — adding them when the pattern proves load-bearing.
- **Supabase IO** (DB CPU, storage, egress). Negligible for alpha; relevant only at scale.
- **Cockpit surface**. The CLI rollup is enough for alpha-1 weekly reports. A cockpit element is the eventual home but not blocking the contract evaluation.

The contract evaluation at end of paper-discipline phase compares **money-truth (`_performance.md` cumulative net P&L) vs. cost-truth (verify.py --cost --cost-days 90 total)**. Both numbers are now readable; the OS passes when the first is greater.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-30 | v1 — Initial scope decision. Trading-only + money-truth + cost-truth contract + alpha-commerce parked. Authored after the post-refactor-wave readiness pass (2026-04-29 observation note + Pass 1–4 alpha-doc refresh + Bug 1 + Bug 2 fixes). |
| 2026-04-30 | v2 — Added §"Authority + authorization (operator-on-behalf invariant)" cross-linking the new §axiom + §"Standing authorizations" sections in CLAUDE-OPERATOR-ACCESS.md. Same-day hardening of the architectural-authority vs invocation-authorization distinction triggered by the smoke-test exchange. Notes the active 2026-04-30 standing grant for order approval on alpha accounts. |
| 2026-04-30 | v2.1 — Correction. The v2 §"Authority + authorization" wording understated how literally standing grants must be read, then the same Claude turn's CLAUDE-OPERATOR-ACCESS.md grant entry over-extended KVK's grant text on both subject (claimed main session covered when only the subagent was) and capability (carved out exclusions KVK did not author). Pattern caught by KVK same session. The §"Authority + authorization" body now names the literal-reading rule explicitly: Claude does not extend subject, capability, or carve-outs of standing grants. |
