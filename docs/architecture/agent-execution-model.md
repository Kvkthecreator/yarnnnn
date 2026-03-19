# Architecture: Agent Execution Model

**Status:** Canonical
**Date:** 2026-02-26 (updated 2026-03-12 for ADR-109: Scope × Skill × Trigger framework terminology)
**Supersedes:** ADR-016 (Layered Agent Architecture) — work agent delegation model
**Codifies:** ADR-080 (Unified Agent Modes) — evolves ADR-061 two-path separation into one agent with modal execution
**Related:**
- [ADR-080: Unified Agent Modes](../adr/ADR-080-unified-agent-modes.md) — governing ADR
- [ADR-061: Two-Path Architecture](../adr/ADR-061-two-path-architecture.md) — predecessor (superseded by ADR-080)
- [ADR-068: Signal-Emergent Agents](../adr/ADR-068-signal-emergent-agents.md) — extends orchestration with signal processing phase
- [ADR-042: Agent Execution Simplification](../adr/ADR-042-agent-execution-simplification.md)
- [ADR-045: Agent Orchestration Redesign](../adr/ADR-045-agent-orchestration-redesign.md)
- [Supervision Model](supervision-model.md) — the complementary UI/UX framing

---

## The Core Principle

YARNNN has one agent with two execution modes. The agent powers both interactive chat and background content generation. Backend orchestration is separate from the agent — it manages scheduling, delivery, retention, and lifecycle.

**The agent** reasons over content using primitives. It produces text.

**The orchestration pipeline** manages everything around the agent: triggers, freshness checks, strategy selection, version tracking, delivery, retention marking. It invokes the agent at one step and receives text back.

---

## One Agent, Two Modes (Three with ADR-124)

> **Note**: ADR-124 (Project Meeting Room, proposed) introduces a third mode — `agent_chat` — where agents participate as attributed authors in project meeting room conversations with domain-scoped primitives. See [ADR-124](../adr/ADR-124-project-meeting-room.md) for the full proposal. The two-mode model below describes the current implementation.

### Chat Mode (Thinking Partner)

```
User ←→ Agent (mode="chat")
```

| Property | Value |
|---|---|
| Character | Conversational, Claude Code-like |
| Latency | <3 seconds |
| Scope | Session-scoped |
| Streaming | Yes |
| Primitives | Full set (read + write + action) |
| Max tool rounds | 15 |
| System prompt | Conversational (`thinking_partner.py`) |
| Entry point | `/api/chat` |
| LLM function | `chat_completion_stream_with_tools()` |

**Chat mode responsibilities:**
- Answer questions (searches memory, platform data, documents)
- Execute one-time platform actions (send Slack message, create Gmail draft)
- Create and configure agents when the user explicitly asks
- Read and explain existing agent versions

### Headless Mode (Content Generation)

```
Orchestration → Agent (mode="headless") → Text → Orchestration continues
```

| Property | Value |
|---|---|
| Character | Structured output, investigation-capable |
| Latency | Latency-tolerant (seconds to minutes) |
| Scope | Stateless (no session) |
| Streaming | No |
| Primitives | Curated subset: Search, Read, List, WebSearch, GetSystemState |
| Max tool rounds | Scope-aware: platform=2, cross_platform=3, knowledge=3, research=6, autonomous=6 (ADR-081/109) |
| System prompt | Directives + memory + learned preferences + optional research directive (ADR-081/087/101) |
| Entry point | `generate_draft_inline()` in agent pipeline |
| LLM function | `chat_completion_with_tools()` |

**Headless mode responsibilities:**
- Generate agent content from gathered context
- Investigate supplementary context via primitives when the gathered context is insufficient
- Produce structured, formatted output following type-specific templates
- For `proactive` and `coordinator` modes (ADR-092): execute a **review pass** — assess domain, return `generate / observe / create_child / advance_schedule / sleep` rather than content

**Headless mode explicitly does NOT:**
- Hold session state or conversation history
- Know about delivery, retention, or version management — that is orchestration

**ADR-092 extension — coordinator/proactive write primitives:**
Coordinator and proactive modes add two headless-only write primitives, scoped exclusively to orchestration actions:
- `CreateAgent` — creates a child agent with `origin=coordinator_created`; headless only
- `AdvanceAgentSchedule` — advances another agent's `next_run_at` to now; headless only

These are not available in chat mode. TP currently creates agents via the Write primitive (`ref="agent:new"`, chat-only). The coordinator's CreateAgent and TP's Write are separate implementations with different defaults and mode gates.

> **Planned (ADR-111):** Agent creation will be unified into a single `CreateAgent` primitive (chat + headless) backed by shared `create_agent_record()` logic. Write stops accepting `ref="agent:new"`. See [ADR-111](../adr/ADR-111-agent-composer.md).
>
> **Planned (ADR-110):** A deterministic bootstrap service will auto-create digest agents post-platform-connection, calling the same shared creation logic. This is an alternative entry point to agent execution — not a separate pipeline. See [ADR-110](../adr/ADR-110-onboarding-bootstrap.md).

---

## Mode-Gated Primitives (ADR-080)

Primitives declare which modes they are available in. One registry, one maintenance track.

```python
PRIMITIVE_MODES = {
    # Read-only investigation — both modes
    "Search":                   ["chat", "headless"],
    "Read":                     ["chat", "headless"],
    "List":                     ["chat", "headless"],
    "GetSystemState":           ["chat", "headless"],
    "WebSearch":                ["chat", "headless"],

    # Write/action/UI primitives — chat only
    "Write":                    ["chat"],
    "Edit":                     ["chat"],   # includes agent_instructions + scoped memory writes (ADR-091)
    "Execute":                  ["chat"],   # includes agent.acknowledge (ADR-091)
    "RefreshPlatformContent":   ["chat", "headless"],  # ADR-085 extended by ADR-092 (headless: scoped to agent sources, no staleness guard)
    "SaveMemory":               ["chat"],   # ADR-108: persist user-stated facts to /memory/notes.md
    "Clarify":                  ["chat"],
    "list_integrations":        ["chat"],

    # Coordinator/proactive primitives — headless only (ADR-092)
    # These are orchestration actions, not user-facing chat operations
    "CreateAgent":        ["headless"],   # coordinator mode: creates child with origin=coordinator_created
    "AdvanceAgentSchedule": ["headless"], # coordinator mode: trigger_existing replacement
}
# Note: platform_* tools (dynamic, loaded per user) are chat-only by default.
# Todo and Respond are handled in the HANDLERS map but not in PRIMITIVES list
# (TP's natural output and conversation stream serve those roles).
```

When a primitive is updated or added, it is tagged with modes. Updates improve both modes simultaneously. No drift.

---

## The Orchestration Boundary

Backend orchestration is NOT agent work. The orchestration pipeline invokes the agent at one step and receives text back.

**Standard generation pipeline** (`recurring`, `goal`, `reactive` on threshold):
```
Backend Orchestration
├── 1. Trigger (scheduler / event / manual)
├── 2. dispatch_trigger() routing (ADR-088) — signal_strength → high/medium/low
├── 3. Freshness check + strategy selection + context gathering (ADR-045)
├── 4. Version creation
├── 5. Agent (mode="headless")           ← agent invocation
│   ├── Receives: gathered context + type prompt + directives + memory + learned preferences (ADR-101)
│   ├── Can use: Search, Read, List, WebSearch, GetSystemState, RefreshPlatformContent
│   ├── Cannot use: Write, Edit, Execute, Clarify, CreateAgent, AdvanceAgentSchedule
│   ├── Max tool rounds: scope-aware (2-6, ADR-081/109)
│   └── Returns: structured content (text)
├── 6. Retention marking (ADR-072)
├── 7. Source snapshots
├── 8. Delivery — email, Slack, Notion (ADR-066, no approval gate)
└── 9. Activity logging
```

**Review pass pipeline** (`proactive`, `coordinator` modes — ADR-092):

> **Note (2026-03-16):** FOUNDATIONS.md v2 reframes the review pass as **TP's supervisory capability**. The agent provides domain assessment; TP (via Heartbeat) decides the action. Current code has the agent returning action decisions directly — this is mechanically preserved but conceptually shifts to TP ownership in ADR-111 Phase 4. See ADR-092 revision notes.

```
TP Heartbeat / Supervisory Pass
├── 1. Trigger: Heartbeat cadence or proactive_next_review_at <= NOW()
├── 2. Agent (mode="headless", review prompt)  ← domain assessment
│   ├── Receives: agent_instructions + agent_memory + source context
│   ├── Can use: Search, Read, List, CrossPlatformQuery, RefreshPlatformContent
│   └── Returns: domain observations + assessment (what's changed, what's notable)
├── 3. TP/Heartbeat decides action based on agent assessment:
│   ├── generate → proceeds to standard generation pipeline above
│   ├── observe → appends note to agent_memory.review_log
│   ├── create (Composer) → TP creates agent via Composer capability
│   ├── advance_schedule → sets another agent's next_run_at = now
│   └── sleep → sets proactive_next_review_at = specified time
└── 4. Activity logging
```

> **Current implementation:** Agent still returns `{action: "generate"|"observe"|...}` and orchestration acts on it directly. The TP decision layer is the Phase 4 target (ADR-111). The mechanical difference is small — agent assessment informs the decision either way — but the ownership distinction matters for the two-layer intelligence model.

**Orchestration's responsibilities:**
- **TP Heartbeat** (ADR-111 revised): Periodic assessment of agent workforce, triggers per-agent supervisory reviews
- **Per-agent supervisory review** (ADR-092, reframed): Agent provides domain assessment, TP/Heartbeat decides action
- **Composer** (ADR-111 revised): Creates/adjusts/dissolves agents based on compositional judgment
- **Analysis phase** (ADR-060): Mine TP session content for recurring patterns, create analyst-suggested agents
- **Execution phase**: Execute agents on trigger, select execution strategy, invoke agent in headless mode, deliver outputs, mark content retained

**Orchestration explicitly does NOT:**
- Participate in conversation
- Hold session state
- Produce content directly (that is the agent's job)

---

## The Boundary in Code

```python
# Chat mode: User-facing, streaming, full primitives
# api/agents/thinking_partner.py → api/services/anthropic.py

User: "Set up a weekly digest of #engineering"
→ Agent (chat mode) calls CreateAgent primitive
→ Agent responds: "Created. It will run every Monday at 9 AM."

# Headless mode: Background, non-streaming, curated primitives
# api/services/agent_execution.py → api/services/anthropic.py

unified_scheduler.py (cron)
  → execute_agent_generation(client, user_id, agent)
      → get_execution_strategy(agent)        # orchestration
      → strategy.gather_context(...)               # orchestration
      → generate_draft_inline(...)                 # agent (headless mode)
          → chat_completion_with_tools(             # agent uses primitives
              tools=get_headless_tools(),
              max_tool_rounds=3,
          )
      → mark_content_retained(...)                 # orchestration
      → deliver_version(...)                       # orchestration
```

The `ThinkingPartnerAgent` (chat mode prompt) is never used in headless mode. Headless mode has its own type-specific structured output prompts. Both modes share the same primitives and the same `chat_completion_with_tools()` function.

---

## Execution Strategies (Orchestration, not Agent)

Complexity in the orchestration pipeline lives in the *strategy*, not in agent logic. Strategies determine what context is gathered before the agent is invoked.

| Scope | Strategy | Data Source |
|---|---|---|
| `platform` | `PlatformBoundStrategy` | `platform_content` from single platform |
| `cross_platform` | `CrossPlatformStrategy` | `platform_content` from all platforms |
| `knowledge` | `KnowledgeStrategy` | Workspace + `/knowledge/` queries (ADR-109) |
| `research` | `ResearchStrategy` | Knowledge + WebSearch + documents |
| `autonomous` | `AutonomousStrategy` | Full primitive set, agent-driven (ADR-109) |

Strategy is selected at execution time from agent `scope` (ADR-109, migrating from `agent.type_classification.binding`). Platform and cross_platform scopes are dump-based (context gathered before LLM call). Knowledge, research, and autonomous scopes are tool-driven (agent drives its own investigation via primitives). See [Agent Framework](agent-framework.md#execution-strategies-by-scope) for details.

See [backend-orchestration.md](backend-orchestration.md) for the full end-to-end pipeline.

---

## Coordinator Context Forwarding (ADR-092)

> **Note:** Signal processing as a separate L3 subsystem is dissolved (ADR-092). The intelligence that previously lived in signal processing now lives in coordinator agents.

When a coordinator agent decides to create a child agent, the coordinator's review reasoning is forwarded into the child's generation context via `trigger_context`:

```python
# proactive_review.py — forward coordinator reasoning
trigger_context={
    "type": "coordinator_created",
    "coordinator_reasoning": review_result.get("reasoning", ""),
    "coordinator_id": coordinator_agent.id,
}
```

This ensures the child agent understands *why* it was created and what the coordinator determined was worth investigating.

---

## Proactive / Autonomous Agents

Proactive autonomy is implemented through **coordinator and proactive modes** (ADR-092) — entirely within backend orchestration. The agent is invoked in headless mode at the content generation step.

| Concept | Belongs in | Rationale |
|---|---|---|
| Domain awareness | Coordinator/proactive review pass (orchestration) | Agent reads sources and decides whether to act |
| Child agent creation | Coordinator agent (headless mode) | CreateAgent + AdvanceAgentSchedule primitives |
| Content generation | Agent (headless mode) | Same agent, same primitives, structured output |
| User promotes child to recurring | `promote-to-recurring` endpoint (orchestration) | `trigger_type` updated; `origin` preserved |

---

## Relationship to the Supervision Model

The [Supervision Model](supervision-model.md) covers the UI/UX dimension: agents are *objects the user supervises*, TP (chat mode) is *how they supervise*. That framing remains correct.

This document covers the *execution* dimension: how the agent produces content in each mode, and how orchestration manages everything around it.

| Document | Domain | Answers |
|---|---|---|
| Supervision Model | UI/UX, product framing | How do users interact with and supervise the system? |
| Agent Execution Model (this doc) | Backend architecture | How does the agent work? What does orchestration manage? |

---

## Anti-Patterns

**Using chat mode for agent content generation**
Chat mode is session-scoped, streaming, and latency-sensitive. Agent generation is background work. Using chat mode for agents would require session infrastructure, streaming (nobody is watching), and 15 tool rounds (unconstrained cost). Headless mode exists for this.

**Creating new agent classes for new agent complexity**
ADR-061 noted that the prior "layered agent" model (TP delegates to specialized work agents) was never realized and produced dead code. Complexity belongs in execution strategies and mode-gated primitives, not new agent classes.

**Treating the orchestration as an agent concern**
Scheduling, delivery, retention marking, version tracking — these are infrastructure, not intelligence. The orchestration pipeline calls the agent and gets text back. It does not need to understand how the agent reasons.

**Maintaining separate primitive registries for each mode**
The unified registry (ADR-080) is the only primitive source. Adding or updating a primitive means tagging it with modes — not maintaining parallel implementations.
