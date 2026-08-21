'use client';

/**
 * NewChatModal — starting a chat is choosing an ENGINE (ADR-558 D1).
 *
 * WHAT THIS USED TO ASK, AND WHY IT CHANGED. The modal asked "Who do you want
 * to talk to?" and listed, as one flat set of answers: a member-authored
 * persona (Lisa), four kernel characters each labelled with an engine, and a
 * human being. Four kinds of thing, one question — so a member who came to use
 * GPT-5 was handed a persona, and a member who wanted a colleague was shown a
 * model id they never asked for.
 *
 * ADR-558 separates the three acts that were fused here:
 *   start a chat   → WHICH ENGINE   (this modal)
 *   bring someone  → the CAST       (CastBar — humans and/or agents, ADR-495)
 *   configure one  → /agents        (personas are named and hired there)
 *
 * This is NOT a reversion of ADR-460. That ADR removed a seven-engine <select>
 * because "LLM-routing is not a layman concept" — correct, and still why
 * `/agents` exists and apps pin residents. Its error was assuming ONE door.
 * Chat is the raw-LLM surface; a member who never thinks about engines never
 * has to, because the sticky default answers for them.
 *
 * STICKY LAST-USED: the door MARKS the engine you last started with (a "last
 * used" badge), per member. It does NOT pre-select, reorder, or auto-scroll —
 * every engine is one click, including the remembered one. This comment claimed
 * "pre-selects" until 2026-08-21, which no code ever did; the badge is the whole
 * mechanism. Convenience without a workspace setting — a preference is
 * per-person, and view-state, not substrate.
 *
 * Errors are SHOWN, never swallowed (the live 409 the old `catch {}` ate).
 */

import { useCallback, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Check, Loader2, X } from 'lucide-react';
import { engineBrandIcon } from '@/lib/ai-providers/brand-icons';
import { SurfaceLink } from '@/components/shell/SurfaceLink';
import { Z_CONFIRM_BACKDROP, Z_CONFIRM_DIALOG } from '@/lib/shell/z-tiers';
import { cn } from '@/lib/utils';

export interface ChatEngineChoice {
  id: string;
  label: string;
  vision?: boolean;
  /** ADR-559 D3 — false when the engine cannot run right now. Absent = available
   *  (an older envelope that predates the field must not grey everything out). */
  available?: boolean;
  unavailable_reason?: string | null;
}

/** Why an engine is dark, in the member's terms. The server sends a REASON CODE
 *  (an operator fact); the wording is the FE's job — as with every other
 *  member-facing string. `no_provider_key` especially must not read as
 *  something they did or can fix: it is our deployment's gap. */
const UNAVAILABLE_COPY: Record<string, string> = {
  no_provider_key: 'not connected yet',
  unpriced: 'unavailable',
  upstream_refused: 'provider unavailable',
};

/** Where the member's last engine is remembered. VIEW STATE — a per-person
 *  convenience, deliberately not a workspace setting (a workspace default would
 *  be one member choosing for everyone). */
const LAST_ENGINE_KEY = 'yarnnn.chat.lastEngine';

export function readLastEngine(): string | null {
  try {
    return window.localStorage.getItem(LAST_ENGINE_KEY);
  } catch {
    return null;
  }
}

export function rememberEngine(id: string): void {
  try {
    window.localStorage.setItem(LAST_ENGINE_KEY, id);
  } catch {
    /* private mode — the door just won't pre-select next time */
  }
}

interface NewChatModalProps {
  engines: ChatEngineChoice[];
  onPick: (engineId: string) => Promise<void>;
  onClose: () => void;
}

export function NewChatModal({ engines, onPick, onClose }: NewChatModalProps) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [last, setLast] = useState<string | null>(null);

  // Read on mount, not at module scope — localStorage is unavailable during SSR.
  useEffect(() => setLast(readLastEngine()), []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const pick = useCallback(
    async (id: string) => {
      setBusy(id);
      setError(null);
      try {
        await onPick(id);
        rememberEngine(id);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Could not start this chat');
        setBusy(null);
      }
    },
    [onPick],
  );

  return createPortal(
    <>
      <div
        className="fixed inset-0 bg-black/50 animate-in fade-in duration-150"
        style={{ zIndex: Z_CONFIRM_BACKDROP }}
        onClick={onClose}
      />
      {/* A centered card on a desktop, a BOTTOM SHEET on a phone — the
          conventional mobile shape (thumb-reachable, no floating card fighting
          the keyboard). `sm:` is the 640px breakpoint the OS uses everywhere. */}
      <div
        className="fixed inset-0 flex items-end sm:items-center justify-center p-0 sm:p-4 pointer-events-none"
        style={{ zIndex: Z_CONFIRM_DIALOG }}
      >
        <div
          className="pointer-events-auto w-full sm:max-w-sm max-h-[85vh] overflow-y-auto rounded-t-2xl sm:rounded-lg border border-border bg-card p-5 shadow-xl animate-in fade-in slide-in-from-bottom-4 sm:slide-in-from-bottom-0 sm:zoom-in-95 duration-150"
          style={{ paddingBottom: 'max(1.25rem, env(safe-area-inset-bottom))' }}
          role="dialog"
          aria-modal="true"
        >
          <div className="flex items-start justify-between">
            <h3 className="text-base font-semibold text-card-foreground">
              Which engine?
            </h3>
            <button
              type="button"
              onClick={onClose}
              className="p-1 -mr-1 -mt-1 rounded text-muted-foreground hover:text-foreground hover:bg-muted"
              aria-label="Close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* ADR-559 D3 — an unavailable engine is SHOWN, disabled, with its
              reason. Hiding it is worse: a member who expects DeepSeek and
              sees an empty space concludes the app is broken. `available`
              absent means available (envelope compatibility). */}
          <div className="mt-3 space-y-1">
            {engines.map((e) => {
              const dark = e.available === false;
              return (
                <button
                  key={e.id}
                  type="button"
                  disabled={!!busy || dark}
                  aria-disabled={dark}
                  onClick={() => void pick(e.id)}
                  className={cn(
                    'w-full flex items-center gap-3 p-2 rounded-md text-left transition-colors',
                    dark
                      ? 'opacity-45 cursor-not-allowed'
                      : 'hover:bg-muted disabled:opacity-50',
                  )}
                >
                  <span className="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-muted-foreground shrink-0">
                    {engineBrandIcon(e.id)}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm">{e.label}</span>
                    {dark && (
                      <span className="block text-xs text-muted-foreground truncate">
                        {UNAVAILABLE_COPY[e.unavailable_reason ?? ''] ?? 'unavailable'}
                      </span>
                    )}
                  </span>
                  {last === e.id && !busy && !dark && (
                    <span className="flex items-center gap-1 text-[10px] text-muted-foreground shrink-0">
                      <Check className="w-3 h-3" />
                      last used
                    </span>
                  )}
                  {busy === e.id && (
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-muted-foreground shrink-0" />
                  )}
                </button>
              );
            })}
          </div>

          {error && (
            <p className="mt-3 text-xs text-destructive" role="alert">
              {error}
            </p>
          )}

          {/* The other two acts, named so the member knows where they live.
              Adding a colleague or a teammate happens IN the conversation
              (the cast), not at this door. */}
          <div className="mt-4 pt-3 border-t border-border space-y-1">
            {/* The door asks "which engine?" but the roster answers only with
                names — a member with no basis to choose had nowhere to go.
                /engines is that basis (external benchmarks + their own usage);
                it ranks nothing, so it never goes stale on a model release. */}
            <a
              href="/engines"
              target="_blank"
              rel="noopener noreferrer"
              className="block text-xs text-muted-foreground hover:text-foreground"
            >
              Not sure which to pick? →
            </a>
            <p className="text-xs text-muted-foreground">
              Add people or agents once the chat is open.
            </p>
            <SurfaceLink
              to="agents"
              className="block text-xs text-muted-foreground hover:text-foreground"
              onClick={onClose}
            >
              Manage your agents →
            </SurfaceLink>
          </div>
        </div>
      </div>
    </>,
    document.body,
  );
}
