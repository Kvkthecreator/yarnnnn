# ADR-235: UpdateContext Dissolution + ManageRecurrence + ManageAgent.create Sunset

> **Status**: **Proposed** (2026-04-29). Single-commit landing per Singular Implementation discipline; sized to be substantial.
> **Date**: 2026-04-29
> **Authors**: KVK, Claude
> **Dimensional classification**: **Mechanism** (Axiom 5) primary, **Substrate** (Axiom 1) + **Identity** (Axiom 2) secondary — restructures the cognitive vocabulary by which all chat-surface mutations reach substrate.
> **Extends**: ADR-168 (Primitive Matrix), ADR-186 (Prompt Profiles), ADR-209 (Authored Substrate as the substrate-write substrate), ADR-216 (orchestration-vs-judgment vocabulary), ADR-231 (recurrence-walker, natural-home substrate).
> **Amends**: ADR-146 (Primitive Hardening) — the unification rationale ("`UpdateContext` is one verb for all context mutations") is honored at the substrate level by ADR-209's `write_revision()`, not at the primitive-name level. ADR-146's primitive consolidation reasoning is preserved; the verb itself dissolves because its targets are heterogeneous.
> **Supersedes**: ADR-138's `ManageAgent` create-action assumption — custom-agent scaffolding leaves the chat primitive surface entirely.
> **Preserves**: FOUNDATIONS axioms 1-9, ADR-141 (execution layers unchanged), ADR-156 (single intelligence layer — YARNNN remains the sole judgment runtime in chat), ADR-159 (filesystem-as-memory), ADR-176 (universal specialist roster — unchanged, the 9-agent roster doesn't depend on user-creation), ADR-194 v2 (Reviewer substrate unchanged), ADR-209 (every write still attributed + retained), ADR-216 (Reviewer + YARNNN identity layer unchanged).

---

## Context

### What `UpdateContext` is today

A single primitive with **eleven targets** that absorbed prior consolidations + post-ADR-231 lifecycle work:

| Target | What it does | Cognitive shape |
|---|---|---|
| `workspace` | Run combined first-act inference (identity + brand + entity + work_intent in one Sonnet call), write IDENTITY.md + BRAND.md, scaffold domains | **Inference-merged write** |
| `identity` | Run inference merge against operator text + uploaded docs + URLs, write IDENTITY.md, run gap detection | **Inference-merged write** |
| `brand` | Same as identity, BRAND.md target | **Inference-merged write** |
| `mandate` | Direct write to `/workspace/context/_shared/MANDATE.md` | **Substrate write** |
| `autonomy` | Direct write to `/workspace/context/_shared/AUTONOMY.md` | **Substrate write** |
| `precedent` | Direct write to `/workspace/context/_shared/PRECEDENT.md` | **Substrate write** |
| `memory` | Append-with-dedup to `/workspace/memory/notes.md` + entry-type inference + activity log | **Substrate append-with-dedup** |
| `awareness` | Direct overwrite of `/workspace/memory/awareness.md` (truncated to 2000 chars) | **Substrate write** |
| `agent` | Append formatted feedback entry to `/agents/{slug}/memory/feedback.md` + activity log | **Substrate append** |
| `task` | Append formatted feedback entry to `/workspace/{natural-home}/{slug}/feedback.md`; 4 sub-targets (`deliverable` default, `criteria`, `objective`, `output_spec`, `run_log`) for sub-routing | **Substrate append** |
| `recurrence` | Five lifecycle actions over a YAML declaration at natural-home substrate (create/update/pause/resume/archive) | **Lifecycle action** |

Three categorically different cognitive shapes hidden under one verb name. The verb's name claims "context mutation"; in practice it is the chat surface's grab-bag for *anything that mutates and isn't a specific entity-layer or file-layer call*.

### Why this broke the framing

The original ADR-146 framing ("`UpdateContext` consolidates 4 context-write verbs into one") was correct for those 4 targets. It became incorrect when:

1. **ADR-209 (Authored Substrate)** unified the substrate-level write path. Every `workspace_files` mutation now routes through `write_revision()` regardless of primitive — attribution, content-addressing, revision chains all happen automatically. The per-target post-processing (dedup, append formatting, gap detection) is implementation detail that the primitive's name was meant to hide. After ADR-209, the consolidation rationale (one verb for all writes) is **achieved at the substrate level**, not at the primitive level.

2. **ADR-231 (Task Abstraction Sunset)** added the `recurrence` target as a lifecycle wrapper. This is `ManageTask` reborn under a different verb. The original `ManageTask` was deleted because tasks dissolved; recurrences are the new lifecycle-managed entity, and they got jammed into `UpdateContext` because there was no other place for them. The verb's name stopped reading accurately — *"create a recurring report"* is not an "update context" operation in any honest sense.

3. **Benchmark exposure.** Claude Code has no `UpdateContext` verb. Memory writes happen through `Edit MEMORY.md`. Identity / preferences / project facts happen through `Edit` against the appropriate file. The conversational agent has direct file vocabulary. Cowork is the same — folder-as-context puts substrate writes in normal write operations.

### The user redirect (2026-04-29)

Mid-audit: *"i'll likely to explicitly remove any primitive (i only remember one) but related to agent scaffolding. for now, no possibility of creating custom agents."*

This folds in. `ManageAgent(action="create")` is the only chat-surface primitive that creates user-authored Agents. Per ADR-216 the systemic Agents (Reviewer, YARNNN) are scaffolded at signup; per ADR-176 the production-role + platform-bot bundles are universal-specialist orchestration capabilities, not user-created. Removing chat's ability to create new Agents collapses the surface to the post-ADR-216 reality: the only Agents in a workspace are the systemic ones plus whatever the kernel scaffolds; users don't author Agents through chat.

---

## Decision

Three structural changes, all landing in one commit:

### D1 — `UpdateContext` dissolves entirely

The verb is **deleted**. Its eleven targets sort into three honest destinations:

#### D1.a — Inference-merged writes become explicit `Infer*` primitives

`identity`, `brand`, `workspace` targets become **two new primitives**:

- **`InferContext(target='identity'|'brand', text, document_ids?, url_contents?)`** — runs `infer_shared_context()`, writes the target file, runs gap detection, returns gap report. **This is the cognitive job, named honestly.** The LLM is calling an inference operation, not a file write. The inference call is YARNNN-internal (Sonnet); the result goes to substrate.
- **`InferWorkspace(text, document_ids?, url_contents?)`** — runs `infer_first_act()`, writes IDENTITY.md + BRAND.md, scaffolds domains, returns structured scaffold report with `work_intent_proposal`. The first-act path. Mirrors the existing handler shape, separated from the consolidated verb.

These primitives are **chat-only** (they require operator text + the LLM-side inference path that lives in chat dispatch). The inference helpers (`infer_shared_context`, `infer_first_act`) and the gap-detection helper are unchanged — the dissolution is a *primitive-shape change*, not an inference-logic change.

#### D1.b — Direct substrate writes use `WriteFile` (chat now reaches it per ADR-234)

Six targets become direct `WriteFile` calls with prompt guidance pointing at the canonical paths:

- `mandate` → `WriteFile(path='/workspace/context/_shared/MANDATE.md', content=..., authored_by='operator')`
- `autonomy` → `WriteFile(path='/workspace/context/_shared/AUTONOMY.md', ...)`
- `precedent` → `WriteFile(path='/workspace/context/_shared/PRECEDENT.md', ...)`
- `awareness` → `WriteFile(path='/workspace/memory/awareness.md', ..., authored_by='yarnnn:chat')`
- `agent` (feedback) → `WriteFile(path='/agents/{slug}/memory/feedback.md', append=True, ...)`
- `task` (feedback) → `WriteFile(path='/workspace/{natural-home-resolved-from-decl}/{slug}/feedback.md', append=True, ...)`

**Append semantics + dedup move into a thin helper, not a primitive.** The existing target-specific post-processing (`_handle_memory`'s entry-type inference, `_handle_agent_feedback`'s "## Feedback (date, source)" header pattern, `_handle_task_feedback`'s natural-home path resolution) is preserved as a small set of formatter helpers in `services/feedback_formatters.py` (new file). Chat's prompt guidance tells YARNNN: *"to append feedback to an agent, use `WriteFile` against the agent's `memory/feedback.md` with the formatter helper from the chat-side append flow."* The formatter logic stays — only its primitive entry point changes.

The `memory` target's dedup logic is the most complex piece. Two options:

- **Option A**: keep dedup as a thin server-side check inside `WriteFile` when the path is `/workspace/memory/notes.md` and `append=True`. Cost: a path-coupled special-case in `WriteFile`. Reject — that's the same problem `UpdateContext` had.
- **Option B**: dedup happens in the formatter helper before `WriteFile` is called. The chat prompt invokes the formatter (`format_memory_entry()` returns either `(content, append=True)` or `None` if duplicate); YARNNN then makes the `WriteFile` call only on non-duplicates. Accept — moves the cognitive work to where it belongs (between LLM and primitive), keeps the primitive clean.

**Activity log writes** (currently inside `_handle_memory`, `_handle_agent_feedback`) move into `WriteFile` itself, gated on a path-prefix recognition (memory/feedback paths emit `memory_written` / `agent_feedback` events). This is the *one* legitimate path-coupling: activity-log emission is fully orthogonal to primitive identity and naturally co-located with the write operation that triggered it.

#### D1.c — Lifecycle action becomes `ManageRecurrence`

The `recurrence` target spins out into a new lifecycle primitive mirroring `ManageAgent` and `ManageDomains`:

```
ManageRecurrence(
    action='create' | 'update' | 'pause' | 'resume' | 'archive',
    shape='deliverable' | 'accumulation' | 'action' | 'maintenance',
    slug=...,
    domain=...?,        # required for shape='accumulation'
    declaration=...?,   # required for action='create'
    changes=...?,       # required for action='update'
)
```

The implementation extracts cleanly: `_handle_recurrence` + `_resolve_recurrence_path` + `_handle_recurrence_single` + `_handle_recurrence_multi` move from `update_context.py` into a new `manage_recurrence.py`. **Chat + headless availability** (mirrors ADR-231 D5's intent — recurrences are managed both from operator chat and from agent dispatch). Headless can `pause`/`resume` its own declarations on outcome signals, etc.

### D2 — `ManageAgent.create` deletes from the chat surface

Per the user's redirect: *"no possibility of creating custom agents."*

- `ManageAgent` retains **4 actions**: `update`, `pause`, `resume`, `archive` (lifecycle management of existing agents — Reviewer, YARNNN, the systemic 9, and any pre-existing user-authored agents in production data).
- The `create` action is **removed from the action enum**. The handler `_handle_create` and its caller chain (`agent_creation.create_agent_record`) is preserved as service code (the data path is fine; the surface is gone).
- Chat prompts that walked operators through agent creation are rewritten to direct operators toward configuring tasks against the systemic roster instead.
- `agent_creation.create_agent_record` is **kept** for the kernel/signup path (`workspace_init.initialize_workspace` still scaffolds YARNNN at signup). It just stops being reachable from a chat-surface primitive.

This honors Singular Implementation: there is no longer a "create custom agent via chat" pathway. If users need custom Agents in the future, a new ADR introduces a new surface. There is no parallel "deprecated but works" creation path.

### D3 — `DiscoverAgents` (orthogonal, scoped check)

The audit prompt asked about agent-scaffolding primitives. `DiscoverAgents` is *not* a scaffolding primitive — it's an inter-agent discovery read (per ADR-116 Phase 2, headless-only). It reads existing agents by role/scope/status. **Stays.** Discovery is read-only and inter-agent coordination remains a real headless need (e.g., a production-role agent looking up which platform-bot bundles are active in this workspace).

---

## Resulting primitive surface

### Chat surface (post-ADR-234 + ADR-235)

| Family | Primitives |
|---|---|
| Entity | `LookupEntity`, `ListEntities`, `SearchEntities`, `EditEntity` |
| File (per ADR-234) | `ReadFile`, `WriteFile`, `SearchFiles`, `ListFiles` |
| Inference (NEW per ADR-235 D1.a) | `InferContext`, `InferWorkspace` |
| Lifecycle (per ADR-235 D1.c + D2) | `ManageAgent` (4 actions: update/pause/resume/archive), `ManageDomains`, `ManageRecurrence` (5 actions) |
| Action | `RepurposeOutput`, `RuntimeDispatch` |
| Approval loop (ADR-193) | `ProposeAction`, `ExecuteProposal`, `RejectProposal` |
| Authored Substrate reads (ADR-209 P3) | `ListRevisions`, `ReadRevision`, `DiffRevisions` |
| Lifecycle dispatch (ADR-231 D5) | `FireInvocation` |
| Interaction | `Clarify` |
| External | `WebSearch` |
| Introspection | `GetSystemState`, `list_integrations` |

**Count: 23 primitives** (was 20 before audit; gains 4 file-family primitives per ADR-234 + 2 inference primitives per ADR-235 D1.a; loses 1 verb name `UpdateContext` whose targets dispersed across the new surface; loses 1 action from `ManageAgent` per D2).

### Headless surface (ADR-235 D1.c only — file family already present)

| Family | Primitives |
|---|---|
| Entity | `LookupEntity`, `ListEntities`, `SearchEntities` (no `EditEntity` — chat-only by ADR-168) |
| File | `ReadFile`, `WriteFile`, `SearchFiles`, `ListFiles`, `QueryKnowledge`, `ReadAgentFile` |
| Lifecycle | `ManageAgent` (4 actions), `ManageDomains`, `ManageRecurrence` (5 actions) |
| Inter-agent | `DiscoverAgents` |
| Lifecycle dispatch | `FireInvocation` |
| Action | `RuntimeDispatch` |
| Approval loop | `ProposeAction` |
| Authored Substrate reads | `ListRevisions`, `ReadRevision`, `DiffRevisions` |
| External | `WebSearch`, `platform_*` (dynamic) |
| Introspection | `GetSystemState` |

**Count: 20 static + `platform_*` dynamic** (gains `ManageRecurrence`; loses none — headless never had `UpdateContext`).

### MCP surface (ADR-169 — affected by D1)

The MCP `remember_this` tool currently dispatches through `UpdateContext` with the two-branch classifier. **Post-ADR-235 it dispatches through `WriteFile` for substrate-write targets (memory, awareness, mandate, etc.) + `InferContext` for identity/brand inference + `ManageRecurrence` if recurrence-write becomes MCP-eligible (it does NOT in this ADR — see "What this does NOT do").**

The two-branch classifier (`classify_memory_target`) preserves its routing intent but its outputs change:

- workspace-level safe default: `("memory", WriteFile path='/workspace/memory/notes.md', append=True)`
- operational-feedback target: `("agent" | "task", WriteFile path=...) ` with feedback-formatter pre-processing

`mcp_composition.py` is rewritten — same classifier logic, different dispatch.

---

## Implementation

### Files created

- `api/services/primitives/infer_context.py` — `INFER_CONTEXT_TOOL` + `handle_infer_context` (extracted from `_handle_shared_context`).
- `api/services/primitives/infer_workspace.py` — `INFER_WORKSPACE_TOOL` + `handle_infer_workspace` (extracted from `_handle_workspace_scaffold`).
- `api/services/primitives/manage_recurrence.py` — `MANAGE_RECURRENCE_TOOL` + `handle_manage_recurrence` + extracted helpers (`_resolve_recurrence_path`, `_handle_recurrence_single`, `_handle_recurrence_multi`).
- `api/services/feedback_formatters.py` — `format_memory_entry()`, `format_agent_feedback_entry()`, `format_task_feedback_entry()`. Pure-Python formatters that the chat prompt calls before `WriteFile`. Returns `(content, append: bool, path)` tuples or `None` on dedup hit.
- `api/test_adr235_update_context_dissolution.py` — comprehensive test gate (see "Test gate" below).

### Files modified

- `api/services/primitives/registry.py` — remove `UpdateContext` import + entry; add `InferContext`, `InferWorkspace`, `ManageRecurrence` imports + entries; restrict `ManageAgent` action enum surface.
- `api/services/primitives/coordinator.py` — `MANAGE_AGENT_TOOL.input_schema.properties.action.enum` removes `"create"`. The `_handle_create` handler stays callable (signup path uses it via `agent_creation.create_agent_record`); only the LLM-facing tool definition shrinks.
- `api/services/primitives/workspace.py` (`WriteFile` handler) — gain activity-log emission gated on path-prefix recognition (`memory_written` event for `/workspace/memory/notes.md`, `agent_feedback` event for `/agents/*/memory/feedback.md`, etc.).
- `api/services/mcp_composition.py` — rewrite `remember_this` dispatch: target classification → `WriteFile` (substrate writes) or `InferContext` (identity/brand inference). Two-branch classifier intent unchanged; dispatch path different.
- `api/mcp_server/server.py` — update `remember_this` tool body to call new dispatch.
- `api/agents/prompts/chat/{tools_core,workspace,entity,onboarding,behaviors,activation,task_scope}.py` — rewrite every `UpdateContext` reference. Replace with new verb appropriate to the cognitive job. Remove every `ManageAgent(action="create"...)` example. Add the file-family + inference + recurrence vocabulary.
- `api/agents/prompts/base.py` + `platforms.py` — minor reference updates (these had ~4 `UpdateContext` mentions combined).
- `api/services/commands.py` — remove the line `Create: ManageAgent(action="create"...)`.
- `api/services/context_inference.py` — unchanged in logic, but its callsites move to `infer_context.py` / `infer_workspace.py`.
- `api/services/feedback_distillation.py`, `api/services/task_deliverable_inference.py` — adjust call shapes if they use `UpdateContext` directly (audit: distillation has 1 hit, task-deliverable-inference has 4 hits — both internal callers, swap to direct `WriteFile` + formatter).
- `api/services/working_memory.py` — comment-only updates.
- `api/services/invocation_dispatcher.py` — no behavioral change; possible reference updates.
- `api/services/scheduling.py`, `api/services/trigger_dispatch.py`, `api/services/orchestration.py`, `api/jobs/unified_scheduler.py` — references audit (most are comment-level; any code-level dispatches to `UpdateContext(target='recurrence')` rewrite to `ManageRecurrence(...)` directly).
- `api/services/primitives/refs.py`, `api/services/primitives/edit.py`, `api/services/primitives/write.py`, `api/services/primitives/fire_invocation.py`, `api/services/primitives/__init__.py` — internal cross-references.
- `api/routes/chat.py`, `api/routes/agents.py`, `api/routes/memory.py`, `api/routes/recurrences.py` — any direct `UpdateContext` invocations move to the new primitives.
- `api/test_adr143_methodology_feedback.py`, `api/test_adr169_mcp_context_hub.py`, `api/test_adr209_phase4.py`, `api/test_adr231_recurrence.py`, `api/test_recent_commits.py` — fix or delete stale `UpdateContext` references. Many of these tests are already broken-by-ADR-231 (import dead modules); confirm at migration time which are live.
- `api/prompts/CHANGELOG.md` — `[2026.04.29.N]` entry covering D1 + D2 + D3.

### Files deleted

- `api/services/primitives/update_context.py` — **the entire 1,261-line file goes**. Its handlers are extracted (4 destinations: `infer_context.py`, `infer_workspace.py`, `manage_recurrence.py`, formatters that drive `WriteFile`); the verb name and its dispatch shell are gone. Singular Implementation: no shim, no parallel verb, no deprecation period.

### Documentation modified

- `docs/architecture/primitives-matrix.md` — full rewrite of:
  - Verb rows (delete `UpdateContext` row; add `InferContext`, `InferWorkspace`, `ManageRecurrence` rows).
  - `ManageAgent.action` enum table (drop `create`).
  - `UpdateContext.target` enum table (deleted entirely).
  - Mode totals (chat ~23, headless ~20 + dynamic).
  - "Hard boundaries" section (chat now has `ReadFile`/`WriteFile`/etc. per ADR-234; the no-`UpdateContext` boundary).
  - Realistic meta-awareness loop example (the cold-start onboarding example uses `InferWorkspace` instead of `UpdateContext(target='workspace')`).
- `docs/design/SURFACE-CONTRACTS.md` — references to `UpdateContext` rewritten.
- `CLAUDE.md` — File Locations table, primitive references in current-canon section.
- ADRs that referenced `UpdateContext` as an example or rationale (ADR-146, 149, 151, 155, 156, 162, 165, 169, 181, 184, 186, 196, 198, 205, 206, 207, 215, 217, 219, 220, 226, 231) — historical ADR summaries are preserved verbatim per the project discipline note in CLAUDE.md; only **active canon docs** (the matrix, SURFACE-CONTRACTS, CLAUDE.md current-canon section) are rewritten. The ADR amendment chain is captured by ADR-235's "Amends" header.

### Test gate

`api/test_adr235_update_context_dissolution.py` covers:

**D1 — UpdateContext dissolution (10 assertions):**
1. `UpdateContext` is **not** in `CHAT_PRIMITIVES`.
2. `UpdateContext` is **not** in `HANDLERS`.
3. `update_context.py` does not exist on disk.
4. `InferContext` is in `CHAT_PRIMITIVES` and dispatches to identity/brand inference path.
5. `InferWorkspace` is in `CHAT_PRIMITIVES` and dispatches to first-act inference path.
6. `ManageRecurrence` is in both `CHAT_PRIMITIVES` and `HEADLESS_PRIMITIVES`.
7. `ManageRecurrence` action enum has exactly 5 values: `create`, `update`, `pause`, `resume`, `archive`.
8. `WriteFile` chat path successfully writes a memory entry (round-trip test against a stub workspace).
9. Activity log emission triggers on `WriteFile` to `/workspace/memory/notes.md` (path-recognition gate works).
10. `mcp_composition.classify_memory_target` returns dispatch shapes that point at the new primitives, not `UpdateContext`.

**D2 — ManageAgent.create sunset (4 assertions):**
11. `MANAGE_AGENT_TOOL.input_schema.properties.action.enum` is exactly `["update", "pause", "resume", "archive"]` (no `create`).
12. `agent_creation.create_agent_record` still callable from `workspace_init` (signup path preserved).
13. No active prompt file (`prompts/chat/*.py`) contains `ManageAgent(action="create"`.
14. `services/commands.py` does not contain `ManageAgent(action="create"`.

**D3 — Singular Implementation grep gates (3 assertions):**
15. `grep -r "UpdateContext\|UPDATE_CONTEXT_TOOL\|update_context" api/` returns zero hits in live code (allowed in tests + CHANGELOG only).
16. `grep -r "UpdateContext" docs/architecture/ docs/design/ CLAUDE.md` returns zero active-canon hits (allowed in archived ADRs + ADR-235 itself + amended ADRs' historical text).
17. ADR-231 invariants gate still passes (regression).

**Combined gate target: 17/17 passing.**

### Render parity

| Service | UpdateContext today | Post-ADR-235 |
|---|---|---|
| API (yarnnn-api) | Imports + dispatches | `WriteFile`/`InferContext`/`InferWorkspace`/`ManageRecurrence` instead. No env changes. |
| Unified Scheduler | Headless never had UpdateContext (it was chat-only) | `ManageRecurrence` available headless; otherwise unchanged. No env changes. |
| MCP Server | `remember_this` dispatches via UpdateContext | Rewritten dispatch through new primitives. **No env changes.** Same auth surface. |
| Output Gateway | Untouched | Untouched |

**No env-var changes. No schema changes. No new services.**

---

## Risks

**R1 — Migration cost.** This commit touches ~30 files in a single landing. Mitigation: the test gate is the contract — if 17/17 passes and ADR-231 invariants stay green and Phase 1 + Phase 2 of ADR-233 stay green, the migration is verifiably correct. The mass of changes is concentrated in two patterns: (a) registry/handler edits, (b) prompt-file rewrites. Both are mechanical once the new primitives are authored.

**R2 — Prompt re-tuning needed.** Six prompt files (`tools_core`, `workspace`, `entity`, `onboarding`, `behaviors`, `activation`) need rewriting to teach YARNNN the new vocabulary. The first few sessions post-ship will reveal where the prompt guidance needs sharpening. Mitigation: keep the prompt rewrites tight to *vocabulary swap* + *cognitive-job framing* — don't simultaneously rewrite the larger guidance. If post-ship sessions reveal LLM confusion, that's a follow-on prompt commit, not an ADR amendment.

**R3 — `WriteFile` activity-log path-coupling.** The decision to gate activity-log emission on path-prefix recognition inside `WriteFile` is the one ADR-235 architectural compromise. It's the cleanest way to preserve the existing `memory_written` / `agent_feedback` events without bloating the primitive's input schema. Mitigation: the path-prefix logic is a small `_emit_activity_for_path()` helper called from `WriteFile`'s success branch; it has its own test (#9 above); if the coupling proves uncomfortable, a follow-on ADR can add an explicit `emit_activity` parameter to `WriteFile` and let the chat formatter pass it through.

**R4 — Custom agents become uncreatable.** Per the user's explicit redirect, this is intentional — but if alpha pressure surfaces a need for user-authored agents before a future ADR introduces a new surface, there is no chat-surface workaround. Mitigation: the data path (`agent_creation.create_agent_record`) is preserved; a future surface can re-introduce creation through a different mechanism (modal, new primitive, etc.). The current decision is *no chat surface for agent creation* — strongest singular-implementation form.

**R5 — Inference primitive naming.** `InferContext` + `InferWorkspace` are new verbs. They're cleanest to name what they do (LLM inference operations whose output is a substrate write) but introduce a new verb prefix to YARNNN's vocabulary. Mitigation: the two primitives are documentation-light (their handlers are well-tested existing inference paths; the new naming surfaces the cognitive job); the matrix doc rewrites their rows clearly.

---

## What this does NOT do

- **Does not remove `UpdateContext` from MCP composition's call surface immediately.** The MCP rewrite happens *in the same commit*; there is no ADR-235 phase where MCP still calls `UpdateContext` while chat doesn't. Singular Implementation.
- **Does not introduce file-family primitives to MCP.** ADR-169 keeps MCP intent-shaped (`work_on_this`, `pull_context`, `remember_this`); foreign LLMs don't get raw `WriteFile`. `remember_this` writes through `WriteFile` *server-side*; the MCP surface stays three intent verbs.
- **Does not change the systemic agent roster.** The 9 systemic Agents (per ADR-176 universal specialist + Reviewer + YARNNN per ADR-216) are unchanged. ADR-235 D2 only removes the *chat surface* for creating *additional* user-authored Agents.
- **Does not touch headless behavioral guidance for substrate writes.** Headless agents already use `WriteFile`; the only headless change is `ManageRecurrence` availability.
- **Does not address `EditEntity` chat-only-ness.** The entity layer's narrowness post-ADR-196 is correct (no semantic content there). `EditEntity` stays chat-only.
- **Does not phase the dissolution.** Singular Implementation: one commit, 17/17 test gate, atomic. If verification reveals a regression, revert via git history.

---

## Phasing

Single commit, sized large but bounded. The pieces are interdependent enough that a multi-phase rollout would create a parallel-implementation period that the project discipline forbids.

1. Author new primitives: `infer_context.py`, `infer_workspace.py`, `manage_recurrence.py`, `feedback_formatters.py`.
2. Update `registry.py`: drop `UpdateContext`, add the three new primitives, restrict `ManageAgent` action enum.
3. Update `WriteFile` handler with path-prefix activity-log emission.
4. Rewrite chat prompt files (vocabulary swap + cognitive-job framing).
5. Rewrite `mcp_composition.py` + `mcp_server/server.py` `remember_this` dispatch.
6. Update internal-caller services (`feedback_distillation.py`, `task_deliverable_inference.py`, `commands.py`, etc.).
7. **Delete** `update_context.py`.
8. Update active-canon docs (matrix, SURFACE-CONTRACTS, CLAUDE.md current-canon section).
9. Author `test_adr235_update_context_dissolution.py`.
10. Add `[2026.04.29.N]` CHANGELOG entry.
11. Run all gates: ADR-235 (17/17), ADR-234 ([n]/[n] expected), ADR-233 Phase 2 (12/12), ADR-233 Phase 1 (13/13), ADR-231 invariants (11/11). Combined target ~70+/70+ passing.
12. Atomic commit + push.

---

## Closing

ADR-235 is the substantive piece of the audit. ADR-234 was the observation ("chat lacks file reach"); ADR-235 is the *consequence* — once chat has file reach, the `UpdateContext` verb's reason for existing collapses. What's left is two genuinely distinct cognitive jobs (inference-merged writes; lifecycle action) wearing one verb's name. Splitting them honors what they are.

The benchmarks pointed exactly here: Claude Code's surface has zero "context mutation" verb because context-as-files makes one unnecessary; lifecycle in Claude Code is implicit (TodoWrite, subagents) because there are no persistent named entities to manage. YARNNN diverges legitimately on lifecycle (we have persistent Agents and Recurrences across sessions), so we keep the `Manage*` family — but we keep it *named accurately*, not hidden inside a context-mutation verb.

The user's redirect (no custom agent creation) sharpens this further: the only `Manage*` verbs that *create* are `ManageDomains.scaffold` (entities inside a domain) and `ManageRecurrence.create` (a YAML declaration). `ManageAgent` becomes lifecycle-only. The roster is fixed; substrate accumulates; recurrences govern when work fires. The vocabulary now reads back the architecture.
