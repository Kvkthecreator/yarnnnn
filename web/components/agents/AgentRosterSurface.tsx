'use client';

/**
 * AgentRosterSurface — Full-width roster view for /agents (ADR-167).
 *
 * Replaces the old left-sidebar AgentTreeNav. This is what you see when you
 * land on /agents with no `?agent=` param: the team roster grouped by class,
 * with health glances per agent.
 *
 * Grouping (ADR-176 v5 + ADR-164):
 *   - Thinking Partner: 1 meta-cognitive agent that owns back office work (shown first)
 *   - Specialists: 6 universal specialist agents (Researcher, Analyst, Writer, Tracker, Designer)
 *   - Reporting: 1 synthesizer agent that reads cross-domain
 *   - Integrations: 3 platform-bot agents (Slack, Notion, GitHub)
 *
 * Per-card health glance:
 *   - Status indicator (active/paused)
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

// 'specialist' is the v5 class; 'domain-steward' kept for backward compat with old DB rows
const CLASS_ORDER = ['meta-cognitive', 'specialist', 'domain-steward', 'synthesizer', 'platform-bot'] as const;
const CLASS_LABELS: Record<string, { title: string; description: string }> = {
  'meta-cognitive': {
    title: 'Thinking Partner',
    description: 'Your day-to-day collaborator. Chats with you and runs background upkeep.',
  },
  'specialist': {
    title: 'Specialists',
    description: 'Each one does one thing well — research, analysis, writing, tracking, or design.',
  },
  'domain-steward': {
    title: 'Specialists',
    description: 'Each one does one thing well — research, analysis, writing, tracking, or design.',
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

function formatRelativeUntil(dateStr: string): string {
  const diff = new Date(dateStr).getTime() - Date.now();
  if (diff <= 0) return 'now';
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `in ${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `in ${hours}h`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `in ${days}d`;
  const weeks = Math.floor(days / 7);
  return `in ${weeks}w`;
}

function normalizeScheduleLabel(schedule?: string | null): string {
  if (!schedule) return '';
  const raw = schedule.trim();
  if (!raw) return '';
  if (/^[a-z-]+$/i.test(raw)) {
    return raw.charAt(0).toUpperCase() + raw.slice(1);
  }
  if (/^(\*|[\d\/,-]+)(\s+(\*|[\d\/,-]+)){4}$/.test(raw)) return 'Custom';
  return raw;
}

function fmtDomain(value?: string | null): string {
  if (!value) return '';
  return value.replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim();
}

export function AgentRosterSurface({ agents, tasks, onSelect }: AgentRosterSurfaceProps) {
  const grouped = useMemo(() => {
    // Group agents: 'specialist' is v5 class; 'domain-steward' is v4 backward compat
    // Both render under the same "Specialists" label — merge them into one group
    const groups = CLASS_ORDER.map(cls => ({
      cls,
      label: CLASS_LABELS[cls],
      agents: agents.filter(a => {
        const agentCls = a.agent_class || 'specialist';
        if (cls === 'specialist') return agentCls === 'specialist' || agentCls === 'domain-steward';
        if (cls === 'domain-steward') return false; // handled by 'specialist' group
        return agentCls === cls;
      }),
    })).filter(g => g.agents.length > 0);
    return groups;
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
  const cls = agent.agent_class || 'specialist';
  const isPaused = agent.status === 'paused';
  const hasNoTasks = agentTasks.length === 0;
  const operationalTasks = activeTasks.length > 0
    ? activeTasks
    : agentTasks.filter(t => t.status !== 'archived');

  const scheduleSet = Array.from(new Set(
    operationalTasks.map(t => normalizeScheduleLabel(t.schedule)).filter(Boolean),
  ));
  const frequencyLabel =
    scheduleSet.length === 0
      ? null
      : scheduleSet.length === 1
        ? scheduleSet[0]
        : `Mixed (${scheduleSet.length})`;

  const nextRun = operationalTasks
    .map(t => t.next_run_at)
    .filter((v): v is string => Boolean(v))
    .map(v => new Date(v))
    .filter(d => !Number.isNaN(d.getTime()))
    .sort((a, b) => a.getTime() - b.getTime())[0] ?? null;

  const statusTone = isPaused
    ? {
        label: 'Paused',
        dot: 'bg-amber-500',
        text: 'text-amber-700 dark:text-amber-300',
      }
    : activeTasks.length > 0
      ? {
          label: 'Active',
          dot: 'bg-emerald-500',
          text: 'text-emerald-700 dark:text-emerald-300',
        }
      : {
          label: 'Idle',
          dot: 'bg-muted-foreground/40',
          text: 'text-muted-foreground/70',
        };

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
            <span className={cn('h-2 w-2 rounded-full shrink-0', statusTone.dot)} />
            <h4 className="text-sm font-semibold truncate">{agent.title}</h4>
          </div>
          {subline && (
            <p className="text-[11px] text-muted-foreground/60 truncate mt-0.5">
              {subline}
            </p>
          )}
        </div>
      </div>

      {/* Status row */}
      <div className="flex items-start justify-between gap-3 mt-3 pt-3 border-t border-border/40">
        <div className="flex flex-wrap items-center gap-2 min-w-0">
          <span
            className={cn(
              'inline-flex items-center gap-1 rounded-full border border-border/50 bg-muted/10 px-2 py-0.5 text-[10px]',
              statusTone.text,
            )}
          >
            <span className={cn('h-1.5 w-1.5 rounded-full', statusTone.dot)} />
            <span className="text-muted-foreground/70">Status</span>
            <span className="font-medium">{statusTone.label}</span>
          </span>
          {frequencyLabel && (
            <span className="text-[11px] text-muted-foreground/60">
              Frequency: {frequencyLabel}
            </span>
          )}
          <span className="text-[11px] text-muted-foreground/60">
            Next: {nextRun ? formatRelativeUntil(nextRun.toISOString()) : 'not scheduled'}
          </span>
        </div>
        {hasNoTasks ? (
          <span className="text-[11px] text-muted-foreground/40 italic shrink-0 ml-2">
            No tasks assigned yet
          </span>
        ) : (
          <div className="flex items-center justify-end gap-2 min-w-0 ml-2">
            <span className="text-[11px] text-muted-foreground/60 shrink-0">
              {activeTasks.length} active {activeTasks.length === 1 ? 'task' : 'tasks'}
            </span>
            {mostRecentTask && (
              <>
                <span className="text-muted-foreground/20">·</span>
                <span className="text-[11px] text-muted-foreground/50 truncate text-right">
                  {mostRecentTask.title}
                </span>
              </>
            )}
          </div>
        )}
      </div>
    </button>
  );
}
