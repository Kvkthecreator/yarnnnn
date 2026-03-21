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

> **Note**: ADR-124 (Project Meeting Room) added a third mode — `agent_chat` — where agents participate as attributed authors in project meeting room conversations. 13 domain-scoped primitives available; PM-only write primitives (`RequestContributorAdvance`, `UpdateWorkPlan`) are role-gated at runtime. See [ADR-124](../adr/ADR-124-project-meeting-room.md). Implementation: `api/agents/chat_agent.py`.

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
- Via the **unified pulse** (ADR-126): all agents pulse via `agent_pulse.py`. Tier 1 applies deterministic gates (fresh content, budget, cooldown). Tier 2 (associate+ seniority) runs a Haiku self-assessment. Decisions are `generate | observe | wait | escalate`. Proactive self-assessment is generalized to all agents via Tier 2 — not limited to specific modes.

**Headless mode explicitly does NOT:**
- Hold session state or conversation history
- Know about delivery, retention, or version management — that is orchestration

**Coordinator/orchestration write primitives (headless only):**
Two headless-only write primitives, scoped exclusively to orchestration actions:
- `CreateAgent` — creates a child agent with `origin=coordinator_created`; headless only
- `AdvanceAgentSchedule` — advances another agent's `next_pulse_at` to now; headless only

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

### Pulse-Driven Execution (ADR-126)

> **Note (2026-03-20):** ADR-126 (Agent Pulse) reframes execution from top-down scheduling to bottom-up agent awareness. The scheduler becomes a **pulse dispatcher** — it gives each agent its turn to pulse, and acts on the agent's decision. The agent owns the generate/observe/wait/escalate decision; the scheduler just provides the cadence.

**Pulse → Generation pipeline:**
```
Pulse Dispatcher (scheduler)
├── 1. Agent pulse fires (agent_pulse.py)
│   ├── Tier 1: Deterministic checks (fresh content? budget? recent run?)
│   ├── Tier 2: Agent self-assessment (Haiku, associate+ seniority)
│   └── Decision: generate | observe | wait | escalate
├── 2. If "generate" → dispatch_trigger() routing
├── 3. Strategy selection + context gathering (ADR-045)
│   └── mandate_context injected: PROJECT.md objective + PM brief (ADR-128)
├── 4. Version creation
├── 5. Agent (mode="headless")           ← agent invocation
│   ├── Receives: gathered context + type prompt + directives + memory + learned preferences (ADR-101)
│   ├── mandate_context: project objective + PM brief + last self-assessment (ADR-128)
│   ├── Can use: Search, Read, List, WebSearch, GetSystemState, RefreshPlatformContent
│   ├── Max tool rounds: scope-aware (2-6, ADR-081/109)
│   └── Returns: structured content (text) + ## Contributor Assessment block (ADR-128)
├── 6. Assessment extraction + stripping (ADR-128)
│   ├── Parse ## Contributor Assessment from output (4 fields: mandate, fitness, currency, confidence)
│   ├── Append to memory/self_assessment.md (rolling history, 5 most recent)
│   └── Strip assessment block from draft — users never see coordination infrastructure
├── 7. Retention marking (ADR-072)
├── 8. Output to workspace + project contributions (assessment already stripped)
├── 9. PM pulse triggered (contributor output event)
└── 10. Activity logging (pulse decision + run)
```

**PM Coordination pulse:**
```
PM Pulse (Tier 3)
├── 1. PM senses project state:
│   ├── Contributor freshness, quality, work plan, budget (existing)
│   ├── Contributor self-assessments — rolling history from memory/self_assessment.md (ADR-128)
│   └── Last pulse metadata per contributor from activity_log (ADR-128)
├── 2. PM walks prerequisite layers 1→5 (ADR-128 cognitive model):
│   ├── L1 Commitment: objective completeness
│   ├── L2 Structure: right team composition for the objective
│   ├── L3 Context: required platform data available and relevant
│   ├── L4 Quality: contributor output + self-assessment trajectories
│   └── L5 Readiness: work plan, budget, assembly readiness
├── 3. PM decides: assemble | steer | advance_contributor | assess_quality | wait | escalate
├── 4. PM writes project_assessment to memory/project_assessment.md (overwrite — authoritative snapshot)
├── 5. If "assemble" → assembly composition + delivery
├── 6. If "steer" → write contribution brief to contributor
├── 7. If "advance_contributor" → trigger contributor pulse
└── 8. Activity logging (PM pulse decision)
```

**Key difference from pre-ADR-126:** The agent decides whether to generate — not the scheduler. Freshness checks, budget gates, and self-assessment all live inside the pulse, not in the scheduler's top-down logic.

**Orchestration's responsibilities (post-ADR-126):**
- **Pulse dispatch**: Give each agent its turn to pulse on cadence
- **Composer** (portfolio-only): Read pulse outcomes, make portfolio-level decisions (create/dissolve projects)
- **Execution phase**: When pulse decides "generate", select strategy, invoke headless mode, write outputs
- **Delivery**: PM-coordinated, project-level (not per-agent)

**Orchestration explicitly does NOT:**
- Decide whether agents should generate (that's the agent's pulse)
- Assess per-agent health or maturity (agents self-report via pulse)
- Participate in conversation
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

## Agent Autonomy — The Pulse Model (ADR-126)

> **Note (2026-03-20):** ADR-126 supersedes the previous "coordinator context forwarding" and "proactive/autonomous agents" sections. Proactive self-assessment is generalized to ALL agents via the pulse. Coordinator mode is dissolved — project coordination belongs to PM agents.

Every agent has a **pulse** — an autonomous sense→decide cycle that is upstream of execution. The pulse is the agent's own intelligence, not TP's supervisory capability.

| Concept | Belongs to | Mechanism |
|---|---|---|
| Domain awareness | Agent (via pulse) | Agent reads own workspace, fresh content, observations |
| Generate decision | Agent (via pulse) | Tier 1 (deterministic) or Tier 2 (self-assessment) |
| Project coordination | PM agent (via pulse Tier 3) | PM reads contributor state, decides assembly/steering/wait |
| Portfolio decisions | Composer (reads pulse outcomes) | Create/dissolve projects, rebalance workforce |
| Agent creation | Composer capability (TP) | Composer scaffolds projects + agents — not coordinator agents |

The pulse makes agent intelligence **visible**: every pulse decision (generate, observe, wait, escalate) is a surfaceable event in project meeting rooms, agent timelines, and dashboards.

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
