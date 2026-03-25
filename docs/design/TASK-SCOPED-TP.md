# Task-Scoped TP — Context-Aware Chat at Task Level

**Date:** 2026-03-25
**Status:** Proposed
**Depends on:** [ADR-139](../adr/ADR-139-workfloor-task-surface-architecture.md) v3, [ADR-138](../adr/ADR-138-agents-as-work-units.md)
**Related:** [SURFACE-ARCHITECTURE.md](SURFACE-ARCHITECTURE.md), [WORKFLOOR-LIVENESS.md](WORKFLOOR-LIVENESS.md)

---

## Problem

With the unified TP model (no PM agent), the same TP serves both the workfloor and the task page. But these surfaces have fundamentally different purposes:

- **Workfloor**: manage the workforce (create agents, create tasks, monitor health)
- **Task page**: manage the work (steer focus, review output, adjust delivery)

Without scoping, the task page chat is just generic TP — it doesn't know which task the user is looking at, can't inject task context, and offers irrelevant actions (like "create agent").

## Decision

TP chat is **context-scoped by surface**. Same TP, same underlying model, but different:
1. Session (keyed by task_slug)
2. System prompt preamble (task context injected)
3. Available actions (plus menu items)
4. Slash commands (filtered to task-relevant)

---

## Scope Comparison

### Workfloor TP (global scope)

**Purpose:** Manage the workforce — create, assign, monitor.

**Session key:** `user_id` only (task_slug IS NULL)

**System prompt preamble:**
```
You are on the user's workfloor — their command center for managing agents and tasks.
Your team: {agent_roster_summary}
Active tasks: {task_list_summary}
Connected platforms: {platform_status}
```

**Primitives available:**
- CreateAgent, CreateTask, TriggerTask (any task)
- Search, WebSearch, RefreshPlatformContent
- Read, Write, Edit, List, Execute
- SaveMemory, Clarify

**Plus menu:**
- Create a task
- Search platforms
- Web search
- Run a task now
- Upload file

**Slash commands:**
- /task, /recap, /summary, /research, /create
- /search, /sync, /memory, /web

### Task TP (task-scoped)

**Purpose:** Manage the work — steer focus, review output, adjust delivery.

**Session key:** `user_id` + `task_slug`

**System prompt preamble:**
```
You are helping the user manage the task "{task_title}".

## Task Definition
{task_md_content}

## Latest Output Summary
{latest_output_first_500_chars}

## Recent Run Log
{run_log_last_5_entries}

## Assigned Agent
{agent_title} ({agent_role})
Agent expertise: {agent_instructions_first_200_chars}

Your job: help the user steer this task's focus, review output quality,
adjust delivery, and trigger runs. You can update TASK.md fields
(objective, criteria, output spec) based on user direction.
```

**Primitives available:**
- TriggerTask (this task only)
- Search, WebSearch, RefreshPlatformContent
- Read, List (scoped to task + agent workspace)
- Edit (TASK.md fields only)
- Clarify

**NOT available (workfloor-only):**
- CreateAgent, CreateTask (wrong scope — go to workfloor for that)

**Plus menu:**
- Run this task now
- Adjust focus / criteria
- Change delivery
- Review last output
- Search platforms

**Slash commands:**
- /run (trigger this task)
- /search, /web
- NOT: /task, /create, /recap, /summary (workfloor-level)

---

## Backend Implementation

### 1. Session routing (`chat.py`)

```python
# In chat stream handler:
task_slug = None
if surface_context and surface_context.type == 'task-detail':
    task_slug = surface_context.taskSlug

if task_slug:
    session = await get_or_create_session(
        client, user_id, scope="daily", task_slug=task_slug
    )
else:
    # Global or agent-scoped
    session = await get_or_create_session(
        client, user_id, scope="daily", agent_id=request_agent_id
    )
```

Requires: `chat_sessions.task_slug` column (migration).

### 2. Context injection (`load_surface_content()`)

When `surface_context.type == 'task-detail'`:
1. Read `/tasks/{slug}/TASK.md` from workspace
2. Read `/tasks/{slug}/memory/run_log.md` (last 5 entries)
3. Read latest output summary (first 500 chars)
4. Resolve agent from TASK.md `## Process` → read AGENT.md
5. Inject all as system prompt preamble

### 3. Primitive gating

The existing `PRIMITIVE_MODES` registry gates by `"chat"` vs `"headless"`.
Add a third dimension: surface scope.

```python
# In tools.py or a new surface_primitives.py:
TASK_SCOPE_ALLOWED = {
    "TriggerTask", "Search", "WebSearch", "Read", "List",
    "RefreshPlatformContent", "Edit", "Clarify",
}

TASK_SCOPE_BLOCKED = {
    "CreateAgent", "CreateTask", "Write", "Execute", "SaveMemory",
}
```

When `surface_context.type == 'task-detail'`, filter the tools list before passing to Claude.

### 4. TP prompt versioning

Task-scoped preamble goes in `api/agents/tp_prompts/task_scope.py` (new file):

```python
TASK_SCOPE_PREAMBLE = """
You are helping the user manage the task "{task_title}".

{task_context}

Your role on this page:
- Steer the task's focus, objective, and success criteria
- Review output quality and suggest improvements
- Trigger runs and adjust delivery
- You CANNOT create new agents or tasks here — direct the user to the workfloor for that
"""
```

---

## Frontend Implementation

### Task page layout (v3)

```
┌─ Left (flex-1, tabbed) ──────────┬─ Right (~40%, resizable) ──┐
│                                   │                             │
│  [Output] [Details] [History]     │  Task-Scoped TP Chat       │
│                                   │                             │
│  Output tab (default, full):      │  Messages (task session)   │
│  Rendered HTML or markdown        │                             │
│                                   │                             │
│  Details tab:                     │                             │
│  Status · Cadence · Delivery      │                             │
│  Objective · Criteria · Agent     │                             │
│                                   │                             │
│  History tab:                     │  ┌──────────────────────┐  │
│  Run trajectory + trend           │  │ Steer this task...   │  │
│                                   │  └──────────────────────┘  │
└───────────────────────────────────┴─────────────────────────────┘
```

### Chat component

Reuse the `ChatPanel` component from workfloor but with:
- `surfaceContext: { type: 'task-detail', taskSlug }`
- Different plus menu actions (task-scoped)
- Different placeholder text ("Steer this task...")

---

## Migration

```sql
ALTER TABLE chat_sessions ADD COLUMN task_slug TEXT;
CREATE INDEX idx_chat_sessions_task_slug
  ON chat_sessions(user_id, task_slug) WHERE task_slug IS NOT NULL;
```

---

## Files to Create/Modify

| File | Change |
|------|--------|
| `api/agents/tp_prompts/task_scope.py` | NEW — task-scoped preamble template |
| `api/routes/chat.py` | Session routing by task_slug, context injection |
| `api/services/working_memory.py` | `load_surface_content()` for task-detail |
| `api/agents/tp_prompts/tools.py` | Document task-scoped primitive restrictions |
| `web/app/(authenticated)/tasks/[slug]/page.tsx` | v3 layout: tabbed left + chat right |
| `web/components/desk/ChatDrawer.tsx` | Keep for task page (or inline ChatPanel variant) |
| `api/prompts/CHANGELOG.md` | Version entry |
| `supabase/migrations/XXX_task_slug_sessions.sql` | Add task_slug column |

---

## Success Criteria

1. User on `/tasks/{slug}` sees task-scoped chat that knows the task context
2. Chat preamble includes TASK.md content, latest output, assigned agent
3. Plus menu shows task-relevant actions only (no "create agent")
4. Session persists per-task (revisiting same task = same conversation)
5. Workfloor chat remains global (no task context leaking)
