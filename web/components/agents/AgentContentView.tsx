'use client';

/**
 * AgentContentView — Agent-class-aware center panel dispatcher.
 *
 * SURFACE-ARCHITECTURE.md v3:
 * - Domain stewards → directory explorer of their context domain + responsibilities
 * - Synthesizers → latest output + run history + responsibilities
 * - Platform bots → temporal observations directory + connection status
 * - Task drill-down → reuses existing OutputView / DeliverableView / RunHistoryView
 */

import { useState, useEffect, useCallback } from 'react';
import {
  FileText,
  Loader2,
  ChevronLeft,
  Layers,
  Play,
  CheckCircle2,
  ChevronRight,
  Users,
  Clock,
  Circle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { WorkspaceTree } from '@/components/workspace/WorkspaceTree';
import { ContentViewer } from '@/components/workspace/ContentViewer';
import type { Agent, Task, TaskDetail, TaskOutput } from '@/types';
import type { AgentView } from './AgentTreeNav';

type TreeNode = import('@/types').WorkspaceTreeNode;

interface AgentContentViewProps {
  agent: Agent;
  tasks: Task[];
  view: AgentView;
  selectedTaskSlug: string | null;
  onBack: () => void;
  onSelectTask: (taskSlug: string) => void;
  onRunTask: (taskSlug: string) => void;
  busy: boolean;
}

// ─── Responsibilities Section (shared across views) ───
function ResponsibilitiesSection({
  tasks,
  onSelectTask,
  onRunTask,
  busy,
}: {
  tasks: Task[];
  onSelectTask: (slug: string) => void;
  onRunTask: (slug: string) => void;
  busy: boolean;
}) {
  if (tasks.length === 0) return null;

  return (
    <div className="border-t border-border px-5 py-4 shrink-0">
      <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-2">
        Responsibilities
      </h3>
      <div className="space-y-1.5">
        {tasks.map(task => {
          const statusColor =
            task.status === 'active' ? 'fill-green-500 text-green-500' :
            task.status === 'paused' ? 'fill-amber-500 text-amber-500' :
            'text-muted-foreground/30';
          return (
            <div
              key={task.slug}
              className="flex items-center gap-2 text-sm group cursor-pointer hover:bg-muted/50 rounded-md px-2 py-1.5 -mx-2"
              onClick={() => onSelectTask(task.slug)}
            >
              <Circle className={cn('w-2 h-2 shrink-0', statusColor)} />
              <span className="flex-1 truncate">{task.title}</span>
              <span className="text-[11px] text-muted-foreground/50">{task.schedule || task.mode}</span>
              {task.last_run_at && (
                <span className="text-[11px] text-muted-foreground/40">
                  {formatRelativeTime(task.last_run_at)}
                </span>
              )}
              <button
                onClick={(e) => { e.stopPropagation(); onRunTask(task.slug); }}
                disabled={busy || task.status !== 'active'}
                className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-primary/10 text-primary disabled:opacity-30"
              >
                <Play className="w-3 h-3" />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Domain Steward View ───
function DomainView({
  agent,
  tasks,
  onSelectTask,
  onRunTask,
  busy,
}: {
  agent: Agent;
  tasks: Task[];
  onSelectTask: (slug: string) => void;
  onRunTask: (slug: string) => void;
  busy: boolean;
}) {
  const [treeNodes, setTreeNodes] = useState<TreeNode[]>([]);
  const [selectedNode, setSelectedNode] = useState<TreeNode | null>(null);
  const [loading, setLoading] = useState(true);

  const domain = agent.context_domain;

  const loadTree = useCallback(async () => {
    if (!domain) { setLoading(false); return; }
    setLoading(true);
    try {
      const tree = await api.workspace.getTree(`/workspace/context/${domain}`);
      const children = Array.isArray(tree) ? tree : [];
      setTreeNodes([{
        name: agent.title,
        path: `/workspace/context/${domain}`,
        type: 'folder',
        children,
      }]);
    } catch {
      setTreeNodes([]);
    }
    setLoading(false);
  }, [domain, agent.title]);

  useEffect(() => { loadTree(); }, [loadTree]);

  if (loading) {
    return <div className="flex items-center justify-center h-full"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>;
  }

  if (!domain || treeNodes.length === 0) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="text-center max-w-sm">
            <Layers className="w-10 h-10 text-muted-foreground/15 mx-auto mb-3" />
            <h3 className="text-sm font-medium mb-1">No domain content yet</h3>
            <p className="text-sm text-muted-foreground">
              This agent&apos;s domain will accumulate as tasks execute.
            </p>
          </div>
        </div>
        <ResponsibilitiesSection tasks={tasks} onSelectTask={onSelectTask} onRunTask={onRunTask} busy={busy} />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 flex min-h-0">
        {/* Mini tree nav */}
        <div className="w-[200px] shrink-0 border-r border-border overflow-y-auto bg-muted/10">
          <div className="p-2">
            <WorkspaceTree
              nodes={treeNodes}
              selectedPath={selectedNode?.path}
              onSelect={setSelectedNode}
            />
          </div>
        </div>
        {/* Content viewer */}
        <div className="flex-1 min-w-0 overflow-hidden">
          {selectedNode ? (
            <ContentViewer selectedNode={selectedNode} onNavigate={setSelectedNode} />
          ) : (
            <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
              Select a file to view
            </div>
          )}
        </div>
      </div>
      <ResponsibilitiesSection tasks={tasks} onSelectTask={onSelectTask} onRunTask={onRunTask} busy={busy} />
    </div>
  );
}

// ─── Synthesizer View (Output + Run History) ───
function SynthesizerView({
  agent,
  tasks,
  onSelectTask,
  onRunTask,
  busy,
}: {
  agent: Agent;
  tasks: Task[];
  onSelectTask: (slug: string) => void;
  onRunTask: (slug: string) => void;
  busy: boolean;
}) {
  const [outputs, setOutputs] = useState<TaskOutput[]>([]);
  const [selectedOutput, setSelectedOutput] = useState<TaskOutput | null>(null);
  const [loading, setLoading] = useState(true);

  // Load outputs from all synthesis tasks
  useEffect(() => {
    const synthesisTasks = tasks.filter(t => t.task_class === 'synthesis');
    if (synthesisTasks.length === 0) { setLoading(false); return; }

    const primaryTask = synthesisTasks[0]; // Show first synthesis task's outputs
    api.tasks.listOutputs(primaryTask.slug, 10).then(r => r.outputs || [])
      .then(outs => {
        setOutputs(outs || []);
        if (outs && outs.length > 0) setSelectedOutput(outs[0]);
      })
      .catch(() => setOutputs([]))
      .finally(() => setLoading(false));
  }, [tasks]);

  if (loading) {
    return <div className="flex items-center justify-center h-full"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>;
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 min-h-0 overflow-auto">
        {selectedOutput ? (
          <div className="flex flex-col h-full">
            {/* Output header */}
            <div className="border-b border-border px-5 py-3 shrink-0">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span className="rounded-full bg-muted px-2 py-0.5">{selectedOutput.date || 'Latest'}</span>
                  <span className="rounded-full bg-muted px-2 py-0.5 capitalize">{selectedOutput.status}</span>
                </div>
              </div>
            </div>
            {/* Output content */}
            <div className="flex-1 overflow-auto">
              {selectedOutput.html_content ? (
                <iframe
                  srcDoc={selectedOutput.html_content}
                  className="h-full min-h-[600px] w-full border-0 bg-white"
                  sandbox="allow-same-origin allow-scripts"
                  title={`${agent.title} output`}
                />
              ) : selectedOutput.content || selectedOutput.md_content ? (
                <div className="p-5">
                  <div className="prose prose-sm max-w-none dark:prose-invert">
                    <MarkdownRenderer content={selectedOutput.content || selectedOutput.md_content || ''} />
                  </div>
                </div>
              ) : (
                <div className="p-8 text-center text-sm text-muted-foreground">No preview available.</div>
              )}
            </div>

            {/* Run history */}
            {outputs.length > 1 && (
              <div className="border-t border-border px-5 py-3 shrink-0">
                <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-2">Run History</h3>
                <div className="space-y-1">
                  {outputs.slice(0, 5).map(o => (
                    <button
                      key={o.folder || o.date}
                      onClick={() => setSelectedOutput(o)}
                      className={cn(
                        'w-full flex items-center gap-2 px-2 py-1 rounded text-sm hover:bg-muted/50',
                        (o.folder || o.date) === (selectedOutput.folder || selectedOutput.date) && 'bg-primary/5'
                      )}
                    >
                      <CheckCircle2 className="w-3.5 h-3.5 text-muted-foreground/40" />
                      <span>{o.date || o.folder}</span>
                      <span className="text-xs text-muted-foreground capitalize ml-auto">{o.status}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full p-8">
            <div className="text-center max-w-sm">
              <FileText className="w-10 h-10 text-muted-foreground/15 mx-auto mb-3" />
              <h3 className="text-sm font-medium mb-1">No outputs yet</h3>
              <p className="text-sm text-muted-foreground">
                This agent hasn&apos;t produced any deliverables yet.
              </p>
            </div>
          </div>
        )}
      </div>
      <ResponsibilitiesSection tasks={tasks} onSelectTask={onSelectTask} onRunTask={onRunTask} busy={busy} />
    </div>
  );
}

// ─── Platform Bot View ───
function BotView({
  agent,
  tasks,
  onSelectTask,
  onRunTask,
  busy,
}: {
  agent: Agent;
  tasks: Task[];
  onSelectTask: (slug: string) => void;
  onRunTask: (slug: string) => void;
  busy: boolean;
}) {
  const [treeNodes, setTreeNodes] = useState<TreeNode[]>([]);
  const [selectedNode, setSelectedNode] = useState<TreeNode | null>(null);
  const [loading, setLoading] = useState(true);

  const domain = agent.context_domain;

  useEffect(() => {
    if (!domain) { setLoading(false); return; }
    api.workspace.getTree(`/workspace/context/${domain}`)
      .then(tree => {
        const children = Array.isArray(tree) ? tree : [];
        setTreeNodes([{
          name: agent.title,
          path: `/workspace/context/${domain}`,
          type: 'folder',
          children,
        }]);
      })
      .catch(() => setTreeNodes([]))
      .finally(() => setLoading(false));
  }, [domain, agent.title]);

  if (loading) {
    return <div className="flex items-center justify-center h-full"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>;
  }

  return (
    <div className="flex flex-col h-full">
      {treeNodes.length > 0 ? (
        <div className="flex-1 flex min-h-0">
          <div className="w-[200px] shrink-0 border-r border-border overflow-y-auto bg-muted/10">
            <div className="p-2">
              <WorkspaceTree
                nodes={treeNodes}
                selectedPath={selectedNode?.path}
                onSelect={setSelectedNode}
              />
            </div>
          </div>
          <div className="flex-1 min-w-0 overflow-hidden">
            {selectedNode ? (
              <ContentViewer selectedNode={selectedNode} onNavigate={setSelectedNode} />
            ) : (
              <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
                Select a file to view
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="text-center max-w-sm">
            <Layers className="w-10 h-10 text-muted-foreground/15 mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">No observations yet. Connect the platform to start.</p>
          </div>
        </div>
      )}
      <ResponsibilitiesSection tasks={tasks} onSelectTask={onSelectTask} onRunTask={onRunTask} busy={busy} />
    </div>
  );
}

// ─── Task Drill-Down View ───
function TaskDrillDown({
  taskSlug,
  onBack,
  onRunTask,
  busy,
}: {
  taskSlug: string;
  onBack: () => void;
  onRunTask: (slug: string) => void;
  busy: boolean;
}) {
  const [task, setTask] = useState<TaskDetail | null>(null);
  const [outputs, setOutputs] = useState<TaskOutput[]>([]);
  const [selectedOutput, setSelectedOutput] = useState<TaskOutput | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.tasks.get(taskSlug),
      api.tasks.listOutputs(taskSlug, 10),
    ]).then(([taskData, outputsResult]) => {
      setTask(taskData);
      const outs = outputsResult?.outputs || [];
      setOutputs(outs);
      if (outs.length > 0) setSelectedOutput(outs[0]);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [taskSlug]);

  if (loading || !task) {
    return <div className="flex items-center justify-center h-full"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>;
  }

  return (
    <div className="flex flex-col h-full">
      {/* Back header */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-border shrink-0">
        <button onClick={onBack} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ChevronLeft className="w-4 h-4" />
          Back
        </button>
        <span className="text-sm font-medium truncate">{task.title}</span>
        <div className="ml-auto flex items-center gap-2">
          {task.schedule && (
            <span className="text-[11px] text-muted-foreground flex items-center gap-0.5">
              <Clock className="w-3 h-3" />
              {task.schedule}
            </span>
          )}
          <button
            onClick={() => onRunTask(task.slug)}
            disabled={busy}
            className="flex items-center gap-1 px-2 py-1 text-xs font-medium rounded bg-primary/10 text-primary hover:bg-primary/20 disabled:opacity-50"
          >
            <Play className="w-3 h-3" />
            Run
          </button>
        </div>
      </div>

      {/* Output content */}
      <div className="flex-1 overflow-auto">
        {selectedOutput ? (
          <>
            {selectedOutput.html_content ? (
              <iframe
                srcDoc={selectedOutput.html_content}
                className="h-full min-h-[600px] w-full border-0 bg-white"
                sandbox="allow-same-origin allow-scripts"
                title={`${task.title} output`}
              />
            ) : selectedOutput.content || selectedOutput.md_content ? (
              <div className="p-5">
                <div className="prose prose-sm max-w-none dark:prose-invert">
                  <MarkdownRenderer content={selectedOutput.content || selectedOutput.md_content || ''} />
                </div>
              </div>
            ) : (
              <div className="p-8 text-center text-sm text-muted-foreground">No preview available.</div>
            )}
          </>
        ) : (
          <div className="flex items-center justify-center h-full p-8">
            <div className="text-center max-w-sm">
              <FileText className="w-10 h-10 text-muted-foreground/15 mx-auto mb-3" />
              <h3 className="text-sm font-medium mb-1">No output yet</h3>
              <p className="text-sm text-muted-foreground">
                {task.next_run_at ? `Next run ${formatRelativeTime(task.next_run_at)}.` : 'Run this task to generate output.'}
              </p>
              <button
                onClick={() => onRunTask(task.slug)}
                disabled={busy}
                className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                <Play className="w-4 h-4" />
                Run now
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Run history footer */}
      {outputs.length > 1 && (
        <div className="border-t border-border px-5 py-3 shrink-0">
          <div className="flex gap-2 overflow-x-auto">
            {outputs.slice(0, 8).map(o => (
              <button
                key={o.folder || o.date}
                onClick={() => setSelectedOutput(o)}
                className={cn(
                  'shrink-0 px-2 py-1 rounded text-xs border',
                  (o.folder || o.date) === (selectedOutput?.folder || selectedOutput?.date)
                    ? 'border-primary/30 bg-primary/5 text-primary'
                    : 'border-border text-muted-foreground hover:bg-muted/50'
                )}
              >
                {o.date || o.folder}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main Dispatcher ───
export function AgentContentView({
  agent,
  tasks,
  view,
  selectedTaskSlug,
  onBack,
  onSelectTask,
  onRunTask,
  busy,
}: AgentContentViewProps) {
  // Task drill-down takes priority
  if (selectedTaskSlug && (view === 'task-output' || view === 'task-deliverable' || view === 'task-history')) {
    return (
      <TaskDrillDown
        taskSlug={selectedTaskSlug}
        onBack={onBack}
        onRunTask={onRunTask}
        busy={busy}
      />
    );
  }

  const agentClass = agent.agent_class || 'domain-steward';

  switch (agentClass) {
    case 'synthesizer':
      return <SynthesizerView agent={agent} tasks={tasks} onSelectTask={onSelectTask} onRunTask={onRunTask} busy={busy} />;
    case 'platform-bot':
      return <BotView agent={agent} tasks={tasks} onSelectTask={onSelectTask} onRunTask={onRunTask} busy={busy} />;
    default: // domain-steward
      return <DomainView agent={agent} tasks={tasks} onSelectTask={onSelectTask} onRunTask={onRunTask} busy={busy} />;
  }
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
