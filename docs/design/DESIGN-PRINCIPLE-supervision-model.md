# Design Principle: The Supervision Model

**Status:** Canonical
**Date:** 2026-02-02
**Related:**
- [ADR-013: Conversation + Surfaces](../adr/ADR-013-conversation-plus-surfaces.md)
- [ADR-018: Recurring Deliverables](../adr/ADR-018-recurring-deliverables.md)
- [ADR-020: Deliverable-Centric Chat](../adr/ADR-020-deliverable-centric-chat.md)
- [Strategic Direction](../strategy/YARNNN_STRATEGIC_DIRECTION.md)

---

## The Core Insight

YARNNN's architecture serves a fundamental shift in how users relate to AI-assisted work:

**From**: User as operator (does the work, AI assists)
**To**: User as supervisor (AI does the work, user oversees)

This shift has specific implications for how we think about deliverables and TP (Thinking Partner).

---

## The Two Dimensions

### Deliverables: Objects of Supervision

Deliverables are **first-class data entities**. They represent:

- What the system produces
- What the user supervises
- What accumulates value over time
- The units of measurable quality

From a data and workflow perspective, deliverables are the core product. They have:
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

| Dimension | Deliverables | TP |
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
│   │   DELIVERABLES      │   │        TP           │            │
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
│              TP manipulates deliverables                       │
│              on user's behalf                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Decision Framework

When making UI/UX decisions, ask these questions:

### 1. Is this about displaying/organizing deliverable data?

**Use deliverable-centric patterns:**
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
- User exercises them on deliverables
- The deliverable is visible; TP is the mechanism for change

---

## Concrete Examples

### Version Review Page

The review page exemplifies the supervision model:

- **Deliverable-centric**: The draft content is displayed prominently for review
- **TP-centric**: Inline refinement chips ("Shorter", "More formal") and custom instruction input
- **Supervision in action**: User reviews (sees the artifact), then uses TP to refine, then approves/rejects

```
┌────────────────────────────────────────────────────────┐
│ Weekly Status Report - Review                          │
├────────────────────────────────────────────────────────┤
│                                                        │
│ [Draft content displayed here - DELIVERABLE]          │
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

### Deliverables Dashboard

The dashboard is primarily deliverable-centric with TP available:

- **Deliverable-centric**: Cards showing each deliverable, status, next due date, quality trend
- **TP-centric**: Floating chat trigger for "Create a new deliverable" or questions
- **Supervision in action**: User scans what needs attention, can ask TP to help

### Onboarding Flow

Onboarding can use either dimension:

- **Deliverable-centric path**: Wizard that walks through creating first deliverable
- **TP-centric path**: Conversational flow where TP asks questions and scaffolds deliverable
- **Both valid**: User chooses their preferred interaction style

---

## Anti-Patterns

### Anti-pattern 1: Chat as Destination

**Wrong**: Making `/dashboard/chat` the primary landing page
**Why**: Chat is an interaction method, not the thing being supervised
**Right**: Dashboard shows deliverables; chat is available everywhere

### Anti-pattern 2: Hiding Deliverables Behind Chat

**Wrong**: User must ask TP to see their deliverables
**Why**: Supervisors need direct visibility into what they supervise
**Right**: Deliverables are directly visible; TP helps manipulate them

### Anti-pattern 3: Direct Manipulation Only

**Wrong**: No TP integration, user must manually edit everything
**Why**: Loses the "AI does work, user supervises" value prop
**Right**: TP-powered refinements available inline, not just manual editing

### Anti-pattern 4: Separate Contexts

**Wrong**: Chat in one place, deliverables in another, no connection
**Why**: TP loses context, user must re-explain
**Right**: TP is contextually aware of what user is viewing

---

## Implementation Checklist

When building a new feature, verify:

- [ ] Deliverable data is visible and accessible (not hidden behind chat)
- [ ] TP interaction is available in context (not requiring navigation)
- [ ] User can supervise (review, approve, reject, track quality)
- [ ] User can delegate/refine via TP (natural language, quick actions)
- [ ] Context flows between deliverable view and TP interaction

---

## Relationship to Other Principles

### ADR-013: Conversation + Surfaces

ADR-013 established the drawer pattern. The supervision model clarifies:
- Surfaces = deliverable views (the objects of supervision)
- Conversation = TP interaction (the method of supervision)
- Drawer = TP appearing in context of deliverables

### ADR-018: Recurring Deliverables

ADR-018 established deliverables as the product. The supervision model clarifies:
- Deliverables are first-class **data entities**
- TP is repositioned as the **interaction layer** for supervision
- Both are first-class, in their respective dimensions

### ADR-020: Deliverable-Centric Chat

ADR-020 proposed inverting chat and content. The supervision model refines this:
- Not "content primary, chat secondary"
- Rather: "deliverables are objects, TP is interaction method"
- Both are essential; neither is subordinate

---

## Summary

**The supervision model provides a unified framework:**

1. **Deliverables** = what user supervises (data, artifacts, quality)
2. **TP** = how user supervises (interaction, refinement, delegation)
3. **User** = supervisor who oversees AI-produced work

This resolves the apparent tension between "deliverables as first-class" and "TP as primary interface" by recognizing they operate in different dimensions—one is data, one is interaction. Both are first-class in their domain.
