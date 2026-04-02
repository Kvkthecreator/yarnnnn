'use client';

/**
 * Task Page — Task management surface
 *
 * Workfloor owns filesystem browsing. This page is not the default document
 * viewer for task files. It is the task management surface:
 * - Left: current output
 * - Right: compact task inspector (meta, spec, context, runs)
 * - Drawer panel: task-scoped TP chat
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Clock,
  ChevronDown,
  FileSearch,
  FileText,
  Globe,
  Loader2,
  Mail,
  MessageCircle,
  Pause,
  Play,
  RefreshCw,
  Send,
  Target,
  X,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useFileAttachments } from '@/hooks/useFileAttachments';
import type { TaskDetail, TaskOutput } from '@/types';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import { WorkspaceLayout, type WorkspacePanelTab } from '@/components/desk/WorkspaceLayout';
import { PlusMenu, type PlusMenuAction } from '@/components/tp/PlusMenu';
import { MessageBlocks } from '@/components/tp/InlineToolCall';
import { ToolResultList } from '@/components/tp/ToolResultCard';
import {
  InlineActionCard,
  type ActionCardConfig,
  RUN_TASK_CARD,
  ADJUST_TASK_CARD,
  RESEARCH_TASK_CARD,
  FEEDBACK_TASK_CARD,
} from '@/components/tp/InlineActionCard';

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

function formatTimestamp(dateStr?: string | null, withTime: boolean = true): string {
  if (!dateStr) return 'Not scheduled';
  const date = new Date(dateStr);
  if (Number.isNaN(date.getTime())) return dateStr;
  return date.toLocaleString('en-US', withTime ? {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  } : {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function InspectorCard({
  title,
  icon,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section
      className="rounded-2xl border border-border bg-background/95 p-4 shadow-sm"
    >
      <div className="mb-3 flex items-center gap-2">
        <span className="text-muted-foreground">{icon}</span>
        <h2 className="text-sm font-medium">{title}</h2>
      </div>
      {children}
    </section>
  );
}

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

function TaskMetaCard({ task }: { task: TaskDetail }) {
  const statusColor =
    task.status === 'active'
      ? 'bg-green-500'
      : task.status === 'paused'
        ? 'bg-amber-500'
        : task.status === 'completed'
          ? 'bg-blue-500'
          : 'bg-gray-400';

  return (
    <InspectorCard title="Task Overview" icon={<FileText className="w-4 h-4" />}>
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="inline-flex items-center gap-2 rounded-full border border-border bg-muted/40 px-2.5 py-1">
            <span className={cn('h-2 w-2 rounded-full', statusColor)} />
            <span className="capitalize">{task.status}</span>
          </span>
          {task.mode && (
            <span className="rounded-full border border-border bg-muted/40 px-2.5 py-1 text-xs capitalize text-muted-foreground">
              {task.mode}
            </span>
          )}
          {task.schedule && (
            <span className="rounded-full border border-border bg-muted/40 px-2.5 py-1 text-xs text-muted-foreground">
              {task.schedule}
            </span>
          )}
        </div>

        <div className="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <p className="mb-1 text-[11px] uppercase tracking-wide text-muted-foreground">Next run</p>
            <p className="font-medium">{formatTimestamp(task.next_run_at)}</p>
          </div>
          <div>
            <p className="mb-1 text-[11px] uppercase tracking-wide text-muted-foreground">Last run</p>
            <p className="font-medium">{task.last_run_at ? formatRelativeTime(task.last_run_at) : 'No runs yet'}</p>
          </div>
          <div>
            <p className="mb-1 text-[11px] uppercase tracking-wide text-muted-foreground">Delivery</p>
            <p className="flex items-center gap-2 font-medium">
              <Mail className="w-3.5 h-3.5 text-muted-foreground" />
              {task.delivery || 'No delivery configured'}
            </p>
          </div>
          <div>
            <p className="mb-1 text-[11px] uppercase tracking-wide text-muted-foreground">Assigned agent</p>
            <p className="font-medium">{task.agent_slugs?.join(', ') || 'Unassigned'}</p>
          </div>
        </div>
      </div>
    </InspectorCard>
  );
}

function DeliverableCard({
  task,
  deliverableMd,
}: {
  task: TaskDetail;
  deliverableMd: string | null;
}) {
  return (
    <InspectorCard title="Deliverable" icon={<Target className="w-4 h-4" />}>
      <div className="space-y-4">
        {task.objective && (
          <div className="grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <p className="mb-1 text-[11px] uppercase tracking-wide text-muted-foreground">Deliverable</p>
              <p>{task.objective.deliverable || 'Not set'}</p>
            </div>
            <div>
              <p className="mb-1 text-[11px] uppercase tracking-wide text-muted-foreground">Audience</p>
              <p>{task.objective.audience || 'Not set'}</p>
            </div>
            <div>
              <p className="mb-1 text-[11px] uppercase tracking-wide text-muted-foreground">Purpose</p>
              <p>{task.objective.purpose || 'Not set'}</p>
            </div>
            <div>
              <p className="mb-1 text-[11px] uppercase tracking-wide text-muted-foreground">Format</p>
              <p>{task.objective.format || 'Not set'}</p>
            </div>
          </div>
        )}

        {task.success_criteria && task.success_criteria.length > 0 && (
          <div>
            <p className="mb-2 text-[11px] uppercase tracking-wide text-muted-foreground">Success criteria</p>
            <ul className="space-y-1.5 text-sm text-muted-foreground">
              {task.success_criteria.map((criterion, index) => (
                <li key={index} className="flex gap-2">
                  <span className="mt-1 h-1.5 w-1.5 rounded-full bg-primary/60" />
                  <span>{criterion}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {task.output_spec && task.output_spec.length > 0 && (
          <div>
            <p className="mb-2 text-[11px] uppercase tracking-wide text-muted-foreground">Output spec</p>
            <ul className="space-y-1.5 text-sm text-muted-foreground">
              {task.output_spec.map((item, index) => (
                <li key={index} className="flex gap-2">
                  <span className="mt-1 h-1.5 w-1.5 rounded-full bg-primary/60" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div>
          <p className="mb-2 text-[11px] uppercase tracking-wide text-muted-foreground">Spec file</p>
          {deliverableMd ? (
            <details className="group rounded-xl border border-border bg-muted/20">
              <summary className="flex cursor-pointer list-none items-center justify-between px-3 py-2 text-sm font-medium text-muted-foreground">
                <span>Open DELIVERABLE.md</span>
                <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" />
              </summary>
              <div className="max-h-[320px] overflow-auto border-t border-border/70 p-3">
                <div className="prose prose-sm max-w-none dark:prose-invert">
                  <MarkdownRenderer content={deliverableMd} />
                </div>
              </div>
            </details>
          ) : (
            <p className="text-sm text-muted-foreground">No `DELIVERABLE.md` found for this task.</p>
          )}
        </div>
      </div>
    </InspectorCard>
  );
}

function ContextCard({
  task,
}: {
  task: TaskDetail;
}) {
  return (
    <InspectorCard title="Context" icon={<FileSearch className="w-4 h-4" />}>
      <div className="space-y-4">
        <div>
          <p className="mb-2 text-[11px] uppercase tracking-wide text-muted-foreground">Reads from</p>
          {task.context_reads && task.context_reads.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {task.context_reads.map((domain) => (
                <span key={domain} className="rounded-full bg-blue-500/10 px-2.5 py-1 text-xs text-blue-700 dark:text-blue-300">
                  {domain}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No read domains configured.</p>
          )}
        </div>

        <div>
          <p className="mb-2 text-[11px] uppercase tracking-wide text-muted-foreground">Writes to</p>
          {task.context_writes && task.context_writes.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {task.context_writes.map((domain) => (
                <span key={domain} className="rounded-full bg-green-500/10 px-2.5 py-1 text-xs text-green-700 dark:text-green-300">
                  {domain}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No write domains configured.</p>
          )}
        </div>

        {task.run_log && (
          <div>
            <p className="mb-2 text-[11px] uppercase tracking-wide text-muted-foreground">Recent run log</p>
            <details className="group rounded-xl border border-border bg-muted/20">
              <summary className="flex cursor-pointer list-none items-center justify-between px-3 py-2 text-sm font-medium text-muted-foreground">
                <span>Open run log</span>
                <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" />
              </summary>
              <pre className="max-h-[220px] overflow-auto border-t border-border/70 p-3 text-xs whitespace-pre-wrap text-muted-foreground">
                {task.run_log}
              </pre>
            </details>
          </div>
        )}
      </div>
    </InspectorCard>
  );
}

function RunsCard({
  task,
  outputs,
  selectedFolder,
  onSelectOutput,
  onRunNow,
  onToggleStatus,
  busy,
}: {
  task: TaskDetail;
  outputs: TaskOutput[];
  selectedFolder: string | null;
  onSelectOutput: (output: TaskOutput) => void;
  onRunNow: () => void;
  onToggleStatus: () => void;
  busy: boolean;
}) {
  const isActive = task.status === 'active';

  return (
    <InspectorCard title="Runs" icon={<Clock className="w-4 h-4" />}>
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <button
            onClick={onRunNow}
            disabled={busy}
            className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
            Run now
          </button>
          <button
            onClick={onToggleStatus}
            disabled={busy}
            className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-2 text-xs font-medium text-muted-foreground hover:bg-muted/50 hover:text-foreground disabled:opacity-50"
          >
            <Pause className="w-3.5 h-3.5" />
            {isActive ? 'Pause task' : 'Resume task'}
          </button>
        </div>

        <div className="space-y-1">
          {outputs.length > 0 ? (
            outputs.map((output) => {
              const folder = output.folder || output.date;
              const selected = folder === selectedFolder;
              const outputStatusColor =
                output.status === 'delivered'
                  ? 'bg-green-500'
                  : output.status === 'failed'
                    ? 'bg-red-500'
                    : 'bg-amber-500';

              return (
                <button
                  key={folder}
                  onClick={() => onSelectOutput(output)}
                  className={cn(
                    'w-full rounded-xl border px-3 py-3 text-left transition-colors',
                    selected ? 'border-primary/30 bg-primary/5' : 'border-border bg-background hover:bg-muted/40'
                  )}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={cn('h-2 w-2 rounded-full', outputStatusColor)} />
                        <p className="text-sm font-medium">{output.date || folder}</p>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {selected ? 'Currently open in output view' : 'Open this run'}
                      </p>
                    </div>
                    <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] capitalize text-muted-foreground">
                      {output.status}
                    </span>
                  </div>
                </button>
              );
            })
          ) : (
            <div className="rounded-xl border border-dashed border-border p-4 text-center">
              <p className="text-sm text-muted-foreground">No runs yet</p>
            </div>
          )}
        </div>
      </div>
    </InspectorCard>
  );
}

function OutputPane({
  task,
  output,
  onRunNow,
}: {
  task: TaskDetail;
  output: TaskOutput | null;
  onRunNow: () => void;
}) {
  const selectedFolder = output?.folder || output?.date || null;

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
          <button
            onClick={onRunNow}
            className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            <Play className="w-4 h-4" />
            Run now
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col bg-background">
      <div className="border-b border-border px-5 py-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Current output</p>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <span className="rounded-full bg-muted px-2 py-0.5">
                {output.date || selectedFolder || 'Latest run'}
              </span>
              <span className="rounded-full bg-muted px-2 py-0.5 capitalize">{output.status}</span>
            </div>
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

function TaskWorkspace({
  task,
  output,
  deliverableMd,
  outputs,
  onSelectOutput,
  onRunNow,
  onToggleStatus,
  busy,
}: {
  task: TaskDetail;
  output: TaskOutput | null;
  deliverableMd: string | null;
  outputs: TaskOutput[];
  onSelectOutput: (output: TaskOutput) => void;
  onRunNow: () => void;
  onToggleStatus: () => void;
  busy: boolean;
}) {
  const selectedFolder = output?.folder || output?.date || null;

  return (
    <div className="flex h-full min-h-0 flex-col lg:flex-row">
      <div className="min-h-0 flex-1 overflow-hidden border-b border-border lg:border-b-0 lg:border-r">
        <OutputPane task={task} output={output} onRunNow={onRunNow} />
      </div>

      <aside className="w-full shrink-0 overflow-y-auto bg-muted/10 lg:w-[380px]">
        <div className="space-y-4 p-4">
          <TaskMetaCard task={task} />
          <DeliverableCard task={task} deliverableMd={deliverableMd} />
          <ContextCard task={task} />
          <RunsCard
            task={task}
            outputs={outputs}
            selectedFolder={selectedFolder}
            onSelectOutput={onSelectOutput}
            onRunNow={onRunNow}
            onToggleStatus={onToggleStatus}
            busy={busy}
          />
        </div>
      </aside>
    </div>
  );
}

function TaskChatPanel({ taskSlug, taskTitle }: { taskSlug: string; taskTitle: string }) {
  const {
    messages,
    sendMessage,
    isLoading,
    status,
    pendingClarification,
    respondToClarification,
    tokenUsage,
  } = useTP();

  const [input, setInput] = useState('');
  const [actionCard, setActionCard] = useState<ActionCardConfig | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleActionSelect = (message: string) => {
    if (message.endsWith(' ')) {
      setInput(message);
      setActionCard(null);
      textareaRef.current?.focus();
    } else {
      sendMessage(message, { surface: { type: 'task-detail', taskSlug } });
      setActionCard(null);
    }
  };

  const {
    attachments,
    attachmentPreviews,
    error: fileError,
    uploadedDocs,
    handleFileSelect,
    handlePaste,
    removeAttachment,
    clearAttachments,
    getImagesForAPI,
    fileInputRef,
  } = useFileAttachments();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, status]);

  const adjustHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`;
  }, []);

  useEffect(() => {
    adjustHeight();
  }, [input, adjustHeight]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((!input.trim() && attachments.length === 0) || isLoading) return;
    const images = await getImagesForAPI();
    sendMessage(input, {
      surface: { type: 'task-detail', taskSlug },
      images: images.length > 0 ? images : undefined,
    });
    setInput('');
    clearAttachments();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  const plusMenuActions: PlusMenuAction[] = [
    { id: 'run-task', label: 'Run now', icon: Play, verb: 'prompt', onSelect: () => setActionCard(RUN_TASK_CARD) },
    { id: 'adjust-task', label: 'Adjust task', icon: Target, verb: 'prompt', onSelect: () => setActionCard(ADJUST_TASK_CARD) },
    { id: 'feedback', label: 'Give feedback', icon: MessageCircle, verb: 'prompt', onSelect: () => setActionCard(FEEDBACK_TASK_CARD) },
    { id: 'web-research', label: 'Web research', icon: Globe, verb: 'prompt', onSelect: () => setActionCard(RESEARCH_TASK_CARD) },
  ];

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-2.5 overflow-y-auto px-3 py-3">
        {messages.length === 0 && !isLoading && (
          <div className="py-6 text-center">
            <MessageCircle className="mx-auto mb-1.5 h-5 w-5 text-muted-foreground/15" />
            <p className="text-[11px] text-muted-foreground/40">Ask anything about this task</p>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={cn(
              'max-w-[92%] rounded-2xl px-3 py-2 text-[13px]',
              msg.role === 'user' ? 'ml-auto rounded-br-md bg-primary/10' : 'rounded-bl-md bg-muted'
            )}
          >
            <span
              className={cn(
                'mb-1 block text-[9px] tracking-wider text-muted-foreground/50',
                msg.role === 'user' ? 'font-medium uppercase' : 'font-brand text-[10px]'
              )}
            >
              {msg.role === 'user' ? 'You' : 'yarnnn'}
            </span>
            {msg.blocks && msg.blocks.length > 0 ? (
              <MessageBlocks blocks={msg.blocks} />
            ) : msg.role === 'assistant' && !msg.content && isLoading ? (
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Loader2 className="h-3 w-3 animate-spin" />
                Thinking...
              </div>
            ) : (
              <>
                {msg.role === 'assistant' ? (
                  <MarkdownRenderer content={msg.content} compact />
                ) : (
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                )}
                {msg.toolResults && msg.toolResults.length > 0 && <ToolResultList results={msg.toolResults} compact />}
              </>
            )}
          </div>
        ))}

        {status.type === 'thinking' && messages[messages.length - 1]?.role === 'user' && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Loader2 className="h-3 w-3 animate-spin" />
            Thinking...
          </div>
        )}

        {status.type === 'clarify' && pendingClarification && (
          <div className="space-y-2 rounded-lg border border-border bg-muted/50 p-3">
            <p className="text-xs font-medium">{pendingClarification.question}</p>
            {pendingClarification.options?.length ? (
              <div className="flex flex-wrap gap-1.5">
                {pendingClarification.options.map((option, index) => (
                  <button
                    key={index}
                    onClick={() => respondToClarification(option)}
                    className="rounded-lg border border-primary/30 bg-primary/5 px-2.5 py-1 text-[11px] font-medium text-primary hover:bg-primary/15"
                  >
                    {option}
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-[10px] text-muted-foreground">Type below</p>
            )}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="shrink-0 border-t border-border px-3 pb-3 pt-1">
        {fileError && (
          <div className="mb-2 rounded-lg border border-destructive/30 bg-destructive/5 p-2 text-xs text-destructive">
            {fileError}
          </div>
        )}

        {uploadedDocs.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-1.5 rounded-lg border border-border bg-muted/30 p-1.5">
            {uploadedDocs.map((doc, index) => (
              <div key={index} className="flex items-center gap-1.5 rounded border border-border bg-background px-2 py-1 text-xs">
                <span className="max-w-[120px] truncate">{doc.name}</span>
                <span className={doc.status === 'done' ? 'text-green-600' : doc.status === 'error' ? 'text-destructive' : 'text-muted-foreground'}>
                  {doc.status === 'uploading' ? '...' : doc.status === 'done' ? '✓' : '✗'}
                </span>
              </div>
            ))}
          </div>
        )}

        {attachmentPreviews.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-2">
            {attachmentPreviews.map((preview, index) => (
              <div key={index} className="group relative">
                <img src={preview} alt="" className="h-10 w-10 rounded border border-border object-cover" />
                <button
                  onClick={() => removeAttachment(index)}
                  className="absolute -right-1 -top-1 flex h-3.5 w-3.5 items-center justify-center rounded-full border border-border bg-background opacity-0 group-hover:opacity-100"
                >
                  <X className="h-2 w-2" />
                </button>
              </div>
            ))}
          </div>
        )}

        {actionCard && (
          <div className="mb-2">
            <InlineActionCard
              config={actionCard}
              onSelect={handleActionSelect}
              onDismiss={() => setActionCard(null)}
            />
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="flex items-end gap-1.5 rounded-xl border border-border bg-background focus-within:ring-2 focus-within:ring-primary/50">
            <input ref={fileInputRef} type="file" accept="image/*,.pdf,.docx,.txt,.md" multiple onChange={handleFileSelect} className="hidden" />
            <PlusMenu actions={plusMenuActions} disabled={isLoading} />
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              onPaste={handlePaste}
              disabled={isLoading}
              enterKeyHint="send"
              placeholder={`Steer ${taskTitle}...`}
              rows={1}
              className="max-h-[150px] flex-1 resize-none bg-transparent py-2.5 pr-1 text-sm focus:outline-none disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isLoading || (!input.trim() && attachments.length === 0)}
              className="shrink-0 p-2.5 text-primary transition-colors disabled:text-muted-foreground disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
          <div className="mt-1 flex items-center justify-between text-[9px] text-muted-foreground/40">
            <span>Enter to send</span>
            {tokenUsage && (
              <span className="font-mono">
                {tokenUsage.totalTokens >= 1000 ? `${(tokenUsage.totalTokens / 1000).toFixed(1)}k` : tokenUsage.totalTokens} tokens
              </span>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}

export default function TaskPage() {
  const params = useParams();
  const router = useRouter();
  const slug = params?.slug as string;
  const { loadScopedHistory } = useTP();

  const [task, setTask] = useState<TaskDetail | null>(null);
  const [outputs, setOutputs] = useState<TaskOutput[]>([]);
  const [selectedOutput, setSelectedOutput] = useState<TaskOutput | null>(null);
  const [deliverableMd, setDeliverableMd] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mutationPending, setMutationPending] = useState(false);

  const refreshData = useCallback(async () => {
    if (!slug) return;
    try {
      const [taskData, outputsData, outputData, deliverableFile] = await Promise.all([
        api.tasks.get(slug),
        api.tasks.listOutputs(slug, 10),
        api.tasks.getLatestOutput(slug),
        api.workspace.getFile(`/tasks/${slug}/DELIVERABLE.md`).catch(() => null),
      ]);

      setTask(taskData);
      setOutputs(outputsData?.outputs || []);
      setSelectedOutput(outputData || null);
      setDeliverableMd(deliverableFile?.content || null);
    } catch (err) {
      console.error('Failed to refresh task workspace:', err);
    }
  }, [slug]);

  useEffect(() => {
    if (slug) {
      loadScopedHistory(undefined, slug);
    }
  }, [slug, loadScopedHistory]);

  useEffect(() => {
    if (!slug) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([
      api.tasks.get(slug).catch(() => null),
      api.tasks.listOutputs(slug, 10).catch(() => ({ outputs: [], total: 0 })),
      api.tasks.getLatestOutput(slug).catch(() => null),
      api.workspace.getFile(`/tasks/${slug}/DELIVERABLE.md`).catch(() => null),
    ])
      .then(([taskData, outputsData, outputData, deliverableFile]) => {
        if (cancelled) return;
        if (!taskData) {
          setError('Task not found');
          setLoading(false);
          return;
        }

        setTask(taskData);
        setOutputs(outputsData?.outputs || []);
        setSelectedOutput(outputData || null);
        setDeliverableMd(deliverableFile?.content || null);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load task workspace:', err);
        if (cancelled) return;
        setError('Failed to load task');
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [slug]);

  useEffect(() => {
    if (!slug || loading) return;
    const interval = setInterval(() => {
      refreshData();
    }, 30000);
    const onFocus = () => {
      if (document.visibilityState === 'visible') {
        refreshData();
      }
    };
    document.addEventListener('visibilitychange', onFocus);
    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', onFocus);
    };
  }, [slug, loading, refreshData]);

  const handleSelectOutput = useCallback((entry: TaskOutput) => {
    const folder = entry.folder || entry.date;
    if (!folder || !slug) {
      setSelectedOutput(entry);
      return;
    }

    api.tasks.getOutput(slug, folder)
      .then((full) => setSelectedOutput(full || entry))
      .catch(() => setSelectedOutput(entry));
  }, [slug]);

  const handleRunNow = useCallback(async () => {
    if (!slug) return;
    setMutationPending(true);
    try {
      await api.tasks.run(slug);
      await refreshData();
    } catch (err) {
      console.error('Run now failed:', err);
    } finally {
      setMutationPending(false);
    }
  }, [refreshData, slug]);

  const handleToggleStatus = useCallback(async () => {
    if (!task) return;
    setMutationPending(true);
    try {
      await api.tasks.update(task.slug, { status: task.status === 'active' ? 'paused' : 'active' });
      await refreshData();
    } catch (err) {
      console.error('Status update failed:', err);
    } finally {
      setMutationPending(false);
    }
  }, [refreshData, task]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !task) {
    return (
      <div className="flex h-full flex-col items-center justify-center">
        <p className="text-sm text-muted-foreground">{error || 'Task not found'}</p>
        <Link href="/workfloor" className="mt-2 text-xs text-primary hover:underline">Back to workfloor</Link>
      </div>
    );
  }

  const displayTitle = task.title || task.slug;

  const panelTabs: WorkspacePanelTab[] = [
    { id: 'chat', label: 'Chat', content: <TaskChatPanel taskSlug={slug} taskTitle={displayTitle} /> },
  ];

  const tpPanelHeader = (
    <div className="z-10 flex shrink-0 items-center justify-between border-b border-border bg-background px-3 py-2.5">
      <div className="flex items-center gap-2">
        <img src="/assets/logos/circleonly_yarnnn_1.svg" alt="" className="h-5 w-5" />
        <span className="text-xs font-medium">TP</span>
        <span className="max-w-[160px] truncate text-[10px] text-muted-foreground/50">
          · viewing {displayTitle}
        </span>
      </div>
      <button
        onClick={() => router.back()}
        className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );

  return (
    <WorkspaceLayout
      identity={{ icon: <FileText className="h-5 w-5" />, label: displayTitle }}
      breadcrumb={
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>
      }
      panelTabs={panelTabs}
      panelHeader={tpPanelHeader}
      panelDefaultOpen={true}
      panelDefaultPct={32}
    >
      <TaskWorkspace
        task={task}
        output={selectedOutput}
        deliverableMd={deliverableMd}
        outputs={outputs}
        onSelectOutput={handleSelectOutput}
        onRunNow={handleRunNow}
        onToggleStatus={handleToggleStatus}
        busy={mutationPending}
      />
    </WorkspaceLayout>
  );
}
