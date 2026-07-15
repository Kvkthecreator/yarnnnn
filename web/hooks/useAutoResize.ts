'use client';

/**
 * useAutoResize — the ONE composer auto-grow rule.
 *
 * A message composer grows with what you're writing and then holds, scrolling
 * inside itself. That's the CLI/Claude-Code gesture: the box is one line when
 * you have one line to say, and a paragraph when you have a paragraph — you
 * never type into a slit that scrolls out from under you.
 *
 * A `<textarea rows={1}>` does NOT do this. `rows` fixes the intrinsic height,
 * and a CSS `max-h-*` only defines a ceiling — nothing ever pushes the element
 * up to it. The height must be written from `scrollHeight` on every change,
 * which is what this hook does.
 *
 * Extracted from ConversationPanel (the shell drawer), which was the only
 * composer in the codebase that grew correctly, so that LanePanel (which
 * powers BOTH /chat and the Studio bound lane) inherits the same behavior
 * rather than growing a second copy of the rule that drifts from it.
 *
 * The `height='auto'` reset before each read is load-bearing: without it,
 * `scrollHeight` can never report LESS than the current height, so the box
 * would grow and never shrink back when text is deleted.
 */

import { useCallback, useEffect, type RefObject } from 'react';

/** The composer ceiling, in px. Past this the textarea scrolls internally —
 *  a composer that grows without bound eats the transcript it's replying to. */
export const COMPOSER_MAX_PX = 150;

/**
 * Grow `ref`'s textarea to fit `value`, capped at `maxPx`, then scroll.
 *
 * @param ref    the textarea
 * @param value  the controlled value — re-measures whenever it changes
 * @param maxPx  the ceiling (defaults to the shared COMPOSER_MAX_PX)
 * @returns      `measure()`, for callers that mutate the value imperatively
 *               (a paste handler, a slash-command insert) and need to re-fit
 *               without waiting for a render.
 */
export function useAutoResize(
  ref: RefObject<HTMLTextAreaElement>,
  value: string,
  maxPx: number = COMPOSER_MAX_PX,
): () => void {
  const measure = useCallback(() => {
    const ta = ref.current;
    if (!ta) return;
    // Reset first — scrollHeight can't report smaller than the set height, so
    // without this the box would never shrink back on delete.
    ta.style.height = 'auto';
    ta.style.height = `${Math.min(ta.scrollHeight, maxPx)}px`;
  }, [ref, maxPx]);

  useEffect(() => {
    measure();
  }, [value, measure]);

  return measure;
}
