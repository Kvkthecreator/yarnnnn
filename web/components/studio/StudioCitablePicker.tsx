'use client';

/**
 * StudioCitablePicker — the cited-file picker the located palette opens
 * (ADR-466 D4: insert is provenance-shaped, in ONE place).
 *
 * The picker-backed kinds (Image / Table / Gallery) used to live in the
 * toolbar's `Media ▾` because a palette row "that half-opens a different panel"
 * had no host. This IS that host: picking Image/Table/Gallery in the slash /
 * gutter palette swaps to this panel at the same anchor, and the pick lands a
 * CITED block at the located insertion point. With no orphan kinds left, the
 * Media button retired (the STUDIO.md named follow-on, executed).
 *
 * The component picks; the surface routes and writes (one door, unchanged).
 */

import { useEffect, useRef, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';

/** The picker-backed kinds — the ones whose palette pick opens THIS panel
 *  instead of dropping a fragment. (Chart is not here: it seeds the lane.) */
export const PICKER_KINDS = new Set(['figure', 'table', 'gallery']);

interface CitableItem {
  path: string;
  updated_at: string | null;
  /** The citation's PIN (ADR-440 D5) — the cited file's head revision at the
   *  moment of citation; stamped by the insert. */
  head_version_id: string | null;
}

function relPath(p: string): string {
  return p.replace(/^\/workspace\//, '');
}

function baseName(p: string): string {
  const parts = p.split('/');
  return parts[parts.length - 1] || p;
}

interface StudioCitablePickerProps {
  kind: 'figure' | 'table' | 'gallery';
  /** Anchor within the canvas wrapper (the palette's own position). */
  left: number;
  top: number;
  onPickOne: (path: string, pin: string | null) => void;
  onPickGallery: (paths: string[], pins: Record<string, string | null>) => void;
  onClose: () => void;
}

export function StudioCitablePicker({
  kind,
  left,
  top,
  onPickOne,
  onPickGallery,
  onClose,
}: StudioCitablePickerProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [items, setItems] = useState<CitableItem[] | null>(null);
  // Gallery = multi-select: taps toggle, the commit button cites them as ONE
  // block (ADR-456 W1).
  const [picked, setPicked] = useState<string[]>([]);

  useEffect(() => {
    let live = true;
    api.studio
      .citable()
      .then((c) => {
        if (live) setItems(kind === 'table' ? c.tables : c.images);
      })
      .catch(() => {
        if (live) setItems([]);
      });
    return () => {
      live = false;
    };
  }, [kind]);

  // Click-away (parent document), Escape, and the canvas's bridged in-frame
  // press (the iframe boundary is opaque to the document listener).
  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) onClose();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    const onFrame = (e: MessageEvent) => {
      if ((e.data as { type?: string } | null)?.type === 'yarnnn-canvas-press') onClose();
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    window.addEventListener('message', onFrame);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
      window.removeEventListener('message', onFrame);
    };
  }, [onClose]);

  const btn =
    'inline-flex items-center gap-1 whitespace-nowrap rounded-md border border-border px-2 py-1 text-[11px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground disabled:opacity-40';

  return (
    <div
      ref={rootRef}
      style={{ left, top }}
      className="absolute z-30 max-h-72 w-80 overflow-y-auto rounded-md border border-border bg-background p-1 shadow-lg"
    >
      <p className="px-2 pb-0.5 pt-1.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
        {kind === 'table' ? 'Insert a table from a CSV' : kind === 'gallery' ? 'Pick images for the gallery' : 'Insert an image from the workspace'}
      </p>
      {items == null && (
        <div className="flex items-center justify-center gap-2 p-3 text-xs text-muted-foreground">
          <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading…
        </div>
      )}
      {items != null && items.length === 0 && (
        <p className="p-3 text-xs text-muted-foreground">
          {kind === 'table'
            ? 'No CSV files in the workspace yet.'
            : 'No images in the workspace yet — drop one into Files, or ask the chat for an SVG.'}
        </p>
      )}
      {kind === 'gallery' && items != null && items.length > 0 && (
        <div className="sticky top-0 z-10 border-b border-border bg-background px-2 py-1.5">
          <button
            type="button"
            disabled={picked.length === 0}
            onClick={() => {
              const pins: Record<string, string | null> = {};
              for (const it of items) pins[it.path] = it.head_version_id;
              onPickGallery(picked, pins);
            }}
            className={`${btn} w-full justify-center`}
          >
            Insert gallery ({picked.length})
          </button>
        </div>
      )}
      {items?.map((it) => {
        const isPicked = kind === 'gallery' && picked.includes(it.path);
        return (
          <button
            key={it.path}
            type="button"
            onClick={() => {
              if (kind === 'gallery') {
                setPicked((cur) =>
                  cur.includes(it.path) ? cur.filter((p) => p !== it.path) : [...cur, it.path],
                );
                return;
              }
              onPickOne(it.path, it.head_version_id);
            }}
            className={`flex w-full items-center justify-between gap-2 rounded px-2 py-1.5 text-left hover:bg-muted/40 ${
              isPicked ? 'bg-indigo-50/60 dark:bg-indigo-950/40' : ''
            }`}
          >
            <span className="min-w-0">
              <span className="block truncate text-xs">{baseName(it.path)}</span>
              <span className="block truncate text-[10px] text-muted-foreground">
                {relPath(it.path)}
              </span>
            </span>
            {isPicked && <span className="shrink-0 text-[10px] text-indigo-600">✓</span>}
          </button>
        );
      })}
    </div>
  );
}
