'use client';

/**
 * SourcePickerModal — pick the SOURCE for a Learn-from creation (ADR-452 D2).
 *
 * A source is usually a fresh arrival (an upload, an intake), so the picker is
 * the workspace recents feed + a filter box — not a full tree browser. Selecting
 * a row hands {path, name} back to the landing, which runs the creation flow.
 * Mirrors the RenameModal shell (portal + Z_CONFIRM tiers).
 */

import { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { FileText, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Z_CONFIRM_BACKDROP, Z_CONFIRM_DIALOG } from '@/lib/shell/z-tiers';
import { api } from '@/lib/api/client';

interface SourcePickerModalProps {
  /** The chosen target's label ("Document", "Deck", …) — null = closed. */
  targetLabel: string | null;
  onClose: () => void;
  onSelect: (source: { path: string; name: string }) => void;
}

function leaf(p: string): string {
  return p.slice(p.lastIndexOf('/') + 1);
}

export function SourcePickerModal({ targetLabel, onClose, onSelect }: SourcePickerModalProps) {
  const [rows, setRows] = useState<Array<{ path: string }> | null>(null);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    if (!targetLabel) return;
    setRows(null);
    setFilter('');
    api.workspace
      .recentRevisions(40)
      .then((res) => {
        // Dedup by path, newest first; hide machine-config + the extraction
        // plumbing (the raw is the source; its projection is read by the lane).
        const seen = new Set<string>();
        const out: Array<{ path: string }> = [];
        for (const r of res.revisions) {
          const p = r.path;
          if (seen.has(p) || leaf(p).startsWith('_') || p.endsWith('.extracted.md')) continue;
          seen.add(p);
          out.push({ path: p });
        }
        setRows(out);
      })
      .catch(() => setRows([]));
  }, [targetLabel]);

  const visible = useMemo(() => {
    if (!rows) return null;
    const f = filter.trim().toLowerCase();
    return f ? rows.filter((r) => r.path.toLowerCase().includes(f)) : rows;
  }, [rows, filter]);

  if (!targetLabel) return null;

  return createPortal(
    <>
      <div
        className="fixed inset-0 bg-black/50 animate-in fade-in duration-150"
        style={{ zIndex: Z_CONFIRM_BACKDROP }}
        onClick={onClose}
      />
      <div
        className="fixed inset-0 flex items-center justify-center p-4 pointer-events-none"
        style={{ zIndex: Z_CONFIRM_DIALOG }}
      >
        <div
          className="pointer-events-auto flex max-h-[70vh] w-full max-w-md flex-col rounded-lg border border-border bg-card p-5 shadow-xl animate-in fade-in zoom-in-95 duration-150"
          role="dialog"
          aria-modal="true"
        >
          <h3 className="text-base font-semibold text-card-foreground">
            {targetLabel} from a source
          </h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Pick the file to learn from — what you create will cite it.
          </p>
          <input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Filter recent files…"
            className="mt-3 w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
            aria-label="Filter files"
          />
          <div className="mt-2 min-h-0 flex-1 overflow-y-auto">
            {visible === null ? (
              <div className="flex items-center justify-center gap-2 p-6 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading…
              </div>
            ) : visible.length === 0 ? (
              <p className="p-6 text-center text-sm text-muted-foreground">
                Nothing matches. Add a file on the Files surface first.
              </p>
            ) : (
              <ul className="space-y-1">
                {visible.slice(0, 30).map((r) => (
                  <li key={r.path}>
                    <button
                      type="button"
                      onClick={() => onSelect({ path: r.path, name: leaf(r.path) })}
                      className={cn(
                        'flex w-full items-center gap-2 rounded-md border border-transparent px-2 py-1.5 text-left',
                        'transition-colors hover:border-border hover:bg-muted/40',
                      )}
                    >
                      <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                      <span className="min-w-0">
                        <span className="block truncate text-sm text-foreground">{leaf(r.path)}</span>
                        <span className="block truncate text-[11px] text-muted-foreground">
                          {r.path.replace(/^\/workspace\//, '')}
                        </span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="mt-4 flex justify-end">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-border px-3.5 py-1.5 text-sm text-foreground transition-colors hover:bg-muted/60"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </>,
    document.body,
  );
}
