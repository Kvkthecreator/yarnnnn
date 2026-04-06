'use client';

/**
 * AgentTreeNav — Left panel agent roster.
 *
 * Three sections: domain stewards, synthesizers, platform bots.
 * Per-class icons. Freshness + task count on right.
 * Click = select (left-border highlight + accent background).
 */

import { Brain, Layers, Plug, Circle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Agent, Task } from '@/types';

interface AgentTreeNavProps {
  agents: Agent[];
  tasks: Task[];
  selectedAgentId: string | null;
  onSelectAgent: (agentId: string) => void;
}

function getAgentSlug(agent: Agent): string {
  return agent.slug || agent.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
}

function hasActiveTasks(agent: Agent, tasks: Task[]): boolean {
  const slug = getAgentSlug(agent);
  return tasks.some(t => t.agent_slugs?.includes(slug) && t.status === 'active');
}

const CLASS_ORDER = ['domain-steward', 'synthesizer', 'platform-bot'] as const;
const CLASS_LABELS: Record<string, string> = {
  'domain-steward': 'Agents',
  'synthesizer': 'Cross-Team',
  'platform-bot': 'Integrations',
};

function formatRelativeShort(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  const weeks = Math.floor(days / 7);
  return `${weeks}w ago`;
}

function freshnessColor(dateStr: string | null): string {
  if (!dateStr) return 'text-muted-foreground/40';
  const hours = (Date.now() - new Date(dateStr).getTime()) / 3600000;
  if (hours < 24) return 'text-green-600 dark:text-green-400';
  if (hours < 72) return 'text-muted-foreground';
  return 'text-amber-600 dark:text-amber-400';
}

/** Per-class icon */
function AgentIcon({ agentClass, active, selected }: { agentClass: string; active: boolean; selected: boolean }) {
  const color = selected
    ? 'text-foreground'
    : active
    ? 'text-foreground/60'
    : 'text-muted-foreground/40';

  const cls = cn('w-4 h-4 shrink-0', color);

  switch (agentClass) {
    case 'synthesizer':
      return <Layers className={cls} />;
    case 'platform-bot':
      return <Plug className={cls} />;
    default:
      return <Brain className={cls} />;
  }
}

export function AgentTreeNav({
  agents,
  tasks,
  selectedAgentId,
  onSelectAgent,
}: AgentTreeNavProps) {
  const grouped = CLASS_ORDER.map(cls => ({
    cls,
    label: CLASS_LABELS[cls],
    agents: agents.filter(a => (a.agent_class || 'domain-steward') === cls),
  })).filter(g => g.agents.length > 0);

  return (
    <div className="flex flex-col h-full text-sm">
      <div className="flex-1 overflow-y-auto py-1">
        {grouped.map(group => (
          <div key={group.cls}>
            <div className="px-3 pt-3 pb-1">
              <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
                {group.label}
              </span>
            </div>

            {group.agents.map(agent => {
              const isSelected = agent.id === selectedAgentId;
              const slug = getAgentSlug(agent);
              const agentTasks = tasks.filter(t => t.agent_slugs?.includes(slug));
              const active = hasActiveTasks(agent, tasks);
              const activeTasks = agentTasks.filter(t => t.status === 'active');
              const taskCount = activeTasks.length;

              const lastRun = agentTasks
                .map(t => t.last_run_at)
                .filter(Boolean)
                .sort()
                .reverse()[0] || null;

              const domain = agent.context_domain;
              const cls = agent.agent_class || 'domain-steward';
              const isBot = cls === 'platform-bot';

              return (
                <button
                  key={agent.id}
                  onClick={() => onSelectAgent(agent.id)}
                  className={cn(
                    'w-full flex items-start gap-2.5 px-3 py-2 text-left transition-colors',
                    isSelected
                      ? 'bg-accent border-l-2 border-foreground'
                      : 'hover:bg-accent/50 border-l-2 border-transparent'
                  )}
                >
                  {/* Icon */}
                  <div className="mt-0.5 shrink-0">
                    <AgentIcon agentClass={cls} active={active} selected={isSelected} />
                  </div>

                  <div className="min-w-0 flex-1">
                    {/* Agent name */}
                    <p className={cn(
                      'text-[13px] truncate leading-tight',
                      isSelected ? 'font-semibold text-foreground' : 'text-foreground/90'
                    )}>
                      {agent.title}
                    </p>

                    {/* Domain label */}
                    <div className="flex items-center gap-1.5 mt-0.5">
                      {domain && (
                        <span className="text-[11px] text-muted-foreground/60 truncate">
                          {domain}/
                        </span>
                      )}
                      {!domain && isBot && (
                        <span className="text-[11px] text-muted-foreground/40 truncate">
                          not connected
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Right: freshness + task count */}
                  <div className="shrink-0 flex flex-col items-end gap-0.5 mt-0.5">
                    {lastRun ? (
                      <span className={cn('text-[11px] tabular-nums font-medium', freshnessColor(lastRun))}>
                        {formatRelativeShort(lastRun)}
                      </span>
                    ) : taskCount > 0 ? (
                      <span className="text-[11px] text-muted-foreground/50">pending</span>
                    ) : null}
                    {taskCount > 0 && (
                      <span className="text-[10px] text-muted-foreground/50">
                        {taskCount} task{taskCount !== 1 ? 's' : ''}
                      </span>
                    )}
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
