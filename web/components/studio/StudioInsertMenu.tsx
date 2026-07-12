'use client';

/**
 * StudioToolbar (file keeps its historical name) — the EXECUTING toolbar
 * (ADR-444, superseding the v1.1 prompt-prefill strip).
 *
 * Buttons here EXECUTE deterministic structural operations at the canvas
 * selection — the PowerPoint/Notion model: Add → a real block lands in the
 * document; pick an image → a cited figure block is INSERTED; Slide → add a
 * slide from a container layout or re-lay the SELECTED slide (slide master).
 * Each execution is one operator-attributed, CAS-guarded revision through
 * the Studio's mechanical write door — no LLM, no prompt.
 *
 * The ONE exception: Chart still asks the lane (authoring an SVG is
 * generative judgment, not a deterministic op).
 *
 * Renders from the served kernel vocabulary (GET /studio/vocabulary) — the
 * same source the lane's posture teaches from (ADR-443 R4).
 */

import { useEffect, useRef, useState } from 'react';
import { ChevronDown, Loader2, Plus, Presentation, X } from 'lucide-react';
import { api } from '@/lib/api/client';

export interface StudioVocabulary {
  blocks: Array<{ kind: string; label: string; description: string; group: string; fragment: string }>;
  layouts: Array<{ slug: string; label: string; description: string }>;
  containers: Record<string, Array<{ slug: string; label: string; description: string; fragment: string }>>;
}

export interface StudioSelection {
  blockId: string | null;
  blockKind: string | null;
  slideIndex: number | null;
  text: string;
}

interface Citable {
  images: Array<{ path: string; updated_at: string | null }>;
  tables: Array<{ path: string; updated_at: string | null }>;
}

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

interface StudioToolbarProps {
  vocabulary: StudioVocabulary | null;
  /** The artifact's current layout slug — gates the Slide menu (deck). */
  layout: string;
  selection: StudioSelection | null;
  onClearSelection: () => void;
  /** EXECUTE: insert this block fragment at the selection. */
  onInsertBlock: (fragment: string, label: string) => void;
  /** EXECUTE: insert a cited block (figure/table) for a picked workspace file. */
  onInsertCited: (kind: 'figure' | 'table', path: string) => void;
  /** EXECUTE: add a slide from a container fragment (after the selection). */
  onAddSlide: (fragment: string, label: string) => void;
  /** EXECUTE: re-lay the SELECTED slide to a container (slide master). */
  onApplySlideLayout: (fragment: string, label: string) => void;
  /** The one generative ask (Chart) — seeds the lane. */
  onSeed: (text: string) => void;
}

export function StudioInsertMenu({
  vocabulary,
  layout,
  selection,
  onClearSelection,
  onInsertBlock,
  onInsertCited,
  onAddSlide,
  onApplySlideLayout,
  onSeed,
}: StudioToolbarProps) {
  const [open, setOpen] = useState<null | 'add' | 'slide' | 'image' | 'table'>(null);
  const [citable, setCitable] = useState<Citable | null>(null);
  const [loadingCitable, setLoadingCitable] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const openPicker = (panel: 'image' | 'table') => {
    setOpen(panel);
    if (!citable && !loadingCitable) {
      setLoadingCitable(true);
      api.studio
        .citable()
        .then(setCitable)
        .catch(() => setCitable({ images: [], tables: [] }))
        .finally(() => setLoadingCitable(false));
    }
  };

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(null);
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [open]);

  const blocks = vocabulary?.blocks ?? [];
  const containers = vocabulary?.containers?.[layout] ?? [];
  const grouped = blocks.reduce<Record<string, typeof blocks>>((acc, b) => {
    (acc[b.group] = acc[b.group] ?? []).push(b);
    return acc;
  }, {});

  const pickBlock = (b: StudioVocabulary['blocks'][number]) => {
    if (b.kind === 'figure') return openPicker('image');
    if (b.kind === 'table') return openPicker('table');
    if (b.kind === 'chart') {
      onSeed('Create an SVG chart at ./assets/chart.svg, cite it in the document, showing: ');
      setOpen(null);
      return;
    }
    onInsertBlock(b.fragment, b.label);
    setOpen(null);
  };

  const items = open === 'image' ? citable?.images : open === 'table' ? citable?.tables : undefined;

  const btn =
    'inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[11px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground disabled:opacity-40';
  const panel =
    'absolute left-2 top-full z-20 mt-1 max-h-72 w-80 overflow-y-auto rounded-md border border-border bg-background p-1 shadow-md';

  return (
    <div ref={rootRef} className="relative flex items-center gap-1 border-b border-border px-2 py-1.5">
      <button type="button" className={btn} onClick={() => setOpen(open === 'add' ? null : 'add')}>
        <Plus className="h-3 w-3" /> Add <ChevronDown className="h-3 w-3" />
      </button>
      {layout === 'deck' && (
        <button type="button" className={btn} onClick={() => setOpen(open === 'slide' ? null : 'slide')}>
          <Presentation className="h-3 w-3" /> Slide <ChevronDown className="h-3 w-3" />
        </button>
      )}

      {/* The selection chip — what the next Add/Slide op anchors to, and what
          the lane hears about on the next message. */}
      {selection && (
        <span className="ml-auto inline-flex min-w-0 items-center gap-1 rounded-full border border-indigo-300/60 bg-indigo-50/60 px-2 py-0.5 text-[10px] text-indigo-900 dark:bg-indigo-950/40 dark:text-indigo-200">
          <span className="truncate">
            {selection.blockKind
              ? `${selection.blockKind}${selection.blockId ? ` · ${selection.blockId}` : ''}`
              : selection.slideIndex != null
                ? `slide ${selection.slideIndex + 1}`
                : 'selection'}
          </span>
          <button type="button" onClick={onClearSelection} aria-label="Clear selection">
            <X className="h-3 w-3" />
          </button>
        </span>
      )}

      {open === 'add' && (
        <div className={panel}>
          {!vocabulary && (
            <div className="flex items-center justify-center gap-2 p-3 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading…
            </div>
          )}
          {Object.entries(grouped).map(([group, list]) => (
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
                  <span className="text-[10px] leading-snug text-muted-foreground">{b.description}</span>
                </button>
              ))}
            </div>
          ))}
        </div>
      )}

      {open === 'slide' && (
        <div className={panel}>
          <p className="px-2 pb-0.5 pt-1.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            Add a slide
          </p>
          {containers.map((c) => (
            <button
              key={`add-${c.slug}`}
              type="button"
              onClick={() => {
                onAddSlide(c.fragment, c.label);
                setOpen(null);
              }}
              className="flex w-full flex-col rounded px-2 py-1.5 text-left hover:bg-muted/40"
            >
              <span className="text-xs">{c.label}</span>
              <span className="text-[10px] leading-snug text-muted-foreground">{c.description}</span>
            </button>
          ))}
          <p className="px-2 pb-0.5 pt-2 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            Change selected slide to
          </p>
          {containers.map((c) => (
            <button
              key={`lay-${c.slug}`}
              type="button"
              disabled={!selection}
              title={selection ? undefined : 'Select something on a slide first'}
              onClick={() => {
                onApplySlideLayout(c.fragment, c.label);
                setOpen(null);
              }}
              className="flex w-full flex-col rounded px-2 py-1.5 text-left hover:bg-muted/40 disabled:opacity-40"
            >
              <span className="text-xs">{c.label}</span>
            </button>
          ))}
        </div>
      )}

      {(open === 'image' || open === 'table') && (
        <div className={panel}>
          {loadingCitable && (
            <div className="flex items-center justify-center gap-2 p-3 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading…
            </div>
          )}
          {!loadingCitable && (!items || items.length === 0) && (
            <p className="p-3 text-xs text-muted-foreground">
              {open === 'image'
                ? 'No images in the workspace yet — drop one into Files, or ask the chat for an SVG.'
                : 'No CSV files in the workspace yet.'}
            </p>
          )}
          {!loadingCitable &&
            items?.map((it) => (
              <button
                key={it.path}
                type="button"
                onClick={() => {
                  onInsertCited(open === 'image' ? 'figure' : 'table', it.path);
                  setOpen(null);
                }}
                className="flex w-full items-center justify-between gap-2 rounded px-2 py-1.5 text-left hover:bg-muted/40"
              >
                <span className="min-w-0">
                  <span className="block truncate text-xs">{baseName(it.path)}</span>
                  <span className="block truncate text-[10px] text-muted-foreground">{relPath(it.path)}</span>
                </span>
              </button>
            ))}
        </div>
      )}
    </div>
  );
}
