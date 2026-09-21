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
 *
 * ⭐ ADR-660 — the words live in the catalog. The helpers the sibling
 * Supervisor files share (`describeSchedule`, `scheduleLine`, `minderLine`,
 * the problem copy) are HOOKS (`useStandingWords`), because a module-level
 * word table is evaluated at import, before any member's language is known.
 * `lowerFirst` stays a pure function: it lower-cases a SERVED sentence and
 * words nothing itself.
 */

import { useTranslations } from 'next-intl';
import { CalendarClock, FolderOpen, Loader2, Pause, Play, Zap } from 'lucide-react';
import type { StandingLastRun, StandingSummary } from '@/lib/api/client';
import { formatLedgerTime } from '@/lib/formatting';
import { cn } from '@/lib/utils';

/** The problems the catalog names in operator words. Anything else falls back
 *  to the honest "Cannot run: {problem}". */
const KNOWN_PROBLEMS: readonly string[] = [
  'missing_target',
  'invalid_target',
  'unsupported_format',
  'sources_invalid',
  'app_invalid',
  'source_cycle',
];

/** A served sentence composed mid-line loses its capital ("reads the latest 50 messages…").
 *  Korean has no case, so this is a no-op there and harmless. */
export function lowerFirst(s: string): string {
  return s ? s.charAt(0).toLowerCase() + s.slice(1) : s;
}

/**
 * THE STATUS SPINE — one derived state per piece of standing work.
 *
 * ⭐ WHY DERIVED AND NOT SERVED (DP29, ADR-658 D2). Every input is already on
 * the roster: `problem`, `paused`, and the newest ledger row. A stored status
 * column would be a second truth that drifts the moment a run lands, and the
 * minder is derived for exactly the same reason.
 *
 * ⚠️ ORDER IS THE WHOLE DESIGN. A member scanning a cockpit asks one question
 * first — *is anything wrong?* — so `problem` outranks `paused`, and both
 * outrank the last run. A paused row that also cannot run reads as "needs
 * fixing", because resuming it would not make it work.
 *
 * ⚠️ FOUR STATES, NOT FIVE. `attention` is the only one that takes a semantic
 * hue (amber), and it is reserved for what a member must ACT on — a
 * declaration that cannot run. A failed RUN is not `attention`: runs fail for
 * reasons that clear themselves (a source was unreachable), and a row that
 * shouts on every transient failure is the noise failure APP-BUILDER-UX §4.2
 * names. That reads `resting` and says what happened in its own line.
 */
export type StandingState = 'attention' | 'paused' | 'running' | 'resting';

export function standingState(row: StandingSummary): StandingState {
  if (row.problem != null) return 'attention';
  if (row.paused) return 'paused';
  if (row.schedule) return 'running';
  return 'resting';
}

function clock(h: string, m: string): string {
  const hh = Number(h);
  const mm = Number(m);
  if (!Number.isFinite(hh) || !Number.isFinite(mm)) return `${h}:${m}`;
  return `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`;
}

/**
 * The standing-work vocabulary, worded. ONE hook so the mirror, the
 * composition, the door and the detail cannot drift into four spellings of
 * one cadence or one refusal.
 */
export function useStandingWords() {
  const t = useTranslations('supervisor');

  /** Operator words for a piece of work that parses but cannot run. */
  const problemCopy = (problem: string): string =>
    KNOWN_PROBLEMS.includes(problem)
      ? t(`problem.${problem}`)
      : t('row.cannotRun', { problem });

  const runStatusLine = (e: StandingLastRun): string => {
    if (e.status === 'skipped' && e.error_reason === 'no_change') return t('lastRun.noChange');
    if (e.status === 'skipped' && e.error_reason === 'sources_unchanged') return t('lastRun.sourcesUnchanged');
    if (e.status === 'skipped' && e.error_reason === 'router_disabled') return t('lastRun.routerDisabled');
    if (e.status === 'skipped') {
      return e.error_reason
        ? t('lastRun.skippedWithReason', { reason: e.error_reason })
        : t('lastRun.skipped');
    }
    if (e.status === 'success') return t('lastRun.success');
    if (e.error_reason === 'shape_violation') return t('lastRun.shapeViolation');
    if (e.error_reason === 'no_sources_fetched') return t('lastRun.noSourcesFetched');
    if (e.error_reason === 'balance_exhausted') return t('lastRun.balanceExhausted');
    if (e.error_reason === 'output_truncated') return t('lastRun.outputTruncated');
    return e.error_reason
      ? t('lastRun.failedWithReason', { reason: e.error_reason })
      : t('lastRun.failed');
  };

  /** The cadence in words where the cron is one of the shapes a member sets
   *  from the door; the raw string otherwise (never a wrong translation). */
  const describeSchedule = (s: string): string => {
    const raw = s.trim();
    if (raw === 'daily') return t('schedule.daily');
    if (raw === 'weekly') return t('schedule.weekly');
    if (raw === 'biweekly') return t('schedule.biweekly');
    if (raw === 'monthly') return t('schedule.monthly');
    const parts = raw.split(/\s+/);
    if (parts.length !== 5) return raw;
    const [m, h, dom, mon, dow] = parts;
    if (!/^\d{1,2}$/.test(m)) return raw;
    if (h === '*' && dom === '*' && mon === '*' && dow === '*') {
      return m === '0' ? t('schedule.hourly') : t('schedule.hourlyAt', { minute: m.padStart(2, '0') });
    }
    if (!/^\d{1,2}$/.test(h) || dom !== '*' || mon !== '*') return raw;
    const at = clock(h, m);
    if (dow === '*') return t('schedule.everyDayAt', { time: at });
    if (dow === '1-5') return t('schedule.everyWeekdayAt', { time: at });
    if (/^[0-6]$/.test(dow)) {
      return t('schedule.everyDayOfWeekAt', { day: t(`schedule.day${Number(dow)}`), time: at });
    }
    return raw;
  };

  /** The cadence, and the clock it is read in.
   *
   * A bare cron says nothing about its timezone, and the "next" beside it is
   * rendered in the BROWSER's — so a Seoul workspace read from Seoul showed
   * `0 13 * * *` next to a 1pm that agreed by luck, and read from anywhere else
   * showed two times, one of which is nobody's. The schedule resolves against
   * the WORKSPACE's clock (migration 247); name it. UTC is left unlabelled —
   * it is the default and the label would be noise on every undeclared row.
   */
  const scheduleLine = (s: StandingSummary['schedule'], tz?: string | null): string => {
    if (!s) return t('schedule.none');
    const cadence = Array.isArray(s)
      ? s.map(describeSchedule).reduce((acc, next, i) =>
          i === 0 ? next : t('schedule.joined', { first: acc, second: next }), '')
      : describeSchedule(String(s));
    return tz && tz !== 'UTC' ? t('schedule.withTimezone', { cadence, timezone: tz }) : cadence;
  };

  /** Who looks after it — the derived minder, or the honest mechanical case. */
  const minderLine = (row: StandingSummary): string => {
    if (row.minder?.name) return t('minder.named', { name: row.minder.name });
    if (row.format && row.format !== 'md') return t('minder.automatic');
    return '';
  };

  return { problemCopy, runStatusLine, describeSchedule, scheduleLine, minderLine };
}

/**
 * The state, rendered — ONE badge, so the row, the detail and the mirror
 * cannot drift into three spellings of one state.
 *
 * ⚠️ The dot carries the state; the word repeats it. Colour alone is not a
 * status (a member who cannot distinguish amber from grey reads the word), and
 * the word alone scans slowly in a list. Both, always.
 */
export function StandingStateBadge({ row, className }: { row: StandingSummary; className?: string }) {
  const t = useTranslations('supervisor.state');
  const state = standingState(row);
  const tone: Record<StandingState, string> = {
    // Amber is the attention hue the product already reserves (surface-icons.tsx).
    attention: 'text-amber-700 dark:text-amber-400',
    paused: 'text-muted-foreground',
    running: 'text-muted-foreground',
    resting: 'text-muted-foreground',
  };
  const dot: Record<StandingState, string> = {
    attention: 'bg-amber-500',
    paused: 'bg-muted-foreground/40',
    running: 'bg-emerald-500',
    resting: 'bg-muted-foreground/40',
  };
  return (
    <span className={cn('inline-flex items-center gap-1.5 text-[11px] font-medium', tone[state], className)}>
      <span aria-hidden className={cn('h-1.5 w-1.5 shrink-0 rounded-full', dot[state])} />
      {t(state)}
    </span>
  );
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
  const t = useTranslations('supervisor');
  const { problemCopy, runStatusLine, scheduleLine, minderLine } = useStandingWords();
  const open = onOpen ?? onOpenFile;
  const minder = minderLine(row);
  return (
    <li
      className={cn(
        'group rounded-lg border bg-background p-4 transition-colors',
        // ⚠️ The border is the ONLY place the state colours the container. A
        // filled amber card in a list of five reads as an alarm; a left edge
        // reads as a flag. Everything else stays neutral so the list is calm.
        row.problem != null ? 'border-amber-500/40' : 'border-border/70 hover:border-border',
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          {/* ⭐ THE FILE IS THE SUBJECT. It was one of four lines at near-equal
              weight; a member scanning the cockpit looks for WHICH FILE first,
              so it leads at the largest type in the row and the state sits
              beside it — the two facts a scan needs, on one line. */}
          <div className="flex min-w-0 flex-wrap items-center gap-x-2.5 gap-y-1">
            <button
              type="button"
              onClick={() => open?.(row)}
              className="flex min-w-0 items-center gap-1.5 text-left text-[14px] font-semibold text-foreground hover:underline"
              title={onOpen ? t('row.openTitle') : t('row.openInFilesTitle')}
            >
              <FolderOpen className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              <span className="truncate">{row.target || t('row.noFileNamed')}</span>
            </button>
            <StandingStateBadge row={row} />
          </div>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {minder ? t('row.withTopic', { topic: row.topic, minder }) : row.topic}
          </p>
          <p className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1">
              <CalendarClock className="h-3 w-3 shrink-0" /> {scheduleLine(row.schedule, row.timezone)}
            </span>
            {/* The `Paused` chip is GONE from this line: the badge above says
                it once, and a state said twice in one row is the ADR-258 fault
                (two things speaking status at once).

                ⚠️ A BLOCKED ROW PROMISED A NEXT RUN (found by driving, not by
                reading, 2026-09-21). The server keeps serving `next_run_at`
                for a declaration that cannot run — correctly, it is when the
                schedule NEXT COMES ROUND — but rendering it put "Needs fixing"
                and "next in an hour" on the same line. It will not run then,
                and saying so is a false promise a member plans around. */}
            {row.next_run_at && !row.paused && row.problem == null && (
              <span>{t('row.next', { when: formatLedgerTime(row.next_run_at) })}</span>
            )}
            {row.sources.length > 0 && (
              <span>{t('row.sources', { count: row.sources.length })}</span>
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
                  {s.reads ? t('row.readsSuffix', { reads: lowerFirst(s.reads) }) : ''}
                </li>
              ))}
            </ul>
          )}
        </div>
        {/* ⚠️ THE VERBS RECEDE UNTIL REACHED FOR. Two bordered buttons at full
            strength competed with the filename for the eye on every row, so a
            list of five read as ten controls. They keep their full contrast on
            hover and on KEYBOARD FOCUS (`focus-within`) — a control that
            appears only on hover is unreachable without a mouse, which is the
            trap this idiom usually springs. */}
        <div className="flex shrink-0 items-center gap-1.5 opacity-70 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
          <button
            type="button"
            onClick={() => onRunNow(row)}
            disabled={busy || row.problem != null}
            title={row.problem != null ? t('row.blockedTitle') : t('row.runNowTitle')}
            className="flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground/30 disabled:opacity-40"
          >
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />}
            {t('row.runNow')}
          </button>
          <button
            type="button"
            onClick={() => onTogglePause(row)}
            disabled={busy}
            title={row.paused ? t('row.resumeTitle') : t('row.pauseTitle')}
            aria-label={row.paused ? t('row.resume') : t('row.pause')}
            className="flex items-center justify-center rounded-md border border-border p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground/30 disabled:opacity-40"
          >
            {row.paused ? <Play className="h-3.5 w-3.5" /> : <Pause className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {row.problem != null && (
        <p className="mt-3 rounded-md border border-amber-500/40 bg-amber-500/5 px-3 py-2 text-xs text-amber-700 dark:text-amber-300">
          {problemCopy(row.problem)} {t('row.fixHint')}
        </p>
      )}

      {(note || row.last_run) && (
        <p className={cn('mt-3 text-xs', note ? 'text-foreground' : 'text-muted-foreground')}>
          {note
            ?? (row.last_run
              ? (row.last_run.at
                  ? t('lastRun.withTime', {
                      line: runStatusLine(row.last_run),
                      when: formatLedgerTime(row.last_run.at),
                    })
                  : runStatusLine(row.last_run))
              : null)}
        </p>
      )}
    </li>
  );
}
