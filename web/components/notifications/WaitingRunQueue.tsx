'use client';

/**
 * WaitingRunQueue — runs due and waiting on the viewer, in Notifications → To
 * do (ADR-670 D5; the third source beside mentions and decisions).
 *
 * Browser work that comes due never acts on its own (ADR-666 D4): it opens a
 * run WAITING on its member. That is something waiting on the member exactly
 * as a decision or a mention is, so it belongs in To do — before ADR-670 it
 * showed only in the run tray and the Supervisor, and To do never listed it.
 *
 * Read from `useNeedsYou` (which reads `useRuns` — no second fetch), rendered
 * by `RunView`, the one rendering of a run. A run opens at its Trace, and
 * "Run it" opens the one door that starts a browser run — both through
 * `useOpenRun` (ADR-670 D6).
 */

import { useTranslations } from 'next-intl';
import { Play } from 'lucide-react';
import { RunView } from '@/components/runs/RunView';
import { useNeedsYou } from '@/lib/attention/useNeedsYou';
import { refreshRuns } from '@/lib/runs/useRuns';
import { useOpenRun } from '@/lib/runs/openRun';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';

export function WaitingRunQueue() {
  const t = useTranslations('supervisor.notifications');
  const { waitingRuns } = useNeedsYou();
  const { userId } = useSurfacePreferences();
  const openRun = useOpenRun();

  if (waitingRuns.length === 0) return null;

  return (
    <div className="mb-6">
      <div className="mb-2 flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        <Play className="h-3.5 w-3.5" />
        {t('runsDueHeading')}
      </div>
      <div className="space-y-2">
        {waitingRuns.map((r) => (
          <RunView
            key={r.id}
            run={r}
            viewerId={userId}
            compact
            onOpen={(run) => openRun(run)}
            onRunIt={(run) => openRun(run, { start: true })}
            onChanged={() => void refreshRuns()}
          />
        ))}
      </div>
    </div>
  );
}
