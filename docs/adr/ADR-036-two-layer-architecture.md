# ADR-036: Two-Layer Architecture

> **Status**: Accepted
> **Created**: 2026-02-10
> **Updated**: 2026-02-10 (Open Item 1 resolved by ADR-037, Open Item 2 resolved by ADR-038)
> **Related**: ADR-034 (Emergent Context Domains), ADR-035 (Platform-First Type System), ADR-037 (Chat-First Surface Architecture), ADR-038 (Claude Code Architecture Mapping), Strategic Validation Document
> **Supersedes**: None (foundational architecture decision)

---

## Context

YARNNN has evolved through multiple architectural phases:

1. **v3-v4**: Complex substrate pipeline (P0→P4), message bus, multi-layer abstraction
2. **v5**: Simplified to deliverables + context + integrations
3. **ADR-034**: Made context domains emergent (not user-configured)
4. **ADR-035**: Made deliverable types platform-first (workflow-oriented)

A strategic discourse (February 10, 2026) identified a tension:

- **Part I thesis**: TP-first activation, context invisible, deliverables via conversation
- **Part II thesis**: Fully emergent system, deliverables discovered by pattern recognition

These appeared to conflict: Is the system structured (deliverables as defined objects) or emergent (everything discovered)?

**The resolution**: These are complementary philosophies governing different layers.

### The Core Insight

> Users know what they want, but express it fluidly. Chat captures this fluidity naturally. Everything else — deliverables, context, tools, scheduling — is supporting infrastructure that makes chat effective.

This mirrors successful AI products:
- **Claude Code**: User expresses intent conversationally; tools (Bash, Edit, Read) are invisible infrastructure
- **ClawdBot**: User chats naturally; memory, heartbeats, integrations are invisible
- **ChatGPT**: User asks questions; retrieval, plugins, code interpreter are invisible

The pattern: **Chat is the interface; infrastructure makes chat effective.**

---

## Decision

Adopt a **Two-Layer Architecture** as the governing framework for YARNNN:

### Layer 1: Interaction Layer

**Philosophy**: Emergent, fluid, chat-first

**Principles**:
1. Chat (TP) is the universal interface
2. User intent is fluid and conversational
3. Infrastructure is invisible to users
4. No configuration exposed in the interaction layer
5. Accessible on any surface: web, mobile, WhatsApp, API

**What this governs**:
- How users express intent
- How the system responds
- What users see and interact with
- UX patterns and conversation flows

### Layer 2: Infrastructure Layer

**Philosophy**: Structured, predictive, hardened

**Principles**:
1. Structured for reliability (typed schemas, defined contracts)
2. Predictive for proactivity (pattern recognition, scheduled execution)
3. Hardened for trust (bulletproof execution, clear error handling)

**What this governs**:
- How the system actually delivers value
- Data models, execution pipelines, integrations
- Scheduling, notifications, feedback loops

### The Orchestration Layer

Between Interaction and Infrastructure sits an **Orchestration Layer** — TP's internal capabilities:

- Interprets user intent
- Selects appropriate skills/tools
- Retrieves relevant context
- Decides when to push/notify
- Pattern recognition for proactive proposals

This layer is invisible to users but critical for connecting fluid interaction to structured infrastructure.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    INTERACTION LAYER                             │
│                    Philosophy: Emergent, Fluid, Chat-First       │
│                                                                  │
│    ┌──────────────────────────────────────────────────────────┐ │
│    │                     CHAT (TP)                            │ │
│    │   • User expresses intent naturally                      │ │
│    │   • System responds conversationally                     │ │
│    │   • No configuration exposed                             │ │
│    │   • Accessible anywhere: web, mobile, WhatsApp           │ │
│    └──────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              │ intent flows down                 │
│                              ▼                                   │
├──────────────────────────────────────────────────────────────────┤
│                    ORCHESTRATION LAYER                           │
│                    (TP's Internal Capabilities)                  │
│                                                                  │
│    • Interprets user intent                                      │
│    • Selects appropriate skills/tools                            │
│    • Retrieves relevant context                                  │
│    • Decides when to push/notify                                 │
│    • Pattern recognition for proactive proposals                 │
│                                                                  │
│                              │                                   │
│                              │ invokes infrastructure            │
│                              ▼                                   │
├──────────────────────────────────────────────────────────────────┤
│                    INFRASTRUCTURE LAYER                          │
│                    Philosophy: Structured, Predictive, Hardened  │
│                                                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────┐ │
│  │    PUSH     │ │ DELIVERABLE │ │  PLATFORM   │ │  CONTEXT   │ │
│  │ SCHEDULING  │ │  AS SKILL   │ │ INTEGRATION │ │   MEMORY   │ │
│  │ PREDICTIVE  │ │   (TOOL)    │ │  LANDSCAPE  │ │ RECURSIVE  │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └────────────┘ │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## The Four Infrastructure Pillars

### Pillar 1: Push / Predictive / Scheduling (First-Class)

**Purpose**: System-initiated contact based on patterns, schedules, predictions.

**Differentiator**: ChatGPT/Claude are purely reactive. YARNNN contacts you.

**Components**:
- Pattern recognition engine (observes user behavior over time)
- Scheduling system (cron-like execution, timezone-aware)
- Attention queue (what needs user review)
- Notification delivery (push to user across channels)

**Examples**:
- "Your weekly status is ready for review"
- "I noticed you ask about Acme every Monday — want me to automate this?"
- "You haven't checked the BigCo digest in 2 weeks — still useful?"

### Pillar 2: Deliverables as Skills/Tools

**Purpose**: Deliverables are capabilities TP invokes, not objects users configure.

**The Reframe**:
```
Old: Deliverable = thing user creates in dashboard
New: Deliverable = skill/tool TP uses to fulfill intent
```

**Skill Interface** (conceptual):
```python
# TP invokes skills like Claude Code invokes tools
tp.invoke_skill(
    skill="generate_status_update",
    params={
        "sources": ["#acme-eng", "#product"],
        "timeframe": "last 7 days",
        "audience": "engineering manager",
        "format": "slack_message"
    }
)
```

**Components**:
- Skill definitions with typed parameters (from ADR-035)
- Execution pipeline (gather → synthesize → output)
- Version tracking (for feedback loop)
- Quality metrics (edit distance, approval rate)

### Pillar 3: Platform Integration with Landscape Awareness

**Purpose**: Reliable, structured extraction from Slack/Gmail/Notion with deep platform understanding.

**Landscape Concept**:
- Know what's *available* (channels, labels, pages)
- Know what's *relevant* (based on user's work patterns)
- Know *how* to extract (platform-specific signals from ADR-030)

**Components**:
- Platform connectors with landscape models
- Extraction rules per platform type
- MCP orchestration for on-demand fetch
- Caching with delta detection

### Pillar 4: Persistent & Recursive Context Memory

**Purpose**: Context that accumulates, persists, and feeds back into future interactions.

**The Recursive Loop**:
```
User request → Context retrieved → Output generated → User feedback
                    ↑                                      │
                    └──────────────────────────────────────┘
                         (feedback becomes context)
```

**Components**:
- Memory storage (embeddings, semantic search)
- Domain scoping (from ADR-034)
- Feedback capture (edit distance, user corrections)
- Memory compaction (summarize when too large)

---

## Consequences

### How Components Are Reframed

| Component | Previous Understanding | Two-Layer Understanding |
|-----------|----------------------|------------------------|
| **Deliverables** | User-created recurring work objects | Skills TP invokes to fulfill intent |
| **Context Blocks** | User-managed knowledge store | Invisible context TP retrieves |
| **Domains** | User groupings (rejected) → Emergent groupings | Invisible infrastructure for context scoping |
| **TP** | Chat assistant alongside dashboard | Primary interface; everything flows through |
| **Dashboard** | Configuration and management surface | ~~TBD~~ → Deprecated; see ADR-037 |

### What This Enables

| Capability | How Two-Layer Enables It |
|------------|-------------------------|
| **Zero configuration friction** | Infrastructure invisible; user just chats |
| **Proactive engagement** | Push/Scheduling pillar contacts user first |
| **Reliable execution** | Hardened infrastructure, not best-effort chat |
| **Context that improves** | Recursive memory pillar learns from feedback |
| **Platform everywhere** | Interaction layer works on web, mobile, WhatsApp |

### What This Prohibits

| Constraint | Rationale |
|------------|-----------|
| **Exposing infrastructure in chat** | Breaks the "invisible infrastructure" principle |
| **Requiring upfront configuration** | Violates "chat is the interface" principle |
| **Stateless interactions** | Must leverage memory pillar for differentiation |
| **Unreliable tool execution** | Hardened infrastructure is non-negotiable |

---

## Relationship to Prior ADRs

### ADR-034 (Emergent Context Domains)
- **Incorporated**: Domain emergence is now part of the Memory pillar
- **Principle preserved**: Users don't configure domains; they emerge

### ADR-035 (Platform-First Type System)
- **Incorporated**: Type definitions become Skill definitions
- **Reframe**: Types are TP-invocable skills, not user-selected templates
- **Preserved**: Extraction signals, governance ceilings, wave taxonomy

### ADR-030 (Context Extraction Methodology)
- **Incorporated**: Extraction rules are part of Platform Integration pillar
- **Enhanced**: Landscape awareness adds "know what's available" dimension

### ADR-021 (Review-First Supervision UX)
- **Compatible**: Review surface remains for user approval of outputs
- **Reframe**: Review is invoked by TP, not navigated to by user

### ADR-037 (Chat-First Surface Architecture)
- **Implements**: Frontend manifestation of Two-Layer
- **Resolves**: Open Item 1 (Dashboard Reinterpretation)

---

## Implementation Implications

### Backend (Hardening Focus)

1. **Skill Registry**
   - Formalize ADR-035 types as TP-invocable skills
   - Typed parameters, clear execution contracts
   - Skill discovery for TP orchestration

2. **Platform Connectors**
   - Landscape models per platform
   - Extraction rules with platform-specific signals
   - MCP orchestration for on-demand fetch

3. **Memory System**
   - Domain-scoped storage (ADR-034)
   - Feedback → memory loop
   - Compaction/summarization

4. **Push Infrastructure**
   - Pattern detection engine
   - Cron-like execution
   - Multi-channel notification delivery

### Frontend (See ADR-037)

1. **Chat = Home**
   - All user interaction flows through chat
   - Route `/` is chat surface

2. **Pages = CRUD + Receipts**
   - Conventional pages for history/management
   - No execution logic in pages

3. **Dashboard Deprecated**
   - Chat is home; dashboard concept dissolved
   - See ADR-037 for full surface architecture

---

## Open Items

These require follow-up ADRs or design decisions:

1. ~~**Dashboard Reinterpretation**~~ → ✅ **Resolved by ADR-037**: Chat is home; dashboard deprecated; pages are CRUD + receipts

2. ~~**TP Skill Interface**~~ → ✅ **Resolved by ADR-038**: Comprehensive mapping validates existing skill implementation follows Claude Code patterns; no new specification needed

3. **Pattern Recognition Scope**: What patterns trigger proposals? Minimum viable implementation?

4. **Power User Escape Hatch**: Do we offer explicit configuration for users who want it?

5. **Cold Start Experience**: What happens before system has patterns? Onboarding flow?

---

## Decision Rationale

### Why Two Layers, Not One?

A single philosophy fails:
- **Pure emergent**: System can't reliably execute (no structure)
- **Pure structured**: Users must configure (friction)

Two layers gives us both: fluid interaction AND reliable infrastructure.

### Why Infrastructure Invisible?

From ClawdBot/Claude Code learnings:
- Users don't care about the system; they care about outcomes
- Visible infrastructure = cognitive overhead = friction
- Configuration work feels like work, not value delivery

### Why Chat Primary?

- Universal interface (everyone understands chat)
- Captures fluid intent naturally
- Works on any surface
- Matches mental model of "talking to AI"

---

## References

- [Strategic Validation: Context Extraction vs. Deliverables Architecture](../strategy/STRATEGIC_VALIDATION_CONTEXT_DELIVERABLES_SPLIT.md)
- [ADR-034: Emergent Context Domains](./ADR-034-emergent-context-domains.md)
- [ADR-035: Platform-First Type System](./ADR-035-platform-first-type-system.md)
- [ADR-037: Chat-First Surface Architecture](./ADR-037-chat-first-surface-architecture.md)
- [ADR-030: Context Extraction Methodology](./ADR-030-context-extraction-methodology.md)
- [ESSENCE.md](../ESSENCE.md) - Core product thesis

---

*This ADR establishes the Two-Layer Architecture as the canonical framework for YARNNN's evolution. All subsequent architectural decisions should align with this foundation.*
