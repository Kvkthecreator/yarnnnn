'use client';

/**
 * WorkspaceDashboard — Main panel default view (replaces isometric room)
 *
 * Shows at-a-glance workspace status:
 * - Upcoming scheduled runs
 * - Recent task activity
 * - Context domain health
 */

import { useMemo } from 'react';
import { Clock, CheckCircle, AlertCircle, FolderOpen, Play, Calendar } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Task, Agent } from '@/types';

interface WorkspaceDashboardProps {
  tasks: Task[];
  agents: Agent[];
}

export function WorkspaceDashboard({ tasks, agents }: WorkspaceDashboardProps) {
  const activeTasks = tasks.filter(t => t.status === 'active');
  const activeAgents = agents.filter(a => a.status !== 'archived');

  // Sort tasks by next_run_at for upcoming view
  const upcoming = useMemo(() => {
    return activeTasks
      .filter(t => t.next_run_at)
      .sort((a, b) => (a.next_run_at || '').localeCompare(b.next_run_at || ''))
      .slice(0, 5);
  }, [activeTasks]);

  // Sort by last_run_at for recent activity
  const recent = useMemo(() => {
    return activeTasks
      .filter(t => t.last_run_at)
      .sort((a, b) => (b.last_run_at || '').localeCompare(a.last_run_at || ''))
      .slice(0, 5);
  }, [activeTasks]);

  // Empty state
  if (activeTasks.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center max-w-sm">
          <FolderOpen className="w-10 h-10 text-muted-foreground/20 mx-auto mb-3" />
          <h3 className="text-sm font-medium mb-1">No tasks yet</h3>
          <p className="text-xs text-muted-foreground">
            Create your first task to start tracking and producing outputs.
            Use the chat to tell TP what you need.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-2xl mx-auto">
      {/* Header */}
      <div>
        <h2 className="text-lg font-medium">Workspace</h2>
        <p className="text-xs text-muted-foreground">
          {activeTasks.length} active task{activeTasks.length !== 1 ? 's' : ''} · {activeAgents.length} agent{activeAgents.length !== 1 ? 's' : ''}
        </p>
      </div>

      {/* Upcoming Runs */}
      {upcoming.length > 0 && (
        <section>
          <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5" />
            Upcoming
          </h3>
          <div className="space-y-1">
            {upcoming.map(task => (
              <a
                key={task.slug}
                href={`/tasks/${task.slug}`}
                className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-muted/50 transition-colors group"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <div className={cn(
                    "w-1.5 h-1.5 rounded-full shrink-0",
                    task.status === 'active' ? 'bg-green-500' : 'bg-gray-400',
                  )} />
                  <span className="text-sm truncate group-hover:text-foreground">{task.title}</span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {task.schedule && (
                    <span className="text-[10px] text-muted-foreground/60">{task.schedule}</span>
                  )}
                  {task.next_run_at && (
                    <span className="text-[10px] text-muted-foreground">
                      {formatRelative(task.next_run_at)}
                    </span>
                  )}
                </div>
              </a>
            ))}
          </div>
        </section>
      )}

      {/* Recent Activity */}
      {recent.length > 0 && (
        <section>
          <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <CheckCircle className="w-3.5 h-3.5" />
            Recent
          </h3>
          <div className="space-y-1">
            {recent.map(task => (
              <a
                key={task.slug}
                href={`/tasks/${task.slug}`}
                className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-muted/50 transition-colors group"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <CheckCircle className="w-3.5 h-3.5 text-green-500/60 shrink-0" />
                  <span className="text-sm truncate group-hover:text-foreground">{task.title}</span>
                </div>
                {task.last_run_at && (
                  <span className="text-[10px] text-muted-foreground shrink-0">
                    {formatRelative(task.last_run_at)}
                  </span>
                )}
              </a>
            ))}
          </div>
        </section>
      )}

      {/* Quick Stats */}
      <section>
        <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
          Overview
        </h3>
        <div className="grid grid-cols-3 gap-3">
          <div className="p-3 rounded-lg bg-muted/30 border border-border/30">
            <p className="text-2xl font-semibold">{activeTasks.length}</p>
            <p className="text-[10px] text-muted-foreground">Active Tasks</p>
          </div>
          <div className="p-3 rounded-lg bg-muted/30 border border-border/30">
            <p className="text-2xl font-semibold">{activeAgents.length}</p>
            <p className="text-[10px] text-muted-foreground">Agents</p>
          </div>
          <div className="p-3 rounded-lg bg-muted/30 border border-border/30">
            <p className="text-2xl font-semibold">{recent.length}</p>
            <p className="text-[10px] text-muted-foreground">Recent Runs</p>
          </div>
        </div>
      </section>
    </div>
  );
}

// =============================================================================
// Helpers
// =============================================================================

function formatRelative(isoDate: string): string {
  try {
    const date = new Date(isoDate);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMin = Math.floor(Math.abs(diffMs) / 60000);
    const future = diffMs < 0;

    if (diffMin < 1) return future ? 'now' : 'just now';
    if (diffMin < 60) return future ? `in ${diffMin}m` : `${diffMin}m ago`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return future ? `in ${diffHours}h` : `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return future ? `in ${diffDays}d` : `${diffDays}d ago`;
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  } catch {
    return isoDate.slice(0, 10);
  }
}
