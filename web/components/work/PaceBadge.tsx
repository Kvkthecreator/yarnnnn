/**
 * PaceBadge — operator-facing pace + queue-depth badge (ADR-298 Phase 5).
 *
 * Surfaces the operator's declared workspace pace (Trigger-dimension dial
 * of the Pace + Autonomy + Persona trifecta per ADR-298 D11) alongside
 * the live wake_queue depths so the operator can see at a glance:
 *
 *   "What rhythm does this agent work at, and how much is pending?"
 *
 * Self-contained: fetches from /api/cockpit/pace on mount + on a refresh
 * tick. Drop-in anywhere in the cockpit; no surface coupling.
 *
 * Per ADR-298 D2 the queue itself is NOT operator-readable substrate
 * (operators read configuration via _pace.yaml, outcomes via the feed +
 * execution_events, watch-state via standing_intent.md). Only the
 * aggregate `queue_depth` is surfaced — implementation detail of "things
 * about to happen" stays opaque.
 */

'use client';

import { useEffect, useState } from 'react';
import { Activity, Loader2 } from 'lucide-react';

import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';

type PaceKind = 'hourly' | 'daily' | 'weekly' | 'continuous';

interface PaceState {
  pace_kind: PaceKind | null;
  pace_every_iso: string | null;
  fires_per_day_cap: number | null;
  paced_lane_depth: number;
  live_lane_depth: number;
}

interface PaceBadgeProps {
  className?: string;
  /** ms between auto-refresh polls. Default 30s. Set to 0 to disable. */
  refreshIntervalMs?: number;
}

const PACE_LABEL: Record<PaceKind, string> = {
  hourly: 'Hourly',
  daily: 'Daily',
  weekly: 'Weekly',
  continuous: 'Continuous',
};

const PACE_TINT: Record<PaceKind, string> = {
  hourly: 'bg-orange-500/10 text-orange-700',
  daily: 'bg-blue-500/10 text-blue-700',
  weekly: 'bg-emerald-500/10 text-emerald-700',
  continuous: 'bg-purple-500/10 text-purple-700',
};

export function PaceBadge({ className, refreshIntervalMs = 30_000 }: PaceBadgeProps) {
  const [state, setState] = useState<PaceState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const fetchPace = async () => {
      try {
        const data = await api.cockpit.pace();
        if (!cancelled) {
          setState(data);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'pace fetch failed');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    fetchPace();

    if (refreshIntervalMs > 0) {
      const interval = setInterval(fetchPace, refreshIntervalMs);
      return () => {
        cancelled = true;
        clearInterval(interval);
      };
    }

    return () => {
      cancelled = true;
    };
  }, [refreshIntervalMs]);

  if (loading) {
    return (
      <span className={cn('inline-flex items-center gap-1.5 text-xs text-muted-foreground', className)}>
        <Loader2 className="h-3 w-3 animate-spin" />
        <span>Pace…</span>
      </span>
    );
  }

  if (error || !state) {
    // Soft-fail — surface nothing operator-disruptive when the cockpit
    // backend is temporarily unreachable. Per ADR-298 D2 the queue is
    // transient compute; absence of badge data is not a substrate state.
    return null;
  }

  const totalPending = state.paced_lane_depth + state.live_lane_depth;
  const kind = state.pace_kind;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs font-medium',
        kind ? PACE_TINT[kind] : 'bg-slate-500/10 text-slate-600',
        className,
      )}
      title={
        kind
          ? `Workspace pace: ${PACE_LABEL[kind]}` +
            (state.pace_every_iso ? ` (every ${state.pace_every_iso})` : '') +
            (state.fires_per_day_cap !== null
              ? ` — drains ≤ ${state.fires_per_day_cap.toFixed(2)} cron-tick wake(s)/day`
              : ' — uncapped') +
            `\nPending: ${state.paced_lane_depth} paced · ${state.live_lane_depth} live`
          : 'No pace declared — paced lane uncapped (operator authoring _pace.yaml controls this)'
      }
    >
      <Activity className="h-3 w-3" />
      <span>{kind ? PACE_LABEL[kind] : 'No pace'}</span>
      {totalPending > 0 && (
        <span className="text-[10px] opacity-75">
          · {totalPending} pending
        </span>
      )}
    </span>
  );
}
