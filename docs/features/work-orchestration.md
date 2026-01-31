# Work Orchestration

> **Status**: ADR-017 approved, migration pending
> **ADRs**: ADR-017 (Unified Work Model), ADR-016 (Layered Architecture), ADR-015 (Unified Context)

---

## Overview

YARNNN uses a two-layer agent architecture for handling user requests:

1. **Layer 1: Thinking Partner (TP)** - Conversational orchestrator
2. **Layer 2: Work Agents** - Specialized executors (Research, Content, Reporting)

TP judges whether to handle a request directly or delegate to a work agent for deeper work.

---

## Unified Work Model (ADR-017)

**Core Principle: Work is work. Frequency is just an attribute.**

All work—whether one-time or recurring—flows through a single entry point. The system treats scheduling as a first-class property of work, not a separate concept.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  USER REQUEST                                                               │
│  "Research AI trends" OR "Send me daily AI updates at 9am"                  │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  THINKING PARTNER (TP)                                                      │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  Single tool: create_work(                                                  │
│      task="Research AI trends",                                             │
│      agent_type="research",                                                 │
│      frequency="once"           # or "daily at 9am", "weekly on Monday"     │
│  )                                                                          │
│                                                                             │
│  TP makes ONE judgment: What work? (including frequency)                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  WORK SYSTEM                                                                │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  frequency="once":                                                          │
│    → Create work + output → Execute immediately → Return result             │
│                                                                             │
│  frequency="daily at 9am":                                                  │
│    → Create work (is_active=true, next_run_at=tomorrow 9am)                 │
│    → If run_first=true: Create output #1 → Execute now                      │
│    → Cron job handles future executions                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  WORK AGENT                                                                 │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  - Receives: task + context (user memories + project memories)              │
│  - Executes: Analysis, synthesis, creation                                  │
│  - Produces: ONE output (markdown document)                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  WORK OUTPUT                                                                │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  - status: pending → running → completed/failed                             │
│  - run_number: 1, 2, 3... (for recurring work)                              │
│  - Stored in work_outputs table                                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Model

### Work Table

Single table for all work (one-time and recurring):

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| task | TEXT | What the agent should do |
| agent_type | TEXT | research, content, reporting |
| frequency | TEXT | "once" or schedule ("daily at 9am") |
| frequency_cron | TEXT | Parsed cron expression |
| timezone | TEXT | User's timezone |
| is_active | BOOLEAN | Will run on schedule |
| next_run_at | TIMESTAMPTZ | Next scheduled execution |
| last_run_at | TIMESTAMPTZ | Last execution time |
| project_id | UUID | Optional (NULL = ambient work) |
| user_id | UUID | Owner |
| parameters | JSONB | Agent-specific config |

### Work Outputs Table

Each execution produces one output:

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| work_id | UUID | FK to work |
| run_number | INTEGER | 1, 2, 3... for recurring |
| status | TEXT | pending, running, completed, failed |
| title | TEXT | Output name |
| content | TEXT | Markdown body |
| metadata | JSONB | Agent-specific |
| started_at | TIMESTAMPTZ | Execution start |
| completed_at | TIMESTAMPTZ | Execution end |
| error_message | TEXT | On failure |

---

## Frequency Options

| Frequency | Behavior |
|-----------|----------|
| `"once"` | Execute immediately, one time only |
| `"daily at 9am"` | Run every day at 9am |
| `"weekly on Monday at 10am"` | Run weekly |
| `"every 6 hours"` | Run at regular intervals |

---

## Work Agents

### Research Agent
- **Purpose**: Investigate, analyze, synthesize
- **Output**: Markdown document (findings, analysis, recommendations)
- **Metadata**: sources, confidence, scope, depth

### Content Agent
- **Purpose**: Create, draft, write content
- **Output**: The content itself (post, article, email, etc.)
- **Metadata**: format, platform, tone, word_count

### Reporting Agent
- **Purpose**: Summarize, structure, present
- **Output**: Structured report
- **Metadata**: style, audience, period

---

## Key Principles

### 1. One Output Per Execution
Each work execution produces exactly ONE output. The agent determines the structure within that output.

```python
# One coherent document
WorkOutput(
  title="AI Code Assistants Analysis",
  content="## Overview\n...\n## Findings\n...\n## Recommendations\n...",
  metadata={sources: [...], confidence: 0.85},
  run_number=1
)
```

### 2. TP References, Doesn't Duplicate
When work completes, TP keeps its response brief and points to the output. It does NOT repeat the content in chat.

### 3. Context Flows Down
User memories and project memories flow from TP to work agents. The agent has full context to do its work.

### 4. Agent Determines Structure
The agent decides how to structure its output based on the task. A research task might need sections; a content task is the content itself.

### 5. Status Lives on Outputs
Execution status (pending/running/completed/failed) is tracked on outputs, not work. Work defines *what* runs; outputs track *each execution*.

---

## TP Tool

Single entry point for all work:

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

---

## Execution Flows

### One-Time Work (frequency="once")

```
1. TP calls create_work(frequency="once")
2. Create work record (is_active=false, next_run_at=NULL)
3. Create output record (status="pending", run_number=1)
4. Execute agent immediately
5. Update output status → "completed"
6. Return result to TP
```

### Recurring Work (frequency="daily at 9am")

```
1. TP calls create_work(frequency="daily at 9am", run_first=true)
2. Create work record:
   - frequency = "daily at 9am"
   - frequency_cron = "0 9 * * *"
   - is_active = true
   - next_run_at = tomorrow 9am
3. If run_first=true:
   - Create output (run_number=1)
   - Execute immediately
4. Return to TP

Later (via cron job every 5 min):
5. Find work where is_active=true AND next_run_at <= NOW()
6. For each:
   - Create output (run_number++)
   - Execute agent
   - Update next_run_at
   - Send notification
```

---

## Ambient Work (ADR-015)

Work can exist without a project:
- **Project-bound**: Explicitly belongs to a project
- **Ambient**: No project, linked to user directly

TP routes intelligently based on context.

---

## TP System Prompt

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

## TP Awareness Status

User sees what TP is doing:

| State | Display |
|-------|---------|
| Ready | 🟢 Ready • Dashboard |
| In project | 🟢 Ready • Client A project |
| Working | 🔄 Research agent working... |
| Complete | ✅ Research complete • View output |

---

## Implementation Status

| Component | Status |
|-----------|--------|
| TP judgment/delegation | ✅ Implemented |
| create_work tool (one-time) | ✅ Implemented |
| Work agents (Research, Content, Reporting) | ✅ Implemented (ADR-016 unified output) |
| Unified output model (ADR-016) | ✅ Implemented |
| TP brevity guidance | ✅ Implemented |
| Work cancellation | ✅ Implemented (cancel_work tool) |
| Timeouts | ✅ Implemented (5 min default) |
| Cron job for scheduled work | ✅ Deployed on Render |
| **Unified work model (ADR-017)** | 🔲 Migration pending |
| TP awareness status UI | 🔲 Pending (frontend) |

---

## Migration from Current Model

ADR-017 simplifies the current system:

| Before (ADR-009) | After (ADR-017) |
|------------------|-----------------|
| `create_work` + `schedule_work` | `create_work` with frequency |
| Templates + Tickets + Outputs | Work + Outputs |
| `is_template` boolean | `frequency` attribute |
| Status on tickets | Status on outputs |
| `work_tickets` table | `work` table |

---

## Related ADRs

- **ADR-017**: Unified Work Model (current spec)
- **ADR-016**: Layered Agent Architecture (unified output)
- **ADR-015**: Unified Context Model (ambient work)
- **ADR-009**: Work and Agent Orchestration (superseded for scheduling)
