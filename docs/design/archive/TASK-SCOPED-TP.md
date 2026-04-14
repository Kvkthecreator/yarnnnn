# Scoped TP — Agent + Task Context-Aware Chat

**Date:** 2026-04-04 (v2 — agent-scoped TP as primary, task-scoped as drill-down)
**Status:** Proposed
**Supersedes:** v1 (2026-03-25, workfloor + task-only scoping)
**Depends on:** [SURFACE-ARCHITECTURE.md](SURFACE-ARCHITECTURE.md) v3, [ADR-138](../adr/ADR-138-agents-as-work-units.md)

---

## Problem

TP serves three surfaces: the chat page (unscoped), the agents page (agent-scoped), and task drill-downs within the agents page (task-scoped). Each surface has a different purpose and needs different context injection.

## Decision

TP chat is **context-scoped by surface**. Same TP, same underlying model, but different:
1. Session (keyed by scope — global, agent_slug, or task_slug)
2. System prompt preamble (scope-appropriate context injected)
3. Available actions (plus menu items filtered by scope)

---

## Three Scopes

### 1. Chat Page TP (global scope)

**Purpose:** Strategic direction — create tasks, manage workspace, cross-cutting questions.

**Session key:** `user_id` only (all slug fields NULL)

**System prompt preamble:**
```
You are on the user's chat page — their strategic command center.

Your team: {agent_roster_summary}
Active tasks: {task_list_summary}
Connected platforms: {platform_status}
Workspace state: {workspace_state_signal}
```

**Plus menu:** Create a task, Update my context, Web search, Upload file

### 2. Agent Page TP (agent-scoped)

**Purpose:** Manage an agent — review domain, trigger tasks, assign new work.

**Session key:** `user_id` + `agent_slug`

**System prompt preamble:**
```
You are helping the user manage the agent "{agent_title}" ({agent_type}).

Agent identity:
{agent_md_summary}

Owned domain: {domain_name} ({entity_count} entities, last updated {last_update})

Assigned tasks:
{task_list_with_status_and_schedule}

Your role:
- Help the user understand what this agent knows and produces
- Trigger any of the agent's tasks, assign new tasks
- Review domain health and suggest improvements
- You CANNOT create new agents here — direct the user to /chat
```

**Plus menu:** Run [task] now, Assign a task, Review domain health, Web research, Give feedback

### 3. Task Drill-Down TP (task-scoped)

**Purpose:** Steer a specific task — focus, criteria, review output, trigger runs.

**Session key:** `user_id` + `task_slug`

**System prompt preamble:**
```
You are helping the user manage the task "{task_title}".

Task definition:
{task_md_content}

Latest output summary:
{latest_output_first_500_chars}

Recent run log:
{run_log_last_5_entries}

Assigned agent: {agent_title} ({agent_role})
Agent expertise: {agent_instructions_first_200_chars}

Your role:
- Steer focus, objective, and success criteria
- Review output quality, suggest improvements
- Trigger runs, adjust delivery
- You CANNOT create agents or tasks here — use back navigation
```

**Plus menu:** Run this task now, Adjust focus, Give feedback, Web research

---

## Backend Implementation

### 1. Session routing (`chat.py`)

```python
# In chat stream handler:
agent_slug = None
task_slug = None

if surface_context:
    if surface_context.type == 'task-detail':
        task_slug = surface_context.taskSlug
    elif surface_context.type == 'agent-detail':
        agent_slug = surface_context.agentSlug

if task_slug:
    session = await get_or_create_session(
        client, user_id, scope="daily", task_slug=task_slug
    )
elif agent_slug:
    session = await get_or_create_session(
        client, user_id, scope="daily", agent_slug=agent_slug
    )
else:
    # Global session (chat page, context page)
    session = await get_or_create_session(
        client, user_id, scope="daily"
    )
```

Requires: `chat_sessions.agent_slug` column (new), `chat_sessions.task_slug` column (existing or new).

### 2. Context injection (`load_surface_content()`)

| Surface type | Context loaded |
|---|---|
| `"chat"` | Agent roster summary, task list, platform status, workspace state |
| `"agent-detail"` | AGENT.md, owned domain summary (entity count, staleness), assigned tasks with status/schedule |
| `"task-detail"` | TASK.md, run_log.md (last 5), latest output (500 chars), assigned agent AGENT.md |
| `"context"` | Navigation path context (domain, entity, file) |

### 3. Primitive scoping

Soft enforcement via prompt — TP has access to all chat-mode primitives but the preamble guides scope-appropriate behavior. No hard blocking needed (prevents legitimate cross-scope actions from being impossible).

---

## Frontend Implementation

### Chat component reuse

All three scopes use the same `ChatPanel` component with different props:

```typescript
// Chat page
<ChatPanel surfaceOverride={{ type: "chat" }}
           plusMenuActions={CHAT_PAGE_ACTIONS} />

// Agents page — agent selected
<ChatPanel surfaceOverride={{ type: "agent-detail", agentSlug }}
           plusMenuActions={buildAgentActions(agent, tasks)}
           placeholder={`Ask about ${agent.title}...`} />

// Agents page — task drill-down
<ChatPanel surfaceOverride={{ type: "task-detail", taskSlug }}
           plusMenuActions={buildTaskActions(task)}
           placeholder={`Steer ${task.title}...`} />
```

### Session scope transitions

When the user selects a different agent or drills into a task, the ChatPanel receives a new `surfaceOverride` and switches session context. The previous session persists — returning to the same agent/task resumes the same conversation.

---

## Files to Create/Modify

| File | Change |
|------|--------|
| `api/agents/tp_prompts/scoped_preambles.py` | NEW — preamble templates for all three scopes |
| `api/routes/chat.py` | Session routing by agent_slug/task_slug |
| `api/services/working_memory.py` | `load_surface_content()` for agent-detail scope |
| `web/app/(authenticated)/agents/page.tsx` | ChatPanel with agent/task scope switching |
| `web/app/(authenticated)/chat/page.tsx` | Full-width ChatPanel with global scope |
| `api/prompts/CHANGELOG.md` | Version entry |

---

## Success Criteria

1. Chat page shows unscoped TP with workspace-level context
2. Agents page shows agent-scoped TP when agent is selected
3. Task drill-down shows task-scoped TP with task context
4. Session persists per-scope (revisiting same agent/task = same conversation)
5. Plus menu adapts to current scope (agent actions vs task actions)
6. Context page uses global session (same as chat page)
