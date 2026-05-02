'use client';

/**
 * ScheduleListSurface — Cadence-sectioned list for /schedule (ADR-243).
 *
 * Renders all recurrences in three sections by temporal flavor:
 *   Recurring → Reactive → One-time
 *
 * Each row links to the canonical detail surface at /work?task={slug} —
 * /schedule does not maintain its own detail mode (ADR-243 Decision 3).
 */

import { useMemo } from 'react';
import { CalendarClock } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatRelativeTime } from '@/lib/formatting';
import {
  cadenceCategory,
  humanizeSchedule,
  CADENCE_ORDER,
  CADENCE_LABELS,
  type CadenceCategory,
} from '@/lib/schedule';
import type { Recurrence } from '@/types';

interface ScheduleListSurfaceProps {
  recurrences: Recurrence[];
  onSelect: (slug: string) => void;
}

export function ScheduleListSurface({ recurrences, onSelect }: ScheduleListSurfaceProps) {
  const grouped = useMemo(() => {
    const buckets: Record<CadenceCategory, Recurrence[]> = {
      recurring: [],
      reactive: [],
      'one-time': [],
    };
    for (const r of recurrences) {
      // Hide archived recurrences from the cadence view — they're no longer
      // scheduled in any meaningful sense. /work tabs surface them with a
      // dedicated "Archived" affordance; /schedule stays focused on what's
      // actively on the calendar.
      if (r.status === 'archived') continue;
      buckets[cadenceCategory(r)].push(r);
    }
    return CADENCE_ORDER
      .map(key => ({
        key,
        label: CADENCE_LABELS[key],
        items: buckets[key],
      }))
      .filter(g => g.items.length > 0);
  }, [recurrences]);

  if (grouped.length === 0) {
    return (
      <div className="flex items-center justify-center h-full px-6">
        <div className="text-center max-w-md">
          <CalendarClock className="w-8 h-8 text-muted-foreground/30 mx-auto mb-4" />
          <h3 className="text-base font-semibold mb-2">Nothing scheduled yet</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Tell YARNNN what you want done and on what cadence.
            Scheduled work will appear here.
          </p>
          <a
            href="/chat"
            className="inline-flex items-center gap-2 rounded-md bg-foreground px-4 py-2 text-sm font-medium text-background hover:bg-foreground/90 transition-colors"
          >
            Talk to YARNNN
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-auto">
      <div className="px-6 py-6 max-w-4xl space-y-8">
        {grouped.map(group => (
          <section key={group.key}>
            <header className="mb-3">
              <h3 className="text-sm font-semibold text-foreground">
                {group.label.title}
                <span className="ml-2 text-xs font-normal text-muted-foreground/50">
                  · {group.items.length}
                </span>
              </h3>
              <p className="text-xs text-muted-foreground/70 mt-0.5">
                {group.label.description}
              </p>
            </header>
            <ul className="divide-y divide-border/40 rounded-lg border border-border/60 bg-background">
              {group.items.map(r => (
                <ScheduleRow key={r.id} recurrence={r} category={group.key} onSelect={onSelect} />
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}

// ─── Row ──────────────────────────────────────────────────────────────────

function ScheduleRow({
  recurrence,
  category,
  onSelect,
}: {
  recurrence: Recurrence;
  category: CadenceCategory;
  onSelect: (slug: string) => void;
}) {
  const cadenceText =
    category === 'recurring'
      ? humanizeSchedule(recurrence.schedule)
      : category === 'reactive'
        ? 'On event'
        : 'One-time';

  const isPaused = recurrence.paused === true;
  const isCompleted = recurrence.status === 'completed';
  const statusTone = isPaused
    ? { dot: 'bg-amber-500', label: 'Paused' }
    : isCompleted
      ? { dot: 'bg-muted-foreground/40', label: 'Completed' }
      : { dot: 'bg-emerald-500', label: 'Active' };

  return (
    <li>
      <button
        onClick={() => onSelect(recurrence.slug)}
        className={cn(
          'w-full text-left px-4 py-3 flex items-center gap-4 hover:bg-muted/30 transition-colors',
          isPaused && 'opacity-60',
        )}
      >
        <span className={cn('h-2 w-2 rounded-full shrink-0', statusTone.dot)} aria-label={statusTone.label} />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium truncate">{recurrence.title}</div>
          <div className="text-[11px] text-muted-foreground/70 mt-0.5 truncate">
            {cadenceText}
          </div>
        </div>
        <div className="text-[11px] text-muted-foreground/60 shrink-0 text-right">
          {recurrence.next_run_at ? (
            <>Next {formatRelativeTime(recurrence.next_run_at)}</>
          ) : recurrence.last_run_at ? (
            <>Last {formatRelativeTime(recurrence.last_run_at)}</>
          ) : (
            <span className="text-muted-foreground/40 italic">Not yet run</span>
          )}
        </div>
      </button>
    </li>
  );
}
