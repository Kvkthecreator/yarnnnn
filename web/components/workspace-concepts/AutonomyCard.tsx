'use client';

/**
 * AutonomyCard — L3 component for /workspace/context/_shared/_autonomy.yaml.
 *
 * Renamed from DelegationCard (2026-05-24) to align with the substrate file
 * (_autonomy.yaml) and the operator's mental model. The schema field
 * `default_delegation` stays — it's the precise data-layer term for the
 * delegated level. At the operator surface the broader concept is Autonomy.
 *
 * The only concept component with a Direct mutation — `setLevel()` writes
 * the file without going through chat (it's a discrete config value,
 * not authored prose). Per the 2026-05-24 design polish: the full variant
 * gates every mutation behind a confirm modal because switching autonomy
 * level has capital impact and one-click commits were too easy to trigger
 * accidentally.
 *
 * Variants:
 *   full    — /autonomy page (four-option control + description + confirm modal)
 *   compact — context overlay (current level + one-line description)
 *   chip    — chat composer (level badge only, read-only)
 *
 * See docs/design/WORKSPACE-COMPONENTS.md §2.
 */

import { useState } from 'react';
import { ShieldCheck, ArrowRight } from 'lucide-react';
import { useAutonomy, type AutonomyLevel } from '@/lib/content-shapes/autonomy';
import { cn } from '@/lib/utils';
import type { WorkspaceRevisionSummary } from '@/types';
import { RevisionFootnote } from './RevisionFootnote';
import { ConfirmDialChange } from './ConfirmDialChange';

export type AutonomyVariant = 'full' | 'compact' | 'chip';

interface AutonomyCardProps {
  variant?: AutonomyVariant;
  /** For chip variant: click opens /autonomy */
  onOpen?: () => void;
  /** ADR-266 D8: pre-fetched _autonomy.yaml content (from setup-bundle).
   *  When supplied, useAutonomy primes from this and skips its self-fetch. */
  initialContent?: string | null;
  /** ADR-266 D7: most-recent revision metadata for the footnote line. */
  lastRevision?: WorkspaceRevisionSummary | null;
  className?: string;
}

// Commit F (2026-05-11): canonical 3-value enum, matches backend
// _VALID_DELEGATION_LEVELS in api/services/review_policy.py.
// `assisted` was retired — it had no backend semantics distinct from
// `manual` and was silently treated as manual by should_auto_execute_verdict.
// `bounded_autonomous` collapsed to `bounded` (Singular Implementation).
//
// `consequence` is the one-line operator-facing summary surfaced by the
// confirm modal on switch attempts (2026-05-24 design polish). Phrased in
// terms of what changes about the Reviewer's authority, not what the dial
// "means."
const LEVELS: {
  value: AutonomyLevel;
  label: string;
  description: string;
  consequence: string;
}[] = [
  {
    value: 'manual',
    label: 'Manual',
    description: 'Every action waits for your approval before executing.',
    consequence: 'Every Reviewer action will pause for your approval. You become the bottleneck on every decision.',
  },
  {
    value: 'bounded',
    label: 'Bounded',
    description: 'Acts autonomously within your declared ceiling. Flags above it.',
    consequence: 'The Reviewer will auto-execute actions within your declared ceiling. Higher-impact actions will still wait for approval.',
  },
  {
    value: 'autonomous',
    label: 'Autonomous',
    description: 'Full delegation within declared boundaries. You review outcomes.',
    consequence: 'The Reviewer will auto-execute every action up to the ceiling without first checking in. You review outcomes after the fact.',
  },
];

export function AutonomyCard({
  variant = 'full',
  onOpen,
  initialContent,
  lastRevision,
  className,
}: AutonomyCardProps) {
  const { meta, loading, effectiveLevel, summary, setLevel } = useAutonomy({ initialContent });

  // Confirm-modal state (full variant only — compact + chip never mutate).
  const [pendingLevel, setPendingLevel] = useState<AutonomyLevel | null>(null);

  if (variant === 'chip') {
    if (loading || !effectiveLevel) return null;
    const levelMeta = LEVELS.find(l => l.value === effectiveLevel);
    return (
      <button
        type="button"
        onClick={onOpen}
        className={cn(
          'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium',
          'bg-muted/60 text-muted-foreground hover:text-foreground transition-colors',
          className,
        )}
        title="Autonomy — click to manage"
      >
        <ShieldCheck className="w-3 h-3" />
        {levelMeta?.label ?? effectiveLevel}
      </button>
    );
  }

  if (variant === 'compact') {
    const levelMeta = LEVELS.find(l => l.value === effectiveLevel);
    return (
      <div className={cn('space-y-1.5', className)}>
        <div className="flex items-center gap-1.5">
          <ShieldCheck className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Autonomy</h3>
        </div>
        {loading ? (
          <p className="text-xs text-muted-foreground/40">Loading…</p>
        ) : (
          <div className="flex items-center justify-between gap-3">
            <div>
              <span className="text-sm font-medium">{levelMeta?.label ?? 'Not set'}</span>
              {levelMeta && (
                <p className="text-xs text-muted-foreground/70 mt-0.5">{levelMeta.description}</p>
              )}
            </div>
            {onOpen && (
              <button type="button" onClick={onOpen}
                className="shrink-0 text-xs text-muted-foreground hover:text-foreground transition-colors">
                Change <ArrowRight className="inline w-3 h-3" />
              </button>
            )}
          </div>
        )}
      </div>
    );
  }

  // full
  const currentLevel = effectiveLevel ?? 'manual';
  const pendingMeta = pendingLevel ? LEVELS.find(l => l.value === pendingLevel) : null;
  const currentMeta = LEVELS.find(l => l.value === currentLevel);

  return (
    <div className={cn('space-y-3', className)}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold">Autonomy</p>
          <p className="text-xs text-muted-foreground mt-0.5">How much YARNNN decides without asking first.</p>
        </div>
        <RevisionFootnote revision={lastRevision ?? null} className="shrink-0 pt-1" />
      </div>

      {loading ? (
        <div className="h-24 rounded-md bg-muted/30 animate-pulse" />
      ) : (
        <div className="space-y-2">
          {LEVELS.map(lvl => {
            const isActive = currentLevel === lvl.value;
            return (
              <button
                key={lvl.value}
                type="button"
                onClick={() => {
                  // No-op on selecting the already-active level (avoids
                  // pointless confirm-modal pops).
                  if (lvl.value === currentLevel) return;
                  setPendingLevel(lvl.value);
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
                  <span className="text-sm font-medium">{lvl.label}</span>
                </div>
                <p className="text-xs text-muted-foreground mt-1 ml-5.5">{lvl.description}</p>
              </button>
            );
          })}

          {meta?.default_ceiling_cents && currentLevel === 'bounded' && (
            <p className="text-[11px] text-muted-foreground/60 px-1">
              Ceiling: ${(meta.default_ceiling_cents / 100).toLocaleString()} per action
            </p>
          )}
        </div>
      )}

      <ConfirmDialChange
        open={pendingLevel !== null && pendingMeta !== undefined}
        dialName="autonomy"
        fromLabel={currentMeta?.label ?? 'current'}
        toLabel={pendingMeta?.label ?? ''}
        consequence={pendingMeta?.consequence ?? ''}
        onCancel={() => setPendingLevel(null)}
        onConfirm={async () => {
          if (!pendingLevel) return;
          const next = pendingLevel;
          setPendingLevel(null);
          await setLevel(next);
        }}
      />
    </div>
  );
}
