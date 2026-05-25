'use client';

/**
 * ConnectionsStatusItem — platform-connection reach chip in the
 * agent-OS menu-bar status cluster (ADR-297 D20, slot 4).
 *
 * Consumes api.workspace.getState() — reads capability_gaps. Read-only
 * popover; mutations (connect/reconnect) happen on /connectors per
 * ADR-297 D19.4.
 *
 * Wi-Fi analog: capability reach is "what tools the agent can touch."
 * Operator-critical when the active program declares required
 * platforms that aren't connected (capability_gaps with connected:
 * false). Chip turns warn-tone when any declared capability is unmet.
 *
 * Icon discipline (ADR-297 D20 amendment 2026-05-25): the chip icon is
 * the canonical /connectors surface icon resolved via
 * `resolveSurfaceIcon('link-2')` — same glyph as the Dock and Launcher
 * render. Singular Implementation: one icon per surface.
 */

import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import { resolveSurfaceIcon } from '@/lib/shell/surface-icons';
import { StatusItemPopover, type StatusTone } from './StatusItemPopover';

type WorkspaceState = Awaited<ReturnType<typeof api.workspace.getState>>;
type CapabilityGap = WorkspaceState['capability_gaps'][number];

export function ConnectionsStatusItem() {
  const [state, setState] = useState<WorkspaceState | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api.workspace
      .getState()
      .then((data) => {
        if (!cancelled) setState(data);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="w-8 h-8 flex items-center justify-center text-muted-foreground" aria-hidden>
        <Loader2 className="w-3 h-3 animate-spin" />
      </div>
    );
  }

  if (!state) {
    return <div className="w-8 h-8" aria-hidden />;
  }

  const gaps = state.capability_gaps;
  const totalDeclared = gaps.length;
  const connected = gaps.filter((g) => g.connected).length;
  const unmet = totalDeclared - connected;

  const tone: StatusTone =
    totalDeclared === 0 ? 'muted' : unmet > 0 ? 'warn' : 'ok';

  // ADR-297 D20 amendment: canonical surface icon for /connectors
  // (resolved from kernel_surfaces.icon_key = "link-2").
  const ConnectionsIcon = resolveSurfaceIcon('link-2');

  const tooltip =
    totalDeclared === 0
      ? 'No platforms declared by active program'
      : `Connections: ${connected}/${totalDeclared}`;

  const popoverHeader = (
    <div className="flex items-center gap-2">
      <ConnectionsIcon className="w-3.5 h-3.5 shrink-0" />
      <span className="text-sm font-medium">
        {totalDeclared === 0
          ? 'No connections required'
          : `${connected}/${totalDeclared} connected`}
      </span>
    </div>
  );

  const popoverBody = (
    <div className="space-y-1 text-muted-foreground text-xs">
      {totalDeclared === 0 ? (
        <p>
          {state.active_program_slug
            ? 'Active program declares no platform requirements.'
            : 'No active program — workspace runs in knowledge mode.'}
        </p>
      ) : (
        <>
          <p>
            {unmet > 0
              ? `${unmet} platform${unmet === 1 ? '' : 's'} unmet — agent runs in knowledge mode without it.`
              : 'All declared platforms connected.'}
          </p>
          <div className="pt-1 space-y-0.5">
            {gaps.map((gap: CapabilityGap) => (
              <div key={gap.capability} className="flex justify-between items-center">
                <span className="capitalize">{gap.requires_platform}</span>
                <span className={gap.connected ? 'text-emerald-600' : 'text-amber-600'}>
                  {gap.connected ? '● connected' : '○ not connected'}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );

  return (
    <StatusItemPopover
      icon={ConnectionsIcon}
      tooltip={tooltip}
      tone={tone}
      ariaLabel="Platform connections"
      popoverHeader={popoverHeader}
      popoverBody={popoverBody}
      footerTarget={{ kind: 'surface', slug: 'connectors' }}
      footerLabel="Connectors"
    />
  );
}
