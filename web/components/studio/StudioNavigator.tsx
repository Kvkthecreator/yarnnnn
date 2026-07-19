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
  arrange: string | null;
  title: string;
  /** The full mini-document for this slide's preview iframe (srcDoc). The
   *  preview renders at the slide's NATURAL box; the parent scales it to fit. */
  doc: string;
}

/** Project the artifact once, then slice it into per-slide preview documents.
 *  Each preview doc = the artifact's <head> (styles) + one slide's <body>
 *  markup at the slide's natural box; the card scales the iframe to fit its
 *  measured width (so a preview is never clipped or distorted). */
async function buildSlidePreviews(html: string, artifactPath: string): Promise<SlidePreview[]> {
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
  const slides = Array.from(doc.querySelectorAll('section.slide'));
  return slides.map((slide, index) => {
    const heading = slide.querySelector('h1, h2, h3, .kicker');
    // Render the slide at its natural landscape box; margin:0 override
    // neutralizes the skin's centering margin so the preview fills edge-to-edge.
    const body = slide.outerHTML;
    const previewDoc =
      `<!doctype html><html><head>${headStyles}` +
      `<style>` +
      `html,body{margin:0;padding:0;background:#fff;overflow:hidden;width:${SLIDE_W}px;height:${SLIDE_H}px;}` +
      `.slide{width:${SLIDE_W}px !important;height:${SLIDE_H}px !important;` +
      `aspect-ratio:auto !important;margin:0 !important;box-shadow:none !important;}` +
      `</style></head><body>${body}</body></html>`;
    return {
      index,
      arrange: slide.getAttribute('data-arrange'),
      title: (heading?.textContent || '').replace(/\s+/g, ' ').trim() || `Slide ${index + 1}`,
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
function SlideThumb({ doc, index }: { doc: string; index: number }) {
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
  return (
    <span
      ref={boxRef}
      className="relative block w-full overflow-hidden rounded-sm border border-border/60 bg-white"
      style={{ aspectRatio: `${SLIDE_W} / ${SLIDE_H}` }}
    >
      {scale > 0 && (
        <iframe
          title={`Slide ${index + 1}`}
          srcDoc={doc}
          sandbox=""
          tabIndex={-1}
          scrolling="no"
          aria-hidden="true"
          className="pointer-events-none absolute left-0 top-0 border-0"
          style={{
            width: SLIDE_W,
            height: SLIDE_H,
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
  /** The artifact's layout slug (document/deck/article). */
  layout: string;
  /** The artifact's SOURCE html. */
  html: string;
  /** Absolute workspace path — the base for citation resolution in previews. */
  artifactPath: string;
  /** The currently selected slide index (deck) — highlights the card. */
  selectedSlide: number | null;
  /** Select a slide by index (deck) — anchors the toolbar's Arrange ops. */
  onSelectSlide: (index: number) => void;
  /** Reorder a slide by dragging it in the strip (PowerPoint) — move the slide
   *  at `from` to sit at `to` in document order. One mechanical revision. */
  onReorderSlide?: (from: number, to: number) => void;
  /** ADR-455: select a heading by block id (document/article outline) —
   *  selects the heading block AND scrolls the canvas to it (deck parity). */
  onSelectHeading?: (blockId: string) => void;
}

export function StudioNavigator({
  layout,
  html,
  artifactPath,
  selectedSlide,
  onSelectSlide,
  onReorderSlide,
  onSelectHeading,
}: StudioNavigatorProps) {
  const [previews, setPreviews] = useState<SlidePreview[] | null>(null);
  // Drag-to-reorder (PowerPoint): the index being dragged, and the gap the drop
  // would land in (0..N — a drop BEFORE slide `dropAt`, or after the last).
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [dropAt, setDropAt] = useState<number | null>(null);
  const listRef = useRef<HTMLUListElement>(null);

  useEffect(() => {
    if (layout !== 'deck') {
      setPreviews(null);
      return;
    }
    let cancelled = false;
    buildSlidePreviews(html, artifactPath)
      .then((p) => !cancelled && setPreviews(p))
      .catch(() => !cancelled && setPreviews([]));
    return () => {
      cancelled = true;
    };
  }, [layout, html, artifactPath]);

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
      if (gap != null && onReorderSlide) {
        // The drop gap is an index in the ORIGINAL order; landing in our own
        // slot or just after it is a no-op.
        const to = gap > dragIndex ? gap - 1 : gap;
        if (to !== dragIndex) onReorderSlide(dragIndex, to);
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
  }, [dragIndex, gapAtPointer, onReorderSlide]);

  if (layout === 'deck') {
    return (
      <div className="flex h-full flex-col overflow-y-auto p-2">
        <p className="px-1 pb-2 pt-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
          Slides
        </p>
        <ul ref={listRef} className="relative space-y-2">
          {(previews ?? []).map((s) => (
            <li key={s.index} data-slide-card className="relative">
              {/* The drop-line: a prediction of where the dragged slide will
                  land (above this card when the gap === this index). */}
              {dragIndex != null && dropAt === s.index && (
                <span className="pointer-events-none absolute -top-1 left-0 right-0 z-10 h-0.5 rounded bg-indigo-500" />
              )}
              <div
                role="button"
                tabIndex={0}
                onClick={() => onSelectSlide(s.index)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onSelectSlide(s.index);
                  }
                }}
                title={s.title}
                className={`block w-full cursor-pointer rounded-md border text-left transition-colors ${
                  dragIndex === s.index ? 'opacity-40' : ''
                } ${
                  selectedSlide === s.index
                    ? 'border-indigo-400 ring-1 ring-indigo-400'
                    : 'border-border hover:border-foreground/30'
                }`}
              >
                <div className="flex items-stretch gap-1.5 p-1">
                  {/* The grip: press to drag-reorder (PowerPoint). The number
                      doubles as the grab handle so the strip stays compact. */}
                  <span
                    onPointerDown={(e) => {
                      if (!onReorderSlide) return;
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
                      onReorderSlide ? 'cursor-grab active:cursor-grabbing' : ''
                    }`}
                  >
                    {s.index + 1}
                  </span>
                  <span className="min-w-0 flex-1">
                    <SlideThumb doc={s.doc} index={s.index} />
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
            <li className="px-1 text-[11px] text-muted-foreground">No slides yet.</li>
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
    <div className="flex h-full flex-col overflow-y-auto p-3">
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
