'use client';

/**
 * Conversation — the Supervisor's conversations, one renderer for two lanes
 * (ADR-666 D4 · ADR-667 D1).
 *
 *  - `laneId` given: a piece of work's OWN conversation, inside its detail —
 *    the lane bound to the kept file under its app (the ADR-653 R3 binding,
 *    `(app, path)`). Run now writes the run's opening message there;
 *    `startRunId` tells the panel to perform it; the member watches every step
 *    land, can stop it, and can say what to do differently mid-run.
 *  - `laneId` absent: the APP's own conversation (`app` alone is the binding,
 *    ADR-653 R3) — the Supervisor's agent, where work is set up. Found among
 *    the member's lanes, or created through the one lane door; the resident
 *    resolves server-side from the app's registration, never from here.
 *
 * WHO the member reads is resolved exactly as the Text app resolves it — the
 * app's name for its resident, else the colleague's, else the engine — read
 * back from the wire, never asserted here. `viewerId` is passed, so the
 * member's own turns read as their own (the `StudioSurface` defect of
 * 2026-09-22: a mount without it labelled the member "A member").
 */

import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useTranslations } from 'next-intl';
import { api } from '@/lib/api/client';
import { LanePanel } from '@/components/chat-surface/LanePanel';
import { Working } from '@/components/shared/Working';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { cn } from '@/lib/utils';

type LanesEnv = Awaited<ReturnType<typeof api.lanes.list>>;

export function Conversation({
  laneId: givenLaneId, app, startRunId, onRunTurnSettled, suggestions, emptyState, className,
}: {
  /** A given lane; absent → the app's own conversation, found or created. */
  laneId?: string | null;
  app: string;
  startRunId?: string | null;
  onRunTurnSettled?: () => void;
  suggestions?: string[];
  emptyState?: ReactNode;
  className?: string;
}) {
  const t = useTranslations('supervisor.detail');
  const { userId } = useSurfacePreferences();
  const [env, setEnv] = useState<LanesEnv | null>(null);
  const [failed, setFailed] = useState(false);
  const [createdId, setCreatedId] = useState<string | null>(null);
  const creating = useRef(false);

  useEffect(() => {
    let live = true;
    api.lanes.list(true).then(
      (e) => { if (live) { setEnv(e); setFailed(false); } },
      () => { if (live) setFailed(true); },
    );
    return () => { live = false; };
  }, [givenLaneId, createdId]);

  // The app's own lane: active, bound to the app, about no file.
  const appLaneId = useMemo(() => {
    if (givenLaneId || !env) return null;
    return env.lanes.find((l) => l.status === 'active' && l.app === app && !l.artifact_path)?.id ?? null;
  }, [env, givenLaneId, app]);
  const laneId = givenLaneId ?? appLaneId ?? createdId;

  useEffect(() => {
    if (givenLaneId || !env || appLaneId || createdId || creating.current || !env.enabled) return;
    creating.current = true;
    api.lanes.create({ app }).then(
      (created) => setCreatedId(String(created.id)),
      () => setFailed(true),
    ).finally(() => { creating.current = false; });
  }, [env, givenLaneId, appLaneId, createdId, app]);

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

  if (failed || (env && !env.enabled)) {
    return (
      <div className="rounded-md border border-dashed border-border/60 bg-muted/10 px-4 py-5 text-sm text-muted-foreground">
        {t('conversationUnreadable')}
      </div>
    );
  }
  if (!lane) return <Working label={t('loading')} />;

  return (
    <div className={cn('flex min-h-0 flex-col overflow-hidden rounded-lg border border-border/70', className ?? 'h-[560px]')}>
      <LanePanel
        key={lane.id}
        laneId={lane.id}
        laneName={lane.name}
        modelLabel={modelLabel}
        speakerLabel={speakerLabel}
        viewerId={userId}
        agentFaces={resident ? { [resident]: { name: speakerLabel } } : undefined}
        startRunId={startRunId}
        onRunTurnSettled={onRunTurnSettled}
        suggestions={suggestions}
        emptyState={emptyState}
      />
    </div>
  );
}
