'use client';

/**
 * DecisionsStreamPane — Stream archetype (ADR-198 §3).
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
 * silently. Never errors-out the surface.
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

interface Decision {
  raw: string;
  timestamp: string | null;
  identity: string | null;
  identityKind: 'human' | 'ai' | 'impersonated' | 'observed' | 'unknown';
  decision: 'approve' | 'reject' | 'defer' | null;
  actionType: string | null;
  proposalId: string | null;
  reasoning: string | null;
}

type IdentityFilter = 'all' | 'human' | 'ai' | 'impersonated';
type DecisionFilter = 'all' | 'approve' | 'reject' | 'defer';

const PAGE_SIZE = 50;

export function DecisionsStreamPane() {
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

function parseDecisions(content: string): Decision[] {
  if (!content) return [];
  const blocks = content.split(/\n?---\s*decision\s*---\n/i).filter(Boolean);
  const decisions: Decision[] = [];
  for (const block of blocks) {
    const trimmed = block.trim();
    if (!trimmed) continue;
    const timestamp = extractField(trimmed, 'timestamp');
    const identity = extractField(trimmed, 'reviewer_identity');
    const decision = (extractField(trimmed, 'decision') ?? '').toLowerCase();
    const actionType = extractField(trimmed, 'action_type');
    const proposalId = extractField(trimmed, 'proposal_id');
    const reasoning = extractReasoning(trimmed);
    decisions.push({
      raw: trimmed,
      timestamp,
      identity,
      identityKind: classifyIdentity(identity),
      decision:
        decision === 'approve' || decision === 'reject' || decision === 'defer'
          ? decision
          : null,
      actionType,
      proposalId,
      reasoning,
    });
  }
  // Newest-at-top: append-only log means later in file = newer.
  return decisions.reverse();
}

function extractField(block: string, key: string): string | null {
  const re = new RegExp(`^\\s*${key}:\\s*(.+?)\\s*$`, 'm');
  const m = block.match(re);
  return m ? m[1].trim() : null;
}

/**
 * Reasoning can be multi-line and may be the last field in the block.
 * Capture everything after "reasoning:" until end of block.
 */
function extractReasoning(block: string): string | null {
  const m = block.match(/reasoning:\s*([\s\S]+)$/i);
  if (!m) return null;
  return m[1].trim();
}

function classifyIdentity(identity: string | null): Decision['identityKind'] {
  if (!identity) return 'unknown';
  if (identity.startsWith('human:')) return 'human';
  if (identity.startsWith('ai:')) return 'ai';
  if (identity.startsWith('impersonated:')) return 'impersonated';
  if (identity.startsWith('reviewer-layer:')) return 'observed';
  return 'unknown';
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

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  if (diffDay < 7) return `${diffDay}d ago`;
  return d.toLocaleDateString();
}
