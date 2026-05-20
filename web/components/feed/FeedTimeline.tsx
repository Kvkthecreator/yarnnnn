/**
 * FeedTimeline — operations timeline (ADR-289 D1 + D6).
 *
 * Renders the workspace narrative as a chronological multi-actor
 * operations timeline:
 *   - InvocationCard for each Reviewer cycle (rows sharing invocation_id)
 *   - OperatorEventMarker for operator messages (standalone markers per
 *     Option B — operator's question is hoisted out of the addressed
 *     cycle's card so chronological flow reads naturally)
 *   - StandaloneEventRow for rows without an invocation_id (legacy data,
 *     orphan system events, balance/capability/exception notifications)
 *   - DaySeparator between rows whose created_at days differ
 *
 * The chat-bubble grammar is retired on this surface. Bubbles imply
 * conversation; the Feed is operations. Conversation happens in the
 * ConversationDrawer (slide-over from this surface) or in the
 * right-panel ConversationPanel on other surfaces.
 *
 * Consumed by FeedSurface at the /feed route (center surface). Not used
 * elsewhere — the right-panel chat mounts use ConversationPanel.
 */

'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ArrowDown, Loader2 } from 'lucide-react';
import type { TPMessage } from '@/types/desk';
import { useNarrative } from '@/contexts/NarrativeContext';
import {
  groupFeedMessages,
  interleaveDaySeparators,
  type FeedRow,
} from '@/lib/feed-grouping';
import { DaySeparator } from './DaySeparator';
import { OperatorEventMarker } from './OperatorEventMarker';
import { InvocationCard } from './InvocationCard';
import { StandaloneEventRow } from './StandaloneEventRow';

export interface FeedTimelineProps {
  /** Empty-state content shown when messages.length === 0. */
  emptyState?: React.ReactNode;
  /** Called when operator activates the "opened conversation with
   *  Reviewer →" affordance on an addressed marker. Parent opens the
   *  ConversationDrawer scrolled to the given invocation_id. */
  onOpenConversation?: (invocationId: string) => void;
}

// Sticky-bottom threshold in pixels. If the scroll position is within
// this distance from the bottom, we consider the operator "at bottom"
// and auto-scroll new content into view. Larger than 0 because the
// operator's reading position naturally lags the bottom by a few rows.
const STICKY_BOTTOM_THRESHOLD_PX = 96;

export function FeedTimeline({ emptyState, onOpenConversation }: FeedTimelineProps) {
  const { messages, status } = useNarrative();
  const scrollerRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);

  // Sticky-bottom state: true when the operator's scroll position is at
  // or near the bottom. Drives whether new content auto-scrolls. Default
  // true so the initial render lands at the bottom.
  const [stickyBottom, setStickyBottom] = useState(true);

  // Group + interleave day separators. Pure derivation from messages
  // — recomputes on every messages change but the work is O(n) and
  // small even at 1000+ rows.
  const rows: FeedRow[] = useMemo(() => {
    const units = groupFeedMessages(messages);
    return interleaveDaySeparators(units);
  }, [messages]);

  // Sticky-bottom detection — runs on scroll. Updates the state only
  // when the at-bottom-ness changes, to avoid render churn.
  const handleScroll = useCallback(() => {
    const el = scrollerRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    const atBottom = distanceFromBottom <= STICKY_BOTTOM_THRESHOLD_PX;
    setStickyBottom((prev) => (prev === atBottom ? prev : atBottom));
  }, []);

  // Auto-scroll: only when sticky-bottom is true. If the operator has
  // scrolled up to read history, new entries don't yank them back down.
  // The "Jump to latest" affordance below opts the operator back in.
  useEffect(() => {
    if (!stickyBottom) return;
    if (messages.length === 0 && status.type === 'idle') return;
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, status, stickyBottom]);

  const jumpToLatest = useCallback(() => {
    setStickyBottom(true);
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  if (rows.length === 0 && status.type === 'idle' && emptyState) {
    return (
      <div className="flex-1 overflow-y-auto px-3 py-3">
        <div className="py-4 px-2">{emptyState}</div>
      </div>
    );
  }

  return (
    <div className="flex-1 min-h-0 relative">
      <div
        ref={scrollerRef}
        onScroll={handleScroll}
        className="absolute inset-0 overflow-y-auto px-3 pt-3 pb-12 space-y-1"
      >
        {rows.map((row) => renderRow(row, onOpenConversation))}

        {/* Status indicators — same shape as ConversationPanel for visual
            continuity when an addressed cycle is in progress. */}
        {status.type === 'thinking' && (
          <div className="flex items-center gap-1.5 pl-0.5 py-0.5 opacity-50">
            <Loader2 className="w-3 h-3 animate-spin text-muted-foreground" />
            <span className="text-[11px] text-muted-foreground">thinking</span>
          </div>
        )}
        {status.type === 'streaming' && status.content && (
          <div className="flex items-center gap-1.5 pl-0.5 py-0.5 opacity-60">
            <Loader2 className="w-3 h-3 animate-spin text-muted-foreground" />
            <span className="text-[11px] text-muted-foreground">{status.content}</span>
          </div>
        )}

        <div ref={endRef} />
      </div>

      {/* Jump-to-latest pill — appears when the operator has scrolled up
          and the timeline is not sticky-bottom. Click opts back into
          sticky-bottom + scrolls to the newest entry. */}
      {!stickyBottom && rows.length > 0 && (
        <button
          type="button"
          onClick={jumpToLatest}
          className="absolute bottom-4 left-1/2 -translate-x-1/2 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-full border border-border bg-background shadow-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors z-10"
          title="Jump to the latest entry"
        >
          <ArrowDown className="w-3.5 h-3.5" />
          Jump to latest
        </button>
      )}
    </div>
  );
}

function renderRow(
  row: FeedRow,
  onOpenConversation?: (invocationId: string) => void,
): JSX.Element {
  switch (row.kind) {
    case 'day-separator':
      return <DaySeparator key={row.id} date={row.date} />;
    case 'operator-event':
      return (
        <OperatorEventMarker
          key={row.id}
          unit={row}
          onOpenConversation={onOpenConversation}
        />
      );
    case 'invocation-card':
      return <InvocationCard key={row.id} unit={row} />;
    case 'standalone-event':
      return <StandaloneEventRow key={row.id} message={row.message} />;
  }
}

// Re-export the message type for parent typing.
export type { TPMessage };
