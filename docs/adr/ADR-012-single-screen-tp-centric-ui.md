# ADR-012: Single-Screen TP-Centric UI Architecture

## Status
Proposed

## Date
2025-01-30

## Context

### Current State (v5)
YARNNN v5 uses traditional page-based routing:
- `/` - Landing/About
- `/chat` - Thinking Partner conversation
- `/projects/[id]` - Project detail with tabs (overview, context, work, documents)
- `/settings` - User settings

This creates friction:
1. User talks to TP → TP triggers work → user must navigate to `/projects/[id]?tab=work` to see results
2. Mental context switching between "conversation mode" and "results mode"
3. No visual feedback that work is happening in the background
4. Projects feel like separate destinations rather than organizational contexts

### Legacy System (yarnnn-app-fullstack)
The previous implementation used a **desktop metaphor**:
- **Chat as wallpaper** - always visible, never navigates away
- **Floating windows** - draggable, resizable panels for context, work, outputs, schedules
- **Dock** - top bar to toggle windows with activity badges
- **Everything on one screen** - no page routing for core interactions
- **Real-time subscriptions** - windows update live via Supabase

Key components:
- `FloatingWindow.tsx` - drag/resize via `react-rnd`
- `DesktopProvider.tsx` - centralized window state management
- `Dock.tsx` - window toggle buttons with badges
- 5 window types: context, work, outputs, recipes, schedule

### Problem Statement
The current navigational approach is:
- **Limiting** - can't see multiple contexts simultaneously
- **Unclear** - relationship between TP, chat, work, and outputs is confusing
- **Disconnected** - TP triggers actions but user must hunt for results

If TP is the single point of contact, why not make it one screen where TP orchestrates what's visible?

## Decision

Adopt a **Single-Screen TP-Centric UI** where:
1. TP chat is always visible (the "wallpaper")
2. Auxiliary content appears in floating/docked panels that TP can control
3. No page navigation for core workflows
4. Projects become context selectors, not destinations

## Architecture

### Layout Structure

```
┌─────────────────────────────────────────────────────────────────────────┐
│  [Logo] YARNNN    [Project: My Startup ▼]    [⚡2] [📊] [📅]    [👤]   │  ← Header/Dock
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────────────────┐       ┌─────────────────────────┐        │
│   │ 📊 Outputs              │       │ 📅 Schedules            │        │
│   │ ─────────────────────── │       │ ─────────────────────── │        │
│   │ • LinkedIn Guide (draft)│       │ Weekly report - Mon 9am │        │
│   │ • Research findings     │       │ Daily check - 6pm       │        │
│   │                    [×]  │       │                    [×]  │        │  ← Floating
│   └─────────────────────────┘       └─────────────────────────┘        │    Panels
│                                                                         │
│  ╔═══════════════════════════════════════════════════════════════════╗ │
│  ║                     THINKING PARTNER                              ║ │
│  ║  ───────────────────────────────────────────────────────────────  ║ │
│  ║                                                                   ║ │
│  ║  TP: I've started research on your LinkedIn strategy...          ║ │
│  ║      ┌──────────────────────────────────────┐                    ║ │
│  ║      │ ⚡ Work in Progress                   │                    ║ │  ← Chat
│  ║      │ Research Agent: 45% complete          │                    ║ │    (Primary)
│  ║      └──────────────────────────────────────┘                    ║ │
│  ║                                                                   ║ │
│  ║  You: Show me what you found so far                              ║ │
│  ║                                                                   ║ │
│  ║  TP: Here's what I've discovered. I'm opening the outputs        ║ │
│  ║      panel so you can see the details.                           ║ │
│  ║      [↗ Opens Outputs Panel]                                     ║ │
│  ║                                                                   ║ │
│  ╠═══════════════════════════════════════════════════════════════════╣ │
│  ║  [Type a message...]                                     [Send]  ║ │
│  ╚═══════════════════════════════════════════════════════════════════╝ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Hierarchy

```
App
├── DesktopProvider (window state management)
│   ├── Header
│   │   ├── Logo
│   │   ├── ProjectSelector (dropdown, not navigation)
│   │   ├── Dock
│   │   │   ├── DockItem (work) - badge shows running count
│   │   │   ├── DockItem (outputs) - badge shows new count
│   │   │   └── DockItem (schedules)
│   │   └── UserMenu
│   │
│   ├── Workspace (main area)
│   │   ├── FloatingPanelContainer
│   │   │   ├── WorkPanel (if open)
│   │   │   ├── OutputsPanel (if open)
│   │   │   ├── SchedulesPanel (if open)
│   │   │   └── ContextPanel (if open)
│   │   │
│   │   └── ChatContainer (always visible, "wallpaper")
│   │       ├── MessageList
│   │       │   ├── Message (user)
│   │       │   ├── Message (assistant)
│   │       │   └── InlineWorkIndicator (embedded progress)
│   │       └── InputBar
│   │
│   └── RealtimeSubscriptions (background)
│       ├── WorkTicketSubscription
│       ├── OutputsSubscription
│       └── SchedulesSubscription
```

### State Management

```typescript
// DesktopContext
interface DesktopState {
  // Panel visibility
  panels: {
    work: PanelState;
    outputs: PanelState;
    schedules: PanelState;
    context: PanelState;
  };

  // Active project (not a route, just context)
  activeProjectId: string | null;

  // Dock indicators
  dock: {
    work: { badge: number; pulse: boolean };
    outputs: { badge: number; pulse: boolean };
    schedules: { badge: number; pulse: boolean };
  };

  // Focus management
  activePanel: PanelId | 'chat' | null;
}

interface PanelState {
  isOpen: boolean;
  position: { x: number; y: number };
  size: { width: number; height: number };
  isMinimized: boolean;
  highlightedItems?: string[]; // Items TP is referencing
}

// Actions TP can trigger via tool results
type DesktopAction =
  | { type: 'OPEN_PANEL'; panel: PanelId; highlight?: string[] }
  | { type: 'CLOSE_PANEL'; panel: PanelId }
  | { type: 'HIGHLIGHT_ITEM'; panel: PanelId; itemId: string }
  | { type: 'SET_BADGE'; panel: PanelId; count: number }
  | { type: 'PULSE'; panel: PanelId }
  | { type: 'SET_PROJECT'; projectId: string };
```

### TP-Controlled UI

The key innovation: **TP's tool responses can include UI directives**.

```typescript
// Example: TP creates work and opens the work panel
{
  "success": true,
  "work": { "id": "...", "status": "running" },
  "ui_action": {
    "type": "OPEN_PANEL",
    "panel": "work",
    "highlight": ["work-id-123"]
  }
}

// Example: Work completes, TP opens outputs panel
{
  "success": true,
  "outputs": [...],
  "ui_action": {
    "type": "OPEN_PANEL",
    "panel": "outputs",
    "highlight": ["output-id-456", "output-id-789"]
  }
}
```

The frontend chat handler interprets these directives:

```typescript
// In chat message handler
const handleTPResponse = (response: TPResponse) => {
  // Render message as usual
  appendMessage(response.message);

  // Execute any UI actions
  if (response.ui_action) {
    dispatch(response.ui_action);
  }
};
```

### Inline Work Indicators

Work progress appears inline in chat, not just in panels:

```tsx
// InlineWorkIndicator component
<div className="inline-work-indicator">
  <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
    <Loader2 className="h-4 w-4 animate-spin" />
    <div>
      <p className="text-sm font-medium">Research Agent Working</p>
      <p className="text-xs text-muted-foreground">
        Analyzing LinkedIn strategy... 45%
      </p>
    </div>
  </div>
</div>
```

### Panel Types

| Panel | Content | Dock Badge | TP Can... |
|-------|---------|------------|-----------|
| **Work** | Running tickets, progress | Running count | Open, highlight ticket |
| **Outputs** | Work results, drafts | New/unread count | Open, highlight output |
| **Schedules** | Recurring work templates | Next due count | Open, highlight schedule |
| **Context** | Memories, documents | - | Open, highlight memory |

### Mobile Adaptation

On mobile, panels become full-screen sheets:

```
┌─────────────────────┐
│ [←] Outputs    [×]  │  ← Sheet header
├─────────────────────┤
│                     │
│ • LinkedIn Guide    │  ← Full screen content
│ • Research findings │
│                     │
└─────────────────────┘
        ↓ swipe to dismiss
┌─────────────────────┐
│ TP Chat             │
│                     │
│ ...                 │
├─────────────────────┤
│ [⚡2] [📊] [📅]     │  ← Bottom dock
└─────────────────────┘
```

### Routing (Minimal)

Only 3 routes needed:

```
/              → Landing (unauthenticated)
/app           → Desktop workspace (authenticated)
/settings      → Settings (could also be a panel)
```

Projects are selected via dropdown, not routes:
- `?project=uuid` query param for deep links
- State stored in DesktopProvider, not URL

## Implementation Phases

### Phase 1: Desktop Provider Foundation
- [ ] Create `DesktopProvider` with panel state management
- [ ] Create `Dock` component with badges
- [ ] Create basic `FloatingPanel` component (no drag yet)
- [ ] Wire up to existing chat

### Phase 2: Panel Content
- [ ] `WorkPanel` - shows running/recent tickets
- [ ] `OutputsPanel` - shows work outputs
- [ ] `SchedulesPanel` - shows scheduled work
- [ ] Real-time subscriptions for each

### Phase 3: TP Integration
- [ ] Add `ui_action` to tool response schema
- [ ] Update `handle_create_work` to return UI action
- [ ] Update chat handler to dispatch UI actions
- [ ] Inline work indicators in chat

### Phase 4: Polish
- [ ] Draggable panels (react-rnd)
- [ ] Panel minimize/maximize
- [ ] Keyboard shortcuts (Cmd+1 for work, etc.)
- [ ] Mobile sheet adaptation

## Consequences

### Positive
- **Unified experience** - everything happens in one place
- **TP has agency** - can show/hide things contextually
- **No context loss** - chat always visible
- **Feels modern** - Figma/desktop app UX
- **Real-time** - see work progress without refreshing

### Negative
- **Significant refactor** - current page structure needs rework
- **Complexity** - window management state is non-trivial
- **Mobile challenge** - floating windows don't work on small screens
- **Learning curve** - users unfamiliar with desktop metaphor

### Neutral
- **SEO irrelevant** - app is authenticated, no public pages
- **URL sharing** - deep links via query params still work

## Alternatives Considered

### 1. Keep Page Routing, Add Notifications
Add toast notifications when work completes, link to project page.
- **Rejected**: Still requires navigation, breaks flow.

### 2. Split Screen Layout
Fixed panels (like Slack): sidebar | chat | detail.
- **Rejected**: Less flexible, wastes space when panels aren't needed.

### 3. Tabbed Interface
Tabs at top: Chat | Work | Outputs | Schedules.
- **Rejected**: Only one view at a time, loses multi-context benefit.

## References

- Legacy implementation: `/Users/macbook/yarnnn-app-fullstack/components/desktop/`
- `react-rnd` library: https://github.com/bokuweb/react-rnd
- Figma's UI: https://figma.com (reference for panel-based design)
