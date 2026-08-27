'use client';

/**
 * NewChatModal — starting a chat is choosing a COLLEAGUE, or an engine.
 *
 * ADR-614 D1 REVERSES ADR-558 D1's centring. That ADR made this door ask
 * "which engine?", and its reasoning was sound for the defect it faced: the
 * modal had been asking "who do you want to talk to?" while listing four
 * different KINDS of thing as one flat set — a persona, kernel characters
 * each labelled with a model id, and a human being. Separating the acts was
 * right. Which one leads was the part that was wrong.
 *
 * A member starting work thinks "I want to write this deck", not "I want
 * Claude Sonnet 5". The colleague is the intent; the engine is the
 * implementation detail behind them (ADR-460 D4's original insight, which
 * ADR-558 preserved but demoted at this particular door). Engines stay one
 * click away, because "I want to use GPT-5" is a real and different intent —
 * it is simply the SECOND one, not the first.
 *
 * WHAT PICKING A COLLEAGUE ACTUALLY DOES — the load-bearing part. It seeds
 * the CAST: the same act as adding them from CastBar a second later, done at
 * the door. It does NOT write a birth-persona scalar onto the lane. ADR-558
 * D3's rule is untouched and still enforced server-side — the cast remains
 * the single authority on who replies (ADR-495 D1), so @mention, adding a
 * second colleague, and inviting a teammate all behave identically whether
 * the conversation started from a name or from an engine.
 *
 * The three acts ADR-558 separated are still separate; only their order at
 * this door changed:
 *   start a chat   → WHO, or which engine   (this modal)
 *   bring someone  → the CAST               (CastBar — ADR-495)
 *   configure one  → /agents                (character + connector scope)
 *
 * STICKY LAST-USED: the door MARKS what you last started with — a colleague
 * or an engine, one key, because they answer the same question. It does not
 * pre-select, reorder, or auto-scroll: every choice stays one click.
 *
 * Errors are SHOWN, never swallowed (the live 409 the old `catch {}` ate).
 */

import { useCallback, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Check, ChevronDown, Loader2, X } from 'lucide-react';
import { engineBrandIcon } from '@/lib/ai-providers/brand-icons';
import { BeingIcon } from '@/components/agents/BeingIcon';
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

/** A colleague the member can start a conversation with. The slice of the
 *  served `beings` row this door needs — copying the whole row would be a
 *  second home for a shape the envelope already carries. */
export interface ChatBeingChoice {
  slug: string;
  name: string;
  blurb: string;
  icon: string;
}

/** Where the member's last choice is remembered — a colleague slug OR an
 *  engine id, in ONE key, because at this door they answer the same question
 *  and only one of them can be the last thing you started. Two keys would let
 *  the door claim two "last used" marks at once.
 *
 *  VIEW STATE — a per-person convenience, deliberately not a workspace setting
 *  (a workspace default would be one member choosing for everyone). */
const LAST_START_KEY = 'yarnnn.chat.lastStart';

export function readLastStart(): string | null {
  try {
    return window.localStorage.getItem(LAST_START_KEY);
  } catch {
    return null;
  }
}

export function rememberStart(id: string): void {
  try {
    window.localStorage.setItem(LAST_START_KEY, id);
  } catch {
    /* private mode — the door just won't mark a last choice next time */
  }
}

interface NewChatModalProps {
  /** The colleagues on offer — the PRIMARY answer (ADR-614 D1). */
  beings: ChatBeingChoice[];
  engines: ChatEngineChoice[];
  /** Exactly one of the two is given. The caller turns that into the right
   *  create call; this door never assembles a request body itself. */
  onPick: (choice: { agent?: string; model?: string }) => Promise<void>;
  onClose: () => void;
}

export function NewChatModal({ beings, engines, onPick, onClose }: NewChatModalProps) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [last, setLast] = useState<string | null>(null);
  // Engines are the SECOND answer, so they start folded. A member who came for
  // a raw engine opens one row; a member who came for a colleague never sees
  // a model id — which is the whole point of the reordering.
  const [showEngines, setShowEngines] = useState(false);

  // Read on mount, not at module scope — localStorage is unavailable during SSR.
  useEffect(() => setLast(readLastStart()), []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const pick = useCallback(
    async (id: string, choice: { agent?: string; model?: string }) => {
      setBusy(id);
      setError(null);
      try {
        await onPick(choice);
        rememberStart(id);
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
              New chat
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

          {/* THE COLLEAGUES — the primary answer (ADR-614 D1). Each is one
              click, and picking one seeds the cast server-side. No engine is
              shown here: a member who picked Editor did not ask what Editor
              runs on, and printing it would hand them the spec sheet ADR-460
              removed for exactly that reason. */}
          <div className="mt-3 space-y-1">
            {beings.map((b) => (
              <button
                key={b.slug}
                type="button"
                disabled={!!busy}
                onClick={() => void pick(b.slug, { agent: b.slug })}
                className="w-full flex items-center gap-3 p-2 rounded-md text-left transition-colors hover:bg-muted disabled:opacity-50"
              >
                <span className="w-8 h-8 rounded-full bg-muted flex items-center justify-center shrink-0">
                  <BeingIcon icon={b.icon} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-sm">{b.name}</span>
                  <span className="block text-xs text-muted-foreground truncate">
                    {b.blurb}
                  </span>
                </span>
                {last === b.slug && !busy && (
                  <span className="flex items-center gap-1 text-[10px] text-muted-foreground shrink-0">
                    <Check className="w-3 h-3" />
                    last used
                  </span>
                )}
                {busy === b.slug && (
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-muted-foreground shrink-0" />
                )}
              </button>
            ))}
          </div>

          {error && (
            <p className="mt-3 text-xs text-destructive" role="alert">
              {error}
            </p>
          )}

          {/* THE ENGINES — the second answer, folded. "I want to use GPT-5" is
              a real intent; it is simply not the first one. */}
          <div className="mt-4 pt-3 border-t border-border">
            {!showEngines ? (
              <button
                type="button"
                onClick={() => setShowEngines(true)}
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
              >
                Or start with an engine
                <ChevronDown className="w-3 h-3" />
              </button>
            ) : (
              <>
                {/* ADR-559 D3 — an unavailable engine is SHOWN, disabled, with
                    its reason. Hiding it is worse: a member who expects
                    DeepSeek and sees an empty space concludes the app is
                    broken. `available` absent means available. */}
                <div className="space-y-1">
                  {engines.map((e) => {
                    const dark = e.available === false;
                    return (
                      <button
                        key={e.id}
                        type="button"
                        disabled={!!busy || dark}
                        aria-disabled={dark}
                        onClick={() => void pick(e.id, { model: e.id })}
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
                {/* The door lists engines by name only; /engines is the basis
                    for choosing between them (external benchmarks + the
                    member's own usage). It ranks nothing, so it never goes
                    stale on a model release. */}
                <a
                  href="/engines"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 block text-xs text-muted-foreground hover:text-foreground"
                >
                  Not sure which to pick? →
                </a>
              </>
            )}
          </div>
        </div>
      </div>
    </>,
    document.body,
  );
}
