# ADR-291: Unified Cost Ledger — `execution_events` as the Single Substrate for LLM Spend

**Status**: Proposed
**Date**: 2026-05-18
**Authors**: KVK, Claude

**Dimensional classification** (FOUNDATIONS v8.5):
- **Substrate** (Axiom 1) — primary. Collapses two parallel cost ledgers into one.
- **Mechanism** (Axiom 5) — secondary. Cost computation moves to the fully-deterministic end of the spectrum; one cache-inclusive function, one markup rule.

**Companion canon**:
- FOUNDATIONS v8.5 Derived Principle 14 (Singular Implementation) — the gate this ADR enforces
- ADR-171 (Token Spend Metering) — universal-ledger commitment preserved; substrate changes
- ADR-172 (Usage-First Billing) — balance as single gate preserved; gate now sees all spend
- ADR-250 (Execution Telemetry) — `execution_events` introduced; this ADR makes it sole canonical
- ADR-258 revised + ADR-275 — Reviewer tool-use loop bounded by `tool_rounds` (8 max)

**Supersedes**:
- ADR-171 §1 single `cost_usd` field design — replaced by cache-inclusive computation reading from richer columns
- ADR-171 §3 `record_token_usage()` as the universal write path — replaced by `record_execution_event()`
- `services/platform_limits.compute_cost_usd()` (cache-agnostic) — deleted; `services/telemetry.compute_cost_usd_inclusive()` is the sole cost function

**Amends**:
- ADR-171 (substrate rename: `token_usage` → `execution_events`; semantic preserved — "universal meter, one number, every LLM call")
- ADR-172 (balance gate now reads `execution_events`; "balance as single gate" semantic preserved and finally true)
- ADR-250 (Phase 2 `execution_events` made load-bearing; Phase 3 daily-spend ceiling unchanged; new derived semantic: this table is the canonical cost substrate, not merely a telemetry side-channel)

**Preserves**:
- FOUNDATIONS v8.5 Axioms 1, 2, 4, 5, 6, 8
- ADR-172 "balance as single gate" commitment (now structurally honest)
- ADR-209 Authored Substrate (no impact — `execution_events` is not workspace_files-backed; it's audit telemetry)
- ADR-258 + ADR-275 Reviewer wake envelope (no impact)
- ADR-289 Phase 1 (BE narrative grouping reads `execution_events.invocation_id`; this ADR adds writers but does not change readers)
- 2x platform multiplier (now applied uniformly across all 7 callers, not just 5)

---

## 1. Context

### The structural finding

The production audit of 2026-05-18 traced an architectural drift in YARNNN's cost-metering substrate. **The system has two parallel cost ledgers that don't gate against the same balance.**

| Concern | Substrate today | Cost computation | Callers |
|---|---|---|---|
| `token_usage` table | Cache-agnostic — only `input_tokens` + `output_tokens` columns | `platform_limits.compute_cost_usd()` — counts `input_tokens` at 2x base, ignores cache_read (Anthropic charges 10%) and cache_create (Anthropic charges 125%) | 5 callers: chat, web_search, specialist, inference, session_summary |
| `execution_events` table | Cache-inclusive — `cache_read_tokens` + `cache_create_tokens` persisted as first-class columns | `telemetry.compute_cost_usd_inclusive()` — full Anthropic-shape cost math at 2x markup | 1 caller: invocation_dispatcher (Reviewer-dispatched recurrences only) |

**Two gates read these tables in mutually exclusive ways:**

```sql
-- Effective balance (services/platform_limits.py::get_effective_balance RPC)
SELECT w.balance_usd - SUM(token_usage.cost_usd) ...  -- DOES NOT see execution_events
```

```python
# Daily spend ceiling (services/telemetry.py::get_daily_spend)
SELECT SUM(execution_events.cost_usd) ...  -- DOES NOT see token_usage
```

### What this produces in practice

1. **The Reviewer reflection loop is the heaviest cost driver in the system** (40 of 55 historical rows; $4.41 of $7.14 billed). It writes only to `execution_events`. **It never debits the user's balance.** A user with `balance_usd = 0.01` can run the Reviewer reflection unchanged.

2. **The daily spend ceiling doesn't see chat / inference / specialist spend.** A user can chat heavily for a day; the ceiling never trips.

3. **Cache-heavy callers are systematically under-billed.** The Reviewer reflection runs against ~90% cache-read input on a typical reflection pass. `compute_cost_usd()` (cache-agnostic) charges the user 2× × `input_tokens × base_rate` — but `input_tokens` for cached calls is *only the non-cached portion*. Anthropic still charges YARNNN 10% × cached_input × base_rate. **For cache-heavy callers under `compute_cost_usd()`, effective markup on real Anthropic cost can dip below 1.0× — i.e., YARNNN loses money.**

4. **The two computation functions disagree on the same input.** A chat call producing identical token counts to a Reviewer reflection produces different `cost_usd` values across the two tables.

### Why ADR-250 didn't already solve this

ADR-250 (2026-05-06) identified §3 verbatim:
> "`token_usage.cost_usd` is cache-agnostic and underreports by ~15–20% on high-cache-hit runs."

ADR-250 introduced `execution_events` with the richer schema as Phase 2. But it stopped short of sunsetting `token_usage` — the two tables coexisted, with `execution_events` framed as "Postgres event ledger" (telemetry-adjacent) and `token_usage` framed as "the meter" (canonical). The framing kept them separate; the audit makes it clear they need to collapse.

### Singular Implementation requirement (FOUNDATIONS DP-14)

Per Derived Principle 14, "Singular Implementation": when one concept is expressed twice, the system has no canonical answer to the question "what does X mean?" Here, **"how much has this user spent this billing period?"** has two answers depending on which table the reader queries. That ambiguity is not a code-quality issue — it's a load-bearing leak in the balance gate.

---

## 2. Decisions

### D1. `execution_events` is the sole canonical cost ledger

Every LLM call across all 7 callers writes exactly one `execution_events` row. The row carries the full cost breakdown: `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_create_tokens`, `cost_usd`, `model`, `caller`, `mode`, `slug`, `agent_run_id`, `duration_ms`, `tool_rounds`, `envelope_load_ms`.

`token_usage` table is DROPPED.

**Caller mapping** to `execution_events.slug`:

| Caller (old `token_usage.caller`) | New `execution_events.slug` | Notes |
|---|---|---|
| `chat` (operator addressed turn) | `addressed` | One row per Reviewer invocation in chat — already used by ADR-289 Phase 1 |
| `reviewer-reflection` | recurrence slug (e.g., `morning-reflection`) | Unchanged — already in `execution_events` |
| `reviewer` (proposal arrival) | recurrence slug or `proposal-arrival` | Unchanged — already in `execution_events` |
| `specialist:designer` (or any `specialist:*`) | `specialist:<role>` | New writer path — promoted from `token_usage` |
| `web_search` | `web-search` | New writer path |
| `recurrence_prompt_inference` | `recurrence-prompt-inference` | New writer path |
| `infer_workspace` | `infer-workspace` | New writer path |
| `infer_context` | `infer-context` | New writer path |
| `session_summary` | `session-summary` | New writer path |

All slugs are domain-meaningful; the slug column does not need a vocabulary registry. ADR-289 Phase 1 BE already groups feed entries by `invocation_id`; promoting these new writers does not change rendering policy (they emit no feed entries today).

### D2. `compute_cost_usd_inclusive()` is the sole cost function

`services/telemetry.compute_cost_usd_inclusive()` (cache-aware, 2x markup) is the single source of cost truth. `services/platform_limits.compute_cost_usd()` (cache-agnostic) is DELETED, not renamed.

**The 2x platform multiplier is encoded in `compute_cost_usd_inclusive()`'s rates** — `_BILLING_RATES` in `telemetry.py` are *user-facing* rates (2× Anthropic). This is consistent with ADR-171's "decoupled rates" principle.

**Singular Implementation honored**: `_BILLING_RATES` exists in exactly one place (`telemetry.py`). The duplicate `BILLING_RATES` table in `platform_limits.py` is DELETED in the same commit.

### D3. `get_effective_balance` RPC reads from `execution_events`

The Postgres RPC `get_effective_balance(p_user_id)` is rewritten to read `execution_events.cost_usd` (replacing `token_usage.cost_usd`). The structural shape preserves:

- Balance = `workspace.balance_usd - SUM(spend since refill anchor)`
- Refill anchor = `workspace.subscription_refill_at` if non-null, else `workspace.created_at`

**One query rewrite, one migration step.** Migration includes the RPC rewrite and the `token_usage` table drop atomically.

### D4. Balance gate now sees Reviewer reflection spend

A direct consequence of D3. Today, a user with `balance_usd = 0.01` can run Reviewer reflection indefinitely. After D3, the reflection's cost debits the same effective balance that the chat gate reads. Balance-as-single-gate (ADR-172) finally becomes structurally true.

**This is the load-bearing fix.** Everything else in this ADR exists to make D4 honest.

### D5. Daily spend ceiling scope unchanged

`get_daily_spend()` already reads `execution_events`. After D1, it sees the full spend surface naturally. No code change to the spend guard.

### D6. No new schema beyond table-drop. No historical preservation.

`execution_events` already has all required columns. The migration is:

1. Rewrite `get_effective_balance(p_user_id)` to read from `execution_events`.
2. `DROP TABLE token_usage CASCADE;` — **no backfill.** The 55 historical rows are dropped with the table.
3. Drop `services/platform_limits.compute_cost_usd` + `BILLING_RATES` constant + `record_token_usage`.

**No new columns. No schema additions. No backfill.** The "two-field ledger" framing from the original session discourse collapses to one field because the breakdown is already persisted as native columns (`input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_create_tokens`) — the implied Anthropic cost is computable from those at any time.

**Rationale for no backfill** (Singular Implementation discipline): preserving 55 historical rows under a derived-slug + `mode='judgment'` mapping would create a second writer-shape semantically distinct from the canonical `record_execution_event` callers. Operators reading historical rows would see slugs like `web-search` and `infer-context` that no live writer produces in that shape — creating downstream ambiguity in admin tooling, analytics, and future readers. The session-discourse intent — *"no dual approach to avoid future ambiguity"* — applies as much to data as to code. Drop the rows; the existing `balance_transactions` table preserves the financial picture (signup grants, top-ups, refills, admin grants) for accounting. Per-call cost lineage for the alpha window is acceptable to lose pre-GA.

### D7. The "anthropic_cost_usd" view is derivable, not stored

If we later want to surface "Anthropic invoice cost" separately from "billed cost" (for transparency or audit), the math is:

```python
anthropic_cost_usd = compute_cost_usd_inclusive(...) / 2.0
```

Or equivalently, a Postgres view if we want it queryable:

```sql
CREATE VIEW execution_events_with_anthropic_cost AS
SELECT *, cost_usd / 2.0 AS anthropic_cost_usd FROM execution_events;
```

**No view created in this ADR.** The pure-arithmetic derivation is honest and doesn't require schema commitment. If/when a billing-transparency UI surface needs it, ship the view then.

### D8. Future cache/optimization changes flow through `compute_cost_usd_inclusive` only

The multiplier rule is now durable: any future Anthropic optimization (extended cache discount rate change, prompt compression, new model tiers) updates `_BILLING_RATES` once and propagates to every caller. There is no second pricing decision to make per optimization. This was the goal stated in the session discourse — durably handled by the substrate collapse.

### D9. Out of scope

The following are explicitly NOT decided here:

- **BYOK** (bring your own API keys) — separately rejected for the YARNNN ICP in the session discourse; not part of this ADR.
- **Mid-loop balance check** (the original "Flaw 2") — overrun bound is ~$0.72 (8 rounds × ~$0.09); not worth a per-call RPC. Revisit only if production data shows real overruns.
- **Pause-on-balance-exhaustion repeat suppression** (the original "Flaw 3") — naturally aligned with this ADR but kept as a follow-on commit (see Phase 3 below) since it's behavior-change in `invocation_dispatcher`, not substrate change.
- **Per-caller multipliers** — single platform-wide 2x preserved. ADR-171's "one rate per model" commitment unchanged.

---

## 3. Implementation phases

### Phase 1 — Substrate collapse (this ADR's core)

Single commit:

1. Migration `170_unified_cost_ledger.sql`:
   - `DROP TABLE token_usage CASCADE;` (no backfill — per D6, historical rows are dropped with the table)
   - Rewrite `get_effective_balance(p_user_id)` RPC to read `execution_events.cost_usd`.
2. Code changes in `services/platform_limits.py`:
   - DELETE `BILLING_RATES` constant.
   - DELETE `compute_cost_usd()` function.
   - DELETE `record_token_usage()` function.
   - DELETE `get_monthly_spend_usd()` and `check_spend_budget()` legacy aliases.
3. Migrate 7 call sites from `record_token_usage()` to `record_execution_event()`:
   - `api/agents/reviewer_agent.py:1306` (reviewer / reviewer-reflection — already writes both; remove `token_usage` write)
   - `api/services/recurrence_prompt_inference.py:121`
   - `api/services/session_continuity.py:145`
   - `api/services/primitives/infer_workspace.py:121`
   - `api/services/primitives/infer_context.py:146`
   - `api/services/primitives/dispatch_specialist.py:344`
   - `api/services/primitives/web_search.py:417`
4. Doc cascade in same commit:
   - This ADR status → Implemented.
   - ADR-171 amendment banner (substrate moved to `execution_events`; semantics preserved).
   - ADR-172 amendment banner (balance gate now reads `execution_events`; commitment now structurally honest).
   - ADR-250 amendment note (Phase 2 made load-bearing).
   - `CLAUDE.md` Billing Model section rewrite.
   - `docs/monetization/STRATEGY.md` + `COST-MODEL.md` rewrite.
   - `docs/monetization/README.md` date + reference update.
   - `docs/database/MIGRATIONS.md` entry.
   - `api/prompts/CHANGELOG.md` — N/A (no prompt change).

### Phase 2 — Flaw 3 cleanup (separate commit)

Suppress repeat material-weight feed emissions when balance stays at zero across multiple scheduler ticks.

`services/invocation_dispatcher.py` balance-exhausted branch: query `execution_events` for the most recent row for `(user_id, slug)`. If `error_reason='balance_exhausted'`, skip feed emission (still write `execution_events` for forensic trail). If the most recent event was a success or a different failure, emit feed entry as normal (the "transition into balance-exhausted" pattern).

One-query check, no schema change. Doc: amend ADR-172 with the suppression rule.

### Phase 3 — Deferred (do not implement)

- Mid-loop balance check (D9 rationale)
- Anthropic-cost view (D7 rationale)
- BYOK (out of session scope)

---

## 4. Validation

### Test gate

New test file `api/test_adr291_unified_cost_ledger.py` asserts:

1. `token_usage` table does not exist post-migration
2. `compute_cost_usd` symbol does not exist in `services.platform_limits`
3. `BILLING_RATES` constant does not exist in `services.platform_limits`
4. `record_token_usage` symbol does not exist in `services.platform_limits`
5. All 7 LLM call sites import `record_execution_event` and call it (grep-based assertion)
6. `get_effective_balance` RPC SQL contains `execution_events`, not `token_usage` (introspect via `pg_get_functiondef`)
7. `compute_cost_usd_inclusive` is the only cost function in `services.telemetry`

### Operator validation

Post-deploy: pick a user with non-zero `balance_usd`, run one Reviewer reflection invocation, verify:

- `execution_events` row written with cache breakdown columns populated
- `get_effective_balance(user_id)` returns `balance_usd - sum(cost_usd including this row)`
- Balance debit visible in admin dashboard
- No `token_usage` table reference anywhere in app logs

---

## 5. Singular Implementation audit

| Concept | Today | After ADR-291 |
|---|---|---|
| "How much has user spent?" | Two answers (depends on table) | One answer: `SUM(execution_events.cost_usd) WHERE user_id = ?` |
| "What does this LLM call cost?" | Two answers (cache-agnostic vs cache-inclusive) | One answer: `compute_cost_usd_inclusive(model, in, out, cache_r, cache_c)` |
| "What gates the user's balance?" | `token_usage` only (misses Reviewer reflection) | `execution_events` (full surface) |
| "Where do I write a new LLM call's cost?" | Decide between two writers | `record_execution_event()` |
| "What does 2× markup apply to?" | Two `BILLING_RATES` constants in two files | One `_BILLING_RATES` in `telemetry.py` |

Five Singular Implementation violations collapse to zero. The substrate gets simpler, not more complex.

---

## 6. Rationale for ADR shape

This ADR is *amendment-shaped*, not supersession-shaped, relative to ADR-171 + ADR-172. The universal-ledger commitment (ADR-171) and balance-as-single-gate commitment (ADR-172) are both preserved — and in ADR-172's case, **finally made structurally honest**. What changes is the substrate the commitments rest on: `token_usage` → `execution_events`.

ADR-250 set up the right substrate. ADR-291 finishes the move.
