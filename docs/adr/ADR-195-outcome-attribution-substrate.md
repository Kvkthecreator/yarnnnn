# ADR-195: Money-Truth Substrate — `_performance.md` as Canonical Home

> **Status**: Phases 1–2 Implemented (substrate target reconciled 2026-04-19). Phases 3–5 Proposed.
> **Date**: 2026-04-19 (v2 rewrite; v1 2026-04-19)
> **Authors**: KVK, Claude
> **Extends**: ADR-181 (Source-Agnostic Feedback Layer), ADR-183 (Commerce Substrate), ADR-187 (Trading Integration), ADR-192 (Write Primitive Coverage Expansion), ADR-193 (Approval Loop)
> **Ratifies**: FOUNDATIONS Axiom 0 (filesystem is the substrate) + Axiom 7 (money-truth is the truth test)
> **Depended on by**: ADR-194 v2 Phase 3 (AI Reviewer consumes `_performance.md`), ADR-196 (autonomous decision loop prioritizes actions by track record)
> **Supersedes**: ADR-195 v1 (2026-04-19) — retracted. v1 specified an `action_outcomes` SQL table as the money-truth ledger; this violates FOUNDATIONS v5.1 Axiom 0 (filesystem is the substrate; semantic content lives in files, not in DB rows). v2 reframes the money-truth substrate as `/workspace/context/{domain}/_performance.md` per domain. The `OutcomeProvider` ABC, per-provider reconcilers (Trading, Commerce), and `back-office-outcome-reconciliation` task all survive; only the write target changes — from SQL INSERT to filesystem append. See "Migration from v1" section for the code refactor plan.

---

## Context

### Why v1 is retracted

ADR-195 v1 shipped an `action_outcomes` SQL table as the reconciled-outcomes ledger. That design was reasonable under the three-layer cognition model of ADR-189, but it conflicts with FOUNDATIONS v5.1 Axiom 0 (filesystem is the substrate; every DB table must be one of four permitted row kinds — scheduling index, audit ledger, credential, ephemeral queue). `action_outcomes` is *none of these*. It holds semantic content — accumulated track records of what the operator has done and what happened — which is the exact category the axiom says must live in files.

The near-miss was instructive: every prior parallel substrate that got collapsed later (`platform_content`, projects, Composer, knowledge tables) followed the same pattern — a DB table holding semantic content, later recognized as belonging in the filesystem. v2 catches it before the shipped code accretes dependents.

v1 Phases 1–2 shipped *live code* (commits `3ad3db5`, `d54d1d6`). The refactor to v2 target preserves ~80% of that code: `OutcomeProvider` ABC, `OutcomeCandidate` TypedDict, `TradingOutcomeProvider` (FIFO-matched realized P&L), `CommerceOutcomeProvider` (paid/refund reconciliation), `back-office-outcome-reconciliation` task, `reconcile_user` dispatcher — all survive. What changes: the `ledger.py` write path. See "Migration from v1" below.

v1 ADR file is overwritten by this v2 (singular-implementation discipline; no dual versions side-by-side).

### The architectural gap (unchanged from v1)

YARNNN today is an **action factory and a context accumulator**. The missing substrate is **money-truth**: every action YARNNN or its agents take must be attributable to a capital outcome, reconciled against the real world, and fed back into the substrates that drive future decisions.

Concretely, today:

- **Trading agent submits a bracket order via ADR-192.** Order executes on Alpaca. Position closes 2 days later. YARNNN has no structural awareness this happened or what the P&L was.
- **Commerce agent creates a discount code.** Customers use it over the week. Revenue attribution to the code is absent.
- **Email agent sends a campaign.** Delivery, open, click data from Resend is not reconciled back.
- **AI Reviewer (ADR-194 v2 Phase 3) has no track record to reason against.** Risk rules are enforced, but capital-EV reasoning collapses into rule-checking without accumulated outcome history.

ADR-181's feedback substrate handles *user corrections* and *YARNNN evaluations*. It does not handle *money-truth reconciliation from external platforms*. The two substrates are complementary — feedback is human / YARNNN judgment; money-truth is the world's judgment.

### What "money-truth" means

Money-truth is the operator's capital reality as platform APIs report it, reconciled into a canonical filesystem substrate:

- **Trading**: filled orders, closed positions, realized P&L, fees.
- **Commerce**: paid orders, refunds, net revenue, subscription events.
- **Email**: delivered, opened, clicked, bounced, conversion-attributed revenue.
- **Future platforms**: same pattern.

Not all outcomes are scalar (e.g., "campaign sent, 3.2% CTR"). The substrate holds both dollar-denominated outcomes and qualitative reconciliation entries where money isn't directly attributable yet.

### The architectural decision (new in v2)

Per FOUNDATIONS Axiom 0, money-truth is filesystem-native. The canonical home for reconciled money-truth is:

```
/workspace/context/{domain}/_performance.md
```

One file per canonical domain. Owned and maintained by the daily back-office reconciler. Consumed by all readers (AI Reviewer, daily-update briefing, YARNNN chat, the operator).

---

## Decision

### 1. Canonical file: `/workspace/context/{domain}/_performance.md`

Per domain. File structure:

```markdown
---
# YAML frontmatter — machine-readable track record
domain: trading
last_reconciled_at: 2026-04-19T08:15:03Z
processed_event_keys:
  - alpaca_order_id:abc123
  - alpaca_order_id:def456
  # ... all idempotency keys seen so far
totals:
  reconciled_event_count: 142
  aggregate_pnl_cents: 325400
  currency: USD
by_action_type:
  trading.submit_order:
    count: 142
    pnl_cents: 325400
    wins: 87
    losses: 55
rolling_30d:
  reconciled_event_count: 38
  pnl_cents: 47200
rolling_90d:
  reconciled_event_count: 121
  pnl_cents: 289300
---

# Trading Performance

Human-readable narrative. Headline numbers, by-action breakdown, recent
notable outcomes with links back to the actions that produced them.

## Recent wins
- 2026-04-17 — AAPL bracket order closed profit $420 (entry $180.20, exit $184.40, 100 shares)
- 2026-04-15 — NVDA partial close profit $280

## Recent losses
- 2026-04-18 — MSFT position closed loss $115 (stop-loss triggered)

## Notes
The body is operator-legible and Reviewer-legible. It is narrative, not
a dump of every event — the full event ledger lives in the frontmatter's
processed_event_keys list. Narrative focuses on what a senior operator
would call out: concentration risk, streaks, outliers, patterns.
```

**Idempotency**: the frontmatter's `processed_event_keys` list is the reconciler's dedup set. No sibling dedup table. Each `OutcomeProvider` declares its `idempotency_key_path` (e.g., `alpaca_order_id`, `ls_event_key`); on each run, the reconciler reads the current key list, filters out already-processed events, reconciles the new ones, and rewrites the file with the extended list.

**Regeneration discipline**: the file is *regenerated idempotently* by the reconciler, not incrementally mutated. This gives us:
- Correctness under provider evolution (schema changes to frontmatter automatically migrate on next reconcile).
- A clear audit story — the reconciler is the only writer.
- Simple recovery — delete the file, next reconcile rebuilds it from platform history (bounded by each provider's history retention).

**Write authority**: the daily `back-office-outcome-reconciliation` task (ADR-195 Phase 2, YARNNN-owned) is the only writer. Agents and humans don't edit — same discipline as `_tracker.md` (ADR-158). If the operator wants to annotate outcomes, they add a note to `/workspace/context/{domain}/notes.md`, not to `_performance.md`.

### 2. No sibling SQL ledger

Dropped. `action_outcomes` table is deleted (Migration 151). There is no parallel DB-side accumulation of outcomes.

This is deliberate and load-bearing:
- **One home for money-truth.** The AI Reviewer, daily briefing, YARNNN, and the operator all read the same file. No "which representation is authoritative today" question.
- **No drift.** Under a dual (SQL + file) system, the two representations inevitably drift — someone updates one and forgets the other, or the sync job fails silently. Deleting the SQL representation eliminates the drift surface.
- **User-legible.** Operators can read their own `_performance.md`. They cannot read an SQL table.

The loss: SQL querying across domains (e.g., "total P&L across all domains last 90 days"). Addressed by: the reconciler writes a rolled-up `/workspace/context/_performance_summary.md` cross-domain aggregate file as part of its daily run. One more file; same substrate.

### 3. `OutcomeProvider` abstraction preserved

v1's `OutcomeProvider` ABC and the two shipped providers (`TradingOutcomeProvider`, `CommerceOutcomeProvider`) are preserved. The abstraction is correct — domain-specific reconcilers are a real structural concern. What changes is the write target.

Provider contract (unchanged):
```python
class OutcomeProvider(ABC):
    provider_name: str
    context_domain: str
    idempotency_key_path: str

    async def reconcile(
        self, user_id: str, client: Any, since: datetime,
    ) -> list[OutcomeCandidate]:
        ...
```

`OutcomeCandidate` shape (unchanged):
```python
class OutcomeCandidate(TypedDict, total=False):
    action_type: str
    action_inputs: dict
    executed_at: datetime
    outcome_label: str
    context_domain: str
    reconciliation_confidence: Literal["high", "medium", "low"]
    outcome_value_cents: int | None
    outcome_currency: str
    outcome_metadata: dict  # MUST carry idempotency key
    reconciliation_notes: str | None
```

What changes: `ledger.py`'s `insert_outcome_candidates` is replaced by a `fold_outcome_candidates` (or renamed variant) that reads the current `_performance.md`, applies the new candidates via the idempotency key list, and writes the file back. Implementation detail — the provider API is stable.

### 4. Back-office task unchanged in shape

`back-office-outcome-reconciliation` task (ADR-195 v1 Phase 2, shipped) stays. Cadence: daily. Owner: YARNNN. Executor: `services.back_office.outcome_reconciliation`. The executor calls `reconcile_user`, which iterates registered providers, collects candidates, folds them into per-domain `_performance.md` files.

The task's markdown report changes from "per-provider inserted/duplicate/invalid counts" to "per-provider appended/duplicate/skipped counts + files written". Same semantic shape; different noun.

### 5. Consumers — all file-readers

Under Axiom 0, consumers read files directly. No service layer over money-truth.

- **AI Reviewer** (ADR-194 v2 Phase 3) — reads `_performance.md` for the proposal's domain to reason about EV.
- **Daily-update briefing** (ADR-195 v2 Phase 4) — reads `_performance.md` frontmatter across domains, emits "Your book this week" section from aggregated totals.
- **YARNNN chat** — surfaces aggregate money-truth signals in the compact index (Phase 4).
- **Operator** — reads directly via the Context surface (ADR-163's four-surface nav).

No `get_performance()` API. No `OutcomeRepository`. Every consumer reads the same file. When the file schema evolves, every consumer picks up the change on next read.

### 6. Feedback actuation (Phase 5)

High-impact outcomes become feedback entries per ADR-181. Concretely: when the reconciler appends an outcome whose magnitude exceeds a threshold declared in `principles.md` or a reasonable default, it also writes a feedback entry into the relevant task's `feedback.md`:

```
Source: system-outcome
Date: 2026-04-19
Action: trading.submit_order (AAPL, 100 shares @ 180.20)
Outcome: closed_profit $420
```

ADR-181's actuation layer reads these entries with the same mechanism it reads user and YARNNN-evaluation entries. No parallel actuation path.

---

## Migration from v1

v1 Phases 1–2 shipped code on `main`. v2 preserves the structure; only the substrate changes.

### What survives as-is (no changes)

- `api/services/outcomes/base.py` — `OutcomeProvider` ABC + `OutcomeCandidate` TypedDict.
- `api/services/outcomes/trading.py` — `TradingOutcomeProvider` FIFO logic.
- `api/services/outcomes/commerce.py` — `CommerceOutcomeProvider` LS order logic.
- `api/services/outcomes/reconciler.py` — `reconcile_user` dispatcher.
- `api/services/back_office/outcome_reconciliation.py` — back-office executor.
- `api/services/task_types.py` entry for `back-office-outcome-reconciliation`.
- `api/services/workspace_init.py` signup scaffolding.

### What changes (Commit 2 of this cycle)

- `api/services/outcomes/ledger.py` — `insert_outcome_candidates` (SQL INSERT) replaced by a filesystem-append function that:
  1. Reads `/workspace/context/{domain}/_performance.md` via the workspace abstraction.
  2. Parses the frontmatter `processed_event_keys` list.
  3. Filters candidates whose idempotency keys are already present.
  4. Folds new candidates into the frontmatter (updates totals, by-action, rolling windows) and body (appends to wins/losses sections).
  5. Writes the file back via the workspace abstraction.
- `compute_since_for_provider` — changes from "last reconciled_at in SQL" to "last_reconciled_at in `_performance.md` frontmatter" (or bootstrap window if file doesn't exist yet).
- `back-office-outcome-reconciliation` executor's report — updates counts wording ("appended/duplicate/skipped" vs "inserted/duplicate/invalid") and names files written.

### What drops (Commit 3 of this cycle)

- `action_outcomes` table — `DROP TABLE` in Migration 151. Zero rows in production (Phase 2 only just shipped; reconciler hasn't run a daily cycle yet at time of this ADR). No backfill needed.

### Verification

- Migration 151 applied → `action_outcomes` gone.
- `reconcile_user` smoke-test invocation against a trading-connected test workspace → `_performance.md` written at `/workspace/context/trading/_performance.md`.
- Second invocation → no duplicate entries; frontmatter `processed_event_keys` list contains all orders; body narrative unchanged.

---

## Impact table (per ADR-191 matrix gate)

| Domain | Impact | Capital-Gain Alignment | Notes |
|--------|--------|------------------------|-------|
| **E-commerce** | **Helps** | Yes, directly | LS order reconciliation produces revenue track record in `/workspace/context/revenue/_performance.md`. Operator sees gross revenue, refund rate, trending products. AI Reviewer (Phase 3) reads this for EV reasoning on commerce proposals. |
| **Day trader** | **Helps** | Yes, directly | Alpaca fills produce P&L track record in `/workspace/context/trading/_performance.md`. Realized P&L, win rate, per-ticker performance. AI Reviewer reads this for EV reasoning on trade proposals. |
| **AI influencer** (scheduled) | Forward-helps | Yes, enabling | Future `EmailOutcomeProvider` produces campaign performance track record. Same substrate, same pattern. |
| **International trader** (scheduled) | Forward-helps | Yes, enabling | Future shipping/commerce providers produce route-level gross margin track records. Same substrate. |

No domain hurt. Gate passes.

---

## Implementation sequence

| # | Phase | Scope | Status |
|---|-------|-------|--------|
| 1 | Ledger + provider ABC | `OutcomeProvider` ABC, `OutcomeCandidate` TypedDict, `TradingOutcomeProvider` FIFO-matched realized P&L, `reconcile_user` dispatcher. | **Implemented 2026-04-19** (v1 shipped this — substrate refactor in v2 Commit 2) |
| 2 | CommerceOutcomeProvider + back-office reconciliation task | `CommerceOutcomeProvider` for LS (revenue + refund). Essential back-office task `back-office-outcome-reconciliation` scaffolded at signup. | **Implemented 2026-04-19** (v1 shipped this — substrate refactor in v2 Commit 2) |
| — | **Substrate refactor (v2 reconciliation)** | Ledger rewrite: SQL INSERT → `_performance.md` append. `action_outcomes` table dropped. | **Targeted for this commit cycle** (Commit 2 + Commit 3) |
| 3 | `_performance.md` schema + narrative body | Rich frontmatter schema (rolling windows, by-action breakdowns, processed-event-key list). Narrative body auto-generated from templates. Cross-domain `_performance_summary.md` roll-up. | Proposed |
| 4 | Daily-update briefing integration | Daily-update reads `_performance.md` frontmatter across domains, emits "Your book this week" section. | Proposed |
| 5 | Feedback actuation + EmailOutcomeProvider | High-impact outcomes emit ADR-181 feedback entries. `EmailOutcomeProvider` for Resend (delivered / opened / clicked / conversion-attributed). Thresholds declared in `principles.md`. | Proposed |

---

## Open questions (deferred to implementation)

1. **Frontmatter schema evolution.** As the file schema grows (more fields, richer rolling windows), how do consumers handle older files? Answer: the reconciler regenerates on every run, so files converge to the current schema within one daily cycle. Readers should tolerate missing fields.
2. **Cross-domain roll-up cadence.** `_performance_summary.md` — same daily cadence as per-domain files, or separate? Defer until Phase 3.
3. **Narrative body length.** Without bounds, the body grows unbounded over years. v2 plan: truncate "Recent wins/losses" to 10 entries; archive older to `/workspace/context/{domain}/_performance-history/{year}.md` (regenerated). Defer to Phase 3.
4. **High-impact threshold for feedback actuation.** Absolute dollar? Percentile? Defer to Phase 5.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-19 | v1 — Initial draft. `action_outcomes` SQL table, `OutcomeProvider` ABC, `TradingOutcomeProvider`, `back-office-outcome-reconciliation` task, five-phase sequence. Phases 1–2 implemented (migration 150 applied, code on `main` at commits `3ad3db5` + `d54d1d6`). |
| 2026-04-19 | v2 — **Full rewrite.** Aligned to FOUNDATIONS v5.1 Axiom 0 (filesystem is the substrate). `action_outcomes` SQL table dropped; money-truth's canonical home is `/workspace/context/{domain}/_performance.md` per domain (YAML frontmatter + narrative body, regenerated idempotently by the reconciler). `OutcomeProvider` ABC and shipped providers (Trading + Commerce) preserved — only the write target changes (SQL INSERT → filesystem append with frontmatter-based idempotency). Phases 1–2 status retained as "Implemented" with the understanding that the substrate refactor (Commit 2) and table drop (Commit 3) are part of this cycle. v1 file overwritten — singular-implementation discipline. |
