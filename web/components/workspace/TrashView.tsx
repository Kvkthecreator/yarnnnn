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
 */

import { useCallback, useEffect, useState } from 'react';
import { Loader2, Trash2, Undo2, FileText, AlertTriangle } from 'lucide-react';
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

function detail(e: unknown, fallback: string): string {
  return e instanceof APIError
    ? (e.data as { detail?: string })?.detail || fallback
    : fallback;
}

export function TrashView() {
  const { runAction } = useFeedback();
  const [items, setItems] = useState<TrashItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  // Two-step confirm, per row and for the whole trash. `null` = nothing armed.
  const [confirmingDelete, setConfirmingDelete] = useState<string | null>(null);
  const [confirmingEmpty, setConfirmingEmpty] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await api.documents.trash();
      setItems(Array.isArray(r?.items) ? r.items : []);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

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

  const permanentDelete = useCallback(async (path: string) => {
    setBusy(path);
    setConfirmingDelete(null);
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
  }, [runAction]);

  const emptyTrash = useCallback(async () => {
    setBusy('__empty__');
    setConfirmingEmpty(false);
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
  }, [runAction, load]);

  return (
    <div className="h-full overflow-y-auto px-6 py-4">
      <div className="mb-4 flex items-center gap-2">
        <Trash2 className="h-4 w-4 text-muted-foreground" />
        <h2 className="text-sm font-medium text-foreground">Trash</h2>
        <span className="text-[11px] text-muted-foreground">
          {loading ? '' : `${items.length} item${items.length === 1 ? '' : 's'}`}
        </span>
        {!loading && items.length > 0 && (
          <div className="ml-auto">
            {confirmingEmpty ? (
              <div className="flex items-center gap-2">
                <span className="text-[11px] text-destructive">Delete all permanently?</span>
                <button
                  type="button"
                  onClick={() => setConfirmingEmpty(false)}
                  className="rounded-md px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={emptyTrash}
                  disabled={busy === '__empty__'}
                  className="inline-flex items-center gap-1 rounded-md border border-destructive/50 px-2.5 py-1 text-xs font-medium text-destructive hover:bg-destructive/10 disabled:opacity-50"
                >
                  {busy === '__empty__' && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  Empty Trash
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setConfirmingEmpty(true)}
                className="inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs text-muted-foreground hover:text-destructive"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Empty Trash
              </button>
            )}
          </div>
        )}
      </div>

      {loading ? (
        <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading trash…
        </div>
      ) : items.length === 0 ? (
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

              {confirmingDelete === it.path ? (
                <div className="flex shrink-0 items-center gap-1.5">
                  <span className="text-[11px] text-destructive">Delete forever?</span>
                  <button
                    type="button"
                    onClick={() => setConfirmingDelete(null)}
                    className="rounded-md px-2 py-1.5 text-xs text-muted-foreground hover:text-foreground"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => permanentDelete(it.path)}
                    disabled={busy === it.path}
                    className="inline-flex items-center gap-1 rounded-md border border-destructive/50 px-2.5 py-1.5 text-xs font-medium text-destructive hover:bg-destructive/10 disabled:opacity-50"
                  >
                    {busy === it.path ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <AlertTriangle className="h-3.5 w-3.5" />}
                    Confirm
                  </button>
                </div>
              ) : (
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
                    onClick={() => setConfirmingDelete(it.path)}
                    disabled={busy === it.path}
                    className="inline-flex items-center gap-1 rounded-md px-2.5 py-1.5 text-xs text-muted-foreground transition-colors hover:text-destructive disabled:opacity-50"
                    title="Permanently delete — cannot be undone"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Delete
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
