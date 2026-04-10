'use client';

/**
 * AgentRosterSurface — Full-width roster view for /agents (ADR-167).
 *
 * Replaces the old left-sidebar AgentTreeNav. This is what you see when you
 * land on /agents with no `?agent=` param: the team roster grouped by class,
 * with health glances per agent.
 *
 * Grouping (ADR-140 v4 + ADR-164):
 *   - Thinking Partner: 1 meta-cognitive agent that owns back office work (shown first)
 *   - Specialists: 5 domain-steward agents that own context domains
 *   - Reporting: 1 synthesizer agent that reads cross-domain
 *   - Integrations: 3 platform-bot agents (Slack, Notion, GitHub)
 *
 * Per-card health glance:
 *   - Status indicator (active/paused)
 *   - Domain owned (for stewards)
 *   - Active task count
 *   - Last run (relative time, color-coded by freshness)
 *   - Approval rate (only if version_count >= 5, with trend)
 *
 * Click a card → onSelect(agentId) → page transitions to detail mode by
 * updating URL to `?agent={slug}`.
 */

import { useMemo } from 'react';
import { Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getAgentSlug, roleTagline } from '@/lib/agent-identity';
import { AgentIcon } from './AgentIcon';
import type { Agent, Task } from '@/types';

interface AgentRosterSurfaceProps {
  agents: Agent[];
  tasks: Task[];
  onSelect: (agentId: string) => void;
}

const CLASS_ORDER = ['meta-cognitive', 'domain-steward', 'synthesizer', 'platform-bot'] as const;
const CLASS_LABELS: Record<string, { title: string; description: string }> = {
  'meta-cognitive': {
    title: 'Thinking Partner',
    description: 'Your day-to-day collaborator. Chats with you and runs background upkeep.',
  },
  'domain-steward': {
    title: 'Specialists',
    description: 'Each one owns a topic and gets smarter about it over time.',
  },
  'synthesizer': {
    title: 'Reporting',
    description: 'Pulls from every specialist to write your cross-topic reports.',
  },
  'platform-bot': {
    title: 'Integrations',
    description: 'Connect your tools (Slack, Notion, GitHub) so the team can see what is happening there.',
  },
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

function fmtDomain(value?: string | null): string {
  if (!value) return '';
  return value.replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim();
}

export function AgentRosterSurface({ agents, tasks, onSelect }: AgentRosterSurfaceProps) {
  const grouped = useMemo(() => {
    return CLASS_ORDER.map(cls => ({
      cls,
      label: CLASS_LABELS[cls],
      agents: agents.filter(a => (a.agent_class || 'domain-steward') === cls),
    })).filter(g => g.agents.length > 0);
  }, [agents]);

  if (agents.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <Sparkles className="w-6 h-6 text-muted-foreground/20 mx-auto mb-2" />
          <p className="text-sm font-medium mb-1">No agents yet</p>
          <p className="text-xs text-muted-foreground">
            Your workspace agents will appear here once scaffolded.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-auto">
      <div className="px-6 py-6 max-w-5xl space-y-8">
        {grouped.map(group => (
          <section key={group.cls}>
            <header className="mb-3">
              <h3 className="text-sm font-semibold text-foreground">
                {group.label.title}
                <span className="ml-2 text-xs font-normal text-muted-foreground/50">
                  · {group.agents.length}
                </span>
              </h3>
              <p className="text-xs text-muted-foreground/70 mt-0.5">
                {group.label.description}
              </p>
            </header>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {group.agents.map(agent => (
                <AgentCard
                  key={agent.id}
                  agent={agent}
                  tasks={tasks}
                  onSelect={() => onSelect(agent.id)}
                />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

// ─── Card ───

function AgentCard({
  agent,
  tasks,
  onSelect,
}: {
  agent: Agent;
  tasks: Task[];
  onSelect: () => void;
}) {
  const slug = getAgentSlug(agent);
  const agentTasks = tasks.filter(t => t.agent_slugs?.includes(slug));
  const activeTasks = agentTasks.filter(t => t.status === 'active');
  const mostRecentTask = [...agentTasks]
    .sort((a, b) => (b.last_run_at ?? '').localeCompare(a.last_run_at ?? ''))
    .find(t => t.status === 'active') ?? activeTasks[0] ?? agentTasks[0] ?? null;
  const lastRun = agentTasks
    .map(t => t.last_run_at)
    .filter(Boolean)
    .sort()
    .reverse()[0] || agent.last_run_at || null;
  const cls = agent.agent_class || 'domain-steward';
  const isPaused = agent.status === 'paused';
  const hasNoTasks = agentTasks.length === 0;

  // Subline: human-readable domain for specialists, role tagline for others
  const subline = agent.context_domain
    ? `Tracks ${fmtDomain(agent.context_domain)}`
    : roleTagline(agent.role) || (
      cls === 'synthesizer' ? 'Assembles cross-domain reports'
      : cls === 'meta-cognitive' ? 'Orchestrates your workforce'
      : ''
    );

  return (
    <button
      onClick={onSelect}
      className={cn(
        'text-left rounded-lg border border-border/60 bg-background hover:bg-muted/30 hover:border-border transition-colors p-4',
        isPaused && 'opacity-60',
      )}
    >
      <div className="flex items-start gap-3">
        <div
          className={cn(
            'w-9 h-9 rounded-md flex items-center justify-center shrink-0',
            cls === 'meta-cognitive' ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400' :
            cls === 'platform-bot' ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400' :
            cls === 'synthesizer' ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400' :
            'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
          )}
        >
          <AgentIcon role={agent.role} className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-semibold truncate">{agent.title}</h4>
            {isPaused && (
              <span className="text-[10px] rounded-full bg-amber-500/10 text-amber-700 px-1.5 py-0.5">
                paused
              </span>
            )}
          </div>
          {subline && (
            <p className="text-[11px] text-muted-foreground/60 truncate mt-0.5">
              {subline}
            </p>
          )}
        </div>
      </div>

      {/* Status row */}
      <div className="flex items-center justify-between mt-3 pt-3 border-t border-border/40">
        {hasNoTasks ? (
          <span className="text-[11px] text-muted-foreground/40 italic">No tasks assigned yet</span>
        ) : (
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-[11px] text-muted-foreground/60 shrink-0">
              {activeTasks.length} active {activeTasks.length === 1 ? 'task' : 'tasks'}
            </span>
            {mostRecentTask && (
              <>
                <span className="text-muted-foreground/20">·</span>
                <span className="text-[11px] text-muted-foreground/50 truncate">
                  {mostRecentTask.title}
                </span>
              </>
            )}
          </div>
        )}
        <span className={cn('text-[11px] shrink-0 ml-2', freshnessColor(lastRun))}>
          {lastRun ? formatRelativeShort(lastRun) : hasNoTasks ? '' : 'never run'}
        </span>
      </div>
    </button>
  );
}
