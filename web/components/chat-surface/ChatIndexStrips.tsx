'use client';

/**
 * Chat's index strips — what needs you, and who (ADR-670 D4).
 *
 * The lane list is Chat's INDEX (ADR-670 D2: index · object · supervision).
 * Two strips sit above its recents:
 *
 *   - NeedsYouStrip — the one needs-you queue (`useNeedsYou`, D5), capped, each
 *     row opening its OBJECT: a mention opens its conversation (the visit
 *     discharges it, ADR-637), a decision opens its decision in place (the
 *     same modal Notifications → To do opens), a due run opens its work.
 *     Absent when nothing waits.
 *   - WhoStrip — the agents as FACES, from the roster the lane list already
 *     receives (`LaneData.agents`; no second roster read). A face is the
 *     who-filter made visible: choosing one filters the list to the chats that
 *     agent is in, choosing it again shows every chat, and with no chat yet it
 *     starts one through the one create path. The filter STATE stays the
 *     surface's (`whoFilter`); this strip only renders it and asks to change it.
 */

import { useTranslations } from 'next-intl';
import { AgentFace } from '@/components/agents/AgentFace';
import { useProposalModal, type ProposalData } from '@/components/queue/ProposalCard';
import type { Run } from '@/lib/api/client';
import { dischargeMention, useNeedsYou } from '@/lib/attention/useNeedsYou';
import { useProposalLabels } from '@/lib/proposal-labels';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { cn } from '@/lib/utils';

/** How many rows the index shows before handing over to To do. The index is
 *  never the place a thing is read in full (ADR-670 D6). */
const NEEDS_YOU_CAP = 3;

const ROW = 'w-full text-left px-3 py-1.5 transition-colors hover:bg-muted/60';
const HEADING = 'px-3 pt-2 pb-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground';

export function NeedsYouStrip({ onOpenLane }: { onOpenLane: (laneId: string) => void }) {
  const t = useTranslations('chat.index');
  const tAttention = useTranslations('shell.attention');
  const tRuns = useTranslations('runs');
  const { actionLabel, queuedByDialLine } = useProposalLabels();
  const { mentions, waitingRuns, proposals, count, refresh } = useNeedsYou();
  const { navigateToSurface } = useSurfacePreferences();
  const { openProposal, modalElement } = useProposalModal({ onResolved: () => void refresh() });

  if (count === 0) return modalElement;

  // One ordered list, capped: mentions lead (the most personal ask), then runs
  // due on you, then decisions — the bell's To do order.
  const rows = [
    ...mentions.map((m) => ({ kind: 'mention' as const, key: `m-${m.conversation_id}-${m.sequence}`, m })),
    ...waitingRuns.map((r) => ({ kind: 'run' as const, key: `r-${r.id}`, r })),
    ...proposals.map((p) => ({ kind: 'proposal' as const, key: `p-${p.id}`, p })),
  ].slice(0, NEEDS_YOU_CAP);

  const openRun = (run: Run) => {
    if (run.topic) navigateToSurface('supervisor', { work: run.topic });
    else if (run.lane_id) onOpenLane(run.lane_id);
  };

  return (
    <div className="shrink-0 border-b border-border pb-1">
      <div className={HEADING}>{t('needsYou')}</div>
      {rows.map((row) => {
        if (row.kind === 'mention') {
          const { m } = row;
          return (
            <button
              key={row.key}
              type="button"
              onClick={() => {
                dischargeMention(m.conversation_id, m.sequence);
                onOpenLane(m.conversation_id);
              }}
              className={ROW}
            >
              <span className="block truncate text-xs text-foreground">
                {tAttention('mentioned', { author: m.author, conversation: m.conversation_name })}
              </span>
              <span className="block truncate text-[10px] text-muted-foreground">{m.excerpt}</span>
            </button>
          );
        }
        if (row.kind === 'run') {
          const { r } = row;
          return (
            <button key={row.key} type="button" onClick={() => openRun(r)} className={ROW}>
              <span className="block truncate text-xs text-foreground">
                {r.topic || tRuns('inConversation')}
              </span>
              <span className="block truncate text-[10px] text-muted-foreground">{tRuns('dueYou')}</span>
            </button>
          );
        }
        const { p } = row;
        return (
          <button
            key={row.key}
            type="button"
            onClick={() => openProposal(p as unknown as ProposalData)}
            className={ROW}
          >
            <span className="block truncate text-xs text-foreground">{actionLabel(p)}</span>
            <span className="block truncate text-[10px] text-muted-foreground">
              {queuedByDialLine(p.source) ?? t('decision')}
            </span>
          </button>
        );
      })}
      {count > NEEDS_YOU_CAP && (
        <button
          type="button"
          onClick={() => navigateToSurface('notifications', { pane: 'resolve' })}
          className="w-full px-3 py-1 text-left text-[11px] text-muted-foreground transition-colors hover:text-foreground"
        >
          {t('moreInToDo', { count: count - NEEDS_YOU_CAP })}
        </button>
      )}
      {modalElement}
    </div>
  );
}

export interface WhoFace {
  slug: string;
  name: string;
  avatarUrl?: string;
}

export function WhoStrip({
  faces,
  selected,
  onChoose,
  onClear,
}: {
  faces: WhoFace[];
  /** The surface's who-filter — the slug of the agent the list is showing. */
  selected: string | null;
  /** A face was chosen. The surface decides: filter, or start a first chat. */
  onChoose: (slug: string) => void;
  onClear: () => void;
}) {
  const t = useTranslations('chat.index');
  if (faces.length === 0) return null;
  return (
    <div className="shrink-0 border-b border-border">
      <div className="flex items-center justify-between pr-2">
        <div className={HEADING}>{t('who')}</div>
        {selected && (
          <button
            type="button"
            onClick={onClear}
            className="rounded px-1.5 pt-1 text-[10px] text-muted-foreground transition-colors hover:text-foreground"
          >
            {t('showAll')}
          </button>
        )}
      </div>
      <div className="flex gap-1 overflow-x-auto px-2 pb-2">
        {faces.map((f) => {
          const active = selected === f.slug;
          return (
            <button
              key={f.slug}
              type="button"
              onClick={() => onChoose(f.slug)}
              aria-pressed={active}
              title={f.name}
              className={cn(
                'flex w-14 shrink-0 flex-col items-center gap-1 rounded-md px-1 py-1 transition-colors',
                active ? 'bg-muted' : 'hover:bg-muted/60',
              )}
            >
              <AgentFace
                name={f.name}
                avatarUrl={f.avatarUrl}
                kind="agent"
                size="md"
                className={cn(active && 'ring-2 ring-primary ring-offset-1 ring-offset-background')}
              />
              <span
                className={cn(
                  'w-full truncate text-center text-[10px]',
                  active ? 'text-foreground' : 'text-muted-foreground',
                )}
              >
                {f.name}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
