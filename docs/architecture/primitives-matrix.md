# Primitives Matrix — Substrate × Mode × Capability

**Status:** Canonical — reflects post-ADR-168 + post-ADR-196 state
**Last updated:** 2026-04-20 (FOUNDATIONS v6.0 alignment — primitives framed as Mechanism-dimension vocabulary)
**Governing ADRs:** ADR-146 (Primitive Hardening), ADR-168 (this matrix — substrate/mode/capability axes + entity/file naming reform), ADR-169 (MCP as third caller), ADR-196 (user_memory table sunset)
**Related:** ADR-154 (Who/What/How), ADR-080 (Unified Agent Modes), ADR-151 (Context Domains), ADR-164 (YARNNN as Agent), ADR-166 (precedent for two-axis registry cleanup), FOUNDATIONS Axiom 1 (filesystem substrate) + Axiom 5 (Mechanism spectrum)

---

## Dimensional framing (FOUNDATIONS v6.0)

Primitives are the **vocabulary of the Mechanism dimension** (Axiom 5). LLM reasoning in YARNNN speaks through primitives — typed verbs with substrate and permission scope. Prompts are the other half of Mechanism's vocabulary — they configure which primitives the LLM reaches for, in which situations. **Designing primitives without prompts, or prompts without primitives, is a dimensional conflation** (FOUNDATIONS Derived Principle 9).

Primitives carry orthogonal scoping across the other five dimensions:

| FOUNDATIONS dimension | How primitives encode it |
|---|---|
| Substrate (what) | Substrate family column (`entity` / `file` / `context` / `lifecycle` / `action` / `interaction` / `external` / `introspection`) |
| Identity (who) | Mode availability (`chat` / `headless` / `MCP`) — which cognitive-layer runtime can call the primitive |
| Purpose (why) | Capability tags (`user-channel`, `user-authorized`, `context-mutation`, etc.) — intent scoping |
| Trigger (when) | Not encoded in the primitive itself — Trigger lives in the caller (scheduler / event / chat turn) |
| Channel (where) | Implicit in return shape — some primitives write substrate, some address external destinations |

**The matrix below is a view onto primitives' placement across these dimensions.** Reading it is reading Mechanism's vocabulary and its scoping.
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

### CRUD split (ADR-206 — operator-facing surface convention)

The primitive set is runtime-neutral, but the *operator surface* convention per ADR-206 routes CRUD actions by cognitive weight:

| Operation | Surface | Primitive path |
|-----------|---------|----------------|
| **Create** (task, agent, rule, signal, SKU) | Modal (`CreateTaskModal`, `AuthorAgentModal`, `CreateRuleModal`) | `ManageTask(action="create")` / `ManageAgent(action="create")` / `UpdateContext` for rule authoring. High-precision, well-specified; modal provides structured fields. |
| **Read** | Direct surface view | Any read primitive (`ReadFile`, `LookupEntity`, `SearchFiles`, `QueryKnowledge`). No modal or chat required. |
| **Update** | Chat + YARNNN | `ManageTask(action="update")`, `ManageAgent(action="update")`, `UpdateContext`, `EditEntity`, `WriteFile`. Judgment-shaped — YARNNN asks "why", proposes alternatives, remembers reasoning. |
| **Delete / archive** | Chat + YARNNN, confirmation required | `ManageTask(action="archive")`, `ManageAgent(action="archive")`. Irreversibility warrants conversation; YARNNN writes attribution to `/workspace/memory/awareness.md`. |
| **Approve / reject proposal** (money-bearing) | Direct click on cockpit Queue | `handle_execute_proposal` / `handle_reject_proposal`. Not CRUD — surface-level action on a Deliverable. YARNNN observes via compact index. |

**Rule of thumb:** direct surface action for *high-precision actions on a known artifact*; chat for *judgment-shaped or context-rich actions*. YARNNN observes all of them regardless — the operator never leaves YARNNN's awareness, but YARNNN is not a mandatory mediator for every click.

---

## The Substrate Families

### `entity` — Relational entity layer

Operates on typed entity references (`<type>:<UUID>` format). Resolves through [api/services/primitives/refs.py](../../api/services/primitives/refs.py) via `parse_ref` + `resolve_ref`. Types: `agent`, `platform`, `session`, `document`, `work`.

**Axiom 0 note:** The entity layer is narrow by design — it operates only on the "scheduling index / credential / ephemeral queue" DB rows permitted by FOUNDATIONS Axiom 0. Semantic content (memory, domain state, theses, observations) lives in files, reached through the `file` substrate family below, not here. ADR-196 removed the stale `memory` and `domain` entity types from `ENTITY_TYPES` when `user_memory` was dropped — both had pointed at a table that held semantic content in DB rows, a violation of Axiom 0. The filesystem replacements (`/workspace/memory/*.md`, `/workspace/context/{domain}/`) are reached via the file substrate.

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

## Perception channel: how YARNNN senses state before it acts

**The matrix below is YARNNN's action vocabulary. It is not YARNNN's entire input surface.** Before YARNNN reaches for a primitive, it reads a precomputed perception channel that is injected into its system prompt on every turn. This section documents that channel so the matrix isn't misread as the only way YARNNN knows about workspace state.

### Two input channels

| Channel | What it carries | When it runs | Who produces it | Primitive cost |
|---|---|---|---|---|
| **Perception** (working memory) | Workspace state snapshot: identity/brand richness, task counts, stale tasks, budget, agent health, context domain fullness, recent uploads, active tasks, recent sessions, system summary | Once per YARNNN turn, before tool dispatch | [api/services/working_memory.py](../../api/services/working_memory.py) `format_compact_index()` | Zero LLM, zero primitives — pure SQL precompute |
| **Action** (primitives) | Mutations + lookups YARNNN initiates in response to what it read from perception | During tool rounds | The primitives in the matrix below | One tool call per verb |

YARNNN **reads perception → decides → acts through primitives**. It does not call primitives to reconstruct state that the perception channel already carries.

### What working memory injects into YARNNN's prompt

Single source of truth: [api/services/working_memory.py:format_compact_index()](../../api/services/working_memory.py). Key fields in the injected dict:

- **`workspace_state`** (ADR-156) — the meta-awareness signal. Identity/brand richness classification (empty / partial / rich), document count, context domain count with content, active task count, stale task count, credits used/limit, budget-exhausted flag, flagged-agent list.
- **`active_tasks`** — currently active task summaries with last run / next run freshness.
- **`context_domains`** — per-domain health: file count, temporal flag, entity count.
- **`recent_uploads`** (ADR-162 Sub-phase B) — documents uploaded in last 7 days that YARNNN may want to process.
- **`recent_sessions`** — prior session continuity markers.
- **`system_summary`** + **`system_reference`** — tier, limits, connected platforms.
- **`user_shared_files`** — shared uploads available as context.
- **`identity`**, **`brand`**, **`awareness`**, **`conversation_summary`** — the narrative layer of workspace memory (ADR-159 filesystem-as-memory).

All of this is precomputed from SQL and file reads — **zero LLM calls** produced it. YARNNN receives it as a compact index (~500 tokens after ADR-159) and reads deeper on demand via file-layer primitives when it needs detail.

### Why perception is not a primitive

This is deliberate, not drift. Two ADRs govern it:

1. **ADR-156 (Composer Sunset / Single Intelligence Layer)**. Making YARNNN call `GetSystemState` + `ListEntities(type=task)` + `QueryKnowledge(domain=…)` + `ListFiles(…)` on every turn to reconstruct workspace state would reintroduce exactly the pattern ADR-156 deleted Composer to avoid — a second reasoning loop judging state that SQL can compute deterministically. Primitives are for actions, not for waste-motion sensing.

2. **ADR-159 (Filesystem-as-Memory)**. YARNNN's prompt is a compact index (~500 tokens) plus on-demand file reads. The compact index *is* the meta-awareness layer. A `GetWorkspaceState` primitive would duplicate what the compact index already carries, burn a tool round to get it, and cost ~70% of the token savings ADR-159 delivered.

Consequence: **there is no `GetWorkspaceState` primitive and there will not be one.** If a state signal is missing from YARNNN's perception, the fix is to add it to `working_memory.format_compact_index()`, not to create a primitive.

### A realistic meta-awareness loop

Concrete example of how perception and action compose during a cold-start onboarding conversation:

| Turn | Perception YARNNN reads (from working memory) | YARNNN decides | Primitive YARNNN calls |
|---|---|---|---|
| 1 | `workspace_state.identity = "empty"`, `tasks_active = 1` (daily-update), `documents = 0` | Cold start. Need context input. | `Clarify(question="Tell me about your work — paste docs, URLs, or describe it in chat?")` |
| 2 | User pastes material → `recent_uploads` populated, user message has text | Run inference. | `UpdateContext(target="identity", text=…)` (context inference) |
| 3 | `workspace_state.identity = "rich"`, `context_domains = 0` | Scaffold domain entities so `track-*` tasks have substrate. | `ManageDomains(action="scaffold", entities=[…])` |
| 4 | `context_domains = 3`, `tasks_active = 1` | Suggest a first recurring deliverable. | `ManageTask(action="create", task_type="competitive-brief", …)` (post-Commit 3) |
| 5 | User: "show me what's running" → `active_tasks` already in compact index | Answer from perception; no primitive needed. | *(no tool call — compose answer from working memory)* |

Four primitives touched in five turns, across four different substrate families (`interaction`, `context`, `lifecycle`, `lifecycle`). Turn 5 uses zero primitives because perception already carries the answer. This is the intended shape: **perception surfaces state, primitives change it.**

Every verb in that loop is in the matrix below. The decision loop ("read perception, pick next action") lives in YARNNN's system prompt, not in any primitive.

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
| `ListFiles` | file | ○ | ● | ○ | file-layer | [workspace.py](../../api/services/primitives/workspace.py) | List files in the agent's workspace. ADR-209 Phase 3: accepts `authored_by` / `since` / `until` filters to answer "what has been written by whom lately". |
| `ListRevisions` | file | ● | ● | ○ | file-layer, authored-substrate | [revisions.py](../../api/services/primitives/revisions.py) | ADR-209 Phase 3. Return the revision chain for a workspace path (newest first). Surfaces the Authored Substrate's parent-pointer history — who edited what, when. Chat parity intentional: operators + YARNNN inspect authored files through the same API. |
| `ReadRevision` | file | ● | ● | ○ | file-layer, authored-substrate | [revisions.py](../../api/services/primitives/revisions.py) | ADR-209 Phase 3. Read a specific historical revision of a file (by offset or revision_id). Returns content + full authorship trailer. Zero-LLM, pure substrate read. |
| `DiffRevisions` | file | ● | ● | ○ | file-layer, authored-substrate | [revisions.py](../../api/services/primitives/revisions.py) | ADR-209 Phase 3. Pure-Python unified diff between two revisions of the same path. Zero LLM cost, deterministic. |
| `QueryKnowledge` | file | ○ | ● | ● | semantic-query | [workspace.py](../../api/services/primitives/workspace.py) | Semantic ranked query over accumulated `/workspace/context/` domains (ADR-151). Distinct from `SearchFiles` — returns ranked results with domain/metadata filters. **MCP's primary primitive**: `pull_context` is a thin wrapper, `work_on_this` composes over it. |
| `ReadAgentFile` | file | ○ | ● | ○ | file-layer, inter-agent | [workspace.py](../../api/services/primitives/workspace.py) | Read a file from another agent's workspace (read-only, ADR-116). |
| `DiscoverAgents` | lifecycle | ○ | ● | ○ | inter-agent | [workspace.py](../../api/services/primitives/workspace.py) | Find other agents in the workspace by role/scope/status (ADR-116 Phase 2). |
| `UpdateContext` | context | ● | ○ | ● | context-mutation | [update_context.py](../../api/services/primitives/update_context.py) | Single verb for all context mutations. Targets: `identity`, `brand`, `memory`, `agent`, `task`, `awareness`. **MCP `remember_this`** dispatches here with a two-branch classifier (workspace-level targets default safely to `memory`, operational feedback uses slug disambiguation). ADR-169 decision: all UpdateContext targets available via MCP *except `awareness`* (YARNNN-only). Safety via ADR-162 provenance stamping, not pre-write guards. |
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

### Mode totals (current state, post-ADR-168 + ADR-169 + ADR-209 Phase 3)

- **Chat mode:** 17 static primitives — `LookupEntity`, `ListEntities`, `SearchEntities`, `EditEntity`, `GetSystemState`, `WebSearch`, `list_integrations`, `UpdateContext`, `ManageDomains`, `ManageAgent`, `ManageTask`, `RepurposeOutput`, `RuntimeDispatch`, `Clarify`, plus ADR-209 Phase 3: `ListRevisions`, `ReadRevision`, `DiffRevisions` (ADR-193 adds `ProposeAction` / `ExecuteProposal` / `RejectProposal` = 20 total). Note: `RuntimeDispatch` was added for YARNNN image/asset generation via Gemini (charts, diagrams, hero images). ADR-186: the primitive set is constant across both prompt profiles — behavioral guidance (not tool availability) determines when YARNNN reaches for each tool. ADR-209 Phase 3 chat parity rationale: operators and YARNNN both need to inspect authored files through the same revision-aware API; the cockpit supervision property (ADR-198) depends on it.
- **Headless mode:** 19 static primitives + `platform_*` dynamic — `LookupEntity`, `ListEntities`, `SearchEntities`, `GetSystemState`, `WebSearch`, `ReadFile`, `WriteFile`, `SearchFiles`, `QueryKnowledge`, `ListFiles`, `DiscoverAgents`, `ReadAgentFile`, `ManageAgent`, `ManageTask`, `ManageDomains`, `RuntimeDispatch`, plus ADR-209 Phase 3: `ListRevisions`, `ReadRevision`, `DiffRevisions` (ADR-193 adds `ProposeAction` = 20 static total).
- **MCP mode (ADR-169):** 2 primitives — `QueryKnowledge` and `UpdateContext`. The MCP tool surface itself is three intent-shaped tools (`work_on_this`, `pull_context`, `remember_this`) that compose over these two primitives. MCP is the foreign-LLM surface — third caller of `execute_primitive()` per ADR-164 runtime-agnostic principle. See [docs/features/mcp/architecture.md](../features/mcp/architecture.md) for the composition layer (`api/services/mcp_composition.py`). **ADR-209 Phase 3 note on MCP**: `ListRevisions` / `ReadRevision` / `DiffRevisions` are deliberately NOT exposed on the MCP surface. The MCP contract is intent-shaped (consult accumulated context, contribute back), not substrate-archaeology-shaped. Foreign LLMs that need revision context receive it through `pull_context` results when relevant; they do not traverse the revision chain directly.

**Hard boundaries (enforced by [api/test_recent_commits.py](../../api/test_recent_commits.py)):**

- Chat does NOT have agent-scoped file-layer write/search primitives (`ReadFile`, `WriteFile`, `SearchFiles`, `ListFiles`). YARNNN operates on task/agent paths through `EditEntity` on typed refs, not through agent-scoped file I/O. **Exception (ADR-209 Phase 3):** the three revision-aware primitives (`ListRevisions`, `ReadRevision`, `DiffRevisions`) ARE available in chat because operators and YARNNN both need to inspect authored files' history for cockpit supervision; revision inspection is workspace-absolute, not agent-scoped, and substrate-read-only.
- Chat has `RuntimeDispatch` for explicit user requests (image generation, charts, diagrams). YARNNN uses it when the user asks for a visual asset or when a visual would materially improve a response.
- Headless does NOT have `EditEntity`, `Clarify`, `UpdateContext`, `RepurposeOutput`, or `list_integrations`. No user-authorization path in headless mode, no user channel, no user-facing mutations, no platform metadata needs that aren't already resolved at capability-bundle time.
- **MCP does NOT have any lifecycle, entity-layer, or agent-scoped file-layer primitives.** MCP callers (foreign LLMs acting on behalf of the user) are consultation-shaped, not operator-shaped. The user in a foreign LLM is in thinking mode, not workforce-management mode — the MCP surface reflects that. Specifically: no `ManageAgent`/`ManageTask`/`ManageDomains` (no workforce control from foreign LLMs), no `LookupEntity`/`ListEntities`/`SearchEntities`/`EditEntity` (entity layer is YARNNN-chat-only), no `ReadFile`/`WriteFile`/`SearchFiles`/`ListFiles`/`ReadAgentFile` (agent-scoped file layer is headless-only), no `RuntimeDispatch`/`RepurposeOutput` (output generation lives on YARNNN's own runtime), no `Clarify` (MCP uses the structured `ambiguous` return shape instead). The two permitted primitives (`QueryKnowledge` + `UpdateContext`) are the exact surface needed for "consult accumulated context + contribute back" and nothing more. ADR-169 decision; see [docs/features/mcp/architecture.md](../features/mcp/architecture.md).

---

## Target/Action Enumerations

For verbs that carry a typed sub-action, the enum is load-bearing. Single source of truth: the tool definitions in code. Mirrored here for reference.

### `UpdateContext.target`

6-value enum. Source of truth: `UPDATE_CONTEXT_TOOL.input_schema.properties.target.enum` in `api/services/primitives/update_context.py`.

| Target | Writes to | Typical caller |
|---|---|---|
| `identity` | Identity substrate (IDENTITY.md + inference merge) | YARNNN during context inference |
| `brand` | Brand substrate (BRAND.md + inference merge) | YARNNN during context inference |
| `memory` | `user_memory` KV store — appends (deduped) | YARNNN in-session fact capture (ADR-156) |
| `agent` | Agent's workspace `memory/feedback.md` — appends feedback entry | YARNNN routing user feedback about an agent |
| `task` | Task's `memory/feedback.md` by default; `feedback_target` sub-parameter can route to `DELIVERABLE.md` preference trail (ADR-149) or patch TASK.md sections directly (`criteria`, `objective`, `output_spec`, `run_log`) | YARNNN routing user feedback on a task's output |
| `awareness` | YARNNN's situational notes (shift handoff) — full replacement, living document | YARNNN updating its own working awareness |

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
| `evaluate` | Write YARNNN evaluation to `memory/feedback.md` (goal-mode steering) | chat | ADR-149 |
| `steer` | Write YARNNN steering note to `memory/steering.md` | chat | ADR-149 |
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
- `api/agents/thinking_partner.py` — YARNNN system prompt
- `api/agents/yarnnn_prompts/*.py` — onboarding, tools, behaviors, system
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
- `docs/architecture/agent-registry.md` — capabilities → tool mapping
- `docs/architecture/agent-execution-model.md`
- `docs/architecture/YARNNN-DESIGN-PRINCIPLES.md`
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
- Expected behavior: How YARNNN/headless behavior shifts
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
| `Read` | `LookupEntity` | ADR-168 Commit 4 *(shipped 2026-04-09)* | Name was ambiguous with file-layer read |
| `List` | `ListEntities` | ADR-168 Commit 4 *(shipped 2026-04-09)* | Name was ambiguous |
| `Search` | `SearchEntities` | ADR-168 Commit 4 *(shipped 2026-04-09)* | Name was ambiguous |
| `Edit` | `EditEntity` | ADR-168 Commit 4 *(shipped 2026-04-09)* | Name was ambiguous |
| `ReadWorkspace` | `ReadFile` | ADR-168 Commit 4 *(shipped 2026-04-09)* | Substrate-first naming |
| `WriteWorkspace` | `WriteFile` | ADR-168 Commit 4 *(shipped 2026-04-09)* | Substrate-first naming |
| `SearchWorkspace` | `SearchFiles` | ADR-168 Commit 4 *(shipped 2026-04-09)* | Substrate-first naming |
| `ListWorkspace` | `ListFiles` | ADR-168 Commit 4 *(shipped 2026-04-09)* | Substrate-first naming |
| `ReadAgentContext` | `ReadAgentFile` | ADR-168 Commit 4 *(shipped 2026-04-09)* | Name was vague; it's a file read with `agent_slug` + `path` |
| `entity:memory` type | (file substrate — `/workspace/memory/*.md` via ReadFile/WriteFile) | ADR-196 *(shipped 2026-04-20)* | Semantic content → filesystem per Axiom 0. `user_memory` table dropped. Stale branches in `refs.py`, `read.py`, `write.py`, `edit.py`, `list.py` stripped in same commit. |
| `entity:domain` type | (file substrate — `/workspace/context/{domain}/` via ReadFile/WriteFile/QueryKnowledge) | ADR-196 *(shipped 2026-04-20)* | Same rationale — pointed at `user_memory`; semantic content lives in filesystem context domains per ADR-151. |

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
- [agent-registry.md](agent-registry.md) — agent types and the `capabilities` → primitive mapping.
- [SERVICE-MODEL.md](SERVICE-MODEL.md) — system-level description; this doc is the primitive-level deep dive.
- [YARNNN-DESIGN-PRINCIPLES.md](YARNNN-DESIGN-PRINCIPLES.md) — design principles for YARNNN's use of chat-mode primitives.
- [workspace-conventions.md](workspace-conventions.md) — filesystem layout that the `file` substrate family operates on.
- [api/services/primitives/registry.py](../../api/services/primitives/registry.py) — source of truth for registries and handlers.
- [api/prompts/CHANGELOG.md](../../api/prompts/CHANGELOG.md) — behavioral change history.
