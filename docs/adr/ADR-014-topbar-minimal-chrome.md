# ADR-014: Top Bar with Minimal Chrome

> **Status**: Implemented ✅
> **Date**: 2025-01-30
> **Completed**: 2025-01-30
> **Supersedes**: Sidebar-based navigation from ADR-013

---

## Context

ADR-013 implemented the Conversation + Surfaces architecture, making chat the primary interface with surfaces (drawer/side panel) for visual persistence. However, it retained the traditional left sidebar for navigation.

**Problem**: With the new paradigm, the sidebar is now redundant:
- Users no longer navigate between pages (conversation is always visible)
- Projects are contextual lenses, not routes
- Surfaces are summoned, not navigated to
- The sidebar consumes valuable horizontal space, especially on mobile

**User feedback from testing**:
> "maybe we swap out the existing global-like left sidebar completely? i think now that we don't expect the user to do much navigational... the top bar or global like can be better?"

---

## Decision

Replace the left sidebar with a **minimal top bar** that provides:
1. Project context switching (dropdown)
2. Surface access buttons
3. User menu / settings
4. Maximized conversation space

### Layout Design

```
DESKTOP (≥1024px):
┌─────────────────────────────────────────────────────────────────┐
│ yarnnn    [Project: None ▾]  [Context] [Schedule]    [⚙️] [👤] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                      CONVERSATION                               │
│                    (full width)                                 │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ [💬 Type a message...]                              [📎] [Send] │
└─────────────────────────────────────────────────────────────────┘

With Surface Panel Open:
┌─────────────────────────────────────────────────────────────────┐
│ yarnnn    [Project: YARNNN ▾]  [Context] [Schedule]  [⚙️] [👤] │
├───────────────────────────────────────────┬─────────────────────┤
│                                           │ Context        [✕]  │
│           CONVERSATION                    │ [Project] [You]     │
│         (shrinks to fit)                  │                     │
│                                           │ Memory items...     │
├───────────────────────────────────────────┤                     │
│ [💬 Type...]                    [📎][Send]│                     │
└───────────────────────────────────────────┴─────────────────────┘

MOBILE (<768px):
┌─────────────────────────┐
│ yarnnn [Project ▾] [👤] │
├─────────────────────────┤
│                         │
│    CONVERSATION         │
│                         │
├─────────────────────────┤
│ [💬 Type...]  [📎][⬆️] │
└─────────────────────────┘
    ↓ Surface buttons in chat input area or bottom nav
```

---

## Components

### 1. TopBar Component
```typescript
// components/shell/TopBar.tsx
- Logo/brand
- ProjectSelector dropdown
- Surface quick-access buttons (desktop only)
- User menu with settings, logout
```

### 2. ProjectSelector Dropdown
```typescript
// components/shell/ProjectSelector.tsx
- Shows "Dashboard" when no project
- Shows project name when active
- Dropdown lists all projects
- "New Project" option at bottom
- Search/filter for many projects
```

### 3. Simplified Layout
```typescript
// components/shell/AuthenticatedLayout.tsx
- Remove Sidebar completely
- TopBar at top (fixed, ~56px height)
- Main content fills remaining space
- Surface panel overlays/docks as before
```

---

## Migration Plan

### Files to Delete
- `web/components/shell/Sidebar.tsx`

### Files to Create
- `web/components/shell/TopBar.tsx`
- `web/components/shell/ProjectSelector.tsx`
- `web/components/shell/UserMenu.tsx`

### Files to Modify
- `web/components/shell/AuthenticatedLayout.tsx` - Remove sidebar, add TopBar
- `web/app/(authenticated)/dashboard/page.tsx` - Adjust height calculations

---

## Benefits

1. **More space**: Chat gets full width on all devices
2. **Simpler mental model**: No "where am I?" confusion
3. **Faster access**: Project switch is one click, not sidebar + click
4. **Mobile-first**: Works better on small screens
5. **Modern feel**: Matches apps like Notion, Linear, Slack

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Users miss sidebar | Project dropdown is equally visible |
| Many projects hard to find | Add search to dropdown |
| Settings harder to access | User menu in top-right |
| Surface buttons hidden on mobile | Add to input area or floating action |

---

## Success Criteria

1. All functionality from sidebar accessible via top bar
2. Conversation area is wider by ~240px (sidebar width)
3. Mobile experience improved (no hamburger menu needed)
4. No regression in core flows

---

## Implementation Notes

- Keep the same context providers (ProjectContext, SurfaceContext)
- TopBar is purely presentational - no new state management
- Consider keyboard shortcuts (Cmd+K for project switch, etc.)
