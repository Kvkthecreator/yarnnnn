'use client';

/**
 * useCoarsePointer — true when the primary input is a coarse pointer (touch),
 * i.e. there is no mouse to right-click or HTML5-drag with.
 *
 * The Files surface delivers every file action through a right-click context
 * menu + drag-to-move (ADR-388/400 Finder-parity) — both mouse-only. On a
 * coarse-pointer device those affordances are unreachable, so the file surfaces
 * render a tappable kebab (⋯) that opens the SAME menu instead (touch parity —
 * no new action model, just a touch-reachable trigger).
 *
 * `(pointer: coarse)` is the capability signal (does the device have a fine
 * pointer?), distinct from `useViewport().isMobile` (a 640px WIDTH threshold).
 * We want the capability, not the width: a narrow desktop window still has a
 * mouse; a large tablet does not.
 */

import { useMediaQuery } from './useMediaQuery';

export function useCoarsePointer(): boolean {
  return useMediaQuery('(pointer: coarse)');
}
