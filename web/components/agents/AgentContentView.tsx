'use client';

/**
 * AgentContentView — Center panel for selected agent.
 *
 * SURFACE-ARCHITECTURE.md v7: Single scrollable view (no tabs).
 *
 * Header (pinned): Agent name, class, domain, rhythm, freshness.
 * Dashboard section: Composed intelligence from workspace files.
 * Tasks section: Task cards with objectives, schedule, actions.
 * Agent section: Identity, AGENT.md, history, feedback.
 *
 * File browsing removed — "View files" links to /context?domain={domain}.
 */

import { useEffect } from 'react';
import { useBreadcrumb } from '@/contexts/BreadcrumbContext';
import {
  Play,
  Pause,
  Circle,
  MessageSquare,
  Layers,
  Brain,
  Plug,
  ExternalLink,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { AgentDashboard } from '@/components/agents/AgentDashboard';
import { avatarColor } from '@/lib/agent-identity';
import { formatRelativeTime } from '@/lib/formatting';
import type { Agent, Task } from '@/types';

interface AgentContentViewProps {
  agent: Agent;
  tasks: Task[];
  onRunTask: (taskSlug: string) => void;
  onPauseTask: (taskSlug: string) => void;
  onOpenChat: (prompt?: string) => void;
  busy: boolean;
}

function getAgentMandate(agent: Agent): string | null {
  if (!agent.agent_instructions) return null;
  const first = agent.agent_instructions.split(/\.\s/)[0];
  return first ? first + '.' : null;
}

const CLASS_LABELS: Record<string, string> = {
  'domain-steward': 'Domain Steward',
  'synthesizer': 'Synthesizer',
  'platform-bot': 'Platform Bot',
};

function HeaderIcon({ agentClass }: { agentClass: string }) {
  const cls = 'w-5 h-5';
  switch (agentClass) {
    case 'synthesizer': return <Layers className={cls} />;
    case 'platform-bot': return <Plug className={cls} />;
    default: return <Brain className={cls} />;
  }
}

// ─── Pinned Header ───

function AgentHeader({ agent, tasks }: { agent: Agent; tasks: Task[] }) {
  const cls = agent.agent_class || 'domain-steward';
  const classLabel = CLASS_LABELS[cls] || cls;
  const domain = agent.context_domain;
  const activeTasks = tasks.filter(t => t.status === 'active');
  const schedule = activeTasks[0]?.schedule;
  const color = avatarColor(agent.role);
  const mandate = getAgentMandate(agent);

  const lastRun = tasks.map(t => t.last_run_at).filter(Boolean).sort().reverse()[0];

  return (
    <div className="px-5 py-3 border-b border-border shrink-0">
      <div className="flex items-center gap-3">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
          style={{ backgroundColor: color + '18' }}
        >
          <div style={{ color }}><HeaderIcon agentClass={cls} /></div>
        </div>
        <div className="flex-1 min-w-0">
          <h2 className="text-base font-semibold truncate">{agent.title}</h2>
          {mandate && <p className="text-xs text-muted-foreground line-clamp-1 mt-0.5">{mandate}</p>}
        </div>
      </div>
      <div className="flex items-center gap-1.5 mt-2 text-xs text-muted-foreground">
        <span>{classLabel}</span>
        {domain && (
          <>
            <span className="text-muted-foreground/30">·</span>
            <span>{domain}/</span>
          </>
        )}
        {schedule && (
          <>
            <span className="text-muted-foreground/30">·</span>
            <span className="capitalize">Works {schedule}</span>
          </>
        )}
        {lastRun && (
          <>
            <span className="text-muted-foreground/30">·</span>
            <span>Ran {formatRelativeTime(lastRun)}</span>
          </>
        )}
        {!activeTasks.length && !schedule && (
          <>
            <span className="text-muted-foreground/30">·</span>
            <span className="text-muted-foreground/50">No active tasks</span>
          </>
        )}
      </div>
    </div>
  );
}

// ─── Tasks Section ───

function TasksSection({
  agent,
  tasks,
  onRunTask,
  onPauseTask,
  onOpenChat,
  busy,
}: {
  agent: Agent;
  tasks: Task[];
  onRunTask: (slug: string) => void;
  onPauseTask: (slug: string) => void;
  onOpenChat: (prompt?: string) => void;
  busy: boolean;
}) {
  if (tasks.length === 0) {
    return (
      <div className="px-5 py-6 text-center">
        <Layers className="w-6 h-6 text-muted-foreground/15 mx-auto mb-2" />
        <p className="text-sm font-medium mb-1">No tasks assigned</p>
        <p className="text-xs text-muted-foreground mb-3">
          Assign a task to this agent to get started.
        </p>
        <button
          onClick={() => onOpenChat(`Create a task for ${agent.title}`)}
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          <MessageSquare className="w-3.5 h-3.5" />
          Assign via TP
        </button>
      </div>
    );
  }

  return (
    <div className="px-5 py-4 space-y-3">
      {/* Context flow summary */}
      {tasks.some(t => (t.context_reads?.length || 0) > 0 || (t.context_writes?.length || 0) > 0) && (
        <div className="flex items-center gap-3 text-xs text-muted-foreground pb-3 border-b border-border/40">
          {Array.from(new Set(tasks.flatMap(t => t.context_writes || []))).map(d => (
            <div key={d} className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500/50" />
              <span>Writes {d}/</span>
            </div>
          ))}
          {Array.from(new Set(tasks.flatMap(t => t.context_reads || []))).map(d => (
            <div key={d} className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500/50" />
              <span>Reads {d}/</span>
            </div>
          ))}
        </div>
      )}

      {tasks.map(task => (
        <TaskCard
          key={task.slug}
          task={task}
          onRun={() => onRunTask(task.slug)}
          onPause={() => onPauseTask(task.slug)}
          onEdit={() => onOpenChat(`I want to update the task "${task.title}"`)}
          busy={busy}
        />
      ))}
    </div>
  );
}

function TaskCard({
  task,
  onRun,
  onPause,
  onEdit,
  busy,
}: {
  task: Task;
  onRun: () => void;
  onPause: () => void;
  onEdit: () => void;
  busy: boolean;
}) {
  const isActive = task.status === 'active';
  const statusColor = isActive
    ? 'fill-green-500 text-green-500'
    : task.status === 'paused'
    ? 'fill-amber-500 text-amber-500'
    : 'text-muted-foreground/30';

  return (
    <div className="border border-border rounded-lg p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Circle className={cn('w-2 h-2 shrink-0', statusColor)} />
        <span className="text-sm font-medium flex-1 truncate">{task.title}</span>
        <span className="text-[10px] rounded-full bg-muted px-1.5 py-0.5 text-muted-foreground capitalize">
          {task.mode || 'recurring'}
        </span>
      </div>

      {task.objective && (
        <div className="text-xs text-muted-foreground space-y-0.5">
          {task.objective.deliverable && <p>· {task.objective.deliverable}</p>}
          {task.objective.audience && <p>· Audience: {task.objective.audience}</p>}
          {task.objective.purpose && <p>· Purpose: {task.objective.purpose}</p>}
        </div>
      )}

      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        {task.schedule && <span className="capitalize">{task.schedule}</span>}
        {task.next_run_at && (
          <>
            <span className="text-muted-foreground/30">·</span>
            <span>Next: {formatRelativeTime(task.next_run_at)}</span>
          </>
        )}
        {task.last_run_at && (
          <>
            <span className="text-muted-foreground/30">·</span>
            <span>Last: {formatRelativeTime(task.last_run_at)}</span>
          </>
        )}
      </div>

      <div className="flex items-center gap-2 pt-1">
        <button
          onClick={onRun}
          disabled={busy || !isActive}
          className="flex items-center gap-1 px-3 py-1 text-xs font-medium rounded bg-primary/10 text-primary hover:bg-primary/20 disabled:opacity-50"
        >
          <Play className="w-3 h-3" />
          Run Now
        </button>
        <button
          onClick={onPause}
          disabled={busy}
          className="flex items-center gap-1 px-3 py-1 text-xs font-medium rounded border border-border text-muted-foreground hover:text-foreground hover:bg-muted"
        >
          {isActive ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
          {isActive ? 'Pause' : 'Resume'}
        </button>
        <button
          onClick={onEdit}
          className="flex items-center gap-1 px-3 py-1 text-xs font-medium rounded border border-border text-muted-foreground hover:text-foreground hover:bg-muted ml-auto"
        >
          <MessageSquare className="w-3 h-3" />
          Edit via TP
        </button>
      </div>
    </div>
  );
}

// ─── Agent Section ───

function AgentSection({ agent }: { agent: Agent }) {
  const cls = agent.agent_class || 'domain-steward';
  const classLabel = CLASS_LABELS[cls] || cls;

  return (
    <div className="px-5 py-4 space-y-5">
      <div className="space-y-2">
        <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/40">Identity</h3>
        <div className="text-xs text-muted-foreground space-y-1">
          <p>· Name: {agent.title}</p>
          <p>· Role: {agent.role} ({classLabel})</p>
          {agent.context_domain && <p>· Domain: {agent.context_domain}/</p>}
          {agent.origin && <p>· Origin: {agent.origin.replace(/_/g, ' ')}</p>}
        </div>
      </div>

      {agent.agent_instructions && (
        <div className="space-y-2">
          <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/40">Instructions</h3>
          <div className="rounded-lg border border-border bg-muted/10 p-3">
            <div className="prose prose-sm max-w-none dark:prose-invert text-xs">
              <MarkdownRenderer content={agent.agent_instructions} />
            </div>
          </div>
        </div>
      )}

      <div className="space-y-2">
        <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/40">History</h3>
        <div className="text-xs text-muted-foreground space-y-1">
          {agent.quality_score != null && (
            <p>
              · Quality: {Math.round((1 - (agent.quality_score || 0)) * 100)}%
              {agent.quality_trend && (
                <span className={cn(
                  'ml-1',
                  agent.quality_trend === 'improving' && 'text-green-500',
                  agent.quality_trend === 'declining' && 'text-red-500',
                )}>
                  ({agent.quality_trend === 'improving' ? '↑' : agent.quality_trend === 'declining' ? '↓' : '→'} {agent.quality_trend})
                </span>
              )}
            </p>
          )}
          {agent.version_count != null && <p>· Total runs: {agent.version_count}</p>}
          {agent.last_run_at && <p>· Last run: {formatRelativeTime(agent.last_run_at)}</p>}
        </div>
      </div>

      {agent.agent_memory?.feedback && (
        <div className="space-y-2">
          <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/40">Feedback</h3>
          <div className="rounded-lg border border-border bg-muted/10 p-3">
            <div className="prose prose-sm max-w-none dark:prose-invert text-xs">
              <MarkdownRenderer content={agent.agent_memory.feedback} />
            </div>
          </div>
        </div>
      )}

      <div className="space-y-2">
        <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/40">Created</h3>
        <p className="text-xs text-muted-foreground">
          {new Date(agent.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })}
        </p>
      </div>
    </div>
  );
}

// ─── Section Divider ───

function SectionDivider({ label }: { label: string }) {
  return (
    <div className="px-5 pt-6 pb-2">
      <h3 className="text-[10px] uppercase tracking-widest text-muted-foreground/30 font-medium">
        {label}
      </h3>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// MAIN COMPONENT — Single scrollable view
// ═══════════════════════════════════════════════════════════════

export function AgentContentView({
  agent,
  tasks,
  onRunTask,
  onPauseTask,
  onOpenChat,
  busy,
}: AgentContentViewProps) {
  const { setBreadcrumb } = useBreadcrumb();

  useEffect(() => {
    setBreadcrumb([{ label: agent.title }]);
  }, [agent.id, agent.title, setBreadcrumb]);

  return (
    <div className="flex flex-col h-full">
      <AgentHeader agent={agent} tasks={tasks} />

      <div className="flex-1 overflow-auto">
        {/* Dashboard section (primary) */}
        <AgentDashboard
          agent={agent}
          tasks={tasks}
        />

        {/* Tasks section */}
        <SectionDivider label="Tasks" />
        <TasksSection
          agent={agent}
          tasks={tasks}
          onRunTask={onRunTask}
          onPauseTask={onPauseTask}
          onOpenChat={onOpenChat}
          busy={busy}
        />

        {/* Agent identity section */}
        <SectionDivider label="Agent" />
        <AgentSection agent={agent} />
      </div>
    </div>
  );
}
