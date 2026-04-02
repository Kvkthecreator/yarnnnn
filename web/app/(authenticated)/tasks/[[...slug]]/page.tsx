'use client';

/**
 * Unified Task Surface — Three-panel explorer
 *
 * Left: TaskTreeNav (task list as expandable tree)
 * Center: TaskContentView (dynamic dispatch by view type)
 * Right: TP chat drawer (FAB to open)
 *
 * Handles both /tasks (auto-selects first active) and /tasks/[slug].
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Loader2,
  X,
  FolderOpen,
  MessageCircle,
  ListChecks,
  Globe,
  Upload,
  Settings2,
  Play,
  Target,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import type { Task, TaskDetail, TaskOutput } from '@/types';
import { api } from '@/lib/api/client';
import { TaskTreeNav, getDefaultView, type TaskView } from '@/components/tasks/TaskTreeNav';
import { TaskContentView } from '@/components/tasks/TaskContentView';
import { ChatPanel } from '@/components/tp/ChatPanel';
import { ContextSetup } from '@/components/tp/ContextSetup';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';
import {
  RUN_TASK_CARD,
  ADJUST_TASK_CARD,
  RESEARCH_TASK_CARD,
  FEEDBACK_TASK_CARD,
  type ActionCardConfig,
} from '@/components/tp/InlineActionCard';

export default function TaskSurface() {
  const params = useParams();
  const router = useRouter();
  const { loadScopedHistory, sendMessage } = useTP();

  // Extract slug from optional catch-all params
  const slugFromUrl = params?.slug ? (params.slug as string[])[0] : null;

  // ── State ──
  const [tasks, setTasks] = useState<Task[]>([]);
  const [tasksLoading, setTasksLoading] = useState(true);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(slugFromUrl);
  const [selectedView, setSelectedView] = useState<TaskView>('output');
  const [filter, setFilter] = useState<string | null>(null);

  const [taskDetail, setTaskDetail] = useState<TaskDetail | null>(null);
  const [outputs, setOutputs] = useState<TaskOutput[]>([]);
  const [selectedOutput, setSelectedOutput] = useState<TaskOutput | null>(null);
  const [deliverableMd, setDeliverableMd] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [mutationPending, setMutationPending] = useState(false);

  const [panelOpen, setPanelOpen] = useState(true);
  const [chatOpen, setChatOpen] = useState(false);
  const [actionCard, setActionCard] = useState<ActionCardConfig | null>(null);

  // ── Load task list ──
  const loadTasks = useCallback(async () => {
    try {
      const list = await api.tasks.list();
      setTasks(list);
      setTasksLoading(false);
      return list;
    } catch {
      setTasks([]);
      setTasksLoading(false);
      return [];
    }
  }, []);

  // ── Load task detail ──
  const hasLoadedOnce = useRef(false);
  const loadTaskDetail = useCallback(async (slug: string) => {
    // Only show loading spinner on first load, not task switches
    if (!hasLoadedOnce.current) setDetailLoading(true);
    try {
      const [taskData, outputsData, outputData, deliverableFile] = await Promise.all([
        api.tasks.get(slug),
        api.tasks.listOutputs(slug, 10),
        api.tasks.getLatestOutput(slug),
        api.workspace.getFile(`/tasks/${slug}/DELIVERABLE.md`).catch(() => null),
      ]);
      setTaskDetail(taskData);
      setOutputs(outputsData?.outputs || []);
      setSelectedOutput(outputData || null);
      setDeliverableMd(deliverableFile?.content || null);
      hasLoadedOnce.current = true;
    } catch (err) {
      console.error('Failed to load task detail:', err);
      setTaskDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const refreshTaskDetail = useCallback(async () => {
    if (!selectedSlug) return;
    await loadTaskDetail(selectedSlug);
  }, [selectedSlug, loadTaskDetail]);

  // ── Initial load — parallel: task list + detail (if slug known) ──
  useEffect(() => {
    const init = async () => {
      // If we have a slug from URL, load list and detail in parallel
      if (slugFromUrl) {
        loadTasks();
        loadTaskDetail(slugFromUrl);
        loadScopedHistory(undefined, slugFromUrl);
      } else {
        // No slug — load list first, then auto-select
        const list = await loadTasks();
        if (list.length > 0) {
          const firstActive = list.find(t => t.status === 'active') || list[0];
          setSelectedSlug(firstActive.slug);
          setSelectedView(getDefaultView(firstActive));
          router.replace(`/tasks/${firstActive.slug}`, { scroll: false });
        }
      }
    };
    init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Load detail when user switches task (after initial load) ──
  useEffect(() => {
    if (selectedSlug && selectedSlug !== slugFromUrl) {
      loadTaskDetail(selectedSlug);
      loadScopedHistory(undefined, selectedSlug);
    }
  }, [selectedSlug, slugFromUrl, loadTaskDetail, loadScopedHistory]);

  // ── Polling ──
  useEffect(() => {
    const interval = setInterval(() => {
      loadTasks();
      if (selectedSlug) refreshTaskDetail();
    }, 30000);
    const onFocus = () => {
      if (document.visibilityState === 'visible') {
        loadTasks();
        if (selectedSlug) refreshTaskDetail();
      }
    };
    document.addEventListener('visibilitychange', onFocus);
    return () => { clearInterval(interval); document.removeEventListener('visibilitychange', onFocus); };
  }, [loadTasks, refreshTaskDetail, selectedSlug]);

  // ── Handlers ──
  const handleSelectTask = useCallback((slug: string, view?: TaskView) => {
    if (slug !== selectedSlug) {
      setSelectedSlug(slug);
      // Use provided view, or determine default from task class
      const task = tasks.find(t => t.slug === slug);
      setSelectedView(view || (task ? getDefaultView(task) : 'output'));
      // Don't clear state — keep old content visible until new data arrives
      router.replace(`/tasks/${slug}`, { scroll: false });
    } else if (view) {
      setSelectedView(view);
    }
  }, [selectedSlug, router, tasks]);

  const handleSelectOutput = useCallback((entry: TaskOutput) => {
    const folder = entry.folder || entry.date;
    if (!folder || !selectedSlug) { setSelectedOutput(entry); return; }
    api.tasks.getOutput(selectedSlug, folder)
      .then(full => setSelectedOutput(full || entry))
      .catch(() => setSelectedOutput(entry));
  }, [selectedSlug]);

  const handleRunNow = useCallback(async () => {
    if (!selectedSlug) return;
    setMutationPending(true);
    try {
      await api.tasks.run(selectedSlug);
      await refreshTaskDetail();
    } catch (err) {
      console.error('Run now failed:', err);
    } finally {
      setMutationPending(false);
    }
  }, [selectedSlug, refreshTaskDetail]);

  const handleToggleStatus = useCallback(async () => {
    if (!taskDetail) return;
    setMutationPending(true);
    try {
      await api.tasks.update(taskDetail.slug, { status: taskDetail.status === 'active' ? 'paused' : 'active' });
      await Promise.all([refreshTaskDetail(), loadTasks()]);
    } catch (err) {
      console.error('Status update failed:', err);
    } finally {
      setMutationPending(false);
    }
  }, [taskDetail, refreshTaskDetail, loadTasks]);

  const handleCreateTask = useCallback(() => {
    setChatOpen(true);
    sendMessage('I want to create a task. What do you suggest based on my context?');
  }, [sendMessage]);

  // ── Chat config ──
  const displayTitle = taskDetail?.title || selectedSlug || 'Tasks';
  const taskSurface = selectedSlug ? { type: 'task-detail' as const, taskSlug: selectedSlug } : undefined;

  const plusMenuActions: PlusMenuAction[] = selectedSlug ? [
    { id: 'run-task', label: 'Run now', icon: Play, verb: 'prompt', onSelect: () => setActionCard(RUN_TASK_CARD) },
    { id: 'adjust-task', label: 'Adjust task', icon: Target, verb: 'prompt', onSelect: () => setActionCard(ADJUST_TASK_CARD) },
    { id: 'feedback', label: 'Give feedback', icon: MessageCircle, verb: 'prompt', onSelect: () => setActionCard(FEEDBACK_TASK_CARD) },
    { id: 'web-research', label: 'Web research', icon: Globe, verb: 'prompt', onSelect: () => setActionCard(RESEARCH_TASK_CARD) },
  ] : [
    { id: 'create-task', label: 'Create a task', icon: ListChecks, verb: 'prompt', onSelect: () => sendMessage('I want to create a task. What do you suggest based on my context?') },
    { id: 'update-info', label: 'Update my info', icon: Settings2, verb: 'prompt', onSelect: () => setChatOpen(true) },
    { id: 'web-search', label: 'Web search', icon: Globe, verb: 'prompt', onSelect: () => setChatOpen(true) },
    { id: 'upload-file', label: 'Upload file', icon: Upload, verb: 'attach', onSelect: () => {} },
  ];

  const chatEmptyState = selectedSlug ? (
    <div className="py-2 text-center">
      <MessageCircle className="mx-auto mb-1.5 h-5 w-5 text-muted-foreground/15" />
      <p className="text-[11px] text-muted-foreground/40">Ask anything about this task</p>
    </div>
  ) : (
    <ContextSetup
      onSubmit={(msg) => sendMessage(msg)}
      showSkipOptions
      onSkipAction={(msg) => sendMessage(msg)}
    />
  );

  // ── Render ──
  return (
    <div className="flex h-full overflow-hidden">
      {/* Left: Task tree nav */}
      {panelOpen ? (
        <div className="w-[280px] shrink-0 border-r border-border flex flex-col bg-background">
          <div className="flex items-center justify-between px-3 py-2 border-b border-border shrink-0">
            <p className="text-sm font-medium text-foreground">Tasks</p>
            <button onClick={() => setPanelOpen(false)} className="p-1 text-muted-foreground/40 hover:text-muted-foreground rounded">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          {tasksLoading ? (
            <div className="flex items-center justify-center flex-1">
              <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <TaskTreeNav
              tasks={tasks}
              selectedSlug={selectedSlug}
              selectedView={selectedView}
              filter={filter}
              onFilterChange={setFilter}
              onSelectTask={handleSelectTask}
              onSelectView={setSelectedView}
              onCreateTask={handleCreateTask}
            />
          )}
        </div>
      ) : (
        <div className="w-10 shrink-0 border-r border-border flex flex-col items-center py-2 gap-2 bg-background">
          <button
            onClick={() => setPanelOpen(true)}
            className="p-2 rounded-md text-muted-foreground/50 hover:text-foreground hover:bg-muted transition-colors"
            title="Tasks"
          >
            <ListChecks className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Center: Dynamic content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {tasks.length === 0 && !tasksLoading ? (
          <div className="flex-1 flex items-center justify-center p-8">
            <div className="max-w-sm text-center">
              <ListChecks className="w-10 h-10 text-muted-foreground/15 mx-auto mb-3" />
              <h2 className="text-lg font-medium mb-1">No tasks yet</h2>
              <p className="text-sm text-muted-foreground mb-4">
                Set up your workspace first, then create tasks to automate your intelligence work.
              </p>
              <button
                onClick={() => router.push('/context')}
                className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
              >
                Set up workspace
              </button>
            </div>
          </div>
        ) : detailLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
          </div>
        ) : taskDetail ? (
          <TaskContentView
            task={taskDetail}
            view={selectedView}
            output={selectedOutput}
            outputs={outputs}
            deliverableMd={deliverableMd}
            onSelectOutput={handleSelectOutput}
            onSwitchView={setSelectedView}
            onRunNow={handleRunNow}
            onToggleStatus={handleToggleStatus}
            busy={mutationPending}
          />
        ) : selectedSlug ? (
          <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
            Task not found
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
            Select a task from the panel
          </div>
        )}
      </div>

      {/* Right: Chat panel or FAB */}
      {chatOpen && (
        <div className="w-[380px] shrink-0 border-l border-border flex flex-col bg-background overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2.5 border-b border-border bg-background z-10 shrink-0">
            <div className="flex items-center gap-2">
              <img src="/assets/logos/circleonly_yarnnn_1.svg" alt="" className="w-5 h-5" />
              <span className="text-xs font-medium">TP</span>
              {selectedSlug && (
                <span className="text-[10px] text-muted-foreground/50 truncate max-w-[160px]">
                  · viewing {displayTitle}
                </span>
              )}
            </div>
            <button onClick={() => setChatOpen(false)} className="p-1.5 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="flex-1 min-h-0">
            <ChatPanel
              surfaceOverride={taskSurface}
              plusMenuActions={plusMenuActions}
              placeholder={selectedSlug ? `Steer ${displayTitle}...` : 'Ask anything or type / ...'}
              emptyState={chatEmptyState}
              showCommandPicker={!selectedSlug}
              pendingActionConfig={actionCard}
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
