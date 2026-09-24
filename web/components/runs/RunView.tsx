'use client';

/**
 * RunView — one run, rendered (ADR-666 D7). THE rendering of a run: the
 * Supervisor's cockpit and detail, and the shell's run tray, all mount this.
 * Chat keeps drawing its own turn's steps inline (from the same stream and, on
 * reload, from the same run) — a second rendering there would show the member
 * every step twice.
 *
 * What a member reads, in order: how it stands (a word AND a dot — colour
 * alone is never a status), what it is and whose it is, the steps as they land
 * (worded from each receipt's record by the chat's own catalog, so a step reads
 * the same here as in the conversation), and the one verb that fits its state:
 * Run it (due, and yours), Stop (going, and yours or you own the workspace),
 * Skip (due, and you may).
 *
 * Steps land live: `useRuns` refetches on every realtime change to `runs`, and
 * this component is pure over the row it is given.
 */

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Loader2, Play, Square } from 'lucide-react';
import { api, isLiveRun, type Run } from '@/lib/api/client';
import { toolStepRef } from '@/components/chat-surface/toolLabels';
import { useToolLabels } from '@/components/chat-surface/useToolLabels';
import { useRunWords } from '@/components/runs/useRunWords';
import { formatLedgerTime } from '@/lib/formatting';
import { cn } from '@/lib/utils';

/** How many of the newest steps a compact view shows before "N more". */
const COMPACT_STEPS = 3;

const DOT: Record<string, string> = {
  queued: 'bg-sky-500 animate-pulse',
  running: 'bg-emerald-500 animate-pulse',
  waiting: 'bg-amber-500',
  done: 'bg-muted-foreground/40',
  failed: 'bg-destructive',
  stopped: 'bg-muted-foreground/40',
};

export function RunStateBadge({ run, className }: { run: Run; className?: string }) {
  const { stateWord } = useRunWords();
  return (
    <span className={cn('inline-flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground', className)}>
      <span aria-hidden className={cn('h-1.5 w-1.5 shrink-0 rounded-full', DOT[run.state] ?? DOT.done)} />
      {stateWord(run)}
    </span>
  );
}

export function RunView({
  run, viewerId, compact = false, onOpen, onRunIt, onOpenFile, onChanged, className,
}: {
  run: Run;
  /** The viewer — decides whether a due run is theirs to run. */
  viewerId?: string | null;
  /** Newest steps only, with a "N more" disclosure. */
  compact?: boolean;
  /** Open the work this run belongs to (the Supervisor's detail). */
  onOpen?: (run: Run) => void;
  /** Start a due run — only offered to its own member. */
  onRunIt?: (run: Run) => void;
  onOpenFile?: (path: string) => void;
  /** A Stop / Skip landed — the caller refreshes what it holds. */
  onChanged?: () => void;
  className?: string;
}) {
  const t = useTranslations('runs');
  const wordStep = useToolLabels();
  const { outcomeLine, stateWord, whoLine } = useRunWords();
  const [expanded, setExpanded] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [stopError, setStopError] = useState<string | null>(null);

  const live = isLiveRun(run);
  const mine = Boolean(viewerId) && run.user_id === viewerId;
  const title = run.topic || t('inConversation');
  const steps = run.steps ?? [];
  const shown = compact && !expanded ? steps.slice(-COMPACT_STEPS) : steps;
  const hidden = steps.length - shown.length;
  const cost = typeof run.cost_usd === 'number' && run.cost_usd > 0
    ? new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 3 }).format(run.cost_usd)
    : null;

  const stop = async () => {
    if (stopping) return;
    setStopping(true);
    setStopError(null);
    try {
      await api.runs.stop(run.id);
      onChanged?.();
    } catch {
      setStopError(t('couldNotStop'));
    } finally {
      setStopping(false);
    }
  };

  const dueLine = mine ? t('dueYou') : t('dueOther', { name: run.member_name || t('someone') });
  // The outcome line only when it says more than the badge beside the title
  // ("Done" twice, one under the other, was the click-pass finding).
  const outcome = !live ? outcomeLine(run) : null;
  const saysMore = outcome !== null && outcome !== stateWord(run);

  return (
    <div className={cn('rounded-lg border border-border/70 bg-background px-3.5 py-3', className)}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 flex-wrap items-center gap-x-2.5 gap-y-1">
            {onOpen && run.topic ? (
              <button
                type="button"
                onClick={() => onOpen(run)}
                className="truncate text-left text-[13px] font-semibold text-foreground hover:underline"
              >
                {title}
              </button>
            ) : (
              <span className="truncate text-[13px] font-semibold text-foreground">{title}</span>
            )}
            <RunStateBadge run={run} />
          </div>
          <p className="mt-0.5 truncate text-[11px] text-muted-foreground">
            {whoLine(run)}
            {run.started_at ? ` · ${formatLedgerTime(run.started_at)}` : ''}
            {cost ? ` · ${t('cost', { cost })}` : ''}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          {run.state === 'waiting' && mine && onRunIt && (
            <button
              type="button"
              onClick={() => onRunIt(run)}
              className="inline-flex items-center gap-1 rounded-md bg-foreground px-2.5 py-1 text-xs font-medium text-background hover:opacity-90"
            >
              <Play className="h-3 w-3" /> {t('runIt')}
            </button>
          )}
          {live && run.can_stop && (
            <button
              type="button"
              onClick={() => void stop()}
              disabled={stopping}
              className="inline-flex items-center gap-1 rounded-md border border-border px-2.5 py-1 text-xs text-foreground hover:bg-muted disabled:opacity-50"
            >
              {stopping ? <Loader2 className="h-3 w-3 animate-spin" /> : <Square className="h-3 w-3" />}
              {run.state === 'waiting' ? t('skip') : t('stop')}
            </button>
          )}
        </div>
      </div>

      {run.state === 'waiting' && <p className="mt-2 text-xs text-foreground">{dueLine}</p>}
      {saysMore && <p className="mt-2 text-xs text-foreground">{outcome}</p>}
      {stopError && <p className="mt-1 text-xs text-destructive">{stopError}</p>}

      {steps.length > 0 && (
        <ol className="mt-2 space-y-0.5 border-l border-border/70 pl-3">
          {hidden > 0 && (
            <li>
              <button
                type="button"
                onClick={() => setExpanded(true)}
                className="text-[11px] text-muted-foreground underline hover:text-foreground"
              >
                {t('moreSteps', { count: hidden })}
              </button>
            </li>
          )}
          {shown.map((s, i) => {
            const line = s.record
              ? wordStep(toolStepRef({ name: s.name ?? '', record: s.record }))
              : (s.text ?? s.name ?? '');
            return (
              <li
                key={`${s.at ?? ''}-${i}`}
                className={cn('truncate text-[12px]', s.ok === false ? 'text-destructive/80' : 'text-muted-foreground')}
                title={s.text ?? undefined}
              >
                {line}
              </li>
            );
          })}
        </ol>
      )}
      {live && run.state !== 'waiting' && steps.length === 0 && (
        <p className="mt-2 text-[12px] text-muted-foreground">{t('noSteps')}</p>
      )}

      {run.record_path && onOpenFile && (
        <button
          type="button"
          onClick={() => onOpenFile(run.record_path!)}
          className="mt-2 text-[11px] text-muted-foreground underline hover:text-foreground"
        >
          {t('record')}
        </button>
      )}
    </div>
  );
}
