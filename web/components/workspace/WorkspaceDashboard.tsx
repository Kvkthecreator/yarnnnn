'use client';

/**
 * WorkspaceDashboard — Live activity feed + compact isometric room
 *
 * Activity feed on top: running tasks, recent completions, upcoming runs.
 * Conveys "things are working without you" — Roomba effect.
 *
 * Compact isometric room below: ambient agent presence.
 */

import { useMemo } from 'react';
import { Loader2, CheckCircle2, Clock, FolderOpen } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Recurrence, Agent } from '@/types';

interface WorkspaceDashboardProps {
  tasks: Recurrence[];
  agents: Agent[];
  isometricRoom?: React.ReactNode;  // Passed from parent
}

export function WorkspaceDashboard({ tasks, agents, isometricRoom }: WorkspaceDashboardProps) {
  const activeTasks = tasks.filter(t => t.status === 'active');

  // Build unified activity list sorted by relevance
  const activityItems = useMemo(() => {
    const items: ActivityItem[] = [];

    for (const task of activeTasks) {
      // Check if task is currently running (next_run_at is in the past but last_run_at is older)
      const nextRun = task.next_run_at ? new Date(task.next_run_at) : null;
      const lastRun = task.last_run_at ? new Date(task.last_run_at) : null;
      const now = new Date();

      if (nextRun && nextRun <= now && (!lastRun || lastRun < nextRun)) {
        items.push({ task, status: 'running', sortKey: 0, time: nextRun });
      } else if (lastRun) {
        const ageMs = now.getTime() - lastRun.getTime();
        items.push({ task, status: 'completed', sortKey: 1 + ageMs / 1e10, time: lastRun });
      }

      if (nextRun && nextRun > now) {
        items.push({ task, status: 'upcoming', sortKey: 2 + (nextRun.getTime() - now.getTime()) / 1e10, time: nextRun });
      }
    }

    items.sort((a, b) => a.sortKey - b.sortKey);
    return items.slice(0, 8);
  }, [activeTasks]);

  // Empty state
  if (activeTasks.length === 0) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center max-w-xs">
            <FolderOpen className="w-8 h-8 text-muted-foreground/15 mx-auto mb-2" />
            <p className="text-sm text-muted-foreground mb-1">No recurrences yet</p>
            <p className="text-xs text-muted-foreground/60">
              Tell YARNNN what you need — "track my competitors" or "help me get set up"
            </p>
          </div>
        </div>
        {isometricRoom && (
          <div className="h-[200px] shrink-0 border-t border-border/20">
            {isometricRoom}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Activity Feed — information first */}
      <div className="flex-1 overflow-auto">
        <div className="p-4 space-y-0.5">
          {activityItems.map((item, i) => (
            <a
              key={`${item.task.slug}-${item.status}`}
              href={`/tasks/${item.task.slug}`}
              className="flex items-center gap-3 py-2.5 px-3 rounded-lg hover:bg-muted/50 transition-colors group"
            >
              {/* Status indicator */}
              <div className="shrink-0">
                {item.status === 'running' && (
                  <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                )}
                {item.status === 'completed' && (
                  <CheckCircle2 className="w-4 h-4 text-green-500/70" />
                )}
                {item.status === 'upcoming' && (
                  <Clock className="w-4 h-4 text-muted-foreground/40" />
                )}
              </div>

              {/* Task info */}
              <div className="flex-1 min-w-0">
                <p className={cn(
                  "text-sm truncate",
                  item.status === 'running' && "font-medium text-foreground",
                  item.status === 'completed' && "text-foreground/80",
                  item.status === 'upcoming' && "text-muted-foreground/60",
                )}>
                  {item.task.title}
                </p>
                {item.status === 'running' && (
                  <p className="text-[10px] text-blue-500/70">running now...</p>
                )}
              </div>

              {/* Time + schedule */}
              <div className="shrink-0 text-right">
                <p className="text-[10px] text-muted-foreground/50">
                  {item.status === 'running' ? '' :
                   item.status === 'completed' ? formatRelative(item.time) :
                   formatRelative(item.time)}
                </p>
                {item.task.schedule && item.status !== 'running' && (
                  <p className="text-[9px] text-muted-foreground/30">{item.task.schedule}</p>
                )}
              </div>
            </a>
          ))}
        </div>
      </div>

      {/* Compact Isometric Room — ambient presence */}
      {isometricRoom && (
        <div className="h-[180px] shrink-0 border-t border-border/10 opacity-80">
          {isometricRoom}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Types + Helpers
// =============================================================================

interface ActivityItem {
  task: Recurrence;
  status: 'running' | 'completed' | 'upcoming';
  sortKey: number;
  time: Date;
}

function formatRelative(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const future = diffMs < 0;
  const absDiffMin = Math.floor(Math.abs(diffMs) / 60000);

  if (absDiffMin < 1) return future ? 'now' : 'just now';
  if (absDiffMin < 60) return future ? `in ${absDiffMin}m` : `${absDiffMin}m ago`;
  const hours = Math.floor(absDiffMin / 60);
  if (hours < 24) return future ? `in ${hours}h` : `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return future ? `in ${days}d` : `${days}d ago`;
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}
