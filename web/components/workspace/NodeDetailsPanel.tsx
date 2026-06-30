'use client';

/**
 * NodeDetailsPanel — the Files "Get Info" / Details panel (ADR-329 D2, amended).
 *
 * Provenance is a *property of the selected node*, not a standing workspace
 * feed. This is the OS "Get Info" / "Properties" convention: select a node,
 * open Details, see what it is and how it came to be — type, last-touched,
 * who authored it, and its revision history.
 *
 * Scopes (one panel, two node shapes):
 *   - FILE   → the file's own revision chain (ADR-209), with revert/diff via
 *              the embedded RevisionHistoryPanel. The canonical `read`-includes-
 *              provenance surface (ADR-329 D1).
 *   - FOLDER → recent revisions across the folder's subtree (read-only
 *              aggregate — each row is the file that changed + who + when).
 *              Reverting an aggregate is meaningless; revert lives on file
 *              Details. Each row deep-links into the file it changed.
 *
 * Both read Layer-1 only (ADR-328 D6): path / authored_by / message /
 * created_at. No embeddings, no search internals.
 *
 * Per-node history (Get Info), complementary to the workspace-wide Recents
 * view (ADR-329 Amendment 2, `RecentRevisions`, center-pane empty-state):
 * Details answers "this file's chain"; Recents answers "what changed across
 * the workspace while I was away." Same Layer-1 data, two Finder-faithful
 * scopes — they never co-render (Details on selection; Recents when nothing
 * is selected).
 */

import { useEffect, useState, useCallback } from 'react';
import { Loader2, FileText, Folder } from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { RevisionHistoryPanel } from '@/components/workspace/RevisionHistoryPanel';
import {
  formatAuthorLabelOrSystem as formatAuthorLabel,
  authorAccent,
} from '@/lib/workspace/attribution';
import type { WorkspaceTreeNode } from '@/types';

// ADR-388 D3: author label + accent come from the ONE shared attribution
// module (the MCP-host form "ChatGPT (via MCP)" surfaces here too).

function fileName(path: string): string {
  return path.split('/').filter(Boolean).pop() || path;
}

function relativeTime(value: string | null): string {
  if (!value) return '';
  const then = new Date(value).getTime();
  if (Number.isNaN(then)) return '';
  const min = Math.floor((Date.now() - then) / 60000);
  if (min < 1) return 'just now';
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const d = Math.floor(hr / 24);
  if (d < 7) return `${d}d ago`;
  return new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

interface SubtreeRevision {
  id: string;
  path?: string | null;
  authored_by: string;
  message: string;
  created_at: string;
}

function FolderDetails({
  node,
  onSelectPath,
}: {
  node: WorkspaceTreeNode;
  onSelectPath?: (path: string) => void;
}) {
  const [revisions, setRevisions] = useState<SubtreeRevision[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api.workspace
      .listRevisions({ pathPrefix: node.path }, 20)
      .then((res) => {
        if (cancelled) return;
        setRevisions((res.revisions || []) as SubtreeRevision[]);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e instanceof APIError ? e.message : String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [node.path]);

  return (
    <div className="border border-border rounded-lg bg-background">
      <div className="px-3 py-2 border-b border-border text-sm font-medium">
        Recent changes in this folder
      </div>
      {loading && (
        <div className="flex items-center gap-2 px-3 py-4 text-sm text-muted-foreground">
          <Loader2 className="w-4 h-4 animate-spin" />
          Loading…
        </div>
      )}
      {!loading && error && (
        <div className="px-3 py-3 text-xs text-destructive">Failed to load: {error}</div>
      )}
      {!loading && !error && revisions.length === 0 && (
        <div className="px-3 py-4 text-xs text-muted-foreground italic">
          Nothing has changed in this folder yet.
        </div>
      )}
      {!loading && !error && revisions.length > 0 && (
        <ul className="divide-y divide-border/60">
          {revisions.map((rev) => {
            const p = rev.path || '';
            return (
              <li key={`${rev.id}`}>
                <button
                  type="button"
                  onClick={() => p && onSelectPath?.(p)}
                  disabled={!p}
                  className="w-full flex items-center gap-2.5 px-3 py-2 text-left hover:bg-muted/40 transition-colors disabled:cursor-default"
                  title={p}
                >
                  <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${authorAccent(rev.authored_by)}`} />
                  <span className="text-sm text-foreground truncate min-w-0 flex-1">
                    {fileName(p)}
                  </span>
                  <span className="text-[11px] text-muted-foreground shrink-0">
                    {formatAuthorLabel(rev.authored_by)}
                  </span>
                  <span className="text-[11px] text-muted-foreground/70 shrink-0 w-16 text-right">
                    {relativeTime(rev.created_at)}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

// ADR-388 follow-up: a compact attribution SYNTHESIS for a file, derived from
// its revision chain — the interop-wedge story in one line (who started it, who
// last touched it, how many principals have contributed). Heads the Get-Info
// modal's file branch, above the full chain.
function FileAttributionSummary({ path }: { path: string }) {
  const [summary, setSummary] = useState<{
    count: number;
    distinct: number;
    first: string | null;
    last: string | null;
  } | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.workspace
      .listRevisions({ path }, 50)
      .then((res) => {
        if (cancelled) return;
        const revs = res.revisions || [];
        if (revs.length === 0) {
          setSummary(null);
          return;
        }
        // revisions come newest-first; first authored = the oldest.
        const authors = revs.map((r) => r.authored_by);
        const distinct = new Set(authors).size;
        setSummary({
          count: revs.length,
          distinct,
          last: authors[0] ?? null,
          first: authors[authors.length - 1] ?? null,
        });
      })
      .catch(() => {
        if (!cancelled) setSummary(null);
      });
    return () => {
      cancelled = true;
    };
  }, [path]);

  if (!summary) return null;

  const firstLabel = formatAuthorLabel(summary.first);
  const lastLabel = formatAuthorLabel(summary.last);
  return (
    <div className="rounded-md border border-border/60 bg-muted/20 px-3 py-2 text-[11px] text-muted-foreground space-y-1">
      <div className="flex items-center gap-1.5">
        <span className={cn('h-1.5 w-1.5 rounded-full shrink-0', authorAccent(summary.last))} />
        <span>
          Last edited by <span className="font-medium text-foreground/80">{lastLabel}</span>
        </span>
      </div>
      {summary.first !== summary.last && (
        <div className="flex items-center gap-1.5">
          <span className={cn('h-1.5 w-1.5 rounded-full shrink-0', authorAccent(summary.first))} />
          <span>
            First authored by <span className="font-medium text-foreground/80">{firstLabel}</span>
          </span>
        </div>
      )}
      <div className="text-muted-foreground/70">
        {summary.count} {summary.count === 1 ? 'revision' : 'revisions'}
        {summary.distinct > 1 ? ` · ${summary.distinct} contributors` : ''}
      </div>
    </div>
  );
}

interface NodeDetailsPanelProps {
  node: WorkspaceTreeNode;
  /** Navigate to a file path (folder Details rows deep-link into files). */
  onSelectPath?: (path: string) => void;
  /** Called after a successful revert so the parent can refetch content. */
  onRevert?: () => void;
}

export function NodeDetailsPanel({ node, onSelectPath, onRevert }: NodeDetailsPanelProps) {
  const isFolder = node.type === 'folder';

  // Node summary line — type · child count (folders) · last-touched · author.
  const summary = useCallback((): string => {
    const parts: string[] = [isFolder ? 'Folder' : 'File'];
    if (isFolder && typeof node.children?.length === 'number') {
      const c = node.children.length;
      parts.push(`${c} ${c === 1 ? 'item' : 'items'}`);
    }
    if (node.updated_at) parts.push(`Updated ${relativeTime(node.updated_at)}`);
    if (node.authored_by) parts.push(`Last touched by ${formatAuthorLabel(node.authored_by)}`);
    return parts.join(' · ');
  }, [isFolder, node.children, node.updated_at, node.authored_by]);

  return (
    <div className="border-b border-border bg-muted/10 px-4 py-3 space-y-3">
      <div className="flex items-center gap-2 min-w-0">
        {isFolder ? (
          <Folder className="w-4 h-4 text-sky-600 shrink-0" />
        ) : (
          <FileText className="w-4 h-4 text-muted-foreground shrink-0" />
        )}
        <div className="min-w-0">
          <p className="text-sm font-medium truncate">{node.name}</p>
          <p className="text-[11px] text-muted-foreground">{summary()}</p>
        </div>
      </div>

      {isFolder ? (
        <FolderDetails node={node} onSelectPath={onSelectPath} />
      ) : (
        // File Details — the attribution synthesis (who started/last-touched,
        // how many contributors) heading the full revision chain with
        // revert/diff (ADR-209). Now the SINGLE home for provenance (the
        // inline FileView panel was removed — ADR-388 follow-up).
        <div className="space-y-3">
          <FileAttributionSummary path={node.path} />
          <RevisionHistoryPanel path={node.path} onRevert={onRevert} />
        </div>
      )}
    </div>
  );
}
