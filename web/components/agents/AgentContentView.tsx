'use client';

/**
 * AgentContentView — Task-cards-as-bridge center panel.
 *
 * SURFACE-ARCHITECTURE.md v3: Three zones top to bottom:
 * 1. Agent header — who this is, what they own/read
 * 2. Task cards — what they're working on, context_reads/writes visible
 * 3. Content area — domain files (stewards), output list (synthesizers),
 *    or full render when a file/output is selected
 *
 * Same layout for all agent classes — only the content area varies.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  FileText,
  Loader2,
  ChevronLeft,
  Layers,
  Play,
  Circle,
  Clock,
  FolderOpen,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { WorkspaceTree } from '@/components/workspace/WorkspaceTree';
import { ContentViewer } from '@/components/workspace/ContentViewer';
import type { Agent, Task, TaskOutput } from '@/types';

type TreeNode = import('@/types').WorkspaceTreeNode;

interface AgentContentViewProps {
  agent: Agent;
  tasks: Task[];
  onRunTask: (taskSlug: string) => void;
  busy: boolean;
}

// ─── Agent Header ───
function AgentHeader({ agent, tasks }: { agent: Agent; tasks: Task[] }) {
  const cls = agent.agent_class || 'domain-steward';
  const domain = agent.context_domain;

  let subtitle = '';
  if (cls === 'domain-steward' && domain) {
    subtitle = `Domain: ${domain}/`;
  } else if (cls === 'synthesizer') {
    const reads = Array.from(new Set(tasks.flatMap(t => t.context_reads || [])));
    subtitle = reads.length > 0 ? `Reads across: ${reads.join(', ')}` : 'Cross-domain synthesizer';
  } else if (cls === 'platform-bot' && domain) {
    subtitle = `Platform: ${domain}`;
  }

  return (
    <div className="px-5 py-3 border-b border-border shrink-0">
      <h2 className="text-base font-medium">{agent.title}</h2>
      {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
    </div>
  );
}

// ─── Task Card ───
function TaskCard({
  task,
  onRun,
  onViewOutput,
  busy,
}: {
  task: Task;
  onRun: () => void;
  onViewOutput?: () => void;
  busy: boolean;
}) {
  const isSynthesis = task.task_class === 'synthesis';
  const reads = task.context_reads || [];
  const writes = task.context_writes || [];

  const statusColor =
    task.status === 'active' ? 'fill-green-500 text-green-500' :
    task.status === 'paused' ? 'fill-amber-500 text-amber-500' :
    'text-muted-foreground/30';

  return (
    <div className="border border-border rounded-lg px-3 py-2.5 space-y-1.5">
      {/* Title row */}
      <div className="flex items-center gap-2">
        <Circle className={cn('w-2 h-2 shrink-0', statusColor)} />
        <span className="text-sm font-medium truncate flex-1">{task.title}</span>
        <span className="text-[10px] rounded-full bg-muted px-1.5 py-0.5 text-muted-foreground shrink-0">
          {task.task_class || 'task'}
        </span>
        {task.schedule && (
          <span className="text-[10px] text-muted-foreground/50 shrink-0 flex items-center gap-0.5">
            <Clock className="w-2.5 h-2.5" />
            {task.schedule}
          </span>
        )}
      </div>

      {/* Context flow + status */}
      <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
        {writes.length > 0 && (
          <span>Writes: {writes.map(d => `${d}/`).join(', ')}</span>
        )}
        {reads.length > 0 && (
          <span>Reads: {reads.map(d => `${d}/`).join(', ')}</span>
        )}
        {task.last_run_at && (
          <span className="ml-auto">Last: {formatRelativeTime(task.last_run_at)}</span>
        )}
        {task.next_run_at && (
          <span>Next: {formatRelativeTime(task.next_run_at)}</span>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1.5">
        {isSynthesis && onViewOutput && (
          <button
            onClick={onViewOutput}
            className="flex items-center gap-1 px-2 py-0.5 text-[11px] font-medium rounded border border-border text-muted-foreground hover:text-foreground hover:bg-muted"
          >
            <FileText className="w-2.5 h-2.5" />
            View output
          </button>
        )}
        <button
          onClick={onRun}
          disabled={busy || task.status !== 'active'}
          className="flex items-center gap-1 px-2 py-0.5 text-[11px] font-medium rounded bg-primary/10 text-primary hover:bg-primary/20 disabled:opacity-50"
        >
          <Play className="w-2.5 h-2.5" />
          Run
        </button>
      </div>
    </div>
  );
}

// ─── Task Cards Section ───
function TaskCardsSection({
  tasks,
  onRunTask,
  onViewOutput,
  busy,
}: {
  tasks: Task[];
  onRunTask: (slug: string) => void;
  onViewOutput: (slug: string) => void;
  busy: boolean;
}) {
  return (
    <div className="px-5 py-3 border-b border-border shrink-0">
      <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-2">Tasks</h3>
      {tasks.length > 0 ? (
        <div className="space-y-2">
          {tasks.map(task => (
            <TaskCard
              key={task.slug}
              task={task}
              onRun={() => onRunTask(task.slug)}
              onViewOutput={task.task_class === 'synthesis' ? () => onViewOutput(task.slug) : undefined}
              busy={busy}
            />
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">No tasks assigned yet.</p>
      )}
    </div>
  );
}

// ─── Domain Browse (file list / tree for stewards + bots) ───
function DomainBrowse({
  domain,
  agentTitle,
  onSelectFile,
}: {
  domain: string;
  agentTitle: string;
  onSelectFile: (node: TreeNode) => void;
}) {
  const [nodes, setNodes] = useState<TreeNode[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.workspace.getTree(`/workspace/context/${domain}`)
      .then(tree => {
        const children = Array.isArray(tree) ? tree : [];
        setNodes(children);
      })
      .catch(() => setNodes([]))
      .finally(() => setLoading(false));
  }, [domain]);

  if (loading) {
    return <div className="flex items-center justify-center py-8"><Loader2 className="w-4 h-4 animate-spin text-muted-foreground" /></div>;
  }

  if (nodes.length === 0) {
    return (
      <div className="text-center py-8">
        <FolderOpen className="w-8 h-8 text-muted-foreground/15 mx-auto mb-2" />
        <p className="text-sm text-muted-foreground">Will accumulate as tasks execute</p>
      </div>
    );
  }

  return (
    <div className="space-y-0.5">
      {nodes.map(node => (
        <button
          key={node.path}
          onClick={() => onSelectFile(node)}
          className="w-full flex items-center gap-2 px-2 py-1.5 text-sm text-left rounded hover:bg-muted/50 transition-colors"
        >
          {node.type === 'folder' ? (
            <FolderOpen className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0" />
          ) : (
            <FileText className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0" />
          )}
          <span className="truncate">{node.name}</span>
          {node.type === 'folder' && node.children && (
            <span className="text-[10px] text-muted-foreground/40 ml-auto shrink-0">
              {node.children.length} items
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

// ─── Output Browse (output list for synthesizers) ───
function OutputBrowse({
  tasks,
  onSelectOutput,
}: {
  tasks: Task[];
  onSelectOutput: (taskSlug: string, output: TaskOutput) => void;
}) {
  const [outputs, setOutputs] = useState<{ taskSlug: string; taskTitle: string; output: TaskOutput }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const synthesisTasks = tasks.filter(t => t.task_class === 'synthesis');
    if (synthesisTasks.length === 0) { setLoading(false); return; }

    Promise.all(
      synthesisTasks.map(async task => {
        try {
          const result = await api.tasks.listOutputs(task.slug, 5);
          return (result.outputs || []).map(o => ({ taskSlug: task.slug, taskTitle: task.title, output: o }));
        } catch { return []; }
      })
    ).then(results => {
      const flat = results.flat().sort((a, b) => (b.output.date || '').localeCompare(a.output.date || ''));
      setOutputs(flat);
    }).finally(() => setLoading(false));
  }, [tasks]);

  if (loading) {
    return <div className="flex items-center justify-center py-8"><Loader2 className="w-4 h-4 animate-spin text-muted-foreground" /></div>;
  }

  if (outputs.length === 0) {
    return (
      <div className="text-center py-8">
        <FileText className="w-8 h-8 text-muted-foreground/15 mx-auto mb-2" />
        <p className="text-sm text-muted-foreground">No outputs yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-0.5">
      {outputs.map((item, i) => (
        <button
          key={`${item.taskSlug}-${item.output.folder || item.output.date}-${i}`}
          onClick={() => onSelectOutput(item.taskSlug, item.output)}
          className="w-full flex items-center gap-2 px-2 py-2 text-sm text-left rounded hover:bg-muted/50 transition-colors"
        >
          <FileText className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0" />
          <div className="min-w-0 flex-1">
            <p className="truncate">{item.taskTitle}</p>
            <p className="text-[11px] text-muted-foreground/50">{item.output.date || item.output.folder}</p>
          </div>
          <span className="text-[10px] text-muted-foreground/40 capitalize shrink-0">{item.output.status}</span>
        </button>
      ))}
    </div>
  );
}

// ─── Full File Viewer ───
function FileView({
  node,
  onBack,
}: {
  node: TreeNode;
  onBack: () => void;
}) {
  return (
    <div className="flex flex-col h-full">
      <button onClick={onBack} className="flex items-center gap-1 px-5 py-2 text-sm text-muted-foreground hover:text-foreground border-b border-border shrink-0">
        <ChevronLeft className="w-4 h-4" />
        Back to overview
      </button>
      <div className="flex-1 overflow-auto">
        <ContentViewer selectedNode={node} onNavigate={() => {}} />
      </div>
    </div>
  );
}

// ─── Full Output Viewer ───
function OutputView({
  output,
  title,
  onBack,
}: {
  output: TaskOutput;
  title: string;
  onBack: () => void;
}) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-5 py-2 border-b border-border shrink-0">
        <button onClick={onBack} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ChevronLeft className="w-4 h-4" />
          Back to overview
        </button>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="rounded-full bg-muted px-2 py-0.5">{output.date || 'Latest'}</span>
          <span className="rounded-full bg-muted px-2 py-0.5 capitalize">{output.status}</span>
        </div>
      </div>
      <div className="flex-1 overflow-auto">
        {output.html_content ? (
          <iframe
            srcDoc={output.html_content}
            className="h-full min-h-[600px] w-full border-0 bg-white"
            sandbox="allow-same-origin allow-scripts"
            title={title}
          />
        ) : output.content || output.md_content ? (
          <div className="p-5">
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <MarkdownRenderer content={output.content || output.md_content || ''} />
            </div>
          </div>
        ) : (
          <div className="p-8 text-center text-sm text-muted-foreground">No preview available.</div>
        )}
      </div>
    </div>
  );
}

// ─── Main Component ───
export function AgentContentView({ agent, tasks, onRunTask, busy }: AgentContentViewProps) {
  const [selectedFile, setSelectedFile] = useState<TreeNode | null>(null);
  const [selectedOutput, setSelectedOutput] = useState<{ taskSlug: string; output: TaskOutput } | null>(null);

  // Reset selection when agent changes
  useEffect(() => {
    setSelectedFile(null);
    setSelectedOutput(null);
  }, [agent.id]);

  const cls = agent.agent_class || 'domain-steward';
  const domain = agent.context_domain;

  const handleBack = () => {
    setSelectedFile(null);
    setSelectedOutput(null);
  };

  const handleViewOutput = (taskSlug: string) => {
    // Fetch the latest output for this task and display it
    api.tasks.getLatestOutput(taskSlug).then(output => {
      if (output) setSelectedOutput({ taskSlug, output });
    }).catch(() => {});
  };

  // ── If a file is selected, show full render ──
  if (selectedFile) {
    return (
      <div className="flex flex-col h-full">
        <AgentHeader agent={agent} tasks={tasks} />
        <TaskCardsSection tasks={tasks} onRunTask={onRunTask} onViewOutput={handleViewOutput} busy={busy} />
        <div className="flex-1 min-h-0 overflow-hidden">
          <FileView node={selectedFile} onBack={handleBack} />
        </div>
      </div>
    );
  }

  // ── If an output is selected, show full render ──
  if (selectedOutput) {
    const taskTitle = tasks.find(t => t.slug === selectedOutput.taskSlug)?.title || selectedOutput.taskSlug;
    return (
      <div className="flex flex-col h-full">
        <AgentHeader agent={agent} tasks={tasks} />
        <TaskCardsSection tasks={tasks} onRunTask={onRunTask} onViewOutput={handleViewOutput} busy={busy} />
        <div className="flex-1 min-h-0 overflow-hidden">
          <OutputView output={selectedOutput.output} title={taskTitle} onBack={handleBack} />
        </div>
      </div>
    );
  }

  // ── Default: browse mode ──
  return (
    <div className="flex flex-col h-full">
      <AgentHeader agent={agent} tasks={tasks} />
      <TaskCardsSection tasks={tasks} onRunTask={onRunTask} onViewOutput={handleViewOutput} busy={busy} />

      {/* Content area — varies by class */}
      <div className="flex-1 min-h-0 overflow-auto px-5 py-3">
        {(cls === 'domain-steward' || cls === 'platform-bot') && domain ? (
          <>
            <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-2">
              {cls === 'platform-bot' ? `Observations: ${domain}/` : `Domain: ${domain}/`}
            </h3>
            <DomainBrowse domain={domain} agentTitle={agent.title} onSelectFile={setSelectedFile} />
          </>
        ) : cls === 'synthesizer' ? (
          <>
            <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-2">Outputs</h3>
            <OutputBrowse tasks={tasks} onSelectOutput={(slug, output) => setSelectedOutput({ taskSlug: slug, output })} />
          </>
        ) : (
          <div className="text-center py-8">
            <Layers className="w-8 h-8 text-muted-foreground/15 mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">No content to display</p>
          </div>
        )}
      </div>
    </div>
  );
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
