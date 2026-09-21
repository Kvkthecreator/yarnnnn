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
 * Nothing here is stored (DP29). No pane presents an agent's record
 * (ADR-640): an agent appears only as the character on a receipt.
 *
 * ADR-645 D3 (2026-09-08) amends the original "consent, selection and
 * apertures stay Settings acts — this window lists and doors" clause. Three
 * of the four connection decisions were WORKSPACE decisions wearing a
 * Settings costume, and doors from the boundary's own front door
 * institutionalised that. Connected OWNS the connection acts; Settings →
 * Connectors is deleted. The acts stay CONNECTION acts: no publish, no
 * run/pause, no agent record — those still belong to the artifact's pane,
 * Notifications and the agent page respectively.
 *
 * Mounts the shared SettingsPaneShell in fullBleed mode (the Notifications
 * shape — one shell, N mounts).
 */

import { useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { ArrowLeftRight, Cable, ExternalLink, Send } from 'lucide-react';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { SettingsPaneShell, PaneHeader, type PaneGroup } from '@/components/settings/SettingsPaneShell';
import { QueueBody } from '@/components/queue/QueueBody';
import { ReachConnected } from '@/components/reach/ReachConnected';
import { BoundaryLedger } from '@/components/reach/BoundaryLedger';

/** ADR-660 — the roster holds catalog KEYS, not words: a module table is
 *  evaluated at import, before the member's language is known. Worded at
 *  render, below. */
const PANE_KEYS = [
  { key: 'connected', labelKey: 'panes.connected', icon: Cable },
  { key: 'leaving', labelKey: 'panes.leaving', icon: Send },
  { key: 'crossed', labelKey: 'panes.crossed', icon: ArrowLeftRight },
] as const;

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
  const t = useTranslations('reach');

  const paneGroups: PaneGroup[] = useMemo(
    () => [
      {
        label: t('groups.boundary'),
        panes: PANE_KEYS.map((p) => ({ key: p.key, label: t(p.labelKey), icon: p.icon })),
      },
    ],
    [t],
  );

  const renderPane = (pane: string) => {
    switch (pane) {
      case 'connected':
        return (
          <div className="flex h-full flex-col">
            <PaneHeader
              icon={Cable}
              title={t('panes.connected')}
              subtitle={t('connected.subtitle')}
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
              title={t('panes.leaving')}
              subtitle={t('leaving.subtitle')}
              action={
                <DoorLink
                  label={t('leaving.showAllToDos')}
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
              title={t('panes.crossed')}
              subtitle={t('crossed.subtitle')}
              action={
                <DoorLink
                  label={t('crossed.showAllActivity')}
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
      paneGroups={paneGroups}
      defaultPane="connected"
      renderPane={renderPane}
      fullBleed
      navLabel="Reach"
    />
  );
}
