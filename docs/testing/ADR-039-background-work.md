# ADR-039: Background Work Agents — Validation

> **ADR**: [ADR-039](../adr/ADR-039-background-work-agents.md)
> **Status**: Implemented 2026-02-10
> **Last Validated**: 2026-02-10 (automated unit tests passed)

---

## Overview

ADR-039 adds Redis-backed background work execution for long-running agent tasks. Provides graceful fallback to synchronous execution when Redis is unavailable.

### Components Under Test

| Component | Location | Purpose |
|-----------|----------|---------|
| `job_queue.py` | `services/job_queue.py` | Queue management, enqueue/status |
| `work_worker.py` | `workers/work_worker.py` | Background execution entry point |
| `work_execution.py` | `services/work_execution.py` | `run_in_background` parameter |
| `routes/work.py` | `routes/work.py` | `/background` and `/status` endpoints |
| Migration 036 | `supabase/migrations/` | Schema changes |

### Infrastructure Dependencies

| Dependency | Required For | Fallback |
|------------|--------------|----------|
| Redis | Background queueing | Sync execution |
| RQ (Redis Queue) | Worker process | N/A |
| Supabase | Status tracking | N/A (required) |

---

## Unit Validation

### 1. Queue Availability Check (No Redis)

```python
# Test: Graceful handling when Redis unavailable
import os
os.environ["REDIS_OPTIONAL"] = "true"

from services.job_queue import is_queue_available, get_queue_status

available = is_queue_available()
print(f"Queue available: {available}")  # False without Redis

status = get_queue_status()
print(f"Status: {status}")
# Expected: {'available': False, 'reason': '...'}

assert available == False
assert status["available"] == False
```

**Result**: ✅ Passed (verified 2026-02-10)

### 2. Work Execution Mode Flag

```python
# Test: execution_mode is set correctly
from services.work_execution import create_and_execute_work

# Mock: Would need actual Supabase client
# Verify ticket_data includes execution_mode
ticket_data = {
    "user_id": "test",
    "task": "test",
    "agent_type": "research",
    "parameters": {},
    "status": "pending",
    "execution_mode": "background",  # When run_in_background=True
}
```

**Result**: ✅ Code inspection verified

### 3. Fallback to Synchronous

```python
# Test: Falls back to sync when queue unavailable
import asyncio

# With REDIS_OPTIONAL=true and no Redis running:
# create_and_execute_work(..., run_in_background=True)
# Should execute synchronously and include fallback_reason

# Verified via log inspection:
# "[WORK] Queue unavailable, falling back to foreground for {ticket_id}"
```

**Result**: ✅ Passed (code path verified)

---

## Integration Validation

### 4. Database Schema Migration

```sql
-- Verify migration 036 applied correctly
-- Run in Supabase SQL Editor

-- Check columns exist
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'work_tickets'
AND column_name IN ('execution_mode', 'progress', 'queued_at', 'job_id');

-- Check execution log table
SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_name = 'work_execution_log'
);

-- Check RLS policies
SELECT policyname FROM pg_policies WHERE tablename = 'work_execution_log';
```

**Result**: ⏳ Requires migration deployment

### 5. API Endpoint Validation

```bash
# Test: POST /work/background endpoint
curl -X POST http://localhost:8000/work/background \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Research competitor pricing",
    "agent_type": "research"
  }'

# Expected response (queue available):
# {
#   "success": true,
#   "ticket_id": "uuid",
#   "job_id": "rq-job-id",
#   "status": "queued",
#   "execution_mode": "background",
#   "message": "Work queued for background execution..."
# }

# Expected response (queue unavailable):
# {
#   "success": true,
#   "ticket_id": "uuid",
#   "status": "completed",  // Ran synchronously
#   "execution_mode": "background",
#   "fallback_reason": "Queue unavailable"
# }
```

**Result**: ⏳ Requires running API

### 6. Status Endpoint Validation

```bash
# Test: GET /work/{ticket_id}/status endpoint
curl http://localhost:8000/work/$TICKET_ID/status \
  -H "Authorization: Bearer $TOKEN"

# Expected response:
# {
#   "ticket_id": "uuid",
#   "status": "queued|running|completed|failed",
#   "execution_mode": "background",
#   "progress": {"stage": "...", "percent": 50, "message": "..."},
#   "queued_at": "2026-02-10T...",
#   "started_at": null,
#   "recent_logs": [...],
#   "output_available": false
# }
```

**Result**: ⏳ Requires running API

---

## Worker Validation

### 7. Worker Process Starts

```bash
# Test: Worker process can start and connect
cd api && python -c "
import os
os.environ['REDIS_URL'] = 'redis://localhost:6379'

from rq import Worker, Queue
import redis

try:
    conn = redis.from_url(os.environ['REDIS_URL'])
    conn.ping()
    print('✓ Redis connection OK')

    queue = Queue('work', connection=conn)
    print(f'✓ Queue created, {len(queue)} pending jobs')
except Exception as e:
    print(f'✗ Error: {e}')
"
```

**Result**: ⏳ Requires Redis running

### 8. Job Execution Flow

```python
# Test: Full background execution cycle
# 1. Enqueue job
# 2. Worker picks up
# 3. Execution completes
# 4. Status updates in DB

# Monitor via:
# - work_tickets.status progression: pending → queued → running → completed
# - work_execution_log entries
# - work_outputs created
```

**Result**: ⏳ Requires full stack deployment

---

## Manual Test Cases

### Scenario A: Background Work with Redis

**Prerequisites**:
- Redis running and connected
- Worker process running (`rq worker work --url $REDIS_URL`)
- Migration 036 applied

**Steps**:
1. POST to `/work/background` with research task
2. Receive immediate response with `status: "queued"`
3. Poll `/work/{id}/status` every 2 seconds
4. Observe progress updates
5. Receive final status with `output_available: true`
6. GET `/work/{id}` to retrieve outputs

**Expected**: Job completes asynchronously, UI can show progress

### Scenario B: Graceful Fallback (No Redis)

**Prerequisites**:
- Redis NOT running
- `REDIS_OPTIONAL=true` set

**Steps**:
1. POST to `/work/background` with research task
2. Request blocks until completion
3. Response includes `fallback_reason: "Queue unavailable"`
4. Work still completes successfully

**Expected**: System works without Redis, just slower UX

### Scenario C: Worker Crash Recovery

**Prerequisites**:
- Redis running
- Job in progress

**Steps**:
1. Start background work
2. Kill worker process mid-execution
3. Restart worker
4. Observe RQ retry behavior

**Expected**: Job retries per RQ configuration (2x with 30/60s backoff)

---

## Render Deployment Checklist

### Infrastructure Setup

- [ ] Create Redis database in Render (`yarnnn-redis`)
- [ ] Verify `REDIS_URL` env var is set on API service
- [ ] Verify `REDIS_URL` env var is set on worker service
- [ ] Deploy worker service (`yarnnn-worker`)
- [ ] Apply migration 036 to Supabase

### Verification Steps

```bash
# 1. Check Redis connection from API
curl http://api.yarnnn.com/health
# Should show Redis status in health check (if implemented)

# 2. Check worker is running
# Render dashboard → yarnnn-worker → Logs
# Should see: "Starting worker... work queue"

# 3. Test background execution
curl -X POST https://api.yarnnn.com/work/background \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"task": "Test background", "agent_type": "research"}'
```

---

## Performance Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Queue latency | <100ms | Time from enqueue to worker pickup |
| Job timeout | 10 min | RQ configuration |
| Retry attempts | 2 | RQ configuration |
| Fallback latency | Same as sync | No additional overhead |

---

## Known Limitations

1. **No SSE progress**: Background jobs don't stream progress; polling required
2. **Token expiry**: Long jobs use service key, not user token
3. **Single queue**: All work types share one queue (no priority)
4. **Redis persistence**: Starter plan has limited persistence

---

## Validation Commands

```bash
# Check module imports (no Redis required)
cd api && python -c "
from services.job_queue import is_queue_available, get_queue_status
from services.work_execution import create_and_execute_work
from workers.work_worker import execute_work_background
print('✓ All imports successful')
print(f'Queue available: {is_queue_available()}')
"

# Check worker can start (requires Redis)
cd api && python -m workers.run_worker

# Manual job test (requires Redis + Supabase)
cd api && python -c "
import asyncio
from workers.work_worker import execute_work_background
result = execute_work_background('ticket-uuid', 'user-uuid')
print(result)
"
```
