'use client';

/**
 * NewChatModal — starting a chat is choosing WHO to talk to.
 *
 * This replaced an INLINE panel that pushed the lane list down inside the
 * sidebar (which itself replaced a toolbar row of chips + a name field — the
 * pre-registry create form with new words in it). Inline was still the lazy
 * shape: choosing a colleague is a deliberate act with its own moment, not a
 * drawer that shoves the list around. A modal gives the act a room.
 *
 * THE FACES ARE THE FORM. No name field — a lane auto-names from its first
 * message (Phase-A hygiene), so asking up front was a field the member had no
 * answer to yet. One click starts the chat.
 *
 * The row says WHO first, then what they are (`Critic · GPT-5`): the operator's
 * rule — a nickname must still say what it IS, at minimum the role and the
 * model. Identity leads; the technical fact rides quietly behind.
 *
 * Errors are SHOWN, never swallowed. The live bug this fixes: creating a lane
 * 409'd (the cap counted Studio's bound lanes) and the FE's `catch {}` dropped
 * it silently — the member clicked Lisa, nothing happened, no reason given.
 */

import { useCallback, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Loader2, X } from 'lucide-react';
import { AgentFace } from '@/components/agents/AgentFace';
import { SurfaceLink } from '@/components/shell/SurfaceLink';
import { Z_CONFIRM_BACKDROP, Z_CONFIRM_DIALOG } from '@/lib/shell/z-tiers';

export interface ChatAgentChoice {
  slug: string;
  name: string;
  blurb: string;
  avatar_url?: string;
  role?: string;
  engine?: string;
  kernel?: boolean;
}

interface NewChatModalProps {
  agents: ChatAgentChoice[];
  onPick: (slug: string) => Promise<void>;
  onClose: () => void;
}

export function NewChatModal({ agents, onPick, onClose }: NewChatModalProps) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const pick = useCallback(
    async (slug: string) => {
      setBusy(slug);
      setError(null);
      try {
        await onPick(slug);
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
      <div
        className="fixed inset-0 flex items-center justify-center p-4 pointer-events-none"
        style={{ zIndex: Z_CONFIRM_DIALOG }}
      >
        <div
          className="pointer-events-auto w-full max-w-sm rounded-lg border border-border bg-card p-5 shadow-xl animate-in fade-in zoom-in-95 duration-150"
          role="dialog"
          aria-modal="true"
        >
          <div className="flex items-start justify-between">
            <h3 className="text-base font-semibold text-card-foreground">
              Who do you want to talk to?
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

          <div className="mt-3 space-y-1">
            {agents.map((a) => (
              <button
                key={a.slug}
                type="button"
                disabled={!!busy}
                onClick={() => void pick(a.slug)}
                className="w-full flex items-center gap-3 p-2 rounded-md hover:bg-muted text-left transition-colors disabled:opacity-50"
              >
                <AgentFace name={a.name} avatarUrl={a.avatar_url} />
                <span className="min-w-0 flex-1">
                  <span className="block text-sm">{a.name}</span>
                  <span className="block text-xs text-muted-foreground truncate">
                    {a.kernel === false
                      ? [a.role, a.engine].filter(Boolean).join(' · ')
                      : a.blurb}
                  </span>
                </span>
                {busy === a.slug && (
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

          <div className="mt-4 pt-3 border-t border-border">
            <SurfaceLink
              to="agents"
              className="text-xs text-muted-foreground hover:text-foreground"
              onClick={onClose}
            >
              Make an agent of your own →
            </SurfaceLink>
          </div>
        </div>
      </div>
    </>,
    document.body,
  );
}
