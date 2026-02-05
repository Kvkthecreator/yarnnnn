# ADR-025 Addendum: Conversation as First-Class Surface

**Status:** Proposed
**Date:** 2026-02-05
**Relates to:** ADR-025 (Claude Code Agentic Alignment), ADR-023 (Supervisor Desk Architecture)

---

## Context

ADR-025 introduced Claude Code-inspired patterns (todos, skills, working mode) to make TP's multi-step work visible. During implementation, we created `TPWorkPanel` as a side panel that appears when TP has active todos.

However, this created tension with ADR-023's supervisor desk philosophy:

> "The supervisor doesn't have separate 'modes' — they're always in the same place, and things flow through."

The side panel approach:
1. Creates visual "mode switching"
2. Fragments attention between surface and panel
3. Treats conversation as a utility rather than primary interaction

## The Supervisor's Two Postures

Revisiting the factory supervisor metaphor reveals two natural postures:

### Posture 1: At The Desk (Monitoring/Acting)

The supervisor glances at the factory floor, handles quick approvals, checks status. Things come to them.

- Brief exchanges: "Approved" / "Run it" / "Show me X"
- Quick navigation between views
- Attention queue surfaces items
- **UI:** Surfaces + TPBar (ambient input)

### Posture 2: In Conversation (Deliberation)

Someone came to discuss something substantive. Could be 5 minutes or an hour. Full attention on the dialogue — clarifying, aligning, deciding together.

- Multi-turn exchanges to reach alignment
- Complex creation or modification flows
- Explaining context, preferences, requirements
- **UI:** Full conversation surface

---

## Decision

**Conversation is a first-class surface, not a utility bar we awkwardly expand.**

### When Conversation Surface Activates

| Trigger | Example |
|---------|---------|
| Skill invoked | `/board-update` — this IS the meeting |
| TP needs extended clarification | Multi-turn back-and-forth |
| User explicitly requests | "Chat about this deliverable" |
| Complex creation flow | "Help me set up reporting for my team" |

### When TPBar Suffices

| Interaction | Example |
|-------------|---------|
| Quick command | "Pause my weekly report" |
| Simple navigation | "Show my deliverables" |
| Single-turn Q&A | "When's my next report due?" |
| Status check | "What are you working on?" |

---

## Revised Surface Model

```
DeskSurface:
├── idle                    → Dashboard, overview
├── deliverable-detail      → Deliverable mini-dashboard
├── deliverable-review      → Edit/approve version
├── deliverable-list        → List all deliverables
├── work-output             → View work result
├── work-list               → List work items
├── context-browser         → Browse memories
├── document-list           → List documents
├── project-detail          → Project settings
├── conversation            → Full-screen deliberation (NEW)
└── ... (other domain surfaces)
```

### Conversation Surface

```typescript
type ConversationSurface = {
  type: 'conversation';
  // Optional: what we're discussing
  context?: {
    deliverableId?: string;
    projectId?: string;
    skillName?: string;
  };
};
```

**Shows:**
- Full chat history (not truncated)
- Todos/progress inline (when applicable)
- Context badge (what deliverable/project/skill)
- Clear exit back to previous surface

**Transitions:**
- Skill invoked → Conversation surface (scoped to skill)
- Multi-turn clarification detected → Conversation surface
- User clicks "Discuss with TP" → Conversation surface (scoped to current item)
- Conversation concludes → Return to appropriate surface with handoff banner

---

## State Model Clarification

### Internal States (What TP is Doing)

These are TP's operational states, not UI modes:

| State | Description |
|-------|-------------|
| `idle` | Waiting for input |
| `listening` | Processing user message |
| `clarifying` | Awaiting user response to clarify() |
| `working` | Executing tools, updating todos |
| `responding` | Streaming response |

### External Views (What User Sees)

| View | When | UI |
|------|------|-----|
| **Desk + TPBar** | Quick interactions, monitoring | Any surface + bottom input bar |
| **Conversation** | Deliberation, complex flows | Full-screen chat surface |

The mapping isn't 1:1. TP can be "working" in either view — the view depends on whether deliberation is needed, not on TP's internal state.

---

## Implementation Changes

### 1. Add Conversation Surface Type

```typescript
// In types/desk.ts or surfaces.ts
type DeskSurface =
  | { type: 'idle' }
  | { type: 'deliverable-detail'; deliverableId: string }
  // ... existing surfaces
  | {
      type: 'conversation';
      context?: {
        deliverableId?: string;
        projectId?: string;
        skillName?: string;
      };
    };
```

### 2. Create ConversationSurface Component

Promote `TPWorkPanel` patterns into a full surface:

```
web/components/surfaces/ConversationSurface.tsx
```

Features:
- Full message history
- Inline todo progress (when active)
- Context header (skill name, related deliverable)
- Input at bottom
- "Back to desk" action

### 3. Transition Logic

In `TPContext` or `DeskContext`:

```typescript
// When to auto-transition to conversation surface
function shouldEscalateToConversation(event: TPEvent): boolean {
  // Skill invoked
  if (event.type === 'skill_activated') return true;

  // Multi-turn clarification (2+ clarify calls in sequence)
  if (event.type === 'clarify' && state.pendingClarifications > 0) return true;

  // Explicit user request
  if (event.type === 'user_requested_conversation') return true;

  return false;
}
```

### 4. Simplify TPWorkPanel Usage

- **Remove** automatic side panel on todo existence
- **Keep** TPWorkPanel for optional "expand" action if user wants to see history while on another surface
- **Primary** multi-step work now happens in Conversation surface

### 5. TPBar Behavior

TPBar remains on all surfaces (including Conversation) for input. On Conversation surface, it's integrated into the chat flow rather than a separate bottom bar.

---

## Migration Path

### Phase 1: Add Conversation Surface
1. Create `ConversationSurface.tsx`
2. Add surface type to `DeskSurface`
3. Route in `SurfaceRouter`

### Phase 2: Skill → Conversation
1. When skill detected, transition to Conversation surface
2. Skill prompt + todos display inline
3. On completion, transition to result surface

### Phase 3: Clarification Escalation
1. Track clarification depth
2. Auto-escalate to Conversation after threshold
3. Or surface a "Continue in chat" affordance

### Phase 4: Simplify TPWorkPanel
1. Remove auto-show on todos
2. Keep as optional expandable history
3. Or remove entirely if Conversation surface covers use cases

---

## Consequences

### Positive

- **Aligned with ADR-023**: Conversation flows through the desk naturally
- **Respects deliberation**: Complex exchanges get full attention
- **Clear mental model**: At desk OR in conversation
- **Simplifies state**: No awkward side panel logic

### Negative

- **Surface proliferation**: One more surface type
- **Transition complexity**: Need to detect when to escalate
- **History management**: Conversation history across surfaces

### Trade-offs Accepted

- Conversation surface is "heavier" than inline chat — accepted because deliberation deserves focus
- Some users may prefer always-inline — can revisit based on feedback

---

## Open Questions

1. **Persistence**: Does conversation history persist across sessions? (Likely yes, stored in chat_sessions)

2. **Context scope**: When in conversation about a deliverable, should TP automatically use that deliverable's context?

3. **Exit behavior**: When conversation concludes, where do we go? Last surface? New surface based on what was created?

4. **Mobile**: Conversation surface is naturally mobile-friendly (full screen chat). Keep TPBar as overlay or integrate fully?

---

## Relation to ADR-025 Core

This addendum **refines** ADR-025, it doesn't replace it:

| ADR-025 Element | Status |
|-----------------|--------|
| `todo_write` tool | ✓ Keep — used for progress tracking |
| Skills (`/board-update`, etc.) | ✓ Keep — trigger conversation surface |
| Todos state in TPContext | ✓ Keep — displayed in conversation surface |
| TPWorkPanel as side panel | **Revise** — promote to Conversation surface |
| "Working mode" concept | **Reframe** — it's conversation posture, not mode |

---

## Summary

The key insight: **Conversation is what happens when deliberation is needed, and it deserves a full surface.**

This reconciles Claude Code's structured workflows (ADR-025) with the supervisor desk philosophy (ADR-023) by treating conversation as a first-class citizen that flows through the desk, rather than an awkward panel bolted onto other surfaces.
