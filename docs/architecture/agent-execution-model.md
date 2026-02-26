# Architecture: Agent Execution Model

**Status:** Canonical
**Date:** 2026-02-26 (updated for ADR-080 unified agent modes)
**Supersedes:** ADR-016 (Layered Agent Architecture) — work agent delegation model
**Codifies:** ADR-080 (Unified Agent Modes) — evolves ADR-061 two-path separation into one agent with modal execution
**Related:**
- [ADR-080: Unified Agent Modes](../adr/ADR-080-unified-agent-modes.md) — governing ADR
- [ADR-061: Two-Path Architecture](../adr/ADR-061-two-path-architecture.md) — predecessor (superseded by ADR-080)
- [ADR-068: Signal-Emergent Deliverables](../adr/ADR-068-signal-emergent-deliverables.md) — extends orchestration with signal processing phase
- [ADR-042: Deliverable Execution Simplification](../adr/ADR-042-deliverable-execution-simplification.md)
- [ADR-045: Deliverable Orchestration Redesign](../adr/ADR-045-deliverable-orchestration-redesign.md)
- [Supervision Model](supervision-model.md) — the complementary UI/UX framing

---

## The Core Principle

YARNNN has one agent with two execution modes. The agent powers both interactive chat and background content generation. Backend orchestration is separate from the agent — it manages scheduling, delivery, retention, and lifecycle.

**The agent** reasons over content using primitives. It produces text.

**The orchestration pipeline** manages everything around the agent: triggers, freshness checks, strategy selection, version tracking, delivery, retention marking. It invokes the agent at one step and receives text back.

---

## One Agent, Two Modes

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
- Create and configure deliverables when the user explicitly asks
- Read and explain existing deliverable versions

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
| Primitives | Curated subset (read-only investigation) |
| Max tool rounds | 3 |
| System prompt | Type-specific structured output |
| Entry point | `generate_draft_inline()` in deliverable pipeline |
| LLM function | `chat_completion_with_tools()` |

**Headless mode responsibilities:**
- Generate deliverable content from gathered context
- Investigate supplementary context via primitives when the gathered context is insufficient
- Produce structured, formatted output following type-specific templates

**Headless mode explicitly does NOT:**
- Hold session state or conversation history
- Execute write operations (create deliverables, send messages, update preferences)
- Know about delivery, retention, or version management — that is orchestration

---

## Mode-Gated Primitives (ADR-080)

Primitives declare which modes they are available in. One registry, one maintenance track.

```python
PRIMITIVE_MODES = {
    # Read-only investigation — both modes
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

When a primitive is updated or added, it is tagged with modes. Updates improve both modes simultaneously. No drift.

---

## The Orchestration Boundary

Backend orchestration is NOT agent work. The orchestration pipeline invokes the agent at one step and receives text back.

```
Backend Orchestration
├── 1. Trigger (scheduler / manual / signal)
├── 2. Freshness check (ADR-049)
├── 3. Strategy selection + context gathering (ADR-045)
├── 4. Version + ticket creation
├── 5. Agent (mode="headless")           ← agent invocation
│   ├── Receives: gathered context + type prompt + signal reasoning
│   ├── Can use: Search, FetchPlatformContent, CrossPlatformQuery
│   ├── Cannot use: CreateDeliverable, UpdatePreferences, UI actions
│   ├── Max 3 tool rounds
│   └── Returns: structured content (text)
├── 6. Retention marking (ADR-072)
├── 7. Source snapshots (ADR-049)
├── 8. Delivery — email, Slack, Notion (ADR-066, no approval gate)
└── 9. Activity logging
```

**Orchestration's responsibilities:**
- **Signal Processing phase** (ADR-068): Extract behavioral signals from `platform_content`, reason over what the user's world warrants, create/trigger deliverables
- **Analysis phase** (ADR-060): Mine TP session content for recurring patterns, create analyst-suggested deliverables
- **Execution phase**: Execute deliverables on schedule or on manual trigger, select execution strategy, invoke agent in headless mode, deliver outputs, mark content retained

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
→ Agent (chat mode) calls CreateDeliverable primitive
→ Agent responds: "Created. It will run every Monday at 9 AM."

# Headless mode: Background, non-streaming, curated primitives
# api/services/deliverable_execution.py → api/services/anthropic.py

unified_scheduler.py (cron)
  → execute_deliverable_generation(client, user_id, deliverable)
      → get_execution_strategy(deliverable)        # orchestration
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

| Binding | Strategy | Data Source |
|---|---|---|
| `platform_bound` | `PlatformBoundStrategy` | `platform_content` from single platform |
| `cross_platform` | `CrossPlatformStrategy` | `platform_content` from all platforms |
| `research` | `ResearchStrategy` | Web research via Anthropic native tool |
| `hybrid` | `HybridStrategy` | Web research + platform content in parallel |

Strategy is selected at execution time from `deliverable.type_classification.binding`. All strategies read from stored `platform_content` (ADR-073). The agent in headless mode receives the gathered context in its prompt and can supplement it with primitive calls.

See [backend-orchestration.md](backend-orchestration.md) for the full end-to-end pipeline.

---

## Signal Context Forwarding (ADR-080)

Signal processing reasons about the user's platform world (Haiku LLM call), producing `reasoning_summary` with cross-platform patterns and entity identification. Previously, this reasoning was discarded before deliverable generation — `trigger_context={"type": "signal_emergent"}` passed zero intelligence.

ADR-080 requires forwarding signal reasoning into the headless mode prompt:

```python
# signal_processing.py — forward reasoning
trigger_context={
    "type": "signal_emergent",
    "signal_reasoning": action.signal_context.get("reasoning_summary", ""),
    "signal_type": action.signal_context.get("signal_type", ""),
}

# generate_draft_inline() — inject into headless system prompt
if trigger_context.get("signal_reasoning"):
    system_prompt += f"\n\nSIGNAL CONTEXT: {trigger_context['signal_reasoning']}"
```

This closes the intelligence gap where signal processing knew *why* a deliverable should exist but that reasoning was lost before generation.

---

## What This Means for Proactive / Autonomous Deliverables

The proactive autonomy roadmap is implemented through **ADR-068: Signal-Emergent Deliverables** — entirely within backend orchestration. The agent is invoked in headless mode at the content generation step.

| Concept | Belongs in | Rationale |
|---|---|---|
| "What happened in user's world?" | Signal Processing (orchestration) | Deterministic extraction from `platform_content`, no agent |
| "What does this warrant?" | Signal Processing (orchestration) | Single Haiku LLM call over signal summary |
| Content generation for signal-emergent deliverable | Agent (headless mode) | Same agent, same primitives, structured output |
| Drift detection, conflict detection, meeting prep | Signal-emergent deliverable creation (orchestration) | `origin=signal_emergent`, `trigger_type=manual` |
| User promotes output to recurring | `promote-to-recurring` endpoint (orchestration) | `trigger_type` updated; `origin` preserved |

---

## Relationship to the Supervision Model

The [Supervision Model](supervision-model.md) covers the UI/UX dimension: deliverables are *objects the user supervises*, TP (chat mode) is *how they supervise*. That framing remains correct.

This document covers the *execution* dimension: how the agent produces content in each mode, and how orchestration manages everything around it.

| Document | Domain | Answers |
|---|---|---|
| Supervision Model | UI/UX, product framing | How do users interact with and supervise the system? |
| Agent Execution Model (this doc) | Backend architecture | How does the agent work? What does orchestration manage? |

---

## Anti-Patterns

**Using chat mode for deliverable content generation**
Chat mode is session-scoped, streaming, and latency-sensitive. Deliverable generation is background work. Using chat mode for deliverables would require session infrastructure, streaming (nobody is watching), and 15 tool rounds (unconstrained cost). Headless mode exists for this.

**Creating new agent classes for new deliverable complexity**
ADR-061 noted that the prior "layered agent" model (TP delegates to specialized work agents) was never realized and produced dead code. Complexity belongs in execution strategies and mode-gated primitives, not new agent classes.

**Treating the orchestration as an agent concern**
Scheduling, delivery, retention marking, version tracking — these are infrastructure, not intelligence. The orchestration pipeline calls the agent and gets text back. It does not need to understand how the agent reasons.

**Maintaining separate primitive registries for each mode**
The unified registry (ADR-080) is the only primitive source. Adding or updating a primitive means tagging it with modes — not maintaining parallel implementations.
