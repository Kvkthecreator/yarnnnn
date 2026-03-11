# Chat File Upload Improvements

## Status: Design

## Problem

Both chat surfaces (`ChatFirstDesk.tsx` dashboard, `AgentChatArea.tsx` agent workspace) have basic file upload via a paperclip button, but lack standard interaction patterns users expect from modern chat interfaces.

### Current state

| Capability | Status |
|---|---|
| Click-to-upload (paperclip button) | Yes — hidden `<input type="file" accept="image/*">` |
| Image preview thumbnails | Yes — 64x64 thumbnails above input |
| Remove attachment before send | Yes — X button on hover |
| Multiple file selection | Yes — `multiple` attribute on input |
| Drag-and-drop onto chat area | No |
| Clipboard paste (Cmd+V / Ctrl+V) | No |
| Drop zone visual feedback | No |
| Non-image file types | No — filtered to `image/*` only |
| File size validation | No |

### Pipeline

```
Frontend (base64) → ChatRequest.images → chat.py → anthropic.py → Claude API (inline image_content)
```

Images are **ephemeral** — base64-encoded on the client, sent inline with the chat message, never stored server-side. This matches Claude's native image input format.

## Scope

### In scope

1. **Drag-and-drop** — drop files anywhere on the chat area (messages + input)
2. **Clipboard paste** — Cmd+V / Ctrl+V to paste images from clipboard
3. **Drop zone overlay** — visual feedback when dragging files over the chat area
4. **File size validation** — reject files over 5MB with user-visible error (Claude API limit: 5MB per image)
5. **Shared hook** — extract duplicated logic into `useFileAttachments` hook

### Out of scope (for now)

- **Non-image file types** (PDF, CSV, etc.) — requires backend changes to handle document content blocks; Claude supports PDFs natively but the pipeline would need `document` content type support
- **Persistent file storage** — images remain ephemeral (inline base64)
- **Upload progress indicators** — files are base64-encoded client-side, no upload step

## Implementation

### 1. Shared hook: `useFileAttachments`

**File:** `web/hooks/useFileAttachments.ts`

Extract the duplicated file handling logic from both chat components into a single hook. Both `ChatFirstDesk.tsx` and `AgentChatArea.tsx` currently have identical implementations of:
- `attachments` / `attachmentPreviews` state
- `handleFileSelect` (onChange handler)
- `removeAttachment`
- `fileToBase64` conversion
- `fileInputRef`

The hook will also add:
- `handlePaste` — clipboard paste handler
- `handleDrop` / `handleDragOver` / `handleDragLeave` — drag-and-drop handlers
- `isDragging` — state for drop zone overlay
- File size validation (5MB limit per file)
- Error state for rejected files

```ts
interface UseFileAttachmentsReturn {
  // State
  attachments: File[];
  attachmentPreviews: string[];
  isDragging: boolean;
  error: string | null;

  // Handlers
  handleFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
  handlePaste: (e: React.ClipboardEvent) => void;
  handleDrop: (e: React.DragEvent) => void;
  handleDragOver: (e: React.DragEvent) => void;
  handleDragLeave: (e: React.DragEvent) => void;
  removeAttachment: (index: number) => void;
  clearAttachments: () => void;
  getImagesForAPI: () => Promise<TPImageAttachment[]>;

  // Refs
  fileInputRef: React.RefObject<HTMLInputElement>;
}
```

### 2. Drag-and-drop

Add drag event handlers to the outer chat container (the element wrapping both messages and input). This gives a large drop target — users don't need to aim for the small input area.

**Event flow:**
- `dragenter` / `dragover` on container → set `isDragging = true`, prevent default
- `dragleave` on container → set `isDragging = false` (with relatedTarget check to avoid flicker on child elements)
- `drop` on container → extract image files from `e.dataTransfer.files`, add to attachments, set `isDragging = false`

### 3. Clipboard paste

Listen for `paste` events on the textarea. When `e.clipboardData.files` contains image files, add them to attachments. This handles:
- Screenshots (Cmd+Shift+4 on macOS, then Cmd+V)
- Copied images from browsers or other apps
- Right-click → Copy Image, then paste

Does NOT interfere with normal text paste — only triggers when clipboard contains files.

### 4. Drop zone overlay

When `isDragging` is true, render a full-area overlay on the chat container:

```
┌──────────────────────────────────┐
│                                  │
│    ┌──────────────────────────┐  │
│    │                          │  │
│    │     Drop images here     │  │
│    │                          │  │
│    └──────────────────────────┘  │
│                                  │
└──────────────────────────────────┘
```

- Semi-transparent backdrop (`bg-primary/5`)
- Dashed border inner zone (`border-2 border-dashed border-primary/40`)
- Upload icon + "Drop images here" text
- `pointer-events-none` on children to prevent drag flicker
- Covers the full chat area (messages + input) using absolute positioning

### 5. File size validation

Before adding a file to attachments, check `file.size <= 5 * 1024 * 1024`. If exceeded:
- Skip the file
- Set `error` state with message: "Images must be under 5MB"
- Auto-clear error after 3 seconds

## Files to modify

| File | Change |
|---|---|
| **NEW** `web/hooks/useFileAttachments.ts` | Shared hook with all file handling logic |
| `web/components/desk/ChatFirstDesk.tsx` | Replace inline file logic with `useFileAttachments`, add drag/paste handlers and drop zone overlay |
| `web/components/agents/AgentChatArea.tsx` | Same as above |

## Verification

- [ ] Drag image file onto chat area → drop zone overlay appears → drop → thumbnail preview shows above input
- [ ] Drag non-image file → no reaction (filtered out)
- [ ] Drag file > 5MB → error message shown briefly, file rejected
- [ ] Copy screenshot to clipboard → Cmd+V in textarea → thumbnail preview appears
- [ ] Paste text → normal text paste behavior, no file handling triggered
- [ ] Paperclip button still works as before
- [ ] Remove attachment via X button still works
- [ ] Send message with attachments → images appear in chat and reach Claude API
- [ ] All above work on both dashboard and agent workspace
- [ ] Drop zone overlay disappears when dragging out of the chat area
