'use client';

/**
 * TradingProposalQueue — Trading-shaped proposal queue (alpha-trader bundle).
 *
 * 2026-04-28 reshape: was a placeholder; now reads real action_proposals
 * filtered to trading-shaped envelopes. Inline approve/reject affordances
 * mirror the kernel-default NeedsMePane shape (ADR-198 Q2 invariant —
 * Queue archetype carries action affordances).
 *
 * Filter inputs come from the SURFACES.yaml binding (`proposal_type=trading`,
 * `status=pending`). Today the filter is applied client-side after fetch;
 * when proposals scale we'll thread filters into the API.
 *
 * Proposals flagged as violations (risk_warnings present, or reviewer
 * reasoning indicating violation) surface in TrustViolations instead and
 * are excluded here — TrustViolations has stronger visual urgency. This
 * pane is the "routine decision queue," not the "trust break detector."
 */

import { useCallback, useEffect, useState } from 'react';
import { TrendingUp, Clock, ShieldAlert, Loader2, AlertCircle } from 'lucide-react';
import Link from 'next/link';
import { api, APIError } from '@/lib/api/client';
import { cn } from '@/lib/utils';

type Proposal = Awaited<ReturnType<typeof api.proposals.list>>['proposals'][number];

const INLINE_LIMIT = 3;

interface TradingProposalQueueProps {
  filters?: Record<string, unknown>;
}

function isTradingShaped(p: Proposal, filters?: Record<string, unknown>): boolean {
  // Prefer explicit task_slug match if filter declares one
  const expectedTaskSlug = filters?.task_slug as string | undefined;
  if (expectedTaskSlug && p.task_slug === expectedTaskSlug) return true;
  // Fall back to action_type prefix (alpaca.* envelopes are trading-shaped)
  if (p.action_type?.startsWith('alpaca.')) return true;
  // Or if the filter says proposal_type=trading and the task_slug carries 'trading'
  if (filters?.proposal_type === 'trading' && (p.task_slug ?? '').includes('trading')) return true;
  return false;
}

function isViolation(p: Proposal): boolean {
  const warnings = (p.risk_warnings ?? []) as unknown[];
  if (Array.isArray(warnings) && warnings.length > 0) return true;
  const reasoning = (p as { reviewer_reasoning?: string | null }).reviewer_reasoning ?? '';
  return /violat|principle|breach|exceed/i.test(reasoning);
}

export function TradingProposalQueue({ filters }: TradingProposalQueueProps) {
  const [proposals, setProposals] = useState<Proposal[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const { proposals } = await api.proposals.list('pending', 50);
      const trading = proposals.filter(
        (p) => isTradingShaped(p, filters) && !isViolation(p),
      );
      setProposals(trading);
    } catch (err) {
      const msg = err instanceof APIError
        ? (err.data as { detail?: string } | null)?.detail ?? err.message
        : err instanceof Error
          ? err.message
          : 'Failed to load proposals';
      setError(msg);
      setProposals([]);
    }
  }, [filters]);

  useEffect(() => { void load(); }, [load]);

  if (proposals === null) {
    return (
      <PaneFrame>
        <div className="flex items-center justify-center py-4">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      </PaneFrame>
    );
  }

  if (error) {
    return (
      <PaneFrame>
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

  if (proposals.length === 0) {
    return (
      <PaneFrame>
        <p className="rounded-md border border-dashed border-border px-4 py-4 text-center text-sm text-muted-foreground">
          No trading proposals waiting.
        </p>
      </PaneFrame>
    );
  }

  const inline = proposals.slice(0, INLINE_LIMIT);
  const overflow = proposals.length - inline.length;

  return (
    <PaneFrame count={proposals.length}>
      <div className="space-y-2">
        {inline.map((p) => (
          <InlineProposalRow key={p.id} proposal={p} onReload={load} />
        ))}
      </div>
      {overflow > 0 && (
        <div className="mt-2 text-center">
          <Link
            href="/agents?agent=reviewer"
            className="text-xs font-medium text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
          >
            See {overflow} more in Reviewer queue
          </Link>
        </div>
      )}
    </PaneFrame>
  );
}

function PaneFrame({ children, count }: { children: React.ReactNode; count?: number }) {
  return (
    <section className="rounded-lg border border-border bg-card p-4">
      <h3 className="mb-3 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground/70">
        <TrendingUp className="h-3.5 w-3.5" />
        Needs me{count !== undefined ? ` · ${count}` : ''}
      </h3>
      {children}
    </section>
  );
}

function InlineProposalRow({ proposal, onReload }: { proposal: Proposal; onReload: () => Promise<void> }) {
  const [acting, setActing] = useState<null | 'approve' | 'reject'>(null);
  const [rowError, setRowError] = useState<string | null>(null);

  const symbol = (proposal.inputs as { symbol?: string } | null)?.symbol ?? null;
  const side = (proposal.inputs as { side?: string } | null)?.side ?? null;
  const qty = (proposal.inputs as { qty?: number } | null)?.qty ?? null;
  const irreversible = proposal.reversibility === 'irreversible';
  const ttl = formatTTL(proposal.expires_at);

  const handle = async (action: 'approve' | 'reject') => {
    setActing(action);
    setRowError(null);
    try {
      if (action === 'approve') {
        const result = await api.proposals.approve(proposal.id);
        if (!result.success) {
          setRowError(result.error ?? 'Failed to approve');
          setActing(null);
          return;
        }
      } else {
        await api.proposals.reject(proposal.id);
      }
      await onReload();
    } catch (err) {
      setRowError(err instanceof Error ? err.message : `Failed to ${action}`);
      setActing(null);
    }
  };

  const headline = symbol && side
    ? `${side.toUpperCase()} ${symbol}${qty ? ` × ${qty}` : ''}`
    : proposal.action_type;

  return (
    <div className="rounded-md border border-border bg-background px-3 py-2">
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-foreground">{headline}</span>
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
        <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{proposal.rationale}</p>
      )}
      {rowError && (
        <p className="mt-1 text-[11px] text-destructive">{rowError}</p>
      )}
      <div className="mt-2 flex items-center gap-1.5">
        <button
          onClick={() => handle('approve')}
          disabled={acting !== null}
          className={cn(
            'rounded-md bg-foreground px-2.5 py-1 text-[11px] font-medium text-background hover:opacity-90',
            acting === 'approve' && 'opacity-60',
          )}
        >
          {acting === 'approve' ? 'Approving…' : 'Approve'}
        </button>
        <button
          onClick={() => handle('reject')}
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

function formatTTL(iso: string): string {
  const diff = new Date(iso).getTime() - Date.now();
  if (diff <= 0) return 'expired';
  const hours = Math.floor(diff / 3_600_000);
  const mins = Math.floor((diff % 3_600_000) / 60_000);
  if (hours >= 24) {
    const days = Math.floor(hours / 24);
    return `${days}d ${hours - days * 24}h`;
  }
  if (hours >= 1) return `${hours}h ${mins}m`;
  return `${mins}m`;
}
