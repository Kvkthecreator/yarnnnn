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
 *   Working   `Updating brief.md.`                 a run is in flight — and for
 *             `Kevin's browser is working on …`    browser work, WHOSE browser
 *   Raising   `brief.md is due — run it.`  + verb  something worth saying
 *
 * ⚠️ WORKING NAMES WHO DOES IT (ADR-667 D6). It said "Supervisor is updating
 * X" for every run — but the Supervisor runs nothing: a derive run is the
 * kept file's derived executor, and a browser run is one member's own agent
 * in that member's browser. The band follows the LEDGER, not only this
 * page's click.
 *
 * ⚠️ RESTING IS NOT AN EMPTY STATE (§4.1). It reads as calm, not as absence —
 * someone is on it and there is nothing to do. That is why the resting line
 * keeps its full sentence and its steady dot rather than dimming to nothing.
 *
 * ⚠️ THE RULE FOR RAISING (§4.2): *raise only what changes what she would do
 * next.* A failed run does not qualify — runs fail transiently and the row
 * says so in its own line. Two things do: a run DUE ON THE VIEWER (browser
 * work waits for its member — ADR-667 D6, the tray's own rule), raised first;
 * then a declaration that CANNOT RUN until a member fixes it.
 *
 * ⚠️ AT MOST ONE RAISE, STRUCTURALLY (§4.2.1). The band renders ONE raise —
 * the first blocked piece of work — and a count carries the rest. There is no
 * room for two by construction, which is the property §4.2 asks for. The
 * sentence itself may wrap: one raise is the rule, not one physical line.
 *
 * ⚠️ DERIVED, NEVER READ. Every input is the roster and the run ledger the surface already holds.
 * This band adds no fetch, so it cannot be the slow band that holds the
 * cockpit (the 2026-09-19 lesson that split the three reads apart).
 */

import { useTranslations } from 'next-intl';
import { AlertTriangle } from 'lucide-react';
import type { Run, StandingSummary } from '@/lib/api/client';
import { WorkingGlyph } from '@/components/shared/Working';
import { cn } from '@/lib/utils';
import { waitsOnViewer } from '@/lib/attention/useNeedsYou';

export function MinderBand({
  rows, runs, viewerId, busyTopic, onOpen, onRunIt,
}: {
  /** The roster; null while its read is still out. */
  rows: StandingSummary[] | null;
  /** The run ledger (`useRuns`); null while its read is still out. */
  runs: Run[] | null;
  viewerId: string | null;
  /** The topic this page just ran (a derive Run now) before its row lands. */
  busyTopic: string | null;
  onOpen: (topic: string) => void;
  onRunIt: (run: Run) => void;
}) {
  const t = useTranslations('supervisor.minderBand');
  const targetOf = (topic: string) => rows?.find((r) => r.topic === topic)?.target || topic;

  // WORKING — a run is in flight, named by who does it. Named, because
  // "working…" on its own is the anonymous spinner ADR-651 exists to replace.
  const running = (runs ?? []).find((r) => r.state === 'running' && r.topic);
  if (running?.topic || busyTopic) {
    const target = targetOf(running?.topic ?? busyTopic ?? '');
    const line = running?.kind === 'browser'
      ? t('workingBrowser', { member: running.member_name || t('aMember'), target })
      : t('working', { target });
    return (
      <Band>
        <WorkingGlyph className="mt-0.5 shrink-0 text-muted-foreground" />
        <span className="min-w-0 truncate">{line}</span>
      </Band>
    );
  }

  // RAISING — first a run due on THIS member; then a piece of work that
  // cannot run until it is fixed.
  const due = (runs ?? []).find((r) => r.topic && waitsOnViewer(r, viewerId));
  if (due?.topic) {
    return (
      <Band tone="attention">
        <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600 dark:text-amber-500" />
        <span className="min-w-0 flex-1">{t('raiseDue', { target: targetOf(due.topic) })}</span>
        <RaiseButton onClick={() => onRunIt(due)}>{t('raiseDueAction')}</RaiseButton>
      </Band>
    );
  }
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
        <RaiseButton onClick={() => onOpen(first.topic)}>{t('raiseAction')}</RaiseButton>
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

function RaiseButton({ children, onClick }: { children: React.ReactNode; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="mt-px shrink-0 rounded-md border border-amber-500/40 px-2 py-0.5 text-[11px] font-medium text-amber-700 transition-colors hover:bg-amber-500/10 dark:text-amber-400"
    >
      {children}
    </button>
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
