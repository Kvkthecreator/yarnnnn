# Survival-audit queries — anr-scout journey (Stage-3 tenure)

> MACHINE-axis instrument for the periodic read ([`JOURNEY-LOG.md`](JOURNEY-LOG.md)). Author-shaped: no market checks; the bare-invariant checks are replaced by corpus-shape checks.
>
> **Subject**: `user_id = 89f467f1-3ff9-4877-a898-ff5599ab4b08` (anr-scout).

```bash
PSQL='postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require'
ANR='89f467f1-3ff9-4877-a898-ff5599ab4b08'
```

## Check 1 — Silent-wake faults (judgment success, no output)
```sql
SELECT id, slug, status, wake_source, created_at FROM execution_events
WHERE user_id='89f467f1-3ff9-4877-a898-ff5599ab4b08' AND mode='judgment'
  AND status='success' AND output_tokens IS NULL ORDER BY created_at DESC;
```

## Check 2 — Failures in window
```sql
SELECT id, slug, status, error_reason, created_at FROM execution_events
WHERE user_id='89f467f1-3ff9-4877-a898-ff5599ab4b08' AND status != 'success'
ORDER BY created_at DESC;
```

## Check 3 — Stuck wake-queue locks (>1h)
```sql
SELECT id, wake_source, status, created_at FROM wake_queue
WHERE user_id='89f467f1-3ff9-4877-a898-ff5599ab4b08'
  AND status IN ('pending','locked') AND created_at < now() - interval '1 hour';
```

## Check 4 — Recurrence liveness (6 scheduled, fires landing)
```sql
SELECT slug, status, next_run_at, last_run_at FROM tasks
WHERE user_id='89f467f1-3ff9-4877-a898-ff5599ab4b08' ORDER BY slug;
```
Green: 6 rows, none paused, daily slugs show last_run within 26h.

## Check 5 — Budget + runway
```sql
SELECT balance_usd FROM workspaces WHERE owner_id='89f467f1-3ff9-4877-a898-ff5599ab4b08';
```
Green: positive, burn consistent with ~7 judgment wakes/week + addressed turns.

## Check 6 — Substrate mutation census (feeds the MIND axis)
```sql
SELECT path, authored_by, left(message,50), created_at FROM workspace_file_versions
WHERE user_id='89f467f1-3ff9-4877-a898-ff5599ab4b08'
  AND created_at > now() - interval '7 days'
ORDER BY created_at DESC LIMIT 40;
```
Expected healthy shape: reviewer-attributed writes under `persona/` + `operation/authored/` (bounded delegation), `_signal.md` accumulation, proposals only for ship/external. Stale-snapshot overwrites on judgment_log = the known Hat-A item; watch for recurrence.

## Check 7 — Perception honesty (lean shape)
Zero platform connections; perception stays uploads+websearch. A platform_connections row or invented watch = finding.
```sql
SELECT count(*) AS platform_conns FROM platform_connections
WHERE user_id='89f467f1-3ff9-4877-a898-ff5599ab4b08';
```
