'use client';

/**
 * FeedbackContext — the app's SINGLE, universal action-feedback layer
 * (ADR-400 polish, 2026-07-03). One home for the three things every
 * operator-initiated action needs and, before this, did with browser-native
 * `window.alert` / `window.prompt` / `window.confirm` (blind, unstyled, jarring):
 *
 *   1. toast(...)        — a transient, non-blocking outcome notice
 *                          (success / error / info), auto-dismissing.
 *   2. confirm(...)      — a blocking yes/no gate before a consequential act
 *                          (a styled modal, not window.confirm), with an
 *                          optional `danger` treatment for destructive verbs.
 *   3. runAction(...)    — wraps an async operation: fires a pending toast,
 *                          awaits, then swaps it to success or error. This is
 *                          the "not blind" primitive: the operator SEES the
 *                          action is running and SEES how it resolved.
 *
 * WHY UNIVERSAL, NOT FILES-ONLY (operator directive, 2026-07-03): the Files
 * verbs surfaced the gap, but every surface has async operator actions
 * (connectors connect/disconnect, settings saves, agent grants…). This layer
 * is mounted once at the authenticated-shell root so any component can call
 * `useFeedback()` — no per-surface re-implementation, no second toast system.
 *
 * CANON: `docs/design/ACTION-FEEDBACK.md` is the singular design doc. Any new
 * "show a toast" / "confirm before X" / "run an async op with feedback" need
 * routes THROUGH this context. Do NOT hand-roll a fixed-position div or a
 * `window.confirm` — that reintroduces the dual approach this replaces.
 *
 * NOT a replacement for INLINE form/pane state. A long-running save with its
 * own progress bar, or a field-level validation error, still lives in its
 * component. This layer is for DISCRETE actions with a point outcome
 * (a verb: rename, move, delete, connect) — the fire-and-report shape.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { createPortal } from 'react-dom';
import { Check, AlertCircle, Info, Loader2, X, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Z_TOAST, Z_CONFIRM_BACKDROP, Z_CONFIRM_DIALOG } from '@/lib/shell/z-tiers';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ToastKind = 'success' | 'error' | 'info' | 'pending';

export interface ToastOptions {
  /** The primary line. */
  message: string;
  /** A second, muted line (e.g. a filename or a reason). */
  description?: string;
  kind?: ToastKind;
  /** ms before auto-dismiss. Default 4000; `pending` toasts never auto-dismiss. */
  durationMs?: number;
}

interface ToastRecord extends Required<Pick<ToastOptions, 'message'>> {
  id: string;
  kind: ToastKind;
  description?: string;
  durationMs: number;
}

export interface ConfirmOptions {
  title: string;
  /** Body text (a plain sentence — write it operator-plain, macOS-style). */
  body?: string;
  /** Confirm-button label. Default "Continue". */
  confirmLabel?: string;
  /**
   * Cancel-button label. Default "Cancel". Pass the empty string `''` to HIDE
   * the cancel button entirely — turning `confirm` into an OK-only alert
   * (acknowledge, no choice). Resolves `true` on OK, `false` on Esc/backdrop.
   */
  cancelLabel?: string;
  /** Destructive treatment (red confirm, warning glyph) for delete-class acts. */
  danger?: boolean;
}

/**
 * runAction options — the fire-and-report async wrapper. `pending`/`success`/
 * `error` are the toast lines for each phase. Omit `pending` to skip the
 * in-flight toast (silent until it resolves); omit `success` to stay quiet on
 * success (only surface failures). `error` may be a string or a fn of the
 * caught error (to pull a backend `detail`).
 */
export interface RunActionOptions {
  pending?: string;
  success?: string;
  error?: string | ((err: unknown) => string);
}

interface FeedbackContextValue {
  /** Show a toast; returns its id (so a caller could dismiss it early). */
  toast: (opts: ToastOptions) => string;
  /** Dismiss a toast by id. */
  dismissToast: (id: string) => void;
  /** Show a blocking styled confirm modal; resolves true/false. */
  confirm: (opts: ConfirmOptions) => Promise<boolean>;
  /**
   * Run an async op with pending→success/error toasts. Returns the op's
   * resolved value, or throws (re-throws) so callers can still branch on
   * failure — the toast is a SIDE-EFFECT, not a swallow. On error the
   * rejection is surfaced as an error toast AND re-thrown.
   */
  runAction: <T>(op: () => Promise<T>, opts?: RunActionOptions) => Promise<T>;
}

const FeedbackContext = createContext<FeedbackContextValue | null>(null);

// A monotonic id source that is SSR/StrictMode-safe (no Math.random / Date.now
// at module scope; a module counter is fine for a client-only provider).
let __toastSeq = 0;
const nextId = () => `t${++__toastSeq}`;

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function FeedbackProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastRecord[]>([]);
  const [confirmState, setConfirmState] = useState<
    (ConfirmOptions & { resolve: (v: boolean) => void }) | null
  >(null);
  const timers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
    const timer = timers.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timers.current.delete(id);
    }
  }, []);

  const toast = useCallback(
    (opts: ToastOptions): string => {
      const id = nextId();
      const kind = opts.kind ?? 'info';
      const durationMs = opts.durationMs ?? (kind === 'pending' ? 0 : 4000);
      setToasts((prev) => [
        ...prev,
        { id, message: opts.message, description: opts.description, kind, durationMs },
      ]);
      if (durationMs > 0) {
        const timer = setTimeout(() => dismissToast(id), durationMs);
        timers.current.set(id, timer);
      } else if (kind === 'pending') {
        // Failsafe: a `pending` toast normally lives until runAction swaps it to
        // success/error. But if the wrapped op HANGS (never settles — a known
        // network/SSE failure mode), the spinner would live forever with no
        // dismiss button. Cap it at 60s so a hung op can't strand the UI.
        const timer = setTimeout(() => dismissToast(id), 60000);
        timers.current.set(id, timer);
      }
      return id;
    },
    [dismissToast],
  );

  const updateToast = useCallback(
    (id: string, patch: Partial<ToastRecord>) => {
      setToasts((prev) => prev.map((t) => (t.id === id ? { ...t, ...patch } : t)));
      const durationMs = patch.durationMs;
      if (typeof durationMs === 'number' && durationMs > 0) {
        const existing = timers.current.get(id);
        if (existing) clearTimeout(existing);
        timers.current.set(id, setTimeout(() => dismissToast(id), durationMs));
      }
    },
    [dismissToast],
  );

  const confirm = useCallback((opts: ConfirmOptions): Promise<boolean> => {
    return new Promise<boolean>((resolve) => {
      // If a confirm is already open (overlapping call), resolve the earlier
      // one as `false` before replacing it — never leave its awaiter hung.
      setConfirmState((prev) => {
        prev?.resolve(false);
        return { ...opts, resolve };
      });
    });
  }, []);

  const closeConfirm = useCallback(
    (result: boolean) => {
      setConfirmState((prev) => {
        prev?.resolve(result);
        return null;
      });
    },
    [],
  );

  const runAction = useCallback(
    async <T,>(op: () => Promise<T>, opts?: RunActionOptions): Promise<T> => {
      const pendingId = opts?.pending
        ? toast({ message: opts.pending, kind: 'pending' })
        : null;
      try {
        const result = await op();
        if (pendingId && opts?.success) {
          updateToast(pendingId, { kind: 'success', message: opts.success, durationMs: 3000 });
        } else {
          if (pendingId) dismissToast(pendingId);
          if (opts?.success) toast({ message: opts.success, kind: 'success' });
        }
        return result;
      } catch (err) {
        const msg =
          typeof opts?.error === 'function'
            ? opts.error(err)
            : opts?.error ?? defaultErrorMessage(err);
        if (pendingId) {
          updateToast(pendingId, { kind: 'error', message: msg, durationMs: 6000 });
        } else {
          toast({ message: msg, kind: 'error', durationMs: 6000 });
        }
        throw err;
      }
    },
    [toast, updateToast, dismissToast],
  );

  // Cleanup all timers on unmount.
  useEffect(() => {
    const map = timers.current;
    return () => {
      map.forEach((t) => clearTimeout(t));
      map.clear();
    };
  }, []);

  const value = useMemo<FeedbackContextValue>(
    () => ({ toast, dismissToast, confirm, runAction }),
    [toast, dismissToast, confirm, runAction],
  );

  return (
    <FeedbackContext.Provider value={value}>
      {children}
      <ToastViewport toasts={toasts} onDismiss={dismissToast} />
      {confirmState && (
        <ConfirmDialog
          opts={confirmState}
          onCancel={() => closeConfirm(false)}
          onConfirm={() => closeConfirm(true)}
        />
      )}
    </FeedbackContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useFeedback(): FeedbackContextValue {
  const ctx = useContext(FeedbackContext);
  if (!ctx) {
    throw new Error('useFeedback must be used within a FeedbackProvider');
  }
  return ctx;
}

// ---------------------------------------------------------------------------
// Toast viewport (portal — bottom-right stack)
// ---------------------------------------------------------------------------

function ToastViewport({
  toasts,
  onDismiss,
}: {
  toasts: ToastRecord[];
  onDismiss: (id: string) => void;
}) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted || toasts.length === 0) return null;

  return createPortal(
    <div
      className="fixed bottom-4 right-4 flex flex-col gap-2 pointer-events-none"
      style={{ zIndex: Z_TOAST }}
      role="status"
      aria-live="polite"
    >
      {toasts.map((t) => (
        <ToastCard key={t.id} toast={t} onDismiss={() => onDismiss(t.id)} />
      ))}
    </div>,
    document.body,
  );
}

const TOAST_ICON: Record<ToastKind, React.ReactNode> = {
  success: <Check className="h-4 w-4 text-success" />,
  error: <AlertCircle className="h-4 w-4 text-destructive" />,
  info: <Info className="h-4 w-4 text-muted-foreground" />,
  pending: <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />,
};

function ToastCard({ toast, onDismiss }: { toast: ToastRecord; onDismiss: () => void }) {
  return (
    <div
      className={cn(
        'pointer-events-auto flex items-start gap-2.5 min-w-[240px] max-w-[360px]',
        'rounded-lg border border-border bg-popover px-3.5 py-2.5 shadow-lg',
        'animate-toast-in',
      )}
    >
      <div className="mt-0.5 shrink-0">{TOAST_ICON[toast.kind]}</div>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-popover-foreground leading-snug">{toast.message}</p>
        {toast.description && (
          <p className="mt-0.5 text-xs text-muted-foreground leading-snug break-words">
            {toast.description}
          </p>
        )}
      </div>
      {toast.kind !== 'pending' && (
        <button
          type="button"
          onClick={onDismiss}
          className="mt-0.5 shrink-0 text-muted-foreground/60 transition-colors hover:text-foreground"
          aria-label="Dismiss"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Confirm dialog (portal — blocking modal)
// ---------------------------------------------------------------------------

function ConfirmDialog({
  opts,
  onCancel,
  onConfirm,
}: {
  opts: ConfirmOptions;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  // Esc always cancels. Enter confirms ONLY for non-danger dialogs — a
  // destructive confirm (delete/trash) must not be committable by a stray
  // Enter (native OS dialogs default the keyboard to the SAFE action); the
  // operator has to click the red button deliberately. The confirm button is
  // autoFocus'd, so Enter-to-confirm still works via the focused button for
  // non-danger dialogs without a global key that fires from anywhere.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel();
      if (e.key === 'Enter' && !opts.danger) onConfirm();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onCancel, onConfirm, opts.danger]);

  if (!mounted) return null;

  return createPortal(
    <>
      <div
        className="fixed inset-0 bg-black/50 animate-fade-in"
        style={{ zIndex: Z_CONFIRM_BACKDROP }}
        onClick={onCancel}
      />
      <div
        className="fixed inset-0 flex items-center justify-center p-4 pointer-events-none"
        style={{ zIndex: Z_CONFIRM_DIALOG }}
      >
        <div
          className="pointer-events-auto w-full max-w-sm rounded-lg border border-border bg-card p-5 shadow-xl animate-dialog-in"
          role="alertdialog"
          aria-modal="true"
        >
          <div className="flex items-start gap-3">
            {opts.danger && (
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
            )}
            <div className="min-w-0 flex-1">
              <h3 className="text-base font-semibold text-card-foreground">{opts.title}</h3>
              {opts.body && (
                <p className="mt-1.5 text-sm text-muted-foreground leading-relaxed">{opts.body}</p>
              )}
            </div>
          </div>
          <div className="mt-5 flex justify-end gap-2">
            {opts.cancelLabel !== '' && (
              <button
                type="button"
                onClick={onCancel}
                className="rounded-md border border-border px-3.5 py-1.5 text-sm text-foreground transition-colors hover:bg-muted/60"
              >
                {opts.cancelLabel ?? 'Cancel'}
              </button>
            )}
            <button
              type="button"
              onClick={onConfirm}
              autoFocus
              className={cn(
                'rounded-md px-3.5 py-1.5 text-sm font-medium transition-colors',
                opts.danger
                  ? 'bg-destructive text-destructive-foreground hover:bg-destructive/90'
                  : 'bg-primary text-primary-foreground hover:bg-primary/90',
              )}
            >
              {opts.confirmLabel ?? 'Continue'}
            </button>
          </div>
        </div>
      </div>
    </>,
    document.body,
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Best-effort human message from a caught error. Prefers a backend
 * `{ detail }` shape (the app's APIError.data), falls back to `.message`,
 * then a generic line. Kept here so `runAction` has a sane default `error`.
 */
export function defaultErrorMessage(err: unknown): string {
  if (err && typeof err === 'object') {
    const anyErr = err as { data?: { detail?: string }; message?: string };
    if (anyErr.data?.detail) return anyErr.data.detail;
    if (anyErr.message) return anyErr.message;
  }
  return 'Something went wrong. Please try again.';
}
