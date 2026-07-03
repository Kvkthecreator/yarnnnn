# Action Feedback — the app's single toast / confirm / async-action layer

> **Status**: Canonical (2026-07-03). **This is the ONE way** to (a) show a toast, (b) confirm before a consequential action, and (c) run an async operator action with loading→outcome feedback. Do not hand-roll a fixed-position toast div or call `window.alert` / `window.confirm` / `window.prompt` in product surfaces — that reintroduces the exact dual-approach this replaces.
>
> **Origin**: The ADR-400 Files-surface polish pass. The Files verbs (rename / move / delete / restore) shipped structurally correct but used browser-native dialogs — "blind" event handling with no toast, no loading state, no styled confirm. The operator asked for the fix to be **universal, not Files-only, so it expands elsewhere.** This layer is that primitive.
>
> **Code**: [`web/contexts/FeedbackContext.tsx`](../../web/contexts/FeedbackContext.tsx) — provider + `useFeedback()` hook. Mounted once at the authenticated-shell root ([`AuthenticatedLayout.tsx`](../../web/components/shell/AuthenticatedLayout.tsx), outermost provider).

---

## Why it exists

Before this, every operator-initiated action reached for the browser primitives:

- `window.alert(msg)` — an unstyled, blocking, jarring notice.
- `window.confirm(msg)` — an unstyled yes/no gate.
- `window.prompt(msg)` — an unstyled text input (used, wrongly, for "Move to… a `/workspace/…` path").

They are **blind** (no in-flight state — the operator can't tell a slow action is running), **unstyled** (they break the product's visual language), and **non-composable** (each caller re-implements the fire→await→report dance). The Files surface made this visible; every surface with async actions (connectors, settings saves, agent grants) has the same need.

The fix is **one context, mounted once**, exposing three verbs. Any component calls `useFeedback()`.

---

## The three verbs

### 1. `toast(opts)` — a transient outcome notice

```tsx
const { toast } = useFeedback();
toast({ message: 'Renamed', kind: 'success' });
toast({ message: 'Move failed', description: 'Destination is read-only', kind: 'error' });
```

- `kind`: `'success' | 'error' | 'info' | 'pending'`. Default `'info'`.
- `description`: optional muted second line (a filename, a reason).
- `durationMs`: auto-dismiss. Default 4000; **`pending` toasts never auto-dismiss** (you resolve them via `runAction` or `dismissToast`).
- Returns the toast `id` for early dismissal.

Bottom-right stack, portal-rendered above everything (`Z_TOAST = 550`, above the launcher — an outcome must never be occluded by the surface that produced it).

### 2. `confirm(opts)` — a blocking styled gate (replaces `window.confirm`)

```tsx
const { confirm } = useFeedback();
const ok = await confirm({
  title: 'Move to Trash?',
  body: '"report.pdf" stays recoverable in Trash.',
  confirmLabel: 'Move to Trash',
  danger: true,
});
if (!ok) return;
```

- Returns `Promise<boolean>`. Esc / backdrop-click → `false`; Enter / confirm → `true`.
- `danger: true` gives the destructive treatment (red confirm button, warning glyph) for delete-class acts.
- Write `body` **operator-plain, macOS-style** — a person's sentence, not an engineer's. ("This file is managed by the system and can't be moved." — not "topology lock on the `system/` prefix.")

### 3. `runAction(op, opts)` — fire-and-report async (the "not blind" primitive)

```tsx
const { runAction } = useFeedback();
await runAction(
  () => api.documents.move(from, to),
  {
    pending: 'Moving…',
    success: 'Moved',
    error: (err) => (err instanceof APIError ? err.data?.detail ?? 'Move failed' : 'Move failed'),
  },
);
```

- Fires a `pending` toast, awaits `op`, then **swaps that same toast** to `success` or `error` in place.
- Returns the op's resolved value; **re-throws on failure** (the toast is a side-effect, not a swallow — callers can still branch/return-early on error).
- `error` may be a string or `(err) => string` (to pull a backend `{ detail }`). Omit `pending` to stay silent until it resolves; omit `success` to surface only failures.
- `defaultErrorMessage(err)` (exported) is the fallback — prefers `err.data.detail` (the app's `APIError` shape), then `err.message`.

---

## What this layer is NOT

- **Not** a replacement for inline form / pane state. A long save with its own progress bar, or a field-level validation error, stays in its component. This layer is for **discrete actions with a point outcome** — a verb (rename, move, delete, connect) that fires and reports.
- **Not** the narrative / notifications feed. Those are durable, server-backed operator-facing records (the `FeedSurface`, Notifications). A toast is ephemeral, client-only, and gone in seconds.
- **Not** a modal framework. `confirm` is a purpose-built yes/no gate. Rich multi-field modals (e.g. the folder-picker for Move) are their own components; they may *use* `toast`/`runAction` for their outcome.

---

## Design tokens it depends on

The layer uses `bg-popover`, `bg-card`, `text-destructive`, `text-success`, `hover:bg-accent`, and their `-foreground` pairs. These are **shadcn-standard tokens** added in the same pass to [`globals.css`](../../web/app/globals.css) + [`tailwind.config.ts`](../../web/tailwind.config.ts). Before this pass the theme defined only 7 tokens, so `bg-popover` resolved to nothing — which is why the Files right-click menu rendered **transparent**. The full overlay/interactive set (`popover`, `card`, `accent`, `destructive`, `success` + foregrounds) is now defined in both light and dark. Use these tokens for any new overlay/menu/danger UI rather than hardcoding hex.

Entrance animations use real keyframes (`.animate-toast-in`, `.animate-fade-in`, `.animate-dialog-in`) defined in `globals.css`, because `tailwindcss-animate` is **not installed** in this project — the `animate-in` / `slide-in-from-*` utilities are dead classes here. Do not reach for them.

---

## Adoption checklist (for the next surface)

1. `const { toast, confirm, runAction } = useFeedback();`
2. Replace `window.confirm(...)` → `await confirm({...})`.
3. Replace `window.alert('X failed')` → it usually disappears: wrap the op in `runAction` and let the `error` line report.
4. Replace bespoke `try/catch` + inline-error-state for a discrete verb → `runAction`.
5. Never add a new fixed-position toast div. If you find one, migrate it here and delete it (Singular Implementation).
