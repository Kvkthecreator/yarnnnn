# ADR-234: Chat File Layer Reach — Read/Write/Search/List on workspace_files

> **Status**: **Implemented** (2026-04-29). Single-commit landing. Test gate 8/8 passing; combined gate (ADR-234 + ADR-233 P1 + P2 + ADR-231 invariants) 44/44 passing. CHANGELOG entry pending — worktree-side agent has been actively editing `api/prompts/CHANGELOG.md` on the same day; entry will land in a follow-on commit or roll into ADR-235's CHANGELOG addition.
> **Date**: 2026-04-29
> **Authors**: KVK, Claude
> **Dimensional classification**: **Mechanism** (Axiom 5) primary, **Identity** (Axiom 2) secondary — promotes the chat caller into the file substrate family it was previously gated out of.
> **Extends**: ADR-168 (Primitive Matrix), ADR-186 (Prompt Profiles), ADR-209 (Authored Substrate read primitives in chat).
> **Amends**: ADR-168 §"Hard boundaries" — the rule "Chat does NOT have agent-scoped file-layer write/search primitives" is reversed for workspace-absolute reads/writes. The exception ADR-209 Phase 3 already cut for revision-aware reads is generalized to the file family.
> **Preserves**: FOUNDATIONS axioms, ADR-141 (execution layers unchanged), ADR-156 (single intelligence layer), ADR-159 (filesystem-as-memory), ADR-216 (orchestration-vs-judgment vocabulary).

---

## Context

Pre-ADR-231 the chat surface had no agent-scoped file-layer primitives by deliberate design. The matrix asserted: *"YARNNN operates on task/agent paths through `EditEntity` on typed refs, not through agent-scoped file I/O."* That worked while typed refs (`task:uuid`, `document:uuid`) covered substrate reads — chat never needed to look at a path.

ADR-231 dissolved the task abstraction. There is no `task` entity type any more; tasks dissolved into recurrence YAML at natural-home paths (`/workspace/reports/{slug}/_spec.yaml`, etc). What remains under `EditEntity`'s reach is a narrow set of scheduling-index/credential/ephemeral types (`agent`, `platform`, `session`, `document`, `work`).

The consequence in production: when YARNNN-the-orchestration-surface needs to read `/workspace/context/competitors/landscape.md` to answer a chat question about competitive state, it has no primitive that reaches that file directly. The compact-index perception channel surfaces *that the file exists*, but for content YARNNN must either:

- (a) call `QueryKnowledge` — but `QueryKnowledge` is headless-only by registry rule;
- (b) call `ReadRevision(offset=0)` — works mechanically, but using a history-archaeology primitive to read current state is incoherent;
- (c) be silent on the content — the production failure mode.

This is a **first-principles failure** revealed by benchmarking against Claude Code (the conversational agent reads `MEMORY.md` via `Read`/`Edit` directly) and Claude Cowork (folder-as-context: agents working in a folder read everything in it). YARNNN's no-chat-file-layer rule was a 2026-04 design heuristic that didn't survive ADR-231 + ADR-209.

---

## Benchmark synthesis

| Question | Claude Code | Claude Cowork | YARNNN today | Right shape |
|---|---|---|---|---|
| Can the conversational agent read its own filesystem? | Yes (`Read`) | Yes (folder-scoped) | No (chat has no `ReadFile`) | Yes |
| Can it write to its filesystem? | Yes (`Write`/`Edit`) | Yes (folder write-back) | Through `UpdateContext` only (10+ targets) | Yes, directly |
| Can it search files? | Yes (`Grep`/`Glob`) | Implicit (folder enumeration) | No (chat has no `SearchFiles`/`ListFiles`) | Yes |
| Is there a separate "context mutation" verb? | No (memory writes happen through `Edit MEMORY.md`) | No (folder writes are folder writes) | Yes (`UpdateContext`) — load-bearing for inference + dedup | **See ADR-235** |

ADR-234 lands the file-family parity. ADR-235 (companion) addresses the `UpdateContext` consequence.

---

## Decision

**Chat gets the file family.** Four primitives added to `CHAT_PRIMITIVES`:

- `ReadFile(path)` — read a workspace_files entry by absolute path. Already exists; promote to chat.
- `WriteFile(path, content, summary?, ...)` — write a workspace_files entry. Already exists; promote to chat.
- `SearchFiles(query, path_prefix?)` — full-text search inside `workspace_files`. Already exists; promote to chat.
- `ListFiles(path?, recursive?, authored_by?, since?, until?)` — list paths under a prefix. Already exists; promote to chat.

`QueryKnowledge` stays headless-only — distinct cognitive shape (semantic-rank composition over context domains, the substrate behind MCP `pull_context`); chat reaches it through working-memory perception + `ReadFile` for specifics.

`ReadAgentFile` stays headless-only — inter-agent coordination (ADR-116 Phase 2), not chat orchestration's job.

### What this enables

Concrete chat flows that worked badly or not at all pre-ADR-234:

| User asks | YARNNN can now |
|---|---|
| *"What's in our competitors' landscape file?"* | `ReadFile(path='/workspace/context/competitors/landscape.md')` |
| *"Update our brand voice — replace 'fun' with 'direct' everywhere"* | `WriteFile` after operator confirmation. Or with revision-aware tools: `ReadFile` → mutate → `WriteFile`. |
| *"Show me every file Reviewer has written this week"* | `ListFiles(authored_by='reviewer:*', since='2026-04-22')` |
| *"Find the file where I last wrote about pricing strategy"* | `SearchFiles(query='pricing strategy')` |

The four primitives also enable the chat-side equivalent of Claude Code's `Read` → think → `Edit` → verify loop on workspace files.

### What this does NOT enable

- **No agent-scoped writes from chat.** `WriteFile` writes to `workspace_files` paths; agent-private paths under `/agents/{slug}/` remain headless-only by *path convention*, not by primitive availability. Chat YARNNN can technically write any path, but the prompt guidance frames `/agents/{slug}/` as "the headless agent's mind, don't reach in." (Same Claude Code pattern: Read/Edit are universal, but the convention is to not edit subagent-internal files from the parent.)
- **No bypass of `UpdateContext` semantics.** Identity/brand inference, memory dedup, feedback-routing → all stay through `UpdateContext` (or its successors per ADR-235). `WriteFile` is for direct file ops; the inference + post-processing handlers remain semantically distinct.

---

## Implementation

### Files modified (4):

- `api/services/primitives/registry.py`
  - Add `READ_FILE_TOOL`, `WRITE_FILE_TOOL`, `SEARCH_FILES_TOOL`, `LIST_FILES_TOOL` to `CHAT_PRIMITIVES`.
  - `CHAT_PRIMITIVES` count: 20 → 24 (still well under any reasonable budget).
  - `_CHAT_TOOL_NAMES` set updates derive automatically.

- `api/agents/prompts/chat/tools_core.py` (or `workspace.py` — whichever profile-section currently documents file-shape primitives)
  - Add a "File Layer" subsection documenting when chat reaches for each verb.
  - Include the path-convention guidance: `/agents/{slug}/` is headless-only-by-convention; `/workspace/context/`, `/workspace/memory/`, `/workspace/reports/`, `/workspace/operations/`, `/workspace/_shared/` are chat's substrate.
  - Establish the **read-before-edit** discipline (matches Claude Code's `Edit` requirement that the file was first read).

- `docs/architecture/primitives-matrix.md`
  - Update mode availability dots: `ReadFile`, `WriteFile`, `SearchFiles`, `ListFiles` go from `chat ○ headless ●` to `chat ● headless ●`.
  - Update mode totals.
  - Rewrite the "Hard boundaries" assertion that claimed chat lacked file-layer primitives — replace with the new boundary: chat does NOT reach inside `/agents/{slug}/` paths by convention (prompt guidance enforces this; primitive does not).

- `api/prompts/CHANGELOG.md`
  - New `[2026.04.29.N]` entry naming the additions and the boundary reframe.

### Files NOT modified

- `api/agents/prompts/chat/onboarding.py`, `entity.py`, `workspace.py`, `behaviors.py` — behavioral guidance for these profiles remains keyed to the cognitive job (onboarding, entity scope, workspace orchestration). The new file-family primitives are tools the profiles can use; they don't change profile composition.
- `api/services/primitives/workspace.py` (the implementation file) — `READ_FILE_TOOL` etc. tool definitions and handlers are unchanged. We're promoting them to chat, not redefining them.
- MCP server / mcp_composition — file-family primitives stay un-exposed on MCP. ADR-169 keeps MCP intent-shaped (`work_on_this`, `pull_context`, `remember_this`); foreign LLMs do not get raw file primitives.
- Headless side — no changes; headless already had the file family.

### Test gate

- `api/test_adr234_chat_file_layer.py` — new test file with assertions:
  - `ReadFile`, `WriteFile`, `SearchFiles`, `ListFiles` are present in `CHAT_PRIMITIVES`.
  - `QueryKnowledge` is **NOT** in `CHAT_PRIMITIVES` (regression guard against over-exposing semantic-rank).
  - `ReadAgentFile` is **NOT** in `CHAT_PRIMITIVES` (regression guard against inter-agent reach in chat).
  - Round-trip: `WriteFile` → `ReadFile` returns the same content (already covered by existing tests; new assertion confirms the chat path reaches it).
  - Prompt sweep: `prompts/chat/tools_core.py` contains the "File Layer" subsection.
  - Matrix doc dot-verification (string scan): `primitives-matrix.md` shows `chat ●` on the four file primitives.

### Render parity

- All four primitives already exist on API (where chat dispatches) + Unified Scheduler (where headless dispatches). This ADR adds them to *chat* mode availability — the headless availability is unchanged, the API service already has the implementations imported.
- Output Gateway: untouched.
- MCP Server: untouched (ADR-169 surface is independent).
- **No env var changes.**
- **No schema changes.**

### Singular Implementation discipline

- The four file primitives are now in *one* registry list per mode. There is no "chat file family v1" / "chat file family v2" coexistence. The matrix doc states one boundary; the prompt profiles document one set of tools.
- The `EditEntity` workaround for reaching files via typed refs is **not** removed (it still has a valid use for the entity types that legitimately exist), but the prompt guidance no longer tells YARNNN to use it as a file-read substitute.

---

## Risks

**R1 — Tool budget creep.** Chat primitive count goes 20 → 24. Each primitive in the system prompt costs context. Mitigation: the four new primitives are documentation-light (a `Read` tool needs ~80 words of prompt; an inference-merging `UpdateContext` target needs ~250). Net prompt token cost: ~+400-500 tokens added to the cached static block. Cache-friendly.

**R2 — Convention vs. enforcement on `/agents/{slug}/` paths.** This ADR enforces the boundary in prompt only, not in primitive code. A misbehaving prompt could write into an agent's private workspace. Mitigation: this is the same pattern Claude Code uses (no enforcement on `Edit` paths beyond what's in the system prompt and test guards), and the consequences are limited because every write is attributed via ADR-209 — drift is detectable. If pressure surfaces post-ship, a path-prefix gate inside `WRITE_FILE_TOOL` is a small follow-on patch.

**R3 — Operator surprise.** Operators who have learned "chat YARNNN can't read my files" will need to update their mental model. Mitigation: the chat profile's tools_core section explicitly documents the new file family with examples; release note or daily-update mention on first use.

---

## Phasing

Single commit. The change is small enough (registry edit + prompt section + matrix doc + test gate + CHANGELOG) and the boundary too clean to split.

1. Edit `registry.py`: add four imports to `CHAT_PRIMITIVES`.
2. Edit `prompts/chat/tools_core.py` (or `workspace.py`): add "File Layer" subsection.
3. Rewrite the relevant rows + boundary section of `primitives-matrix.md`.
4. Author `test_adr234_chat_file_layer.py`.
5. Add `[2026.04.29.N]` CHANGELOG entry.
6. Atomic commit + push.

ADR-235 (UpdateContext dissolution) lands separately — it's far larger and its diff would obscure ADR-234's small surgical change.

---

## Closing

ADR-234 is the easy half of the audit. The benchmark question (*"why is YARNNN's chat surface less reachable than Claude Code's?"*) has a clean answer: pre-ADR-231 the typed-ref entity layer covered the substrate chat needed to reach. Post-ADR-231 it doesn't. The fix is to give chat the same file-family vocabulary every other reference system gives its conversational agent, scoped by path convention rather than by primitive gating.
