'use client';

/**
 * StartPicker — step one of the door: *what should it keep current?*
 *
 * ⭐ WHY THE STARTS MOVED INTO THE MODAL. They lived in the work band's EMPTY
 * STATE, which made them reachable exactly once — before a member had any
 * standing work. The moment the first piece existed the empty state was gone,
 * and with it every pre-shaped start: the only remaining door was "New
 * standing work", which opened a BLANK form. A member with one piece of work
 * had a strictly worse creation path than a member with none.
 *
 * The house gesture for creation is a modal that shows CHOICES, never form
 * fields, and opens a focused form once one is picked — `NewArtifactModal`
 * (ADR-452 v2) is that pattern's tenant, and this follows it: pick a start,
 * then name it. The empty state keeps a single button into this same modal
 * rather than a second, divergent copy of the list.
 *
 * ⚠️ ONE LIST, ONE SHAPE. The starts render through the shared `StartMark`, so
 * a Slack start wears the same face here, in Reach and in the finder.
 */

import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useTranslations } from 'next-intl';
import { ChevronRight, Plus } from 'lucide-react';
import { Z_CONFIRM_BACKDROP, Z_CONFIRM_DIALOG } from '@/lib/shell/z-tiers';
import { StartMark } from '@/components/supervisor/StartMark';
import { lowerFirst } from '@/components/standing/StandingRow';
import type { StandingStart } from '@/lib/api/client';

export function StartPicker({
  open, starts, onPick, onClose, onOpenReach,
}: {
  open: boolean;
  starts: StandingStart[];
  /** A chosen start, or null for the blank form ("set up from scratch"). */
  onPick: (start: StandingStart | null) => void;
  onClose: () => void;
  onOpenReach: () => void;
}) {
  const t = useTranslations('supervisor.section');
  const tp = useTranslations('supervisor.startPicker');

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return;
      e.stopPropagation();
      onClose();
    };
    window.addEventListener('keydown', onKey, true);
    return () => window.removeEventListener('keydown', onKey, true);
  }, [open, onClose]);

  if (!open || typeof document === 'undefined') return null;

  const connectorStarts = starts.filter((s) => s.kind === 'connector');

  return createPortal(
    <>
      <div
        className="fixed inset-0 bg-black/50 animate-in fade-in duration-150"
        style={{ zIndex: Z_CONFIRM_BACKDROP }}
        onClick={onClose}
      />
      <div
        className="pointer-events-none fixed inset-0 flex items-center justify-center p-4"
        style={{ zIndex: Z_CONFIRM_DIALOG }}
      >
        <div
          role="dialog"
          aria-modal="true"
          aria-label={tp('title')}
          className="pointer-events-auto flex max-h-[85vh] w-full max-w-lg flex-col overflow-hidden rounded-xl border border-border bg-background shadow-xl animate-in fade-in zoom-in-95 duration-150"
        >
          <div className="border-b border-border px-5 py-4">
            <h2 className="text-base font-semibold text-foreground">{tp('title')}</h2>
            <p className="mt-1 text-xs text-muted-foreground">{tp('subtitle')}</p>
          </div>

          <div className="flex-1 overflow-y-auto px-5 py-4">
            <ul className="space-y-2">
              {starts.map((s) => {
                // Worded here rather than inline: a multi-line ternary inside
                // JSX reads to the ADR-660 meter as literal copy even when
                // every branch is a `t()` call.
                const sub = s.kind === 'connector'
                  ? t('startConnector', {
                      name: s.name,
                      reads: s.reads ? lowerFirst(s.reads) : t('startConnectorFallback'),
                    })
                  : s.reads
                    ? lowerFirst(s.reads)
                    : t('startPage');
                return (
                <li key={`${s.kind}-${s.connector ?? s.title}`}>
                  <button
                    type="button"
                    onClick={() => onPick(s)}
                    className="group flex w-full items-center gap-3 rounded-lg border border-border/70 bg-background px-3.5 py-3 text-left transition-colors hover:border-border hover:bg-muted/30 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground/30"
                  >
                    <StartMark start={s} />
                    <span className="min-w-0 flex-1">
                      <span className="block text-[13px] font-medium text-foreground">{s.title}</span>
                      <span className="block truncate text-[12px] text-muted-foreground">{sub}</span>
                    </span>
                    <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground/50 transition-colors group-hover:text-muted-foreground" />
                  </button>
                </li>
                );
              })}
            </ul>

            {/* Nothing connected: the next step is Reach, the door that makes a
                connection — the same guidance the empty state gave. */}
            {connectorStarts.length === 0 && (
              <p className="mt-3 text-[11px] text-muted-foreground">
                {t('workEmptyNoStarts')}{' '}
                <button
                  type="button"
                  onClick={onOpenReach}
                  className="underline hover:text-foreground"
                >
                  {t('openReach')}
                </button>
              </p>
            )}
          </div>

          <div className="flex items-center justify-between gap-3 border-t border-border px-5 py-3">
            <button
              type="button"
              onClick={() => onPick(null)}
              className="inline-flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
            >
              <Plus className="h-3.5 w-3.5" /> {t('setUpFromScratch')}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted/40"
            >
              {tp('cancel')}
            </button>
          </div>
        </div>
      </div>
    </>,
    document.body,
  );
}
