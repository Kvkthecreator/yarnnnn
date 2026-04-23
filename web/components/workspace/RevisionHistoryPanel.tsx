'use client';

/**
 * RevisionHistoryPanel — ADR-209 Phase 4.
 *
 * Reads the Authored Substrate's revision chain for a given workspace path
 * and renders it newest-first as:
 *
 *   r{N}  {author-chip}  "{message}"  {ago}
 *
 * Click a revision → inline unified diff vs. current (uses
 * /api/workspace/revisions/diff/two). The currently-displayed revision
 * is marked "current". Operator-authored + YARNNN-authored + agent-authored
 * + system-authored revisions all render with distinct author-chip colors
 * so the cognitive-layer pattern is visible at a glance (supervision
 * property per ADR-198 + FOUNDATIONS Derived Principle 12).
 *
 * Revert action: surfaces for non-head revisions. Revert is a write of the
 * prior revision's content back through PATCH /api/workspace/file — which
 * lands a new revision attributed to "operator" with message
 * "revert to r{N}". No special server primitive; the revert IS a new
 * revision (the chain's DAG-shape makes this natural).
 */

import { useEffect, useState, useCallback } from 'react';
import {
  Loader2,
  History,
  User,
  Bot,
  Cpu,
  Wrench,
  AlertTriangle,
  Undo2,
  GitCompare,
  X,
} from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { cn } from '@/lib/utils';

interface RevisionSummary {
  id: string;
  authored_by: string;
  author_identity_uuid: string | null;
  message: string;
  created_at: string;
  parent_version_id: string | null;
}

interface RevisionHistoryPanelProps {
  /** Absolute workspace path (e.g., /workspace/context/_shared/MANDATE.md). */
  path: string;
  /** Optional CSS class for outer container. */
  className?: string;
  /** Optional limit on how many revisions to fetch (default 10). */
  limit?: number;
  /** If true, panel starts collapsed. Default false (expanded). */
  initiallyCollapsed?: boolean;
  /** Optional: called after a successful revert so parent can refetch content. */
  onRevert?: () => void;
  /** Optional: if the path is not editable via PATCH /api/workspace/file, hide the revert button. */
  revertDisabled?: boolean;
}

type AuthorLayer = 'operator' | 'yarnnn' | 'agent' | 'specialist' | 'reviewer' | 'system' | 'unknown';

function authorLayer(authored_by: string): AuthorLayer {
  if (!authored_by) return 'unknown';
  if (authored_by === 'operator') return 'operator';
  if (authored_by.startsWith('yarnnn:')) return 'yarnnn';
  if (authored_by.startsWith('agent:')) return 'agent';
  if (authored_by.startsWith('specialist:')) return 'specialist';
  if (authored_by.startsWith('reviewer:')) return 'reviewer';
  if (authored_by.startsWith('system:')) return 'system';
  return 'unknown';
}

function authorChipColor(layer: AuthorLayer): string {
  switch (layer) {
    case 'operator':
      return 'bg-blue-500/10 text-blue-700 border-blue-500/30';
    case 'yarnnn':
      return 'bg-purple-500/10 text-purple-700 border-purple-500/30';
    case 'agent':
      return 'bg-emerald-500/10 text-emerald-700 border-emerald-500/30';
    case 'specialist':
      return 'bg-cyan-500/10 text-cyan-700 border-cyan-500/30';
    case 'reviewer':
      return 'bg-amber-500/10 text-amber-700 border-amber-500/30';
    case 'system':
      return 'bg-zinc-500/10 text-zinc-600 border-zinc-500/30';
    default:
      return 'bg-zinc-500/10 text-zinc-600 border-zinc-500/30';
  }
}

function AuthorIcon({ layer }: { layer: AuthorLayer }) {
  const cls = 'w-3 h-3';
  switch (layer) {
    case 'operator':
      return <User className={cls} />;
    case 'yarnnn':
      return <Bot className={cls} />;
    case 'agent':
      return <Cpu className={cls} />;
    case 'reviewer':
      return <AlertTriangle className={cls} />;
    case 'specialist':
    case 'system':
    default:
      return <Wrench className={cls} />;
  }
}

function formatAge(iso: string): string {
  try {
    const then = new Date(iso).getTime();
    if (!Number.isFinite(then)) return '';
    const seconds = Math.floor((Date.now() - then) / 1000);
    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
    return new Date(iso).toLocaleDateString();
  } catch {
    return '';
  }
}

export function RevisionHistoryPanel({
  path,
  className,
  limit = 10,
  initiallyCollapsed = false,
  onRevert,
  revertDisabled = false,
}: RevisionHistoryPanelProps) {
  const [revisions, setRevisions] = useState<RevisionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(initiallyCollapsed);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [diffText, setDiffText] = useState<string | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);
  const [diffIdentical, setDiffIdentical] = useState(false);
  const [revertBusy, setRevertBusy] = useState(false);
  const [revertError, setRevertError] = useState<string | null>(null);

  const fetchRevisions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.workspace.listRevisions(path, limit);
      setRevisions(result.revisions || []);
    } catch (e) {
      setError(e instanceof APIError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [path, limit]);

  useEffect(() => {
    fetchRevisions();
  }, [fetchRevisions]);

  const headId = revisions[0]?.id ?? null;

  const openDiff = useCallback(
    async (revId: string) => {
      if (!headId || revId === headId) {
        // Clicking current just closes any open diff
        setSelectedId(null);
        setDiffText(null);
        return;
      }
      setSelectedId(revId);
      setDiffText(null);
      setDiffIdentical(false);
      setDiffLoading(true);
      try {
        const result = await api.workspace.diffRevisions(path, revId, headId);
        setDiffText(result.diff);
        setDiffIdentical(result.identical);
      } catch (e) {
        setDiffText(`# diff fetch failed\n${e instanceof APIError ? e.message : String(e)}`);
      } finally {
        setDiffLoading(false);
      }
    },
    [path, headId]
  );

  const doRevert = useCallback(
    async (rev: RevisionSummary) => {
      setRevertBusy(true);
      setRevertError(null);
      try {
        const detail = await api.workspace.readRevision(path, rev.id);
        if (detail.content === null || detail.content === undefined) {
          throw new Error('Revision has no content to restore');
        }
        const shortId = rev.id.slice(0, 8);
        await api.workspace.editFile(
          path,
          detail.content,
          undefined,
          `revert to revision ${shortId}`
        );
        // Close diff view + refetch
        setSelectedId(null);
        setDiffText(null);
        await fetchRevisions();
        onRevert?.();
      } catch (e) {
        setRevertError(e instanceof APIError ? e.message : String(e));
      } finally {
        setRevertBusy(false);
      }
    },
    [path, fetchRevisions, onRevert]
  );

  const totalCount = revisions.length;

  return (
    <div className={cn('border border-border rounded-lg bg-background', className)}>
      <button
        type="button"
        onClick={() => setCollapsed(c => !c)}
        className="w-full flex items-center justify-between px-3 py-2 text-sm hover:bg-muted/40 transition-colors"
        aria-expanded={!collapsed}
      >
        <span className="flex items-center gap-2">
          <History className="w-4 h-4 text-muted-foreground" />
          <span className="font-medium">Revision history</span>
          {!loading && (
            <span className="text-xs text-muted-foreground">
              ({totalCount}{totalCount === limit ? '+' : ''})
            </span>
          )}
        </span>
        <span className="text-xs text-muted-foreground">
          {collapsed ? 'show' : 'hide'}
        </span>
      </button>

      {!collapsed && (
        <div className="border-t border-border">
          {loading && (
            <div className="flex items-center gap-2 px-3 py-4 text-sm text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin" />
              Loading revisions…
            </div>
          )}

          {!loading && error && (
            <div className="px-3 py-3 text-xs text-destructive">Failed to load: {error}</div>
          )}

          {!loading && !error && revisions.length === 0 && (
            <div className="px-3 py-4 text-xs text-muted-foreground italic">
              No revisions yet for this file.
            </div>
          )}

          {!loading && !error && revisions.length > 0 && (
            <ul className="divide-y divide-border">
              {revisions.map((rev, idx) => {
                const isHead = rev.id === headId;
                const layer = authorLayer(rev.authored_by);
                const chipCls = authorChipColor(layer);
                const isSelected = selectedId === rev.id;
                const revNumber = totalCount - idx; // newest = highest r-number

                return (
                  <li key={rev.id} className="px-3 py-2">
                    <div
                      className={cn(
                        'flex items-start gap-2 cursor-pointer',
                        isHead && 'opacity-90'
                      )}
                      onClick={() => openDiff(rev.id)}
                    >
                      <div className="flex items-center gap-2 shrink-0 pt-0.5">
                        <span className="text-[11px] font-mono text-muted-foreground">
                          r{revNumber}
                        </span>
                        <span
                          className={cn(
                            'inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[10px]',
                            chipCls
                          )}
                          title={rev.authored_by}
                        >
                          <AuthorIcon layer={layer} />
                          <span className="font-medium">{layer}</span>
                        </span>
                        {isHead && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/30">
                            current
                          </span>
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs text-foreground truncate">{rev.message}</div>
                        <div className="text-[10px] text-muted-foreground/60">
                          {formatAge(rev.created_at)}
                        </div>
                      </div>
                      {!isHead && !revertDisabled && (
                        <button
                          type="button"
                          onClick={e => {
                            e.stopPropagation();
                            doRevert(rev);
                          }}
                          disabled={revertBusy}
                          className="shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded border border-border text-[11px] hover:bg-muted disabled:opacity-50"
                          title="Revert to this revision — creates a new revision attributed to you"
                        >
                          <Undo2 className="w-3 h-3" />
                          revert
                        </button>
                      )}
                      {!isHead && (
                        <span className="shrink-0 text-[10px] text-muted-foreground/50 inline-flex items-center gap-1">
                          <GitCompare className="w-3 h-3" />
                          diff
                        </span>
                      )}
                    </div>

                    {isSelected && (
                      <div className="mt-2 rounded border border-border bg-muted/30">
                        <div className="flex items-center justify-between px-2 py-1 border-b border-border">
                          <span className="text-[11px] text-muted-foreground">
                            Diff against current (r{totalCount})
                          </span>
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedId(null);
                              setDiffText(null);
                            }}
                            className="text-muted-foreground hover:text-foreground"
                            aria-label="Close diff"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </div>
                        {diffLoading && (
                          <div className="flex items-center gap-2 p-3 text-xs text-muted-foreground">
                            <Loader2 className="w-3 h-3 animate-spin" />
                            Computing diff…
                          </div>
                        )}
                        {!diffLoading && diffIdentical && (
                          <div className="p-3 text-xs text-muted-foreground italic">
                            Content identical — different revisions written with the same bytes.
                          </div>
                        )}
                        {!diffLoading && diffText && !diffIdentical && (
                          <pre className="px-3 py-2 text-[11px] font-mono whitespace-pre overflow-x-auto max-h-96">
                            {diffText}
                          </pre>
                        )}
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          )}

          {revertError && (
            <div className="px-3 py-2 border-t border-border text-xs text-destructive">
              Revert failed: {revertError}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
