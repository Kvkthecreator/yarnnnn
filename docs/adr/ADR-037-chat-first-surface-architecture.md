# ADR-037: Chat-First Surface Architecture

> **Status**: Accepted
> **Created**: 2026-02-10
> **Related**: ADR-036 (Two-Layer Architecture), ADR-023 (Supervisor Desk - superseded), ADR-034 (Emergent Context Domains)
> **Supersedes**: ADR-023 (Supervisor Desk Architecture)

---

## Context

ADR-036 established the Two-Layer Architecture:
- **Interaction Layer**: Chat-first, emergent, fluid
- **Infrastructure Layer**: Structured, predictive, hardened

This ADR resolves the open item from ADR-036: *"Dashboard/Observation Surface: How does existing dashboard design philosophy fit?"*

### The Problem

The current frontend architecture (ADR-023: Supervisor Desk) attempted to combine:
- Navigation and browsing
- Execution and real-time updates
- Judgment and decision-making
- Display of changed information

This dual-purpose approach created:
- Performance issues (execution + rendering interleaved)
- Complex state management
- Unclear user mental model

### The Insight

From discourse on February 10, 2026:

> **Surfaces serve three distinct functions for supervisors:**
> 1. **Direct** — Express intent, request work (Chat)
> 2. **Review** — Approve, refine, reject work (Invoked surfaces)
> 3. **Verify** — See history, receipts, audit trail (Pages)

These functions were conflated. They should be separated.

---

## Decision

Adopt a **Chat-First Surface Architecture** with clear separation of concerns:

### 1. Chat = Home (Execution Surface)

**Route**: `/` (root)

**Purpose**: Primary interaction, execution, real-time results

**Characteristics**:
- TP conversation is the main interface
- Execution happens here (skill invocation, generation, refinement)
- Results displayed inline
- Analogous to Claude Code's terminal experience
- Surfaces attention items on load ("2 items ready for review")

**What lives here**:
- All user intent expression
- All TP execution and responses
- Inline results and drafts
- Refinement interactions
- Real-time progress indicators

### 2. Pages = CRUD + Receipts (Navigation Surfaces)

**Purpose**: Conventional SaaS pages for browsing, history, management

**Characteristics**:
- No execution logic
- Fetch and display only
- Standard CRUD patterns
- Link to chat for actions

**The Page Map**:

| Route | Purpose | Content |
|-------|---------|---------|
| `/deliverables` | List recurring work | All deliverables, create fallback |
| `/deliverables/:id` | Deliverable detail | Versions, history, sources, config |
| `/platforms` | Connected platforms | OAuth management, source selection |
| `/docs` | Uploaded documents | Document list, upload interface |
| `/activity` | Audit trail | What happened, when, provenance |
| `/settings` | Preferences | Account, notifications, timezone |
| `/review` | Attention queue (optional) | Items pending approval |

### 3. Deprecated Surfaces

| Surface | Reason | Replacement |
|---------|--------|-------------|
| `/dashboard` | Chat is home | Chat surfaces attention; pages provide history |
| `/context` | ADR-034 makes context emergent/invisible | Context shown as lineage on outputs |
| Complex wizards | Creation is conversational | TP creates; simple form fallback |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         CHAT (HOME)                              │
│                         Route: /                                 │
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │                                                          │  │
│   │                    TP CONVERSATION                       │  │
│   │                                                          │  │
│   │   User: "Give me a weekly update on Acme"               │  │
│   │   TP: "I'll pull from #acme-eng. Ready Monday 9am?"     │  │
│   │   User: "Yes"                                            │  │
│   │   TP: "Created. Here's the first draft..."              │  │
│   │                                                          │  │
│   │   [Inline draft display]                                 │  │
│   │   [Refinement chips: Shorter | More detail | Edit]       │  │
│   │                                                          │  │
│   └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│   Focus: Execution, judgment, real-time                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ produces artifacts visible in
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         PAGES                                    │
│                         Conventional CRUD + Receipts             │
│                                                                  │
│   /deliverables ──→ List, detail, versions, history             │
│   /platforms    ──→ OAuth, sources, connection status           │
│   /docs         ──→ Uploaded files, assets                      │
│   /activity     ──→ What happened, audit trail                  │
│   /settings     ──→ Account, notifications                      │
│   /review       ──→ (Optional) Attention queue                  │
│                                                                  │
│   Focus: Browse, history, receipts, CRUD                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Consequences

### What This Enables

| Capability | How |
|------------|-----|
| **Simplified state management** | Execution state in chat only; pages are stateless fetches |
| **Better performance** | Pages don't run execution logic; chat is optimized for real-time |
| **Clear user mental model** | Chat = do things; Pages = see things |
| **Easier testing** | Pages are pure display; chat has isolated execution tests |

### What This Requires

| Requirement | Implementation |
|-------------|----------------|
| **Extract pages from hybrid surfaces** | Current surfaces split into chat features + page routes |
| **Route `/` to chat** | Chat becomes landing page |
| **Remove deprecated routes** | Dashboard, context browser removed |
| **TP inline capabilities** | Draft display, refinement, approval in chat |

### What This Prohibits

| Constraint | Rationale |
|------------|-----------|
| **Execution logic in pages** | Pages are CRUD only; execution belongs to chat |
| **Navigation-first UX** | Users land on chat, not a dashboard |
| **Context browser** | Context is invisible infrastructure (ADR-034) |

---

## Navigation Model

Under Chat-First, navigation is **fallback for exploration**, not primary interaction:

| Access Pattern | How User Gets There |
|----------------|---------------------|
| **Attention items** | Chat surfaces on load; or `/review` page |
| **Specific deliverable** | TP links inline; or `/deliverables/:id` |
| **Platform management** | TP suggests; or `/platforms` |
| **History/audit** | `/activity` page |
| **Settings** | `/settings` page |

**Primary nav structure**:
- TP (always visible, primary)
- Secondary: Deliverables, Platforms, Docs, Activity, Settings
- Flat hierarchy, no deep nesting

---

## Relationship to Prior ADRs

### ADR-023 (Supervisor Desk) — Superseded

ADR-023's core principles are **preserved but reinterpreted**:

| ADR-023 Principle | Chat-First Interpretation |
|-------------------|---------------------------|
| "One surface at a time" | Chat is the surface; pages are secondary |
| "TP always present" | TP IS the primary surface |
| "Surfaces flow through desk" | Surfaces are invoked from chat |
| "Review-first when attention needed" | Chat surfaces attention; `/review` is fallback |

The Supervisor Desk becomes the Chat itself.

### ADR-036 (Two-Layer Architecture) — Implemented

This ADR is the **frontend manifestation** of Two-Layer:

| Two-Layer Concept | Chat-First Implementation |
|-------------------|---------------------------|
| Interaction Layer | Chat surface |
| Infrastructure invisible | No context browser; lineage shown on outputs |
| Deliverables-as-Skills | TP invokes; results inline in chat |
| Push/Scheduling | Chat surfaces attention on load |

### ADR-034 (Emergent Context Domains) — Enforced

Context browser deprecation enforces ADR-034's "context is invisible" principle.

---

## Implementation Implications

### Frontend Changes

1. **Route restructure**
   - `/` → Chat (home)
   - Remove `/dashboard`
   - Remove `/context`
   - Keep/create entity pages (`/deliverables`, `/platforms`, `/docs`, `/activity`, `/settings`)

2. **Component extraction**
   - Extract CRUD views from hybrid surfaces
   - Move execution logic to chat components
   - Create pure display components for pages

3. **State management**
   - Chat owns execution state (TP conversation, pending actions, real-time updates)
   - Pages own fetch state only (loading, data, error)
   - No shared execution state between chat and pages

4. **Navigation**
   - Simplify nav to flat list
   - TP prominent/primary
   - Pages as secondary nav items

### Backend Implications

None directly. Backend APIs remain the same. Frontend consumption patterns change.

---

## Migration Path

### Phase 1: Route Setup
- Create new route structure
- `/` redirects to chat
- Entity pages created as shells

### Phase 2: Component Extraction
- Extract CRUD views from current surfaces
- Populate entity pages with extracted components
- Chat absorbs execution features

### Phase 3: Cleanup
- Remove deprecated routes (dashboard, context)
- Remove hybrid surface code
- Consolidate state management

### Phase 4: Polish
- Chat inline features (draft display, refinement)
- Navigation refinement
- Performance optimization

---

## Open Items

1. **Review page**: Keep as optional dedicated page, or fully absorb into chat?
2. **Deliverable creation fallback**: Simple form on `/deliverables` or modal from chat?
3. **Mobile considerations**: How does chat-first work on mobile web?

---

## References

- [ADR-036: Two-Layer Architecture](./ADR-036-two-layer-architecture.md)
- [ADR-034: Emergent Context Domains](./ADR-034-emergent-context-domains.md)
- [ADR-023: Supervisor Desk Architecture](./ADR-023-supervisor-desk-architecture.md) (superseded)
- [DESIGN-PRINCIPLE: Supervision Model](../design/DESIGN-PRINCIPLE-supervision-model.md)

---

*This ADR establishes Chat-First Surface Architecture as the frontend manifestation of the Two-Layer Architecture. Chat is home; pages are receipts.*
