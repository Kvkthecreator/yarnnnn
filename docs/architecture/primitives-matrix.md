# Primitives Matrix — Substrate × Mode × Capability

**Status:** Canonical — reflects post-ADR-337 state (working-tree verbs: EditFile / DeleteFile / MoveFile + SearchFiles exact match)
**Last updated:** 2026-06-11 (ADR-337 — file-layer verb completion)
**Governing ADRs:** ADR-146 (Primitive Hardening), ADR-168 (substrate/mode/capability axes + naming reform), ADR-169 (MCP as third caller), ADR-196 (user_memory sunset), ADR-231 (ManageTask dissolved → ManageRecurrence + FireInvocation), ADR-235 (UpdateContext dissolved → InferContext / InferWorkspace / ManageRecurrence / WriteFile), ADR-261 (ManageRecurrence → Schedule; recurrences are prompts; specialists are tools the Reviewer's loop calls), **ADR-296 v2 (wake-as-irreducible-unit; ManageHook added; FireInvocation removed from REVIEWER_PRIMITIVES per D3)**, **ADR-337 (working-tree verbs: EditFile / DeleteFile / MoveFile + SearchFiles exact match — the rm/mv/Edit half of the repo analogy)**
**Related:** ADR-080 (Unified Agent Modes), ADR-151 (Context Domains), ADR-166 (registry cleanup), ADR-216 (YARNNN as orchestration surface, not judgment Agent), ADR-247 (three-party narrative model + primitive ownership), ADR-260 (real-time Reviewer loop), ADR-262 (output topology; Compose primitive + opt-out structural default), FOUNDATIONS Axiom 1 (filesystem substrate) + Axiom 4 (Trigger — wake) + Axiom 5 (Mechanism spectrum)

> **Header note (ADR-261, 2026-05-08):** the `Schedule` primitive is renamed to `Schedule`. Throughout this document, references to `Schedule` should be read as `Schedule` going forward. The semantic surface (action enum: `create | update | pause | resume | archive`) is preserved; only the verb-name changes. Per CLAUDE.md primitive-rename protocol (rule 7b), the code-PR companion to these ADRs sweeps all references in `api/`, `web/`, and remaining docs in one commit. New primitives added by ADRs 260/261/262: `DispatchSpecialist` (Reviewer-only, ADR-261 D7) and `Compose` (callable + opt-out structural-trigger default, ADR-262 D4). The `headless` permission mode survives as a **runtime characteristic** (LLM-call shape) rather than a separate execution path — specialist sub-LLM-calls run with `headless` characteristics within the Reviewer's loop.

> **Header note (ADR-307, 2026-05-30) — the permission gate + `read_only` taxonomy:** every primitive is classified `read_only` (reads + narration: `LookupEntity`, `ListEntities`, `SearchEntities`, `ReadFile`, `ListFiles`, `SearchFiles`, `ReadAgentFile`, `ListRevisions`, `ReadRevision`, `DiffRevisions`, `QueryKnowledge`, `GetSystemState`, `DiscoverAgents`, `list_integrations`, `WebSearch`, `ReturnVerdict`) or **consequential** (everything else — fail-closed default). A single uniform permission gate at `execute_primitive` (`services/primitives/permission.py::resolve_permission`) resolves **apply / queue / deny** for consequential Reviewer calls — no primitive gates itself (the inline autonomy gate was removed from `handle_write_file`). Gate-queueable consequential primitives: `WriteFile` + `EditFile` + `DeleteFile` + `MoveFile` (path-addressed: governance-lock + diff; `MoveFile` is dual-path-addressed — the gate checks source AND destination per ADR-337), `Schedule`, `ManageHook`, `ManageDomains`, `DispatchSpecialist` (delegation-gated). (`ManageAgent` was on this list until its primitive was deleted 2026-08-26; the NAME stays in `GATE_QUEUEABLE_PRIMITIVES` deliberately — that list is keyed by name and fails closed.) Under bounded/manual they QUEUE to the generic `action_proposals` queue (`family='substrate'`); under autonomous they apply. The capital path (`ExecuteProposal`) gates at `review_proposal_dispatch`. `ACTION_DISPATCH_MAP` deleted — proposals store `primitive` directly. New capability tag: **`consequential`** (the complement of `read_only`). **`Clarify` is gate-owned, not read-only (ADR-352):** the ask-gate resolves apply/deny from the witness dial — `bounded`/`manual` → apply; `autonomous` → deny unless `structural_gap=true` (the ADR-344 (B) escalation). See [ADR-307](../adr/ADR-307-unified-permission-taxonomy.md) + [ADR-352](../adr/ADR-352-ask-as-governance-derived-outcome.md) + FOUNDATIONS Derived Principle 23.

> **Header note (ADR-296 v2, 2026-05-20):** the singular Reviewer-invocation gateway is `services/wake.py::submit_wake_proposal()` (plus `stream_addressed_wake()` for SSE). Five wake sources contribute proposals to one evaluation funnel (`services/wake_evaluation.py`); the Reviewer fires only on `escalate`. Two amendments to the primitive matrix: (1) **`ManageHook`** added — the substrate-event-hook lifecycle primitive, sibling to `Schedule`, registered in CHAT_PRIMITIVES + HEADLESS_PRIMITIVES + REVIEWER_PRIMITIVES; (2) **`FireInvocation`** removed from `REVIEWER_PRIMITIVES` per D3 (Reviewer does not self-invoke; cadence + standing-intent + hook-authoring are its trigger-authoring authority). FireInvocation remains in CHAT_PRIMITIVES + HEADLESS_PRIMITIVES — the operator-chat manual-fire surface preserves operator's explicit-assertion wake-warrant per D1.

---

## Dimensional framing (FOUNDATIONS v6.0)

Primitives are the **vocabulary of the Mechanism dimension** (Axiom 5). LLM reasoning in YARNNN speaks through primitives — typed verbs with substrate and permission scope. Prompts are the other half of Mechanism's vocabulary — they configure which primitives the LLM reaches for, in which situations. **Designing primitives without prompts, or prompts without primitives, is a dimensional conflation** (FOUNDATIONS Derived Principle 9).

Primitives carry orthogonal scoping across the other five dimensions:

| FOUNDATIONS dimension | How primitives encode it |
|---|---|
| Substrate (what) | Substrate family column (`entity` / `file` / `lifecycle` / `action` / `interaction` / `external` / `introspection`) — `context` DISSOLVED per ADR-321 (domains are `file`-family paths under `operation/`) |
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
| **Substrate family** (what it operates on) | `entity` / `file` / `lifecycle` / `action` / `interaction` / `external` / `introspection` | Dispatch path, mental model, naming convention. (`context` DISSOLVED per ADR-321 — domains are `file`-family paths under `operation/`.) |
| **Permission mode** (who can call it) | `chat` / `headless` / `both` | Runtime tool availability. Enforced by `CHAT_PRIMITIVES` and `HEADLESS_PRIMITIVES` registries. |

**Plus capability tags** (orthogonal, descriptive): `entity-layer`, `file-layer`, `semantic-query`, `context-mutation`, `lifecycle`, `user-channel`, `user-authorized`, `external`, `introspection`, `asset-render`, `inter-agent`. Tags are metadata on this table, not part of primitive names.

### CRUD split (ADR-206 — operator-facing surface convention)

The primitive set is runtime-neutral, but the *operator surface* convention per ADR-206 routes CRUD actions by cognitive weight:

| Operation | Surface | Primitive path |
|-----------|---------|----------------|
| **Create** (recurrence, rule, signal, SKU) | Modal (`CreateTaskModal`, `CreateRuleModal`) | `Schedule(action="create")` / `WriteFile(scope="workspace", ...)` for governance + rule authoring. High-precision, well-specified; modal provides structured fields. **Note (ADR-235 D2):** there is no feed-surface or modal pathway to author *new agents* — the systemic roster is fixed at signup. |
| **Read** | Direct surface view | Any read primitive (`ReadFile`, `LookupEntity`, `SearchFiles`, `QueryKnowledge`). No modal or chat required. |
| **Update** | Chat + YARNNN | `Schedule(action="update")`, `InferContext` (identity/brand merge), `WriteFile(scope="workspace", ...)` (substrate writes), `EditEntity`. Judgment-shaped — YARNNN asks "why", proposes alternatives, remembers reasoning. |
| **Delete / archive** | Chat + YARNNN, confirmation required | `Schedule(action="archive")`. Irreversibility warrants conversation; YARNNN writes attribution to `/workspace/memory/awareness.md`. |
| **Approve / reject proposal** (money-bearing) | Direct click on cockpit Queue | `handle_execute_proposal` / `handle_reject_proposal`. Not CRUD — surface-level action on a Deliverable. YARNNN observes via compact index. |

**Rule of thumb:** direct surface action for *high-precision actions on a known artifact*; chat for *judgment-shaped or context-rich actions*. YARNNN observes all of them regardless — the operator never leaves YARNNN's awareness, but YARNNN is not a mandatory mediator for every click.

### Three-party primitive ownership (ADR-258 — supersedes ADR-247 D4)

The approval loop primitives express the structural independence of the three parties:

| Party | Primitives available | Safety story |
|-------|---------------------|---------------|
| **YARNNN** (chat) | Full `CHAT_PRIMITIVES` set | Operator-present chat session; attribution `authored_by="yarnnn:chat"`; AUTONOMY gates capital actions |
| **Reviewer** (chat) | Curated `REVIEWER_PRIMITIVES` subset (21 tools as of ADR-296 v2 Checkpoint 2, 2026-05-20 — all reads + `WriteFile` lock-gated + `ProposeAction` + `Schedule` + `ManageHook` (D3 — substrate-event hook authoring as standing-intent authority) + `Compose` + `DispatchSpecialist` + `SyncPlatformState` + `Clarify`) + `ReturnVerdict`. **`FireInvocation` removed per ADR-296 v2 D3** — Reviewer does not self-invoke; cadence + standing-intent + hook-authoring are its trigger-authoring authority. | Attribution `authored_by="reviewer:{occupant}"` + revision chain + AUTONOMY gating + `DEFAULT_REVIEWER_WRITE_LOCKS` (operator-authored substrate locked-by-default) + operator-authored `_locks.yaml` extensions/overrides |
| **Headless agents** (production) | `HEADLESS_PRIMITIVES` (curated subset) + dynamic `platform_*` per capability bundle | `ProposeAction` only for external-write actions — cannot bind decisions; attribution `authored_by="agent:{slug}"` |

**ADR-258 retired the "Reviewer has no primitives" claim.** The Reviewer is a chat-mode caller of the canonical primitive registry — same dispatch path as YARNNN. Independence (THESIS Commitment 2) means the Reviewer's judgment is evaluated against ground truth (money-truth in `_money_truth.md`), not against producer agreement. Independence is preserved by *what the Reviewer reasons against*, not by *which primitives it can call*.

Operator-authored access policy lives in `/workspace/_shared/_locks.yaml` (default-empty, opt-in). When the Reviewer calls `WriteFile`, the handler reads the locks file and rejects writes targeting locked paths. The operator decides their own access policy; the platform does not.

The Reviewer's system prompt cockpit-awareness section is **generated** from `CHAT_PRIMITIVES` and `workspace_paths` constants at module load time (see `api/agents/cockpit_awareness.py`) — the prompt cannot drift from runtime behavior.

---

## The Substrate Families

### `entity` — Relational read layer (the agent OS's `/proc`)

Operates on typed entity references (`<type>:<UUID>` format) over genuinely-non-file DB records. Resolves through [api/services/primitives/refs.py](../../api/services/primitives/refs.py) via `parse_ref` + `resolve_ref`. **Types (post-ADR-322 — the live `ENTITY_TYPES` set, the `/proc` core): `agent`, `version`, `platform`, `session`.** Four DB-backed objects the filesystem can't naturally express: the roster (`agents`), the run ledger (`agent_runs`, immutable), OAuth credential state (`platform_connections`), chat continuity (`chat_sessions`).

**Pruned by ADR-322** (they were never `/proc` records): `document` → a FILE (ADR-197: `workspace_files` at `uploads/{slug}.md`; read via `ReadFile`/`SearchFiles(path_prefix='uploads/')`); `task` → a REDIRECT (ADR-231: thin scheduling index; recurrence interaction is `Schedule`/`FireInvocation`/`ReadFile` of the YAML — the thin `tasks` table stays, just not entity-ref-addressed). `EditEntity` shrinks to the two mutable records (`agent`, `platform`). (`work` was never a real type — ADR-138 renamed it `task`.)

**Axiom 0 note:** The entity layer is narrow by design — it operates only on the "scheduling index / credential / ephemeral queue" DB rows permitted by FOUNDATIONS Axiom 0, and pairs with `GetSystemState` (the aggregate snapshot) as the per-record `cat /proc/{pid}` to its `ps aux`. Semantic content (memory, domain state, theses, observations, uploaded documents) lives in files, reached through the `file` substrate family below, not here. ADR-196 removed `memory`/`domain` (pointed at the dropped `user_memory`); ADR-322 removed `document`/`task` (a file and a redirect). The filesystem replacements (`/workspace/memory/*.md`, `/workspace/operation/{domain}/`, `/workspace/uploads/*.md`) are reached via the file substrate.

Mental model: **"`cat /proc/{record}` — look up a live DB record by reference."** For files (including uploaded documents), use the `file` family.

Verbs: `LookupEntity`, `ListEntities`, `SearchEntities`, `EditEntity`.

### `file` — Virtual filesystem layer

Operates on path-based files in the virtual filesystem (`workspace_files` table). Resolves through `AgentWorkspace` / `KnowledgeBase` classes in [api/services/workspace.py](../../api/services/workspace.py). Paths scoped by `agent_slug` (agent workspace) or `domain` (context domain) or task slug.

Mental model: **"read or write this file at this path."**

Verbs: `ReadFile`, `WriteFile`, `EditFile`, `DeleteFile`, `MoveFile` (ADR-337 working-tree verbs), `SearchFiles` (semantic + exact match), `ListFiles`, `QueryKnowledge` (semantic variant), `ReadAgentFile` (cross-agent variant).

**Repo-analogy mapping (ADR-337)** — names + safety semantics are YARNNN's; parameter contracts follow Claude Code's tool shapes where a trained model prior exists:

| Claude Code / repo verb | YARNNN primitive | Divergence |
|---|---|---|
| `Read` | `ReadFile` | — |
| `Write` | `WriteFile` | every write is an attributed revision (ADR-209) |
| `Edit` | `EditFile` | identical contract (`old_string`/`new_string`/`replace_all`); may not empty a file |
| `rm` | `DeleteFile` | view-only removal — tombstone revision; chain retained; restore = revert-as-write |
| `mv` | `MoveFile` | one attributed operation; refuses destination overwrite; both paths lock-checked |
| Put Back | `Restore` | one verb, both grains — a single trashed file, or a folder trashed as a unit (resolved from `trashed_with`, never from the caller) |
| `rm -r` | `DeleteFolder` | **a FAN-OUT, not one act** — one archive revision per file; group restores as ONE unit; locked children refused + reported; capped at 500 (`MAX_FAN_OUT`) |
| `mv` (dir) | `MoveFolder` | the same fan over `MoveFile`; rename is a sibling move; both roots lock-checked |
| `grep -F` | `SearchFiles(match='exact')` | case-insensitive literal substring over content + path |
| `git log` / `show` / `diff` | `ListRevisions` / `ReadRevision` / `DiffRevisions` | — |
| `git revert` | `ReadRevision` + `WriteFile` | ADR-209 D7 revert-as-write (no pointer-flip) |
| `cp` | — | excluded (demand-pull; no demonstrated need — ADR-337 D6) |
| `Bash` | — | excluded by design: every mutation passes a typed, gateable verb (ADR-307) |

### `context` — DISSOLVED (ADR-321)

The `context` substrate family is **deleted**. Post-ADR-320 a "context domain" is not a separate root — it is `operation/{domain}/`, a `file`-family path under the `operation` root. The family's three members re-homed:

- **Substrate writes** → `file` family. `WriteFile(scope="workspace", path="operation/{domain}/...", content=...)`. The path's top-level root is the address (ADR-320 gate reads it); there is no `scope='context'` and no `domain` param (ADR-321 deleted both). Direct, attributed, revision-chained per ADR-209.
- **Recurrence lifecycle** → `lifecycle` family. `Schedule(action=..., ...)`.
- **Inference-merged writes** → `InferContext` **dissolved** by ADR-324 (it was an application-level workflow — LLM-merge into two identity/brand files — not a primitive; its merge relocated to a dispatch helper).

Mental model (post-ADR-321): **one authored write** (`write_revision`, ADR-209) over a five-root path-native filesystem; "context" was never a place, only a path prefix. ADR-146's consolidation rationale is preserved at the substrate level (one attribution + revision chain), not as a primitive-name family.

### `lifecycle` — Entity lifecycle management

Verbs that update, pause, resume, archive a recurrence, hook, or domain entity. Consistent `Manage*` / `Schedule` pattern. `Schedule` and `ManageHook` both include `action="create"` to author new recurrences / hooks respectively. **`ManageAgent` is DELETED (2026-08-26)** — it managed the pre-ADR-596 agent model (rows in the `agents` table), and an agent is now a BEING declared in `services/agents_registry.AGENTS`, not a row an LLM edits.

Mental model: **"take this lifecycle action on this named thing."**

Verbs: `Schedule` (recurrence lifecycle — cron-tick wake source's configuration), **`ManageHook`** (substrate-event hook lifecycle per ADR-296 v2 D2 — substrate-event wake source's configuration), `ManageDomains`, `DiscoverAgents` (read-only lifecycle), `FireInvocation` (chat-only manual-fire of recurrences per ADR-296 v2 D3 — removed from REVIEWER_PRIMITIVES).

`ManageTask` was dissolved by ADR-231 Phase 3.7 — lifecycle actions route to `Schedule`, run-now trigger routes to `FireInvocation`.

**Schedule and ManageHook are sibling shapes** (ADR-296 v2 D2). Both write to root-level YAML in `/workspace/`: `_recurrences.yaml` and `_hooks.yaml`. Both configure a wake source. Both go through the same ADR-209 attribution chain. The two surfaces let Identities author cadence and event-interest as parallel modes of trigger authoring per Derived Principle 18.

### `action` — User-initiated typed actions

Verbs that take a specific typed action at the user's direction, distinct from entity mutations. **Currently empty** — `RepurposeOutput` was deleted by ADR-579 D9 (broken, UI-less, and doctrinally refused by ADR-333 D5's no-second-production-pass rule; repurposing is a lane judgment act producing a new cited artifact). The category is kept as a named slot — publish, export-as-X would land here if promoted.

Mental model: **"do this specific operation the user just asked for."**

Verbs: (none). (ADR-417: `RuntimeDispatch` asset generation retired; ADR-579: `RepurposeOutput` deleted.)

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
| 2 | User pastes material → `recent_uploads` populated, user message has text | Run inference. | `InferContext(target="identity", text=…)` (ADR-235 D1.a — inference-merged write to IDENTITY.md) |
| 3 | `workspace_state.identity = "rich"`, `context_domains = 0` | Scaffold domain entities so accumulation recurrences have substrate. | `ManageDomains(action="scaffold", entities=[…])` |
| 4 | `context_domains = 3`, `recurrences_active = 1` | Suggest a first recurring deliverable. | `Schedule(action="create", shape="deliverable", slug="competitive-brief", body={…})` (ADR-235 D1.c) |
| 5 | User: "show me what's running" → `active_tasks` already in compact index | Answer from perception; no primitive needed. | *(no tool call — compose answer from working memory)* |

Four primitives touched in five turns, across four different substrate families (`interaction`, `context`, `lifecycle`, `lifecycle`). Turn 5 uses zero primitives because perception already carries the answer. This is the intended shape: **perception surfaces state, primitives change it.**

Every verb in that loop is in the matrix below. The decision loop ("read perception, pick next action") lives in YARNNN's system prompt, not in any primitive.

---

## The Full Matrix

**Legend:** ● available, ○ not available in this mode.

**MCP mode** was added by ADR-169 as a third runtime mode alongside Chat and Headless. MCP is the foreign-LLM surface — tools are invoked by Claude.ai, ChatGPT, Gemini, and other LLM hosts on behalf of the user. **The MCP tool surface (ADR-543 + ADR-545 over ADR-512) is file-native — `open` / `list` / `search` / `save` / `edit` / `delete` / `move` / `history` / `share` — each verb a binding of a kernel verb, SERVER-SIDE composed over the kernel primitives below** (consumer hosts chain only ~3–5 tool rounds, so composition lives inside yarnnn — ADR-368 Correction 1, retained). One species-blind **file** contract (ADR-512): `open` = deterministic path/handle read + attribution + recent revisions; `list` = the workspace-scoped enumeration; `search` = ranked semantic read; `save` = the CAS attributed write; `history` = the revision chain (`ListRevisions`/`DiffRevisions` — ADR-311 §3's killer capability, exposed via composition); `share` = the grant act. The ADR-169 intent tools (`work_on_this`/`pull_context`/`remember_this`) AND the ADR-368 memory verbs (`remember`/`recall`/`trace`) are DELETED. See [docs/features/mcp/architecture.md](../features/mcp/architecture.md).

| Primitive | Substrate | Chat | Headless | MCP | Capability tags | Handler file | Purpose |
|---|---|:---:|:---:|:---:|---|---|---|
| `LookupEntity` | entity | ● | ● | ○ | entity-layer | [read.py](../../api/services/primitives/read.py) | Look up entity by typed ref (`agent:uuid`, `document:uuid`). |
| `ListEntities` | entity | ● | ● | ○ | entity-layer | [list.py](../../api/services/primitives/list.py) | Enumerate entities by type and filter. |
| `SearchEntities` | entity | ● | ● | ○ | entity-layer | [search.py](../../api/services/primitives/search.py) | Search entities by content or metadata. |
| `EditEntity` | entity | ● | ○ | ○ | entity-layer, user-authorized | [edit.py](../../api/services/primitives/edit.py) | Mutate entity fields under user direction. Chat only — headless has no user authorization path. |
| `ReadFile` | file | ● | ● | ○ | file-layer | [workspace.py](../../api/services/primitives/workspace.py) | Read a file from the workspace filesystem. Two scopes (**ADR-235 Option A**): `scope='workspace'` (chat default) reaches operator-shared substrate via workspace-relative path; `scope='agent'` (headless default) reaches the calling agent's workspace. MCP reads workspace files via `pull_context` → `QueryKnowledge` (user-scoped), not via `ReadFile` (path-shaped). |
| `WriteFile` | file | ● | ● | ○ | file-layer | [workspace.py](../../api/services/primitives/workspace.py) | Write a file to the workspace through the Authored Substrate (ADR-209 attribution + revision chain). Two scopes (**ADR-321** — address-space selector; the path's top-level root IS the address): `scope='workspace'` (chat default — the five-root operator-shared filesystem; accumulated domain context is path-native at `operation/{domain}/`); `scope='agent'` (calling agent's workspace). **`scope='context'` + `domain` param DELETED by ADR-321** — domains re-rooted from `context/` to `operation/`; embedding is no longer a write side-effect (the explicit `Embed` primitive, ADR-325). **ADR-235 D1.b**: writes to recognized canonical paths emit activity-log events automatically (`system/notes.md` → `memory_written`, `agents/{slug}/memory/feedback.md` → `agent_feedback`). |
| `EditFile` | file | ● | ● | ○ | file-layer, consequential | [workspace.py](../../api/services/primitives/workspace.py) | **ADR-337 D1.** Surgical string replacement (`old_string`/`new_string`/`replace_all` — the Claude Code `Edit` contract, borrowed model prior). One attributed revision; may not empty a file (`empty_content_blocked` — removal is `DeleteFile`, by intent). Path-addressed gate-queueable (governance locks DENY). Preferred over `WriteFile` for any change to an existing file — kills the whole-file-rewrite truncation exposure. |
| `DeleteFile` | file | ● | ● | ○ | file-layer, consequential | [workspace.py](../../api/services/primitives/workspace.py) | **ADR-337 D2.** Remove a file from the live view: attributed tombstone revision (current blob, `DeleteFile:` message) + `workspace_files` row removal. The revision chain is retained — deletion is a view change, not information loss; restore = `ReadRevision` + `WriteFile` (ADR-209 D7). Path-addressed gate-queueable; governance-locked paths cannot be deleted. |
| `DeleteFolder` | folder | ● | ● | ○ | folder-layer, consequential | [folder.py](../../api/services/primitives/folder.py) | **ADR-337 amended (2026-08-21).** Move a whole folder to Trash by fanning out `folder_organize.trash_folder` — one attributed `lifecycle='archived'` revision per file, the group stamped with its deleted ROOT so Trash restores it as one unit. Locked children REFUSED and named in `locked`, never silently skipped. Refuses past `MAX_FAN_OUT` (500) rather than half-performing. Path-addressed gate-queueable. **Not an artifact verb** — after the fan there is nothing at the path to open. |
| `MoveFolder` | folder | ● | ● | ○ | folder-layer, consequential | [folder.py](../../api/services/primitives/folder.py) | **ADR-337 amended (2026-08-21).** Move or RENAME a folder — one act, addressed differently. Fans out over `MoveFile` (the ONE mover, so an upload's `.extracted.md` projection travels with its raw per ADR-554 D1); nested empty folders travel as markers. **Dual-path-addressed**: a fan INTO locked territory is as much a breach as one OUT of it. Reports `{moved, failed, locked}` — a half-landed fan is reported, not hidden. |
| `MoveFile` | file | ● | ● | ○ | file-layer, consequential | [workspace.py](../../api/services/primitives/workspace.py) | **ADR-337 D3.** Move/rename as one attributed operation: revision at `new_path` + tombstone/removal at `path`, cross-referencing messages. Refuses to overwrite an existing destination (`destination_exists` — explicit `DeleteFile` first). **Dual-path-addressed**: the gate lock-checks BOTH source and destination. |
| `SearchFiles` | file | ● | ● | ○ | file-layer | [workspace.py](../../api/services/primitives/workspace.py) | Search across workspace files. Two match modes (**ADR-337 D4**): `match='semantic'` (default, BM25 ranked) or `match='exact'` (case-insensitive literal substring over content + path — the grep shape; **ADR-339 D2**: ONE literal substring — multi-word queries match only as exact phrases, and zero-yield results say so explicitly). Two scopes (**ADR-235 Option A**): `scope='workspace'` (chat default — entire operator workspace) or `scope='agent'`. |
| `ListFiles` | file | ● | ● | ○ | file-layer | [workspace.py](../../api/services/primitives/workspace.py) | Recursive tree listing with metadata (**ADR-339 D1**): one call returns the full subtree under `path` — per-file `path` / `bytes` / `updated_at` / head `authored_by` (the `git status`-shaped view; 0-byte litter visible without a read). Two scopes (**ADR-235 Option A**): `scope='workspace'` (chat default) or `scope='agent'`. ADR-209 Phase 3 filters (`authored_by` / `since` / `until`) apply to the head revision. |
| `ListRevisions` | file | ● | ● | ○ | file-layer, authored-substrate | [revisions.py](../../api/services/primitives/revisions.py) | ADR-209 Phase 3. Return the revision chain for a workspace path (newest first). Surfaces the Authored Substrate's parent-pointer history — who edited what, when. Chat parity intentional: operators + YARNNN inspect authored files through the same API. |
| `ReadRevision` | file | ● | ● | ○ | file-layer, authored-substrate | [revisions.py](../../api/services/primitives/revisions.py) | ADR-209 Phase 3. Read a specific historical revision of a file (by offset or revision_id). Returns content + full authorship trailer. Zero-LLM, pure substrate read. |
| `DiffRevisions` | file | ● | ● | ○ | file-layer, authored-substrate | [revisions.py](../../api/services/primitives/revisions.py) | ADR-209 Phase 3. Pure-Python unified diff between two revisions of the same path. Zero LLM cost, deterministic. |
| `QueryKnowledge` | file | ○ | ● | ● | semantic-query | [workspace.py](../../api/services/primitives/workspace.py) | Semantic ranked query over accumulated `/workspace/context/` domains (ADR-151). Distinct from `SearchFiles` — returns ranked results with domain/metadata filters. **MCP's primary primitive**: `pull_context` is a thin wrapper, `work_on_this` composes over it. |
| `ReadAgentFile` | file | ○ | ● | ○ | file-layer, inter-agent | [workspace.py](../../api/services/primitives/workspace.py) | Read a file from another agent's workspace (read-only, ADR-116). |
| `DiscoverAgents` | lifecycle | ○ | ● | ○ | inter-agent | [workspace.py](../../api/services/primitives/workspace.py) | Find other agents in the workspace by role/scope/status (ADR-116 Phase 2). |
| `InferContext` | context | ● | ○ | ● | inference, context-mutation | [infer_context.py](../../api/services/primitives/infer_context.py) | **ADR-235 D1.a.** Inference-merged write to IDENTITY.md or BRAND.md. Sonnet merge over operator text + uploaded docs + URLs; preserves prior content. ADR-162 gap detection runs on the result and is returned in `gaps`. **MCP `remember_this`** dispatches here for `target='identity'`/`'brand'`. |
| `Schedule` | lifecycle | ● | ● | ○ | lifecycle | [manage_recurrence.py](../../api/services/primitives/manage_recurrence.py) | **ADR-235 D1.c.** Recurrence-declaration lifecycle: `create`/`update`/`pause`/`resume`/`archive` over `/workspace/_recurrences.yaml` (the cron-tick wake source's configuration per ADR-296 v2 D2). Mirrors `ManageDomains`. Sibling to `ManageHook`. |
| `ManageHook` | lifecycle | ● | ● | ○ | lifecycle | [manage_hook.py](../../api/services/primitives/manage_hook.py) | **ADR-296 v2 D2.** Substrate-event hook lifecycle: `create`/`update`/`pause`/`resume`/`archive` over `/workspace/_hooks.yaml` (the substrate-event wake source's configuration). Sibling shape to `Schedule`. Hook fields: `slug`, `event` (today: `substrate_change`), `path_match` (workspace-absolute glob), `field_change` (frontmatter key → expected new value), `prompt`. The substrate-event wake source walks recent `workspace_file_versions` revisions at scheduler tick, matches against declared hooks, submits wake proposals per match. Reviewer-authorable per ADR-296 v2 D3 (standing-intent authority). |
| `ManageDomains` | lifecycle | ● | ● | ○ | lifecycle | [scaffold.py](../../api/services/primitives/scaffold.py) | Scaffold, add, remove, list entities in workspace context domains (ADR-155/157). |
| `Clarify` | interaction | ● | ○ | ○ | user-channel | [registry.py](../../api/services/primitives/registry.py) | Surface a decision only the operator can make. Gate-owned (ADR-352): the ask-gate derives apply/deny from the witness dial — under `autonomous` it is denied unless `structural_gap=true` (ADR-344 (B) escalation), so a Reviewer under a delegated mandate acts instead of enumerating options. Requires live user channel — impossible in headless. MCP uses the `ambiguous` response shape instead. |
| `WebSearch` | external | ● | ● | ○ | external | [web_search.py](../../api/services/primitives/web_search.py) | Search the public web. |
| `SyncPlatformState` | external | ○ | ● | ○ | external, substrate-mirror | [sync_platform_state.py](../../api/services/primitives/sync_platform_state.py) | **ADR-264.** Substrate-canonical-world primitive: wraps `(platform-tool call → substrate write → diff-awareness)` as one atomic deterministic operation. Inputs: `tool` (platform tool name), `tool_args`, `write_to` (substrate path template), optional `iterate_field` + `item_key` for per-item iteration, `diff_aware` (skip write if content unchanged). Writes via `write_revision()` with `authored_by="system:sync-platform-state"`. **NOT in `CHAT_PRIMITIVES`** — operators don't invoke directly; they author `mechanical`-mode recurrences (per ADR-263) that invoke `SyncPlatformState` via the `@primitive: ...` dispatch convention. The dispatcher's `@primitive: ...` parser routes mechanical-recurrence prompts here. Dual surface to the LLM-callable platform tools (D4) — same API client, different consumption pattern (substrate write vs LLM-context return). |
| `list_integrations` | introspection | ● | ○ | ○ | introspection | [registry.py](../../api/services/primitives/registry.py) | List the user's connected platforms. |
| `GetSystemState` | introspection | ● | ● | ○ | introspection | [system_state.py](../../api/services/primitives/system_state.py) | Report system state (tier, limits, health flags). |
| `platform_*` | external | ○ | ● (capability-gated) | ○ | external | [platform_tools.py](../../api/services/platform_tools.py) | Dynamic set resolved per agent capability bundle. Routed through `handle_platform_tool`. Not in static registries. |

### Mode totals (current state, post-ADR-296 v2)

- **Chat mode:** **29 static primitives** (ADR-417 removed `RuntimeDispatch`; ADR-579 removed `RepurposeOutput`) — `LookupEntity`, `ListEntities`, `SearchEntities`, `EditEntity`, `GetSystemState`, `WebSearch`, `list_integrations`, `Embed` (ADR-325), `ManageDomains`, `Schedule` (ADR-235 D1.c), **`ManageHook` (ADR-296 v2 D2 — substrate-event hook lifecycle)**, `Compose` (ADR-262 D4), `DispatchSpecialist` (ADR-261 D7), `Clarify`, `FireInvocation` (ADR-231 D5; chat-only per ADR-296 v2 D3), `ProposeAction` / `ExecuteProposal` / `RejectProposal` (ADR-193), `ListRevisions` / `ReadRevision` / `DiffRevisions` (ADR-209 Phase 3), and the **file family**: `ReadFile`, `WriteFile`, `EditFile` / `DeleteFile` / `MoveFile` (**ADR-337 working-tree verbs**), `SearchFiles`, `ListFiles` (with **ADR-235 Option A** `scope='workspace'`). `QueryKnowledge` + `ReadAgentFile` stay headless-only.
- **Headless mode:** **29 static primitives + `platform_*` dynamic** (ADR-417 removed `RuntimeDispatch`) — `LookupEntity`, `ListEntities`, `SearchEntities`, `GetSystemState`, `WebSearch`, `SyncPlatformState` (ADR-264 — substrate mirror, also dispatched by `mechanical`-mode recurrences via `@primitive: ...` parser), `ReadFile`, `WriteFile`, `EditFile` / `DeleteFile` / `MoveFile` (**ADR-337**), `SearchFiles`, `QueryKnowledge`, `ListFiles`, `Embed` (ADR-325), `DiscoverAgents`, `ReadAgentFile`, `Schedule` (ADR-235 D1.c — agents may pause/resume their own declarations on outcome signals), **`ManageHook` (ADR-296 v2 D2)**, `ManageDomains`, `FireInvocation` (ADR-231 D5), `Compose`, `DispatchSpecialist`, `ProposeAction` (ADR-193), `ListRevisions` / `ReadRevision` / `DiffRevisions` (ADR-209 Phase 3). `ManageTask` removed by ADR-231 Phase 3.7. `UpdateContext` removed by ADR-235.
- **REVIEWER_PRIMITIVES (curated subset for the Reviewer's chat-mode invocations):** **24 tools** — all reads (`ReadFile`/`ListFiles`/`SearchFiles`/`ListRevisions`/`ReadRevision`/`DiffRevisions`/`GetSystemState`/`SearchEntities`/`LookupEntity`/`ListEntities`/`list_integrations`/`WebSearch`/`QueryKnowledge`) + `WriteFile` (lock-gated) + `EditFile` / `DeleteFile` / `MoveFile` (**ADR-337 D5 — the working-tree verbs whose primary customer is the Reviewer's ADR-275 housekeeping cadence**; same-family file verbs, not novel-surface tools — the standing soak watches post-deploy output volume against the 2026-05-25 tool-count canary fingerprint) + `ProposeAction` + `Schedule` + **`ManageHook` (ADR-296 v2 D3 — Reviewer's standing-intent-authoring authority extends to substrate-event hooks)** + `Compose` + `DispatchSpecialist` + `SyncPlatformState` + `Clarify`. **`FireInvocation` removed per ADR-296 v2 D3** — Reviewer does not self-invoke; cadence (`Schedule`) + substrate-event interest (`ManageHook`) + standing intent (`WriteFile` to `/workspace/review/standing_intent.md`) are its trigger-authoring authority.
- **LANE mode (ADR-411 D3 + ADR-467 D4) — the surface a MEMBER actually uses:** the **file verbs** (`ReadFile`, `WriteFile`, `EditFile`, `DeleteFile`, `MoveFile`, `SearchFiles`, `ListFiles`) + the **folder verbs** (`DeleteFolder`, `MoveFolder`) + the uniform extras `QueryKnowledge` / `WebSearch` / `list_integrations` (ADR-535 D2) / `GenerateImage` (ADR-568 D3). Declared in `api/services/lane_runner.py::LANE_TOOL_NAMES` + `LANE_SURFACE_EXTRA`, composed by `lane_tools_openai()`. **Uniform for every lane and every Agent** — capability is not a character trait (ADR-467 D4: a per-Agent `tools` field was a bug factory with no safety payoff). No entity verbs, no `Schedule`, no `DispatchSpecialist`, no `platform_*` reach. ⭐ **`DeleteFile` + `MoveFile` added 2026-08-21**: their absence was the anomaly — they already shipped in Chat, in Reviewer, and as `delete`/`move` on MCP, so a foreign LLM over MCP could delete a member's file while the member's own lane could not, and said so out loud. ⭐ **`DeleteFolder` + `MoveFolder` added the same day**, one grain up and for the identical reason: the fan-out already existed (`services/folder_organize.py`) and only the Files surface could reach it. Gate: [test_verb_families_are_one_set.py](../../api/test_verb_families_are_one_set.py).
- **MCP mode (ADR-543 + ADR-545 over ADR-512):** the tool surface is file-native — `open` / `list` / `search` / `save` / `edit` / `delete` / `move` / `history` / `share` — composed server-side in `api/services/mcp_composition.py` over these kernel primitives: `WriteFile` (save — CAS via `expected_parent_version_id`, gate-checked against `CALLER_WRITE_POLICY["mcp"]`), `EditFile` / `DeleteFile` / `MoveFile` (the ADR-337 working-tree verbs, bound by ADR-545), **`DeleteFolder` / `MoveFolder` (the same two verbs at folder grain)**, `QueryKnowledge` (search's ranked read), `ListRevisions` / `DiffRevisions` (history's chain + inline diffs), and direct workspace-scoped reads (open/list, with list's `since` change feed). MCP is the foreign-LLM surface — a caller of `execute_primitive()` per ADR-164. **The ADR-209-era "revision reads deliberately NOT exposed on MCP" rule is REVERSED** (first by ADR-368's `trace`, ratified at contract altitude by ADR-512): the attributed revision chain is the surface's distinguishing capability, not an archaeology to hide. `InferContext` no longer exists (deleted per ADR-324); its row above is retained history in this table's deleted-primitives ledger sense only.

> ### ⭐ Standing discipline — ONE delete, ONE meaning
>
> **Delete = move to Trash, whoever pulls the lever.** `archive_live_file`
> (`services/authored_substrate.py`) is the single act: the row stays with
> `lifecycle='archived'`, the file appears in Trash, and **`Restore`** puts it
> back — one verb, both grains, bound to the same `restore_group` the Trash
> view calls.
>
> **Why it is a rule (2026-08-21).** Delete used to mean two different things.
> The Files surface archived; the `DeleteFile` primitive REMOVED the live row.
> Both honoured "attributed and retained" — the chain kept everything either
> way — so both looked correct in isolation. But they meant different things TO
> THE OPERATOR: their own click put a file in Trash, an agent's `DeleteFile`
> made it vanish from Trash too, restorable only by hand. Measured before the
> fix: **27 archived rows vs 13 row-removal tombstones** — two populations of
> "deleted" with different recoverability and nothing telling them apart.
>
> ⚠️ **`delete_live_file` REMAINS, and is still correct for MOVE.** A move's
> source row must genuinely go: the file lives at its destination, and
> archiving the source would put a moved file in Trash as well. The two acts
> are not redundant — they answer different questions. **At BOTH grains**: a
> moved folder's source marker tombstones-and-removes too (it used to archive,
> leaving an empty ghost folder in Trash that `Restore` would resurrect at the
> old path).
>
> **One act each, one head-blob form.** `archive_live_file` /
> `restore_live_file` in `services/authored_substrate.py` are called by the
> single-file route, the folder fan-out AND the `Restore` primitive. Each used
> to carry its own write plus its own copy of the ADR-427 head-blob form; they
> agreed, which is not the same as being singular.
>
> **Trashed is a STATE, not an absence.** A read of a trashed path answers
> *"`{path}` is in Trash (moved {date}), as part of the folder `{root}`…"* via
> `describe_if_trashed`, never "File not found". The filter that stops deleted
> content leaking would otherwise turn a deletion into an absence — and the
> model then tells the operator the file never existed while it sits in Trash,
> intact. Metadata only: the bytes stay behind `ReadRevision`, because "deleted
> but still readable in one call" is the ambiguity the filter removed.
>
> The OS lesson this encodes: in a desktop, trashed is a **place you can open**,
> with Put Back beside it — the reversibility is VISIBLE, which is what makes it
> trustworthy. A hidden lifecycle flag has two failure modes and we shipped
> both: readers that forget it serve deleted content; readers that respect it
> report absence.
>
> ⭐ **Interop resolves the grain — against the LIVE tree (2026-08-26).** The
> kernel has two grains; the MCP roster deliberately has ONE `delete` and ONE
> `move`, and `mcp_composition._names_a_folder` picks the fan-out, so a foreign
> caller never has to learn our taxonomy. That resolver must ask about the
> **live** tree, because that is the only tree the fan-outs act on
> (`folder_organize.enumerate_subtree` excludes archived rows by contract). It
> did not, and the two disagreed: `delete` on an already-trashed folder resolved
> as a folder, fanned out over nothing, and answered `success: True · "0 moved
> to Trash"` — an **incorrect success** (ADR-373 D6), where the file grain would
> have refused with `file_not_found`. The resolver now reads with the same
> `lifecycle in (active, delivered)` filter `compose_list` uses: **one definition
> of "what is live"**, so a third reader cannot invent a fourth.
>
> ⭐ **A silently-resolved grain must be a LOUDLY-described one.** Because the
> caller does not choose the grain, the only place the blast radius can be
> declared is the verb's own prose — and ADR-337's safety model is exactly that
> *the descriptive name carries the radius*. Both interop entries said "a
> **file**" while the code fanned out over a subtree up to `MAX_FAN_OUT` (500);
> the kernel's `DELETE_FOLDER_TOOL` had stated its radius since the day it
> shipped. Roster entry and tool docstring now both name the folder grain and
> the sweep. Gate: [test_adr337_interop_folder_grain.py](../../api/test_adr337_interop_folder_grain.py)
> — it DRIVES the resolver (a grep for a missing filter passes for the wrong
> reason) and pins the grain phrase, not the word "folder" (`move`'s docstring
> already said "a better folder", about the destination, and passed vacuously).

> ### ⭐ Standing discipline — a trashed file does not read back
>
> Delete is a **lifecycle transition, not a row removal** (ADR-337 D2 /
> ADR-400): a trashed file KEEPS its `workspace_files` row, which is exactly
> what makes it restorable. So **"the row exists" and "the file is live" are
> different questions**, and every read must ask the second one explicitly via
> `services/workspace_context.py::live_files_filter`.
>
> **Why it is a rule (2026-08-21).** The operator moved 20 briefs to Trash. The
> delete was correct — all 20 archived, chain intact. They kept appearing in the
> Text app's Recents, opened at their URL with full content, read back through
> `ReadFile`, and matched in `SearchFiles`, so the delete looked broken. Four
> read paths never asked. The predicate was a STRING hand-copied into six sites
> and absent from four, in two incompatible dialects —
> `.or_("lifecycle.is.null,lifecycle.neq.archived")` (canonical) and
> `.in_("lifecycle", ["active","delivered"])` (excludes NULL). They agree only
> while the column stays fully backfilled, which is why the divergence hid.
>
> ⚠️ **`_exact_search` filters in Python, not with the helper** — deliberately.
> Its match already occupies the query's one `.or_()` slot, and a second
> `.or_()` REPLACES the first rather than ANDing, which would silently turn a
> substring search into "everything not archived".
>
> The ranked/semantic paths filter **in SQL** (migration 218) so a new caller
> inherits the behaviour — a Python-side filter cannot reach inside an RPC.
>
> Gate: [test_trashed_file_does_not_read_back.py](../../api/test_trashed_file_does_not_read_back.py)
> — asserts the BEHAVIOUR, never the spelling (a gate on the string would pass
> on the wrong dialect).

> ### ⭐ Standing discipline — a verb FAMILY is ONE SET, whoever holds it
>
> Two families today: **file** (`ReadFile` · `WriteFile` · `EditFile` ·
> `DeleteFile` · `MoveFile` · `SearchFiles` · `ListFiles`) and **folder**
> (`DeleteFolder` · `MoveFolder`). Each is **one set**. Any surface that reaches
> the workspace on a principal's behalf holds the WHOLE family — or the
> narrowing is a deliberate decision **with its reason recorded in this
> document**, never an accident of which roster someone remembered to edit.
>
> **Why it is a rule and not a preference (2026-08-21).** The same defect landed
> twice in one day. First: a member asked their lane to delete two config files
> and was told *"my available file tools do not include a file deletion
> primitive"* — true of that surface, false of the system. Then, one grain up:
> asked to delete the FOLDER, the lane said the primitives *"only operate
> file-by-file"* and advised running **`rm -rf` in a terminal** — which would not
> have touched the files at all, the substrate being Postgres rather than disk.
> The fan-out had shipped that week; only the Files surface could reach it.
>
> Nothing caught either because **no gate compared the rosters**: each was
> internally consistent, and the divergence was the defect. A divergence has no
> home unless something asserts *across* surfaces.
>
> ADR-337 named this failure in advance, ruling out a `Bash` primitive: *"it is
> also why missing verbs hurt so much here — there is no shell escape hatch —
> which argues for COMPLETING THE VERB SET, not adding the hatch."* A missing
> verb does not degrade gracefully; it becomes a confident refusal plus a
> workaround that corrupts the operator's model of where their substrate lives.
>
> **No extra ceremony in front of a folder verb, deliberately.** The first
> instinct was to make a lane's folder-delete queue for approval, or cap its fan
> below the operator's. Both were rejected on ADR-337's own first principles:
> the descriptive names ARE the safety model, and the safety here is structural.
> `trash_folder` writes one attributed archive revision PER FILE — nothing is
> removed, the group restores as ONE unit, locked children are refused and
> reported. That is safer than the `rm -rf` the model reached for, and safer
> than `WriteFile`, which can truncate content and flows freely. Gating the
> safest destructive verb while the lossy one runs unimpeded is incoherence,
> not caution.
>
> The comparison is now gated by
> [test_verb_families_are_one_set.py](../../api/test_verb_families_are_one_set.py),
> which derives **both** sides (never a hand-kept expected list, which would
> reproduce the failure it guards) and asserts the load-bearing one directly:
> *a foreign LLM must not be able to do to a member's files what the member's
> own lane cannot.*
>
> Three narrowings are deliberate and stated here:
> - **`DuplicateFile` (ADR-514 D1) is NOT on the lane or MCP surfaces** — it is
>   a convenience over `ReadFile` + `WriteFile` (which both surfaces hold), so
>   its absence costs no capability. On the surfaces that DO carry it the stack
>   is complete and reachable: primitive → `/api/documents/duplicate` →
>   `api.documents.duplicate` → `useFileOrganizeVerbs.onDuplicate` → the Files
>   context menu (`FileContextMenu.tsx`, file targets only) and the Studio
>   artifact menu. Verified 2026-08-21.
> - **`DeleteFile` is not in `LANE_ARTIFACT_VERBS`** — an artifact card is a
>   deep link to a file to open, and after a delete there is nothing there.
>   The call still shows as a labelled tool row; the chain stays walkable.
> - **`MoveFile` cards its DESTINATION** — its result carries both paths and
>   `path` is the source, which no longer exists once the move succeeds.
> - **Neither folder verb is carded** — `DeleteFolder` for `DeleteFile`'s reason
>   (nothing remains at the path); `MoveFolder` because its result names a
>   FOLDER, and an artifact card deep-links a FILE to open. Both still show as
>   labelled tool rows, and their results carry the honest partial
>   (`{archived|moved, locked, failed}`) for the lane to report.

**Hard boundaries (enforced by [api/test_recent_commits.py](../../api/test_recent_commits.py)):**

- Chat has the file-family primitives (`ReadFile`, `WriteFile`, `SearchFiles`, `ListFiles`) per **ADR-234**, with `scope='workspace'` per **ADR-235 Option A** so the chat caller (no agent context) can reach operator-shared substrate. **Boundary preserved by prompt convention, not primitive gating:** chat does NOT reach into `/agents/{slug}/` private paths beyond declared canonical feedback substrate; agent-private workspace is read-only via `ReadAgentFile` in headless mode. `QueryKnowledge` stays headless-only (semantic-rank composition). `ReadAgentFile` stays headless-only (inter-agent coordination per ADR-116).
- ADR-417: `RuntimeDispatch` (image/chart/diagram generation) is retired — yarnnn hosts no generation engine. Generation, when it returns, is a member-attached connector (ADR-413), not an in-house primitive.
- **`UpdateContext` is dissolved** (ADR-235). Inference-merged writes use `InferContext`; substrate writes use `WriteFile(scope='workspace', ...)`; recurrence lifecycle uses `Schedule`. There is no successor verb that re-aggregates these. (ADR-235's `InferWorkspace` first-act primitive was later removed per ADR-314 D4 — dissolved by Direction A; bundle-fork is the constitution-creation event.)
- **`ManageAgent` action enum tightened** (ADR-235 D2): no feed-surface `create`. The systemic agent roster is fixed at signup; users compose recurrences against it instead of authoring new agents. Service code (`agent_creation.create_agent_record`) preserved for the kernel/signup path.
- Headless does NOT have `EditEntity`, `Clarify`, or `list_integrations`. No user-authorization path in headless mode, no user channel, no user-facing mutations, no platform metadata needs that aren't already resolved at capability-bundle time.
- **MCP does NOT have any lifecycle, entity-layer, or agent-scoped file-layer primitives.** The boundary rationale is the ADR-311 §5 substrate↔kernel line (corrected from the older "thinking-mode vs management-mode" framing): a foreign LLM is *userspace with a filesystem* — it operates the commons (file + revision + membership verbs, ADR-512) but never the kernel machinery, **because kernel operations are not filesystem operations**. Specifically: no `ManageAgent`/`Schedule`/`ManageDomains` (no workforce control from foreign LLMs), no `LookupEntity`/`ListEntities`/`SearchEntities`/`EditEntity` (entity layer is chat-only), no `ReadAgentFile` (agent-private file layer is headless-only), no `Clarify` (MCP uses the structured `ambiguous`/`confidence` return shape instead). What varies per principal is the **grant and the lock-set** (`CALLER_WRITE_POLICY["mcp"]`), never the verb ontology (ADR-512 D2) — see [docs/features/mcp/architecture.md](../features/mcp/architecture.md).

---

## Target/Action Enumerations

For verbs that carry a typed sub-action, the enum is load-bearing. Single source of truth: the tool definitions in code. Mirrored here for reference.

### `InferContext.target` (ADR-235 D1.a)

2-value enum. Source of truth: `INFER_CONTEXT_TOOL.input_schema.properties.target.enum` in `api/services/primitives/infer_context.py`.

| Target | Writes to | Typical caller |
|---|---|---|
| `identity` | Identity substrate (`/workspace/persona/IDENTITY.md` + inference merge, ADR-320) | YARNNN during operator-input handling |
| `brand` | Brand substrate (`/workspace/operation/BRAND.md` + inference merge, ADR-320) | YARNNN during operator-input handling |

### `Schedule.action` (ADR-261 §3 — renamed from ManageRecurrence per ADR-235 D1.c)

5-value enum. Source of truth: `SCHEDULE_TOOL.input_schema.properties.action.enum` in `api/services/primitives/schedule.py`.

`shape` is required for all actions and determines the natural-home substrate location (per ADR-231 D2):
- `deliverable` → `/workspace/reports/{slug}/_spec.yaml`
- `accumulation` → `/workspace/operation/{domain}/_recurring.yaml` (multi-entry; `domain` required; ADR-321 re-root from context/)
- `action` → `/workspace/operations/{slug}/_action.yaml`
- `maintenance` → entry in `/workspace/_shared/back-office.yaml` (multi-entry)

| Action | Effect | Mode availability |
|---|---|---|
| `create` | Author a new recurrence YAML declaration (single-decl shapes) or append an entry (multi-decl shapes). Body fields depend on shape. | both |
| `update` | Merge `changes` dict into the existing declaration's body | both |
| `pause` | Set `paused: true` in the declaration. Optional `paused_until` ISO timestamp for time-bound pause. | both |
| `resume` | Clear `paused` flag | both |
| `archive` | Remove the declaration (delete file or remove entry from multi-decl YAML) | both |

After every successful write, the scheduling index is re-materialized (best-effort, non-fatal).

### `WriteFile.scope` (ADR-321 — address-space selector)

2-value enum. Source of truth: `WRITE_FILE_TOOL.input_schema.properties.scope.enum` in `api/services/primitives/workspace.py`. **ADR-321 deleted the 3rd value `context`** (it addressed the dissolved `context/` root) + the `domain` param. The path's top-level root is the address (the ADR-320 gate reads it).

| Scope | Path semantics | Default for | Reaches |
|---|---|---|---|
| `workspace` | Workspace-relative path via `UserMemory` | chat | the five-root operator-shared filesystem (`governance/*`, `constitution/*`, `persona/*`, `operation/*` [incl. accumulated `operation/{domain}/*`], `system/*`, plus `reports/*`, `operations/*`, `agents/{slug}/*`) |
| `agent` | Calling agent's workspace via `AgentWorkspace` | headless agents (when agent context attached to auth) | `/agents/{slug}/{path}` |

`ReadFile` / `SearchFiles` / `ListFiles` share the same 2-value `scope` enum (`workspace` | `agent`). Domain context (formerly `scope='context'`) is now path-native: `WriteFile(scope='workspace', path='operation/{domain}/...')`.

**Activity-log emission** (ADR-235 D1.b): writes to recognized canonical paths emit activity-log events automatically inside `WriteFile`:
- `memory/notes.md` → `memory_written`
- `agents/{slug}/memory/feedback.md` → `agent_feedback`

Other paths emit no activity event (silent default).

### `ManageDomains.action`

| Action | Effect |
|---|---|
| `scaffold` | Bulk entity creation (onboarding, identity update) |
| `add` | Single entity creation (steady-state) |
| `remove` | Deprecate an entity (mark inactive in tracker) |
| `list` | List entities in a domain |

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
- `web/components/feed-surface/` — artifacts that render tool results
- `web/components/workspace/WorkspaceNav.tsx`
- `web/lib/utils.ts`
- `web/lib/api/client.ts` — any primitive-name string literals

### Docs sweep

- `docs/architecture/primitives-matrix.md` — **this file** (update first)
- `docs/architecture/registry-matrix.md` — if the primitive appears in task-type examples
- `docs/architecture/SERVICE-MODEL.md` — primitive references in the service description
- `docs/architecture/orchestration.md` — capabilities → tool mapping
- `docs/architecture/agent-execution-model.md`
- `docs/architecture/YARNNN-DESIGN-PRINCIPLES.md`
- `docs/architecture/WORKSPACE.md`
- `docs/architecture/output-substrate.md`
- `docs/features/context.md`
- `docs/features/agent-playbook-framework.md`
- `docs/features/sessions.md`
- `docs/features/memory.md`
- `docs/features/task-types.md`
- `docs/design/WORKSPACE.md` (ADR-215 surface contracts)
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
| `CaptureConnector` | `services/connectors.py::drain_due_connector_captures` (a direct scheduler walk, not a primitive) | ADR-582 *(2026-08-19)* | The connector is a WRITER, not a pipeline: its only production caller was a `@primitive:` directive string seeded into `_captures.yaml` (production carried zero seeded rows), reading a `_watch.yaml` mirror of a selection the DB row already held. The fan-out insight (per-selector reads over a declared aperture) survives inside the walk. Files `primitives/capture_connector.py` + `services/connector_watch.py` deleted. |
| `RuntimeDispatch` | (none — generation retired) | ADR-417 *(2026-07-08)* | The render service (yarnnn-render) is decommissioned — generation is rented, not owned; yarnnn hosts no generation engine. Asset generation (chart/mermaid/image/video) retired; the `designer` role collapses to compose-only; `has_asset_capabilities()` returns `False` universally. Compose (section→HTML) moved in-API (`services/compose/engine.py`). File `primitives/runtime_dispatch.py` deleted. |
| `RepurposeOutput` | (none — a lane judgment act producing a NEW cited artifact, ADR-579 D8) | ADR-579 D9 *(2026-08-18)* | Broken (`NameError` after the paid LLM call), zero FE consumers since ADR-185 (closed refused), and doctrinally refused by ADR-333 D5 — a second production pass over finished content. File `primitives/repurpose.py` deleted; `/recurrences/{slug}/repurpose` route and the `repurpose` system-call row deleted with it. |
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
| `ManageTask` | `Schedule` (lifecycle) + `FireInvocation` (run-now) | ADR-231 Phase 3.7 *(shipped 2026-04-29)* | Tasks-as-units dissolved; recurrences are YAML declarations at natural-home substrate paths. ManageTask's 8 actions split: lifecycle to ManageRecurrence, trigger to FireInvocation. |
| `UpdateContext` | `InferContext` (identity/brand merge) + `InferWorkspace` (first-act scaffold) + `WriteFile(scope='workspace', ...)` (mandate/autonomy/precedent/awareness/feedback) + `Schedule` (recurrence lifecycle) | ADR-235 *(shipped 2026-04-29)* | Three categorically different cognitive shapes (inference-merged write, substrate write, lifecycle action) hidden under one verb name. Splitting them honors what they are. ADR-209's `write_revision` already unifies the substrate-level write path; the consolidation rationale of ADR-146 is preserved at the substrate level, not at the primitive-name level. |
| `ManageAgent(action="create")` | (no feed-surface successor) | ADR-235 D2 *(shipped 2026-04-29)* | The systemic agent roster is fixed at signup; no feed-surface pathway to author new agents. Service code (`agent_creation.create_agent_record`) preserved for the kernel/signup path. |
| `ManageAgent` (the whole primitive) | (none — an agent is no longer an editable row) | *(shipped 2026-08-26)* | Deleted with the pre-ADR-596 agent model it managed. It wrote lifecycle actions to the `agents` table, which production held EMPTY, for a concept an agent is no longer: a BEING is a row in `services/agents_registry.AGENTS` (ADR-596/600), and authority over a being is UNREPRESENTABLE by the ADR-460 D3.a cliff — so there is deliberately no successor verb. `services/primitives/coordinator.py` deleted; the `/api/agents` router deleted with it. The NAME survives in `GATE_QUEUEABLE_PRIMITIVES` (keyed by name, fails closed) and in FE tool-label maps that render HISTORICAL turns — the ADR-603 D5 `ManageRecurrence` precedent. |

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
- [orchestration.md](orchestration.md) — agent types and the `capabilities` → primitive mapping.
- [SERVICE-MODEL.md](SERVICE-MODEL.md) — system-level description; this doc is the primitive-level deep dive.
- [YARNNN-DESIGN-PRINCIPLES.md](YARNNN-DESIGN-PRINCIPLES.md) — design principles for YARNNN's use of chat-mode primitives.
- [WORKSPACE.md](WORKSPACE.md) — workspace architecture, including the filesystem layout that the `file` substrate family operates on.
- [api/services/primitives/registry.py](../../api/services/primitives/registry.py) — source of truth for registries and handlers.
- [api/prompts/CHANGELOG.md](../../api/prompts/CHANGELOG.md) — behavioral change history.
