'use client';

/**
 * useViewport — ADR-297 D15.
 *
 * Tracks viewport size + a derived `isMobile` boolean (< MOBILE_BREAKPOINT_PX).
 * Used by the window manager to switch between multi-window mode
 * (desktop / tablet) and single-window mode (phone < 640px).
 *
 * SSR-safe: initial render returns a sensible desktop fallback
 * (1280×800, isMobile=false); the post-mount effect picks up real
 * viewport size on the first client render.
 */

import { useEffect, useState } from 'react';
import { MOBILE_BREAKPOINT_PX } from './surface-preferences';

interface ViewportState {
  width: number;
  height: number;
  isMobile: boolean;
}

const SSR_DEFAULT: ViewportState = {
  width: 1280,
  height: 800,
  isMobile: false,
};

export function useViewport(): ViewportState {
  const [state, setState] = useState<ViewportState>(SSR_DEFAULT);

  useEffect(() => {
    const compute = (): ViewportState => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      return { width: w, height: h, isMobile: w < MOBILE_BREAKPOINT_PX };
    };

    setState(compute());

    let raf: number | null = null;
    const handler = () => {
      if (raf !== null) cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => setState(compute()));
    };
    window.addEventListener('resize', handler);
    return () => {
      window.removeEventListener('resize', handler);
      if (raf !== null) cancelAnimationFrame(raf);
    };
  }, []);

  return state;
}
