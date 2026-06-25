'use client';

/**
 * HomeRecents — the Home front page's VISUAL re-representation of the Files
 * "Recents" (ADR-369 §D4 slot #3 + §D6).
 *
 * The operator's home-home direction: after "what needs my OK" (the decision
 * queue), the front page shows "what's been happening" — a card/visual glance
 * of recent attributed substrate changes, richer than the Files surface's
 * columnar table. Same DATA SOURCE as the Files Recents (the ADR-209 revision
 * chain via GET /api/workspace/recent-revisions, `api.workspace.recentRevisions`)
 * — Singular Implementation: one recency feed, two presentations (the Files
 * columnar table for the explorer; these cards for the front-page glance).
 *
 * DISTINCT from KernelRecentArtifacts (ADR-369 §D6): Recents = broad recent
 * *substrate changes* (who wrote what across the whole workspace); recent
 * artifacts = the narrow set of *delivered outputs* (the "dividends"). They are
 * two sections on the Home tab, never merged — merging would hide the "what did
 * the operation ship" signal inside "what changed".
 *
 * Self-hiding (kernel-slot contract): renders nothing when there are no recent
 * changes yet (honest cold-start Home).
 *
 * Rows deep-link into the Files surface at the changed path (the Recents
 * presentation glances; the explorer is where you dwell).
 */

import { useEffect, useState } from 'react';
import { History, Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import { SurfaceLink } from '@/components/shell/SurfaceLink';
import { formatRelativeTime } from '@/lib/formatting';

interface Revision {
  path: string;
  authored_by: string | null;
  message: string | null;
  created_at: string | null;
}

// authored_by taxonomy → operator-facing label (ADR-209). Kept identical to
// the Files RecentRevisions + ContentViewer mapping — small + stable, avoids a
// cross-surface import dependency.
function formatAuthorLabel(authored_by: string | null | undefined): string {
  if (!authored_by) return 'System';
  if (authored_by === 'operator') return 'You';
  if (authored_by.startsWith('yarnnn:')) return 'YARNNN';
  if (authored_by.startsWith('agent:')) return `Agent (${authored_by.slice('agent:'.length)})`;
  if (authored_by.startsWith('specialist:')) return 'Specialist';
  if (authored_by.startsWith('reviewer:')) return 'Reviewer';
  if (authored_by.startsWith('system:')) return 'System';
  return 'System';
}

// Author-class accent — a quiet dot, not a loud badge (who, at a glance).
function authorAccent(authored_by: string | null | undefined): string {
  const label = formatAuthorLabel(authored_by);
  switch (label) {
    case 'You': return 'bg-primary';
    case 'Reviewer': return 'bg-rose-400';
    case 'YARNNN': return 'bg-sky-400';
    default: return 'bg-muted-foreground/40';
  }
}

function fileName(path: string): string {
  return path.split('/').filter(Boolean).pop() || path;
}

// "Where" — the substrate section the file lives in. Strips the leading
// /workspace/ so it reads "operation/reports/weekly", not the absolute path.
function whereLabel(path: string): string {
  const parts = path.split('/').filter(Boolean);
  const dirs = parts.slice(0, -1);
  if (dirs[0] === 'workspace') dirs.shift();
  return dirs.join('/');
}

export function HomeRecents() {
  const [revisions, setRevisions] = useState<Revision[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        // A front-page glance, not the full feed — fewer rows than the Files
        // explorer table (which loads 30).
        const result = await api.workspace.recentRevisions(8);
        if (!cancelled) setRevisions(Array.isArray(result?.revisions) ? result.revisions : []);
      } catch {
        if (!cancelled) setRevisions([]);
      } finally {
        if (!cancelled) setLoaded(true);
      }
    };
    load();
    const interval = setInterval(load, 30000);
    const onFocus = () => { if (document.visibilityState === 'visible') load(); };
    document.addEventListener('visibilitychange', onFocus);
    return () => {
      cancelled = true;
      clearInterval(interval);
      document.removeEventListener('visibilitychange', onFocus);
    };
  }, []);

  // Self-hiding: nothing to show yet (or still loading the first batch) →
  // render nothing. The cold-start Home stays honest (ADR-312 D2 contract).
  if (!loaded || revisions.length === 0) {
    if (!loaded) {
      return (
        <section aria-label="Recents" className="flex items-center gap-2 px-1 py-2 text-xs text-muted-foreground">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Loading recent changes…
        </section>
      );
    }
    return null;
  }

  return (
    <section aria-label="Recents">
      <div className="mb-2 flex items-center gap-2">
        <History className="h-4 w-4 text-muted-foreground" />
        <h2 className="text-sm font-medium text-foreground">Recents</h2>
        <span className="text-[11px] text-muted-foreground">recent changes across your workspace</span>
      </div>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {revisions.map((rev, i) => (
          <SurfaceLink
            key={`${rev.path}-${rev.created_at}-${i}`}
            to="files"
            params={{ path: rev.path }}
            className="group flex flex-col items-start gap-1.5 rounded-lg border border-border/60 bg-card/50 px-3.5 py-3 text-left transition-colors hover:border-border hover:bg-card"
            title={rev.path}
          >
            <span className="flex w-full items-center gap-2">
              <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${authorAccent(rev.authored_by)}`} />
              <span className="min-w-0 flex-1 truncate text-sm font-medium text-foreground">
                {fileName(rev.path)}
              </span>
              <span className="shrink-0 text-[11px] text-muted-foreground/80">
                {rev.created_at ? formatRelativeTime(rev.created_at) : ''}
              </span>
            </span>
            <span className="flex w-full items-center justify-between gap-2">
              <span className="min-w-0 truncate text-[11px] text-muted-foreground">{whereLabel(rev.path)}</span>
              <span className="shrink-0 text-[11px] text-muted-foreground/70">
                {formatAuthorLabel(rev.authored_by)}
              </span>
            </span>
          </SurfaceLink>
        ))}
      </div>
    </section>
  );
}
