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
 *   - "To do"     (present — what wants my decision)  → pending action_proposals,
 *                  honestly labeled (ADR-410 D2: action + proposer + the
 *                  dial line) → Operation ?pane=resolve
 *   - "Activity"  (past — what just happened)          → the WORKSPACE TIMELINE
 *                  (ADR-410 D1: peer + agent acts only — actor ≠ viewer —
 *                  since last looked; self-acts excluded by construction,
 *                  ADR-405 D4). Re-sourced from chat.globalHistory, which
 *                  post-ADR-407-Phase-4 was the viewer's PRIVATE thread —
 *                  self-echo in, peers invisible. → ?pane=understand
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
 * (api.recurrences.list). The "last looked" cursor is presentation state —
 * localStorage keyed per (workspace, user) as the local cache, write-through
 * to the member-state store ('attention') for cross-device continuity
 * (ADR-407 Phase 3; a read cursor, not workspace state).
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
import { shellStateSuffix } from '@/lib/shell/surface-preferences';
import { Z_POPOVER } from '@/lib/shell/z-tiers';
import { usePopoverDismissal } from '@/lib/shell/usePopoverDismissal';
import { cn } from '@/lib/utils';
import { PrincipalBadge } from '@/lib/workspace/principal-badge';
import { proposalQueuedByDialLine } from '@/lib/proposal-labels';
import { resolveActorForViewer, useWorkspaceRoster } from '@/lib/workspace/viewer';
import { actorLine } from '@/lib/workspace/timeline-rows';

const REFRESH_INTERVAL_MS = 60_000;
const LOW_BALANCE_THRESHOLD_USD = 1.0;
// ADR-407 Phase 3 — re-keyed per (workspace, user) via shellStateSuffix (the
// same suffix the shell/window keys use); the bare key was browser-global, so
// one user's "I looked" advanced every user's/workspace's cursor on a shared
// browser. Also write-through to the server-backed member-state store
// ('attention'); on mount the NEWER of server vs local wins.
const LAST_SEEN_KEY_PREFIX = 'yarnnn:attention:last-seen:';
const MAX_ROWS_PER_SECTION = 5;

interface PendingProposal {
  id: string;
  primitive: string;
  family: 'capital' | 'substrate';
  task_slug: string | null;
  agent_slug: string | null;
  created_at: string;
  /** ADR-410 D2 — the proposer (drives the dial line + attribution). */
  source: string | null;
}

/** ADR-410 D1 — one peer/agent act from the workspace timeline. */
interface PeerActivity {
  id: string;
  actor: string | null;
  actorId: string | null;
  kind: 'revision' | 'invocation';
  title: string;
  detail: string | null;
  created_at: string;
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

function lastSeenKey(userId: string): string {
  return `${LAST_SEEN_KEY_PREFIX}${shellStateSuffix(userId)}`;
}

function readLastSeen(userId: string): string | null {
  if (typeof window === 'undefined' || typeof localStorage === 'undefined') return null;
  try {
    return localStorage.getItem(lastSeenKey(userId));
  } catch {
    return null;
  }
}

function writeLastSeen(userId: string, iso: string) {
  if (typeof window === 'undefined' || typeof localStorage === 'undefined') return;
  try {
    localStorage.setItem(lastSeenKey(userId), iso);
  } catch {
    // Quota/private-mode failures are non-fatal — the cursor simply
    // doesn't persist and every material event reads as unseen.
  }
}

export function AttentionCenter() {
  const [isOpen, setIsOpen] = useState(false);
  const [proposals, setProposals] = useState<PendingProposal[]>([]);
  const [activity, setActivity] = useState<PeerActivity[]>([]);
  const [upcoming, setUpcoming] = useState<UpcomingFire[]>([]);
  const [lowBalance, setLowBalance] = useState<number | null>(null);
  const [lastSeen, setLastSeen] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  // ADR-346: navigateToSurface (not foregroundSurface) — it writes the
  // ?pane= param so the bell lands on the right Operation act. userId is the
  // same resolution useSurfacePreferences performs (its provider resolves it
  // once via supabase.auth.getUser()) — reused here for the per-(workspace,
  // user) cursor key.
  const { navigateToSurface, userId, foregrounded } = useSurfacePreferences();

  // 2026-07-08 — the bell is this window's ONLY top-bar door (the Dock tile
  // is suppressed via `chrome_fronted`), so it must carry the foregrounded
  // highlight a Dock icon otherwise would: when the Notifications window fills
  // the screen, the bell reads as active — "the glyph is the window you're in."
  const windowActive = foregrounded === 'notifications';

  // ADR-407 Phase 3 — resolve the read cursor once userId is known: read the
  // local (workspace, user)-keyed cursor, then reconcile with the server copy
  // ('attention' member-state) — the NEWER of the two wins (ISO strings
  // compare lexicographically). Failures are non-fatal (local-only).
  useEffect(() => {
    if (!userId) return;
    let cancelled = false;
    const local = readLastSeen(userId);
    if (local) setLastSeen(local);
    api.memberState
      .get('attention')
      .then((res) => {
        if (cancelled) return;
        const serverSeen = (res.value as { lastSeen?: unknown } | null)?.lastSeen;
        if (typeof serverSeen === 'string' && (!local || serverSeen > local)) {
          setLastSeen(serverSeen);
          writeLastSeen(userId, serverSeen);
        }
      })
      .catch((e) => {
        console.warn('[attention] member-state read failed (local-only):', e);
      });
    return () => {
      cancelled = true;
    };
  }, [userId]);

  useEffect(() => {
    let cancelled = false;

    const derive = async () => {
      const [proposalsResult, timelineResult, limitsResult, recurrencesResult] =
        await Promise.allSettled([
          api.proposals.list('pending', 20),
          // ADR-410 D1 — the ONE "what happened" source (the attributed
          // ledgers). chat.globalHistory is gone: post-ADR-407-Phase-4 it
          // read the viewer's PRIVATE thread — self-echo, peers invisible.
          api.workspace.timeline(60),
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
            source: (p as { source?: string | null }).source ?? null,
          })),
        );
      }

      if (timelineResult.status === 'fulfilled') {
        // Revision + invocation acts (proposal lifecycle renders in TO DO /
        // the Notifications workbench, not twice here). Self-filtering
        // happens at render time (viewer + roster); D6's sub-minute
        // invocation dedupe happens here.
        const seen = new Set<string>();
        const rows: PeerActivity[] = [];
        for (const e of timelineResult.value.entries || []) {
          if (e.kind !== 'revision' && e.kind !== 'invocation') continue;
          if (!e.at) continue;
          if (e.kind === 'invocation') {
            const minuteKey = `${e.slug}:${e.at.slice(0, 16)}`;
            if (seen.has(minuteKey)) continue;
            seen.add(minuteKey);
          }
          rows.push({
            id: e.id,
            actor: e.actor,
            actorId: e.actor_id,
            kind: e.kind,
            title: e.title || '',
            detail: e.detail,
            created_at: e.at,
          });
        }
        setActivity(rows);
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

  // ADR-410 D1 — peer-first: the viewer's own acts are excluded by
  // construction (ADR-405 D4 — you don't need to be told what you just
  // did). Resolution via the ADR-412 D6 viewer layer (roster + viewer id).
  const roster = useWorkspaceRoster();
  const peerActivity = activity
    .map((e) => ({ e, who: resolveActorForViewer(e.actor, e.actorId, userId, roster) }))
    .filter(({ who }) => !who.isSelf);

  const unseenPeer = peerActivity.filter(
    ({ e }) => !lastSeen || e.created_at > lastSeen,
  );

  const badgeCount = proposals.length + unseenPeer.length;
  const hasWarning = lowBalance != null;

  const toggleOpen = useCallback(() => {
    setIsOpen((prev) => {
      const next = !prev;
      if (next) {
        // Opening the center IS the "I looked" act — advance the read
        // cursor so the unseen-material count resets. The events stay
        // listed (recent context), only the count derivation moves.
        const now = new Date().toISOString();
        if (userId) writeLastSeen(userId, now);
        setLastSeen(now);
        // ADR-407 Phase 3 — fire-and-forget write-through to the server
        // copy so the cursor follows the member across devices.
        api.memberState.put('attention', { lastSeen: now }).catch((e) => {
          console.warn('[attention] member-state write failed (local-only):', e);
        });
      }
      return next;
    });
  }, [userId]);

  // ADR-346: the bell lands on the Operation composition (the surface that
  // carries controls) — "To do" rows → the resolve pane, "Activity" rows →
  // the understand pane (the labels match the Attention section headers so
  // the bell + surface speak one language; pane keys unchanged). Billing
  // stays an account pane. Instead of the bare mirrors.
  const goTo = useCallback(
    (target: 'resolve' | 'understand' | 'tune' | 'billing') => {
      setIsOpen(false);
      if (target === 'billing') {
        // ADR-429 §13.3 (2026-07-09) — billing re-homed to the account door
        // (User Settings, Vercel-style; content stays workspace-scoped).
        // navigateToSurface keeps the /desktop pathname (History-API param update).
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

  // ADR-410 D4 — actor-first activity lines, no internal enums: a revision
  // reads "‹actor› updated ‹file›"; an invocation "‹actor› ran ‹Title›"
  // (mode/trigger enum words never render; the FE label layer owns this).
  // Shared grammar with the Notifications workbench (timeline-rows —
  // ADR-410 D5 one-grammar discipline).
  const activityLine = (e: PeerActivity, who: string) =>
    actorLine({ kind: e.kind, title: e.title }, who);

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
          // Foregrounded window → solid fill (matches the Dock's foregrounded
          // icon treatment); popover-open → muted. windowActive wins.
          windowActive ? 'bg-foreground text-background' : isOpen && 'bg-muted',
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
                    <span className="block text-foreground">{proposalLabel(p)}</span>
                    {/* ADR-410 D2 — honest labels: the proposer (icon) + the
                        dial line, so a queue entry reads as the AGENT's dial
                        product, never "your work awaits a superior". */}
                    <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                      {p.source && (
                        <PrincipalBadge authoredBy={p.source} showLabel={false} size={11} />
                      )}
                      {proposalQueuedByDialLine(p.source) ?? formatRelativeTime(p.created_at)}
                    </span>
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

            {peerActivity.length > 0 && (
              <div className={upcoming.length > 0 ? 'border-b border-border/60' : undefined}>
                <div className="px-3 pt-2 pb-1 text-[10px] uppercase tracking-wide text-muted-foreground">
                  Activity
                </div>
                {peerActivity.slice(0, MAX_ROWS_PER_SECTION).map(({ e, who }) => (
                  <button
                    key={e.id}
                    type="button"
                    onClick={() => goTo('understand')}
                    className="w-full text-left px-3 py-1.5 text-xs hover:bg-muted transition-colors"
                  >
                    <span className="block text-foreground truncate">
                      {activityLine(e, who.label)}
                    </span>
                    <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                      {e.actor && (
                        <PrincipalBadge authoredBy={e.actor} showLabel={false} size={11} />
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
              peerActivity.length === 0 &&
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
