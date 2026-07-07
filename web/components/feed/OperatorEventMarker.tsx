/**
 * OperatorEventMarker — Feed timeline operator message row (ADR-289).
 *
 * Operator messages (`role='user'`) on the Feed render as standalone
 * marker rows, NOT as right-aligned chat bubbles. The Feed is the
 * operations timeline, not a conversation — the operator is one actor
 * among many.
 *
 * Compact, left-aligned, monochrome — distinct from the bubble grammar
 * used in the Conversation surface. (The "opened conversation →" drawer
 * affordance was deleted 2026-07-07 — unreachable under the sole
 * remaining mount, Channels In.)
 */

'use client';

import type { OperatorEventUnit } from '@/lib/feed-grouping';
import { PrincipalBadge } from '@/lib/workspace/principal-badge';

interface OperatorEventMarkerProps {
  unit: OperatorEventUnit;
}

export function OperatorEventMarker({ unit }: OperatorEventMarkerProps) {
  const time = unit.timestamp.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });

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
    </div>
  );
}
