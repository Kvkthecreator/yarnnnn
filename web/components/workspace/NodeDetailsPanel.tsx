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

import { useEffect, useMemo, useState } from 'react';
import { Loader2, FileText, Folder } from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { formatRelativeTime, formatAbsolute } from '@/lib/formatting';
import { RevisionHistoryPanel } from '@/components/workspace/RevisionHistoryPanel';
import {
  formatAuthorLabelOrSystem as formatAuthorLabel,
  authorAccent,
} from '@/lib/workspace/attribution';
import { operatorCanOrganize, organizeBlockedReason } from '@/lib/workspace/ownership';
import { fileLegibilityState, legibilityDescriptor } from '@/lib/workspace/legibility';
import { resolveHandlers } from '@/lib/file-types/handlers';
import { extractTemplate, knownKind, rememberKind } from '@/lib/file-types';
import type { WorkspaceTreeNode } from '@/types';

// ADR-388 D3: author label + accent come from the ONE shared attribution
// module (the MCP-host form "ChatGPT (via MCP)" surfaces here too).

function fileName(path: string): string {
  return path.split('/').filter(Boolean).pop() || path;
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
                  <span
                    className="text-[11px] text-muted-foreground/70 shrink-0 w-16 text-right"
                    title={formatAbsolute(rev.created_at)}
                  >
                    {formatRelativeTime(rev.created_at, { rollToDate: true })}
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

  // ADR-422 D4: the plain-language "why" for a not-freely-editable file. For
  // agent-authored, name the most-recent contributor (the head author).
  const legibility = fileLegibilityState(node);
  const headAuthor = node.authored_by ?? contributors?.[0] ?? null;
  const stateDescriptor = legibilityDescriptor(
    legibility,
    legibility === 'agent-authored' ? formatAuthorLabel(headAuthor) : null,
  );

  return (
    <div className="rounded-md border border-border/60 bg-muted/10 px-3 py-2">
      {/* ADR-422 D4: the file's legibility state, stated in object language at
          the top — why it's not freely editable (system-managed / a record /
          agent-authored). Reuses the macOS-plain copy discipline (ADR-400 Am.2). */}
      {stateDescriptor && (
        <p className="mb-2 text-[11px] leading-snug text-muted-foreground">{stateDescriptor}</p>
      )}
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
            <span className="text-[10px] text-muted-foreground">{organizeBlockedReason(node.path).body}</span>
          </span>
        )}
      </PropRow>
      {node.updated_at && (
        <PropRow label="Modified">
          <span title={formatAbsolute(node.updated_at)}>
            {formatRelativeTime(node.updated_at, { rollToDate: true })}
          </span>
        </PropRow>
      )}
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
          <FileOpensWith path={node.path} />
          <FileReach path={node.path} />
          <FileShares path={node.path} />
          <RevisionHistoryPanel path={node.path} onRevert={onRevert} />
        </div>
      )}
    </div>
  );
}


// ── Opens with — the per-file default binding (ADR-514 D2.4) ───────────────
// The macOS Get Info "Open with:" row. Per-FILE only (per-type config is
// deferred), so the default lives ON the file and travels with it. Renders only
// when the file HAS a choice — a single-handler file has nothing to bind, and a
// dropdown of one is noise.

function FileOpensWith({ path }: { path: string }) {
  // ADR-518 click-pass run-1 finding: resolve WITH the file's kind, else a
  // document's row read "Studio (default)" and never offered Docs. This
  // panel reads the file anyway (for the override), so the kind rides the
  // same fetch and lands in the shared PATH_KIND cache.
  const [kind, setKind] = useState<string | null | undefined>(() => knownKind(path));
  const handlers = useMemo(
    () => resolveHandlers({ paths: [path], isFolder: false, kind }),
    [path, kind],
  );
  const [override, setOverride] = useState<string | null | undefined>(undefined);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.workspace
      .getFile(path)
      .then((f) => {
        if (cancelled) return;
        const k = extractTemplate(f.content ?? '');
        rememberKind(path, k);
        setKind(k);
        const launch = (f.metadata as { launch?: { handler?: string } } | undefined)?.launch;
        setOverride(launch?.handler ?? null);
      })
      .catch(() => { if (!cancelled) setOverride(null); });
    return () => { cancelled = true; };
  }, [path]);

  if (handlers.length < 2) return null;

  // The effective default: the override when it still names a live handler,
  // else the registry's first. A STALE override reads as the registry default
  // here for the same reason it resolves that way — it must never strand a file.
  const effective = handlers.some((h) => h.id === override) ? override : handlers[0].id;

  const pick = async (id: string) => {
    setSaving(true);
    const next = id === handlers[0].id ? null : id; // choosing the registry default clears
    try {
      await api.documents.setLaunchHandler(path, next);
      setOverride(next);
    } catch {
      /* the select reverts on the next read; nothing durable changed */
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-md border border-border/60 bg-muted/10 px-3 py-2">
      <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
        Opens with
      </p>
      <select
        value={effective ?? handlers[0].id}
        disabled={saving || override === undefined}
        onChange={(e) => void pick(e.target.value)}
        className="w-full rounded border border-border bg-background px-2 py-1 text-xs"
      >
        {handlers.map((h, i) => (
          <option key={h.id} value={h.id}>
            {h.label}{i === 0 ? ' (default)' : ''}
          </option>
        ))}
      </select>
    </div>
  );
}


// ── Reach — "who can reach this file" (ADR-512 D6) ─────────────────────────
// The Get-Info answer Finder taught everyone to look for: per-principal
// read/write over THIS path, computed server-side by the same powerbox
// matcher the gate consults (the panel and the gate cannot disagree).

function FileReach({ path }: { path: string }) {
  const [rows, setRows] = useState<Array<{
    principal_id: string; role: string; label: string | null;
    can_read?: boolean | null; can_write?: boolean | null;
  }> | null>(null);

  useEffect(() => {
    let alive = true;
    api.workspace
      .getMembers(path)
      .then((r) => { if (alive) setRows(r.members); })
      .catch(() => { if (alive) setRows(null); });
    return () => { alive = false; };
  }, [path]);

  if (!rows || rows.length === 0) return null;
  const reachable = rows.filter((m) => m.can_read || m.can_write);
  if (reachable.length === 0) return null;

  return (
    <div>
      <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        Who can reach this
      </p>
      <ul className="space-y-1">
        {reachable.map((m) => (
          <li key={m.principal_id} className="flex items-center gap-2 text-xs">
            <span className="min-w-0 flex-1 truncate">
              {m.label || m.principal_id}
              <span className="ml-1 text-muted-foreground">({m.role})</span>
            </span>
            <span
              className={cn(
                'shrink-0 rounded px-1.5 py-0.5 text-[10px]',
                m.can_write
                  ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400'
                  : 'bg-muted text-muted-foreground',
              )}
            >
              {m.can_write ? 'can edit' : m.can_read ? 'read-only' : '—'}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}


// ── Shares — the "Manage Shared File…" row (ADR-465/513) ───────────────────
// The live share links that point at THIS artifact: their shape (full access
// vs view-only) and a revoke. Revocation is the control that makes a public
// capability link honest (ADR-513 D4: dark means dark).

/** Both spellings of one path compare equal.
 *
 *  A share row's `artifact_path` is whatever the minting origin passed —
 *  ABSOLUTE (`/workspace/operation/x.html`) from the cockpit + the MCP share
 *  verb, workspace-RELATIVE from callers that pre-strip. Comparing one spelling
 *  against the other silently matched nothing, so the whole share section
 *  (including its Revoke) rendered `null` while a live public link kept serving
 *  — found live 2026-08-03. Normalize both sides; never compare raw. */
function shareKey(path: string): string {
  return (path.startsWith('/workspace/') ? path.slice('/workspace/'.length) : path).replace(/^\/+/, '');
}

function FileShares({ path }: { path: string }) {
  const rel = shareKey(path);
  const [shares, setShares] = useState<Array<{
    id: string; artifact_path: string | null; role: string; status: string;
  }> | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = () => {
    api.workspace
      .listShares()
      .then((r) => setShares(r.shares.filter(
        (s) => s.artifact_path != null && shareKey(s.artifact_path) === rel,
      )))
      .catch(() => setShares(null));
  };
  useEffect(load, [rel]);

  const revoke = async (id: string) => {
    setBusy(id);
    try {
      await api.workspace.revokeShare(id);
      load();
    } catch {
      /* the row stays; the next load shows the truth */
    } finally {
      setBusy(null);
    }
  };

  if (!shares || shares.length === 0) return null;
  return (
    <div>
      <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        Share links to this file
      </p>
      <ul className="space-y-1">
        {shares.map((s) => (
          <li key={s.id} className="flex items-center gap-2 text-xs">
            <span className="min-w-0 flex-1 truncate text-muted-foreground">
              {s.role === 'viewer' ? 'View-only link' : 'Full-access link'}
            </span>
            <button
              type="button"
              onClick={() => void revoke(s.id)}
              disabled={busy === s.id}
              className="shrink-0 rounded border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground transition-colors hover:text-destructive disabled:opacity-50"
            >
              {busy === s.id ? 'Revoking…' : 'Revoke'}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
