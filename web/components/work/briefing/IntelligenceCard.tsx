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
 * ADR-204 Phase 2 — Lazy refresh:
 *   On load, if sys_manifest.created_at is older than 6 hours, silently
 *   trigger a background re-run and reload when it completes. Existing
 *   (stale) content remains visible during the refresh.
 *
 * Empty states:
 *   - No output yet (day-zero or first run pending): warming-up placeholder
 *   - Load error: non-fatal, shows retry
 */

import { useEffect, useState } from 'react';
import { Brain, Loader2, RefreshCw } from 'lucide-react';
import { api } from '@/lib/api/client';
import { TaskOutputCard } from '@/components/work/details/DeliverableMiddle';
import { useTaskOutputs } from '@/hooks/useTaskOutputs';

const STALE_THRESHOLD_MS = 6 * 60 * 60 * 1000; // 6 hours

export function IntelligenceCard({ refreshKey }: { refreshKey?: number }) {
  const { latest, loading, error, reload } = useTaskOutputs('maintain-overview', {
    includeLatest: true,
    refreshKey: refreshKey ?? 0,
  });
  const [isRefreshing, setIsRefreshing] = useState(false);

  // ADR-204 Phase 2: Lazy refresh — if sys_manifest.created_at > 6h, trigger
  // background re-execution so the next Overview load sees fresh output.
  // Fires once after the initial load resolves. Silent failure — stale content
  // is always better than a broken card.
  useEffect(() => {
    if (loading || isRefreshing || !latest) return;

    const sysManifest = latest.sys_manifest as Record<string, unknown> | undefined;
    const createdAt = sysManifest?.created_at as string | undefined;
    if (!createdAt) return;

    const ageMs = Date.now() - new Date(createdAt).getTime();
    if (ageMs <= STALE_THRESHOLD_MS) return;

    setIsRefreshing(true);
    void api.tasks
      .run('maintain-overview')
      .then(() => reload())
      .catch(() => {})
      .finally(() => setIsRefreshing(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading]); // only re-check when loading state changes (i.e., on initial load)

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
        {isRefreshing && (
          <>
            <span className="text-muted-foreground/30 text-[10px]">·</span>
            <Loader2 className="h-3 w-3 animate-spin text-muted-foreground/40" />
            <span className="text-[10px] text-muted-foreground/40">Updating</span>
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
