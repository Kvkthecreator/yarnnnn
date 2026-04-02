'use client';

/**
 * Tasks Surface — Task command center with TP chat drawer
 *
 * Main content: task list with status filters.
 * Right: TP chat drawer (FAB to open), context-aware.
 */

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  ListChecks,
  Loader2,
  ChevronRight,
  Clock,
  Play,
  Pause,
  CheckCircle2,
  Archive,
  X,
  MessageCircle,
  Globe,
  Upload,
  Settings2,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import type { Task } from '@/types';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import { ChatPanel } from '@/components/tp/ChatPanel';
import { ContextSetup } from '@/components/tp/ContextSetup';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';

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

const STATUS_CONFIG = {
  active: { icon: Play, color: 'text-green-500', bg: 'bg-green-500', label: 'Active' },
  paused: { icon: Pause, color: 'text-amber-500', bg: 'bg-amber-500', label: 'Paused' },
  completed: { icon: CheckCircle2, color: 'text-blue-500', bg: 'bg-blue-500', label: 'Completed' },
  archived: { icon: Archive, color: 'text-gray-400', bg: 'bg-gray-400', label: 'Archived' },
};

export default function TasksPage() {
  const { loadScopedHistory, sendMessage } = useTP();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string | null>(null);
  const [chatOpen, setChatOpen] = useState(false);

  useEffect(() => { loadScopedHistory(); }, [loadScopedHistory]);

  const refreshTasks = useCallback(() => {
    api.tasks.list()
      .then(setTasks)
      .catch(() => setTasks([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refreshTasks();
    const interval = setInterval(refreshTasks, 30000);
    const onFocus = () => { if (document.visibilityState === 'visible') refreshTasks(); };
    document.addEventListener('visibilitychange', onFocus);
    return () => { clearInterval(interval); document.removeEventListener('visibilitychange', onFocus); };
  }, [refreshTasks]);

  const filtered = filter ? tasks.filter(t => t.status === filter) : tasks;
  const activeTasks = tasks.filter(t => t.status !== 'archived');

  const statusCounts = {
    all: tasks.length,
    active: tasks.filter(t => t.status === 'active').length,
    paused: tasks.filter(t => t.status === 'paused').length,
    completed: tasks.filter(t => t.status === 'completed').length,
  };

  const plusMenuActions: PlusMenuAction[] = [
    { id: 'create-task', label: 'Create a task', icon: ListChecks, verb: 'prompt', onSelect: () => { sendMessage('I want to create a task. What do you suggest based on my context?'); } },
    { id: 'update-info', label: 'Update my info', icon: Settings2, verb: 'prompt', onSelect: () => { setChatOpen(true); } },
    { id: 'web-search', label: 'Web search', icon: Globe, verb: 'prompt', onSelect: () => { setChatOpen(true); } },
    { id: 'upload-file', label: 'Upload file', icon: Upload, verb: 'attach', onSelect: () => { } },
  ];

  const emptyState = activeTasks.length === 0 ? (
    <ContextSetup
      onSubmit={(msg) => { sendMessage(msg); }}
      showSkipOptions
      onSkipAction={(msg) => { sendMessage(msg); }}
    />
  ) : (
    <div className="space-y-3">
      <div className="text-center">
        <MessageCircle className="w-5 h-5 text-muted-foreground/15 mx-auto mb-1.5" />
        <p className="text-[11px] text-muted-foreground/40">Quick actions</p>
      </div>
      <div className="flex flex-col gap-1.5">
        <button
          onClick={() => { sendMessage('How are my tasks doing?'); }}
          className="text-left text-[11px] px-3 py-2 rounded-lg border border-border/50 text-muted-foreground hover:text-foreground hover:border-border hover:bg-muted/50 transition-colors"
        >
          How are my tasks doing?
        </button>
        <button
          onClick={() => { sendMessage('I want to create a new task. What do you suggest?'); }}
          className="text-left text-[11px] px-3 py-2 rounded-lg border border-border/50 text-muted-foreground hover:text-foreground hover:border-border hover:bg-muted/50 transition-colors"
        >
          Create a new task
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex h-full overflow-hidden">
      {/* Main: Task list */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 py-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-2xl font-medium mb-1">Tasks</h1>
            <p className="text-sm text-muted-foreground">
              Your defined work — what gets produced, on what cadence, delivered where.
            </p>
          </div>

          {/* Filters */}
          <div className="flex gap-2 mb-6">
            {[
              { key: null, label: 'All', count: statusCounts.all },
              { key: 'active', label: 'Active', count: statusCounts.active },
              { key: 'paused', label: 'Paused', count: statusCounts.paused },
              { key: 'completed', label: 'Completed', count: statusCounts.completed },
            ].map(f => (
              <button
                key={f.key ?? 'all'}
                onClick={() => setFilter(f.key)}
                className={cn(
                  'px-3 py-1.5 text-xs font-medium rounded-full border transition-colors',
                  filter === f.key
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-border text-muted-foreground hover:text-foreground hover:border-foreground/30'
                )}
              >
                {f.label} {f.count > 0 && <span className="ml-1 opacity-60">{f.count}</span>}
              </button>
            ))}
          </div>

          {/* Content */}
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-16">
              <ListChecks className="w-10 h-10 text-muted-foreground/20 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground mb-1">
                {tasks.length === 0 ? 'No tasks yet' : 'No matching tasks'}
              </p>
              <p className="text-xs text-muted-foreground/60">
                {tasks.length === 0
                  ? 'Tell TP what work you need done — "track my competitors" or "weekly market brief".'
                  : 'Try a different filter.'}
              </p>
              {tasks.length === 0 && (
                <button
                  onClick={() => setChatOpen(true)}
                  className="inline-block mt-4 px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
                >
                  Get started
                </button>
              )}
            </div>
          ) : (
            <div className="border border-border rounded-xl overflow-hidden divide-y divide-border">
              {filtered.map(task => {
                const status = STATUS_CONFIG[task.status] || STATUS_CONFIG.active;
                return (
                  <Link
                    key={task.id}
                    href={`/tasks/${task.slug}`}
                    className="flex items-center justify-between p-4 hover:bg-muted/50 transition-colors group"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2.5 mb-1">
                        <span className={cn('w-2 h-2 rounded-full shrink-0', status.bg)} />
                        <span className="text-sm font-medium truncate">{task.title}</span>
                        <span className={cn('text-[10px] uppercase tracking-wider font-medium', status.color)}>
                          {status.label}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 ml-[18px] text-xs text-muted-foreground">
                        {task.schedule && (
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {task.schedule}
                          </span>
                        )}
                        {task.last_run_at && (
                          <span>Last: {formatRelativeTime(task.last_run_at)}</span>
                        )}
                        {task.agent_slugs?.[0] && (
                          <span className="text-muted-foreground/60">Agent: {task.agent_slugs[0]}</span>
                        )}
                        {task.delivery && (
                          <span className="text-muted-foreground/60">{task.delivery}</span>
                        )}
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-muted-foreground/30 group-hover:text-foreground transition-colors shrink-0 ml-4" />
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Right: Chat panel or FAB */}
      {chatOpen && (
        <div className="w-[380px] shrink-0 border-l border-border flex flex-col bg-background overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2.5 border-b border-border bg-background z-10 shrink-0">
            <div className="flex items-center gap-2">
              <img src="/assets/logos/circleonly_yarnnn_1.svg" alt="" className="w-5 h-5" />
              <span className="text-xs font-medium">TP</span>
            </div>
            <button onClick={() => setChatOpen(false)} className="p-1.5 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="flex-1 min-h-0">
            <ChatPanel
              plusMenuActions={plusMenuActions}
              emptyState={emptyState}
            />
          </div>
        </div>
      )}

      {!chatOpen && (
        <button
          onClick={() => setChatOpen(true)}
          className="fixed bottom-6 right-6 z-50 w-12 h-12 rounded-full shadow-lg hover:shadow-xl hover:scale-110 transition-all flex items-center justify-center group"
          title="Chat with TP"
        >
          <img
            src="/assets/logos/circleonly_yarnnn_1.svg"
            alt="yarnnn"
            className="w-12 h-12 transition-transform duration-500 group-hover:rotate-180"
          />
        </button>
      )}
    </div>
  );
}
