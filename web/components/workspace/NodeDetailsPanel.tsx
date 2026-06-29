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
import { RevisionHistoryPanel } from '@/components/workspace/RevisionHistoryPanel';
import type { WorkspaceTreeNode } from '@/types';

// ADR-209 authored_by taxonomy → operator-readable label. Same mapping the
// rest of the Files surface uses; kept local because it's a one-liner.
function formatAuthorLabel(authored_by: string | null | undefined): string {
  if (!authored_by) return 'System';
  if (authored_by === 'operator') return 'You';
  if (authored_by.startsWith('yarnnn:')) return 'YARNNN';
  if (authored_by.startsWith('agent:')) return `Agent (${authored_by.slice('agent:'.length)})`;
  if (authored_by.startsWith('specialist:')) return 'Specialist';
  if (authored_by.startsWith('freddie:')) return 'Reviewer';
  if (authored_by.startsWith('system:')) return 'System';
  return 'System';
}

function authorAccent(authored_by: string | null | undefined): string {
  switch (formatAuthorLabel(authored_by)) {
    case 'You': return 'bg-primary';
    case 'Reviewer': return 'bg-rose-400';
    case 'YARNNN': return 'bg-purple-400';
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
        // File Details — the full revision chain with revert/diff (ADR-209).
        // revertDisabled mirrors ContentViewer's prior behavior: revert writes
        // through PATCH /workspace/file, which the backend gates to editable
        // prefixes; non-editable system files still show history (read), just
        // no revert button.
        <RevisionHistoryPanel path={node.path} onRevert={onRevert} />
      )}
    </div>
  );
}
