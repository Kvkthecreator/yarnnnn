'use client';

/**
 * QueueBody — the reusable pending-proposals body (ADR-346).
 *
 * Extracted from /queue/page.tsx so the SAME body mounts in two places
 * (the ADR-340 D8 "one body, two mounts" rule, mirroring the shared
 * ActivityLog):
 *   - the /queue mirror surface (QueuePage wraps this in SurfacePage)
 *   - the Operation composition's Resolve pane (mounts this bare)
 *
 * Both read the same action_proposals over the same ADR-307 gate (one
 * gate, one queue). The body owns its own data-load + modal + refresh;
 * the wrapper owns only the surface chrome.
 */

import { useCallback, useEffect, useState } from 'react';
import { Inbox, ShieldCheck } from 'lucide-react';
import { useProposalModal, type ProposalData } from '@/components/tp/ProposalCard';
import { api } from '@/lib/api/client';
import { proposalQueuedByDialLine } from '@/lib/proposal-labels';
import { cn } from '@/lib/utils';

interface QueueProposal extends ProposalData {
  created_at: string;
}

interface Occupant {
  occupant: string;
  occupant_class: 'human' | 'ai' | 'external' | 'impersonated' | '';
  display_label: string;
}

type QueueFamily = 'capital' | 'external-write' | 'substrate';

// ADR-307 (2026-06-19): external-write joins capital + substrate. Audience-
// addressing sends (Slack channel post, Notion page/block, email blast) the
// operator must approve under bounded/manual — a third-party-affecting effect,
// not a money move and not a file diff.
const FAMILY_META: Record<QueueFamily, { label: string; help: string; dot: string }> = {
  capital: {
    label: 'Money-moving',
    help: 'Actions that move capital or bind an external transaction.',
    dot: 'bg-amber-500',
  },
  'external-write': {
    label: 'Outbound messages',
    help: 'Posts, pages, or emails sent to an audience outside your workspace.',
    dot: 'bg-violet-500',
  },
  substrate: {
    label: 'Workspace changes',
    help: 'Edits to your workspace files — reversible via the revision chain.',
    dot: 'bg-sky-500',
  },
};

function rowLabel(p: QueueProposal): string {
  if (p.family === 'substrate') {
    const dc = (p.decision_context ?? {}) as Record<string, unknown>;
    const path = (dc.path as string) ?? ((dc.diff as { path?: string })?.path) ?? '';
    return path ? `Write · ${path}` : 'Substrate write';
  }
  const prim = p.primitive.replace(/^platform_/, '').replace(/_/g, ' ');
  return prim.charAt(0).toUpperCase() + prim.slice(1);
}

function relativeAge(iso: string): string {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return '';
  const mins = Math.round((Date.now() - t) / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
}

export function QueueBody() {
  const [proposals, setProposals] = useState<QueueProposal[] | null>(null);
  const [occupant, setOccupant] = useState<Occupant | null>(null);

  const load = useCallback(async () => {
    try {
      const r = await api.proposals.list('pending', 100);
      setProposals((r.proposals as unknown as QueueProposal[]) ?? []);
      const occ = r.current_occupant as Occupant | Record<string, never>;
      setOccupant('occupant' in occ ? (occ as Occupant) : null);
    } catch {
      setProposals([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // After approve/reject the modal closes → refresh so the resolved row drops.
  const { openProposal, modalElement } = useProposalModal({ onResolved: () => void load() });

  return (
    <>
      {proposals === null ? (
        <div className="h-24 rounded-md bg-muted/30 animate-pulse" />
      ) : proposals.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border/60 px-6 py-10 text-center">
          <Inbox className="mx-auto mb-3 h-6 w-6 text-muted-foreground/40" />
          <p className="text-sm font-medium text-foreground/80">Nothing awaiting your decision</p>
          <p className="mt-1 text-xs text-muted-foreground/70">
            When an agent proposes an action that needs your OK, it appears here.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {occupant && occupant.occupant_class && (
            <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground/70">
              <ShieldCheck className="h-3 w-3" />
              <span>
                Verdicts rendered by <span className="font-medium">{occupant.display_label}</span>
              </span>
            </div>
          )}
          {(['capital', 'external-write', 'substrate'] as const).map((family) => {
            const group = proposals.filter((p) => p.family === family);
            if (group.length === 0) return null;
            const meta = FAMILY_META[family];
            return (
              <section key={family} className="rounded-lg border border-border/60 overflow-hidden">
                <header className="flex items-center gap-2 border-b border-border/60 bg-muted/20 px-4 py-2">
                  <span className={cn('h-1.5 w-1.5 rounded-full shrink-0', meta.dot)} aria-hidden />
                  <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    {meta.label}
                  </span>
                  <span className="text-[11px] text-muted-foreground/50">{group.length}</span>
                  <span className="ml-auto hidden sm:block text-[11px] text-muted-foreground/50">{meta.help}</span>
                </header>
                <ul className="divide-y divide-border/40">
                  {group.map((p) => (
                    <li key={p.id}>
                      <button
                        type="button"
                        onClick={() => openProposal(p)}
                        className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-muted/40 transition-colors"
                      >
                        <span className={cn('h-1.5 w-1.5 rounded-full shrink-0', meta.dot)} aria-hidden />
                        <span className="flex-1 min-w-0">
                          <span className="block text-sm text-foreground truncate">{rowLabel(p)}</span>
                          {/* ADR-408 D5.2: agent-queued rows attribute the
                              queuing to the agent's witness dial (ADR-405),
                              not a permission failure. */}
                          {proposalQueuedByDialLine(p.source) && (
                            <span className="block text-[11px] text-muted-foreground/50 truncate">
                              {proposalQueuedByDialLine(p.source)}
                            </span>
                          )}
                        </span>
                        {(p.agent_identity ?? p.reviewer_identity)?.startsWith('ai:') && (
                          <span className="shrink-0 text-[10px] rounded-full bg-emerald-500/10 px-1.5 py-0.5 text-emerald-700 dark:text-emerald-400">
                            Agent approved
                          </span>
                        )}
                        <span className="shrink-0 text-[11px] text-muted-foreground/50">{relativeAge(p.created_at)}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            );
          })}
        </div>
      )}
      {modalElement}
    </>
  );
}
