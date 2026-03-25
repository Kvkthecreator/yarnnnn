'use client';

/**
 * Task Page — ADR-139: Task Working Surface
 *
 * Left: [Output] [Chat] tabs — output is hero, chat for task-scoped TP
 * Right: Task details, objective, criteria, run history
 *
 * Backend dependency: /api/tasks/{slug} endpoints (ADR-138 Phase 3)
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Loader2,
  Play,
  Clock,
  Mail,
  MessageSquare,
  FileText,
  ChevronRight,
  Send,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useDesk } from '@/contexts/DeskContext';
import type { TaskDetail, TaskOutput } from '@/types';
import ReactMarkdown from 'react-markdown';
import { cn } from '@/lib/utils';
import { MessageBlocks } from '@/components/tp/InlineToolCall';
import { ToolResultList } from '@/components/tp/ToolResultCard';
import { WorkspaceLayout, WorkspacePanelTab } from '@/components/desk/WorkspaceLayout';
import { api } from '@/lib/api/client';

// =============================================================================
// Helpers
// =============================================================================

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

function OutputView({ task, output }: { task: TaskDetail; output: TaskOutput | null }) {
  if (!output) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <FileText className="w-10 h-10 text-muted-foreground/20 mb-3" />
        <p className="text-sm text-muted-foreground">No output yet</p>
        {task.next_run_at && (
          <p className="text-xs text-muted-foreground/60 mt-1">
            Next run: {formatRelativeTime(task.next_run_at)}
          </p>
        )}
      </div>
    );
  }

  // Prefer HTML, fallback to markdown
  if (output.html_content) {
    return (
      <div className="p-4 overflow-y-auto flex-1">
        <iframe
          srcDoc={output.html_content}
          className="w-full min-h-[600px] border-0 rounded-lg bg-white"
          sandbox="allow-same-origin"
          title="Task output"
        />
      </div>
    );
  }

  if (output.md_content) {
    return (
      <div className="p-5 overflow-y-auto flex-1">
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <ReactMarkdown>{output.md_content}</ReactMarkdown>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
      Output available but content not loaded
    </div>
  );
}

// =============================================================================
// Left Panel: Chat Tab (task-scoped TP)
// =============================================================================

function TaskChat({ taskSlug }: { taskSlug: string }) {
  const {
    messages,
    sendMessage,
    isLoading,
    status,
    loadScopedHistory,
  } = useTP();
  const { surface } = useDesk();

  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // TODO: Load task-scoped history when backend supports task_slug sessions
  useEffect(() => {
    loadScopedHistory();
  }, [loadScopedHistory]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, status]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    // Send with task surface context
    sendMessage(input, {
      surface: { type: 'task-detail', taskSlug },
    });
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {messages.length === 0 && !isLoading && (
          <div className="text-center py-8">
            <MessageSquare className="w-8 h-8 text-muted-foreground/20 mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">
              Steer this task — adjust focus, criteria, or output format.
            </p>
          </div>
        )}

        {messages.map(msg => (
          <div
            key={msg.id}
            className={cn(
              'text-sm rounded-2xl px-4 py-3 max-w-[85%]',
              msg.role === 'user'
                ? 'bg-primary/10 ml-auto rounded-br-md'
                : 'bg-muted rounded-bl-md'
            )}
          >
            <span className={cn(
              "text-[10px] font-medium text-muted-foreground/70 tracking-wider block mb-1.5",
              msg.role === 'user' ? 'uppercase' : 'font-brand text-[11px]'
            )}>
              {msg.role === 'user' ? 'You' : 'yarnnn'}
            </span>
            {msg.blocks && msg.blocks.length > 0 ? (
              <MessageBlocks blocks={msg.blocks} />
            ) : msg.role === 'assistant' ? (
              <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-1">
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>
            ) : (
              <p className="whitespace-pre-wrap">{msg.content}</p>
            )}
            {msg.toolResults && msg.toolResults.length > 0 && (
              <ToolResultList results={msg.toolResults} compact />
            )}
          </div>
        ))}

        {status.type === 'thinking' && (
          <div className="flex items-center gap-2 text-muted-foreground text-sm">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Thinking...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-4 pb-4 pt-2 shrink-0">
        <form onSubmit={handleSubmit}>
          <div className="flex items-end gap-2 border border-border bg-background shadow-sm rounded-xl focus-within:ring-2 focus-within:ring-primary/50">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              enterKeyHint="send"
              placeholder="Steer this task..."
              rows={1}
              className="flex-1 py-3 pl-4 pr-2 text-sm bg-transparent resize-none focus:outline-none disabled:opacity-50 max-h-[120px]"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="shrink-0 p-3 text-primary hover:text-primary/80 disabled:text-muted-foreground disabled:opacity-50 transition-colors"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// =============================================================================
// Right Panel: Task Details
// =============================================================================

function TaskDetailsPanel({
  task,
  outputs,
  onSelectOutput,
}: {
  task: TaskDetail;
  outputs: TaskOutput[];
  onSelectOutput: (output: TaskOutput) => void;
}) {
  const statusColor = task.status === 'active' ? 'bg-green-500'
    : task.status === 'paused' ? 'bg-amber-500'
    : task.status === 'completed' ? 'bg-blue-500' : 'bg-gray-400';

  return (
    <div className="p-3 space-y-5">
      {/* Metadata */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className={cn('w-2 h-2 rounded-full', statusColor)} />
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {task.status}
          </span>
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs">
          {task.schedule && (
            <div>
              <span className="text-muted-foreground">Cadence</span>
              <p className="font-medium">{task.schedule}</p>
            </div>
          )}
          {task.next_run_at && (
            <div>
              <span className="text-muted-foreground">Next run</span>
              <p className="font-medium">{formatRelativeTime(task.next_run_at)}</p>
            </div>
          )}
          {task.delivery && (
            <div>
              <span className="text-muted-foreground">Delivery</span>
              <p className="font-medium flex items-center gap-1">
                <Mail className="w-3 h-3" />
                {task.delivery}
              </p>
            </div>
          )}
          {task.agent_slugs?.[0] && (
            <div>
              <span className="text-muted-foreground">Agent</span>
              <p className="font-medium">{task.agent_slugs[0]}</p>
            </div>
          )}
        </div>
      </div>

      {/* Objective */}
      {task.objective && (
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Objective</p>
          <div className="text-xs space-y-1">
            {task.objective.deliverable && <p><span className="text-muted-foreground">Deliverable:</span> {task.objective.deliverable}</p>}
            {task.objective.audience && <p><span className="text-muted-foreground">Audience:</span> {task.objective.audience}</p>}
            {task.objective.purpose && <p><span className="text-muted-foreground">Purpose:</span> {task.objective.purpose}</p>}
            {task.objective.format && <p><span className="text-muted-foreground">Format:</span> {task.objective.format}</p>}
          </div>
        </div>
      )}

      {/* Success Criteria */}
      {task.success_criteria && task.success_criteria.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Success Criteria</p>
          <ul className="text-xs space-y-1 list-disc list-inside text-muted-foreground">
            {task.success_criteria.map((c, i) => <li key={i}>{c}</li>)}
          </ul>
        </div>
      )}

      {/* Run History */}
      {outputs.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Run History</p>
          <div className="space-y-1">
            {outputs.map((output, i) => (
              <button
                key={output.folder}
                onClick={() => onSelectOutput(output)}
                className="w-full flex items-center justify-between p-2 rounded-md hover:bg-muted/50 transition-colors text-xs"
              >
                <div className="flex items-center gap-2">
                  <span className={cn(
                    'w-1.5 h-1.5 rounded-full',
                    output.status === 'delivered' ? 'bg-green-500' : output.status === 'failed' ? 'bg-red-500' : 'bg-amber-500'
                  )} />
                  <span>{output.date}</span>
                </div>
                <span className="text-muted-foreground">{output.status === 'delivered' ? '✓' : output.status}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={() => api.tasks.run(task.slug).catch(console.error)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <Play className="w-3 h-3" />
          Run Now
        </button>
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

  const [task, setTask] = useState<TaskDetail | null>(null);
  const [outputs, setOutputs] = useState<TaskOutput[]>([]);
  const [selectedOutput, setSelectedOutput] = useState<TaskOutput | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [leftTab, setLeftTab] = useState<'output' | 'chat'>('output');

  // Load task data
  useEffect(() => {
    if (!slug) return;

    Promise.all([
      api.tasks.get(slug).catch(() => null),
      api.tasks.listOutputs(slug, 10).catch(() => ({ outputs: [], total: 0 })),
      api.tasks.getLatestOutput(slug).catch(() => null),
    ]).then(([taskData, outputsData, latestOutput]) => {
      if (!taskData) {
        setError('Task not found');
        setLoading(false);
        return;
      }
      setTask(taskData);
      setOutputs(outputsData.outputs);
      setSelectedOutput(latestOutput);
      setLoading(false);
    }).catch(() => {
      setError('Failed to load task');
      setLoading(false);
    });
  }, [slug]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !task) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <p className="text-sm text-muted-foreground">{error || 'Task not found'}</p>
        <Link href="/workfloor" className="text-xs text-primary mt-2 hover:underline">
          Back to workfloor
        </Link>
      </div>
    );
  }

  const panelTabs: WorkspacePanelTab[] = [
    {
      id: 'details',
      label: 'Details',
      content: (
        <TaskDetailsPanel
          task={task}
          outputs={outputs}
          onSelectOutput={setSelectedOutput}
        />
      ),
    },
  ];

  return (
    <WorkspaceLayout
      identity={{
        icon: <FileText className="w-5 h-5" />,
        label: task.title,
      }}
      breadcrumb={
        <Link href="/workfloor" className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="w-4 h-4" />
          <span className="hidden sm:inline">Workfloor</span>
        </Link>
      }
      panelTabs={panelTabs}
      panelDefaultOpen={true}
      panelDefaultPct={35}
    >
      <div className="flex flex-col flex-1 min-h-0">
        {/* Left tab bar */}
        <div className="flex border-b border-border shrink-0 px-2">
          <button
            onClick={() => setLeftTab('output')}
            className={cn(
              'px-3 py-2.5 text-sm font-medium border-b-2 transition-colors',
              leftTab === 'output'
                ? 'border-primary text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            Output
          </button>
          <button
            onClick={() => setLeftTab('chat')}
            className={cn(
              'px-3 py-2.5 text-sm font-medium border-b-2 transition-colors',
              leftTab === 'chat'
                ? 'border-primary text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            Chat
          </button>
        </div>

        {/* Left content */}
        {leftTab === 'output' ? (
          <OutputView task={task} output={selectedOutput} />
        ) : (
          <TaskChat taskSlug={slug} />
        )}
      </div>
    </WorkspaceLayout>
  );
}
