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

import { useState } from 'react';
import Link from 'next/link';
import { AlertCircle, ChevronDown, ChevronRight, FolderOpen, Layers, Loader2, RefreshCw, Shield } from 'lucide-react';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { useTaskOutputs } from '@/hooks/useTaskOutputs';
import { CONTEXT_ROUTE } from '@/lib/routes';
import type { DeliverableSpec, Task } from '@/types';

// Quality Contract panel for context-driven tasks — context-shaped copy
function QualityContractPanel({ spec }: { spec: DeliverableSpec }) {
  const [open, setOpen] = useState(false);
  const hasContent = spec.quality_criteria?.length || spec.expected_output;
  if (!hasContent) return null;

  return (
    <div className="px-6 pb-2">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex w-full items-center gap-1.5 text-[10px] text-muted-foreground/50 hover:text-muted-foreground transition-colors"
      >
        <Shield className="h-3 w-3" />
        <span className="uppercase tracking-wide font-medium">Data Contract</span>
        {open ? <ChevronDown className="h-3 w-3 ml-auto" /> : <ChevronRight className="h-3 w-3 ml-auto" />}
      </button>

      {open && (
        <div className="mt-2 rounded-md border border-border bg-muted/5 p-3 space-y-3 text-xs">
          {spec.expected_output && (
            <div>
              <p className="text-[10px] font-medium text-muted-foreground/50 uppercase tracking-wide mb-1">Context Structure</p>
              <div className="space-y-0.5 text-muted-foreground">
                {spec.expected_output.paths && <p>Paths: {spec.expected_output.paths}</p>}
                {spec.expected_output.format && <p>Output: {spec.expected_output.format}</p>}
              </div>
            </div>
          )}
          {spec.quality_criteria?.length ? (
            <div>
              <p className="text-[10px] font-medium text-muted-foreground/50 uppercase tracking-wide mb-1">Data Quality Criteria</p>
              <ul className="space-y-0.5 text-muted-foreground list-none">
                {spec.quality_criteria.map((c, i) => (
                  <li key={i} className="flex gap-1.5"><span className="text-muted-foreground/30 flex-shrink-0">–</span>{c}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {spec.audience && (
            <div>
              <p className="text-[10px] font-medium text-muted-foreground/50 uppercase tracking-wide mb-1">Feeds</p>
              <p className="text-muted-foreground">{spec.audience}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function TrackingMiddle({
  task,
  refreshKey,
  deliverableSpec,
}: {
  task: Task;
  refreshKey: number;
  deliverableSpec?: DeliverableSpec | null;
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
        <h3 className="text-[11px] font-medium text-muted-foreground/60 mb-2">
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

      {/* ADR-178 Phase 6: Data Contract — collapsible quality spec for context tasks */}
      {deliverableSpec && <QualityContractPanel spec={deliverableSpec} />}

      {/* Last-run CHANGELOG in a nested card */}
      <div className="px-6 py-4">
        <div className="flex items-center gap-2 mb-2">
          <h3 className="text-[11px] font-medium text-muted-foreground/60">Last run summary</h3>
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
