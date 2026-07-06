'use client';

/**
 * NeedsMePane — Queue archetype (ADR-198 §3).
 *
 * Lists pending action_proposals needing operator attention.
 * Each proposal rendered with ProposalCard (shipped in ADR-193 Phase 2).
 * Surface action affordances (approve/reject) live here per Q2 invariant.
 *
 * Empty state is silent-friendly: "Nothing needs you right now."
 * Never silent in the "loading failed" sense — show an error state with retry.
 *
 * Reads from existing /api/proposals?status=pending. No new API.
 */

import { useEffect, useState, useCallback } from 'react';
import { Loader2, AlertCircle, Clock, ShieldAlert } from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { useProposalModal } from '@/components/tp/ProposalCard';
import { proposalQueuedByDialLine } from '@/lib/proposal-labels';

type Proposal = Awaited<ReturnType<typeof api.proposals.list>>['proposals'][number];

const INLINE_LIMIT = 3;

export interface NeedsMePaneProps {
  onOpenChatDraft: (prompt: string) => void;
}

export function NeedsMePane({ onOpenChatDraft }: NeedsMePaneProps) {
  const [proposals, setProposals] = useState<Proposal[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { proposals } = await api.proposals.list('pending', 50);
      setProposals(proposals);
    } catch (err) {
      const msg =
        err instanceof APIError
          ? (err.data as { detail?: string } | null)?.detail ?? err.message
          : err instanceof Error
            ? err.message
            : 'Failed to load proposals';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading && proposals === null) {
    return (
      <PaneFrame title="Needs me">
        <div className="flex items-center justify-center py-6">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      </PaneFrame>
    );
  }

  if (error) {
    return (
      <PaneFrame title="Needs me">
        <div className="flex items-center gap-2 rounded-md border border-border bg-muted/30 px-3 py-2 text-sm text-muted-foreground">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span className="flex-1">{error}</span>
          <button
            onClick={() => void load()}
            className="rounded px-2 py-0.5 text-xs font-medium hover:bg-muted hover:text-foreground"
          >
            Retry
          </button>
        </div>
      </PaneFrame>
    );
  }

  const list = proposals ?? [];
  if (list.length === 0) {
    return (
      <PaneFrame title="Needs me">
        <p className="rounded-md border border-dashed border-border px-4 py-6 text-center text-sm text-muted-foreground">
          Nothing needs you right now.
        </p>
      </PaneFrame>
    );
  }

  const inline = list.slice(0, INLINE_LIMIT);
  const overflow = list.length - inline.length;

  return (
    <NeedsMePaneBody
      list={list}
      inline={inline}
      overflow={overflow}
      onReload={load}
      onOpenChatDraft={onOpenChatDraft}
    />
  );
}

/**
 * Hook-bearing body extracted so useProposalModal() can be called
 * unconditionally (Rules of Hooks) — the empty/loading/error early-
 * returns in the parent skip past hook calls.
 */
function NeedsMePaneBody({
  list,
  inline,
  overflow,
  onReload,
  onOpenChatDraft,
}: {
  list: Proposal[];
  inline: Proposal[];
  overflow: number;
  onReload: () => Promise<void>;
  onOpenChatDraft: (prompt: string) => void;
}) {
  // ADR-258 + Audit C LB-2 (2026-05-11): briefing Queue rows open the
  // same InteractiveModal + ProposalDetail that chat-stream ProposalCard
  // uses. Singular Implementation: one modal path, three entry points
  // (chat ProposalCard chip + cockpit TrackingFace ProposalRow + briefing
  // NeedsMePane row).
  const { openProposal, modalElement } = useProposalModal({
    onResolved: () => {
      void onReload();
    },
  });

  return (
    <PaneFrame title={`Needs me · ${list.length}`}>
      <div className="flex flex-col gap-2">
        {inline.map((p) => (
          <InlineProposalRow
            key={p.id}
            proposal={p}
            onOpen={() => openProposal(adaptProposalForModal(p))}
          />
        ))}
      </div>
      {overflow > 0 && (
        <div className="mt-2 text-center">
          <button
            onClick={() =>
              onOpenChatDraft(
                `Show me the ${overflow} additional pending proposals`,
              )
            }
            className="text-xs font-medium text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
          >
            See {overflow} more
          </button>
        </div>
      )}
      {modalElement}
    </PaneFrame>
  );
}

// Adapter: api.proposals.list shape → ProposalCard's ProposalData shape.
// Same shape as TrackingFace.adaptProposalForModal — kept local to avoid
// a 3-line shared module. If a third caller emerges, hoist to a shared
// helper.
function adaptProposalForModal(p: Proposal): import('@/components/tp/ProposalCard').ProposalData {
  // ADR-307: generic gated-action queue shape (primitive + family +
  // decision_context). ProposalCard normalizes decision_context per family.
  return {
    id: p.id,
    primitive: p.primitive,
    family: p.family,
    decision_context: p.decision_context ?? undefined,
    expires_at: p.expires_at,
    status: p.status,
    inputs: p.inputs,
    // ADR-408 D5.2: the modal attributes agent-queued proposals to the
    // agent's witness dial (ADR-405).
    source: p.source,
  };
}

function PaneFrame({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </h2>
      {children}
    </section>
  );
}

/**
 * Inline row — compact proposal preview, click-to-inspect-and-act.
 *
 * Per Audit C LB-2 (2026-05-11): all proposal-row surfaces (chat
 * ProposalCard, cockpit TrackingFace, briefing NeedsMePane) route
 * approval through the SAME InteractiveModal + ProposalDetail.
 * Pre-2026-05-11, this row had inline Approve/Reject buttons that
 * bypassed the modal — operators acted on proposals without seeing
 * reviewer reasoning, expected_effect, or risk_warnings (Channel-
 * legibility violation per Derived Principle 12).
 */
function InlineProposalRow({
  proposal,
  onOpen,
}: {
  proposal: Proposal;
  onOpen: () => void;
}) {
  const ttl = formatTTL(proposal.expires_at);
  const dc = (proposal.decision_context ?? {}) as Record<string, unknown>;
  // ADR-307: reversibility lives in capital decision_context; substrate writes
  // are reversible via the revision chain (never flagged irreversible).
  const irreversible = proposal.family === 'capital' && dc.reversibility === 'irreversible';
  const label = formatProposalLabel(proposal);
  const summary = proposal.family === 'substrate'
    ? (dc.message as string) || ''
    : (dc.rationale as string) || '';

  return (
    <button
      type="button"
      onClick={onOpen}
      aria-label={`Open ${label} proposal`}
      className="w-full rounded-md border border-border bg-card px-3 py-2 text-left transition-colors hover:border-foreground/40 hover:bg-muted/30 focus:outline-none focus:ring-1 focus:ring-foreground/40"
    >
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-foreground">
          {label}
        </span>
        {irreversible && (
          <span className="inline-flex items-center gap-1 rounded-sm bg-destructive/10 px-1.5 py-0.5 text-[10px] font-medium uppercase text-destructive">
            <ShieldAlert className="h-3 w-3" />
            Irreversible
          </span>
        )}
        <span className="ml-auto inline-flex items-center gap-1 text-[11px] text-muted-foreground">
          <Clock className="h-3 w-3" />
          {ttl}
        </span>
      </div>
      {summary && (
        <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
          {summary}
        </p>
      )}
      {/* ADR-408 D5.2: agent-queued rows attribute the queuing to the agent's
          witness dial (ADR-405), not a permission failure. */}
      {proposalQueuedByDialLine(proposal.source) && (
        <p className="mt-1 text-[11px] text-muted-foreground/50">
          {proposalQueuedByDialLine(proposal.source)}
        </p>
      )}
      <p className="mt-1.5 text-[10px] uppercase tracking-wide text-muted-foreground/60">
        Click to inspect &amp; act
      </p>
    </button>
  );
}

// ADR-307: human label from (primitive, family). Substrate → target path;
// capital → provider · tool.
function formatProposalLabel(p: Proposal): string {
  if (p.family === 'substrate') {
    const dc = (p.decision_context ?? {}) as Record<string, unknown>;
    const path = (dc.path as string) ?? ((dc.diff as { path?: string })?.path) ?? '';
    return path ? `Write · ${path}` : 'Substrate write';
  }
  const prim = p.primitive.replace(/^platform_/, '');
  const [provider, ...rest] = prim.split('_');
  if (!provider || rest.length === 0) return prim;
  return `${capitalize(provider)} · ${capitalize(rest.join(' '))}`;
}

function capitalize(s: string): string {
  return s.length > 0 ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

function formatTTL(iso: string): string {
  const expires = new Date(iso).getTime();
  const now = Date.now();
  const diffMs = expires - now;
  if (diffMs <= 0) return 'expired';
  const hours = Math.floor(diffMs / 3_600_000);
  const mins = Math.floor((diffMs % 3_600_000) / 60_000);
  if (hours >= 24) {
    const days = Math.floor(hours / 24);
    return `${days}d ${hours - days * 24}h`;
  }
  if (hours >= 1) return `${hours}h ${mins}m`;
  return `${mins}m`;
}
