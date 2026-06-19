'use client';

/**
 * RecentRevisions — the Files "Recents" view (ADR-329 Amendment 2, 2026-06-19).
 *
 * The macOS-Finder-faithful workspace-wide recency view: a columnar table of
 * what the system authored in the workspace, and by whom, newest first. It is
 * the surface's EMPTY STATE — it fills the wide center pane when no node is
 * selected (replacing the bare "Select a file or folder" placeholder), exactly
 * like Finder's Recents fills the main pane until you open a file.
 *
 * Reads the ADR-209 revision chain (workspace_file_versions) via
 * GET /api/workspace/recent-revisions. Layer-1-only (ADR-328 D6) — no
 * embeddings/search internals.
 *
 * Two complementary recency surfaces, matching Finder (Amendment 2):
 *   - Recents (THIS)        — workspace-wide "what changed while I was away."
 *                             Center pane, empty-state, columnar.
 *   - Get Info / Details    — this file's revision chain (NodeDetailsPanel).
 *                             On selection, per-node.
 * They are mutually exclusive by construction (Recents renders only when
 * nothing is selected; Details only when something is), so the Amendment-1
 * "two stacked recency views" failure cannot recur.
 *
 * Columns (Finder shape): Name · Where · Author · When. Full filenames — no
 * truncation (the prior cramped sidebar mount is deleted; the center pane has
 * room to read them). Each row deep-links into the file it changed.
 */

import { useEffect, useState, useCallback } from 'react';
import { History, Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatRelativeTime } from '@/lib/formatting';

interface Revision {
  path: string;
  authored_by: string | null;
  message: string | null;
  created_at: string | null;
}

// authored_by taxonomy → operator-facing label (ADR-209). Kept local-and-
// identical to the Files tree + ContentViewer mapping rather than imported, to
// avoid a circular dep with the page; the mapping is small and stable.
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

// "Where" — Finder shows the containing folder; we show the parent folder's
// name (the substrate section the file lives in). Strips the leading
// /workspace/ so the column reads "operation/reports/weekly" not the full
// absolute path. Empty for top-level files.
function whereLabel(path: string): string {
  const parts = path.split('/').filter(Boolean);
  // drop the filename; drop a leading "workspace" segment
  const dirs = parts.slice(0, -1);
  if (dirs[0] === 'workspace') dirs.shift();
  return dirs.join('/');
}

interface RecentRevisionsProps {
  /** Navigate to a file path (the page owns selection + URL sync). */
  onSelectPath: (path: string) => void;
}

export function RecentRevisions({ onSelectPath }: RecentRevisionsProps) {
  const [revisions, setRevisions] = useState<Revision[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const result = await api.workspace.recentRevisions(30);
      setRevisions(Array.isArray(result?.revisions) ? result.revisions : []);
    } catch {
      setRevisions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    // Refresh on the same cadence as the explorer tree (30s) + on focus.
    const interval = setInterval(load, 30000);
    const onFocus = () => { if (document.visibilityState === 'visible') load(); };
    document.addEventListener('visibilitychange', onFocus);
    return () => { clearInterval(interval); document.removeEventListener('visibilitychange', onFocus); };
  }, [load]);

  if (loading && revisions.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
        Loading…
      </div>
    );
  }

  // Cold-start honest: nothing authored yet → the original empty-state copy.
  if (!loading && revisions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center px-6">
        <History className="w-8 h-8 text-muted-foreground/40 mb-3" />
        <p className="text-sm text-muted-foreground">
          Nothing authored yet. As the system writes to your workspace, recent
          changes show here — who wrote what, and when.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-6 py-3 border-b border-border/60 shrink-0">
        <History className="w-4 h-4 text-muted-foreground shrink-0" />
        <h2 className="text-sm font-medium text-foreground">Recents</h2>
        <span className="text-[11px] text-muted-foreground">
          {revisions.length} change{revisions.length === 1 ? '' : 's'}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-background z-10">
            <tr className="border-b border-border/60 text-[11px] uppercase tracking-wide text-muted-foreground">
              <th className="text-left font-medium px-6 py-2">Name</th>
              <th className="text-left font-medium px-3 py-2 hidden md:table-cell">Where</th>
              <th className="text-left font-medium px-3 py-2">Author</th>
              <th className="text-right font-medium px-6 py-2 w-28">When</th>
            </tr>
          </thead>
          <tbody>
            {revisions.map((rev, i) => (
              <tr
                key={`${rev.path}-${rev.created_at}-${i}`}
                onClick={() => onSelectPath(rev.path)}
                className="border-b border-border/40 hover:bg-muted/40 cursor-pointer transition-colors"
                title={rev.path}
              >
                <td className="px-6 py-2">
                  <span className="flex items-center gap-2.5 min-w-0">
                    <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${authorAccent(rev.authored_by)}`} />
                    <span className="text-foreground truncate">{fileName(rev.path)}</span>
                  </span>
                </td>
                <td className="px-3 py-2 text-muted-foreground hidden md:table-cell">
                  <span className="block truncate max-w-[18rem]">{whereLabel(rev.path)}</span>
                </td>
                <td className="px-3 py-2 text-muted-foreground whitespace-nowrap">
                  {formatAuthorLabel(rev.authored_by)}
                </td>
                <td className="px-6 py-2 text-right text-muted-foreground/80 whitespace-nowrap">
                  {rev.created_at ? formatRelativeTime(rev.created_at) : ''}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
