# ADR-195: Outcome Attribution Substrate (Money-Truth)

> **Status**: Proposed (2026-04-19)
> **Date**: 2026-04-19
> **Authors**: KVK, Claude
> **Extends**: ADR-181 (Source-Agnostic Feedback Layer), ADR-183 (Commerce Substrate), ADR-187 (Trading Integration), ADR-192 (Write Primitive Coverage Expansion), ADR-193 (Approval Loop)
> **Ratifies**: FOUNDATIONS Axiom 7 — Money-Truth Is the Truth Test
> **Depended on by**: ADR-194 Phase 4 (AI reviewer consumes `_performance.md`), ADR-196 (Autonomous decision loop prioritizes actions by track record)
> **Supersedes (sequencing)**: Original handoff plan queued ADR-195 as "Autonomous decision loop." That is renumbered to ADR-196 per the same sequencing shift noted in ADR-194.

---

## Context

### The architectural gap

YARNNN today is an **action factory and a context accumulator**. The missing substrate is **money-truth**: every action YARNNN or its agents take must be attributable to a capital outcome, reconciled against the real world, and fed back into the substrates that drive future decisions.

Concretely, today:

- A trader's `submit_bracket_order` fires into Alpaca and the proposal closes. Two days later when the trade fills and later closes, *nothing in YARNNN knows whether the trade made money or lost it.*
- An e-commerce operator's `create_discount` creates a coupon in LS. Two weeks later when the coupon has driven (or failed to drive) revenue, *nothing in YARNNN attributes that revenue back to the decision.*
- YARNNN's daily-update briefing says what the team did, not what the team's decisions produced in money-terms.
- The AI reviewer (ADR-194) has `_risk.md` rules and `_operator_profile.md` declared strategy but **no track record** to reason against. It collapses into rule-checking.
- Accumulated context (`/workspace/context/`) compounds by staleness and entity-count. It does not compound by *money-tested truth*. A thesis that produced a losing trade has the same weight in the context files as a thesis that produced a winning trade.

This is a structural gap, not a reporting gap. Reports *view* state. Substrates *shape* decisions. ADR-195 introduces the outcome-attribution substrate as a first-class citizen alongside `action_proposals` and the workspace filesystem — not as a dashboard view over them.

### The axiom this ADR ratifies

FOUNDATIONS Axiom 7 (Money-Truth Is the Truth Test) states three properties:

1. Actions must be attributable to outcomes.
2. Accumulated context is pruned by outcome, not just staleness.
3. Reviewers reason in capital terms.

ADR-195 is the substrate that makes properties (1) and (2) structural. Property (3) is ADR-194's AI reviewer consuming the substrate this ADR builds.

### Why this is a substrate, not a table

The `action_outcomes` table is the ledger. But the substrate is wider — it includes:
- **The ledger** (`action_outcomes` table) — one row per reconciled outcome
- **The reconcilers** (`OutcomeProvider` implementations) — domain-specific adapters that translate platform events into outcome rows
- **The canonical file** (`/workspace/context/{domain}/_performance.md`) — human-readable, agent-readable accumulated track record
- **The consumers** — daily-update briefing, AI reviewer, feedback actuation (ADR-181), context pruning
- **The reconciliation loop** — back-office task owned by YARNNN that sweeps unreconciled actions and resolves them

Treating this as a substrate (not a table) is the difference between "we log outcomes" and "outcomes are how the system learns." The former is reporting. The latter is money-truth as architecture.

---

## Decision

### 1. New table: `action_outcomes`

One row per reconciled outcome. Linked to `action_proposals` when the action went through approval; standalone when it didn't (direct platform tool calls from agent runs or YARNNN).

```sql
CREATE TABLE action_outcomes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,

    -- Linkage (either to a proposal or to a raw action record)
    proposal_id uuid REFERENCES action_proposals(id),
    action_type text NOT NULL,              -- e.g., "trading.submit_bracket_order"
    action_inputs jsonb NOT NULL,           -- the inputs that produced this outcome
    executed_at timestamptz NOT NULL,       -- when the action was taken

    -- Outcome (reconciled)
    outcome_value_cents bigint,             -- signed: positive=gain, negative=loss, NULL=not applicable
    outcome_currency text DEFAULT 'USD',
    outcome_label text NOT NULL,            -- e.g., "closed_profit", "refund_issued", "campaign_revenue", "no_effect"
    outcome_metadata jsonb DEFAULT '{}',    -- domain-specific: fill_price, share_count, attribution_window, etc.

    -- Reconciliation
    reconciled_at timestamptz NOT NULL DEFAULT now(),
    reconciled_by text NOT NULL,            -- "trading-reconciler-v1", "commerce-reconciler-v1", "manual"
    reconciliation_confidence text NOT NULL, -- "high" | "medium" | "low" — how certain is the attribution
    reconciliation_notes text,

    -- Context domain this outcome belongs to (e.g., "trading", "customers", "campaigns")
    -- Enables _performance.md updates and AI reviewer track-record lookups.
    context_domain text NOT NULL,

    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_action_outcomes_workspace ON action_outcomes(workspace_id, executed_at DESC);
CREATE INDEX idx_action_outcomes_proposal ON action_outcomes(proposal_id) WHERE proposal_id IS NOT NULL;
CREATE INDEX idx_action_outcomes_domain ON action_outcomes(workspace_id, context_domain, executed_at DESC);
CREATE INDEX idx_action_outcomes_action_type ON action_outcomes(workspace_id, action_type, executed_at DESC);
```

**Why not extend `action_proposals`:** many outcomes originate from actions that never went through a proposal (direct platform tool calls from headless agent runs, YARNNN-initiated writes). A separate table with an optional FK is cleaner.

**Reversibility tracking:** `outcome_metadata` carries domain-specific reversal info (e.g., `refunded_amount_cents` for a commerce sale, `stop_hit_vs_target_hit` for a trade). Not a first-class column because semantics vary too much per domain.

### 2. `OutcomeProvider` abstraction

Each platform gets a reconciler that knows how to turn platform events into `action_outcomes` rows.

```python
# api/services/outcomes/base.py

class OutcomeCandidate(TypedDict):
    action_type: str
    action_inputs: dict
    executed_at: datetime
    outcome_value_cents: int | None
    outcome_label: str
    outcome_metadata: dict
    context_domain: str
    reconciliation_confidence: Literal["high", "medium", "low"]


class OutcomeProvider(ABC):
    provider_name: str  # "trading-reconciler-v1", etc.

    @abstractmethod
    async def reconcile(
        self,
        workspace: Workspace,
        since: datetime,
    ) -> list[OutcomeCandidate]:
        """
        Pull platform events since `since` and produce OutcomeCandidates.
        Idempotent — reconciler handles its own de-duplication against
        existing action_outcomes rows (e.g., by proposal_id or by a
        provider-specific natural key in outcome_metadata).
        """
```

Initial implementations:
- `TradingOutcomeProvider` — pulls from Alpaca: closed positions (realized P&L), filled orders (entry vs. exit), stop-hit vs. target-hit events
- `CommerceOutcomeProvider` — pulls from LS: order revenue attributed by `metadata.yarnnn_proposal_id` (when available), refund events, subscription-renewal events
- `EmailOutcomeProvider` — pulls from Resend: delivered/opened/clicked/bounced per campaign message

Each provider writes `outcome_metadata` in a domain-specific shape but shares the row schema.

### 3. Reconciliation back-office task

A new essential back-office task owned by YARNNN (per ADR-164 pattern): `back-office-outcome-reconciliation`.

- **Cadence:** daily (recurring)
- **Executor:** `api.services.back_office.outcome_reconciliation:run_reconciliation`
- **Behavior:**
  - For each workspace with connected platforms, run the corresponding `OutcomeProvider.reconcile(since=last_reconciled_at)`
  - Insert new `action_outcomes` rows
  - For each affected `context_domain`, regenerate `/workspace/context/{domain}/_performance.md` from the ledger (see §4)
  - Emit a `feedback.md` entry on high-impact outcomes (loss > threshold, win > threshold) per ADR-181 for actuation
- **Failure mode:** provider errors logged but don't block other providers. Partial reconciliation is valid.

Seeded at signup alongside the other two essential back-office tasks (`back-office-agent-hygiene`, `back-office-workspace-cleanup`).

### 4. Canonical file: `/workspace/context/{domain}/_performance.md`

Auto-generated by the reconciler after each run. Format (markdown with YAML frontmatter):

```markdown
---
domain: trading
last_reconciled: 2026-04-19T14:30:00Z
rolling_30d_pnl_cents: 12400
rolling_30d_trades: 23
rolling_30d_win_rate: 0.61
all_time_pnl_cents: 187500
reconciler: trading-reconciler-v1
---

# Trading — Performance Track Record

## Summary (rolling 30 days)
- P&L: +$124.00
- Trades: 23 (14 winners, 9 losers)
- Win rate: 61%
- Best trade: +$3,200 (AAPL bracket, entry $180 / exit $192)
- Worst trade: -$850 (NVDA stop hit)

## By action type
- `submit_bracket_order`: 18 outcomes, +$142 avg, 67% win rate
- `place_trailing_stop`: 3 outcomes, -$6 avg, 33% win rate  ← underperforming
- `close_position`: 2 outcomes, +$19 avg (manual exits)

## By thesis tag (from action_inputs.rationale_tag when present)
- `momentum-breakout`: 8 outcomes, +$310 avg, 75% win rate  ← edge
- `mean-reversion`: 5 outcomes, -$45 avg, 40% win rate  ← outside edge?
- `earnings-play`: 2 outcomes, +$600 avg  ← small sample

## Recent outcomes (last 5)
- 2026-04-18  submit_bracket_order  AAPL  +$320  (target hit)
- 2026-04-17  submit_bracket_order  NVDA  -$180  (stop hit)
- 2026-04-17  place_trailing_stop   TSLA  -$40   (trail too tight)
- 2026-04-16  close_position        MSFT  +$95   (manual exit)
- 2026-04-15  submit_bracket_order  META  +$210  (target hit)
```

**Consumers:**
- **AI reviewer** (ADR-194 Phase 4) reads this as the track-record input. "Given the operator hit 75% on momentum-breakout and 40% on mean-reversion, this mean-reversion proposal is outside edge."
- **Daily update** pulls headline numbers for the capital-focused briefing section.
- **YARNNN in chat** references outcomes conversationally ("last month you were up 4% on tech — this proposal fits that pattern").

**Write discipline:** the reconciler owns this file. Agents and humans don't edit it — it's regenerated idempotently from the `action_outcomes` ledger on every reconciliation run. Same pattern as `_tracker.md` (ADR-158).

### 5. Integration points

**Into the daily-update task (ADR-161):**
New section injected when `_performance.md` files exist:

```
## Your book this week
- Trading: +$124 (23 trades, 61% win rate). Best: +$320 on AAPL bracket.
- Customers: +$2,400 new MRR. 3 new subs, 1 churn. Net +2.
- Campaigns: "Spring sale" drove $890 (147 opens, 34 clicks, 12 buys).
```

Deterministic rendering from `_performance.md` frontmatter — no LLM cost.

**Into the AI reviewer (ADR-194 Phase 4):**
Prompt reads `_performance.md` as the track-record input alongside `_risk.md` and `_operator_profile.md`. Shape guidance in ADR-194 §5.

**Into feedback actuation (ADR-181):**
High-impact outcomes (configurable thresholds per domain) emit feedback entries. Loss above threshold writes `source: system-outcome` feedback to `/tasks/{slug}/feedback.md` if the action had a task origin. Per ADR-181 Tier 2, accumulated system-sourced feedback actuates workspace mutations (e.g., de-prioritizing action patterns with poor track records).

**Into context domain pruning:**
`_performance.md` is the objective signal for pruning. Entities / theses / patterns associated with poor track records are flagged for review. Exact pruning mechanics are domain-specific and deferred to each context domain's own care (out of scope for this ADR — just exposing the signal).

### 6. Proposal-to-outcome linkage

When a proposal executes via `ExecuteProposal`, the resulting action's identifier is captured in a field the reconciler can later match. For trading: `alpaca_order_id` stored in `action_proposals.execution_result.order_id` → reconciler matches by order_id. For commerce: proposal_id passed as `metadata.yarnnn_proposal_id` on LS entities when the API supports it; when unavailable, best-effort matching by creation timestamp + entity ID.

Rows in `action_outcomes` with a `proposal_id` are authoritative; rows without are best-effort attribution (direct tool calls, etc.). The `reconciliation_confidence` field exposes this distinction.

### 7. What this ADR does NOT do

Out of scope, deferred to follow-on ADRs:

- **Multi-currency normalization** — everything in `USD` for v1. FX conversion deferred.
- **Tax / accounting treatment** — realized vs. unrealized P&L is tracked, but wash-sale rules, cost basis accounting, and tax reporting are explicitly not YARNNN's job.
- **Real-time outcome streams** — reconciliation is daily. Intraday P&L in trading is live-read from Alpaca in the existing dashboard code, not from this substrate.
- **Cross-workspace benchmarking** — "how does your win rate compare to other traders on YARNNN" — privacy boundary, deferred.
- **Manual outcome entry** — v1 only ingests via providers. UI-driven manual entry (e.g., "I made $5K on a deal I closed by phone") is a later surface decision.

---

## Impact table (per ADR-191 matrix gate)

| Domain | Impact | Capital-Gain Alignment | Notes |
|--------|--------|----------------------|-------|
| **E-commerce** | **Helps** | **Yes, directly** | Revenue attribution to specific campaigns, discounts, and product decisions — the core operator question ("what worked?") becomes answerable for the first time. Feeds the daily-update briefing with real dollar amounts. |
| **Day trader** | **Helps** | **Yes, directly** | P&L attribution to specific trades and thesis tags. Win-rate by strategy. Enables the AI reviewer (ADR-194) to reason in EV terms. The single most-asked question ("did my system work this week?") becomes deterministically answerable. |
| **AI influencer** (scheduled) | **Forward-helps** | **Yes, enabling** | When brand-deal revenue + affiliate attribution land, the provider pattern fits directly. Content-piece-to-revenue attribution uses the same `outcome_metadata` shape. |
| **International trader** (scheduled) | **Forward-helps** | **Yes, enabling** | Gross margin by route / counterparty maps to the same `_performance.md` structure. |

No domain hurt. No verticalization — the substrate is shape-generic (one table, one ABC, domain-specific providers). Gate passes cleanly on both verticalization and capital-gain alignment axes.

---

## Implementation sequence

Five phases. Phase 1 ships independently; Phase 2+ can parallel with ADR-194 Phase 3-4.

| # | Phase | Scope |
|---|-------|-------|
| 1 | Ledger + provider ABC | `action_outcomes` table (migration), `OutcomeProvider` ABC, `TradingOutcomeProvider` for Alpaca (highest signal-to-noise domain). Manual `reconcile()` invocation from a test script — no scheduled task yet. |
| 2 | CommerceOutcomeProvider + reconciliation back-office task | `CommerceOutcomeProvider` for LS (revenue + refund reconciliation). Essential back-office task `back-office-outcome-reconciliation` scaffolded at signup. Seeded for existing workspaces via backfill script. |
| 3 | `_performance.md` canonical file | Reconciler regenerates `_performance.md` per domain after each run. YAML frontmatter + human-readable body. Idempotent regeneration from ledger. |
| 4 | Daily-update integration | Daily-update briefing reads `_performance.md` frontmatter and emits deterministic "Your book this week" section. Empty-state: no section when no outcomes yet. |
| 5 | Feedback actuation + EmailOutcomeProvider | High-impact outcomes emit ADR-181 feedback entries. `EmailOutcomeProvider` for Resend (delivered / opened / clicked). Thresholds tunable per-workspace via future `OUTCOMES-POLICY.md` (deferred until we observe real thresholds). |

ADR-194 Phase 4 (AI reviewer reads `_performance.md`) depends on ADR-195 Phase 3. The two ADRs are sequenced:

```
ADR-195 Phase 1 → ADR-195 Phase 2 → ADR-195 Phase 3 → ADR-194 Phase 4
                                 ↘ ADR-195 Phase 4 (daily update)
                                 ↘ ADR-195 Phase 5 (feedback actuation)
```

---

## Render service impact

- **API**: new primitive registrations not required (reconciliation is not a primitive — it's a back-office task executor). `OutcomeProvider` classes live in `api/services/outcomes/`.
- **Unified Scheduler**: picks up `back-office-outcome-reconciliation` via the standard cron-queries-tasks path (same as `back-office-agent-hygiene`). No new env vars.
- **MCP Server**: untouched. Outcomes are not exposed via MCP tools in v1. (Future: `pull_context` with `domain="trading"` should naturally surface `_performance.md` chunks via existing semantic search.)
- **Output Gateway**: untouched.

No env var changes. No Render parity concerns.

---

## Open questions (deferred to implementation)

1. **Reconciliation latency tolerance.** Daily is fine for e-commerce. Traders may want intraday. v1 is daily; v2 may add per-domain cadence.
2. **Outcome idempotency key precision.** For trading: `alpaca_order_id` is clean. For commerce: when LS metadata doesn't carry proposal_id, attribution is heuristic. Document confidence level in `reconciliation_confidence` and accept that v1 commerce has medium-confidence linkage on pre-attribution data.
3. **Historical backfill on new connections.** When an operator connects a new platform with existing history, do we reconcile backward? v1: reconcile forward only (from connection date). Backfill deferred until operators ask.
4. **`_performance.md` size management.** Track record grows unbounded. v1 writes rolling 30d + all-time summary + last 5 detailed. Full ledger in DB; file is a projection. Size never blows up.
5. **Per-task outcome views.** Today outcomes are per-domain. If operators want "how is the Weekly Trading Brief task producing outcomes when its signals are acted on?" that's a different projection. Deferred until demand.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-19 | v1 — Initial draft. `action_outcomes` table, `OutcomeProvider` ABC, `TradingOutcomeProvider` + `CommerceOutcomeProvider` + `EmailOutcomeProvider`, `back-office-outcome-reconciliation` essential task, `_performance.md` canonical file, integration with daily-update + AI reviewer (ADR-194) + feedback actuation (ADR-181). Ratifies FOUNDATIONS Axiom 7. Renumbers original ADR-195 (autonomous decision loop) → ADR-196. |
