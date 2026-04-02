'use client';

/**
 * TaskContentView — Dynamic center content dispatcher for the task surface.
 *
 * Renders different content based on the selected view:
 * - output: iframe (HTML) or markdown preview or empty state
 * - task-definition: rendered TASK.md from workspace
 * - deliverable: objective fields + rendered DELIVERABLE.md
 * - run-history: list of runs with click to select
 *
 * Extensible — future file types render through the same dispatch.
 */

import { useState, useEffect } from 'react';
import {
  FileText,
  Play,
  Pause,
  Loader2,
  RefreshCw,
  Clock,
  CheckCircle2,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import type { TaskDetail, TaskOutput } from '@/types';
import type { TaskView } from './TaskTreeNav';

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

// ─── Output View ───
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
            <div className="mb-3 flex items-center gap-1.5 text-xs text-muted-foreground/60">
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Markdown preview</span>
            </div>
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

// ─── Task Definition View ───
function TaskDefinitionView({ task }: { task: TaskDetail }) {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.workspace.getFile(`/tasks/${task.slug}/TASK.md`)
      .then(file => setContent(file?.content || null))
      .catch(() => setContent(null))
      .finally(() => setLoading(false));
  }, [task.slug]);

  if (loading) {
    return <div className="flex items-center justify-center h-full"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>;
  }

  if (!content) {
    return <div className="p-8 text-center text-sm text-muted-foreground">No TASK.md found.</div>;
  }

  return (
    <div className="p-6 overflow-auto">
      <div className="prose prose-sm max-w-none dark:prose-invert">
        <MarkdownRenderer content={content} />
      </div>
    </div>
  );
}

// ─── Deliverable View ───
function DeliverableView({ task, deliverableMd }: { task: TaskDetail; deliverableMd: string | null }) {
  return (
    <div className="p-6 space-y-6 overflow-auto">
      {/* Objective fields */}
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

      {/* Success criteria */}
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

      {/* Output spec */}
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

      {/* DELIVERABLE.md rendered */}
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
  task,
  outputs,
  selectedFolder,
  onSelectOutput,
  onSwitchToOutput,
  onRunNow,
  onToggleStatus,
  busy,
}: {
  task: TaskDetail;
  outputs: TaskOutput[];
  selectedFolder: string | null;
  onSelectOutput: (output: TaskOutput) => void;
  onSwitchToOutput: () => void;
  onRunNow: () => void;
  onToggleStatus: () => void;
  busy: boolean;
}) {
  return (
    <div className="p-6 space-y-4">
      {/* Actions */}
      <div className="flex items-center gap-2">
        <button
          onClick={onRunNow}
          disabled={busy}
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          <Play className="w-3.5 h-3.5" />
          Run now
        </button>
        <button
          onClick={onToggleStatus}
          disabled={busy}
          className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-50"
        >
          {task.status === 'active' ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          {task.status === 'active' ? 'Pause' : 'Resume'}
        </button>
      </div>

      {/* Run list */}
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
    case 'task-definition':
      return <TaskDefinitionView task={task} />;
    case 'deliverable':
      return <DeliverableView task={task} deliverableMd={deliverableMd} />;
    case 'run-history':
      return (
        <RunHistoryView
          task={task}
          outputs={outputs}
          selectedFolder={selectedFolder}
          onSelectOutput={onSelectOutput}
          onSwitchToOutput={() => onSwitchView('output')}
          onRunNow={onRunNow}
          onToggleStatus={onToggleStatus}
          busy={busy}
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
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
