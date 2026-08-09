/**
 * stageGeometry — a staged medium's box, read from the DOCUMENT.
 *
 * THE RULE: a deck slide's geometry is a property of the FILE, never of the
 * viewer. A PowerPoint deck does not rearrange itself because you opened it on
 * a tablet, and neither does ours. The viewer's only geometric job is to SCALE
 * the stage to fit; it must never RESIZE it.
 *
 * Why this module exists. The 992×558 deck box was a bare literal in three
 * files with no shared import — `projection.ts`, `StudioCanvas.tsx` and
 * `PagedNavigator.tsx` each carried its own copy — and the canvas pinned the
 * slide to it with `!important` in `pointer` mode ONLY. Everywhere else (share,
 * export, thumbnail) the artifact fell back to its baked `width: min(100%,
 * 62rem)`, which reads the CONTAINER. So one deck had two geometries: fixed in
 * the editor, viewport-dependent everywhere a reader would actually meet it.
 * In a narrow container that skin shrank the 16:9 box until the unshrinking
 * `3.5rem 4rem` padding overflowed `overflow:hidden` and the slide clipped to
 * visual emptiness — the ADR-447 D7.7 defect, which had been fixed in the
 * canvas and nowhere else.
 *
 * The dimensions now ride the artifact itself (`--stage-w`/`--stage-h` in the
 * deck skin, `data-w`/`data-h` + inline vars on an IMAGES stage root), which
 * is the pattern `services/images/stage.py` already established. This module is
 * the ONE place the FE reads them back, so a viewer that needs the box for fit
 * math asks the document rather than restating a number.
 *
 * The fallbacks are the natural landscape box. They are a legacy path, not a
 * default to design against: a deck authored before the dimensions were baked
 * carries no vars, and must still render at its true 16:9 rather than
 * collapsing to zero.
 */

/** The deck stage's natural landscape box — 62rem wide at 16:9. */
export const DECK_STAGE_FALLBACK_W = 992;
export const DECK_STAGE_FALLBACK_H = Math.round((DECK_STAGE_FALLBACK_W * 9) / 16); // 558

/** The IMAGES stage default — a square, matching `stage.py`'s own fallback. */
export const IMAGE_STAGE_FALLBACK_W = 1080;
export const IMAGE_STAGE_FALLBACK_H = 1080;

export interface StageSize {
  width: number;
  height: number;
}

/** The natural box for a template slug, before the document is consulted. */
export function fallbackStageSize(template: string | null | undefined): StageSize {
  if (template === 'image') {
    return { width: IMAGE_STAGE_FALLBACK_W, height: IMAGE_STAGE_FALLBACK_H };
  }
  return { width: DECK_STAGE_FALLBACK_W, height: DECK_STAGE_FALLBACK_H };
}

/** Parse a px-or-bare number off a CSS custom property value ("992px" → 992). */
function parsePx(raw: string | null | undefined): number | null {
  if (!raw) return null;
  const n = parseFloat(String(raw).trim());
  return Number.isFinite(n) && n > 0 ? n : null;
}

/**
 * Read a staged artifact's real box out of its own markup.
 *
 * Order of authority, strongest first:
 *   1. `--stage-w`/`--stage-h` — the VALUES the skin consumes (both media).
 *   2. `data-w`/`data-h` — the MARKERS an IMAGES stage root carries.
 *   3. the template's natural box — legacy artifacts only.
 *
 * Reads the root element and the first `.slide`, because the deck skin declares
 * the vars on `.slide` while an IMAGES stage writes them inline on `<html>`.
 */
export function readStageSize(
  doc: Document | null | undefined,
  template: string | null | undefined,
): StageSize {
  const fallback = fallbackStageSize(template);
  if (!doc) return fallback;

  const root = doc.documentElement;
  const slide = doc.querySelector('.slide');

  for (const el of [slide, root]) {
    if (!el) continue;

    // Computed style resolves the vars wherever they were declared — but ONLY
    // in a document with a browsing context. `doc.defaultView` is null for a
    // DOMParser document (the export + navigator paths), so this silently
    // yields nothing there and the fallbacks below carry it.
    const style = doc.defaultView?.getComputedStyle(el);
    const w = parsePx(style?.getPropertyValue('--stage-w'));
    const h = parsePx(style?.getPropertyValue('--stage-h'));
    if (w && h) return { width: w, height: h };

    // Inline vars (how an IMAGES stage root carries its dimensions) + the
    // data-w/data-h markers. Both readable without a view.
    const inline = el.getAttribute('style') || '';
    const iw = parsePx(/--stage-w:\s*([^;]+)/.exec(inline)?.[1]);
    const ih = parsePx(/--stage-h:\s*([^;]+)/.exec(inline)?.[1]);
    if (iw && ih) return { width: iw, height: ih };

    const dw = parsePx(el.getAttribute('data-w'));
    const dh = parsePx(el.getAttribute('data-h'));
    if (dw && dh) return { width: dw, height: dh };
  }

  // The deck skin declares its vars in a STYLESHEET, not inline. Without a
  // browsing context that is unreachable through the CSSOM, so read the
  // declaration out of the artifact's own <style> text. This is the path a
  // deck raster export takes — without it, every deck falls back and exports
  // at the wrong aspect ratio, which is the defect this reader was built for.
  const css = Array.from(doc.querySelectorAll('head style'))
    .map((el) => el.textContent || '')
    .join('\n');
  const cw = parsePx(/--stage-w:\s*([^;}]+)/.exec(css)?.[1]);
  const ch = parsePx(/--stage-h:\s*([^;}]+)/.exec(css)?.[1]);
  if (cw && ch) return { width: cw, height: ch };

  return fallback;
}
