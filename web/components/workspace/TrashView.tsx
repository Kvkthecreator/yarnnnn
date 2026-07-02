'use client';

/**
 * TrashView — the visible, reversible home of the delete verb (ADR-400 D4).
 *
 * Delete is already trash-not-erase (archive, ADR-329/ADR-209): a deleted file
 * becomes a lifecycle='archived' revision — retained, attributed, recoverable.
 * This surface makes that state visible: it lists the operator's archived files
 * (GET /documents/trash) and offers Restore (POST /documents/restore → a new
 * 'active' revision). There is NO hard-delete (ADR-400 Q3 — ADR-209 keeps
 * everything; Trash is a view, not an eraser).
 */

import { useCallback, useEffect, useState } from 'react';
import { Loader2, Trash2, Undo2, FileText } from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { FileIcon } from './FileIcon';
import { formatAuthorLabelOrSystem } from '@/lib/workspace/attribution';

interface TrashItem {
  path: string;
  filename: string;
  archived_at: string;
  authored_by: string | null;
}

export function TrashView() {
  const [items, setItems] = useState<TrashItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [restoring, setRestoring] = useState<string | null>(null);

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
    setRestoring(path);
    try {
      await api.documents.restore(path);
      setItems((prev) => prev.filter((it) => it.path !== path));
    } catch (e) {
      window.alert(e instanceof APIError ? (e.data as { detail?: string })?.detail || 'Restore failed' : 'Restore failed');
    } finally {
      setRestoring(null);
    }
  }, []);

  return (
    <div className="h-full overflow-y-auto px-6 py-4">
      <div className="mb-4 flex items-center gap-2">
        <Trash2 className="h-4 w-4 text-muted-foreground" />
        <h2 className="text-sm font-medium text-foreground">Trash</h2>
        <span className="text-[11px] text-muted-foreground">
          {loading ? '' : `${items.length} item${items.length === 1 ? '' : 's'}`}
        </span>
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
            Files you delete land here — recoverable, never erased. Deleting is
            reversible (ADR-209: your substrate is always retained).
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
              <button
                type="button"
                onClick={() => restore(it.path)}
                disabled={restoring === it.path}
                className="inline-flex shrink-0 items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground disabled:opacity-50"
              >
                {restoring === it.path ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Undo2 className="h-3.5 w-3.5" />}
                Restore
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
