'use client';

/**
 * ProposalCard — stream entry chip + modal detail for action proposals.
 *
 * ADR-258: interactive items in the stream use one pattern:
 *   1. ProposalChip  — compact stream entry, triggers modal on click
 *   2. ProposalDetail — full detail rendered inside InteractiveModal
 *   3. ProposalCard   — wires chip + modal together (the export ToolResultCard uses)
 *
 * ADR-249 D3 framing: the Reviewer IS the operator's judgment function.
 * The modal shows what the Reviewer decided, then asks the operator to
 * ratify or override — not to independently approve a system action.
 */

import { useState, useEffect } from 'react';
import {
  CheckCircle2, XCircle, Clock, ShieldAlert, Loader2,
  AlertCircle, ShieldCheck, ShieldX, ShieldQuestion, Hexagon,
} from 'lucide-react';
import api from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { useReviewerPersona } from '@/lib/reviewer-persona';
import { InteractiveModal } from './InteractiveModal';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ProposalData {
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
}

interface ProposalResult {
  success: boolean;
  proposal_id?: string;
  proposal?: ProposalData;
  error?: string;
  message?: string;
}

interface ProposalCardProps {
  result: ProposalResult;
}

type LocalStatus = 'pending' | 'approving' | 'approved' | 'rejecting' | 'rejected' | 'error';
type ReviewerPosture = 'approve_advisory' | 'defer' | 'rejected' | 'none';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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

function reversibilityLabel(r: string): string {
  if (r === 'reversible') return 'Reversible';
  if (r === 'soft-reversible') return 'Soft-reversible';
  if (r === 'irreversible') return 'Irreversible';
  return r;
}

function deriveReviewerPosture(
  reviewerIdentity?: string,
  reviewerReasoning?: string,
  proposalStatus?: string,
): ReviewerPosture {
  if (!reviewerIdentity || !reviewerReasoning) return 'none';
  if (proposalStatus === 'rejected') return 'rejected';
  if (reviewerIdentity.startsWith('ai:') && proposalStatus === 'pending') return 'approve_advisory';
  if (proposalStatus === 'pending') return 'defer';
  return 'none';
}

// Strip trailing boilerplate from Reviewer reasoning for display
function cleanReasoning(reasoning: string): string {
  const confirmIdx = reasoning.indexOf('\n\n**Your confirmation required**');
  const decidedIdx = reasoning.indexOf('\n\n— ');
  const cutAt = Math.min(
    confirmIdx >= 0 ? confirmIdx : reasoning.length,
    decidedIdx >= 0 ? decidedIdx : reasoning.length,
  );
  return reasoning.slice(0, cutAt).trim();
}

// ---------------------------------------------------------------------------
// ProposalChip — compact stream entry
// ---------------------------------------------------------------------------

interface ProposalChipProps {
  proposal: ProposalData;
  reviewerPosture: ReviewerPosture;
  personaName: string | null;
  terminalStatus: LocalStatus | null;
  onClick: () => void;
}

function ProposalChip({ proposal, reviewerPosture, personaName, terminalStatus, onClick }: ProposalChipProps) {
  const name = personaName ?? 'Reviewer';

  const reviewerLine =
    reviewerPosture === 'approve_advisory' ? `${name} approved` :
    reviewerPosture === 'defer' ? `${name} deferred` :
    reviewerPosture === 'rejected' ? `${name} rejected` :
    null;

  const isTerminal = terminalStatus === 'approved' || terminalStatus === 'rejected';
  const terminalLine =
    terminalStatus === 'approved' ? 'Executed' :
    terminalStatus === 'rejected' ? 'Rejected' :
    null;

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={isTerminal}
      className={cn(
        'w-full text-left rounded-lg border px-3 py-2.5 transition-colors',
        isTerminal
          ? 'border-border/40 bg-muted/20 cursor-default opacity-60'
          : 'border-border bg-muted/10 hover:bg-muted/30 cursor-pointer',
      )}
    >
      <div className="flex items-center gap-2">
        <Hexagon className="w-3.5 h-3.5 shrink-0 text-muted-foreground/50" />
        <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
          Proposal
        </span>
        <span className="text-xs text-muted-foreground/70 truncate flex-1">
          {formatActionType(proposal.action_type)}
        </span>
        <span className="text-[10px] text-muted-foreground/40 shrink-0">
          {reversibilityLabel(proposal.reversibility)}
        </span>
      </div>
      {(reviewerLine || terminalLine) && (
        <div className="mt-1 pl-5 text-[11px] text-muted-foreground/60">
          {terminalLine ?? reviewerLine}
          {!isTerminal && (
            <span className="ml-1 text-muted-foreground/40">· tap to review</span>
          )}
        </div>
      )}
    </button>
  );
}

// ---------------------------------------------------------------------------
// ProposalDetail — modal body
// ---------------------------------------------------------------------------

interface ProposalDetailProps {
  proposal: ProposalData;
  onClose: () => void;
}

function ProposalDetail({ proposal, onClose }: ProposalDetailProps) {
  const personaName = useReviewerPersona();
  const [status, setStatus] = useState<LocalStatus>(
    proposal.status === 'executed' ? 'approved' :
    proposal.status === 'rejected' ? 'rejected' :
    'pending',
  );
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [liveProposal, setLiveProposal] = useState(proposal);

  useEffect(() => {
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
      if (res.success) { setStatus('approved'); onClose(); }
      else { setStatus('error'); setErrorMsg(res.error || 'Execution failed'); }
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
      if (res.success) { setStatus('rejected'); onClose(); }
      else { setStatus('error'); setErrorMsg('Rejection failed'); }
    } catch (err) {
      setStatus('error');
      setErrorMsg(err instanceof Error ? err.message : 'Network error');
    }
  };

  const isTerminal = status === 'approved' || status === 'rejected';
  const isLoading = status === 'approving' || status === 'rejecting';
  const approveLabel =
    reviewerPosture === 'approve_advisory' ? 'Confirm · Execute' :
    reviewerPosture === 'defer' ? 'Proceed anyway' :
    'Approve';

  return (
    <div className="space-y-3">
      {/* Rationale */}
      {liveProposal.rationale && (
        <p className="text-sm">{liveProposal.rationale}</p>
      )}
      {liveProposal.expected_effect && (
        <p className="text-xs text-muted-foreground border-l-2 border-border pl-2">
          {liveProposal.expected_effect}
        </p>
      )}

      {/* Reviewer verdict */}
      {liveProposal.reviewer_reasoning && (
        <div className="space-y-1 pt-1">
          {reviewerPosture === 'approve_advisory' && (
            <div className="flex items-center gap-1.5 text-[11px] text-emerald-700 dark:text-emerald-400">
              <ShieldCheck className="w-3 h-3 shrink-0" />
              <span className="font-medium">{personaName ?? 'Reviewer'} approved</span>
            </div>
          )}
          {reviewerPosture === 'defer' && (
            <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
              <ShieldQuestion className="w-3 h-3 shrink-0" />
              <span className="font-medium">{personaName ?? 'Reviewer'} deferred — your judgment needed</span>
            </div>
          )}
          {reviewerPosture === 'rejected' && (
            <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
              <ShieldX className="w-3 h-3 shrink-0" />
              <span className="font-medium">{personaName ?? 'Reviewer'} rejected</span>
            </div>
          )}
          <p className="text-xs text-muted-foreground leading-relaxed pl-4">
            {cleanReasoning(liveProposal.reviewer_reasoning)}
          </p>
        </div>
      )}

      {/* Risk warnings */}
      {liveProposal.risk_warnings && liveProposal.risk_warnings.length > 0 && (
        <div className="flex items-start gap-1.5 rounded border border-border/60 bg-muted/30 px-2.5 py-2">
          <ShieldAlert className="w-3.5 h-3.5 text-muted-foreground shrink-0 mt-0.5" />
          <div className="text-xs text-muted-foreground space-y-0.5">
            {liveProposal.risk_warnings.map((w, i) => <div key={i}>{w}</div>)}
          </div>
        </div>
      )}

      {/* Action area */}
      {!isTerminal && reviewerPosture !== 'rejected' && (
        <div className="flex items-center gap-2 pt-1 border-t border-border/40">
          <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
            <Clock className="w-3 h-3" />
            <span>expires {formatExpiresAt(liveProposal.expires_at)}</span>
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
            {isLoading && <Loader2 className="w-3 h-3 animate-spin" />}
            {approveLabel}
          </button>
        </div>
      )}

      {reviewerPosture === 'rejected' && !isTerminal && (
        <div className="flex items-center gap-1.5 pt-1 border-t border-border/40 text-[11px] text-muted-foreground">
          <Clock className="w-3 h-3" />
          <span>expires {formatExpiresAt(liveProposal.expires_at)} · update risk rules and re-propose to proceed</span>
        </div>
      )}

      {status === 'error' && errorMsg && (
        <div className="flex items-start gap-2 text-xs text-destructive pt-1">
          <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <span>{errorMsg}</span>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ProposalCard — chip + modal wired together (the exported interface)
// ---------------------------------------------------------------------------

export function ProposalCard({ result }: ProposalCardProps) {
  const [open, setOpen] = useState(false);
  const personaName = useReviewerPersona();

  if (!result.success || !result.proposal) {
    return (
      <div className="rounded-lg border border-border/60 bg-muted/10 px-3 py-2 text-sm">
        <div className="flex items-center gap-2 text-muted-foreground">
          <AlertCircle className="w-4 h-4" />
          <span>Proposal couldn&apos;t be created</span>
        </div>
        {result.message && <div className="mt-1 text-xs text-muted-foreground/70">{result.message}</div>}
      </div>
    );
  }

  const proposal = result.proposal;

  // Derive posture from initial result for chip display (modal re-fetches live state)
  const initialPosture = deriveReviewerPosture(
    proposal.reviewer_identity,
    proposal.reviewer_reasoning,
    proposal.status,
  );

  const terminalStatus: LocalStatus | null =
    proposal.status === 'executed' ? 'approved' :
    proposal.status === 'rejected' ? 'rejected' :
    null;

  return (
    <>
      <ProposalChip
        proposal={proposal}
        reviewerPosture={initialPosture}
        personaName={personaName}
        terminalStatus={terminalStatus}
        onClick={() => setOpen(true)}
      />
      <InteractiveModal
        isOpen={open}
        onClose={() => setOpen(false)}
        title="Proposal"
        subtitle={formatActionType(proposal.action_type)}
      >
        <ProposalDetail proposal={proposal} onClose={() => setOpen(false)} />
      </InteractiveModal>
    </>
  );
}
