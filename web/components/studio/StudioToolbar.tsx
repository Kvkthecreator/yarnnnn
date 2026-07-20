'use client';

/**
 * StudioToolbar — the DOCUMENT-grain toolbar (ADR-444 executing toolbar,
 * grain-realigned by ADR-453 D3; renamed from StudioInsertMenu).
 *
 * Verbs, in operator words:
 *  - Media +             — the picker-backed block kinds (Image/Table/Gallery)
 *                          that the located palette cannot serve, plus Chart.
 *  - New slide/section + — the page-grain structural act, first-class: an
 *                          arrangement GALLERY with derived wireframe
 *                          thumbnails (ADR-447 D7.1 lands here).
 *
 * The selection chip is GONE (2026-07-15) — ADR-453 D3's "acknowledgment" was
 * the receipt for a selection-gated world that ADR-458 replaced with hover.
 * The navigator's ring + the canvas marking + the Design tab's scope already
 * say it; the chip was the third telling. The selection STATE is untouched.
 *
 * "Re-arrange" (change THIS page's arrangement) is selection-scoped and lives
 * in the Design tab's page scope (ADR-453 D4) — the old mixed-grain
 * "Arrange ▾" menu is deleted. Every button EXECUTES a deterministic op
 * through the one mechanical write door; Chart stays the one generative ask
 * (seeds the lane).
 */

import { useEffect, useRef, useState } from 'react';
import { Image as ImageIcon, LayoutGrid, LayoutTemplate, Loader2, Plus } from 'lucide-react';
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

/** A MEASURE (ADR-461 D4) — the one continuous property. A token's values are
 *  enumerated and the kernel pre-declares a selector per value; a measure's are
 *  not, so the kernel pre-declares the MECHANISM (`width: var(--yw, auto)`) and
 *  the element carries the value. Bounded: free WITHIN its frame, never
 *  unbounded — which is why `applies` is deck + media only (a slide has a
 *  frame; a page has only a viewport to guess at). */
export interface StudioMeasure {
  key: string;
  label: string;
  applies: string[];
  unit: string;
  min: number;
  max: number;
  css_var: string;
  description: string;
}

export interface StudioVocabulary {
  blocks: Array<{ kind: string; label: string; description: string; group: string; fragment: string }>;
  layouts: Array<{ slug: string; label: string; description: string; mode: 'flow' | 'paged' }>;
  arrangements: Record<string, StudioArrangement[]>;
  tokens: StudioToken[];
  /** ADR-461 D4 — the measures: a property whose MECHANISM is enumerable but
   *  whose VALUE is not (the kernel pre-declares `var()`, the element carries
   *  the value). Served WITH its bound, so nothing downstream invents one. */
  measures: StudioMeasure[];
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

/** ADR-466 D5 — the galleries forewarn instead of post-failing: a slotless
 *  arrangement applied to a page that holds content MOVES that content to a
 *  new content page (the handler's resolution). The note says so where the
 *  choice is made. Shared by the toolbar's Layout gallery and the Properties
 *  page scope's Re-arrange gallery. */
export function arrangementCarryNote(
  a: Pick<StudioArrangement, 'slots'>,
  carriedCount: number | null,
  pageNoun: string,
): string | null {
  const n = carriedCount ?? 0;
  if (n > 0 && a.slots.length === 0) {
    return `content → new ${pageNoun}`;
  }
  return null;
}

interface Citable {
  // `head_version_id` is the citation's PIN (ADR-440 D5) — served so the
  // insert can stamp it at the moment the citation is made.
  images: Array<{ path: string; updated_at: string | null; head_version_id: string | null }>;
  tables: Array<{ path: string; updated_at: string | null; head_version_id: string | null }>;
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
  /** The layout's composition mode (kernel-named). `paged` gets the New-‹noun›
   *  gallery; `flow` has no page unit to offer. */
  isPaged: boolean;
  /** EXECUTE: insert this block fragment at the selection. */
  onInsertBlock: (fragment: string, label: string) => void;
  /** EXECUTE: insert a cited block (figure/table) for a picked workspace file. */
  /** EXECUTE: insert a cited block (figure/table), PINNED to the cited file's
   *  head revision at the moment of citation (ADR-440 D5). */
  onInsertCited: (kind: 'figure' | 'table', path: string, pin?: string | null) => void;
  /** EXECUTE: insert a gallery block citing the picked images (ADR-456 W1). */
  onInsertGallery: (paths: string[], pins?: Record<string, string | null>) => void;
  /** EXECUTE: add a new page (slide/section) from the gallery. */
  onAddArrangement: (fragment: string, label: string) => void;
  /** EXECUTE: re-lay the CURRENT page (ADR-466 D5 — the PowerPoint pair: Layout
   *  beside New slide; same gallery as the Properties page scope, two mounts). */
  onApplyArrangement: (a: StudioArrangement) => void;
  /** Blocks the anchored page would carry through an arrangement change —
   *  drives the carry note on slotless thumbs. */
  carriedCount: number | null;
  /** The anchored page's current arrangement slug (highlighted in Layout). */
  currentArrange: string | null;
  /** Whether a page can be resolved from the selection — Layout disables
   *  (with a teaching title) when nothing anchors it. */
  hasPageAnchor: boolean;
  /** The one generative ask (Chart) — seeds the lane. */
  onSeed: (text: string) => void;
}

export function StudioToolbar({
  vocabulary,
  layout,
  isPaged,
  onInsertBlock,
  onInsertCited,
  onInsertGallery,
  onAddArrangement,
  onApplyArrangement,
  carriedCount,
  currentArrange,
  hasPageAnchor,
  onSeed,
}: StudioToolbarProps) {
  // ADR-447/453: a deck's page is a "slide"; a document/article's is a
  // "section" — the operator word follows the layout.
  const pageNoun = layout === 'deck' ? 'slide' : 'section';
  const [open, setOpen] = useState<null | 'insert' | 'new' | 'layout' | 'image' | 'table' | 'gallery'>(null);
  const [citable, setCitable] = useState<Citable | null>(null);
  const [loadingCitable, setLoadingCitable] = useState(false);
  // The gallery picker's multi-select (ADR-456 W1) — N cited images, ONE block.
  const [galleryPick, setGalleryPick] = useState<string[]>([]);
  const rootRef = useRef<HTMLDivElement>(null);
  // The trigger cluster (buttons + their panels) — the click-away boundary.
  // Deliberately NOT rootRef, which spans the row's full flex-1 width.
  const menuRef = useRef<HTMLDivElement>(null);

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

  // Click-away + Escape. Two things this must get right, both learned the hard
  // way (2026-07-15):
  //
  // 1. The listener anchors on `menuRef` (the trigger + its panel), NOT on the
  //    whole toolbar row. `rootRef` is `flex-1`, so it spans the wide empty
  //    stretch between the crumb and the zoom — clicking that apparently-blank
  //    toolbar counted as "inside" and the panel never closed.
  // 2. The canvas is an IFRAME: a mousedown on the document never reaches this
  //    listener (the same boundary StudioSlashPalette documents). The canvas
  //    bridges its in-frame presses out as `yarnnn-canvas-press`, so clicking
  //    the artifact — the most natural "click outside" — closes the panel too.
  useEffect(() => {
    if (!open) return;
    const close = () => setOpen(null);
    const onDown = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) close();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
    };
    const onFrame = (e: MessageEvent) => {
      if ((e.data as { type?: string } | null)?.type === 'yarnnn-canvas-press') close();
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    window.addEventListener('message', onFrame);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
      window.removeEventListener('message', onFrame);
    };
  }, [open]);

  const blocks = vocabulary?.blocks ?? [];
  const arrangements = vocabulary?.arrangements?.[layout] ?? [];
  // The Media panel carries ONLY the picker-backed kinds — the ones a located
  // entrance (the gutter's +, or `/`) cannot serve because they open a file
  // picker instead of dropping a fragment. They are exactly the slash palette's
  // SLASH_EXCLUDED set, kept in sync by construction: everything else is
  // reachable at the pointer, and only these would be stranded without a home.
  // `chart` rides along — it seeds the lane rather than inserting, so it has no
  // located gesture either.
  const MEDIA_KINDS = new Set(['figure', 'table', 'gallery', 'chart']);
  const grouped = blocks
    .filter((b) => MEDIA_KINDS.has(b.kind))
    .reduce<Record<string, typeof blocks>>((acc, b) => {
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
  // Anchored to the TRIGGER CLUSTER (menuRef), not the row: `left-2` against a
  // flex-1 row put both panels at the row's left edge regardless of which button
  // opened them. `z-30` matches the sibling Studio popovers (StudioNewMenu,
  // StudioSlashPalette) — `z-20` lost to them.
  const panel =
    'absolute left-0 top-full z-30 mt-1 max-h-72 w-80 overflow-y-auto rounded-md border border-border bg-background p-1 shadow-md';

  return (
    // NOTE: this row must NOT become a scroll container (`overflow-x-auto`) —
    // the dropdown panels are positioned `absolute top-full`, so any overflow
    // clipping would cut them off below the row. `min-w-0` lets the row yield
    // width to its shrink-0 neighbours (the zoom cluster) instead of painting
    // over them — it was the deleted selection chip that used to be the elastic
    // element, and without a replacement the buttons overflowed onto the zoom.
    <div ref={rootRef} className="relative flex min-w-0 items-center gap-1 border-b border-border px-2 py-1.5">
      <div ref={menuRef} className="relative flex min-w-0 items-center gap-1">
      {/* "+ Insert" is GONE as a general insert (2026-07-15) — it was the one
          affordance with no LOCATION, falling back to the last block the caret
          touched or the document end, so where a block landed was effectively
          arbitrary. Every ordinary block kind is now inserted from a LOCATED
          entrance: the gutter's + at the hovered row, or `/` in an empty block.

          It survives ONLY as "Media" — the picker-backed kinds (Image / Table /
          Gallery, SLASH_EXCLUDED in the slash palette because they open a file
          picker rather than drop a fragment). Deleting the button outright
          would strand them with no way in. Routing them through the located
          palette is the right end state and its own change; this narrows the
          button to exactly what nothing else can reach, rather than shipping a
          hole. Tracked as the follow-on in docs/design/STUDIO.md.

          "New ‹noun›" is PAGED-only. In a flow artifact there is no section to
          insert — blocks flow — so the gallery was offering a page unit to a
          model that has no pages. */}
      {/* `+` not `▾`: these ADD something. A chevron promises a menu of
          options to pick among (a filter, a view); a plus promises a thing
          appears. Both open a panel — the glyph should say what the panel is
          FOR, and the OS teaches `+` as "insert" everywhere else (the gutter's
          + is the same promise at the row grain). */}
      <button type="button" className={btn} onClick={() => setOpen(open === 'insert' ? null : 'insert')}>
        <ImageIcon className="h-3 w-3" /> Media <Plus className="h-3 w-3" />
      </button>
      {isPaged && arrangements.length > 0 && (
        <button type="button" className={btn} onClick={() => setOpen(open === 'new' ? null : 'new')}>
          <LayoutGrid className="h-3 w-3" /> New {pageNoun} <Plus className="h-3 w-3" />
        </button>
      )}
      {/* Layout — re-lay the CURRENT page (ADR-466 D5): the PowerPoint pair,
          New slide beside Layout. Same gallery as the Properties page scope
          (one component grammar, two mounts); needs an anchored page. */}
      {isPaged && arrangements.length > 0 && (
        <button
          type="button"
          className={btn}
          disabled={!hasPageAnchor}
          title={
            hasPageAnchor
              ? `Change this ${pageNoun}'s layout`
              : `Select a ${pageNoun} first — click it on the canvas or in the strip`
          }
          onClick={() => setOpen(open === 'layout' ? null : 'layout')}
        >
          <LayoutTemplate className="h-3 w-3" /> Layout
        </button>
      )}

      {/* The selection chip is DELETED (2026-07-15). ADR-453 D3 gave it one
          job — "the acknowledgment" — for a world where every affordance was
          selection-gated (ADR-458 §1: "click → toolbar chip + Design tab"), so
          the chip was the receipt proving the click landed. ADR-458 moved the
          entrance to HOVER (the gutter's + / ⋮⋮ need no selection), and the
          receipt lost its errand: there is no longer a gated act it unlocks.

          What remained was a third rendering of one fact — the navigator
          already rings the slide indigo, the canvas already marks it, and the
          Design tab already flips to page scope. Its ✕ was the only live
          affordance, and clicking the canvas margin already clears the same
          selection through the same handler (the ADR-453 grain ladder).

          The STATE (`selection`) is untouched and still load-bearing: it
          anchors every op and scopes the Design tab. Only its third display
          is gone. */}

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

      {/* The Layout gallery — re-lay the current page (ADR-466 D5). Slotless
          thumbs carry the amber note: applying one moves this page's content
          to a new content page (the handler's resolution), never a dead-end. */}
      {open === 'layout' && (
        <div className={panel}>
          <p className="px-2 pb-1 pt-1.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            Change this {pageNoun} to
          </p>
          <div className="grid grid-cols-2 gap-1.5 p-1">
            {arrangements.map((a) => {
              const note = arrangementCarryNote(a, carriedCount, pageNoun);
              const current = currentArrange === a.slug;
              return (
                <button
                  key={a.slug}
                  type="button"
                  title={
                    note
                      ? `${a.description} — this ${pageNoun}'s content moves to a new content ${pageNoun} after it.`
                      : a.description
                  }
                  onClick={() => {
                    onApplyArrangement(a);
                    setOpen(null);
                  }}
                  className={`flex flex-col gap-1 rounded-md border p-1.5 text-left hover:bg-muted/20 ${
                    current ? 'border-indigo-400' : 'border-transparent hover:border-border'
                  }`}
                >
                  <ArrangementThumb slots={a.slots} fragment={a.fragment} />
                  <span className="truncate text-[11px]">{a.label}</span>
                  {note && (
                    <span className="truncate text-[9px] leading-tight text-amber-600 dark:text-amber-500">
                      {note}
                    </span>
                  )}
                </button>
              );
            })}
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
                  // Pins, keyed by path — the picked rows carry their head rev.
                  const pins: Record<string, string | null> = {};
                  for (const it of items ?? []) pins[it.path] = it.head_version_id;
                  onInsertGallery(galleryPick, pins);
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
                    onInsertCited(
                      open === 'image' ? 'figure' : 'table',
                      it.path,
                      it.head_version_id,
                    );
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
    </div>
  );
}
