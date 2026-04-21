'use client';

/**
 * OverviewSurface — composes three panes for the cockpit HOME (ADR-199 + ADR-203).
 *
 * Pane composition follows ADR-198 §3 archetype vocabulary:
 *   - SinceLastLookPane: Briefing archetype (temporal, pointer-based)
 *   - NeedsMePane: Queue archetype (pending proposals + alerts, actionable)
 *   - SnapshotPane: Dashboard-snippets (linked, not embedded, per I2)
 *   - IntelligenceCard: Synthesis artifact from maintain-overview task (ADR-204)
 *
 * Semantic day-zero (ADR-203): when the workspace is scaffolded but the
 * operator hasn't acted yet — no operator-authored agents
 * (origin != 'system_bootstrap'), no non-essential active tasks, no
 * pending proposals — render OverviewEmptyState instead of the three
 * panes. This is the common new-signup case post-ADR-189 scaffolding;
 * the previous (structural) threshold never fired.
 *
 * Invariant I2 discipline: panes LINK to foreign substrate, never embed it.
 */

import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import { SinceLastLookPane } from './SinceLastLookPane';
import { NeedsMePane } from './NeedsMePane';
import { SnapshotPane } from './SnapshotPane';
import { OverviewEmptyState } from './OverviewEmptyState';
import { IntelligenceCard } from './IntelligenceCard';

export interface OverviewSurfaceProps {
  onOpenChatDraft: (prompt: string) => void;
  /**
   * Called when semantic-day-zero detection resolves, so the page can
   * configure the ambient YARNNN rail to open by default with a seeded
   * first-session prompt (ADR-203 §3).
   */
  onDayZeroResolved?: (isDayZero: boolean) => void;
}

type DayZeroState = 'loading' | 'day-zero' | 'active';

export function OverviewSurface({
  onOpenChatDraft,
  onDayZeroResolved,
}: OverviewSurfaceProps) {
  const [state, setState] = useState<DayZeroState>('loading');

  useEffect(() => {
    void detectSemanticDayZero().then((isDayZero) => {
      setState(isDayZero ? 'day-zero' : 'active');
      onDayZeroResolved?.(isDayZero);
    });
  }, [onDayZeroResolved]);

  if (state === 'loading') {
    // Show panes in loading state — they each handle their own loading UX.
    return (
      <div className="flex flex-1 flex-col gap-6 overflow-y-auto px-6 py-6">
        <NeedsMePane onOpenChatDraft={onOpenChatDraft} />
        <SinceLastLookPane />
        <SnapshotPane isDayZero={false} />
        <IntelligenceCard />
      </div>
    );
  }

  if (state === 'day-zero') {
    return <OverviewEmptyState onOpenChatDraft={onOpenChatDraft} />;
  }

  return (
    <div className="flex flex-1 flex-col gap-6 overflow-y-auto px-6 py-6">
      <NeedsMePane onOpenChatDraft={onOpenChatDraft} />
      <SinceLastLookPane />
      <SnapshotPane isDayZero={false} />
      <IntelligenceCard />
    </div>
  );
}

/**
 * Detect **semantic** day-zero (ADR-203 §1).
 *
 * Pre-ADR-203 this function checked raw row counts. Post-ADR-189 every
 * YARNNN signup scaffolds 12 agents + 5 essential tasks — so raw-count
 * day-zero never fires. Semantic day-zero filters out the scaffold:
 *
 *   - operator-authored agent = origin != 'system_bootstrap'
 *   - operator-triggered task = !essential (essential=true means system
 *     heartbeat task like daily-update + back-office cleanup)
 *   - pending proposal = any proposal in queue (always operator-relevant)
 *
 * Returns true if NONE of the three exist — the workspace is structurally
 * scaffolded but the operator has not yet acted.
 *
 * Uses Promise.allSettled so any failing endpoint degrades to "assume
 * non-day-zero" (safer default — better to show panes than accidentally
 * show the cold-start welcome to an active operator).
 */
async function detectSemanticDayZero(): Promise<boolean> {
  const [agentsResult, tasksResult, proposalsResult] = await Promise.allSettled([
    api.agents.list(),
    api.tasks.list(),
    api.proposals.list('pending', 1),
  ]);

  const agents = agentsResult.status === 'fulfilled' ? agentsResult.value : null;
  const tasks = tasksResult.status === 'fulfilled' ? tasksResult.value : null;
  const proposals =
    proposalsResult.status === 'fulfilled'
      ? proposalsResult.value.proposals
      : null;

  // If any fetch failed, assume non-empty (safer default).
  if (agents === null || tasks === null || proposals === null) return false;

  const hasOperatorAuthoredAgents = agents.some(
    (a) => a.origin !== undefined && a.origin !== 'system_bootstrap',
  );
  const hasNonEssentialActiveTasks = tasks.some(
    (t) => t.status === 'active' && !t.essential,
  );
  const hasPendingProposals = proposals.length > 0;

  return (
    !hasOperatorAuthoredAgents &&
    !hasNonEssentialActiveTasks &&
    !hasPendingProposals
  );
}
