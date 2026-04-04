'use client';

/**
 * AgentTreeNav — Left panel flat roster for the agents surface.
 *
 * SURFACE-ARCHITECTURE.md v3: Flat agent list (no tree expansion).
 * Three sections: domain stewards, synthesizers, platform bots.
 * Each agent shows domain/class + task count. Click = select.
 * Tasks are NOT children here — they appear as cards in the center panel.
 */

import { Circle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Agent, Task } from '@/types';

interface AgentTreeNavProps {
  agents: Agent[];
  tasks: Task[];
  selectedAgentId: string | null;
  filter: string | null;
  onFilterChange: (filter: string | null) => void;
  onSelectAgent: (agentId: string) => void;
  busy?: boolean;
}

/** Get agent slug for task matching */
function getAgentSlug(agent: Agent): string {
  return agent.slug || agent.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
}

/** Count tasks for an agent */
function countTasks(agent: Agent, tasks: Task[]): number {
  const slug = getAgentSlug(agent);
  return tasks.filter(t => t.agent_slugs?.includes(slug)).length;
}

/** Check if agent has any active tasks */
function hasActiveTasks(agent: Agent, tasks: Task[]): boolean {
  const slug = getAgentSlug(agent);
  return tasks.some(t => t.agent_slugs?.includes(slug) && t.status === 'active');
}

/** Check if agent has any paused tasks */
function hasPausedTasks(agent: Agent, tasks: Task[]): boolean {
  const slug = getAgentSlug(agent);
  return tasks.some(t => t.agent_slugs?.includes(slug) && t.status === 'paused');
}

const CLASS_ORDER = ['domain-steward', 'synthesizer', 'platform-bot'] as const;
const CLASS_LABELS: Record<string, string> = {
  'domain-steward': 'Domain Stewards',
  'synthesizer': 'Synthesizers',
  'platform-bot': 'Platform Bots',
};

/** Metadata line: domain or class label + task count */
function getMetaLine(agent: Agent, taskCount: number): string {
  const domain = agent.context_domain;
  const cls = agent.agent_class || 'domain-steward';
  const domainLabel = domain ? `${domain}/` : cls === 'synthesizer' ? 'synthesizer' : '';
  const taskLabel = taskCount === 1 ? '1 task' : `${taskCount} tasks`;
  return domainLabel ? `${domainLabel} · ${taskLabel}` : taskLabel;
}

export function AgentTreeNav({
  agents,
  tasks,
  selectedAgentId,
  filter,
  onFilterChange,
  onSelectAgent,
}: AgentTreeNavProps) {
  // Filter
  const filtered = filter === 'active'
    ? agents.filter(a => hasActiveTasks(a, tasks))
    : filter === 'dormant'
    ? agents.filter(a => !hasActiveTasks(a, tasks))
    : agents;

  // Group by class
  const grouped = CLASS_ORDER.map(cls => ({
    cls,
    label: CLASS_LABELS[cls],
    agents: filtered.filter(a => (a.agent_class || 'domain-steward') === cls),
  })).filter(g => g.agents.length > 0);

  // Counts
  const activeCount = agents.filter(a => hasActiveTasks(a, tasks)).length;
  const dormantCount = agents.length - activeCount;

  return (
    <div className="flex flex-col h-full text-sm">
      {/* Filter pills */}
      <div className="flex gap-1 px-3 py-2 border-b border-border shrink-0">
        {[
          { key: null, label: 'All', count: agents.length },
          { key: 'active', label: 'Active', count: activeCount },
          { key: 'dormant', label: 'Dormant', count: dormantCount },
        ].map(f => (
          <button
            key={f.key ?? 'all'}
            onClick={() => onFilterChange(f.key)}
            className={cn(
              'px-2 py-0.5 text-[11px] font-medium rounded-full transition-colors',
              filter === f.key
                ? 'bg-primary/10 text-primary'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            {f.label} {f.count > 0 && <span className="opacity-50">{f.count}</span>}
          </button>
        ))}
      </div>

      {/* Agent list */}
      <div className="flex-1 overflow-y-auto py-1">
        {grouped.map(group => (
          <div key={group.cls}>
            {/* Section label */}
            <div className="px-3 pt-3 pb-1">
              <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
                {group.label}
              </span>
            </div>

            {group.agents.map(agent => {
              const isSelected = agent.id === selectedAgentId;
              const taskCount = countTasks(agent, tasks);
              const active = hasActiveTasks(agent, tasks);
              const paused = hasPausedTasks(agent, tasks);

              const statusColor = active
                ? 'fill-green-500 text-green-500'
                : paused
                ? 'fill-amber-500 text-amber-500'
                : 'text-muted-foreground/30';

              return (
                <button
                  key={agent.id}
                  onClick={() => onSelectAgent(agent.id)}
                  className={cn(
                    'w-full flex items-start gap-2 px-3 py-2 text-left rounded-sm hover:bg-accent transition-colors',
                    isSelected && 'bg-accent/50'
                  )}
                >
                  <Circle className={cn('w-2 h-2 shrink-0 mt-1.5', statusColor)} />
                  <div className="min-w-0 flex-1">
                    <p className={cn('text-sm truncate', isSelected ? 'font-medium' : '')}>{agent.title}</p>
                    <p className="text-[11px] text-muted-foreground/50 truncate">
                      {getMetaLine(agent, taskCount)}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        ))}

        {filtered.length === 0 && (
          <div className="px-3 py-4 text-center text-sm text-muted-foreground">
            No matching agents
          </div>
        )}
      </div>
    </div>
  );
}
