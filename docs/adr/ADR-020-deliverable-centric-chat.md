# ADR-020: Deliverable-Centric Chat Architecture

**Status:** Accepted
**Date:** 2026-02-02
**Refines:** ADR-013 (Conversation + Surfaces) - clarifies, does not supersede
**Builds On:** ADR-018 (Recurring Deliverables), ADR-007 (TP Tool Use)
**See Also:** [Design Principle: Supervision Model](../design/DESIGN-PRINCIPLE-supervision-model.md)

## Context

ADR-013 established **conversation-first with surfaces as drawers** - the user talks to TP, and TP summons visual surfaces (outputs, context, schedules) as drawers layered on the conversation.

ADR-018 pivoted YARNNN to **recurring deliverables** as the core product - users set up deliverables, get regular outputs, and quality improves over time via the feedback loop.

These two decisions appeared to create tension:

1. **ADR-013 says**: Chat is the primary surface, content appears in drawers
2. **ADR-018 says**: Deliverables are the core product and primary value

### The Resolution: The Supervision Model

The apparent tension dissolves when we recognize **"first-class" operates in two different dimensions**:

| Dimension | First-Class Entity | Role |
|-----------|-------------------|------|
| **Data/Workflow** | Deliverables | Objects the user supervises |
| **UI/Interaction** | TP (Thinking Partner) | Method of supervision |

This is the **supervision model**: the user is a supervisor overseeing AI-produced work.
- **Deliverables** = *what* they supervise (data artifacts, versions, quality metrics)
- **TP** = *how* they supervise (interaction layer, refinement mechanism, delegation interface)

Neither is "primary" or "secondary"—they serve different purposes and are both first-class in their respective dimensions.

See [Design Principle: Supervision Model](../design/DESIGN-PRINCIPLE-supervision-model.md) for the full conceptual framework.

### Practical Architecture

```
┌─────────────────────────────────────────────────────┐
│  DELIVERABLE VIEW (what user supervises)            │
│  ─────────────────────────────────────────────────  │
│                                                      │
│  ## Weekly Status Report                             │
│  [Draft content visible for review]                 │
│                                                      │
│  ┌─────────────────────────────────────────────────┐│
│  │ Refine with AI: (TP as inline interaction)      ││
│  │ [Shorter] [More detail] [Custom instruction...] ││
│  └─────────────────────────────────────────────────┘│
│                                                      │
│  [Discard]                   [Cancel] [Mark as Done]│
└─────────────────────────────────────────────────────┘
                                        + 💬 Floating
                                          chat for
                                          conversational
                                          interaction
```

**Key insight**: TP manifests in two forms:
1. **Inline refinements** - direct manipulation via TP (chips, custom instructions)
2. **Floating chat** - conversational interaction with TP

Both are TP; one is embedded in the deliverable view, one is available globally.

### User Mental Model

Users don't wake up thinking "I want to chat with AI." They think:
- "I need to send my status report today"
- "Is my investor update ready?"
- "What does my weekly digest look like?"

The deliverable is the goal. Chat/TP is the means to refine, improve, and eventually automate that goal.

## Decision

### 1. Deliverables Dashboard as Primary Destination

The authenticated landing (`/dashboard`) shows the deliverables dashboard:
- Upcoming deliverables (what's due)
- Staged for review (what needs attention)
- Recent outputs (what was sent)
- Quality trends (improvement over time)

This replaces chat as the first thing users see.

### 2. Chat as Floating Contextual Assistant

Chat becomes a floating panel/drawer that:
- Is accessible from any page (not just `/dashboard/chat`)
- Is **contextual** to the current page:
  - On deliverable detail page: chat about that deliverable
  - On deliverables dashboard: chat about all deliverables
  - On project page: chat about that project (legacy behavior)
- Can be minimized/dismissed without losing state
- TP "sees what the user sees" and has context about current page

### 3. TP Can Create Deliverables

TP gains the ability to scaffold new deliverables through conversation:

```
User: I need to send a weekly progress report to my manager

TP: I can set that up for you. What day should I draft it?

User: Mondays would be good, so I can send it Tuesday morning

TP: Got it. I'll create a Weekly Progress Report deliverable that
    drafts every Monday. You'll review and approve before sending.

    [TP uses create_deliverable tool]

    Done! Your first draft will be ready next Monday. You can
    review it from the dashboard or I'll remind you.
```

This complements (not replaces) the onboarding wizard - users can set up deliverables either way.

### 4. Session Continuity Shifts to Deliverables

Currently: Sessions are per-project-per-day (ADR-006)

New model: Session context includes:
- Active deliverable (if viewing one)
- Recent deliverable interactions
- Cross-deliverable patterns (user's editing style, preferences)

The deliverable becomes the "anchor" for context, similar to how projects were the anchor before.

## Architecture

### Floating Chat Component

```typescript
// Global component mounted at layout level
<FloatingChat
  context={{
    page: 'deliverable-detail',
    deliverableId: 'del_123',
    deliverable: currentDeliverable,
    currentVersion: latestVersion,
  }}
/>
```

Context types:
- `deliverable-detail`: Viewing a specific deliverable
- `deliverable-review`: Reviewing a staged version
- `deliverables-dashboard`: Browsing all deliverables
- `project`: Legacy project context
- `global`: No specific context

### New TP Tools

Add `create_deliverable` tool:
```python
CREATE_DELIVERABLE_TOOL = {
    "name": "create_deliverable",
    "description": """
    Create a new recurring deliverable for the user.
    Use this when user describes something they need to produce regularly.

    Returns the created deliverable details.
    """,
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Name of the deliverable"},
            "deliverable_type": {
                "type": "string",
                "enum": ["status_report", "research_brief", "meeting_prep", "custom"],
            },
            "frequency": {
                "type": "string",
                "enum": ["daily", "weekly", "monthly"],
            },
            "day_of_week": {
                "type": "integer",
                "description": "0=Sunday, 1=Monday... Only for weekly.",
            },
            "day_of_month": {
                "type": "integer",
                "description": "1-28 for monthly.",
            },
            "recipient_name": {"type": "string"},
            "recipient_relationship": {"type": "string"},
            "description": {"type": "string", "description": "What this deliverable covers"},
        },
        "required": ["title", "deliverable_type", "frequency"],
    }
}
```

### Page-to-Context Mapping

| Page Route | Chat Context | Primary TP Focus |
|------------|--------------|------------------|
| `/dashboard/deliverables` | All deliverables | Overview, create new |
| `/dashboard/deliverable/[id]` | Specific deliverable | Refine, explain, improve |
| `/dashboard/deliverable/[id]/review` | Version under review | Edit assistance, approve |
| `/dashboard/project/[id]` | Project (legacy) | Project work |
| `/dashboard` | Global | General questions |

### URL Structure

Existing routes remain, but semantics shift:
- `/dashboard/chat` - Demoted or removed (chat is everywhere now)
- `/dashboard/deliverables` - Primary destination
- `/dashboard/deliverable/[id]` - Deliverable detail with floating chat

## Migration Path

### Phase 1: Floating Chat Infrastructure
1. Create `FloatingChatProvider` context
2. Implement `FloatingChatPanel` component (reuses existing chat UI)
3. Mount at authenticated layout level
4. Pass page context to chat

### Phase 2: Deliverable Page Integration
1. Remove `DeliverableChatDrawer` (replaced by floating chat)
2. Update `DeliverableDetail` to provide context to floating chat
3. Floating chat auto-opens with deliverable context on "Refine with AI"

### Phase 3: Create Deliverable via Chat
1. Add `create_deliverable` tool to TP
2. TP can scaffold deliverables from conversation
3. After creation, navigates user to new deliverable or dashboard

### Phase 4: Session/Context Update
1. Update session model to include deliverable context
2. TP system prompt updated for deliverable-centric framing
3. Cross-deliverable learning (editing patterns become global context)

## Consequences

### Positive

- **Supervision model clarity**: Users supervise deliverables (objects), TP is the interaction method
- **Both first-class**: Deliverables first-class in data/workflow; TP first-class in interaction
- **Consistent access**: TP available everywhere—inline refinements + floating chat
- **Natural onboarding**: Users can set up deliverables via TP conversation OR wizard
- **Aligns with ADR-018**: Deliverables are visible, accessible objects of supervision

### Negative

- **Complexity**: Floating chat with page context is more complex than single chat page
- **Migration**: Existing chat patterns need updating
- **Mobile considerations**: Floating chat on mobile needs careful UX
- **Two TP manifestations**: Users may need to understand inline vs. conversational TP

### Neutral

- **Legacy routes**: `/dashboard/chat` can remain for direct chat access
- **Project context**: Still works, just not the primary framing

## Implementation Notes

### Floating Chat State
```typescript
interface FloatingChatState {
  isOpen: boolean;
  isMinimized: boolean;
  context: PageContext;
  messages: ChatMessage[];  // Preserved across page navigation
}
```

### Context Injection
When chat sends a message, the context is injected similar to current `DeliverableChatDrawer`:
```typescript
// First message includes page context
if (messages.length === 0 && context.deliverable) {
  contextMessage = `I'm looking at my "${context.deliverable.title}"
    deliverable. ${userMessage}`;
}
```

### TP System Prompt Update
```python
SYSTEM_PROMPT = """
You are Thinking Partner (TP), the user's AI collaborator for
recurring deliverables.

The user is currently viewing: {page_context}

Deliverables are the core product - scheduled documents the user
produces regularly. Your role is to:
- Help refine and improve deliverables
- Set up new deliverables when users describe recurring needs
- Provide context and insights across deliverable history
- Assist with edits and quality improvement
"""
```

## References

- [Design Principle: Supervision Model](../design/DESIGN-PRINCIPLE-supervision-model.md) - Canonical framework
- ADR-013: Conversation + Surfaces UI Architecture
- ADR-018: Recurring Deliverables Product Pivot
- ADR-007: Unified Streaming with Tool Support
- Implementation:
  - `web/components/deliverables/VersionReview.tsx` - Inline refinements (TP embedded)
  - `web/components/FloatingChatPanel.tsx` - Conversational TP
  - `web/hooks/useContentRefinement.ts` - TP refinement hook
