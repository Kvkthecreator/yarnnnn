'use client';

/**
 * Reach — the boundary's door (ADR-642).
 *
 * The Channel dimension (Axiom 6 — every act has a Where) had five pieces
 * and no front door. This window asks the member's three questions about
 * the workspace boundary and answers each from what already exists:
 *
 *   Connected — every connection they hold: where it points, what it reads
 *               and writes, who reads through it on a schedule, how fresh.
 *   Leaving   — what is about to leave: the proposal queue filtered to the
 *               two families that cross (external-write · capital).
 *   Crossed   — what arrived and what left: the workspace timeline under
 *               its boundary lens, receipts attached.
 *
 * A kernel surface, not an app (ADR-639 D4's cut: it owns no file type).
 * Nothing here is stored (DP29) and nothing here authors: the only writes
 * reachable are the two proposal decisions the queue already carried.
 * Consent, selection and apertures stay Settings acts — this window lists
 * and doors. No pane presents an agent's record (ADR-640): an agent appears
 * only as the character on a receipt.
 *
 * Mounts the shared SettingsPaneShell in fullBleed mode (the Notifications
 * shape — one shell, N mounts).
 */

import { ArrowLeftRight, Cable, ExternalLink, Send } from 'lucide-react';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { SettingsPaneShell, PaneHeader, type PaneGroup } from '@/components/settings/SettingsPaneShell';
import { QueueBody } from '@/components/queue/QueueBody';
import { ReachConnected } from '@/components/reach/ReachConnected';
import { BoundaryLedger } from '@/components/reach/BoundaryLedger';

const PANE_GROUPS: PaneGroup[] = [
  {
    label: 'The boundary',
    panes: [
      { key: 'connected', label: 'Connected', icon: Cable },
      { key: 'leaving', label: 'Leaving', icon: Send },
      { key: 'crossed', label: 'Crossed', icon: ArrowLeftRight },
    ],
  },
];

/** The escape-hatch row (the Notifications MirrorLink grammar). */
function DoorLink({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-1.5 text-xs text-primary hover:underline"
    >
      <ExternalLink className="w-3.5 h-3.5" />
      {label}
    </button>
  );
}

export default function ReachPage() {
  const { navigateToSurface } = useSurfacePreferences();

  const renderPane = (pane: string) => {
    switch (pane) {
      case 'connected':
        return (
          <div className="flex h-full flex-col">
            <PaneHeader
              icon={Cable}
              title="Connected"
              subtitle="Your connections — held under your account, reachable wherever you work; other members hold and see their own. What each reads and writes, and who in this workspace reads through it."
              action={<DoorLink label="Manage connections" onClick={() => navigateToSurface('connectors')} />}
            />
            <div className="flex-1 overflow-y-auto p-6">
              <ReachConnected />
            </div>
          </div>
        );
      case 'leaving':
        return (
          <div className="flex h-full flex-col">
            <PaneHeader
              icon={Send}
              title="Leaving"
              subtitle="What is about to leave the workspace — approve or refuse below. Nothing here goes out on its own."
              action={
                <DoorLink
                  label="Everything awaiting you"
                  onClick={() => navigateToSurface('notifications', { pane: 'resolve' })}
                />
              }
            />
            <div className="flex-1 overflow-y-auto p-6">
              {/* ADR-642 D2 — the boundary families only. A substrate
                  proposal is a workspace write awaiting witness; it never
                  leaves, so it lives on To do, not here. */}
              <QueueBody families={['external-write', 'capital']} />
            </div>
          </div>
        );
      case 'crossed':
        return (
          <div className="flex h-full flex-col">
            <PaneHeader
              icon={ArrowLeftRight}
              title="Crossed"
              subtitle="What arrived and what left — every act signed, every receipt kept."
              action={
                <DoorLink
                  label="The whole timeline"
                  onClick={() => navigateToSurface('notifications', { pane: 'understand' })}
                />
              }
            />
            <div className="flex-1 min-h-0">
              <BoundaryLedger />
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <SettingsPaneShell
      windowSlug="reach"
      paneGroups={PANE_GROUPS}
      defaultPane="connected"
      renderPane={renderPane}
      fullBleed
      navLabel="Reach"
    />
  );
}
