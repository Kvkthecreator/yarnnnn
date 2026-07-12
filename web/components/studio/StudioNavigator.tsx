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

import { useEffect, useState } from 'react';
import { resolveArtifactHtml } from '@/components/workspace/viewers/projection';

interface OutlineEntry {
  level: number;
  text: string;
}

// A slide is authored at roughly this pixel box; the thumbnail scales it down.
const SLIDE_W = 1280;
const SLIDE_H = 720;
const THUMB_W = 208; // matches the rail width (w-56 minus padding)
const SCALE = THUMB_W / SLIDE_W;
const THUMB_H = Math.round(SLIDE_H * SCALE);

interface SlidePreview {
  index: number;
  arrange: string | null;
  title: string;
  /** The full mini-document for this slide's preview iframe (srcDoc). */
  doc: string;
}

/** Project the artifact once, then slice it into per-slide preview documents.
 *  Each preview doc = the artifact's <head> (styles) + one slide's <body>
 *  markup, wrapped so a scaled iframe renders it like the real slide. */
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
    // Render the slide at authored dimensions, then scale the whole doc down.
    const body = `<div class="yarnnn-thumb-frame">${slide.outerHTML}</div>`;
    const previewDoc =
      `<!doctype html><html><head>${headStyles}` +
      `<style>` +
      `html,body{margin:0;padding:0;background:#fff;overflow:hidden;}` +
      `.yarnnn-thumb-frame{width:${SLIDE_W}px;min-height:${SLIDE_H}px;` +
      `transform:scale(${SCALE});transform-origin:top left;}` +
      `.yarnnn-thumb-frame .slide{min-height:${SLIDE_H}px;}` +
      `</style></head><body>${body}</body></html>`;
    return {
      index,
      arrange: slide.getAttribute('data-arrange'),
      title: (heading?.textContent || '').replace(/\s+/g, ' ').trim() || `Slide ${index + 1}`,
      doc: previewDoc,
    };
  });
}

/** Extract h1/h2 outline from source html (document/article rail). */
function extractOutline(html: string): OutlineEntry[] {
  if (typeof window === 'undefined' || !html) return [];
  const doc = new DOMParser().parseFromString(html, 'text/html');
  return Array.from(doc.querySelectorAll('h1, h2'))
    .map((h) => ({
      level: h.tagName === 'H1' ? 1 : 2,
      text: (h.textContent || '').replace(/\s+/g, ' ').trim(),
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
}

export function StudioNavigator({
  layout,
  html,
  artifactPath,
  selectedSlide,
  onSelectSlide,
}: StudioNavigatorProps) {
  const [previews, setPreviews] = useState<SlidePreview[] | null>(null);

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

  if (layout === 'deck') {
    return (
      <div className="flex h-full flex-col overflow-y-auto p-2">
        <p className="px-1 pb-2 pt-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
          Slides
        </p>
        <ul className="space-y-2">
          {(previews ?? []).map((s) => (
            <li key={s.index}>
              <button
                type="button"
                onClick={() => onSelectSlide(s.index)}
                title={s.title}
                className={`block w-full rounded-md border text-left transition-colors ${
                  selectedSlide === s.index
                    ? 'border-indigo-400 ring-1 ring-indigo-400'
                    : 'border-border hover:border-foreground/30'
                }`}
              >
                <div className="flex items-stretch gap-1.5 p-1">
                  <span className="mt-0.5 w-3 shrink-0 text-right text-[10px] font-medium text-muted-foreground">
                    {s.index + 1}
                  </span>
                  <span
                    className="relative block flex-1 overflow-hidden rounded-sm border border-border/60 bg-white"
                    style={{ height: THUMB_H }}
                  >
                    <iframe
                      title={`Slide ${s.index + 1}`}
                      srcDoc={s.doc}
                      sandbox=""
                      tabIndex={-1}
                      scrolling="no"
                      className="pointer-events-none absolute left-0 top-0 border-0"
                      style={{ width: THUMB_W, height: THUMB_H }}
                    />
                  </span>
                </div>
                <span className="block truncate px-1.5 pb-1 text-[10px] text-muted-foreground">
                  {s.title}
                </span>
              </button>
            </li>
          ))}
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

  // document + article → the outline (a table of contents).
  const outline = extractOutline(html);
  return (
    <div className="flex h-full flex-col overflow-y-auto p-3">
      <p className="mb-2 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
        Outline
      </p>
      {outline.length === 0 ? (
        <p className="text-[11px] text-muted-foreground">Headings appear here.</p>
      ) : (
        <ul className="space-y-1">
          {outline.map((h, i) => (
            <li
              key={i}
              className={`truncate text-xs ${
                h.level === 1 ? 'font-medium' : 'pl-3 text-muted-foreground'
              }`}
              title={h.text}
            >
              {h.text}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
