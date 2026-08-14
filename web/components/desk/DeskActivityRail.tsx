'use client';

/**
 * DeskActivityRail — a desk folder's ONE lifecycle rail (ADR-565 D1 +
 * ADR-567 D2.3, housing-extracted for ADR-569 D6).
 *
 * ADR-565 D1: "the revision history is the delta rail; the diff is the delta."
 * This rail is that history, generalized to the folder a desk manages: one
 * merged, attributed, newest-first list of
 *
 *   - every revision under the folder subtree (the maintained artifact, its
 *     declaration files, and anything the member drops in — the folder is the
 *     subject's home, ADR-565 D3), via the pathPrefix aggregate the revisions
 *     route already serves;
 *   - the standing runs that produced NO revision (empty/failed/skipped) from
 *     the execution ledger — the folder's pulse stays honest between changes.
 *
 * A successful run is deliberately NOT shown as an event row: its revision IS
 * the row (one happening, one row).
 *
 * A revision row expands to the diff against its PARENT — "what this change
 * did" — and rows the consuming desk declares revertable offer restore (a
 * revert is a new revision, conditional on the head the panel loaded;
 * ADR-406 D2).
 *
 * The rail is app-agnostic (ADR-518's housing move): each desk passes its own
 * vocabulary — author labels for its standing writer, operator words for its
 * folder's files, which paths are machine noise, which are revertable, and how
 * a run event reads. The defaults are the shared attribution vocabulary and
 * nothing revertable.
 */

import { useCallback, useEffect, useState } from 'react';
import { GitCompare, Loader2, Undo2, X } from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { formatRelativeTime, formatAbsolute } from '@/lib/formatting';
import { authorClass, formatAuthorLabelOrSystem } from '@/lib/workspace/attribution';

interface RailRevision {
  id: string;
  authored_by: string;
  message: string;
  created_at: string;
  parent_version_id: string | null;
  path: string;
}

export interface RailEvent {
  slug: string;
  status: string;
  created_at?: string | null;
  error_reason?: string | null;
}

type RailRow =
  | { kind: 'revision'; at: string; rev: RailRevision }
  | { kind: 'event'; at: string; event: RailEvent };

function defaultAuthorChip(authoredBy: string): string {
  switch (authorClass(authoredBy)) {
    case 'you':
      return 'bg-blue-500/10 text-blue-700 border-blue-500/30';
    case 'yarnnn':
    case 'reviewer':
      return 'bg-indigo-500/10 text-indigo-700 border-indigo-500/30';
    case 'mcp':
      return 'bg-amber-500/10 text-amber-700 border-amber-500/30';
    case 'agent':
    case 'specialist':
      return 'bg-emerald-500/10 text-emerald-700 border-emerald-500/30';
    default:
      return 'bg-zinc-500/10 text-zinc-600 border-zinc-500/30';
  }
}

function defaultEventLine(e: RailEvent): string {
  if (e.status === 'skipped')
    return `Run skipped${e.error_reason ? ` — ${e.error_reason}` : ''}`;
  return `Run failed${e.error_reason ? ` — ${e.error_reason}` : ''}`;
}

export function DeskActivityRail({
  deskRoot,
  events,
  refreshNonce,
  onReverted,
  className,
  authorLabel,
  authorChip,
  fileLabel,
  hideRevision,
  canRevert,
  eventLine,
}: {
  /** Absolute workspace path of the desk's folder. */
  deskRoot: string;
  /** The desk's recent ledger events (success rows are folded into their
   *  revisions; only non-success rows render as events). */
  events: RailEvent[];
  /** Bump to refetch (a lane write landed, the member hit refresh). */
  refreshNonce: number;
  /** A revert landed — the parent should re-read the files it projects. */
  onReverted?: () => void;
  className?: string;
  /** The desk's word for an author (its standing writer's mechanism actor →
   *  the colleague's name). Return undefined to fall back to the shared
   *  attribution vocabulary. */
  authorLabel?: (authoredBy: string) => string | undefined;
  /** Chip classes to pair with `authorLabel`; undefined → shared vocabulary. */
  authorChip?: (authoredBy: string) => string | undefined;
  /** Operator words for the folder's own files, keyed on the deskRoot-relative
   *  path. Return undefined to show the leaf as-is. */
  fileLabel?: (relPath: string) => string | undefined;
  /** Machine noise the rail should not show (distilled signals, legacy
   *  shelves). Default: nothing hidden. */
  hideRevision?: (path: string) => boolean;
  /** Which paths offer "restore this version". Default: none. */
  canRevert?: (path: string) => boolean;
  /** The desk's sentence for a non-success ledger event. */
  eventLine?: (e: RailEvent) => string;
}) {
  const [revisions, setRevisions] = useState<RailRevision[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [diffText, setDiffText] = useState<string | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);
  const [revertBusy, setRevertBusy] = useState(false);
  const [revertError, setRevertError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setError(null);
    api.workspace
      .listRevisions({ pathPrefix: deskRoot }, 30)
      .then((res) => {
        if (!alive) return;
        const rows = (res.revisions || [])
          .filter((r): r is typeof r & { path: string } => typeof r.path === 'string')
          .filter((r) => !(hideRevision?.(r.path) ?? false))
          .map((r) => ({
            id: r.id,
            authored_by: r.authored_by,
            message: r.message,
            created_at: r.created_at,
            parent_version_id: r.parent_version_id,
            path: r.path,
          }));
        setRevisions(rows);
      })
      .catch((e) => {
        if (!alive) return;
        setRevisions([]);
        setError(e instanceof APIError ? e.message : String(e));
      });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deskRoot, refreshNonce]);

  const rows: RailRow[] = [
    ...(revisions ?? []).map<RailRow>((rev) => ({ kind: 'revision', at: rev.created_at, rev })),
    ...events
      .filter((e) => e.status !== 'success' && e.created_at)
      .map<RailRow>((event) => ({ kind: 'event', at: event.created_at as string, event })),
  ]
    .sort((a, b) => (a.at < b.at ? 1 : -1))
    .slice(0, 20);

  const toggleDiff = useCallback(async (rev: RailRevision) => {
    setRevertError(null);
    if (expandedId === rev.id) {
      setExpandedId(null);
      setDiffText(null);
      return;
    }
    setExpandedId(rev.id);
    setDiffText(null);
    if (!rev.parent_version_id) {
      setDiffText(null);
      setDiffLoading(false);
      return;
    }
    setDiffLoading(true);
    try {
      // The delta IS this revision vs its parent (ADR-565 D1 — the chain
      // carries the deltas; "vs current" answers a different question).
      const res = await api.workspace.diffRevisions(rev.path, rev.parent_version_id, rev.id);
      setDiffText(res.diff);
    } catch (e) {
      setDiffText(`# diff fetch failed\n${e instanceof APIError ? e.message : String(e)}`);
    } finally {
      setDiffLoading(false);
    }
  }, [expandedId]);

  const revert = useCallback(async (rev: RailRevision) => {
    setRevertBusy(true);
    setRevertError(null);
    try {
      const [detail, head] = await Promise.all([
        api.workspace.readRevision(rev.path, rev.id),
        api.workspace.listRevisions({ path: rev.path }, 1),
      ]);
      if (detail.content == null) throw new Error('revision has no content to restore');
      const headId = head.revisions?.[0]?.id ?? null;
      if (headId === rev.id) throw new Error('already the current version');
      await api.workspace.editFile(
        rev.path,
        detail.content,
        undefined,
        `revert to revision ${rev.id.slice(0, 8)}`,
        headId,
      );
      setExpandedId(null);
      setDiffText(null);
      onReverted?.();
    } catch (e) {
      setRevertError(e instanceof APIError ? e.message : String(e));
    } finally {
      setRevertBusy(false);
    }
  }, [onReverted]);

  if (revisions === null) {
    return (
      <div className={cn('flex items-center gap-2 py-3 text-xs text-muted-foreground', className)}>
        <Loader2 className="h-3.5 w-3.5 animate-spin" /> Reading the folder&apos;s history…
      </div>
    );
  }

  if (error && rows.length === 0) {
    return (
      <p className={cn('py-2 text-xs text-muted-foreground', className)}>
        The history could not be read ({error}).
      </p>
    );
  }

  if (rows.length === 0) {
    return (
      <p className={cn('py-2 text-xs text-muted-foreground', className)}>
        Nothing has happened here yet.
      </p>
    );
  }

  return (
    <ul className={cn('divide-y rounded-md border', className)}>
      {rows.map((row) => {
        if (row.kind === 'event') {
          return (
            <li
              key={`event-${row.at}-${row.event.slug}`}
              className="flex items-baseline gap-2 px-3 py-2 text-xs text-muted-foreground"
            >
              <span
                className="shrink-0 tabular-nums"
                title={formatAbsolute(row.at)}
              >
                {formatRelativeTime(row.at, { rollToDate: true })}
              </span>
              <span className="min-w-0">{(eventLine ?? defaultEventLine)(row.event)}</span>
            </li>
          );
        }
        const { rev } = row;
        const rel = rev.path.startsWith(`${deskRoot}/`)
          ? rev.path.slice(deskRoot.length + 1)
          : rev.path;
        const chipLabel = fileLabel?.(rel) ?? rel;
        const revertable = canRevert?.(rev.path) ?? false;
        const expanded = expandedId === rev.id;
        return (
          <li key={rev.id} className="px-3 py-2">
            <div
              className="flex cursor-pointer items-start gap-2"
              onClick={() => void toggleDiff(rev)}
            >
              <span
                className="shrink-0 pt-0.5 text-xs tabular-nums text-muted-foreground"
                title={formatAbsolute(rev.created_at)}
              >
                {formatRelativeTime(rev.created_at, { rollToDate: true })}
              </span>
              <span className="shrink-0 rounded border border-border bg-muted/40 px-1.5 py-0.5 text-[10px]">
                {chipLabel}
              </span>
              <span
                className={cn(
                  'shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-medium',
                  authorChip?.(rev.authored_by) ?? defaultAuthorChip(rev.authored_by),
                )}
                title={rev.authored_by}
              >
                {authorLabel?.(rev.authored_by) ?? formatAuthorLabelOrSystem(rev.authored_by)}
              </span>
              <span className="min-w-0 flex-1 truncate text-xs">{rev.message}</span>
              <span className="shrink-0 inline-flex items-center gap-1 text-[10px] text-muted-foreground/50">
                <GitCompare className="h-3 w-3" /> diff
              </span>
            </div>

            {expanded && (
              <div className="mt-2 rounded border border-border bg-muted/30">
                <div className="flex items-center justify-between border-b border-border px-2 py-1">
                  <span className="text-[11px] text-muted-foreground">
                    {rev.parent_version_id
                      ? 'What this change did'
                      : 'First revision — nothing to diff against'}
                  </span>
                  <span className="flex items-center gap-2">
                    {revertable && (
                      <button
                        type="button"
                        disabled={revertBusy}
                        onClick={(e) => {
                          e.stopPropagation();
                          void revert(rev);
                        }}
                        className="inline-flex items-center gap-1 rounded border border-border px-1.5 py-0.5 text-[10px] hover:bg-muted disabled:opacity-50"
                        title="Restore this version — lands as a new revision attributed to you"
                      >
                        <Undo2 className="h-3 w-3" /> restore this version
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setExpandedId(null);
                        setDiffText(null);
                      }}
                      className="text-muted-foreground hover:text-foreground"
                      aria-label="Close diff"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                </div>
                {diffLoading && (
                  <div className="flex items-center gap-2 p-3 text-xs text-muted-foreground">
                    <Loader2 className="h-3 w-3 animate-spin" /> Computing diff…
                  </div>
                )}
                {!diffLoading && diffText && (
                  <pre className="max-h-80 overflow-auto whitespace-pre px-3 py-2 font-mono text-[11px]">
                    {diffText}
                  </pre>
                )}
                {revertError && (
                  <div className="border-t border-border px-3 py-2 text-xs text-destructive">
                    Restore failed: {revertError}
                  </div>
                )}
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
