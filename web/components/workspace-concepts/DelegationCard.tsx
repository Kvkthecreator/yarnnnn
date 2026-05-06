'use client';

/**
 * DelegationCard — L3 component for /workspace/context/_shared/AUTONOMY.md.
 *
 * The only concept component with a Direct mutation — setLevel() writes
 * the file without going through chat (it's a discrete config value,
 * not authored prose).
 *
 * Variants:
 *   full    — /workspace page (four-option control + description)
 *   compact — context overlay (current level + one-line description)
 *   chip    — chat composer (level badge only, read-only)
 *
 * See docs/design/WORKSPACE-COMPONENTS.md.
 */

import { ShieldCheck, ArrowRight } from 'lucide-react';
import { useAutonomy, type AutonomyLevel } from '@/lib/content-shapes/autonomy';
import { cn } from '@/lib/utils';

export type DelegationVariant = 'full' | 'compact' | 'chip';

interface DelegationCardProps {
  variant?: DelegationVariant;
  /** For chip variant: click opens /workspace */
  onOpen?: () => void;
  className?: string;
}

const LEVELS: { value: AutonomyLevel; label: string; description: string }[] = [
  {
    value: 'manual',
    label: 'Manual',
    description: 'Every action waits for your approval before executing.',
  },
  {
    value: 'assisted',
    label: 'Assisted',
    description: 'YARNNN stages and prepares; you approve before consequences.',
  },
  {
    value: 'bounded_autonomous',
    label: 'Bounded',
    description: 'Acts autonomously within your declared ceiling. Flags above it.',
  },
  {
    value: 'autonomous',
    label: 'Autonomous',
    description: 'Full delegation within declared boundaries. You review outcomes.',
  },
];

export function DelegationCard({ variant = 'full', onOpen, className }: DelegationCardProps) {
  const { meta, loading, effectiveLevel, summary, setLevel } = useAutonomy();

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
        title="Delegation level — click to manage"
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
          <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Delegation</h3>
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

  return (
    <div className={cn('space-y-3', className)}>
      <div>
        <p className="text-sm font-semibold">Delegation</p>
        <p className="text-xs text-muted-foreground mt-0.5">How much YARNNN decides without asking first.</p>
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
                onClick={() => void setLevel(lvl.value)}
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

          {meta?.default_ceiling_cents && currentLevel === 'bounded_autonomous' && (
            <p className="text-[11px] text-muted-foreground/60 px-1">
              Ceiling: ${(meta.default_ceiling_cents / 100).toLocaleString()} per action
            </p>
          )}
        </div>
      )}
    </div>
  );
}
