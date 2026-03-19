# Design Principle: The Supervision Model

**Status:** Canonical — UI/UX and product framing only
**Scope:** Covers how users interact with and supervise the system (UI/UX, product model). Does NOT cover backend execution paths — see [Agent Execution Model](agent-execution-model.md) for that.
**Date:** 2026-02-02
**Related:**
- [Agent Execution Model](agent-execution-model.md) — unified agent (chat + headless modes), orchestration boundary
- [ADR-080: Unified Agent Modes](../adr/ADR-080-unified-agent-modes.md) — supersedes ADR-061
- [ADR-061: Two-Path Architecture](../adr/ADR-061-two-path-architecture.md) — historical (superseded by ADR-080)
- [ADR-013: Conversation + Surfaces](../adr/ADR-013-conversation-plus-surfaces.md)
- [ADR-018: Recurring Agents](../adr/ADR-018-recurring-agents.md)
- [ADR-020: Agent-Centric Chat](../adr/ADR-020-agent-centric-chat.md)
- [Strategic Direction](../strategy/YARNNN_STRATEGIC_DIRECTION.md)

---

## The Core Insight

YARNNN's architecture serves a fundamental shift in how users relate to AI-assisted work:

**From**: User as operator (does the work, AI assists)
**To**: User as supervisor (AI does the work, user oversees)

This shift has specific implications for how we think about agents and TP (Thinking Partner).

---

## The Two Dimensions

### Agents: Objects of Supervision

Agents are **first-class data entities**. They represent:

- What the system produces
- What the user supervises
- What accumulates value over time
- The units of measurable quality

From a data and workflow perspective, agents are the core product. They have:
- Versions (each execution produces a new one)
- Feedback (user edits captured and categorized)
- Quality metrics (edit distance decreasing over time)
- History (the 10th delivery is better than the 1st)

### TP: Method of Supervision

TP is the **first-class interaction surface**. It represents:

- How users communicate intent
- How users exercise supervision
- How users refine and improve artifacts
- The interface for delegation

From a UI/UX perspective, TP is how users interact with the system. It provides:
- Contextual awareness (knows what user is looking at)
- Natural language interaction (conversational or direct)
- Tool execution (creates, modifies, explains)
- Memory and continuity (witnessed existence)

---

## The Reconciliation

These two dimensions are not in conflict—they're complementary:

| Dimension | Agents | TP |
|-----------|--------------|-----|
| **Role** | Data entities | Interaction surface |
| **What they hold** | Artifacts, versions, metrics | Context, memory, preferences |
| **User relationship** | Objects to supervise | Interface to talk to |
| **System role** | Units of value/output | Orchestrator of operations |

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER AS SUPERVISOR                          │
│                                                                 │
│   What user supervises:     How user supervises:                │
│   ┌─────────────────────┐   ┌─────────────────────┐            │
│   │      AGENTS          │   │        TP           │            │
│   │   (data objects)    │◄──│  (interaction layer)│            │
│   │                     │   │                     │            │
│   │ • Review drafts     │   │ • "Make it shorter" │            │
│   │ • Approve/reject    │   │ • "Add more detail" │            │
│   │ • Track quality     │   │ • "Set up a new one"│            │
│   │ • See trends        │   │ • "Explain this"    │            │
│   └─────────────────────┘   └─────────────────────┘            │
│              ▲                        │                        │
│              │                        │                        │
│              └────────────────────────┘                        │
│              TP manipulates agents                       │
│              on user's behalf                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Decision Framework

When making UI/UX decisions, ask these questions:

### 1. Is this about displaying/organizing agent data?

**Use agent-centric patterns:**
- Dashboard views (what's due, what's staged, quality trends)
- Detail pages (version history, content, metadata)
- List/grid layouts for browsing
- Status indicators and metrics

### 2. Is this about user interaction/intent?

**Use TP-centric patterns:**
- Inline refinements (quick action chips, custom instructions)
- Floating/contextual chat (conversational interaction)
- Tool-based operations (create, modify, explain)
- Natural language input fields

### 3. Is this about the intersection?

**Apply the supervision principle:**
- TP surfaces capabilities
- User exercises them on agents
- The agent is visible; TP is the mechanism for change

---

## Concrete Examples

### Version Review Page

The review page exemplifies the supervision model:

- **Agent-centric**: The draft content is displayed prominently for review
- **TP-centric**: Inline refinement chips ("Shorter", "More formal") and custom instruction input
- **Supervision in action**: User reviews (sees the artifact), then uses TP to refine, then approves/rejects

```
┌────────────────────────────────────────────────────────┐
│ Weekly Status Report - Review                          │
├────────────────────────────────────────────────────────┤
│                                                        │
│ [Draft content displayed here - AGENT OUTPUT]         │
│                                                        │
├────────────────────────────────────────────────────────┤
│ Refine with AI:                           [TP LAYER]  │
│ [Shorter] [More detail] [More formal] [More casual]   │
│ ┌──────────────────────────────────────┐ [Send]       │
│ │ Or tell me what to change...         │              │
│ └──────────────────────────────────────┘              │
├────────────────────────────────────────────────────────┤
│ [Discard]                    [Cancel] [Mark as Done]  │
└────────────────────────────────────────────────────────┘
```

### Agents Dashboard

The dashboard is primarily agent-centric with TP available:

- **Agent-centric**: Cards showing each agent, status, next due date, quality trend
- **TP-centric**: Floating chat trigger for "Create a new agent" or questions
- **Supervision in action**: User scans what needs attention, can ask TP to help

### Onboarding Flow

Onboarding can use either dimension:

- **Agent-centric path**: Wizard that walks through creating first agent
- **TP-centric path**: Conversational flow where TP asks questions and scaffolds agent
- **Both valid**: User chooses their preferred interaction style

---

## Anti-Patterns

### Anti-pattern 1: Chat as Destination

**Wrong**: Making `/dashboard/chat` the primary landing page
**Why**: Chat is an interaction method, not the thing being supervised
**Right**: Dashboard shows agents; chat is available everywhere

### Anti-pattern 2: Hiding Agents Behind Chat

**Wrong**: User must ask TP to see their agents
**Why**: Supervisors need direct visibility into what they supervise
**Right**: Agents are directly visible; TP helps manipulate them

### Anti-pattern 3: Direct Manipulation Only

**Wrong**: No TP integration, user must manually edit everything
**Why**: Loses the "AI does work, user supervises" value prop
**Right**: TP-powered refinements available inline, not just manual editing

### Anti-pattern 4: Separate Contexts

**Wrong**: Chat in one place, agents in another, no connection
**Why**: TP loses context, user must re-explain
**Right**: TP is contextually aware of what user is viewing

---

## Implementation Checklist

When building a new feature, verify:

- [ ] Agent data is visible and accessible (not hidden behind chat)
- [ ] TP interaction is available in context (not requiring navigation)
- [ ] User can supervise (review, approve, reject, track quality)
- [ ] User can delegate/refine via TP (natural language, quick actions)
- [ ] Context flows between agent view and TP interaction

---

## Relationship to Other Principles

### ADR-013: Conversation + Surfaces

ADR-013 established the drawer pattern. The supervision model clarifies:
- Surfaces = agent views (the objects of supervision)
- Conversation = TP interaction (the method of supervision)
- Drawer = TP appearing in context of agents

### ADR-018: Recurring Agents

ADR-018 established agents as the product. The supervision model clarifies:
- Agents are first-class **data entities**
- TP is repositioned as the **interaction layer** for supervision
- Both are first-class, in their respective dimensions

### ADR-020: Agent-Centric Chat

ADR-020 proposed inverting chat and content. The supervision model refines this:
- Not "content primary, chat secondary"
- Rather: "agents are objects, TP is interaction method"
- Both are essential; neither is subordinate

---

## Evolution: Two-Layer Intelligence and Autonomy-First (2026-03-16)

FOUNDATIONS.md v2 extends the supervision model in two important ways:

### TP as Autonomous Supervisor (not just reactive interface)

The original model frames TP as the user's **interaction surface** — the user directs, TP executes. FOUNDATIONS Axiom 5 and ADR-111 (revised) add an autonomous dimension:

- **TP Composer**: TP autonomously creates and configures agents based on compositional judgment
- **TP Heartbeat**: TP periodically assesses agent workforce health without user prompting
- **TP Supervisory**: TP reviews individual agent performance and decides on lifecycle changes

The user's role shifts from **directing** to **supervising** to (at tenured state) **overseeing**. TP does more autonomously as it accumulates compositional judgment about what works for this user.

### Agents as Developing Entities (not just data objects)

The original model frames agents as "first-class data entities." FOUNDATIONS Axiom 3 extends this — agents are **developing entities** with:

- **Intentions** that evolve (not just static configuration)
- **Capabilities** earned through feedback (read → analyze → write-back → act)
- **Autonomy** that graduates per-capability (supervised → semi-autonomous → autonomous)

This doesn't change the supervision model's core insight (user supervises, TP facilitates). It extends it: what the user supervises becomes richer over time, and TP's autonomous capabilities reduce the supervision burden.

See [Agent Developmental Model Considerations](../analysis/agent-developmental-model-considerations.md) for the pre-decision analysis.

### Feedback vs Configuration (orthogonal axes)

The supervision model implicitly treats all user input as "supervision." The hardened framing distinguishes:

- **Feedback** (qualitative): edits, approvals, dismissals → improves output quality, compounds over time
- **Configuration** (control/scoping): instructions, sources, schedule, tool scope → defines boundaries, changed deliberately

Both are supervision. But they serve different purposes and flow through different channels.

---

## Evolution: Project Meeting Room (ADR-124, Proposed)

ADR-124 extends the supervision model further by making agents **visible participants** in a shared project conversation:

- **Agents shift from data objects to conversational participants** — users talk to agents directly via `@agent-slug` mentions, not only through TP proxy
- **PM becomes the default interlocutor** in project scope — TP recedes to infrastructure (system-level commands, cross-project queries)
- **Group scope emerges** as a new data layer — the shared conversation transcript, participant state, and cross-participant awareness (distinct from agent-private scope and project-charter scope)
- **Conversation as perception layer** (Axiom 2 extension) — the meeting room transcript becomes a fourth perception source alongside external (platform_content), internal (workspace_files), and reflexive (user feedback)

This doesn't replace the supervision model — it deepens it. The user still supervises, but now through direct dialogue with the agents doing the work, not only through a mediating TP layer.

See [ADR-124](../adr/ADR-124-project-meeting-room.md) for the full proposal.

---

## Summary

**The supervision model provides a unified framework:**

1. **Agents** = what user supervises (developing entities that accumulate domain expertise)
2. **TP** = how user supervises (interaction surface + autonomous compositor/supervisor)
3. **User** = supervisor whose role shifts from directing → supervising → overseeing as tenure increases

This resolves the apparent tension between "agents as first-class" and "TP as primary interface" by recognizing they operate in different dimensions—one is data, one is interaction. Both are first-class in their domain.
