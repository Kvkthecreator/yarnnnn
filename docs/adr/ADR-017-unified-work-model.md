# ADR-017: Unified Work Model

> **Status**: Accepted
> **Date**: 2026-01-31
> **Supersedes**: ADR-009 (Work and Agent Orchestration) - scheduling aspects
> **Builds on**: ADR-016 (Layered Agent Architecture)

---

## Context

The current work system has conceptual complexity:

1. **Two entry points**: `create_work` for one-time, `schedule_work` for recurring
2. **Template confusion**: Scheduled work creates "templates" that spawn "tickets"
3. **Dual table semantics**: `work_tickets` serves as both executable work AND schedule templates
4. **Split judgment**: TP must decide "which tool?" in addition to "what work?"

This creates:
- Cognitive overhead for users ("I created a template" vs "I set up recurring work")
- Code duplication in handlers
- Confusing queries (find template, then tickets, then outputs)
- Unclear status semantics (templates are permanently "pending")

---

## Decision: Unified Work Model

### Core Principle

**Work is work. Frequency is just an attribute.**

Every work request has:
- **What**: task, agent_type, parameters
- **When**: frequency (`"once"` | `"daily at 9am"` | `"every Monday"` | ...)
- **Where**: project_id (optional)

### Single Entry Point

```python
create_work(
    task="Research AI trends",
    agent_type="research",
    frequency="once",              # or "daily at 9am", "weekly on Monday", etc.
    project_id=None,               # optional
    parameters={},                 # optional
    run_first=True                 # for recurring: execute immediately?
)
```

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
│    frequency          -- "once" | cron/human schedule                       │
│    frequency_cron     -- Parsed cron expression (NULL for "once")           │
│    timezone           -- User's timezone                                    │
│                                                                             │
│  Scheduling:                                                                │
│    is_active          -- true = will run on schedule                        │
│    next_run_at        -- When it runs next (NULL = no more runs)            │
│    last_run_at        -- When it last ran                                   │
│                                                                             │
│  Metadata:                                                                  │
│    created_at, updated_at                                                   │
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

### Key Changes

| Aspect | Before (ADR-009) | After (ADR-017) |
|--------|------------------|-----------------|
| Concepts | Template + Ticket + Output | Work + Output |
| Entry point | `create_work` + `schedule_work` | `create_work` with frequency |
| One-time | ticket (is_template=false) | work (frequency="once") |
| Recurring | template spawns tickets | work produces outputs |
| Status | On ticket | On output |
| History | Many tickets per template | Many outputs per work |
| Table | work_tickets (dual purpose) | work (single purpose) |

---

## Execution Flow

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
│     - is_active = false (done after)    │
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
│  CRON (every 5 min):                    │
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

## TP Tools (Simplified)

### Primary Tool

```python
CREATE_WORK_TOOL = {
    "name": "create_work",
    "description": """Create work for a specialized agent.

Frequency options:
- "once" - Execute immediately, one time only (default)
- "daily at 9am" - Run every day at specified time
- "weekly on Monday at 10am" - Run weekly on specified day
- "every 6 hours" - Run at regular intervals

For recurring work, set run_first=true to also execute immediately.
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "What the agent should do"
            },
            "agent_type": {
                "type": "string",
                "enum": ["research", "content", "reporting"]
            },
            "frequency": {
                "type": "string",
                "description": "'once' or a schedule like 'daily at 9am'",
                "default": "once"
            },
            "project_id": {
                "type": "string",
                "description": "Optional project context"
            },
            "parameters": {
                "type": "object",
                "description": "Agent-specific parameters"
            },
            "run_first": {
                "type": "boolean",
                "description": "For recurring: also execute immediately?",
                "default": true
            }
        },
        "required": ["task", "agent_type"]
    }
}
```

### Management Tools

| Tool | Purpose |
|------|---------|
| `list_work` | List all work (filter by active, completed, project) |
| `get_work` | Get work details with outputs |
| `update_work` | Pause, resume, change frequency, update task |
| `delete_work` | Remove work and its outputs |

### Removed Tools

| Tool | Replacement |
|------|-------------|
| `schedule_work` | `create_work` with frequency parameter |
| `list_schedules` | `list_work(filter="active")` |
| `update_schedule` | `update_work` |
| `delete_schedule` | `delete_work` |
| `cancel_work` | `update_work(is_active=false)` or `delete_work` |
| `get_work_status` | `get_work` |

---

## TP System Prompt (Simplified)

```markdown
## Work Delegation

Use create_work to delegate to specialized agents:

**Agent types:**
- "research" - Investigation, analysis, synthesis
- "content" - Writing, drafting, content creation
- "reporting" - Summaries, structured reports

**Frequency:**
- "once" - Do it now, one time (default)
- "daily at 9am" - Repeat daily
- "weekly on Monday" - Repeat weekly
- "every 6 hours" - Repeat at interval

**Examples:**
- "Research competitors" → create_work(task=..., frequency="once")
- "Weekly status report" → create_work(task=..., frequency="weekly on Monday at 9am")
- "Daily news digest" → create_work(task=..., frequency="daily at 6pm")
```

---

## Database Migration

### Rename and Restructure

```sql
-- Rename table
ALTER TABLE work_tickets RENAME TO work;

-- Rename/repurpose columns
ALTER TABLE work RENAME COLUMN schedule_cron TO frequency_cron;
ALTER TABLE work ADD COLUMN frequency TEXT DEFAULT 'once';

-- Simplify: is_template becomes derived from frequency
-- is_template=true  → frequency != 'once'
-- is_template=false → frequency = 'once'
ALTER TABLE work DROP COLUMN is_template;

-- schedule_enabled becomes is_active
ALTER TABLE work RENAME COLUMN schedule_enabled TO is_active;

-- parent_template_id no longer needed (outputs link to work directly)
ALTER TABLE work DROP COLUMN parent_template_id;

-- Status moves to outputs
ALTER TABLE work DROP COLUMN status;
ALTER TABLE work DROP COLUMN started_at;
ALTER TABLE work DROP COLUMN completed_at;
ALTER TABLE work DROP COLUMN error_message;

-- Add run_number to outputs
ALTER TABLE work_outputs ADD COLUMN run_number INTEGER DEFAULT 1;
ALTER TABLE work_outputs ADD COLUMN started_at TIMESTAMPTZ;
ALTER TABLE work_outputs ADD COLUMN completed_at TIMESTAMPTZ;
ALTER TABLE work_outputs ADD COLUMN error_message TEXT;

-- Rename FK
ALTER TABLE work_outputs RENAME COLUMN ticket_id TO work_id;
```

### Migration Strategy

1. **Phase 1**: Add new columns, keep old ones
2. **Phase 2**: Migrate data (templates → work with frequency, tickets → outputs)
3. **Phase 3**: Drop old columns
4. **Phase 4**: Update application code

---

## Benefits

1. **Conceptual clarity**: One concept (work) instead of three (template, ticket, output)
2. **Single entry point**: TP makes one decision, not two
3. **Natural queries**: "Show outputs for this work" not "find template → tickets → outputs"
4. **Simpler code**: One handler with branching, not separate tools
5. **Better UX**: "Your daily research" not "your research template"
6. **Status where it belongs**: On outputs (the actual executions)

---

## Success Criteria

1. User can create one-time and recurring work with same mental model
2. TP uses single tool with frequency parameter
3. Work history shows outputs, not intermediate tickets
4. Pause/resume works for recurring work
5. No concept of "templates" in user-facing UI or TP responses

---

## References

- ADR-009: Work and Agent Orchestration (superseded for scheduling)
- ADR-016: Layered Agent Architecture (unified output model)
- ADR-015: Unified Context Model (ambient work)
