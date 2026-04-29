'use client';

/**
 * DecisionsStream — Stream archetype (ADR-198 §3) on /work.
 *
 * Per ADR-241 D3, the Decisions stream relocates from /agents to /work
 * because Decisions are the actionable consequence of the kernel's
 * judgment layer over operator-emitted action_proposals — the natural
 * home for "what the kernel decided about my proposals" is the page
 * where proposals live (TrackingFace already shows pending ones).
 *
 * Tail-parses /workspace/review/decisions.md for reviewer decision entries
 * and renders them newest-at-top with identity-tag and decision filters.
 *
 * Format expected (per ADR-194 v2 Phase 2a):
 *   --- decision ---
 *   timestamp: <iso>
 *   reviewer_identity: human:<uuid> | ai:reviewer-sonnet-v1 | impersonated:<admin>-as-<persona> | reviewer-layer:observed
 *   decision: approve | reject | defer
 *   action_type: <e.g., trading.submit_bracket_order>
 *   proposal_id: <uuid>
 *   reasoning: <multi-line text, may span multiple lines>
 *
 * Tolerant parser: missing fields render as "—"; malformed blocks skipped
 * silently. Never errors-out the surface. Uses the canonical parser at
 * @/lib/reviewer-decisions per ADR-239 D1.
 */

import { useEffect, useState, useMemo } from 'react';
import {
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  User,
  Bot,
  Shield,
  Eye,
  AlertCircle,
} from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import {
  parseDecisions,
  formatActionType,
  formatRelativeTimestamp as formatTimestamp,
  type ReviewerDecision as Decision,
} from '@/lib/reviewer-decisions';

type IdentityFilter = 'all' | 'human' | 'ai' | 'impersonated';
type DecisionFilter = 'all' | 'approve' | 'reject' | 'defer';

const PAGE_SIZE = 50;

export function DecisionsStream() {
  const [raw, setRaw] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [identityFilter, setIdentityFilter] = useState<IdentityFilter>('all');
  const [decisionFilter, setDecisionFilter] = useState<DecisionFilter>('all');
  const [showCount, setShowCount] = useState(PAGE_SIZE);

  useEffect(() => {
    void (async () => {
      try {
        const file = await api.workspace.getFile('/workspace/review/decisions.md');
        setRaw(file.content ?? '');
      } catch (err) {
        if (err instanceof APIError && err.status === 404) {
          setRaw(''); // File not yet created — empty state
        } else {
          setError(err instanceof Error ? err.message : 'Failed to load decisions log');
        }
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const allDecisions = useMemo(() => parseDecisions(raw ?? ''), [raw]);

  const filtered = useMemo(() => {
    return allDecisions.filter((d) => {
      if (identityFilter !== 'all' && d.identityKind !== identityFilter) return false;
      if (decisionFilter !== 'all' && d.decision !== decisionFilter) return false;
      return true;
    });
  }, [allDecisions, identityFilter, decisionFilter]);

  const visible = filtered.slice(0, showCount);

  if (loading) {
    return (
      <section className="rounded-md border border-border bg-card p-4">
        <header className="mb-3">
          <h2 className="text-sm font-semibold">Decisions</h2>
        </header>
        <div className="flex items-center justify-center py-6">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="rounded-md border border-border bg-card p-4">
        <header className="mb-3">
          <h2 className="text-sm font-semibold">Decisions</h2>
        </header>
        <div className="flex items-center gap-2 rounded-md bg-muted/30 px-3 py-2 text-sm text-muted-foreground">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-md border border-border bg-card p-4">
      <header className="mb-3 flex flex-wrap items-center gap-2">
        <h2 className="text-sm font-semibold">
          Decisions {allDecisions.length > 0 && `· ${filtered.length}`}
        </h2>
        <div className="ml-auto flex flex-wrap gap-1">
          <FilterGroup
            current={identityFilter}
            options={[
              { value: 'all', label: 'All' },
              { value: 'human', label: 'Human' },
              { value: 'ai', label: 'AI' },
              { value: 'impersonated', label: 'Impersonated' },
            ]}
            onChange={(v) => setIdentityFilter(v as IdentityFilter)}
          />
          <FilterGroup
            current={decisionFilter}
            options={[
              { value: 'all', label: 'All' },
              { value: 'approve', label: 'Approved' },
              { value: 'reject', label: 'Rejected' },
              { value: 'defer', label: 'Deferred' },
            ]}
            onChange={(v) => setDecisionFilter(v as DecisionFilter)}
          />
        </div>
      </header>

      {allDecisions.length === 0 ? (
        <p className="rounded-md border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
          No reviewer decisions recorded yet. Decisions appear here when you
          approve or reject proposals.
        </p>
      ) : filtered.length === 0 ? (
        <p className="rounded-md border border-dashed border-border px-4 py-6 text-center text-sm text-muted-foreground">
          No decisions match the current filter.
        </p>
      ) : (
        <>
          <ul className="flex flex-col gap-2">
            {visible.map((d, idx) => (
              <DecisionRow key={idx} decision={d} />
            ))}
          </ul>
          {filtered.length > showCount && (
            <div className="mt-3 text-center">
              <button
                onClick={() => setShowCount((c) => c + PAGE_SIZE)}
                className="rounded-md border border-border px-3 py-1 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                Load older ({filtered.length - showCount} more)
              </button>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function FilterGroup({
  current,
  options,
  onChange,
}: {
  current: string;
  options: Array<{ value: string; label: string }>;
  onChange: (value: string) => void;
}) {
  return (
    <div className="flex items-center gap-0.5 rounded-full bg-muted/60 p-0.5">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={cn(
            'rounded-full px-2 py-0.5 text-[11px] font-medium transition-colors',
            current === opt.value
              ? 'bg-foreground text-background'
              : 'text-muted-foreground hover:text-foreground',
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

function DecisionRow({ decision }: { decision: Decision }) {
  const Icon =
    decision.decision === 'approve'
      ? CheckCircle2
      : decision.decision === 'reject'
        ? XCircle
        : Clock;
  const iconColor =
    decision.decision === 'approve'
      ? 'text-emerald-600 dark:text-emerald-400'
      : decision.decision === 'reject'
        ? 'text-destructive'
        : 'text-muted-foreground';

  return (
    <li
      className={cn(
        'rounded-md border border-border px-3 py-2.5 text-sm',
        decision.identityKind === 'impersonated' && 'border-amber-500/40 bg-amber-500/5',
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        <Icon className={cn('h-4 w-4 shrink-0', iconColor)} />
        <span className="font-medium capitalize">{decision.decision ?? '—'}</span>
        {decision.actionType && (
          <span className="text-muted-foreground">· {formatActionType(decision.actionType)}</span>
        )}
        <IdentityBadge kind={decision.identityKind} raw={decision.identity} />
        {decision.timestamp && (
          <span className="ml-auto text-[11px] text-muted-foreground">
            {formatTimestamp(decision.timestamp)}
          </span>
        )}
      </div>
      {decision.reasoning && (
        <p className="mt-1.5 line-clamp-3 text-[13px] text-muted-foreground">
          {decision.reasoning}
        </p>
      )}
    </li>
  );
}

function IdentityBadge({
  kind,
  raw,
}: {
  kind: Decision['identityKind'];
  raw: string | null;
}) {
  if (kind === 'unknown') return null;
  const config = {
    human: { Icon: User, label: 'Human', cls: 'bg-muted text-foreground' },
    ai: { Icon: Bot, label: 'AI', cls: 'bg-blue-500/10 text-blue-700 dark:text-blue-400' },
    impersonated: {
      Icon: Shield,
      label: 'Impersonated',
      cls: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
    },
    observed: {
      Icon: Eye,
      label: 'Observed',
      cls: 'bg-muted text-muted-foreground',
    },
  }[kind];
  const { Icon, label, cls } = config;
  return (
    <span
      title={raw ?? label}
      className={cn(
        'inline-flex items-center gap-1 rounded-sm px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide',
        cls,
      )}
    >
      <Icon className="h-2.5 w-2.5" />
      {label}
    </span>
  );
}

// Parser + formatters moved to `web/lib/reviewer-decisions.ts` (singular
// implementation — shared with the Snapshot overlay's Recent tab).
