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

import React, { useState, useEffect } from 'react';
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

export interface ProposalData {
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
  /** Audit-pass-2 DD-6: structured action inputs (ticker/qty/limit-price
   * for trading.submit_order; product/discount params for commerce.*;
   * page_id/properties for notion.write_page). Shape varies by
   * action_type. Rendered by `ProposalInputs` component below. */
  inputs?: Record<string, unknown>;
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

// ---------------------------------------------------------------------------
// ProposalInputs — type-keyed renderer for proposal.inputs (Audit-pass-2 DD-6)
// ---------------------------------------------------------------------------
//
// Pre-2026-05-11 the modal showed rationale + expected_effect (operator-
// facing prose) but never displayed the structured `inputs` dict. Operator
// approving a trading.submit_order saw "Long NVDA breakout signal" but
// not the actual ticker/qty/limit_price they were binding to execution.
// This renderer surfaces the structured payload at the moment of decision.
//
// Shape: action_type-keyed switch with a generic key/value fallback for
// unknown types. The known cases prioritize the operator-facing fields
// (ticker/qty/price for trading; product/discount params for commerce);
// the fallback shows all keys formatted so unknown types are never silent.

function ProposalInputs({ actionType, inputs }: { actionType: string; inputs?: Record<string, unknown> }) {
  if (!inputs || Object.keys(inputs).length === 0) return null;

  // Trading actions: surface the order ticket fields prominently
  if (actionType.startsWith('trading.')) {
    const symbol = inputs.symbol ?? inputs.ticker;
    const qty = inputs.qty ?? inputs.quantity;
    const side = inputs.side;
    const orderType = inputs.type ?? inputs.order_type;
    const limit = inputs.limit_price;
    const stop = inputs.stop_price;
    const tif = inputs.time_in_force ?? inputs.tif;
    const fields: Array<[string, unknown]> = [];
    if (symbol) fields.push(['Symbol', symbol]);
    if (side) fields.push(['Side', side]);
    if (qty !== undefined) fields.push(['Quantity', qty]);
    if (orderType) fields.push(['Type', orderType]);
    if (limit !== undefined) fields.push(['Limit', limit]);
    if (stop !== undefined) fields.push(['Stop', stop]);
    if (tif) fields.push(['TIF', tif]);
    if (fields.length === 0) return <GenericInputsTable inputs={inputs} />;
    return (
      <div className="rounded-md border border-border/60 bg-muted/20 px-3 py-2">
        <div className="text-[10px] uppercase tracking-wide text-muted-foreground/70 mb-1">
          Order ticket
        </div>
        <dl className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-xs">
          {fields.map(([label, value]) => (
            <div key={label} className="contents">
              <dt className="text-muted-foreground">{label}</dt>
              <dd className="font-mono text-foreground">{String(value)}</dd>
            </div>
          ))}
        </dl>
      </div>
    );
  }

  // All other action types — generic key/value display so the operator
  // always sees the structured payload they're approving.
  return <GenericInputsTable inputs={inputs} />;
}

function GenericInputsTable({ inputs }: { inputs: Record<string, unknown> }) {
  return (
    <div className="rounded-md border border-border/60 bg-muted/20 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wide text-muted-foreground/70 mb-1">
        Inputs
      </div>
      <dl className="grid grid-cols-[max-content,1fr] gap-x-3 gap-y-0.5 text-xs">
        {Object.entries(inputs).map(([key, value]) => (
          <div key={key} className="contents">
            <dt className="text-muted-foreground">{key}</dt>
            <dd className="font-mono text-foreground break-all">
              {typeof value === 'object' ? JSON.stringify(value) : String(value)}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

// Strip trailing boilerplate from Reviewer reasoning for display.
// The boilerplate strings are written by review_proposal_dispatch.py
// (advisory-approve path) and must stay in lockstep — when the backend
// wording changes, this function MUST be updated in the same commit.
// 2026-05-11 hardening pass: "**Your confirmation required**" → "**Operator-
// in-real-time confirmation required**" per Axiom 2 two-embodiments
// framing (Commit B DD-2). Both wordings checked here for backward-
// compat with old persisted advisory entries written before the rename.
function cleanReasoning(reasoning: string): string {
  const confirmIdxNew = reasoning.indexOf('\n\n**Operator-in-real-time confirmation required**');
  const confirmIdxOld = reasoning.indexOf('\n\n**Your confirmation required**');
  const decidedIdx = reasoning.indexOf('\n\n— ');
  const candidates = [confirmIdxNew, confirmIdxOld, decidedIdx]
    .filter((i) => i >= 0);
  const cutAt = candidates.length > 0 ? Math.min(...candidates) : reasoning.length;
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

      {/* Audit-pass-2 DD-6: structured inputs (the actual payload being
          approved — ticker/qty/limit-price for trading; product params
          for commerce; etc). Operator sees what they're binding before
          confirming, not just the prose summary. */}
      <ProposalInputs actionType={liveProposal.action_type} inputs={liveProposal.inputs} />

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

// ---------------------------------------------------------------------------
// useProposalModal — shared modal launcher for any surface that needs
// click-to-inspect-and-act on a proposal (FOUNDATIONS v8.4 + Audit C LB-2).
// ---------------------------------------------------------------------------
//
// Singular Implementation: ONE modal path (InteractiveModal +
// ProposalDetail), N entry points. Currently used by:
//   - ProposalCard (chat-stream chip-click)
//   - TrackingFace ProposalRow (cockpit Queue row-click — added 2026-05-11)
//   - NeedsMePane ProposalRow (briefing Queue row-click — added 2026-05-11)
//
// Pre-2026-05-11 the cockpit + briefing rows had INLINE Approve/Reject
// buttons that bypassed the modal entirely — operators approved trades
// from cockpit without seeing reviewer reasoning, expected_effect, or
// risk_warnings (Channel-legibility violation per Derived Principle 12).
// This hook is the unification.
//
// Usage:
//   const { openProposal, modalElement } = useProposalModal({ onResolved });
//   return (<>
//     {proposals.map(p => <Row onClick={() => openProposal(p)} ... />)}
//     {modalElement}
//   </>);
//
// `onResolved` fires when the operator approves/rejects (the modal
// auto-closes; caller typically refreshes the list to remove the row).

export interface UseProposalModalOpts {
  /** Called after the operator approves or rejects the proposal. The
   *  caller typically refreshes their proposal list here. */
  onResolved?: (proposalId: string) => void;
}

export interface UseProposalModalReturn {
  /** Open the modal for a specific proposal. */
  openProposal: (proposal: ProposalData) => void;
  /** Render this once at the bottom of your tree — the modal portals out. */
  modalElement: React.ReactElement | null;
  /** True while the modal is open. Useful for caller UX (e.g., dim row). */
  isOpen: boolean;
}

/**
 * InlineProposalChipById — fetch-by-id wrapper around ProposalCard for
 * surfaces that only have a proposal_id (e.g., system_agent narration
 * entries on the feed where metadata.proposal_id is the only handle).
 *
 * Audit-pass-2 DD-4: heartbeat / reflection / cron-fired ProposeAction
 * narrations land as plain-text System Agent bubbles; embedding this
 * chip inline restores the click-to-modal affordance the addressed-
 * trigger path already has via ToolResultCard.
 *
 * Renders nothing while fetching; on fetch failure renders an inert
 * "proposal unavailable" chip so the operator sees that the proposal
 * existed but couldn't be loaded (e.g., expired + cleaned up).
 */
export function InlineProposalChipById({ proposalId }: { proposalId: string }) {
  const [proposal, setProposal] = useState<ProposalData | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.proposals.get(proposalId).then((res) => {
      if (cancelled) return;
      if (res?.proposal) {
        setProposal({
          id: res.proposal.id,
          action_type: res.proposal.action_type,
          rationale: res.proposal.rationale ?? '',
          expected_effect: res.proposal.expected_effect ?? '',
          reversibility: res.proposal.reversibility,
          risk_warnings: res.proposal.risk_warnings ?? [],
          expires_at: res.proposal.expires_at,
          status: res.proposal.status,
          reviewer_identity: res.proposal.reviewer_identity ?? undefined,
          reviewer_reasoning: res.proposal.reviewer_reasoning ?? undefined,
          inputs: res.proposal.inputs,  // DD-6: pass through structured payload
        });
      } else {
        setFailed(true);
      }
    }).catch(() => {
      if (!cancelled) setFailed(true);
    });
    return () => { cancelled = true; };
  }, [proposalId]);

  if (failed) {
    return (
      <div className="mt-2 rounded-lg border border-border/40 bg-muted/20 px-3 py-2 text-xs text-muted-foreground">
        Proposal {proposalId.slice(0, 8)} unavailable (expired or removed)
      </div>
    );
  }

  if (!proposal) return null;

  return (
    <div className="mt-2">
      <ProposalCard result={{ success: true, proposal_id: proposalId, proposal }} />
    </div>
  );
}

export function useProposalModal(opts: UseProposalModalOpts = {}): UseProposalModalReturn {
  const [active, setActive] = useState<ProposalData | null>(null);
  const { onResolved } = opts;

  const openProposal = (proposal: ProposalData) => {
    setActive(proposal);
  };

  const handleClose = () => {
    const closingId = active?.id;
    setActive(null);
    if (closingId && onResolved) {
      onResolved(closingId);
    }
  };

  const modalElement = active ? (
    <InteractiveModal
      isOpen={true}
      onClose={handleClose}
      title="Proposal"
      subtitle={formatActionType(active.action_type)}
    >
      <ProposalDetail proposal={active} onClose={handleClose} />
    </InteractiveModal>
  ) : null;

  return { openProposal, modalElement, isOpen: active !== null };
}
