'use client';

/**
 * TrashView — the delete verb's two steps (ADR-400 D4 + ADR-478).
 *
 * Step one is trash-not-erase (archive, ADR-329/ADR-209): a deleted file becomes
 * a lifecycle='archived' revision — retained, attributed, recoverable. This
 * surface lists those files and offers Restore.
 *
 * Step two is permanent delete (ADR-478): the terminal, unrecoverable removal —
 * per-file ("Delete Permanently") and over-all ("Empty Trash"). Both confirm
 * first. The contract is unrecoverable-not-unremembered: the file and its bytes
 * go, every OTHER file's ledger is untouched. Owner-gated in a shared workspace
 * (the backend 403s a non-owner). A file a live file still cites is refused
 * (per-file: 409 naming the dependents) or skipped (empty: reported back).
 *
 * TWO ROW SHAPES, because there are two acts (2026-08-21). Deleting a FOLDER
 * fans out — one attributed archive revision per file under it — so a 40-file
 * folder would arrive here as 40 loose rows, and restoring it would mean 40
 * clicks and rebuilding the shape by hand. It comes back as ONE GROUP instead
 * ("ai-frontier · 40 items"), restored whole. Trash mirrors the act the operator
 * performed: they deleted one folder, so they see one thing.
 */

import { useCallback, useEffect, useState } from 'react';
import { Loader2, Trash2, Undo2, FileText, FolderClosed } from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { FileIcon } from './FileIcon';
import { formatAuthorLabelOrSystem } from '@/lib/workspace/attribution';
import { useFeedback } from '@/contexts/FeedbackContext';

interface TrashItem {
  path: string;
  filename: string;
  archived_at: string;
  authored_by: string | null;
}

/** A whole folder that was moved to Trash, restorable as ONE unit. `count` is
 *  FILES — a directory is not an item you deleted, it is where they were. */
interface TrashGroup {
  root: string;
  name: string;
  count: number;
  archived_at: string;
}

function detail(e: unknown, fallback: string): string {
  return e instanceof APIError
    ? (e.data as { detail?: string })?.detail || fallback
    : fallback;
}

export function TrashView() {
  // Gates AND outcomes both ride the canonical layer now — this file used
  // runAction for its outcomes while hand-rolling inline "second-click"
  // gates, which made permanent delete (the MOST destructive act on the
  // surface) carry the LIGHTEST confirmation in the app (transient-surfacing
  // streamline 2026-08-22).
  const { runAction, confirm: confirmDialog } = useFeedback();
  const [items, setItems] = useState<TrashItem[]>([]);
  const [groups, setGroups] = useState<TrashGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const r = await api.documents.trash();
      setItems(Array.isArray(r?.items) ? r.items : []);
      setGroups(Array.isArray(r?.groups) ? r.groups : []);
    } catch {
      setItems([]);
      setGroups([]);
    } finally {
      setLoading(false);
    }
  }, []);

  /** Restore a whole trashed folder — the inverse of the fan-out, in one act. */
  const restoreGroup = useCallback(async (root: string) => {
    setBusy(root);
    try {
      await runAction(() => api.documents.restoreTrashGroup(root), {
        pending: 'Restoring folder…',
        success: (res) => res.message || 'Restored',
        error: (e) => detail(e, 'Restore failed'),
      });
      setGroups((prev) => prev.filter((g) => g.root !== root));
    } catch {
      // toast surfaced; keep the row for retry
    } finally {
      setBusy(null);
    }
  }, [runAction]);

  useEffect(() => { load(); }, [load]);

  const restore = useCallback(async (path: string) => {
    setBusy(path);
    try {
      await runAction(() => api.documents.restore(path), {
        pending: 'Restoring…',
        success: 'Restored',
        error: (e) => detail(e, 'Restore failed'),
      });
      setItems((prev) => prev.filter((it) => it.path !== path));
    } catch {
      // toast surfaced; keep the row for retry
    } finally {
      setBusy(null);
    }
  }, [runAction]);

  const permanentDelete = useCallback(async (path: string, filename: string) => {
    const ok = await confirmDialog({
      title: 'Delete forever?',
      body: `"${filename}" cannot be recovered after this.`,
      confirmLabel: 'Delete forever',
      danger: true,
    });
    if (!ok) return;
    setBusy(path);
    try {
      await runAction(() => api.documents.permanentDelete(path), {
        pending: 'Deleting permanently…',
        success: 'Permanently deleted',
        error: (e) => detail(e, 'Delete failed'),
      });
      setItems((prev) => prev.filter((it) => it.path !== path));
    } catch {
      // toast surfaced (incl. the 409 "N files were made from this") — keep the row
    } finally {
      setBusy(null);
    }
  }, [runAction, confirmDialog]);

  const emptyTrash = useCallback(async () => {
    const ok = await confirmDialog({
      title: 'Empty Trash?',
      body: 'Everything here is deleted permanently. Files other work was made from are kept.',
      confirmLabel: 'Empty Trash',
      danger: true,
    });
    if (!ok) return;
    setBusy('__empty__');
    try {
      const res = await runAction(() => api.documents.emptyTrash(), {
        pending: 'Emptying trash…',
        success: 'Trash emptied',
        error: (e) => detail(e, 'Empty trash failed'),
      });
      // The per-file skip detail (cited files kept) isn't a failure, so surface
      // it as its own note rather than losing it behind the generic success line.
      if (res.skipped.length > 0) {
        // eslint-disable-next-line no-console
        console.info(`[trash] kept ${res.skipped.length} referenced file(s): ${res.skipped.join(', ')}`);
      }
      await load();
    } catch {
      // toast surfaced
    } finally {
      setBusy(null);
    }
  }, [runAction, load, confirmDialog]);

  // Groups and loose files are both ROWS. Counted together so the header, the
  // empty state and the Empty-Trash affordance all agree on "is there anything
  // in here" — three separate `items.length` checks would disagree the moment a
  // trash held only folders.
  const rowCount = items.length + groups.length;

  return (
    <div className="h-full overflow-y-auto px-6 py-4">
      <div className="mb-4 flex items-center gap-2">
        <Trash2 className="h-4 w-4 text-muted-foreground" />
        <h2 className="text-sm font-medium text-foreground">Trash</h2>
        {/* The header count is ROWS — what the operator is looking at — so a
            trashed folder counts as one thing, matching the one act that put it
            here. Its 40 files are named on the row itself. */}
        <span className="text-[11px] text-muted-foreground">
          {loading ? '' : `${rowCount} item${rowCount === 1 ? '' : 's'}`}
        </span>
        {!loading && rowCount > 0 && (
          <div className="ml-auto">
            <button
              type="button"
              onClick={emptyTrash}
              disabled={busy === '__empty__'}
              className="inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs text-muted-foreground hover:text-destructive disabled:opacity-50"
            >
              {busy === '__empty__' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
              Empty Trash
            </button>
          </div>
        )}
      </div>

      {loading ? (
        <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading trash…
        </div>
      ) : rowCount === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <Trash2 className="mb-3 h-8 w-8 text-muted-foreground/40" />
          <p className="text-sm text-muted-foreground">Trash is empty.</p>
          <p className="mt-1 text-xs text-muted-foreground/70">
            Files you delete land here — recoverable until you permanently delete
            them. Permanent delete cannot be undone.
          </p>
        </div>
      ) : (
        <div className="divide-y divide-border/50 overflow-hidden rounded-lg border border-border/60">
          {/* FOLDER GROUPS first — the biggest acts at the top, and the ones a
              member is most likely to be looking for after a mis-click.
              Restore-all only: permanently deleting a whole folder is a
              different, terminal decision (ADR-478 is per-file and owner-gated,
              and "Empty Trash" already reaches the whole trash). Offering a
              per-group permanent delete would be a new destructive act smuggled
              in beside a recovery affordance. */}
          {groups.map((g) => (
            <div key={g.root} className="flex items-center gap-3 px-4 py-2.5 hover:bg-muted/30">
              <FolderClosed className="h-5 w-5 shrink-0 text-muted-foreground" />
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm text-foreground">{g.name}</div>
                <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                  <span className="truncate">{g.root.replace('/workspace/', '')}</span>
                  <span>· {g.count} item{g.count === 1 ? '' : 's'}</span>
                  {g.archived_at && <span>· deleted {g.archived_at.slice(0, 10)}</span>}
                </div>
              </div>
              <button
                type="button"
                onClick={() => restoreGroup(g.root)}
                disabled={busy === g.root}
                className="inline-flex shrink-0 items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground disabled:opacity-50"
              >
                {busy === g.root ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Undo2 className="h-3.5 w-3.5" />}
                Restore all
              </button>
            </div>
          ))}
          {items.map((it) => (
            <div key={it.path} className="flex items-center gap-3 px-4 py-2.5 hover:bg-muted/30">
              <FileIcon filename={it.filename} size="md" />
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm text-foreground">{it.filename}</div>
                <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                  <FileText className="h-3 w-3 shrink-0" />
                  <span className="truncate">{it.path.replace('/workspace/', '')}</span>
                  {it.archived_at && <span>· deleted {it.archived_at.slice(0, 10)}</span>}
                  {it.authored_by && <span>· by {formatAuthorLabelOrSystem(it.authored_by)}</span>}
                </div>
              </div>

              <div className="flex shrink-0 items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => restore(it.path)}
                  disabled={busy === it.path}
                  className="inline-flex items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground disabled:opacity-50"
                >
                  {busy === it.path ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Undo2 className="h-3.5 w-3.5" />}
                  Restore
                </button>
                <button
                  type="button"
                  onClick={() => permanentDelete(it.path, it.filename)}
                  disabled={busy === it.path}
                  className="inline-flex items-center gap-1 rounded-md px-2.5 py-1.5 text-xs text-muted-foreground transition-colors hover:text-destructive disabled:opacity-50"
                  title="Permanently delete — cannot be undone"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
