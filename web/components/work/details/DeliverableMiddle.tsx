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
 * ADR-170: When sys_manifest.json is present (compose substrate), shows a
 * section provenance strip above the output. Each pill = one declared section,
 * color-coded by freshness. TP can target individual sections via:
 *   ManageTask(action="steer", target_section="executive-summary")
 */

import { AlertCircle, Clock, FileText, Loader2, RefreshCw } from 'lucide-react';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { useTaskOutputs } from '@/hooks/useTaskOutputs';
import type { TaskSectionEntry } from '@/types';

// ---------------------------------------------------------------------------
// Section kind display config
// ---------------------------------------------------------------------------

const KIND_LABELS: Record<string, string> = {
  'narrative': 'prose',
  'metric-cards': 'metrics',
  'entity-grid': 'entities',
  'comparison-table': 'table',
  'trend-chart': 'chart',
  'distribution-chart': 'chart',
  'timeline': 'timeline',
  'status-matrix': 'matrix',
  'data-table': 'table',
  'callout': 'callout',
  'checklist': 'checklist',
};

function sectionFreshnessAge(producedAt: string | undefined): 'fresh' | 'stale' | 'unknown' {
  if (!producedAt) return 'unknown';
  try {
    const ms = Date.now() - new Date(producedAt).getTime();
    const hours = ms / (1000 * 60 * 60);
    if (hours < 25) return 'fresh';
    if (hours < 72) return 'stale';
    return 'stale';
  } catch {
    return 'unknown';
  }
}

function SectionPill({ section }: { section: TaskSectionEntry }) {
  const age = sectionFreshnessAge(section.produced_at);
  const kindLabel = section.kind ? (KIND_LABELS[section.kind] ?? section.kind) : null;

  const dotColor =
    age === 'fresh' ? 'bg-emerald-400/70' :
    age === 'stale' ? 'bg-amber-400/70' :
    'bg-muted-foreground/30';

  return (
    <div className="flex items-center gap-1.5 rounded-md border border-border bg-background px-2.5 py-1 text-[10px] leading-none">
      <span className={`h-1.5 w-1.5 rounded-full flex-shrink-0 ${dotColor}`} />
      <span className="text-foreground font-medium">{section.title ?? section.slug}</span>
      {kindLabel && (
        <span className="text-muted-foreground/50">· {kindLabel}</span>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section provenance strip (only renders when sys_manifest sections exist)
// ---------------------------------------------------------------------------

function SectionProvenanceStrip({ sections }: { sections: TaskSectionEntry[] }) {
  if (!sections.length) return null;

  const freshCount = sections.filter(s => sectionFreshnessAge(s.produced_at) === 'fresh').length;
  const totalCount = sections.length;

  return (
    <div className="px-6 pb-2">
      <div className="flex items-center gap-2 mb-2">
        <Clock className="h-3 w-3 text-muted-foreground/40" />
        <span className="text-[10px] text-muted-foreground/50 uppercase tracking-wide">
          {freshCount}/{totalCount} sections current
        </span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {sections.map(section => (
          <SectionPill key={section.slug} section={section} />
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

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

  const hasSections = (latest.sections?.length ?? 0) > 0;

  return (
    <div className="py-4">
      <div className="flex items-center gap-2 mb-2 px-6">
        <h3 className="text-[11px] font-medium text-muted-foreground/60">Latest output</h3>
        {latest.date && (
          <>
            <span className="text-muted-foreground/30 text-[10px]">·</span>
            <span className="text-[10px] text-muted-foreground/60">{latest.date}</span>
          </>
        )}
      </div>

      {/* ADR-170: Section provenance strip — only when compose substrate has run */}
      {hasSections && (
        <SectionProvenanceStrip sections={latest.sections!} />
      )}

      <div className="px-6 pb-6">
        <div className="rounded-lg border border-border bg-muted/5 overflow-hidden">
          {latest.html_content ? (
            <iframe
              srcDoc={latest.html_content}
              className="min-h-[500px] w-full border-0 bg-white block"
              style={{ height: 'auto' }}
              onLoad={(e) => {
                const iframe = e.currentTarget;
                try {
                  const h = iframe.contentDocument?.documentElement?.scrollHeight;
                  if (h) iframe.style.height = `${h}px`;
                } catch {}
              }}
              sandbox="allow-same-origin allow-scripts"
              title={`${taskSlug} output`}
            />
          ) : (
            <div className="p-5">
              <div className="prose prose-sm max-w-none dark:prose-invert">
                <MarkdownRenderer content={latest.content ?? latest.md_content ?? ''} />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
