'use client';

/**
 * DeskActivityRail — the watched folder's ONE lifecycle rail (ADR-565 D1 +
 * ADR-567 D2.3).
 *
 * ADR-565 D1: "the revision history is the delta rail; the diff is the delta."
 * This rail is that history, generalized to the folder the desk manages: one
 * merged, attributed, newest-first list of
 *
 *   - every revision under the folder subtree (the report, CRITERION.md,
 *     _radar.yaml, and anything the member drops in — the folder is the
 *     subject's home, ADR-565 D3), via the pathPrefix aggregate the revisions
 *     route already serves;
 *   - the sweeps that produced NO revision (NO_CHANGE / failures) from the
 *     execution ledger — the folder's pulse stays honest between changes.
 *
 * A successful sweep is deliberately NOT shown as an event row: its report
 * revision IS the row (one happening, one row). Machine noise is filtered
 * (_watch_signal.yaml, the legacy briefs shelf).
 *
 * A revision row expands to the diff against its PARENT — "what this change
 * did" — and report/criterion rows offer revert (a revert is a new revision,
 * conditional on the head the panel loaded; ADR-406 D2).
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

interface RailSweep {
  slug: string;
  status: string;
  created_at?: string | null;
  error_reason?: string | null;
}

type RailRow =
  | { kind: 'revision'; at: string; rev: RailRevision }
  | { kind: 'sweep'; at: string; sweep: RailSweep };

/** The desk fronts the colleague (ADR-567 D1): the sweep's mechanism
 *  attribution reads as Researcher; everything else keeps the shared
 *  attribution vocabulary. */
function railAuthorLabel(authoredBy: string): string {
  if (authoredBy === 'system:radar') return 'Researcher';
  return formatAuthorLabelOrSystem(authoredBy);
}

function railAuthorChip(authoredBy: string): string {
  if (authoredBy === 'system:radar')
    return 'bg-emerald-500/10 text-emerald-700 border-emerald-500/30';
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

/** Operator words for the folder's own files; anything else shows its leaf. */
function fileChipLabel(deskRoot: string, path: string): string {
  const rel = path.startsWith(`${deskRoot}/`) ? path.slice(deskRoot.length + 1) : path;
  if (rel === 'report.md') return 'Report';
  if (rel === 'CRITERION.md') return 'Criterion';
  if (rel === '_radar.yaml') return 'Setup';
  return rel;
}

function sweepStatusLine(s: RailSweep): string {
  if (s.status === 'skipped' && s.error_reason === 'no_change')
    return 'Sweep ran — no change worth reporting';
  if (s.status === 'skipped' && s.error_reason === 'router_disabled')
    return 'Sweep skipped — the engine is unavailable';
  if (s.status === 'skipped') return `Sweep skipped${s.error_reason ? ` — ${s.error_reason}` : ''}`;
  return `Sweep failed${s.error_reason ? ` — ${s.error_reason}` : ''}`;
}

export function DeskActivityRail({
  deskRoot,
  sweeps,
  refreshNonce,
  onReverted,
  className,
}: {
  /** Absolute workspace path of the watched folder. */
  deskRoot: string;
  /** The hub view's recent sweep events (success rows are folded into their
   *  revisions; only non-success rows render as events). */
  sweeps: RailSweep[];
  /** Bump to refetch (a lane write landed, the member hit refresh). */
  refreshNonce: number;
  /** A revert landed — the parent should re-read the files it projects. */
  onReverted?: () => void;
  className?: string;
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
          .filter(
            (r) =>
              !r.path.endsWith('/_watch_signal.yaml') &&
              !r.path.includes('/briefs/'),
          )
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
  }, [deskRoot, refreshNonce]);

  const rows: RailRow[] = [
    ...(revisions ?? []).map<RailRow>((rev) => ({ kind: 'revision', at: rev.created_at, rev })),
    ...sweeps
      .filter((s) => s.status !== 'success' && s.created_at)
      .map<RailRow>((sweep) => ({ kind: 'sweep', at: sweep.created_at as string, sweep })),
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
        if (row.kind === 'sweep') {
          return (
            <li
              key={`sweep-${row.at}-${row.sweep.slug}`}
              className="flex items-baseline gap-2 px-3 py-2 text-xs text-muted-foreground"
            >
              <span
                className="shrink-0 tabular-nums"
                title={formatAbsolute(row.at)}
              >
                {formatRelativeTime(row.at, { rollToDate: true })}
              </span>
              <span className="min-w-0">{sweepStatusLine(row.sweep)}</span>
            </li>
          );
        }
        const { rev } = row;
        const revertable =
          rev.path.endsWith('/report.md') || rev.path.endsWith('/CRITERION.md');
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
                {fileChipLabel(deskRoot, rev.path)}
              </span>
              <span
                className={cn(
                  'shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-medium',
                  railAuthorChip(rev.authored_by),
                )}
                title={rev.authored_by}
              >
                {railAuthorLabel(rev.authored_by)}
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
