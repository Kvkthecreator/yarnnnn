'use client';

/**
 * ReviewerDetailView — Reviewer as systemic agent detail (ADR-214).
 *
 * Absorbs the prior `/review` destination composition into the Agents page's
 * detail slot. Reviewer is one of two systemic Agents per ADR-212; both
 * YARNNN and Reviewer live as systemic detail views inside `/agents` rather
 * than as top-level cockpit tabs.
 *
 * Panes (all substrate reads via existing /api/workspace/file):
 *   - ReviewerCardPane: IDENTITY.md render (Dashboard archetype, ADR-198 §3)
 *   - PrinciplesPane: principles.md render + deep-link to Files for edits
 *     (Dashboard + R3-compliant substrate path per ADR-215 Phase 3)
 *   - DecisionsStreamPane: decisions.md tail-parse with filters (Stream)
 *
 * ADR-215 R3: no chat-routed edit affordances. All operator edits to
 * Reviewer substrate (IDENTITY, principles) happen on Files with
 * `authored_by=operator` attribution via the revision chain (ADR-209).
 * decisions.md is append-only (Stream archetype invariant); it is never
 * operator-edited.
 */

import { ReviewerCardPane } from './ReviewerCardPane';
import { PrinciplesPane } from './PrinciplesPane';
import { DecisionsStreamPane } from './DecisionsStreamPane';

export function ReviewerDetailView() {
  return (
    <div className="flex flex-1 flex-col gap-6 overflow-y-auto px-6 py-6">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <ReviewerCardPane />
        <PrinciplesPane />
      </div>
      <DecisionsStreamPane />
    </div>
  );
}
