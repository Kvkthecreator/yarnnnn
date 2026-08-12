'use client';

/**
 * useWorkbenchWidth — the authoring workbench's ONE answer to "how much room
 * do I have", and therefore to which rung of the collapse ladder is live.
 *
 * ## Why this exists
 *
 * Docs and Studio are the same component (`StudioSurface`, parameterized by
 * `AuthoringApp`), and it was the one major surface doing responsive purely in
 * raw Tailwind class strings — `md:flex`, `md:hidden` — reading neither
 * `useViewport` nor `useCoarsePointer`. That produced two defects measured live
 * on prod (2026-08-12):
 *
 *  1. **A breakpoint the shell disagreed with.** The shell collapses to
 *     single-window at `MOBILE_BREAKPOINT_PX` (640); the workbench switched
 *     panes at `md` (768). In the band between, and again from 768 up to the
 *     layout's real ~1008px minimum, three columns were attempted with no room:
 *     at 820px the toolbar row yielded to **16px** while its contents needed
 *     **274**, and because the row is `overflow: visible` (it must be — its
 *     galleries are `absolute top-full` and a scroll container would clip them)
 *     the buttons escaped and painted **260px over the Properties column**.
 *  2. **A canvas that absorbed the entire deficit** — 177px wide at 768,
 *     cropping the artifact past legibility — because it was the sole `flex-1`
 *     among `shrink-0` siblings.
 *
 * ## Why it measures the container, not the window
 *
 * `useViewport().isMobile` answers "is the WINDOW narrow", which is a poor proxy
 * for the room a surface has: a surface lives inside a window that resizes
 * independently (`WINDOW_MIN_WIDTH` = 320), beside a chat drawer, on a monitor
 * of any size. `useNarrowContainer` was generalized out of the Studio for
 * exactly this reason (its docstring cites the Studio's own ResizeObserver as
 * the pattern) — and the Studio never adopted it back. This closes that loop.
 *
 * SSR-safe: reports the ROOMIEST rung until the first measurement, so the
 * markup is stable through hydration and never flashes the collapsed layout.
 * That direction is deliberate and matches ADR-482 D3 / ADR-506 D2 — chrome
 * withholds rather than guesses, and the roomy branch is the one that shows
 * chrome in its resting place.
 *
 * ## The ladder
 *
 * | rung           | layout                          | what folds                    |
 * |----------------|---------------------------------|-------------------------------|
 * | `full`         | three columns, full labels      | nothing                       |
 * | `condensed`    | three columns, icon verbs       | labels; Share/Export → ⋯       |
 * | `two-pane`     | canvas + side as OVERLAY drawer | the side column               |
 * | `single-pane`  | one pane + bottom tab bar       | everything but the active pane |
 *
 * Thresholds live in `lib/shell/surface-preferences.ts` beside the shell's own,
 * so "how wide is wide" has one declared home. Never re-spell them as `md:`/
 * `lg:` in a class string — that is the drift this module exists to end.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  WORKBENCH_FULL_LABELS_PX,
  WORKBENCH_SINGLE_PANE_PX,
  WORKBENCH_THREE_COLUMN_PX,
} from '@/lib/shell/surface-preferences';

/** The live rung of the collapse ladder, widest → narrowest. */
export type WorkbenchRung = 'full' | 'condensed' | 'two-pane' | 'single-pane';

export interface WorkbenchWidth {
  rung: WorkbenchRung;
  /** The measured container width in px, or null before the first measurement.
   *  Callers that must CLAMP against real room (the resizable slide strip) need
   *  the number, not just the rung — a persisted 520px strip inside an 800px
   *  workbench is the same crush this ladder exists to prevent, arriving through
   *  member state instead of through the layout. */
  measuredWidth: number | null;
  /** Three real columns (nav · canvas · side) fit side by side. */
  threeColumn: boolean;
  /** The side pane (Properties / Chat) is an OVERLAY, not a column. */
  sideIsOverlay: boolean;
  /** One pane at a time, switched by the bottom tab bar. */
  singlePane: boolean;
  /** Toolbar verbs wear their full text labels. */
  fullLabels: boolean;
}

/** Derive the rung from a measured width. Exported for the gate, which asserts
 *  the ladder's BEHAVIOUR at each boundary rather than pinning a spelling. */
export function rungForWidth(width: number): WorkbenchRung {
  if (width < WORKBENCH_SINGLE_PANE_PX) return 'single-pane';
  if (width < WORKBENCH_THREE_COLUMN_PX) return 'two-pane';
  if (width < WORKBENCH_FULL_LABELS_PX) return 'condensed';
  return 'full';
}

/** Expand a rung into the flags the surface actually branches on, so no caller
 *  re-derives "does this rung mean three columns" and gets it subtly different.
 *  (Five spellings of one predicate is the drift ADR-539 D1 names.) */
export function widthFromRung(
  rung: WorkbenchRung,
  measuredWidth: number | null = null,
): WorkbenchWidth {
  return {
    rung,
    measuredWidth,
    threeColumn: rung === 'full' || rung === 'condensed',
    sideIsOverlay: rung === 'two-pane',
    singlePane: rung === 'single-pane',
    fullLabels: rung === 'full',
  };
}

/**
 * Observe the workbench's own width and report which rung of the ladder is live.
 *
 * Returns a CALLBACK REF, not an object ref, and that is load-bearing.
 *
 * The first spelling took a `RefObject` and observed `ref.current` inside a
 * `useEffect([ref])`. It shipped green — tsc, build and 33 gate assertions all
 * passed — and never once measured, because the surface returns the START state
 * before it returns the workbench: at the effect's only run `ref.current` was
 * null, so it bailed, and a stable `ref` identity meant it never re-ran when the
 * workbench finally mounted. The rung sat at its `full` default forever, which
 * on a tablet is exactly the broken layout the ladder exists to prevent —
 * measured on prod at 820px, indistinguishable from the original defect.
 *
 * A callback ref cannot fail that way: React invokes it with the node at attach
 * and with null at detach, so observation begins whenever the element actually
 * appears, however many render branches precede it.
 *
 * @returns `[setNode, width]` — spread the callback into the element's `ref`.
 */
export function useWorkbenchWidth(): [(node: HTMLElement | null) => void, WorkbenchWidth] {
  // Start at the roomiest rung (see the SSR note above): withhold, never guess.
  const [width, setWidth] = useState<number | null>(null);
  const observerRef = useRef<ResizeObserver | null>(null);

  const setNode = useCallback((node: HTMLElement | null) => {
    observerRef.current?.disconnect();
    observerRef.current = null;
    if (!node) return;
    const measure = () => {
      const w = node.clientWidth;
      // A zero width means "not laid out yet" (display:none, pre-paint), not
      // "infinitely narrow" — treating it as narrow would collapse the layout
      // for a frame on every mount. Same guard as useNarrowContainer.
      if (w > 0) setWidth(w);
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(node);
    observerRef.current = ro;
  }, []);

  // Unmount safety — the callback ref's null call covers element swaps, this
  // covers the hook itself going away.
  useEffect(() => () => observerRef.current?.disconnect(), []);

  return [setNode, widthFromRung(width == null ? 'full' : rungForWidth(width), width)];
}
