# ADR-168: Primitive Matrix — Two Axes, Entity/File/Action Families, Finish ADR-146

**Status:** Proposed
**Date:** 2026-04-09
**Authors:** KVK, Claude
**Extends:** ADR-146 (Primitive Hardening), ADR-154 (Execution Boundary Reform), ADR-080 (Unified Agent Modes)
**Supersedes:** ADR-146 Phase 3 (Execute retirement, Write/Edit audit — previously deferred) and ADR-146 Phase 5 (canonical primitives doc — never shipped)
**Related:** ADR-164 (TP as Agent), ADR-166 (Registry Coherence Pass — precedent for two-axis cleanup)

---

## Context

After ADRs 138 → 164 progressively evolved the agent and task models (tasks as work units, unified execution, TP as agent), the primitive layer is visibly the next thing lagging the unification story. A coherence audit conducted on 2026-04-09 surfaced five issues.

### Issue 1: ADR-146 Phase 5 was never executed

ADR-146 Phase 5 explicitly committed to "Rewrite `docs/architecture/primitives.md` from scratch" — documenting the two registries, the five design principles, the consolidated primitive set, and a primitive decision tree. That file does not exist in `docs/architecture/`. The only thing that ships today is `docs/architecture/previous_versions/primitives-analogy.md` — a pre-146 analogy document.

The consequence: primitive knowledge is scattered across 14+ files (ADR-146, ADR-151, ADR-153, ADR-154, ADR-155, SERVICE-MODEL.md, agent-framework.md, workspace-conventions.md, registry.py docstrings, individual primitive file docstrings). There is no single place to answer "what primitives exist, who can call them, and what do they do?" The primitive surface has grown post-146 — `ManageDomains` (ADR-155/157), `RepurposeOutput` (ADR-148) — without the canonical matrix being updated, because there was no canonical matrix to update.

### Issue 2: ADR-146 Phase 3 left `Execute` in place

ADR-146 Phase 3 specified the `Execute` primitive dissolution:

- `platform.publish` → `ManageTask` delivery path
- `agent.generate` → `ManageTask(action="trigger")`
- `agent.acknowledge` → `UpdateContext(target="agent")`
- `agent.schedule` → `ManageTask(action="update", schedule=…)`

Phase 3 was never executed. `api/services/primitives/execute.py` still exists, `EXECUTE_TOOL` and `handle_execute` still ship in `CHAT_PRIMITIVES` and `HANDLERS`, and the TP prompt still references `Execute(action=…)` shapes. This is real drift — not a rename question, an unfinished migration.

### Issue 3: `CreateTask` vs `ManageTask` asymmetry

`ManageAgent` covers creation (`handle_manage_agent` handles both new-agent and existing-agent flows). `ManageTask` doesn't — `CreateTask` is a separate primitive with its own tool, handler, and file ([api/services/primitives/task.py](../../api/services/primitives/task.py)). ADR-146 left this as-is and even codified it in Phase 4 ("Lifecycle (3): CREATE_AGENT_TOOL, CREATE_TASK_TOOL, MANAGE_TASK_TOOL"), but the asymmetry is visible friction every time a caller reaches for the task-lifecycle verb: "is this a creation or a manage? different call."

### Issue 4: Naming obscures the two substrates

The chat-mode primitives `Read`, `List`, `Search`, `Edit` and the headless-mode primitives `ReadWorkspace`, `WriteWorkspace`, `SearchWorkspace`, `ListWorkspace` look like near-duplicates. They are not. They address two different substrates:

1. **Entity layer.** `Read(ref="agent:uuid-123")` / `Read(ref="document:uuid-456")` operates on a relational abstraction through `parse_ref` + `resolve_ref` ([api/services/primitives/refs.py](../../api/services/primitives/refs.py)). Input is a typed reference string (`<type>:<UUID>`). Types: agent, platform, memory, session, domain, document, work. It's a **database-level entity lookup**.

2. **File layer.** `ReadWorkspace(path="AGENT.md")` / `WriteWorkspace(path="acme-corp/signals.md", scope="context", domain="competitors")` operates on a virtual filesystem through `AgentWorkspace` / `KnowledgeBase` classes ([api/services/workspace.py](../../api/services/workspace.py)). Input is a path string, scoped by `agent_slug` or `domain`. It's a **filesystem read/write**.

These are two different mental models, two different dispatch paths, and two different permission models. Calling both "Read" invites confusion every time someone reads the registry or writes a new prompt. Worse, it invites *wrong* intuitions: a new contributor sees `Read` and assumes it reads files; TP (the prompt) sees `Read` first in the tool list and has to be explicitly told that it doesn't work on paths.

The audit confirmed this isn't drift — it's a naming problem on top of a load-bearing distinction. The distinction should stay. The names should not obscure it.

### Issue 5: No capability taxonomy for "needs a user" / "runs against a substrate"

The chat/headless mode split is test-enforced ([api/test_recent_commits.py:306-336](../../api/test_recent_commits.py#L306-L336)) but the *reason* for each primitive's mode assignment lives in tribal knowledge. Why is `Clarify` chat-only? Because it literally needs a live user channel. Why is `UpdateContext` chat-only? Because targets like `identity` and `brand` are user-facing judgment calls. Why is `RuntimeDispatch` headless-only? Because it's an asset-render dispatch that runs post-generation, not a mid-conversation tool.

The reasons vary by primitive. None are documented anywhere a new contributor could discover without re-deriving the decision from the test file.

A caller-identity prefix convention was considered ("should TP-exclusive primitives be prefixed `TP*`?") and rejected — see "Alternatives Considered" below. The right instrument is a **capability tag** column on the matrix, not a name prefix.

---

## Decision

### 1. Ship the canonical matrix doc (finish ADR-146 Phase 5)

Write [docs/architecture/primitives-matrix.md](../architecture/primitives-matrix.md) as a sibling to `registry-matrix.md`. It is the single reference for:

- **Two axes**: substrate family (`entity` / `file` / `context` / `lifecycle` / `action` / `interaction` / `external` / `introspection`) and permission mode (`chat` / `headless` / `both`).
- **Capability tags**: `user-channel`, `user-authorized`, `entity-layer`, `file-layer`, `context-mutation`, `lifecycle`, `external`, `introspection`, `asset-render`.
- **Complete table** of every primitive with: verb, substrate family, mode, capability tags, handler file, one-line purpose.
- **Target/action enumerations** for `UpdateContext`, `ManageAgent`, `ManageTask`, `ManageDomains`, `RuntimeDispatch`, `RepurposeOutput`.
- **Rename protocol**: the standing grep-sweep checklist (CLAUDE.md rule 7b, pinned here as well so it's discoverable from the doc itself).
- **Deleted primitives** ledger — old name → replacement → superseding ADR.
- **Cross-references** to ADR-146, ADR-154, ADR-080, ADR-166 (the two-axis precedent), `registry-matrix.md`, `agent-framework.md`.

This doc is the standing reference. It never gets "versioned" — it reflects current state. History lives in the ADR chain (146 → 168 → future primitive ADRs) that the status header links to.

### 2. Dissolve `Execute` (finish ADR-146 Phase 3)

Delete [api/services/primitives/execute.py](../../api/services/primitives/execute.py) entirely. Remove `EXECUTE_TOOL` + `handle_execute` from `registry.py`. Remove from `HANDLERS`, `CHAT_PRIMITIVES`.

Migrate each known caller per ADR-146 Phase 3:

| Old call shape | New call shape | Rationale |
|---|---|---|
| `Execute(action="platform.publish", target="agent:uuid", via="platform:x")` | `ManageTask(action="trigger", task_id=…)` with delivery configured on the task | Tasks are the execution unit, not agents directly. Delivery is a task property. |
| `Execute(action="agent.generate", target="agent:uuid")` | `ManageTask(action="trigger", task_id=…)` | Same: execution is task-scoped. |
| `Execute(action="agent.acknowledge", target="agent:uuid", text="…")` | `UpdateContext(target="agent", agent_id=…, text="…")` | An acknowledgement is a context update, not an execution. |
| `Execute(action="agent.schedule", target="agent:uuid", schedule=…)` | `ManageTask(action="update", task_id=…, schedule=…)` | Schedules live on tasks (ADR-138). |

Caller migration is grep-enumerated in Commit 2 (below) — no caller is guessed.

**Singular implementation:** no shim, no fallback, no `Execute` → `ManageTask` redirect handler. `Execute` ceases to exist. Callers are migrated in the same commit.

### 3. Fold `CreateTask` into `ManageTask(action="create")`

Move `handle_create_task` logic into `handle_manage_task` as the `"create"` action branch. Delete `CREATE_TASK_TOOL`. Expand `MANAGE_TASK_TOOL.input_schema.action.enum` to include `"create"`. Delete [api/services/primitives/task.py](../../api/services/primitives/task.py) (the file becomes empty after removing `CREATE_TASK_TOOL` and `handle_create_task`).

This mirrors `ManageAgent` which already covers agent creation. After this change, the two lifecycle verbs have symmetric shapes:

```
ManageAgent(action="create"|"update"|"pause"|"resume"|..., agent_id=...)
ManageTask (action="create"|"trigger"|"update"|"pause"|"resume"|"evaluate"|"steer"|"complete", task_id=...)
```

### 4. Rename primitives to two verb families: `*Entity` and `*File`

The load-bearing distinction between the entity layer and the file layer becomes visible in the names themselves. Renames:

| Current | New | Substrate | Mode (unchanged) |
|---|---|---|---|
| `Read(ref=…)` | `LookupEntity(ref=…)` | Entity layer | chat |
| `List(...)` | `ListEntities(...)` | Entity layer | chat |
| `Search(...)` | `SearchEntities(...)` | Entity layer | chat |
| `Edit(...)` | `EditEntity(...)` | Entity layer | chat |
| `ReadWorkspace(path=…)` | `ReadFile(path=…)` | File layer | headless |
| `WriteWorkspace(path=…)` | `WriteFile(path=…)` | File layer | headless |
| `SearchWorkspace(query=…)` | `SearchFiles(query=…)` | File layer | headless |
| `ListWorkspace(path=…)` | `ListFiles(path=…)` | File layer | headless |
| `ReadAgentContext(agent_slug, path)` | `ReadAgentFile(agent_slug, path)` | File layer | headless |

**Kept as-is (correctly named):**

- `QueryKnowledge` — it is *not* a file read. It's a cross-domain semantic query over accumulated context domains (ADR-151), returning ranked results with metadata filters. Different mental model, correctly distinguished from `SearchFiles`.
- `DiscoverAgents` — already descriptive.
- `UpdateContext` — the consolidated context-mutation verb from ADR-146. Name is correct.
- `ManageAgent`, `ManageTask`, `ManageDomains` — lifecycle verbs in a consistent `Manage*` pattern.
- `RuntimeDispatch` — the asset-render dispatch to the output gateway (ADR-118). Correctly named.
- `RepurposeOutput` — the ADR-148 repurpose verb. Correctly named.
- `Clarify`, `GetSystemState`, `WebSearch`, `list_integrations` — stable, descriptive.
- `platform_*` — already follows a working convention (ADR-050) and maps to a real dispatch path (`handle_platform_tool`).

### 5. Capability tags, not caller prefixes

Each primitive gets one or more capability tags in the matrix doc. Tags describe what the primitive *does* or *requires*, not who calls it. The tag set:

| Tag | Meaning |
|---|---|
| `entity-layer` | Resolves entities by typed ref. Dispatches through `parse_ref`/`resolve_ref`. |
| `file-layer` | Reads or writes paths in the virtual filesystem. Dispatches through `AgentWorkspace`/`KnowledgeBase`. |
| `semantic-query` | Ranked semantic search over accumulated context domains. |
| `context-mutation` | Writes to identity/brand/memory/agent/task/deliverable context stores. |
| `lifecycle` | Creates or mutates the lifecycle of an agent, task, or domain entity. |
| `user-channel` | Requires a live user channel to function (Clarify). |
| `user-authorized` | Mutates state under explicit user direction (EditEntity, RepurposeOutput). |
| `external` | Makes an external API call (WebSearch, platform_*). |
| `introspection` | Read-only system or workspace introspection (GetSystemState, list_integrations). |
| `asset-render` | Dispatches to the output gateway for binary/asset rendering (RuntimeDispatch). |
| `inter-agent` | Crosses agent boundaries (DiscoverAgents, ReadAgentFile). |

Tags are metadata on the matrix table. They do not appear in primitive names. They enable matrix-level queries ("which primitives need a user channel?" → grep `user-channel` in the matrix doc) without coupling naming to caller identity.

### 6. Scope clarification — matrix is the action vocabulary, not the perception channel

The matrix is TP's **action** vocabulary. It is not TP's entire input surface. TP also receives a precomputed **perception** channel via `working_memory.format_compact_index()` — `workspace_state` (identity/brand richness, task counts, budget, agent health), `active_tasks`, `context_domains`, `recent_uploads`, `system_summary`, and more — injected into every TP turn before tool dispatch. Zero LLM produced it, zero primitives fetched it.

This is deliberate per ADR-156 (single intelligence layer) and ADR-159 (filesystem-as-memory): meta-awareness is precomputed SQL, not LLM-driven tool rounds. There is **no `GetWorkspaceState` primitive and there will not be one**. If a state signal is missing from TP's perception, the fix is to extend `format_compact_index()`, not to add a primitive.

Consequence for this ADR: the matrix describes what TP can *do*, not everything TP can *see*. `primitives-matrix.md` includes a "Perception channel" section positioned before the Full Matrix table that documents the working-memory injection, a realistic meta-awareness loop (cold-start onboarding → 4 primitives across 5 turns), and the ADR-156/159 rationale for keeping perception out of the primitive layer.

### 7. Resulting surface (post-commits 2–4)

**Chat mode (13 tools, was 15):**

| # | Primitive | Substrate family | Tags |
|---|---|---|---|
| 1 | `LookupEntity` | entity | entity-layer |
| 2 | `ListEntities` | entity | entity-layer |
| 3 | `SearchEntities` | entity | entity-layer |
| 4 | `EditEntity` | entity | entity-layer, user-authorized |
| 5 | `GetSystemState` | introspection | introspection |
| 6 | `WebSearch` | external | external |
| 7 | `list_integrations` | introspection | introspection |
| 8 | `UpdateContext` | context | context-mutation |
| 9 | `ManageDomains` | lifecycle | lifecycle |
| 10 | `ManageAgent` | lifecycle | lifecycle |
| 11 | `ManageTask` | lifecycle | lifecycle |
| 12 | `RepurposeOutput` | action | user-authorized |
| 13 | `Clarify` | interaction | user-channel |

Changes vs current chat mode: `Execute` deleted, `CreateTask` folded into `ManageTask`. Net: 15 → 13.

**Headless mode (14 tools, was 16):**

| # | Primitive | Substrate family | Tags |
|---|---|---|---|
| 1 | `LookupEntity` | entity | entity-layer |
| 2 | `ListEntities` | entity | entity-layer |
| 3 | `SearchEntities` | entity | entity-layer |
| 4 | `GetSystemState` | introspection | introspection |
| 5 | `WebSearch` | external | external |
| 6 | `ReadFile` | file | file-layer |
| 7 | `WriteFile` | file | file-layer |
| 8 | `SearchFiles` | file | file-layer |
| 9 | `ListFiles` | file | file-layer |
| 10 | `QueryKnowledge` | file | semantic-query |
| 11 | `DiscoverAgents` | lifecycle | inter-agent |
| 12 | `ReadAgentFile` | file | file-layer, inter-agent |
| 13 | `ManageAgent` | lifecycle | lifecycle |
| 14 | `ManageTask` | lifecycle | lifecycle |
| 15 | `ManageDomains` | lifecycle | lifecycle |

*Note: entity-layer primitives added to headless because post-rename the distinction is explicit and headless agents can legitimately benefit from `LookupEntity(ref="document:uuid")` during research. Pending confirmation with test file contract — if test asserts entity verbs are chat-only, keep that boundary and this row drops to 14.*

**Deleted in this ADR:** `Execute`, `CreateTask` (folded).

Platform tools (`platform_*`) continue to be added dynamically per agent capability bundle via `get_headless_tools_for_agent()`. Unchanged.

---

## Why no caller-prefix convention (e.g., `TP*`)

Considered and rejected. Two reasons.

**Reason 1 — conflation of permission with identity.** The real distinction behind "this primitive is only in chat mode" isn't "TP calls it." It's "requires a user channel" OR "requires user-authorized judgment" OR "is a user-initiated action." `Clarify` is user-channel-bound. `UpdateContext(target="identity")` is user-authorized. `RepurposeOutput` is user-initiated. These are three different capability constraints. Prefixing all of them `TP*` would collapse the distinction into the caller identity and lose the information.

**Reason 2 — TP is an agent now (ADR-164).** Post-ADR-164, "TP" is just the agent with `role='thinking_partner'`. A `TP*` prefix would encode a caller identity into the tool name. If tomorrow we decide Slack Bot agents should be able to call `Clarify` (by prompting the user in Slack), the `TP*` name becomes a lie and triggers a rename cascade — the exact problem ADR-166 cleaned up when it dropped `category` (denormalized owner metadata).

The capability-tag approach gives the same discoverability benefit (grep `user-channel` in the matrix) without the identity lock.

**The one prefix that IS kept:** `platform_*`. That prefix maps to a real dispatch path (`handle_platform_tool`), a real permission model (capability-scoped, OAuth-backed), and a real runtime boundary (external API call). It's a technical grouping, not a caller-identity grouping. It stays.

---

## Consequences

### Positive

- **Single reference for primitives.** `primitives-matrix.md` is the first canonical primitive doc since ADR-146. New contributors read one file to understand the surface.
- **Naming matches substrate.** `LookupEntity` vs `ReadFile` tells you the mental model without requiring tribal knowledge.
- **ADR-146 finally complete.** Phase 3 (`Execute`) and Phase 5 (docs) close after six weeks of drift.
- **Symmetric lifecycle verbs.** `ManageAgent(create|…)` and `ManageTask(create|…)` have the same shape.
- **Capability tags unlock matrix queries.** "What needs a user?" / "What's user-authorized?" / "What's entity-layer?" — all answerable by grep on the matrix doc.
- **Rename protocol pinned in one place.** CLAUDE.md rule 7b grep list lives in the matrix doc so future primitive changes follow a standing ritual, not re-derived discipline.

### Negative

- **Commit 4 (the rename) is large.** ~10 primitive renames across backend prompts, frontend display components, test assertions, and 15+ doc files. Mitigated by grep enumeration before editing and by running the test suite after each commit.
- **TP prompt CHANGELOG entries will cluster.** Three behavioral changes in quick succession (Execute deletion, CreateTask fold, renames). Each gets its own entry for traceability.
- **Short-term dissonance for KVK's muscle memory.** `Read(ref=…)` → `LookupEntity(ref=…)` will feel unfamiliar for a session or two.

### Risks

- **Caller miss in Commit 2 (Execute).** Risk: a caller of `Execute` that isn't in the enumerated grep list breaks silently at runtime. Mitigation: after code deletion, the `Execute` handler returns `"unknown_primitive"` error (TP's existing error surface) rather than a silent no-op. Any surviving caller is loud.
- **Test file contract drift.** `api/test_recent_commits.py` asserts specific primitive presence/absence in each mode. Each commit updates the test assertions in the same commit. Running the test after every commit is the validation gate.
- **Frontend tool_name string comparisons.** `web/components/tp/InlineToolCall.tsx` and others compare tool names as strings. Commit 4's grep sweep covers frontend — mitigation is doing the sweep thoroughly, not hoping for compile-time safety.

---

## Implementation Plan

Five commits, each ending in a green state (backend boots, frontend builds, test file passes).

### Commit 1 — Docs foundation (this commit)

- Write `docs/adr/ADR-168-primitive-matrix.md` (this file).
- Write `docs/architecture/primitives-matrix.md` (sibling to `registry-matrix.md`).
- Update `docs/architecture/README.md` — add `primitives-matrix.md` to Canonical Docs table and Reading Order.
- Update `CLAUDE.md` — add ADR-168 entry after ADR-167; add `primitives-matrix.md` to File Locations.
- Add `api/prompts/CHANGELOG.md` entry `[2026.04.09.1]` — direction declared, no behavior change yet.

**No code changes.** The direction is canonical; subsequent commits execute it.

### Commit 2 — Dissolve `Execute`

- Grep-enumerate all callers of `Execute` and `EXECUTE_TOOL`.
- Migrate each caller to the replacement shape per Decision §2.
- Delete `api/services/primitives/execute.py`.
- Remove from `registry.py` imports, `HANDLERS`, `CHAT_PRIMITIVES`.
- Update `api/test_recent_commits.py` — remove `Execute`-related assertions, add assertions that `Execute` is not in `HANDLERS`.
- TP prompt sweep: `api/agents/thinking_partner.py`, `api/agents/tp_prompts/*.py` — remove `Execute(action=…)` examples.
- Doc sweep (rule 7b): `docs/architecture/`, `docs/design/`, `docs/features/`, `CLAUDE.md`.
- Update `primitives-matrix.md` "deleted primitives" ledger row.
- CHANGELOG entry `[2026.04.09.2]`.

### Commit 3 — Fold `CreateTask` into `ManageTask(action="create")`

- Move `handle_create_task` logic into `handle_manage_task` as the `"create"` action branch.
- Update `MANAGE_TASK_TOOL.input_schema.action.enum` to include `"create"` as the first value. Update the tool description with the new action.
- Delete `CREATE_TASK_TOOL` from `api/services/primitives/task.py`. Delete `handle_create_task`.
- Delete `api/services/primitives/task.py` entirely if empty after removals.
- `api/services/primitives/registry.py` — remove `CREATE_TASK_TOOL` import, `CreateTask` handler registration, and `CREATE_TASK_TOOL` from both registries.
- Caller migration: grep `CreateTask` across `api/agents/tp_prompts/`, `api/routes/chat.py`, `api/services/commands.py`, `api/services/agent_creation.py`, `web/contexts/TPContext.tsx`, `web/components/tp/InlineToolCall.tsx`. Each caller updated to `ManageTask(action="create", …)`.
- Update `api/test_recent_commits.py` — the assertion "Chat has CreateTask" becomes "Chat has ManageTask" + "ManageTask schema has create action".
- TP prompt updates: `CreateTask(...)` examples become `ManageTask(action="create", ...)` with field mapping preserved.
- Frontend: `InlineToolCall.tsx` drops `CreateTask` display branch — `ManageTask` display branch handles `create` action.
- Doc sweep.
- Update `primitives-matrix.md` lifecycle row and action enum for `ManageTask`.
- CHANGELOG entry `[2026.04.09.3]`.

### Commit 4 — Rename: `*Entity` and `*File` verb families

- Rename tool `name` fields in tool dicts across `api/services/primitives/read.py`, `list.py`, `search.py`, `edit.py`, `workspace.py`:
  - `Read` → `LookupEntity` (tool name, handler `handle_lookup_entity`, constant `LOOKUP_ENTITY_TOOL`)
  - `List` → `ListEntities` (handler `handle_list_entities`, constant `LIST_ENTITIES_TOOL`)
  - `Search` → `SearchEntities` (handler `handle_search_entities`, constant `SEARCH_ENTITIES_TOOL`)
  - `Edit` → `EditEntity` (handler `handle_edit_entity`, constant `EDIT_ENTITY_TOOL`)
  - `ReadWorkspace` → `ReadFile` (handler `handle_read_file`, constant `READ_FILE_TOOL`)
  - `WriteWorkspace` → `WriteFile` (handler `handle_write_file`, constant `WRITE_FILE_TOOL`)
  - `SearchWorkspace` → `SearchFiles` (handler `handle_search_files`, constant `SEARCH_FILES_TOOL`)
  - `ListWorkspace` → `ListFiles` (handler `handle_list_files`, constant `LIST_FILES_TOOL`)
  - `ReadAgentContext` → `ReadAgentFile` (handler `handle_read_agent_file`, constant `READ_AGENT_FILE_TOOL`)
- Module files kept in place (`read.py` still holds `LookupEntity` logic) to avoid unnecessary import churn — file renames can happen in a follow-up if the names become misleading.
- `registry.py` — update all imports, `HANDLERS` keys, `CHAT_PRIMITIVES`/`HEADLESS_PRIMITIVES` lists.
- Update every tool description to match: `LookupEntity` description starts with "Look up any entity by reference"; `ReadFile` description starts with "Read a file from your workspace"; etc. Cross-references within descriptions updated.
- **Critical backend sweep:**
  - `api/agents/thinking_partner.py`
  - `api/agents/tp_prompts/*.py` (onboarding, tools, behaviors, system)
  - `api/agents/chat_agent.py`
  - `api/services/agent_pipeline.py`
  - `api/services/task_pipeline.py`
  - `api/services/working_memory.py`
  - `api/services/workspace.py`
  - `api/services/task_types.py`
  - `api/services/commands.py`
  - `api/services/agent_creation.py`
  - `api/test_recent_commits.py`
- **Critical frontend sweep:**
  - `web/components/tp/InlineToolCall.tsx`
  - `web/lib/utils.ts`
  - `web/contexts/TPContext.tsx`
  - `web/components/tp/NotificationCard.tsx`
  - `web/components/workspace/WorkspaceNav.tsx`
  - `web/components/chat-surface/artifacts/*.tsx` (grep-enumerated)
- **Doc sweep:**
  - `docs/architecture/` — agent-framework, SERVICE-MODEL, agent-execution-model, TP-DESIGN-PRINCIPLES, workspace-conventions, output-substrate, registry-matrix, primitives-matrix
  - `docs/features/` — context, agent-playbook-framework, sessions, memory, task-types
  - `docs/design/` — SURFACE-PRIMITIVES-MAP explicitly, + grep the rest
  - `docs/adr/` — ADRs are immutable history; add a one-line "renamed by ADR-168" link in ADR-146's status line only; do not rewrite prior ADR prose
  - `CLAUDE.md`
- **Behavioral changelog**: large entry `[2026.04.09.4]` listing every renamed primitive and expected TP behavior (no semantic change — same tools, new names).
- Update `primitives-matrix.md` with final names and mark ADR-168 status `Implemented` in a follow-up commit.

### Commit 5 — Mark ADR-168 Implemented, final verification

- Update ADR-168 status header: `Proposed` → `Implemented`.
- Update `primitives-matrix.md` status header with implementation date.
- Update CLAUDE.md ADR-168 entry to reflect shipped state.
- **Final grep sweep** for old names across all paths — must return zero matches in live code (ADRs and archived docs excluded). Any surviving match is fixed in the same commit.
- Run `api/test_recent_commits.py` — must pass.
- Run `cd web && pnpm build` — must pass.
- Backend boot smoke test (`uvicorn main:app --reload`, curl `/health`) — must pass.
- CHANGELOG entry `[2026.04.09.5]` marking implementation complete.

---

## Testing & Validation

After each code-touching commit (2, 3, 4):

1. **`api/test_recent_commits.py`** — the registry contract test. Updated in the same commit, run as a gate.
2. **Backend boot smoke** — `cd api && uvicorn main:app --reload --port 8000` then `curl localhost:8000/health`. Catches import breakage.
3. **Frontend build** — `cd web && pnpm build`. Catches TypeScript breakage from tool-name string renames.
4. **Grep gate** — for Commit 2: no live-code reference to `Execute` primitive. For Commit 3: no live-code reference to `CreateTask` primitive. For Commit 4: no live-code reference to any old name (Read, List, Search, Edit, ReadWorkspace, WriteWorkspace, SearchWorkspace, ListWorkspace, ReadAgentContext) except as string literals in rename logic or ADR history.

Post-Commit 5: **live TP smoke test.** Open chat, trigger a conversation that exercises the renamed tools (context inference → UpdateContext → ManageTask create → LookupEntity on the new task → ListFiles on the task folder). Manual validation by KVK before next session.

---

## Schema Changes

**None.** All changes are in the Python primitive layer, tool definitions, prompts, and documentation. No database tables, columns, or migrations touched. No Render service env vars touched.

---

## Alternatives Considered

### A: Keep current names, just write the matrix doc

The minimal doc-only path. Rejected because the `Read`/`ReadWorkspace` naming confusion is a standing source of friction that the doc alone cannot fix. Every new prompt, every new contributor, every return to the code after a break re-hits the same question: "wait, which `Read` does what?" The doc would describe the confusion, not resolve it.

### B: Caller-identity prefixes (`TP*`)

Considered and rejected — see "Why no caller-prefix convention" section above.

### C: Merge entity layer and file layer into one verb

Would be `Read(ref_or_path=…)` with the primitive introspecting whether the argument is a ref string or a path. Rejected because:
- Ambiguity at the tool-use site. The LLM has to think about which kind of argument to pass, and TP prompts become harder to write ("when to use ref form vs path form").
- The two substrates have genuinely different permission models (ref-based resolves through RLS; path-based resolves through agent_slug scoping). Merging invites permission bugs.
- Hides the dispatch path, which is load-bearing for debugging.

### D: Delete the entity layer primitives entirely

Considered because headless agents don't use them. Rejected because TP genuinely needs them — `LookupEntity(ref="document:uuid")`, `SearchEntities(scope="document", query=…)`, `EditEntity(ref="task:uuid", fields=…)` are all active paths in chat mode and have no file-layer equivalent for database-backed entities like sessions, documents, and platform connections.

### E: Rename `QueryKnowledge` to `SemanticSearch` or `SearchContext`

Considered for consistency with the `*Files`/`*Entities` naming. Rejected because `QueryKnowledge` names the *output* (knowledge) not the operation, which is intentional — it distinguishes a semantic ranked query from a filesystem search. `SearchContext` would collide with `UpdateContext` semantically. `SemanticSearch` is accurate but loses the "accumulated knowledge domains" framing that ADR-151 established. Keep.

---

## References

- ADR-146: Primitive Hardening (extended by this ADR; Phase 3 and Phase 5 completed here)
- ADR-154: Execution Boundary Reform (Who/What/How file separation — the substrate language this ADR adopts)
- ADR-080: Unified Agent Modes (chat/headless mode split — preserved here)
- ADR-151: Shared Context Domains (`QueryKnowledge` semantics)
- ADR-166: Registry Coherence Pass (precedent for two-axis registry cleanup; this ADR applies the same discipline to primitives)
- ADR-164: Back Office Tasks — TP as Agent (reason `TP*` prefix is rejected)
- `docs/architecture/primitives-matrix.md` — the canonical matrix shipped by Commit 1
- `docs/architecture/registry-matrix.md` — sibling reference for task/agent/domain registries
