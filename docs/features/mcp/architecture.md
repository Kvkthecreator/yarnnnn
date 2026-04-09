# MCP Architecture — Dispatch, Composition, Cost, Provenance

> **Parent**: [README.md](README.md)
> **Audience**: engineers implementing the MCP server tools against existing YARNNN primitives and services
> **Scope**: how the three tools route through the ADR-168 primitives matrix, what each one composes internally, cost model, and how each tool maps onto existing YARNNN primitives

---

## The runtime-agnostic principle (ADR-164) and the primitives matrix (ADR-168)

Two foundations are load-bearing for this design:

**ADR-164** formalized that primitives are runtime-agnostic: `execute_primitive(auth, name, input)` dispatches to a single handler regardless of caller. Chat calls it, the scheduler calls it via back-office tasks, and the MCP server will call it — same code, same auth, same audit path.

**ADR-168** published the canonical primitives matrix ([docs/architecture/primitives-matrix.md](../../architecture/primitives-matrix.md)) which names every primitive YARNNN exposes, its substrate family, its mode availability, and its handler location. Every tool on the MCP surface maps to one or more primitives from that matrix. **No MCP tool introduces a new primitive.**

The MCP server's job is to be a **thin intent→primitive translator**. The three tools (`work_on_this`, `pull_context`, `remember_this`) are not primitives. They are user-intent-shaped wrappers over existing primitives, dispatched through the same `execute_primitive()` entry point that the chat surface and back-office tasks already use.

### The five callers of `execute_primitive()`

After this design ships, `execute_primitive()` has five callers:

1. **Chat** — `api/agents/thinking_partner.py` (TP streaming conversation)
2. **Scheduler** — `api/services/task_pipeline.py` (task execution, ADR-141)
3. **Back-office tasks** — `api/services/back_office/` (TP-owned hygiene tasks, ADR-164)
4. **Unified scheduler events** — `api/jobs/unified_scheduler.py` (cron triggers)
5. **MCP** — `api/mcp_server/server.py` (this design)

All five enter the primitive layer through the same function with the same signature. This is the load-bearing invariant: there is one pipeline, and MCP is the fifth caller, not a parallel system.

---

## Tool-to-primitive mapping

Every MCP tool maps to one or more existing primitives from the ADR-168 matrix. The column headings match the matrix exactly.

| MCP Tool | Primary primitive | Substrate family | Composition layer |
|---|---|---|---|
| `work_on_this` | `QueryKnowledge` + `ReadFile` | file (semantic-query + file-layer) | `compose_subject_context` + `compose_active_candidates` (ambiguity fallback) |
| `pull_context` | `QueryKnowledge` | file (semantic-query) | thin format step only — no new composition |
| `remember_this` | `UpdateContext` | context (context-mutation) | `classify_memory_target` (deterministic with rare Haiku fallback) |

All three primary primitives already exist:

- **`QueryKnowledge`** — handler in [api/services/primitives/workspace.py](../../../api/services/primitives/workspace.py). "Semantic ranked query over accumulated `/workspace/context/` domains (ADR-151). Distinct from `SearchFiles` — returns ranked results with domain/metadata filters." (from ADR-168 matrix, headless-mode primitive)
- **`ReadFile`** — handler in [api/services/primitives/workspace.py](../../../api/services/primitives/workspace.py). "Read a file from the agent's own workspace." (from ADR-168 matrix, headless-mode primitive)
- **`UpdateContext`** — handler in [api/services/primitives/update_context.py](../../../api/services/primitives/update_context.py). "Single verb for all context mutations. Targets: `identity`, `brand`, `memory`, `agent`, `task`, `deliverable`." (from ADR-168 matrix, chat-mode primitive)

### Mode-crossing note

ADR-168's matrix marks `QueryKnowledge`, `ReadFile`, and the file-layer primitives as **headless-only**, not chat-mode. MCP is a new mode distinct from both chat and headless, and the mode-based availability rules in the matrix were written for the TP chat runtime and task execution runtime.

MCP should receive its own mode column in the ADR-168 matrix as part of shipping ADR-169. Proposed values for the three primitives MCP uses:

- `QueryKnowledge` — **MCP: ●** (available) — this is the entire substrate of `pull_context` and `work_on_this`
- `ReadFile` — **MCP: ●** (available, scoped) — scoped to reading paths returned from prior `QueryKnowledge` results, not arbitrary paths
- `UpdateContext` — **MCP: ●** (available with scope guards) — see "Scope guards" below for which `target` values MCP is allowed to write

This is an additive change to the matrix, not a redefinition. ADR-169 will include the matrix update as part of its implementation sweep.

### `work_on_this` composition — `compose_subject_context`

The composition is a new function, `compose_subject_context(auth, subject_hint, context)`, that lives at **`api/services/mcp_composition.py`** (new file). Its job:

1. **Resolve subject from `subject_hint` or extract from `context`** via keyword matching against the directory registry (`WORKSPACE_DIRECTORIES` in [api/services/directory_registry.py](../../../api/services/directory_registry.py)). Deterministic, LLM-free. If keyword matching fails, fall through to the ambiguity fallback below.
2. **Identify the subject's domain** from the registry's keyword metadata.
3. **Pull the entity profile** via `execute_primitive(auth, "QueryKnowledge", {"query": subject, "domain": domain, "limit": 1})` then `execute_primitive(auth, "ReadFile", {"path": ...})` for the top hit's full content.
4. **Pull recent signals** via `execute_primitive(auth, "QueryKnowledge", {"query": f"{subject} recent signals", "domain": domain, "limit": 5})` — take top 5.
5. **Pull identity-relevant snippets** — read `/workspace/IDENTITY.md` via `ReadFile` and scan for subject mentions. Skip if no match.
6. **Pull prior decisions** — query `/workspace/memory/notes.md` for subject mentions via `QueryKnowledge` with `path_prefix="/workspace/memory/"`.
7. **List related tasks** — lightweight SQL query against `tasks` table for tasks with `context_reads` touching the subject's domain. This is a direct table read, not a primitive (because there is no task-listing primitive at the MCP level and task listing is outside the file substrate).
8. **Assemble and return** the `primed_context` bundle with flat `citations` list and `pull_context_hint`.

If subject resolution fails entirely (empty subject, no keyword match, no `subject_hint`), call `compose_active_candidates(auth)` instead.

### `work_on_this` ambiguity fallback — `compose_active_candidates`

Returns the candidate list when `work_on_this` cannot resolve a subject. It reads:

1. **Active tasks** — `_get_active_tasks_sync()` from [working_memory.py](../../../api/services/working_memory.py) (already exists at line 289)
2. **Recent signal activity** — query `workspace_files` for files under `/workspace/context/` modified in the last 7 days, grouped by entity (direct SQL query, not a primitive)
3. **Draft outputs** — query `workspace_files` for paths matching `/tasks/*/outputs/*` with recent updates (direct SQL)
4. **Rank** — freshness + priority score (overdue tasks first, then fresh signals, then drafts)
5. **Return** top 3-5 candidates as the `ambiguous.candidates` list

The direct SQL queries in steps 2 and 3 are a pragmatic exception to "everything goes through primitives" — there is no primitive for "list recently-modified workspace paths grouped by subject," and adding one just for MCP would be premature generalization. If a future caller (back-office task freshness, for example) needs the same query, we can promote it to a primitive then.

### `pull_context` — thin format step over `QueryKnowledge`

`pull_context` is a thin wrapper:

```python
async def handle_pull_context(auth, input):
    subject = input["subject"]
    question = input.get("question")
    domain = input.get("domain")
    limit = min(input.get("limit", 10), 30)

    query = question or subject
    domain_path = f"/workspace/context/{domain}/" if domain else "/workspace/context/"

    result = await execute_primitive(auth, "QueryKnowledge", {
        "query": query,
        "path_prefix": domain_path,
        "limit": limit,
    })

    if not result.get("success"):
        return {"success": False, "error": result.get("error")}

    chunks = [
        {
            "path": r["path"],
            "excerpt": (r.get("content") or "")[:500],
            "relevance": r.get("relevance", r.get("rank")),
            "last_updated": r.get("updated_at"),
            "domain": _extract_domain_from_path(r["path"]),
            "source_tag": _extract_provenance_tag(r.get("content", "")),
        }
        for r in result.get("results", [])
    ]

    return {
        "success": True,
        "subject": subject,
        "chunks": chunks,
        "total_matches": result.get("total_matches", len(chunks)),
        "returned": len(chunks),
        "citations": [c["path"] for c in chunks],
    }
```

Two small helpers:

- `_extract_domain_from_path(path)` — parses `/workspace/context/<domain>/...` and returns the domain segment
- `_extract_provenance_tag(content)` — reads the first-line `<!-- source: ... -->` HTML comment (ADR-162 format) and returns the source identifier (`mcp:claude.ai`, `agent:competitive-intelligence`, etc.) or None

Neither helper is a primitive. They're plain functions in `mcp_composition.py`.

**There is no LLM call anywhere in `pull_context`.** The entire tool is a database query + field reshaping.

### `remember_this` — `UpdateContext` with classification shim

Implementation:

```python
async def handle_remember_this(auth, input):
    content = input["content"]
    about = input.get("about")

    # Classify to UpdateContext target + path
    target, path_hint, confidence = classify_memory_target(content, about)

    if confidence == "ambiguous":
        return {
            "success": True,
            "ambiguous": _build_candidate_targets(content, about),
        }

    # Stamp provenance per ADR-162
    client_name = _derive_client_name(auth)  # from OAuth client reg or User-Agent
    stamped = (
        f"<!-- source: mcp:{client_name} | date: {_today()} "
        f"| user_context: \"{(about or content[:80])}\" -->\n"
        f"{content}"
    )

    # Dispatch through the primitive
    result = await execute_primitive(auth, "UpdateContext", {
        "target": target,
        "text": stamped,
        "path_hint": path_hint,  # for entity-level appends
    })

    return {
        "success": result.get("success", True),
        "written_to": result.get("path"),
        "domain": result.get("domain"),
        "entity": result.get("entity"),
        "append_type": target,
        "provenance": {
            "source": f"mcp:{client_name}",
            "date": _today(),
            "original_context": about or content[:80],
        },
    }
```

### Target permissions and classification branches

All six `UpdateContext` targets (`identity`, `brand`, `memory`, `agent`, `task`, `deliverable`) are **available via MCP**. There are no blanket blocks. This is a deliberate choice: the user is in a thinking session in a foreign LLM, and artificially restricting which context types they can update forces them to close the LLM and switch to YARNNN for things they should be able to say naturally.

Safety shifts from pre-write gating to three mechanisms operating together:

1. **Classification with confident routing** — `classify_memory_target` must confidently identify the target, or return the `ambiguous` response shape. No silent mis-routing.
2. **Mandatory provenance stamping** — every write carries `source: mcp:<client>` per ADR-162. Wrong writes are traceable and correctable downstream.
3. **Daily-update surfacing** — the morning briefing shows what MCP contributed the prior day, grouped by source. The user notices and corrects if something is off.

| Target | MCP allowed? | Routing mechanism |
|---|---|---|
| `identity` | ✅ yes | Classifier routes user-role/company/work facts. Single file — no target ambiguity possible. |
| `brand` | ✅ yes | Classifier routes voice/style preferences. Single file — no target ambiguity possible. |
| `memory` | ✅ yes | Classifier routes general facts + entity-scoped observations. Default workspace-level target. |
| `agent` | ✅ yes, with slug disambiguation | Classifier matches to agent slugs from content + `about`; if multiple slug matches, return `ambiguous` with candidate list. |
| `task` | ✅ yes, with slug disambiguation | Classifier matches to task slugs; if multiple matches, return `ambiguous` with candidates. |
| `deliverable` | ✅ yes, with slug disambiguation | Classifier matches to task slugs (deliverable feedback is task-scoped); ambiguity handled same way. |

### Two-branch classifier logic

The two kinds of writes have structurally different routing:

**Workspace-level branch** (`identity`, `brand`, `memory`) — the target enum is small, mutually exclusive, and each target is a single file. Routing cannot fail in the "which file" sense; it can only fail in the "which enum" sense, and that defaults safely:

```
content is about user's role, company, or work context           → target = identity
content is about voice, tone, style, visual preferences         → target = brand
content is a general fact, preference, or standing instruction  → target = memory
ambiguous between identity and memory                           → default to memory
ambiguous between brand and memory                              → default to memory
```

Defaulting to `memory` is safe because it's the least-committal workspace-level target. If the user says "I actually meant that as an identity fact, not just a note" on their next chat turn, TP-in-chat can re-route via a normal `UpdateContext(target="identity")` call. No state is lost.

**Operational feedback branch** (`agent`, `task`, `deliverable`) — the target enum is conceptually small but routing must identify a specific slug. This is where ambiguity can cause real harm (feedback going to the wrong agent pollutes an innocent memory file), so the classifier is strict:

```
content is feedback about a specific agent's work quality
  → identify agent slug from content + `about`
  → if exactly one agent matches: target = agent, slug = <match>
  → if zero matches: fall through to workspace-level memory with an "unrouted feedback" marker
  → if multiple matches: return ambiguous with candidate slug list

content is feedback about a specific task's output
  → identify task slug from content + `about`
  → same fan-out logic as agents

content is feedback about output format / delivery preferences
  → identify task slug (deliverable feedback is always task-scoped)
  → same fan-out logic
```

When the operational-feedback classifier finds zero slug matches, it falls through to `memory` with a marker rather than returning ambiguous — because zero matches means the LLM probably mis-categorized the content as feedback in the first place, and returning ambiguous would force a useless clarification round. `memory` with a marker is the safer default; TP surfaces unrouted feedback on the next chat turn for disambiguation.

### The classifier in pseudocode

```python
def classify_memory_target(content: str, about: str, auth) -> ClassificationResult:
    # --- Workspace-level branch ---
    if _is_identity_claim(content, about):
        return Result(target="identity", confidence="high")
    if _is_brand_preference(content, about):
        return Result(target="brand", confidence="high")

    # --- Operational feedback branch ---
    if _is_agent_feedback(content, about):
        slugs = _match_agent_slugs(content, about, auth)
        if len(slugs) == 1:
            return Result(target="agent", slug=slugs[0], confidence="high")
        if len(slugs) > 1:
            return Result(ambiguous=True, candidates=[
                {"target": f"agent:{s}", "reason": _slug_reason(s, content)}
                for s in slugs
            ])
        # Zero matches — treat as mis-categorized, fall through to memory
        return Result(target="memory", marker="feedback_unrouted", confidence="medium")

    if _is_task_feedback(content, about):
        # Same fan-out logic as agent
        ...

    if _is_deliverable_preference(content, about):
        # Same fan-out logic as agent
        ...

    # --- Default: general memory ---
    return Result(target="memory", confidence="high")
```

The sub-predicates (`_is_identity_claim`, `_is_agent_feedback`, etc.) are keyword-heuristic functions. A rare Haiku fallback is only invoked when the workspace-level branch is ambiguous between two workspace targets *and* `about` is absent — expected to be <5% of calls. The fallback is a single Haiku call with a tight prompt ("classify this into one of: identity / brand / memory"), costing ~$0.001.

Operational feedback never escalates to Haiku — slug matching is deterministic (either the slug substring is in the content or it isn't), and genuine ambiguity returns the structured `ambiguous` shape for the LLM to surface to the user.

---

## Cost model

Per-call cost, including the rare Haiku fallback on `remember_this`:

| Tool | Cost | What drives it |
|---|---|---|
| `work_on_this` | **~$0** | Deterministic composition over existing primitives, no LLM call |
| `pull_context` | **~$0** | Pure `QueryKnowledge` dispatch + field reshaping |
| `remember_this` | **~$0** in ~95% of cases; ~$0.001 in the rare ambiguous-classification Haiku fallback (~5%) | Deterministic classification dominates; Haiku only when `about` is absent AND keywords are ambiguous |

**Aggregate at scale.** A power user making 20 MCP calls per day across all three tools costs ~$0 in MCP compute — maybe a penny per month if they happen to hit the rare Haiku fallback path. This is a category change from the prior `explain_this` design, which would have cost ~$0.30/month per user.

### Three consequences of zero-cost MCP

1. **Work budget accounting is a non-issue.** MCP calls do not need to consume work units (ADR-120). The Free/Pro tier differentiation does not need to include MCP call limits. Basic abuse prevention (a sanity cap like 1000 calls/day/user shared across all MCP clients for one user) is sufficient.

2. **Cross-LLM installation is free for YARNNN to encourage.** A user installing YARNNN on Claude.ai, ChatGPT, and Gemini simultaneously costs us nothing extra. We can positioning-wise say "install YARNNN on every LLM you use" without worrying about cost scaling with cross-LLM adoption. This is a material GTM improvement over the prior design.

3. **MCP Render service scales cheaply.** Without LLM API calls in the serving path, the MCP server is pure dispatch — Postgres queries, field reshaping, and response composition. It can run on the smallest Render instance profile and scale horizontally on request volume alone. No per-request Claude API budget to manage.

### Why we chose retrieval over composition

The previous design had an `explain_this` tool that made an internal Haiku call to compose an answer from retrieved chunks. It was deleted. Three reasons we don't regret it:

1. **Cross-LLM consistency matters more than in-call synthesis.** Two LLMs querying the same subject must see the same material — otherwise the user notices YARNNN giving different answers to the same question depending on which LLM is calling, and trust collapses. Composition inside YARNNN would introduce answer drift between invocations.

2. **Host LLMs are better at synthesis than a YARNNN-internal Haiku call.** Claude 4.6, GPT-5, and Gemini 3.0 are trained on RAG patterns and are good at synthesizing ranked chunks. They also have the user's conversation, tone, and framing as additional context that a YARNNN-internal composer cannot see. Delegating synthesis to the host LLM is strictly better-informed than doing it server-side.

3. **Zero cost unlocks positioning.** See consequences above. The cost savings translate directly into the "install everywhere" GTM story, which is the product.

---

## Provenance end-to-end

ADR-162 introduced source-provenance HTML comments in workspace files. MCP extends this with the `mcp:<client_name>` source type.

### Where provenance is written

`remember_this` is the only tool that writes to the workspace, so provenance is stamped there. Before calling `UpdateContext`, the MCP wrapper prepends:

```markdown
<!-- source: mcp:claude.ai | date: 2026-04-09 | user_context: "drafting memo about Anthropic enterprise pricing" -->
```

The `<client_name>` is derived from the MCP client's identifier:
- OAuth clients (Claude.ai, ChatGPT): from the client_id registered during OAuth client registration
- Static bearer clients (Claude Desktop, Cursor): from the `User-Agent` header on HTTP transport, or a configured name
- Unknown clients: `mcp:unknown`

Known client identifiers: `claude.ai`, `claude_desktop`, `chatgpt`, `gemini`, `cursor`.

### Where provenance is read

Four places downstream consume MCP provenance:

1. **`pull_context`** — reads the `<!-- source: ... -->` tag from chunk content and surfaces it as `source_tag` in the returned chunks. This is how Case 3 in [workflows.md](workflows.md) achieves cross-LLM attribution ("via ChatGPT, based on the provenance").
2. **Daily-update task pipeline** — when composing the daily briefing, the pipeline groups recent workspace changes by provenance source. MCP-contributed content gets surfaced with attribution ("From your Claude.ai conversation on 2026-04-08: ...").
3. **Inference gap detection (ADR-162)** — existing inference gap reports include provenance; MCP-contributed content flows through the same inference pipeline.
4. **User-facing file viewers in YARNNN** — when the user browses workspace files in YARNNN proper, the HTML comment is rendered as a provenance caption.

### The loop-closing effect

The loop from MCP write → daily-update surfacing → user reads in email is what makes the MCP write path trustworthy. The user contributes something via ChatGPT at 4pm, and at 8am the next morning their daily briefing emails them with "you said this yesterday, here's how it fits with what your workforce is watching."

The **cross-LLM** loop is even more direct: user writes via ChatGPT at 4pm, user opens Gemini at 4:01pm, Gemini's `pull_context` call returns the chunk with `source_tag: mcp:chatgpt`, Gemini attributes the source in its response, user sees the thread across rooms. That's the cross-LLM continuity effect in one round-trip.

Trust accumulates through visibility at multiple time horizons.

---

## File changes required

### New files

- **`api/services/mcp_composition.py`** — new composition module containing:
  - `compose_subject_context(auth, subject_hint, context)` — drives `work_on_this`
  - `compose_active_candidates(auth)` — drives `work_on_this` ambiguity fallback
  - `classify_memory_target(content, about)` — drives `remember_this` (deterministic with rare Haiku fallback)
  - `_extract_domain_from_path(path)` — helper for `pull_context` chunk formatting
  - `_extract_provenance_tag(content)` — helper for `pull_context` source attribution
  - `_derive_client_name(auth)` — helper for `remember_this` provenance stamping

### Modified files

- **`api/mcp_server/server.py`** — rewrite tool registration. Delete 9 existing tools. Add 3 new tools (`work_on_this`, `pull_context`, `remember_this`). Tool handlers become thin wrappers: parse input → call composition function → dispatch primitive → return. No direct service imports beyond `execute_primitive` and the composition module.
- **`api/mcp_server/__init__.py`** — update module docstring to reflect the new three-tool design and the ADR-169 reference.
- **`CLAUDE.md`** — update File Locations table: MCP Server entry gets a sentence about being the fifth caller of `execute_primitive()`. Update any references to "9 tools" or "6 tools" in prior mentions.
- **`docs/architecture/primitives-matrix.md`** — add MCP mode column alongside Chat and Headless. Mark `QueryKnowledge`, `ReadFile`, and `UpdateContext` (scoped) as MCP-available. Keep the matrix's other columns unchanged.
- **`docs/adr/ADR-075-mcp-connector-architecture.md`** — add a note that tool surface is superseded by ADR-169. Everything about OAuth, transport, auth layers stays canonical.
- **`docs/integrations/MCP-CONNECTORS.md`** — mark as superseded by `docs/features/mcp/README.md`. The old doc is frozen at 2026-02-25 and references dead concepts (`platform_content`, `signal-emergent`, `cross_platform binding`).

### Deleted code

Per singular-implementation discipline:

- **9 tool functions in `api/mcp_server/server.py`**: `get_status`, `list_agents`, `run_agent`, `get_agent_output`, `get_context`, `search_content`, `get_agent_card`, `search_knowledge`, `discover_agents`. All gone. No parallel tool registry.
- **Direct service imports in `server.py`**: `execute_agent_run`, `build_working_memory`, `handle_get_system_state`, `AgentWorkspace`, `get_agent_slug`, `get_domain_folder`. None of these belong in the MCP server after this refactor — everything routes through `execute_primitive()` or `mcp_composition`.

### Unchanged

- **`api/mcp_server/auth.py`** — two-layer auth (OAuth + service key) is solid
- **`api/mcp_server/oauth_provider.py`** — OAuth 2.1 implementation unchanged
- **`api/mcp_server/__main__.py`** — entry point and transport selection unchanged
- **Render service config** (`yarnnn-mcp-server`) — same container, same env vars, same deployment
- **OAuth storage tables** (`mcp_oauth_*`) — unchanged

---

## Testing strategy

Five test surfaces, each covering a specific risk:

1. **Composition correctness** — `api/tests/services/test_mcp_composition.py` (new):
   - `compose_subject_context` returns expected primed bundle for a seeded workspace with known entities
   - `compose_active_candidates` ranks candidates correctly given fabricated workspace state
   - `classify_memory_target` routes content to correct `UpdateContext` target under realistic inputs and respects scope guards
   - `_extract_provenance_tag` parses ADR-162 HTML comments correctly

2. **Primitive dispatch invariant** — `api/tests/mcp_server/test_runtime_agnostic.py` (new):
   - Every tool handler calls `execute_primitive()` and does not directly import services
   - The MCP server has no imports from `api/services/` other than `primitives.registry` and `mcp_composition`
   - `remember_this` scope guards reject forbidden targets (`identity`, `brand`, `agent`, `task`, `deliverable`)

3. **Ambiguity & empty shapes contract** — `api/tests/mcp_server/test_response_shapes.py` (new):
   - `work_on_this` with empty context returns `ambiguous` with candidates
   - `remember_this` with unclassifiable content + no `about` returns `ambiguous` with candidates
   - `pull_context` with no matching subject returns `chunks: []` with explanation, not an error

4. **Cross-LLM consistency** — `api/tests/integration/test_mcp_cross_llm.py` (new):
   - `remember_this` from simulated `claude.ai` client commits synchronously
   - Immediately subsequent `pull_context` from simulated `chatgpt` client returns the newly-written chunk
   - Returned chunk carries `source_tag: mcp:claude.ai`
   - Multiple MCP clients in sequence produce distinct source tags readable by a downstream consumer
   - **This is the highest-value test in the suite** — it proves the load-bearing cross-LLM continuity narrative works end-to-end

5. **Provenance end-to-end** — `api/tests/integration/test_mcp_provenance.py` (new):
   - A `remember_this` call stamps the expected HTML comment
   - The stamp is readable by the daily-update pipeline's provenance extractor
   - Gap reports from ADR-162 correctly attribute MCP-sourced material

These tests should be written in the same commit as the implementation per singular-implementation discipline. No "tests coming later."

---

## Rollout plan

The rollout is a single commit (or a small series of commits on one branch) because:

- The change is atomic — old tools deleted, new tools added, MCP server becomes thin dispatcher
- There is no user-facing migration — MCP clients discover tools via the MCP protocol at connection time, so the switch is seamless on client reconnect
- The backend invariants are preserved (auth, transport, OAuth) so existing connected clients don't need to re-authenticate

Sequence within the branch:

1. Write `mcp_composition.py` with the five composition/helper functions and unit tests
2. Rewrite `server.py` with the three new tools, routing through `execute_primitive()` and `mcp_composition`
3. Delete the 9 old tool functions and their direct service imports
4. Update `docs/architecture/primitives-matrix.md` with the MCP mode column
5. Update `CLAUDE.md`, `ADR-075`, and the old `MCP-CONNECTORS.md` (mark superseded)
6. Add integration tests for cross-LLM consistency and provenance
7. Write ADR-169 referencing this folder as canonical product framing; resolve the four open questions listed in README
8. Commit, push, deploy to the MCP server Render service
9. Validate end-to-end: Claude Desktop (stdio), Claude.ai (HTTP + OAuth), ChatGPT (HTTP + OAuth). The most important validation is **cross-LLM**: write via one client, read via another, verify same chunk with correct provenance

Rollback, if needed: revert the branch. OAuth storage and transport are untouched, so there's nothing stateful to unwind. Rollback cost is near zero.

---

## Pre-ship validation gate: `QueryKnowledge` ranking quality

One assumption this entire design rests on is that the existing `QueryKnowledge` primitive's ranking is good enough for subject-level retrieval. If ranking returns irrelevant chunks for real subjects ("Anthropic", "the user's top client", "a recent project"), then `pull_context` returns bad material and host LLMs reason badly over it — and the whole cross-LLM consistency story collapses because the shared substrate is unhelpful.

**This is a testable assumption, not a theoretical worry.** ADR-169 should require a pre-ship validation step:

1. Implement `pull_context` against current `QueryKnowledge`
2. Run it against 10 real subjects from a realistic seeded workspace
3. Human eyeball: are the returned chunks what a human would want to see for that subject?
4. If yes → ship
5. If no → close the gap before shipping. Two options, in preference order:
   - **Embedding-based reranking**: run an embedding similarity pass over the top 30 `QueryKnowledge` results and return the top 10 by cosine similarity. Zero LLM cost, deterministic, improves ranking without composition.
   - **Internal Haiku reranker**: single Haiku call with the query and 30 candidate chunks, returning an ordered top-10. Small cost (~$0.0005), still deterministic from the user's perspective (same chunks in, same order out — no composition drift).

We do not ship until ranking is validated. This is the one explicit quality gate on the implementation.
