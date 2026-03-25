'use client';

/**
 * Tasks List — ADR-139
 *
 * Browse all tasks with status, cadence, last output, assigned agent.
 * Each row links to /tasks/[slug].
 */

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  ListChecks,
  Loader2,
  ChevronRight,
  Clock,
  Play,
  Pause,
  CheckCircle2,
  Archive,
} from 'lucide-react';
import type { Task } from '@/types';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

const STATUS_CONFIG = {
  active: { icon: Play, color: 'text-green-500', bg: 'bg-green-500', label: 'Active' },
  paused: { icon: Pause, color: 'text-amber-500', bg: 'bg-amber-500', label: 'Paused' },
  completed: { icon: CheckCircle2, color: 'text-blue-500', bg: 'bg-blue-500', label: 'Completed' },
  archived: { icon: Archive, color: 'text-gray-400', bg: 'bg-gray-400', label: 'Archived' },
};

export default function TasksListPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string | null>(null);

  useEffect(() => {
    api.tasks.list()
      .then(setTasks)
      .catch(() => setTasks([]))
      .finally(() => setLoading(false));
  }, []);

  const filtered = filter
    ? tasks.filter(t => t.status === filter)
    : tasks;

  const statusCounts = {
    all: tasks.length,
    active: tasks.filter(t => t.status === 'active').length,
    paused: tasks.filter(t => t.status === 'paused').length,
    completed: tasks.filter(t => t.status === 'completed').length,
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <ListChecks className="w-6 h-6 text-muted-foreground" />
          <h1 className="text-2xl font-medium">Tasks</h1>
        </div>
        <p className="text-sm text-muted-foreground">
          Your defined work — what gets produced, on what cadence, delivered where.
          Each task is assigned to an agent that handles the full thinking chain.
        </p>
      </div>

      {/* Filters */}
      <div className="flex gap-2 mb-6">
        {[
          { key: null, label: 'All', count: statusCounts.all },
          { key: 'active', label: 'Active', count: statusCounts.active },
          { key: 'paused', label: 'Paused', count: statusCounts.paused },
          { key: 'completed', label: 'Completed', count: statusCounts.completed },
        ].map(f => (
          <button
            key={f.key ?? 'all'}
            onClick={() => setFilter(f.key)}
            className={cn(
              'px-3 py-1.5 text-xs font-medium rounded-full border transition-colors',
              filter === f.key
                ? 'border-primary bg-primary/10 text-primary'
                : 'border-border text-muted-foreground hover:text-foreground hover:border-foreground/30'
            )}
          >
            {f.label} {f.count > 0 && <span className="ml-1 opacity-60">{f.count}</span>}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16">
          <ListChecks className="w-10 h-10 text-muted-foreground/20 mx-auto mb-3" />
          <p className="text-sm text-muted-foreground mb-1">
            {tasks.length === 0 ? 'No tasks yet' : 'No matching tasks'}
          </p>
          <p className="text-xs text-muted-foreground/60">
            {tasks.length === 0
              ? 'Go to the workfloor and tell the orchestrator what work you need done.'
              : 'Try a different filter.'}
          </p>
          {tasks.length === 0 && (
            <Link
              href="/workfloor"
              className="inline-block mt-4 px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              Go to workfloor
            </Link>
          )}
        </div>
      ) : (
        <div className="border border-border rounded-xl overflow-hidden divide-y divide-border">
          {filtered.map(task => {
            const status = STATUS_CONFIG[task.status] || STATUS_CONFIG.active;
            return (
              <Link
                key={task.id}
                href={`/tasks/${task.slug}`}
                className="flex items-center justify-between p-4 hover:bg-muted/50 transition-colors group"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2.5 mb-1">
                    <span className={cn('w-2 h-2 rounded-full shrink-0', status.bg)} />
                    <span className="text-sm font-medium truncate">{task.title}</span>
                    <span className={cn('text-[10px] uppercase tracking-wider font-medium', status.color)}>
                      {status.label}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 ml-[18px] text-xs text-muted-foreground">
                    {task.schedule && (
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {task.schedule}
                      </span>
                    )}
                    {task.last_run_at && (
                      <span>Last: {formatRelativeTime(task.last_run_at)}</span>
                    )}
                    {task.agent_slugs?.[0] && (
                      <span className="text-muted-foreground/60">Agent: {task.agent_slugs[0]}</span>
                    )}
                    {task.delivery && (
                      <span className="text-muted-foreground/60">{task.delivery}</span>
                    )}
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-muted-foreground/30 group-hover:text-foreground transition-colors shrink-0 ml-4" />
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
