# ADR-146: Primitive Hardening — Consolidation & Design Principles

> **Status**: Gate 1 Implemented
> **Created**: 2026-03-28
> **Supersedes**: docs/architecture/primitives.md (stale — still documents projects, PM primitives, agent_chat mode)
> **Related ADRs**: ADR-138 (Agents as Work Units), ADR-141 (Unified Execution), ADR-144 (Inference-First Context), ADR-145 (Task Type Registry)
> **Implementation**: `api/services/primitives/`

---

## Problem

The primitive set has grown organically from 7 (v2, 2026-02-11) to 27 (current) through per-ADR additions. Each ADR introduced its own tools without asking: *does this belong as a separate primitive, or is it a parameter on an existing one?*

### Symptoms

1. **No design principle for tool boundaries.** "New ADR = new primitive" became the de facto heuristic. Result: 27 tools that an LLM must parse, understand, and choose between — directly degrading tool selection accuracy.

2. **Context mutation is fragmented across 4 primitives.** `UpdateSharedContext` (identity/brand), `SaveMemory` (notes), `WriteAgentFeedback` (agent preferences), `WriteTaskFeedback` (task specs) all persist "something TP learned from the user." TP must classify the user's intent into the correct bucket — a routing decision the inference layer should handle, exactly as `UpdateSharedContext` already infers *where in IDENTITY.md* to put content.

3. **Task lifecycle is 5 separate tools.** `CreateTask`, `TriggerTask`, `UpdateTask`, `PauseTask`, `ResumeTask` — the last three are status/schedule mutations on an existing task. PauseTask and ResumeTask are literally status toggles.

4. **The CRUD quintet predates the workspace filesystem.** `Read`, `Write`, `Edit`, `List`, `Search` were designed for a `type:identifier` reference grammar world. Post-ADR-106, workspace files coexist as a parallel addressing system. `Write(ref="memory:new")` and `WriteWorkspace(path="memory/x.md")` are two paradigms for the same operation. In practice, `Write` is vestigial — agent creation redirects to `ManageAgent`, memory creation is handled by `SaveMemory`, and document creation is handled by file upload.

5. **Execute is a grab bag.** 4 remaining actions (`agent.generate`, `platform.publish`, `agent.acknowledge`, `agent.schedule`) with no unifying principle. `agent.generate` is redundant with `TriggerTask`. `agent.acknowledge` is a workspace append.

6. **Canonical docs are stale.** `docs/architecture/primitives.md` still documents projects, `CreateProject`, `AdvanceAgentSchedule`, PM role-gating, `agent_chat` mode — all eliminated by ADR-138. The doc says 25 primitives; the registry has 27. Neither is correct for the current architecture.

7. **Headless-only tools inflate the chat toolset.** All 27 primitives are defined in `PRIMITIVES`, then filtered by `get_tools_for_mode()`. But the flat list in the registry obscures which tools the LLM actually sees. Chat mode exposes ~18 tools; headless ~16. The shared definition creates the illusion of a larger surface than either consumer faces.

### Cost of Inaction

Every unnecessary tool in the TP prompt:
- Increases token cost (~200 tokens per tool definition)
- Dilutes tool selection accuracy (more options = more classification error)
- Forces TP to learn routing rules that belong in infrastructure
- Makes the prompt longer and behavioral guidance more complex

---

## Design Principles (New)

These principles govern when something deserves to be a primitive vs. a parameter on an existing primitive, and how the primitive set should evolve.

### P1: Tools Are Verbs, Not Nouns

A primitive should represent a *class of action* (update context, manage task, search), not an *entity type* or *field*. If two tools differ only in their target, they should be one tool with a parameter.

**Test**: "Would a developer create a separate function for this, or add a parameter?" If the latter, it's one primitive.

### P2: Inference Over Classification

When the LLM must decide *where* information goes, prefer a single tool that routes internally over multiple tools the LLM must choose between. The LLM is good at *gathering* information but error-prone at *classifying* its destination.

**Test**: "Is this routing decision better made by infrastructure (deterministic) or the LLM (probabilistic)?" If deterministic is possible, route internally.

### P3: One Tool Per Decision

Each primitive should represent one user-visible decision by TP. "Create a task" is one decision. "Pause a task" is one decision. But "update task schedule" and "pause task" are both "change task state" — one tool, one decision: what to change.

### P4: Separate Chat and Headless Registries

Chat and headless modes serve different consumers (user-facing TP vs. background agents) with different tool needs. Define them as two explicit lists, not one list with mode filtering. This makes the actual surface visible at a glance.

### P5: Surface Area Budget

**Chat mode: ≤15 tools.** This is the LLM's cognitive budget. Every tool above 15 must justify itself with usage data showing it's called >5% of sessions. Headless mode: no hard limit (agents are specialized; their tool selection is narrower by context).

---

## Decision

### Phase 1: Consolidate Context Mutations (4 → 1)

**Merge** `UpdateSharedContext`, `SaveMemory`, `WriteAgentFeedback`, `WriteTaskFeedback` into a single **`UpdateContext`** primitive.

```python
UpdateContext(
    target: "identity" | "brand" | "memory" | "agent" | "task",
    text: str,                    # What TP learned from the user
    agent_slug: Optional[str],    # Required for target="agent"
    task_slug: Optional[str],     # Required for target="task"
    document_contents: Optional[list],  # For identity/brand inference
    url_contents: Optional[list],       # For identity/brand inference
)
```

**Internal routing:**
- `target="identity"` / `target="brand"` → inference merge (existing `infer_shared_context()`)
- `target="memory"` → append to `memory/notes.md` (existing `SaveMemory` logic)
- `target="agent"` → append to agent `memory/feedback.md` (existing `WriteAgentFeedback` logic)
- `target="task"` → patch TASK.md or append to `memory/run_log.md` (existing `WriteTaskFeedback` logic)

**Why this works:** TP already gathers the information ("the user wants formal tone in reports"). The only remaining decision is *what scope* — which is a simple enum, not a separate tool. And for identity/brand, the inference layer handles the hard part (where in the file to merge it).

**Migration:** Delete `UpdateSharedContext`, `SaveMemory`, `WriteAgentFeedback`, `WriteTaskFeedback` from registry. Add `UpdateContext`. Update TP prompt tools section and behavioral guidance.

### Phase 2: Consolidate Task Lifecycle (5 → 2)

**Keep** `CreateTask` (complex, registry-aware, writes TASK.md).
**Merge** `TriggerTask`, `UpdateTask`, `PauseTask`, `ResumeTask` into **`ManageTask`**.

```python
ManageTask(
    task_slug: str,
    action: "trigger" | "update" | "pause" | "resume",
    # For action="trigger":
    context: Optional[str],
    # For action="update":
    schedule: Optional[dict],
    delivery: Optional[dict],
    mode: Optional[str],
)
```

**Why:** These are all mutations on an existing task. TP already knows which task — the only decision is what to do. One tool, one decision.

### Phase 3: Retire Vestigial CRUD Primitives

**Delete `Write`** — Every creation path has a specialized primitive:
- Agents → `ManageAgent`
- Tasks → `CreateTask`
- Memories → `UpdateContext(target="memory")`
- Documents → file upload (not a primitive)

`Write` currently redirects agent creation to `ManageAgent` anyway. Its remaining paths (memory:new, document:new) are either handled by `UpdateContext` or unused.

**Retire `Execute`** — Its remaining actions dissolve:
- `agent.generate` → `ManageTask(action="trigger")` (tasks are the execution unit, not agents directly)
- `agent.acknowledge` → `UpdateContext(target="agent", text="...")` (it's a context update)
- `platform.publish` → Keep as standalone `PublishToplatform` if still used, or fold into ManageTask delivery
- `agent.schedule` → `ManageTask(action="update", schedule=...)` for task-based scheduling

**Evaluate `Edit`** — Its agent-specific paths (status, instructions, observations) need audit:
- `status` changes → May fold into agent management
- `agent_instructions` → Already writes to workspace AGENT.md; could become `UpdateContext(target="agent")`
- `append_observation` / `set_goal` → Workspace operations; `UpdateContext` subsumes

**Keep `Read`, `List`, `Search`** — These are genuine discovery primitives with no specialized replacement.

### Phase 4: Explicit Mode Registries

Replace single `PRIMITIVES` list + `PRIMITIVE_MODES` filter with two explicit registries:

```python
CHAT_PRIMITIVES = [
    # Discovery (4)
    READ_TOOL, LIST_TOOL, SEARCH_TOOL, GET_SYSTEM_STATE_TOOL,
    # External (3)
    REFRESH_PLATFORM_CONTENT_TOOL, WEB_SEARCH_PRIMITIVE, LIST_INTEGRATIONS_TOOL,
    # Context mutations (1)
    UPDATE_CONTEXT_TOOL,
    # Agent/Task lifecycle (3)
    CREATE_AGENT_TOOL, CREATE_TASK_TOOL, MANAGE_TASK_TOOL,
    # Interaction (1)
    CLARIFY_TOOL,
    # Agent editing (1 — evaluate Phase 3)
    EDIT_TOOL,
]  # 13 tools — under budget

HEADLESS_PRIMITIVES = [
    # Discovery
    READ_TOOL, LIST_TOOL, SEARCH_TOOL, GET_SYSTEM_STATE_TOOL,
    # External
    REFRESH_PLATFORM_CONTENT_TOOL, WEB_SEARCH_PRIMITIVE,
    # Workspace (5)
    READ_WORKSPACE_TOOL, WRITE_WORKSPACE_TOOL, SEARCH_WORKSPACE_TOOL,
    QUERY_KNOWLEDGE_TOOL, LIST_WORKSPACE_TOOL,
    # Inter-agent (2)
    DISCOVER_AGENTS_TOOL, READ_AGENT_CONTEXT_TOOL,
    # Lifecycle
    CREATE_AGENT_TOOL, CREATE_TASK_TOOL, MANAGE_TASK_TOOL,
    # Output
    RUNTIME_DISPATCH_TOOL,
]  # 16 tools
```

### Phase 5: Update Canonical Docs

**Rewrite `docs/architecture/primitives.md`** from scratch:
- Remove all project/PM/agent_chat references (ADR-138 eliminated these)
- Document the two registries (chat + headless)
- Document the 5 design principles
- Update entity schemas for current reality (agents + tasks, no projects)
- Update reference syntax (audit which `type:identifier` patterns are still used)
- Add primitive decision tree: "I want to... → use this tool"

---

## Consolidated Primitive Set

### Chat Mode (13 tools → from 18)

| # | Primitive | Purpose |
|---|-----------|---------|
| 1 | **Read** | Get entity by reference |
| 2 | **List** | Find entities by pattern |
| 3 | **Search** | Find by content |
| 4 | **Edit** | Modify entity fields (under review — Phase 3) |
| 5 | **GetSystemState** | System introspection |
| 6 | **RefreshPlatformContent** | Sync platform data |
| 7 | **WebSearch** | Search the web |
| 8 | **list_integrations** | Platform metadata |
| 9 | **UpdateContext** | All context mutations (identity, brand, memory, agent feedback, task feedback) |
| 10 | **ManageAgent** | Create agent identity |
| 11 | **CreateTask** | Create task with registry |
| 12 | **ManageTask** | Trigger, update, pause, resume tasks |
| 13 | **Clarify** | Ask user for input |

### Headless Mode (16 tools → from 16)

| # | Primitive | Purpose |
|---|-----------|---------|
| 1-6 | Discovery + External | Same as chat (minus Edit, list_integrations, Clarify, UpdateContext) |
| 7-11 | Workspace suite | ReadWorkspace, WriteWorkspace, SearchWorkspace, QueryKnowledge, ListWorkspace |
| 12-13 | Inter-agent | DiscoverAgents, ReadAgentContext |
| 14-15 | Lifecycle | ManageAgent, CreateTask, ManageTask |
| 16 | Output | RuntimeDispatch |

### Deleted (14 tools removed from combined surface)

| Primitive | Absorbed Into | Rationale |
|-----------|--------------|-----------|
| `UpdateSharedContext` | `UpdateContext` | P2: Inference over classification |
| `SaveMemory` | `UpdateContext` | P2: Same action, different target |
| `WriteAgentFeedback` | `UpdateContext` | P2: Same action, different scope |
| `WriteTaskFeedback` | `UpdateContext` | P2: Same action, different scope |
| `TriggerTask` | `ManageTask` | P3: One tool per decision |
| `UpdateTask` | `ManageTask` | P3: One tool per decision |
| `PauseTask` | `ManageTask` | P3: One tool per decision |
| `ResumeTask` | `ManageTask` | P3: One tool per decision |
| `Write` | Specialized primitives | P1: No remaining unique purpose |
| `Execute` | `ManageTask` + `UpdateContext` | P1: Actions dissolve into typed tools |

---

## Implementation Plan

### Gate 1: UpdateContext + ManageTask (code changes)
1. Create `api/services/primitives/update_context.py` — unified handler with target-based routing
2. Create `api/services/primitives/manage_task.py` — unified handler with action-based routing
3. Update `registry.py` — remove old tools, add new ones, split into `CHAT_PRIMITIVES` / `HEADLESS_PRIMITIVES`
4. Delete: `save_memory.py` (logic moves to update_context.py), standalone task lifecycle handlers from `task.py`
5. Update TP prompts: `tools.py`, `behaviors.py`, `onboarding.py`
6. Update `api/prompts/CHANGELOG.md`

### Gate 2: Retire Write + Execute
1. Delete `write.py` — audit remaining callers first
2. Refactor `execute.py` — dissolve actions into ManageTask / UpdateContext / PublishToPlatform
3. Evaluate `edit.py` — determine which paths survive vs. fold into UpdateContext

### Gate 3: Docs overhaul
1. Rewrite `docs/architecture/primitives.md` from scratch
2. Archive current version to `docs/adr/archive/primitives-v3-pre-hardening.md`
3. Update CLAUDE.md primitive references

---

## Consequences

### Positive
- **Chat tool count drops from ~18 to 13** — measurably better tool selection accuracy
- **TP prompt shrinks** — ~1,000 fewer tokens in tool definitions
- **Context mutations become inference-driven** — TP says "this is what I learned," infrastructure decides where it goes
- **Design principles prevent future bloat** — new tools must justify their existence against P1-P5
- **Docs reflect reality** — canonical doc matches actual code for the first time since ADR-138

### Negative
- **Migration effort** — existing behavioral guidance references old tool names
- **Prompt rewrite** — tools.py and behaviors.py need significant updates
- **Testing** — tool consolidation requires end-to-end validation of all routing paths

### Risks
- **Routing accuracy in UpdateContext** — the `target` enum must be unambiguous. If TP can't distinguish "agent feedback" from "memory note," the consolidation fails. Mitigation: clear target descriptions + examples in tool definition.
- **ManageTask action overload** — if `update` gains too many optional fields, it becomes a god-tool. Mitigation: keep optional fields minimal; complex changes go through TP conversation → CreateTask replacement.

---

## Alternatives Considered

### A: Keep All 27, Just Fix Docs
Rejected. The problem isn't documentation — it's tool selection accuracy. 27 tools force TP to make fine-grained classification decisions that infrastructure should handle. Fixing docs without consolidating tools addresses a symptom, not the cause.

### B: Collapse Everything Into CRUD + Execute
Rejected. The original 7-primitive vision (Read, Write, Edit, List, Search, Execute, Clarify) was elegant but doesn't work for specialized operations like task creation (registry-aware, writes TASK.md) or context inference (LLM merge). Some specialization is necessary; the question is *how much*.

### C: AI-Routed Single Tool
A single `Do(intent, context)` tool where an inner LLM routes to the correct handler. Rejected — adds latency, cost, and a debugging black box. The `target` enum approach gives deterministic routing with the same UX benefit.

---

## References

- `docs/adr/archive/primitives-v2.md` — Original 7-primitive design (2026-02-11)
- `docs/architecture/primitives.md` — Stale canonical doc (to be rewritten)
- `api/services/primitives/registry.py` — Current 27-primitive registry
- `api/agents/tp_prompts/tools.py` — Current TP tool documentation
- `api/agents/tp_prompts/behaviors.py` — Current TP behavioral guidance
