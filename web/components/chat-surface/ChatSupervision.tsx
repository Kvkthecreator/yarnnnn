'use client';

/**
 * ChatSupervision — Chat's `side` slot: what this conversation made, and what
 * it ran (ADR-670 D3).
 *
 * The frame is PANES' own (ADR-670 D2): the lane list is the index, the
 * conversation is the canvas, and this is the supervision beside it — the one
 * place an agent's work shows NEXT TO the conversation that caused it.
 *
 * Two sections, each read from a store that already exists, each ABSENT when
 * it has nothing to show:
 *
 *   - Made here — the files this conversation's turns wrote, newest first, one
 *     per path. Reported up by `LanePanel` (`onArtifactsChange`) from the same
 *     rows its cards render, including writes that land live mid-turn. No read
 *     of its own. Opening one follows the one file-open rule `ArtifactCard`
 *     follows (ADR-438): an owned format opens in its app, anything else in
 *     `FileOpenModal`, in place.
 *   - Runs — `useRuns` filtered to this conversation AND to `trigger !==
 *     'chat'`. A chat turn's own steps already render inline in the turn
 *     (ADR-666 D7); listing that run here too would be the second rendering D7
 *     forbids. What remains is work this conversation set going that runs
 *     outside a turn — a Run now, a scheduled browser run taken up here.
 *     Rendered by `RunView`, the one rendering of a run.
 *
 * With both absent the side says one sentence rather than folding away, so the
 * conversation does not jump when the first file lands.
 *
 * REFUSED, so no one adds them (ADR-670 D3): a numbered plan (no plan
 * primitive exists — a UI-invented checklist is a claim without a receipt), a
 * reach panel (ADR-644: one reach structure, rendered at Reach), and a copy of
 * the turn's steps.
 */

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { FileIcon } from '@/components/workspace/FileIcon';
import { FileOpenModal } from '@/components/chat-surface/FileOpenModal';
import type { MadeHereFile } from '@/components/chat-surface/LanePanel';
import { RunView } from '@/components/runs/RunView';
import { knownKind, resolveSurfaceApplication } from '@/lib/file-types';
import { useRuns } from '@/lib/runs/useRuns';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';

export function ChatSupervision({
  laneId,
  files,
}: {
  laneId: string;
  /** What this conversation's turns wrote, newest first — from `LanePanel`. */
  files: MadeHereFile[];
}) {
  const t = useTranslations('chat.supervision');
  const { runs, refresh } = useRuns();
  const { navigateToSurface, userId } = useSurfacePreferences();
  const [opening, setOpening] = useState<string | null>(null);

  // ADR-666 D7 — a chat-triggered run's steps are already in its turn.
  const laneRuns = useMemo(
    () => (runs ?? []).filter((r) => r.lane_id === laneId && r.trigger !== 'chat'),
    [runs, laneId],
  );

  // The one file-open rule, as `ArtifactCard` applies it: an owned format
  // opens in its app, everything else in its own frame, here.
  const open = (path: string) => {
    const owningApp = resolveSurfaceApplication(path, undefined, knownKind(path));
    if (owningApp) navigateToSurface(owningApp.surface, { [owningApp.param]: path });
    else setOpening(path);
  };

  const openWork = (topic: string, start = false) =>
    navigateToSurface('supervisor', { work: topic, ...(start ? { start: '1' } : {}) });

  if (files.length === 0 && laneRuns.length === 0) {
    return (
      <p className="px-4 py-6 text-xs leading-relaxed text-muted-foreground">{t('empty')}</p>
    );
  }

  return (
    <div className="space-y-5 px-3 py-3">
      {files.length > 0 && (
        <section>
          <h3 className="mb-1.5 px-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            {t('madeHere')}
          </h3>
          <ul>
            {files.map((f) => {
              const name = f.path.split('/').pop() || f.path;
              const rel = f.path.replace(/^\/workspace\//, '');
              return (
                <li key={f.path}>
                  <button
                    type="button"
                    onClick={() => open(f.path)}
                    title={rel}
                    className="flex w-full items-start gap-2 rounded-md px-1 py-1.5 text-left transition-colors hover:bg-muted"
                  >
                    <FileIcon filename={name} size="sm" />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[13px] text-foreground">{name}</span>
                      <span className="block truncate text-[10px] text-muted-foreground">{rel}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      {laneRuns.length > 0 && (
        <section>
          <h3 className="mb-1.5 px-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            {t('runs')}
          </h3>
          <ul className="space-y-2">
            {laneRuns.map((r) => (
              <li key={r.id}>
                <RunView
                  run={r}
                  viewerId={userId}
                  compact
                  onOpen={(run) => run.topic && openWork(run.topic)}
                  onRunIt={(run) => run.topic && openWork(run.topic, true)}
                  onOpenFile={open}
                  onChanged={() => void refresh()}
                />
              </li>
            ))}
          </ul>
        </section>
      )}

      {opening && <FileOpenModal path={opening} onClose={() => setOpening(null)} />}
    </div>
  );
}
