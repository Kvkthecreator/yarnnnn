'use client';

/**
 * ActionMiddle — Detail middle band for `output_kind: external_action`.
 *
 * ADR-167: For tasks like slack-respond and notion-update — the artifact is
 * NOT a workspace file. The task composes a message and writes it to a
 * third-party platform via API. The user wants to know:
 *
 *   1. When did this task fire? (run history)
 *   2. What was the target? (which Slack channel, which Notion page)
 *   3. Did it succeed? (delivery status)
 *   4. What did it post? (sent message text, if available)
 *
 * Data sources:
 *   - api.recurrences.listOutputs(slug) → one row per fire, with manifest + sent text
 *   - task.delivery / task.objective → fallback display of intended target
 *
 * No iframe — there is no rendered HTML deliverable. The artifact lives on
 * the third-party platform; we link out where possible.
 */

import { AlertCircle, CheckCircle2, ExternalLink, Loader2, RefreshCw, Send } from 'lucide-react';
import { formatRelativeTime } from '@/lib/formatting';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { useTaskOutputs } from '@/hooks/useTaskOutputs';
import { PlatformSourcesSection } from './PlatformSourcesSection';
import type { Task } from '@/types';

export function ActionMiddle({
  task,
  refreshKey,
  onSourcesUpdated,
}: {
  task: Task;
  refreshKey: number;
  onSourcesUpdated?: () => void;
}) {
  const { latest, history: outputs, loading, error, reload } = useTaskOutputs(task.slug, {
    includeLatest: true,
    historyLimit: 10,
    refreshKey,
  });

  return (
    <>
      {/* Platform source picker — for slack-respond, notion-update: which channel/page to read from */}
      <PlatformSourcesSection task={task} onSourcesUpdated={onSourcesUpdated} />

      {/* Action target block */}
      <div className="px-6 py-4 border-b border-border/40">
        <h3 className="text-[11px] font-medium text-muted-foreground/60 mb-2">
          Action Target
        </h3>
        <div className="flex items-center gap-2 text-sm">
          <Send className="w-4 h-4 text-muted-foreground" />
          <span className="text-muted-foreground">
            {task.delivery && task.delivery !== 'none'
              ? task.delivery
              : task.objective?.audience || 'Configured via task sources'}
          </span>
        </div>
        <p className="mt-2 text-xs text-muted-foreground/70">
          This task takes an action on an external platform. Each fire posts a
          message to the target above. The artifact lives on the platform —
          there is no workspace output file.
        </p>
      </div>

      {/* Latest payload */}
      <div className="px-6 py-4 border-b border-border/40">
        <h3 className="text-[11px] font-medium text-muted-foreground/60 mb-2">
          Latest payload
        </h3>
        {loading ? (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <div className="text-center py-2">
            <AlertCircle className="mx-auto mb-2 h-5 w-5 text-destructive/70" />
            <p className="text-xs text-muted-foreground">{error}</p>
            <button
              onClick={() => void reload()}
              className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              <RefreshCw className="h-3 w-3" />
              Retry
            </button>
          </div>
        ) : latest && (latest.content || latest.md_content) ? (
          <div className="rounded-lg border border-border bg-muted/5 overflow-hidden">
            <div className="max-h-[240px] overflow-auto p-5">
              <div className="prose prose-sm max-w-none dark:prose-invert">
                <MarkdownRenderer content={latest.content ?? latest.md_content ?? ''} />
              </div>
            </div>
          </div>
        ) : (
          <p className="text-xs text-muted-foreground/60">
            No payload preview is available for the most recent fire.
          </p>
        )}
      </div>

      {/* Action history */}
      <div className="px-6 py-4">
        <h3 className="text-[11px] font-medium text-muted-foreground/60 mb-2">
          Action history <span className="text-muted-foreground/30">· most recent first</span>
        </h3>
        <div className="max-h-[400px] overflow-auto">
          {loading ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
            </div>
          ) : error ? (
            <div className="text-center py-2">
              <AlertCircle className="mx-auto mb-2 h-5 w-5 text-destructive/70" />
              <p className="text-xs text-muted-foreground">{error}</p>
            </div>
          ) : outputs.length === 0 ? (
            <p className="text-xs text-muted-foreground/60 py-2">
              No fires yet. Use the Fire button above or ask YARNNN to trigger this action.
            </p>
          ) : (
            <ul className="divide-y divide-border/40">
              {outputs.map(o => {
                const ok = o.status === 'active' || o.status === 'completed' || o.status === 'delivered';
                const externalUrl =
                  (o.manifest as Record<string, unknown> | undefined)?.delivery_external_url as string | undefined;
                return (
                  <li key={o.folder} className="py-2 flex items-start gap-2">
                    {ok ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-green-500 shrink-0 mt-0.5" />
                    ) : (
                      <AlertCircle className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="text-xs text-foreground">
                        {o.date}
                        <span className="text-muted-foreground/40 ml-1.5">
                          ({formatRelativeTime(o.date)})
                        </span>
                      </div>
                      {externalUrl && (
                        <a
                          href={externalUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-[11px] text-primary hover:underline mt-0.5"
                        >
                          View on platform <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                    <span className="text-[10px] text-muted-foreground/50 shrink-0 capitalize">
                      {o.status}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>
    </>
  );
}
