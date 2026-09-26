'use client';

/**
 * RunTrace — the Trace level: one run, opened full (ADR-670 D6).
 *
 * `?supervisor.run=<id>` puts the run in the canvas, rendered by the ONE
 * `RunView` (ADR-666 D7) — uncompacted, every step. Where the run comes from:
 * the live ledger first (`useRuns`, so its steps keep landing while it goes),
 * then the opened work's own history, and only if neither holds it (an old run
 * the ledger has aged out) its own route, once.
 *
 * A run with no piece of work behind it happened in a conversation; the door
 * to that conversation stands under it.
 */

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { MessageSquare } from 'lucide-react';
import { api, type Run } from '@/lib/api/client';
import { RunView } from '@/components/runs/RunView';
import { Working } from '@/components/shared/Working';
import { useRuns } from '@/lib/runs/useRuns';
import { useOpenRun } from '@/lib/runs/openRun';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';

export function RunTrace({ runId, known }: { runId: string; known: Run[] }) {
  const t = useTranslations('supervisor');
  const { runs, refresh } = useRuns();
  const { navigateToSurface, userId } = useSurfacePreferences();
  const openRun = useOpenRun();
  const [fetched, setFetched] = useState<Run | null>(null);
  const [gone, setGone] = useState(false);

  const held = (runs ?? []).find((r) => r.id === runId) ?? known.find((r) => r.id === runId) ?? null;

  useEffect(() => {
    setFetched(null);
    setGone(false);
  }, [runId]);

  // Only when neither store holds it, and only once the ledger has answered —
  // a cold link must not race the ledger's first read.
  const ledgerRead = runs !== null;
  useEffect(() => {
    if (held || !ledgerRead || fetched || gone) return;
    let live = true;
    api.runs.get(runId).then(
      (r) => { if (live) setFetched(r); },
      () => { if (live) setGone(true); },
    );
    return () => { live = false; };
  }, [held, ledgerRead, fetched, gone, runId]);

  const run = held ?? fetched;
  if (!run) {
    if (gone) {
      return (
        <div className="rounded-md border border-dashed border-border/60 bg-muted/10 px-4 py-5 text-sm text-muted-foreground">
          {t('trace.gone')}
        </div>
      );
    }
    return <Working label={t('surface.loading')} fill />;
  }

  return (
    <div className="space-y-3">
      <RunView
        run={run}
        viewerId={userId}
        onRunIt={(r) => openRun(r, { start: true })}
        onOpenFile={(path) => navigateToSurface('files', { path })}
        onChanged={() => void refresh()}
      />
      {!run.topic && run.lane_id && (
        <button
          type="button"
          onClick={() => navigateToSurface('chat', { lane: run.lane_id! })}
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
        >
          <MessageSquare className="h-3.5 w-3.5" /> {t('trace.openConversation')}
        </button>
      )}
    </div>
  );
}
