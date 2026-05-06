'use client';

/**
 * ProposalCard — inline proposal + Reviewer verdict card.
 *
 * ADR-249 D3 framing: the Reviewer IS the operator's judgment function.
 * The card shows what the Reviewer decided, then asks the user to ratify
 * or override that judgment — not to independently approve a system action.
 *
 * Three postures based on Reviewer state:
 *   approve_advisory — Reviewer approved; autonomy gate requires your
 *                      real-time confirmation. Action: "Confirm · Execute"
 *   defer            — Reviewer needs more evidence or deferred judgment.
 *                      Action: "Proceed anyway" (explicit override)
 *   no_reviewer      — No reviewable substrate; judgment seat inactive.
 *                      Action: "Approve" (plain, no Reviewer context)
 *   rejected         — Reviewer rejected. No approve affordance — user must
 *                      update mandate/risk and re-propose.
 */

import { useState, useMemo, useEffect } from 'react';
import { CheckCircle2, XCircle, Clock, ShieldAlert, Loader2, AlertCircle, ShieldCheck, ShieldX, ShieldQuestion } from 'lucide-react';
import api from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { useReviewerPersona } from '@/lib/reviewer-persona';

interface ProposalResult {
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
    reviewer_identity?: string;
    reviewer_reasoning?: string;
  };
  error?: string;
  message?: string;
}

interface ProposalCardProps {
  result: ProposalResult;
}

type LocalStatus = 'pending' | 'approving' | 'approved' | 'rejecting' | 'rejected' | 'error';

// Reviewer verdict posture derived from proposal state
type ReviewerPosture = 'approve_advisory' | 'defer' | 'rejected' | 'none';

function formatActionType(action: string): string {
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

function deriveReviewerPosture(
  reviewerIdentity?: string,
  reviewerReasoning?: string,
  proposalStatus?: string,
): ReviewerPosture {
  if (!reviewerIdentity || !reviewerReasoning) return 'none';
  // AI occupant already rejected at proposal level
  if (proposalStatus === 'rejected') return 'rejected';
  // Advisory approve: Reviewer approved but autonomy gate requires user confirmation
  if (reviewerIdentity.startsWith('ai:') && proposalStatus === 'pending') return 'approve_advisory';
  // Defer: Reviewer deferred, proposal still pending
  if (proposalStatus === 'pending') return 'defer';
  return 'none';
}

interface ReviewerBannerProps {
  posture: ReviewerPosture;
  reasoning: string;
  personaName: string | null;
}

function ReviewerBanner({ posture, reasoning, personaName }: ReviewerBannerProps) {
  const name = personaName ?? 'Reviewer';
  // Strip the trailing "Your confirmation required…" sentence for display
  // — that instruction lives in the action affordance label, not here.
  // Strip the trailing "Your confirmation required…" and "— decided by…" lines.
  // Use indexOf-based slice instead of /s flag (tsconfig target compat).
  const confirmIdx = reasoning.indexOf('\n\n**Your confirmation required**');
  const decidedIdx = reasoning.indexOf('\n\n— ');
  const cutAt = Math.min(
    confirmIdx >= 0 ? confirmIdx : reasoning.length,
    decidedIdx >= 0 ? decidedIdx : reasoning.length,
  );
  const displayReasoning = reasoning.slice(0, cutAt).trim();

  if (posture === 'approve_advisory') {
    return (
      <div className="flex items-start gap-2 rounded border border-emerald-500/30 bg-emerald-500/5 px-2.5 py-2">
        <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
        <div className="space-y-1 min-w-0">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-emerald-700 dark:text-emerald-400">
            {name} approved
          </div>
          <div className="text-xs text-muted-foreground leading-relaxed line-clamp-3">
            {displayReasoning}
          </div>
        </div>
      </div>
    );
  }

  if (posture === 'defer') {
    return (
      <div className="flex items-start gap-2 rounded border border-amber-500/30 bg-amber-500/5 px-2.5 py-2">
        <ShieldQuestion className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
        <div className="space-y-1 min-w-0">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-400">
            {name} deferred — your judgment needed
          </div>
          <div className="text-xs text-muted-foreground leading-relaxed line-clamp-3">
            {displayReasoning}
          </div>
        </div>
      </div>
    );
  }

  if (posture === 'rejected') {
    return (
      <div className="flex items-start gap-2 rounded border border-rose-500/30 bg-rose-500/5 px-2.5 py-2">
        <ShieldX className="w-3.5 h-3.5 text-rose-600 shrink-0 mt-0.5" />
        <div className="space-y-1 min-w-0">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-rose-700 dark:text-rose-400">
            {name} rejected
          </div>
          <div className="text-xs text-muted-foreground leading-relaxed line-clamp-3">
            {displayReasoning}
          </div>
        </div>
      </div>
    );
  }

  return null;
}

export function ProposalCard({ result }: ProposalCardProps) {
  const personaName = useReviewerPersona();

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
  const [status, setStatus] = useState<LocalStatus>(
    proposal.status === 'executed' ? 'approved' :
    proposal.status === 'rejected' ? 'rejected' :
    'pending'
  );
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  // Live proposal state — fetched on mount to pick up reviewer_reasoning
  // written after ProposeAction returned (Reviewer runs async).
  const [liveProposal, setLiveProposal] = useState(proposal);

  useEffect(() => {
    // Re-fetch the proposal to get reviewer_reasoning/reviewer_identity
    // which are written after the tool result was serialised.
    let cancelled = false;
    api.proposals.get(proposal.id).then((res) => {
      if (!cancelled && res?.proposal) {
        setLiveProposal((prev) => ({
          ...prev,
          reviewer_identity: res.proposal.reviewer_identity ?? undefined,
          reviewer_reasoning: res.proposal.reviewer_reasoning ?? undefined,
          status: res.proposal.status ?? prev.status,
        }));
      }
    }).catch(() => {/* non-fatal */});
    return () => { cancelled = true; };
  }, [proposal.id]);

  const revTone = useMemo(() => reversibilityTone(liveProposal.reversibility), [liveProposal.reversibility]);
  const expiresLabel = formatExpiresAt(liveProposal.expires_at);

  const reviewerPosture = deriveReviewerPosture(
    liveProposal.reviewer_identity,
    liveProposal.reviewer_reasoning,
    liveProposal.status,
  );

  const handleApprove = async () => {
    setStatus('approving');
    setErrorMsg(null);
    try {
      const res = await api.proposals.approve(liveProposal.id);
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
      const res = await api.proposals.reject(liveProposal.id);
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

  // Contextual approve label per ADR-249 D3 framing
  const approveLabel =
    reviewerPosture === 'approve_advisory' ? 'Confirm · Execute' :
    reviewerPosture === 'defer' ? 'Proceed anyway' :
    'Approve';

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
          {formatActionType(liveProposal.action_type)}
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
        {liveProposal.rationale && (
          <div className="text-sm">{liveProposal.rationale}</div>
        )}
        {liveProposal.expected_effect && (
          <div className="text-xs text-muted-foreground border-l-2 border-border pl-2">
            {liveProposal.expected_effect}
          </div>
        )}

        {/* Reviewer verdict banner — shown above risk warnings + actions */}
        {liveProposal.reviewer_reasoning && (
          <ReviewerBanner
            posture={reviewerPosture}
            reasoning={liveProposal.reviewer_reasoning}
            personaName={personaName}
          />
        )}

        {liveProposal.risk_warnings && liveProposal.risk_warnings.length > 0 && (
          <div className="flex items-start gap-1.5 rounded border border-amber-500/30 bg-amber-500/5 px-2 py-1.5">
            <ShieldAlert className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
            <div className="text-xs text-amber-900 dark:text-amber-100 space-y-0.5">
              {liveProposal.risk_warnings.map((w, i) => (
                <div key={i}>{w}</div>
              ))}
            </div>
          </div>
        )}

        {/* Action area */}
        {status === 'pending' && reviewerPosture !== 'rejected' && (
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
              {approveLabel}
            </button>
          </div>
        )}

        {/* Reviewer rejected — no approve affordance */}
        {status === 'pending' && reviewerPosture === 'rejected' && (
          <div className="flex items-center gap-2 pt-1 text-[11px] text-muted-foreground">
            <Clock className="w-3 h-3" />
            <span>expires {expiresLabel} · update risk rules and re-propose to proceed</span>
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
            <span>Executed</span>
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
    </div>
  );
}
