'use client';

/**
 * OverviewSurface — composes three panes for the cockpit HOME (ADR-199).
 *
 * Pane composition follows ADR-198 §3 archetype vocabulary:
 *   - SinceLastLookPane: Briefing archetype (temporal, pointer-based)
 *   - NeedsMePane: Queue archetype (pending proposals + alerts, actionable)
 *   - SnapshotPane: Dashboard-snippets (linked, not embedded, per I2)
 *
 * Day-zero empty state (ADR-161 heartbeat discipline): when the workspace
 * has zero agents AND zero active tasks AND zero pending proposals, render
 * OverviewEmptyState instead of the three panes. The operator sees a
 * welcome + explicit CTAs rather than three "nothing here" panes.
 *
 * Invariant I2 discipline: panes LINK to foreign substrate, never embed it.
 * Clicking a proposal approves/rejects in place (Queue is the home of
 * proposal affordances). Clicking a snapshot tile deep-links to Work / Team /
 * Context / Review — that's cross-substrate navigation, not embedding.
 */

import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import { SinceLastLookPane } from './SinceLastLookPane';
import { NeedsMePane } from './NeedsMePane';
import { SnapshotPane } from './SnapshotPane';
import { OverviewEmptyState } from './OverviewEmptyState';

export interface OverviewSurfaceProps {
  onOpenChatDraft: (prompt: string) => void;
}

type DayZeroState = 'loading' | 'day-zero' | 'active';

export function OverviewSurface({ onOpenChatDraft }: OverviewSurfaceProps) {
  const [state, setState] = useState<DayZeroState>('loading');

  useEffect(() => {
    void detectDayZero().then((isDayZero) =>
      setState(isDayZero ? 'day-zero' : 'active'),
    );
  }, []);

  if (state === 'loading') {
    // Show panes in loading state — they each handle their own loading UX.
    return (
      <div className="flex flex-1 flex-col gap-6 overflow-y-auto px-6 py-6">
        <NeedsMePane onOpenChatDraft={onOpenChatDraft} />
        <SinceLastLookPane />
        <SnapshotPane />
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
      <SnapshotPane />
    </div>
  );
}

/**
 * Detect day-zero: zero agents + zero active tasks + zero pending proposals.
 *
 * Uses Promise.allSettled so any failing endpoint degrades to "assume
 * non-zero" (non-empty state is the safer default — better to show panes
 * than accidentally show the cold-start welcome to an active operator).
 */
async function detectDayZero(): Promise<boolean> {
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

  const hasAgents = agents.length > 0;
  const hasActiveTasks = tasks.some((t) => t.status === 'active');
  const hasPendingProposals = proposals.length > 0;

  return !hasAgents && !hasActiveTasks && !hasPendingProposals;
}
