'use client';

/**
 * ReviewerDetailView — Reviewer as systemic agent detail (ADR-214, 2026-04-23).
 *
 * Absorbs the prior `/review` destination composition into the Agents page's
 * detail slot. Reviewer is one of two systemic Agents per ADR-212; both
 * YARNNN and Reviewer live as systemic detail views inside `/agents` rather
 * than as top-level cockpit tabs.
 *
 * Panes (substrate reads via existing /api/workspace/file):
 *   - ReviewerCardPane: IDENTITY.md render (Dashboard archetype, ADR-198 §3)
 *   - PrinciplesPane: principles.md render + chat-routed edit CTA (Dashboard)
 *   - DecisionsStreamPane: decisions.md tail-parse with filters (Stream)
 *
 * Invariant preserved from ADR-200: principles edits route through YARNNN
 * rail via onOpenChatDraft — no inline edit forms for foreign substrate
 * (ADR-198 I2).
 */

import { ReviewerCardPane } from './ReviewerCardPane';
import { PrinciplesPane } from './PrinciplesPane';
import { DecisionsStreamPane } from './DecisionsStreamPane';

export interface ReviewerDetailViewProps {
  onOpenChatDraft?: (prompt: string) => void;
}

export function ReviewerDetailView({ onOpenChatDraft }: ReviewerDetailViewProps) {
  // Fall back to a no-op if the host doesn't wire up chat — the CTA will still
  // render but clicks become inert (host should always pass this in).
  const handleOpenChatDraft = onOpenChatDraft ?? (() => {});

  return (
    <div className="flex flex-1 flex-col gap-6 overflow-y-auto px-6 py-6">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <ReviewerCardPane />
        <PrinciplesPane onOpenChatDraft={handleOpenChatDraft} />
      </div>
      <DecisionsStreamPane />
    </div>
  );
}
