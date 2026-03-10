# Inline Plus Menu — Contextual Actions in Chat Input

**Related:** [Surface-Action Mapping](SURFACE-ACTION-MAPPING.md) — design principle that references the verb taxonomy defined here

## Status: Implemented (v2 — verb taxonomy)

## Problem

Action discoverability drops to zero after the first message. Starter cards (empty state) disappear, and `/` slash commands are a power-user pattern. The paperclip button is the only persistent affordance — but with drag-and-drop and clipboard paste now handling image upload, a dedicated image button is redundant.

## Decision

Replace the paperclip button with a `+` button in the same position (left side of input bar). Tapping `+` opens a compact popover menu of contextual actions. Image upload becomes one action inside the menu.

### Why inline `+`, not a FAB

- **Substitutive, not additive** — the paperclip earned its slot; the `+` inherits it
- **Consistent with user expectation** — iMessage, WhatsApp, Slack all use `+` inside the input bar
- **No layout complexity** — no absolute/fixed positioning conflicts with messages or drop zone overlay
- **Compact** — popover anchored to the button, not a floating panel

## Action verb taxonomy

Each action has a **verb type** that determines what happens when selected. Actions must never default to "pre-fill text" — each must be explicitly mapped to the right verb.

| Verb | Behavior | Example |
|---|---|---|
| **show** | Renders an inline UI component in the chat area | "Create deliverable" → show type selection cards |
| **execute** | Fires a function immediately, no chat involved | "Generate new version" → calls `onRunNow` |
| **prompt** | Pre-fills input for user to refine before sending | "Search platforms" → pre-fills "Search for ..." |
| **attach** | Opens a system dialog (file picker, etc.) | "Attach image" → file picker |

Rules:
- Every action must declare its verb explicitly
- **show** actions toggle a UI panel/cards in the chat area (not a modal)
- **execute** actions fire-and-forget with no user input required
- **prompt** is only appropriate when the user needs to add information (e.g., a search query)
- Never use **prompt** as a lazy default — if the action can be done without user input, use **execute** or **show**

### UX requirements per verb

**show:**
- Dismiss on click outside the shown panel
- Dismiss after the user selects an option within the panel
- Dismiss when any message is sent (manual or auto)
- Include a close (X) button for explicit dismiss
- Panel renders above the input bar, below messages

**execute:**
- No intermediate UI — action fires immediately on menu selection
- Provide feedback via existing UI (e.g., loading state, toast)

**prompt:**
- Pre-fill should place cursor at the end of the text
- Focus the input after pre-fill

**attach:**
- Opens native system dialog — no custom UI needed

## Per-surface action sets

### Dashboard (`ChatFirstDesk.tsx`)

| Action | Verb | Icon | Behavior |
|---|---|---|---|
| Attach image | **attach** | ImagePlus | Opens file picker |
| Create deliverable | **show** | Sparkles | Toggles deliverable type cards inline (same cards as empty state) |
| Search platforms | **prompt** | Search | Pre-fills: "Search across my connected platforms for " |

### Deliverable workspace (`DeliverableChatArea.tsx`)

| Action | Verb | Icon | Behavior |
|---|---|---|---|
| Attach image | **attach** | ImagePlus | Opens file picker |
| Generate new version | **execute** | Play | Calls `onRunNow` directly |
| Update instructions | **prompt** | Pencil | Pre-fills: "I want to update the instructions for this deliverable" |

## Component architecture

### `PlusMenu` component

**File:** `web/components/tp/PlusMenu.tsx`

```ts
interface PlusMenuAction {
  id: string;
  label: string;
  icon: LucideIcon;
  verb: 'show' | 'execute' | 'prompt' | 'attach';
  onSelect: () => void;
}
```

The `verb` field is for documentation/clarity in action definitions. The actual behavior lives in `onSelect` — the component doesn't branch on verb type.

### Integration

Each surface defines its own action array. The `onSelect` callback implements the verb:

- **attach**: `() => fileInputRef.current?.click()`
- **show**: `() => setShowCreateCards(prev => !prev)` — toggles inline UI state
- **execute**: `() => onRunNow()` — fires the function
- **prompt**: `() => { setInput('...'); textareaRef.current?.focus(); }`

### "Create deliverable" show behavior

When toggled, renders the `STARTER_CARDS` grid (same component as empty state) below the messages, above the input bar. Works whether messages exist or not. Clicking a card sends the message immediately (not pre-fill). Dismissed after selection or by toggling `+` → "Create deliverable" again.

## Files

| File | Role |
|---|---|
| `web/components/tp/PlusMenu.tsx` | Reusable plus-menu component |
| `web/components/desk/ChatFirstDesk.tsx` | Dashboard surface — attach, show (create), prompt (search) |
| `web/components/deliverables/DeliverableChatArea.tsx` | Deliverable surface — attach, execute (generate), prompt (update) |

## Supersedes

- Replaces the earlier FAB/speed-dial concept (plan file `rosy-roaming-crystal.md`)
- The file upload design doc (`archive/CHAT-FILE-UPLOAD-IMPROVEMENTS.md`) remains valid — drag-and-drop/paste are independent of this change

## Verification

- [ ] `+` button visible in input bar on both surfaces
- [ ] "Attach image" opens file picker
- [ ] "Create deliverable" toggles inline type cards in chat area
- [ ] Clicking a type card sends the message and dismisses the cards
- [ ] "Generate new version" triggers execution immediately (no chat)
- [ ] "Search platforms" pre-fills input with cursor at end
- [ ] Click outside / Escape closes popover
- [ ] Existing drag-and-drop and paste still work (unaffected)
