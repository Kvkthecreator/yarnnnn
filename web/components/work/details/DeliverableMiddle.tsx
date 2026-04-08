'use client';

/**
 * DeliverableMiddle — Detail middle band for `output_kind: produces_deliverable`.
 *
 * ADR-167: This is the original WorkDetail.OutputPreview, extracted unchanged.
 * It renders the latest `/tasks/{slug}/outputs/{date}/output.html` (iframe) or
 * `output.md` (markdown). For tasks like daily-update, market-report, and
 * competitive-brief — the artifact IS the rendered output.
 *
 * The other three output kinds get their own middle components because their
 * centerpiece data lives elsewhere (context domains, agent_runs, hygiene logs).
 */

import { useEffect, useState } from 'react';
import { Loader2, FileText } from 'lucide-react';
import { api } from '@/lib/api/client';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import type { TaskOutput } from '@/types';

export function DeliverableMiddle({ taskSlug }: { taskSlug: string }) {
  const [loading, setLoading] = useState(true);
  const [latest, setLatest] = useState<TaskOutput | null>(null);

  useEffect(() => {
    setLoading(true);
    setLatest(null);
    api.tasks.getLatestOutput(taskSlug)
      .then(result => setLatest(result))
      .catch(() => setLatest(null))
      .finally(() => setLoading(false));
  }, [taskSlug]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!latest || (!latest.html_content && !latest.content)) {
    return (
      <div className="px-5 py-8 text-center">
        <FileText className="w-6 h-6 text-muted-foreground/15 mx-auto mb-2" />
        <p className="text-xs text-muted-foreground/60">
          No output yet. This task will produce its first output on its next run.
        </p>
      </div>
    );
  }

  return (
    <div className="border-b border-border/40">
      <div className="px-5 py-2 text-[11px] text-muted-foreground/60 flex items-center gap-2">
        <span>Latest output</span>
        {latest.date && (
          <>
            <span className="text-muted-foreground/30">·</span>
            <span>{latest.date}</span>
          </>
        )}
      </div>
      <div className="min-h-[300px] max-h-[600px] overflow-auto">
        {latest.html_content ? (
          <iframe
            srcDoc={latest.html_content}
            className="h-[600px] w-full border-0 bg-white"
            sandbox="allow-same-origin allow-scripts"
            title={`${taskSlug} output`}
          />
        ) : (
          <div className="p-5">
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <MarkdownRenderer content={latest.content ?? ''} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
