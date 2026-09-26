'use client';

/**
 * openRun — the ONE way any surface opens a run (ADR-670 D6).
 *
 * A run opens at its TRACE level: `?supervisor.run=<id>`, which renders the run
 * in full (`RunView`) in the Supervisor's canvas. A run of declared work also
 * opens that work (`?supervisor.work=<topic>`), so its side — its runs, its
 * sources, its verbs — stands beside the run it came from.
 *
 * "Run it" on a run that is due is not a look but an act: it opens the work
 * with `start=1`, the one door that starts a browser run (ADR-666 D4), which
 * lives in the work's own conversation.
 *
 * Before ADR-670 each caller (the bell, the run tray, Notifications → To do,
 * Chat's index and its supervision side) spelled its own fallback — the work
 * if the run had a topic, else the conversation — and they were free to drift.
 * One function now answers where a run opens.
 *
 * Every key is DELIVERED, even the ones this open clears (`''`): the shell
 * merges delivered params over the surface's remembered ones, so an omitted
 * key would let a work opened days ago frame a run from somewhere else.
 */

import { useCallback } from 'react';
import type { Run } from '@/lib/api/client';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';

/** Where a run opens, as the Supervisor's params. Pure, so a gate can read it. */
export function runParams(run: Run, opts: { start?: boolean } = {}): Record<string, string> {
  if (opts.start && run.topic) return { work: run.topic, run: '', start: '1' };
  return { work: run.topic ?? '', run: run.id, start: '' };
}

/** Open a run — its Trace, or with `start`, the door that runs it. */
export function useOpenRun(): (run: Run, opts?: { start?: boolean }) => void {
  const { navigateToSurface } = useSurfacePreferences();
  return useCallback(
    (run: Run, opts?: { start?: boolean }) => {
      navigateToSurface('supervisor', runParams(run, opts));
    },
    [navigateToSurface],
  );
}
