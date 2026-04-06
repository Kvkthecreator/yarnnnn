'use client';

/**
 * AgentContentView — Center panel for selected agent.
 *
 * SURFACE-ARCHITECTURE.md v7.2: Task-class-aware tabs.
 *
 * BI + Intelligence Room framing:
 *   Report tab — latest deliverables (synthesis task outputs)
 *   Data tab — accumulated context (domain entity view)
 *   Pipeline tab — task config, schedule, actions
 *   Agent tab — identity, instructions, history
 *
 * Tab visibility depends on task_class presence, not agent_class.
 * Report is default when synthesis outputs exist; Data otherwise.
 */

import { useState, useEffect, useMemo } from 'react';
import { useBreadcrumb } from '@/contexts/BreadcrumbContext';
import {
  Play,
  Pause,
  Circle,
  MessageSquare,
  Layers,
  Brain,
  Plug,
  FileText,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { AgentDashboard } from '@/components/agents/AgentDashboard';
import { avatarColor } from '@/lib/agent-identity';
import { formatRelativeTime } from '@/lib/formatting';
import type { Agent, Task, TaskOutput } from '@/types';

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

// ─── Work State (fetched once, shared across header) ───

interface WorkState {
  entityCount: number;
  recentEntityCount: number;  // updated in last 24h
  synthesisOutputCount: number;
  lastEntityUpdate: string | null;
}

// ─── Pinned Header ───

function AgentHeader({ agent, tasks, workState }: { agent: Agent; tasks: Task[]; workState: WorkState | null }) {
  const cls = agent.agent_class || 'domain-steward';
  const classLabel = CLASS_LABELS[cls] || cls;
  const domain = agent.context_domain;
  const activeTasks = tasks.filter(t => t.status === 'active');
  const schedule = activeTasks[0]?.schedule;
  const color = avatarColor(agent.role);
  const mandate = getAgentMandate(agent);
  const lastRun = tasks.map(t => t.last_run_at).filter(Boolean).sort().reverse()[0];

  // Health signal: all fresh, some stale, or empty
  const healthSignal = workState
    ? workState.entityCount === 0 ? 'empty'
      : workState.recentEntityCount === workState.entityCount ? 'fresh'
      : workState.recentEntityCount > 0 ? 'partial'
      : 'stale'
    : null;

  const healthColor = healthSignal === 'fresh' ? 'bg-green-500' : healthSignal === 'partial' ? 'bg-amber-500' : healthSignal === 'stale' ? 'bg-red-400' : 'bg-muted-foreground/20';

  return (
    <div className="px-5 py-3 border-b border-border shrink-0">
      {/* Line 1: Avatar + Name + Mandate */}
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

      {/* Line 2: Identity signals */}
      <div className="flex items-center gap-1.5 mt-2 text-xs text-muted-foreground">
        <span>{classLabel}</span>
        {domain && (
          <><span className="text-muted-foreground/30">·</span><span>{domain}/</span></>
        )}
        {schedule && (
          <><span className="text-muted-foreground/30">·</span><span className="capitalize">Works {schedule}</span></>
        )}
        {lastRun && (
          <><span className="text-muted-foreground/30">·</span><span>Ran {formatRelativeTime(lastRun)}</span></>
        )}
        {!activeTasks.length && !schedule && (
          <><span className="text-muted-foreground/30">·</span><span className="text-muted-foreground/50">No active tasks</span></>
        )}
      </div>

      {/* Line 3: Work-state signals (only when we have data) */}
      {workState && workState.entityCount > 0 && (
        <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <span className={cn('w-1.5 h-1.5 rounded-full', healthColor)} />
            <span>{workState.entityCount} entities tracked</span>
          </div>
          {workState.recentEntityCount > 0 && workState.recentEntityCount < workState.entityCount && (
            <span>{workState.recentEntityCount} updated recently</span>
          )}
          {workState.synthesisOutputCount > 0 && (
            <><span className="text-muted-foreground/30">·</span><span>{workState.synthesisOutputCount} reports</span></>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Tab Bar (adaptive) ───

type TabKey = 'report' | 'data' | 'pipeline' | 'agent';

interface TabDef {
  key: TabKey;
  label: string;
}

function TabBar({ tabs, active, onChange }: { tabs: TabDef[]; active: TabKey; onChange: (t: TabKey) => void }) {
  return (
    <div className="flex gap-0 border-b border-border shrink-0">
      {tabs.map(t => (
        <button
          key={t.key}
          onClick={() => onChange(t.key)}
          className={cn(
            'px-4 py-2 text-sm font-medium transition-colors relative',
            active === t.key ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
          )}
        >
          {t.label}
          {active === t.key && <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-foreground" />}
        </button>
      ))}
    </div>
  );
}

// ─── Report Tab ───

function ReportTab({ tasks }: { tasks: Task[] }) {
  const synthesisTasks = useMemo(() => tasks.filter(t => t.task_class === 'synthesis'), [tasks]);
  const [latestOutput, setLatestOutput] = useState<{ html?: string; md?: string; date?: string; taskTitle?: string } | null>(null);
  const [outputs, setOutputs] = useState<{ taskSlug: string; taskTitle: string; output: TaskOutput }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (synthesisTasks.length === 0) { setLoading(false); return; }

    const primary = synthesisTasks[0];
    Promise.all([
      api.tasks.getLatestOutput(primary.slug).catch(() => null),
      ...synthesisTasks.map(async task => {
        try {
          const result = await api.tasks.listOutputs(task.slug, 5);
          return (result.outputs || []).map((o: TaskOutput) => ({ taskSlug: task.slug, taskTitle: task.title, output: o }));
        } catch { return []; }
      }),
    ]).then(([latest, ...histories]) => {
      if (latest) {
        setLatestOutput({
          html: latest.html_content,
          md: latest.content || latest.md_content,
          date: latest.date,
          taskTitle: primary.title,
        });
      }
      const flat = histories.flat().sort((a, b) => (b.output.date || '').localeCompare(a.output.date || ''));
      setOutputs(flat);
    }).finally(() => setLoading(false));
  }, [synthesisTasks.map(t => t.slug).join(',')]); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) {
    return <div className="flex items-center justify-center py-16"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>;
  }

  if (!latestOutput && outputs.length === 0) {
    return (
      <div className="px-5 py-12 text-center">
        <FileText className="w-10 h-10 text-muted-foreground/15 mx-auto mb-3" />
        <p className="text-sm text-muted-foreground">No reports yet</p>
        <p className="text-xs text-muted-foreground/50 mt-1">
          Reports will appear here once synthesis tasks produce their first output.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Hero: latest rendered output */}
      {latestOutput && (
        <>
          {latestOutput.date && (
            <div className="px-5 py-2 text-[11px] text-muted-foreground/50 border-b border-border/40 flex items-center gap-2">
              <span>Latest: {latestOutput.taskTitle}</span>
              <span className="text-muted-foreground/20">·</span>
              <span>{latestOutput.date}</span>
            </div>
          )}
          <div className="flex-1 min-h-0 overflow-auto">
            {latestOutput.html ? (
              <iframe
                srcDoc={latestOutput.html}
                className="h-full min-h-[500px] w-full border-0 bg-white"
                sandbox="allow-same-origin allow-scripts"
                title="Latest report"
              />
            ) : latestOutput.md ? (
              <div className="p-5">
                <div className="prose prose-sm max-w-none dark:prose-invert">
                  <MarkdownRenderer content={latestOutput.md} />
                </div>
              </div>
            ) : null}
          </div>
        </>
      )}

      {/* Version history */}
      {outputs.length > 0 && (
        <div className="border-t border-border px-5 py-3 shrink-0">
          <p className="text-[10px] uppercase tracking-wide text-muted-foreground/40 mb-1.5">History</p>
          <div className="space-y-0.5">
            {outputs.slice(0, 5).map((item, i) => (
              <div key={`${item.taskSlug}-${item.output.date}-${i}`} className="flex items-center gap-2 text-xs text-muted-foreground py-0.5">
                <span className="font-medium">{item.taskTitle}</span>
                <span className="text-muted-foreground/30">·</span>
                <span>{item.output.date || item.output.folder}</span>
                <span className="text-muted-foreground/30">·</span>
                <span className="capitalize">{item.output.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Pipeline Tab (was Tasks) ───

function PipelineTab({
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
        <p className="text-xs text-muted-foreground mb-3">Assign a task to this agent to get started.</p>
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

function TaskCard({ task, onRun, onPause, onEdit, busy }: {
  task: Task; onRun: () => void; onPause: () => void; onEdit: () => void; busy: boolean;
}) {
  const isActive = task.status === 'active';
  const statusColor = isActive
    ? 'fill-green-500 text-green-500'
    : task.status === 'paused' ? 'fill-amber-500 text-amber-500' : 'text-muted-foreground/30';

  return (
    <div className="border border-border rounded-lg p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Circle className={cn('w-2 h-2 shrink-0', statusColor)} />
        <span className="text-sm font-medium flex-1 truncate">{task.title}</span>
        <span className="text-[10px] rounded-full bg-muted px-1.5 py-0.5 text-muted-foreground capitalize">{task.mode || 'recurring'}</span>
        {task.task_class && (
          <span className={cn(
            'text-[10px] rounded-full px-1.5 py-0.5',
            task.task_class === 'context' ? 'bg-blue-500/10 text-blue-600' : 'bg-green-500/10 text-green-600'
          )}>
            {task.task_class}
          </span>
        )}
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
        {task.next_run_at && <><span className="text-muted-foreground/30">·</span><span>Next: {formatRelativeTime(task.next_run_at)}</span></>}
        {task.last_run_at && <><span className="text-muted-foreground/30">·</span><span>Last: {formatRelativeTime(task.last_run_at)}</span></>}
      </div>
      <div className="flex items-center gap-2 pt-1">
        <button onClick={onRun} disabled={busy || !isActive} className="flex items-center gap-1 px-3 py-1 text-xs font-medium rounded bg-primary/10 text-primary hover:bg-primary/20 disabled:opacity-50">
          <Play className="w-3 h-3" /> Run Now
        </button>
        <button onClick={onPause} disabled={busy} className="flex items-center gap-1 px-3 py-1 text-xs font-medium rounded border border-border text-muted-foreground hover:text-foreground hover:bg-muted">
          {isActive ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
          {isActive ? 'Pause' : 'Resume'}
        </button>
        <button onClick={onEdit} className="flex items-center gap-1 px-3 py-1 text-xs font-medium rounded border border-border text-muted-foreground hover:text-foreground hover:bg-muted ml-auto">
          <MessageSquare className="w-3 h-3" /> Edit via TP
        </button>
      </div>
    </div>
  );
}

// ─── Agent Tab ───

function AgentTab({ agent }: { agent: Agent }) {
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
                <span className={cn('ml-1', agent.quality_trend === 'improving' && 'text-green-500', agent.quality_trend === 'declining' && 'text-red-500')}>
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

// ═══════════════════════════════════════════════════════════════
// MAIN — Task-class-aware tabs
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
  const [workState, setWorkState] = useState<WorkState | null>(null);

  // Fetch work-state signals for the header
  useEffect(() => {
    setWorkState(null);
    const domain = agent.context_domain;
    const synthesisTasks = tasks.filter(t => t.task_class === 'synthesis');

    const promises: Promise<void>[] = [];

    // Domain entity stats
    if (domain) {
      promises.push(
        api.workspace.getDomainEntities(domain).then(data => {
          const entities = data.entities || [];
          const now = Date.now();
          const recentCount = entities.filter(
            e => e.last_updated && (now - new Date(e.last_updated).getTime()) < 86400000
          ).length;
          const allUpdates = entities.map(e => e.last_updated).filter(Boolean).sort().reverse();

          setWorkState(prev => ({
            entityCount: data.entity_count || entities.length,
            recentEntityCount: recentCount,
            synthesisOutputCount: prev?.synthesisOutputCount ?? 0,
            lastEntityUpdate: allUpdates[0] || null,
          }));
        }).catch(() => {})
      );
    }

    // Synthesis output count
    if (synthesisTasks.length > 0) {
      promises.push(
        Promise.all(
          synthesisTasks.map(t => api.tasks.listOutputs(t.slug, 1).then(r => r.total || 0).catch(() => 0))
        ).then(counts => {
          const total = counts.reduce((a, b) => a + b, 0);
          setWorkState(prev => ({
            entityCount: prev?.entityCount ?? 0,
            recentEntityCount: prev?.recentEntityCount ?? 0,
            synthesisOutputCount: total,
            lastEntityUpdate: prev?.lastEntityUpdate ?? null,
          }));
        })
      );
    }
  }, [agent.id, agent.context_domain, tasks.map(t => t.slug).join(',')]); // eslint-disable-line react-hooks/exhaustive-deps

  // Derive which tabs to show based on task classes
  const hasSynthesisTasks = tasks.some(t => t.task_class === 'synthesis');
  const hasContextDomain = !!agent.context_domain;

  const availableTabs = useMemo<TabDef[]>(() => {
    const tabs: TabDef[] = [];
    if (hasSynthesisTasks) tabs.push({ key: 'report', label: 'Report' });
    if (hasContextDomain) tabs.push({ key: 'data', label: 'Data' });
    tabs.push({ key: 'pipeline', label: tasks.length > 0 ? `Pipeline (${tasks.length})` : 'Pipeline' });
    tabs.push({ key: 'agent', label: 'Agent' });
    return tabs;
  }, [hasSynthesisTasks, hasContextDomain, tasks.length]);

  const defaultTab = hasSynthesisTasks ? 'report' : hasContextDomain ? 'data' : 'pipeline';
  const [activeTab, setActiveTab] = useState<TabKey>(defaultTab);

  // Reset to appropriate default when agent changes
  useEffect(() => {
    const newDefault = hasSynthesisTasks ? 'report' : hasContextDomain ? 'data' : 'pipeline';
    setActiveTab(newDefault);
  }, [agent.id, hasSynthesisTasks, hasContextDomain]);

  // Ensure active tab is valid
  const validTab = availableTabs.some(t => t.key === activeTab) ? activeTab : availableTabs[0]?.key || 'pipeline';

  useEffect(() => {
    setBreadcrumb([{ label: agent.title }]);
  }, [agent.id, agent.title, setBreadcrumb]);

  return (
    <div className="flex flex-col h-full">
      <AgentHeader agent={agent} tasks={tasks} workState={workState} />
      <TabBar tabs={availableTabs} active={validTab} onChange={setActiveTab} />

      <div className="flex-1 overflow-auto">
        {validTab === 'report' && <ReportTab tasks={tasks} />}
        {validTab === 'data' && <AgentDashboard agent={agent} tasks={tasks} />}
        {validTab === 'pipeline' && (
          <PipelineTab agent={agent} tasks={tasks} onRunTask={onRunTask} onPauseTask={onPauseTask} onOpenChat={onOpenChat} busy={busy} />
        )}
        {validTab === 'agent' && <AgentTab agent={agent} />}
      </div>
    </div>
  );
}
