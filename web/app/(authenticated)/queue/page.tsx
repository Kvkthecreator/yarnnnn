'use client';

/**
 * /queue — atomic Queue surface (ADR-297 D1).
 *
 * Lists pending action_proposals awaiting Reviewer or operator decision.
 * Phase 2 ships a thin placeholder pointing operators to the existing
 * proposal-review affordances on the Feed (where Reviewer verdict cards
 * already render). A richer dedicated queue view is a follow-on if
 * operator demand surfaces — the substrate (action_proposals) is in
 * place; this is purely a Channel-layer affordance.
 */

import Link from 'next/link';
import { Inbox, ArrowRight } from 'lucide-react';
import { SurfacePage } from '@/components/shell/SurfacePage';

export default function QueuePage() {
  return (
    <SurfacePage
      iconKey="inbox"
      title="Queue"
      summary="Pending proposals awaiting Reviewer or operator decision."
    >
      <div className="rounded-lg border border-dashed border-border/60 bg-card/40 px-6 py-10 text-center">
        <Inbox className="mx-auto mb-3 h-6 w-6 text-muted-foreground/40" />
        <p className="text-sm text-muted-foreground">
          Proposal review currently lives on the Feed where Reviewer verdicts
          render in-line as decisions are made. A dedicated queue browser
          arrives when there&apos;s operator demand for batch handling.
        </p>
        <Link
          href="/feed"
          className="mt-4 inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-sm font-medium text-foreground hover:bg-muted transition-colors"
        >
          Go to Feed
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </SurfacePage>
  );
}
