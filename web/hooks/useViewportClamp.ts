import { useLayoutEffect, useRef, useState } from 'react';

/**
 * Keep a floating box (context menu, popover) fully on screen.
 *
 * ── WHY A HOOK AND NOT A THIRD COPY ────────────────────────────────────────
 *
 * Every menu that opens at a pointer has to answer the same question, and
 * three of them answered it three different ways:
 *
 *   StudioBlockMenu     MEASURED the box (correct — ADR-586 D4)
 *   FileContextMenu     `innerHeight - 240`  (a guess at its own height)
 *   CanvasContextMenu   `innerHeight - 120`  (a different guess)
 *
 * A static guess is wrong the moment the box is taller than the number — and
 * the number cannot track a menu whose rows are conditional on the target.
 * FileContextMenu's guess was 240px for a box that reaches ~380px on a folder
 * (Open · Properties · Share · Keep current · New Folder · Rename · Move ·
 * Duplicate · Delete), so a right-click in the lower half of the window ran
 * the last verbs off the bottom of the screen: present in the DOM, invisible
 * and unreachable (operator-observed KVK 2026-08-27, screenshot).
 *
 * Studio had already fixed exactly this and written down why. Extracting it
 * here is what stops the fix from being a property of whichever menu someone
 * happened to be looking at. Same bug three times — the signature of a
 * missing funnel, which this codebase names in the surfaces it has already
 * funnelled.
 *
 * ── THE RULE ───────────────────────────────────────────────────────────────
 *
 * Measure the real box in `useLayoutEffect` (before the browser paints, so
 * there is no visible jump) and clamp both axes into the viewport with a
 * margin. First paint uses the raw point so the menu never flashes at 0,0.
 *
 * Deliberately CLAMP, not flip. A flipped menu jumps out from under the
 * pointer; clamping keeps the box adjacent to where the operator clicked,
 * which is the same reason ADR-586 D4 forbids re-clamping a parent when a
 * flyout opens (measured 647→421 top on one open, 2026-08-19).
 *
 * `deps` re-runs the measurement — pass anything that changes the box's own
 * HEIGHT (e.g. an INLINE tier that expands rows). Do NOT pass flyout state:
 * a flyout beside the box does not change the parent's height, and
 * re-clamping on open is what moves the menu out from under the pointer.
 */
export function useViewportClamp<T extends HTMLElement = HTMLDivElement>(
  x: number,
  y: number,
  deps: unknown[] = [],
) {
  const ref = useRef<T | null>(null);
  const [clamped, setClamped] = useState<{ left: number; top: number } | null>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const { width, height } = el.getBoundingClientRect();
    const MARGIN = 8; // never flush against the edge
    setClamped({
      left: Math.max(MARGIN, Math.min(x, window.innerWidth - width - MARGIN)),
      top: Math.max(MARGIN, Math.min(y, window.innerHeight - height - MARGIN)),
      // A box TALLER than the viewport clamps to MARGIN and overflows the
      // bottom by construction; callers whose menus can reach that height cap
      // it with `max-height` + `overflow-y-auto` so the tail stays reachable.
    });
  }, [x, y, ...deps]); // eslint-disable-line react-hooks/exhaustive-deps

  // Until measured, sit at the raw point: the box is invisible for that tick
  // (the layout effect runs before paint), so this is the no-flash seed, not
  // a position anyone sees.
  return { ref, left: clamped?.left ?? x, top: clamped?.top ?? y, measured: clamped !== null };
}
