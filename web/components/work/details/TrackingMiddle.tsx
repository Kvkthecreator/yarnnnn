'use client';

/**
 * TrackingMiddle — Detail middle band for `output_kind: accumulates_context`.
 *
 * ADR-167: For tasks like track-competitors, slack-digest, github-digest —
 * the artifact is NOT a rendered output. It's the context domain folder the
 * task writes to. The user wants to know:
 *
 *   1. Which domain(s) does this task feed?
 *   2. When did it last grow? (last_run_at)
 *   3. What changed in the last run? (CHANGELOG from outputs/{date}/output.md)
 *   4. Take me to the domain itself.
 *
 * The "latest output" for a context task is a CHANGELOG of what was added —
 * which entities were created, which signals were appended. We render that
 * inline if it exists, plus link out to the domain folder in /context.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Loader2, FolderOpen, Layers } from 'lucide-react';
import { api } from '@/lib/api/client';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { CONTEXT_ROUTE } from '@/lib/routes';
import type { Task, TaskOutput } from '@/types';

export function TrackingMiddle({ task }: { task: Task }) {
  const [loading, setLoading] = useState(true);
  const [latest, setLatest] = useState<TaskOutput | null>(null);

  useEffect(() => {
    setLoading(true);
    setLatest(null);
    api.tasks.getLatestOutput(task.slug)
      .then(result => setLatest(result))
      .catch(() => setLatest(null))
      .finally(() => setLoading(false));
  }, [task.slug]);

  // Primary domain = first context_writes entry that isn't `signals`
  // (signals is a cross-cutting log every track-* writes to)
  const writes = task.context_writes ?? [];
  const primaryDomain = writes.find(d => d !== 'signals') ?? writes[0] ?? null;
  const otherDomains = writes.filter(d => d !== primaryDomain);

  return (
    <div className="border-b border-border/40">
      {/* Domain status block */}
      <div className="px-5 py-4">
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

      {/* Last-run CHANGELOG (if any) */}
      <div className="border-t border-border/40">
        <div className="px-5 py-2 text-[11px] text-muted-foreground/60 flex items-center gap-2">
          <span>Last run summary</span>
          {latest?.date && (
            <>
              <span className="text-muted-foreground/30">·</span>
              <span>{latest.date}</span>
            </>
          )}
        </div>
        <div className="px-5 pb-4 max-h-[400px] overflow-auto">
          {loading ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
            </div>
          ) : latest && (latest.content || latest.md_content) ? (
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <MarkdownRenderer content={latest.content ?? latest.md_content ?? ''} />
            </div>
          ) : (
            <p className="text-xs text-muted-foreground/60 py-2">
              No run summary yet. After the first run, you'll see what was added or updated here.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
