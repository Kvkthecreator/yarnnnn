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

## Perception channel: how TP senses state before it acts

**The matrix below is TP's action vocabulary. It is not TP's entire input surface.** Before TP reaches for a primitive, it reads a precomputed perception channel that is injected into its system prompt on every turn. This section documents that channel so the matrix isn't misread as the only way TP knows about workspace state.

### Two input channels

| Channel | What it carries | When it runs | Who produces it | Primitive cost |
|---|---|---|---|---|
| **Perception** (working memory) | Workspace state snapshot: identity/brand richness, task counts, stale tasks, budget, agent health, context domain fullness, recent uploads, active tasks, recent sessions, system summary | Once per TP turn, before tool dispatch | [api/services/working_memory.py](../../api/services/working_memory.py) `format_compact_index()` | Zero LLM, zero primitives — pure SQL precompute |
| **Action** (primitives) | Mutations + lookups TP initiates in response to what it read from perception | During tool rounds | The primitives in the matrix below | One tool call per verb |

TP **reads perception → decides → acts through primitives**. It does not call primitives to reconstruct state that the perception channel already carries.

### What working memory injects into TP's prompt

Single source of truth: [api/services/working_memory.py:format_compact_index()](../../api/services/working_memory.py). Key fields in the injected dict:

- **`workspace_state`** (ADR-156) — the meta-awareness signal. Identity/brand richness classification (empty / partial / rich), document count, context domain count with content, active task count, stale task count, credits used/limit, budget-exhausted flag, flagged-agent list.
- **`active_tasks`** — currently active task summaries with last run / next run freshness.
- **`context_domains`** — per-domain health: file count, temporal flag, entity count.
- **`recent_uploads`** (ADR-162 Sub-phase B) — documents uploaded in last 7 days that TP may want to process.
- **`recent_sessions`** — prior session continuity markers.
- **`system_summary`** + **`system_reference`** — tier, limits, connected platforms.
- **`user_shared_files`** — shared uploads available as context.
- **`identity`**, **`brand`**, **`awareness`**, **`conversation_summary`** — the narrative layer of workspace memory (ADR-159 filesystem-as-memory).

All of this is precomputed from SQL and file reads — **zero LLM calls** produced it. TP receives it as a compact index (~500 tokens after ADR-159) and reads deeper on demand via file-layer primitives when it needs detail.

### Why perception is not a primitive

This is deliberate, not drift. Two ADRs govern it:

1. **ADR-156 (Composer Sunset / Single Intelligence Layer)**. Making TP call `GetSystemState` + `ListEntities(type=task)` + `QueryKnowledge(domain=…)` + `ListFiles(…)` on every turn to reconstruct workspace state would reintroduce exactly the pattern ADR-156 deleted Composer to avoid — a second reasoning loop judging state that SQL can compute deterministically. Primitives are for actions, not for waste-motion sensing.

2. **ADR-159 (Filesystem-as-Memory)**. TP's prompt is a compact index (~500 tokens) plus on-demand file reads. The compact index *is* the meta-awareness layer. A `GetWorkspaceState` primitive would duplicate what the compact index already carries, burn a tool round to get it, and cost ~70% of the token savings ADR-159 delivered.

Consequence: **there is no `GetWorkspaceState` primitive and there will not be one.** If a state signal is missing from TP's perception, the fix is to add it to `working_memory.format_compact_index()`, not to create a primitive.

### A realistic meta-awareness loop

Concrete example of how perception and action compose during a cold-start onboarding conversation:

| Turn | Perception TP reads (from working memory) | TP decides | Primitive TP calls |
|---|---|---|---|
| 1 | `workspace_state.identity = "empty"`, `tasks_active = 1` (daily-update), `documents = 0` | Cold start. Need context input. | `Clarify(question="Tell me about your work — paste docs, URLs, or describe it in chat?")` |
| 2 | User pastes material → `recent_uploads` populated, user message has text | Run inference. | `UpdateContext(target="identity", text=…)` (context inference) |
| 3 | `workspace_state.identity = "rich"`, `context_domains = 0` | Scaffold domain entities so `track-*` tasks have substrate. | `ManageDomains(action="scaffold", entities=[…])` |
| 4 | `context_domains = 3`, `tasks_active = 1` | Suggest a first recurring deliverable. | `ManageTask(action="create", task_type="competitive-brief", …)` (post-Commit 3) |
| 5 | User: "show me what's running" → `active_tasks` already in compact index | Answer from perception; no primitive needed. | *(no tool call — compose answer from working memory)* |

Four primitives touched in five turns, across four different substrate families (`interaction`, `context`, `lifecycle`, `lifecycle`). Turn 5 uses zero primitives because perception already carries the answer. This is the intended shape: **perception surfaces state, primitives change it.**

Every verb in that loop is in the matrix below. The decision loop ("read perception, pick next action") lives in TP's system prompt, not in any primitive.

---

## The Full Matrix

**Legend:** ● available, ○ not available in this mode.

**MCP mode** was added by ADR-169 as a third runtime mode alongside Chat and Headless. MCP is the foreign-LLM surface — tools are invoked by Claude.ai, ChatGPT, Gemini, and other LLM hosts on behalf of the user. The MCP tool surface itself is three intent-shaped tools (`work_on_this`, `pull_context`, `remember_this`) that compose over a curated subset of the primitives below. See [docs/features/mcp/architecture.md](../features/mcp/architecture.md) for the tool-to-primitive mapping.

| Primitive | Substrate | Chat | Headless | MCP | Capability tags | Handler file | Purpose |
|---|---|:---:|:---:|:---:|---|---|---|
| `LookupEntity` | entity | ● | ● | ○ | entity-layer | [read.py](../../api/services/primitives/read.py) | Look up entity by typed ref (`agent:uuid`, `document:uuid`). |
| `ListEntities` | entity | ● | ● | ○ | entity-layer | [list.py](../../api/services/primitives/list.py) | Enumerate entities by type and filter. |
| `SearchEntities` | entity | ● | ● | ○ | entity-layer | [search.py](../../api/services/primitives/search.py) | Search entities by content or metadata. |
| `EditEntity` | entity | ● | ○ | ○ | entity-layer, user-authorized | [edit.py](../../api/services/primitives/edit.py) | Mutate entity fields under user direction. Chat only — headless has no user authorization path. |
| `ReadFile` | file | ○ | ● | ○ | file-layer | [workspace.py](../../api/services/primitives/workspace.py) | Read a file from the agent's own workspace. MCP reads workspace files via `pull_context` → `QueryKnowledge` (user-scoped), not via `ReadFile` (agent-scoped). |
| `WriteFile` | file | ○ | ● | ○ | file-layer | [workspace.py](../../api/services/primitives/workspace.py) | Write a file to the agent's workspace or (with `scope="context"`) to a shared context domain. |
| `SearchFiles` | file | ○ | ● | ○ | file-layer | [workspace.py](../../api/services/primitives/workspace.py) | Full-text search within the agent's workspace. |
| `ListFiles` | file | ○ | ● | ○ | file-layer | [workspace.py](../../api/services/primitives/workspace.py) | List files in the agent's workspace. |
| `QueryKnowledge` | file | ○ | ● | ● | semantic-query | [workspace.py](../../api/services/primitives/workspace.py) | Semantic ranked query over accumulated `/workspace/context/` domains (ADR-151). Distinct from `SearchFiles` — returns ranked results with domain/metadata filters. **MCP's primary primitive**: `pull_context` is a thin wrapper, `work_on_this` composes over it. |
| `ReadAgentFile` | file | ○ | ● | ○ | file-layer, inter-agent | [workspace.py](../../api/services/primitives/workspace.py) | Read a file from another agent's workspace (read-only, ADR-116). |
| `DiscoverAgents` | lifecycle | ○ | ● | ○ | inter-agent | [workspace.py](../../api/services/primitives/workspace.py) | Find other agents in the workspace by role/scope/status (ADR-116 Phase 2). |
| `UpdateContext` | context | ● | ○ | ● | context-mutation | [update_context.py](../../api/services/primitives/update_context.py) | Single verb for all context mutations. Targets: `identity`, `brand`, `memory`, `agent`, `task`, `awareness`. **MCP `remember_this`** dispatches here with a two-branch classifier (workspace-level targets default safely to `memory`, operational feedback uses slug disambiguation). ADR-169 decision: all UpdateContext targets available via MCP *except `awareness`* (TP-only). Safety via ADR-162 provenance stamping, not pre-write guards. |
| `ManageAgent` | lifecycle | ● | ● | ○ | lifecycle | [coordinator.py](../../api/services/primitives/coordinator.py) | Create, update, pause, resume, archive agent. |
| `ManageTask` | lifecycle | ● | ● | ○ | lifecycle | [manage_task.py](../../api/services/primitives/manage_task.py) | Create, trigger, update, pause, resume, evaluate, steer, complete task. ADR-168 Commit 3 folded the former `CreateTask` primitive into `action="create"` for symmetry with `ManageAgent`. |
| `ManageDomains` | lifecycle | ● | ● | ○ | lifecycle | [scaffold.py](../../api/services/primitives/scaffold.py) | Scaffold, add, remove, list entities in workspace context domains (ADR-155/157). |
| `RepurposeOutput` | action | ● | ○ | ○ | user-authorized | [repurpose.py](../../api/services/primitives/repurpose.py) | Adapt an existing task output to a different format or channel (ADR-148). |
| `RuntimeDispatch` | action | ● | ○ (via type capability) | ○ | asset-render | [runtime_dispatch.py](../../api/services/primitives/runtime_dispatch.py) | Dispatch to output gateway for asset rendering (ADR-118). Chat exposure for explicit user requests. Headless agents with asset capabilities invoke it as a post-generation step, not as a mid-task tool. |
| `Clarify` | interaction | ● | ○ | ○ | user-channel | [registry.py](../../api/services/primitives/registry.py) | Ask the user a question. Requires live user channel — impossible in headless. MCP does not have a clarify path; the LLM host disambiguates via the tool's `ambiguous` response shape instead. |
| `WebSearch` | external | ● | ● | ○ | external | [web_search.py](../../api/services/primitives/web_search.py) | Search the public web. |
| `list_integrations` | introspection | ● | ○ | ○ | introspection | [registry.py](../../api/services/primitives/registry.py) | List the user's connected platforms. |
| `GetSystemState` | introspection | ● | ● | ○ | introspection | [system_state.py](../../api/services/primitives/system_state.py) | Report system state (tier, limits, health flags). |
| `platform_*` | external | ○ | ● (capability-gated) | ○ | external | [platform_tools.py](../../api/services/platform_tools.py) | Dynamic set resolved per agent capability bundle. Routed through `handle_platform_tool`. Not in static registries. |

### Mode totals

**Current state (post-ADR-168 Commit 3 + ADR-169, as of 2026-04-09):**

- **Chat mode:** 13 tools (was 15). `Execute` dissolved in Commit 2; `CreateTask` folded into `ManageTask(action="create")` in Commit 3. Current set: `Read`, `List`, `Search`, `Edit`, `GetSystemState`, `WebSearch`, `list_integrations`, `UpdateContext`, `ManageDomains`, `ManageAgent`, `ManageTask`, `RepurposeOutput`, `Clarify`. *(Names still in pre-Commit-4 form.)*
- **Headless mode:** 15 static tools + `platform_*` dynamic (was 16). `CreateTask` folded in Commit 3. Set: `Read`, `List`, `Search`, `GetSystemState`, `WebSearch`, `ReadWorkspace`, `WriteWorkspace`, `SearchWorkspace`, `QueryKnowledge`, `ListWorkspace`, `DiscoverAgents`, `ReadAgentContext`, `ManageAgent`, `ManageTask`, `ManageDomains`.
- **MCP mode (ADR-169):** 2 primitives — `QueryKnowledge` and `UpdateContext`. The MCP tool surface itself is three intent-shaped tools (`work_on_this`, `pull_context`, `remember_this`) that compose over these two primitives. MCP is the foreign-LLM surface — fifth caller of `execute_primitive()` per ADR-164 runtime-agnostic principle. See [docs/features/mcp/architecture.md](../features/mcp/architecture.md) for the composition layer (`api/services/mcp_composition.py`).

**Target state (post-ADR-168 Commit 5):**

- **Chat mode:** 13 static primitives (`LookupEntity`, `ListEntities`, `SearchEntities`, `EditEntity`, `GetSystemState`, `WebSearch`, `list_integrations`, `UpdateContext`, `ManageDomains`, `ManageAgent`, `ManageTask`, `RepurposeOutput`, `Clarify`). Entity verbs renamed (no count change from current).
- **Headless mode:** 15 static primitives + `platform_*` dynamic. The static set: `LookupEntity`, `ListEntities`, `SearchEntities`, `GetSystemState`, `WebSearch`, `ReadFile`, `WriteFile`, `SearchFiles`, `ListFiles`, `QueryKnowledge`, `DiscoverAgents`, `ReadAgentFile`, `ManageAgent`, `ManageTask`, `ManageDomains`. Entity + file verbs renamed; no count change from current.
- **MCP mode:** 2 primitives unchanged by Commit 4 rename (`QueryKnowledge` keeps its name; `UpdateContext` keeps its name). The three intent-shaped MCP tools remain `work_on_this`, `pull_context`, `remember_this`.

**Hard boundaries (enforced by [api/test_recent_commits.py](../../api/test_recent_commits.py)):**

- Chat does NOT have file-layer primitives (`ReadFile`, `WriteFile`, `SearchFiles`, `ListFiles`). TP operates on task/agent paths through `EditEntity` on typed refs, not through agent-scoped file I/O.
- Chat does NOT have `RuntimeDispatch` as a general-purpose tool (only as an opt-in for explicit user requests).
- Headless does NOT have `EditEntity`, `Clarify`, `UpdateContext`, `RepurposeOutput`, or `list_integrations`. No user-authorization path in headless mode, no user channel, no user-facing mutations, no platform metadata needs that aren't already resolved at capability-bundle time.
- **MCP does NOT have any lifecycle, entity-layer, or agent-scoped file-layer primitives.** MCP callers (foreign LLMs acting on behalf of the user) are consultation-shaped, not operator-shaped. The user in a foreign LLM is in thinking mode, not workforce-management mode — the MCP surface reflects that. Specifically: no `ManageAgent`/`ManageTask`/`ManageDomains` (no workforce control from foreign LLMs), no `LookupEntity`/`ListEntities`/`SearchEntities`/`EditEntity` (entity layer is TP-chat-only), no `ReadFile`/`WriteFile`/`SearchFiles`/`ListFiles`/`ReadAgentFile` (agent-scoped file layer is headless-only), no `RuntimeDispatch`/`RepurposeOutput` (output generation lives on YARNNN's own runtime), no `Clarify` (MCP uses the structured `ambiguous` return shape instead). The two permitted primitives (`QueryKnowledge` + `UpdateContext`) are the exact surface needed for "consult accumulated context + contribute back" and nothing more. ADR-169 decision; see [docs/features/mcp/architecture.md](../features/mcp/architecture.md).

---

## Target/Action Enumerations

For verbs that carry a typed sub-action, the enum is load-bearing. Single source of truth: the tool definitions in code. Mirrored here for reference.

### `UpdateContext.target`

6-value enum. Source of truth: `UPDATE_CONTEXT_TOOL.input_schema.properties.target.enum` in `api/services/primitives/update_context.py`.

| Target | Writes to | Typical caller |
|---|---|---|
| `identity` | Identity substrate (IDENTITY.md + inference merge) | TP during context inference |
| `brand` | Brand substrate (BRAND.md + inference merge) | TP during context inference |
| `memory` | `user_memory` KV store — appends (deduped) | TP in-session fact capture (ADR-156) |
| `agent` | Agent's workspace `memory/feedback.md` — appends feedback entry | TP routing user feedback about an agent |
| `task` | Task's `memory/feedback.md` by default; `feedback_target` sub-parameter can route to `DELIVERABLE.md` preference trail (ADR-149) or patch TASK.md sections directly (`criteria`, `objective`, `output_spec`, `run_log`) | TP routing user feedback on a task's output |
| `awareness` | TP's situational notes (shift handoff) — full replacement, living document | TP updating its own working awareness |

The `feedback_target` sub-parameter on `target="task"` has its own 5-value enum: `deliverable` (default, writes to `memory/feedback.md` for DELIVERABLE.md inference), `criteria`, `objective`, `output_spec`, `run_log`. It's a refinement of where within a task's substrate the feedback lands, not a top-level target.

### `ManageAgent.action`

| Action | Effect |
|---|---|
| `create` | Scaffold a new agent (identity + workspace + default tasks per capability bundle) |
| `update` | Patch agent identity or config |
| `pause` | Deactivate agent (tasks don't fire) |
| `resume` | Reactivate agent |
| `archive` | Soft-delete agent |

### `ManageTask.action`

8-value enum. Source of truth: `MANAGE_TASK_TOOL.input_schema.properties.action.enum` in `api/services/primitives/manage_task.py`. ADR-168 Commit 3 folded the former `CreateTask` primitive into this enum as `"create"` for symmetry with `ManageAgent`.

Note: `task_slug` is required for all actions EXCEPT `create` (which generates the slug from `title`). The top-level `required` field in the tool schema is `["action"]`; the `task_slug` requirement is enforced inside `handle_manage_task()` for non-create actions.

| Action | Effect | Mode availability | Introduced |
|---|---|---|---|
| `create` | Scaffold a new task from a task type (or custom `agent_slug` + `objective`), generate slug from `title`, write TASK.md + DELIVERABLE.md + memory scaffolds, create `tasks` row. | both | ADR-168 C3 |
| `trigger` | Fire the task immediately (dispatch to task pipeline via `_handle_trigger` → `execute_task()`) | both | ADR-146 |
| `update` | Patch task fields (schedule, objective, sources, delivery) | both | ADR-146 |
| `pause` | Set `tasks.status = 'paused'` | both | ADR-146 |
| `resume` | Set `tasks.status = 'active'`, recompute `next_run_at` | both | ADR-146 |
| `evaluate` | Write TP evaluation to `memory/feedback.md` (goal-mode steering) | chat | ADR-149 |
| `steer` | Write TP steering note to `memory/steering.md` | chat | ADR-149 |
| `complete` | Mark goal-mode task complete | chat | ADR-149 |

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
| `Execute` | `ManageTask(action="trigger")` / `UpdateContext(target="agent")` / `ManageTask(action="update")` | ADR-168 Commit 2 *(shipped 2026-04-09)* | Actions dissolve into typed verbs. Also removed: `action` + `system` entity types from `refs.py` (vestigial — only served Execute's action-discovery surface). |
| `CreateTask` | `ManageTask(action="create", title="...", type_key="..."\|agent_slug="...")` | ADR-168 Commit 3 *(shipped 2026-04-09)* | Symmetry with ManageAgent. Absorbed `title`, `type_key`, `agent_slug`, `focus`, `objective`, `success_criteria`, `output_spec` fields into `MANAGE_TASK_TOOL.input_schema`. Helpers (`_slugify`, `_build_custom_task_md`) moved into `manage_task.py`. File `primitives/task.py` deleted. |
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
