'use client';

/**
 * AutonomyHeaderChip — workspace-level autonomy posture in the feed
 * header (adjacent to the YARNNN logo).
 *
 * Commit G (2026-05-11) — relocates the autonomy chip from the chat
 * composer to the feed header. Pre-G placement was a holdover from
 * when the composer felt like the workspace command center; per
 * ADR-247 the operator-in-real-time is one of three feed participants,
 * not the primary actor. Autonomy is workspace-level standing intent
 * — it belongs at the workspace frame, not the operator-input frame.
 *
 * Two visual states:
 *   active mode (delegation displayed)  → muted chip "Bounded · $200"
 *   paused (paused_until in future)     → attention chip "⚠ Paused 5pm"
 *
 * Click → PauseAutonomyModal opens. Modal handles both delegation
 * change (forwarded to setDelegation) and pause/resume.
 *
 * Singular Implementation: one chip, one location. The composer's
 * old chip was deleted in the same commit.
 */

import { useState } from 'react';
import { ShieldAlert, ShieldCheck, Pause } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAutonomy, type AutonomyDelegation } from '@/lib/content-shapes/autonomy';
import { PauseAutonomyModal } from './PauseAutonomyModal';

function formatPauseUntil(untilIso: string): string {
  const dt = new Date(untilIso);
  if (isNaN(dt.getTime())) return 'paused';
  const now = new Date();
  const sameDay =
    dt.getFullYear() === now.getFullYear() &&
    dt.getMonth() === now.getMonth() &&
    dt.getDate() === now.getDate();
  if (sameDay) {
    return `until ${dt.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}`;
  }
  // Far-future indefinite sentinel ('2099-…') → "indefinitely"
  if (dt.getFullYear() >= 2099) return 'indefinitely';
  return `until ${dt.toLocaleDateString([], { month: 'short', day: 'numeric' })}`;
}

function delegationLabel(d: AutonomyDelegation | null): string {
  if (d === 'autonomous') return 'Full auto';
  if (d === 'bounded') return 'Bounded';
  if (d === 'manual') return 'Manual';
  return 'Autonomy';
}

export function AutonomyHeaderChip() {
  const { effectiveDelegation, pause, meta, loading } = useAutonomy();
  const [modalOpen, setModalOpen] = useState(false);

  if (loading) return null;

  // Paused state takes visual precedence over delegation.
  if (pause.active && pause.until) {
    return (
      <>
        <button
          type="button"
          onClick={() => setModalOpen(true)}
          className={cn(
            'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium',
            'bg-amber-100 text-amber-900 hover:bg-amber-200 transition-colors',
            'dark:bg-amber-900/30 dark:text-amber-200 dark:hover:bg-amber-900/50',
          )}
          title={pause.reason ? `Paused: ${pause.reason} — click to manage` : 'Click to manage autonomy'}
        >
          <Pause className="w-3 h-3 shrink-0" />
          <span>Paused {formatPauseUntil(pause.until)}</span>
        </button>
        {modalOpen && <PauseAutonomyModal onClose={() => setModalOpen(false)} />}
      </>
    );
  }

  // Active delegation state.
  const Icon = effectiveDelegation === 'autonomous' ? ShieldCheck : ShieldAlert;
  const label = delegationLabel(effectiveDelegation);
  const ceilingCents = meta?.default_ceiling_cents;
  const ceilingLabel =
    effectiveDelegation === 'bounded' && ceilingCents
      ? ` · $${(ceilingCents / 100).toLocaleString()}`
      : '';

  return (
    <>
      <button
        type="button"
        onClick={() => setModalOpen(true)}
        className={cn(
          'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors',
          effectiveDelegation && effectiveDelegation !== 'manual'
            ? 'bg-primary/10 text-primary hover:bg-primary/20'
            : 'text-muted-foreground hover:bg-muted hover:text-foreground border border-border',
        )}
        title="Autonomy posture — click to manage"
      >
        <Icon className="w-3 h-3 shrink-0" />
        <span>{label}{ceilingLabel}</span>
      </button>
      {modalOpen && <PauseAutonomyModal onClose={() => setModalOpen(false)} />}
    </>
  );
}
