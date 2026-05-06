# ADR-250: Execution Telemetry — Sentry + Postgres Event Ledger + Spend Guard

> **Status**: **Proposed**
> **Date**: 2026-05-06
> **Authors**: KVK, Claude
> **Canonical reference**: [docs/architecture/observability.md](../architecture/observability.md)

---

## Context

On 2026-05-04, the `track-universe-2` recurrence ran 12 tool rounds three times in one day (1am, 4am, 8am PT), consuming ~700K–755K input tokens per run. By 2026-05-05 01:07 PT, the Anthropic API returned HTTP 400 `credit balance too low`, silently failing all subsequent invocations for the rest of the day. No alert fired. The operator discovered it post-hoc by cross-referencing Anthropic's billing dashboard against `agent_runs`.

A comprehensive audit (session 2026-05-06) identified five structural gaps:

1. **Failed runs create no DB record.** Invocations that fail before or during generation (balance exhaustion, capability unavailable, unhandled exception) emit only a narrative entry and a stdout log line. They do not produce an `agent_runs` row, so admin queries and analytics are blind to them.

2. **No structured error preservation.** Error reasons exist only as prose in narrative body text or ephemeral Render stdout logs (7-day retention). There is no queryable error field.

3. **Cost is post-hoc and inaccurate.** `token_usage.cost_usd` is cache-agnostic and underreports by ~15–20% on high-cache-hit runs. Per-run cost is not stored in `agent_runs`. Per-task cost attribution requires manual correlation.

4. **No circuit breaker.** Nothing checks daily spend before dispatching. The Anthropic 400 was the de facto circuit breaker — ungraceful and invisible until it fires.

5. **Unhandled exceptions are ephemeral.** Python exceptions in the scheduler and dispatcher go to stdout only. Render retains logs for ~7 days. There is no persistent, searchable error record.

---

## Decision

Adopt a three-layer execution telemetry stack. All three layers are zero marginal cost at current alpha scale.

### Layer 1 — Sentry SDK (errors + performance traces)

Wire Sentry into FastAPI (API service + Unified Scheduler) and Next.js (web). Every unhandled exception is captured with: full stack trace, user_id, request context, environment tag. Performance traces capture end-to-end invocation duration with span breakdown.

**Scope:**
- `sentry-sdk[fastapi]` added to `api/requirements.txt`
- `@sentry/nextjs` added to `web/package.json`
- `sentry_sdk.init()` called at startup in `api/main.py` and `api/jobs/unified_scheduler.py`
- `user_id` set on Sentry scope at every invocation boundary
- `task_slug`, `shape`, `tool_rounds` attached as Sentry tags on invocation spans
- `SENTRY_DSN` env var on API + Unified Scheduler + web (no cost until >5K errors/month on free tier)

**What this catches that nothing else does:**
- Every unhandled exception with full context, permanently, searchable
- Email alert on first occurrence of a new error class (e.g., first Anthropic 400)
- Performance regression detection (invocation taking 4× longer than baseline)

### Layer 2 — `execution_events` table (Postgres-native event ledger)

A dedicated table that is the authoritative structured record of every invocation attempt — success, failure, and early exit alike. Replaces the fragmented pattern of writing partial data to `agent_runs.metadata`, `token_usage`, and narrative entries.

**Schema (migration 165):**

```sql
CREATE TABLE execution_events (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid NOT NULL REFERENCES auth.users(id),
    slug            text NOT NULL,                    -- recurrence slug
    shape           text NOT NULL,                    -- deliverable | accumulation | action | maintenance
    trigger_type    text NOT NULL,                    -- scheduled | manual | back_office
    status          text NOT NULL,                    -- success | failed | skipped
    error_reason    text,                             -- balance_exhausted | capability_unavailable | exception | timeout | NULL
    error_detail    text,                             -- exception message, truncated to 2000 chars
    tool_rounds     int,
    input_tokens    bigint,
    output_tokens   bigint,
    cache_read_tokens bigint,
    cache_create_tokens bigint,
    cost_usd        numeric(10,6),                   -- cache-inclusive, accurate
    duration_ms     int,
    agent_run_id    uuid REFERENCES agent_runs(id),  -- NULL for failures that produce no run row
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_execution_events_user_date ON execution_events (user_id, created_at DESC);
CREATE INDEX idx_execution_events_slug ON execution_events (user_id, slug, created_at DESC);
CREATE INDEX idx_execution_events_status ON execution_events (status, created_at DESC);
```

**Write discipline:**
- Every invocation attempt writes one row, regardless of outcome
- Written at invocation completion (success or failure) in `invocation_dispatcher.py`
- For early-exit failures (balance, capability), written at the exit point with `status='failed'` and the appropriate `error_reason`
- `cost_usd` computed using cache-inclusive formula (see Layer 3 cost computation below)
- `agent_run_id` is NULL for failures that never reach generation; non-NULL for delivered runs

**Cost formula (cache-inclusive):**
```python
cost_usd = (
    (input_tokens / 1_000_000) * input_rate        # fresh input at full rate
  + (cache_read_tokens / 1_000_000) * input_rate * 0.10   # cache read at 10%
  + (cache_create_tokens / 1_000_000) * input_rate * 1.25 # cache write at 125%
  + (output_tokens / 1_000_000) * output_rate
)
```

This replaces `platform_limits.compute_cost_usd()` which is cache-agnostic and underreports. The `token_usage` table's `cost_usd` field remains as-is (backwards-compatible historical record); `execution_events.cost_usd` is the accurate forward-looking field.

**What this enables that nothing else does:**
- "Which task cost the most this week?" — one SQL query on `execution_events`
- "How many invocations failed and why?" — queryable by `status` + `error_reason`
- "What did that specific run cost?" — per-row `cost_usd` with cache included
- Admin dashboard per-task cost column — reads directly from `execution_events`
- Alpha operator ritual — cost-per-task in the weekly report

### Layer 3 — Daily spend guard (circuit breaker in dispatcher)

Before dispatching any generative invocation (shape: deliverable, accumulation, action), the dispatcher checks today's spend from `execution_events`. If the sum of `cost_usd WHERE created_at >= today AND user_id = X` exceeds a configurable daily ceiling, the invocation is skipped with `status='skipped'`, `error_reason='spend_ceiling'`, and a narrative entry is emitted.

**Configuration:**
- Ceiling declared as `DAILY_SPEND_CEILING_USD` env var (default: `10.0`)
- Per-user override possible via workspace AUTONOMY.md `spend_ceiling_usd:` field (future)
- Maintenance shape (back-office tasks) is exempt — zero LLM cost, should not be blocked
- Manual/addressed triggers (user-initiated from chat) skip the ceiling check and emit a warning instead of blocking

**Behavior:**
```
[DISPATCH] Daily spend ceiling check: $8.43 / $10.00 today
[DISPATCH] ✗ track-universe-2: spend ceiling reached ($10.00/day). Skipping.
```

Narrative entry emitted with `role='system'`, `weight='routine'`, summary: `"Spend ceiling reached — {slug} skipped. {$X.XX} of {$Y.00} daily limit used."` — visible in the operator's chat surface.

**What this prevents:**
- The May 2026 incident: `track-universe-2` would have been blocked after the first or second run of the day, not after balance hit zero
- Silent runaway loops: operator sees a narrative entry on the same surface they check for proposals

---

## Implementation Plan

### Phase 1 — Sentry wiring (API + Scheduler + Web)
- Add `sentry-sdk[fastapi]` to `api/requirements.txt`
- Add `@sentry/nextjs` to `web/package.json`, run `npx @sentry/wizard@latest -i nextjs`
- `sentry_sdk.init()` in `api/main.py` (FastAPI lifespan) and `api/jobs/unified_scheduler.py` (top of `__main__`)
- Set `SENTRY_DSN` env var on all 4 Render services (free DSN from sentry.io)
- Attach `user_id`, `task_slug`, `shape` as Sentry scope tags at every invocation boundary in `invocation_dispatcher.py`

### Phase 2 — `execution_events` table + write path
- Migration 165: create table + indexes
- `api/services/telemetry.py`: new module, single function `record_execution_event(...)` — wraps the insert, non-fatal (try/except, logs on failure, never raises)
- Wire into `invocation_dispatcher.py`:
  - Success path: call after `agent_runs` update, with `agent_run_id` populated
  - Balance-exhausted path: call at early exit with `status='failed'`, `error_reason='balance_exhausted'`
  - Capability-unavailable path: call at early exit with `status='failed'`, `error_reason='capability_unavailable'`
  - Unhandled exception path: call in the outer except block with `status='failed'`, `error_reason='exception'`, `error_detail=str(e)[:2000]`
- Update `api/routes/admin.py` `/execution-stats` to include per-task `cost_usd` sum and `failed_count` from `execution_events`

### Phase 3 — Daily spend guard
- `api/services/telemetry.py`: add `get_daily_spend(user_id, client) -> float` — sums `execution_events.cost_usd` for today UTC
- Wire into `invocation_dispatcher.py` at the top of the generative dispatch path, after capability check, before generation
- Skip maintenance shape (back-office tasks exempt)
- Write `execution_events` row with `status='skipped'`, `error_reason='spend_ceiling'` when blocked
- Emit narrative entry with spend summary
- Add `DAILY_SPEND_CEILING_USD` to API + Unified Scheduler env vars on Render

### Phase 4 — Admin dashboard update
- Add `cost_usd` column to per-task breakdown table in admin frontend
- Add `failed_count` and `skipped_count` to per-task rows
- Add daily spend rate card (today's spend vs ceiling)

---

## What This Does NOT Do

- **Real-time cost meter during a run** — not implemented. Cost is recorded at completion. A run that's mid-execution is not metered in real time.
- **Per-tool cost breakdown** — not implemented. Cost is per-invocation, not per-tool-call.
- **External log aggregation** (Axiom, Datadog, Grafana Loki) — not needed at current scale. Render stdout + Sentry covers the error case. Postgres covers the analytics case.
- **SMS / push alerting** — Sentry email alerts are sufficient for alpha scale. PagerDuty-style on-call is not warranted.
- **Multi-tenant spend isolation** — spend ceiling is per-user from day one (user_id-scoped), but UI to configure it per-user is deferred.

---

## Dimensional Classification (FOUNDATIONS v6.0)

- **Substrate** (Axiom 1): `execution_events` table is a new substrate layer — every invocation leaves a permanent attributed record
- **Mechanism** (Axiom 5): Spend guard is a deterministic zero-LLM gate at the mechanical end of the spectrum
- **Channel** (Axiom 6): Sentry is an operator-facing external channel for error visibility; narrative entry is the in-product channel for spend ceiling events

---

## Supersedes / Amends

- **Amends** ADR-141 (execution layers): Layer 1 (mechanical/scheduler) gains the spend guard; Layer 2 (generation) gains structured telemetry emission
- **Amends** ADR-164 (back-office tasks): maintenance shape explicitly exempt from spend ceiling
- **Amends** ADR-202 (external channel discipline): Sentry is a pointer channel (error → Sentry alert → operator acts in cockpit), consistent with ADR-202's no-replacement-UX principle
- **Does not supersede** `token_usage` table — it remains as the billing ledger; `execution_events` is the execution telemetry ledger (different concern)

---

## Canonical Reference

[docs/architecture/observability.md](../architecture/observability.md) — start here for all future observability work. This ADR records the decision; that document is the living operational reference.
