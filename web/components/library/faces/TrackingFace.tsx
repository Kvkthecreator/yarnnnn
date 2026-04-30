'use client';

/**
 * TrackingFace — face #4 of the four-face cockpit (ADR-228).
 *
 * Renders what is in motion right now. Three regions inside one face:
 *   1. Pending decisions — proposal queue with inline approve/reject
 *      (absorbs KernelNeedsMePane / TradingProposalQueue)
 *   2. Operational state — bundle-shaped table (positions for trader,
 *      active campaigns for commerce). Phase 1 (this commit) shows a
 *      link-out; Commit 4 wires the bundle-declared component.
 *   3. Recent activity — outcome events only (fills, closes, decisions,
 *      approvals/rejections). Task-run delivery events excluded entirely
 *      per ADR-228 D5 — they belong on /work list, not the cockpit.
 *
 * The three regions are not three sub-panes; they are three sections of
 * one face. Each is bundle-fed via the SURFACES.yaml `cockpit.tracking`
 * block. Bundles cannot reorder the regions or omit them — the structural
 * shape is universal.
 *
 * Phase 1 (this commit) renders Pending Decisions and Recent Activity
 * with kernel-default outcome filters. Operational state renders as a
 * link-out placeholder until bundle wiring lands in Commit 4.
 */

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { Loader2, AlertCircle, Clock, ShieldAlert, Sparkles } from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import type { NarrativeMaterialEntry } from '@/types';

type Proposal = Awaited<ReturnType<typeof api.proposals.list>>['proposals'][number];

interface MaterialEntry extends NarrativeMaterialEntry {
  task_slug: string;
}

const PROPOSAL_INLINE_LIMIT = 3;
const ACTIVITY_LIMIT = 5;

// Outcome event types kept on the cockpit. Task-run delivery events
// (e.g., "pre-market-brief delivered") are NOT cockpit signal — they live
// on /work list rows and the agent timeline.
//
// The narrative API doesn't yet emit a typed `event_kind` we can filter on.
// As an interim until the narrative substrate gains a typed event field,
// we filter by summary heuristic: outcomes contain action verbs (filled,
// closed, approved, rejected, triggered) where deliveries contain
// "delivered" / "completed" boilerplate. When the narrative gains a typed
// field, this heuristic deletes in favor of a server-side filter.
const DELIVERY_NOISE = /\b(delivered|completed|finished|generated)\b/i;
const OUTCOME_HINT = /\b(filled|closed|approved|rejected|triggered|stopped|breached|escalated|opened)\b/i;

function isOutcomeEvent(entry: NarrativeMaterialEntry): boolean {
  if (DELIVERY_NOISE.test(entry.summary) && !OUTCOME_HINT.test(entry.summary)) {
    return false;
  }
  // Default-include: if it doesn't look like delivery noise, surface it.
  // Better to over-show outcomes than to silently drop them.
  return true;
}

export function TrackingFace() {
  const [proposals, setProposals] = useState<Proposal[] | null>(null);
  const [proposalError, setProposalError] = useState<string | null>(null);
  const [activity, setActivity] = useState<MaterialEntry[] | null>(null);

  const loadProposals = useCallback(async () => {
    setProposalError(null);
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
      setProposalError(msg);
      setProposals([]);
    }
  }, []);

  useEffect(() => {
    void loadProposals();
  }, [loadProposals]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const resp = await api.narrative.byTask(24);
        const flat: MaterialEntry[] = [];
        for (const slice of resp.tasks) {
          if (slice.last_material && isOutcomeEvent(slice.last_material)) {
            flat.push({ ...slice.last_material, task_slug: slice.task_slug });
          }
        }
        flat.sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
        );
        if (!cancelled) setActivity(flat);
      } catch {
        if (!cancelled) setActivity([]);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const proposalsLoading = proposals === null;
  const activityLoading = activity === null;

  if (proposalsLoading && activityLoading) return null;

  return (
    <section
      aria-label="Tracking"
      className="rounded-lg border border-border bg-card p-5"
    >
      <div className="mb-4 flex items-center justify-between text-xs">
        <span className="font-medium uppercase tracking-wide text-muted-foreground/70">
          Tracking
        </span>
        <span className="text-muted-foreground/40">in motion now</span>
      </div>

      {/* Region 1: Pending decisions */}
      <PendingDecisions
        proposals={proposals ?? []}
        loading={proposalsLoading}
        error={proposalError}
        onReload={loadProposals}
      />

      {/* Region 2: Operational state — bundle-fed, kernel placeholder */}
      <OperationalState />

      {/* Region 3: Recent activity (outcomes only) */}
      <RecentActivity activity={activity ?? []} loading={activityLoading} />
    </section>
  );
}

// ─── Region 1 ────────────────────────────────────────────────────────────────

function PendingDecisions({
  proposals,
  loading,
  error,
  onReload,
}: {
  proposals: Proposal[];
  loading: boolean;
  error: string | null;
  onReload: () => Promise<void>;
}) {
  return (
    <div className="mb-5">
      <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        Pending decisions {proposals.length > 0 && `· ${proposals.length}`}
      </h3>
      {loading ? (
        <div className="flex items-center justify-center py-4">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      ) : error ? (
        <div className="flex items-center gap-2 rounded-md border border-border bg-muted/30 px-3 py-2 text-sm text-muted-foreground">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span className="flex-1">{error}</span>
          <button
            onClick={() => void onReload()}
            className="rounded px-2 py-0.5 text-xs font-medium hover:bg-muted hover:text-foreground"
          >
            Retry
          </button>
        </div>
      ) : proposals.length === 0 ? (
        <p className="rounded-md border border-dashed border-border px-3 py-3 text-center text-sm text-muted-foreground">
          Nothing needs you right now.
        </p>
      ) : (
        <div className="flex flex-col gap-2">
          {proposals.slice(0, PROPOSAL_INLINE_LIMIT).map((p) => (
            <ProposalRow key={p.id} proposal={p} onReload={onReload} />
          ))}
          {proposals.length > PROPOSAL_INLINE_LIMIT && (
            <Link
              href="/agents?agent=reviewer"
              className="text-center text-xs font-medium text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
            >
              See {proposals.length - PROPOSAL_INLINE_LIMIT} more
            </Link>
          )}
        </div>
      )}
    </div>
  );
}

function ProposalRow({
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
    <div className="rounded-md border border-border bg-background px-3 py-2">
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
      {error && <p className="mt-1 text-[11px] text-destructive">{error}</p>}
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

// ─── Region 2 ────────────────────────────────────────────────────────────────

import { dispatchComponent } from '../registry';
import { useComposition as useCompositionForOpState } from '@/lib/compositor';

function OperationalState() {
  // ADR-242 D4 Phase 2: when the bundle declares
  // `cockpit.tracking.operational_state` with a `kind`, dispatch the
  // bundle component. Else fall through to the kernel placeholder.
  // Singular Implementation: one render path per workspace state.
  const { data: composition } = useCompositionForOpState();
  const opState = (composition.composition.tabs?.work?.list as {
    cockpit?: { tracking?: { operational_state?: { kind: string; source?: string } } }
  } | undefined)?.cockpit?.tracking?.operational_state;

  if (opState?.kind && opState.source) {
    return (
      <div className="mb-5">
        {dispatchComponent(
          { kind: opState.kind, source: '__opstate__' },
          { __opstate__: { type: 'file', path: opState.source } },
        )}
      </div>
    );
  }

  // Kernel placeholder fallthrough — for workspaces without a bundle
  // declaring operational_state.
  return (
    <div className="mb-5">
      <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        Operational state
      </h3>
      <Link
        href="/context?path=%2Fworkspace%2Fcontext%2Fportfolio%2F"
        className="block rounded-md border border-dashed border-border bg-muted/20 px-3 py-3 text-sm text-muted-foreground hover:bg-muted/30"
      >
        Activate a program with operational substrate (e.g., alpha-trader)
        to render positions / active campaigns / watchlist here.
      </Link>
    </div>
  );
}

// ─── Region 3 ────────────────────────────────────────────────────────────────

function RecentActivity({
  activity,
  loading,
}: {
  activity: MaterialEntry[];
  loading: boolean;
}) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Recent activity · 24h
        </h3>
        <Link
          href="/chat?weight=material"
          className="text-[11px] text-muted-foreground/60 underline-offset-4 hover:text-foreground hover:underline"
        >
          Full narrative →
        </Link>
      </div>
      {loading ? (
        <div className="flex items-center justify-center py-3">
          <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
        </div>
      ) : activity.length === 0 ? (
        <p className="rounded-md border border-dashed border-border px-3 py-3 text-center text-sm text-muted-foreground">
          Quiet — no outcomes since last look.
        </p>
      ) : (
        <ul className="space-y-1.5">
          {activity.slice(0, ACTIVITY_LIMIT).map((entry, idx) => (
            <li key={`${entry.task_slug}-${idx}`} className="flex items-start gap-2 text-sm">
              <Sparkles className="mt-0.5 h-3 w-3 shrink-0 text-muted-foreground/40" />
              <div className="flex-1 min-w-0">
                <Link
                  href={`/work?task=${encodeURIComponent(entry.task_slug)}`}
                  className="text-foreground hover:underline"
                >
                  <span className="line-clamp-1">{entry.summary}</span>
                </Link>
                <span className="text-[11px] text-muted-foreground/60">
                  {entry.task_slug} · {formatRelative(entry.created_at)}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

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

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
