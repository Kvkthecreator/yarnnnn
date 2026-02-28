# ADR-083: Remove RQ Worker and Redis

> **Status**: Implemented
> **Created**: 2026-02-27
> **Supersedes**: ADR-039 (Background Work Agents)

---

## Context

ADR-039 (2026-02-10) introduced Redis/RQ infrastructure for background work execution: a `yarnnn-worker` Render Background Worker service and a `yarnnn-redis` Valkey 8 database. The intended use case was async processing of long-running work tickets.

### What Changed Since ADR-039

1. **Platform sync moved to crons**: ADR-053/ADR-077 introduced dedicated cron jobs (`platform_sync_scheduler`, `unified_scheduler`) that execute all scheduled work inline — no RQ queue involved.

2. **Deliverable execution moved inline**: ADR-042 simplified the deliverable pipeline to run inline during scheduler execution, not through the RQ worker.

3. **Only 5 enqueue call sites remained**, and 4 of them silently failed when Redis was unavailable:
   - `POST /integrations/{provider}/sync` — returned `job_id: None`, did nothing
   - `freshness.sync_stale_sources()` — returned `job_id: None` per stale source, did nothing
   - `_handle_platform_sync()` TP primitive — returned `job_id: None` to TP
   - `_handle_work_run()` TP primitive — returned `job_id: None` to TP
   - `_enqueue_work_background()` — had fallback to foreground execution (the only one that worked)

4. **Redis was already optional**: `REDIS_OPTIONAL=true` was set in production, meaning the system was designed to survive without Redis.

## Decision

Remove the RQ worker service, Redis database, and all RQ/Redis dependencies entirely. Replace the 5 enqueue call sites with direct execution:

| Call Site | Before | After |
|-----------|--------|-------|
| `POST /integrations/{provider}/sync` | `enqueue_job()` → None | `background_tasks.add_task(sync_platform, ...)` |
| `freshness.sync_stale_sources()` | `enqueue_job()` → None | `sync_platform()` direct call |
| TP `platform.sync` primitive | `enqueue_job()` → None | `asyncio.to_thread(sync_platform, ...)` fire-and-forget → **subsequently replaced by `RefreshPlatformContent` primitive (ADR-085)** |
| TP `work.run` primitive | `enqueue_job()` → None | `await execute_work_ticket()` inline |
| `_enqueue_work_background()` | RQ with foreground fallback | Always foreground (fallback was already the only working path) |

## Consequences

### Positive
- **Removes 1 Render service** (Background Worker) and **1 Render database** (Redis) — cost savings
- **4 Render services** instead of 5: API, Unified Scheduler, Platform Sync, MCP Server
- **4 silently broken call sites now work** — direct execution replaces no-op enqueue
- Simpler deployment — no Redis connection to manage
- Removes `redis` and `rq` Python dependencies

### Negative
- Work tickets always execute synchronously in the calling process. For the current workload (sub-minute execution), this is acceptable.
- If truly long-running background work is needed in the future, a new solution would need to be designed.

## Files Changed

| Action | Files |
|--------|-------|
| **Deleted** | `api/services/job_queue.py`, `api/workers/work_worker.py`, `api/workers/deliverable_worker.py`, `api/workers/run_worker.py`, `api/workers/__init__.py`, `api/test_job_queue_contracts.py` |
| **Modified** | `api/services/work_execution.py`, `api/services/freshness.py`, `api/services/primitives/execute.py`, `api/routes/integrations.py`, `api/routes/work.py`, `api/main.py`, `api/requirements.txt`, `render.yaml`, `web/lib/api/client.ts` |
