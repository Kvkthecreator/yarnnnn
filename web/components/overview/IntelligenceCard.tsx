'use client';

/**
 * IntelligenceCard — fourth pane on Overview (ADR-204).
 *
 * Renders the latest output of the `maintain-overview` task as the
 * Workspace Intelligence Cockpit. Uses the same TaskOutputCard primitive
 * as DeliverableMiddle so iframe auto-height, SectionProvenanceStrip,
 * and markdown fallback are shared — no duplicate logic.
 *
 * ADR-198 I2 amendment: this is not "foreign substrate" — maintain-overview
 * is a purpose-built artifact for Overview's exclusive consumption
 * (delivery: none, sole consumer this surface). I2 passes.
 *
 * Empty states:
 *   - No output yet (day-zero or first run pending): warming-up placeholder
 *   - Load error: non-fatal, shows retry
 */

import { Brain, Loader2, RefreshCw } from 'lucide-react';
import { TaskOutputCard } from '@/components/work/details/DeliverableMiddle';
import { useTaskOutputs } from '@/hooks/useTaskOutputs';

export function IntelligenceCard({ refreshKey }: { refreshKey?: number }) {
  const { latest, loading, error, reload } = useTaskOutputs('maintain-overview', {
    includeLatest: true,
    refreshKey: refreshKey ?? 0,
  });

  const hasOutput = latest && (latest.html_content || latest.content || latest.md_content);

  return (
    <div className="rounded-xl border border-border bg-card">
      {/* Header */}
      <div className="flex items-center gap-2 px-6 py-4 border-b border-border/40">
        <Brain className="h-4 w-4 text-muted-foreground/50" />
        <h2 className="text-sm font-semibold text-foreground">Workspace Intelligence</h2>
        {latest?.date && (
          <>
            <span className="text-muted-foreground/30 text-[10px]">·</span>
            <span className="text-[10px] text-muted-foreground/50">{latest.date}</span>
          </>
        )}
      </div>

      {/* Body */}
      {loading ? (
        <div className="flex items-center justify-center py-10">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground/40" />
        </div>
      ) : error ? (
        <div className="px-6 py-8 text-center">
          <p className="text-xs text-muted-foreground/60 mb-3">{error}</p>
          <button
            onClick={() => void reload()}
            className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <RefreshCw className="h-3 w-3" /> Retry
          </button>
        </div>
      ) : !hasOutput ? (
        <div className="px-6 py-8 text-center">
          <Brain className="w-6 h-6 text-muted-foreground/15 mx-auto mb-2" />
          <p className="text-xs text-muted-foreground/60">
            Synthesis pending — runs at 06:00 as your workspace accumulates knowledge.
          </p>
        </div>
      ) : (
        <div className="pt-3">
          <TaskOutputCard
            htmlContent={latest.html_content}
            mdContent={latest.content ?? latest.md_content}
            sections={latest.sections}
            taskSlug="maintain-overview"
            showProvenance={true}
          />
        </div>
      )}
    </div>
  );
}
