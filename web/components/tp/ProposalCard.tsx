'use client';

/**
 * ProposalCard — ADR-193 Phase 2 inline approval UI
 *
 * Rendered when a tool result has `toolName === 'ProposeAction'` and
 * `data.success === true`. Shows the proposal's rationale + expected effect
 * + reversibility + TTL, with Approve / Reject buttons that call the
 * /api/proposals/:id/{approve,reject} endpoints directly (no LLM round-trip).
 *
 * Modify flow is not included in Phase 2 — if the user wants to adjust,
 * they tell YARNNN in chat ("make that price $18 instead") and YARNNN
 * re-proposes. Simpler + faster than a form-based modify.
 */

import { useState, useMemo } from 'react';
import { CheckCircle2, XCircle, Clock, ShieldAlert, Loader2, AlertCircle } from 'lucide-react';
import api from '@/lib/api/client';
import { cn } from '@/lib/utils';

interface ProposalCardProps {
  /** Full result payload from ProposeAction tool — shape matches backend response. */
  result: {
    success: boolean;
    proposal_id?: string;
    proposal?: {
      id: string;
      action_type: string;
      rationale: string;
      expected_effect: string;
      reversibility: 'reversible' | 'soft-reversible' | 'irreversible';
      risk_warnings: string[];
      expires_at: string;
      status: string;
    };
    error?: string;
    message?: string;
  };
}

type LocalStatus = 'pending' | 'approving' | 'approved' | 'rejecting' | 'rejected' | 'error';

function formatActionType(action: string): string {
  // "trading.submit_bracket_order" → "Trading · Submit bracket order"
  const [provider, ...rest] = action.split('.');
  const tool = rest.join('.').replace(/_/g, ' ');
  return `${provider.charAt(0).toUpperCase()}${provider.slice(1)} · ${tool.charAt(0).toUpperCase()}${tool.slice(1)}`;
}

function formatExpiresAt(iso: string): string {
  const expires = new Date(iso).getTime();
  const now = Date.now();
  const diffMs = expires - now;
  if (diffMs <= 0) return 'expired';
  const hours = Math.floor(diffMs / 3_600_000);
  const mins = Math.floor((diffMs % 3_600_000) / 60_000);
  if (hours >= 1) return `in ${hours}h ${mins}m`;
  return `in ${mins}m`;
}

function reversibilityTone(r: string): { label: string; className: string } {
  switch (r) {
    case 'reversible':
      return { label: 'Reversible', className: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20' };
    case 'soft-reversible':
      return { label: 'Soft-reversible', className: 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20' };
    case 'irreversible':
      return { label: 'Irreversible', className: 'bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/20' };
    default:
      return { label: r, className: 'bg-muted text-muted-foreground' };
  }
}

export function ProposalCard({ result }: ProposalCardProps) {
  // Guard — ProposeAction may have errored; render fallback
  if (!result.success || !result.proposal) {
    return (
      <div className="rounded-lg border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm">
        <div className="flex items-center gap-2 text-destructive">
          <AlertCircle className="w-4 h-4" />
          <span className="font-medium">Proposal couldn't be created</span>
        </div>
        {result.message && <div className="mt-1 text-xs text-muted-foreground">{result.message}</div>}
      </div>
    );
  }

  const proposal = result.proposal;
  const [status, setStatus] = useState<LocalStatus>('pending');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const revTone = useMemo(() => reversibilityTone(proposal.reversibility), [proposal.reversibility]);
  const expiresLabel = formatExpiresAt(proposal.expires_at);

  const handleApprove = async () => {
    setStatus('approving');
    setErrorMsg(null);
    try {
      const res = await api.proposals.approve(proposal.id);
      if (res.success) {
        setStatus('approved');
      } else {
        setStatus('error');
        setErrorMsg(res.error || 'Execution failed');
      }
    } catch (err) {
      setStatus('error');
      setErrorMsg(err instanceof Error ? err.message : 'Network error');
    }
  };

  const handleReject = async () => {
    setStatus('rejecting');
    setErrorMsg(null);
    try {
      const res = await api.proposals.reject(proposal.id);
      if (res.success) {
        setStatus('rejected');
      } else {
        setStatus('error');
        setErrorMsg('Rejection failed');
      }
    } catch (err) {
      setStatus('error');
      setErrorMsg(err instanceof Error ? err.message : 'Network error');
    }
  };

  const isTerminal = status === 'approved' || status === 'rejected';
  const isLoading = status === 'approving' || status === 'rejecting';

  return (
    <div
      className={cn(
        'rounded-lg border overflow-hidden',
        status === 'approved' ? 'border-emerald-500/40 bg-emerald-500/5' :
        status === 'rejected' ? 'border-muted bg-muted/20' :
        status === 'error' ? 'border-destructive/40 bg-destructive/5' :
        'border-border bg-muted/10',
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border/40 bg-muted/20">
        <span className="text-xs font-medium tracking-wider text-muted-foreground uppercase">
          Proposal
        </span>
        <span className="text-xs text-muted-foreground/70 truncate">
          {formatActionType(proposal.action_type)}
        </span>
        <span
          className={cn(
            'ml-auto inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[10px] font-medium',
            revTone.className,
          )}
        >
          {revTone.label}
        </span>
      </div>

      {/* Body */}
      <div className="px-3 py-2.5 space-y-2">
        {proposal.rationale && (
          <div className="text-sm">{proposal.rationale}</div>
        )}
        {proposal.expected_effect && (
          <div className="text-xs text-muted-foreground border-l-2 border-border pl-2">
            {proposal.expected_effect}
          </div>
        )}
        {proposal.risk_warnings && proposal.risk_warnings.length > 0 && (
          <div className="flex items-start gap-1.5 rounded border border-amber-500/30 bg-amber-500/5 px-2 py-1.5">
            <ShieldAlert className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
            <div className="text-xs text-amber-900 dark:text-amber-100 space-y-0.5">
              {proposal.risk_warnings.map((w, i) => (
                <div key={i}>{w}</div>
              ))}
            </div>
          </div>
        )}

        {/* Expiration + action area */}
        {status === 'pending' && (
          <div className="flex items-center gap-2 pt-1">
            <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
              <Clock className="w-3 h-3" />
              <span>expires {expiresLabel}</span>
            </div>
            <div className="flex-1" />
            <button
              type="button"
              onClick={handleReject}
              disabled={isLoading}
              className="px-2.5 py-1 text-xs rounded border border-border hover:bg-muted transition-colors disabled:opacity-50"
            >
              Reject
            </button>
            <button
              type="button"
              onClick={handleApprove}
              disabled={isLoading}
              className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded bg-foreground text-background hover:bg-foreground/90 transition-colors disabled:opacity-50"
            >
              Approve
            </button>
          </div>
        )}

        {status === 'approving' && (
          <div className="flex items-center gap-2 pt-1 text-xs text-muted-foreground">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span>Executing…</span>
          </div>
        )}

        {status === 'rejecting' && (
          <div className="flex items-center gap-2 pt-1 text-xs text-muted-foreground">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span>Rejecting…</span>
          </div>
        )}

        {status === 'approved' && (
          <div className="flex items-center gap-2 pt-1 text-xs text-emerald-700 dark:text-emerald-400">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Approved + executed</span>
          </div>
        )}

        {status === 'rejected' && (
          <div className="flex items-center gap-2 pt-1 text-xs text-muted-foreground">
            <XCircle className="w-3.5 h-3.5" />
            <span>Rejected</span>
          </div>
        )}

        {status === 'error' && (
          <div className="flex items-start gap-2 pt-1 text-xs text-destructive">
            <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <div>Something went wrong</div>
              {errorMsg && <div className="text-muted-foreground">{errorMsg}</div>}
            </div>
          </div>
        )}
      </div>

      {/* Terminal status hint */}
      {isTerminal && (
        <div className="border-t border-border/30 bg-muted/10 px-3 py-1.5 text-[10px] text-muted-foreground/70">
          YARNNN will reflect this in the next turn.
        </div>
      )}
    </div>
  );
}
