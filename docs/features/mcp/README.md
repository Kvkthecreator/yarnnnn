# MCP Connector — The Judged Context Hub Across LLMs

> **Status**: Implemented. **Strategic framing** governed by **ADR-310** (judged substrate, interop as distribution face — one moat, two faces). **Tool surface** governed by **ADR-368** (memory-first: three verbs `remember` / `recall` / `trace`, composed server-side), which supersedes ADR-311's pure-primitive surface and ADR-169's original three intent tools. ADR-075's OAuth/transport infrastructure is preserved. The connector is **multi-user** (per-request OAuth identity, ADR-310 D4), and `remember` is a **judged write** — every foreign-LLM contribution wakes the Reviewer for evaluation against authored ground-truth (ADR-310 D2 / ADR-368 D5).
> **Updated**: 2026-06-25 (ADR-368 memory-first surface)
> **Authors**: KVK, Claude
> **Related ADRs**: **ADR-368** (memory-first tool surface — governing the verbs), **ADR-310** (judged substrate / interop face — governing the framing), ADR-311 (pure-primitive surface — superseded by ADR-368; substrate truths preserved), ADR-169 (original context-hub framing — superseded; OAuth infra retained), ADR-320/366 (the permission topology the write surface gates against — writes reach `operation/` only), ADR-075 (OAuth + transport — preserved), ADR-296 (wake architecture — `substrate_event` source the judged write fires), ADR-209 (authored substrate — the chain `trace` surfaces)
>
> **Vocabulary note**: This folder was authored on 2026-04-09 under ADR-169, which framed the substrate as grown by "an autonomous workforce." That workforce was dissolved by the bare-kernel ratification (2026-06-01) — the live substrate-growing organ is now the **Reviewer** (the persona-bearing judgment seat) plus **program activation**. Where older text below says "workforce," read "Reviewer + program activation." The load-bearing claims have been corrected; some incidental phrasing is preserved as historical artifact.

---

## What MCP is for YARNNN

**MCP is the interop face of YARNNN's one moat: a judged context substrate, served everywhere.**

YARNNN has exactly one moat — authored substrate under a persona-bearing judgment seat (the Reviewer). That moat is exposed through two faces (ADR-310): the **cockpit** (the operator, in-app) and the **interop face** (a foreign LLM, via MCP). MCP is not a second product. It is how the *judged* substrate reaches the LLMs the operator already uses.

Operators spend their thinking time inside Claude.ai, ChatGPT, Gemini, and other foreign LLM surfaces — often several in a day. Each LLM starts cold; each conversation's conclusions die in that surface. MCP connects each foreign LLM to a single shared substrate: the operator's YARNNN workspace. Every LLM pulls from the same accumulated, *judged* material. Every LLM can contribute back — and every contribution is evaluated by the Reviewer.

The Reviewer + program activation keep the workspace growing. Across the MCP boundary that machinery is invisible. What crosses is **three memory verbs** — shaped on the user's own mental model of a memory that follows them across rooms (ADR-368): put something in, get something out, trace how it changed.

### The singular framing

> A storage hub returns whatever is stored — garbage in, garbage out, no opinion. YARNNN returns substrate the Reviewer has judged, and accepts contributions the Reviewer evaluates. The copyable half (three thin MCP verbs) sits downstream of the uncopyable half (a calibrated judgment seat). **YARNNN is the *judged* memory every LLM consults and contributes to.**

Three things the user can do with their YARNNN memory from any LLM:

| Intent | Verb | What it does |
|---|---|---|
| **"Remember this."** | `remember` | Saves an observation, decision, or insight into the workspace commons (`operation/`), attributed and immediately visible to any other LLM. The seat validates it against ground-truth in the background. |
| **"What do I know about ___?"** | `recall` | Returns ranked excerpts of accumulated material about a subject — composed server-side in one call. YARNNN returns the material; the host LLM explains it. |
| **"How did my thinking on ___ change?"** | `trace` | Returns the authored revision chain of a recorded fact — who changed it, when, and what the change was. The differentiator no plain storage connector can show. |

That's the entire MCP surface. No `list_agents`, no `run_task`, no `get_status`. The user in a foreign LLM is not in operator mode — they're using a memory, and the verbs mirror memory, not operating.

---

## Why these three verbs (ADR-368)

The surface is shaped on the **user's memory mental model**, not the kernel's verb taxonomy. A person does exactly three things with a memory that follows them across rooms: **put something in** (`remember`), **get something out** (`recall`), **trace how it changed** (`trace`). That is the whole surface.

**Why composed verbs, not raw primitives.** ADR-311 proposed exposing the kernel's file primitives directly (`ReadFile` / `SearchFiles` / `WriteFile` / `ListRevisions`) and letting the host LLM compose intent by chaining them — the Claude Code model. ADR-368 corrects this: claude.ai / ChatGPT / Gemini connectors are *consumer chat* hosts that execute only ~3–5 tool rounds per turn before yielding to the user (undocumented but observed; Anthropic publishes no per-turn round limit). A read that *requires* the host to chain `Query → Read → Read → synthesize` burns the round budget fetching and stalls — on exactly the hosts where the ambient magic must happen. So **the multi-step composition lives server-side** (inside YARNNN, an agentic context with no round limit): `recall` and `trace` each compose the kernel primitives internally and return a reason-ready result in **one round**. The raw primitives remain available `defer_loading` for agentic hosts (Claude Code, Desktop) that genuinely chain — the verbs are the front door, the primitives the deferred back door. There is no second vocabulary: the verbs ARE the kernel primitives wearing the user's words.

**Why `recall` returns rather than explains.** A tool that composed an *answer* internally was rejected. Three reasons: (1) **cross-LLM consistency** — an internal composition step returns different answers by invocation timing/temperature/model version; every LLM must see the same substrate. (2) **the host LLM synthesizes better** — it has the user's conversation, tone, and framing; YARNNN has only the chunks. (3) **memory-first clarity** — a tool that "does the thinking" is the deferred *delegation* nature leaking in; the bright line is that the foreign LLM reads/writes a store and the host explains. `recall` connotes retrieval, not synthesis.

**Not nine tools.** A pre-ADR-169 implementation exposed `get_status`, `list_agents`, `run_agent`, `get_context`, `search_content`, `discover_agents` — data-shaped CRUD that mirrored the backend. Wrong: the user in a foreign LLM does not think about agents, tasks, or files. They think about remembering, recalling, and how their thinking changed. The surface matches the user's grammar, not the database's.

See [tool-contracts.md](tool-contracts.md) for the exact signatures, parameters, return shapes, and the hidden instructions embedded in each tool's description field. See [workflows.md](workflows.md) for end-to-end dynamics, including the cross-LLM continuity case that is the load-bearing narrative for this design. See [architecture.md](architecture.md) for the primitive-level mapping (each tool wraps an existing YARNNN primitive from ADR-168's matrix), cost model, and implementation plan.

---

## Cross-LLM continuity is the product

The single hardest thing foreign-LLM users struggle with is **continuity across LLMs**. A user who:

- Discusses their acquisition strategy with Claude.ai on Monday morning
- Drafts board deck talking points with ChatGPT on Tuesday afternoon
- Brainstorms risks with Gemini on Wednesday evening

currently has three disconnected conversations. Each LLM starts cold. Each one's insights die when the tab closes. The user is the only thread connecting them — and the user has to re-explain the context in every session.

MCP fixes this at the substrate level. Every `remember` call commits immediately to Postgres (the foreign tool never blocks) **and wakes the Reviewer to judge the contribution** against authored ground-truth (eventually-async, ADR-310 D2). Every subsequent `recall` call from any other LLM sees the new material immediately. A user who contributes an insight via ChatGPT at 3pm will find that same insight available to Gemini at 4pm — not because Gemini has a better memory, but because YARNNN is the shared *judged* layer all three LLMs now reach through. Captured instantly; judged shortly after. And because every write is attributed, `trace` lets any LLM show *how* a recorded fact evolved and *who* contributed each version — the provenance no plain memory has.

This is the concrete mechanism under the marketing line. The positioning follows:

> **Install YARNNN on every LLM you use. Whatever you tell one, every other one now knows — and your Reviewer judges each contribution against your own ground-truth before it becomes load-bearing. Your thinking stays coherent across rooms, and no careless write silently corrupts the others.**

---

## The "this" problem and how we handle it

The most important design question is how YARNNN resolves words like **"this"** when the user says "work on this" or "remember this" mid-conversation. The referent lives in the foreign LLM's context window — in the conversation the user has been having — not in the tool call's parameters.

The resolution mechanism has three parts:

1. **Free-form `context` parameter.** Each tool accepts a `context` string the LLM fills at call time. The LLM compresses the recent conversation into one or two sentences and passes it. This is parameter-side work for the LLM, not the user. The user never sees it.

2. **Hidden instruction in the tool description.** Every tool's `description` field explicitly instructs the LLM: *"Before calling, compress what you and the user have been discussing. Do not ask the user for clarification."* The LLM reads descriptions when deciding how to call tools, so this is where the silent conversation-summary mechanic lives.

3. **Empty results are a clean signal, not an error.** When `recall` or `trace` find nothing for a subject, they return an explicit empty result with an explanation ("YARNNN has nothing recorded yet — answer from your own knowledge"), never an error. The host LLM continues naturally. The user's "remember this" with no clear subject still writes — to the `operation/` commons notes — so a save never fails for lack of a scope hint.

The three resolution cases — conversation topic, in-conversation artifact, cold start — plus the new cross-LLM continuity case are walked end-to-end with dialogue examples in [workflows.md](workflows.md).

---

## Strategic positioning

**We are not a storage connector.** Linear, Notion, and GitHub have MCP servers that expose their storage — garbage in, garbage out, no opinion. That is not what YARNNN is.

**We are not passive memory.** ChatGPT Memory and Claude Projects store conversational facts. YARNNN holds substrate under a judgment seat: the Reviewer evaluates what is fit against authored ground-truth, and program activation gives the substrate a mandate. And it remembers *how its thinking changed* — the attributed revision chain `trace` surfaces, which a flat memory cannot. MCP exposes that *judged, historied* substrate as three memory verbs.

**We are the *judged* memory every LLM consults.** YARNNN sits above any single LLM, and MCP is how each LLM reaches up to consult it — and contribute back through a write the Reviewer judges. Cross-LLM consistency is a direct consequence: every LLM pulls from the same Postgres-backed substrate, so what one LLM learns, the others see — and what any LLM contributes is evaluated before it becomes load-bearing. This is a category YARNNN is alone in, because **the copyable part (three MCP verbs) sits downstream of the uncopyable part (a calibrated, persona-bearing judgment seat + an attributed history).** A weekend-clone can copy the verbs; it cannot copy the Reviewer or the provenance.

The one-line pitch to a foreign-LLM user:

> Install this connector on Claude.ai, ChatGPT, and Gemini — every one of them now reaches the same judged substrate, and every one of them can contribute back, with each contribution evaluated by your Reviewer against your own ground-truth. Your thinking stops starting cold every time you switch LLMs, and a careless write from one room doesn't silently corrupt the others.

This positioning holds for every big-player surface and for any future A2A ecosystem. External agents consulting YARNNN on a user's behalf use the same three tools — they don't talk to YARNNN's internal agents, they consult the same workspace every other caller consults.

---

## What's on this page and what isn't

This README is the entry point. It establishes the service philosophy, the three-tool surface, and the strategic framing. The depth lives in the sibling docs:

- **[tool-contracts.md](tool-contracts.md)** — exact signatures, parameter schemas, return shapes, ambiguity payloads, tool-description text (the hidden instructions), and provenance tags
- **[workflows.md](workflows.md)** — dialogue-level walkthroughs: conversation topic, in-conversation artifact, cold start, and cross-LLM continuity (the load-bearing case)
- **[architecture.md](architecture.md)** — primitive mapping to the ADR-168 matrix, backend dispatch through `execute_primitive()`, cost model, implementation plan

**ADR-310** is the governing decision record (superseding ADR-169); this folder is the canonical product framing it references. The ADR captures the decision; these docs capture the feature.

---

## What stays the same from the current MCP implementation

The infrastructure is solid and carries forward unchanged:

- **OAuth 2.1 + static bearer fallback** (ADR-075) — transport auth carries forward
- **FastMCP server + stdio/HTTP transports** — unchanged
- **`api/mcp_server/` module layout** (`server.py`, `auth.py`, `oauth_provider.py`) — module layout unchanged (contents rewritten for ADR-310 D4)
- **Render service** (`yarnnn-mcp-server`) — unchanged

**Changed by ADR-310 D4 (multi-user):** the connector no longer scopes all data to a single boot-time `MCP_USER_ID`. Identity is resolved **per request** from the OAuth access token (`resolve_request_client()` reads the token's `user_id`), so each operator's own LLM authenticates as themselves and reaches their own substrate. `/authorize` requires a real yarnnn login (binding the real Supabase user to the auth code via `GET /api/mcp/oauth-callback`). `MCP_USER_ID` survives only as the stdio / static-bearer fallback. Service-key + explicit `.eq("user_id", …)` still does data isolation — once the real user flows in. **Deferred (Change B, out of scope):** multiple humans sharing ONE workspace — that needs a membership layer and a substrate re-key from `user_id` to `workspace_id`, demand-gated.

What changes is only the **tool surface and the dispatch layer**. The 9 existing tools are deleted as a singular implementation; the 3 new tools replace them. The MCP server becomes a thin caller of `execute_primitive()` per the ADR-164 runtime-agnostic principle — no more direct service imports in `server.py`.

---

## Decisions (ADR-169 → superseded by ADR-310)

> **ADR-368 supersession (2026-06-25):** the *tool names* below (`remember_this` / `pull_context` / `work_on_this`) are the ADR-169 originals, retained here as historical trace. The live surface is `remember` / `recall` / `trace` (ADR-368). The decisions' *substance* — judged write, attributed provenance, ranking validation, rate cap — carries forward unchanged onto the new verbs. The write path no longer routes a five-target enum; it writes the `operation/` commons only (ADR-368 D3).

The original four ADR-169 decisions are preserved below for trace continuity. The load-bearing one — write safety — was **superseded by ADR-310 D2**: pre-write gating is replaced not by three post-write visibility mechanisms but by **the Reviewer judging every foreign write** (eventually-async). Note also that the post-ADR-235 write path uses `WriteFile` / `InferContext`, not the `UpdateContext` six-target model the original text assumed; `deliverable` is no longer a target.

1. **`remember_this` safety — ADR-310 D2 (judged write).** A foreign-LLM write commits immediately (never blocks the tool) and then wakes the Reviewer via the `substrate_event` source (ADR-296) to evaluate the contribution against authored ground-truth. Foreignness is carried in the wake's `hook.prompt` (ADR-310 D3); the author is also stamped on the revision (`authored_by="yarnnn:mcp"`, ADR-288). Provenance stamping (`source: mcp:<client>`, ADR-162) and confident-routing-or-structured-ambiguity classification still apply as supporting mechanisms — but the *judgment* of fitness is the Reviewer's, not a post-hoc daily-briefing glance. _(Original ADR-169 text: "all six targets available; safety shifts to classification + provenance + daily-update surfacing." That visibility-only model is superseded.)_

2. **Provenance display in the daily-update — DECIDED: yes, attributed.** The daily-update task pipeline groups recent workspace changes by provenance source. MCP-contributed content is surfaced with attribution ("From your Claude.ai conversation yesterday: ..."). This closes the loop visibly across the cross-LLM boundary and makes wrong writes correctable by the user the morning after they happen.

3. **`QueryKnowledge` ranking quality — DECIDED: pre-ship validation gate.** Implementation happens first; validation against 10 real seeded subjects before merge. If ranking is insufficient, the fix is embedding-based reranking (zero-cost, deterministic) — or, as a fallback, a Haiku reranker (~$0.0005/call, still deterministic from the user's perspective). Ship only after eyeball validation passes. This is the one explicit quality gate on the implementation and is called out in [architecture.md](architecture.md).

4. **Rate limiting — DECIDED: 1000 calls/day/user, unified cap.** Shared across all MCP clients registered to a single user (Claude.ai + ChatGPT + Gemini counted together). No Free/Pro tier differentiation on MCP calls because per-call cost is ~$0. Basic abuse prevention only.

### Resolved from prior drafts

- **Per-call cost** — effectively zero for all three tools; no Haiku composition in the serving path
- **Work budget accounting** — MCP calls do not consume work units (ADR-120) because they don't spend meaningful compute
- **Tier differentiation on MCP** — none; the value of MCP scales cross-LLM, not per-call

ADR-169 is now a pure decision record with no deferred items. Implementation can proceed immediately after the ADR is written: rewrite `api/mcp_server/server.py`, add the three new tool handlers as thin wrappers over existing primitives, update the Render service instructions, delete the legacy tools, update `CLAUDE.md` file locations, ship.
