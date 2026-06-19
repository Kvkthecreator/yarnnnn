'use client';

/**
 * AttentionCenter — the agent-OS Notification Center (ADR-340 D3, P1).
 *
 * One top-bar item answering "what wants me since I last looked." It is
 * a DIFFERENT chrome role from the SystemStatusCluster: the cluster is
 * the Control Center analog (standing STATE — autonomy, money, reach);
 * this is the Notification Center analog (EVENTS demanding the
 * operator). macOS keeps these deliberately separate; so do we.
 *
 * Binding discipline (ADR-340 D3 / Derived Principle 29): attention is
 * DERIVED, NEVER STORED. No notifications table exists or may exist —
 * every row here is a live derivation over already-ratified substrate:
 *
 *   - pending `action_proposals` (the Decide act)        → api.proposals.list
 *   - material-weight narrative since last looked (Read) → api.feed.globalHistory
 *     (the ADR-219 weight taxonomy — material/routine — IS the
 *     notification classification; nothing is re-classified here)
 *   - runway warnings (low balance)                      → api.integrations.getLimits
 *
 * Every row deep-links into the operator's real home for the act. Per
 * ADR-346 the bell now lands on the Operation composition — the surface
 * that CARRIES controls — instead of the bare mirrors: Decide rows →
 * operation?pane=resolve (the Queue body, where you approve); Read rows →
 * operation?pane=understand (the Feed narrative); billing warning →
 * settings?pane=billing. The mirrors stay reachable behind Operation
 * (the escape hatch), but the bell stops being a dead-end router that
 * can only point. The "last looked" cursor is client-side presentation
 * state in localStorage, same single-device-continuity stance as the
 * window-manager preferences (lib/shell/surface-preferences.ts) — it is
 * a read cursor, not workspace state, and never touches substrate.
 *
 * Consequence (ADR-340 D3): mirror surfaces stop being attention
 * destinations — the operator arrives at the Queue by routing, not by
 * remembering to check it.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Bell } from 'lucide-react';
import { api } from '@/lib/api/client';
import { proposalActionLabel } from '@/lib/proposal-labels';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { Z_POPOVER } from '@/lib/shell/z-tiers';
import { cn } from '@/lib/utils';
import { useRouter } from 'next/navigation';

const REFRESH_INTERVAL_MS = 60_000;
const LOW_BALANCE_THRESHOLD_USD = 1.0;
const LAST_SEEN_KEY = 'yarnnn:attention:last-seen';
const MAX_ROWS_PER_SECTION = 5;

interface PendingProposal {
  id: string;
  primitive: string;
  family: 'capital' | 'substrate';
  task_slug: string | null;
  agent_slug: string | null;
  created_at: string;
}

interface MaterialEvent {
  id: string;
  role: string;
  headline: string;
  created_at: string;
}

function readLastSeen(): string | null {
  if (typeof window === 'undefined' || typeof localStorage === 'undefined') return null;
  try {
    return localStorage.getItem(LAST_SEEN_KEY);
  } catch {
    return null;
  }
}

function writeLastSeen(iso: string) {
  if (typeof window === 'undefined' || typeof localStorage === 'undefined') return;
  try {
    localStorage.setItem(LAST_SEEN_KEY, iso);
  } catch {
    // Quota/private-mode failures are non-fatal — the cursor simply
    // doesn't persist and every material event reads as unseen.
  }
}

export function AttentionCenter() {
  const [isOpen, setIsOpen] = useState(false);
  const [proposals, setProposals] = useState<PendingProposal[]>([]);
  const [materialEvents, setMaterialEvents] = useState<MaterialEvent[]>([]);
  const [lowBalance, setLowBalance] = useState<number | null>(null);
  const [lastSeen, setLastSeen] = useState<string | null>(() => readLastSeen());
  const containerRef = useRef<HTMLDivElement>(null);
  // ADR-346: navigateToSurface (not foregroundSurface) — it writes the
  // ?pane= param so the bell lands on the right Operation act.
  const { navigateToSurface } = useSurfacePreferences();
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;

    const derive = async () => {
      const [proposalsResult, historyResult, limitsResult] = await Promise.allSettled([
        api.proposals.list('pending', 20),
        api.chat.globalHistory(1),
        api.integrations.getLimits(),
      ]);
      if (cancelled) return;

      if (proposalsResult.status === 'fulfilled') {
        setProposals(
          (proposalsResult.value.proposals || []).map((p) => ({
            id: p.id,
            primitive: p.primitive,
            family: p.family,
            task_slug: p.task_slug,
            agent_slug: p.agent_slug,
            created_at: p.created_at,
          })),
        );
      }

      if (historyResult.status === 'fulfilled') {
        // ADR-219 weight taxonomy is the classification — surface
        // material-weight, non-operator narrative entries only.
        const events: MaterialEvent[] = [];
        for (const session of historyResult.value.sessions || []) {
          for (const msg of session.messages || []) {
            if (msg.role === 'user') continue;
            if (msg.metadata?.weight !== 'material') continue;
            events.push({
              id: msg.id,
              role: msg.role,
              headline: msg.metadata?.summary || msg.content?.slice(0, 120) || '(event)',
              created_at: msg.created_at,
            });
          }
        }
        events.sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
        setMaterialEvents(events);
      }

      if (limitsResult.status === 'fulfilled') {
        const balance = (limitsResult.value as { balance_usd: number }).balance_usd;
        setLowBalance(balance <= LOW_BALANCE_THRESHOLD_USD ? balance : null);
      }
    };

    derive();
    const interval = setInterval(derive, REFRESH_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  // Click-outside + Escape close (same pattern as StatusItemPopover).
  useEffect(() => {
    if (!isOpen) return;
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKey);
    };
  }, [isOpen]);

  const unseenMaterial = materialEvents.filter(
    (e) => !lastSeen || e.created_at > lastSeen,
  );

  const badgeCount = proposals.length + unseenMaterial.length;
  const hasWarning = lowBalance != null;

  const toggleOpen = useCallback(() => {
    setIsOpen((prev) => {
      const next = !prev;
      if (next) {
        // Opening the center IS the "I looked" act — advance the read
        // cursor so the unseen-material count resets. The events stay
        // listed (recent context), only the count derivation moves.
        const now = new Date().toISOString();
        writeLastSeen(now);
        setLastSeen(now);
      }
      return next;
    });
  }, []);

  // ADR-346: the bell lands on the Operation composition (the surface that
  // carries controls) — "To do" rows → the resolve pane, "Activity" rows →
  // the understand pane (the labels match the Attention section headers so
  // the bell + surface speak one language; pane keys unchanged). Billing
  // stays an account pane. Instead of the bare mirrors.
  const goTo = useCallback(
    (target: 'resolve' | 'understand' | 'billing') => {
      setIsOpen(false);
      if (target === 'billing') {
        router.push('/settings?pane=billing');
      } else {
        navigateToSurface('operation', { pane: target });
      }
    },
    [navigateToSurface, router],
  );

  // ADR-340 P4 F3: operator-language labels via the shared labeler —
  // Stage-1 eval found the primitive slug rendering at the moment of
  // highest consequence ("platform_trading_submit_order"); the operator's
  // concept is "a trade wants my approval."
  const proposalLabel = (p: PendingProposal) => {
    const scope = p.task_slug || p.agent_slug;
    return `${proposalActionLabel(p)}${scope ? ` · ${scope}` : ''}`;
  };

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={toggleOpen}
        className={cn(
          'relative w-8 h-8 rounded-md flex items-center justify-center transition-colors',
          hasWarning
            ? 'text-amber-700 hover:bg-amber-100 dark:text-amber-300 dark:hover:bg-amber-900/30'
            : badgeCount > 0
              ? 'text-foreground hover:bg-muted'
              : 'text-muted-foreground hover:bg-muted hover:text-foreground',
          isOpen && 'bg-muted',
        )}
        title="Attention"
        aria-label={`Attention center${badgeCount > 0 ? ` — ${badgeCount} items` : ''}`}
        aria-expanded={isOpen}
      >
        <Bell className="w-4 h-4 shrink-0" />
        {badgeCount > 0 && (
          <span
            aria-hidden
            className="absolute -top-0.5 -right-0.5 min-w-[14px] h-[14px] px-0.5 rounded-full bg-destructive text-destructive-foreground text-[9px] leading-[14px] text-center font-medium"
          >
            {badgeCount > 9 ? '9+' : badgeCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div
          style={{ zIndex: Z_POPOVER }}
          className="absolute top-full right-0 mt-1 w-80 max-w-[calc(100vw-1rem)] bg-background border border-border rounded-lg shadow-lg overflow-hidden"
          role="dialog"
          aria-label="Attention center"
        >
          <div className="px-3 py-2 border-b border-border bg-muted/30 text-sm font-medium">
            Attention
          </div>

          <div className="max-h-96 overflow-y-auto">
            {hasWarning && (
              <button
                type="button"
                onClick={() => goTo('billing')}
                className="w-full text-left px-3 py-2 text-xs text-amber-700 dark:text-amber-300 hover:bg-muted transition-colors border-b border-border/60"
              >
                Balance is low (${lowBalance?.toFixed(2)}) — workspace hard-stops at $0
              </button>
            )}

            {proposals.length > 0 && (
              <div className="border-b border-border/60">
                <div className="px-3 pt-2 pb-1 text-[10px] uppercase tracking-wide text-muted-foreground">
                  To do
                </div>
                {proposals.slice(0, MAX_ROWS_PER_SECTION).map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => goTo('resolve')}
                    className="w-full text-left px-3 py-1.5 text-xs hover:bg-muted transition-colors"
                  >
                    <span className="text-foreground">{proposalLabel(p)}</span>
                  </button>
                ))}
                {proposals.length > MAX_ROWS_PER_SECTION && (
                  <button
                    type="button"
                    onClick={() => goTo('resolve')}
                    className="w-full text-left px-3 py-1.5 text-[11px] text-muted-foreground hover:bg-muted transition-colors"
                  >
                    +{proposals.length - MAX_ROWS_PER_SECTION} more pending…
                  </button>
                )}
              </div>
            )}

            {materialEvents.length > 0 && (
              <div>
                <div className="px-3 pt-2 pb-1 text-[10px] uppercase tracking-wide text-muted-foreground">
                  Activity
                </div>
                {materialEvents.slice(0, MAX_ROWS_PER_SECTION).map((e) => (
                  <button
                    key={e.id}
                    type="button"
                    onClick={() => goTo('understand')}
                    className="w-full text-left px-3 py-1.5 text-xs hover:bg-muted transition-colors"
                  >
                    <span className="block text-foreground truncate">{e.headline}</span>
                    <span className="block text-[10px] text-muted-foreground">
                      {new Date(e.created_at).toLocaleString([], {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </button>
                ))}
              </div>
            )}

            {!hasWarning && proposals.length === 0 && materialEvents.length === 0 && (
              <p className="px-3 py-4 text-xs text-muted-foreground">
                Nothing needs you. To-dos, activity, and runway warnings
                surface here.
              </p>
            )}
          </div>

          <button
            type="button"
            onClick={() => goTo('resolve')}
            className="w-full text-left px-3 py-2 text-xs text-primary hover:bg-muted border-t border-border transition-colors"
          >
            Open Operation →
          </button>
        </div>
      )}
    </div>
  );
}
