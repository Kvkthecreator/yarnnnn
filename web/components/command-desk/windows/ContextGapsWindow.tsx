'use client';

import { AlertCircle, CheckCircle2 } from 'lucide-react';
import type { Agent, Task } from '@/types';

interface ContextGapsWindowProps {
  agents: Agent[];
  tasks: Task[];
  loading: boolean;
}

export function ContextGapsWindow({ agents, tasks, loading }: ContextGapsWindowProps) {
  const domainAgents = agents.filter((agent) => (agent.agent_class || 'domain-steward') === 'domain-steward');
  const agentsWithoutTasks = domainAgents.filter((agent) => {
    const slug = agent.slug || agent.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
    return !tasks.some((task) => task.agent_slugs?.includes(slug));
  });
  const contextTasks = tasks.filter((task) => task.task_class === 'context').length;

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center px-5 py-8 text-xs text-muted-foreground">
        Checking workspace context...
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      <div>
        <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground/60">Coverage</p>
        <div className="mt-2 grid grid-cols-2 gap-2">
          <div className="rounded-lg border border-border/70 bg-muted/20 p-3">
            <p className="text-lg font-semibold">{domainAgents.length}</p>
            <p className="text-[10px] text-muted-foreground">domain agents</p>
          </div>
          <div className="rounded-lg border border-border/70 bg-muted/20 p-3">
            <p className="text-lg font-semibold">{contextTasks}</p>
            <p className="text-[10px] text-muted-foreground">context tasks</p>
          </div>
        </div>
      </div>

      {agentsWithoutTasks.length > 0 ? (
        <div>
          <div className="mb-2 flex items-center gap-1.5 text-xs font-medium">
            <AlertCircle className="h-3.5 w-3.5 text-amber-500" />
            Needs setup
          </div>
          <div className="space-y-1.5">
            {agentsWithoutTasks.slice(0, 5).map((agent) => (
              <div key={agent.id} className="rounded-md border border-border/70 px-2.5 py-2 text-xs text-muted-foreground">
                <span className="font-medium text-foreground">{agent.title}</span> has no assigned work yet.
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="rounded-lg border border-border/70 bg-muted/20 p-3">
          <div className="flex items-center gap-1.5 text-xs font-medium">
            <CheckCircle2 className="h-3.5 w-3.5 text-green-600" />
            Workspace coverage looks ready
          </div>
          <p className="mt-1 text-[11px] text-muted-foreground">
            TP has at least one work path for every domain agent.
          </p>
        </div>
      )}
    </div>
  );
}
