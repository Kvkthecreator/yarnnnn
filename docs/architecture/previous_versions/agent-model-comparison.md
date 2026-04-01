# YARNNN Agent Model: Position & Conviction

**Status:** Canonical
**Date:** 2026-03-03 (updated 2026-03-04 for ADR-092)
**Authors:** Kevin Kim, Claude (analysis)
**Related:**
- [ADR-092: Agent Intelligence & Mode Taxonomy](../adr/ADR-092-agent-intelligence-mode-taxonomy.md) — the fullest expression of this model; defines coordinator, proactive, reactive modes and dissolves signal processing
- [ADR-087: Agent Scoped Context](../adr/ADR-087-workspace-scoping-architecture.md)
- [ADR-080: Unified Agent Modes](../adr/ADR-080-unified-agent-modes.md)
- [ADR-072: Unified Content Layer](../adr/ADR-072-unified-content-layer-tp-execution-pipeline.md)
- [ADR-071: Strategic Architecture Principles](../adr/ADR-071-strategic-architecture-principles.md)
- [Agent Execution Model](agent-execution-model.md)
- [Development Landscape](../analysis/workspace-architecture-landscape.md)

---

## Purpose

This document hardens YARNNN's conviction in its own agent model. It exists to prevent architectural drift toward other models by making explicit what YARNNN is, what it is not, and why.

Every architectural decision should be tested against this document: "Does this move us toward our model, or toward someone else's?"

---

## The Three Models

### Claude Code / Cowork — The Tool Model

The agent is a powerful tool. The human holds the steering wheel. Sessions are discrete, stateless between invocations, and user-initiated. The agent has no persistent identity or accumulated understanding beyond what the user provides (CLAUDE.md, skills). Each session starts from scratch.

**Strengths:** Predictable, auditable, cost-efficient, enterprise-friendly. The agent does nothing you didn't ask for.

**Limitations:** No learning between sessions. No continuous awareness. The agent can't say "based on my last 30 runs, here's what I've noticed." Quality doesn't compound — it resets.

**Product thesis:** The LLM is the product. Better models = better output. Context is user-provided.

### OpenClaw — The Agent Model

The agent is a colleague. It has persistent identity (SOUL.md), instructions (AGENTS.md), accumulated memory (MEMORY.md + daily logs), and continuous awareness through heartbeats. A unified gateway routes all inputs (messages, crons, hooks, webhooks, heartbeats) to a Lane Queue for serial execution per workspace. The agent "lives" in its workspace.

**Strengths:** Continuous awareness, identity coherence, rich memory accumulation, unified input handling. The agent gets smarter over time without explicit user guidance.

**Limitations:** Always-on cost (heartbeats burn compute even when nothing changed). Single-workspace assumption (one agent per workspace, not many specialized agents). Personification adds product complexity (users must understand the agent's identity model). Scaling to many concurrent workspaces is architecturally expensive.

**Product thesis:** The agent relationship is the product. Accumulated context = moat. The agent understands you.

### YARNNN — The Agent Model

The agent is a network of purpose-built specialists. Each agent is a lightweight, self-contained agent: it has its own instructions, its own accumulated memory, its own sources, its own schedule, and its own output history. The agent sleeps between executions but gets smarter each time it wakes up. A unified input router decides the appropriate response to each signal — not just "generate or ignore" but a graduated spectrum from "note this" to "produce output."

**Strengths:** Multi-specialist by design (20 agents = 20 specialized agents). Cost-efficient (agents sleep when not needed). Accumulation compounds per agent (the Monday digest gets better at digests; the meeting prep gets better at meeting prep). Task-based foundation with agent-like extensions means you get predictability AND continuous improvement.

**Limitations:** No single unified agent identity (each agent is independent — they don't share context with each other unless via global user memory). Agent as container may feel unfamiliar to users expecting a single AI assistant. The "network of specialists" framing requires clear product communication.

**Product thesis:** Accumulated, specialized context is the product. Each agent carries forward everything it has learned. Quality compounds per work product, not per session.

---

## Why YARNNN Is Neither — And Shouldn't Try To Be

### Why not the Tool Model

Claude Code's sessions are stateless by design. YARNNN's agents accumulate context across every execution, every TP conversation, every platform event. A YARNNN agent that has run 50 times knows things about the user's work that a fresh Claude Code session never will — what format the user prefers, what topics spike before deadlines, which team members are most relevant to surface.

Adopting the tool model would mean discarding the accumulation moat (ADR-072) that is YARNNN's core strategic thesis.

### Why not the Agent Model

OpenClaw's always-on, single-agent-per-workspace model optimizes for continuous awareness of one work context. YARNNN serves users who have many distinct work products — a weekly digest, a meeting prep flow, a competitor tracker, a board report. Running a continuous awareness loop for each of these would be computationally wasteful. Most of the time, the right action is "note this for later," not "reason about this now."

Adopting the agent model would mean rebuilding infrastructure for a product concept (one persistent agent) that doesn't match YARNNN's multi-agent reality.

### What YARNNN takes from each

| From Claude Code | From OpenClaw | YARNNN's synthesis |
|-----------------|--------------|-------------------|
| Task-based execution (discrete triggers, clear boundaries) | Memory accumulation (the agent gets smarter over time) | Agents execute on trigger, accumulate memory between triggers |
| Mode-gated primitives (tools serve the task) | Unified input routing (one gateway for all signals) | `process_agent_input()` — one decision point, graduated response |
| Session-scoped chat (TP is conversational) | Instructions as behavioral directives (AGENTS.md) | `agent_instructions` — user-authored, per-agent |
| Orchestration boundary (pipeline manages lifecycle) | Workspace as context container | Agent as context container (instructions + memory + sources + outputs) |
| — | Heartbeats (periodic self-review) | ADR-092: `proactive` and `coordinator` modes — periodic domain review per agent, sleeping between cycles |

---

## The Agent as Lightweight Agent

After ADR-087, each agent carries:

| Component | Field | Equivalent |
|-----------|-------|-----------|
| **Identity** | `title` + `description` + `agent_type` | OpenClaw's workspace name + SOUL.md |
| **Instructions** | `agent_instructions` | OpenClaw AGENTS.md, Cowork skills, Claude Code CLAUDE.md |
| **Memory** | `agent_memory` | OpenClaw MEMORY.md + daily logs |
| **Sources** | `sources` (JSONB) → `platform_content` | OpenClaw workspace files, Claude Code source files |
| **Schedule** | `schedule` + `trigger_config` | OpenClaw HEARTBEAT.md + crons |
| **Output history** | `agent_runs` | OpenClaw agent responses (but immutable, versioned) |
| **Capabilities** | Mode-gated primitives | OpenClaw TOOLS.md |

This is a complete agent definition — without the overhead of a persistent process, a dedicated workspace directory, or an always-on awareness loop.

### What makes this distinct

**Multiplicity without overhead.** A user can have 20 agents, each with unique instructions and accumulated memory, running at different modes and frequencies. This is 20 specialized agents — with the resource cost of zero when they're not executing.

**Graduated response.** Not every signal requires full generation. Dispatch routing (ADR-088) and the review pass (ADR-092) both implement graduated response: `observe`, `sleep`, `generate`. The agent stays informed without being always-on.

**Quality compounds per specialist.** The meeting prep agent gets better at meeting prep. The coordinator watching your calendar gets better at knowing when prep is actually needed. Each agent's memory is domain-specific, not diluted across a generalized agent identity.

**Living agent experience without always-on cost.** Coordinator and proactive agents (ADR-092) provide the "feels like a living agent" experience that OpenClaw achieves with a persistent always-on process — but YARNNN achieves it with sleeping specialists. Each wakes, reviews its domain, acts if warranted, and returns to sleep. The experience is proactive and personified. The architecture is cost-efficient and cleanly bounded.

**L3 is genuinely dumb.** Platform sync populates `platform_content`. Downstream consumers mark content retained. Nothing reasons at L3. Signal processing — which was L3 infrastructure doing L4 intelligence work — is dissolved (ADR-092). All intelligence lives in agents.

---

## A2A and Multi-Agent Future

In the Agent-to-Agent landscape (Google A2A protocol, MCP tool use, multi-agent orchestration), agents need to describe themselves, communicate capabilities, and negotiate task handoffs.

A YARNNN agent is already an agent card:
- **Name and purpose:** title + description
- **Capabilities:** agent_type + sources + primitives
- **Knowledge:** agent_memory
- **How to trigger:** schedule + trigger_config
- **What it produces:** agent_type + output history

The agent model is natively multi-agent. Each agent can participate in an A2A network as a specialized agent. This is harder to achieve with a single-agent model (OpenClaw would need to expose sub-workspace capabilities) and impossible with a stateless tool model (Claude Code has no persistent agent identity to advertise).

---

## Architectural Principles (Restated for the Agent Model)

These extend ADR-071's strategic principles with model-specific conviction:

### 1. The agent is the unit of work AND the unit of intelligence

A agent doesn't just produce output — it accumulates understanding. Every execution, every TP conversation, every platform event enriches its memory. The agent is simultaneously a configuration (what to produce), a specialist (how to produce it well), and a knowledge base (what it has learned about this work).

### 2. Sleep is a feature, not a limitation

Unlike always-on agents, YARNNN's agents sleep between triggers. This is a design choice, not a compromise. Sleep means: zero cost when idle, no wasted computation, no hallucinated activity. When the agent wakes, it has everything it needs in its memory and instructions. The quality of waking is what matters, not the continuity of awareness.

### 3. Accumulation is the moat — per agent

Global user memory (`user_memory`) captures cross-cutting preferences. But the real compounding happens at the agent level. A agent that has run 50 times carries 50 sessions of feedback patterns, observations, and session summaries. This is a moat that resets to zero if the user switches to any tool-based alternative.

### 4. Graduated response preserves the task-based foundation

Full generation is expensive and often unnecessary. The graduated response model (high → generate, medium → update memory, low → log) preserves the task-based execution model while enabling continuous awareness. The agent doesn't need to be always-on to be always-informed.

### 5. Orchestration stays outside the agent

The delivery pipeline, scheduling, retention marking, version tracking — these are infrastructure. The agent is invoked at one step, produces text, and returns. This boundary (from ADR-080) ensures the agent model stays clean regardless of how complex the orchestration becomes.

---

## Decision Tests

When evaluating an architectural proposal, ask:

1. **Does this strengthen the agent as the unit of intelligence?** If the proposal requires shared state between agents, or a global agent process, it's drifting toward the agent model.

2. **Does this maintain sleep efficiency?** If the proposal requires continuous background processing per agent, it's drifting toward the agent model. Periodic is fine; continuous is a red flag.

3. **Does this compound quality per specialist?** If the proposal improves all agents generically rather than each one specifically, it may be worthwhile but doesn't leverage the agent model's strength.

4. **Does this keep the graduated response?** If the proposal can only produce full output (no lighter actions), it's reverting to the binary trigger model that ADR-088 addresses.

5. **Does this respect the orchestration boundary?** If the proposal requires the agent to know about scheduling, delivery, or version management, it's violating ADR-080.

---

## Evolution: Two-Layer Intelligence and Autonomy-First (2026-03-16)

The original comparison above (March 2026) accurately captures the agent-side model. FOUNDATIONS.md v2 adds two critical dimensions that affect how YARNNN relates to both benchmarks:

### Two-Layer Intelligence

YARNNN has a meta-cognitive layer (TP) that neither Claude Code nor OpenClaw have in the same form:

- **Claude Code**: No meta-layer. User is the orchestrator.
- **OpenClaw**: Single agent per workspace. The agent is both domain-cognitive and self-orchestrating (heartbeat = self-assessment). No separation between "who decides what to do" and "who does it."
- **YARNNN**: TP (meta-cognitive) orchestrates and composes. Agents (domain-cognitive) execute. TP creates agents, monitors their health, adjusts their configuration, dissolves them. Agents develop domain expertise but don't manage their own lifecycle.

This means YARNNN takes OpenClaw's heartbeat pattern but applies it **at the meta-cognitive layer** — TP periodically assesses the whole agent workforce, not each agent self-assessing. The cost savings of sleep-between-triggers (Principle 2 above) are preserved for agents; the awareness is centralized in TP's heartbeat.

### Platform Content as Onramp, Not Engine

The original comparison implicitly frames platform sync as the ongoing fuel for agents. The refined model:

- **Platform content is the onramp** — it seeds context, meets users where their work lives, and jumpstarts agent work from existing data
- **As agent quality improves, platform dependency decreases** — the agents' own outputs, observations, theses, and cross-references become the primary substrate (Axiom 2: recursive perception)
- **The enduring moat is recursive accumulation**, not breadth of platform integrations

This strengthens YARNNN's position relative to both benchmarks: Claude Code has no accumulation at all; OpenClaw accumulates within a single workspace but doesn't have the multi-agent recursive substrate where one agent's output feeds another agent's input.

### Autonomy as Architecture

The original comparison describes YARNNN as "task-based foundation with agent-like extensions." The hardened framing:

- **Autonomy is the default architecture**, not a feature layered on top of tasks
- **TP's bias is toward action** — create agents, configure them, let feedback correct
- **The user's role shifts from directing to supervising** as tenure increases

This is a stronger position than "feels like a living agent" (Principle from the original). It's: **the system works for you from the moment you connect**. The sophistication of what it does increases with accumulated judgment.

### Updated Decision Tests

Add to the existing five:

6. **Does this strengthen TP's compositional authority?** If the proposal requires agents to self-orchestrate (create other agents, decide their own lifecycle), it's undermining the two-layer model.

7. **Does this reduce platform dependency over time?** If the proposal makes agents more dependent on fresh platform data rather than accumulated substrate, it's drifting away from the recursive perception model.

---

## What This Document Is Not

This is not an argument that YARNNN's model is objectively superior. It's an argument that YARNNN's model is the right one for YARNNN's product thesis — many specialized work products that improve with use. Other models serve other theses well.

This document exists to prevent the architectural gravity of larger projects (Claude Code's ecosystem, OpenClaw's community momentum) from pulling YARNNN away from its own position. Comparison is for learning; conviction is for building.

---

## References

- [ADR-038: Filesystem as Context](../adr/ADR-038-filesystem-as-context.md) — the original Claude Code comparison
- [ADR-072: Unified Content Layer](../adr/ADR-072-unified-content-layer-tp-execution-pipeline.md) — accumulation moat thesis
- [ADR-087: Agent Scoped Context](../adr/ADR-087-workspace-scoping-architecture.md) — the schema that completes the agent as agent
- [Pre-ADR Analysis](../analysis/workspace-architecture-analysis-2026-03-02.md) — full OpenClaw comparison (v4, Section 12)
- [Development Landscape](../analysis/workspace-architecture-landscape.md) — implementation sequence
- [FOUNDATIONS.md](FOUNDATIONS.md) — canonical axioms (two-layer intelligence, recursive perception, autonomy as direction)
- [TP Composer Autonomy Analysis](../analysis/tp-composer-autonomy-analysis.md) — TP heartbeat, auto-create posture, OpenClaw/Claude SDK benchmarks
