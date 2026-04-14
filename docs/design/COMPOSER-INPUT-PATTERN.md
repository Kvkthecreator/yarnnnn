# ComposerInput Pattern

**Location**: `web/components/chat-surface/ComposerInput.tsx`
**Status**: Active (2026-04-14)

---

## What it is

`ComposerInput` is the shared UI primitive for any modal that collects user intent via text + links + files and composes it into a single message sent to TP.

**Unified-composer layout:**

```
┌─────────────────────────────────────────┐
│ [attached links]                        │  ← appear when added
│ [attached files]                        │  ← appear when added
│ ─────────────────────────────────────── │  ← divider (only when attachments present)
│ textarea (primary input, autoFocus)     │
│ ─────────────────────────────────────── │
│ Link  File                              │  ← toolbar
└─────────────────────────────────────────┘
```

Text, links, and files are **co-equal inputs** inside a single bordered container — not three separate labeled sections. The border treatment signals "this is one unified input."

---

## Why extracted (not duplicated)

All intent-capture modals share identical data handling:

```
links + files + text → caller composes a string → TP primitive
```

The substrate is the same. Only the *framing* (placeholder text, composed message format, surrounding UI) differs per consumer. Extracting the shared primitive means:

- Layout changes (border, toolbar, attachment display) propagate to all consumers in one edit
- Upload logic (`api.documents.upload`, status tracking) lives in one place
- Link validation and normalization is not duplicated

---

## Current consumers

| Component | Modal | TP target | Route logic |
|-----------|-------|-----------|-------------|
| `ContextSetup` | `OnboardingModal` | `UpdateContext + ManageDomains` | None — single intent |
| `TaskSetup` | `TaskSetupModal` | `ManageTask(action="create")` | Route toggle (track / deliverable) |

---

## Props interface

```tsx
interface ComposerInputProps {
  notes: string;
  onNotesChange: (v: string) => void;
  links: string[];
  onLinksChange: (links: string[]) => void;
  uploadedDocs: UploadedDoc[];
  onUploadedDocsChange: React.Dispatch<React.SetStateAction<UploadedDoc[]>>;
  placeholder?: string;       // textarea placeholder
  rows?: number;              // default 4
  autoFocus?: boolean;        // default true
  linkPlaceholder?: string;   // link input placeholder
  className?: string;
}
```

State lives in the **consumer**, not in `ComposerInput`. The primitive is stateless for the domain values — it only owns the link-input toggle and file-input ref.

---

## When to add a new consumer

If a modal collects intent via text + links + files → compose → TP, it should compose `ComposerInput`. The caller owns:

1. Any framing UI above (header, route toggle, etc.)
2. The message composition logic (`parts.join('\n')`)
3. The submit button and gate condition

---

## When NOT to use ComposerInput

- If the input shape is fundamentally different (e.g. structured form fields, multi-step wizard with divergent screens) — fork rather than contort the shared primitive
- If there's no file/link attachment requirement — a plain `<textarea>` is cleaner

---

## Layout decision rationale

Previous pattern (ContextSetup before 2026-04-14):

```
LINKS    [always-visible input field]
FILES    [dashed upload button]
NOTES    [textarea — last, labeled "Notes"]
```

Problems: text was third and labeled as supplementary. Files had a form-widget feel. Links had persistent input noise.

New pattern: one bordered container, text first and dominant, attachments appear above it when added, toolbar sits at the bottom like a chat composer. This makes materials genuinely co-equal with text rather than visually subordinate.
