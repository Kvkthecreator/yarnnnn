'use client';

/**
 * KernelDecisionQueue — Home slot #3 (ADR-312, made act-in-place by ADR-367).
 *
 * Kernel-universal: renders for EVERY workspace from kernel substrate
 * (the ADR-307 generic gated-action queue over `action_proposals`),
 * independent of which program is activated. Programs do NOT declare
 * this slot — the kernel owns it.
 *
 * ADR-367 — Home as Operating Cockpit: this slot ACTS IN PLACE. A pending
 * proposal row is no longer a deep-link to /queue; clicking it opens the
 * shared `useProposalModal` overlay (the SAME modal QueueBody, the chat
 * stream, and the briefing queue use — Singular Implementation, one gate,
 * N entry points) so the operator approves/rejects through the ADR-307 gate
 * WITHOUT leaving Home. The cockpit decides on what it shows. Compact by
 * design (top few + a "Review →" into the Notifications workbench for the
 * full list); the breadth view stays in Notifications (deliberate tiered
 * redundancy, ADR-367 §D3 — the macOS Control-Center/System-Settings model).
 * Self-hides when nothing is pending — the cold-start Home stays honest.
 */

import { useCallback, useEffect, useState } from 'react';
import { Inbox, ArrowRight } from 'lucide-react';
import { SurfaceLink } from '@/components/shell/SurfaceLink';
import { useProposalModal, type ProposalData } from '@/components/tp/ProposalCard';
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
  family: 'capital' | 'external-write' | 'substrate';
  decision_context?: Record<string, unknown> | null;
  created_at: string;
  // ADR-367: the cockpit acts in place, so the slot carries the fields the
  // shared proposal modal needs (it renders inputs/diff + expiry + replays
  // the approve through the gate). The home-bundle + api.proposals.list both
  // provide the full row, so these are always present.
  expires_at?: string;
  status?: string;
  inputs?: Record<string, unknown>;
}

interface KernelDecisionQueueProps {
  /**
   * ADR-312 home-bundle: when the Home pre-fetches the pending queue (one
   * bundled call), it passes it here and the slot skips its self-fetch.
   * Standalone mounts omit it and self-fetch.
   */
  initialProposals?: PendingProposal[];
}

/** ADR-367: map a slot row to the shared modal's ProposalData. The modal
 * re-fetches live Reviewer state by id; we supply the fields it renders
 * before that returns (family/inputs/expiry/decision_context). */
function toProposalData(p: PendingProposal): ProposalData {
  return {
    id: p.id,
    primitive: p.primitive,
    family: p.family,
    decision_context: p.decision_context ?? undefined,
    expires_at: p.expires_at ?? '',
    status: p.status ?? 'pending',
    inputs: p.inputs,
  };
}

export function KernelDecisionQueue({ initialProposals }: KernelDecisionQueueProps = {}) {
  const [proposals, setProposals] = useState<PendingProposal[] | null>(
    initialProposals ?? null,
  );

  // ADR-367: after an inline approve/reject we refetch so the resolved row
  // drops (and the slot self-hides when the queue empties).
  const reload = useCallback(async () => {
    try {
      const r = await api.proposals.list('pending', COMPACT_LIMIT + 1);
      setProposals(r.proposals as unknown as PendingProposal[]);
    } catch {
      setProposals([]);
    }
  }, []);

  const { openProposal, modalElement } = useProposalModal({ onResolved: () => void reload() });

  useEffect(() => {
    // Primed by the home-bundle — nothing to fetch.
    if (initialProposals !== undefined) {
      setProposals(initialProposals);
      return;
    }
    void reload();
  }, [initialProposals, reload]);

  // Self-hide: loading or empty renders nothing (honest cold-start Home).
  if (!proposals || proposals.length === 0) return null;

  const shown = proposals.slice(0, COMPACT_LIMIT);
  const overflow = proposals.length - shown.length;

  return (
    <>
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
          {/* ADR-367 §D5: the full list lives in the Notifications workbench's
              Resolve pane (the post-ADR-349 canonical act surface), not the
              bare /queue mirror. */}
          <SurfaceLink
            to="notifications"
            params={{ pane: 'resolve' }}
            className="inline-flex items-center gap-1 text-[11px] text-muted-foreground/70 hover:text-foreground transition-colors"
          >
            Review <ArrowRight className="h-3 w-3" />
          </SurfaceLink>
        </header>
        <ul className="divide-y divide-border/30">
          {shown.map((p) => (
            <li key={p.id}>
              {/* ADR-367: act in place — open the shared proposal modal
                  (full reasoning + inputs + approve/reject through the
                  ADR-307 gate) as an overlay, no surface jump. */}
              <button
                type="button"
                onClick={() => openProposal(toProposalData(p))}
                className="flex w-full items-center gap-3 px-4 py-2.5 text-left hover:bg-muted/40 transition-colors"
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
              </button>
            </li>
          ))}
        </ul>
        {overflow > 0 && (
          <SurfaceLink
            to="notifications"
            params={{ pane: 'resolve' }}
            className="block px-4 py-2 text-[11px] text-muted-foreground/60 hover:text-foreground hover:bg-muted/30 transition-colors border-t border-border/30"
          >
            +{overflow} more →
          </SurfaceLink>
        )}
      </section>
      {modalElement}
    </>
  );
}
