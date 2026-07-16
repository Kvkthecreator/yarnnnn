# ADR-463 — Capability, not Vendor: the model-agnostic carve

> **Status**: **Accepted** (2026-07-16, operator-ratified). Implemented in phases P0–P2 (see §9); P3 is direction, gated on evidence.
> **Date**: 2026-07-16
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Mechanism** (Axiom 5 — which engine serves a capability) with a **Substrate** consequence (the tool surface an Agent reaches). The correction is Axiom-0-shaped: a single name (`WebSearch`) currently spans *capability* and *vendor*, and the fix is to cleave it.

**Amends**:
- [ADR-402](ADR-402-model-routing-as-kernel-data.md) — the routing table's values gain provider prefixes and flow through the ADR-408 D4 router. ADR-402's claim ("model routing is kernel **data**, not identity") is **preserved and made true**: the table currently holds bare Anthropic ids it cannot prefix, so the dial it defines has exactly one reachable position (§2).
- [ADR-411](ADR-411-chat-lanes-and-the-lane-tool-surface.md) **D3** — `LANE_TOOL_NAMES` stops being a constant and becomes a per-Agent resolution. D3's *load-bearing* claim (a lane is hands on the filesystem; no entity verbs, no Schedule, no platform tools) is **preserved and tightened** into a hard invariant (§5).
- [ADR-045](ADR-045-web-search.md) — `WebSearch` is re-read as *a capability the kernel resolves*, not *Anthropic's `web_search` tool*.

**Preserves** (load-bearing, untouched): ADR-307 (the one consequential gate — this ADR **strengthens** it, §5), ADR-460 D3.a (authority is unrepresentable — extended to the `tools` field), ADR-363 (Freddie's prompt-cache economics — the reason Freddie does NOT migrate, §4), ADR-439 (BYOK), ADR-396 (one meter), ADR-408 D4 (the router).

---

## 1. Context — the operator's read, checked

> *"existing tool configs and agents configs have not really been streamlined towards the multi-LLM consideration… most likely we have remnants of a single-llm model with lite-llm considerations and need a more model agnostic approach in terms of architecture. THAN, after that, the actual wiring per agent may in fact be biased."*

Confirmed by audit (`docs/analysis/multi-llm-audit-and-the-agent-lineup-2026-07-16.md`), with one correction that sharpens it.

**The architecture is agnostic. The code is not.** `services/model_router.py::route_completion` is genuinely provider-blind — LiteLLM lib-mode, OpenAI-shape messages, tool calls normalized, streaming-with-tools supported. **3 modules route; 8 call Anthropic directly.**

**The correction**: this is not decay. The router arrived with ADR-408 D4 **for lanes**, and nothing older was migrated. It is **a migration that was never declared** — so the remedy is a decision, not a cleanup.

## 2. D1 — The routing table must be able to name a foreign model

The sharpest receipt. `services/model_routing.py` — the module ADR-402 created to make routing *kernel data*:

```python
DEFAULT_ROUTES = {
    SHAPE_ADDRESSED:  ModelRoute(model="claude-sonnet-4-6", max_rounds=20),
    ...
}
```

Bare Anthropic ids. No provider prefix. The router's own docstring: *"Bare names rely on LiteLLM's inference map — **pass the prefix**."*

**A dial whose every position is the same vendor is not a dial.** `YARNNN_MODEL_ADDRESSED=gemini/gemini-2.5-pro` would be read from env and handed to the Anthropic SDK.

**Decision**: routing-table values carry provider prefixes (`anthropic/claude-sonnet-4-6`). At N=1 this is byte-identical — LiteLLM routes the same model to the same vendor — but the dial becomes real.

**D1.a — the two modules.** `model_router.py` (transport: *how to call any model*) and `model_routing.py` (selection: *which model for which wake*) are one letter apart and never touch. They **compose** — selection picks, transport calls — and the names must say so. `model_routing.py` → **`services/model_selection.py`**; a session reading either name now guesses right.

## 3. D2 — Capability is not vendor

`WebSearch` calls `get_anthropic_client()` and hardcodes `claude-haiku-4-5-20251001`, because it uses **Anthropic's server-side `web_search` tool** — a vendor-native capability with no LiteLLM equivalent.

So "give Scout web search" means **Gemini calls a Claude subprocess to search**. That is a legitimate *hosted-capability* pattern; it must be a **decision**, not a discovery.

**The taxonomy the codebase lacks:**

| Class | Example | Fungible? |
|---|---|---|
| **Transport** | "complete this with tools" | ✅ LiteLLM |
| **Vendor-hosted capability** | Anthropic `web_search`, OpenAI image gen | ❌ inherently bound |
| **Our own primitives** | the five file verbs, `QueryKnowledge` | ✅ provider-irrelevant |

**Model-agnostic does not mean vendor-capability-free.** It means: *the agent asks for a capability; the kernel decides who serves it.* Today `WebSearch` **IS** "Anthropic's web_search" rather than "search, currently served by Anthropic." **That conflation is the bug — not the Anthropic dependency.**

**Decision**: `WebSearch` gains a **server** indirection (`services/capabilities.py`). The primitive asks for search; a kernel resolver names the server. The agent never knows, and swapping in Gemini grounding or a Brave/Tavily call is a kernel edit, not an agent change.

## 4. D3 — What does NOT migrate, and why (the honest boundary)

**Freddie stays on the direct Anthropic path. This is a decision, not debt.**

`freddie_agent.py` uses two Anthropic-exclusive features:
- `cache_control: {"type": "ephemeral"}` — prompt caching. The governance prefix is cached at every wake; the module's own comment says the saving *"accrues as platform margin"* (ADR-363).
- `context_management` / `clear_tool_uses_20250919` — beta tool-history clearing.

**The router carries neither** (`grep -c cache_control services/model_router.py` → **0**). Routing Freddie today would **silently drop prompt caching** — a cost regression disguised as an architecture win, on the system's most frequent LLM call.

**The rule this establishes**: *a caller migrates when the router can serve it without loss.* Not before. Migration is not a virtue in itself; **an un-migrated caller with a stated reason is not debt — an un-migrated caller with no reason is.**

**Ledger of the 8 direct callers:**

| Module | Verdict |
|---|---|
| `web_search` | **Migrates** via the capability server (§3) — it is the ADR's subject |
| `wake_evaluation` · `context_inference` · `harvest` · `recurrence_prompt_inference` · `repurpose` · `dispatch_specialist` | **Migrate** — plain completions, no vendor-exclusive features |
| `freddie_agent` | **STAYS** — prompt caching + context-management (above). Revisit iff the router grows pass-through. |

## 5. D4 — `tools` becomes a field, with a hard ceiling

`LANE_TOOL_NAMES` is five file verbs, **uniform for every Agent**. Meanwhile two primitives sit implemented and unreachable, both classed **non-consequential reads** in `permission.py` — the same class as `ReadFile`, which lanes already have:

- **`QueryKnowledge`** — semantic/vector recall over `operation/`
- **`WebSearch`** — ADR-045

**Two consequences state the case:**
1. **Scout is a lie.** Its blurb promises *"digs through material fast"*; it has only `SearchFiles` (exact) and `ListFiles`. A researcher with no research tools, doing grep and calling it digging.
2. **`recall` is shipped to strangers and withheld from ourselves.** ADR-368 serves semantic recall over MCP to ChatGPT and Claude. **External LLMs can semantically search the workspace; our own Agents cannot.** Backwards on the moat's own terms.

The registry already named the trigger: *"a per-Agent tool scope with exactly one possible value is a field that lies about being a choice. **It lands when a second value exists.**"* It does now.

**Decision**: `tools` becomes an optional `KERNEL_AGENTS` key. Absent → the five file verbs (every existing Agent, byte-identical). Scout gains `QueryKnowledge` + `WebSearch`.

**⚠️ D4.a — THE CEILING, MADE STRUCTURAL (the ADR-460 D3.a pattern, second instance).**

> **A `tools` value may name ONLY a primitive that `permission.py` classes non-consequential.** Reads and our own primitives. **Never an outward write.**

This is not a style rule. "Give an Agent a Slack connection" is **two asks wearing one word**:
- a connection that **reads** (sync into substrate) is an ADR-401 **peripheral** — mechanical, no judgment;
- a connection that **writes outward** (post to Slack, update Notion) **IS consequential external action** — the one fact that is not a dial (ADR-460 D3).

An outward write reachable from a `tools` list is **the Rung-2 cliff arriving through config** — the exact back door ADR-460 D3.a closed in the row shape, reopened one field over. So the ceiling is enforced **at resolution time against `permission.py`'s own classification** (not a hand-maintained deny-list that would drift), and gated. **A session that puts a consequential primitive in a `tools` list has violated this ADR.**

## 6. D5 — Per-Agent engine wiring is LAST, and follows evidence

The operator's *"sonnet for reasoning, gemini for image making, something else for reasoning + web search"* is the right end-state and the **wrong next step** — today the selection table cannot even name a foreign model (§2). It becomes expressible after P0.

Two honesty notes carried rather than papered over:
- **Sonnet and Designer already share `claude-sonnet-4-6`.** The roster is not "one Agent per vendor" and never was. Per-Agent engine choice should follow **evidence of a real output difference**, not vendor symmetry.
- **Image generation does not exist.** ADR-417 decommissioned the render service; `RuntimeDispatch` is deleted. "Gemini for image making" is a **capability that must be built** (a vendor-hosted capability under §3's resolver), not a wiring change.

## 7. What this ADR does NOT do

- **It does not migrate Freddie** (§4) or add cache pass-through to the router.
- **It does not change the roster's size** — four characters over a now-differentiated tool surface. A fifth before D4 would be four prompts wearing five names.
- **It does not move the ADR-307 gate**, weaken the witness dial, or make any Agent consequential (D4.a makes that *unrepresentable* in `tools`).
- **It does not build image generation** (§6) or per-Agent engine bias (D5).
- **It adds no schema, no migration, no env var.**

## 8. Consequences

- **The ADR-402 dial becomes real** — a foreign model is nameable for the first time.
- **Scout stops lying**, and the moat's own recall serves the moat's own agents.
- **One capability seam** replaces a vendor name baked into a primitive.
- **The cliff gains a second structural guard** — D3.a in the row, D4.a in the field. Both enforced by ratchet, not prose.
- **The risk, named**: `tools` is a new surface, and a future session will want to put something consequential in it. D4.a's resolution-time check against `permission.py` is the mitigation, and it is structural. *A deny-list would drift; a derivation cannot.*

## 9. Sequencing

1. **P0 — the dial is real.** Prefix `DEFAULT_ROUTES`; `model_routing.py` → `model_selection.py`; selection composes with transport.
2. **P1 — capability, not vendor.** `services/capabilities.py` resolves search → a server. `WebSearch` asks for search.
3. **P2 — `tools` is a field.** Scout gains `QueryKnowledge` + `WebSearch`. D4.a gated.
4. **P3 — the biased wiring.** Direction only; **gated on evidence** of a real per-Agent output difference (§6).

Cleanup ships **inside** each phase, never after (Singular Implementation): the migrated caller's direct import is **deleted in the same commit**, not left beside its replacement.

## 10. One-line statement

**The router is genuinely provider-blind and almost nothing uses it — so the fix is not "use LiteLLM everywhere" (Freddie's prompt caching would silently die) but to cleave *capability* from *vendor*: the agent asks for search, the kernel names the server, the routing table can finally spell a foreign model, and `tools` becomes the field that lets Scout do the digging its blurb already promises — with the hard ceiling, enforced against `permission.py`'s own classification rather than a drifting deny-list, that a tools list may name reads and our own primitives and never an outward write, because that is the cliff, not a scope.**
