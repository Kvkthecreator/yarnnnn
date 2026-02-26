# ADR-081: Execution Path Consolidation

**Status:** Implemented
**Date:** 2026-02-26
**Amends:** ADR-080 (Unified Agent Modes) — extends headless mode scope to cover research execution
**Supersedes:** ADR-045 Phases 2-4 (ResearcherAgent, subagent orchestration) — absorbed into unified agent
**Related:**
- [ADR-042: Deliverable Execution Simplification](ADR-042-deliverable-execution-simplification.md)
- [ADR-044: Deliverable Type Reconceptualization](ADR-044-deliverable-type-reconceptualization.md)
- [ADR-045: Deliverable Orchestration Redesign](ADR-045-deliverable-orchestration-redesign.md)
- [ADR-080: Unified Agent with Chat and Headless Modes](ADR-080-unified-agent-modes.md)

---

## Context

### ADR-080 was incomplete

ADR-080 introduced headless mode: `generate_draft_inline()` uses `chat_completion_with_tools()` with 5 read-only primitives and max 3 tool rounds. The decision was framed as "one agent, two modes" — chat and headless share the same primitive registry.

**What the analysis missed:** The codebase has not two but **four independent agentic loops** with tool use:

| Loop | File | LLM call | Tools | Max rounds | Purpose |
|------|------|----------|-------|------------|---------|
| 1. TP Chat | `thinking_partner.py` | `chat_completion_stream_with_tools()` | 12 primitives + platform tools | 15 | User conversation |
| 2. Web Research | `web_research.py` | `client.messages.create()` | `web_search_20250305` (server tool) | 5 searches | Context gathering for research deliverables |
| 3. Headless Gen | `deliverable_execution.py` | `chat_completion_with_tools()` | 5 read-only primitives | 3 | Content generation |
| 4. WebSearch Primitive | `primitives/web_search.py` | `client.messages.create()` | `web_search_20250305` (server tool) | multi-turn continuation | Single web search per invocation |

Loops 2 and 4 are nearly identical implementations — both create a Claude call with `web_search_20250305`, both handle multi-turn continuations, both return synthesized results. Loop 2 runs during strategy execution (step 4); Loop 4 runs when the headless agent (Loop 3) or TP (Loop 1) calls the `WebSearch` primitive. Neither was accounted for in ADR-080's "one agent, two modes" framing.

Loop 2 was written for ADR-045 Phase 2 as a standalone context-gathering agent. Loop 4 was written as a primitive for TP. Both predate the unified agent concept.

### The problem this creates

**Research-type deliverables make 2 separate agentic LLM calls** — one in `ResearchStrategy.gather_context()` (via `web_research.py`) and another in `generate_draft_inline()` (headless mode). The web research results get serialized into the prompt as `[WEB RESEARCH]` text, then the headless agent generates content on top of it. The headless agent also has a `WebSearch` primitive it could use, but never does because the research is already done.

This means:
1. **Duplicated capability** — WebSearch primitive in headless mode and `web_search_20250305` in web_research.py do the same thing through different mechanisms
2. **Context loss** — web research results are flattened to text before the generation agent sees them. The generating LLM can't follow up on research findings or ask clarifying searches
3. **No unified observability** — research tool usage and headless tool usage are logged in different systems with different formats
4. **Unnecessary architectural complexity** — `web_research.py` is a 200-line agentic loop that reimplements what headless mode already provides, just at a different pipeline stage

### Full LLM call audit

For completeness, here are ALL 8 LLM call sites in YARNNN:

| # | Path | Function | Tools | Rounds | Model | Agentic? |
|---|------|----------|-------|--------|-------|----------|
| 1 | TP Chat | `chat_completion_stream_with_tools()` | 12+ primitives | 15 | Sonnet | Yes |
| 2 | Headless Gen | `chat_completion_with_tools()` | 5 primitives | 3 | Sonnet | Yes |
| 3 | Web Research (strategy) | `client.messages.create()` | web_search (server) | 5 | Sonnet | Yes |
| 4 | WebSearch Primitive | `client.messages.create()` | web_search (server) | multi-turn | Sonnet | Yes |
| 5 | Signal Processing | `chat_completion()` | None | 1 | Haiku | No |
| 6 | Memory Extraction | `client.messages.create()` | None | 1 | Sonnet | No |
| 7 | Session Summary | `client.messages.create()` | None | 1 | Sonnet | No |
| 8 | Conversation Analysis | `client.messages.create()` | None | 1 | Sonnet | No |
| 9 | History Compaction | `client.messages.create()` | None | 1 | Sonnet | No |

Paths 5-9 are correctly single-call (no tools needed). Path 4 is a nested agentic call inside a primitive (acceptable — bounded, single-purpose). The issue is paths 1-3: three independent top-level agentic loops when ADR-080 promised "one agent, two modes." Path 3 is the one that needs to be absorbed.

---

## Decision

### Absorb web research into headless mode

Eliminate `web_research.py` as a standalone agentic loop. Instead, the headless agent in `generate_draft_inline()` handles web research directly through its existing `WebSearch` primitive.

**Before (current — 2 sequential agent calls for research types):**

```
Strategy: ResearchStrategy.gather_context()
├── LLM call 1: web_research.py agentic loop (web_search server tool, up to 5 rounds)
├── Serialize research to text
├── Merge with platform context
└── Return gathered_context string

Generation: generate_draft_inline()
├── LLM call 2: headless agent (5 primitives, up to 3 rounds)
├── Agent sees pre-baked [WEB RESEARCH] text
├── Agent generates deliverable content
└── Return draft
```

**After (single agent call — research is headless work):**

```
Strategy: ResearchStrategy.gather_context()
├── Gather platform context (unchanged)
├── DO NOT run web research
└── Return gathered_context + research_directive

Generation: generate_draft_inline()
├── Receives gathered_context + research_directive in prompt
├── LLM call: headless agent (same primitives, higher round limit for research)
├── Agent uses WebSearch to investigate, uses Search/Read for platform cross-reference
├── Agent generates deliverable content informed by its own research
└── Return draft
```

### Mode-specific tool round limits

The current flat `HEADLESS_MAX_TOOL_ROUNDS = 3` doesn't fit all bindings. Research types need more room to investigate; platform-bound types rarely need any.

```python
HEADLESS_TOOL_ROUNDS = {
    "platform_bound":  2,   # Rarely needs tools — context is pre-gathered
    "cross_platform":  3,   # Occasionally useful for cross-referencing
    "research":        6,   # Needs room for web search + follow-up
    "hybrid":          6,   # Web research + platform investigation
}
```

### Research directive in prompt

When a deliverable has `binding: "research"` or `binding: "hybrid"`, the headless system prompt receives a **research directive** section:

```
## Research Directive
This deliverable requires web research. Use WebSearch to investigate the topic.
Research objective: {deliverable.title}
{deliverable.description}

Search thoroughly (2-4 queries), then synthesize findings with any platform context provided.
```

This replaces the `RESEARCH_SYSTEM_PROMPT` from `web_research.py`.

### What changes in execution strategies

| Strategy | Before | After |
|----------|--------|-------|
| `PlatformBoundStrategy` | Gathers platform context | Unchanged |
| `CrossPlatformStrategy` | Gathers multi-platform context | Unchanged |
| `ResearchStrategy` | Runs `research_topic()` → gathers web + platform context | Gathers platform context only, adds `research_directive` to result |
| `HybridStrategy` | Runs `research_topic()` + platform in parallel | Gathers platform context only, adds `research_directive` to result |

Research and Hybrid strategies still do their platform context gathering (delegating to CrossPlatformStrategy). They just stop running the separate web research agent.

---

## What changes in code

### `generate_draft_inline()` — accept binding, adjust rounds

```python
async def generate_draft_inline(
    client, user_id, deliverable, gathered_context,
    trigger_context=None,
    research_directive=None,      # NEW: from ResearchStrategy
):
    ...
    binding = deliverable.get("type_classification", {}).get("binding", "cross_platform")
    max_rounds = HEADLESS_TOOL_ROUNDS.get(binding, 3)
    ...
```

### `_build_headless_system_prompt()` — research directive section

When `research_directive` is provided, add a `## Research Directive` section to the headless system prompt that instructs the agent to use WebSearch. This replaces the separate RESEARCH_SYSTEM_PROMPT.

### `execution_strategies.py` — simplify Research and Hybrid

```python
class ResearchStrategy(ExecutionStrategy):
    async def gather_context(self, client, user_id, deliverable) -> GatheredContext:
        # Platform grounding (if any sources configured)
        integration_sources = [s for s in sources if s.get("type") == "integration_import"]
        if integration_sources:
            platform_strategy = CrossPlatformStrategy()
            platform_result = await platform_strategy.gather_context(client, user_id, deliverable)
            result.content = platform_result.content
            ...

        # Build research directive (headless agent will do the actual research)
        result.summary["research_directive"] = _build_research_directive(deliverable)
        return result
```

### `web_research.py` — deprecate

Mark as deprecated. Remove import from `execution_strategies.py`. The `research_topic()` function can remain for potential direct use, but is no longer called by the deliverable pipeline.

---

## What does NOT change

| Component | Status | Rationale |
|-----------|--------|-----------|
| TP Chat (Path 1) | Unchanged | Chat mode is independent — streaming, user present, full primitives |
| Signal Processing (Path 4) | Unchanged | Single Haiku call, no tools — correctly scoped |
| Memory Extraction (Path 5) | Unchanged | Single call, no tools needed |
| Session Compaction (Path 8) | Unchanged | Single call, no tools needed |
| Conversation Analysis (Path 7) | Unchanged | Single call, no tools needed |
| Primitive registry | Unchanged | Same 5 headless tools (Read, Search, List, WebSearch, GetSystemState) |
| Strategy selection | Unchanged | `get_execution_strategy()` still routes by binding |
| Platform context gathering | Unchanged | Strategies still gather from `platform_content` |
| Delivery pipeline | Unchanged | Post-generation delivery infrastructure |

---

## Consequences

### Positive

1. **Actually "one agent, two modes."** ADR-080's promise is fulfilled. Every agentic tool-use call in the deliverable pipeline goes through the headless agent.
2. **Research quality improves.** The generating agent can do its own targeted research informed by the deliverable template, rather than receiving pre-baked research text that may not match what it needs.
3. **Single observability path.** All headless tool use (including web search) logged through one system: `[GENERATE] Headless agent used N tool round(s): WebSearch, Search`.
4. **Less code.** `web_research.py`'s agentic loop (~100 lines) is absorbed into existing headless mode infrastructure. No new code, just wiring.
5. **Research types are natural multi-turn test cases.** The headless agent will actually use tools for `research_brief`, `deep_research`, and `intelligence_brief` — providing production validation of multi-turn headless execution.

### Negative

1. **Research deliverables cost profile changes.** Before: 1 research call + 1 generation call (2 separate Sonnet calls with different system prompts). After: 1 headless call with up to 6 tool rounds (potentially 7 Sonnet calls). Mitigated by: the headless agent is instructed to be efficient, and most research won't exhaust 6 rounds.
2. **WebSearch primitive vs. Anthropic web_search_20250305.** The current `WebSearch` primitive in the registry may not use the same Anthropic server-side tool that `web_research.py` uses. Need to verify and potentially update the primitive to use Anthropic's native web search for quality parity.

### Risk

**Nested agentic call in WebSearch primitive.** The `WebSearch` primitive (`web_search.py`) is itself a hidden agentic loop — it creates a *separate* Claude call with `web_search_20250305`, handles multi-turn continuations (`while response.stop_reason == "tool_use"`), then returns summarized results. This means when the headless agent calls `WebSearch`, we have a Claude-calling-Claude pattern: the outer headless loop → WebSearch primitive → inner Claude + web_search loop. This is architecturally sound (the inner call is scoped and bounded), but costs 1 additional Sonnet call per WebSearch invocation. This is the same cost structure as `web_research.py` — no regression, just making the hidden call explicit.

**WebSearch primitive quality parity.** Both `web_search.py` (primitive) and `web_research.py` (standalone) use identical Anthropic `web_search_20250305` server tools and Sonnet. The primitive returns structured results; the standalone returns narrative text. The headless agent will get structured results and synthesize itself — potentially better than pre-baked narrative.

---

## Implementation sequence

### Phase 1 — Verify WebSearch primitive (~30 min)

Read the WebSearch primitive implementation. Confirm it uses Anthropic's native `web_search_20250305` server tool (or equivalent quality). If not, update it.

### Phase 2 — Binding-aware tool rounds (~20 lines)

Replace `HEADLESS_MAX_TOOL_ROUNDS = 3` with `HEADLESS_TOOL_ROUNDS` dict keyed by binding. `generate_draft_inline()` reads binding from deliverable and selects appropriate round limit.

### Phase 3 — Research directive in system prompt (~30 lines)

Add research directive section to `_build_headless_system_prompt()`. Pass `research_directive` from strategy result into `generate_draft_inline()`.

### Phase 4 — Simplify ResearchStrategy and HybridStrategy (~50 lines removed)

Remove `web_research.research_topic()` calls from both strategies. Add `research_directive` to `GatheredContext`. Platform context gathering stays.

### Phase 5 — Delete web_research.py ✅ (2026-02-27)

File deleted. No runtime imports remained after Phase 4. Production validated via Phase 6 before deletion.

### Phase 6 — Production validation

Trigger research-type deliverables. Verify:
- WebSearch tool is called during headless generation (multi-turn)
- Research quality is at parity with pre-change baseline
- Logs show `[GENERATE] Headless agent used N tool round(s): WebSearch`
- Cost is within bounds

---

## Open questions

1. **Should the headless agent get Anthropic's native `web_search_20250305` as a server tool alongside the WebSearch primitive?** Server tools are handled by Anthropic (no client execution). This might be simpler than routing through the primitive system, but breaks the "one registry" principle.

2. **Should signal-emergent deliverables get higher tool round limits?** They already get signal reasoning in the system prompt. If the signal is about a new topic, more investigation room could help.

3. **Type consolidation (ADR-044 deferred item).** 28 types is a lot. Many beta/experimental types have zero usage. Should we prune before or after this change? Independent but related.
