# Primitives Matrix — Substrate × Mode × Capability

**Status:** Canonical
**Date:** 2026-04-09 (ADR-168)
**Related:** ADR-146 (Primitive Hardening), ADR-154 (Who/What/How), ADR-080 (Unified Agent Modes), ADR-151 (Context Domains), ADR-164 (TP as Agent), ADR-166 (precedent for two-axis registry cleanup)
**Sibling reference:** [registry-matrix.md](registry-matrix.md) — for domains × tasks × agents
**Source of truth:** [api/services/primitives/registry.py](../../api/services/primitives/registry.py)

---

## What this doc is

The single reference for YARNNN's primitive surface. Three questions it answers:

1. **What primitives exist?** — the full table below.
2. **Where does each primitive dispatch to?** — substrate family column.
3. **Who can call each primitive, and why?** — mode + capability tag columns.

If you are adding a primitive, renaming one, or changing mode availability, **update this doc in the same commit** as the code change. CLAUDE.md rule 7b (pinned below in the Rename Protocol section) enumerates the grep sweep.

This doc reflects **current state**. Historical context lives in the ADR chain referenced in the status header.

---

## Two Axes of Organization

Every primitive is described by exactly two axes.

| Axis | Values | Used for |
|---|---|---|
| **Substrate family** (what it operates on) | `entity` / `file` / `context` / `lifecycle` / `action` / `interaction` / `external` / `introspection` | Dispatch path, mental model, naming convention. |
| **Permission mode** (who can call it) | `chat` / `headless` / `both` | Runtime tool availability. Enforced by `CHAT_PRIMITIVES` and `HEADLESS_PRIMITIVES` registries. |

**Plus capability tags** (orthogonal, descriptive): `entity-layer`, `file-layer`, `semantic-query`, `context-mutation`, `lifecycle`, `user-channel`, `user-authorized`, `external`, `introspection`, `asset-render`, `inter-agent`. Tags are metadata on this table, not part of primitive names.

---

## The Substrate Families

### `entity` — Relational entity layer

Operates on typed entity references (`<type>:<UUID>` format). Resolves through [api/services/primitives/refs.py](../../api/services/primitives/refs.py) via `parse_ref` + `resolve_ref`. Types: `agent`, `platform`, `memory`, `session`, `domain`, `document`, `work`.

Mental model: **"look up this database record by reference."**

Verbs: `LookupEntity`, `ListEntities`, `SearchEntities`, `EditEntity`.

### `file` — Virtual filesystem layer

Operates on path-based files in the virtual filesystem (`workspace_files` table). Resolves through `AgentWorkspace` / `KnowledgeBase` classes in [api/services/workspace.py](../../api/services/workspace.py). Paths scoped by `agent_slug` (agent workspace) or `domain` (context domain) or task slug.

Mental model: **"read or write this file at this path."**

Verbs: `ReadFile`, `WriteFile`, `SearchFiles`, `ListFiles`, `QueryKnowledge` (semantic variant), `ReadAgentFile` (cross-agent variant).

### `context` — Typed context mutations

Single verb that writes to one of several typed context stores (identity, brand, memory, agent feedback, task feedback, deliverable preferences). Each target has its own storage location but all go through one consolidated entry point (ADR-146 Phase 1).

Mental model: **"update this piece of the user's context."**

Verb: `UpdateContext`.

### `lifecycle` — Entity lifecycle management

Verbs that create, update, pause, resume, or complete an agent, task, or domain entity. Consistent `Manage*` pattern across all three. `ManageAgent` and `ManageTask` both include `action="create"` to keep creation symmetric with other lifecycle actions (ADR-168).

Mental model: **"take this lifecycle action on this named thing."**

Verbs: `ManageAgent`, `ManageTask`, `ManageDomains`, `DiscoverAgents` (read-only lifecycle).

### `action` — User-initiated typed actions

Verbs that take a specific typed action at the user's direction, distinct from entity mutations. Currently one verb: `RepurposeOutput` (ADR-148). Sized for growth — asset render, publish, export-as-X would land here if promoted from task types.

Mental model: **"do this specific operation the user just asked for."**

Verbs: `RepurposeOutput`, `RuntimeDispatch` (when invoked in chat; in headless it's asset-render).

### `interaction` — User interaction

The primitive that requires a live user channel to function. Single verb: `Clarify`.

Mental model: **"ask the user something."**

Verb: `Clarify`.

### `external` — External API calls

Primitives that dispatch to an external service. `WebSearch` is the base entry. `platform_*` tools (resolved dynamically per agent capability bundle via `get_headless_tools_for_agent()`) route through `handle_platform_tool`.

Mental model: **"make a call outside YARNNN."**

Verbs: `WebSearch`, `platform_*` (dynamic set).

### `introspection` — System/workspace read-only

Primitives that report state without mutating anything. `GetSystemState`, `list_integrations`.

Mental model: **"tell me what's currently true."**

Verbs: `GetSystemState`, `list_integrations`.

---

## The Full Matrix

**Legend:** ● available, ○ not available in this mode.

| Primitive | Substrate | Chat | Headless | Capability tags | Handler file | Purpose |
|---|---|:---:|:---:|---|---|---|
| `LookupEntity` | entity | ● | ● | entity-layer | [read.py](../../api/services/primitives/read.py) | Look up entity by typed ref (`agent:uuid`, `document:uuid`). |
| `ListEntities` | entity | ● | ● | entity-layer | [list.py](../../api/services/primitives/list.py) | Enumerate entities by type and filter. |
| `SearchEntities` | entity | ● | ● | entity-layer | [search.py](../../api/services/primitives/search.py) | Search entities by content or metadata. |
| `EditEntity` | entity | ● | ○ | entity-layer, user-authorized | [edit.py](../../api/services/primitives/edit.py) | Mutate entity fields under user direction. Chat only — headless has no user authorization path. |
| `ReadFile` | file | ○ | ● | file-layer | [workspace.py](../../api/services/primitives/workspace.py) | Read a file from the agent's own workspace. |
| `WriteFile` | file | ○ | ● | file-layer | [workspace.py](../../api/services/primitives/workspace.py) | Write a file to the agent's workspace or (with `scope="context"`) to a shared context domain. |
| `SearchFiles` | file | ○ | ● | file-layer | [workspace.py](../../api/services/primitives/workspace.py) | Full-text search within the agent's workspace. |
| `ListFiles` | file | ○ | ● | file-layer | [workspace.py](../../api/services/primitives/workspace.py) | List files in the agent's workspace. |
| `QueryKnowledge` | file | ○ | ● | semantic-query | [workspace.py](../../api/services/primitives/workspace.py) | Semantic ranked query over accumulated `/workspace/context/` domains (ADR-151). Distinct from `SearchFiles` — returns ranked results with domain/metadata filters. |
| `ReadAgentFile` | file | ○ | ● | file-layer, inter-agent | [workspace.py](../../api/services/primitives/workspace.py) | Read a file from another agent's workspace (read-only, ADR-116). |
| `DiscoverAgents` | lifecycle | ○ | ● | inter-agent | [workspace.py](../../api/services/primitives/workspace.py) | Find other agents in the workspace by role/scope/status (ADR-116 Phase 2). |
| `UpdateContext` | context | ● | ○ | context-mutation | [update_context.py](../../api/services/primitives/update_context.py) | Single verb for all context mutations. Targets: `identity`, `brand`, `memory`, `agent`, `task`, `deliverable`. Chat only today; may extend to headless in future. |
| `ManageAgent` | lifecycle | ● | ● | lifecycle | [coordinator.py](../../api/services/primitives/coordinator.py) | Create, update, pause, resume, archive agent. |
| `ManageTask` | lifecycle | ● | ● | lifecycle | [manage_task.py](../../api/services/primitives/manage_task.py) | Create, trigger, update, pause, resume, evaluate, steer, complete task. (Folds former `CreateTask` as `action="create"`.) |
| `ManageDomains` | lifecycle | ● | ● | lifecycle | [scaffold.py](../../api/services/primitives/scaffold.py) | Scaffold, add, remove, list entities in workspace context domains (ADR-155/157). |
| `RepurposeOutput` | action | ● | ○ | user-authorized | [repurpose.py](../../api/services/primitives/repurpose.py) | Adapt an existing task output to a different format or channel (ADR-148). |
| `RuntimeDispatch` | action | ● | ○ (via type capability) | asset-render | [runtime_dispatch.py](../../api/services/primitives/runtime_dispatch.py) | Dispatch to output gateway for asset rendering (ADR-118). Chat exposure for explicit user requests. Headless agents with asset capabilities invoke it as a post-generation step, not as a mid-task tool. |
| `Clarify` | interaction | ● | ○ | user-channel | [registry.py](../../api/services/primitives/registry.py) | Ask the user a question. Requires live user channel — impossible in headless. |
| `WebSearch` | external | ● | ● | external | [web_search.py](../../api/services/primitives/web_search.py) | Search the public web. |
| `list_integrations` | introspection | ● | ○ | introspection | [registry.py](../../api/services/primitives/registry.py) | List the user's connected platforms. |
| `GetSystemState` | introspection | ● | ● | introspection | [system_state.py](../../api/services/primitives/system_state.py) | Report system state (tier, limits, health flags). |
| `platform_*` | external | ○ | ● (capability-gated) | external | [platform_tools.py](../../api/services/platform_tools.py) | Dynamic set resolved per agent capability bundle. Routed through `handle_platform_tool`. Not in static registries. |

### Mode totals (post-ADR-168 implementation)

- **Chat mode:** 13 static primitives (`LookupEntity`, `ListEntities`, `SearchEntities`, `EditEntity`, `GetSystemState`, `WebSearch`, `list_integrations`, `UpdateContext`, `ManageDomains`, `ManageAgent`, `ManageTask`, `RepurposeOutput`, `Clarify`). +`RuntimeDispatch` as an explicit-user-request escape hatch.
- **Headless mode:** 14 static primitives + `platform_*` dynamic tools. The static set: `LookupEntity`, `ListEntities`, `SearchEntities`, `GetSystemState`, `WebSearch`, `ReadFile`, `WriteFile`, `SearchFiles`, `ListFiles`, `QueryKnowledge`, `DiscoverAgents`, `ReadAgentFile`, `ManageAgent`, `ManageTask`, `ManageDomains`.

**Hard boundaries (enforced by [api/test_recent_commits.py](../../api/test_recent_commits.py)):**

- Chat does NOT have file-layer primitives (`ReadFile`, `WriteFile`, `SearchFiles`, `ListFiles`). TP operates on task/agent paths through `EditEntity` on typed refs, not through agent-scoped file I/O.
- Chat does NOT have `RuntimeDispatch` as a general-purpose tool (only as an opt-in for explicit user requests).
- Headless does NOT have `EditEntity`, `Clarify`, `UpdateContext`, `RepurposeOutput`, or `list_integrations`. No user-authorization path in headless mode, no user channel, no user-facing mutations, no platform metadata needs that aren't already resolved at capability-bundle time.

---

## Target/Action Enumerations

For verbs that carry a typed sub-action, the enum is load-bearing. Single source of truth: the tool definitions in code. Mirrored here for reference.

### `UpdateContext.target`

| Target | Writes to | Typical caller |
|---|---|---|
| `identity` | `/workspace/context/_identity.md` or memory substrate | TP during context inference |
| `brand` | `/workspace/context/_brand.md` | TP during context inference |
| `memory` | `user_memory` KV store | TP in-session fact capture (ADR-156) |
| `agent` | Agent's workspace `memory/feedback.md` | TP routing user feedback |
| `task` | Task's `memory/feedback.md` | TP routing user feedback on a task |
| `deliverable` | Task's `DELIVERABLE.md` preference trail | TP routing user feedback on output format/content (ADR-149) |

### `ManageAgent.action`

| Action | Effect |
|---|---|
| `create` | Scaffold a new agent (identity + workspace + default tasks per capability bundle) |
| `update` | Patch agent identity or config |
| `pause` | Deactivate agent (tasks don't fire) |
| `resume` | Reactivate agent |
| `archive` | Soft-delete agent |

### `ManageTask.action` (post-ADR-168 Commit 3)

| Action | Effect | Mode availability |
|---|---|---|
| `create` | Scaffold a new task from a task type, assign to an agent, write TASK.md | both |
| `trigger` | Fire the task immediately (dispatch to task pipeline) | both |
| `update` | Patch task fields (schedule, objective, sources, delivery) | both |
| `pause` | Set `tasks.status = 'paused'` | both |
| `resume` | Set `tasks.status = 'active'`, recompute `next_run_at` | both |
| `evaluate` | Write TP evaluation to `memory/feedback.md` (goal-mode steering) | chat |
| `steer` | Write TP steering note to `memory/steering.md` | chat |
| `complete` | Mark goal-mode task complete | chat |

### `ManageDomains.action`

| Action | Effect |
|---|---|
| `scaffold` | Bulk entity creation (onboarding, identity update) |
| `add` | Single entity creation (steady-state) |
| `remove` | Deprecate an entity (mark inactive in tracker) |
| `list` | List entities in a domain |

### `RepurposeOutput.target`

| Category | Targets | Execution path |
|---|---|---|
| Mechanical | `pdf`, `xlsx`, `docx`, `markdown` | Backend format conversion via output gateway |
| Editorial | `linkedin`, `slides`, `summary`, `medium`, `twitter` | Agent re-composition via prompt |

---

## Rename Protocol

When renaming, adding, or removing a primitive, perform a grep sweep across these paths **in the same commit** as the code change. This pins CLAUDE.md rule 7b to a discoverable location.

### Backend sweep

- `api/services/primitives/registry.py` — imports, `HANDLERS`, `CHAT_PRIMITIVES`, `HEADLESS_PRIMITIVES`
- `api/services/primitives/*.py` — tool definition files
- `api/agents/thinking_partner.py` — TP system prompt
- `api/agents/tp_prompts/*.py` — onboarding, tools, behaviors, system
- `api/agents/chat_agent.py`
- `api/services/agent_pipeline.py` — reasoning agent prompts
- `api/services/task_pipeline.py` — task execution prompts
- `api/services/working_memory.py` — tool hints in compact index
- `api/services/workspace.py` — class-level docstrings referencing primitives
- `api/services/task_types.py` — task type step instructions
- `api/services/commands.py` — slash command help text
- `api/services/agent_creation.py` — agent scaffolding instructions
- `api/test_recent_commits.py` — contract test assertions

### Frontend sweep

- `web/components/tp/InlineToolCall.tsx` — tool name display branches + icon map
- `web/contexts/TPContext.tsx` — tool result parsing by name
- `web/components/tp/NotificationCard.tsx`
- `web/components/chat-surface/` — artifacts that render tool results
- `web/components/workspace/WorkspaceNav.tsx`
- `web/lib/utils.ts`
- `web/lib/api/client.ts` — any primitive-name string literals

### Docs sweep

- `docs/architecture/primitives-matrix.md` — **this file** (update first)
- `docs/architecture/registry-matrix.md` — if the primitive appears in task-type examples
- `docs/architecture/SERVICE-MODEL.md` — primitive references in the service description
- `docs/architecture/agent-framework.md` — capabilities → tool mapping
- `docs/architecture/agent-execution-model.md`
- `docs/architecture/TP-DESIGN-PRINCIPLES.md`
- `docs/architecture/workspace-conventions.md`
- `docs/architecture/output-substrate.md`
- `docs/features/context.md`
- `docs/features/agent-playbook-framework.md`
- `docs/features/sessions.md`
- `docs/features/memory.md`
- `docs/features/task-types.md`
- `docs/design/SURFACE-PRIMITIVES-MAP.md`
- `docs/design/` — grep the rest
- `docs/adr/` — **reference-only sweep**. ADRs are immutable history. For a rename, add a one-line note in the superseding ADR's status header. Do not rewrite prior ADR prose.
- `CLAUDE.md` — ADR list entry for the change, File Locations table if affected

### Behavioral changelog

Any primitive change (rename, add, remove, mode change, enum extension) writes an entry to [api/prompts/CHANGELOG.md](../../api/prompts/CHANGELOG.md) with the standard format:

```markdown
## [YYYY.MM.DD.N] - Description

### Changed
- registry.py: What changed
- <other files>: What changed
- Expected behavior: How TP/headless behavior shifts
```

---

## Deleted Primitives — Migration Ledger

| Old name | Replaced by | Superseding ADR | Rationale |
|---|---|---|---|
| `UpdateSharedContext` | `UpdateContext(target="identity"\|"brand")` | ADR-146 | One verb, typed target |
| `SaveMemory` | `UpdateContext(target="memory")` | ADR-146 | One verb, typed target |
| `WriteAgentFeedback` | `UpdateContext(target="agent")` | ADR-146 | One verb, typed target |
| `WriteTaskFeedback` | `UpdateContext(target="task")` | ADR-146 | One verb, typed target |
| `TriggerTask` | `ManageTask(action="trigger")` | ADR-146 | One verb, typed action |
| `UpdateTask` | `ManageTask(action="update")` | ADR-146 | One verb, typed action |
| `PauseTask` | `ManageTask(action="pause")` | ADR-146 | One verb, typed action |
| `ResumeTask` | `ManageTask(action="resume")` | ADR-146 | One verb, typed action |
| `Write` | Specialized primitives (ManageAgent, ManageTask, UpdateContext) | ADR-146 | P1: no remaining unique purpose |
| `RefreshPlatformContent` | (none — flow dissolved) | ADR-153 | Platform sync removed; data flows through tracking tasks |
| `Execute` | `ManageTask(action="trigger")` / `UpdateContext(target="agent")` / `ManageTask(action="update")` | ADR-168 Commit 2 | Actions dissolve into typed verbs |
| `CreateTask` | `ManageTask(action="create")` | ADR-168 Commit 3 | Symmetry with ManageAgent |
| `Read` | `LookupEntity` | ADR-168 Commit 4 | Name was ambiguous with file-layer read |
| `List` | `ListEntities` | ADR-168 Commit 4 | Name was ambiguous |
| `Search` | `SearchEntities` | ADR-168 Commit 4 | Name was ambiguous |
| `Edit` | `EditEntity` | ADR-168 Commit 4 | Name was ambiguous |
| `ReadWorkspace` | `ReadFile` | ADR-168 Commit 4 | Substrate-first naming |
| `WriteWorkspace` | `WriteFile` | ADR-168 Commit 4 | Substrate-first naming |
| `SearchWorkspace` | `SearchFiles` | ADR-168 Commit 4 | Substrate-first naming |
| `ListWorkspace` | `ListFiles` | ADR-168 Commit 4 | Substrate-first naming |
| `ReadAgentContext` | `ReadAgentFile` | ADR-168 Commit 4 | Name was vague; it's a file read with `agent_slug` + `path` |

---

## Reading Order

If you are new to this doc:

1. **Substrate families** section — read top-to-bottom. Understanding the six dispatch paths is the single most load-bearing thing in this doc.
2. **Full Matrix** table — scan it once to see the whole surface.
3. **Target/Action Enumerations** — read only the verbs you're using.
4. **Rename Protocol** — read when you're about to make a change.
5. **Deleted Primitives** ledger — read when you're trying to understand legacy code.

---

## Cross-references

- [registry-matrix.md](registry-matrix.md) — what the system works on (domains × tasks × agents). This doc is its sibling covering *how* the system acts on it.
- [agent-framework.md](agent-framework.md) — agent types and the `capabilities` → primitive mapping.
- [SERVICE-MODEL.md](SERVICE-MODEL.md) — system-level description; this doc is the primitive-level deep dive.
- [TP-DESIGN-PRINCIPLES.md](TP-DESIGN-PRINCIPLES.md) — design principles for TP's use of chat-mode primitives.
- [workspace-conventions.md](workspace-conventions.md) — filesystem layout that the `file` substrate family operates on.
- [api/services/primitives/registry.py](../../api/services/primitives/registry.py) — source of truth for registries and handlers.
- [api/prompts/CHANGELOG.md](../../api/prompts/CHANGELOG.md) — behavioral change history.
