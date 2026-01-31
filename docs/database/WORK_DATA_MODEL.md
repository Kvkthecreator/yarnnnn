# Work System Data Model

> **Reference**: ADR-017 (Unified Work Model), ADR-016 (Layered Agents)
> **Last Updated**: 2026-01-31
> **Migration Status**: ADR-017 approved, implementation pending

---

## Conceptual Framework

### Core Principle

**Work is work. Frequency is just an attribute.**

Every work request—whether one-time or recurring—flows through a single entry point. The system treats scheduling as a first-class property of work, not a separate concept requiring different tools or tables.

### Data Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  work                                                                       │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  Core:                                                                      │
│    id, task, agent_type, project_id, user_id, parameters                    │
│                                                                             │
│  Frequency:                                                                 │
│    frequency          -- "once" | "daily at 9am" | "weekly on Monday"       │
│    frequency_cron     -- Parsed cron expression (NULL for "once")           │
│    timezone           -- User's timezone                                    │
│                                                                             │
│  Scheduling:                                                                │
│    is_active          -- true = will run on schedule                        │
│    next_run_at        -- When it runs next (NULL = no more runs)            │
│    last_run_at        -- When it last ran                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              │ 1:n
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  work_outputs                                                               │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│    id, work_id, user_id                                                     │
│    title, content, metadata                                                 │
│    status: pending | running | completed | failed                           │
│    run_number         -- 1, 2, 3... for recurring work                      │
│    started_at, completed_at, error_message                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Execution Flows

### One-Time Work (frequency="once")

```
User: "Research AI trends"
           │
           ▼
TP → create_work(task=..., frequency="once")
           │
           ▼
┌─────────────────────────────────────────┐
│  1. Create work record                  │
│     - frequency = "once"                │
│     - is_active = false (no more runs)  │
│     - next_run_at = NULL                │
│                                         │
│  2. Create output record                │
│     - status = "pending"                │
│     - run_number = 1                    │
│                                         │
│  3. Execute agent                       │
│     - output.status → "running"         │
│     - Agent produces content            │
│     - output.status → "completed"       │
│                                         │
│  4. Return result to TP                 │
└─────────────────────────────────────────┘
```

### Recurring Work (frequency="daily at 9am")

```
User: "Send me daily AI updates at 9am"
           │
           ▼
TP → create_work(task=..., frequency="daily at 9am", run_first=true)
           │
           ▼
┌─────────────────────────────────────────┐
│  1. Create work record                  │
│     - frequency = "daily at 9am"        │
│     - frequency_cron = "0 9 * * *"      │
│     - is_active = true                  │
│     - next_run_at = tomorrow 9am        │
│                                         │
│  2. If run_first:                       │
│     - Create output (run_number=1)      │
│     - Execute immediately               │
│                                         │
│  3. Return to TP                        │
└─────────────────────────────────────────┘
           │
           ▼ (later, via cron)
┌─────────────────────────────────────────┐
│  CRON JOB (every 5 min):                │
│                                         │
│  Find work where:                       │
│    is_active = true                     │
│    next_run_at <= NOW()                 │
│                                         │
│  For each:                              │
│    - Create output (run_number++)       │
│    - Execute agent                      │
│    - Update next_run_at                 │
│    - Send notification                  │
└─────────────────────────────────────────┘
```

---

## Key Distinctions

| Aspect | One-Time Work | Recurring Work |
|--------|---------------|----------------|
| frequency | `"once"` | `"daily at 9am"`, `"weekly on Monday"`, etc. |
| is_active | `false` | `true` |
| next_run_at | `NULL` | Next scheduled time |
| Outputs | 1 output | Multiple outputs (run_number 1, 2, 3...) |
| Cron job | Ignores | Triggers execution |

---

## work Table

Single table for all work (one-time and recurring):

```sql
work
├── id                      UUID PK
├── task                    TEXT            -- What to do
├── agent_type              TEXT            -- research, content, reporting
├── parameters              JSONB           -- Agent-specific config
├── project_id              UUID FK?        -- Optional (NULL = ambient work)
├── user_id                 UUID FK         -- Direct ownership for RLS
├── created_at              TIMESTAMPTZ
├── updated_at              TIMESTAMPTZ
│
├── frequency               TEXT            -- "once" | "daily at 9am" | etc.
├── frequency_cron          TEXT?           -- Parsed cron (NULL for "once")
├── timezone                TEXT            -- User's timezone (default UTC)
│
├── is_active               BOOLEAN         -- Will run on schedule
├── next_run_at             TIMESTAMPTZ?    -- When cron will execute next
└── last_run_at             TIMESTAMPTZ?    -- When last executed
```

---

## work_outputs Table

Each execution produces one output:

```sql
work_outputs
├── id                      UUID PK
├── work_id                 UUID FK         -- Which work produced this
├── user_id                 UUID FK         -- For RLS
├── run_number              INTEGER         -- 1, 2, 3... for recurring
│
├── title                   TEXT            -- Human-readable title
├── content                 TEXT            -- Markdown body
├── output_type             TEXT            -- "text" | "file"
├── metadata                JSONB           -- Agent-specific
├── file_url                TEXT?           -- For file outputs
├── file_format             TEXT?           -- pdf, docx, etc.
│
├── status                  TEXT            -- pending, running, completed, failed
├── started_at              TIMESTAMPTZ?    -- Execution start
├── completed_at            TIMESTAMPTZ?    -- Execution end
├── error_message           TEXT?           -- On failure
│
└── created_at              TIMESTAMPTZ
```

---

## TP Tool

Single entry point for all work:

| Tool | Purpose |
|------|---------|
| `create_work` | Create work with frequency parameter |
| `list_work` | List all work (filter by active, project) |
| `get_work` | Get work details with outputs |
| `update_work` | Pause, resume, change frequency |
| `delete_work` | Remove work and outputs |

---

## Query Patterns

### Find all work for user
```sql
SELECT * FROM work
WHERE user_id = $user_id;
```

### Find active recurring work
```sql
SELECT * FROM work
WHERE user_id = $user_id
  AND is_active = true
  AND frequency != 'once';
```

### Find work due for execution (cron job)
```sql
SELECT * FROM work
WHERE is_active = true
  AND next_run_at <= NOW();
```

### Get outputs for work (ordered by run)
```sql
SELECT * FROM work_outputs
WHERE work_id = $work_id
ORDER BY run_number DESC;
```

### Get latest output for work
```sql
SELECT * FROM work_outputs
WHERE work_id = $work_id
ORDER BY run_number DESC
LIMIT 1;
```

---

## Naming Conventions

| Term | Meaning |
|------|---------|
| **work** | A row in the work table (defines what to do and when) |
| **output** | Result of executing work (one per execution) |
| **run_number** | Which execution (1st, 2nd, 3rd...) for recurring work |
| **frequency** | How often: "once", "daily at 9am", etc. |
| **active** | Whether recurring work will continue running |

---

## Important Invariants

1. **One output per execution**: Each run creates exactly one work_output
2. **Status on outputs**: Execution status lives on outputs, not work
3. **run_number increments**: Each execution gets the next run_number
4. **next_run_at updated after execution**: Cron advances the schedule
5. **user_id required**: All work and outputs need user_id for RLS
6. **frequency="once" means is_active=false**: No future runs scheduled

---

## Migration from Legacy Model

ADR-017 simplifies the previous ADR-009 model:

| Before (ADR-009) | After (ADR-017) |
|------------------|-----------------|
| work_tickets (dual purpose) | work (single purpose) |
| is_template boolean | frequency attribute |
| Templates spawn tickets | Work produces outputs |
| Status on tickets | Status on outputs |
| parent_template_id | Not needed |
| schedule_* columns | frequency_*, is_active, next/last_run_at |

---

## References

- [ADR-017: Unified Work Model](../adr/ADR-017-unified-work-model.md)
- [ADR-016: Layered Agent Architecture](../adr/ADR-016-work-agents-and-artifacts.md)
- [ADR-009: Work and Agent Orchestration](../adr/ADR-009-work-agent-orchestration.md) (superseded for scheduling)
