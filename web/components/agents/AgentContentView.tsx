'use client';

/**
 * AgentContentView — Three-tab center panel.
 *
 * SURFACE-ARCHITECTURE.md v4: Three tabs:
 * 1. Agent (default) — knowledge is the hero. Status line + domain browser / output viewer.
 * 2. Setup — task configuration, schedule, delivery, actions.
 * 3. Settings — identity, AGENT.md, history, feedback.
 *
 * Same tab structure for all agent classes — only the Agent tab hero varies.
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import {
  FileText,
  Loader2,
  ChevronLeft,
  FolderOpen,
  Play,
  Pause,
  Circle,
  ArrowRight,
  MessageSquare,
  Layers,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { ContentViewer } from '@/components/workspace/ContentViewer';
import type { Agent, Task, TaskOutput } from '@/types';

type TreeNode = import('@/types').WorkspaceTreeNode;

type Tab = 'agent' | 'setup' | 'settings';

interface AgentContentViewProps {
  agent: Agent;
  tasks: Task[];
  onRunTask: (taskSlug: string) => void;
  onPauseTask: (taskSlug: string) => void;
  onOpenChat: (prompt?: string) => void;
  busy: boolean;
}

// ─── Helpers ───

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
  const future = diff < 0;
  const absDiff = Math.abs(diff);
  const mins = Math.floor(absDiff / 60000);
  if (mins < 1) return future ? 'soon' : 'just now';
  if (mins < 60) return future ? `in ${mins}m` : `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return future ? `in ${hours}h` : `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return future ? `in ${days}d` : `${days}d ago`;
}

function getAgentDescription(agent: Agent, tasks: Task[]): string {
  const cls = agent.agent_class || 'domain-steward';
  // Use first task's objective purpose as description, or fallback
  const firstTask = tasks[0];
  if (firstTask?.objective?.purpose) return firstTask.objective.purpose;
  if (cls === 'synthesizer') return 'Cross-domain composition into executive summaries and reports';
  if (cls === 'platform-bot') return `Monitors ${agent.context_domain || 'platform'} for activity and changes`;
  return `Maintains ${agent.context_domain || 'domain'} intelligence`;
}

// ─── Tab Bar ───

function TabBar({ active, onChange }: { active: Tab; onChange: (t: Tab) => void }) {
  const tabs: { key: Tab; label: string }[] = [
    { key: 'agent', label: 'Agent' },
    { key: 'setup', label: 'Setup' },
    { key: 'settings', label: 'Settings' },
  ];

  return (
    <div className="flex gap-0 border-b border-border shrink-0">
      {tabs.map(t => (
        <button
          key={t.key}
          onClick={() => onChange(t.key)}
          className={cn(
            'px-4 py-2 text-sm font-medium transition-colors relative',
            active === t.key
              ? 'text-foreground'
              : 'text-muted-foreground hover:text-foreground'
          )}
        >
          {t.label}
          {active === t.key && (
            <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-foreground" />
          )}
        </button>
      ))}
    </div>
  );
}

// ─── Status Line (collapsed task metadata) ───

function StatusLine({
  agent,
  tasks,
  onClickSetup,
}: {
  agent: Agent;
  tasks: Task[];
  onClickSetup: () => void;
}) {
  const activeTasks = tasks.filter(t => t.status === 'active');
  const hasActive = activeTasks.length > 0;

  // Freshness: most recent last_run_at across tasks
  const lastRun = tasks
    .map(t => t.last_run_at)
    .filter(Boolean)
    .sort()
    .reverse()[0];

  // Cadence: most frequent schedule
  const schedule = activeTasks[0]?.schedule;

  // Context flow: unique reads → writes
  const reads = Array.from(new Set(tasks.flatMap(t => t.context_reads || [])));
  const writes = Array.from(new Set(tasks.flatMap(t => t.context_writes || [])));
  const flow = writes.length > 0
    ? `${writes.map(d => `${d}/`).join(', ')}${reads.length > 0 ? ` ← ${reads.filter(r => !writes.includes(r)).map(d => `${d}/`).join(', ')}` : ''}`
    : reads.length > 0
    ? `Reads: ${reads.map(d => `${d}/`).join(', ')}`
    : '';

  const statusColor = hasActive ? 'fill-green-500 text-green-500' : 'text-muted-foreground/30';

  return (
    <button
      onClick={onClickSetup}
      className="w-full flex items-center gap-2 px-5 py-1.5 text-[11px] text-muted-foreground hover:bg-muted/30 transition-colors border-b border-border"
      title="View setup details"
    >
      <Circle className={cn('w-2 h-2 shrink-0', statusColor)} />
      {hasActive ? (
        <>
          <span>Active</span>
          {lastRun && (
            <>
              <span className="text-muted-foreground/30">·</span>
              <span>Updated {formatRelativeTime(lastRun)}</span>
            </>
          )}
          {schedule && (
            <>
              <span className="text-muted-foreground/30">·</span>
              <span className="capitalize">{schedule}</span>
            </>
          )}
        </>
      ) : (
        <span>No active tasks</span>
      )}
      {flow && (
        <>
          <span className="text-muted-foreground/30 ml-auto">·</span>
          <span className="truncate max-w-[200px]">{flow}</span>
        </>
      )}
      <ArrowRight className="w-3 h-3 text-muted-foreground/30 shrink-0 ml-1" />
    </button>
  );
}

// ═══════════════════════════════════════════════════════════════
// TAB 1: AGENT — Knowledge is the hero
// ═══════════════════════════════════════════════════════════════

function AgentTab({
  agent,
  tasks,
  onClickSetup,
}: {
  agent: Agent;
  tasks: Task[];
  onClickSetup: () => void;
}) {
  const cls = agent.agent_class || 'domain-steward';
  const domain = agent.context_domain;
  const [selectedNode, setSelectedNode] = useState<TreeNode | null>(null);

  // Reset selection when agent changes
  useEffect(() => { setSelectedNode(null); }, [agent.id]);

  const description = getAgentDescription(agent, tasks);

  return (
    <div className="flex flex-col h-full">
      {/* Agent header */}
      <div className="px-5 py-3 shrink-0">
        <h2 className="text-base font-medium">{agent.title}</h2>
        <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{description}</p>
      </div>

      {/* Status line */}
      <StatusLine agent={agent} tasks={tasks} onClickSetup={onClickSetup} />

      {/* Hero content */}
      <div className="flex-1 min-h-0 overflow-auto">
        {selectedNode ? (
          <div className="flex flex-col h-full">
            <button
              onClick={() => setSelectedNode(null)}
              className="flex items-center gap-1 px-5 py-2 text-sm text-muted-foreground hover:text-foreground border-b border-border shrink-0"
            >
              <ChevronLeft className="w-4 h-4" />
              Back to overview
            </button>
            <div className="flex-1 overflow-auto">
              <ContentViewer selectedNode={selectedNode} onNavigate={setSelectedNode} />
            </div>
          </div>
        ) : (cls === 'domain-steward' || cls === 'platform-bot') && domain ? (
          <DomainBrowse domain={domain} onSelectNode={setSelectedNode} />
        ) : cls === 'synthesizer' ? (
          <SynthesizerHero tasks={tasks} onSelectNode={setSelectedNode} />
        ) : (
          <EmptyDomain />
        )}
      </div>

      {/* Latest output footer (for stewards with synthesis tasks) */}
      {cls !== 'synthesizer' && <LatestOutputFooter tasks={tasks} onSelect={setSelectedNode} />}
    </div>
  );
}

function DomainBrowse({
  domain,
  onSelectNode,
}: {
  domain: string;
  onSelectNode: (node: TreeNode) => void;
}) {
  const [nodes, setNodes] = useState<TreeNode[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.workspace.getTree(`/workspace/context/${domain}`)
      .then(tree => setNodes(Array.isArray(tree) ? tree : []))
      .catch(() => setNodes([]))
      .finally(() => setLoading(false));
  }, [domain]);

  if (loading) {
    return <div className="flex items-center justify-center py-12"><Loader2 className="w-4 h-4 animate-spin text-muted-foreground" /></div>;
  }

  if (nodes.length === 0) {
    return <EmptyDomain />;
  }

  return (
    <div className="px-3 py-2 space-y-0.5">
      {nodes.map(node => (
        <button
          key={node.path}
          onClick={() => onSelectNode(node)}
          className="w-full flex items-center gap-2 px-2 py-1.5 text-sm text-left rounded hover:bg-muted/50 transition-colors"
        >
          {node.type === 'folder' ? (
            <FolderOpen className="w-3.5 h-3.5 text-sky-600/60 shrink-0" />
          ) : (
            <FileText className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0" />
          )}
          <span className="truncate flex-1">{node.name}</span>
          {node.type === 'folder' && node.children && (
            <span className="text-[10px] text-muted-foreground/40 shrink-0">
              {node.children.length} items
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

function SynthesizerHero({
  tasks,
  onSelectNode,
}: {
  tasks: Task[];
  onSelectNode: (node: TreeNode) => void;
}) {
  const [latestOutput, setLatestOutput] = useState<TaskOutput | null>(null);
  const [outputs, setOutputs] = useState<{ taskSlug: string; taskTitle: string; output: TaskOutput }[]>([]);
  const [loading, setLoading] = useState(true);

  const synthesisTasks = useMemo(() => tasks.filter(t => t.task_class === 'synthesis'), [tasks]);

  useEffect(() => {
    if (synthesisTasks.length === 0) { setLoading(false); return; }

    // Load latest output for hero display + history
    const primary = synthesisTasks[0];
    Promise.all([
      api.tasks.getLatestOutput(primary.slug).catch(() => null),
      ...synthesisTasks.map(async task => {
        try {
          const result = await api.tasks.listOutputs(task.slug, 5);
          return (result.outputs || []).map(o => ({ taskSlug: task.slug, taskTitle: task.title, output: o }));
        } catch { return []; }
      }),
    ]).then(([latest, ...histories]) => {
      if (latest) setLatestOutput(latest);
      const flat = histories.flat().sort((a, b) => (b.output.date || '').localeCompare(a.output.date || ''));
      setOutputs(flat);
    }).finally(() => setLoading(false));
  }, [synthesisTasks]);

  if (loading) {
    return <div className="flex items-center justify-center py-12"><Loader2 className="w-4 h-4 animate-spin text-muted-foreground" /></div>;
  }

  if (!latestOutput && outputs.length === 0) {
    return (
      <div className="text-center py-12">
        <FileText className="w-8 h-8 text-muted-foreground/15 mx-auto mb-2" />
        <p className="text-sm text-muted-foreground">No outputs yet</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Hero: latest rendered output */}
      {latestOutput && (
        <div className="flex-1 min-h-0">
          {latestOutput.html_content ? (
            <iframe
              srcDoc={latestOutput.html_content}
              className="h-full min-h-[400px] w-full border-0 bg-white"
              sandbox="allow-same-origin allow-scripts"
              title="Latest output"
            />
          ) : latestOutput.content || latestOutput.md_content ? (
            <div className="p-5">
              <div className="prose prose-sm max-w-none dark:prose-invert">
                <MarkdownRenderer content={latestOutput.content || latestOutput.md_content || ''} />
              </div>
            </div>
          ) : null}
        </div>
      )}

      {/* Run history */}
      {outputs.length > 0 && (
        <div className="border-t border-border px-5 py-2 shrink-0">
          <p className="text-[10px] uppercase tracking-wide text-muted-foreground/50 mb-1">Run history</p>
          <div className="space-y-0.5">
            {outputs.slice(0, 5).map((item, i) => (
              <div key={`${item.taskSlug}-${item.output.date}-${i}`} className="flex items-center gap-2 text-xs text-muted-foreground py-0.5">
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

function LatestOutputFooter({
  tasks,
  onSelect,
}: {
  tasks: Task[];
  onSelect: (node: TreeNode) => void;
}) {
  const [latest, setLatest] = useState<{ slug: string; title: string; output: TaskOutput } | null>(null);

  const synthesisTasks = useMemo(() => tasks.filter(t => t.task_class === 'synthesis'), [tasks]);

  useEffect(() => {
    if (synthesisTasks.length === 0) return;
    const task = synthesisTasks[0];
    api.tasks.getLatestOutput(task.slug)
      .then(output => { if (output) setLatest({ slug: task.slug, title: task.title, output }); })
      .catch(() => {});
  }, [synthesisTasks]);

  if (!latest) return null;

  return (
    <div className="border-t border-border px-5 py-2 shrink-0">
      <button
        onClick={() => {
          // Create a synthetic tree node for the output
          const node: TreeNode = {
            name: `${latest.title} — ${latest.output.date || 'Latest'}`,
            path: `/tasks/${latest.slug}/outputs/latest/output.html`,
            type: 'file',
          };
          onSelect(node);
        }}
        className="w-full flex items-center gap-2 text-sm text-left hover:bg-muted/30 rounded px-1 py-1 transition-colors"
      >
        <FileText className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0" />
        <span className="truncate flex-1">Latest: {latest.title}</span>
        <span className="text-[10px] text-muted-foreground/40 shrink-0">{latest.output.date || ''}</span>
        <span className="text-[10px] text-muted-foreground/40 capitalize shrink-0">{latest.output.status}</span>
      </button>
    </div>
  );
}

function EmptyDomain() {
  return (
    <div className="text-center py-12">
      <FolderOpen className="w-8 h-8 text-muted-foreground/15 mx-auto mb-2" />
      <p className="text-sm text-muted-foreground">Knowledge will accumulate as tasks run.</p>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// TAB 2: SETUP — Task configuration + actions
// ═══════════════════════════════════════════════════════════════

function SetupTab({
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
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center max-w-xs">
          <Layers className="w-8 h-8 text-muted-foreground/15 mx-auto mb-3" />
          <p className="text-sm font-medium mb-1">No tasks assigned</p>
          <p className="text-xs text-muted-foreground mb-4">
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
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-auto px-5 py-4 space-y-4">
      <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/50">Tasks</h3>

      {tasks.map(task => (
        <TaskSetupCard
          key={task.slug}
          task={task}
          onRun={() => onRunTask(task.slug)}
          onPause={() => onPauseTask(task.slug)}
          onEdit={() => onOpenChat(`I want to update the task "${task.title}"`)}
          busy={busy}
        />
      ))}

      {/* Sources summary */}
      {tasks.some(t => (t.context_reads?.length || 0) > 0 || (t.context_writes?.length || 0) > 0) && (
        <div className="pt-2">
          <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/50 mb-2">Context Flow</h3>
          <div className="text-xs text-muted-foreground space-y-1">
            {Array.from(new Set(tasks.flatMap(t => t.context_writes || []))).map(d => (
              <div key={d} className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500/50" />
                <span>Writes to {d}/</span>
              </div>
            ))}
            {Array.from(new Set(tasks.flatMap(t => t.context_reads || []))).map(d => (
              <div key={d} className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-500/50" />
                <span>Reads from {d}/</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function TaskSetupCard({
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
  const statusColor = isActive ? 'fill-green-500 text-green-500' : task.status === 'paused' ? 'fill-amber-500 text-amber-500' : 'text-muted-foreground/30';

  return (
    <div className="border border-border rounded-lg p-4 space-y-3">
      {/* Title + status */}
      <div className="flex items-center gap-2">
        <Circle className={cn('w-2 h-2 shrink-0', statusColor)} />
        <span className="text-sm font-medium flex-1 truncate">{task.title}</span>
        <span className="text-[10px] rounded-full bg-muted px-1.5 py-0.5 text-muted-foreground capitalize">
          {task.mode || 'recurring'}
        </span>
      </div>

      {/* Objective */}
      {task.objective && (
        <div className="space-y-1">
          <p className="text-[10px] uppercase tracking-wide text-muted-foreground/50">Objective</p>
          <div className="text-xs text-muted-foreground space-y-0.5">
            {task.objective.deliverable && <p>· {task.objective.deliverable}</p>}
            {task.objective.audience && <p>· Audience: {task.objective.audience}</p>}
            {task.objective.purpose && <p>· Purpose: {task.objective.purpose}</p>}
          </div>
        </div>
      )}

      {/* Schedule */}
      <div className="space-y-1">
        <p className="text-[10px] uppercase tracking-wide text-muted-foreground/50">Schedule</p>
        <div className="text-xs text-muted-foreground space-y-0.5">
          {task.schedule && <p>· Cadence: <span className="capitalize">{task.schedule}</span></p>}
          {task.next_run_at && <p>· Next: {formatRelativeTime(task.next_run_at)}</p>}
          {task.last_run_at && <p>· Last: {formatRelativeTime(task.last_run_at)}</p>}
        </div>
      </div>

      {/* Actions */}
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

// ═══════════════════════════════════════════════════════════════
// TAB 3: SETTINGS — Identity, history, feedback
// ═══════════════════════════════════════════════════════════════

function SettingsTab({ agent }: { agent: Agent }) {
  const cls = agent.agent_class || 'domain-steward';
  const classLabel = cls === 'domain-steward' ? 'Domain Steward' : cls === 'synthesizer' ? 'Synthesizer' : 'Platform Bot';

  return (
    <div className="flex-1 overflow-auto px-5 py-4 space-y-5">
      {/* Identity */}
      <div className="space-y-2">
        <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/50">Identity</h3>
        <div className="text-xs text-muted-foreground space-y-1">
          <p>· Name: {agent.title}</p>
          <p>· Role: {agent.role} ({classLabel})</p>
          {agent.context_domain && <p>· Domain: {agent.context_domain}/</p>}
          {agent.origin && <p>· Origin: {agent.origin.replace(/_/g, ' ')}</p>}
        </div>
      </div>

      {/* Instructions (AGENT.md) */}
      {agent.agent_instructions && (
        <div className="space-y-2">
          <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/50">Instructions (AGENT.md)</h3>
          <div className="rounded-lg border border-border bg-muted/10 p-3">
            <div className="prose prose-sm max-w-none dark:prose-invert text-xs">
              <MarkdownRenderer content={agent.agent_instructions} />
            </div>
          </div>
        </div>
      )}

      {/* History */}
      <div className="space-y-2">
        <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/50">History</h3>
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

      {/* Feedback */}
      {agent.agent_memory?.feedback && (
        <div className="space-y-2">
          <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/50">Feedback</h3>
          <div className="rounded-lg border border-border bg-muted/10 p-3">
            <div className="prose prose-sm max-w-none dark:prose-invert text-xs">
              <MarkdownRenderer content={agent.agent_memory.feedback} />
            </div>
          </div>
        </div>
      )}

      {/* Created */}
      <div className="space-y-2">
        <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/50">Created</h3>
        <p className="text-xs text-muted-foreground">
          {new Date(agent.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })}
        </p>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════

export function AgentContentView({ agent, tasks, onRunTask, onPauseTask, onOpenChat, busy }: AgentContentViewProps) {
  const [activeTab, setActiveTab] = useState<Tab>('agent');

  // Reset to Agent tab when agent changes
  useEffect(() => { setActiveTab('agent'); }, [agent.id]);

  const switchToSetup = useCallback(() => setActiveTab('setup'), []);

  return (
    <div className="flex flex-col h-full">
      <TabBar active={activeTab} onChange={setActiveTab} />

      {activeTab === 'agent' && (
        <AgentTab agent={agent} tasks={tasks} onClickSetup={switchToSetup} />
      )}
      {activeTab === 'setup' && (
        <SetupTab
          agent={agent}
          tasks={tasks}
          onRunTask={onRunTask}
          onPauseTask={onPauseTask}
          onOpenChat={onOpenChat}
          busy={busy}
        />
      )}
      {activeTab === 'settings' && (
        <SettingsTab agent={agent} />
      )}
    </div>
  );
}
