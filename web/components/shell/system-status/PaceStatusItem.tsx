'use client';

/**
 * PaceStatusItem — pace + wake-queue depth chip in the agent-OS
 * menu-bar status cluster (ADR-297 D20, slot 2).
 *
 * Consumes api.cockpit.pace() (ADR-298 D2, ADR-300). Read-only popover;
 * mutations happen on the /pace atomic surface (ADR-300 D1).
 *
 * Replaces PaceBadge (deleted in same commit) — the pace indicator
 * moves from /cadence-only chrome to kernel chrome (every surface).
 *
 * Per ADR-298 D2 the queue itself is NOT operator-readable substrate;
 * only the aggregate depth is surfaced.
 */

import { useEffect, useState } from 'react';
import { Activity, Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import { StatusItemPopover, type StatusTone } from './StatusItemPopover';

type PaceKind = 'hourly' | 'daily' | 'weekly' | 'continuous';

interface PaceState {
  pace_kind: PaceKind | null;
  pace_every_iso: string | null;
  fires_per_day_cap: number | null;
  paced_lane_depth: number;
  live_lane_depth: number;
}

const PACE_LABEL: Record<PaceKind, string> = {
  hourly: 'Hourly',
  daily: 'Daily',
  weekly: 'Weekly',
  continuous: 'Continuous',
};

const PACE_DESCRIPTION: Record<PaceKind, string> = {
  hourly: 'Reviewer wakes ~168×/day. Higher cost; supports time-sensitive workflows.',
  daily: 'Reviewer wakes ~24×/day. Default for most operators.',
  weekly: 'Reviewer wakes ~7×/week. Lowest cost; longest latency for paced work.',
  continuous: 'No drain cap — paced lane drains as fast as it accumulates. Highest cost ceiling.',
};

const REFRESH_INTERVAL_MS = 30_000;

export function PaceStatusItem() {
  const [state, setState] = useState<PaceState | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const fetchPace = async () => {
      try {
        const data = await api.cockpit.pace();
        if (!cancelled) {
          setState(data);
        }
      } catch {
        // Soft-fail; popover shows skeleton-state
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchPace();
    const interval = setInterval(fetchPace, REFRESH_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (loading) {
    return (
      <div className="w-8 h-8 flex items-center justify-center text-muted-foreground" aria-hidden>
        <Loader2 className="w-3 h-3 animate-spin" />
      </div>
    );
  }

  const kind = state?.pace_kind ?? null;
  const totalPending = (state?.paced_lane_depth ?? 0) + (state?.live_lane_depth ?? 0);
  const tone: StatusTone = !kind ? 'muted' : totalPending > 0 ? 'ok' : 'muted';

  const kindLabel = kind ? PACE_LABEL[kind] : 'Not set';
  const tooltip = kind
    ? `Pace: ${kindLabel}${totalPending > 0 ? ` · ${totalPending} pending` : ''}`
    : 'Pace not set';

  const popoverHeader = (
    <div className="flex items-center gap-2">
      <Activity className="w-3.5 h-3.5 shrink-0" />
      <span className="text-sm font-medium">
        {kindLabel}
        {totalPending > 0 && (
          <span className="text-muted-foreground"> · {totalPending} pending</span>
        )}
      </span>
    </div>
  );

  const popoverBody = (
    <div className="space-y-1 text-muted-foreground text-xs">
      <p>{kind ? PACE_DESCRIPTION[kind] : 'Operator has not declared a pace yet.'}</p>
      {state && kind && (
        <div className="pt-1 space-y-0.5">
          <div className="flex justify-between">
            <span>Paced lane</span>
            <span className="font-mono">{state.paced_lane_depth}</span>
          </div>
          <div className="flex justify-between">
            <span>Live lane</span>
            <span className="font-mono">{state.live_lane_depth}</span>
          </div>
          {state.fires_per_day_cap !== null && (
            <div className="flex justify-between">
              <span>Cron-tick cap</span>
              <span className="font-mono">≤ {state.fires_per_day_cap.toFixed(1)}/day</span>
            </div>
          )}
        </div>
      )}
    </div>
  );

  return (
    <StatusItemPopover
      icon={Activity}
      tooltip={tooltip}
      tone={tone}
      ariaLabel="Pace and wake queue"
      popoverHeader={popoverHeader}
      popoverBody={popoverBody}
      footerTarget={{ kind: 'surface', slug: 'pace' }}
      footerLabel="Pace Settings"
    />
  );
}
