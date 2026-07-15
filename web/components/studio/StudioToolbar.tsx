'use client';

/**
 * StudioToolbar — the DOCUMENT-grain toolbar (ADR-444 executing toolbar,
 * grain-realigned by ADR-453 D3; renamed from StudioInsertMenu).
 *
 * Verbs, in operator words:
 *  - Insert ▾            — block-grain content units into the current
 *                          flow/slot (the former "Add", honestly named).
 *  - New slide/section ▾ — the page-grain structural act, first-class: an
 *                          arrangement GALLERY with derived wireframe
 *                          thumbnails (ADR-447 D7.1 lands here).
 *  - a minimal selection chip — identity + clear (the acknowledgment; the
 *                          selection's VERBS live in the Design tab).
 *
 * "Re-arrange" (change THIS page's arrangement) is selection-scoped and lives
 * in the Design tab's page scope (ADR-453 D4) — the old mixed-grain
 * "Arrange ▾" menu is deleted. Every button EXECUTES a deterministic op
 * through the one mechanical write door; Chart stays the one generative ask
 * (seeds the lane).
 */

import { useEffect, useRef, useState } from 'react';
import { ChevronDown, LayoutGrid, Loader2, Plus, X } from 'lucide-react';
import { api } from '@/lib/api/client';
import { ArrangementThumb } from './ArrangementThumb';

/** An arrangement (ADR-447) — the composition shape of a page/slide. `slots`
 *  carry {name, role}; role gates what can land in a slot (ADR-453 D5). */
export interface StudioArrangement {
  slug: string;
  label: string;
  description: string;
  grain: string;
  slots: Array<{ name: string; role: string }>;
  fragment: string;
}

/** A property token family (ADR-453 D1) — tokens, not pixels. */
export interface StudioToken {
  key: string;
  label: string;
  applies: string[];
  values: Array<{ value: string; label: string }>;
  description: string;
}

export interface StudioVocabulary {
  blocks: Array<{ kind: string; label: string; description: string; group: string; fragment: string }>;
  layouts: Array<{ slug: string; label: string; description: string }>;
  arrangements: Record<string, StudioArrangement[]>;
  tokens: StudioToken[];
  media_kinds: string[];
  kernel_css_version: number;
  kernel_style_element: string;
  design_systems: Array<{ name: string; manifest_path: string; folder: string; css: string[] }>;
}

/** The canvas selection (ADR-444/446, slot + page grains added by ADR-453):
 *  blockId set → block grain; slot set (no block) → slot grain; otherwise a
 *  page grain when slideIndex/pageIndex is known. */
export interface StudioSelection {
  blockId: string | null;
  blockKind: string | null;
  slideIndex: number | null;
  pageIndex: number | null;
  slot: string | null;
  arrange: string | null;
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
  /** The artifact's current layout slug — selects the arrangement set + noun. */
  layout: string;
  selection: StudioSelection | null;
  onClearSelection: () => void;
  /** EXECUTE: insert this block fragment at the selection. */
  onInsertBlock: (fragment: string, label: string) => void;
  /** EXECUTE: insert a cited block (figure/table) for a picked workspace file. */
  onInsertCited: (kind: 'figure' | 'table', path: string) => void;
  /** EXECUTE: insert a gallery block citing the picked images (ADR-456 W1). */
  onInsertGallery: (paths: string[]) => void;
  /** EXECUTE: add a new page (slide/section) from the gallery. */
  onAddArrangement: (fragment: string, label: string) => void;
  /** The one generative ask (Chart) — seeds the lane. */
  onSeed: (text: string) => void;
}

export function StudioToolbar({
  vocabulary,
  layout,
  selection,
  onClearSelection,
  onInsertBlock,
  onInsertCited,
  onInsertGallery,
  onAddArrangement,
  onSeed,
}: StudioToolbarProps) {
  // ADR-447/453: a deck's page is a "slide"; a document/article's is a
  // "section" — the operator word follows the layout.
  const pageNoun = layout === 'deck' ? 'slide' : 'section';
  const [open, setOpen] = useState<null | 'insert' | 'new' | 'image' | 'table' | 'gallery'>(null);
  const [citable, setCitable] = useState<Citable | null>(null);
  const [loadingCitable, setLoadingCitable] = useState(false);
  // The gallery picker's multi-select (ADR-456 W1) — N cited images, ONE block.
  const [galleryPick, setGalleryPick] = useState<string[]>([]);
  const rootRef = useRef<HTMLDivElement>(null);

  const openPicker = (panel: 'image' | 'table' | 'gallery') => {
    setOpen(panel);
    if (panel === 'gallery') setGalleryPick([]);
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
  const arrangements = vocabulary?.arrangements?.[layout] ?? [];
  const grouped = blocks.reduce<Record<string, typeof blocks>>((acc, b) => {
    (acc[b.group] = acc[b.group] ?? []).push(b);
    return acc;
  }, {});

  const pickBlock = (b: StudioVocabulary['blocks'][number]) => {
    if (b.kind === 'figure') return openPicker('image');
    if (b.kind === 'gallery') return openPicker('gallery');
    if (b.kind === 'table') return openPicker('table');
    if (b.kind === 'chart') {
      onSeed('Create an SVG chart at ./assets/chart.svg, cite it in the document, showing: ');
      setOpen(null);
      return;
    }
    onInsertBlock(b.fragment, b.label);
    setOpen(null);
  };

  const items =
    open === 'image' || open === 'gallery'
      ? citable?.images
      : open === 'table'
        ? citable?.tables
        : undefined;

  // shrink-0 + whitespace-nowrap: a flex child is shrinkable BY DEFAULT, so
  // when the row ran out of width (the chat panel open on a narrow viewport)
  // these triggers compressed below their text and the label wrapped mid-button
  // — "New / — / slide" stacked three lines tall, buckling the row. A control's
  // label is its meaning: it never wraps. The row scrolls instead (see the root).
  const btn =
    'inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-md border border-border px-2 py-1 text-[11px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground disabled:opacity-40';
  const panel =
    'absolute left-2 top-full z-20 mt-1 max-h-72 w-80 overflow-y-auto rounded-md border border-border bg-background p-1 shadow-md';

  return (
    // NOTE: this row must NOT become a scroll container (`overflow-x-auto`) —
    // the dropdown panels are positioned `absolute top-full` against it, so any
    // overflow clipping would cut them off below the row. The controls simply
    // never shrink (`btn` carries shrink-0 + whitespace-nowrap); the row's own
    // parent gives it the width, and the selection chip (`min-w-0` + truncate)
    // is the elastic part that yields first.
    <div ref={rootRef} className="relative flex items-center gap-1 border-b border-border px-2 py-1.5">
      <button type="button" className={btn} onClick={() => setOpen(open === 'insert' ? null : 'insert')}>
        <Plus className="h-3 w-3" /> Insert <ChevronDown className="h-3 w-3" />
      </button>
      {arrangements.length > 0 && (
        <button type="button" className={btn} onClick={() => setOpen(open === 'new' ? null : 'new')}>
          <LayoutGrid className="h-3 w-3" /> New {pageNoun} <ChevronDown className="h-3 w-3" />
        </button>
      )}

      {/* The minimal selection chip (ADR-453 D3): identity + clear. It is the
          acknowledgment and the anchor indicator — the selection's VERBS and
          properties live in the Design tab. */}
      {selection && (
        <div className="ml-auto flex min-w-0 items-center gap-1">
          <span className="inline-flex min-w-0 items-center gap-1 rounded-full border border-indigo-300/60 bg-indigo-50/60 px-2 py-0.5 text-[10px] text-indigo-900 dark:bg-indigo-950/40 dark:text-indigo-200">
            <span className="truncate">
              {selection.blockKind
                ? `${selection.blockKind}${selection.blockId ? ` · ${selection.blockId}` : ''}`
                : selection.slot
                  ? `slot · ${selection.slot}`
                  : selection.slideIndex != null
                    ? `slide ${selection.slideIndex + 1}`
                    : selection.pageIndex != null
                      ? `${pageNoun} ${selection.pageIndex + 1}`
                      : 'selection'}
            </span>
            <button type="button" onClick={onClearSelection} aria-label="Clear selection">
              <X className="h-3 w-3" />
            </button>
          </span>
        </div>
      )}

      {open === 'insert' && (
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

      {/* The New ‹slide|section› gallery — arrangement wireframes (D7.1). */}
      {open === 'new' && (
        <div className={panel}>
          <p className="px-2 pb-1 pt-1.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            New {pageNoun}
          </p>
          <div className="grid grid-cols-2 gap-1.5 p-1">
            {arrangements.map((a) => (
              <button
                key={a.slug}
                type="button"
                onClick={() => {
                  onAddArrangement(a.fragment, a.label);
                  setOpen(null);
                }}
                title={a.description}
                className="flex flex-col gap-1 rounded-md border border-transparent p-1.5 text-left hover:border-border hover:bg-muted/20"
              >
                <ArrangementThumb slots={a.slots} fragment={a.fragment} />
                <span className="truncate text-[11px]">{a.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {(open === 'image' || open === 'table' || open === 'gallery') && (
        <div className={panel}>
          {loadingCitable && (
            <div className="flex items-center justify-center gap-2 p-3 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading…
            </div>
          )}
          {!loadingCitable && (!items || items.length === 0) && (
            <p className="p-3 text-xs text-muted-foreground">
              {open === 'table'
                ? 'No CSV files in the workspace yet.'
                : 'No images in the workspace yet — drop one into Files, or ask the chat for an SVG.'}
            </p>
          )}
          {/* Gallery = multi-select: taps toggle, the button below commits ONE
              block citing all picked images (ADR-456 W1). */}
          {open === 'gallery' && !loadingCitable && items && items.length > 0 && (
            <div className="sticky top-0 z-10 border-b border-border bg-background px-2 py-1.5">
              <button
                type="button"
                disabled={galleryPick.length === 0}
                onClick={() => {
                  onInsertGallery(galleryPick);
                  setOpen(null);
                }}
                className={`${btn} w-full justify-center`}
              >
                Insert gallery ({galleryPick.length})
              </button>
            </div>
          )}
          {!loadingCitable &&
            items?.map((it) => {
              const picked = open === 'gallery' && galleryPick.includes(it.path);
              return (
                <button
                  key={it.path}
                  type="button"
                  onClick={() => {
                    if (open === 'gallery') {
                      setGalleryPick((cur) =>
                        cur.includes(it.path)
                          ? cur.filter((p) => p !== it.path)
                          : [...cur, it.path],
                      );
                      return;
                    }
                    onInsertCited(open === 'image' ? 'figure' : 'table', it.path);
                    setOpen(null);
                  }}
                  className={`flex w-full items-center justify-between gap-2 rounded px-2 py-1.5 text-left hover:bg-muted/40 ${
                    picked ? 'bg-indigo-50/60 dark:bg-indigo-950/40' : ''
                  }`}
                >
                  <span className="min-w-0">
                    <span className="block truncate text-xs">{baseName(it.path)}</span>
                    <span className="block truncate text-[10px] text-muted-foreground">{relPath(it.path)}</span>
                  </span>
                  {picked && <span className="shrink-0 text-[10px] text-indigo-600">✓</span>}
                </button>
              );
            })}
        </div>
      )}
    </div>
  );
}
