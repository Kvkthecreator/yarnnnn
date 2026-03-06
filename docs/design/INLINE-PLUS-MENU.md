# Inline Plus Menu — Contextual Actions in Chat Input

## Status: Implemented

## Problem

Action discoverability drops to zero after the first message. Starter cards (empty state) disappear, and `/` slash commands are a power-user pattern. The paperclip button is the only persistent affordance — but with drag-and-drop and clipboard paste now handling image upload, a dedicated image button is redundant.

## Decision

Replace the paperclip button with a `+` button in the same position (left side of input bar). Tapping `+` opens a compact popover menu of contextual actions. Image upload becomes one action inside the menu.

### Why inline `+`, not a FAB

- **Substitutive, not additive** — the paperclip earned its slot; the `+` inherits it
- **Consistent with user expectation** — iMessage, WhatsApp, Slack all use `+` inside the input bar
- **No layout complexity** — no absolute/fixed positioning conflicts with messages or drop zone overlay
- **Compact** — popover anchored to the button, not a floating panel

## Per-surface action sets

Actions differ by surface because scope is fundamentally different: dashboard = "what do I want to create/explore", deliverable page = "refine/generate/understand this thing".

### Dashboard (`ChatFirstDesk.tsx`)

| Action | Icon | Behavior |
|---|---|---|
| Attach image | Image icon | Opens file picker (current paperclip behavior) |
| Create deliverable | Sparkles | Pre-fills: "I want to create a new deliverable" |
| Search platforms | Search | Pre-fills: "Search across my connected platforms for " |

Kept intentionally small for v1. More actions can be added as patterns emerge.

### Deliverable workspace (`DeliverableChatArea.tsx`)

| Action | Icon | Behavior |
|---|---|---|
| Attach image | Image icon | Opens file picker |
| Generate new version | Play | Pre-fills: "Generate a new version" |
| Update instructions | Pencil | Pre-fills: "I want to update the instructions" |

Deliverable actions TBD beyond these — start minimal, expand based on usage.

## Component architecture

### `PlusMenu` component

**File:** `web/components/tp/PlusMenu.tsx`

```ts
interface PlusMenuAction {
  id: string;
  label: string;
  icon: LucideIcon;
  onSelect: () => void;   // Pre-fill input, open file picker, etc.
}

interface PlusMenuProps {
  actions: PlusMenuAction[];
}
```

- Self-contained open/close state
- Renders as popover anchored to the `+` button (opens upward from input bar)
- Click outside or Escape closes
- Selecting an action fires `onSelect` and closes the menu

### Integration

Each surface defines its own action array and passes it to `<PlusMenu>`. The `onSelect` callbacks either:
- Call `setInput(prompt)` to pre-fill the chat input
- Call `fileInputRef.current?.click()` for image upload
- Call a direct function (future: `onRunNow` for deliverables)

### Visual layout

```
┌─ input bar ───────────────────────────────┐
│         ┌────────────────────┐            │
│         │ Attach image       │            │
│         │ Create deliverable │            │
│         │ Search platforms   │            │
│         └────────────────────┘            │
│  [+]  Ask anything...              [➤]   │
└───────────────────────────────────────────┘
```

Popover opens **upward** from the `+` button, left-aligned.

## Files to create/modify

| File | Change |
|---|---|
| **NEW** `web/components/tp/PlusMenu.tsx` | Reusable plus-menu component |
| `web/components/desk/ChatFirstDesk.tsx` | Replace paperclip with `PlusMenu`, define dashboard actions |
| `web/components/deliverables/DeliverableChatArea.tsx` | Replace paperclip with `PlusMenu`, define deliverable actions |

## Supersedes

- Replaces the earlier FAB/speed-dial concept (plan file `rosy-roaming-crystal.md`)
- The file upload design doc (`CHAT-FILE-UPLOAD-IMPROVEMENTS.md`) remains valid — drag-and-drop/paste are independent of this change

## Verification

- [ ] `+` button visible in input bar on both surfaces
- [ ] Click `+` opens popover with surface-specific actions
- [ ] "Attach image" opens file picker, image appears as preview thumbnail
- [ ] "Create deliverable" pre-fills input, user sends to start conversational flow
- [ ] Click outside / Escape closes popover
- [ ] Existing drag-and-drop and paste still work (unaffected)
- [ ] Popover doesn't overflow viewport on small screens
