'use client';

/**
 * IntelligenceCard — fourth pane in BriefingStrip (ADR-204 + ADR-205 F2).
 *
 * Renders the latest output of the `maintain-overview` task as the
 * Workspace Intelligence Cockpit. Uses the same TaskOutputCard primitive
 * as DeliverableMiddle so iframe auto-height, SectionProvenanceStrip,
 * and markdown fallback are shared — no duplicate logic.
 *
 * ADR-198 I2 amendment: this is not "foreign substrate" — maintain-overview
 * is a purpose-built artifact for BriefingStrip's exclusive consumption
 * (delivery: none, sole consumer this surface). I2 passes.
 *
 * ADR-215 Phase 4: silent-degrade per ADR-198 §3 Briefing invariant.
 * The task is not scaffolded at signup (ADR-206), so the 404-before-
 * first-run path is a normal empty state, not an error. Absent output
 * always renders the "Synthesis pending" placeholder. Broken HTTP (5xx,
 * network) is also absorbed into the placeholder — Briefing never
 * sprouts a Retry box inside a list surface.
 *
 * ADR-204 Phase 2 — Lazy refresh:
 *   When output exists and is >6h old, trigger a background re-run.
 *   Skipped on empty-state (nothing to refresh yet).
 */

import { useEffect, useState } from 'react';
import { Brain, Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import { TaskOutputCard } from '@/components/work/details/DeliverableMiddle';
import { useTaskOutputs } from '@/hooks/useTaskOutputs';

const STALE_THRESHOLD_MS = 6 * 60 * 60 * 1000; // 6 hours

export function IntelligenceCard({ refreshKey }: { refreshKey?: number }) {
  const { latest, loading, reload } = useTaskOutputs('maintain-overview', {
    includeLatest: true,
    refreshKey: refreshKey ?? 0,
  });
  const [isRefreshing, setIsRefreshing] = useState(false);

  // ADR-204 Phase 2: Lazy refresh — if sys_manifest.created_at > 6h, trigger
  // background re-execution. Skipped when no output exists yet (task not
  // scaffolded per ADR-206 until the operator's mandate is declared).
  // Silent failure — stale content is always better than a broken card.
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

      {/* Body. ADR-215 R4-adjacent: no Retry affordance inside Briefing.
          Missing output (404) and transient load errors both collapse into
          the "Synthesis pending" empty state — the Briefing archetype
          surfaces pointers, not error chrome. */}
      {loading ? (
        <div className="flex items-center justify-center py-10">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground/40" />
        </div>
      ) : !hasOutput ? (
        <div className="px-6 py-8 text-center">
          <Brain className="w-6 h-6 text-muted-foreground/15 mx-auto mb-2" />
          <p className="text-xs text-muted-foreground/60">
            Synthesis pending — runs daily as your workspace accumulates knowledge.
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
