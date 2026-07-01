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
 * The bell is the glanceable HEAD of the Operation surface (ADR-346) — the
 * same object at two zooms. It is a TEMPORAL triad (past · present · future),
 * not merely "what needs you," and it speaks the SAME operator words as the
 * Operation panes so the bell and the surface it lands on read as one thing:
 *
 *   - "To do"     (present — what wants my decision)  → pending action_proposals
 *                  → Operation ?pane=resolve (the Queue body, where you approve)
 *   - "Activity"  (past — what just happened)          → material-weight narrative
 *                  since last looked → Operation ?pane=understand (the Feed)
 *   - "Coming up" (future — what's scheduled next)     → recurrence next_run_at
 *                  → Operation ?pane=tune (the Schedule list)
 *   - runway warning (low balance)                     → settings ?pane=billing
 *
 * Operator-vocabulary partition (the deliberate one): the bell NEVER shows
 * engine words (wake / recurrence / invocation / proposal). Those stay in
 * substrate + ADRs + the run-ledger detail. "Coming up" rows show the
 * recurrence's operator-facing TITLE + a relative time, never "next wake."
 *
 * Binding discipline (ADR-340 D3 / Derived Principle 29): attention is
 * DERIVED, NEVER STORED. No notifications table exists or may exist — every
 * row is a live derivation over already-ratified substrate (proposals,
 * ADR-219 material narrative, recurrence next_run_at, balance). The "Coming
 * up" limb adds NO state — next_run_at already rides on every recurrence
 * (api.recurrences.list). The "last looked" cursor is client-side
 * presentation state in localStorage (a read cursor, not workspace state).
 *
 * Consequence (ADR-340 D3): mirror surfaces stop being attention
 * destinations — the operator arrives at the Queue by routing, not by
 * remembering to check it.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Bell } from 'lucide-react';
import { api } from '@/lib/api/client';
import { proposalActionLabel } from '@/lib/proposal-labels';
import { formatRelativeTime } from '@/lib/formatting';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { Z_POPOVER } from '@/lib/shell/z-tiers';
import { usePopoverDismissal } from '@/lib/shell/usePopoverDismissal';
import { cn } from '@/lib/utils';
import { PrincipalBadge } from '@/lib/workspace/principal-badge';

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
  /** Actor identity (2026-06-30): the authored_by taxonomy → the shared
   *  PrincipalBadge, so an Activity row shows the actor's icon + canonical
   *  label (fixing the "Claude" vs "chatgpt" casing drift in the raw headline). */
  authoredBy?: string;
}

// "Coming up" — a derived view over each recurrence's next_run_at. No new
// state: next_run_at already rides on the recurrence list (ADR-340 D3
// derived-never-stored preserved). title is the operator-facing label —
// never the engine "recurrence/wake" word.
interface UpcomingFire {
  slug: string;
  title: string;
  next_run_at: string;
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
  const [upcoming, setUpcoming] = useState<UpcomingFire[]>([]);
  const [lowBalance, setLowBalance] = useState<number | null>(null);
  const [lastSeen, setLastSeen] = useState<string | null>(() => readLastSeen());
  const containerRef = useRef<HTMLDivElement>(null);
  // ADR-346: navigateToSurface (not foregroundSurface) — it writes the
  // ?pane= param so the bell lands on the right Operation act.
  const { navigateToSurface } = useSurfacePreferences();

  useEffect(() => {
    let cancelled = false;

    const derive = async () => {
      const [proposalsResult, historyResult, limitsResult, recurrencesResult] =
        await Promise.allSettled([
          api.proposals.list('pending', 20),
          api.chat.globalHistory(1),
          api.integrations.getLimits(),
          api.recurrences.list({ status: 'active' }),
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
              authoredBy: msg.metadata?.authored_by,
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

      if (recurrencesResult.status === 'fulfilled') {
        // "Coming up" — future-only next_run_at, non-paused, soonest first.
        // Pure derivation over the recurrence list (next_run_at already rides
        // on every row; no new state, ADR-340 D3 preserved). The title is the
        // operator-facing label — never the engine "recurrence/wake" word.
        const now = Date.now();
        const fires: UpcomingFire[] = (recurrencesResult.value || [])
          .filter((r) => !r.paused && r.next_run_at && Date.parse(r.next_run_at) > now)
          .map((r) => ({ slug: r.slug, title: r.title, next_run_at: r.next_run_at as string }))
          .sort((a, b) => Date.parse(a.next_run_at) - Date.parse(b.next_run_at));
        setUpcoming(fires);
      }
    };

    derive();
    const interval = setInterval(derive, REFRESH_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  // Click-outside + Escape close (shared dismissal contract, 2026-07-01).
  usePopoverDismissal(containerRef, isOpen, () => setIsOpen(false));

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
    (target: 'resolve' | 'understand' | 'tune' | 'billing') => {
      setIsOpen(false);
      if (target === 'billing') {
        // ADR-358 (2026-06-23) — open the billing pane of the account
        // (settings) window via navigateToSurface, which keeps the /desktop
        // pathname (History-API param update). The prior router.push(
        // '/settings?pane=billing') was a full-page nav that left the SPA
        // and reset the chat rail.
        navigateToSurface('settings', { pane: 'billing' });
      } else {
        navigateToSurface('notifications', { pane: target });
      }
    },
    [navigateToSurface],
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
        title="Notifications"
        aria-label={`Notifications${badgeCount > 0 ? ` — ${badgeCount} items` : ''}`}
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
          aria-label="Notifications"
        >
          <div className="px-3 py-2 border-b border-border bg-muted/30 text-sm font-medium">
            Notifications
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
              <div className={upcoming.length > 0 ? 'border-b border-border/60' : undefined}>
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
                    <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                      {/* Actor identity (2026-06-30): icon-only badge before
                          the timestamp — the headline already names the actor;
                          the icon makes Claude vs ChatGPT vs system legible at
                          a glance. */}
                      {e.authoredBy && (
                        <PrincipalBadge authoredBy={e.authoredBy} showLabel={false} size={11} />
                      )}
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

            {/* "Coming up" (future limb) — next scheduled fires, soonest
                first. Reference, not a demand: it does NOT inflate the badge
                (the badge counts only what NEEDS you — To do + unseen
                Activity). Deep-links to the Schedule pane. */}
            {upcoming.length > 0 && (
              <div>
                <div className="px-3 pt-2 pb-1 text-[10px] uppercase tracking-wide text-muted-foreground">
                  Coming up
                </div>
                {upcoming.slice(0, MAX_ROWS_PER_SECTION).map((u) => (
                  <button
                    key={u.slug}
                    type="button"
                    onClick={() => goTo('tune')}
                    className="w-full text-left px-3 py-1.5 text-xs hover:bg-muted transition-colors"
                  >
                    <span className="text-foreground">{u.title}</span>
                    <span className="text-[11px] text-muted-foreground">
                      {' · '}{formatRelativeTime(u.next_run_at)}
                    </span>
                  </button>
                ))}
                {upcoming.length > MAX_ROWS_PER_SECTION && (
                  <button
                    type="button"
                    onClick={() => goTo('tune')}
                    className="w-full text-left px-3 py-1.5 text-[11px] text-muted-foreground hover:bg-muted transition-colors"
                  >
                    +{upcoming.length - MAX_ROWS_PER_SECTION} more scheduled…
                  </button>
                )}
              </div>
            )}

            {!hasWarning &&
              proposals.length === 0 &&
              materialEvents.length === 0 &&
              upcoming.length === 0 && (
                <p className="px-3 py-4 text-xs text-muted-foreground">
                  Nothing here yet. To-dos, activity, what&apos;s coming up, and
                  runway warnings surface here.
                </p>
              )}
          </div>

          <button
            type="button"
            onClick={() => goTo('resolve')}
            className="w-full text-left px-3 py-2 text-xs text-primary hover:bg-muted border-t border-border transition-colors"
          >
            Open Notifications →
          </button>
        </div>
      )}
    </div>
  );
}
