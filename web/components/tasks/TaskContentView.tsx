'use client';

/**
 * TaskContentView — Class-aware center content dispatcher.
 *
 * Context tasks: embedded file explorer scoped to context_writes domains
 * Synthesis tasks: composed HTML/markdown deliverable
 * Both: deliverable spec, run history as secondary views
 */

import { useState, useEffect, useCallback } from 'react';
import {
  FileText,
  Play,
  Loader2,
  CheckCircle2,
  ChevronRight,
  Layers,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { WorkspaceTree } from '@/components/workspace/WorkspaceTree';
import { ContentViewer } from '@/components/workspace/ContentViewer';
import { RevisionHistoryPanel } from '@/components/workspace/RevisionHistoryPanel';
import type { TaskDetail, TaskOutput } from '@/types';
import type { TaskView } from './TaskTreeNav';

type TreeNode = import('@/types').WorkspaceTreeNode;

interface TaskContentViewProps {
  task: TaskDetail;
  view: TaskView;
  output: TaskOutput | null;
  outputs: TaskOutput[];
  deliverableMd: string | null;
  onSelectOutput: (output: TaskOutput) => void;
  onSwitchView: (view: TaskView) => void;
  onRunNow: () => void;
  onToggleStatus: () => void;
  busy: boolean;
}

// ─── Export Button ───
function ExportButton({ slug, folder }: { slug: string; folder?: string | null }) {
  const [active, setActive] = useState<string | null>(null);
  const handleExport = async (format: string) => {
    setActive(format);
    try {
      const res = await api.tasks.export(slug, format, folder || undefined);
      if (res.url) window.open(res.url, '_blank');
    } catch (e) {
      console.error(`Export ${format} failed:`, e);
    } finally {
      setActive(null);
    }
  };
  return (
    <button
      onClick={() => handleExport('pdf')}
      disabled={active !== null}
      className="inline-flex items-center gap-1 rounded-md border border-border/60 bg-background px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted/50 hover:text-foreground disabled:opacity-50"
    >
      {active === 'pdf' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileText className="w-3.5 h-3.5" />}
      Export PDF
    </button>
  );
}

// ─── Output View (Synthesis tasks: the deliverable) ───
function OutputView({ task, output, onRunNow }: { task: TaskDetail; output: TaskOutput | null; onRunNow: () => void }) {
  if (!output) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="max-w-sm text-center">
          <FileText className="mx-auto mb-4 h-12 w-12 text-muted-foreground/20" />
          <h2 className="text-lg font-medium">No output yet</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            This task has not produced a deliverable yet.
            {task.next_run_at ? ` Next run ${formatRelativeTime(task.next_run_at)}.` : ''}
          </p>
          <button onClick={onRunNow} className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90">
            <Play className="w-4 h-4" />
            Run now
          </button>
        </div>
      </div>
    );
  }

  const selectedFolder = output.folder || output.date || null;

  return (
    <div className="flex h-full flex-col bg-background">
      <div className="border-b border-border px-5 py-3 shrink-0">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="rounded-full bg-muted px-2 py-0.5">{output.date || selectedFolder || 'Latest'}</span>
            <span className="rounded-full bg-muted px-2 py-0.5 capitalize">{output.status}</span>
          </div>
          {(output.html_content || output.md_content || output.content) && (
            <ExportButton slug={task.slug} folder={selectedFolder} />
          )}
        </div>
      </div>
      <div className="flex-1 overflow-auto">
        {output.html_content ? (
          <iframe
            srcDoc={output.html_content}
            className="h-full min-h-[720px] w-full border-0 bg-white"
            sandbox="allow-same-origin allow-scripts"
            title={`${task.title} output`}
          />
        ) : output.content || output.md_content ? (
          <div className="p-5">
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <MarkdownRenderer content={output.content || output.md_content || ''} />
            </div>
          </div>
        ) : (
          <div className="p-8 text-center text-sm text-muted-foreground">
            Output available but preview content is not currently loaded.
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Domain Explorer View (Context tasks: browse the actual files) ───
function DomainExplorerView({ task }: { task: TaskDetail }) {
  const [treeNodes, setTreeNodes] = useState<TreeNode[]>([]);
  const [selectedNode, setSelectedNode] = useState<TreeNode | null>(null);
  const [loading, setLoading] = useState(true);

  const loadTree = useCallback(async () => {
    const writesDomains = task.context_writes || [];
    if (writesDomains.length === 0) { setLoading(false); return; }

    setLoading(true);
    const nodes: TreeNode[] = [];
    for (const domain of writesDomains) {
      try {
        const tree = await api.workspace.getTree(`/workspace/context/${domain}`);
        const children = Array.isArray(tree) ? tree : [];
        nodes.push({
          name: domain.charAt(0).toUpperCase() + domain.slice(1),
          path: `/workspace/context/${domain}`,
          type: 'folder',
          children,
        });
      } catch {
        nodes.push({
          name: domain.charAt(0).toUpperCase() + domain.slice(1),
          path: `/workspace/context/${domain}`,
          type: 'folder',
          children: [],
        });
      }
    }
    setTreeNodes(nodes);
    setLoading(false);
  }, [task.slug, task.context_writes]);

  useEffect(() => { loadTree(); }, [loadTree]);

  const handleSelect = useCallback((node: TreeNode) => {
    setSelectedNode(node);
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center h-full"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>;
  }

  if (treeNodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full p-8">
        <div className="text-center max-w-sm">
          <Layers className="w-10 h-10 text-muted-foreground/15 mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">This task doesn't write to any context domains.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Mini tree nav — scoped to this task's domains */}
      <div className="w-[200px] shrink-0 border-r border-border overflow-y-auto bg-muted/10">
        <div className="p-2">
          <WorkspaceTree
            nodes={treeNodes}
            selectedPath={selectedNode?.path}
            onSelect={handleSelect}
          />
        </div>
      </div>

      {/* Content viewer */}
      <div className="flex-1 min-w-0 overflow-hidden">
        {selectedNode ? (
          <ContentViewer selectedNode={selectedNode} onNavigate={handleSelect} />
        ) : (
          <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
            Select a file to view
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Deliverable View ───
function DeliverableView({ task, deliverableMd }: { task: TaskDetail; deliverableMd: string | null }) {
  return (
    <div className="p-6 space-y-6 overflow-auto h-full">
      {task.objective && (
        <div>
          <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-3">Objective</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            {(['deliverable', 'audience', 'purpose', 'format'] as const).map(field => (
              <div key={field}>
                <p className="text-[11px] uppercase tracking-wide text-muted-foreground mb-1">{field}</p>
                <p className="text-sm">{task.objective?.[field] || 'Not set'}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {task.success_criteria && task.success_criteria.length > 0 && (
        <div>
          <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-2">Success criteria</h3>
          <ul className="space-y-1.5 text-sm text-muted-foreground">
            {task.success_criteria.map((c, i) => (
              <li key={i} className="flex gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-primary/60 shrink-0" />
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {task.output_spec && task.output_spec.length > 0 && (
        <div>
          <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-2">Output spec</h3>
          <ul className="space-y-1.5 text-sm text-muted-foreground">
            {task.output_spec.map((item, i) => (
              <li key={i} className="flex gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-primary/60 shrink-0" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {deliverableMd && (
        <div>
          <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-3">DELIVERABLE.md</h3>
          <div className="prose prose-sm max-w-none dark:prose-invert rounded-xl border border-border p-4">
            <MarkdownRenderer content={deliverableMd} />
          </div>
        </div>
      )}

      {!task.objective && !deliverableMd && (
        <div className="p-8 text-center text-sm text-muted-foreground">No deliverable spec configured.</div>
      )}
    </div>
  );
}

// ─── Run History View ───
function RunHistoryView({
  outputs,
  selectedFolder,
  onSelectOutput,
  onSwitchToOutput,
}: {
  outputs: TaskOutput[];
  selectedFolder: string | null;
  onSelectOutput: (output: TaskOutput) => void;
  onSwitchToOutput: () => void;
}) {
  return (
    <div className="p-6 space-y-4 overflow-auto h-full">
      {outputs.length > 0 ? (
        <div className="border border-border rounded-xl overflow-hidden divide-y divide-border">
          {outputs.map((entry) => {
            const folder = entry.folder || entry.date;
            const isSelected = folder === selectedFolder;
            return (
              <button
                key={folder}
                onClick={() => { onSelectOutput(entry); onSwitchToOutput(); }}
                className={cn(
                  'w-full flex items-center justify-between p-3 text-left hover:bg-muted/50 transition-colors',
                  isSelected && 'bg-primary/5'
                )}
              >
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className={cn('w-4 h-4', entry.status === 'completed' ? 'text-green-500' : 'text-muted-foreground/40')} />
                  <div>
                    <p className="text-sm font-medium">{entry.date || folder}</p>
                    <p className="text-xs text-muted-foreground capitalize">{entry.status}</p>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-muted-foreground/30" />
              </button>
            );
          })}
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-border p-6 text-center">
          <p className="text-sm text-muted-foreground">No runs yet</p>
        </div>
      )}
    </div>
  );
}

// ─── Task Definition View ───
function TaskDefinitionView({ task }: { task: TaskDetail }) {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const taskMdPath = `/tasks/${task.slug}/TASK.md`;

  const refetch = useCallback(() => {
    setLoading(true);
    return api.workspace.getFile(taskMdPath)
      .then(file => setContent(file?.content || null))
      .catch(() => setContent(null))
      .finally(() => setLoading(false));
  }, [taskMdPath]);

  useEffect(() => { refetch(); }, [refetch]);

  if (loading) {
    return <div className="flex items-center justify-center h-full"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>;
  }

  if (!content) {
    return <div className="p-8 text-center text-sm text-muted-foreground">No TASK.md found.</div>;
  }

  return (
    <div className="p-6 overflow-auto h-full space-y-4">
      <div className="prose prose-sm max-w-none dark:prose-invert">
        <MarkdownRenderer content={content} />
      </div>
      {/* ADR-209 Phase 4: revision history for TASK.md — who has edited it and when */}
      <RevisionHistoryPanel path={taskMdPath} onRevert={refetch} initiallyCollapsed />
    </div>
  );
}

// ─── Main Dispatcher ───
export function TaskContentView({
  task,
  view,
  output,
  outputs,
  deliverableMd,
  onSelectOutput,
  onSwitchView,
  onRunNow,
  onToggleStatus,
  busy,
}: TaskContentViewProps) {
  const selectedFolder = output?.folder || output?.date || null;

  switch (view) {
    case 'output':
      return <OutputView task={task} output={output} onRunNow={onRunNow} />;
    case 'domain-status':
      return <DomainExplorerView task={task} />;
    case 'task-definition':
      return <TaskDefinitionView task={task} />;
    case 'deliverable':
      return <DeliverableView task={task} deliverableMd={deliverableMd} />;
    case 'run-history':
      return (
        <RunHistoryView
          outputs={outputs}
          selectedFolder={selectedFolder}
          onSelectOutput={onSelectOutput}
          onSwitchToOutput={() => onSwitchView('output')}
        />
      );
    default:
      return <OutputView task={task} output={output} onRunNow={onRunNow} />;
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
