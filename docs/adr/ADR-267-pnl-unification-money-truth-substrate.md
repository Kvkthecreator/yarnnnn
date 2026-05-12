# ADR-267 — P&L Unification + Money-Truth Substrate Collapse

**Date:** 2026-05-12
**Status:** Implemented (Commits 1–5 landed in this PR; Commit 6 migrates live workspaces)
**Authors:** KVK, Claude
**Refs:** ADR-195 v2 (Outcome reconciliation substrate), ADR-228 (cockpit four-face), ADR-245 (content-shape registry), ADR-261 / 262 / 263 (recurrence substrate), SCOPE.md (alpha-1 success contract)

---

## Context

The pre-refactor money-truth pipeline was structurally fragmented across substrate, workflow, agent prompts, and visual displays. The 2026-05-12 cross-layer audit ([docs/analysis/pnl-unification-audit-2026-05-12.md](../analysis/) — captured in the commit history of this PR) found three concrete drifts:

1. **Substrate-vs-code drift.** `_performance.md` schema had no `by_signal` block. `TradingOutcomeProvider.reconcile()` read Alpaca fills but never joined them against `action_proposals` to recover signal attribution. Signal_id was carried in proposal.inputs but lost at reconciliation.

2. **Prompt-vs-substrate drift.** Three Reviewer recurrence prompts (`morning-reflection`, `weekly-performance-review`, `quarterly-signal-audit`) mandated per-signal data the substrate didn't provide. Reviewer either stood down silently or hallucinated reconstruction from raw signal/{slug}.yaml files.

3. **FE-vs-substrate drift.** `web/lib/content-shapes/performance.ts` parsed flat YAML keys (`pnl_30d_pct`, `win_rate`, etc.) that the backend never emitted. MoneyTruthFace + PerformanceFace rendered empty-state on every workspace. Bundle-bound `TraderSignalExpectancy` component read an `expectancy_by_signal` field that didn't exist.

Per SCOPE.md, the alpha-1 success contract requires money-truth + cost-truth with per-signal attribution surviving Reviewer Check 4. The pre-refactor pipeline made that contract structurally unsatisfiable.

---

## Decisions

### D1 — Signal attribution is native to the outcome via Alpaca's `client_order_id` round-trip

ExecuteProposal sets `client_order_id = proposal.id` on Alpaca submit. Alpaca persists this field on every order and returns it on every read. `TradingOutcomeProvider.reconcile()` reads `client_order_id` from filled orders, batch-fetches `action_proposals` by id, and extracts `signal_id` from `proposal.inputs`. Native attribution, no heuristic joins, no new DB tables, no schema migration.

Constraint: Alpaca's `client_order_id` field is max 128 chars; our proposal UUIDs are 36 chars. Comfortable headroom.

### D2 — Substrate collapse from three files to one (per domain) + one cross-domain

Old substrate (legacy):
- `/workspace/context/{domain}/_performance.md` (per-domain track record)
- `/workspace/context/_performance_summary.md` (cross-domain aggregate)
- Signal attribution reconstructed at prompt time from `/workspace/context/trading/signals/{slug}.yaml`

New substrate (canonical):
- `/workspace/context/{domain}/_money_truth.md` (per-domain track record + native by_signal block)
- `/workspace/context/_money_truth_summary.md` (cross-domain aggregate)

Rationale for the rename: "_money_truth.md" makes the file's role unambiguous to operators and Reviewer. "_performance.md" was structurally accurate but invited confusion with verdict-quality calibration. The new name aligns with FOUNDATIONS Axiom 8 (Money-Truth) and SCOPE.md's success contract language.

### D3 — `by_signal` block is first-class in frontmatter

Each signal with at least one realized outcome gets a state dict in `_money_truth.md` frontmatter:

```json
{
  "by_signal": {
    "momentum-breakout": {
      "count": 18,
      "value_cents": 95200,
      "wins": 12,
      "losses": 6,
      "rolling_7d": {"count": 3, "value_cents": 12000, "wins": 2, "losses": 1},
      "rolling_30d": {"count": 14, "value_cents": 78400, "wins": 9, "losses": 5},
      "rolling_90d": {"count": 18, "value_cents": 95200, "wins": 12, "losses": 6}
    }
  }
}
```

Per-signal rolling windows are recomputed in lockstep with domain-wide windows on every fold — same `_compute_window()` helper, filtered by `signal_id`. Events without `signal_id` (manual trades, pre-attribution submissions) contribute to totals + by_action_type but skip `by_signal` — degrading gracefully without fabricating attribution.

### D4 — Reviewer prompts read `by_signal` from frontmatter directly

All four prompts that previously demanded per-signal reasoning (`morning-calibration`, `morning-reflection`, `weekly-performance-review`, `quarterly-signal-audit`) now read `by_signal` from `_money_truth.md` frontmatter directly. No reconstruction. The reconciler computes per-signal windows at fold time; the Reviewer surfaces and judges them.

This closes the audit finding (A3 in the Cluster 2 audit, 2026-05-12): Reviewer no longer self-quantifies thresholds per cycle. Identical evidence produces same verdict shape.

### D5 — Cockpit faces consume canonical substrate

MoneyTruthFace reads `_money_truth_summary.md` by default (bundle override: per-domain `_money_truth.md`). Renders Net 7d/30d/90d windows + per-signal attribution table when `by_signal` has entries. Empty-state preserved for cold-start. Cost-truth column shape declared in `deriveNetMetrics()` (returns `cost_cents: undefined` until cost-truth integration lands).

PerformanceFace substrate path updated to canonical `_money_truth_summary.md`. Reviewer calibration headline rendering unchanged.

### D6 — TraderSignalExpectancy component deleted

Per Singular Implementation: no parallel components for the same concern. The dead bundle component (read fields the backend never emitted) is replaced by native per-signal rendering in MoneyTruthFace. Operator gets one place to read signal P&L, not two.

### D7 — Cost-truth integration deferred to follow-on

The data layer is logged in `token_usage` table (ADR-171) and rolled up via `verify.py --cost` CLI. Surfacing it in `_money_truth.md` frontmatter and the cockpit faces is the natural follow-on. `deriveNetMetrics()` declares the shape (`gross_cents`, `cost_cents`, `net_cents`) so consumers branch on `cost === undefined` until the integration arrives. Tracked separately because the data join requires reconciler-side computation of platform cost per domain over rolling windows.

---

## Implementation

Six commits, each independently revertable, each ending green:

| # | Scope | Files touched | Commit |
|---|---|---|---|
| 1 | Signal attribution native to outcomes (client_order_id round-trip + OutcomeCandidate.signal_id) | alpaca_client.py · base.py · trading.py · propose_action.py · platform_tools.py | `b5f6664` |
| 2 | `_money_truth.md` substrate shape + by_signal block; rename across ledger.py | ledger.py · reconciler.py · __init__.py | `d9fce77` |
| 3 | Reviewer + System Agent prompt re-grounding | cockpit_awareness.py · reviewer_agent.py · tools_core.py · review_proposal_dispatch.py · _recurrences.yaml · CHANGELOG.md | `84a3100` |
| 4 | Cockpit faces consume canonical substrate; delete dead TraderSignalExpectancy | MoneyTruthFace.tsx · PerformanceFace.tsx · money-truth.ts (renamed from performance.ts) · registry.tsx · SURFACES.yaml | `ca80128` |
| 5 | Documentation sweep + this ADR | ADR-267 · WORKSPACE.md cross-refs · BOOTSTRAP.md note · ALPHA-1-PLAYBOOK §3A.7 update | this commit |
| 6 | Legacy cleanup + live workspace migration | Migration script · purge of `_performance.md` / `_performance_summary.md` on alpha-trader-2 + kvk | next commit |

---

## Supersedes / Amends

- **Amends** ADR-195 v2 — outcome reconciliation substrate paths renamed (`_performance.md` → `_money_truth.md`); per-signal attribution becomes first-class via `by_signal` block.
- **Amends** ADR-228 — cockpit four-face contract preserved; substrate paths the faces read updated to canonical money-truth surfaces.
- **Amends** ADR-242 — alpha-trader bundle face overrides preserved; `TraderSignalExpectancy` component deprecated and deleted (per-signal rendering now native in MoneyTruthFace).
- **Amends** ADR-245 — `performance` content shape replaced by `money_truth` shape with proper JSON-frontmatter parser.
- **Preserves** ADR-194 v2, ADR-258, ADR-263, ADR-264 — Reviewer apparatus, primitives surface, recurrence mode, substrate-canonical-world principle all unchanged.

---

## Validation

**Unit-test gates** (api-local, no DB):
- Commit 1: 4 sanity checks (client_order_id param presence on 3 submit functions, FIFO 4-tuple return shape, cross-signal first-match attribution, no-signal degradation).
- Commit 2: 5 sanity checks (path canonicalization, `_init_money_truth` includes by_signal, `_apply_entries` buckets signal-attributed events, per-signal rolling windows populated, render output contains per-signal section, frontmatter JSON valid).

**FE typecheck:** `npx tsc --noEmit` clean across web/ after Commit 4.

**Integration gate (deferred to Commit 6):** Run `reconcile_user` against alpha-trader-2 with a real paper trade. Verify:
1. Outcome carries `signal_id` recovered from proposal lookup.
2. `_money_truth.md` written at canonical path with `by_signal` block populated.
3. Cockpit's MoneyTruthFace renders Net + per-signal table.
4. `weekly-performance-review` recurrence reads `by_signal` directly.

---

## What this commits us to

- **Operator-at-a-glance signal P&L** — one file, one face, one table. The alpha-1 success contract per SCOPE.md (per-signal attribution surviving Reviewer Check 4) becomes structurally satisfiable.
- **Deterministic Reviewer reasoning** over per-signal performance. No self-quantification, no reconstruction. Identical evidence → same verdict shape.
- **One canonical money-truth surface** per workspace domain. No dual-file fragmentation.
- **Native attribution** — proposal-to-outcome relationship is structural via Alpaca's `client_order_id`, not heuristic via (symbol, qty, time) joins.

## What we explicitly defer

- **Cost-truth integration into `_money_truth.md` frontmatter.** Tracked in follow-on; shape declared in `deriveNetMetrics()`.
- **Commerce parallel** — `CommerceOutcomeProvider` doesn't carry signal attribution today (no equivalent of trading signals in commerce flow). The shape supports it; when alpha-commerce reaches operational state, the per-channel attribution gets the same first-class treatment.
- **Multi-currency aggregation** in `_money_truth_summary.md`. Alpha-1 is USD-only; multi-currency is a future ADR.
