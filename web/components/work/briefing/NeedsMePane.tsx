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
import { cn } from '@/lib/utils';

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
    <PaneFrame title={`Needs me · ${list.length}`}>
      <div className="flex flex-col gap-2">
        {inline.map((p) => (
          <InlineProposalRow key={p.id} proposal={p} onReload={load} />
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
    </PaneFrame>
  );
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
 * Inline row — compact proposal preview with inline approve/reject.
 *
 * Simpler than the full ProposalCard (which renders inside chat conversation
 * context). Inline here means: single line title + rationale, two buttons,
 * TTL badge. Deep-link to chat for full conversation if the user wants to
 * modify or discuss.
 */
function InlineProposalRow({
  proposal,
  onReload,
}: {
  proposal: Proposal;
  onReload: () => Promise<void>;
}) {
  const [acting, setActing] = useState<null | 'approve' | 'reject'>(null);
  const [error, setError] = useState<string | null>(null);

  const handleApprove = async () => {
    setActing('approve');
    setError(null);
    try {
      const result = await api.proposals.approve(proposal.id);
      if (!result.success) {
        setError(result.error ?? 'Failed to approve');
        setActing(null);
        return;
      }
      await onReload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve');
      setActing(null);
    }
  };

  const handleReject = async () => {
    setActing('reject');
    setError(null);
    try {
      await api.proposals.reject(proposal.id);
      await onReload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject');
      setActing(null);
    }
  };

  const ttl = formatTTL(proposal.expires_at);
  const irreversible = proposal.reversibility === 'irreversible';

  return (
    <div className="rounded-md border border-border bg-card px-3 py-2">
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-foreground">
          {formatActionType(proposal.action_type)}
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
      {proposal.rationale && (
        <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
          {proposal.rationale}
        </p>
      )}
      {error && (
        <p className="mt-1 text-[11px] text-destructive">{error}</p>
      )}
      <div className="mt-2 flex items-center gap-1.5">
        <button
          onClick={handleApprove}
          disabled={acting !== null}
          className={cn(
            'rounded-md bg-foreground px-2.5 py-1 text-[11px] font-medium text-background hover:opacity-90',
            acting === 'approve' && 'opacity-60',
          )}
        >
          {acting === 'approve' ? 'Approving…' : 'Approve'}
        </button>
        <button
          onClick={handleReject}
          disabled={acting !== null}
          className={cn(
            'rounded-md border border-border px-2.5 py-1 text-[11px] text-muted-foreground hover:bg-muted hover:text-foreground',
            acting === 'reject' && 'opacity-60',
          )}
        >
          {acting === 'reject' ? 'Rejecting…' : 'Reject'}
        </button>
      </div>
    </div>
  );
}

function formatActionType(action: string): string {
  const [provider, ...rest] = action.split('.');
  if (!provider || rest.length === 0) return action;
  const tool = rest.join('.').replace(/_/g, ' ');
  return `${capitalize(provider)} · ${capitalize(tool)}`;
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
