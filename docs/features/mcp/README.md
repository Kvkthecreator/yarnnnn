# MCP Connector — The Shared Attributed Workspace, Reached From Any LLM

> **Status**: Implemented. **Strategic framing** governed by **ADR-310** (judged
> substrate, interop as distribution face — one moat, two faces). **Tool surface**
> governed by **[ADR-543](../../adr/ADR-543-the-interop-surface-speaks-the-kernel-verbs.md)
> (2026-08-10)**: the surface is **file-native, in full** — every verb a binding of a
> kernel verb (ADR-512 D3), the memory ontology (`remember`/`recall`/`trace`, the
> ADR-169→368 strata) retired without aliases. Server-side composition and the
> round-budget constraint (ADR-368 Correction 1) carry forward unchanged. ADR-075's
> OAuth/transport infrastructure is preserved. The connector is **multi-user**
> (per-request OAuth identity, ADR-310 D4).
> **Updated**: 2026-08-10 (ADR-543 file-native re-cut + ADR-545 binding completion — edit/delete/move, the change feed, the honest save)
> **Authors**: KVK, Claude
> **Related ADRs**: **ADR-543** (file-native surface — governing the verbs),
> **ADR-512** (the file is the unit of interop — the contract), **ADR-310** (judged
> substrate / interop face — the framing), ADR-533 (one participant contract),
> ADR-368 (server-side composition — superseded at the verb layer, Correction 1
> retained), ADR-320/366 (the permission topology the write surface gates against),
> ADR-075 (OAuth + transport — preserved), ADR-209 (authored substrate — the chain
> `history` surfaces), ADR-448 (the `derived_from` reference edge)

---

## What MCP is for YARNNN

**MCP is the interop face of YARNNN's one moat: a judged context substrate, served everywhere.**

YARNNN has exactly one moat — authored substrate under a persona-bearing judgment seat. That moat is exposed through two faces (ADR-310): the **cockpit** (the operator, in-app) and the **interop face** (a foreign LLM, via MCP). MCP is not a second product. It is how the shared, attributed workspace reaches the LLMs the operator already uses.

Operators spend their thinking time inside Claude.ai, ChatGPT, Gemini, and other foreign LLM surfaces — often several in a day. Each LLM starts cold; each conversation's conclusions die in that surface. MCP connects each foreign LLM to a single shared workspace. Every LLM reads the same files; every LLM writes attributed revisions beside every human change.

What crosses the boundary is **the kernel's own verb contract** (ADR-512 D3), served compound:

| Intent | Verb | What it does |
|---|---|---|
| **"Look at this doc."** | `open` | The exact-version read: content + who last changed it + recent attributed revisions. |
| **"What's in my workspace?"** | `list` | Enumerate a folder (or the whole tree) — every file with who last touched it and when. |
| **"Find what I have on ___."** | `search` | Ranked paths + excerpts + an honest `confidence` signal. YARNNN returns; the host explains. |
| **"Save that back."** | `save` | A whole-file attributed revision, with read-before-write CAS, `derived_from` citations, and the large-file honesty guard. |
| **"Change this part."** | `edit` | The anchored write — only the change travels, so truncated reads can't destroy what they never saw. |
| **"Get rid of this." / "Rename it."** | `delete` / `move` | The tidy verbs — attributed tombstones, chain retained, restore possible. The tree stops being grow-only. |
| **"What moved since yesterday?"** | `list(since=…)` | The change feed — asynchronous multi-principal coordination in one call. |
| **"How did this change?"** | `history` | The authored revision chain of one exact file — who, when, what, with diffs and cited sources. |
| **"Share this with my team."** | `share` | Mint a member/viewer link; the host relays it. |

That's the entire MCP surface. No `list_agents`, no `run_task`, no separate "memory" object — the workspace **is** the memory, and files at paths are its only ontology (ADR-543 D1). Exact signatures: [tool-contracts.md](tool-contracts.md).

### The singular framing

> A storage connector returns whatever is stored — garbage in, garbage out, no opinion, no history. YARNNN is the system of record where human and AI work accrues: every change signed by whoever made it, every file's lineage walkable, nothing lost. The copyable half (nine thin verbs) sits downstream of the uncopyable half (an attributed, judged history). **YARNNN is the shared workspace every LLM works in — not a memory bolted onto one of them.**

---

## Why composed verbs, not raw primitives

ADR-311 proposed exposing the kernel's file primitives directly (`ReadFile` / `SearchFiles` / `WriteFile` / `ListRevisions`) and letting the host LLM compose intent by chaining them — the Claude Code model. ADR-368 Correction 1 (retained by ADR-543): claude.ai / ChatGPT / Gemini connectors are *consumer chat* hosts that execute only ~3–5 tool rounds per turn. A read that *requires* the host to chain `Search → Read → Read → synthesize` burns the round budget fetching and stalls. So **the multi-step composition lives server-side**: `open` bundles content + attribution + revisions; `history` bundles the chain + diffs + cited sources' chains; each returns a reason-ready result in **one round**. There is no second vocabulary: the verbs ARE the kernel contract, served compound (ADR-512 D3 Layer 2 — compounds compose contract objects and say so).

**Why `search` returns rather than explains.** (1) **cross-LLM consistency** — an internal composition step returns different answers by timing/temperature/model; every LLM must see the same substrate. (2) **the host LLM synthesizes better** — it has the user's conversation, tone, and framing; YARNNN has only the files. (3) **clarity of role** — YARNNN is the workspace, not the agent in the conversation ([honest-state-contract.md](honest-state-contract.md)).

**Why exact and fuzzy are separate verbs.** `open`/`history` never guess — a miss is `found: false`. `search` is the only fuzzy verb and says how sure it is. `list` closes the loop: an external principal can *enumerate* the tree instead of inferring it from search hits (the 2026-08-10 external-audit finding that precipitated ADR-543 — the pre-543 surface had no enumeration verb at all, so a connected LLM reconstructed the tree from semantic hits and said so: "it's inferred, not listed").

---

## Cross-LLM continuity is the product

A user who discusses acquisition strategy with Claude.ai on Monday, drafts board-deck talking points with ChatGPT on Tuesday, and brainstorms risks with Gemini on Wednesday currently has three disconnected conversations. Each LLM starts cold; each one's insights die when the tab closes.

MCP fixes this at the substrate level. Every `save` commits immediately to the workspace ledger, attributed to the calling LLM. Every subsequent `open`/`list`/`search` from any other LLM sees the material at once. And because every write is attributed, `history` lets any LLM show *how* a file evolved and *who* contributed each version — the provenance no flat memory has.

> **Install YARNNN on every LLM you use. They all work in the same workspace — every change signed by whoever made it, human or AI, and nothing lost.** Your thinking stops starting cold every time you switch rooms.

Ambient capture survives the re-cut as a *taught behavior*, not a verb: the connector instructions tell the host to save conversational conclusions worth keeping — by meaning, like any participant; an observation with no better home goes under Downloads. The write is an ordinary attributed `save`.

---

## Strategic positioning

**We are not a storage connector.** Linear, Notion, and GitHub have MCP servers that expose their storage — no attribution, no walkable lineage, no opinion.

**We are not passive memory.** ChatGPT Memory and Claude Projects store conversational facts inside one vendor's walls. YARNNN is the vendor-neutral system of record: a shared filesystem where every principal — the operator, teammates, every connected AI — works under its own grant, signed on every change. It remembers *how the work changed* — the attributed revision chain `history` surfaces, which a flat memory cannot.

The one-line pitch to a foreign-LLM user:

> Install this connector on Claude.ai, ChatGPT, and Gemini — every one of them now works in the same attributed workspace. What one writes, the others see; who wrote what is never lost; and your team can be let in with one link.

---

## What's on this page and what isn't

This README is the entry point. The depth lives in the sibling docs:

- **[tool-contracts.md](tool-contracts.md)** — exact signatures, parameter schemas, return shapes, the reference grammar, contract semantics
- **[workflows.md](workflows.md)** — dialogue-level walkthroughs, including the cross-LLM continuity case
- **[architecture.md](architecture.md)** — primitive mapping, backend dispatch through `execute_primitive()`, cost model
- **[presentation.md](presentation.md)** — rich rendering on the interop face (ADR-372): how a widget-rendering host (ChatGPT/Apps SDK) gets an interactive view of the *same returned substrate*, text-default always preserved
- **[CONNECTING.md](CONNECTING.md)** — connecting each host, and the stale-manifest reconnect step (load-bearing after any verb change — ADR-533 §13)
- **[SUBMISSION.md](SUBMISSION.md)** — the ChatGPT App-directory submission playbook
- **[honest-state-contract.md](honest-state-contract.md)** — how every tool reports uncertainty to the host

---

## Infrastructure (unchanged by the verb re-cuts)

- **OAuth 2.1 + static bearer fallback** (ADR-075) — transport auth
- **FastMCP server + stdio/HTTP transports**; served at the domain root (ADR-370)
- **`api/mcp_server/` module layout** (`server.py`, `auth.py`, `oauth_provider.py`, `presentation/`, `widgets/`)
- **Render service** (`yarnnn-mcp-server`) — deploys from `main`
- **Multi-user identity** (ADR-310 D4): resolved per request from the OAuth access token; `MCP_USER_ID` survives only as the stdio / static-bearer fallback
- **Attribution** (ADR-288): every MCP write lands `authored_by="yarnnn:mcp:{client}"` — the room is named, not just "an MCP write"
- **Rate cap**: 1000 calls/day/user, unified across all of a user's connected hosts; per-call cost ≈ $0 (zero YARNNN-side LLM calls on the serving path)
