# ADR-022: Chat-First Architecture with Drawer Views

**Status:** Accepted (Revised)
**Date:** 2026-02-02
**Supersedes:** ADR-021 (Review-First Supervision UX)
**Revision:** Simplified from tab-based to chat-first model

## Context

Previous iterations tried to solve "TP presence everywhere" by:
1. Embedding TP inputs on every page (felt bolted-on)
2. Persistent TP bottom bar with tabs (created confusion about where messages live)

**The core problem:** Splitting TP across locations fragments the conversation experience. Users don't know where to look for messages or where their conversation history lives.

**The insight:** Don't split TP. **Chat IS the home base.** Everything else is supporting views that chat can summon.

## Decision

### 1. Chat as Primary Surface

The main authenticated view is a **full-screen chat interface** (like Claude Code):

```
┌─────────────────────────────────────────────────────────────────┐
│ yarnnn                                           [User Menu]    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TP: Good morning! You have 2 deliverables ready for review.    │
│                                                                 │
│  User: Show me the weekly status report                         │
│                                                                 │
│  TP: Here's your Weekly Status Report draft:                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 📋 Weekly Status Report          [Open] [Approve] [Edit] │   │
│  │ Week of Jan 27 • Ready for review                        │   │
│  │ ─────────────────────────────────────────────────────── │   │
│  │ Summary: This week focused on Q1 planning...             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  User: Make it shorter                                          │
│                                                                 │
│  TP: Done. I've condensed it to key points.                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 📋 Weekly Status Report (revised)  [Open] [Approve]      │   │
│  │ ...                                                      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ [Quick: Review pending | Run all | Create new]                  │
│ Message TP...                                            [Send] │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Drawer for Contextual Views

When users need to see full content (edit a deliverable, review version history, browse memories), it opens as a **drawer**:

```
┌──────────────────────────────────┬──────────────────────────────┐
│ Chat (dimmed/narrowed)           │ Drawer                       │
│                                  │                              │
│                                  │ Weekly Status Report         │
│                                  │ ════════════════════════     │
│                                  │ Status: Ready for review     │
│                                  │                              │
│                                  │ [Content editing area]       │
│                                  │                              │
│                                  │ [Approve] [Discard] [×]      │
└──────────────────────────────────┴──────────────────────────────┘
```

**Drawer behavior:**
- Opens from right side (desktop) or bottom sheet (mobile)
- Chat remains visible but de-emphasized
- Closing drawer returns full focus to chat
- "Ask TP about this" button sends context back to chat

### 3. Data Views as Separate Routes (Optional)

For users who want to browse all deliverables, memories, etc., there are dedicated data views:

- `/dashboard` - Chat (home)
- `/deliverables` - All deliverables grid/list
- `/memories` - Memory browser
- `/settings` - User settings

These are **not** chat - they're traditional data views. Each item has an "Ask TP" action that opens chat with context.

### 4. Information Density in Chat

TP responses use appropriate density:

**Inline:** Brief confirmations
```
TP: Done! Schedule updated to Tuesdays at 9am.
```

**Card:** Actionable items (deliverables, versions)
```
TP: Here's the latest version:
┌────────────────────────────────────────┐
│ 📋 Stakeholder Update    [Open drawer] │
│ Version 5 • Jan 28       [Approve now] │
│ Preview: Q1 results exceeded...        │
└────────────────────────────────────────┘
```

**Drawer:** Full editing/review experience
```
[Opens drawer with complete content, editing tools, actions]
```

## Architecture

### Components

1. **ChatView** - Full-screen chat interface (primary view)
2. **Drawer** - Slide-out panel for detail views
3. **DrawerContent variants:**
   - DeliverableDrawer - View/edit deliverable
   - VersionReviewDrawer - Review and approve draft
   - MemoryDrawer - View/edit memory
4. **DataViews** - Traditional list/grid views for browsing
5. **Quick Actions** - Context-aware shortcuts below chat

### State Flow

```
User in Chat
    │
    ├─► Asks about deliverable ─► TP shows card in chat
    │                                    │
    │                                    ├─► "Open" ─► Drawer opens
    │                                    └─► "Approve" ─► Inline confirmation
    │
    ├─► Clicks "Open" on card ─► Drawer opens
    │
    └─► Navigates to /deliverables ─► Data view (separate page)
                                           │
                                           └─► "Ask TP" ─► Back to chat with context
```

### URL Strategy

```
/dashboard                    → Chat (home)
/dashboard?drawer=del_123     → Chat with deliverable drawer open
/dashboard?drawer=review_456  → Chat with review drawer open
/deliverables                 → Deliverables data view
/memories                     → Memories data view
/settings                     → Settings
```

## Consequences

### Positive

- **Single source of truth for conversation** - All TP messages in one place
- **Clear mental model** - Chat is home, drawers are temporary detail views
- **No fragmented TP** - Don't need to figure out where messages go
- **Natural escalation** - Inline → Card → Drawer as detail increases
- **Simpler implementation** - Less state to manage than full tab system

### Negative

- **More navigation** - Need to open drawer for detailed editing
- **Less IDE-like** - Can't have multiple deliverables open side-by-side

### Trade-off Accepted

- We prioritize **conversation coherence** over **multi-document workflows**
- Users who need to compare deliverables can use the data views

## Migration from Current State

1. **Keep:** ChatView, Drawer system, existing data components
2. **Refactor:** DeliverableDetail → DeliverableDrawer
3. **Refactor:** VersionReview → VersionReviewDrawer
4. **Remove:** Tab infrastructure (TabBar, TabShell, PersistentTP, TabContent, tab renderers)
5. **Simplify:** Layout back to chat-primary

## References

- [ADR-021: Review-First Supervision UX](ADR-021-review-first-supervision-ux.md)
- Legacy: yarn CHAT_FIRST_ARCHITECTURE
- Claude Code interaction patterns
