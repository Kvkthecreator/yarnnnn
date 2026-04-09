'use client';

/**
 * AgentContentView — Canonical agent detail surface content.
 *
 * Rendering model:
 * - agent_class decides the top-level shell/context block
 * - task.output_kind decides the assigned-work card shape
 * - task.type_key can lightly specialize labels without forking the page
 *
 * This mirrors WorkDetail's registry-driven approach instead of branching on
 * individual agent pages or legacy role names.
 */

import Link from 'next/link';
import {
  ArrowUpRight,
  Bot,
  Brain,
  ChevronRight,
  FolderKanban,
  Sparkles,
  Target,
  TrendingDown,
  TrendingUp,
  Minus,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { WorkModeBadge } from '@/components/work/WorkModeBadge';
import { SurfaceIdentityHeader } from '@/components/shell/SurfaceIdentityHeader';
import { formatRelativeTime } from '@/lib/formatting';
import { CONTEXT_ROUTE, WORK_ROUTE } from '@/lib/routes';
import {
  agentClassDescription,
  agentClassLabel,
  roleDisplayName,
  roleTagline,
} from '@/lib/agent-identity';
import type { Agent, Task } from '@/types';

interface AgentContentViewProps {
  agent: Agent;
  tasks: Task[];
}

type AgentClass = NonNullable<Agent['agent_class']>;
type TaskOutputKind = NonNullable<Task['output_kind']>;

interface AgentShellDescriptor {
  label: string;
  title: (agent: Agent) => string;
  description: (agent: Agent) => string;
  highlights: (agent: Agent, counts: TaskKindCounts) => string[];
}

interface TaskCardDescriptor {
  label: string;
  badgeClass: string;
  summary: (task: Task) => string;
  details: (task: Task) => string[];
}

type TaskKindCounts = Record<TaskOutputKind, number>;

const EMPTY_TASK_COUNTS: TaskKindCounts = {
  accumulates_context: 0,
  produces_deliverable: 0,
  external_action: 0,
  system_maintenance: 0,
};

const TASK_TYPE_LABELS: Record<string, string> = {
  'track-competitors': 'Competitor tracker',
  'track-market': 'Market tracker',
  'track-relationships': 'Relationship tracker',
  'track-projects': 'Project tracker',
  'research-topics': 'Topic research',
  'slack-digest': 'Slack digest',
  'notion-digest': 'Notion digest',
  'github-digest': 'GitHub digest',
  'daily-update': 'Daily update',
  'competitive-intel-brief': 'Competitive brief',
  'market-report': 'Market report',
  'relationship-health-digest': 'Relationship digest',
  'stakeholder-update': 'Stakeholder update',
  'project-status-report': 'Project status report',
  'meeting-prep': 'Meeting prep',
  'slack-respond': 'Slack response',
  'notion-update': 'Notion update',
  'back-office-agent-hygiene': 'Agent hygiene',
  'back-office-workspace-cleanup': 'Workspace cleanup',
};

const AGENT_SHELL_REGISTRY: Record<AgentClass, AgentShellDescriptor> = {
  'domain-steward': {
    label: 'Domain role',
    title: (agent) => (
      agent.context_domain ? `Owns the ${agent.context_domain} context` : roleDisplayName(agent.role)
    ),
    description: (agent) => roleTagline(agent.role) || agentClassDescription(agent.agent_class),
    highlights: (agent, counts) => {
      const highlights = [
        `${counts.accumulates_context} tracking ${counts.accumulates_context === 1 ? 'task' : 'tasks'}`,
      ];
      if (counts.produces_deliverable > 0) {
        highlights.push(`${counts.produces_deliverable} deliverable ${counts.produces_deliverable === 1 ? 'task' : 'tasks'}`);
      }
      if (agent.context_domain) highlights.push(`${agent.context_domain} is the owned domain`);
      return highlights;
    },
  },
  synthesizer: {
    label: 'Cross-domain role',
    title: () => 'Synthesizes across your specialists',
    description: (agent) => roleTagline(agent.role) || agentClassDescription(agent.agent_class),
    highlights: (_, counts) => {
      const highlights = [
        `${counts.produces_deliverable} deliverable ${counts.produces_deliverable === 1 ? 'task' : 'tasks'}`,
      ];
      if (counts.accumulates_context > 0) highlights.push(`${counts.accumulates_context} tracking input ${counts.accumulates_context === 1 ? 'task' : 'tasks'}`);
      return highlights;
    },
  },
  'platform-bot': {
    label: 'Platform role',
    title: (agent) => `${roleDisplayName(agent.role).replace(' Bot', '')} is connected through this agent`,
    description: (agent) => roleTagline(agent.role) || agentClassDescription(agent.agent_class),
    highlights: (agent, counts) => {
      const highlights = [
        `${counts.accumulates_context} observation ${counts.accumulates_context === 1 ? 'task' : 'tasks'}`,
      ];
      if (counts.external_action > 0) {
        highlights.push(`${counts.external_action} write-back ${counts.external_action === 1 ? 'task' : 'tasks'}`);
      }
      if (agent.context_domain) highlights.push(`${agent.context_domain} is the platform bridge`);
      return highlights;
    },
  },
  'meta-cognitive': {
    label: 'Workforce role',
    title: () => 'Owns orchestration and back office maintenance',
    description: (agent) => roleTagline(agent.role) || agentClassDescription(agent.agent_class),
    highlights: (_, counts) => {
      const highlights = [
        `${counts.system_maintenance} maintenance ${counts.system_maintenance === 1 ? 'task' : 'tasks'}`,
      ];
      if (counts.produces_deliverable > 0) {
        highlights.push(`${counts.produces_deliverable} report ${counts.produces_deliverable === 1 ? 'task' : 'tasks'}`);
      }
      return highlights;
    },
  },
};

const TASK_CARD_REGISTRY: Record<TaskOutputKind, TaskCardDescriptor> = {
  accumulates_context: {
    label: 'Tracking',
    badgeClass: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
    summary: (task) => readableDomainSummary(task.context_writes || task.context_reads, 'Maintains context'),
    details: (task) => [
      ...(task.context_writes?.length ? [`Writes ${readableDomainSummary(task.context_writes, '')}`] : []),
      ...(task.context_reads?.length ? [`Reads ${readableDomainSummary(task.context_reads, '')}`] : []),
      ...(task.objective?.purpose ? [task.objective.purpose] : []),
    ].filter(Boolean),
  },
  produces_deliverable: {
    label: 'Deliverable',
    badgeClass: 'bg-violet-500/10 text-violet-700 dark:text-violet-300',
    summary: (task) => (
      task.objective?.deliverable ||
      task.objective?.format ||
      'Produces a user-facing deliverable'
    ),
    details: (task) => [
      ...(task.objective?.audience ? [`Audience: ${task.objective.audience}`] : []),
      ...(task.objective?.purpose ? [task.objective.purpose] : []),
      ...(task.delivery ? [`Delivery: ${task.delivery}`] : []),
    ].filter(Boolean),
  },
  external_action: {
    label: 'Action',
    badgeClass: 'bg-blue-500/10 text-blue-700 dark:text-blue-300',
    summary: (task) => (
      task.objective?.deliverable ||
      task.delivery ||
      inferActionTarget(task) ||
      'Takes action on an external platform'
    ),
    details: (task) => [
      ...(task.objective?.purpose ? [task.objective.purpose] : []),
      ...(inferActionTarget(task) ? [`Target: ${inferActionTarget(task)}`] : []),
    ].filter(Boolean),
  },
  system_maintenance: {
    label: 'Maintenance',
    badgeClass: 'bg-amber-500/10 text-amber-700 dark:text-amber-300',
    summary: (task) => task.objective?.purpose || 'Keeps the workspace and workforce coherent',
    details: (task) => [
      ...(task.essential ? ['Essential anchor task'] : []),
      ...(task.objective?.deliverable ? [`Output: ${task.objective.deliverable}`] : []),
    ].filter(Boolean),
  },
};

function stripLeadingH1IfMatchesTitle(content: string, title: string): string {
  const lines = content.split('\n');
  let i = 0;
  while (i < lines.length && lines[i].trim() === '') i++;
  if (i >= lines.length) return content;

  const firstLine = lines[i].trim();
  if (!firstLine.startsWith('# ') || firstLine.startsWith('## ')) return content;

  const h1Text = firstLine.slice(2).trim();
  if (h1Text.toLowerCase() !== title.toLowerCase()) return content;

  let j = i + 1;
  while (j < lines.length && lines[j].trim() === '') j++;
  return lines.slice(j).join('\n');
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/40 mb-2">
      {children}
    </h3>
  );
}

function readableDomainSummary(domains: string[] | undefined, fallback: string): string {
  if (!domains || domains.length === 0) return fallback;
  return domains.join(', ');
}

function taskTypeLabel(typeKey?: string | null): string | null {
  if (!typeKey) return null;
  return TASK_TYPE_LABELS[typeKey] || typeKey.replace(/-/g, ' ');
}

function inferActionTarget(task: Task): string | null {
  if (task.type_key?.startsWith('slack-')) return 'Slack';
  if (task.type_key?.startsWith('notion-')) return 'Notion';
  return task.delivery || null;
}

function getTaskKindCounts(tasks: Task[]): TaskKindCounts {
  return tasks.reduce<TaskKindCounts>((counts, task) => {
    const kind = task.output_kind;
    if (kind && kind in counts) counts[kind as TaskOutputKind] += 1;
    return counts;
  }, { ...EMPTY_TASK_COUNTS });
}

function shellIcon(agentClass?: string | null) {
  switch (agentClass) {
    case 'platform-bot':
      return Bot;
    case 'meta-cognitive':
      return Brain;
    case 'synthesizer':
      return Target;
    default:
      return FolderKanban;
  }
}

function AgentMetadata({ agent, tasks }: { agent: Agent; tasks: Task[] }) {
  const classLabel = agentClassLabel(agent.agent_class);
  const showClassLabel = classLabel.toLowerCase() !== agent.title.toLowerCase();
  const domain = agent.context_domain;
  const activeTaskCount = tasks.filter((task) => task.status === 'active').length;
  const lastRun = tasks
    .map((task) => task.last_run_at)
    .filter(Boolean)
    .sort()
    .reverse()[0] || agent.last_run_at || null;

  const segments: React.ReactNode[] = [];
  if (showClassLabel) segments.push(<span key="class">{classLabel}</span>);
  if (domain) {
    segments.push(
      <Link
        key="domain"
        href={`${CONTEXT_ROUTE}?domain=${domain}`}
        className="hover:text-foreground hover:underline"
      >
        {domain}/
      </Link>,
    );
  }
  segments.push(
    <span key="tasks">
      {activeTaskCount} active {activeTaskCount === 1 ? 'task' : 'tasks'}
    </span>,
  );
  if (lastRun) segments.push(<span key="last-run">Ran {formatRelativeTime(lastRun)}</span>);

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      {segments.map((segment, index) => (
        <span key={index} className="flex items-center gap-1.5">
          {index > 0 && <span className="text-muted-foreground/30">·</span>}
          {segment}
        </span>
      ))}
    </div>
  );
}

function AgentRoleBlock({ agent, tasks }: { agent: Agent; tasks: Task[] }) {
  const descriptor = AGENT_SHELL_REGISTRY[(agent.agent_class || 'domain-steward') as AgentClass];
  const Icon = shellIcon(agent.agent_class);
  const counts = getTaskKindCounts(tasks);
  const highlights = descriptor.highlights(agent, counts);

  return (
    <div className="px-6 py-5 border-t border-border/40">
      <SectionLabel>{descriptor.label}</SectionLabel>
      <div className="rounded-lg border border-border/60 bg-muted/10 px-4 py-4">
        <div className="flex items-start gap-3">
          <div className="w-9 h-9 rounded-lg bg-background border border-border/60 flex items-center justify-center shrink-0">
            <Icon className="w-4 h-4 text-muted-foreground" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="text-sm font-medium text-foreground">{descriptor.title(agent)}</h4>
              {agent.context_domain && (
                <Link
                  href={`${CONTEXT_ROUTE}?domain=${agent.context_domain}`}
                  className="inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground"
                >
                  Open context
                  <ArrowUpRight className="w-3 h-3" />
                </Link>
              )}
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              {descriptor.description(agent)}
            </p>
            {highlights.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-3">
                {highlights.map((highlight) => (
                  <span
                    key={highlight}
                    className="inline-flex items-center rounded-full bg-background px-2 py-1 text-[11px] text-muted-foreground border border-border/50"
                  >
                    {highlight}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function TaskCard({ task }: { task: Task }) {
  const descriptor = TASK_CARD_REGISTRY[task.output_kind as TaskOutputKind] || TASK_CARD_REGISTRY.produces_deliverable;
  const typeLabel = taskTypeLabel(task.type_key);
  const details = descriptor.details(task);

  return (
    <Link
      href={`${WORK_ROUTE}?task=${encodeURIComponent(task.slug)}`}
      className={cn(
        'group rounded-lg border border-border/40 bg-background hover:bg-muted/30 hover:border-border transition-colors px-3 py-3 block',
        task.status !== 'active' && 'opacity-70',
      )}
    >
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={cn('inline-flex rounded-full px-1.5 py-0.5 text-[10px] font-medium', descriptor.badgeClass)}>
              {descriptor.label}
            </span>
            {typeLabel && (
              <span className="inline-flex rounded-full bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                {typeLabel}
              </span>
            )}
            <WorkModeBadge mode={task.mode} />
            {task.essential && (
              <span className="inline-flex rounded-full bg-amber-500/10 px-1.5 py-0.5 text-[10px] text-amber-700">
                essential
              </span>
            )}
            {task.status === 'paused' && (
              <span className="inline-flex rounded-full bg-amber-500/10 px-1.5 py-0.5 text-[10px] text-amber-700">
                paused
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 mt-2">
            <span className="text-sm font-medium truncate">{task.title}</span>
          </div>

          <p className="text-[12px] text-muted-foreground mt-1">
            {descriptor.summary(task)}
          </p>

          <div className="flex items-center gap-2 mt-2 text-[11px] text-muted-foreground flex-wrap">
            {task.schedule && <span className="truncate">{task.schedule}</span>}
            {task.schedule && task.last_run_at && <span className="text-muted-foreground/30">·</span>}
            {task.last_run_at && <span>Ran {formatRelativeTime(task.last_run_at)}</span>}
            {!task.last_run_at && !task.schedule && <span>Never run</span>}
          </div>

          {details.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-3">
              {details.map((detail) => (
                <span
                  key={detail}
                  className="inline-flex rounded-md border border-border/50 bg-muted/10 px-2 py-1 text-[11px] text-muted-foreground"
                >
                  {detail}
                </span>
              ))}
            </div>
          )}
        </div>
        <ChevronRight className="w-4 h-4 text-muted-foreground/30 group-hover:text-muted-foreground/70 shrink-0 mt-1" />
      </div>
    </Link>
  );
}

function TasksBlock({ tasks }: { tasks: Task[] }) {
  if (tasks.length === 0) {
    return (
      <div className="px-6 py-5 border-t border-border/40">
        <SectionLabel>Assigned work</SectionLabel>
        <p className="text-sm text-muted-foreground/70">
          No tasks assigned yet.
        </p>
      </div>
    );
  }

  const sorted = [...tasks].sort((a, b) => {
    const statusOrder: Record<string, number> = { active: 0, paused: 1, archived: 2 };
    const statusDelta = (statusOrder[a.status] ?? 3) - (statusOrder[b.status] ?? 3);
    if (statusDelta !== 0) return statusDelta;
    const aTime = a.last_run_at ? new Date(a.last_run_at).getTime() : 0;
    const bTime = b.last_run_at ? new Date(b.last_run_at).getTime() : 0;
    return bTime - aTime;
  });

  return (
    <div className="px-6 py-5 border-t border-border/40">
      <SectionLabel>Assigned work · {tasks.length}</SectionLabel>
      <div className="space-y-2">
        {sorted.map((task) => (
          <TaskCard key={task.id} task={task} />
        ))}
      </div>
    </div>
  );
}

function LearnedBlock({ agent }: { agent: Agent }) {
  const feedback = agent.agent_memory?.feedback;
  const reflections = agent.agent_memory?.reflections;
  if (!feedback && !reflections) return null;

  return (
    <div className="px-6 py-5 border-t border-border/40 space-y-5">
      {feedback && (
        <div>
          <SectionLabel>
            <span className="inline-flex items-center gap-1.5">
              <Sparkles className="w-3 h-3" />
              Learned from your feedback
            </span>
          </SectionLabel>
          <div className="rounded-lg border border-border/60 bg-muted/10 px-4 py-3">
            <div className="prose prose-sm max-w-none dark:prose-invert text-sm">
              <MarkdownRenderer content={feedback} />
            </div>
          </div>
        </div>
      )}
      {reflections && (
        <div>
          <SectionLabel>Recent reflections</SectionLabel>
          <div className="rounded-lg border border-border/60 bg-muted/10 px-4 py-3">
            <div className="prose prose-sm max-w-none dark:prose-invert text-sm">
              <MarkdownRenderer content={reflections} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function InstructionsBlock({ agent }: { agent: Agent }) {
  if (!agent.agent_instructions) return null;
  const content = stripLeadingH1IfMatchesTitle(agent.agent_instructions, agent.title);
  if (!content.trim()) return null;

  return (
    <div className="px-6 py-5 border-t border-border/40">
      <SectionLabel>How I work</SectionLabel>
      <div className="rounded-lg border border-border/60 bg-muted/10 px-4 py-3">
        <div className="prose prose-sm max-w-none dark:prose-invert">
          <MarkdownRenderer content={content} />
        </div>
      </div>
    </div>
  );
}

function StatsStrip({ agent }: { agent: Agent }) {
  const totalRuns = agent.version_count ?? 0;
  const approvalPct = agent.quality_score != null
    ? Math.round((1 - (agent.quality_score || 0)) * 100)
    : null;
  const trend = agent.quality_trend;
  const avgEdit = agent.avg_edit_distance;
  const hasStats = totalRuns > 0 || approvalPct != null || avgEdit != null;

  if (!hasStats && !agent.created_at) return null;

  return (
    <div className="px-6 py-5 border-t border-border/40">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-muted-foreground">
        {totalRuns > 0 && (
          <span>
            <span className="font-medium text-foreground">{totalRuns}</span> {totalRuns === 1 ? 'run' : 'runs'}
          </span>
        )}
        {approvalPct != null && totalRuns >= 5 && (
          <span className="inline-flex items-center gap-1">
            <span className="font-medium text-foreground">{approvalPct}%</span> approved
            {trend === 'improving' && <TrendingUp className="w-3 h-3 text-green-500" />}
            {trend === 'declining' && <TrendingDown className="w-3 h-3 text-red-500" />}
            {trend === 'stable' && <Minus className="w-3 h-3 text-muted-foreground/50" />}
          </span>
        )}
        {avgEdit != null && totalRuns >= 5 && (
          <span>
            avg edit distance <span className="font-medium text-foreground">{avgEdit.toFixed(2)}</span>
          </span>
        )}
        <span className="text-muted-foreground/40">
          Created {new Date(agent.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}
        </span>
      </div>
    </div>
  );
}

export function AgentContentView({ agent, tasks }: AgentContentViewProps) {
  return (
    <div className="flex-1 overflow-auto">
      <SurfaceIdentityHeader
        title={agent.title}
        metadata={<AgentMetadata agent={agent} tasks={tasks} />}
      />
      <div className="max-w-3xl">
        <AgentRoleBlock agent={agent} tasks={tasks} />
        <TasksBlock tasks={tasks} />
        <LearnedBlock agent={agent} />
        <InstructionsBlock agent={agent} />
        <StatsStrip agent={agent} />
      </div>
    </div>
  );
}
