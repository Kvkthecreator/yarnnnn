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
 * by `RunView`, the one rendering of a run. "Run it" opens the work with
 * `start=1`, the one door that starts a browser run (the run tray's door).
 */

import { useTranslations } from 'next-intl';
import { Play } from 'lucide-react';
import { RunView } from '@/components/runs/RunView';
import { useNeedsYou } from '@/lib/attention/useNeedsYou';
import { refreshRuns } from '@/lib/runs/useRuns';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';

export function WaitingRunQueue() {
  const t = useTranslations('supervisor.notifications');
  const { waitingRuns } = useNeedsYou();
  const { navigateToSurface, userId } = useSurfacePreferences();

  if (waitingRuns.length === 0) return null;

  const openWork = (topic: string, start = false) =>
    navigateToSurface('supervisor', { work: topic, ...(start ? { start: '1' } : {}) });

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
            onOpen={(run) => run.topic && openWork(run.topic)}
            onRunIt={(run) => run.topic && openWork(run.topic, true)}
            onChanged={() => void refreshRuns()}
          />
        ))}
      </div>
    </div>
  );
}
