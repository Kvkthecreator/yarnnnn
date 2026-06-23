'use client';

/**
 * AutonomyStatusItem — autonomy posture chip in the agent-OS menu-bar
 * status cluster (ADR-297 D20, slot 1).
 *
 * Consumes useAutonomy() (ADR-238 D2). Read-only popover; mutations
 * happen on the /autonomy atomic surface (ADR-297 D1).
 *
 * Replaces AutonomyHeaderChip (deleted in same commit) — the autonomy
 * indicator moves from Feed-only chrome to kernel chrome (every
 * surface). PauseAutonomyModal also deleted — pause/resume happens on
 * /autonomy via AutonomyCard's confirm-modal pattern.
 *
 * Icon discipline (ADR-297 D20 amendment 2026-05-25): the default chip
 * icon is the canonical /autonomy surface icon resolved via
 * `resolveSurfaceIcon('shield-check')` — same glyph as the Dock and
 * Launcher render. State-specific overrides (Pause when paused) are
 * the only deviation. Singular Implementation: one icon per surface.
 */

import { Pause } from 'lucide-react';
import { useAutonomy, type AutonomyDelegation } from '@/lib/content-shapes/autonomy';
import { resolveSurfaceIcon } from '@/lib/shell/surface-icons';
import { StatusItemPopover, type StatusTone } from './StatusItemPopover';

function delegationLabel(d: AutonomyDelegation | null): string {
  if (d === 'autonomous') return 'Full auto';
  if (d === 'bounded') return 'Bounded';
  if (d === 'manual') return 'Manual';
  return 'Not set';
}

function delegationDescription(d: AutonomyDelegation | null): string {
  if (d === 'autonomous') return 'Reviewer approves any capital action within ceiling.';
  if (d === 'bounded') return 'Reviewer approves under ceiling; above ceiling queues for operator.';
  if (d === 'manual') return 'Every Reviewer verdict queues for operator approval.';
  return 'Autonomy posture not configured.';
}

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
  if (dt.getFullYear() >= 2099) return 'indefinitely';
  return `until ${dt.toLocaleDateString([], { month: 'short', day: 'numeric' })}`;
}

export function AutonomyStatusItem() {
  const { effectiveDelegation, pause, meta, loading } = useAutonomy();

  if (loading) {
    return <div className="w-8 h-8" aria-hidden />;
  }

  const isPaused = pause.active && pause.until;
  const tone: StatusTone = isPaused
    ? 'paused'
    : effectiveDelegation === 'autonomous'
      ? 'ok'
      : effectiveDelegation && effectiveDelegation !== 'manual'
        ? 'ok'
        : 'muted';

  // ADR-297 D20 amendment: canonical surface icon for /autonomy
  // (resolved from kernel_surfaces.icon_key = "shield-check"). Paused
  // state is the only state-specific override.
  const AutonomyIcon = resolveSurfaceIcon('shield-check');
  const Icon = isPaused ? Pause : AutonomyIcon;
  const label = delegationLabel(effectiveDelegation);
  const ceilingCents = meta?.default_ceiling_cents;
  const ceilingLabel =
    effectiveDelegation === 'bounded' && ceilingCents
      ? ` · $${(ceilingCents / 100).toLocaleString()}`
      : '';

  const tooltip = isPaused
    ? `Autonomy paused ${formatPauseUntil(pause.until!)}`
    : `Autonomy: ${label}${ceilingLabel}`;

  const popoverHeader = (
    <div className="flex items-center gap-2">
      <Icon className="w-3.5 h-3.5 shrink-0" />
      <span className="text-sm font-medium">
        {isPaused ? `Paused ${formatPauseUntil(pause.until!)}` : `${label}${ceilingLabel}`}
      </span>
    </div>
  );

  // The hard safety list — actions/paths that ALWAYS queue regardless of
  // delegation (default_never_auto). Per-domain overrides too. Surfacing
  // these gives the popover the same key/value depth the Budget popover has.
  const neverAuto = meta?.default_never_auto ?? [];
  const domains = meta?.domains ?? {};
  const domainNames = Object.keys(domains);

  const popoverBody = (
    <div className="space-y-1.5 text-muted-foreground text-xs">
      <p>{isPaused && pause.reason ? `Reason: ${pause.reason}` : delegationDescription(effectiveDelegation)}</p>

      {!isPaused && (
        <div className="pt-1 space-y-0.5">
          {/* Ceiling — the per-action cap. Shown for any configured level
              (it bounds even "Full auto"), not just bounded. */}
          {ceilingCents != null && (
            <div className="flex justify-between">
              <span>Ceiling per action</span>
              <span className="font-mono">${(ceilingCents / 100).toLocaleString()}</span>
            </div>
          )}
          {/* The hard safety list — always queues regardless of level. */}
          {neverAuto.length > 0 && (
            <div className="flex justify-between gap-3">
              <span className="shrink-0">Always queues</span>
              <span className="text-right truncate" title={neverAuto.join(', ')}>
                {neverAuto.length === 1
                  ? neverAuto[0]
                  : `${neverAuto.length} guarded actions`}
              </span>
            </div>
          )}
          {/* Per-domain overrides, if the operator set any. */}
          {domainNames.length > 0 && (
            <div className="flex justify-between">
              <span>Domain overrides</span>
              <span className="font-mono">{domainNames.length}</span>
            </div>
          )}
        </div>
      )}

      {!isPaused && effectiveDelegation === 'bounded' && ceilingCents != null && (
        <p className="pt-0.5">Above the ceiling, capital actions queue for your approval.</p>
      )}
    </div>
  );

  return (
    <StatusItemPopover
      icon={Icon}
      tooltip={tooltip}
      tone={tone}
      ariaLabel="Autonomy posture"
      popoverHeader={popoverHeader}
      popoverBody={popoverBody}
      footerTarget={{ kind: 'surface', slug: 'autonomy' }}
      footerLabel="Autonomy Settings"
    />
  );
}
