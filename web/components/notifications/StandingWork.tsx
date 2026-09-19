'use client';

/**
 * StandingWork — the Notifications window's STANDING WORK pane (ADR-639 D4).
 *
 * The lens ADR-603 D4 described ("where a member reads what stands, what
 * ran, and what changed") finally housed: standing work is a kernel lane,
 * not an app, so its roster is a system view here rather than a Dock pane.
 * It renders the declarations the kernel discovers (`GET /api/standing`) and
 * offers the two direct switches that had exactly one caller each on the
 * deleted Strings pane — Run now and Pause/Resume. Everything else that pane
 * did (sources as parties, consumers, head facts, contract render) was chrome
 * and left with it: the file is read at its own surface (Files / Text), the
 * runs are receipts in the Activity pane beside this one.
 *
 * ADR-658 A1.5: this pane is the MIRROR (ADR-340 D1 — complete, neutral,
 * never deleted). The Supervisor app is the COMPOSITION — the door, the
 * starts, the detail — and the ROW is one shared component mounted by both
 * (`components/standing/StandingRow`, the ADR-340 D8 rule: one body, two
 * mounts). Setting standing work up is the Supervisor's act or a
 * conversation under `declaring-standing-work`; the empty state names both.
 *
 * DP29: everything here is derived at read time from the roster the server
 * composes; nothing is stored.
 */

import { useCallback, useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { Working } from '@/components/shared/Working';
import { StandingRow } from '@/components/standing/StandingRow';
import { api, type StandingSummary } from '@/lib/api/client';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { useFeedback } from '@/contexts/FeedbackContext';

export function StandingWork() {
  const { navigateToSurface } = useSurfacePreferences();
  const { runAction } = useFeedback();
  const [rows, setRows] = useState<StandingSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    try {
      setRows(await api.standing.list());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setRows([]);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const runNow = useCallback(async (row: StandingSummary) => {
    if (busy) return;
    setBusy(row.topic);
    try {
      // The per-row `note` STAYS: it is a durable result the member reads
      // against that row (which file, what changed), not a transient outcome
      // — the canon's in-surface lane. What was missing is the wait: a run
      // takes seconds and the row said nothing while it ran.
      const res = await runAction(() => api.standing.run(row.topic), {
        pending: `Running ${row.topic}…`,
      });
      const line = res.no_change
        ? 'Ran — nothing changed.'
        : res.success
          ? 'Ran — the file was updated.'
          : res.error_reason === 'shape_violation'
            ? `Update refused — ${res.detail ?? 'the fetched data broke the declared shape'}.`
            : res.error_reason === 'router_disabled'
              ? 'Skipped — the engine is unavailable on this workspace.'
              : `Run failed (${res.error_reason ?? 'unknown'}).`;
      setNote((n) => ({ ...n, [row.topic]: line }));
    } catch (e) {
      setNote((n) => ({ ...n, [row.topic]: `Run failed (${e instanceof Error ? e.message : String(e)}).` }));
    } finally {
      setBusy(null);
      void load();
    }
  }, [busy, load, runAction]);

  const togglePause = useCallback(async (row: StandingSummary) => {
    if (busy) return;
    setBusy(row.topic);
    try {
      // try/finally with NO catch: a failed pause threw into the void, the row
      // reloaded unchanged, and the member read it as the toggle ignoring them.
      await runAction(() => api.standing.update(row.topic, { paused: !row.paused }), {
        success: row.paused ? 'Resumed' : 'Paused',
        error: row.paused ? 'Could not resume this' : 'Could not pause this',
      });
    } catch {
      /* reported; the reload below restores the true state */
    } finally {
      setBusy(null);
      void load();
    }
  }, [busy, load, runAction]);

  if (rows === null) {
    return (
      <Working label="Loading…" className="p-6 text-sm" />
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b px-6 py-3">
        <p className="text-xs text-muted-foreground">
          Files kept current on a schedule. Set one up in Supervisor, or ask an agent in chat.
        </p>
        <button
          type="button"
          onClick={() => void load()}
          title="Refresh"
          className="rounded border p-1.5 hover:bg-muted"
        >
          <RefreshCw className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {error && (
          <p className="mb-4 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-xs text-destructive">
            Could not load this: {error}
          </p>
        )}

        {rows.length === 0 && !error && (
          <div className="rounded-md border border-dashed border-border px-4 py-6 text-center">
            <p className="text-sm text-foreground">Nothing is kept current yet.</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Set one up in Supervisor, or ask an agent in chat. The instructions go next to
              the file and run on a schedule.
            </p>
            <button
              type="button"
              onClick={() => navigateToSurface('supervisor')}
              className="mt-3 rounded-md border border-border px-2.5 py-1.5 text-xs text-foreground hover:bg-muted/40"
            >
              Open Supervisor
            </button>
          </div>
        )}

        <ul className="space-y-3">
          {rows.map((row) => (
            <StandingRow
              key={row.topic}
              row={row}
              busy={busy === row.topic}
              note={note[row.topic]}
              onRunNow={(r) => void runNow(r)}
              onTogglePause={(r) => void togglePause(r)}
              onOpenFile={(r) => navigateToSurface('files', { path: r.target_path ?? `/workspace/${r.topic}/${r.target}` })}
            />
          ))}
        </ul>
      </div>
    </div>
  );
}
