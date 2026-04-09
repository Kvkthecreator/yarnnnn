# TP Notification Channel — Unified Side-Effect Surfacing

**Date:** 2026-04-02
**Status:** Proposed (ADR-155 Phase 3)
**Depends on:** Chat-as-drawer (SURFACE-ARCHITECTURE.md), InlineActionCard pattern, TPContext streaming

---

## Principle

**All system side effects surface through the TP conversation.**

The TP chat stream is the single notification channel. No separate toast system, no notification center, no alert banners. When the system does something worth telling the user about — workspace scaffolded, task completed, feedback needed — it appears as an inline card in the chat stream.

When chat is closed, the FAB communicates ambient state — "something happened" — and opening chat reveals the details.

## Why Not Toasts?

Toasts are disconnected from context. They pop up, the user reads them, they disappear. There's no history, no conversation, no way to act on them. The TP chat already has:
- Full conversation history (scrollback)
- Tool results with structured data
- Action affordances (buttons, links)
- Contextual follow-up ("Want me to adjust?")

Routing notifications through chat makes them **conversational** — the user can respond, ask questions, give feedback — instead of ephemeral.

## Two Surfaces, One Channel

```
┌─────────────────────────────────────────────────────┐
│ Chat OPEN                                           │
│                                                     │
│ User: "Set up my workspace"                         │
│                                                     │
│ TP: "Got it — setting up your workspace."           │
│                                                     │
│ ┌─────────────────────────────────────┐             │
│ │ ✓ Identity updated                  │             │
│ │ ✓ Workspace scaffolded              │             │
│ │   competitors: cursor, copilot      │             │
│ │   market: ai-coding-tools           │             │
│ │   15 entities · 5 domains   [View →]│             │
│ └─────────────────────────────────────┘             │
│                                                     │
│ TP: "Want me to create a tracking task?"            │
│                                                     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Chat CLOSED                                         │
│                                                     │
│                                          ┌───┐      │
│                    (FAB with badge) →     │ 2 │      │
│                                          └───┘      │
│                                                     │
│ User opens chat → queued cards appear at bottom     │
│ Badge clears                                        │
└─────────────────────────────────────────────────────┘
```

## FAB States

The FAB (floating action button) is already the chat toggle. It gains ambient state:

| State | Visual | Trigger | Clears when |
|-------|--------|---------|-------------|
| **Idle** | Static chat icon | Default | — |
| **Working** | Pulse animation | Tool executing (inference, task run) | Tool completes |
| **Notified** | Badge count (e.g., "2") | Side effects while chat closed | Chat opened |
| **Attention** | Subtle glow/ring | TP generated text while chat closed | Chat opened |

States are mutually exclusive, priority: Working > Notified > Attention > Idle.

## Notification-Worthy Tool Results

Not every tool result is worth surfacing. Only tool results with **user-visible side effects**:

| Tool | Side Effect | Card Content |
|------|------------|-------------|
| UpdateContext (identity + inference) | Workspace scaffolded | Domains + entity count + "View" link |
| UpdateContext (identity/brand) | Context updated | File updated confirmation |
| ManageTask (create) | Task created | Task name + schedule + "View" link |
| ManageTask (evaluate) | Task evaluated | Quality assessment summary |
| ManageTask (complete) | Task completed | Completion summary |
| WriteWorkspace | File written | Path + summary (only if on context page) |

Tools that are NOT notification-worthy: Search, Read, GetSystemState, WebSearch (internal investigation, not user-facing side effects).

## Implementation

### Data Flow

```
Tool executes → tool_result event in stream
    ↓
TPContext.handleToolResult(result)
    ↓
Is this notification-worthy? (check NOTIFICATION_WORTHY_TOOLS map)
    ↓
YES → Build notification card from result data
    ↓
Chat open?
    ├── YES → Render inline immediately (existing InlineActionCard pattern)
    └── NO  → Push to pendingNotifications queue → update FAB badge
```

### Files

| File | Change |
|------|--------|
| `web/contexts/TPContext.tsx` | Add `pendingNotifications` state + `handleToolResult` dispatcher |
| `web/components/tp/ChatPanel.tsx` | Render queued notifications on open, clear queue |
| `web/components/tp/ChatFAB.tsx` | Badge count from `pendingNotifications.length`, pulse from `isToolExecuting` |
| `web/components/tp/NotificationCard.tsx` | NEW — card component for tool result side effects |

### NotificationCard Types

Reuses the InlineActionCard visual pattern (border, icon, content, optional action button):

```tsx
type NotificationCardType =
  | { type: 'workspace_scaffolded'; domains: Record<string, string[]>; total: number }
  | { type: 'context_updated'; target: string; filename: string }
  | { type: 'task_created'; slug: string; title: string; schedule: string }
  | { type: 'task_evaluated'; slug: string; quality: string }
  | { type: 'task_completed'; slug: string; title: string }
```

> **Note (ADR-164):** These are **TypeScript notification card types**, not activity_log event types. The notification channel detects TP tool calls in the chat response stream (e.g., `ManageTask(action="evaluate")` returns → emit `task_evaluated` notification card). It does NOT read from activity_log. The matching task-lifecycle events in activity_log were deleted per ADR-164 as redundant denormalizations, but this frontend notification infrastructure still works because it's sourced from TP's live tool-use stream.

### Notification Queue

```tsx
// In TPContext
const [pendingNotifications, setPendingNotifications] = useState<NotificationCard[]>([]);

// When tool result arrives and chat is closed
const handleToolSideEffect = (card: NotificationCard) => {
  if (chatOpen) {
    // Render inline — existing stream handles this
  } else {
    setPendingNotifications(prev => [...prev, card]);
  }
};

// When chat opens
useEffect(() => {
  if (chatOpen && pendingNotifications.length > 0) {
    // Flush queued notifications as inline cards
    flushNotifications();
    setPendingNotifications([]);
  }
}, [chatOpen]);
```

## Workspace Tree Refresh

When a notification card indicates workspace mutation (scaffolding, file write), the context page's workspace tree should refresh. This uses the same callback pattern:

1. `TPContext` exposes `onWorkspaceMutation` callback
2. Context page registers a listener
3. On mutation notification → `loadExplorer()` re-fetches the tree
4. Tree re-renders with new nodes (the "magic moment")

This decouples the refresh trigger from the notification display — they use the same data source but have separate consumers.

## Relation to Existing Patterns

- **InlineActionCard** (existing): styled cards for task actions (run, adjust, research, feedback). Same visual pattern, extended to tool result side effects.
- **Chat drawer** (SURFACE-ARCHITECTURE.md): FAB trigger, right-edge drawer. Preserved — FAB gains ambient state.
- **TP streaming** (anthropic.py): tool_use and tool_result events already in stream. Frontend already processes them. This adds a post-processing layer.

## Future Extensions

Once the channel exists, everything routes through it:
- **Task execution results** (scheduler runs complete) — card shows output summary
- **Platform sync completion** — card shows "Slack synced: 12 new messages"
- **Feedback needed** — card shows "Review pending: Competitive Brief" with approve/reject buttons
- **Agent developmental milestones** — "Competitive Intelligence agent reached steady state"

All through the same pattern: tool result → notification card → inline or queued → FAB badge.
