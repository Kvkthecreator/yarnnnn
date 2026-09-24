'use client';

/**
 * WorkConversation — browser work's own conversation, inside its detail
 * (ADR-666 D4).
 *
 * A browser run is a LANE TURN — the only place browser hands exist (ADR-662
 * D9). This is where it happens: the lane bound to the kept file under its
 * app (the ADR-653 R3 binding, `(app, path)` — the rule the Text app keys its
 * own conversation about a file on, so the two are the same conversation).
 * Run now writes the run's opening message here; `startRunId` tells the panel
 * to perform it; the member watches every step land, can stop it, and can
 * tell it what to do differently mid-run.
 *
 * WHO the member reads is resolved exactly as the Text app resolves it — the
 * app's name for its resident, else the colleague's, else the engine — read
 * back from the wire, never asserted here. `viewerId` is passed, so the
 * member's own turns read as their own (the `StudioSurface` defect of
 * 2026-09-22: a mount without it labelled the member "A member").
 */

import { useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { api } from '@/lib/api/client';
import { LanePanel } from '@/components/chat-surface/LanePanel';
import { Working } from '@/components/shared/Working';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';

type LanesEnv = Awaited<ReturnType<typeof api.lanes.list>>;

export function WorkConversation({
  laneId, app, startRunId, onRunTurnSettled,
}: {
  laneId: string;
  app: string;
  startRunId?: string | null;
  onRunTurnSettled?: () => void;
}) {
  const t = useTranslations('supervisor.detail');
  const { userId } = useSurfacePreferences();
  const [env, setEnv] = useState<LanesEnv | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let live = true;
    api.lanes.list(true).then(
      (e) => { if (live) { setEnv(e); setFailed(false); } },
      () => { if (live) setFailed(true); },
    );
    return () => { live = false; };
  }, [laneId]);

  const lane = env?.lanes.find((l) => l.id === laneId) ?? null;
  const modelLabel = useMemo(() => {
    const id = lane?.model;
    return env?.models?.find((m) => m.id === id)?.label || id || '';
  }, [env, lane]);
  const resident = env?.apps?.find((a) => a.slug === app)?.resident || lane?.agent || null;
  const speakerLabel = useMemo(() => {
    const appName = env?.apps?.find((a) => a.slug === app)?.name;
    if (appName) return appName;
    const named = env?.agents?.find((a) => a.slug === resident)?.name;
    return named || modelLabel;
  }, [env, app, resident, modelLabel]);

  if (failed) {
    return (
      <div className="rounded-md border border-dashed border-border/60 bg-muted/10 px-4 py-5 text-sm text-muted-foreground">
        {t('conversationUnreadable')}
      </div>
    );
  }
  if (!lane) return <Working label={t('loading')} />;

  return (
    <div className="flex h-[560px] min-h-0 flex-col overflow-hidden rounded-lg border border-border/70">
      <LanePanel
        key={laneId}
        laneId={laneId}
        laneName={lane.name}
        modelLabel={modelLabel}
        speakerLabel={speakerLabel}
        viewerId={userId}
        agentFaces={resident ? { [resident]: { name: speakerLabel } } : undefined}
        startRunId={startRunId}
        onRunTurnSettled={onRunTurnSettled}
      />
    </div>
  );
}
