# ADR-025 Addendum: TP as Persistent Drawer (Model B)

**Status:** Accepted
**Date:** 2026-02-05
**Supersedes:** Initial addendum (Conversation as Surface)
**Relates to:** ADR-025 (Claude Code Agentic Alignment), ADR-023 (Supervisor Desk Architecture)

---

## Context

After implementing "Conversation as Surface" (Model A), we reconsidered from first principles:

**Model A (Conversation as Surface):**
- Chat is a place you navigate to
- Creates friction: viewing deliverable → must navigate away to discuss it
- Feels like "leaving" to talk

**Model B (TP as Persistent Drawer):**
- Chat is always present, beside your work
- Natural: the assistant sits beside you at the desk
- No navigation needed to converse

The supervisor metaphor clarifies this: **TP sits beside you at the desk, not in another room.**

---

## Decision

**TP conversation is a persistent right drawer, not a separate surface.**

### Layout

```
Desktop (≥768px):
┌──────────────────────────┬─────────────────┐
│                          │                 │
│   Surface Content        │   TP Drawer     │
│   (flex-1)               │   (360-400px)   │
│                          │   collapsible   │
│                          │                 │
└──────────────────────────┴─────────────────┘

Mobile (<768px):
┌─────────────────────────────────────────────┐
│   Surface (when drawer closed)              │
│                 OR                          │
│   TP Chat (when drawer open, full screen)   │
└─────────────────────────────────────────────┘
```

### Drawer States

| State | Desktop | Mobile |
|-------|---------|--------|
| **Collapsed** | Hidden, FAB or tab to expand | FAB in corner |
| **Expanded** | 360-400px right panel | Full screen overlay |

### What the Drawer Shows

When expanded:
- Full message history
- Inline todo progress (when TP is working)
- Input field at bottom
- Context indicators (what surface you're viewing, selected project)
- Collapse button

---

## Why Right Drawer (Not Bottom)

| Aspect | Right Drawer | Bottom Drawer |
|--------|--------------|---------------|
| Mental model | "Assistant beside you" | "Pulling up a tool" |
| Surface visibility | Full height preserved | Compressed vertically |
| Wide screens | Natural use of space | Awkward empty sides |
| Convention | Slack, Discord, Cursor | Mobile chat apps |

Bottom drawer makes sense for mobile (thumb reach), but right drawer better fits the "working together" metaphor on desktop.

---

## Implementation

### 1. Remove `conversation` Surface Type

No longer needed — conversation happens in the drawer, not a surface.

```typescript
// REMOVE from DeskSurface union:
// | { type: 'conversation'; context?: {...} }
```

### 2. Create TPDrawer Component

```
web/components/tp/TPDrawer.tsx
```

Consolidates:
- `TPWorkPanel.tsx` (delete)
- `ConversationSurface.tsx` (delete)
- Chat functionality from `TPBar.tsx`

Features:
- Collapsible right panel (desktop)
- Full-screen overlay (mobile)
- Full message history
- Inline todos when active
- Input with skill picker
- Context awareness (current surface, project)

### 3. Update DeskLayout

```tsx
// In DeskLayout or page component
<div className="flex h-full">
  <main className="flex-1 overflow-hidden">
    <SurfaceRouter surface={surface} />
  </main>
  <TPDrawer />
</div>
```

### 4. Simplify TPBar

TPBar becomes just a collapsed indicator / expand trigger:
- Shows TP status when collapsed
- Click/tap to expand drawer
- On mobile: FAB that opens full-screen chat

### 5. State Management

Add to TPContext or DeskContext:
```typescript
drawerExpanded: boolean;
setDrawerExpanded: (expanded: boolean) => void;
```

Auto-expand drawer when:
- User sends a message
- TP starts multi-step work (todos appear)
- Skill invoked

---

## Behavior

### Desktop
1. User views deliverable → Surface shows deliverable detail
2. User types in TPBar (collapsed) → Drawer expands, message sent
3. TP responds → Chat visible in drawer
4. User can collapse drawer to focus on surface
5. TP progress (todos) visible in expanded drawer

### Mobile
1. User views deliverable → Full screen surface
2. User taps TP FAB → Full screen chat overlay
3. Chat happens
4. User taps back/X → Returns to surface
5. Simple toggle between surface and chat

---

## Migration

### Files to Create
- `web/components/tp/TPDrawer.tsx`

### Files to Delete
- `web/components/tp/TPWorkPanel.tsx`
- `web/components/surfaces/ConversationSurface.tsx`

### Files to Modify
- `web/types/desk.ts` — remove `conversation` surface type
- `web/components/desk/SurfaceRouter.tsx` — remove conversation route
- `web/components/tp/TPBar.tsx` — simplify to drawer trigger
- `web/components/surfaces/DeliverableDetailSurface.tsx` — remove TPWorkPanel integration
- `web/components/surfaces/IdleSurface.tsx` — remove TPWorkPanel integration
- `DeskLayout` or page — add TPDrawer to layout

---

## Consequences

### Positive

- **Simpler mental model**: Surface + Drawer, always available
- **No mode switching**: Don't "go to" conversation
- **Context preserved**: See deliverable while discussing it
- **Aligned with ADR-023**: TP is ambient, not a destination

### Negative

- **Screen real estate**: Drawer takes 360px on desktop
- **Mobile simplification**: Full-screen toggle, not true side-by-side

### Trade-offs Accepted

- Desktop-first side-by-side experience
- Mobile falls back to toggle (acceptable for phone form factor)

---

## Relation to ADR-025 Core

| ADR-025 Element | Status |
|-----------------|--------|
| `todo_write` tool | ✓ Keep — displayed in drawer |
| Skills (`/board-update`, etc.) | ✓ Keep — invoked from drawer input |
| Todos state in TPContext | ✓ Keep — displayed inline in drawer |
| TPWorkPanel | **Delete** — consolidated into TPDrawer |
| ConversationSurface | **Delete** — drawer replaces it |

---

## Summary

**The key insight: TP is your companion at the desk, not a room you visit.**

The drawer model means conversation is always one click away, visible alongside your work, and doesn't require navigating away from what you're doing. This is the natural expression of ADR-023's "supervisor at the desk" philosophy combined with ADR-025's agentic capabilities.
