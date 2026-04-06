'use client';

/**
 * AgentContentView — Center panel for selected agent.
 *
 * SURFACE-ARCHITECTURE.md v5: Pinned header + three renamed tabs.
 *
 * Header (pinned): Agent name, class, domain, rhythm, freshness, actions.
 * Browse tab (default): Finder-style domain browser with per-item freshness.
 * Tasks tab: Task cards with objectives, schedule, delivery, actions.
 * Agent tab: Identity, AGENT.md, history, feedback.
 *
 * Design rationale: agents are autonomous workers maintaining a filesystem.
 * Header shows "who + when" (worker rhythm). Browse shows "what" (content
 * freshness per file). Two separate freshness signals — worker vs knowledge.
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import {
  FileText,
  Loader2,
  ChevronLeft,
  FolderOpen,
  FolderClosed,
  Play,
  Pause,
  Circle,
  MessageSquare,
  Layers,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { ContentViewer } from '@/components/workspace/ContentViewer';
import { FileIcon } from '@/components/workspace/FileIcon';
import type { Agent, Task, TaskOutput } from '@/types';

type TreeNode = import('@/types').WorkspaceTreeNode;

type Tab = 'browse' | 'tasks' | 'agent';

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
  if (days < 7) return future ? `in ${days}d` : `${days}d ago`;
  const weeks = Math.floor(days / 7);
  return future ? `in ${weeks}w` : `${weeks}w ago`;
}

function formatTimestamp(value?: string): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const diff = Date.now() - date.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  const weeks = Math.floor(days / 7);
  if (weeks < 5) return `${weeks}w ago`;
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

const CLASS_LABELS: Record<string, string> = {
  'domain-steward': 'Domain Steward',
  'synthesizer': 'Synthesizer',
  'platform-bot': 'Platform Bot',
};

// ─── Pinned Header ───

function AgentHeader({
  agent,
  tasks,
  onRunTask,
  onPauseTask,
  busy,
}: {
  agent: Agent;
  tasks: Task[];
  onRunTask: (slug: string) => void;
  onPauseTask: (slug: string) => void;
  busy: boolean;
}) {
  const cls = agent.agent_class || 'domain-steward';
  const classLabel = CLASS_LABELS[cls] || cls;
  const domain = agent.context_domain;
  const activeTasks = tasks.filter(t => t.status === 'active');
  const hasActive = activeTasks.length > 0;
  const schedule = activeTasks[0]?.schedule;

  // Most recent run across all tasks
  const lastRun = tasks
    .map(t => t.last_run_at)
    .filter(Boolean)
    .sort()
    .reverse()[0];

  // Primary active task for Run Now
  const primaryTask = activeTasks[0];

  return (
    <div className="px-5 py-3 border-b border-border shrink-0">
      {/* Line 1: Name + actions */}
      <div className="flex items-center gap-3">
        <h2 className="text-base font-medium flex-1 truncate">{agent.title}</h2>
        {primaryTask && (
          <div className="flex items-center gap-1.5 shrink-0">
            <button
              onClick={() => onRunTask(primaryTask.slug)}
              disabled={busy}
              className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded bg-primary/10 text-primary hover:bg-primary/20 disabled:opacity-50 transition-colors"
            >
              <Play className="w-3 h-3" />
              Run
            </button>
            <button
              onClick={() => onPauseTask(primaryTask.slug)}
              disabled={busy}
              className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded border border-border text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-50 transition-colors"
            >
              {primaryTask.status === 'active' ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
              {primaryTask.status === 'active' ? 'Pause' : 'Resume'}
            </button>
          </div>
        )}
      </div>

      {/* Line 2: Class · domain · rhythm · freshness */}
      <div className="flex items-center gap-1.5 mt-1 text-xs text-muted-foreground">
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
        {!hasActive && !schedule && (
          <>
            <span className="text-muted-foreground/30">·</span>
            <span className="text-muted-foreground/50">No active tasks</span>
          </>
        )}
      </div>
    </div>
  );
}

// ─── Tab Bar ───

function TabBar({
  active,
  onChange,
  taskCount,
}: {
  active: Tab;
  onChange: (t: Tab) => void;
  taskCount: number;
}) {
  const tabs: { key: Tab; label: string }[] = [
    { key: 'browse', label: 'Browse' },
    { key: 'tasks', label: taskCount > 0 ? `Tasks (${taskCount})` : 'Tasks' },
    { key: 'agent', label: 'Agent' },
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

// ═══════════════════════════════════════════════════════════════
// TAB 1: BROWSE — Finder-style domain browser
// ═══════════════════════════════════════════════════════════════

function BrowseTab({
  agent,
  tasks,
}: {
  agent: Agent;
  tasks: Task[];
}) {
  const cls = agent.agent_class || 'domain-steward';
  const domain = agent.context_domain;
  const [selectedNode, setSelectedNode] = useState<TreeNode | null>(null);

  // Reset selection when agent changes
  useEffect(() => { setSelectedNode(null); }, [agent.id]);

  return (
    <div className="flex flex-col h-full">
      {selectedNode ? (
        <div className="flex flex-col h-full">
          <button
            onClick={() => setSelectedNode(null)}
            className="flex items-center gap-1 px-5 py-2 text-sm text-muted-foreground hover:text-foreground border-b border-border shrink-0"
          >
            <ChevronLeft className="w-4 h-4" />
            Back
          </button>
          <div className="flex-1 overflow-auto">
            <ContentViewer selectedNode={selectedNode} onNavigate={setSelectedNode} />
          </div>
        </div>
      ) : cls === 'synthesizer' ? (
        <SynthesizerBrowse tasks={tasks} onSelectNode={setSelectedNode} />
      ) : domain ? (
        <DomainBrowse domain={domain} onSelectNode={setSelectedNode} />
      ) : (
        <EmptyBrowse agentClass={cls} />
      )}
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
    return <EmptyBrowse agentClass="domain-steward" />;
  }

  // Sort: folders first, then files, alphabetical within
  const sorted = [...nodes].sort((a, b) => {
    const aRank = a.type === 'folder' ? 0 : 1;
    const bRank = b.type === 'folder' ? 0 : 1;
    return aRank - bRank || a.name.localeCompare(b.name);
  });

  return (
    <div className="flex-1 overflow-auto">
      {/* Column headers */}
      <div className="grid grid-cols-[minmax(0,1fr)_80px] gap-3 px-5 py-2 text-[10px] uppercase tracking-wide text-muted-foreground/40 border-b border-border/40">
        <span>Name</span>
        <span className="text-right">Modified</span>
      </div>

      {/* File list */}
      <div className="divide-y divide-border/30">
        {sorted.map(node => (
          <button
            key={node.path}
            onClick={() => onSelectNode(node)}
            className="grid w-full grid-cols-[minmax(0,1fr)_80px] gap-3 px-5 py-2.5 text-left hover:bg-muted/30 transition-colors"
          >
            <div className="flex items-center gap-2.5 min-w-0">
              {node.type === 'folder' ? (
                <FolderClosed className="w-4 h-4 text-sky-600/60 shrink-0" />
              ) : (
                <FileIcon filename={node.name} size="md" />
              )}
              <div className="min-w-0 flex-1">
                <p className="text-sm truncate">{node.name}</p>
                {node.type === 'folder' && node.children && (
                  <p className="text-[10px] text-muted-foreground/40">
                    {node.children.length} item{node.children.length !== 1 ? 's' : ''}
                  </p>
                )}
              </div>
            </div>
            <div className="text-[11px] text-muted-foreground/50 text-right self-center tabular-nums">
              {formatTimestamp(node.updated_at)}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function SynthesizerBrowse({
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
    return <EmptyBrowse agentClass="synthesizer" />;
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
          <p className="text-[10px] uppercase tracking-wide text-muted-foreground/40 mb-1">Run history</p>
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

function EmptyBrowse({ agentClass }: { agentClass: string }) {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center">
        <FolderOpen className="w-8 h-8 text-muted-foreground/15 mx-auto mb-2" />
        <p className="text-sm text-muted-foreground/50">
          {agentClass === 'synthesizer'
            ? 'No outputs yet'
            : agentClass === 'platform-bot'
            ? 'Connect platform to populate'
            : 'Knowledge will accumulate as tasks run'}
        </p>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// TAB 2: TASKS — Task configuration + actions
// ═══════════════════════════════════════════════════════════════

function TasksTab({
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
    <div className="flex-1 overflow-auto px-5 py-4 space-y-3">
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
        <div className="text-xs text-muted-foreground space-y-0.5">
          {task.objective.deliverable && <p>· {task.objective.deliverable}</p>}
          {task.objective.audience && <p>· Audience: {task.objective.audience}</p>}
          {task.objective.purpose && <p>· Purpose: {task.objective.purpose}</p>}
        </div>
      )}

      {/* Schedule */}
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
// TAB 3: AGENT — Identity, history, feedback
// ═══════════════════════════════════════════════════════════════

function AgentTab({ agent }: { agent: Agent }) {
  const cls = agent.agent_class || 'domain-steward';
  const classLabel = CLASS_LABELS[cls] || cls;

  return (
    <div className="flex-1 overflow-auto px-5 py-4 space-y-5">
      {/* Identity */}
      <div className="space-y-2">
        <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/40">Identity</h3>
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
          <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/40">Instructions</h3>
          <div className="rounded-lg border border-border bg-muted/10 p-3">
            <div className="prose prose-sm max-w-none dark:prose-invert text-xs">
              <MarkdownRenderer content={agent.agent_instructions} />
            </div>
          </div>
        </div>
      )}

      {/* History */}
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

      {/* Feedback */}
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

      {/* Created */}
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
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════

export function AgentContentView({ agent, tasks, onRunTask, onPauseTask, onOpenChat, busy }: AgentContentViewProps) {
  const [activeTab, setActiveTab] = useState<Tab>('browse');

  // Reset to Browse tab when agent changes
  useEffect(() => { setActiveTab('browse'); }, [agent.id]);

  const taskCount = tasks.length;

  return (
    <div className="flex flex-col h-full">
      <AgentHeader
        agent={agent}
        tasks={tasks}
        onRunTask={onRunTask}
        onPauseTask={onPauseTask}
        busy={busy}
      />
      <TabBar active={activeTab} onChange={setActiveTab} taskCount={taskCount} />

      {activeTab === 'browse' && (
        <BrowseTab agent={agent} tasks={tasks} />
      )}
      {activeTab === 'tasks' && (
        <TasksTab
          agent={agent}
          tasks={tasks}
          onRunTask={onRunTask}
          onPauseTask={onPauseTask}
          onOpenChat={onOpenChat}
          busy={busy}
        />
      )}
      {activeTab === 'agent' && (
        <AgentTab agent={agent} />
      )}
    </div>
  );
}
