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
 * Declaring is a CONVERSATION: any colleague holds `declaring-standing-work`,
 * so the empty state says so rather than offering a form (ADR-569 D7's
 * form-free discipline, unchanged).
 *
 * DP29: everything here is derived at read time from the roster the server
 * composes; nothing is stored. `runStatusLine` is the three-way refusal
 * renderer lifted verbatim from the deleted pane — an honest refusal reads
 * as what it is, never as "failed".
 */

import { useCallback, useEffect, useState } from 'react';
import { CalendarClock, FolderOpen, Loader2, Pause, Play, RefreshCw, Zap } from 'lucide-react';
import { api, type StandingLastRun, type StandingSummary } from '@/lib/api/client';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { formatLedgerTime } from '@/lib/formatting';
import { cn } from '@/lib/utils';

/** Operator words for a declaration that parses but cannot run. */
const PROBLEM_COPY: Record<string, string> = {
  missing_target: 'No target named — the declaration does not say which file to keep.',
  invalid_target: 'The target must be one file in the declaration’s own folder.',
  unsupported_format: 'Only md, csv, json and txt files can be kept current.',
  sources_invalid: 'The sources are not valid — a structured file takes exactly one.',
  app_invalid: 'The declaration names an app that does not exist.',
};

function runStatusLine(e: StandingLastRun): string {
  if (e.status === 'skipped' && e.error_reason === 'no_change') return 'Ran — nothing changed';
  if (e.status === 'skipped' && e.error_reason === 'router_disabled') return 'Skipped — the engine is unavailable';
  if (e.status === 'skipped') return `Skipped${e.error_reason ? ` — ${e.error_reason}` : ''}`;
  if (e.status === 'success') return 'Ran — the file was updated';
  if (e.error_reason === 'shape_violation') return 'Update refused — the fetched data broke the declared shape';
  if (e.error_reason === 'no_sources_fetched') return 'Fetch failed — no source could be read';
  if (e.error_reason === 'balance_exhausted') return 'Did not run — the workspace balance is exhausted';
  return `Run failed${e.error_reason ? ` — ${e.error_reason}` : ''}`;
}

function scheduleLine(s: StandingSummary['schedule']): string {
  if (!s) return 'no cadence';
  return Array.isArray(s) ? s.join(' · ') : String(s);
}

export function StandingWork() {
  const { navigateToSurface } = useSurfacePreferences();
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
      const res = await api.standing.run(row.topic);
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
  }, [busy, load]);

  const togglePause = useCallback(async (row: StandingSummary) => {
    if (busy) return;
    setBusy(row.topic);
    try {
      await api.standing.update(row.topic, { paused: !row.paused });
    } finally {
      setBusy(null);
      void load();
    }
  }, [busy, load]);

  if (rows === null) {
    return (
      <div className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> Reading what stands…
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b px-6 py-3">
        <p className="text-xs text-muted-foreground">
          Files kept current on a contract and a cadence. To keep another file current, ask any
          colleague — they write the declaration beside the file.
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
            Could not read the roster: {error}
          </p>
        )}

        {rows.length === 0 && !error && (
          <div className="rounded-md border border-dashed border-border px-4 py-6 text-center">
            <p className="text-sm text-foreground">Nothing is being kept current yet.</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Open a file in Text and tell Editor what it must stay true to and where its
              updates come from. The declaration lands beside the file and runs on its schedule.
            </p>
          </div>
        )}

        <ul className="space-y-3">
          {rows.map((row) => {
            const kept = row.target_path ?? `/workspace/${row.topic}/${row.target}`;
            const isBusy = busy === row.topic;
            return (
              <li key={row.topic} className="rounded-lg border border-border/70 bg-background p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <button
                      type="button"
                      onClick={() => navigateToSurface('files', { path: kept })}
                      className="flex items-center gap-1.5 text-sm font-medium text-foreground hover:underline"
                      title="Open in Files"
                    >
                      <FolderOpen className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="truncate">{row.target || '(no target)'}</span>
                    </button>
                    <p className="mt-0.5 truncate text-xs text-muted-foreground">{row.topic}</p>
                    <p className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                      <span className="inline-flex items-center gap-1">
                        <CalendarClock className="h-3 w-3" /> {scheduleLine(row.schedule)}
                      </span>
                      {row.paused && (
                        <span className="rounded bg-muted px-1.5 py-0.5 text-[11px] font-medium text-foreground/70">
                          Paused
                        </span>
                      )}
                      {row.next_run_at && !row.paused && (
                        <span>next {formatLedgerTime(row.next_run_at)}</span>
                      )}
                      {row.sources.length > 0 && (
                        <span>
                          {row.sources.length} source{row.sources.length === 1 ? '' : 's'}
                        </span>
                      )}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <button
                      type="button"
                      onClick={() => void runNow(row)}
                      disabled={isBusy || row.problem != null}
                      title={row.problem != null
                        ? 'It cannot run until its declaration is repaired'
                        : 'Fetch the sources and update the file now'}
                      className="flex items-center gap-1.5 rounded border px-2.5 py-1.5 text-xs hover:bg-muted disabled:opacity-40"
                    >
                      {isBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />}
                      Run now
                    </button>
                    <button
                      type="button"
                      onClick={() => void togglePause(row)}
                      disabled={isBusy}
                      className="flex items-center gap-1.5 rounded border px-2.5 py-1.5 text-xs hover:bg-muted disabled:opacity-40"
                    >
                      {row.paused
                        ? (<><Play className="h-3.5 w-3.5" /> Resume</>)
                        : (<><Pause className="h-3.5 w-3.5" /> Pause</>)}
                    </button>
                  </div>
                </div>

                {row.problem != null && (
                  <p className="mt-3 rounded-md border border-amber-500/40 bg-amber-500/5 px-3 py-2 text-xs text-amber-700 dark:text-amber-300">
                    {PROBLEM_COPY[row.problem] ?? `Cannot run: ${row.problem}`} Ask a colleague to repair the declaration.
                  </p>
                )}

                {(note[row.topic] || row.last_run) && (
                  <p className={cn('mt-3 text-xs', note[row.topic] ? 'text-foreground' : 'text-muted-foreground')}>
                    {note[row.topic]
                      ?? (row.last_run
                        ? `${runStatusLine(row.last_run)}${row.last_run.at ? ` · ${formatLedgerTime(row.last_run.at)}` : ''}`
                        : null)}
                  </p>
                )}
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
