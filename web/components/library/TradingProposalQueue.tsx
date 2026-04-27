'use client';

/**
 * TradingProposalQueue — system component library, ADR-225.
 *
 * Renders pending trading proposals from action_proposals binding.
 * Placeholder visual; the real implementation reads action_proposals
 * filtered to trading-shaped envelopes with signal attribution. For
 * now, a placeholder pointing at the proposal review surface.
 *
 * Note (Phase 2 implementation refinement): the alpha-trader paper
 * design implied an `AttributedActionReview` universal that would
 * render this — but `TradingProposalQueue` is what alpha-trader's
 * SURFACES.yaml references. We ship the literal kind name; reconcile
 * with `AttributedActionReview` when alpha-prediction or alpha-defi
 * activate and the universal generalization is forced.
 */

import { TrendingUp } from 'lucide-react';
import Link from 'next/link';

interface TradingProposalQueueProps {
  /** Action-proposals filter declared in the binding. Currently surfaced
   * as a pointer; the visual rendering deferred to additive work. */
  filters?: Record<string, unknown>;
}

export function TradingProposalQueue({ filters }: TradingProposalQueueProps) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-neutral-900">
        <TrendingUp className="h-4 w-4" />
        Trading Proposal Queue
      </div>
      <div className="text-sm text-neutral-600">
        Pending trading proposals are reviewed in the{' '}
        <Link
          href="/agents?agent=reviewer"
          className="text-blue-600 underline hover:text-blue-700"
        >
          Reviewer queue
        </Link>
        .
      </div>
      {filters && Object.keys(filters).length > 0 && (
        <div className="mt-2 text-xs text-neutral-500">
          Filter: {Object.entries(filters).map(([k, v]) => `${k}=${String(v)}`).join(', ')}
        </div>
      )}
    </div>
  );
}
