'use client';

/**
 * KernelRecentArtifacts — Home slot #5 (ADR-312).
 *
 * Kernel-universal: renders for EVERY workspace from kernel substrate
 * (delivered task outputs in `workspace_files` under
 * /workspace/operation/reports/{slug}/{date}/output.md), independent of the active
 * program. Programs do NOT declare this slot.
 *
 * ADR-329 cleanup (2026-06-08): this is the *delivered-outputs* glance —
 * the report face — deliberately DISTINCT from the Files "Recently
 * authored" feed (substrate changes / who-authored-what, ADR-329 D2).
 * The depth lives on Files now; Home keeps only a thin glance + a pointer.
 * Limit reduced 5 → 3; "All" points at the authored-substrate recency view
 * on Files (the canonical "what changed in my workspace" surface).
 *
 * Self-hides when the workspace has produced nothing yet — the cold-start
 * Home stays honest.
 */

import { useEffect, useState } from 'react';
import { FileText, ArrowRight } from 'lucide-react';
import { SurfaceLink } from '@/components/shell/SurfaceLink';
import { api } from '@/lib/api/client';
import { formatRelativeTime } from '@/lib/formatting';

// A glance, not the recency surface — the full authored-substrate history
// lives on Files (ADR-329 D2). Home shows just the top few delivered outputs.
const COMPACT_LIMIT = 3;

interface Artifact {
  slug: string;
  date: string;
  path: string;
  summary: string | null;
  updated_at: string | null;
}

interface KernelRecentArtifactsProps {
  /**
   * ADR-312 home-bundle: pre-fetched delivered outputs from the Home's single
   * bundled call. When present the slot skips its self-fetch; standalone
   * mounts omit it and self-fetch.
   */
  initialArtifacts?: Artifact[];
}

export function KernelRecentArtifacts({ initialArtifacts }: KernelRecentArtifactsProps = {}) {
  const [artifacts, setArtifacts] = useState<Artifact[] | null>(
    initialArtifacts ?? null,
  );

  useEffect(() => {
    if (initialArtifacts !== undefined) {
      setArtifacts(initialArtifacts);
      return;
    }
    let cancelled = false;
    api.workspace
      .recentArtifacts(COMPACT_LIMIT)
      .then((r) => {
        if (!cancelled) setArtifacts(r.artifacts);
      })
      .catch(() => {
        if (!cancelled) setArtifacts([]);
      });
    return () => {
      cancelled = true;
    };
  }, [initialArtifacts]);

  if (!artifacts || artifacts.length === 0) return null;

  return (
    <section
      aria-label="Recent artifacts"
      className="rounded-lg border border-border/60 bg-card/50"
    >
      <header className="flex items-center justify-between px-4 py-2.5 border-b border-border/40">
        <div className="flex items-center gap-2">
          <FileText className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <h2 className="text-sm font-medium text-foreground">Recently delivered</h2>
        </div>
        {/* ADR-329: the depth lives on Files now. "All" points at the
            authored-substrate recency view (Files), not a stale reports
            path. Fixes the prior /workspace/reports deep-link — the
            substrate moved to /workspace/operation/reports per ADR-231 D2. */}
        <SurfaceLink
          to="files"
          className="inline-flex items-center gap-1 text-[11px] text-muted-foreground/70 hover:text-foreground transition-colors"
        >
          View in Files <ArrowRight className="h-3 w-3" />
        </SurfaceLink>
      </header>
      <ul className="divide-y divide-border/30">
        {artifacts.map((a) => (
          <li key={a.path}>
            <SurfaceLink
              to="recurrence"
              params={{ task: a.slug }}
              className="flex items-center gap-3 px-4 py-2.5 hover:bg-muted/40 transition-colors"
            >
              {/* Backend returns a clean human title (path/machine prefixes
                  stripped); render it as the single line. */}
              <span className="flex-1 min-w-0 text-sm text-foreground truncate">
                {a.summary?.trim() || a.slug}
              </span>
              {a.updated_at && (
                <span className="text-[11px] text-muted-foreground/50 shrink-0 tabular-nums">
                  {formatRelativeTime(a.updated_at)}
                </span>
              )}
            </SurfaceLink>
          </li>
        ))}
      </ul>
    </section>
  );
}
