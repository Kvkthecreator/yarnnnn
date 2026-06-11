# Survival-audit queries — alpha-trader-2 longitudinal soak

> **Purpose**: the reusable instrument for the periodic survival read ([`TRACKING-LOG.md`](TRACKING-LOG.md), [`../LONGITUDINAL-TRACKING.md`](../LONGITUDINAL-TRACKING.md) §6 rule 6). Built demand-pull from the live soak — not speculative. Each query is a standalone, copy-pasteable psql block; run them in order, paste results into a dated TRACKING-LOG entry, deploy-marker-stamped.
>
> **Survival before improvement.** These queries answer "is the operation surviving tenure?" — NOT "is it improving?" (that's the curve read, NEXT-5). A survival pass is clean only when checks 1–5 are all green for the window.
>
> **Subject**: `user_id = 29a74c63-0c9c-4998-b8bb-56dd0d810a4e` (alpha-trader-2).
>
> **Connection**: `PSQL` from [`../../database/ACCESS.md`](../../database/ACCESS.md) — extract with `grep -oE 'postgresql://[^"]+' docs/database/ACCESS.md | head -1`.

```bash
PSQL='postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require'
UID2='29a74c63-0c9c-4998-b8bb-56dd0d810a4e'   # NB: avoid bare $UID in zsh (reserved) — use UID2 or inline the literal
```

---

## Check 1 — Silent-wake machine fault (S9)

**The seam that detects machine-faults before a judgment read.** A `mode='judgment'` wake that completed with `status='success'` but produced **no output tokens** is a silent-wake fault — the Reviewer was invoked, the run was recorded as success, but nothing was actually generated (the `reviewer_returned_none` class, fixed structurally in `services/wake.py` but still worth monitoring). Mechanical-mode wakes legitimately have NULL output_tokens (zero-LLM by design) — they are NOT faults, so the `mode='judgment'` filter is load-bearing.

```sql
SELECT slug, status, wake_source, funnel_decision, created_at
FROM execution_events
WHERE user_id = '29a74c63-0c9c-4998-b8bb-56dd0d810a4e'
  AND mode = 'judgment'
  AND status = 'success'
  AND output_tokens IS NULL
ORDER BY created_at DESC;
```

**Green** = 0 rows. **Any row = a silent-wake fault** → triage `services/wake.py` + the trigger path; do NOT read improvement until resolved.

---

## Check 2 — Failure triage (all non-success events)

Every execution that didn't end in `success`, grouped by reason. Surfaces budget-gate rejections, reviewer errors, market-data failures, etc.

```sql
SELECT status, error_reason, mode, count(*) AS events, max(created_at) AS last_seen
FROM execution_events
WHERE user_id = '29a74c63-0c9c-4998-b8bb-56dd0d810a4e'
  AND status != 'success'
GROUP BY status, error_reason, mode
ORDER BY events DESC;
```

**Expected-benign** statuses to recognize (not faults): budget-gate `skipped`/`deferred` when within-envelope pacing kicks in; `no_universe`/`no_signals` early-returns when substrate is legitimately empty. **Investigate**: any `error` status, `reviewer_returned_none`, unexpected `failed`.

---

## Check 3 — Stuck wake-queue locks

ADR-298 single-in-flight + stale-lock reclaim. A wake `locked` for a long time without completing is a stuck lock (a survival hazard — it blocks the lane). The scheduler reclaims stale locks each tick, so a transiently-locked row is fine; a row locked for many minutes is the signal.

```sql
SELECT slug, wake_source, lane, status, locked_at, locked_by,
       (now() - locked_at) AS lock_age
FROM wake_queue
WHERE user_id = '29a74c63-0c9c-4998-b8bb-56dd0d810a4e'
  AND status = 'locked'
ORDER BY locked_at;
```

**Green** = 0 rows, OR any `locked` row with `lock_age` < ~2min (actively draining). **Investigate**: `status='locked'` with `lock_age` > ~5min (reclaim should have fired).

Companion — wake_queue status distribution over the window:

```sql
SELECT status, lane, count(*), min(enqueued_at) AS first, max(enqueued_at) AS last
FROM wake_queue
WHERE user_id = '29a74c63-0c9c-4998-b8bb-56dd0d810a4e'
GROUP BY status, lane
ORDER BY last DESC;
```

**Healthy**: mostly `completed`; `pending` only transiently; zero long-lived `locked`; `dropped` only where dedup legitimately fired.

---

## Check 4 — Budget burn vs the envelope

The ADR-327 budget gate is part of what the soak tests: does the operation self-pace within its declared `_budget.yaml` envelope ($50/monthly, $1/wake for this workspace), and does the LLM-spend wallet (`balance_usd`) hold the runway? A soak that exhausts `balance_usd` goes silent — which would LOOK like a survival failure but is just an empty wallet (§6). This check distinguishes the two.

```sql
SELECT
  (SELECT balance_usd FROM workspaces WHERE owner_id = '29a74c63-0c9c-4998-b8bb-56dd0d810a4e') AS balance_usd,
  count(*) AS llm_events,
  coalesce(sum(cost_usd), 0) AS total_cost_usd,
  coalesce(sum(cost_usd) FILTER (WHERE created_at > now() - interval '24 hours'), 0) AS cost_last_24h,
  max(cost_usd) AS max_single_wake_usd
FROM execution_events
WHERE user_id = '29a74c63-0c9c-4998-b8bb-56dd0d810a4e'
  AND cost_usd IS NOT NULL;
```

**Watch**: `max_single_wake_usd` should respect the `$1.00` per-wake ceiling; `total_cost_usd` should track well under the $30 runway over the window; `cost_last_24h` gives the daily burn rate (project days-of-runway = `balance_usd / cost_last_24h`). **Distinguish**: low/zero activity + healthy balance = quiet-but-alive (fine); balance near zero = wallet-exhaustion (fund before judging survival).

---

## Check 5 — Schedule health (the off-hours / market-handling check)

Confirms every recurrence has a valid future `next_run_at` (semantic schedules resolved against market_context) and nothing is wrongly stuck-due or paused. Off-hours quiet with all-future next_run_at is CORRECT (market-handling working), not a stall.

```sql
SELECT slug, schedule, next_run_at, last_run_at,
       (next_run_at <= now()) AS due_now, paused
FROM tasks
WHERE user_id = '29a74c63-0c9c-4998-b8bb-56dd0d810a4e'
ORDER BY next_run_at NULLS FIRST;
```

**Green**: every row has a non-NULL future `next_run_at`; `due_now` rows clear quickly (next tick fires them); no unexpected `paused=t`; no NULL `next_run_at` (a NULL means a semantic schedule failed to resolve — a market_context fault).

---

## Check 6 — Stale scheduling-index drift

The `tasks` table is a thin scheduling index reconstructable from `_recurrences.yaml` (ADR-231 D4). They must stay in sync — a `tasks` slug with no YAML entry (or vice-versa) is index drift. This is a code-side reconstruct query (the YAML lives in `workspace_files`):

```bash
# tasks slugs:
psql "$PSQL" -P pager=off -t -c "SELECT slug FROM tasks WHERE user_id='29a74c63-0c9c-4998-b8bb-56dd0d810a4e' ORDER BY slug;"
# _recurrences.yaml slugs (anchor on list-item 'slug:' — NB a stray 'dedup: stable' can false-match a loose grep):
psql "$PSQL" -P pager=off -t -A -o /tmp/rec.yaml -c "SELECT content FROM workspace_files WHERE user_id='29a74c63-0c9c-4998-b8bb-56dd0d810a4e' AND path='/workspace/_recurrences.yaml';"
grep -oE '^\s*-?\s*slug:\s*[a-z0-9][a-z0-9-]+' /tmp/rec.yaml | sed -E 's/.*slug:\s*//' | sort; rm -f /tmp/rec.yaml
```

**Green**: the two slug sets are identical (genesis: 11 = 11). **Drift**: any asymmetry → run `services.scheduling.materialize_scheduling_index` to reconcile, and investigate why they diverged.

---

## Check 7 — Perception-field liveness (ADR-335, added 2026-06-11)

**The standing eval of the perception route.** For each watch the program declares in `substrate_abi.watches` (alpha-trader: `universe` → `{TICKER}.yaml` via track-universe; `regime` → `_regime.yaml` via track-regime), the distilled signal substrate must be **fresher than its cadence tolerance** — declaration → mechanical read → distilled attributed substrate, verified as a loop, every read. Absence is the failure signal (the ADR-335 D5-governance principle: binding failures surface as *absent observations*, read from the record — no freshness table, this query IS the read).

**This check is deliberately transport-blind.** It reads the observation-contract layer (revision freshness on the `distills_to` substrate), not the transport — so when a watch's transport changes (Alpaca Direct API today; an MCP-client binding at Crawl-B; web/RSS at D7), this check applies **unchanged**. The Crawl-B-specific addition will be a small per-binding contract test at binding time (call the foreign tool once, validate distillation) — the tenure instrument is already written.

```sql
-- Latest distilled observation per watched substrate path.
-- Green: universe tickers ≤ 1 trading day old (49h weekend-tolerant);
--        _regime.yaml ≤ 1 trading day old.
-- Red: any watched path absent or stale → the watch's transport/binding
--      failed silently OR the recurrence stopped firing (cross-check
--      execution_events for the watch's recurrence slug).
SELECT path, max(created_at) AS latest_observation, count(*) AS total_revisions
FROM workspace_file_versions
WHERE user_id = '29a74c63-0c9c-4998-b8bb-56dd0d810a4e'
  AND (path ~ '/workspace/operation/trading/[A-Z]+\.yaml'
       OR path = '/workspace/operation/trading/_regime.yaml')
GROUP BY path
ORDER BY latest_observation DESC;
```

**Also assert the declared universe matches the observed universe**: the ticker set in `_universe.yaml` (the operator's watch declaration) must equal the set of `{TICKER}.yaml` paths above — a declared-but-never-observed ticker is a dead watch; an observed-but-undeclared ticker is an unauthorized watch (both are findings).

---

## Reading the results into the tracking log

A survival read appends a dated TRACKING-LOG entry with: deploy-marker (current `origin/main` commit the Render services run), the window covered (since last read), checks 1–7 results (green/finding + receipts), and a verdict — **SURVIVING** (all green) or **FINDING: <class>** (with the failing check + substrate-receipt). Only after a SURVIVING verdict holds across a window that captured real judgment events does the improvement curve (NEXT-5) become readable as evidence.
