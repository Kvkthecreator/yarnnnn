/**
 * OperatorEventMarker — Feed timeline operator message row (ADR-289).
 *
 * Operator messages (`role='user'`) on the Feed render as standalone
 * marker rows, NOT as right-aligned chat bubbles. The Feed is the
 * operations timeline, not a conversation — the operator is one actor
 * among many. When the message led to an addressed Reviewer exchange
 * (shares invocation_id with downstream Reviewer rows), the marker
 * carries a pointer "opened conversation with Reviewer →" that opens
 * the Conversation drawer scrolled to that invocation.
 *
 * Compact, left-aligned, monochrome — distinct from the bubble grammar
 * used in the Conversation surface.
 */

'use client';

import { CornerDownRight, MessageCircle } from 'lucide-react';
import type { OperatorEventUnit } from '@/lib/feed-grouping';
import { PrincipalBadge } from '@/lib/workspace/principal-badge';

interface OperatorEventMarkerProps {
  unit: OperatorEventUnit;
  /** Open the Conversation drawer scrolled to the given invocation_id.
   *  When undefined, the "opened conversation" affordance does not appear
   *  even if `unit.ledToInvocation` is true. */
  onOpenConversation?: (invocationId: string) => void;
}

export function OperatorEventMarker({
  unit,
  onOpenConversation,
}: OperatorEventMarkerProps) {
  const time = unit.timestamp.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });

  const canOpenConversation =
    unit.ledToInvocation && unit.invocationId && onOpenConversation;

  return (
    <div className="px-2 py-1.5 my-0.5">
      {/* Header row: actor + time. Operator marker is always the operator →
          the shared PrincipalBadge ("You" + the operator glyph), consistent
          with the actor identity shown on every other surface (2026-06-30). */}
      <div className="flex items-baseline gap-2 mb-0.5">
        <PrincipalBadge authoredBy="operator" size={12} />
        <span className="text-[10px] text-muted-foreground/50 tabular-nums">
          {time}
        </span>
      </div>

      {/* Message content — left-aligned, no bubble chrome */}
      <p className="text-[13px] text-foreground/90 whitespace-pre-wrap break-words">
        {unit.message.content}
      </p>

      {/* "opened conversation" affordance — only when the message led to
          an addressed exchange and the parent gave us a drawer-opener. */}
      {canOpenConversation && (
        <button
          type="button"
          onClick={() => onOpenConversation!(unit.invocationId!)}
          className="mt-1 inline-flex items-center gap-1 text-[11px] font-medium text-primary/70 hover:text-primary hover:bg-primary/5 px-1.5 py-0.5 -mx-0.5 rounded transition-colors"
          title="Open this conversation with the Reviewer"
        >
          <MessageCircle className="w-3 h-3" />
          opened conversation with Reviewer
          <CornerDownRight className="w-3 h-3" />
        </button>
      )}
    </div>
  );
}
