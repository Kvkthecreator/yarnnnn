'use client';

/**
 * RunTray — the shell's run tray (ADR-666 D9).
 *
 * A member is usually somewhere else while their work runs — in Text, in Chat,
 * in another app entirely. The tray is how they know, from anywhere: present
 * in the top bar ONLY while a run is going in the workspace or one is due on
 * them; absent otherwise (a permanent control that is almost always empty is
 * chrome, not signal). Opening it shows the live runs in the one `RunView`,
 * with Stop where the viewer may stop, and the door to the Supervisor.
 *
 * It reads the SAME store as the cockpit (`useRuns`) — one reader of the run
 * ledger on the client — so the tray and the cockpit cannot disagree about
 * whether something is still running.
 *
 * "Run it" on a due run opens the work's detail with `start=1` — the ONE door
 * that starts a browser run, because the run happens in the work's own
 * conversation, which lives there.
 */

import { useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import { ArrowRight } from 'lucide-react';
import type { Run } from '@/lib/api/client';
import { RunView } from '@/components/runs/RunView';
import { useRuns } from '@/lib/runs/useRuns';
import { usePopoverDismissal } from '@/lib/shell/usePopoverDismissal';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { Z_POPOVER } from '@/lib/shell/z-tiers';
import { cn } from '@/lib/utils';

export function RunTray() {
  const t = useTranslations('runs.tray');
  const { runs, refresh } = useRuns();
  const { navigateToSurface, userId } = useSurfacePreferences();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  usePopoverDismissal(ref, open, () => setOpen(false));

  const going = (runs ?? []).filter((r) => r.state === 'queued' || r.state === 'running');
  const dueOnMe = (runs ?? []).filter((r) => r.state === 'waiting' && r.user_id === userId);
  const shown: Run[] = [...going, ...dueOnMe];
  if (shown.length === 0) return null;

  // Worded here, never inline (the ADR-660 meter reads a JSX ternary as copy).
  const label = going.length > 0
    ? t('label', { count: going.length })
    : t('labelWaiting', { count: dueOnMe.length });

  const openWork = (topic: string, start = false) => {
    setOpen(false);
    navigateToSurface('supervisor', { work: topic, ...(start ? { start: '1' } : {}) });
  };

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className={cn(
          'flex h-8 items-center gap-1.5 rounded-md px-2 text-[12px] font-medium text-foreground transition-colors hover:bg-muted',
          open && 'bg-muted',
        )}
      >
        <span
          aria-hidden
          className={cn(
            'h-1.5 w-1.5 shrink-0 rounded-full',
            going.length > 0 ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500',
          )}
        />
        <span className="hidden sm:inline">{label}</span>
        <span className="sm:hidden">{shown.length}</span>
      </button>

      {open && (
        <div
          role="dialog"
          aria-label={t('title')}
          style={{ zIndex: Z_POPOVER }}
          className="absolute right-0 top-full mt-1 w-96 max-w-[calc(100vw-1rem)] overflow-hidden rounded-lg border border-border bg-background shadow-lg"
        >
          <div className="border-b border-border bg-muted/30 px-3 py-2 text-sm font-medium">{t('title')}</div>
          <ul className="max-h-[28rem] space-y-2 overflow-y-auto p-2">
            {shown.map((r) => (
              <li key={r.id}>
                <RunView
                  run={r}
                  viewerId={userId}
                  compact
                  onOpen={(run) => run.topic && openWork(run.topic)}
                  onRunIt={(run) => run.topic && openWork(run.topic, true)}
                  onChanged={() => void refresh()}
                />
              </li>
            ))}
          </ul>
          <button
            type="button"
            onClick={() => { setOpen(false); navigateToSurface('supervisor'); }}
            className="flex w-full items-center justify-between border-t border-border px-3 py-2 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            {t('openSupervisor')} <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}
