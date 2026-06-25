'use client';

/**
 * KernelDecisionQueue — Home slot #3 (ADR-312).
 *
 * Kernel-universal: renders for EVERY workspace from kernel substrate
 * (the ADR-307 generic gated-action queue over `action_proposals`),
 * independent of which program is activated. Programs do NOT declare
 * this slot — the kernel owns it.
 *
 * Compact-by-design: shows the top few pending proposals as glanceable
 * rows with a "Review in Queue →" link to the full Queue surface. The
 * Home is a composition glance, not the place you act on each proposal
 * (that's /queue + the Feed). Self-hides when nothing is pending — the
 * cold-start Home stays honest (no empty card).
 */

import { useEffect, useState } from 'react';
import { Inbox, ArrowRight } from 'lucide-react';
import { SurfaceLink } from '@/components/shell/SurfaceLink';
import { api } from '@/lib/api/client';
// ADR-340 P4 F3: the single operator-language labeler — this file's
// inline label map + actionLabel() consolidated into the shared module
// (Singular Implementation; ProposalCard + AttentionCenter use the
// same import).
import { proposalActionLabel } from '@/lib/proposal-labels';

const COMPACT_LIMIT = 4;

interface PendingProposal {
  id: string;
  primitive: string;
  family: 'capital' | 'substrate';
  decision_context?: Record<string, unknown> | null;
  created_at: string;
}

interface KernelDecisionQueueProps {
  /**
   * ADR-312 home-bundle: when the Home pre-fetches the pending queue (one
   * bundled call), it passes it here and the slot skips its self-fetch.
   * Standalone mounts omit it and self-fetch.
   */
  initialProposals?: PendingProposal[];
}

export function KernelDecisionQueue({ initialProposals }: KernelDecisionQueueProps = {}) {
  const [proposals, setProposals] = useState<PendingProposal[] | null>(
    initialProposals ?? null,
  );

  useEffect(() => {
    // Primed by the home-bundle — nothing to fetch.
    if (initialProposals !== undefined) {
      setProposals(initialProposals);
      return;
    }
    let cancelled = false;
    api.proposals
      .list('pending', COMPACT_LIMIT + 1)
      .then((r) => {
        if (!cancelled) setProposals(r.proposals as PendingProposal[]);
      })
      .catch(() => {
        if (!cancelled) setProposals([]);
      });
    return () => {
      cancelled = true;
    };
  }, [initialProposals]);

  // Self-hide: loading or empty renders nothing (honest cold-start Home).
  if (!proposals || proposals.length === 0) return null;

  const shown = proposals.slice(0, COMPACT_LIMIT);
  const overflow = proposals.length - shown.length;

  return (
    <section
      aria-label="Decision queue"
      className="rounded-lg border border-border/60 bg-card/50"
    >
      <header className="flex items-center justify-between px-4 py-2.5 border-b border-border/40">
        <div className="flex items-center gap-2">
          <Inbox className="h-3.5 w-3.5 text-amber-600 shrink-0" />
          <h2 className="text-sm font-medium text-foreground">Waiting for your OK</h2>
          <span className="text-[11px] text-muted-foreground/60">{proposals.length}</span>
        </div>
        <SurfaceLink
          to="queue"
          className="inline-flex items-center gap-1 text-[11px] text-muted-foreground/70 hover:text-foreground transition-colors"
        >
          Review <ArrowRight className="h-3 w-3" />
        </SurfaceLink>
      </header>
      <ul className="divide-y divide-border/30">
        {shown.map((p) => (
          <li key={p.id}>
            <SurfaceLink
              to="queue"
              className="flex items-center gap-3 px-4 py-2.5 hover:bg-muted/40 transition-colors"
            >
              {/* Color dot distinguishes money-moving (amber) from
                  workspace-content (sky) actions without the jargon word. */}
              <span
                className={
                  p.family === 'capital'
                    ? 'h-1.5 w-1.5 rounded-full bg-amber-500 shrink-0'
                    : 'h-1.5 w-1.5 rounded-full bg-sky-500 shrink-0'
                }
                aria-hidden
              />
              <span className="flex-1 min-w-0 text-sm text-foreground truncate">
                {proposalActionLabel(p)}
              </span>
            </SurfaceLink>
          </li>
        ))}
      </ul>
      {overflow > 0 && (
        <SurfaceLink
          to="queue"
          className="block px-4 py-2 text-[11px] text-muted-foreground/60 hover:text-foreground hover:bg-muted/30 transition-colors border-t border-border/30"
        >
          +{overflow} more →
        </SurfaceLink>
      )}
    </section>
  );
}
