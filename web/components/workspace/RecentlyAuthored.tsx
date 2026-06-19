'use client';

/**
 * RecentlyAuthored — the Files "Recently authored" feed (ADR-329 D2).
 *
 * The substrate-legibility view: a reverse-chronological glance of what
 * the system authored in the workspace, and by whom. Reads the ADR-209
 * revision chain (workspace_file_versions) via
 * GET /api/workspace/recent-revisions. Layer-1-only (ADR-328 D6) — no
 * embeddings/search internals.
 *
 * Distinct from Home's recent-artifacts (delivered outputs) and the
 * judgment trail (Reviewer decisions): this is the substrate *delta* —
 * any authored Layer-1 mutation, deliverable or not. It answers "what
 * changed in my workspace while I was away."
 *
 * Each entry deep-links into the file it changed (/files?path=…), where
 * ADR-329 D1's promoted provenance hero shows the full revision history.
 *
 * Collapsible — the operator can fold it to reclaim explorer space. Open
 * by default (it's the surface's "what's new" header). Self-hides when
 * there are no revisions yet (cold-start honest).
 */

import { useEffect, useState, useCallback } from 'react';
import { History, ChevronDown, ChevronRight, Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';

interface Revision {
  path: string;
  authored_by: string | null;
  message: string | null;
  created_at: string | null;
}

// Same authored_by taxonomy mapping the Files tree + ContentViewer use
// (ADR-209). Kept local-and-identical rather than imported to avoid a
// circular dep with the page; the mapping is small and stable.
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

// Author-class accent — a quiet dot, not a loud badge. Keeps the feed
// glanceable (who, at a glance) without competing with the file name.
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

function relativeTime(value: string | null): string {
  if (!value) return '';
  const then = new Date(value).getTime();
  if (Number.isNaN(then)) return '';
  const diff = Date.now() - then;
  const min = Math.floor(diff / 60000);
  if (min < 1) return 'just now';
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const d = Math.floor(hr / 24);
  if (d < 7) return `${d}d ago`;
  return new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

interface RecentlyAuthoredProps {
  /** Navigate to a file path (the page owns selection + URL sync). */
  onSelectPath: (path: string) => void;
  /** Currently-selected path, to highlight its row if present. */
  selectedPath?: string | null;
}

export function RecentlyAuthored({ onSelectPath, selectedPath }: RecentlyAuthoredProps) {
  const [revisions, setRevisions] = useState<Revision[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(true);

  const load = useCallback(async () => {
    try {
      const result = await api.workspace.recentRevisions(15);
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

  // Cold-start honest: nothing authored yet → render nothing.
  if (!loading && revisions.length === 0) return null;

  return (
    <div className="border-b border-border/60 bg-muted/10">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-4 py-2.5 text-left hover:bg-muted/30 transition-colors"
      >
        {open ? (
          <ChevronDown className="w-3.5 h-3.5 text-muted-foreground/60 shrink-0" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/60 shrink-0" />
        )}
        <History className="w-4 h-4 text-muted-foreground shrink-0" />
        <span className="text-sm font-medium text-foreground">Recently authored</span>
        {!loading && (
          <span className="text-[11px] text-muted-foreground">
            {revisions.length} change{revisions.length === 1 ? '' : 's'}
          </span>
        )}
        {loading && <Loader2 className="w-3.5 h-3.5 animate-spin text-muted-foreground/60" />}
      </button>

      {open && (
        <div className="px-2 pb-2">
          {revisions.map((rev, i) => {
            const isSelected = selectedPath === rev.path;
            return (
              <button
                key={`${rev.path}-${rev.created_at}-${i}`}
                onClick={() => onSelectPath(rev.path)}
                className={`w-full flex items-center gap-2.5 px-2 py-1.5 rounded-md text-left transition-colors ${
                  isSelected ? 'bg-primary/10' : 'hover:bg-muted/40'
                }`}
                title={rev.path}
              >
                <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${authorAccent(rev.authored_by)}`} />
                <span className="text-sm text-foreground truncate min-w-0 flex-1">
                  {fileName(rev.path)}
                </span>
                <span className="text-[11px] text-muted-foreground shrink-0">
                  {formatAuthorLabel(rev.authored_by)}
                </span>
                <span className="text-[11px] text-muted-foreground/70 shrink-0 w-16 text-right">
                  {relativeTime(rev.created_at)}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
