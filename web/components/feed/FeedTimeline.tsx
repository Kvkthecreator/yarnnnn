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

import { useEffect, useMemo, useRef } from 'react';
import { Loader2 } from 'lucide-react';
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

export function FeedTimeline({ emptyState, onOpenConversation }: FeedTimelineProps) {
  const { messages, status } = useNarrative();
  const endRef = useRef<HTMLDivElement>(null);

  // Group + interleave day separators. Pure derivation from messages
  // — recomputes on every messages change but the work is O(n) and
  // small even at 1000+ rows.
  const rows: FeedRow[] = useMemo(() => {
    const units = groupFeedMessages(messages);
    return interleaveDaySeparators(units);
  }, [messages]);

  // Auto-scroll to bottom on new messages (operations timeline reads
  // newest-at-bottom like the Conversation surface).
  useEffect(() => {
    if (messages.length === 0 && status.type === 'idle') return;
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, status]);

  if (rows.length === 0 && status.type === 'idle' && emptyState) {
    return (
      <div className="flex-1 overflow-y-auto px-3 py-3">
        <div className="py-4 px-2">{emptyState}</div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-3 py-3 space-y-1">
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
