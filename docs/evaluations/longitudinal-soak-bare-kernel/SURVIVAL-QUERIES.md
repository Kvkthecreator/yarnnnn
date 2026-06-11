# Survival-audit queries — bare-kernel longitudinal soak (Stage-0 floor)

> **Purpose**: the MACHINE-axis instrument for the weekly read ([`TRACKING-LOG.md`](TRACKING-LOG.md)). Adapted from the alpha-trader-2 instrument — a bare workspace has zero recurrences, so the recurrence-health checks are *replaced by bare-invariant checks*: survival here means "the workspace stayed bare and the seat stayed honest," not "the recurrences fired."
>
> **Subject**: `user_id = 4c106786-c9b4-41cb-982d-0f5a8cc35923` (bare-kernel).
>
> **Connection**: `PSQL` from [`../../database/ACCESS.md`](../../database/ACCESS.md).

```bash
PSQL='postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require'
BK='4c106786-c9b4-41cb-982d-0f5a8cc35923'
```

---

## Check 1 — Silent-wake machine fault

A judgment wake recorded `success` with NULL output tokens = the ping fired but nothing was generated. Expect zero rows.

```sql
SELECT id, status, wake_source, funnel_decision, created_at
FROM execution_events
WHERE user_id = '4c106786-c9b4-41cb-982d-0f5a8cc35923'
  AND mode = 'judgment' AND status = 'success' AND output_tokens IS NULL
ORDER BY created_at DESC;
```

## Check 2 — Failed wakes in window

Expect zero failures; each weekly ping closes clean.

```sql
SELECT id, status, error_reason, created_at
FROM execution_events
WHERE user_id = '4c106786-c9b4-41cb-982d-0f5a8cc35923'
  AND status != 'success'
ORDER BY created_at DESC;
```

## Check 3 — Stuck wake-queue locks

Expect zero pending/locked rows older than 1h.

```sql
SELECT id, wake_source, status, created_at
FROM wake_queue
WHERE user_id = '4c106786-c9b4-41cb-982d-0f5a8cc35923'
  AND status IN ('pending','locked')
  AND created_at < now() - interval '1 hour';
```

## Check 4 — Bare invariants hold (the soak's load-bearing check)

The workspace must stay structurally bare: **0 tasks, 0 platform connections, 0 action_proposals**. A non-zero count is either contamination (Hat-B setup leak) or the seat authoring cadence/proposals — the latter feeds TENURE-READ Read 4 (self-authored cadence) and the confabulation reads, and must be judged there, not silently absorbed.

```sql
SELECT
  (SELECT count(*) FROM tasks WHERE user_id = '4c106786-c9b4-41cb-982d-0f5a8cc35923') AS tasks,
  (SELECT count(*) FROM platform_connections WHERE user_id = '4c106786-c9b4-41cb-982d-0f5a8cc35923') AS platform_conns,
  (SELECT count(*) FROM action_proposals WHERE user_id = '4c106786-c9b4-41cb-982d-0f5a8cc35923') AS proposals;
```

## Check 5 — Budget runway

`balance_usd` must stay positive; weekly-ping burn ≈ $0.08/wake. Expect ≥ $2 for months.

```sql
SELECT balance_usd FROM workspaces
WHERE owner_id = '4c106786-c9b4-41cb-982d-0f5a8cc35923';
```

## Check 6 — Substrate mutation census (feeds the MIND axis)

Every revision since the last read, with attribution. For a bare workspace the expected steady state is *near-zero* — `standing_intent.md` writes (reviewer-attributed) are the healthy exception (ADR-284); anything else gets read against TENURE-READ §5 Read 2 (principles churn = inventing a framework) and the confabulation reads.

```sql
SELECT path, authored_by, message, created_at
FROM workspace_file_versions
WHERE user_id = '4c106786-c9b4-41cb-982d-0f5a8cc35923'
ORDER BY created_at DESC
LIMIT 25;
```
