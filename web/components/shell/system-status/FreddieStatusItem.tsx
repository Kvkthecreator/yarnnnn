'use client';

/**
 * FreddieStatusItem — the SYSTEM-AGENT chip in the agent-OS menu-bar status
 * cluster (ADR-297 D20 slot 1; reframed 2026-07-01).
 *
 * The conceptual reframe (operator call, 2026-07-01): now that the substrate
 * filesystem is the service model and Freddie is the system agent latched onto
 * it (the GitHub-⇄-Copilot shape — the substrate is the repo, Freddie is the
 * agent working over it), this chip is not an abstract "OS autonomy dial." It
 * is FREDDIE's disposition — how much the system agent acts on its own. Autonomy
 * is the READOUT; Freddie is the entity. The chip reads "Freddie · <posture>",
 * the copy speaks of Freddie, and the footer opens Freddie's settings (the
 * `autonomy` pane resolves to Freddie's pane, Grant group — ADR-387 §6.4).
 *
 * Consumes useAutonomy() (ADR-238 D2). Read-only popover; mutations happen on
 * Freddie's Autonomy pane (footer link; the `autonomy` slug is pane_of: agents,
 * so foregroundSurface delivers agents.pane=autonomy → Freddie's Grant group).
 *
 * Visual: the FreddieAvatar mascot (2026-07-01) — the full-color Frankie —
 * now has a FACE in the top bar, not the shield-check glyph. The mascot wears
 * the LIVENESS its posture implies (livenessFor): manual→waiting, autonomous→
 * acting, bounded/not-set→idle, paused→paused. This is the first mount point of
 * the Freddie Design System (one mascot, layered SVG, state-expressive).
 *
 * NOTE: Budget (the adjacent MONEY chip) is being reframed separately with the
 * pricing-model work — it is deliberately untouched here (operator, 2026-07-01).
 */

import { useAutonomy, type AutonomyDelegation } from '@/lib/content-shapes/autonomy';
import { StatusItemPopover, type StatusTone } from './StatusItemPopover';
import { FreddieAvatar, type FreddieLiveness } from '@/components/freddie/FreddieAvatar';

function delegationLabel(d: AutonomyDelegation | null): string {
  if (d === 'autonomous') return 'Full auto';
  if (d === 'bounded') return 'Bounded';
  if (d === 'manual') return 'Manual';
  return 'Not set';
}

// Disposition → the liveness the mascot wears in the chip. The chip reads a
// resting POSTURE (not real-time activity), so we map each posture to the
// liveness that reads honestly at rest:
//   paused     → paused  (asleep)
//   manual     → waiting (defers every decision to you — always looking at you)
//   autonomous → acting  (acts on its own)
//   bounded    → idle    (steady; acts within the ceiling, calm at rest)
//   not set    → idle    (nothing configured — calm/dormant)
function livenessFor(d: AutonomyDelegation | null, paused: boolean): FreddieLiveness {
  if (paused) return 'paused';
  if (d === 'manual') return 'waiting';
  if (d === 'autonomous') return 'acting';
  return 'idle';
}

// Freddie-framed disposition copy — "how much the system agent acts on its own."
function delegationDescription(d: AutonomyDelegation | null): string {
  if (d === 'autonomous') return 'Freddie acts on any step within the ceiling without waiting for you.';
  if (d === 'bounded') return 'Freddie acts under the ceiling; above it, it queues for your approval.';
  if (d === 'manual') return 'Every Freddie decision queues for your approval before it binds.';
  return "Freddie's autonomy isn't configured yet.";
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

export function FreddieStatusItem() {
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

  // The chip is a HERO placement of Freddie — the mascot, wearing the
  // liveness its current posture implies (the 2026-07-01 avatar). It replaces
  // the shield-check glyph: Freddie now literally has a FACE in the top bar.
  const liveness = livenessFor(effectiveDelegation, !!isPaused);
  // Bound trigger icon — StatusItemPopover renders `<Icon className=... />`, so
  // we hand it a component with the state pre-bound.
  const TriggerIcon = ({ className }: { className?: string }) => (
    <FreddieAvatar state={liveness} className={className} />
  );
  const label = delegationLabel(effectiveDelegation);
  const ceilingCents = meta?.default_ceiling_cents;
  const ceilingLabel =
    effectiveDelegation === 'bounded' && ceilingCents
      ? ` · $${(ceilingCents / 100).toLocaleString()}`
      : '';

  // The chip names the ENTITY (Freddie), with its disposition as the readout.
  const tooltip = isPaused
    ? `Freddie paused ${formatPauseUntil(pause.until!)}`
    : `Freddie · ${label}${ceilingLabel}`;

  const popoverHeader = (
    <div className="flex items-center gap-2">
      <FreddieAvatar state={liveness} className="w-4 h-4 shrink-0" />
      <span className="text-sm font-medium">
        Freddie
        <span className="text-muted-foreground">
          {isPaused ? ` · paused ${formatPauseUntil(pause.until!)}` : ` · ${label}${ceilingLabel}`}
        </span>
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
        <p className="pt-0.5">Any spend above your limit waits for your approval.</p>
      )}
    </div>
  );

  return (
    <StatusItemPopover
      icon={TriggerIcon}
      tooltip={tooltip}
      tone={tone}
      ariaLabel="Freddie, the system agent"
      popoverHeader={popoverHeader}
      popoverBody={popoverBody}
      // The `autonomy` slug is pane_of: agents (ADR-387 §6.4), so this lands on
      // Freddie's Autonomy pane (Grant group) — "Freddie's settings", not a
      // standalone OS dial.
      footerTarget={{ kind: 'surface', slug: 'autonomy' }}
      footerLabel="Freddie settings"
    />
  );
}
