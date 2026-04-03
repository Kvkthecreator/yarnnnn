# Surface → Primitives → Actions Map

Canonical mapping of what's available on each surface. Defines scope boundaries
for TP primitives, slash commands, plus menu actions, and suggestion chips.

**Principle:** Each surface has a data scope. Actions available on that surface
must match the scope — workspace-level actions on the workfloor, task-level actions
on the task page. TP receives surface context and should respect these boundaries.

---

## Workfloor (`/workfloor`)

**Scope:** Workspace-level. User manages identity, brand, agents, tasks overview.
**Session:** Global TP session.
**Surface context:** `type: "idle"` (no specific entity focused).

### Plus Menu Actions

| Action | Prompt | Maps to Primitive |
|--------|--------|-------------------|
| Update my identity | "Update my identity" | `UpdateSharedContext(target="identity")` |
| Update my brand | "Update my brand" | `UpdateSharedContext(target="brand")` |
| Create a task | "Create a task for " | `CreateTask(...)` |
| Web search | "Search the web for " | `WebSearch(query=...)` |
| Fetch URL | (user pastes URL) | `WebSearch(url=...)` |
| Upload file | (file dialog) | Attachment flow |

### Slash Commands (workfloor only)

| Command | Trigger | Flow |
|---------|---------|------|
| `/task` | "create a task" | Clarify → CreateTask |
| `/recap` | "slack recap" | Clarify → CreateTask (digest) |
| `/summary` | "work summary" | Clarify → CreateTask (report) |
| `/research` | "research this" | Clarify → CreateTask (research) |
| `/create` | "create agent" | ManageAgent |
| `/search` | "search my platforms" | Search (platform_content) |
| `/sync` | "sync my", "refresh" | RefreshPlatformContent |
| `/memory` | "remember that" | SaveMemory |
| `/web` | "search the web" | WebSearch |

### Cold Start Suggestion Chips

Shown when chat history is empty (no LLM call — static frontend):

- "Tell me about myself and my work" → identity enrichment
- "Update my brand from our website" → brand enrichment
- "Help me set up my first task" → task creation flow

Chips disappear once user sends any message.

### TP Primitives Available (chat mode)

All chat-mode primitives are available. Workspace-relevant:
- `UpdateSharedContext` — identity/brand mutations
- `CreateTask`, `TriggerTask` — task lifecycle (with auto-navigate)
- `ManageAgent` — agent creation
- `SaveMemory` — store user preferences/facts
- `WebSearch`, `Search`, `Read`, `List` — information retrieval
- `RefreshPlatformContent` — platform sync
- `Clarify` — ask user for input

---

## Task Page (`/tasks/{slug}`)

**Scope:** Single task. User steers execution, reviews output, refines criteria.
**Session:** Task-scoped TP session (keyed by `task_slug`).
**Surface context:** `type: "task-detail"`, includes TASK.md + run_log + latest output.

### Plus Menu Actions

| Action | Prompt | Maps to Primitive |
|--------|--------|-------------------|
| Run this task now | "Run the task \"{title}\" now" | `TriggerTask(task_slug)` |
| Adjust focus | "For this task, focus on " | Conversational (UpdateTask) |
| Refine criteria | "Refine the success criteria..." | `UpdateTask(task_slug)` |
| Review latest output | "Review the latest output..." | Conversational (read + assess) |
| Web research for this task | "Search the web for..." | `WebSearch(...)` |

### Slash Commands

**None.** Task page has no slash command picker. All task actions are through
the plus menu or natural conversation.

### TP Primitives Available (chat mode)

Same set as workfloor, but TP receives task surface context that scopes behavior:
- `TriggerTask` — run this specific task
- `UpdateTask`, `PauseTask`, `ResumeTask` — modify this task
- `WebSearch`, `Search` — research scoped to task context
- `Read`, `List` — information retrieval

**Not intended for task page** (workspace-level):
- `UpdateSharedContext` — available but TP should not offer it in task context
- `CreateTask` — available but unusual from within a task page
- `ManageAgent` — available but irrelevant to task scope

---

## Scope Boundaries

TP receives `surface_content` in its system prompt which tells it what the user
is viewing. The context awareness prompt (ADR-144) and surface context together
guide TP toward scope-appropriate actions.

**Enforcement model:** Soft (prompt-level), not hard (primitive rejection).
TP can technically call any chat-mode primitive from any surface, but the prompt
guides it toward scope-appropriate behavior. This is intentional — hard gating
would prevent legitimate cross-scope actions (e.g., "create a task from this
output" on a task page).

---

## UX Conductor (NAVIGATE)

Primitives that create or trigger entities return `ui_action: {type: "NAVIGATE", data: {url, label}}`.
The frontend auto-navigates on success (600ms delay). Current navigating primitives:

| Primitive | Navigates to |
|-----------|-------------|
| `CreateTask` | `/tasks/{slug}` |
| `TriggerTask` | `/tasks/{slug}` |

Future candidates:
- `ManageAgent` → `/agents/{id}`

---

## Maintenance

When adding new primitives, update this doc:
1. Add to the relevant surface's primitive list
2. If user-facing, add plus menu action or slash command
3. If it creates an entity, add NAVIGATE ui_action
4. Update PRIMITIVE_MODES in `api/services/primitives/registry.py`
