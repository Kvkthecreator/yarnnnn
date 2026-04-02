'use client';

/**
 * Task Page — v3: Tabbed Left + Task-Scoped Chat Right
 *
 * Left: [Output] [Task] [Schedule] [Agents] tabs
 * Right: Task-scoped TP chat (always visible, resizable)
 * Same WorkspaceLayout pattern as workfloor.
 *
 * Chat is task-scoped: different plus menu, different context injection,
 * session keyed by task_slug. See docs/design/TASK-SCOPED-TP.md.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Loader2,
  Play,
  FileText,
  Mail,
  Clock,
  Send,
  Globe,
  RefreshCw,
  X,
  ListChecks,
  Target,
  MessageCircle,
  // Presentation removed — repurpose bar simplified
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useDesk } from '@/contexts/DeskContext';
import { useFileAttachments } from '@/hooks/useFileAttachments';
import type { TaskDetail, TaskOutput, Agent } from '@/types';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import { WorkspaceLayout, type WorkspacePanelTab } from '@/components/desk/WorkspaceLayout';
import { PlusMenu, type PlusMenuAction } from '@/components/tp/PlusMenu';
import { MessageBlocks } from '@/components/tp/InlineToolCall';
import { ToolResultList } from '@/components/tp/ToolResultCard';
import { ProcessTab } from '@/components/tasks/ProcessTab';
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

// =============================================================================
// Left Panel: Output Tab
// =============================================================================

function ExportButton({ slug }: { slug: string }) {
  const [active, setActive] = useState<string | null>(null);

  const handleExport = async (format: string) => {
    setActive(format);
    try {
      const res = await api.tasks.export(slug, format);
      if (res.url) window.open(res.url, '_blank');
    } catch (e) {
      console.error(`Export ${format} failed:`, e);
    } finally {
      setActive(null);
    }
  };

  return (
    <div className="flex items-center gap-1.5">
      {['pdf'].map((fmt) => (
        <button
          key={fmt}
          onClick={() => handleExport(fmt)}
          disabled={active !== null}
          className="inline-flex items-center gap-1 px-2 py-1 text-[11px] font-medium rounded-md border border-border/50 bg-background hover:bg-muted transition-colors disabled:opacity-50"
        >
          {active === fmt ? <Loader2 className="w-3 h-3 animate-spin" /> : <FileText className="w-3 h-3" />}
          {fmt.toUpperCase()}
        </button>
      ))}
    </div>
  );
}

function OutputTab({ task, output }: { task: TaskDetail; output: TaskOutput | null }) {
  if (!output) {
    return (
      <div className="text-center py-16">
        <FileText className="w-10 h-10 text-muted-foreground/15 mx-auto mb-4" />
        <p className="text-sm text-muted-foreground">No output yet</p>
        {task.next_run_at && (
          <p className="text-xs text-muted-foreground/60 mt-1 flex items-center justify-center gap-1">
            <Clock className="w-3 h-3" /> Next run: {formatRelativeTime(task.next_run_at)}
          </p>
        )}
        <button
          onClick={() => api.tasks.run(task.slug).catch(console.error)}
          className="mt-4 inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <Play className="w-3.5 h-3.5" /> Run Now
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Export — only PDF, compact, only when content exists */}
      {(output.html_content || output.md_content) && (
        <div className="flex items-center justify-end px-4 py-1.5 border-b border-border/30">
          <ExportButton slug={task.slug} />
        </div>
      )}
      <div className="flex-1 min-h-0">
        {output.html_content ? (
          <iframe
            srcDoc={output.html_content}
            className="w-full h-full min-h-[500px] border-0 bg-white"
            sandbox="allow-same-origin allow-scripts"
            title="Task output"
          />
        ) : (output as any).content || output.md_content ? (
          <div className="p-4">
            <div className="text-xs text-muted-foreground/50 mb-3 flex items-center gap-1.5">
              <RefreshCw className="w-3 h-3" />
              <span>Markdown preview — composed view loading</span>
            </div>
            <MarkdownRenderer content={(output as any).content || output.md_content || ''} />
          </div>
        ) : (
          <p className="text-sm text-muted-foreground text-center py-8">Output available but content not loaded</p>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// Left Panel: Task Tab (definition — objective, criteria, output spec)
// =============================================================================

function TaskDefinitionTab({ task, onChatMessage }: { task: TaskDetail; onChatMessage?: (msg: string) => void }) {
  return (
    <div className="p-5 space-y-6">
      {task.objective && (
        <div>
          <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide mb-2">Objective</p>
          <div className="space-y-2">
            {task.objective.deliverable && <p className="text-sm"><span className="text-muted-foreground text-xs mr-1.5">Deliverable</span> {task.objective.deliverable}</p>}
            {task.objective.audience && <p className="text-sm"><span className="text-muted-foreground text-xs mr-1.5">Audience</span> {task.objective.audience}</p>}
            {task.objective.purpose && <p className="text-sm"><span className="text-muted-foreground text-xs mr-1.5">Purpose</span> {task.objective.purpose}</p>}
            {task.objective.format && <p className="text-sm"><span className="text-muted-foreground text-xs mr-1.5">Format</span> {task.objective.format}</p>}
          </div>
        </div>
      )}

      {task.success_criteria && task.success_criteria.length > 0 && (
        <div>
          <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide mb-2">Success Criteria</p>
          <ul className="text-sm space-y-1.5 list-disc list-inside text-muted-foreground">
            {task.success_criteria.map((c, i) => <li key={i}>{c}</li>)}
          </ul>
        </div>
      )}

      {task.output_spec && task.output_spec.length > 0 && (
        <div>
          <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide mb-2">Output Spec</p>
          <ul className="text-sm space-y-1.5 list-disc list-inside text-muted-foreground">
            {task.output_spec.map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        </div>
      )}

      {task.delivery && (
        <div>
          <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide mb-2">Delivery</p>
          <p className="text-sm flex items-center gap-1.5"><Mail className="w-3.5 h-3.5 text-muted-foreground" />{task.delivery}</p>
        </div>
      )}

      {!task.objective && !task.success_criteria?.length && !task.output_spec?.length && (
        <div className="py-6 space-y-3">
          <p className="text-sm text-muted-foreground">This task needs a definition. Tell the chat what you want:</p>
          {onChatMessage && (
            <div className="flex flex-wrap gap-1.5">
              {[
                { label: 'Define objective', msg: 'Define the objective for this task' },
                { label: 'Set audience', msg: 'Set the audience for this task' },
                { label: 'Add criteria', msg: 'Add success criteria for this task' },
              ].map((a, i) => (
                <button
                  key={i}
                  onClick={() => onChatMessage(a.msg)}
                  className="px-2.5 py-1 text-[11px] rounded-lg border border-primary/30 bg-primary/5 text-primary hover:bg-primary/15 font-medium transition-colors"
                >
                  {a.label}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Left Panel: Schedule Tab (controls + run trajectory)
// =============================================================================

function ScheduleTab({
  task,
  outputs,
  selectedFolder,
  onSelectOutput,
  onRefresh,
}: {
  task: TaskDetail;
  outputs: TaskOutput[];
  selectedFolder: string | null;
  onSelectOutput: (o: TaskOutput) => void;
  onRefresh?: () => void;
}) {
  const [pausing, setPausing] = useState(false);
  const [resuming, setResuming] = useState(false);
  const statusColor = task.status === 'active' ? 'bg-green-500' : task.status === 'paused' ? 'bg-amber-500' : task.status === 'completed' ? 'bg-blue-500' : 'bg-gray-400';

  const handlePauseResume = async () => {
    try {
      if (task.status === 'active') {
        setPausing(true);
        await api.tasks.update(task.slug, { status: 'paused' });
      } else {
        setResuming(true);
        await api.tasks.update(task.slug, { status: 'active' });
      }
      onRefresh?.();
    } catch (e) {
      console.error(e);
    } finally {
      setPausing(false);
      setResuming(false);
    }
  };

  return (
    <div className="p-5 space-y-4">
      {/* Controls */}
      <div className="p-4 rounded-lg border border-border bg-muted/30 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className={cn('w-2 h-2 rounded-full', statusColor)} />
            <span className="text-sm font-medium capitalize">{task.status}</span>
            {task.schedule && <span className="text-sm text-muted-foreground">· {task.schedule}</span>}
          </div>
          <div className="flex items-center gap-1.5">
            <button
              onClick={handlePauseResume}
              disabled={pausing || resuming}
              className={cn(
                "px-3 py-1 text-xs font-medium rounded-md transition-colors",
                task.status === 'active'
                  ? "border border-amber-300 text-amber-700 hover:bg-amber-50 dark:text-amber-400 dark:hover:bg-amber-950"
                  : "border border-green-300 text-green-700 hover:bg-green-50 dark:text-green-400 dark:hover:bg-green-950"
              )}
            >
              {pausing ? '...' : resuming ? '...' : task.status === 'active' ? 'Pause' : 'Resume'}
            </button>
            <button
              onClick={() => api.tasks.run(task.slug).then(() => onRefresh?.()).catch(console.error)}
              className="px-3 py-1 text-xs font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              <Play className="w-3 h-3 inline mr-1" />Run Now
            </button>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs">
          {task.next_run_at && (
            <div>
              <span className="text-muted-foreground block mb-0.5">Next run</span>
              <span className="font-medium">{new Date(task.next_run_at).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}</span>
            </div>
          )}
          {task.last_run_at && (
            <div>
              <span className="text-muted-foreground block mb-0.5">Last run</span>
              <span className="font-medium">{formatRelativeTime(task.last_run_at)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Run trajectory */}
      <div>
        <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide mb-2">
          Runs {outputs.length > 0 && `(${outputs.length})`}
        </p>
        {outputs.length > 0 ? (
          <div className="space-y-1">
            {outputs.map(output => (
              <button
                key={output.folder}
                onClick={() => onSelectOutput(output)}
                className={cn(
                  'w-full flex items-center justify-between p-3 rounded-lg text-sm transition-colors',
                  selectedFolder === output.folder ? 'bg-primary/10 border border-primary/20' : 'hover:bg-muted/50'
                )}
              >
                <div className="flex items-center gap-2.5">
                  <span className={cn('w-2 h-2 rounded-full', output.status === 'delivered' ? 'bg-green-500' : output.status === 'failed' ? 'bg-red-500' : 'bg-amber-500')} />
                  <span>{output.date}</span>
                </div>
                <span className="text-xs text-muted-foreground/50">{output.status === 'delivered' ? '✓' : output.status}</span>
              </button>
            ))}
          </div>
        ) : (
          <div className="py-6 text-center border border-dashed border-border/40 rounded-lg">
            <p className="text-xs text-muted-foreground/40">No runs yet</p>
          </div>
        )}
      </div>
    </div>
  );
}

// AgentsTab removed — replaced by ProcessTab (ADR-145 Gate 3)

// =============================================================================
// Right Panel: Task-Scoped Chat
// =============================================================================

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
  const { attachments, attachmentPreviews, error: fileError, uploadedDocs, handleFileSelect, handlePaste, removeAttachment, clearAttachments, getImagesForAPI, fileInputRef } = useFileAttachments();

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, status]);

  const adjustHeight = useCallback(() => {
    const ta = textareaRef.current;
    if (ta) { ta.style.height = 'auto'; ta.style.height = `${Math.min(ta.scrollHeight, 150)}px`; }
  }, []);
  useEffect(() => { adjustHeight(); }, [input, adjustHeight]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((!input.trim() && attachments.length === 0) || isLoading) return;
    const images = await getImagesForAPI();
    // Send with task surface context
    sendMessage(input, {
      surface: { type: 'task-detail', taskSlug },
      images: images.length > 0 ? images : undefined,
    });
    setInput('');
    clearAttachments();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(e as unknown as React.FormEvent); }
  };

  // Task-scoped plus menu — pre-LLM action cards
  const plusMenuActions: PlusMenuAction[] = [
    { id: 'run-task', label: 'Run now', icon: Play, verb: 'prompt', onSelect: () => setActionCard(RUN_TASK_CARD) },
    { id: 'adjust-task', label: 'Adjust task', icon: Target, verb: 'prompt', onSelect: () => setActionCard(ADJUST_TASK_CARD) },
    { id: 'feedback', label: 'Give feedback', icon: MessageCircle, verb: 'prompt', onSelect: () => setActionCard(FEEDBACK_TASK_CARD) },
    { id: 'web-research', label: 'Web research', icon: Globe, verb: 'prompt', onSelect: () => setActionCard(RESEARCH_TASK_CARD) },
  ];

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2.5">
        {messages.length === 0 && !isLoading && (
          <div className="text-center py-6">
            <MessageCircle className="w-5 h-5 text-muted-foreground/15 mx-auto mb-1.5" />
            <p className="text-[11px] text-muted-foreground/40">Ask anything about this task</p>
          </div>
        )}

        {messages.map(msg => (
          <div key={msg.id} className={cn('text-[13px] rounded-2xl px-3 py-2 max-w-[92%]', msg.role === 'user' ? 'bg-primary/10 ml-auto rounded-br-md' : 'bg-muted rounded-bl-md')}>
            <span className={cn("text-[9px] font-medium text-muted-foreground/50 tracking-wider block mb-1", msg.role === 'user' ? 'uppercase' : 'font-brand text-[10px]')}>
              {msg.role === 'user' ? 'You' : 'yarnnn'}
            </span>
            {msg.blocks && msg.blocks.length > 0 ? (
              <MessageBlocks blocks={msg.blocks} />
            ) : msg.role === 'assistant' && !msg.content && isLoading ? (
              <div className="flex items-center gap-1.5 text-muted-foreground text-xs"><Loader2 className="w-3 h-3 animate-spin" />Thinking...</div>
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
          <div className="flex items-center gap-1.5 text-muted-foreground text-xs"><Loader2 className="w-3 h-3 animate-spin" />Thinking...</div>
        )}

        {status.type === 'clarify' && pendingClarification && (
          <div className="space-y-2 bg-muted/50 rounded-lg p-3 border border-border">
            <p className="text-xs font-medium">{pendingClarification.question}</p>
            {pendingClarification.options?.length ? (
              <div className="flex flex-wrap gap-1.5">
                {pendingClarification.options.map((opt, i) => (
                  <button key={i} onClick={() => respondToClarification(opt)} className="px-2.5 py-1 text-[11px] rounded-lg border border-primary/30 bg-primary/5 text-primary hover:bg-primary/15 font-medium">{opt}</button>
                ))}
              </div>
            ) : <p className="text-[10px] text-muted-foreground">Type below</p>}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="px-3 pb-3 pt-1 border-t border-border shrink-0">
        {fileError && (
          <div className="mb-2 p-2 rounded-lg border border-destructive/30 bg-destructive/5 text-xs text-destructive">
            {fileError}
          </div>
        )}

        {uploadedDocs.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2 p-1.5 rounded-lg border border-border bg-muted/30">
            {uploadedDocs.map((doc, i) => (
              <div key={i} className="flex items-center gap-1.5 text-xs px-2 py-1 rounded bg-background border border-border">
                <span className="truncate max-w-[120px]">{doc.name}</span>
                <span className={doc.status === 'done' ? 'text-green-600' : doc.status === 'error' ? 'text-destructive' : 'text-muted-foreground'}>
                  {doc.status === 'uploading' ? '...' : doc.status === 'done' ? '✓' : '✗'}
                </span>
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
          <div className="flex items-end gap-1.5 border border-border bg-background rounded-xl focus-within:ring-2 focus-within:ring-primary/50">
            <input ref={fileInputRef} type="file" accept="image/*,.pdf,.docx,.txt,.md" multiple onChange={handleFileSelect} className="hidden" />
            <PlusMenu actions={plusMenuActions} disabled={isLoading} />
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              onPaste={handlePaste}
              disabled={isLoading}
              enterKeyHint="send"
              placeholder="Ask anything or type / ..."
              rows={1}
              className="flex-1 py-2.5 pr-1 text-sm bg-transparent resize-none focus:outline-none disabled:opacity-50 max-h-[150px]"
            />
            <button type="submit" disabled={isLoading || (!input.trim() && attachments.length === 0)} className="shrink-0 p-2.5 text-primary disabled:text-muted-foreground disabled:opacity-50 transition-colors"><Send className="w-4 h-4" /></button>
          </div>
          <div className="mt-1 flex items-center justify-between text-[9px] text-muted-foreground/40">
            <span>Enter to send</span>
            {tokenUsage && <span className="font-mono">{tokenUsage.totalTokens >= 1000 ? `${(tokenUsage.totalTokens / 1000).toFixed(1)}k` : tokenUsage.totalTokens} tokens</span>}
          </div>
        </form>
      </div>
    </div>
  );
}

// =============================================================================
// Main Task Page
// =============================================================================

export default function TaskPage() {
  const params = useParams();
  const router = useRouter();
  const slug = params?.slug as string;
  const { loadScopedHistory, sendMessage } = useTP();

  const [task, setTask] = useState<TaskDetail | null>(null);
  const [outputs, setOutputs] = useState<TaskOutput[]>([]);
  const [selectedOutput, setSelectedOutput] = useState<TaskOutput | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [leftTab, setLeftTab] = useState<'output' | 'deliverable' | 'schedule' | 'context'>('output');
  const [deliverableMd, setDeliverableMd] = useState<string | null>(null);

  const refreshData = useCallback(() => {
    if (!slug) return;
    api.tasks.get(slug).then(setTask).catch(console.error);
    api.tasks.listOutputs(slug, 10)
      .then(data => setOutputs(data?.outputs || []))
      .catch(() => {});
    // Refresh latest output only if we're viewing the most recent
    api.tasks.getLatestOutput(slug)
      .then(latest => {
        if (latest) setSelectedOutput(prev => {
          // Only auto-update if viewing latest or no selection
          if (!prev || prev.date === latest.date) return latest;
          return prev;
        });
      })
      .catch(() => {});
  }, [slug]);

  // Load task-scoped chat history (not global)
  useEffect(() => { if (slug) loadScopedHistory(undefined, slug); }, [slug, loadScopedHistory]);

  // Initial load
  useEffect(() => {
    if (!slug) return;
    Promise.all([
      api.tasks.get(slug).catch(() => null),
      api.tasks.listOutputs(slug, 10).catch(() => ({ outputs: [], total: 0 })),
      api.tasks.getLatestOutput(slug).catch(() => null),
      api.workspace.getFile(`/tasks/${slug}/DELIVERABLE.md`).catch(() => null),
    ]).then(([taskData, outputsData, latestOutput, deliverableFile]) => {
      if (!taskData) { setError('Task not found'); setLoading(false); return; }
      setTask(taskData);
      setOutputs(outputsData?.outputs || []);
      setSelectedOutput(latestOutput || null);
      if (deliverableFile?.content) setDeliverableMd(deliverableFile.content);
      setLoading(false);
    }).catch(() => { setError('Failed to load task'); setLoading(false); });
  }, [slug]);

  // Polling + visibility refresh (matches workfloor pattern)
  useEffect(() => {
    if (!slug || loading) return;
    const interval = setInterval(refreshData, 30000);
    const onFocus = () => { if (document.visibilityState === 'visible') refreshData(); };
    document.addEventListener('visibilitychange', onFocus);
    return () => { clearInterval(interval); document.removeEventListener('visibilitychange', onFocus); };
  }, [slug, loading, refreshData]);

  // Fetch full output content when selecting a historical run from ScheduleTab
  const handleSelectOutput = useCallback((entry: TaskOutput) => {
    if (!slug) return;
    // If entry already has content, use it directly
    if (entry.content || entry.html_content) {
      setSelectedOutput(entry);
      setLeftTab('output');
      return;
    }
    // Fetch the specific output by date folder
    const dateFolder = entry.folder || entry.date;
    if (!dateFolder) { setSelectedOutput(entry); setLeftTab('output'); return; }
    api.tasks.getOutput(slug, dateFolder)
      .then(full => { setSelectedOutput(full || entry); setLeftTab('output'); })
      .catch(() => { setSelectedOutput(entry); setLeftTab('output'); });
  }, [slug]);

  if (loading) return <div className="flex items-center justify-center h-full"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>;
  if (error || !task) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <p className="text-sm text-muted-foreground">{error || 'Task not found'}</p>
        <Link href="/workfloor" className="text-xs text-primary mt-2 hover:underline">Back to workfloor</Link>
      </div>
    );
  }

  const displayTitle = task.title || task.slug;

  // Right panel = Task-scoped chat
  const panelTabs: WorkspacePanelTab[] = [
    { id: 'chat', label: 'Chat', content: <TaskChatPanel taskSlug={slug} taskTitle={displayTitle} /> },
  ];

  // TP-style panel header — matches workfloor chat header
  const tpPanelHeader = (
    <div className="flex items-center justify-between px-3 py-2.5 border-b border-border bg-background z-10 shrink-0">
      <div className="flex items-center gap-2">
        <img src="/assets/logos/circleonly_yarnnn_1.svg" alt="" className="w-5 h-5" />
        <span className="text-xs font-medium">TP</span>
        <span className="text-[10px] text-muted-foreground/50 truncate max-w-[160px]">
          · viewing {displayTitle}
        </span>
      </div>
      <button onClick={() => router.back()} className="p-1.5 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted transition-colors">
        <X className="w-4 h-4" />
      </button>
    </div>
  );

  return (
    <WorkspaceLayout
      identity={{ icon: <FileText className="w-5 h-5" />, label: displayTitle }}
      breadcrumb={
        <button onClick={() => router.back()} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="w-4 h-4" />
        </button>
      }
      panelTabs={panelTabs}
      panelHeader={tpPanelHeader}
      panelDefaultOpen={true}
      panelDefaultPct={33}
    >
      {/* Left: Tabbed content */}
      <div className="flex flex-col flex-1 min-h-0">
        {/* Tab bar */}
        <div className="flex border-b border-border shrink-0 px-5">
          {([
            { key: 'output', label: 'Output' },
            { key: 'deliverable', label: 'Deliverable' },
            { key: 'schedule', label: 'Schedule' },
            { key: 'context', label: 'Context' },
          ] as const).map(tab => (
            <button
              key={tab.key}
              onClick={() => setLeftTab(tab.key)}
              className={cn(
                'px-3 py-2.5 text-sm font-medium border-b-2 transition-colors',
                leftTab === tab.key ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground/40 hover:text-muted-foreground'
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto">
          {leftTab === 'output' && <OutputTab task={task} output={selectedOutput} />}
          {leftTab === 'deliverable' && (
            <div className="p-5 space-y-4">
              {deliverableMd ? (
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <MarkdownRenderer content={deliverableMd} />
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No deliverable spec yet. Ask TP to set one up.
                </p>
              )}
            </div>
          )}
          {leftTab === 'schedule' && (
            <ScheduleTab
              task={task}
              outputs={outputs}
              selectedFolder={selectedOutput?.folder || selectedOutput?.date || null}
              onSelectOutput={handleSelectOutput}
              onRefresh={refreshData}
            />
          )}
          {leftTab === 'context' && (
            <div className="p-5 space-y-4">
              <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Context Domains</h3>
              <div className="space-y-3">
                {(task.context_reads?.length ?? 0) > 0 && (
                  <div>
                    <p className="text-[11px] text-muted-foreground mb-1">Reads from:</p>
                    <div className="flex flex-wrap gap-1.5">
                      {task.context_reads!.map(d => (
                        <span key={d} className="px-2 py-0.5 text-[11px] rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400">
                          {d}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {(task.context_writes?.length ?? 0) > 0 && (
                  <div>
                    <p className="text-[11px] text-muted-foreground mb-1">Writes to:</p>
                    <div className="flex flex-wrap gap-1.5">
                      {task.context_writes!.map(d => (
                        <span key={d} className="px-2 py-0.5 text-[11px] rounded-full bg-green-500/10 text-green-600 dark:text-green-400">
                          {d}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {task.output_category && (
                  <div>
                    <p className="text-[11px] text-muted-foreground mb-1">Output promoted to:</p>
                    <span className="px-2 py-0.5 text-[11px] rounded-full bg-purple-500/10 text-purple-600 dark:text-purple-400">
                      {task.output_category}
                    </span>
                  </div>
                )}
                {!task.context_reads?.length && !task.context_writes?.length && (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No context domains configured for this task.
                  </p>
                )}
              </div>
              {task.agent_slugs && task.agent_slugs.length > 0 && (
                <div className="pt-3 border-t border-border/50">
                  <p className="text-[11px] text-muted-foreground mb-1">Assigned agent:</p>
                  <p className="text-sm font-medium">{task.agent_slugs.join(', ')}</p>
                </div>
              )}
              {task.mode && (
                <div>
                  <p className="text-[11px] text-muted-foreground mb-1">Mode:</p>
                  <span className={cn(
                    "px-2 py-0.5 text-[11px] rounded-full",
                    task.mode === 'recurring' && "bg-blue-500/10 text-blue-600",
                    task.mode === 'goal' && "bg-amber-500/10 text-amber-600",
                    task.mode === 'reactive' && "bg-gray-500/10 text-gray-600",
                  )}>
                    {task.mode}
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </WorkspaceLayout>
  );
}
