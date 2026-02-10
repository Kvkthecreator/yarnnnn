# ADR-039: Background Work Agents

> **Status**: Proposed
> **Created**: 2026-02-10
> **Priority**: P2 (High value, requires infrastructure)
> **Related**: ADR-038 (Claude Code Architecture Mapping), ADR-017 (Recurring Work)
> **Effort**: 2-3 weeks development

---

## Context

ADR-038 identified background agent capability as an enhancement opportunity. Currently, all work agent execution is synchronous — the API request blocks until the agent completes.

### Current State

**Synchronous execution** (`services/work_execution.py`):
```python
async def create_and_execute_work(auth, task, agent_type, ...):
    # 1. Create ticket (pending)
    # 2. Execute agent (blocking, up to 300s timeout)
    # 3. Save output
    # 4. Return result
    # Total: HTTP request blocks entire duration
```

**What works:**
- Short tasks (<30s) complete within typical HTTP timeouts
- Scheduler handles recurring work (every 5 minutes)
- Results stored reliably in database

**What fails:**
- Deep research (>60s) — HTTP timeout, user sees error
- Multi-source analysis — Too slow for interactive use
- Batch operations — Can't parallelize

### Claude Code Comparison

Claude Code's `Task` tool supports `run_in_background`:
```python
Task(
    prompt="Research competitor pricing",
    subagent_type="Explore",
    run_in_background=True  # Returns immediately with task_id
)
```

YARNNN lacks this capability — all work is foreground-only.

### Why This Matters

Some valuable operations require significant time:
- Comprehensive competitive research (multiple sources)
- Large document analysis
- Multi-platform data aggregation

Users shouldn't wait at a loading screen. They should continue chatting while work progresses.

---

## Decision

Add **background work execution** capability with real-time progress updates.

### Architecture

```
User Request ("Research competitors")
    ↓
TP calls create_work(run_in_background=True)
    ↓
Work ticket created (status: queued)
    ↓
Response returns immediately with ticket_id
    ↓
Background worker picks up job
    ↓
Progress updates via polling endpoint
    ↓
Completion notification to user
```

### Key Components

1. **Job Queue** — Redis-backed queue (Render supports Redis)
2. **Worker Process** — Separate process consuming queue
3. **Progress Tracking** — Status updates stored in database
4. **Polling Endpoint** — Real-time status for frontend
5. **Notification** — Email or push on completion

---

## Specification

### 1. Database Schema Changes

```sql
-- Add columns to work_tickets
ALTER TABLE work_tickets ADD COLUMN IF NOT EXISTS
    execution_mode TEXT DEFAULT 'foreground';  -- 'foreground' | 'background'

ALTER TABLE work_tickets ADD COLUMN IF NOT EXISTS
    progress JSONB DEFAULT '{}';  -- {stage: string, percent: int, message: string}

ALTER TABLE work_tickets ADD COLUMN IF NOT EXISTS
    queued_at TIMESTAMPTZ;

-- Execution log for debugging
CREATE TABLE IF NOT EXISTS work_execution_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID REFERENCES work_tickets(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    stage TEXT,  -- 'queued', 'started', 'tool_call', 'completed', 'failed'
    message TEXT,
    metadata JSONB
);
```

### 2. Job Queue (Redis)

```python
# services/job_queue.py

import redis
from rq import Queue

redis_conn = redis.from_url(os.environ["REDIS_URL"])
work_queue = Queue("work", connection=redis_conn)

async def enqueue_work(ticket_id: str, auth_token: str) -> str:
    """Add work to background queue."""
    job = work_queue.enqueue(
        "workers.work_worker.execute_work_background",
        ticket_id,
        auth_token,
        job_timeout="10m",  # 10 minute max
        result_ttl=86400,   # Keep result 24h
    )
    return job.id

def get_job_status(job_id: str) -> dict:
    """Get job status from queue."""
    job = work_queue.fetch_job(job_id)
    if not job:
        return {"status": "not_found"}
    return {
        "status": job.get_status(),
        "result": job.result,
        "error": str(job.exc_info) if job.is_failed else None,
    }
```

### 3. Worker Process

```python
# workers/work_worker.py

from services.work_execution import execute_work_ticket
from services.supabase import get_user_client_from_token

async def execute_work_background(ticket_id: str, auth_token: str):
    """Background worker entry point."""
    # Reconstruct auth from token
    auth = get_user_client_from_token(auth_token)

    # Update status to running
    await update_ticket_status(auth.client, ticket_id, "running")
    await log_execution(ticket_id, "started", "Background execution started")

    try:
        # Execute with progress callbacks
        result = await execute_work_ticket(
            auth,
            ticket_id,
            on_progress=lambda stage, msg: log_execution(ticket_id, stage, msg)
        )

        await log_execution(ticket_id, "completed", "Execution successful")
        return result

    except Exception as e:
        await update_ticket_status(auth.client, ticket_id, "failed", str(e))
        await log_execution(ticket_id, "failed", str(e))
        raise
```

### 4. Modified create_work Tool

```python
# services/project_tools.py (modified handle_create_work)

CREATE_WORK_TOOL = {
    "name": "create_work",
    "description": """Create work for an agent to execute.

    Parameters:
    - task: What the agent should do
    - agent_type: research, content, or reporting
    - run_in_background: If true, returns immediately (default: false)
    - ... other existing params
    """,
    "input_schema": {
        "type": "object",
        "properties": {
            # ... existing properties
            "run_in_background": {
                "type": "boolean",
                "description": "If true, work runs in background and returns ticket_id immediately",
                "default": False
            }
        }
    }
}

async def handle_create_work(auth: UserClient, input: dict) -> dict:
    run_in_background = input.get("run_in_background", False)

    # Create ticket
    ticket = await create_work_ticket(auth, input)

    if run_in_background:
        # Enqueue for background processing
        job_id = await enqueue_work(ticket.id, auth.token)

        return {
            "success": True,
            "ticket_id": str(ticket.id),
            "job_id": job_id,
            "execution_mode": "background",
            "message": f"Work queued for background execution. Track via ticket {ticket.id}.",
            "ui_action": {
                "type": "SHOW_WORK_QUEUED",
                "data": {"ticket_id": str(ticket.id)}
            }
        }
    else:
        # Existing synchronous execution
        result = await execute_work_ticket(auth, ticket.id)
        return result
```

### 5. Status Endpoint

```python
# routes/work.py (new endpoint)

@router.get("/work/{ticket_id}/status")
async def get_work_status(
    ticket_id: UUID,
    auth: UserClient = Depends(get_user_client)
) -> WorkStatusResponse:
    """Get real-time status of work execution."""
    ticket = await get_work_ticket(auth.client, ticket_id)

    if not ticket:
        raise HTTPException(404, "Work ticket not found")

    # Get execution log
    log = await get_execution_log(auth.client, ticket_id, limit=10)

    return WorkStatusResponse(
        ticket_id=ticket_id,
        status=ticket.status,
        progress=ticket.progress,
        execution_mode=ticket.execution_mode,
        started_at=ticket.started_at,
        completed_at=ticket.completed_at,
        log=log,
        output_available=ticket.status == "completed"
    )
```

### 6. Frontend Integration

```typescript
// contexts/WorkStatusContext.tsx (additions)

interface BackgroundWork {
  ticketId: string;
  task: string;
  agentType: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  progress?: { stage: string; percent: number; message: string };
}

// Poll for background work status
const pollBackgroundWork = async (ticketId: string) => {
  const response = await fetch(`/api/work/${ticketId}/status`);
  const status = await response.json();

  if (status.status === 'completed') {
    // Show notification
    showNotification(`Work complete: ${status.task}`);
    // Optionally navigate to output
  }

  return status;
};
```

---

## Implementation Plan

### Phase 1: Infrastructure (1 week)

1. Set up Redis on Render
2. Add RQ (Redis Queue) dependency
3. Create `services/job_queue.py`
4. Create `workers/work_worker.py`
5. Add Render worker process configuration

### Phase 2: Backend Integration (1 week)

1. Add database schema changes
2. Modify `create_work` tool with `run_in_background`
3. Add `/work/{id}/status` endpoint
4. Add execution logging
5. Test end-to-end with manual queue

### Phase 3: Frontend & Polish (0.5 week)

1. Add background work tracking to WorkStatusContext
2. Add polling for background work status
3. Add completion notifications
4. Update TP to use background for long tasks

---

## Deployment Configuration

### Render Setup

```yaml
# render.yaml additions

services:
  - type: worker
    name: yarnnn-worker
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: rq worker work --url $REDIS_URL
    envVars:
      - key: REDIS_URL
        sync: false
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_SERVICE_KEY
        sync: false
      - key: ANTHROPIC_API_KEY
        sync: false
```

### Redis Instance

```yaml
databases:
  - name: yarnnn-redis
    type: redis
    plan: starter  # Or higher based on volume
```

---

## Consequences

### Positive

1. **Long-running tasks work** — No HTTP timeout issues
2. **Better UX** — Users continue chatting while work progresses
3. **Scalability** — Workers can scale independently
4. **Reliability** — Queue persists jobs through restarts

### Negative

1. **Infrastructure cost** — Redis instance + worker process
2. **Complexity** — Distributed system considerations
3. **Debugging** — Harder to trace than synchronous

### Risks

1. **Job loss** — Redis failure loses queued jobs
   - Mitigation: Ticket status in Supabase is source of truth

2. **Token expiry** — Long job outlasts auth token
   - Mitigation: Use service key for background execution

3. **Worker crashes** — Incomplete jobs
   - Mitigation: RQ has built-in retry logic

---

## Open Questions

1. **Notification mechanism** — Email? Push? In-app only?
   - Start with in-app polling, add email later

2. **Concurrency limit** — How many background jobs per user?
   - Start with 3 concurrent, tune based on usage

3. **Priority queue** — Should some work jump the queue?
   - Defer to future iteration

---

## Alternatives Considered

### A: SSE for Progress

Stream progress via Server-Sent Events instead of polling.

**Rejected**: Adds complexity, polling sufficient for MVP. Can add later.

### B: Celery Instead of RQ

Use Celery for more features (scheduling, routing).

**Rejected**: RQ is simpler, sufficient for our needs. Scheduler already handles recurring.

### C: In-Process Background

Use asyncio.create_task() without separate worker.

**Rejected**: Would block API process, no isolation, no horizontal scaling.

---

## References

- [ADR-038: Claude Code Architecture Mapping](./ADR-038-claude-code-architecture-mapping.md) — Gap analysis
- [ADR-017: Recurring Work](./ADR-017-recurring-work.md) — Existing scheduler
- [RQ Documentation](https://python-rq.org/) — Redis Queue
- `services/work_execution.py` — Current execution logic

---

*This ADR proposes background work execution to enable long-running agent tasks without blocking user interaction.*
