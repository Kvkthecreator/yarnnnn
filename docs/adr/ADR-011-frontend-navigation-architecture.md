# ADR-011: Frontend Navigation Architecture

**Status**: Accepted (Phase 1 Implemented)
**Date**: 2026-01-30
**Related**: ADR-010 (Thinking Partner Architecture), ADR-006 (Session Architecture)

---

## Context

YARNNN's frontend currently has:
- **Dashboard** with Chat (global) and "About You" (user context) tabs
- **Project Pages** with Context, Work, and Chat tabs
- **Sidebar** with project list navigation

Per ADR-010, the Thinking Partner (TP) is the user's single point of contact that "follows" them across scopes. The stress tests in ADR-010 reveal implications for how navigation and UI should support this model.

### Current Implementation

```
┌─────────────────────────────────────────────────────────────┐
│  SIDEBAR                 │           MAIN CONTENT           │
│                          │                                  │
│  ┌──────────────────┐    │  ┌───────────────────────────┐   │
│  │    Dashboard     │────┼──│  Dashboard Page           │   │
│  └──────────────────┘    │  │  ├── Tab: Chat (global)   │   │
│                          │  │  └── Tab: About You       │   │
│  ┌──────────────────┐    │  └───────────────────────────┘   │
│  │    Projects      │    │                                  │
│  │  ├── Project A   │────┼──│  Project Page             │   │
│  │  ├── Project B   │    │  │  ├── Tab: Context         │   │
│  │  └── Project C   │    │  │  ├── Tab: Work            │   │
│  └──────────────────┘    │  │  └── Tab: Chat (scoped)   │   │
└─────────────────────────────────────────────────────────────┘
```

### Key Questions

1. Should Chat be a tab, or always visible?
2. When user navigates from Dashboard to Project, should conversation continue?
3. How do we reinforce the "TP follows you" mental model in the UI?
4. Should default tab be consistent across dashboard/projects?

---

## Analysis

### Current UX Flow vs ADR-010 Model

| ADR-010 Expectation | Current UX | Gap |
|---------------------|------------|-----|
| TP follows user seamlessly | Chat is one tab among several | Chat hidden when viewing Context/Work |
| Conversation continues across scope | Separate sessions per scope | No visual continuity indicator |
| TP knows where user came from | No scope history tracking | TP can't reference "you were just in..." |
| TP reaches out proactively | No notification system | Users must check for outputs |

### Design Options

#### Option A: Chat as Primary (Always Visible)

```
┌────────────────────────────────────────────────────────────────┐
│  SIDEBAR          │  CONTEXT PANEL  │      CHAT (PRIMARY)     │
│                   │                 │                          │
│  Dashboard        │  [Switchable]   │  ┌──────────────────┐   │
│  ───────────      │  - User Context │  │                  │   │
│  Projects         │  - Project Ctx  │  │  TP Chat Area    │   │
│  ├── Project A    │  - Work Status  │  │                  │   │
│  ├── Project B    │                 │  │  Always visible  │   │
│  └── Project C    │                 │  │  across all      │   │
│                   │                 │  │  navigation      │   │
│                   │                 │  └──────────────────┘   │
└────────────────────────────────────────────────────────────────┘
```

**Pros:**
- TP is literally always present (embodies "follows you" metaphor)
- Easy to ask questions while browsing context
- Reduces clicks to interact with TP

**Cons:**
- Less screen space for context/work viewing
- May feel cluttered on smaller screens
- Chat dominates even when user wants to focus on content

#### Option B: Chat Default with Quick-Switch Context (Recommended for MVP)

Keep current tab structure but make Chat the default tab everywhere:

```
Dashboard:
  ├── Tab: Chat (DEFAULT, index 0)
  └── Tab: About You

Project:
  ├── Tab: Chat (DEFAULT, index 0)
  ├── Tab: Context
  └── Tab: Work
```

**Pros:**
- Minimal change to current architecture
- Chat is first thing user sees (reinforces TP centrality)
- Full screen for context/work when needed
- Works well on mobile

**Cons:**
- Still hides TP when viewing other tabs
- Context switching requires tab clicks

#### Option C: Persistent Chat Footer

Chat input always visible at bottom, expandable:

```
┌──────────────────────────────────────────────────────┐
│  [Current Tab Content - Context/Work/etc]            │
│                                                      │
│                                                      │
│                                                      │
├──────────────────────────────────────────────────────┤
│  🤖 TP: "Working on Project A"  [Ask anything...]   │
│  [Expand ↑]                                          │
└──────────────────────────────────────────────────────┘
```

**Pros:**
- TP presence always visible
- Quick access without navigation
- Can show scope indicator ("Currently in Project A")

**Cons:**
- More complex implementation
- Persistent elements can be distracting
- Need to handle expand/collapse state

---

## Decision

### Phase 1: Quick Wins ✅ Implemented

1. **Make Chat the default tab on Project pages** ✅
   - Changed default from "context" to "chat"
   - Reordered tabs: Chat, Context, Work
   - Reinforces TP as primary interface

2. **Add scope indicator to Chat component** ✅
   - Shows "Chatting in: Dashboard" or "Chatting in: [Project Name]"
   - Added `projectName` prop to Chat component
   - Helps user know where they are

3. **Add "Last seen" to project items in sidebar** (Deferred)
   - Requires tracking `last_active_at` in projects table
   - Lower priority, planned for Phase 2

### Phase 2: Enhanced Navigation (Post-MVP)

4. **Scope transition indicator**
   - When navigating to different scope, brief toast: "Now in Project A"
   - TP could optionally acknowledge: "Switched to Project A context"

5. **Recent activity shortcut**
   - Dashboard shows "Continue where you left off" link to last project
   - TP can suggest: "Want to continue in API Redesign?"

6. **Notification center**
   - Bell icon in header
   - Shows completed work, TP messages while away
   - Deep-links to relevant project

### Phase 3: Advanced (Future)

7. **Chat footer option**
   - User preference to enable persistent chat input
   - Collapses by default, expands on focus

8. **Cross-scope memory panel**
   - When in project, ability to "pin" user-level memories
   - Visual distinction between scopes

---

## Implementation Details

### Change 1: Default Tab on Project Page

```typescript
// web/app/(authenticated)/projects/[id]/page.tsx
// Line 29: Change default from "context" to "chat"

const [activeTab, setActiveTab] = useState<Tab>("chat");  // Was: "context"
```

### Change 2: Scope Indicator Component

```typescript
// New component: web/components/ScopeIndicator.tsx

interface ScopeIndicatorProps {
  projectId?: string;
  projectName?: string;
}

export function ScopeIndicator({ projectId, projectName }: ScopeIndicatorProps) {
  const scope = projectId ? projectName : "Personal";

  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
      <span className="w-2 h-2 rounded-full bg-primary" />
      Chatting in: {scope}
    </div>
  );
}
```

### Change 3: Sidebar Last Active

```typescript
// web/components/shell/Sidebar.tsx
// In project list item, add last_active display

<div className="flex justify-between items-center">
  <span>{project.name}</span>
  <span className="text-xs text-muted-foreground">
    {formatRelativeTime(project.last_active_at)}
  </span>
</div>
```

Requires backend change: `projects` table already has `updated_at`, but need to track `last_active_at` (last message in project session).

---

## Consequences

### Positive

- **Reinforces TP centrality**: Chat as default makes TP primary interface
- **Scope awareness**: Users always know where they are
- **Foundation for proactivity**: Notification structure enables push features
- **Consistent UX**: Same default tab across dashboard and projects

### Negative

- **Context tab less discoverable**: Users may not find context management
- **More UI elements**: Scope indicator adds visual complexity

### Mitigations

- Onboarding can guide users to Context tab
- Scope indicator is minimal and unobtrusive
- Phase approach allows validation before committing to larger changes

---

## Testing Scenarios

Validate against ADR-010 stress tests:

| Stress Test | Frontend Behavior |
|-------------|-------------------|
| S1: Multiple scope transitions | User sees Chat by default in each scope |
| S2: Conversation across scope change | (Backend handles) Scope indicator updates |
| S3: Document upload during transition | File attachment works in any scope |
| S4: Work discussed across projects | (Backend handles) |
| S5: Proactive notification | Phase 2: Notification center |
| S6: Memory scope ambiguity | Phase 2: Cross-scope memory panel |
| S7: Cold start "where am I?" | Dashboard Chat + About You provide orientation |
| S8: Rapid context switching | Tab state persists during session |

---

## References

- [ADR-010: Thinking Partner Architecture](ADR-010-thinking-partner-architecture.md)
- [ADR-010: Stress Tests](ADR-010-stress-tests.md)
- [ADR-006: Session and Message Architecture](ADR-006-session-message-architecture.md)
- Current Implementation: `web/app/(authenticated)/`
