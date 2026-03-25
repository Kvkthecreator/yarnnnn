'use client';

/**
 * Task Page — ADR-139 v2: Output Hero + Chat Drawer
 *
 * Left: Latest rendered output (full width hero)
 * Right: Task details, objective, criteria, run trajectory
 * Chat: Drawer (FAB + ⌘K, task-scoped TP)
 */

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Loader2,
  Play,
  FileText,
  Mail,
  Clock,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import type { TaskDetail, TaskOutput } from '@/types';
import ReactMarkdown from 'react-markdown';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import { ChatDrawer } from '@/components/desk/ChatDrawer';

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
      setOutputs(outputsData.outputs);
      setSelectedOutput(latestOutput);
      setLoading(false);
    }).catch(() => { setError('Failed to load task'); setLoading(false); });
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
        <Link href="/workfloor" className="text-xs text-primary mt-2 hover:underline">Back to workfloor</Link>
      </div>
    );
  }

  const statusColor = task.status === 'active' ? 'bg-green-500'
    : task.status === 'paused' ? 'bg-amber-500'
    : task.status === 'completed' ? 'bg-blue-500' : 'bg-gray-400';

  return (
    <div className="h-full flex overflow-hidden">
      {/* ===== Left: Output Hero ===== */}
      <div className="flex-1 overflow-y-auto flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border shrink-0 flex items-center gap-3">
          <Link href="/workfloor" className="text-muted-foreground hover:text-foreground transition-colors">
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div className="min-w-0 flex-1">
            <h1 className="text-base font-medium truncate">{task.title}</h1>
            <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
              <span className={cn('w-1.5 h-1.5 rounded-full', statusColor)} />
              <span>{task.status}</span>
              {task.schedule && <><span className="opacity-30">|</span><span>{task.schedule}</span></>}
              {task.agent_slugs?.[0] && <><span className="opacity-30">|</span><span>{task.agent_slugs[0]}</span></>}
            </div>
          </div>
        </div>

        {/* Output content */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-3xl mx-auto">
            {selectedOutput ? (
              selectedOutput.html_content ? (
                <iframe
                  srcDoc={selectedOutput.html_content}
                  className="w-full min-h-[600px] border-0 rounded-lg bg-white"
                  sandbox="allow-same-origin"
                  title="Task output"
                />
              ) : selectedOutput.md_content ? (
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <ReactMarkdown>{selectedOutput.md_content}</ReactMarkdown>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-8">Output available but content not loaded</p>
              )
            ) : (
              <div className="text-center py-16">
                <FileText className="w-10 h-10 text-muted-foreground/15 mx-auto mb-4" />
                <p className="text-sm text-muted-foreground">No output yet</p>
                {task.next_run_at && (
                  <p className="text-xs text-muted-foreground/60 mt-1 flex items-center justify-center gap-1">
                    <Clock className="w-3 h-3" />
                    Next run: {formatRelativeTime(task.next_run_at)}
                  </p>
                )}
                <button
                  onClick={() => api.tasks.run(task.slug).catch(console.error)}
                  className="mt-4 inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
                >
                  <Play className="w-3.5 h-3.5" />
                  Run Now
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ===== Right: Task Details ===== */}
      <div className="hidden lg:flex lg:flex-col w-[340px] border-l border-border bg-muted/20 overflow-y-auto shrink-0">
        <div className="p-4 space-y-5">
          {/* Metadata */}
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="p-2.5 rounded-lg border border-border bg-background">
              <span className="text-muted-foreground block mb-0.5">Status</span>
              <span className="font-medium flex items-center gap-1.5">
                <span className={cn('w-1.5 h-1.5 rounded-full', statusColor)} />
                {task.status}
              </span>
            </div>
            {task.schedule && (
              <div className="p-2.5 rounded-lg border border-border bg-background">
                <span className="text-muted-foreground block mb-0.5">Cadence</span>
                <span className="font-medium">{task.schedule}</span>
              </div>
            )}
            {task.next_run_at && (
              <div className="p-2.5 rounded-lg border border-border bg-background">
                <span className="text-muted-foreground block mb-0.5">Next run</span>
                <span className="font-medium">{formatRelativeTime(task.next_run_at)}</span>
              </div>
            )}
            {task.delivery && (
              <div className="p-2.5 rounded-lg border border-border bg-background">
                <span className="text-muted-foreground block mb-0.5">Delivery</span>
                <span className="font-medium flex items-center gap-1"><Mail className="w-3 h-3" />{task.delivery}</span>
              </div>
            )}
          </div>

          {/* Objective */}
          {task.objective && (
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">Objective</p>
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
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">Success Criteria</p>
              <ul className="text-xs space-y-1 list-disc list-inside text-muted-foreground">
                {task.success_criteria.map((c, i) => <li key={i}>{c}</li>)}
              </ul>
            </div>
          )}

          {/* Run Trajectory */}
          {outputs.length > 0 && (
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">Run Trajectory</p>
              <div className="space-y-1">
                {outputs.map((output) => (
                  <button
                    key={output.folder}
                    onClick={() => setSelectedOutput(output)}
                    className={cn(
                      'w-full flex items-center justify-between p-2 rounded-lg text-xs transition-colors',
                      selectedOutput?.folder === output.folder ? 'bg-primary/10 border border-primary/20' : 'hover:bg-muted/50'
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <span className={cn(
                        'w-1.5 h-1.5 rounded-full',
                        output.status === 'delivered' ? 'bg-green-500' : output.status === 'failed' ? 'bg-red-500' : 'bg-amber-500'
                      )} />
                      <span>{output.date}</span>
                    </div>
                    <span className="text-muted-foreground/50">{output.status === 'delivered' ? '✓' : output.status}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2">
            <button
              onClick={() => api.tasks.run(task.slug).catch(console.error)}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              <Play className="w-3 h-3" />
              Run Now
            </button>
          </div>
        </div>
      </div>

      {/* ===== Chat Drawer (task-scoped) ===== */}
      <ChatDrawer surfaceOverride={{ type: 'task-detail', taskSlug: slug }} />
    </div>
  );
}
