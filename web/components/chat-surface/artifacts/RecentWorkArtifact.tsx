'use client';

import { CheckCircle2, Clock3, PauseCircle } from 'lucide-react';
import { taskModeLabel, type Agent, type Task } from '@/types';
import { cn } from '@/lib/utils';

interface RecentWorkArtifactProps {
  agents: Agent[];
  tasks: Task[];
  loading: boolean;
}

function agentTitleForTask(task: Task, agents: Agent[]) {
  const slug = task.agent_slugs?.[0];
  return agents.find((agent) => agent.slug === slug)?.title || slug || 'TP';
}

function formatRelativeTime(value?: string) {
  if (!value) return null;
  const then = new Date(value).getTime();
  if (Number.isNaN(then)) return null;
  const diff = Date.now() - then;
  const future = diff < 0;
  const abs = Math.abs(diff);
  const mins = Math.floor(abs / 60000);
  if (mins < 1) return future ? 'soon' : 'just now';
  if (mins < 60) return future ? `in ${mins}m` : `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return future ? `in ${hours}h` : `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return future ? `in ${days}d` : `${days}d ago`;
}

export function RecentWorkArtifact({ agents, tasks, loading }: RecentWorkArtifactProps) {
  const visibleTasks = tasks
    .slice()
    .sort((a, b) => new Date(b.updated_at || b.created_at).getTime() - new Date(a.updated_at || a.created_at).getTime())
    .slice(0, 6);

  if (loading) {
    return (
      <div className="px-5 py-8 text-sm text-muted-foreground">
        Loading current work...
      </div>
    );
  }

  if (visibleTasks.length === 0) {
    return (
      <div className="px-5 py-8">
        <p className="text-sm font-medium">No work is running yet.</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Tell TP what you want watched, prepared, or produced.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2 p-4">
      {visibleTasks.map((task) => {
        const active = task.status === 'active';
        const completed = task.status === 'completed';
        const Icon = completed ? CheckCircle2 : active ? Clock3 : PauseCircle;
        const lastSignal = formatRelativeTime(task.last_run_at || task.updated_at);

        return (
          <div key={task.id} className="rounded-lg border border-border/70 bg-muted/20 p-3">
            <div className="flex items-start gap-2">
              <Icon className={cn('mt-0.5 h-4 w-4 shrink-0', active ? 'text-green-600' : 'text-muted-foreground')} />
              <div className="min-w-0 flex-1">
                <div className="flex min-w-0 items-center gap-2">
                  <p className="truncate text-sm font-medium">{task.title}</p>
                  <span className="shrink-0 rounded border border-border bg-background px-1.5 py-0.5 text-[10px] text-muted-foreground">
                    {taskModeLabel(task.mode)}
                  </span>
                </div>
                <p className="mt-1 truncate text-xs text-muted-foreground">
                  {agentTitleForTask(task, agents)}
                  {task.objective?.deliverable ? ` -> ${task.objective.deliverable}` : ''}
                </p>
              </div>
              {lastSignal && <span className="shrink-0 text-xs text-muted-foreground/60">{lastSignal}</span>}
            </div>
          </div>
        );
      })}
    </div>
  );
}
