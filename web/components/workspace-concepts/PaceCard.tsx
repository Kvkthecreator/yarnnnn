'use client';

/**
 * PaceCard — L3 component for /workspace/governance/_pace.yaml.
 *
 * ADR-300 (2026-05-22): pace promoted to atomic kernel surface. PaceCard
 * mirrors AutonomyCard's shape — Direct mutation (setKind() writes the
 * file without going through chat, same as AutonomyCard.setLevel()). Per
 * the 2026-05-24 design polish (see docs/design/WORKSPACE-COMPONENTS.md
 * §6), the full variant gates every mutation behind a confirm modal —
 * pace changes have cost impact (switching to Continuous removes the
 * drain cap) and one-click commits were too easy to trigger accidentally.
 *
 * V1 edit scope is kind-only per ADR-300 D2. Secondary fields (`pace.every`,
 * `monthly_budget_usd`) display when present but route through chat for
 * edits (the escape hatch documented in ADR-300 D2).
 *
 * Variants:
 *   full    — /pace atomic surface (four-option control + confirm modal + secondary-field display)
 *   compact — context overlay (current kind + summary line)
 *   chip    — chat composer (kind badge only, read-only; deep-links to /pace)
 *
 * Pace is operator-only substrate per ADR-298 D11; the Reviewer cannot
 * write it (path in DEFAULT_REVIEWER_WRITE_LOCKS).
 */

import { useState } from 'react';
import { Gauge, ArrowRight } from 'lucide-react';
import {
  useCockpitPace,
  paceKindLabel,
  type PaceKind,
} from '@/lib/content-shapes/pace';
import { cn } from '@/lib/utils';
import type { WorkspaceRevisionSummary } from '@/types';
import { RevisionFootnote } from './RevisionFootnote';
import { ConfirmDialChange } from './ConfirmDialChange';

export type PaceVariant = 'full' | 'compact' | 'chip';

interface PaceCardProps {
  variant?: PaceVariant;
  /** For chip variant: click opens /pace. */
  onOpen?: () => void;
  /** ADR-266 D8 parity: pre-fetched _pace.yaml content (from setup-bundle).
   *  When supplied, useCockpitPace primes from this and skips its self-fetch. */
  initialContent?: string | null;
  /** ADR-266 D7: most-recent revision metadata for the footnote line. */
  lastRevision?: WorkspaceRevisionSummary | null;
  className?: string;
}

// Display order intentionally mirrors PACE_KINDS in the content-shape module
// (slowest → fastest). Continuous is the most permissive — no drain cap.
//
// `consequence` is the one-line operator-facing summary surfaced by the
// confirm modal on switch attempts (2026-05-24 design polish). Phrased in
// terms of what changes about the drain behavior, not what the kind "means."
const KIND_OPTIONS: {
  value: PaceKind;
  label: string;
  description: string;
  consequence: string;
}[] = [
  {
    value: 'weekly',
    label: 'Weekly',
    description: 'Reviewer wakes ~7×/week. Lowest cost; longest latency for paced work.',
    consequence: 'Paced recurrences will fire at most ~7 times per week. Any cron declared above this rate will be refused at create-time.',
  },
  {
    value: 'daily',
    label: 'Daily',
    description: 'Reviewer wakes ~24×/day. Default for most operators.',
    consequence: 'Paced recurrences will fire at most ~24 times per day. Existing recurrences above this rate will fail their next pace check.',
  },
  {
    value: 'hourly',
    label: 'Hourly',
    description: 'Reviewer wakes ~168×/day. Higher cost; supports time-sensitive workflows.',
    consequence: 'Paced recurrences can fire up to ~168 times per day. Daily costs will increase materially.',
  },
  {
    value: 'continuous',
    label: 'Continuous',
    description: 'No drain cap — paced lane drains as fast as it accumulates. Highest cost ceiling.',
    consequence: 'The paced lane will drain without a rate ceiling — every cron-tick wake fires regardless of total frequency. Cost is bounded only by your monthly budget.',
  },
];

export function PaceCard({
  variant = 'full',
  onOpen,
  initialContent,
  lastRevision,
  className,
}: PaceCardProps) {
  const { meta, loading, kind, summary, setKind } = useCockpitPace({ initialContent });

  // Confirm-modal state (full variant only — compact + chip never mutate).
  const [pendingKind, setPendingKind] = useState<PaceKind | null>(null);

  if (variant === 'chip') {
    if (loading || !kind) return null;
    return (
      <button
        type="button"
        onClick={onOpen}
        className={cn(
          'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium',
          'bg-muted/60 text-muted-foreground hover:text-foreground transition-colors',
          className,
        )}
        title="Pace — click to manage"
      >
        <Gauge className="w-3 h-3" />
        {paceKindLabel(kind)}
      </button>
    );
  }

  if (variant === 'compact') {
    return (
      <div className={cn('space-y-1.5', className)}>
        <div className="flex items-center gap-1.5">
          <Gauge className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Pace</h3>
        </div>
        {loading ? (
          <p className="text-xs text-muted-foreground/40">Loading…</p>
        ) : (
          <div className="flex items-center justify-between gap-3">
            <div>
              <span className="text-sm font-medium">{summary}</span>
              {kind && (
                <p className="text-xs text-muted-foreground/70 mt-0.5">
                  {KIND_OPTIONS.find(o => o.value === kind)?.description}
                </p>
              )}
            </div>
            {onOpen && (
              <button
                type="button"
                onClick={onOpen}
                className="shrink-0 text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                Change <ArrowRight className="inline w-3 h-3" />
              </button>
            )}
          </div>
        )}
      </div>
    );
  }

  // full
  const currentKind = kind;
  const pendingMeta = pendingKind ? KIND_OPTIONS.find(o => o.value === pendingKind) : null;
  const currentMeta = currentKind ? KIND_OPTIONS.find(o => o.value === currentKind) : null;

  return (
    <div className={cn('space-y-3', className)}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold">Workspace pace</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            How often the Reviewer wakes through the paced lane. Trigger-dimension dial of the Pace + Autonomy + Identity trifecta (ADR-298 D11).
          </p>
        </div>
        <RevisionFootnote revision={lastRevision ?? null} className="shrink-0 pt-1" />
      </div>

      {loading ? (
        <div className="h-24 rounded-md bg-muted/30 animate-pulse" />
      ) : (
        <div className="space-y-2">
          {KIND_OPTIONS.map(opt => {
            const isActive = currentKind === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => {
                  // No-op when selecting already-active kind.
                  if (opt.value === currentKind) return;
                  setPendingKind(opt.value);
                }}
                className={cn(
                  'w-full text-left rounded-lg border px-4 py-3 transition-colors',
                  isActive
                    ? 'border-primary/50 bg-primary/5'
                    : 'border-border/60 hover:border-border hover:bg-muted/20',
                )}
              >
                <div className="flex items-center gap-2">
                  <div className={cn(
                    'h-3.5 w-3.5 rounded-full border-2 shrink-0 transition-colors',
                    isActive ? 'border-primary bg-primary' : 'border-border',
                  )} />
                  <span className="text-sm font-medium">{opt.label}</span>
                </div>
                <p className="text-xs text-muted-foreground mt-1 ml-5.5">{opt.description}</p>
              </button>
            );
          })}

          {/* Secondary-field display (ADR-300 D2): preserved on disk but
              not editable in the surface. Surfaces here so operators can
              see what they currently have; chat is the edit path. */}
          {(meta?.every || meta?.monthly_budget_usd) && (
            <div className="rounded-md bg-muted/20 border border-border/40 px-3 py-2 space-y-1">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                Additional settings
              </p>
              {meta?.every && (
                <p className="text-xs text-muted-foreground">
                  Numeric override: <span className="font-mono">{meta.every}</span> · edit via chat
                </p>
              )}
              {meta?.monthly_budget_usd !== undefined && (
                <p className="text-xs text-muted-foreground">
                  Monthly budget: ${meta.monthly_budget_usd.toLocaleString()} · edit via chat
                </p>
              )}
            </div>
          )}

          {!currentKind && (
            <p className="text-[11px] text-muted-foreground/60 px-1">
              No pace declared — paced lane drains without cap until you choose one.
            </p>
          )}
        </div>
      )}

      <ConfirmDialChange
        open={pendingKind !== null && pendingMeta !== undefined}
        dialName="pace"
        fromLabel={currentMeta?.label ?? 'unset'}
        toLabel={pendingMeta?.label ?? ''}
        consequence={pendingMeta?.consequence ?? ''}
        onCancel={() => setPendingKind(null)}
        onConfirm={async () => {
          if (!pendingKind) return;
          const next = pendingKind;
          setPendingKind(null);
          await setKind(next);
        }}
      />
    </div>
  );
}
