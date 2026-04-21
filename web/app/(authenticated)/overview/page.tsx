'use client';

/**
 * Overview Page — Cockpit HOME (ADR-199 + ADR-203).
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
 * Cold-start guidance (ADR-203): when OverviewSurface detects semantic day-zero
 * (structurally scaffolded, operator hasn't acted yet), the ambient rail opens
 * by default with a seeded first-session prompt so YARNNN can greet the operator
 * inline. Rail stays closed on non-day-zero loads (preserves operator focus).
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

import { useCallback, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';
import { ThreePanelLayout } from '@/components/shell/ThreePanelLayout';
import { PageHeader } from '@/components/shell/PageHeader';
import { OverviewSurface } from '@/components/overview/OverviewSurface';

const COLD_START_SEED =
  "I just signed up — help me understand what YARNNN is and what I should do first. Walk me through the cockpit briefly, then ask what I want my workforce to track or produce.";

export default function OverviewPage() {
  const searchParams = useSearchParams();
  const [chatDraftSeed, setChatDraftSeed] = useState<{ id: string; text: string } | null>(null);
  const [chatOpenSignal, setChatOpenSignal] = useState(0);
  const [isColdStart, setIsColdStart] = useState<boolean | null>(null);

  // Forward-compat: accept ?focus=queue|alerts + ?since=<iso> per ADR-202.
  const focus = searchParams.get('focus');
  const since = searchParams.get('since');
  void focus; // intentional no-op — see ADR-202
  void since; // intentional no-op — see ADR-202

  const plusMenuActions: PlusMenuAction[] = [];

  const handleOpenChatDraft = useCallback((prompt: string) => {
    setChatDraftSeed({ id: crypto.randomUUID(), text: prompt });
    setChatOpenSignal((n) => n + 1);
  }, []);

  // When OverviewSurface finishes day-zero detection, configure the rail:
  // cold-start → rail opens by default with the greeting seed ready;
  // non-cold-start → rail stays closed (operator focus).
  const handleDayZeroResolved = useCallback((dayZero: boolean) => {
    setIsColdStart((prev) => (prev === null ? dayZero : prev));
    if (dayZero) {
      // Seed the composer; signal the rail to open.
      setChatDraftSeed((current) =>
        current ?? { id: 'cold-start-seed', text: COLD_START_SEED },
      );
      setChatOpenSignal((n) => n + 1);
    }
  }, []);

  // defaultOpen follows cold-start — rail is open during first-run guidance,
  // closed otherwise. Once isColdStart resolves, the value stays stable for
  // this session (setState-once guard in handleDayZeroResolved above).
  const railDefaultOpen = isColdStart === true;

  return (
    <ThreePanelLayout
      chat={{
        draftSeed: chatDraftSeed,
        plusMenuActions,
        placeholder: 'Ask YARNNN anything or type / ...',
        defaultOpen: railDefaultOpen,
        openSignal: chatOpenSignal,
      }}
    >
      <PageHeader defaultLabel="Overview" />
      <OverviewSurface
        onOpenChatDraft={handleOpenChatDraft}
        onDayZeroResolved={handleDayZeroResolved}
      />
    </ThreePanelLayout>
  );
}
