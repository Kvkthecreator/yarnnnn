# Surface → Primitives → Actions Map

**Date:** 2026-04-04 (v2 — Chat + Agents + Context surfaces)
**Supersedes:** v1 (2026-03-25, Workfloor + Task Page)

Canonical mapping of what's available on each surface. Defines scope boundaries
for TP primitives, slash commands, plus menu actions, and suggestion chips.

**Principle:** Each surface has a data scope. Actions available on that surface
must match the scope — workspace-level actions on the chat page, agent-level actions
on the agents page. TP receives surface context and should respect these boundaries.

---

## Chat Page (`/chat`)

**Scope:** Workspace-level. User manages identity, brand, creates tasks, strategic direction.
**Session:** Global TP session.
**Surface context:** `type: "chat"`.

### Plus Menu Actions

| Action | Prompt | Maps to Primitive |
|--------|--------|-------------------|
| Create a task | "Create a task for " | `CreateTask(...)` |
| Update my context | "Update my context" | `UpdateSharedContext(target=...)` |
| Web search | "Search the web for " | `WebSearch(query=...)` |
| Upload file | (file dialog) | Attachment flow |

### Slash Commands

| Command | Trigger | Flow |
|---------|---------|------|
| `/task` | "create a task" | Clarify → CreateTask |
| `/recap` | "slack recap" | Clarify → CreateTask (digest) |
| `/summary` | "work summary" | Clarify → CreateTask (report) |
| `/research` | "research this" | Clarify → CreateTask (research) |
| `/create` | "create agent" | ManageAgent |
| `/search` | "search my workspace" | Search |
| `/memory` | "remember that" | SaveMemory |
| `/web` | "search the web" | WebSearch |

### Cold Start Suggestion Chips

Shown when chat history is empty (no LLM call — static frontend):

- "Tell me about my work and who I serve"
- "Set up competitive intelligence tracking"
- "Create a weekly Slack recap"

Chips disappear once user sends any message.

### TP Primitives Available (chat mode)

All chat-mode primitives are available. Workspace-relevant:
- `UpdateSharedContext` — identity/brand mutations
- `CreateTask`, `TriggerTask` — task lifecycle (with auto-navigate)
- `ManageAgent` — agent management
- `SaveMemory` — store user preferences/facts
- `WebSearch`, `Search`, `Read`, `List` — information retrieval
- `Clarify` — ask user for input

---

## Agents Page (`/agents`) — Agent Selected

**Scope:** Single agent. User reviews accumulated knowledge, manages responsibilities.
**Session:** Agent-scoped TP session (keyed by `agent_slug`).
**Surface context:** `type: "agent-detail"`, includes AGENT.md + domain summary + assigned tasks.

### Plus Menu Actions

| Action | Prompt | Maps to Primitive |
|--------|--------|-------------------|
| Run [task] now | "Run the task \"{title}\" now" | `TriggerTask(task_slug)` |
| Assign a new task | "Assign a new task to this agent" | `CreateTask(agent_slug=...)` |
| Review domain health | "How is this agent's domain?" | Conversational (read + assess) |
| Web research | "Search the web for..." | `WebSearch(...)` |
| Give feedback | "For the latest output..." | `UpdateContext(feedback_target=...)` |

### TP Primitives Available

Same set as chat page, but TP receives agent surface context that scopes behavior:
- `TriggerTask` — run any of this agent's tasks
- `CreateTask` — assign new work to this agent
- `WebSearch`, `Search` — research scoped to agent's domain
- `Read`, `List` — information retrieval

**Available but not surfaced in plus menu** (workspace-level):
- `UpdateSharedContext` — available but TP should not offer it in agent context
- `ManageAgent` — available for this agent (rename, update identity)

---

## Agents Page — Task Drill-Down

**Scope:** Single task under the selected agent. User steers execution, reviews output.
**Session:** Task-scoped TP session (keyed by `task_slug`).
**Surface context:** `type: "task-detail"`, includes TASK.md + run_log + latest output.

### Plus Menu Actions

| Action | Prompt | Maps to Primitive |
|--------|--------|-------------------|
| Run this task now | "Run the task \"{title}\" now" | `TriggerTask(task_slug)` |
| Adjust focus | "For this task, focus on " | Conversational (ManageTask) |
| Give feedback | "For the latest output..." | `UpdateContext(feedback_target="deliverable")` |
| Web research for this task | "Search the web for..." | `WebSearch(...)` |

### TP Primitives Available

Narrowed to task-relevant:
- `TriggerTask` — run this specific task
- `ManageTask` — update, evaluate, steer, complete
- `WebSearch`, `Search` — research scoped to task context
- `Read`, `List` — information retrieval
- `Clarify`

**Not intended for task drill-down** (agent/workspace-level):
- `CreateTask` — go back to agent view or chat page
- `ManageAgent` — agent-level, not task-level

---

## Context Page (`/context`)

**Scope:** Workspace substrate. User browses domains, uploads, settings.
**Session:** Global TP session (shared with chat page).
**Surface context:** `type: "context"`, includes navigation path (domain, entity, file).

### Plus Menu Actions

| Action | Prompt | Maps to Primitive |
|--------|--------|-------------------|
| Update my context | "Update my context" | `UpdateSharedContext(target=...)` |
| Upload file | (file dialog) | Attachment flow |
| Web search | "Search the web for " | `WebSearch(query=...)` |
| Create a task | "Create a task" | `CreateTask(...)` |

### TP Primitives Available

Same as chat page (same global session). Navigation context tells TP what the user is viewing, enabling contextual suggestions ("You're looking at the competitors domain — want me to create a tracking task?").

---

## Activity Page (`/activity`)

**Scope:** Temporal observation. Read-only.
**Session:** None (no chat on this surface).

No primitives, no plus menu, no slash commands. This is a pure observation surface.

---

## Scope Boundaries

TP receives `surface_content` in its system prompt which tells it what the user
is viewing. The context awareness prompt (ADR-144) and surface context together
guide TP toward scope-appropriate actions.

**Enforcement model:** Soft (prompt-level), not hard (primitive rejection).
TP can technically call any chat-mode primitive from any surface, but the prompt
guides it toward scope-appropriate behavior. This is intentional — hard gating
would prevent legitimate cross-scope actions (e.g., "create a new task" while
viewing an agent's domain).

---

## UX Conductor (NAVIGATE)

Primitives that create or trigger entities return `ui_action: {type: "NAVIGATE", data: {url, label}}`.
The frontend auto-navigates on success (600ms delay). Current navigating primitives:

| Primitive | Navigates to |
|-----------|-------------|
| `CreateTask` | `/agents?agent={agent_slug}&task={task_slug}` |
| `TriggerTask` | `/agents?agent={agent_slug}&task={task_slug}` |
| `ManageAgent` | `/agents?agent={agent_slug}` |

---

## Maintenance

When adding new primitives, update this doc:
1. Add to the relevant surface's primitive list
2. If user-facing, add plus menu action or slash command
3. If it creates an entity, add NAVIGATE ui_action
4. Update PRIMITIVE_MODES in `api/services/primitives/registry.py`
