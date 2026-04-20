'use client';

/**
 * ReviewSurface — composes three panes for the Review destination (ADR-200).
 *
 * Archetype composition per ADR-198 §3:
 *   - ReviewerCardPane: Dashboard archetype (IDENTITY.md render)
 *   - PrinciplesPane: Dashboard archetype (principles.md render + edit CTA)
 *   - DecisionsStreamPane: Stream archetype (decisions.md tail-parse with filters)
 *
 * All three panes read from existing /api/workspace/file?path= endpoints.
 * No new backend APIs. Principles edits route through YARNNN rail via the
 * onOpenChatDraft prop (invariant I2: no inline edit forms for foreign
 * substrate — writes flow through primitives, not surfaces).
 */

import { ReviewerCardPane } from './ReviewerCardPane';
import { PrinciplesPane } from './PrinciplesPane';
import { DecisionsStreamPane } from './DecisionsStreamPane';

export interface ReviewSurfaceProps {
  onOpenChatDraft: (prompt: string) => void;
}

export function ReviewSurface({ onOpenChatDraft }: ReviewSurfaceProps) {
  return (
    <div className="flex flex-1 flex-col gap-6 overflow-y-auto px-6 py-6">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <ReviewerCardPane />
        <PrinciplesPane onOpenChatDraft={onOpenChatDraft} />
      </div>
      <DecisionsStreamPane />
    </div>
  );
}
