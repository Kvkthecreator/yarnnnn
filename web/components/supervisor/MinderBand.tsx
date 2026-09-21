'use client';

/**
 * MinderBand — band 2, *who is minding it* (APP-BUILDER-UX §4).
 *
 * ⭐ THE FRAME'S CENTRAL PROMISE, RENDERED. The app-builder design calls this
 * "the hardest design problem here, and the one that is judgment rather than
 * mechanism". It shipped as a CONSTANT — one sentence that read identically
 * whether five pieces of work were running, one was failing, or none existed.
 * A band that cannot change cannot be wrong, and it also cannot be trusted:
 * a member learns in a week that it never says anything, which is exactly the
 * "surfaces noise to prove it is alive" failure arriving by the other door.
 *
 * THE THREE STATES ARE §4.1's, unchanged:
 *
 *   Resting   `Supervisor looks after this.`        most of the time — DEFAULT
 *   Working   `Supervisor is updating brief.md.`    a run is in flight
 *   Raising   `brief.md can't run…`      + one verb  something worth saying
 *
 * ⚠️ RESTING IS NOT AN EMPTY STATE (§4.1). It reads as calm, not as absence —
 * someone is on it and there is nothing to do. That is why the resting line
 * keeps its full sentence and its steady dot rather than dimming to nothing.
 *
 * ⚠️ THE RULE FOR RAISING (§4.2): *raise only what changes what she would do
 * next.* A failed run does not qualify — runs fail transiently and the row
 * says so in its own line. Only a declaration that CANNOT RUN until a member
 * fixes it changes what she does next, so `problem` is the sole raise.
 *
 * ⚠️ AT MOST ONE RAISE, STRUCTURALLY (§4.2.1). The band renders ONE raise —
 * the first blocked piece of work — and a count carries the rest. There is no
 * room for two by construction, which is the property §4.2 asks for. The
 * sentence itself may wrap: one raise is the rule, not one physical line.
 *
 * ⚠️ DERIVED, NEVER READ. Every input is the roster the surface already holds.
 * This band adds no fetch, so it cannot be the slow band that holds the
 * cockpit (the 2026-09-19 lesson that split the three reads apart).
 */

import { useTranslations } from 'next-intl';
import { AlertTriangle } from 'lucide-react';
import type { StandingSummary } from '@/lib/api/client';
import { WorkingGlyph } from '@/components/shared/Working';
import { cn } from '@/lib/utils';

export function MinderBand({
  rows, busyTopic, onOpen,
}: {
  /** The roster; null while its read is still out. */
  rows: StandingSummary[] | null;
  /** The topic with a run in flight, if any — the surface's own `busy`. */
  busyTopic: string | null;
  onOpen: (topic: string) => void;
}) {
  const t = useTranslations('supervisor.minderBand');

  // WORKING — a run is in flight. Named, because "working…" on its own is the
  // anonymous spinner ADR-651 exists to replace.
  if (busyTopic) {
    const target = rows?.find((r) => r.topic === busyTopic)?.target ?? busyTopic;
    return (
      <Band>
        <WorkingGlyph className="mt-0.5 shrink-0 text-muted-foreground" />
        <span className="min-w-0 truncate">{t('working', { target })}</span>
      </Band>
    );
  }

  // RAISING — the first piece of work that cannot run until it is fixed.
  const blocked = rows?.filter((r) => r.problem != null) ?? [];
  if (blocked.length > 0) {
    const first = blocked[0];
    // Worded here rather than inline: a multi-line ternary inside JSX reads to
    // the ADR-660 meter as literal copy even when every branch is a `t()` call.
    const raise = blocked.length === 1
      ? t('raiseOne', { target: first.target || first.topic })
      : t('raiseMany', { target: first.target || first.topic, count: blocked.length - 1 });
    return (
      <Band tone="attention">
        <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600 dark:text-amber-500" />
        {/* WRAPS, never truncates. A raise clipped to "…can't run until its
            ins…" (driven at 390px) has lost the one thing it exists to say.
            Band 2 is one RAISE, not one physical line — §4.2's "no room for
            two" is about how many raises, not how many lines. */}
        <span className="min-w-0 flex-1">{raise}</span>
        <button
          type="button"
          onClick={() => onOpen(first.topic)}
          className="mt-px shrink-0 rounded-md border border-amber-500/40 px-2 py-0.5 text-[11px] font-medium text-amber-700 transition-colors hover:bg-amber-500/10 dark:text-amber-400"
        >
          {t('raiseAction')}
        </button>
      </Band>
    );
  }

  // RESTING — the default, and a complete reassuring sentence.
  return (
    <Band>
      <span aria-hidden className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500/70" />
      <span className="min-w-0 truncate">{t('resting')}</span>
    </Band>
  );
}

function Band({ children, tone }: { children: React.ReactNode; tone?: 'attention' }) {
  return (
    <div
      className={cn(
        // `items-start`, because a wrapped raise must keep its glyph and its
        // action on the first line rather than floating to the middle.
        'flex items-start gap-2 border-b px-5 py-2.5 text-[13px]',
        tone === 'attention'
          ? 'border-amber-500/30 bg-amber-500/[0.07] text-amber-900 dark:text-amber-200'
          : 'border-border/60 bg-muted/20 text-foreground/80',
      )}
    >
      {children}
    </div>
  );
}
