'use client';

/**
 * PauseAutonomyModal — manage workspace autonomy posture from the feed
 * header chip (Commit G, 2026-05-11).
 *
 * Two responsibilities:
 *   1. Change delegation level (manual / bounded / autonomous) — via
 *      useAutonomy().setDelegation. Same backend write path the
 *      composer chip used pre-Commit-G; functionally identical.
 *   2. Pause / resume the workspace-wide autonomy gate (ADR-248 D3) —
 *      via useAutonomy().setPause / clearPause. Time-based; expires
 *      automatically.
 *
 * Pause preset durations (kernel default; bundle-supplied custom
 * presets are a follow-on per ADR-188 kernel-agnostic principle):
 *   1h · 4h · Until end of day · Indefinite
 *
 * Indefinite sets a far-future timestamp (year 2099) which the
 * operator must explicitly lift via the Resume button.
 */

import { useState } from 'react';
import { Pause, Play, Loader2, AlertCircle } from 'lucide-react';
import { InteractiveModal } from '@/components/tp/InteractiveModal';
import { useAutonomy, type AutonomyDelegation } from '@/lib/content-shapes/autonomy';
import { cn } from '@/lib/utils';

interface PauseAutonomyModalProps {
  onClose: () => void;
}

interface DelegationOption {
  value: AutonomyDelegation;
  label: string;
  description: string;
}

const DELEGATION_OPTIONS: ReadonlyArray<DelegationOption> = [
  {
    value: 'manual',
    label: 'Manual',
    description: 'Every proposal requires your approval.',
  },
  {
    value: 'bounded',
    label: 'Bounded',
    description: 'Auto-approve within ceiling; above ceiling needs operator click.',
  },
  {
    value: 'autonomous',
    label: 'Full auto',
    description: 'Reviewer approves and executes. Still respects never_auto + irreversibility gate.',
  },
];

interface PauseDurationOption {
  label: string;
  /** Returns ISO-8601 timestamp for the pause expiry. null = indefinite. */
  computeUntil: () => string | null;
}

const PAUSE_DURATIONS: ReadonlyArray<PauseDurationOption> = [
  {
    label: '1 hour',
    computeUntil: () => new Date(Date.now() + 60 * 60 * 1000).toISOString(),
  },
  {
    label: '4 hours',
    computeUntil: () => new Date(Date.now() + 4 * 60 * 60 * 1000).toISOString(),
  },
  {
    label: 'Until end of day',
    computeUntil: () => {
      const eod = new Date();
      eod.setHours(23, 59, 59, 999);
      return eod.toISOString();
    },
  },
  {
    label: 'Indefinite',
    computeUntil: () => null,
  },
];

export function PauseAutonomyModal({ onClose }: PauseAutonomyModalProps) {
  const {
    effectiveDelegation,
    pause,
    setDelegation,
    setPause,
    clearPause,
  } = useAutonomy();

  const [pending, setPending] = useState<null | 'delegation' | 'pause' | 'resume'>(null);
  const [error, setError] = useState<string | null>(null);
  const [pauseReason, setPauseReason] = useState('');

  const handleDelegationChange = async (next: AutonomyDelegation) => {
    if (next === effectiveDelegation) return;
    setPending('delegation');
    setError(null);
    try {
      await setDelegation(next);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update delegation');
      setPending(null);
    }
  };

  const handlePause = async (computeUntil: () => string | null, label: string) => {
    setPending('pause');
    setError(null);
    try {
      await setPause(computeUntil(), pauseReason || `paused ${label.toLowerCase()}`);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to pause');
      setPending(null);
    }
  };

  const handleResume = async () => {
    setPending('resume');
    setError(null);
    try {
      await clearPause();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to resume');
      setPending(null);
    }
  };

  const isLoading = pending !== null;

  return (
    <InteractiveModal
      isOpen={true}
      onClose={onClose}
      title="Autonomy"
      subtitle={
        pause.active
          ? 'Paused — Reviewer is not auto-executing any proposals.'
          : 'How much explicit approval each Reviewer-approved action requires.'
      }
    >
      <div className="space-y-5">
        {/* Pause / Resume section — visually prominent when paused */}
        {pause.active ? (
          <div className="rounded-md border border-amber-300 bg-amber-50 p-3 dark:border-amber-700 dark:bg-amber-900/20">
            <div className="flex items-start gap-2">
              <Pause className="w-4 h-4 text-amber-700 dark:text-amber-300 shrink-0 mt-0.5" />
              <div className="flex-1 space-y-2">
                <div>
                  <p className="text-sm font-medium text-amber-900 dark:text-amber-100">
                    Paused {pause.until && new Date(pause.until).getFullYear() < 2099 ? `until ${new Date(pause.until).toLocaleString()}` : 'indefinitely'}
                  </p>
                  {pause.reason && (
                    <p className="text-xs text-amber-800/80 dark:text-amber-200/80 mt-0.5">
                      {pause.reason}
                    </p>
                  )}
                </div>
                <button
                  type="button"
                  onClick={handleResume}
                  disabled={isLoading}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded bg-amber-700 text-amber-50 hover:bg-amber-800 transition-colors disabled:opacity-50"
                >
                  {pending === 'resume' ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
                  Resume autonomy
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Pause autonomy
              </p>
              <p className="text-[11px] text-muted-foreground/70 mt-0.5">
                Halt all auto-execution while you review or step away. Lifts automatically at the chosen time.
              </p>
            </div>
            <input
              type="text"
              value={pauseReason}
              onChange={(e) => setPauseReason(e.target.value)}
              placeholder="Optional reason — surfaces on cockpit"
              disabled={isLoading}
              className="w-full px-2.5 py-1.5 text-xs rounded border border-border bg-background focus:outline-none focus:ring-1 focus:ring-foreground/40 disabled:opacity-50"
            />
            <div className="flex flex-wrap gap-1.5">
              {PAUSE_DURATIONS.map(({ label, computeUntil }) => (
                <button
                  key={label}
                  type="button"
                  onClick={() => handlePause(computeUntil, label)}
                  disabled={isLoading}
                  className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium rounded border border-border text-muted-foreground hover:border-foreground/40 hover:bg-muted hover:text-foreground transition-colors disabled:opacity-50"
                >
                  {pending === 'pause' && <Loader2 className="w-3 h-3 animate-spin" />}
                  {label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Delegation level section — disabled while paused (pause supersedes) */}
        <div className={cn('space-y-2', pause.active && 'opacity-50 pointer-events-none')}>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Delegation level {pause.active && <span className="text-[10px] normal-case text-muted-foreground/60">(while not paused)</span>}
            </p>
          </div>
          <div className="space-y-1.5">
            {DELEGATION_OPTIONS.map((opt) => {
              const isActive = opt.value === effectiveDelegation;
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => handleDelegationChange(opt.value)}
                  disabled={isLoading || pause.active}
                  className={cn(
                    'w-full text-left rounded-md border px-3 py-2 transition-colors disabled:cursor-not-allowed',
                    isActive
                      ? 'border-primary/50 bg-primary/5'
                      : 'border-border/60 hover:border-border hover:bg-muted/30',
                  )}
                >
                  <div className="flex items-center gap-2">
                    <div className={cn(
                      'h-3 w-3 rounded-full border-2 shrink-0 transition-colors',
                      isActive ? 'border-primary bg-primary' : 'border-border',
                    )} />
                    <span className="text-xs font-medium">{opt.label}</span>
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-0.5 ml-5">{opt.description}</p>
                </button>
              );
            })}
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-1.5 text-xs text-destructive">
            <AlertCircle className="w-3 h-3 shrink-0" />
            {error}
          </div>
        )}
      </div>
    </InteractiveModal>
  );
}
