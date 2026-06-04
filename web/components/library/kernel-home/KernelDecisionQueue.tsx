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
import Link from 'next/link';
import { Inbox, ArrowRight } from 'lucide-react';
import { api } from '@/lib/api/client';

const COMPACT_LIMIT = 4;

interface PendingProposal {
  id: string;
  primitive: string;
  family: 'capital' | 'substrate';
  created_at: string;
}

// Plain-language label for a pending action. The operator sees what the
// action DOES in their words, not the primitive name. Known primitives map
// to a human verb; unknown ones fall back to a de-jargoned title-case.
const PRIMITIVE_LABELS: Record<string, string> = {
  WriteFile: 'Save a workspace change',
  EditFile: 'Edit a workspace file',
  Schedule: 'Change a schedule',
  ManageRecurrence: 'Change a schedule',
  FireInvocation: 'Run a task now',
  RuntimeDispatch: 'Generate an asset',
  InferContext: 'Update your context',
};

function actionLabel(primitive: string): string {
  if (PRIMITIVE_LABELS[primitive]) return PRIMITIVE_LABELS[primitive];
  // platform_trading_submit_order → "Trading submit order"
  const base = primitive.includes('_')
    ? primitive.replace(/^platform_/, '').replace(/_/g, ' ')
    : primitive.replace(/([a-z])([A-Z])/g, '$1 $2').toLowerCase();
  return base.charAt(0).toUpperCase() + base.slice(1);
}

export function KernelDecisionQueue() {
  const [proposals, setProposals] = useState<PendingProposal[] | null>(null);

  useEffect(() => {
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
  }, []);

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
        <Link
          href="/queue"
          className="inline-flex items-center gap-1 text-[11px] text-muted-foreground/70 hover:text-foreground transition-colors"
        >
          Review <ArrowRight className="h-3 w-3" />
        </Link>
      </header>
      <ul className="divide-y divide-border/30">
        {shown.map((p) => (
          <li key={p.id}>
            <Link
              href="/queue"
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
                {actionLabel(p.primitive)}
              </span>
            </Link>
          </li>
        ))}
      </ul>
      {overflow > 0 && (
        <Link
          href="/queue"
          className="block px-4 py-2 text-[11px] text-muted-foreground/60 hover:text-foreground hover:bg-muted/30 transition-colors border-t border-border/30"
        >
          +{overflow} more →
        </Link>
      )}
    </section>
  );
}
