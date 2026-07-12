'use client';

/**
 * StudioInsertMenu — the block palette (ADR-440 v1.1 → ADR-443 D7).
 *
 * Prompt-composer buttons rendered from the ONE kernel vocabulary
 * (GET /studio/vocabulary — the same source the lane's posture teaches from,
 * ADR-443 R4). Buttons PREFILL the composer with the right ask; nothing here
 * writes the artifact — the lane does, when the member sends.
 *
 * Operator words only in the chrome (ADR-443 D3): "Add" — never "compose".
 * Citation-backed kinds keep their pickers over the commons: Image (figure)
 * and Table open GET /studio/citable lists; Chart seeds the SVG-authoring
 * ask (plain-text authoring, ADR-440 D7).
 */

import { useEffect, useRef, useState } from 'react';
import { BarChart3, ImagePlus, Loader2, Plus, Table2 } from 'lucide-react';
import { api } from '@/lib/api/client';

interface Citable {
  images: Array<{ path: string; updated_at: string | null }>;
  tables: Array<{ path: string; updated_at: string | null }>;
}

interface VocabularyBlock {
  kind: string;
  label: string;
  description: string;
  group: string;
}

/** The ask each block kind seeds. Falls back to a generic add for kinds the
 *  kernel grows later — the palette never needs a code change per kind. */
const KIND_SEEDS: Record<string, string> = {
  prose: 'Add a text section about: ',
  callout: 'Add a callout that highlights: ',
  quote: 'Add a quote: ',
  checklist: 'Add a checklist of: ',
  metrics: 'Add a metrics row showing: ',
  chart: 'Create an SVG chart at ./assets/chart.svg, cite it in the document, showing: ',
};

const GROUP_LABELS: Record<string, string> = {
  content: 'Content',
  data: 'Data',
  media: 'Media',
};

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
  const [open, setOpen] = useState<null | 'image' | 'table' | 'add'>(null);
  const [citable, setCitable] = useState<Citable | null>(null);
  const [blocks, setBlocks] = useState<VocabularyBlock[] | null>(null);
  const [loading, setLoading] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const toggle = (panel: 'image' | 'table' | 'add') => {
    setOpen((cur) => (cur === panel ? null : panel));
    if (panel === 'add' && !blocks) {
      api.studio
        .vocabulary()
        .then((v) => setBlocks(v.blocks))
        .catch(() => setBlocks([]));
    }
    if ((panel === 'image' || panel === 'table') && !citable && !loading) {
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

  const pickCitable = (path: string) => {
    const rel = relPath(path);
    onSeed(
      open === 'image'
        ? `Insert the workspace image "${rel}" where it fits best. `
        : `Show the data from "${rel}" as a table in the document. `,
    );
    setOpen(null);
  };

  const pickBlock = (b: VocabularyBlock) => {
    // Citation-backed kinds route to their pickers; the rest seed directly.
    if (b.kind === 'figure') {
      toggle('image');
      return;
    }
    if (b.kind === 'table') {
      toggle('table');
      return;
    }
    onSeed(KIND_SEEDS[b.kind] ?? `Add a ${b.label.toLowerCase()} block: `);
    setOpen(null);
  };

  const items = open === 'image' ? citable?.images : open === 'table' ? citable?.tables : undefined;

  const groupedBlocks = (blocks ?? []).reduce<Record<string, VocabularyBlock[]>>((acc, b) => {
    (acc[b.group] = acc[b.group] ?? []).push(b);
    return acc;
  }, {});

  const btn =
    'inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[11px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground';

  return (
    <div ref={rootRef} className="relative flex items-center gap-1 border-b border-border px-2 py-1.5">
      <button type="button" className={btn} onClick={() => toggle('add')}>
        <Plus className="h-3 w-3" /> Add
      </button>
      <button type="button" className={btn} onClick={() => toggle('image')}>
        <ImagePlus className="h-3 w-3" /> Image
      </button>
      <button type="button" className={btn} onClick={() => toggle('table')}>
        <Table2 className="h-3 w-3" /> Table
      </button>
      <button
        type="button"
        className={btn}
        onClick={() => {
          onSeed(KIND_SEEDS.chart);
          setOpen(null);
        }}
      >
        <BarChart3 className="h-3 w-3" /> Chart
      </button>

      {open === 'add' && (
        <div className="absolute left-2 top-full z-20 mt-1 max-h-72 w-72 overflow-y-auto rounded-md border border-border bg-background p-1 shadow-md">
          {!blocks && (
            <div className="flex items-center justify-center gap-2 p-3 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading…
            </div>
          )}
          {Object.entries(groupedBlocks).map(([group, list]) => (
            <div key={group} className="mb-1">
              <p className="px-2 pb-0.5 pt-1.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                {GROUP_LABELS[group] ?? group}
              </p>
              {list.map((b) => (
                <button
                  key={b.kind}
                  type="button"
                  onClick={() => pickBlock(b)}
                  className="flex w-full flex-col rounded px-2 py-1.5 text-left hover:bg-muted/40"
                >
                  <span className="text-xs">{b.label}</span>
                  <span className="text-[10px] leading-snug text-muted-foreground">
                    {b.description}
                  </span>
                </button>
              ))}
            </div>
          ))}
        </div>
      )}

      {(open === 'image' || open === 'table') && (
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
                onClick={() => pickCitable(it.path)}
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
