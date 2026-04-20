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
 */

import { useState } from 'react';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';
import { ThreePanelLayout } from '@/components/shell/ThreePanelLayout';
import { PageHeader } from '@/components/shell/PageHeader';
import { OverviewSurface } from '@/components/overview/OverviewSurface';

export default function OverviewPage() {
  const [chatDraftSeed, setChatDraftSeed] = useState<{ id: string; text: string } | null>(null);
  const [chatOpenSignal, setChatOpenSignal] = useState(0);

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
