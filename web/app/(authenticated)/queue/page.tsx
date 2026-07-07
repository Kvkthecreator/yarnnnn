'use client';

/**
 * /queue — atomic Queue surface (ADR-297 D1 + ADR-338 D4.3).
 *
 * The dedicated browse view of pending action_proposals (the ADR-307 generic
 * gated-action queue) — the OS "permission dialog" surface (ADR-338 D2). Lists
 * everything awaiting a decision, grouped by family (capital / substrate), each
 * row opening the full ProposalDetail modal (the SINGULAR modal path —
 * useProposalModal, shared with the Feed + cockpit + briefing) so the operator
 * sees the diff / order ticket + reviewer reasoning BEFORE approving.
 *
 * ADR-338 D4.3 closes the approve-blind hole: a substrate write's diff — incl.
 * the NULL-content case — is visible at approval time (SubstrateDiff warns on
 * absent or empty content). Batch handling (multi-select approve/reject) is
 * deferred — no operator demand yet; logged here, not silently dropped.
 *
 * Above the consent line (ADR-338 D3): approving binds the operation's action.
 *
 * ADR-346 (2026-06-19): the proposal body extracted to the reusable QueueBody
 * (one body, two mounts) — this mirror wraps it in SurfacePage; the Operation
 * composition's Resolve pane mounts it bare. Queue demoted primary → utilities
 * in the launcher; it stays the complete decide mirror, fronted by Operation.
 */

import { SurfacePage } from '@/components/shell/SurfacePage';
import { QueueBody } from '@/components/queue/QueueBody';

export default function QueuePage() {
  return (
    <SurfacePage
      iconKey="inbox"
      title="Queue"
      summary="Pending proposals awaiting your decision. Click any row to see the full diff or order ticket — and the agent's reasoning — before you approve."
    >
      <QueueBody />
    </SurfacePage>
  );
}
