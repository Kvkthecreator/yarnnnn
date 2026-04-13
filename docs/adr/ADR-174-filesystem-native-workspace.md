# ADR-174: Filesystem-Native Workspace — Discovery, Search, and Conventions

**Date:** 2026-04-13
**Status:** Implemented
**Authors:** KVK, Claude
**Supersedes:** ADR-151 (Shared Context Domains — discovery mechanism only), ADR-152 (Directory Registry — demoted from enforcement to vocabulary)
**Extends:** ADR-106 (Agent Workspace Architecture), ADR-159 (Filesystem-as-Memory), ADR-166 (Registry Coherence Pass), ADR-170 (Compose Substrate), ADR-173 (Accumulation-First Execution)

---

## Context

YARNNN's workspace accumulates intelligence across runs: context domains grow richer, task outputs converge toward their quality target, and agent memory deepens over time (ADR-173). The infrastructure for this accumulation is in place. What is missing is the structural coherence that makes it discoverable, searchable, and self-documenting.

Three specific gaps drive this ADR:

**Gap 1: Discovery is registry-bound, not filesystem-bound.**
`_get_context_domain_health_sync()` in `working_memory.py` iterates `CONTEXT_DOMAINS` from the Python registry, querying each declared path. Directories created by TP outside the declared key set — `/workspace/context/customers/`, `/workspace/context/investors/`, any domain that emerges organically from work — are invisible to TP's compact index. The workspace cannot see itself fully.

**Gap 2: Semantic search infrastructure exists but is unwired.**
The `workspace_files` table has an `embedding vector(1536)` column and an `ivfflat` index. `QueryKnowledge` and `SearchFiles` use BM25 full-text search (`search_workspace` RPC via Postgres `ts_rank` + `plainto_tsquery`). Embeddings are generated only by `documents.py` (uploaded PDFs via `filesystem_chunks`). Agent-written context files — `/workspace/context/competitors/openai/profile.md`, `/workspace/context/market/landscape.md`, every file that grows richest through use — have no embeddings and are invisible to semantic retrieval. The moat (ADR-072) only compounds if what accumulates can be found.

**Gap 3: Workspace conventions exist only in Python code.**
The structural rules of the workspace — which files to overwrite vs. append, how to name entity folders, where synthesis files live, how to declare page_structure for compose — exist as `STEP_INSTRUCTIONS` strings in `task_types.py`. TP-authored bespoke tasks get no structural guidance. The compose pipeline reads `page_structure` from the task type registry, so TP-created tasks without a registry match cannot use the compose layer. Conventions are locked in code where neither agents nor users can read or extend them.

The direction being formalized: treat the filesystem as the primary source of truth. Registries serve as vocabulary and scaffold libraries, not enforcement gates. Conventions are workspace-resident documents that agents can read, follow, and extend.

---

## Decision

### Decision 1: Filesystem-First Discovery

`_get_context_domain_health_sync()` in `working_memory.py` is rewritten to query `workspace_files` directly for all paths under `/workspace/context/`, grouping results by the first directory segment after `context/`. The directory registry (`WORKSPACE_DIRECTORIES` in `directory_registry.py`) provides display names and `temporal` flags as a lookup layer but does not determine what gets reported. A domain created by TP at `/workspace/context/customers/` appears in the compact index as soon as it contains files, without any registry update.

**Compact index format for domains** — one fixed-width line per non-empty directory:

```
{domain}/ — {N} files, last updated {date} [{canonical|temporal}]
```

Domains with zero files are omitted: they exist as scaffolds, not intelligence. The `temporal` classification (e.g., platform bot directories) comes from the registry lookup; unrecognized domains default to `canonical`. A hard **600-token ceiling** applies across the full compact index regardless of how many domains exist — as the workspace grows, the per-domain line remains fixed. The index is orientation, not documentation; TP reads details on demand via `ReadFile` or `ListFiles`.

The 600-token ceiling is enforced in `format_compact_index()`. In development, a threshold breach raises an assertion. In production, the function logs a warning and truncates deterministically (active tasks first, then domains by last-updated descending, then system summary).

### Decision 2: Selective Semantic Search — Embedding on Write for Context Files Only

Embedding generation is scoped to context domain files only. The cost and complexity analysis:

- OpenAI `text-embedding-3-small`: $0.02 per 1M tokens
- Average context file: ~500 tokens → $0.00001 per file
- 100 active users each writing 10 context files per day: ~500K tokens per day = $0.01 per day
- Cost is negligible. The constraint is latency on the write path and system complexity.

**What gets embedded:**
- Context domain files: all paths matching `/workspace/context/**`

**What does not get embedded:**
- Task outputs (`/tasks/{slug}/outputs/`) — derivative, searched via manifest not content
- Task memory files (`/tasks/{slug}/memory/`) — small, accessed by slug-scoped path not searched
- Uploads (`/workspace/uploads/`) — already handled by `documents.py` and the `filesystem_chunks` table
- Workspace identity/brand/awareness files — small, always read directly by path

This scoping restricts embedding to the intelligence accumulation layer: the files that grow richest through use and are queried most broadly.

**Implementation:**
- `handle_write_file()` in `primitives/workspace.py`: after a successful write to any `/workspace/context/` path, fire-and-forget an async call to `get_embedding(content)` and update the row's `embedding` column. The write operation does not block on embedding completion; failure to embed is logged but does not fail the write.
- New SQL RPC `search_workspace_semantic(p_user_id, p_query_embedding, p_path_prefix, p_limit)`: cosine similarity via `embedding <=> p_query_embedding`, filtered to `p_path_prefix`, returns `path`, `summary`, `content`, `similarity`. Migration adds the RPC; the `ivfflat` index already exists.
- `QueryKnowledge` updated: embed the query string → semantic search as primary path → fall back to BM25 if the embedding API call fails or returns zero results above threshold. The fallback preserves current behavior exactly; the primary path adds semantic recall.
- `SearchFiles` is not changed. It is path-scoped agent workspace search (BM25 is the right tool for path + keyword retrieval). Semantic search is for domain intelligence: "what do we know about OpenAI's pricing strategy?" not "list files in competitors/".

### Decision 3: Workspace Conventions Document

A file `CONVENTIONS.md` is scaffolded at workspace initialization at `/workspace/CONVENTIONS.md`. This is a human- and agent-readable document that declares the structural rules of the workspace. It is injected as a compact block into every task execution prompt and referenced in the TP system prompt.

The initial scaffolded content:

```
## Workspace Conventions

### Directory Layout
/workspace/context/{domain}/{entity-slug}/ — entity-specific files
/workspace/context/{domain}/landscape.md  — cross-entity synthesis (overwrite each run)
/workspace/context/signals/               — temporal signal log (append, newest first)
/workspace/uploads/                       — user-contributed files (never modified by agents)
/tasks/{slug}/outputs/latest/             — current best output (overwrite)
/tasks/{slug}/outputs/{datetime}/         — dated snapshot (preserved)
/tasks/{slug}/memory/                     — task working memory (agent-managed)
/agents/{slug}/                           — agent identity and memory

### Entity File Conventions
Each entity gets its own subfolder: {domain}/{entity-slug}/
Standard files: profile.md, signals.md (domain-specific variants documented in registry)
Naming: lowercase hyphen-separated slugs (e.g., openai/, acme-corp/)

### Write Modes
Entity files (profile.md, product.md, strategy.md): overwrite — keep current best version
Signal/log files (signals.md, latest.md): append newest-first — preserve history
Synthesis files (landscape.md, _synthesis.md): overwrite — full rewrite each cycle
Task outputs (output.md): overwrite latest/, preserve dated snapshot

### Creating New Domains
If the work requires a context domain that does not exist (e.g., /workspace/context/customers/):
create it. No registry approval needed. Name it like existing domains (lowercase, plural noun).
Update landscape.md to describe what the domain tracks.

### page_structure Format (for TP-authored produce_deliverable tasks)
page_structure is a list of section objects in TASK.md under the Process step:
  - id: section-slug
    title: "Section Title"
    prompt: "What to write in this section"
    source_domains: [competitors, market]  # context domains to read
    asset_type: chart  # optional: chart | image | mermaid
The compose pipeline reads page_structure from TASK.md first, registry as fallback.
```

This document is the conventions layer. Agents follow it because it produces consistent, searchable structure. TP reads it when deciding where to write bespoke task outputs and how to scaffold new domains.

**Critically, this document can be extended by TP.** If a user establishes a new convention — "always track investor names under /workspace/context/investors/" — TP appends to CONVENTIONS.md. The document is a living workspace artifact, not frozen code. TP uses `WriteFile(path="/workspace/CONVENTIONS.md")` to extend it.

**Extension discipline:** TP may append to existing sections or add new sections following the same structure (header + bullet grammar). TP cannot restructure, rename, or remove existing sections — only add. This preserves backward compatibility for agents that have already internalized the conventions. A new section must follow the same format: a `###` header, a one-line description, and a bullet list of rules. Prose paragraphs are not permitted in extensions — only structured bullets. This constraint makes the document machine-parseable over time even as it grows.

### Decision 4: Fluid Task Creation — task_types.py as Scaffold Library

`task_types.py` is demoted from an enforcement gate to a scaffold library. The registry remains a curated set of well-tested starting templates that TP draws from when they apply. What changes is what happens when they do not apply.

**Specific changes:**

- `ManageTask(action="create")` can draw from the scaffold library OR accept a bespoke TASK.md spec authored by TP. The registry check becomes a lookup, not a gate.
- The task pipeline reads `page_structure` from TASK.md first; the registry is a fallback. This is the same fallback pattern `surface_type` already uses.
- A new optional field `scaffolded_from: {task_type_key}` can be written to TASK.md to record which template was used. Informational only — not load-bearing for any pipeline logic.

**Compose layer protection:** The compose pipeline (ADR-170) depends on `page_structure` being present for `produces_deliverable` tasks. For TP-authored tasks without a registry match, TP is responsible for writing `page_structure` into TASK.md using the format documented in CONVENTIONS.md. The pipeline behavior is: if `page_structure` is present in TASK.md, use it; if absent and a registry match exists, use the registry definition; if absent and no registry match, skip compose and deliver raw output. This three-tier fallback degrades gracefully without breaking existing tasks.

The registry is not removed. It grows more valuable as a scaffold library as bespoke task creation increases — it is the set of proven templates TP recommends at cold start when there is no workspace context to infer from.

### Decision 5: Compact Index Token Discipline

The working memory compact index (ADR-159) has a hard 600-token ceiling. This formalizes what was previously a soft target. Enforcement rules:

- **Active tasks:** max one line each — `{slug} [{mode}] — last run {date}, next {date}`. Not titles, not objectives, not output previews.
- **Context domains:** one line each as specified in Decision 1 — domain name, file count, last updated, canonical/temporal classification.
- **System summary:** max 3 lines — agent count, workspace state signal, any critical flags (budget exhausted, stale integrations).
- **TP reads on demand.** Task details, agent identities, file contents — all retrieved via `ReadFile`, `ListFiles`, or `GetSystemState` when needed. The index is a map, not a dump.

`format_compact_index()` gains a token count assertion after formatting. In development (non-production env), breaching 600 tokens raises `AssertionError` with the actual count and the offending section. In production, the function logs a warning and applies deterministic truncation: system summary is never truncated; active tasks are truncated beyond 20 entries (oldest last-run first); domains are truncated beyond 15 entries (smallest file count first).

---

## Architecture Integration

### Relationship to Existing ADRs

| ADR | Relationship |
|-----|-------------|
| ADR-106 (Agent Workspace Architecture) | Extends — `AgentWorkspace` abstraction preserved, embedding added to the write path for context files |
| ADR-151 (Shared Context Domains) | Supersedes the discovery mechanism — filesystem query replaces registry iteration; domain structure and entity conventions preserved |
| ADR-152 (Directory Registry) | Demoted from enforcement gate to vocabulary lookup — `WORKSPACE_DIRECTORIES` provides display names and temporal flags, not discovery scope |
| ADR-159 (Filesystem-as-Memory) | Extends — compact index discipline and 600-token ceiling formalized as hard enforcement |
| ADR-166 (Registry Coherence Pass) | Extends — `task_types.py` demoted from gate to scaffold library; output_kind taxonomy and TASK.md serialization preserved |
| ADR-168 (Primitive Matrix) | No changes to primitive names or signatures — `WriteFile`, `ReadFile`, `ListFiles`, `SearchFiles`, `QueryKnowledge` are the right primitives. No new primitives needed. |
| ADR-170 (Compose Substrate) | Protected — `page_structure` promoted to TASK.md as primary source; registry as fallback; compose pipeline gains three-tier fallback |
| ADR-173 (Accumulation-First) | Supported — semantic search makes the accumulated context domain layer findable at scale; CONVENTIONS.md gives agents the structural guidance to accumulate coherently |

### What Does Not Change

**The primitives matrix (ADR-168).** `ReadFile`, `WriteFile`, `SearchFiles`, `ListFiles`, `QueryKnowledge` are the right primitives. No `CreateFolder`, `DeleteFolder`, or `MoveFile` primitives are introduced — `WriteFile` to an arbitrary path creates parent directories implicitly, which is the correct filesystem model.

**The agent roster (ADR-140).** Eight pre-scaffolded agents remain stable. Agent creation stays deliberate. TP can create new context domains freely; creating new agents remains a higher-bar decision requiring durable new context scope.

**The compose substrate (ADR-170).** `sys_manifest.json`, `generation_gaps`, HTML assembly — all filesystem-native and unaffected. This ADR makes `page_structure` readable from TASK.md, which extends compose to bespoke tasks without changing the compose pipeline's internal mechanics.

**The accumulation-first principle (ADR-173).** Unaffected. This ADR makes the infrastructure that principle relies on more robust: semantic search makes accumulated context findable, CONVENTIONS.md gives agents the structural vocabulary to write consistently, and filesystem-first discovery ensures TP sees the full workspace state.

**The directory registry Python file.** `directory_registry.py` is retained as a vocabulary and display-name lookup. It is removed from the discovery hot path but not deleted. The `temporal` flag it carries (distinguishing platform bot directories from canonical domains) is still read by the discovery layer.

### Onboarding Second-Order Effects

Fluid task creation and filesystem-first discovery change onboarding implicitly:

- **Onboarding is the first conversation.** No separate onboarding page or flow. TP reads an empty workspace, sees the compact index is sparse, offers to help. The user's first action becomes their first task.
- **The scaffold library is more valuable at cold start.** When there is no workspace context to infer from, TP draws from `task_types.py` templates. The registry's value is highest when the workspace is empty.
- **CONVENTIONS.md is scaffolded at workspace init.** TP has structural guidance from the first interaction, before any context accumulates.
- **Pre-scaffolded agents are empty vessels.** They gain identity through task execution. The onboarding moment is when TP assigns their first task, not when the user fills in a configuration form.

---

## Implementation Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | ✅ Implemented (2026-04-13) | Filesystem-first discovery — `_get_context_domain_health_sync()` rewritten to query actual filesystem paths, grouped by directory segment. Registry reduced to display-name/temporal-flag lookup. 600-token ceiling enforced in `format_compact_index()` (assertion in dev, warning+truncation in prod). `DEFAULT_CONVENTIONS_MD` added to `agent_framework.py`, scaffolded at `/workspace/CONVENTIONS.md` via `workspace_init.py` Phase 3. Compact conventions block injected into every task execution prompt in `task_pipeline.py`. |
| Phase 2 | ✅ Implemented (2026-04-13) | Semantic search activation — `search_workspace_semantic` SQL RPC added (migration 145). `handle_write_file` scope=context: registry gate removed (unknown domains now accepted, folder derives to `context/{domain}/`), async embedding generation fires on write via `_embed_workspace_file` helper. `handle_query_knowledge` rewritten: semantic-first via `search_workspace_semantic` (threshold 0.3), BM25 fallback on API failure or low similarity. `QUERY_KNOWLEDGE_TOOL` domain field changed from enum to free-form string. Response includes `search_method` field for observability. |
| Phase 3 | ✅ Implemented (2026-04-13) | Fluid task creation — `parse_task_md()` now parses `## Page Structure` YAML section from TASK.md; all four `page_structure` read sites in `task_pipeline.py` prefer `task_info.get("page_structure")` with registry as fallback; three-tier fallback (TASK.md → registry → raw output). `ManageTask(action="create")` gains `page_structure` input field; `_build_custom_task_md()` serializes it as YAML under `## Page Structure`; YAML round-trip uses `pyyaml.safe_load/dump`. `MANAGE_TASK_TOOL` description updated. `DEFAULT_CONVENTIONS_MD` page_structure section updated to reflect `## Page Structure` as top-level TASK.md section (not nested under `## Process`). |

---

## Consequences

**Positive:**
- TP's compact index reflects the actual workspace state, not a subset declared in Python. User-created or TP-created domains are visible immediately.
- Semantic search unlocks the full value of accumulated context: "what do we know about OpenAI's enterprise pricing?" returns semantically relevant files, not just files containing those exact tokens.
- CONVENTIONS.md gives agents structural guidance that TP can extend. The workspace can document its own patterns as they emerge.
- Bespoke tasks authored by TP can participate in the compose pipeline, not just registry-matched tasks.
- The 600-token compact index ceiling prevents working memory bloat as the workspace grows — orientation stays fast.

**Constraints:**
- Embedding generation on the write path adds latency for context file writes. The fire-and-forget pattern means this is non-blocking from the caller's perspective, but it must not fail silently in ways that leave rows with null embeddings indefinitely. A background reconciliation sweep is out of scope for Phase 2 but should be considered if embedding coverage gaps appear in production.
- `QueryKnowledge` now makes an embedding API call on every invocation (Phase 2). At high query volume this adds per-call cost and a failure mode. The BM25 fallback must be tested as a production path, not just a theoretical backup.
- CONVENTIONS.md is an agent-writable file. TP must apply the same judgment to extending it as to any other workspace mutation — conventions that are too specific or contradictory will degrade structural coherence. The document's value depends on TP writing to it rarely and deliberately.
- The three-tier `page_structure` fallback in the compose pipeline (TASK.md → registry → raw output) introduces a new code path that must be tested for all three branches. The "raw output" branch (no page_structure anywhere) must not silently produce malformed compose output.

**Risk: Registry demotion ambiguity.** Demoting `task_types.py` from enforcement gate to scaffold library is a clear architectural statement but requires that every caller of `get_task_type()` that currently treats missing keys as errors is updated to treat them as "no template available." Any caller that raises on a missing registry key will break bespoke task creation.

**Deferred concern: Workspace rot — dirty and wrong knowledge.** As workspaces age and agents accumulate context across many cycles, files can become stale, incorrect, or contradictory. An entity profile written from a web search in January may be factually wrong by April. A synthesis file may reflect a view that newer signals contradict. The current architecture has no mechanism for: (1) detecting that a context file's source data has changed since it was written, beyond a timestamp check on the file itself; (2) marking a file as superseded without destroying its history; (3) flagging contradictions between files in the same domain. The accumulation moat thesis depends on accumulation being *accurate*, not just rich. Workspace hygiene — freshness scoring, deprecation lifecycle, domain-level synthesis rewrites as a correctness mechanism — is a future ADR. The existing `landscape.md` overwrite pattern and `signals.md` append convention are partial mitigations, but they do not address entity file staleness. This concern grows in proportion to workspace age and should be addressed before the product scales to real users with months of accumulated context.
