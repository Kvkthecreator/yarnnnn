'use client';

/**
 * StandingRow — ONE row of standing work, mounted twice (ADR-658 A1.5; the
 * ADR-340 D8 rule, one body two mounts):
 *
 *   - the Notifications "Standing work" pane — the MIRROR (complete, neutral)
 *   - the Supervisor app's `work` band — the COMPOSITION (door, starts, detail)
 *
 * The row answers what a member asks of a piece of standing work: which file
 * it keeps, who looks after it (DERIVED — ADR-658 D2, never a stored field),
 * when it runs and in whose clock, where its updates come from, and what the
 * last run did. The verbs are the caller's: `onRunNow` / `onTogglePause`
 * (both mounts), `onOpen` (the composition opens its detail), `onOpenFile`
 * (the mirror opens the kept file in Files).
 *
 * DP29: everything here is derived at read time from the served roster;
 * nothing is stored. `runStatusLine` is the three-way refusal renderer lifted
 * from the deleted Strings pane — an honest refusal reads as what it is, never
 * as "failed".
 */

import { CalendarClock, FolderOpen, Loader2, Pause, Play, Zap } from 'lucide-react';
import type { StandingLastRun, StandingSummary } from '@/lib/api/client';
import { formatLedgerTime } from '@/lib/formatting';
import { cn } from '@/lib/utils';

/** Operator words for a piece of work that parses but cannot run. */
export const PROBLEM_COPY: Record<string, string> = {
  missing_target: 'No file named. The instructions don’t say which file to keep current.',
  invalid_target: 'The file to keep current must be in the same folder as the instructions.',
  unsupported_format: 'Only md, csv, json and txt files can be kept current.',
  sources_invalid: 'The sources aren’t valid. A data file (csv or json) takes exactly one source, and a file rather than a folder.',
  app_invalid: 'The instructions name an app that can’t keep a file current.',
  source_cycle: 'This is part of a loop: it is kept from a file that is kept from it. Neither will run until one source changes.',
};

export function runStatusLine(e: StandingLastRun): string {
  if (e.status === 'skipped' && e.error_reason === 'no_change') return 'Ran. Nothing changed';
  if (e.status === 'skipped' && e.error_reason === 'sources_unchanged') return 'Checked. Nothing new to read';
  if (e.status === 'skipped' && e.error_reason === 'router_disabled') return 'Skipped. The engine is unavailable';
  if (e.status === 'skipped') return `Skipped${e.error_reason ? ` — ${e.error_reason}` : ''}`;
  if (e.status === 'success') return 'Ran. The file was updated';
  if (e.error_reason === 'shape_violation') return 'Not updated. The new data didn’t fit the file’s shape';
  if (e.error_reason === 'no_sources_fetched') return 'No source could be read';
  if (e.error_reason === 'balance_exhausted') return 'Did not run. The workspace balance is used up';
  if (e.error_reason === 'output_truncated') return 'Not updated. The file has grown too long to keep current in one run';
  return `Run failed${e.error_reason ? ` — ${e.error_reason}` : ''}`;
}

const DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

function clock(h: string, m: string): string {
  const hh = Number(h);
  const mm = Number(m);
  if (!Number.isFinite(hh) || !Number.isFinite(mm)) return `${h}:${m}`;
  return `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`;
}

/** The cadence in words where the cron is one of the shapes a member sets
 *  from the door; the raw string otherwise (never a wrong translation). */
export function describeSchedule(s: string): string {
  const t = s.trim();
  if (t === 'daily') return 'Every day';
  if (t === 'weekly') return 'Every week';
  if (t === 'biweekly') return 'Every two weeks';
  if (t === 'monthly') return 'Every month';
  const parts = t.split(/\s+/);
  if (parts.length !== 5) return t;
  const [m, h, dom, mon, dow] = parts;
  if (!/^\d{1,2}$/.test(m)) return t;
  if (h === '*' && dom === '*' && mon === '*' && dow === '*') return m === '0' ? 'Every hour' : `Every hour at :${m.padStart(2, '0')}`;
  if (!/^\d{1,2}$/.test(h) || dom !== '*' || mon !== '*') return t;
  const at = clock(h, m);
  if (dow === '*') return `Every day at ${at}`;
  if (dow === '1-5') return `Every weekday at ${at}`;
  if (/^[0-6]$/.test(dow)) return `Every ${DAY_NAMES[Number(dow)]} at ${at}`;
  return t;
}

/** The cadence, and the clock it is read in.
 *
 * A bare cron says nothing about its timezone, and the "next" beside it is
 * rendered in the BROWSER's — so a Seoul workspace read from Seoul showed
 * `0 13 * * *` next to a 1pm that agreed by luck, and read from anywhere else
 * showed two times, one of which is nobody's. The schedule resolves against
 * the WORKSPACE's clock (migration 247); name it. UTC is left unlabelled —
 * it is the default and the label would be noise on every undeclared row.
 */
export function scheduleLine(s: StandingSummary['schedule'], tz?: string | null): string {
  if (!s) return 'no schedule';
  const cadence = Array.isArray(s) ? s.map(describeSchedule).join(' · ') : describeSchedule(String(s));
  return tz && tz !== 'UTC' ? `${cadence} · ${tz}` : cadence;
}

/** A served sentence composed mid-line loses its capital ("reads the latest 50 messages…"). */
export function lowerFirst(s: string): string {
  return s ? s.charAt(0).toLowerCase() + s.slice(1) : s;
}

/** Who looks after it — the derived minder, or the honest mechanical case. */
export function minderLine(row: StandingSummary): string {
  if (row.minder?.name) return `${row.minder.name} looks after this`;
  if (row.format && row.format !== 'md') return 'Updated automatically';
  return '';
}

export function StandingRow({
  row, busy, note, onRunNow, onTogglePause, onOpen, onOpenFile,
}: {
  row: StandingSummary;
  busy?: boolean;
  note?: string | null;
  onRunNow: (row: StandingSummary) => void;
  onTogglePause: (row: StandingSummary) => void;
  onOpen?: (row: StandingSummary) => void;
  onOpenFile?: (row: StandingSummary) => void;
}) {
  const open = onOpen ?? onOpenFile;
  const minder = minderLine(row);
  return (
    <li className="rounded-lg border border-border/70 bg-background p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <button
            type="button"
            onClick={() => open?.(row)}
            className="flex items-center gap-1.5 text-sm font-medium text-foreground hover:underline"
            title={onOpen ? 'Open' : 'Open in Files'}
          >
            <FolderOpen className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="truncate">{row.target || '(no file named)'}</span>
          </button>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {row.topic}
            {minder ? ` · ${minder}` : ''}
          </p>
          <p className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1">
              <CalendarClock className="h-3 w-3" /> {scheduleLine(row.schedule, row.timezone)}
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
          {/* A connector source reads what the CONNECTION reads, and the
              server says so itself (`reads`) — shown so a member sees that a
              GitHub source is issue + pull-request activity, not a commit log,
              before a run says "no source could be read". */}
          {row.sources.some((s) => s.connector) && (
            <ul className="mt-1 space-y-0.5 text-[11px] text-muted-foreground">
              {row.sources.filter((s) => s.connector).map((s) => (
                <li key={s.id} className="truncate">
                  <span className="font-medium text-foreground/70">{s.connector}</span>
                  {s.selector ? ` · ${s.selector}` : ''}
                  {s.reads ? ` — reads ${lowerFirst(s.reads)}` : ''}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={() => onRunNow(row)}
            disabled={busy || row.problem != null}
            title={row.problem != null
              ? 'It can’t run until its instructions are fixed'
              : 'Update the file now'}
            className="flex items-center gap-1.5 rounded border px-2.5 py-1.5 text-xs hover:bg-muted disabled:opacity-40"
          >
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />}
            Run now
          </button>
          <button
            type="button"
            onClick={() => onTogglePause(row)}
            disabled={busy}
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
          {PROBLEM_COPY[row.problem] ?? `Cannot run: ${row.problem}`} Fix the instructions, or ask an agent in chat to.
        </p>
      )}

      {(note || row.last_run) && (
        <p className={cn('mt-3 text-xs', note ? 'text-foreground' : 'text-muted-foreground')}>
          {note
            ?? (row.last_run
              ? `${runStatusLine(row.last_run)}${row.last_run.at ? ` · ${formatLedgerTime(row.last_run.at)}` : ''}`
              : null)}
        </p>
      )}
    </li>
  );
}
