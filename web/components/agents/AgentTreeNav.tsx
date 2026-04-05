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
  onSelectAgent: (agentId: string) => void;
}

/** Get agent slug for task matching */
function getAgentSlug(agent: Agent): string {
  return agent.slug || agent.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
}

/** Check if agent has any active tasks */
function hasActiveTasks(agent: Agent, tasks: Task[]): boolean {
  const slug = getAgentSlug(agent);
  return tasks.some(t => t.agent_slugs?.includes(slug) && t.status === 'active');
}

const CLASS_ORDER = ['domain-steward', 'synthesizer', 'platform-bot'] as const;
const CLASS_LABELS: Record<string, string> = {
  'domain-steward': 'Your Team',
  'synthesizer': 'Cross-Team',
  'platform-bot': 'Integrations',
};

/** Metadata line: domain + work rhythm (derived from most frequent task schedule) */
function getMetaLine(agent: Agent, agentTasks: Task[]): string {
  const domain = agent.context_domain;
  const cls = agent.agent_class || 'domain-steward';
  const domainLabel = domain ? `${domain}/` : cls === 'synthesizer' ? 'synthesizer' : '';

  const activeTasks = agentTasks.filter(t => t.status === 'active');
  const rhythm = activeTasks[0]?.schedule;
  const rhythmLabel = rhythm ? `works ${rhythm}` : agentTasks.length > 0 ? `${agentTasks.length} tasks` : '';

  return domainLabel && rhythmLabel ? `${domainLabel} · ${rhythmLabel}` : domainLabel || rhythmLabel || '';
}

export function AgentTreeNav({
  agents,
  tasks,
  selectedAgentId,
  onSelectAgent,
}: AgentTreeNavProps) {
  // Group by class
  const grouped = CLASS_ORDER.map(cls => ({
    cls,
    label: CLASS_LABELS[cls],
    agents: agents.filter(a => (a.agent_class || 'domain-steward') === cls),
  })).filter(g => g.agents.length > 0);

  return (
    <div className="flex flex-col h-full text-sm">
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
              const slug = getAgentSlug(agent);
              const agentTasks = tasks.filter(t => t.agent_slugs?.includes(slug));
              const active = hasActiveTasks(agent, tasks);

              const statusColor = active
                ? 'fill-green-500 text-green-500'
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
                      {getMetaLine(agent, agentTasks)}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        ))}

        {agents.length === 0 && (
          <div className="px-3 py-4 text-center text-sm text-muted-foreground">
            No agents
          </div>
        )}
      </div>
    </div>
  );
}
