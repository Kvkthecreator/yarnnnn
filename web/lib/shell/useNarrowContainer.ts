'use client';

/**
 * useNarrowContainer — "is the space I actually have narrow?", measured.
 *
 * `useViewport().isMobile` answers a different question: is the WINDOW narrow.
 * For a two-column surface that distinction is the whole bug. A surface renders
 * inside a window that can be resized independently (WINDOW_MIN_WIDTH = 320),
 * beside a chat drawer that can be 720px wide, on a desktop of any size — so
 * viewport width is a poor proxy for the room a component has.
 *
 * Two real consequences of keying the chat surface's rail to the viewport:
 *
 *  · A 768px tablet is `isMobile === false` (the threshold is 640), so it gets
 *    the full desktop treatment. With the chat drawer open at its 400px default
 *    that leaves 368px for the surface — and the rail's own `w-72 shrink-0`
 *    takes 288 of those, leaving ~80px of transcript.
 *  · A 320px WINDOW on a 1440px monitor is also `isMobile === false`, so the
 *    288px rail still renders and the conversation gets ~32px.
 *
 * Both are the same defect — a component asking the window how much room it has
 * instead of measuring — and both are fixed by observing the element.
 *
 * This is the pattern the Studio already uses for exactly this reason
 * (StudioCanvas measures its own frame via ResizeObserver so the fit tracks the
 * column, not the window). It is generalized here so the shell can use it too.
 *
 * SSR-safe: returns `false` (the roomy branch) until the first measurement, so
 * markup is stable through hydration and never flashes the collapsed layout.
 */

import { useEffect, useState, type RefObject } from 'react';

/**
 * Observe `ref`'s width and report whether it is below `threshold` px.
 *
 * @param ref        the element to measure — the CONTAINER, not the window
 * @param threshold  px width below which the container counts as narrow
 */
export function useNarrowContainer(
  ref: RefObject<HTMLElement | null>,
  threshold: number,
): boolean {
  const [narrow, setNarrow] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const measure = () => {
      const w = el.clientWidth;
      // A zero width means "not laid out yet" (display:none, pre-paint), not
      // "infinitely narrow" — treating it as narrow would collapse the layout
      // for a frame on every mount.
      if (w > 0) setNarrow(w < threshold);
    };

    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [ref, threshold]);

  return narrow;
}
