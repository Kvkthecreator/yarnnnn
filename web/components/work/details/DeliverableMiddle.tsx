'use client';

/**
 * DeliverableMiddle — Detail middle band for `output_kind: produces_deliverable`.
 *
 * ADR-167 v5: the output (iframe or rendered markdown) is wrapped in a
 * bordered, visually inset card. This is the "nested document" pattern —
 * the card frame tells the user "this is a document the task produced,"
 * which keeps whatever H1 lives inside the output (e.g. daily-update's
 * `<h1>Daily Workspace Update — April 8, 2026</h1>`) from competing with
 * the task's real H1 above (SurfaceIdentityHeader's `task.title`).
 *
 * For tasks like daily-update, market-report, and competitive-brief — the
 * artifact IS the rendered output. This middle renders it framed as a
 * document-within-a-page.
 */

import { AlertCircle, FileText, Loader2, RefreshCw } from 'lucide-react';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { useTaskOutputs } from '@/hooks/useTaskOutputs';

export function DeliverableMiddle({
  taskSlug,
  refreshKey,
}: {
  taskSlug: string;
  refreshKey: number;
}) {
  const { latest, loading, error, reload } = useTaskOutputs(taskSlug, {
    includeLatest: true,
    refreshKey,
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-6 py-8 text-center">
        <AlertCircle className="mx-auto mb-2 h-6 w-6 text-destructive/70" />
        <p className="text-sm font-medium text-foreground">Failed to load output</p>
        <p className="mt-1 text-xs text-muted-foreground">{error}</p>
        <button
          onClick={() => void reload()}
          className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <RefreshCw className="h-3 w-3" />
          Retry
        </button>
      </div>
    );
  }

  if (!latest || (!latest.html_content && !latest.content && !latest.md_content)) {
    return (
      <div className="px-6 py-8 text-center">
        <FileText className="w-6 h-6 text-muted-foreground/15 mx-auto mb-2" />
        <p className="text-xs text-muted-foreground/60">
          No output yet. This task will produce its first output on its next run.
        </p>
      </div>
    );
  }

  return (
    <div className="px-6 py-4">
      <div className="flex items-center gap-2 mb-2">
        <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/40">Latest output</h3>
        {latest.date && (
          <>
            <span className="text-muted-foreground/30 text-[10px]">·</span>
            <span className="text-[10px] text-muted-foreground/60">{latest.date}</span>
          </>
        )}
      </div>
      <div className="rounded-lg border border-border bg-muted/5 overflow-hidden">
        {latest.html_content ? (
          <iframe
            srcDoc={latest.html_content}
            className="h-[600px] w-full border-0 bg-white"
            sandbox="allow-same-origin allow-scripts"
            title={`${taskSlug} output`}
          />
        ) : (
          <div className="max-h-[600px] overflow-auto p-5">
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <MarkdownRenderer content={latest.content ?? latest.md_content ?? ''} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
