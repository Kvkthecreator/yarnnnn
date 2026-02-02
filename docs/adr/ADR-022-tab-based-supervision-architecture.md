# ADR-022: Tab-Based Supervision Architecture

**Status:** Proposed
**Date:** 2026-02-02
**Supersedes:** ADR-021 (Review-First Supervision UX) - extends significantly
**See Also:** [Design Spec: Tab-Based Supervision UI](../design/DESIGN-tab-based-supervision-ui.md)

## Context

ADR-021 established the "review-first" principle and "TP presence on every screen" rule. Implementation revealed a fundamental tension:

**The problem:** Adding TP to existing pages feels like "chat bolted on" rather than an integrated experience.

**The insight:** Observing Claude Code's IDE-like interaction model revealed a more coherent pattern:
- Claude (AI) is the **constant frame** - always present
- Files/code are **surfaces** that appear within that frame
- You don't "navigate to Claude" - Claude IS the interaction layer
- Content opens as tabs, AI persists across all of them

This inverts the traditional "pages with AI sidebar" model.

## Decision

### 1. Tab-Based Content Model

All viewable content in YARNNN opens as **tabs**, similar to files in an IDE:

```
┌─────────────────────────────────────────────────────────────────┐
│ [🏠 Home] [📋 Weekly Status ×] [🧠 Preferences ×] [+ New]       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Active tab's content renders here]                            │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ TP: [context-aware quick actions]        [input...............]  │
└─────────────────────────────────────────────────────────────────┘
```

**Tab types:**
- `home` - Dashboard/overview (default)
- `deliverable` - Deliverable detail view
- `version-review` - Draft editing/approval
- `memory` - Memory item view/edit
- `context` - Context/knowledge item
- `document` - Uploaded document viewer
- `profile` - User settings

### 2. TP as Persistent Bottom Layer

TP is not a sidebar, floating panel, or embedded input. It's a **persistent bottom layer** that:

- Is always visible (never hidden behind navigation)
- Knows the active tab's context
- Provides context-specific quick actions
- Accepts natural language input
- Renders responses inline (cards, previews, confirmations)

**Key difference from IDE:** In Claude Code, Claude is in a sidebar. In YARNNN, TP IS the bottom of the screen - you're always "in conversation."

### 3. Content Types Determine Rendering

Each tab type has specific:
- **Content renderer** - How the tab body looks
- **Quick actions** - What TP shortcuts appear
- **TP context** - How TP understands "this item"

| Tab Type | Quick Actions Example |
|----------|----------------------|
| `home` | [Create new] [What's due] [Run all] |
| `deliverable` | [Run now] [Edit schedule] [Pause] |
| `version-review` | [Shorter] [More detail] [Approve] |
| `memory` | [Edit] [Delete] [Link to deliverable] |

### 4. Information Density Levels

Following Claude Code's pattern, TP responses use three density levels:

**Inline:** Brief status in message flow
```
TP: Done! Schedule updated to Tuesdays.
```

**Card:** Embedded but distinct, with actions
```
TP: New version ready.
┌────────────────────────────────────────┐
│ ✓ Version 13 generated    [Open tab]  │
└────────────────────────────────────────┘
```

**Tab:** Full content view
```
[Opens as new tab with complete content and editing]
```

### 5. Mobile Adaptation

Mobile uses a **single-tab view** with TP as **bottom sheet**:

- No visible tab bar (navigation instead)
- Swipe gestures for tab switching
- TP collapses to minimal bar, expands on tap
- Essential actions only

## Consequences

### Positive

- **Coherent mental model** - TP is always there, content surfaces through it
- **No "navigate to chat"** - Conversation is ambient, not a destination
- **Scalable to new content types** - Add new tab types easily
- **IDE-like familiarity** - Users understand tabs
- **Mobile-friendly** - Clear degradation strategy

### Negative

- **Significant refactor** - Current page-based routing needs rethinking
- **State complexity** - Managing multiple open tabs
- **Learning curve** - Different from typical web apps
- **URL routing** - Need to sync tabs with URLs for sharing/bookmarks

### Neutral

- **Existing components reusable** - DeliverableDetail, VersionReview become tab renderers
- **API unchanged** - Backend doesn't care about frontend tab model

## Implementation

### Phase 1: Infrastructure
- Tab bar component
- Tab state management
- URL sync (`/dashboard?tabs=del_123,mem_456&active=del_123`)

### Phase 2: TP Layer
- Persistent bottom TP component
- Context-aware quick actions
- Response card system

### Phase 3: Tab Renderers
- Convert existing pages to tab renderers
- Home tab (dashboard content)
- Deliverable tab
- Version review tab
- Memory/context tabs

### Phase 4: Mobile
- Bottom sheet TP
- Single-tab layout
- Navigation patterns

## Migration

### From Current State

1. **Keep:** All existing components (DeliverableDetail, VersionReview, etc.)
2. **Refactor:** Wrap in tab renderer pattern
3. **Remove:** EmbeddedTPInput, FloatingChatPanel, FloatingChatTrigger
4. **Add:** TabBar, TabManager, PersistentTP, tab renderers

### URL Strategy

Current:
```
/dashboard
/dashboard/deliverable/[id]
/dashboard/deliverable/[id]/review
```

Proposed:
```
/dashboard                           → Home tab only
/dashboard?tab=del_123              → Home + deliverable tab (active)
/dashboard?tab=del_123,review_v456  → Multiple tabs
```

Deep links still work - URL opens the relevant tab.

## Alternatives Considered

### A. Keep page-based with better TP integration

**Rejected:** Still feels like "TP bolted on" - the page IS primary, TP is secondary.

### B. Full chat-primary (no tabs)

**Rejected:** Loses direct manipulation of content. Users need to see and edit deliverables, not just talk about them.

### C. Split view (chat left, content right)

**Rejected:** Wastes space, feels like two separate apps. Tab model is more integrated.

## References

- [Design Spec: Tab-Based Supervision UI](../design/DESIGN-tab-based-supervision-ui.md)
- [ADR-021: Review-First Supervision UX](ADR-021-review-first-supervision-ux.md) (superseded)
- [Design Principle: Supervision Model](../design/DESIGN-PRINCIPLE-supervision-model.md)
- Legacy: `/Users/macbook/yarnnn-app-fullstack/docs/architecture/CHAT_FIRST_ARCHITECTURE_V1.md`
- Claude Code IDE patterns (observed interaction model)
