# The multi-LLM audit — what is actually model-agnostic, and what the lineup should be

**Status**: Audit + direction. **Doc-first — no code in this pass.** The operator's cut: *"existing tool configs and agents configs have not really been streamlined towards the multi-LLM consideration… most likely we have remnants of a single-llm model with lite-llm considerations and need a more model agnostic approach in terms of architecture. THAN, after that, the actual wiring per agent may in fact be biased."*
**Date**: 2026-07-16
**Relates to**: ADR-402 (model routing as kernel data) · ADR-408 D4 (the LiteLLM router) · ADR-411 D5 (`LANE_MODELS`) · ADR-460 (one Agent concept, independent facts) · ADR-045 (WebSearch) · ADR-307 (the one consequential gate) · ADR-417 (the render service is gone)

---

## 1. The assumption, checked

The operator's read was **confirmed, with one correction that makes it sharper**.

**Confirmed**: the architecture is agnostic; the *code* is not. `services/model_router.py::route_completion` is genuinely provider-blind — LiteLLM lib-mode, OpenAI-shape messages in, translated per provider, `anthropic/…` · `openai/…` · `gemini/…` · `deepseek/…` all real. That work is done and it is good.

**But almost nothing uses it.**

| Path | Modules | Agnostic? |
|---|---|---|
| `route_completion` (LiteLLM) | `lane_runner` · `settle` · `session_continuity` | ✅ |
| `services/anthropic.py` (direct SDK) | `freddie_agent` · `dispatch_specialist` · `web_search` · `wake_evaluation` · `harvest` · `context_inference` · `recurrence_prompt_inference` · `repurpose` | ❌ |

**3 route. 8 bypass.** The router is a road built beside a town that still walks.

**The correction to the framing**: this is not "remnants of a single-LLM era" in the sense of *forgotten* code. It is **the chat lane being the only thing ever built on the router**. The router arrived with ADR-408 D4 *for lanes*; everything older kept its direct Anthropic call, and nothing since has been migrated. The drift is not decay — it is a migration that was never declared.

## 2. The receipt that proves the ceiling — ADR-402's table cannot name a foreign model

The sharpest single finding. `services/model_routing.py` (ADR-402 — "model routing is kernel data, not identity") is the kernel's model-selection table:

```python
DEFAULT_ROUTES: dict[str, ModelRoute] = {
    SHAPE_ADDRESSED:  ModelRoute(model="claude-sonnet-4-6", max_rounds=20),
    SHAPE_PROPOSAL:   ModelRoute(model="claude-sonnet-4-6", max_rounds=20),
    SHAPE_RECURRENCE: ModelRoute(model="claude-sonnet-4-6", max_rounds=20),
}
```

Every value is a **bare Anthropic model id — no provider prefix**. The router's own docstring says: *"Bare names rely on LiteLLM's inference map — **pass the prefix**."*

So the module named "model routing," whose ADR says *routing is kernel data*, **structurally cannot express a non-Anthropic route**. `YARNNN_MODEL_ADDRESSED=gemini/gemini-2.5-pro` would be read from env, handed to `chat_completion_with_tools`, and hit the Anthropic SDK. The dial exists; the wire behind it goes one place.

**Two modules, ~one letter apart, doing different jobs:**
- `model_router.py` (18KB) — the provider-blind LiteLLM transport. **How to call any model.**
- `model_routing.py` (6KB) — ADR-402's Freddie shape→model table. **Which model for which wake.**

They should compose (`routing` picks, `router` calls). They don't touch. A session reading either name will guess wrong about the other; the near-collision is itself a finding.

## 3. `WebSearch` is the case in point

The operator: *"websearch shouldn't be anthropic only."* Correct, and it is worse than a preference:

- `web_search.py` calls `get_anthropic_client()` and hardcodes `model="claude-haiku-4-5-20251001"` — it uses **Anthropic's server-side `web_search` tool**, a vendor-native capability with no LiteLLM equivalent.
- So "give Scout web search" means: **Gemini calls a Claude subprocess to search.** That is not fatal — it is a legitimate *hosted-capability* pattern — but it must be a decision, not a discovery.

**The real cut this exposes** — a taxonomy the codebase does not have yet:

| Class | Example | Agnostic? |
|---|---|---|
| **Transport** | "complete this with tools" | ✅ LiteLLM — genuinely fungible |
| **Vendor-hosted capability** | Anthropic `web_search`, OpenAI image gen, Gemini long-context | ❌ **Inherently vendor-bound** |
| **Our own primitives** | the five file verbs, `QueryKnowledge` | ✅ ours, provider-irrelevant |

**Model-agnostic does not mean vendor-capability-free.** It means: *the agent asks for a capability; the kernel decides which vendor serves it.* A search is a search — Anthropic's tool, Gemini grounding, or Brave/Tavily behind our own primitive. The **agent must never know**. Today `WebSearch` IS "Anthropic's web_search" rather than "search, currently served by Anthropic," and that conflation is the bug — not the Anthropic dependency itself.

## 4. The lineup — and why the roster is not the problem

The operator's read (*"they're ONLY centered around reasoning"*) is **mostly right, and undersells it**: every Agent has `WriteFile`/`EditFile`. They reason **over your files, and they make things**. That is the moat, not a gap.

The real finding is one layer down:

> **`LANE_TOOL_NAMES` is five file verbs. Uniform. For every Agent.**

And two implemented primitives sit unreachable:

| Primitive | State | Reachable by an Agent? |
|---|---|---|
| `QueryKnowledge` | **Real** — semantic/vector recall over `operation/` | ❌ |
| `WebSearch` | **Real** — ADR-045 | ❌ |

Both are classed **non-consequential reads** in `permission.py` — the same safety class as `ReadFile`, which lanes already have. **They are withheld by an allowlist, not by a gate.**

**Consequences worth stating plainly:**

1. **Scout is currently a lie.** Its blurb promises *"digs through material fast — lookups, quick reads"*; its posture says *"say 'not here' rather than guessing."* Scout has **no semantic search** — only `SearchFiles` (exact) and `ListFiles`. A researcher with no research tools, doing grep and calling it digging.
2. **`recall` is shipped to strangers and withheld from ourselves.** ADR-368 serves semantic recall over MCP to ChatGPT and Claude. **External LLMs can semantically search the workspace; our own Agents cannot.** That is backwards on the moat's own terms.
3. **A fifth character changes nothing** while every Agent has identical hands. The lineup question is downstream of the tools question.

**The registry's own comment already named the trigger:**

> `tools` is deliberately absent in v1: every lane gets the same five file verbs, and a per-Agent tool scope with **exactly one possible value is a field that lies about being a choice. It lands when a second value exists.**

**A second value now exists.**

## 5. The three tiers — and where the cliff is

The operator's *"tooling and connection considerations"* resolves into three tiers with **very different clocks** (the ADR-380 D2 test: what kind of time does this ship on?):

| Tier | Content | Clock | Gate |
|---|---|---|---|
| **1 — Reads** | `QueryKnowledge` · `WebSearch` | **Engineering time** | none — already non-consequential |
| **2 — Skills** | authoring/rendering capability | Blocked: **machinery is DEAD** (ADR-417 killed the render service) | n/a — a spec, not a field |
| **3 — Connections** | Slack/Notion/GitHub | **The cliff** | **ADR-307** |

**Tier 3 is where the operator's instinct gets sharp, and it splits:**
- A connection that **reads** (sync into substrate) is a **peripheral** — ADR-401's driver, mechanical, no judgment.
- A connection that **writes outward** (post to Slack, update Notion) **IS consequential external action** — the one fact that is not a dial (ADR-460 D3).

So "give an Agent a Slack connection" is **two different asks wearing one word**. The read half is Tier 1's cousin. The write half is the Rung-2 cliff arriving through a tools list — *exactly* the back door ADR-460 D3.a made structural in the registry row. **The `tools` field must never be able to express an outward write.** If it can, the cliff is reopened by config.

## 6. Direction (not a build order — this wants operator sign-off)

**Phase 0 — the honest name.** `model_routing.py` values gain provider prefixes (`anthropic/claude-sonnet-4-6`) and flow through `route_completion`. Byte-identical behavior at N=1 (LiteLLM routes the same model to the same vendor); it makes the ADR-402 dial *real*. Fold or rename the two `model_rout*` modules so their jobs are legible.

**Phase 1 — capability, not vendor.** `WebSearch` stops meaning "Anthropic's web_search" and starts meaning "search." One resolver decides who serves it. The agent never knows. (Whether the server is Anthropic-hosted, Gemini grounding, or our own Brave/Tavily call is a kernel decision — and a cost decision.)

**Phase 2 — `tools` becomes a field.** Sonnet/Critic keep the five verbs. **Scout gains `QueryKnowledge` + `WebSearch` and stops lying.** Designer keeps making. The differentiator moves from *posture-only* to *posture + reach* — which is what makes four characters genuinely four things rather than four prompts.
> ⚠️ The field's range is **reads and our own primitives ONLY**. An outward write is not a tool scope; it is the ADR-307 gate. Gate this the way D3.a is gated.

**Phase 3 — the biased wiring** (the operator's *"sonnet for reasoning, gemini for image making, something else for reasoning + web search"*). **This is the last step, not the first** — and it only becomes expressible once Phase 0 lands, because today the selection table cannot name a foreign model. Note honestly: Sonnet and Designer share `claude-sonnet-4-6` today, so the "one Agent per vendor" framing is already not what the roster does; per-Agent engine choice should follow **evidence of a real difference in output**, not vendor-symmetry.

**Deliberately NOT in scope**: the roster's size. Four characters over a uniform tool surface is a coherent base set; adding a fifth before Phase 2 would be four prompts wearing five names.

## 7. One-line statement

**The router is genuinely provider-blind and almost nothing uses it — 3 modules route, 8 call Anthropic directly, and ADR-402's own model-selection table holds bare Anthropic ids it cannot prefix, so the "model routing is kernel data" dial goes exactly one place; the fix is to separate *capability* from *vendor* (a search is a search; Anthropic merely serves it today), and only then does per-Agent wiring become expressible — at which point the real prize is not a fifth character but `tools` becoming a field, so Scout can finally do the digging its blurb already promises, with the hard line that a tools list may express reads and our own primitives and never an outward write, because that is the cliff, not a scope.**
