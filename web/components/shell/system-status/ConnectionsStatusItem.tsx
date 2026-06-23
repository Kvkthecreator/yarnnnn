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

  // Account-level inventory — platforms the operator has connected, regardless
  // of whether the active program requires them. The chip shows demand
  // (gaps) AND inventory (connectedPlatforms) so it stays consistent with the
  // Connectors pane: a program that declares no requirements no longer reads
  // "No connections required" while Slack/Notion/GitHub sit Connected.
  const connectedPlatforms = state.connected_platforms ?? [];
  // Platforms required by the program already appear in `gaps`; list the rest
  // (connected-but-not-required) separately so we never double-count.
  const requiredPlatforms = new Set(gaps.map((g) => g.requires_platform));
  const extraConnected = connectedPlatforms.filter((p) => !requiredPlatforms.has(p));

  // The real connected inventory across the account (not just the program's
  // required set). The header leads with this so 3 connected + 1 required
  // gap never reads as "0/1 connected" (operator-flagged 2026-06-23).
  const totalConnected = connectedPlatforms.length;

  // Tone: a required gap is a SOFT condition — the agent degrades to
  // knowledge mode, it does not break — so it is NOT an error/warn color.
  // Keep the chip neutral (muted) when nothing's connected, and primary
  // (ok) once any platform is connected, regardless of an unmet required
  // gap. (operator-flagged 2026-06-23: 1-of-1 required unmet against 3
  // connected should not paint the cluster orange.)
  const tone: StatusTone = totalConnected > 0 ? 'ok' : 'muted';

  // ADR-297 D20 amendment: canonical surface icon for /connectors
  // (resolved from kernel_surfaces.icon_key = "link-2").
  const ConnectionsIcon = resolveSurfaceIcon('link-2');

  const plural = (n: number) => (n === 1 ? '' : 's');

  // Header + tooltip lead with the connected inventory; the required gap is
  // a secondary clause, not the headline.
  const headerLabel =
    totalConnected > 0
      ? unmet > 0
        ? `${totalConnected} connected · ${unmet} required missing`
        : `${totalConnected} connected`
      : unmet > 0
        ? `${unmet} required platform${plural(unmet)} missing`
        : 'No connections';

  const tooltip =
    totalConnected > 0
      ? unmet > 0
        ? `${totalConnected} connected · ${unmet} required missing`
        : `${totalConnected} platform${plural(totalConnected)} connected`
      : 'No platforms connected';

  const popoverHeader = (
    <div className="flex items-center gap-2">
      <ConnectionsIcon className="w-3.5 h-3.5 shrink-0" />
      <span className="text-sm font-medium">{headerLabel}</span>
    </div>
  );

  const popoverBody = (
    <div className="space-y-1 text-muted-foreground text-xs">
      {totalDeclared > 0 && (
        <>
          <p>
            {unmet > 0
              ? `${unmet} required platform${plural(unmet)} not yet connected — the agent runs in knowledge mode until then.`
              : 'All required platforms connected.'}
          </p>
          <div className="pt-1 space-y-0.5">
            {gaps.map((gap: CapabilityGap) => (
              <div key={gap.capability} className="flex justify-between items-center">
                <span className="capitalize">{gap.requires_platform}</span>
                {/* A missing required platform is a SOFT condition (degrades
                    to knowledge mode) — render it neutral/muted, not the
                    amber error tone (operator-flagged 2026-06-23). */}
                <span className={gap.connected ? 'text-emerald-600' : 'text-muted-foreground'}>
                  {gap.connected ? '● connected' : '○ not connected'}
                </span>
              </div>
            ))}
          </div>
        </>
      )}

      {totalDeclared === 0 && connectedPlatforms.length === 0 && (
        <p>
          {state.active_program_slug
            ? 'Active program declares no platform requirements.'
            : 'No active program — workspace runs in knowledge mode.'}
        </p>
      )}

      {/* Connected-but-not-required — the inventory the program doesn't
          demand. Shown after any required rows so the header reflects what
          the Connectors pane shows. */}
      {extraConnected.length > 0 && (
        <div className={totalDeclared > 0 ? 'pt-2 mt-1 border-t border-border/40' : ''}>
          {totalDeclared > 0 && (
            <p className="pb-1">Connected, not required by this program:</p>
          )}
          {totalDeclared === 0 && (
            <p className="pb-1">
              {state.active_program_slug
                ? 'Active program requires no platforms. Connected anyway:'
                : 'No active program. Connected platforms:'}
            </p>
          )}
          <div className="space-y-0.5">
            {extraConnected.map((platform) => (
              <div key={platform} className="flex justify-between items-center">
                <span className="capitalize">{platform}</span>
                <span className="text-emerald-600">● connected</span>
              </div>
            ))}
          </div>
        </div>
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
