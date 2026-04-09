'use client';

/**
 * TrackingMiddle — Detail middle band for `output_kind: accumulates_context`.
 *
 * ADR-167 v5: the last-run CHANGELOG markdown is wrapped in a bordered,
 * inset card for consistency with DeliverableMiddle. The "nested document"
 * pattern applies to any task-produced markdown content — the card frame
 * visually scopes the content as "a document the task produced," keeping
 * its internal headers subordinate to the task's real H1 in
 * SurfaceIdentityHeader above.
 *
 * For tasks like track-competitors, slack-digest, github-digest — the
 * artifact is NOT a rendered output. It's the context domain folder the
 * task writes to. The user wants to know:
 *
 *   1. Which domain(s) does this task feed?
 *   2. When did it last grow? (last_run_at)
 *   3. What changed in the last run? (CHANGELOG from outputs/{date}/output.md)
 *   4. Take me to the domain itself.
 *
 * The "latest output" for a context task is a CHANGELOG of what was added.
 * We render it inline inside a nested card, plus link out to the domain.
 */

import Link from 'next/link';
import { AlertCircle, FolderOpen, Layers, Loader2, RefreshCw } from 'lucide-react';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { useTaskOutputs } from '@/hooks/useTaskOutputs';
import { CONTEXT_ROUTE } from '@/lib/routes';
import type { Task } from '@/types';

export function TrackingMiddle({
  task,
  refreshKey,
}: {
  task: Task;
  refreshKey: number;
}) {
  const { latest, loading, error, reload } = useTaskOutputs(task.slug, {
    includeLatest: true,
    refreshKey,
  });

  // Primary domain = first context_writes entry that isn't `signals`
  // (signals is a cross-cutting log every track-* writes to)
  const writes = task.context_writes ?? [];
  const primaryDomain = writes.find(d => d !== 'signals') ?? writes[0] ?? null;
  const otherDomains = writes.filter(d => d !== primaryDomain);

  return (
    <>
      {/* Domain status block */}
      <div className="px-6 py-4 border-b border-border/40">
        <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/40 mb-2">
          Context Domain
        </h3>
        {primaryDomain ? (
          <div className="space-y-2">
            <Link
              href={`${CONTEXT_ROUTE}?domain=${primaryDomain}`}
              className="inline-flex items-center gap-2 text-sm font-medium text-primary hover:underline"
            >
              <FolderOpen className="w-4 h-4" />
              /workspace/context/{primaryDomain}/
            </Link>
            {otherDomains.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
                <Layers className="w-3 h-3" />
                <span>Also writes to:</span>
                {otherDomains.map(d => (
                  <Link
                    key={d}
                    href={`${CONTEXT_ROUTE}?domain=${d}`}
                    className="hover:text-foreground hover:underline"
                  >
                    {d}
                  </Link>
                ))}
              </div>
            )}
            <p className="text-xs text-muted-foreground/70">
              This task accumulates context — its work lives in the domain folder above,
              not as a rendered report. Click through to browse what's been collected.
            </p>
          </div>
        ) : (
          <p className="text-xs text-muted-foreground/60">
            No context domain configured for this task.
          </p>
        )}
      </div>

      {/* Last-run CHANGELOG in a nested card */}
      <div className="px-6 py-4">
        <div className="flex items-center gap-2 mb-2">
          <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/40">Last run summary</h3>
          {latest?.date && (
            <>
              <span className="text-muted-foreground/30 text-[10px]">·</span>
              <span className="text-[10px] text-muted-foreground/60">{latest.date}</span>
            </>
          )}
        </div>
        <div className="rounded-lg border border-border bg-muted/5 overflow-hidden">
          <div className="max-h-[400px] overflow-auto p-5">
            {loading ? (
              <div className="flex items-center justify-center py-2">
                <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
              </div>
            ) : error ? (
              <div className="text-center">
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
              <div className="prose prose-sm max-w-none dark:prose-invert">
                <MarkdownRenderer content={latest.content ?? latest.md_content ?? ''} />
              </div>
            ) : (
              <p className="text-xs text-muted-foreground/60">
                No run summary yet. After the first run, you'll see what was added or updated here.
              </p>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
