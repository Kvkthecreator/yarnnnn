# Action Feedback — the app's single toast / confirm / async-action layer

> **Status**: Canonical (2026-07-03; placement + lane taxonomy amended 2026-08-22, operator-ruled). **This is the ONE way** to (a) show a toast, (b) confirm before a consequential action, and (c) run an async operator action with loading→outcome feedback. Do not hand-roll a fixed-position toast div or call `window.alert` / `window.confirm` / `window.prompt` in product surfaces — that reintroduces the exact dual-approach this replaces.

---

## Placement: TOP-RIGHT — the attention corridor (2026-08-22)

The toast stack renders **top-right, below the top bar, beside the bell**
(`fixed top-[4.25rem] right-4`, newest on top). Operator-ruled; the macOS
benchmark carries it: banners arrive top-right next to the Notification
Center, so **everything that informs the operator shares one corridor** —
transient self-act feedback lands there and evaporates; durable peer/system
attention accumulates behind the bell an inch away. (Bottom-right was the
unexamined web-app default.)

This is the front-end half of ADR-593's split, rendered spatially:

- **Your own acts → the toast corridor.** Self-witness is trivially satisfied
  (ADR-405 D4) — a self-act NEVER reaches the bell, the timeline badge, or
  any stored record. A toast is ephemeral, client-only, gone in seconds.
- **Peers' and agents' acts → the bell.** Derived from the ledgers, never
  from this layer. This layer must never write anything durable.

## The lanes (what surfaces where)

| Lane | What | Home |
|---|---|---|
| **Self-act toast** | A discrete verb you fired just resolved (rename, run, disconnect) | `toast` / `runAction` — the top-right stack. Never hand-rolled. |
| **Confirm** | A consequential act needs a yes/no before it binds | `confirm` — the one styled gate. Never `window.confirm`, never a bespoke `fixed inset-0` clone. |
| **In-surface banner** | Unresolved state that must SURVIVE until acted on (Text's 409 conflict with its two exits, the OAuth failure with its caveat, a validation error) | The surface itself, `role="alert"`. **Deliberately not this layer** — a toast auto-dismisses, and these must not. |
| **Micro-feedback** | A control acknowledging itself (Copy → check) | At the control, `COPY_FEEDBACK_MS` (2000ms — the sweep found four durations for one gesture). Never a toast. |
| **Inline stream card** | A fact that belongs to the conversation record (tool side-effects) | The chat stream (`NotificationCard` etc.) — durable in the transcript, not transient. |

The one sanctioned **surface-local** transient: a canvas-coordinate gesture
refusal (Studio's "select from one area at a time") stays inside its canvas —
it is about a POSITION, and yanking the eye to the corridor would lose it.
Name any new exemption here, or it reads as an unswept offender.
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

Top-right stack (see Placement above), portal-rendered above everything (`Z_TOAST = 550`, above the launcher — an outcome must never be occluded by the surface that produced it). The viewport is **always mounted**: a live region must exist in the DOM before its content changes, or the first toast is never announced to screen readers.

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
- `body` accepts a **ReactNode** for structured content (a stat list before a purge). Rich multi-FIELD modals stay their own components — see "What this layer is NOT".
- When destructuring beside code that could shadow the native, alias it: `const { confirm: confirmDialog } = useFeedback()` — a bare `confirm(` call is exactly the spelling this layer bans.
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

Entrance animations use **`tailwindcss-animate`** — the shadcn-ecosystem companion to the token set (`animate-in fade-in slide-in-from-bottom-2 zoom-in-95 duration-150`). It was installed 2026-07-03 (same pass); before that it was missing, and 5 components under `components/tp/` had silently-dead `animate-in` classes. It is now wired in `tailwind.config.ts` — use these utilities for entrances/exits rather than hand-rolling `@keyframes` (a second animation system for the same job). Any shadcn component copied in animates correctly by default.

---

## Adoption checklist (for the next surface)

1. `const { toast, confirm, runAction } = useFeedback();`
2. Replace `window.confirm(...)` → `await confirm({...})`.
3. Replace `window.alert('X failed')` → it usually disappears: wrap the op in `runAction` and let the `error` line report.
4. Replace bespoke `try/catch` + inline-error-state for a discrete verb → `runAction`.
5. Never add a new fixed-position toast div. If you find one, migrate it here and delete it (Singular Implementation).
6. Success and failure never share one styled channel — the 2026-08-22 sweep found "Operation failed" rendered under a green check because one state var carried both.

## Adoption ledger (2026-08-22 sweep)

**Migrated in the streamline commit**: the Settings danger zone (hand-rolled
bottom-right toast at z-50 + bespoke confirm modal — both deleted), connector
disconnect (bare native `confirm(` + silent `console.error` failure),
plan cancellation (`window.confirm` on a money-visible act), multi-slide
delete (`window.confirm`), TrashView's inline "second-click" gates (permanent
delete — the most destructive act on the surface — carried the lightest gate
in the app), the Recurrence run/pause `ActionNotice` (a verbatim `runAction`
clone with its own kind enum and 5s timer, threaded through a context), and
the Text CSV notice (bottom-center hand-rolled div → `runAction`).

**Deliberately NOT migrated** (in-surface lanes, see the table): Text's
peer-edit notice + 409 conflict banner + header save state, the OAuth outcome
banner, upload partial-failure notices, the billing top-up arrival banner,
`role="alert"` field errors, chat stream cards/frames, Studio's canvas-local
gesture refusal.

**Owed**: `FlowEditor.tsx`'s `window.prompt('Link to (URL):')` — the last
native survivor; it needs an input, which `confirm` deliberately lacks
(an inline link popover, not a prompt modal). The bespoke
`WorkspaceMembersCard` modals (revoke / spend cap / access scopes) carry
fields, so they stay components — but they need dialog semantics
(`role`, `aria-modal`, Esc, focus trap) they currently lack; same for the
canonical `ConfirmDialog`'s missing focus trap/restore.
