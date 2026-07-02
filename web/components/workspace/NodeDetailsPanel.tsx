'use client';

/**
 * NodeDetailsPanel — the Files "Properties" panel body (ADR-329 D2, amended;
 * ADR-400 redesign — flat properties block + ownership + revision history).
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

import { useEffect, useState } from 'react';
import { Loader2, FileText, Folder } from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { RevisionHistoryPanel } from '@/components/workspace/RevisionHistoryPanel';
import {
  formatAuthorLabelOrSystem as formatAuthorLabel,
  authorAccent,
} from '@/lib/workspace/attribution';
import { operatorCanOrganize, organizeBlockedReason } from '@/lib/workspace/ownership';
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

// A single labeled row of the Properties block (Windows-Explorer Properties
// idiom): a muted label on the left, the value on the right.
function PropRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3 py-1">
      <span className="w-24 shrink-0 text-[11px] text-muted-foreground">{label}</span>
      <span className="min-w-0 flex-1 text-[12px] text-foreground">{children}</span>
    </div>
  );
}

// The file's Properties — the flat "what is this" block (ADR-400).
//
// Answers the two Properties questions cleanly, without the box-in-box clutter
// the old three-way attribution stack had: Kind · Location · Ownership · Modified
// · Contributors. The redundant "Last edited by · N revisions" summary card was
// DELETED — "last edited by" is already in the modal header + the r1 chain row;
// its one unique fact (contributor count) folds into the Contributors row here.
// Ownership is the ADR-400 two-principal story: "Yours" (you may move/rename/
// trash it) vs "Managed by Freddie" (an agent authored it — edit through chat).
function FileProperties({ node }: { node: WorkspaceTreeNode }) {
  const [contributors, setContributors] = useState<string[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.workspace
      .listRevisions({ path: node.path }, 50)
      .then((res) => {
        if (cancelled) return;
        const revs = res.revisions || [];
        // Distinct authors, most-recent first, deduped in encounter order.
        const seen = new Set<string>();
        const ordered: string[] = [];
        for (const r of revs) {
          if (r.authored_by && !seen.has(r.authored_by)) {
            seen.add(r.authored_by);
            ordered.push(r.authored_by);
          }
        }
        setContributors(ordered);
      })
      .catch(() => { if (!cancelled) setContributors([]); });
    return () => { cancelled = true; };
  }, [node.path]);

  const canOrganize = operatorCanOrganize(node.path);
  const kind = describeKind(node.path);
  const location = node.path.replace(/\/[^/]*$/, '') || '/';

  return (
    <div className="rounded-md border border-border/60 bg-muted/10 px-3 py-2">
      <PropRow label="Kind">{kind}</PropRow>
      <PropRow label="Location">
        <span className="break-all font-mono text-[11px] text-muted-foreground">{location}</span>
      </PropRow>
      {/* ADR-400 Amendment 1: what the operator can DO here (organize). Content
          editing routes through chat for every file (that boundary holds); this
          row is about move/rename/trash. Almost everything is organizable — the
          only carves are system/ runtime + machine-config the system reads by
          name (renaming would break the reader). */}
      <PropRow label="You can">
        {canOrganize ? (
          <span className="text-[11px] text-foreground/80">move · rename · trash it · edit via chat</span>
        ) : (
          <span className="inline-flex flex-col gap-0.5">
            <span className="text-[11px] text-foreground/80">read it · edit via chat</span>
            <span className="text-[10px] text-muted-foreground">{organizeBlockedReason(node.path)}</span>
          </span>
        )}
      </PropRow>
      {node.updated_at && <PropRow label="Modified">{relativeTime(node.updated_at)}</PropRow>}
      {contributors && contributors.length > 0 && (
        <PropRow label="Contributors">
          <span className="inline-flex flex-wrap items-center gap-x-1.5 gap-y-0.5">
            {contributors.map((a, i) => (
              <span key={`${a}-${i}`} className="inline-flex items-center gap-1">
                <span className={cn('h-1.5 w-1.5 rounded-full shrink-0', authorAccent(a))} />
                <span className="text-[11px] text-foreground/80">{formatAuthorLabel(a)}</span>
                {i < contributors.length - 1 && <span className="text-muted-foreground/40">·</span>}
              </span>
            ))}
          </span>
        </PropRow>
      )}
    </div>
  );
}

// Human-readable "Kind" from the filename extension (Properties-dialog style).
function describeKind(path: string): string {
  const ext = (path.split('.').pop() || '').toLowerCase();
  const map: Record<string, string> = {
    md: 'Markdown document', txt: 'Text document', pdf: 'PDF document',
    docx: 'Word document', doc: 'Word document',
    xlsx: 'Spreadsheet', xls: 'Spreadsheet', csv: 'CSV data',
    pptx: 'Presentation', ppt: 'Presentation',
    png: 'PNG image', jpg: 'JPEG image', jpeg: 'JPEG image', gif: 'GIF image',
    webp: 'WebP image', svg: 'SVG image',
    yaml: 'Config (YAML)', yml: 'Config (YAML)', json: 'Data (JSON)',
    html: 'HTML document',
  };
  return map[ext] || (ext ? `${ext.toUpperCase()} file` : 'File');
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

  return (
    <div className="space-y-3">
      {/* Identity line — icon + name + a one-line kind/count summary. The modal
          header already shows the name, so this is a compact restatement with
          the type + child-count for folders. */}
      <div className="flex items-center gap-2 min-w-0">
        {isFolder ? (
          <Folder className="w-4 h-4 text-sky-600 shrink-0" />
        ) : (
          <FileText className="w-4 h-4 text-muted-foreground shrink-0" />
        )}
        <div className="min-w-0">
          <p className="text-sm font-medium truncate">{node.name}</p>
          {isFolder && typeof node.children?.length === 'number' && (
            <p className="text-[11px] text-muted-foreground">
              {node.children.length} {node.children.length === 1 ? 'item' : 'items'}
            </p>
          )}
        </div>
      </div>

      {isFolder ? (
        <FolderDetails node={node} onSelectPath={onSelectPath} />
      ) : (
        // File Properties — the flat "what is this" block (Kind · Location ·
        // Ownership · Modified · Contributors), then the revision history (the
        // "how it came to be" — the moat a plain Finder can't show). The panel
        // renders its own "Revision history" header. ADR-400.
        <div className="space-y-3">
          <FileProperties node={node} />
          <RevisionHistoryPanel path={node.path} onRevert={onRevert} />
        </div>
      )}
    </div>
  );
}
