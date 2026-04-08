'use client';

import { AlertCircle, CheckCircle2 } from 'lucide-react';
import type { Agent, Task } from '@/types';

interface ContextGapsArtifactProps {
  agents: Agent[];
  tasks: Task[];
  loading: boolean;
}

export function ContextGapsArtifact({ agents, tasks, loading }: ContextGapsArtifactProps) {
  const domainAgents = agents.filter((agent) => (agent.agent_class || 'domain-steward') === 'domain-steward');
  const agentsWithoutTasks = domainAgents.filter((agent) => {
    const slug = agent.slug || agent.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
    return !tasks.some((task) => task.agent_slugs?.includes(slug));
  });
  // ADR-166: task_class → output_kind. "context" → "accumulates_context".
  const contextTasks = tasks.filter((task) => task.output_kind === 'accumulates_context').length;

  if (loading) {
    return (
      <div className="px-5 py-8 text-sm text-muted-foreground">
        Checking context...
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground/60">Coverage</p>
        <div className="mt-2 grid grid-cols-2 gap-2">
          <div className="rounded-lg border border-border/70 bg-muted/20 p-3">
            <p className="text-xl font-semibold">{domainAgents.length}</p>
            <p className="text-xs text-muted-foreground">domain agents</p>
          </div>
          <div className="rounded-lg border border-border/70 bg-muted/20 p-3">
            <p className="text-xl font-semibold">{contextTasks}</p>
            <p className="text-xs text-muted-foreground">context tasks</p>
          </div>
        </div>
      </div>

      {agentsWithoutTasks.length > 0 ? (
        <div>
          <div className="mb-2 flex items-center gap-1.5 text-sm font-medium">
            <AlertCircle className="h-4 w-4 text-amber-500" />
            Needs setup
          </div>
          <div className="space-y-1.5">
            {agentsWithoutTasks.slice(0, 5).map((agent) => (
              <div key={agent.id} className="rounded-md border border-border/70 px-3 py-2 text-sm text-muted-foreground">
                <span className="font-medium text-foreground">{agent.title}</span> has no assigned work yet.
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="rounded-lg border border-border/70 bg-muted/20 p-3">
          <div className="flex items-center gap-1.5 text-sm font-medium">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            Coverage looks ready
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            TP has at least one work path for every domain agent.
          </p>
        </div>
      )}
    </div>
  );
}
