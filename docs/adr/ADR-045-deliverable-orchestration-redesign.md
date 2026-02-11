# ADR-045: Deliverable Orchestration Redesign

**Date**: 2026-02-11
**Status**: Proposed
**Supersedes**: ADR-016 (Layered Agent Architecture) - execution model
**Relates to**: ADR-044 (Type Reconceptualization), ADR-038 (Primitives)

---

## Context

### The Disconnect

The current pipeline was designed for ADR-019's format-centric types:

```python
# Current: One-size-fits-all pipeline
async def execute_pipeline(deliverable_id):
    gather_result = await execute_gather_step(...)      # Always ResearchAgent
    synthesize_result = await execute_synthesize_step(...) # Always ContentAgent
    stage_result = await execute_stage_step(...)
```

This ignores:
- **Type classification** (ADR-044): binding, temporal_pattern, freshness requirements
- **Platform-specific signals**: Hot threads, unanswered questions, sender importance
- **Research types**: Need web search, which doesn't exist
- **Parallel execution**: All sources fetched sequentially despite being independent

### Current Agent Architecture (Post-Rename)

```
┌─────────────────────────────────────────────────────────────────┐
│ Agents (api/agents/)                                            │
├─────────────────────────────────────────────────────────────────┤
│ SynthesizerAgent  - Synthesizes pre-fetched context             │
│ DeliverableAgent  - Generates deliverable output (primary)      │
│ ReportAgent       - Generates standalone reports                │
│ ThinkingPartner   - Chat agent with primitives                  │
├─────────────────────────────────────────────────────────────────┤
│ All agents have ONE tool: submit_output                         │
│ No agents have: web_search, platform_fetch, file operations     │
└─────────────────────────────────────────────────────────────────┘
```

**Agent Type Mapping** (old → new):
- `research` → `synthesizer`
- `content` → `deliverable`
- `reporting` → `report`

**Problem**: Agents are passive processors, not active gatherers. The pipeline hardcodes gather logic in Python, not in agent reasoning.

### Claude Code's Model (Reference)

Claude Code has specialized subagents spawned via `Task` tool:

```typescript
// Claude Code subagent types
"Explore"       // Fast codebase exploration
"Plan"          // Implementation planning
"Bash"          // Command execution
"general-purpose" // Multi-step tasks
```

Each subagent:
- Has specific tools available (Explore can't edit, Plan can't write)
- Runs autonomously with own context
- Returns results to parent for integration

---

## Decision

Redesign deliverable orchestration with **type-aware execution strategies** and **tool-equipped agents**.

### Principle 1: Type Classification Drives Orchestration

The `type_classification` from ADR-044 determines HOW the deliverable is executed:

| Binding | Orchestration Strategy |
|---------|----------------------|
| `platform_bound` | Single-platform gatherer → Platform-specific synthesizer |
| `cross_platform` | Parallel platform gatherers → Cross-platform synthesizer |
| `research` | Research agent with web search → Research synthesizer |
| `hybrid` | Research + Platform gatherers → Hybrid synthesizer |

```python
async def execute_pipeline(deliverable):
    classification = deliverable.get("type_classification", {})
    binding = classification.get("binding", "cross_platform")

    strategy = get_strategy(binding)
    return await strategy.execute(deliverable)
```

### Principle 2: Agents Get Tools Based on Role

Instead of one `submit_output` tool, agents get tools matching their responsibility:

#### Platform Gatherer Agent
```python
TOOLS = [
    "platform.fetch",      # Fetch from specific platform (Slack, Gmail, Notion)
    "platform.list",       # List available resources
    "submit_output",       # Return gathered context
]
```

#### Research Agent (Enhanced)
```python
TOOLS = [
    "platform.fetch",      # Can still use platform context
    "web.search",          # NEW: Search the web
    "web.fetch",           # NEW: Fetch and extract from URL
    "submit_output",       # Return research findings
]
```

#### Synthesizer Agent
```python
TOOLS = [
    "submit_output",       # Return final content
    # No fetch tools - works with provided context only
]
```

### Principle 3: Parallel Execution for Independent Sources

```python
# Current: Sequential
for source in sources:
    result = await fetch_source(source)  # Blocks

# Proposed: Parallel by platform
slack_sources = [s for s in sources if s.provider == "slack"]
gmail_sources = [s for s in sources if s.provider == "gmail"]
notion_sources = [s for s in sources if s.provider == "notion"]
web_sources = [s for s in sources if s.type == "web_research"]

results = await asyncio.gather(
    gather_slack(slack_sources),
    gather_gmail(gmail_sources),
    gather_notion(notion_sources),
    research_web(web_sources) if classification.binding == "research" else None,
)
```

### Principle 4: Type-Specific Synthesis

Different types need different synthesis approaches:

| Type | Synthesizer Focus |
|------|-------------------|
| `slack_channel_digest` | Hot threads, unanswered questions, decisions |
| `gmail_inbox_brief` | Priority triage, action-required, sender importance |
| `weekly_status` | Cross-platform themes, progress metrics |
| `research_brief` | External findings + internal grounding |
| `competitive_analysis` | Web research synthesis (NEW) |

---

## Execution Strategies

### Strategy: Platform-Bound

For `slack_channel_digest`, `gmail_inbox_brief`, `notion_page_summary`:

```
┌─────────────────────────────────────────────────────────────────┐
│ Platform-Bound Execution                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐                                           │
│  │ Platform Gatherer │ ← Tools: platform.fetch, platform.list   │
│  │ (e.g., Slack)     │                                          │
│  └────────┬─────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌──────────────────┐                                           │
│  │ Platform-Specific │ ← Prompt: TYPE_PROMPTS[slack_digest]     │
│  │ Synthesizer       │   Knows: hot threads, decisions, etc.    │
│  └────────┬─────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│      [Final Content]                                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Strategy: Cross-Platform

For `weekly_status`, `project_brief`, `meeting_prep`:

```
┌─────────────────────────────────────────────────────────────────┐
│ Cross-Platform Execution                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                 │
│  │   Slack    │  │   Gmail    │  │   Notion   │  (parallel)     │
│  │  Gatherer  │  │  Gatherer  │  │  Gatherer  │                 │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘                 │
│        │               │               │                        │
│        └───────────────┼───────────────┘                        │
│                        ▼                                        │
│              ┌──────────────────┐                               │
│              │ Cross-Platform   │ ← Synthesizes themes across   │
│              │ Synthesizer      │   all platform contexts       │
│              └────────┬─────────┘                               │
│                       │                                         │
│                       ▼                                         │
│                 [Final Content]                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Strategy: Research (NEW)

For `research_brief`, `competitive_analysis`, `market_landscape`:

```
┌─────────────────────────────────────────────────────────────────┐
│ Research Execution                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────┐  ┌────────────┐                                 │
│  │    Web     │  │  Platform  │  (parallel)                     │
│  │ Researcher │  │  Grounding │                                 │
│  │ (NEW)      │  │ (optional) │                                 │
│  └─────┬──────┘  └─────┬──────┘                                 │
│        │               │                                        │
│        │   Tools:      │   Tools:                               │
│        │   web.search  │   platform.fetch                       │
│        │   web.fetch   │                                        │
│        │               │                                        │
│        └───────────────┼                                        │
│                        ▼                                        │
│              ┌──────────────────┐                               │
│              │ Research         │ ← Synthesizes external        │
│              │ Synthesizer      │   + internal context          │
│              └────────┬─────────┘                               │
│                       │                                         │
│                       ▼                                         │
│                 [Final Content]                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tool Definitions

### web.search (NEW)

```python
WEB_SEARCH_TOOL = {
    "name": "web_search",
    "description": "Search the web for information. Use for current events, "
                   "competitor research, industry trends, or any external context.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "max_results": {
                "type": "integer",
                "default": 5,
                "description": "Maximum results to return"
            }
        },
        "required": ["query"]
    }
}
```

### web.fetch (NEW)

```python
WEB_FETCH_TOOL = {
    "name": "web_fetch",
    "description": "Fetch and extract content from a specific URL. "
                   "Returns cleaned text content from the page.",
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to fetch"
            },
            "extract_prompt": {
                "type": "string",
                "description": "What to extract from the page"
            }
        },
        "required": ["url"]
    }
}
```

### platform.fetch (Existing, formalized)

```python
PLATFORM_FETCH_TOOL = {
    "name": "platform_fetch",
    "description": "Fetch content from a connected platform (Slack, Gmail, Notion).",
    "input_schema": {
        "type": "object",
        "properties": {
            "platform": {
                "type": "string",
                "enum": ["slack", "gmail", "notion"]
            },
            "source": {
                "type": "string",
                "description": "Source identifier (channel ID, label, page ID)"
            },
            "scope": {
                "type": "object",
                "properties": {
                    "mode": {"type": "string", "enum": ["delta", "fixed_window"]},
                    "days": {"type": "integer"},
                    "max_items": {"type": "integer"}
                }
            }
        },
        "required": ["platform", "source"]
    }
}
```

---

## New Deliverable Types

With web search capability, add the ADR-044 research types:

| Type | Binding | Tools Required |
|------|---------|----------------|
| `competitive_analysis` | research | web.search, web.fetch |
| `market_landscape` | research | web.search, web.fetch |
| `topic_deep_dive` | research | web.search, web.fetch, platform.fetch |
| `industry_brief` | hybrid | web.search, platform.fetch |

---

## Implementation Phases

### Phase 1: Type-Aware Strategy Selection ✅ (2026-02-11)
- [x] Add strategy dispatcher based on `type_classification.binding`
- [x] Keep existing agents (now DeliverableAgent), route via strategy
- [x] Parallel source fetching within cross-platform strategy

**Implementation:**
- `api/services/execution_strategies.py` - Strategy classes and dispatcher
- `api/services/deliverable_execution.py` - Updated to use `get_execution_strategy()`

**Strategies implemented:**
- `PlatformBoundStrategy` - Single platform focus
- `CrossPlatformStrategy` - Parallel multi-platform fetch via `asyncio.gather`
- `ResearchStrategy` - Web research via Anthropic native tools
- `HybridStrategy` - Parallel web research + platform fetch

### Phase 2: Web Research ✅ (2026-02-11)
- [x] Create ResearcherAgent with Anthropic's native `web_search` tool
- [x] Update ResearchStrategy to use ResearcherAgent
- [x] Update HybridStrategy to run web research + platform fetch in parallel
- [x] No external API needed - uses Anthropic's server-side web search

**Implementation:**
- `api/agents/researcher.py` - ResearcherAgent using `web_search_20250305` tool
- `api/services/execution_strategies.py` - Updated ResearchStrategy and HybridStrategy

**Key design decisions:**
- Anthropic's native `web_search` is a server-side tool (no client execution)
- Research runs before deliverable generation (context gathering phase)
- HybridStrategy runs web research and platform fetch concurrently via `asyncio.gather`

### Phase 3: Research Types (Next)
- [ ] Add `competitive_analysis`, `market_landscape` to type registry
- [ ] Add `research_brief` to deliverable_types
- [ ] Test end-to-end research deliverable flow

### Phase 4: Subagent Orchestration (Future)
- [ ] Task-like delegation for parallel agents
- [ ] Progress tracking for long-running research
- [ ] Result integration from multiple subagents

---

## Mapping to Claude Code Patterns

| Claude Code | YARNNN Equivalent |
|-------------|-------------------|
| `Task(subagent_type="Explore")` | `await gather_strategy.execute(sources)` |
| `Task(subagent_type="Plan")` | Conversation-based planning (no change) |
| `WebSearch` tool | Anthropic native `web_search` in ResearcherAgent |
| `WebFetch` tool | `web.fetch` tool for ResearchAgent |
| Parallel tool calls | `asyncio.gather` for independent sources |
| Background execution | Existing work ticket system |

---

## Migration

Existing deliverables continue to work:
- Default `binding` is `cross_platform`
- Default strategy is current ResearchAgent → ContentAgent chain
- No breaking changes to API

New types and strategies are additive.

---

## Open Questions

1. **Web search provider**: Use Anthropic's built-in (if available via API), or integrate external (Tavily, Brave Search)?

2. **Cost implications**: Web search adds API costs. Should research types have usage limits?

3. **Caching**: Web search results should be cached. What TTL?

4. **Platform grounding for research**: How explicit should the grounding instruction be in the prompt?

---

## Related

- ADR-044: Deliverable Type Reconceptualization
- ADR-038: TP Primitives (Execute, Search)
- ADR-016: Layered Agent Architecture (partially superseded)
- ADR-030: Platform Sync (source fetching mechanics)
