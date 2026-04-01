# ADR-103: Agentic Framework Reframe

**Status:** Accepted
**Date:** 2026-03-10
**Authors:** Kevin Kim, Claude (analysis)
**Supersedes:** Portions of naming-conventions.md (Tier 1 vocabulary for "Agent")
**Updates:**
- [Agent Model Comparison](../architecture/agent-model-comparison.md) — reframes YARNNN's model position
- [Naming Conventions](../architecture/naming-conventions.md) — revises Tier 1 vocabulary
- [ESSENCE.md](../ESSENCE.md) — repositions product thesis
- [GTM_POSITIONING.md](../GTM_POSITIONING.md) — revises competitive positioning
**Related:**
- [ADR-092: Agent Intelligence & Mode Taxonomy](ADR-092-agent-intelligence-mode-taxonomy.md)
- [ADR-101: Agent Intelligence Model](ADR-101-agent-intelligence-model.md)
- [ADR-080: Unified Agent Modes](ADR-080-unified-agent-modes.md)
- [ADR-072: Unified Content Layer](ADR-072-unified-content-layer-tp-execution-pipeline.md)

---

## Context

YARNNN's architecture has organically evolved into an autonomous agent framework. The codebase already implements:

- **Persistent autonomous agents** with identity, memory, instructions, scheduled execution, feedback learning, and five distinct execution modes (recurring, goal, reactive, proactive, coordinator)
- **An orchestrator agent** (TP) with full tool access, user memory injection, and the ability to create/manage sub-agents
- **A mode-gated capability registry** (primitives) governing what each agent can do in each execution context
- **A perception pipeline** (platform sync) feeding a shared knowledge base (platform_content)
- **A meta-agent** (coordinator mode) that spawns and directs other agents

However, the terminology — rooted in the original "agent generation platform" framing — obscures this reality. Strategic conversations, investor communication, developer onboarding, and competitive positioning all require a translation layer between what the system *is* and what it's *called*.

### Market Context (March 2026)

The AI landscape has shifted decisively toward agentic execution:

- **Microsoft Copilot Cowork** (March 9, 2026): Multi-step task execution across M365, built on Anthropic's Claude. Intent → plan → execution → checkpoints. Running on Work IQ (Microsoft Graph + contextual reasoning). Enterprise pricing at $99/user E7 tier.
- **Claude Cowork** (January 2026): Desktop agent with computer use. Plan → execute → check → deliver. Session-based, file-system-native.
- **Claude Code**: Agentic coding with persistent project context (CLAUDE.md), tool use, and multi-step execution.
- **OpenClaw**: Always-on persistent agent with identity, memory, and continuous awareness.

The common pattern: **agents that execute work, not assistants that respond to prompts.** Context is an implementation detail of execution quality, not the product itself.

YARNNN's architecture is aligned with this direction — but the vocabulary is not. "Agent" communicates output artifacts. "Agent" communicates autonomous execution. The product already does the latter; the language should catch up.

### The Naming Decision That Changed

The previous naming-conventions.md explicitly chose "Agent" over "Agent" with this rationale:

> "Task" implies one-time. "Workflow" implies multi-step process. "Agent" implies autonomous entity. "Agent" implies recurring, specialized, improving output.

This was correct when agents were primarily scheduled content generation configs. After ADR-087 (per-agent instructions and memory), ADR-092 (five execution modes including proactive and coordinator), and ADR-101 (four-layer intelligence model with feedback learning), agents **are** autonomous entities. The naming rationale is now self-defeating — we chose "Agent" to avoid implying autonomous entity, but the system became exactly that.

---

## Decision

### 1. Adopt agent-native vocabulary across documentation, positioning, and future development

The following terminology mapping establishes the new canonical vocabulary:

#### Core Entity Rename

| Current term | New term | Scope | Rationale |
|---|---|---|---|
| Agent | **Agent** | Docs, positioning, investor comms, future UI | The entity has identity, memory, instructions, capabilities, and execution autonomy. It is an agent. |
| Agent type (digest, brief, status...) | **Agent archetype** | Docs, positioning | Pre-configured skill set and output format for an agent |
| Agent mode (recurring, goal, reactive, proactive, coordinator) | **Execution mode** | No change needed | Already accurate |
| Agent instructions | **Agent directives** | Docs, positioning | User-authored behavioral programming for a persistent agent |
| Agent memory | **Agent memory** | Docs, positioning | System-accumulated operational state |
| Agent versions | **Agent outputs** (or **runs**) | Docs, positioning | The artifact produced per execution cycle |
| Thinking Partner (TP) | **Orchestrator** | Docs, positioning | The user-facing agent that manages the agent network. TP remains as internal code abbreviation. |

#### System Layer Rename

| Current term | New term | Rationale |
|---|---|---|
| Platform sync | **Perception pipeline** | How agents sense the external world |
| Platform content | **Knowledge base** | The shared substrate agents reason over |
| Working memory | **Runtime context** | What gets assembled into an agent's prompt at execution time |
| Primitives | **Capabilities** (externally) / **Primitives** (internally) | External vocabulary should be accessible; internal can stay precise |
| Feedback loop (edit distance, learned preferences) | **Learning loop** | How agents improve from human corrections |
| Orchestration pipeline | **Execution pipeline** | The infrastructure managing agent lifecycle |
| Context accumulation | **Knowledge accumulation** | Avoids the overloaded term "context" |

#### Architectural Framing

| Current framing | New framing |
|---|---|
| "Agent generation platform with context accumulation" | "Autonomous agent platform for recurring knowledge work" |
| "Each agent is a lightweight specialist agent" | "Each agent is a persistent, sleeping specialist" |
| "The accumulation moat" | "Knowledge accumulation as agent intelligence" |
| "Sleep is a feature" | "Sleep-wake architecture" — agents sleep between executions, wake fully informed |
| "Supervision model" | "Human-in-the-loop agent supervision" |

### 2. Phased implementation — documentation first, code later

**Phase 0 (Pre-Thursday, this ADR):** Establish vocabulary. Write investor-facing architecture document using new terminology. Update ESSENCE.md and GTM_POSITIONING.md.

**Phase 1 (Post-Thursday, documentation):** Update all docs/architecture/*.md, docs/features/*.md, and relevant ADRs to use new vocabulary. Update naming-conventions.md as the canonical reference.

**Phase 2 (Future, frontend):** Update UI labels — "Work" nav → "Agents", agent cards use agent language, creation flow uses agent framing.

**Phase 3 (Future, backend):** Rename code variables, API routes, and eventually DB columns. This is the most disruptive phase and should be carefully sequenced.

### 3. Preserve "agent" where it remains accurate

The word "agent" doesn't disappear — it describes what agents *produce*. An agent produces agents (outputs). The entity itself is an agent. This mirrors human organizations: a consultant (agent) produces agents (outputs). The consultant is not called "a agent."

### 4. Reposition the product thesis

**Previous thesis:** "Context accumulation enables meaningful autonomy."

**Updated thesis:** "Persistent agents with accumulated knowledge do recurring work better than any session-based alternative."

The shift is subtle but important:
- **Before:** Context is the product; autonomy is the feature enabled by context.
- **After:** Agents are the product; accumulated knowledge is what makes them excellent.

This aligns with the macro market direction (agents as the work abstraction) while preserving YARNNN's genuine differentiator (persistence, memory, sleep-wake architecture, feedback learning).

---

## Competitive Positioning Under New Framing

### vs. Microsoft Copilot Cowork
"Copilot Cowork requires you to hand off a task. YARNNN agents run autonomously — on schedule, proactively, or in response to events — without anyone asking. They're persistent specialists, not session-based assistants."

### vs. Claude Cowork
"Claude Cowork is session-based: you start a task, it executes, the session ends. YARNNN agents persist across time. They accumulate memory from every execution, learn from your corrections, and produce better output on their 50th run than their 1st. No session to start. No context to re-establish."

### vs. OpenClaw
"OpenClaw runs one always-on agent per workspace. YARNNN runs many sleeping specialists — each with its own memory, instructions, and execution mode. Twenty agents at zero idle cost, each improving at its specific job."

### The YARNNN difference (summary)
| Dimension | Copilot Cowork | Claude Cowork | OpenClaw | YARNNN |
|---|---|---|---|---|
| Initiation | User hands off task | User starts session | Always-on heartbeat | **Scheduled, proactive, or event-driven** |
| Persistence | None (task-scoped) | None (session-scoped) | Single workspace agent | **Many persistent agents** |
| Memory | Work IQ (platform data) | Filesystem access | MEMORY.md per workspace | **Per-agent memory + global user memory** |
| Learning | None | None | Accumulated logs | **Feedback loop from user edits** |
| Multi-agent | No | No | One per workspace | **Native: coordinator spawns/directs agents** |
| Idle cost | N/A | N/A | Heartbeat compute | **Zero (sleep-wake)** |

---

## What Doesn't Change

- **Code internals:** `agent_execution.py`, `agents` table, `agent_runs` table — all stay as-is for now. The code works; renaming is Phase 3.
- **TP as internal identifier:** The codebase uses "TP" as a system abbreviation. This continues. The user-facing and investor-facing term becomes "Orchestrator" or is kept as brand name.
- **Architecture:** No architectural changes. The system already implements the agentic model. This ADR changes how we talk about it, not how it works.
- **Primitive terminology internally:** "Primitives" stays in code. "Capabilities" is used in external communication.

---

## Risks

1. **"Agent" is overloaded.** Every AI company says "agents" in 2026. Risk: YARNNN becomes one of many "agent platforms." Mitigation: the differentiator is specific — *persistent sleeping specialists with per-agent memory and feedback learning*. No one else has this exact model.

2. **Terminology churn.** This is the second vocabulary revision (after naming-conventions.md established "Agent"). Risk: team confusion, doc rot. Mitigation: Phased rollout. Documentation first. Code last. Each phase is independently valuable.

3. **"Agent" had product clarity.** It communicated tangible output. Risk: losing that specificity. Mitigation: "Agent" is the entity; "agent" is what it produces. Both words survive.

---

## Consequences

- All new documentation, ADRs, and positioning materials use agent-native vocabulary
- naming-conventions.md is updated to reflect the new Tier 1 vocabulary
- ESSENCE.md is updated to frame YARNNN as an autonomous agent platform
- GTM_POSITIONING.md is updated with new competitive positioning
- An investor-facing architecture document is created using the new vocabulary
- Code, API routes, and database remain unchanged until Phase 3
- The word "agent" continues to describe agent outputs, not the agent itself

---

## References

- [Microsoft Copilot Cowork announcement (March 9, 2026)](https://www.microsoft.com/en-us/microsoft-365/blog/2026/03/09/copilot-cowork-a-new-way-of-getting-work-done/)
- [Claude Cowork (Anthropic)](https://support.claude.com/en/articles/13345190-get-started-with-cowork)
- naming-conventions.md — previous vocabulary standard (partially superseded)
- agent-model-comparison.md — YARNNN's model conviction (updated by this ADR)
