# ADR-080: Unified Agent with Chat and Headless Modes

**Status:** Implemented
**Date:** 2026-02-26
**Implemented:** 2026-02-26 (Phases 0-3 code-complete, production monitoring pending)
**Supersedes:** ADR-061 (Two-Path Architecture) — evolves strict path separation into unified agent with modal execution
**Amends:** ADR-072 (TP Execution Pipeline) — the "TP headless mode" aspiration is now formalized with precise boundaries
**Related:**
- [ADR-042: Deliverable Execution Simplification](ADR-042-deliverable-execution-simplification.md)
- [ADR-045: Deliverable Orchestration Redesign](ADR-045-deliverable-orchestration-redesign.md)
- [ADR-068: Signal-Emergent Deliverables](ADR-068-signal-emergent-deliverables.md)
- [Agent Execution Model](../architecture/agent-execution-model.md)

---

## Context

YARNNN has two LLM execution paths (codified in ADR-061):

1. **TP (Path A)** — conversational, streaming, 20+ primitives, multi-turn tool use via `chat_completion_stream_with_tools()`. Used for chat.
2. **Backend Orchestrator (Path B)** — single LLM call via `chat_completion()`, no tools, no reasoning. Used for deliverable generation.

Both paths call the same underlying Anthropic SDK, but Path B has no access to any primitives. This creates a measurable quality gap: TP can search, cross-reference, and investigate iteratively. Deliverable generation gets a content dump and must produce output in one pass.

### What ADR-061 got right

The separation between **orchestration** (scheduling, strategy selection, delivery, retention) and **content generation** (the LLM call) is sound. Backend orchestration should not become conversational. The scheduler, freshness checks, delivery pipeline, retention marking — none of this is agent work.

### What ADR-061 got wrong

ADR-061 framed the separation as "TP vs. Orchestrator" — two entirely separate systems. In practice, both systems use the same LLM, the same primitives would be useful to both, and maintaining two separate tool registries creates drift risk. The framing also made it architecturally awkward to improve deliverable generation quality, because any use of primitives was considered "mixing paths."

ADR-072 attempted to address this with "TP in headless mode" but only as an aspiration — it was never implemented, and three documentation files incorrectly claimed it was.

### The actual problem

Step 6 of the deliverable execution pipeline — `generate_draft_inline()` — calls `chat_completion()`, a 10-line function that sends one prompt and returns one response. No tools. No investigation ability. The other 9 steps of the pipeline (trigger, freshness, strategy, version creation, delivery, retention, etc.) are well-designed backend orchestration that should not change.

---

## Decision

### One agent, two modes

YARNNN has one agent concept with two execution modes:

| | **Chat mode** | **Headless mode** |
|---|---|---|
| **Surface** | User-facing conversation (TP) | Background content generation |
| **Entry point** | `/api/chat` | `generate_draft_inline()` in deliverable pipeline |
| **LLM function** | `chat_completion_stream_with_tools()` | `chat_completion_with_tools()` |
| **Streaming** | Yes | No |
| **System prompt** | Conversational (thinking_partner.py) | Type-specific structured output |
| **Max tool rounds** | 15 | 3 |
| **Session state** | Yes (session_messages, token tracking) | No |
| **Available primitives** | Full set | Curated subset (read-only) |
| **User present** | Yes | No |

### The boundary stays

Backend orchestration is NOT agent work. The pipeline does not change:

```
Backend Orchestration (unchanged)
├── 1. Trigger (scheduler / manual / signal)
├── 2. Freshness check
├── 3. Strategy selection + context gathering
├── 4. Version + ticket creation
├── 5. Agent (mode="headless")           ← ONLY this step changes
│   ├── Receives: gathered context + type prompt + signal reasoning
│   ├── Can use: Search, FetchPlatformContent, CrossPlatformQuery
│   ├── Cannot use: CreateDeliverable, UpdatePreferences, UI actions
│   ├── Max 3 tool rounds
│   └── Returns: structured content (text)
├── 6. Retention marking
├── 7. Source snapshots
├── 8. Delivery (email, Slack, Notion)
└── 9. Activity logging
```

The orchestration pipeline calls the agent at step 5, receives text back, and continues with delivery infrastructure. The agent does not know about versions, tickets, delivery, or retention.

### Mode-gated primitive registry

Primitives declare which modes they support:

```python
PRIMITIVE_MODES = {
    # Read-only investigation — available in both modes
    "Search":                 ["chat", "headless"],
    "FetchPlatformContent":   ["chat", "headless"],
    "CrossPlatformQuery":     ["chat", "headless"],
    "GetSystemState":         ["chat", "headless"],

    # Write/action primitives — chat only
    "CreateDeliverable":      ["chat"],
    "ManageDeliverable":      ["chat"],
    "UpdatePreferences":      ["chat"],
    "SendSlackMessage":       ["chat"],
    "CreateGmailDraft":       ["chat"],
    "UpdateNotionPage":       ["chat"],
}
```

When a primitive is updated or added, it is tagged with modes. One registry, one maintenance track. No drift.

### Signal context forwarding

Signal processing currently discards all reasoning before deliverable generation (`trigger_context={"type": "signal_emergent"}` — zero signal intelligence forwarded). This ADR requires:

1. `_queue_signal_emergent_execution()` forwards `reasoning_summary` and `signal_context` from the `SignalAction` into `trigger_context`
2. `generate_draft_inline()` reads `trigger_context.signal_reasoning` and injects it into the headless system prompt as investigation guidance

This is ~15 lines of code and is a prerequisite for headless mode to produce meaningfully better signal-emergent deliverables.

---

## What changes in code

### `generate_draft_inline()` — the only structural change

**Before (current):**
```python
draft = await chat_completion(
    messages=[{"role": "user", "content": prompt}],
    system=system_prompt,
    model=SONNET_MODEL,
    max_tokens=4000,
)
```

**After:**
```python
from services.primitives import get_headless_tools, create_headless_executor

tools = get_headless_tools()
executor = create_headless_executor(client, user_id)

response = await chat_completion_with_tools(
    messages=[{"role": "user", "content": prompt}],
    system=headless_system_prompt,
    tools=tools,
    model=SONNET_MODEL,
    max_tokens=4000,
    max_tool_rounds=3,
)
draft = response.text
```

### `signal_processing.py` — forward reasoning

**Before:**
```python
trigger_context={"type": "signal_emergent"}
```

**After:**
```python
trigger_context={
    "type": "signal_emergent",
    "signal_reasoning": action.signal_context.get("reasoning_summary", ""),
    "signal_type": action.signal_context.get("signal_type", ""),
}
```

### New files

- `api/services/primitives/registry.py` — primitive mode registry, `get_tools_for_mode(mode)`, `get_executor_for_mode(mode)`

### Modified files

- `api/services/deliverable_execution.py` — `generate_draft_inline()` switches from `chat_completion()` to `chat_completion_with_tools()`
- `api/services/signal_processing.py` — `_queue_signal_emergent_execution()` forwards signal context
- `api/services/anthropic.py` — no changes (both `chat_completion_with_tools()` and streaming version already exist)

---

## What does NOT change

| Component | Status | Rationale |
|---|---|---|
| `execute_deliverable_generation()` | Unchanged | Orchestration pipeline — calls agent, gets text back |
| Execution strategies | Unchanged | Strategy-based context gathering is pre-agent work |
| `build_type_prompt()` | Unchanged | Type-specific prompt assembly still provides the base prompt |
| Delivery pipeline | Unchanged | Post-agent delivery infrastructure |
| Freshness checks | Unchanged | Pre-agent validation |
| Retention marking | Unchanged | Post-agent content lifecycle |
| Unified scheduler | Unchanged | Trigger mechanism |
| `chat_completion_stream_with_tools()` | Unchanged | Chat mode continues using existing streaming loop |
| `chat_completion_with_tools()` | Unchanged | Already exists, already tested — headless mode uses it directly |
| TP system prompt | Unchanged | Chat mode prompt is independent of headless mode prompt |

---

## Naming

| Term | Definition |
|---|---|
| **Agent** | The unified YARNNN agent concept. Powers both chat and headless execution. |
| **Chat mode** | Agent running with a user session. Streaming, full primitive set, conversational prompt. Product-facing name: Thinking Partner (TP). |
| **Headless mode** | Agent running without a user session. Non-streaming, curated primitives, structured output prompt. Used by backend orchestration for content generation. |
| **Orchestration** | The backend pipeline (scheduler, strategy, delivery, retention). NOT agent work. Orchestration invokes the agent in headless mode at the content generation step. |
| **Primitives** | Tools available to the agent. The shared toolkit. Mode-gated. |

---

## Consequences

### Positive

1. **One primitive maintenance track.** Update Search once, it improves everywhere. Add a new primitive, tag it with modes.
2. **Deliverable quality improvement.** Headless mode can search semantically, cross-reference platforms, and investigate — not just summarize a content dump.
3. **Signal reasoning preserved.** Signal processing intelligence flows through to generation instead of being discarded.
4. **Future modes are natural.** If signal processing ever needs its own agent reasoning (e.g., `mode="analysis"`), it's a new mode — not a new system.
5. **Clean boundary preserved.** Orchestration remains orchestration. The agent is invoked at one step and returns text.
6. **Cost-bounded.** 3 tool rounds max in headless mode. Each round is one LLM call + tool execution. Worst case: 4 LLM calls per deliverable (vs. 1 today). Predictable.

### Negative

1. **Higher per-deliverable cost.** Tool rounds mean additional LLM calls. Mitigated by the 3-round cap and the fact that most deliverables will use 0-1 tool rounds (the gathered context is already in the prompt — tools supplement, not replace).
2. **Slower generation.** Tool execution adds latency. Acceptable because deliverables are background jobs — nobody is waiting.
3. **Primitive error handling in headless context.** If a tool call fails in chat mode, TP tells the user. In headless mode, failures must be handled silently or logged. The executor needs headless-appropriate error handling.

### Risk

**Cost runaway.** If the headless system prompt encourages excessive tool use, costs could spike. Mitigated by: max 3 tool rounds, curated read-only primitives (no write operations that could cascade), and the system prompt explicitly instructs the agent to use tools only when gathered context is insufficient.

---

## Supersedes

### ADR-061 (Two-Path Architecture)

ADR-061's core insight — separate orchestration from generation — is preserved. What changes is the framing: instead of "TP vs. Orchestrator" as two separate systems, the agent is unified and the orchestration pipeline invokes it in headless mode.

ADR-061's anti-pattern "Using TP for deliverable content generation" is refined: TP (chat mode) is still not used for deliverable generation. Headless mode is a different execution mode of the same agent — different prompt, different primitives, different constraints.

### ADR-072 "TP Headless Mode" aspiration

ADR-072 described TP running in headless mode with access to primitives for deliverable generation. This ADR formalizes that aspiration with precise boundaries, naming, and implementation details. The vague aspiration becomes a specified architecture.

---

## Implementation sequence

### Phase 0 — Signal context forwarding (prerequisite, ~15 lines)

Forward `reasoning_summary` from signal processing into `trigger_context`. `generate_draft_inline()` reads and injects into prompt. No architectural change. Immediate quality improvement for signal-emergent deliverables.

### Phase 1 — Primitive registry + headless executor (~100 lines)

Create `primitives/registry.py` with mode-gated tool definitions. Create `create_headless_executor()` that dispatches tool calls to existing primitive implementations with headless-appropriate error handling. Write headless system prompt template.

### Phase 2 — Switch generation call (~20 lines)

`generate_draft_inline()` switches from `chat_completion()` to `chat_completion_with_tools()` using the headless registry and executor. Gathered context from strategy is still passed in the prompt — tools are supplementary investigation, not a replacement.

### Phase 3 — Validation and tuning

Test across deliverable types. Tune headless system prompt to avoid unnecessary tool use. Verify cost increase is within bounds (target: <2x average cost per deliverable). Monitor tool usage patterns.

---

## Relationship to deferred items

| Deferred item | Relationship to this ADR |
|---|---|
| F9 Embedding Generation | **Becomes more valuable** — headless Search can use semantic embeddings when populated |
| F5/F2 merge (GAP-4) | **Independent** — conversation analysis vs signal processing is an orchestration concern, not an agent concern |
| Event triggers (ADR-031) | **Independent** — trigger mechanism, not generation quality |
| Multi-destination delivery | **Independent** — post-agent delivery, not agent work |
| Quality metrics | **Benefits from** — better generation quality makes metrics more meaningful |
| Session summaries (ADR-067) | **Independent** — chat mode infrastructure |
| Deliverable type consolidation | **Independent** — template cleanup, pairs well with Phase 2 |
| In-session compaction (ADR-067) | **Independent** — chat mode infrastructure |
