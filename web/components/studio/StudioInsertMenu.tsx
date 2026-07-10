'use client';

/**
 * StudioInsertMenu — prompt-composer buttons (ADR-440 v1.1).
 *
 * Buttons that PREFILL the lane's composer with the right citation ask —
 * teaching the Studio's verbs by existing. NOT a second write path: nothing
 * here touches the artifact; the lane does, when the member sends.
 *
 * Image / Table open a picker over the commons (GET /studio/citable);
 * Chart seeds an SVG-authoring ask directly (SVG is plain-text authoring —
 * ADR-440 D7 scope clarification).
 */

import { useEffect, useRef, useState } from 'react';
import { BarChart3, ImagePlus, Loader2, Table2 } from 'lucide-react';
import { api } from '@/lib/api/client';

interface Citable {
  images: Array<{ path: string; updated_at: string | null }>;
  tables: Array<{ path: string; updated_at: string | null }>;
}

function relPath(p: string): string {
  return p.replace(/^\/workspace\//, '');
}

function baseName(p: string): string {
  const parts = p.split('/');
  return parts[parts.length - 1] || p;
}

interface StudioInsertMenuProps {
  onSeed: (text: string) => void;
}

export function StudioInsertMenu({ onSeed }: StudioInsertMenuProps) {
  const [open, setOpen] = useState<null | 'image' | 'table'>(null);
  const [citable, setCitable] = useState<Citable | null>(null);
  const [loading, setLoading] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const toggle = (kind: 'image' | 'table') => {
    setOpen((cur) => (cur === kind ? null : kind));
    if (!citable && !loading) {
      setLoading(true);
      api.studio
        .citable()
        .then(setCitable)
        .catch(() => setCitable({ images: [], tables: [] }))
        .finally(() => setLoading(false));
    }
  };

  // Close on outside click.
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(null);
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [open]);

  const items =
    open === 'image' ? citable?.images : open === 'table' ? citable?.tables : undefined;

  const pick = (path: string) => {
    const rel = relPath(path);
    onSeed(
      open === 'image'
        ? `Insert the workspace image "${rel}" where it fits best. `
        : `Show the data from "${rel}" as a table in the document. `,
    );
    setOpen(null);
  };

  const btn =
    'inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[11px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground';

  return (
    <div ref={rootRef} className="relative flex items-center gap-1 border-b border-border px-2 py-1.5">
      <button type="button" className={btn} onClick={() => toggle('image')}>
        <ImagePlus className="h-3 w-3" /> Image
      </button>
      <button type="button" className={btn} onClick={() => toggle('table')}>
        <Table2 className="h-3 w-3" /> Table
      </button>
      <button
        type="button"
        className={btn}
        onClick={() =>
          onSeed('Create an SVG chart at ./assets/chart.svg, cite it in the document, showing: ')
        }
      >
        <BarChart3 className="h-3 w-3" /> Chart
      </button>

      {open && (
        <div className="absolute left-2 top-full z-20 mt-1 max-h-64 w-80 overflow-y-auto rounded-md border border-border bg-background p-1 shadow-md">
          {loading && (
            <div className="flex items-center justify-center gap-2 p-3 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading…
            </div>
          )}
          {!loading && (!items || items.length === 0) && (
            <p className="p-3 text-xs text-muted-foreground">
              {open === 'image'
                ? 'No images in the workspace yet — drop one into Files, or ask for an SVG instead.'
                : 'No CSV files in the workspace yet.'}
            </p>
          )}
          {!loading &&
            items?.map((it) => (
              <button
                key={it.path}
                type="button"
                onClick={() => pick(it.path)}
                className="flex w-full items-center justify-between gap-2 rounded px-2 py-1.5 text-left hover:bg-muted/40"
              >
                <span className="min-w-0">
                  <span className="block truncate text-xs">{baseName(it.path)}</span>
                  <span className="block truncate text-[10px] text-muted-foreground">
                    {relPath(it.path)}
                  </span>
                </span>
              </button>
            ))}
        </div>
      )}
    </div>
  );
}
