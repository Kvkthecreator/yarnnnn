# ADR-169: MCP as Context Hub — Three-Tool Surface for Cross-LLM Continuity

**Status:** Implemented (2026-04-09) — `api/services/mcp_composition.py` shipped, `api/mcp_server/server.py` rewritten to 3 tools, 9 legacy tools deleted, primitives matrix updated with MCP mode column, ADR-075 tool surface marked superseded, `docs/integrations/MCP-CONNECTORS.md` marked superseded. Pre-ship validation of `QueryKnowledge` ranking quality still pending before the MCP Render service is redeployed — see Risks section.
**Date:** 2026-04-09
**Authors:** KVK, Claude
**Supersedes:** The 9-tool MCP surface shipped in ADR-075 Phase 1 (`get_status`, `list_agents`, `run_agent`, `get_agent_output`, `get_context`, `search_content`, `get_agent_card`, `search_knowledge`, `discover_agents`)
**Extends:** ADR-075 (MCP technical architecture — OAuth 2.1, transport, auth layers preserved), ADR-164 (primitives runtime-agnostic — MCP becomes the fifth caller of `execute_primitive()`), ADR-168 (primitives matrix — MCP reuses `QueryKnowledge`, `ReadFile`, `UpdateContext`; no new primitives), ADR-151 (context domains — the substrate MCP reads and writes), ADR-152 (unified directory registry), ADR-159 (filesystem-as-memory), ADR-162 (source-provenance HTML comments — extended with `mcp:<client>` source type)

**Canonical product framing:** [docs/features/mcp/README.md](../features/mcp/README.md) and sibling docs (`tool-contracts.md`, `workflows.md`, `architecture.md`). This ADR is the decision record; the feature folder is the living documentation.

---

## Context

### The disease

The previous MCP server (ADR-075 Phase 1, shipped early 2026) exposed 9 tools shaped like YARNNN's backend exposed as CRUD: `get_status`, `list_agents`, `run_agent`, `get_agent_output`, `get_context`, `search_content`, `get_agent_card`, `search_knowledge`, `discover_agents`. This was correct at the time — the platform was much less mature and the MCP surface mirrored what the UI had available.

Since then, 90+ ADRs have reshaped the platform: ADR-138 collapsed the project layer, ADR-140 introduced the pre-scaffolded workforce roster, ADR-151 made context domains the primary accumulation substrate, ADR-156 sunset Composer and made TP the single intelligence layer, ADR-159 moved TP to filesystem-as-memory with a compact index, ADR-161 added the daily-update heartbeat, ADR-163 restructured the surfaces into Chat/Work/Agents/Context, ADR-164 made TP a first-class agent and formalized primitives as runtime-agnostic, ADR-168 published the canonical primitives matrix.

The MCP server tracked none of this. Its tools still reference `agent_runs.draft_content`, still dump the full `build_working_memory()` into a `get_context` response (~3-8K tokens), still expose agent-shaped operations when agents are now an implementation detail. The `instructions` field still mentions Gmail and Calendar (both deleted in ADR-131). The doc that was supposed to carry product framing ([docs/integrations/MCP-CONNECTORS.md](../integrations/MCP-CONNECTORS.md)) is frozen at 2026-02-25 and references `platform_content` (deleted in ADR-153).

### The deeper misframe

The technical drift above is a symptom. The root cause is that the 9-tool surface was shaped by a wrong mental model — **"MCP exposes YARNNN's backend to foreign LLMs"**. Under that framing, the natural design is to port each backend concept (agent, task, output, status) as a tool. This produces operator-mode tools for a user who is not in operator mode.

A user in Claude.ai, ChatGPT, or Gemini is in *thinking* mode, not operator mode. They are mid-conversation, writing a memo, drafting a strategy, prepping a meeting. They will not context-switch to a remote-control interface for their agent workforce. They will not think "let me query `list_agents` to find my competitor agent, then `run_agent` to trigger it, then `get_agent_output` to read the result." That's a YARNNN-employee thought, not a Claude.ai-user thought.

What the user actually wants, implicitly, is that **the LLM they're already in already knows what YARNNN knows** — and can contribute back what they just figured out. The MCP surface should match that thought shape, not the backend shape.

### The cross-LLM insight

A single user often works across multiple LLMs in a single week: Claude.ai for research, ChatGPT for drafting, Gemini for brainstorming. Today each of those conversations starts cold. Insights die when the tab closes. The user is the only thread connecting them, and they keep re-explaining context in every session.

YARNNN can be the thread. The Postgres-backed workspace is already a consistent substrate — every tool call against it sees the same state. If MCP exposes that substrate as consult-and-contribute operations, then every LLM the user installs the connector on reaches the same accumulated intelligence, and every contribution from one LLM is immediately visible to the next. **Cross-LLM continuity becomes the product, not a side-effect.**

This is a category of one. Linear/Notion/GitHub MCP servers expose static storage. Native LLM memory (ChatGPT Memory, Claude Projects) stores conversational facts but does not accumulate intelligence on its own. YARNNN has an autonomous workforce growing the substrate in the background — so the cross-LLM hub is also a *living* hub that gets smarter between sessions without user intervention. No other MCP server can make that claim today.

---

## Decision

### 1. The MCP surface is three intent-shaped tools, not nine data-shaped tools

The entire MCP tool surface becomes:

| Tool | Purpose | Primary primitive |
|---|---|---|
| `work_on_this(context, subject_hint?)` | Prime the LLM with a curated, opinionated starting bundle for a subject the user is about to work on. Ambiguity fallback surfaces workspace-active candidates on cold starts. | `QueryKnowledge` + `ReadFile` + composition |
| `pull_context(subject, question?, domain?, limit?)` | Fetch ranked chunks of accumulated workspace material about a subject. Returns raw material, not a composed answer — the host LLM reasons over the chunks. The primary cross-LLM consultation tool. | `QueryKnowledge` (thin format wrapper) |
| `remember_this(content, about?)` | Write an observation, decision, or insight back into the workspace. Synchronous commit. Immediately visible to any other LLM via subsequent `pull_context`. | `UpdateContext` (with classification shim) |

All 9 legacy tools are deleted. No backward-compatibility shims. Singular implementation per CLAUDE.md discipline.

The names are intentionally layman-shaped. The internals are arbitrarily technical. The LLM reads the tool *description* (not the name) when deciding how to call a tool, so the descriptions carry the hidden instructions — most importantly the instruction to **compress the ongoing conversation into the `context` parameter silently, without asking the user for clarification**. Full descriptions in [docs/features/mcp/tool-contracts.md](../features/mcp/tool-contracts.md).

### 2. Zero YARNNN-internal LLM calls on the serving path

None of the three tools invokes an LLM inside YARNNN as part of normal operation. `work_on_this` composes via deterministic retrieval and ranking. `pull_context` is pure `QueryKnowledge` dispatch. `remember_this` classifies deterministically via keyword heuristics, escalating to a single Haiku call only in the rare `about`-absent-and-ambiguous case (<5% of calls).

This was a deliberate choice over an earlier design that included an `explain_this` tool making an internal Haiku call to compose answers from retrieved chunks. Three reasons we rejected it:

- **Cross-LLM consistency requires substrate-level determinism.** Composition inside YARNNN would produce drift between invocations — two LLMs querying the same subject would see different answers, and trust in YARNNN as a shared context layer would collapse.
- **Host LLMs are better at synthesis than a YARNNN-internal composer.** They have the user's conversation, tone, and framing as context. Delegating synthesis to the host LLM is strictly better-informed.
- **Zero cost unlocks positioning.** Per-call cost of ~$0 means we can encourage users to install YARNNN on every LLM they use without cost scaling. This is the "install everywhere" GTM story.

### 3. `remember_this` target permissions: all six `UpdateContext` targets available

No blanket scope guards. MCP is permitted to write to `identity`, `brand`, `memory`, `agent`, `task`, and `deliverable` — all six `UpdateContext` targets. Safety shifts from pre-write gating to three mechanisms operating together:

1. **Classification with confident routing or structured ambiguity.** The `classify_memory_target` function inside `mcp_composition.py` has a two-branch structure: workspace-level targets (`identity`/`brand`/`memory`) default safely to `memory` on enum ambiguity; operational-feedback targets (`agent`/`task`/`deliverable`) require a confident slug match or return the structured `ambiguous` response shape with candidate slugs for the LLM to surface to the user.
2. **Mandatory provenance stamping** per ADR-162. Every write carries `<!-- source: mcp:<client_name> | date: ... | user_context: ... -->`.
3. **Daily-update surfacing.** The morning briefing groups recent workspace changes by provenance source and attributes MCP contributions explicitly ("From your Claude.ai conversation yesterday: ..."). The user notices and can correct any wrong write within 24 hours.

Pre-write restriction was rejected because it artificially forces the user out of the foreign LLM to make natural workspace-level updates that should happen inline. Post-write visibility plus structured ambiguity handles the safety concerns without friction.

Full target permissions table and classifier pseudocode in [docs/features/mcp/architecture.md](../features/mcp/architecture.md).

### 4. MCP is the fifth caller of `execute_primitive()` — no parallel code path

Per ADR-164's runtime-agnostic principle, the MCP server becomes a thin intent→primitive translator. Tool handlers call `execute_primitive(auth, name, input)` directly. The MCP server does not import services directly beyond `primitives.registry` and the new `mcp_composition` module. Singular code path — no MCP-specific bypass of the primitive layer.

The five callers of `execute_primitive()` after this ADR ships:

1. Chat — `api/agents/thinking_partner.py`
2. Scheduler — `api/services/task_pipeline.py`
3. Back-office tasks — `api/services/back_office/`
4. Unified scheduler events — `api/jobs/unified_scheduler.py`
5. **MCP — `api/mcp_server/server.py`**

### 5. The primitives matrix (ADR-168) gains an MCP mode column

ADR-168's matrix today has two mode columns: Chat and Headless. MCP is a new mode distinct from both and needs its own column. Three primitives become MCP-available:

| Primitive | Chat | Headless | **MCP** | Notes |
|---|:---:|:---:|:---:|---|
| `QueryKnowledge` | ○ | ● | **●** | Entire substrate of `pull_context` and `work_on_this` |
| `ReadFile` | ○ | ● | **●** | Scoped to paths returned from prior `QueryKnowledge` results |
| `UpdateContext` | ● | ○ | **●** | All six targets available; classification + provenance are the safety mechanisms |

This is an additive change to the matrix, not a redefinition. The matrix update ships in the same commit as the MCP server rewrite.

### 6. Cross-LLM continuity is the load-bearing narrative

The design is optimized for the four-case user experience documented in [docs/features/mcp/workflows.md](../features/mcp/workflows.md): conversation topic (`work_on_this`), mid-session reference (`pull_context`), **cross-LLM continuity** (`remember_this` in one LLM → `pull_context` in another), and cold-start ambiguity (`work_on_this` fallback). Case 3 — the cross-LLM one — is the case the entire design exists to serve, and its end-to-end dialogue walkthrough is the load-bearing proof that the mechanism works.

The highest-value integration test in the suite validates this case end-to-end: a `remember_this` call from a simulated `claude.ai` client must be visible to a subsequent `pull_context` call from a simulated `chatgpt` client, with the `source_tag: mcp:claude.ai` preserved on the returned chunk.

### 7. Four decisions locked in as implementation contract

The four items that were open questions during the design discussion are now decided:

| Decision | Value |
|---|---|
| `remember_this` target permissions | All six targets allowed; safety via classification + provenance + daily-update visibility (Decision 3 above) |
| Provenance display in daily-update | Yes. MCP-contributed material surfaces with attribution in the morning briefing |
| `QueryKnowledge` ranking quality | Pre-ship validation gate. Implement first, validate against 10 real seeded subjects, close any gap with embedding-based reranking (zero-cost) before merge |
| Rate limiting | 1000 calls/day/user unified cap across all MCP clients; no Free/Pro tier differentiation on MCP calls because per-call cost is ~$0 |

Per-call cost, work budget accounting, and tier differentiation questions from prior design drafts are resolved: MCP calls are effectively free to serve, do not consume work units (ADR-120), and do not need tier gating.

---

## Consequences

### Implementation

A single branch contains the full changeset. Singular implementation per CLAUDE.md discipline — no parallel tool registry, no dual paths. Sequenced work:

1. **New file**: `api/services/mcp_composition.py` containing `compose_subject_context`, `compose_active_candidates`, `classify_memory_target` (two-branch), and helpers `_extract_domain_from_path`, `_extract_provenance_tag`, `_derive_client_name`
2. **Rewrite**: `api/mcp_server/server.py` — delete 9 legacy tool functions and all direct service imports (`execute_agent_run`, `build_working_memory`, `handle_get_system_state`, `AgentWorkspace`, `get_agent_slug`, `get_domain_folder`). Register 3 new tools routing through `execute_primitive()` and `mcp_composition`
3. **Update**: `api/mcp_server/__init__.py` — docstring reflects the three-tool design and ADR-169 reference
4. **Update**: `docs/architecture/primitives-matrix.md` — add the MCP mode column with `●` on `QueryKnowledge`, `ReadFile`, `UpdateContext`
5. **Update**: `CLAUDE.md` — File Locations entry for MCP server gains the "fifth caller of `execute_primitive()`" sentence; any "9 tools" / "6 tools" references updated to "3 tools"
6. **Mark superseded**: `docs/adr/ADR-075-mcp-connector-architecture.md` gains a note that the tool surface is superseded by this ADR (ADR-169). Everything about OAuth 2.1, transport, auth layers remains canonical and unchanged.
7. **Mark superseded**: `docs/integrations/MCP-CONNECTORS.md` — the frozen 2026-02-25 product-framing doc — is marked as superseded by `docs/features/mcp/README.md`
8. **Tests**: five new test files covering composition correctness, primitive dispatch invariant, ambiguity & empty shape contracts, cross-LLM consistency, and provenance end-to-end. The cross-LLM test is the highest-value validation.
9. **Pre-ship validation**: eyeball 10 real seeded subjects through `pull_context` against the current `QueryKnowledge` RPC. If ranking is insufficient, land embedding-based reranking before merge.

### What stays unchanged

- OAuth 2.1 + static bearer fallback (ADR-075 Phase 1)
- Two-layer auth model (service key + `MCP_USER_ID`)
- FastMCP server + stdio/HTTP transport selection
- `api/mcp_server/auth.py`, `oauth_provider.py`, `__main__.py` module contents
- Render service `yarnnn-mcp-server` container, env vars, deployment configuration
- OAuth storage tables (`mcp_oauth_clients`, `mcp_oauth_codes`, `mcp_oauth_access_tokens`, `mcp_oauth_refresh_tokens`)

This ADR changes the MCP tool surface. It does not touch any of the infrastructure that makes the MCP server a running service.

### Strategic consequences

- **New positioning line**: "YARNNN is the context hub across the LLMs you already use. Install it on Claude.ai, ChatGPT, and Gemini — every one of them now reaches the same accumulated intelligence, and every one of them can contribute back."
- **GTM freedom**: zero per-call cost means no worry about scaling with cross-LLM adoption. Encouraging users to install on every LLM they use is cost-free for us to serve.
- **Category of one**: no other MCP server has an autonomous workforce growing its substrate. The cross-LLM hub positioning is unique to YARNNN.
- **A2A-ready**: external agents consulting YARNNN on a user's behalf use the same three tools. They don't talk to YARNNN's internal agents — they consult the same workspace every other caller consults. The three-tool surface holds for the future ecosystem without modification.

### Risks

1. **`QueryKnowledge` ranking quality is unknown at pre-ship.** This is the one real risk and it has an explicit pre-ship validation gate. If the current RPC returns bad chunks for real subjects, the cross-LLM story fails quietly and users blame YARNNN for being unhelpful. Mitigation: validate before merge, land embedding-based reranking if needed, do not ship until eyeball validation passes.
2. **LLM hosts may not call the tools proactively.** The tool descriptions explicitly instruct the LLM to compress conversation and use the tools without being asked, but LLM hosts have varying proactivity. Mitigation: the descriptions are the first lever; if proactivity is insufficient in practice, a follow-up doc revision sharpens them. Not an architectural risk.
3. **`remember_this` classification may route feedback to the wrong agent in the operational-feedback branch.** The two-branch classifier returns `ambiguous` on multi-slug matches, but single-wrong-match cases are possible. Mitigation: provenance stamps and daily-update surfacing make wrong writes visible and correctable within 24 hours. If empirical wrong-routing rate is high post-ship, strengthen the slug matching or fall through to general memory with a marker.

---

## Related docs

- **Canonical product framing**: [docs/features/mcp/README.md](../features/mcp/README.md)
- **Tool contracts**: [docs/features/mcp/tool-contracts.md](../features/mcp/tool-contracts.md) — signatures, response shapes, tool description text
- **Workflows**: [docs/features/mcp/workflows.md](../features/mcp/workflows.md) — four end-to-end cases including cross-LLM continuity
- **Architecture**: [docs/features/mcp/architecture.md](../features/mcp/architecture.md) — primitive mapping, classifier branches, cost model, testing strategy

---

## Status

**Implemented (2026-04-09)**. Code changes landed in a single commit:

- `api/services/mcp_composition.py` — new module with `compose_subject_context`, `compose_active_candidates`, `classify_memory_target` (two-branch), and provenance helpers (`stamp_provenance`, `derive_client_name`, `extract_domain_from_path`, `_extract_provenance_tag`, `_normalize_client_id`)
- `api/mcp_server/server.py` — rewritten. 9 legacy tools deleted (`get_status`, `list_agents`, `run_agent`, `get_agent_output`, `get_context`, `search_content`, `get_agent_card`, `search_knowledge`, `discover_agents`) plus all direct service imports (`execute_agent_run`, `build_working_memory`, `handle_get_system_state`, `AgentWorkspace`, `get_agent_slug`, `get_domain_folder`). Three new tools registered (`work_on_this`, `pull_context`, `remember_this`). Only `services.mcp_composition` and `services.primitives.registry.execute_primitive` are imported from the services layer — ADR-164 runtime-agnostic invariant satisfied.
- `api/mcp_server/__init__.py` — module docstring updated to reflect the three-tool surface and ADR-169 reference
- `docs/architecture/primitives-matrix.md` — new MCP mode column added to the full matrix, mode totals section updated with MCP entry, hard boundaries section updated with MCP-specific rules
- `docs/adr/ADR-075-mcp-connector-architecture.md` — status line updated to mark tool surface superseded; infrastructure (OAuth 2.1, transport, auth layers, module layout, Render config, OAuth storage tables) remains canonical
- `docs/integrations/MCP-CONNECTORS.md` — superseded banner added at the top pointing to `docs/features/mcp/` and ADR-169; historical content preserved
- `CLAUDE.md` — File Locations table updated with three MCP entries (`MCP Server`, `MCP Composition`, `MCP Feature Docs`)

**Deferred to pre-ship validation**:

- `QueryKnowledge` ranking quality validation against 10 real seeded subjects. If ranking is insufficient, embedding-based reranker lands before the MCP Render service is redeployed. This is the one explicit quality gate called out in the Risks section.

**Unchanged** (intentionally preserved from ADR-075 Phase 1): OAuth 2.1, static bearer fallback, two-layer auth, FastMCP transport selection, `api/mcp_server/{auth,oauth_provider,__main__}.py` module contents, Render service `yarnnn-mcp-server` container and env vars, OAuth storage tables (`mcp_oauth_clients`, `mcp_oauth_codes`, `mcp_oauth_access_tokens`, `mcp_oauth_refresh_tokens`).
