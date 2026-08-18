'use client';

/**
 * useStickToBottom — THE scroll policy for chat-shaped transcripts (2026-08-18).
 *
 * One rule, the one every conventional chat surface implements (and the one
 * Claude Code's ScrollBox names `stickyScroll`): the view follows the bottom
 * while the reader is AT the bottom, and stops following the moment they
 * scroll up. Reading is never interrupted; new content below is announced by
 * the JumpToLatest affordance instead of a forced scroll.
 *
 * WHAT THIS REPLACES. Both transcripts (LanePanel, ConversationPanel) carried
 * a local `scrollIntoView({behavior:'smooth'})` effect keyed on message-array
 * identity. That policy had four defects, each felt constantly:
 *   - no pinned check → every streaming delta yanked a reader who had
 *     scrolled up back to the bottom;
 *   - array identity as the trigger → the 15s out-of-band poll re-scrolled
 *     even when nothing changed;
 *   - `smooth` on every delta → the animation restarted per token (judder),
 *     and the initial load ANIMATED through the whole history;
 *   - `scrollIntoView` scrolls every scrollable ANCESTOR, not just the
 *     transcript — in nested workbench panes that nudged outer containers.
 *
 * MECHANISM. Pinned-ness is derived from scroll position (distance from
 * bottom < threshold) on every scroll event. Following is driven by a
 * ResizeObserver on the CONTENT, not by message-keyed effects: content height
 * is the honest signal, because a transcript grows for reasons no message
 * array can see — an artifact card finishing its async load, a mermaid block
 * rendering, an image resolving. While pinned, growth sets `scrollTop`
 * directly (instant, container-scoped); while unpinned, growth does nothing.
 *
 * Mount contract: `containerRef` on the ONE scroll container (`overflow-y-auto`),
 * `contentRef` on its single content wrapper, `onScroll` is attached by the
 * hook itself. Call `scrollToBottom()` when the member ACTS (sending a
 * message always reveals it — their own turn is the one growth that re-pins).
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowDown } from 'lucide-react';

/** How close to the bottom still counts as "at the bottom". Generous enough
 *  that sub-line settling (fonts, fades) never un-pins; small enough that a
 *  deliberate scroll-up immediately does. */
const PIN_THRESHOLD_PX = 80;

export function useStickToBottom() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const contentRef = useRef<HTMLDivElement | null>(null);
  // Ref + state pair: the ResizeObserver callback reads the ref (no stale
  // closure, no effect re-subscription); the state drives the JumpToLatest
  // render.
  const pinnedRef = useRef(true);
  const [pinned, setPinned] = useState(true);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'auto') => {
    const el = containerRef.current;
    if (!el) return;
    // Re-pin FIRST, so growth landing mid-scroll keeps following.
    pinnedRef.current = true;
    setPinned(true);
    el.scrollTo({ top: el.scrollHeight, behavior });
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const onScroll = () => {
      const atBottom =
        el.scrollHeight - el.scrollTop - el.clientHeight <= PIN_THRESHOLD_PX;
      pinnedRef.current = atBottom;
      setPinned(atBottom);
    };
    el.addEventListener('scroll', onScroll, { passive: true });
    const ro = new ResizeObserver(() => {
      // Instant, container-scoped follow. Never smooth: a smooth follow
      // restarts per growth event and fights the reader's own wheel.
      if (pinnedRef.current) el.scrollTop = el.scrollHeight;
    });
    ro.observe(el); // the viewport itself resizing (window/pane resize)
    if (contentRef.current) ro.observe(contentRef.current); // content growth
    // Open AT the bottom, instantly — a transcript is read from its end.
    el.scrollTop = el.scrollHeight;
    return () => {
      el.removeEventListener('scroll', onScroll);
      ro.disconnect();
    };
  }, []);

  return { containerRef, contentRef, pinned, scrollToBottom };
}

/** The unpinned affordance: content may be arriving below; the way back is a
 *  click, never a forced scroll. Mount inside a `relative` wrapper around the
 *  scroll container. */
export function JumpToLatest({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Jump to latest"
      title="Jump to latest"
      className="absolute bottom-3 left-1/2 z-10 flex h-7 w-7 -translate-x-1/2 items-center justify-center rounded-full border border-border bg-background/95 text-muted-foreground shadow-sm transition-colors hover:bg-muted hover:text-foreground"
    >
      <ArrowDown className="h-3.5 w-3.5" />
    </button>
  );
}
