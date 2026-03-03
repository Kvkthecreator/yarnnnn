# YARNNN Agent Model: Position & Conviction

**Status:** Canonical
**Date:** 2026-03-03
**Authors:** Kevin Kim, Claude (analysis)
**Related:**
- [ADR-087: Deliverable Scoped Context](../adr/ADR-087-workspace-scoping-architecture.md)
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

### YARNNN — The Deliverable Model

The agent is a network of purpose-built specialists. Each deliverable is a lightweight, self-contained agent: it has its own instructions, its own accumulated memory, its own sources, its own schedule, and its own output history. The agent sleeps between executions but gets smarter each time it wakes up. A unified input router decides the appropriate response to each signal — not just "generate or ignore" but a graduated spectrum from "note this" to "produce output."

**Strengths:** Multi-specialist by design (20 deliverables = 20 specialized agents). Cost-efficient (agents sleep when not needed). Accumulation compounds per deliverable (the Monday digest gets better at digests; the meeting prep gets better at meeting prep). Task-based foundation with agent-like extensions means you get predictability AND continuous improvement.

**Limitations:** No single unified agent identity (each deliverable is independent — they don't share context with each other unless via global user memory). Deliverable as container may feel unfamiliar to users expecting a single AI assistant. The "network of specialists" framing requires clear product communication.

**Product thesis:** Accumulated, specialized context is the product. Each deliverable carries forward everything it has learned. Quality compounds per work product, not per session.

---

## Why YARNNN Is Neither — And Shouldn't Try To Be

### Why not the Tool Model

Claude Code's sessions are stateless by design. YARNNN's deliverables accumulate context across every execution, every TP conversation, every platform event. A YARNNN deliverable that has run 50 times knows things about the user's work that a fresh Claude Code session never will — what format the user prefers, what topics spike before deadlines, which team members are most relevant to surface.

Adopting the tool model would mean discarding the accumulation moat (ADR-072) that is YARNNN's core strategic thesis.

### Why not the Agent Model

OpenClaw's always-on, single-agent-per-workspace model optimizes for continuous awareness of one work context. YARNNN serves users who have many distinct work products — a weekly digest, a meeting prep flow, a competitor tracker, a board report. Running a continuous awareness loop for each of these would be computationally wasteful. Most of the time, the right action is "note this for later," not "reason about this now."

Adopting the agent model would mean rebuilding infrastructure for a product concept (one persistent agent) that doesn't match YARNNN's multi-deliverable reality.

### What YARNNN takes from each

| From Claude Code | From OpenClaw | YARNNN's synthesis |
|-----------------|--------------|-------------------|
| Task-based execution (discrete triggers, clear boundaries) | Memory accumulation (the agent gets smarter over time) | Deliverables execute on trigger, accumulate memory between triggers |
| Mode-gated primitives (tools serve the task) | Unified input routing (one gateway for all signals) | `process_deliverable_input()` — one decision point, graduated response |
| Session-scoped chat (TP is conversational) | Instructions as behavioral directives (AGENTS.md) | `deliverable_instructions` — user-authored, per-deliverable |
| Orchestration boundary (pipeline manages lifecycle) | Workspace as context container | Deliverable as context container (instructions + memory + sources + outputs) |
| — | Heartbeats (periodic self-review) | ADR-089: periodic workspace review per deliverable (when validated) |

---

## The Deliverable as Lightweight Agent

After ADR-087, each deliverable carries:

| Component | Field | Equivalent |
|-----------|-------|-----------|
| **Identity** | `title` + `description` + `deliverable_type` | OpenClaw's workspace name + SOUL.md |
| **Instructions** | `deliverable_instructions` | OpenClaw AGENTS.md, Cowork skills, Claude Code CLAUDE.md |
| **Memory** | `deliverable_memory` | OpenClaw MEMORY.md + daily logs |
| **Sources** | `sources` (JSONB) → `platform_content` | OpenClaw workspace files, Claude Code source files |
| **Schedule** | `schedule` + `trigger_config` | OpenClaw HEARTBEAT.md + crons |
| **Output history** | `deliverable_versions` | OpenClaw agent responses (but immutable, versioned) |
| **Capabilities** | Mode-gated primitives | OpenClaw TOOLS.md |

This is a complete agent definition — without the overhead of a persistent process, a dedicated workspace directory, or an always-on awareness loop.

### What makes this distinct

**Multiplicity without overhead.** A user can have 20 deliverables, each with unique instructions and accumulated memory, running at different frequencies, watching different sources. This is 20 specialized agents — with the resource cost of zero when they're not executing.

**Graduated response.** Not every signal requires full generation. With unified input processing (ADR-088), the system can note observations in `deliverable_memory` (cheap, Haiku-level) or trigger full generation (expensive, Opus-level) based on signal strength. The agent stays informed without being always-on.

**Quality compounds per specialist.** The meeting prep deliverable gets better at meeting prep. The competitor tracker gets better at tracking competitors. Each deliverable's memory is domain-specific, not diluted across a generalized agent identity.

---

## A2A and Multi-Agent Future

In the Agent-to-Agent landscape (Google A2A protocol, MCP tool use, multi-agent orchestration), agents need to describe themselves, communicate capabilities, and negotiate task handoffs.

A YARNNN deliverable is already an agent card:
- **Name and purpose:** title + description
- **Capabilities:** deliverable_type + sources + primitives
- **Knowledge:** deliverable_memory
- **How to trigger:** schedule + trigger_config
- **What it produces:** deliverable_type + output history

The deliverable model is natively multi-agent. Each deliverable can participate in an A2A network as a specialized agent. This is harder to achieve with a single-agent model (OpenClaw would need to expose sub-workspace capabilities) and impossible with a stateless tool model (Claude Code has no persistent agent identity to advertise).

---

## Architectural Principles (Restated for the Deliverable Model)

These extend ADR-071's strategic principles with model-specific conviction:

### 1. The deliverable is the unit of work AND the unit of intelligence

A deliverable doesn't just produce output — it accumulates understanding. Every execution, every TP conversation, every platform event enriches its memory. The deliverable is simultaneously a configuration (what to produce), a specialist (how to produce it well), and a knowledge base (what it has learned about this work).

### 2. Sleep is a feature, not a limitation

Unlike always-on agents, YARNNN's deliverables sleep between triggers. This is a design choice, not a compromise. Sleep means: zero cost when idle, no wasted computation, no hallucinated activity. When the deliverable wakes, it has everything it needs in its memory and instructions. The quality of waking is what matters, not the continuity of awareness.

### 3. Accumulation is the moat — per deliverable

Global user memory (`user_memory`) captures cross-cutting preferences. But the real compounding happens at the deliverable level. A deliverable that has run 50 times carries 50 sessions of feedback patterns, observations, and session summaries. This is a moat that resets to zero if the user switches to any tool-based alternative.

### 4. Graduated response preserves the task-based foundation

Full generation is expensive and often unnecessary. The graduated response model (high → generate, medium → update memory, low → log) preserves the task-based execution model while enabling continuous awareness. The agent doesn't need to be always-on to be always-informed.

### 5. Orchestration stays outside the agent

The delivery pipeline, scheduling, retention marking, version tracking — these are infrastructure. The agent is invoked at one step, produces text, and returns. This boundary (from ADR-080) ensures the agent model stays clean regardless of how complex the orchestration becomes.

---

## Decision Tests

When evaluating an architectural proposal, ask:

1. **Does this strengthen the deliverable as the unit of intelligence?** If the proposal requires shared state between deliverables, or a global agent process, it's drifting toward the agent model.

2. **Does this maintain sleep efficiency?** If the proposal requires continuous background processing per deliverable, it's drifting toward the agent model. Periodic is fine; continuous is a red flag.

3. **Does this compound quality per specialist?** If the proposal improves all deliverables generically rather than each one specifically, it may be worthwhile but doesn't leverage the deliverable model's strength.

4. **Does this keep the graduated response?** If the proposal can only produce full output (no lighter actions), it's reverting to the binary trigger model that ADR-088 addresses.

5. **Does this respect the orchestration boundary?** If the proposal requires the agent to know about scheduling, delivery, or version management, it's violating ADR-080.

---

## What This Document Is Not

This is not an argument that YARNNN's model is objectively superior. It's an argument that YARNNN's model is the right one for YARNNN's product thesis — many specialized work products that improve with use. Other models serve other theses well.

This document exists to prevent the architectural gravity of larger projects (Claude Code's ecosystem, OpenClaw's community momentum) from pulling YARNNN away from its own position. Comparison is for learning; conviction is for building.

---

## References

- [ADR-038: Filesystem as Context](../adr/ADR-038-filesystem-as-context.md) — the original Claude Code comparison
- [ADR-072: Unified Content Layer](../adr/ADR-072-unified-content-layer-tp-execution-pipeline.md) — accumulation moat thesis
- [ADR-087: Deliverable Scoped Context](../adr/ADR-087-workspace-scoping-architecture.md) — the schema that completes the deliverable as agent
- [Pre-ADR Analysis](../analysis/workspace-architecture-analysis-2026-03-02.md) — full OpenClaw comparison (v4, Section 12)
- [Development Landscape](../analysis/workspace-architecture-landscape.md) — implementation sequence
