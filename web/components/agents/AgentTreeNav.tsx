'use client';

/**
 * AgentTreeNav — Left panel navigation for the agents surface.
 *
 * SURFACE-ARCHITECTURE.md v3: Agents as parents (stable roster),
 * tasks as expandable children (responsibilities). Three sections:
 * domain stewards, synthesizers, platform bots.
 */

import { useState } from 'react';
import {
  ChevronRight,
  ChevronDown,
  Circle,
  Clock,
  Play,
  Pause,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Agent, Task } from '@/types';

export type AgentView = 'domain' | 'output' | 'observations' | 'task-output' | 'task-deliverable' | 'task-history';

interface AgentTreeNavProps {
  agents: Agent[];
  tasks: Task[];
  selectedAgentId: string | null;
  selectedTaskSlug: string | null;
  selectedView: AgentView;
  filter: string | null;
  onFilterChange: (filter: string | null) => void;
  onSelectAgent: (agentId: string) => void;
  onSelectTask: (agentId: string, taskSlug: string) => void;
  onSelectView: (view: AgentView) => void;
  onRunTask?: (taskSlug: string) => void;
  onToggleTaskStatus?: (taskSlug: string) => void;
  busy?: boolean;
}

/** Get the default view for an agent based on class */
export function getDefaultAgentView(agent: Agent): AgentView {
  switch (agent.agent_class) {
    case 'synthesizer': return 'output';
    case 'platform-bot': return 'observations';
    default: return 'domain'; // domain-steward
  }
}

/** Group tasks by their first agent_slug */
function groupTasksByAgent(tasks: Task[]): Record<string, Task[]> {
  const grouped: Record<string, Task[]> = {};
  for (const task of tasks) {
    const slug = task.agent_slugs?.[0];
    if (!slug) continue;
    if (!grouped[slug]) grouped[slug] = [];
    grouped[slug].push(task);
  }
  return grouped;
}

/** Match agent to its tasks using slug derived from title */
function getAgentSlug(agent: Agent): string {
  // Agents have a slug field if available, otherwise derive from title
  return agent.slug || agent.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
}

const CLASS_ORDER = ['domain-steward', 'synthesizer', 'platform-bot'] as const;
const CLASS_LABELS: Record<string, string> = {
  'domain-steward': 'Domain Stewards',
  'synthesizer': 'Synthesizers',
  'platform-bot': 'Platform Bots',
};

export function AgentTreeNav({
  agents,
  tasks,
  selectedAgentId,
  selectedTaskSlug,
  selectedView,
  filter,
  onFilterChange,
  onSelectAgent,
  onSelectTask,
  onSelectView,
  onRunTask,
  onToggleTaskStatus,
  busy,
}: AgentTreeNavProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>(() => {
    if (selectedAgentId) return { [selectedAgentId]: true };
    return {};
  });

  const tasksByAgent = groupTasksByAgent(tasks);

  // Filter agents by task assignment status
  const hasActiveTasks = (agent: Agent) => {
    const slug = getAgentSlug(agent);
    const agentTasks = tasksByAgent[slug] || [];
    return agentTasks.some(t => t.status === 'active');
  };

  const filtered = filter === 'active'
    ? agents.filter(hasActiveTasks)
    : filter === 'dormant'
    ? agents.filter(a => !hasActiveTasks(a))
    : agents;

  // Group by agent class
  const grouped = CLASS_ORDER.map(cls => ({
    cls,
    label: CLASS_LABELS[cls],
    agents: filtered.filter(a => (a.agent_class || 'domain-steward') === cls),
  })).filter(g => g.agents.length > 0);

  const toggleExpand = (id: string) => {
    setExpanded(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const handleAgentClick = (agent: Agent) => {
    setExpanded(prev => ({ ...prev, [agent.id]: true }));
    onSelectAgent(agent.id);
    onSelectView(getDefaultAgentView(agent));
  };

  // Counts
  const activeCount = agents.filter(hasActiveTasks).length;
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

      {/* Agent tree */}
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
              const isExpanded = expanded[agent.id] || isSelected;
              const agentSlug = getAgentSlug(agent);
              const agentTasks = tasksByAgent[agentSlug] || [];
              const hasWork = agentTasks.some(t => t.status === 'active');

              const statusColor = hasWork
                ? 'fill-green-500 text-green-500'
                : 'text-muted-foreground/30';

              return (
                <div key={agent.id}>
                  {/* Agent row */}
                  <button
                    onClick={() => handleAgentClick(agent)}
                    className={cn(
                      'w-full flex items-center gap-1.5 px-2 py-1.5 text-left hover:bg-accent rounded-sm',
                      isSelected && !selectedTaskSlug && 'bg-accent/50'
                    )}
                  >
                    {agentTasks.length > 0 ? (
                      <button
                        onClick={(e) => { e.stopPropagation(); toggleExpand(agent.id); }}
                        className="p-0.5 shrink-0"
                      >
                        {isExpanded
                          ? <ChevronDown className="w-3 h-3 text-muted-foreground" />
                          : <ChevronRight className="w-3 h-3 text-muted-foreground" />
                        }
                      </button>
                    ) : (
                      <span className="w-4 shrink-0" />
                    )}
                    <Circle className={cn('w-2 h-2 shrink-0', statusColor)} />
                    <span className="truncate flex-1 font-medium">{agent.title}</span>
                    {agentTasks.length > 0 && (
                      <span className="text-[10px] text-muted-foreground/50 shrink-0">
                        {agentTasks.length}
                      </span>
                    )}
                  </button>

                  {/* Task children */}
                  {isExpanded && agentTasks.length > 0 && (
                    <div className="ml-5">
                      {agentTasks.map(task => {
                        const isTaskSelected = isSelected && selectedTaskSlug === task.slug;
                        const taskStatusColor =
                          task.status === 'active' ? 'fill-green-500 text-green-500' :
                          task.status === 'paused' ? 'fill-amber-500 text-amber-500' :
                          task.status === 'completed' ? 'fill-blue-500 text-blue-500' :
                          'text-muted-foreground/30';

                        return (
                          <div key={task.slug}>
                            <button
                              onClick={() => onSelectTask(agent.id, task.slug)}
                              className={cn(
                                'w-full flex items-center gap-2 px-2 py-1 text-left rounded-sm hover:bg-accent',
                                isTaskSelected
                                  ? 'bg-primary/10 text-primary'
                                  : 'text-muted-foreground'
                              )}
                            >
                              <Circle className={cn('w-1.5 h-1.5 shrink-0', taskStatusColor)} />
                              <span className="truncate flex-1 text-[13px]">{task.title}</span>
                              {task.schedule && (
                                <span className="text-[10px] text-muted-foreground/40 shrink-0">{task.schedule}</span>
                              )}
                            </button>

                            {/* Task actions when selected */}
                            {isTaskSelected && (
                              <div className="ml-4 mt-1 mb-2 px-2 py-1.5 rounded-lg bg-muted/30 space-y-1.5">
                                <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[11px] text-muted-foreground">
                                  {task.mode && <span className="capitalize">{task.mode}</span>}
                                  {task.schedule && (
                                    <span className="flex items-center gap-0.5">
                                      <Clock className="w-2.5 h-2.5" />
                                      {task.schedule}
                                    </span>
                                  )}
                                </div>
                                <div className="flex gap-1.5">
                                  {onRunTask && (
                                    <button
                                      onClick={(e) => { e.stopPropagation(); onRunTask(task.slug); }}
                                      disabled={busy}
                                      className="flex items-center gap-1 px-2 py-0.5 text-[11px] font-medium rounded bg-primary/10 text-primary hover:bg-primary/20 disabled:opacity-50"
                                    >
                                      <Play className="w-2.5 h-2.5" />
                                      Run
                                    </button>
                                  )}
                                  {onToggleTaskStatus && (
                                    <button
                                      onClick={(e) => { e.stopPropagation(); onToggleTaskStatus(task.slug); }}
                                      disabled={busy}
                                      className="flex items-center gap-1 px-2 py-0.5 text-[11px] font-medium rounded border border-border text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-50"
                                    >
                                      {task.status === 'active' ? <Pause className="w-2.5 h-2.5" /> : <Play className="w-2.5 h-2.5" />}
                                      {task.status === 'active' ? 'Pause' : 'Resume'}
                                    </button>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
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
