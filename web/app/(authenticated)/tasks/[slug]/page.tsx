'use client';

/**
 * Task Page — v3: Tabbed Left + Task-Scoped Chat Right
 *
 * Left: [Output] [Task] tabs — output is hero, task tab has everything else
 * Right: Task-scoped TP chat (always visible, resizable)
 * Same WorkspaceLayout pattern as workfloor.
 *
 * Chat is task-scoped: different plus menu, different context injection,
 * session keyed by task_slug. See docs/design/TASK-SCOPED-TP.md.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Loader2,
  Play,
  FileText,
  Mail,
  Clock,
  Send,
  Search,
  Globe,
  RefreshCw,
  X,
  ListChecks,
  Target,
  MessageCircle,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useDesk } from '@/contexts/DeskContext';
import { useFileAttachments } from '@/hooks/useFileAttachments';
import type { TaskDetail, TaskOutput } from '@/types';
import ReactMarkdown from 'react-markdown';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import { WorkspaceLayout, type WorkspacePanelTab } from '@/components/desk/WorkspaceLayout';
import { CommandPicker } from '@/components/tp/CommandPicker';
import { PlusMenu, type PlusMenuAction } from '@/components/tp/PlusMenu';
import { MessageBlocks } from '@/components/tp/InlineToolCall';
import { ToolResultList } from '@/components/tp/ToolResultCard';

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

  if (output.html_content) {
    return (
      <iframe
        srcDoc={output.html_content}
        className="w-full h-full min-h-[500px] border-0 rounded-lg bg-white"
        sandbox="allow-same-origin"
        title="Task output"
      />
    );
  }

  // API returns 'content' (markdown text) — check both field names for compatibility
  const mdContent = (output as any).content || output.md_content;
  if (mdContent) {
    return (
      <div className="prose prose-sm dark:prose-invert max-w-none p-4">
        <ReactMarkdown>{mdContent}</ReactMarkdown>
      </div>
    );
  }

  return <p className="text-sm text-muted-foreground text-center py-8">Output available but content not loaded</p>;
}

// =============================================================================
// Left Panel: Task Tab (unified — schedule + runs + agents + definition)
// =============================================================================

function TaskTab({
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
  const agentSlugs = task.agent_slugs || [];

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
    <div className="p-4 space-y-4 max-w-xl overflow-y-auto">

      {/* ── Schedule controls (hero) ── */}
      <div className="p-3 rounded-lg border border-border bg-muted/30 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className={cn('w-2 h-2 rounded-full', statusColor)} />
            <span className="text-sm font-medium capitalize">{task.status}</span>
            {task.schedule && <span className="text-xs text-muted-foreground">· {task.schedule}</span>}
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
          {task.delivery && (
            <div>
              <span className="text-muted-foreground block mb-0.5">Delivery</span>
              <span className="font-medium flex items-center gap-1"><Mail className="w-3 h-3" />{task.delivery}</span>
            </div>
          )}
        </div>
      </div>

      {/* ── Runs ── */}
      <div>
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
          Runs {outputs.length > 0 && `(${outputs.length})`}
        </p>
        {outputs.length > 0 ? (
          <div className="space-y-1">
            {outputs.map(output => (
              <button
                key={output.folder}
                onClick={() => onSelectOutput(output)}
                className={cn(
                  'w-full flex items-center justify-between p-2.5 rounded-lg text-xs transition-colors',
                  selectedFolder === output.folder ? 'bg-primary/10 border border-primary/20' : 'hover:bg-muted/50'
                )}
              >
                <div className="flex items-center gap-2">
                  <span className={cn('w-1.5 h-1.5 rounded-full', output.status === 'delivered' ? 'bg-green-500' : output.status === 'failed' ? 'bg-red-500' : 'bg-amber-500')} />
                  <span>{output.date}</span>
                </div>
                <span className="text-muted-foreground/50">{output.status === 'delivered' ? '✓' : output.status}</span>
              </button>
            ))}
          </div>
        ) : (
          <div className="py-4 text-center border border-dashed border-border/40 rounded-lg">
            <p className="text-[10px] text-muted-foreground/40">No runs yet</p>
          </div>
        )}
      </div>

      {/* ── Agents ── */}
      {agentSlugs.length > 0 && (
        <div>
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
            Agents {agentSlugs.length > 1 && `(${agentSlugs.length} — sequential)`}
          </p>
          <div className="space-y-1">
            {agentSlugs.map((slug, idx) => (
              <Link
                key={slug}
                href={`/agents/${slug}`}
                className="flex items-center gap-2.5 p-2.5 rounded-lg border border-border hover:border-primary/30 hover:bg-primary/5 transition-colors text-xs"
              >
                {agentSlugs.length > 1 && (
                  <span className="w-5 h-5 rounded-full bg-muted flex items-center justify-center text-[10px] font-mono font-bold text-muted-foreground">{idx + 1}</span>
                )}
                <span className="font-medium">{slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
                <span className="text-muted-foreground ml-auto">{slug}</span>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* ── Objective ── */}
      {task.objective && (
        <details className="group" open>
          <summary className="text-xs font-medium text-muted-foreground uppercase tracking-wide cursor-pointer hover:text-foreground transition-colors">
            Objective
          </summary>
          <div className="text-xs space-y-1 mt-2 pl-1">
            {task.objective.deliverable && <p><span className="text-muted-foreground">Deliverable:</span> {task.objective.deliverable}</p>}
            {task.objective.audience && <p><span className="text-muted-foreground">Audience:</span> {task.objective.audience}</p>}
            {task.objective.purpose && <p><span className="text-muted-foreground">Purpose:</span> {task.objective.purpose}</p>}
            {task.objective.format && <p><span className="text-muted-foreground">Format:</span> {task.objective.format}</p>}
          </div>
        </details>
      )}

      {/* ── Success Criteria ── */}
      {task.success_criteria && task.success_criteria.length > 0 && (
        <details className="group">
          <summary className="text-xs font-medium text-muted-foreground uppercase tracking-wide cursor-pointer hover:text-foreground transition-colors">
            Success Criteria ({task.success_criteria.length})
          </summary>
          <ul className="text-xs space-y-1 list-disc list-inside text-muted-foreground mt-2 pl-1">
            {task.success_criteria.map((c, i) => <li key={i}>{c}</li>)}
          </ul>
        </details>
      )}

      {/* ── Output Spec ── */}
      {task.output_spec && task.output_spec.length > 0 && (
        <details className="group">
          <summary className="text-xs font-medium text-muted-foreground uppercase tracking-wide cursor-pointer hover:text-foreground transition-colors">
            Output Spec ({task.output_spec.length} sections)
          </summary>
          <ul className="text-xs space-y-1 list-disc list-inside text-muted-foreground mt-2 pl-1">
            {task.output_spec.map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        </details>
      )}
    </div>
  );
}

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
  const [commandPickerOpen, setCommandPickerOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { attachments, attachmentPreviews, handleFileSelect, handlePaste, removeAttachment, clearAttachments, getImagesForAPI, fileInputRef } = useFileAttachments();

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, status]);

  const adjustHeight = useCallback(() => {
    const ta = textareaRef.current;
    if (ta) { ta.style.height = 'auto'; ta.style.height = `${Math.min(ta.scrollHeight, 150)}px`; }
  }, []);
  useEffect(() => { adjustHeight(); }, [input, adjustHeight]);

  const commandQuery = input.startsWith('/') ? input.slice(1).split(' ')[0] : null;
  useEffect(() => { setCommandPickerOpen(commandQuery !== null && !input.includes(' ')); }, [commandQuery, input]);

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

  // Task-scoped plus menu — different from workfloor
  const plusMenuActions: PlusMenuAction[] = [
    { id: 'run-task', label: 'Run this task now', icon: Play, verb: 'prompt', onSelect: () => { setInput(`Run the task "${taskTitle}" now`); textareaRef.current?.focus(); } },
    { id: 'adjust-focus', label: 'Adjust focus', icon: Target, verb: 'prompt', onSelect: () => { setInput('For this task, focus on '); textareaRef.current?.focus(); } },
    { id: 'search-platforms', label: 'Search platforms', icon: Search, verb: 'prompt', onSelect: () => { setInput('Search across my connected platforms for '); textareaRef.current?.focus(); } },
    { id: 'web-search', label: 'Web search', icon: Globe, verb: 'prompt', onSelect: () => { setInput('Search the web for '); textareaRef.current?.focus(); } },
  ];

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2.5">
        {messages.length === 0 && !isLoading && (
          <div className="text-center py-6">
            <MessageCircle className="w-5 h-5 text-muted-foreground/15 mx-auto mb-1.5" />
            <p className="text-[11px] text-muted-foreground/40">Steer this task — adjust focus, review output, or trigger a run</p>
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
                  <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-0.5"><ReactMarkdown>{msg.content}</ReactMarkdown></div>
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
        <CommandPicker query={commandQuery ?? ''} onSelect={(cmd) => { setInput(cmd + ' '); setCommandPickerOpen(false); textareaRef.current?.focus(); }} onClose={() => setCommandPickerOpen(false)} isOpen={commandPickerOpen} />

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
              placeholder="Steer this task..."
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
  const slug = params?.slug as string;
  const { loadScopedHistory } = useTP();

  const [task, setTask] = useState<TaskDetail | null>(null);
  const [outputs, setOutputs] = useState<TaskOutput[]>([]);
  const [selectedOutput, setSelectedOutput] = useState<TaskOutput | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [leftTab, setLeftTab] = useState<'output' | 'task'>('output');

  const loadTask = useCallback(() => {
    if (!slug) return;
    api.tasks.get(slug).then(setTask).catch(console.error);
  }, [slug]);

  useEffect(() => { loadScopedHistory(); }, [loadScopedHistory]);

  useEffect(() => {
    if (!slug) return;
    Promise.all([
      api.tasks.get(slug).catch(() => null),
      api.tasks.listOutputs(slug, 10).catch(() => ({ outputs: [], total: 0 })),
      api.tasks.getLatestOutput(slug).catch(() => null),
    ]).then(([taskData, outputsData, latestOutput]) => {
      if (!taskData) { setError('Task not found'); setLoading(false); return; }
      setTask(taskData);
      setOutputs(outputsData?.outputs || []);
      setSelectedOutput(latestOutput || null);
      setLoading(false);
    }).catch(() => { setError('Failed to load task'); setLoading(false); });
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

  // Right panel = Task-scoped chat
  const panelTabs: WorkspacePanelTab[] = [
    { id: 'chat', label: 'Chat', content: <TaskChatPanel taskSlug={slug} taskTitle={task.title} /> },
  ];

  return (
    <WorkspaceLayout
      identity={{ icon: <FileText className="w-5 h-5" />, label: task.title }}
      breadcrumb={
        <Link href="/workfloor" className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="w-4 h-4" />
        </Link>
      }
      panelTabs={panelTabs}
      panelDefaultOpen={true}
      panelDefaultPct={40}
    >
      {/* Left: Tabbed content */}
      <div className="flex flex-col flex-1 min-h-0">
        {/* Tab bar */}
        <div className="flex border-b border-border shrink-0 px-2">
          {(['output', 'task'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setLeftTab(tab)}
              className={cn(
                'px-3 py-2 text-xs font-medium border-b-2 transition-colors capitalize',
                leftTab === tab ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground/50 hover:text-muted-foreground'
              )}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto">
          {leftTab === 'output' && <OutputTab task={task} output={selectedOutput} />}
          {leftTab === 'task' && (
            <TaskTab
              task={task}
              outputs={outputs}
              selectedFolder={selectedOutput?.folder || null}
              onSelectOutput={(o) => { setSelectedOutput(o); setLeftTab('output'); }}
              onRefresh={loadTask}
            />
          )}
        </div>
      </div>
    </WorkspaceLayout>
  );
}
