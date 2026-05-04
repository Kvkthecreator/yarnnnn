'use client';

/**
 * OperationsTab — YARNNN detail Operations tab.
 *
 * Surfaces the operational heartbeat per ADR-249 D5: the set of active
 * recurrences that constitute the Operator ↔ System loop, their cadence,
 * and last/next run timing.
 *
 * Read-only. Editing a recurrence's schedule routes to chat (YARNNN
 * adjusts the YAML) per ADR-231 + ADR-206 D6 CRUD split.
 * Row click navigates to /work?task={slug} for full detail.
 */

import { Activity, Clock, ArrowRight } from 'lucide-react';
import Link from 'next/link';
import { useAgentsAndRecurrences } from '@/hooks/useAgentsAndRecurrences';
import { humanizeSchedule } from '@/lib/schedule';
import { formatRelativeTime } from '@/lib/formatting';
import { WORK_ROUTE } from '@/lib/routes';
import type { Recurrence } from '@/types';

const SHAPE_LABELS: Record<string, string> = {
  deliverable: 'Report',
  accumulation: 'Tracker',
  action: 'Action',
  maintenance: 'System',
};

function cadenceLabel(r: Recurrence): string {
  if (!r.schedule) return r.shape === 'action' ? 'Reactive' : 'On demand';
  return humanizeSchedule(r.schedule);
}

function heartbeatSummary(active: Recurrence[]): string {
  if (active.length === 0) return 'No active recurrences';
  const scheduled = active.filter((r) => r.schedule);
  if (scheduled.length === 0) return `${active.length} reactive`;
  return `${active.length} active · ${scheduled.length} scheduled`;
}

export function OperationsTab() {
  const { tasks, loading } = useAgentsAndRecurrences();

  const active = tasks.filter((r) => r.status === 'active' && !r.paused);
  const paused = tasks.filter((r) => r.paused);

  if (loading) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        Loading…
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Heartbeat summary */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Activity className="w-4 h-4 shrink-0" />
        <span>{heartbeatSummary(active)}</span>
      </div>

      {/* Active recurrences */}
      {active.length === 0 ? (
        <div className="rounded-lg border border-border/50 px-4 py-6 text-center text-sm text-muted-foreground">
          No active recurrences. Ask YARNNN in chat to set one up.
        </div>
      ) : (
        <div className="divide-y divide-border/50 rounded-lg border border-border/50">
          {active.map((r) => (
            <Link
              key={r.id}
              href={`${WORK_ROUTE}?task=${r.slug}`}
              className="flex items-center justify-between gap-4 px-4 py-3 hover:bg-muted/40 transition-colors group"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium truncate">{r.title}</span>
                  {r.shape && (
                    <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">
                      {SHAPE_LABELS[r.shape] ?? r.shape}
                    </span>
                  )}
                </div>
                <div className="mt-0.5 flex items-center gap-3 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {cadenceLabel(r)}
                  </span>
                  {r.last_run_at && (
                    <span>Last: {formatRelativeTime(r.last_run_at)}</span>
                  )}
                  {r.next_run_at && (
                    <span>Next: {formatRelativeTime(r.next_run_at)}</span>
                  )}
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-muted-foreground/40 shrink-0 group-hover:text-muted-foreground transition-colors" />
            </Link>
          ))}
        </div>
      )}

      {/* Paused recurrences */}
      {paused.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground/60">
            Paused
          </p>
          <div className="divide-y divide-border/50 rounded-lg border border-border/50 opacity-60">
            {paused.map((r) => (
              <Link
                key={r.id}
                href={`${WORK_ROUTE}?task=${r.slug}`}
                className="flex items-center justify-between gap-4 px-4 py-3 hover:bg-muted/40 transition-colors group"
              >
                <div className="min-w-0 flex-1">
                  <span className="text-sm font-medium truncate">{r.title}</span>
                  <div className="mt-0.5 text-xs text-muted-foreground">
                    {cadenceLabel(r)}
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-muted-foreground/40 shrink-0 group-hover:text-muted-foreground transition-colors" />
              </Link>
            ))}
          </div>
        </div>
      )}

      <p className="text-xs text-muted-foreground/50">
        To change a recurrence&apos;s schedule, ask YARNNN in chat.
      </p>
    </div>
  );
}
