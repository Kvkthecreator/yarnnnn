'use client';

/**
 * StudioNavigator — the Studio's left rail (ADR-447 workbench restructure).
 *
 * A PER-TYPE navigator: what it shows follows the artifact's layout —
 *   - deck    → a slide strip of VISUAL PREVIEWS (PowerPoint / Preview.app):
 *               one card per `[data-arrange]` slide, a scaled render of the
 *               real slide; clicking a card selects that slide.
 *   - article → the outline (h1/h2 headings) — a publishing shape reads as a
 *               table of contents.
 *   - document→ the outline too (sections under one title).
 *
 * The slide previews are REAL renders: the artifact is projected once
 * (citations resolved to displayable content, executables stripped — the same
 * `resolveArtifactHtml` the canvas uses, but WITHOUT the pointer/edit runtime),
 * then each slide's HTML + the artifact's <style> is rendered in a small
 * `sandbox=""` iframe scaled down with CSS transform. Previews are display-only
 * (no scripts); selecting a slide is a parent click on the card, not in-frame.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { resolveArtifactHtml } from '@/components/workspace/viewers/projection';

interface OutlineEntry {
  level: number;
  text: string;
  /** The heading block's id (ADR-455) — present when the heading is annotated
   *  (scaffolds + the posture stamp headings); makes the entry navigational. */
  blockId: string | null;
}

// A deck slide is LANDSCAPE 16:9 (the skin: aspect-ratio 16/9). The preview
// iframe renders the slide at its NATURAL landscape box (SLIDE_W×SLIDE_H) and
// the whole document is scaled to whatever width the rail gives us — measured,
// never hardcoded. The old code pinned THUMB_W=200 while the rail (w-56 minus
// its padding + the number column) is only ~176px wide, so the 200px iframe was
// CLIPPED on the right by its overflow-hidden parent and read as a squished,
// portrait-ish strip. Now the scale is derived from the real container width so
// the 16:9 preview always fits edge-to-edge, undistorted.
const SLIDE_W = 992; // the slide's max width (62rem) — its natural landscape box
const SLIDE_H = Math.round((SLIDE_W * 9) / 16); // 16:9 → 558

interface SlidePreview {
  index: number;
  /** A deck slide (16:9 box) vs a page section (natural height). */
  isSlide: boolean;
  arrange: string | null;
  title: string;
  /** The full mini-document for this page's preview iframe (srcDoc). The
   *  preview renders at the page's NATURAL box; the parent scales it to fit. */
  doc: string;
}

// The page grain — a deck slide (`section.slide`) OR an arranged page section
// (`section[data-arrange]`). Must match artifactOps.PAGE_SEL and the canvas
// runtime's pageSel so indices agree across the navigator, the ops, and the
// canvas scroll. This is the "both paged templates" seam: the strip is a
// function of mode === 'paged', not the 'deck' slug (ADR-222).
const PAGE_SEL = 'section.slide, [data-arrange]';

/** Project the artifact once, then slice it into per-page preview documents.
 *  Each preview doc = the artifact's <head> (styles) + one page's <body> markup;
 *  the card scales the iframe to fit its measured width. A deck slide renders at
 *  its natural 16:9 box; a page section (variable height) renders at the slide
 *  width and lets its own content set the height (the card is aspect-free). */
async function buildPagePreviews(html: string, artifactPath: string): Promise<SlidePreview[]> {
  if (typeof window === 'undefined' || !html) return [];
  // Project citations to displayable content (no pointer/edit runtime — these
  // are previews). resolveArtifactHtml with no opts resolves data-ref only.
  const projected = html.includes('data-ref')
    ? await resolveArtifactHtml(html, artifactPath)
    : html;
  const doc = new DOMParser().parseFromString(projected, 'text/html');
  const headStyles = Array.from(doc.querySelectorAll('head style, head link'))
    .map((el) => el.outerHTML)
    .join('\n');
  const pages = Array.from(doc.querySelectorAll(PAGE_SEL));
  return pages.map((page, index) => {
    const isSlide = page.matches('section.slide');
    const heading = page.querySelector('h1, h2, h3, .kicker');
    const body = page.outerHTML;
    // A deck slide is pinned to its landscape box; a page section keeps its
    // natural height (the skin's own layout) so a tall hero previews as tall.
    const sizing = isSlide
      ? `html,body{margin:0;padding:0;background:#fff;overflow:hidden;width:${SLIDE_W}px;height:${SLIDE_H}px;}` +
        `.slide{width:${SLIDE_W}px !important;height:${SLIDE_H}px !important;` +
        `aspect-ratio:auto !important;margin:0 !important;box-shadow:none !important;}`
      : `html,body{margin:0;padding:0;background:#fff;width:${SLIDE_W}px;}` +
        `[data-arrange]{margin:0 !important;box-shadow:none !important;}`;
    const previewDoc =
      `<!doctype html><html><head>${headStyles}` +
      `<style>${sizing}</style></head><body>${body}</body></html>`;
    return {
      index,
      isSlide,
      arrange: page.getAttribute('data-arrange'),
      title:
        (heading?.textContent || '').replace(/\s+/g, ' ').trim() ||
        (isSlide ? `Slide ${index + 1}` : `Section ${index + 1}`),
      doc: previewDoc,
    };
  });
}

/** A single slide preview card: a fixed 16:9 box (CSS aspect-ratio — no
 *  measurement feedback, no SSR/hydration style swap) whose iframe renders the
 *  slide at its natural 992×558 box and is scaled to fill via a ResizeObserver-
 *  measured factor. The box height comes from `aspect-ratio`, so the scale never
 *  drives the height (the old code set height FROM the measured width, a loop
 *  that could settle small); the scale only sizes the iframe INSIDE a box that
 *  is already the right shape. */
function SlideThumb({ doc, index, isSlide }: { doc: string; index: number; isSlide: boolean }) {
  const boxRef = useRef<HTMLSpanElement>(null);
  const [scale, setScale] = useState(0);
  useEffect(() => {
    const box = boxRef.current;
    if (!box) return;
    const measure = () => {
      const w = box.clientWidth;
      if (w > 0) setScale(w / SLIDE_W);
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(box);
    return () => ro.disconnect();
  }, []);
  // A deck slide is a fixed 16:9 box; a page section keeps its natural
  // proportion but is capped so a very tall hero card doesn't dominate the rail.
  return (
    <span
      ref={boxRef}
      className="relative block w-full overflow-hidden rounded-sm border border-border/60 bg-white"
      style={
        isSlide
          ? { aspectRatio: `${SLIDE_W} / ${SLIDE_H}` }
          : { aspectRatio: `${SLIDE_W} / ${SLIDE_H}` } // page sections share the 16:9 card frame; overflow-hidden crops a tall section to a legible preview
      }
    >
      {scale > 0 && (
        <iframe
          title={isSlide ? `Slide ${index + 1}` : `Section ${index + 1}`}
          srcDoc={doc}
          sandbox=""
          tabIndex={-1}
          scrolling="no"
          aria-hidden="true"
          className="pointer-events-none absolute left-0 top-0 border-0"
          style={{
            width: SLIDE_W,
            height: isSlide ? SLIDE_H : SLIDE_H * 3, // a page section can be tall; render generously, the card crops
            transform: `scale(${scale})`,
            transformOrigin: 'top left',
          }}
        />
      )}
    </span>
  );
}

/** Extract h1/h2 outline from source html (document/article rail). */
function extractOutline(html: string): OutlineEntry[] {
  if (typeof window === 'undefined' || !html) return [];
  const doc = new DOMParser().parseFromString(html, 'text/html');
  return Array.from(doc.querySelectorAll('h1, h2'))
    .map((h) => ({
      level: h.tagName === 'H1' ? 1 : 2,
      text: (h.textContent || '').replace(/\s+/g, ' ').trim(),
      blockId: h.getAttribute('data-block-id'),
    }))
    .filter((h) => h.text)
    .slice(0, 40);
}

interface StudioNavigatorProps {
  /** The artifact's layout slug (document/deck/article/page/canvas). */
  layout: string;
  /** The composition mode (STUDIO_LAYOUT_MODES): 'paged' → the card strip
   *  (deck slides, page sections); 'flow' → the outline. Derived from the
   *  kernel's mode, NOT a 'deck' slug test, so both paged templates get the
   *  management strip (ADR-222 — the kernel names the category). */
  isPaged: boolean;
  /** The artifact's SOURCE html. */
  html: string;
  /** Absolute workspace path — the base for citation resolution in previews. */
  artifactPath: string;
  /** The PRIMARY selected page index (paged) — drives the canvas scroll + the
   *  Design-tab scope. One of the multi-selection, the last one clicked. */
  selectedSlide: number | null;
  /** Select a page by index (paged) — plain click. Anchors the toolbar's
   *  Arrange ops and scrolls the canvas. */
  onSelectSlide: (index: number) => void;
  /** Reorder ONE page by dragging it (PowerPoint) — move `from` → `to` in
   *  document order. One mechanical revision. Kept for the single-drag path. */
  onReorderSlide?: (from: number, to: number) => void;
  /** Reorder a MULTI-SELECTION as a contiguous group to the drop gap `to`
   *  (preserving internal order). One compound revision. */
  onReorderPages?: (indices: number[], to: number) => void;
  /** Delete a selection of pages as ONE compound revision (multi-select
   *  Delete). The parent confirms when >1. */
  onDeletePages?: (indices: number[]) => void;
  /** ADR-455: select a heading by block id (document/article outline) —
   *  selects the heading block AND scrolls the canvas to it (deck parity). */
  onSelectHeading?: (blockId: string) => void;
}

export function StudioNavigator({
  layout,
  isPaged,
  html,
  artifactPath,
  selectedSlide,
  onSelectSlide,
  onReorderSlide,
  onReorderPages,
  onDeletePages,
  onSelectHeading,
}: StudioNavigatorProps) {
  const [previews, setPreviews] = useState<SlidePreview[] | null>(null);
  // Drag-to-reorder (PowerPoint): the index being dragged, and the gap the drop
  // would land in (0..N — a drop BEFORE page `dropAt`, or after the last).
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [dropAt, setDropAt] = useState<number | null>(null);
  // Multi-selection (PowerPoint/Finder): the set of selected page indices. The
  // PRIMARY (selectedSlide, owned by the parent) is the one that drives the
  // canvas + Design scope; this set adds the ⌘/shift-clicked others. The anchor
  // is the pivot for shift-range selection.
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const anchorRef = useRef<number | null>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const stripRef = useRef<HTMLDivElement>(null);
  const pageCount = previews?.length ?? 0;

  useEffect(() => {
    if (!isPaged) {
      setPreviews(null);
      return;
    }
    let cancelled = false;
    buildPagePreviews(html, artifactPath)
      .then((p) => !cancelled && setPreviews(p))
      .catch(() => !cancelled && setPreviews([]));
    return () => {
      cancelled = true;
    };
  }, [isPaged, html, artifactPath]);

  // The parent's primary selection is always part of the multi-selection; keep
  // the two in sync when the parent selects a page from elsewhere (canvas click,
  // toolbar). A pure primary-change collapses the selection to just it.
  useEffect(() => {
    if (selectedSlide == null) {
      setSelected(new Set());
      anchorRef.current = null;
      return;
    }
    setSelected((prev) => (prev.has(selectedSlide) ? prev : new Set([selectedSlide])));
    if (anchorRef.current == null) anchorRef.current = selectedSlide;
  }, [selectedSlide]);

  // Drop selections that fell out of range when the page count shrank (a delete
  // reflow), so a stale index never anchors an op.
  useEffect(() => {
    setSelected((prev) => {
      const next = new Set(Array.from(prev).filter((i) => i < pageCount));
      return next.size === prev.size ? prev : next;
    });
  }, [pageCount]);

  // The current selection as a sorted array (op input).
  const selectedList = useCallback(
    () => Array.from(selected).sort((a, b) => a - b),
    [selected],
  );

  // A card click with modifiers (PowerPoint/Finder): plain = select-one (parent
  // owns it, drives the canvas); ⌘/ctrl = toggle; shift = range from the anchor.
  const onCardClick = useCallback(
    (index: number, e: { metaKey: boolean; ctrlKey: boolean; shiftKey: boolean }) => {
      if (e.shiftKey && anchorRef.current != null) {
        const lo = Math.min(anchorRef.current, index);
        const hi = Math.max(anchorRef.current, index);
        const range = new Set<number>();
        for (let i = lo; i <= hi; i++) range.add(i);
        setSelected(range);
        onSelectSlide(index); // primary follows the shift target (canvas scroll)
        return;
      }
      if (e.metaKey || e.ctrlKey) {
        setSelected((prev) => {
          const next = new Set(prev);
          if (next.has(index)) next.delete(index);
          else next.add(index);
          return next;
        });
        anchorRef.current = index;
        onSelectSlide(index);
        return;
      }
      // Plain click — collapse to a single selection. Setting it explicitly
      // (not leaning on the primary-sync effect) is load-bearing: the effect
      // KEEPS a set that already contains the clicked index, so a plain click
      // on an already-multi-selected card would otherwise not collapse.
      setSelected(new Set([index]));
      anchorRef.current = index;
      onSelectSlide(index);
    },
    [onSelectSlide],
  );

  // Delete the current selection (Delete/Backspace or a future menu). Confirms
  // only for a multi-delete — a single delete is cheap and ⌘Z undoes it.
  const deleteSelection = useCallback(() => {
    const list = selectedList();
    if (!list.length || !onDeletePages) return;
    if (list.length > 1) {
      const noun = layout === 'deck' ? 'slides' : 'sections';
      if (!window.confirm(`Delete ${list.length} ${noun}?`)) return;
    }
    onDeletePages(list);
  }, [selectedList, onDeletePages, layout]);

  // Keyboard on the focused strip (PowerPoint/Finder ladder): Delete removes the
  // selection; ↑/↓ move the primary (+ scroll); ⌘A selects all; Esc clears to
  // the primary. Bound to the strip container (tabIndex=0), so it fires only
  // when the navigator has focus — never steals the canvas's own keys.
  const onStripKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!isPaged || pageCount === 0) return;
      if (e.key === 'Delete' || e.key === 'Backspace') {
        e.preventDefault();
        deleteSelection();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        const cur = selectedSlide ?? -1;
        const nextI = Math.min(cur + 1, pageCount - 1);
        anchorRef.current = nextI;
        onSelectSlide(nextI);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        const cur = selectedSlide ?? pageCount;
        const prevI = Math.max(cur - 1, 0);
        anchorRef.current = prevI;
        onSelectSlide(prevI);
      } else if ((e.metaKey || e.ctrlKey) && (e.key === 'a' || e.key === 'A')) {
        e.preventDefault();
        setSelected(new Set(Array.from({ length: pageCount }, (_, i) => i)));
      } else if (e.key === 'Escape') {
        if (selectedSlide != null) setSelected(new Set([selectedSlide]));
      }
    },
    [isPaged, pageCount, deleteSelection, selectedSlide, onSelectSlide],
  );

  // Which gap does the pointer sit over? Walk the rendered cards, compare the
  // pointer-Y to each card's vertical midpoint — the first card whose midpoint
  // is below the pointer is the insertion point (drop BEFORE it); past the last
  // card, drop at the end (N).
  const gapAtPointer = useCallback((clientY: number): number => {
    const items = listRef.current?.querySelectorAll('[data-slide-card]');
    if (!items || !items.length) return 0;
    for (let i = 0; i < items.length; i++) {
      const r = items[i].getBoundingClientRect();
      if (clientY < r.top + r.height / 2) return i;
    }
    return items.length;
  }, []);

  // The drag lives on WINDOW listeners, not on the <ul>'s React handlers — a
  // pointerdown on the grip must NOT setPointerCapture (that would route every
  // subsequent move to the grip element, so the list never hears them and the
  // drag appears dead). window listeners see the moves wherever the pointer
  // goes, including off the strip. `dropAtRef` mirrors the state so the up
  // handler reads the final gap synchronously. Bound only while a drag is live.
  const dropAtRef = useRef<number | null>(null);
  useEffect(() => {
    if (dragIndex == null) return;
    const onMove = (e: PointerEvent) => {
      const gap = gapAtPointer(e.clientY);
      dropAtRef.current = gap;
      setDropAt(gap);
    };
    const onUp = () => {
      const gap = dropAtRef.current;
      if (gap != null) {
        // If the grabbed card is part of a multi-selection, MOVE THE GROUP;
        // else move the single card (the original path). The group move lands
        // the selection as a contiguous run before the page currently at `gap`.
        const sel = Array.from(selected).sort((a, b) => a - b);
        if (sel.length > 1 && sel.includes(dragIndex) && onReorderPages) {
          onReorderPages(sel, gap);
        } else if (onReorderSlide) {
          // The drop gap is an index in the ORIGINAL order; landing in our own
          // slot or just after it is a no-op.
          const to = gap > dragIndex ? gap - 1 : gap;
          if (to !== dragIndex) onReorderSlide(dragIndex, to);
        }
      }
      setDragIndex(null);
      setDropAt(null);
      dropAtRef.current = null;
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    window.addEventListener('pointercancel', onUp);
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      window.removeEventListener('pointercancel', onUp);
    };
  }, [dragIndex, gapAtPointer, onReorderSlide, onReorderPages, selected]);

  if (isPaged) {
    const noun = layout === 'deck' ? 'Slides' : 'Sections';
    const selCount = selected.size;
    return (
      <div
        ref={stripRef}
        tabIndex={0}
        onKeyDown={onStripKeyDown}
        className="flex h-full w-full flex-col overflow-y-auto p-2 outline-none"
      >
        <div className="flex items-center justify-between px-1 pb-2 pt-1">
          <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            {noun}
          </p>
          {selCount > 1 && (
            <span className="text-[10px] text-muted-foreground">{selCount} selected</span>
          )}
        </div>
        <ul ref={listRef} className="relative w-full space-y-2">
          {(previews ?? []).map((s) => (
            <li key={s.index} data-slide-card className="relative">
              {/* The drop-line: a prediction of where the dragged page will
                  land (above this card when the gap === this index). */}
              {dragIndex != null && dropAt === s.index && (
                <span className="pointer-events-none absolute -top-1 left-0 right-0 z-10 h-0.5 rounded bg-indigo-500" />
              )}
              <div
                role="button"
                tabIndex={0}
                onClick={(e) =>
                  onCardClick(s.index, {
                    metaKey: e.metaKey,
                    ctrlKey: e.ctrlKey,
                    shiftKey: e.shiftKey,
                  })
                }
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onCardClick(s.index, {
                      metaKey: e.metaKey,
                      ctrlKey: e.ctrlKey,
                      shiftKey: e.shiftKey,
                    });
                  }
                }}
                title={s.title}
                className={`block w-full cursor-pointer rounded-md border text-left transition-colors ${
                  dragIndex === s.index ? 'opacity-40' : ''
                } ${
                  // Primary = solid ring; a secondary multi-selected card = a
                  // lighter fill so the group reads as one selection.
                  selectedSlide === s.index
                    ? 'border-indigo-400 ring-1 ring-indigo-400'
                    : selected.has(s.index)
                      ? 'border-indigo-300 bg-indigo-50/60 dark:bg-indigo-500/10'
                      : 'border-border hover:border-foreground/30'
                }`}
              >
                <div className="flex items-stretch gap-1.5 p-1">
                  {/* The grip: press to drag-reorder (PowerPoint). The number
                      doubles as the grab handle so the strip stays compact. A
                      drag of a card inside a multi-selection moves the group. */}
                  <span
                    onPointerDown={(e) => {
                      if (!onReorderSlide && !onReorderPages) return;
                      // Do NOT setPointerCapture — window listeners own the drag
                      // (capture would starve them). Stop propagation so the
                      // card's onClick/select doesn't also fire on the press.
                      e.preventDefault();
                      e.stopPropagation();
                      dropAtRef.current = s.index;
                      setDragIndex(s.index);
                      setDropAt(s.index);
                    }}
                    title="Drag to reorder"
                    className={`mt-0.5 w-3 shrink-0 select-none text-right text-[10px] font-medium text-muted-foreground ${
                      onReorderSlide || onReorderPages ? 'cursor-grab active:cursor-grabbing' : ''
                    }`}
                  >
                    {s.index + 1}
                  </span>
                  <span className="min-w-0 flex-1">
                    <SlideThumb doc={s.doc} index={s.index} isSlide={s.isSlide} />
                  </span>
                </div>
                <span className="block truncate px-1.5 pb-1 text-[10px] text-muted-foreground">
                  {s.title}
                </span>
              </div>
            </li>
          ))}
          {/* The trailing drop-line — a drop AFTER the last slide. */}
          {dragIndex != null && dropAt === (previews?.length ?? 0) && (previews?.length ?? 0) > 0 && (
            <li className="pointer-events-none relative h-0">
              <span className="absolute -top-1 left-0 right-0 h-0.5 rounded bg-indigo-500" />
            </li>
          )}
          {previews === null && (
            <li className="px-1 text-[11px] text-muted-foreground">Loading previews…</li>
          )}
          {previews?.length === 0 && (
            <li className="px-1 text-[11px] text-muted-foreground">
              {layout === 'deck' ? 'No slides yet.' : 'No sections yet.'}
            </li>
          )}
        </ul>
      </div>
    );
  }

  // document + article → the outline, NAVIGATIONAL (ADR-455): clicking a
  // heading selects its block and scrolls the canvas to it — the Docs/Word
  // nav-pane contract, via the same bridge the deck strip uses.
  const outline = extractOutline(html);
  return (
    <div className="flex h-full w-full flex-col overflow-y-auto p-3">
      <p className="mb-2 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
        Outline
      </p>
      {outline.length === 0 ? (
        <p className="text-[11px] text-muted-foreground">Headings appear here.</p>
      ) : (
        <ul className="space-y-0.5">
          {outline.map((h, i) =>
            h.blockId && onSelectHeading ? (
              <li key={i}>
                <button
                  type="button"
                  onClick={() => onSelectHeading(h.blockId!)}
                  title={h.text}
                  className={`block w-full truncate rounded px-1 py-0.5 text-left text-xs transition-colors hover:bg-muted/40 hover:text-foreground ${
                    h.level === 1 ? 'font-medium' : 'pl-3 text-muted-foreground'
                  }`}
                >
                  {h.text}
                </button>
              </li>
            ) : (
              <li
                key={i}
                className={`truncate px-1 py-0.5 text-xs ${
                  h.level === 1 ? 'font-medium' : 'pl-3 text-muted-foreground'
                }`}
                title={h.text}
              >
                {h.text}
              </li>
            ),
          )}
        </ul>
      )}
    </div>
  );
}
