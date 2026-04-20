'use client';

/**
 * Overview Page — Cockpit HOME (ADR-199).
 *
 * The operator's mission-control landing surface per ADR-198 v2.
 * Three panes composed inside ThreePanelLayout:
 *   1. Since last look (Briefing archetype) — temporal changes since last session
 *   2. Needs me (Queue archetype) — pending action_proposals awaiting review
 *   3. Snapshot (Dashboard-snippets, linked-not-embedded) — book / workforce / context headlines
 *
 * Ambient YARNNN rail available via ThreePanelLayout (no new work — already shipped).
 * No new backend APIs — reads from existing /api/proposals, /api/agents, /api/tasks,
 * /api/workspace/file?path=.
 *
 * Design invariants (ADR-198):
 *   I1 — No surface holds state (substrate is authoritative)
 *   I2 — No surface embeds foreign substrate (all cross-references are links)
 *   I3 — Exactly one primary cognitive consumer (the operator)
 *
 * Deep-link forward-compat (ADR-202):
 *   Accepted query params: ?focus=queue|alerts (from expository-pointer emails)
 *                          ?since=<iso> (from daily-update briefings)
 *   Currently no-op — forward-compat so backend's deep-link rollout doesn't 404.
 *   Pane-focus scroll behavior will wire during ADR-202 Phase 3 if observed
 *   operator use shows the navigation value.
 */

import { useState } from 'react';
import { useSearchParams } from 'next/navigation';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';
import { ThreePanelLayout } from '@/components/shell/ThreePanelLayout';
import { PageHeader } from '@/components/shell/PageHeader';
import { OverviewSurface } from '@/components/overview/OverviewSurface';

export default function OverviewPage() {
  const searchParams = useSearchParams();
  const [chatDraftSeed, setChatDraftSeed] = useState<{ id: string; text: string } | null>(null);
  const [chatOpenSignal, setChatOpenSignal] = useState(0);

  // Forward-compat: accept ?focus=queue|alerts + ?since=<iso> per ADR-202.
  // Currently no-op; used when backend's expository-pointer emails start
  // deep-linking here. Reading the params here (even without routing on them)
  // prevents the URL from being cleaned up by route validation.
  const focus = searchParams.get('focus');
  const since = searchParams.get('since');
  void focus; // intentional no-op — see ADR-202
  void since; // intentional no-op — see ADR-202

  const plusMenuActions: PlusMenuAction[] = [];

  const handleOpenChatDraft = (prompt: string) => {
    setChatDraftSeed({ id: crypto.randomUUID(), text: prompt });
    setChatOpenSignal((n) => n + 1);
  };

  return (
    <ThreePanelLayout
      chat={{
        draftSeed: chatDraftSeed,
        plusMenuActions,
        placeholder: 'Ask YARNNN anything or type / ...',
        defaultOpen: false,
        openSignal: chatOpenSignal,
      }}
    >
      <PageHeader defaultLabel="Overview" />
      <OverviewSurface onOpenChatDraft={handleOpenChatDraft} />
    </ThreePanelLayout>
  );
}
