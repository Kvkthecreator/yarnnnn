'use client';

/**
 * Work Page — List/detail surface (ADR-167 v5).
 *
 * SURFACE-ARCHITECTURE.md v9.4: /work is a single surface with two modes:
 *   - List mode (no `?task=` param): full-width WorkListSurface with filter
 *     chips, search, group-by, agent filter
 *   - Detail mode (`?task={slug}`): kind-aware WorkDetail dispatching the
 *     middle band on task.output_kind (ADR-166)
 *
 * The breadcrumb is rendered as chrome via <PageHeader /> — pure navigation,
 * no title, no metadata, no actions. The task's visual identity (title +
 * metadata + actions) lives inside WorkDetail via <SurfaceIdentityHeader />
 * where it belongs alongside the task content. v5 undoes the v2-v4 pattern
 * of plumbing task-shaped data through the chrome layer.
 *
 * The `?agent={slug}` query param is preserved as a deep-link shortcut.
 */

import { useState, useEffect, useRef, useMemo, useCallback, type ReactNode } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { AlertCircle, ArrowLeft, Briefcase, Loader2, MessageCircle, RefreshCw } from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useBreadcrumb } from '@/contexts/BreadcrumbContext';
import { useAgentsAndRecurrences } from '@/hooks/useAgentsAndRecurrences';
import { useRecurrenceDetail } from '@/hooks/useRecurrenceDetail';
import { APIError, api } from '@/lib/api/client';
import { WorkListSurface, type WorkTab } from '@/components/work/WorkListSurface';
import { WorkDetail } from '@/components/work/WorkDetail';
import { CockpitRenderer } from '@/components/library/CockpitRenderer';
import { ThreePanelLayout } from '@/components/shell/ThreePanelLayout';
import { PageHeader } from '@/components/shell/PageHeader';
// RecurrenceSetupModal removed — creation via Chat
import { getAgentSlug } from '@/lib/agent-identity';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';
import type { DeskSurface } from '@/types/desk';

type ActionNotice = { kind: 'info' | 'success' | 'error'; text: string } | null;

function getActionErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof APIError) {
    const detail = (error.data as { detail?: unknown } | null)?.detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }
  return fallback;
}

function SurfaceState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-1 items-center justify-center px-6 py-12">
      <div className="max-w-md text-center">
        <AlertCircle className="mx-auto mb-3 h-8 w-8 text-muted-foreground/20" />
        <h2 className="text-base font-medium text-foreground">{title}</h2>
        <p className="mt-2 text-sm text-muted-foreground">{description}</p>
        {action && <div className="mt-4 flex items-center justify-center gap-2">{action}</div>}
      </div>
    </div>
  );
}

export default function WorkPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { sendMessage } = useTP();
  const { setBreadcrumb, clearBreadcrumb } = useBreadcrumb();
  // ADR-219 Commit 4: opt into narrative fetch — /work is the surface
  // that renders recent-activity headlines from session_messages.
  const { agents, tasks, narrativeByTask, loading, error, reload } = useAgentsAndRecurrences({ includeNarrative: true });

  const agentFilter = searchParams.get('agent');
  const taskSlugFromUrl = searchParams.get('task');
  // ?tab=dashboard|schedule — URL-driven so TP can deep-link to a specific tab.
  // Default is 'schedule'; 'dashboard' is the cockpit view.
  const tabParam = searchParams.get('tab');
  // Local state is the source of truth for the active tab — router.replace
  // updates the URL as a side effect but useSearchParams can lag in the
  // App Router. Initial value is derived from the URL param.
  const [activeTab, setActiveTab] = useState<WorkTab>(
    tabParam === 'dashboard' ? 'dashboard' : 'schedule'
  );
  const {
    task: selectedRecurrenceDetail,
    loading: taskDetailLoading,
    error: taskDetailError,
    notFound: taskNotFound,
    reload: reloadRecurrenceDetail,
  } = useRecurrenceDetail(taskSlugFromUrl);

  const selectedTaskHint = useMemo(
    () => (taskSlugFromUrl ? tasks.find(t => t.slug === taskSlugFromUrl) ?? null : null),
    [taskSlugFromUrl, tasks],
  );
  const selectedTask = selectedRecurrenceDetail ?? selectedTaskHint;

  const [mutationPending, setMutationPending] = useState(false);
  const [pendingAction, setPendingAction] = useState<'run' | 'pause' | null>(null);
  const [detailRefreshKey, setDetailRefreshKey] = useState(0);
  const [actionNotice, setActionNotice] = useState<ActionNotice>(null);
  const [chatDraftSeed, setChatDraftSeed] = useState<{ id: string; text: string } | null>(null);
  const [chatOpenSignal, setChatOpenSignal] = useState(0);

  // Sync from URL only on initial mount and genuine external navigation
  // (back/forward, TP deep-link). Do NOT re-sync on every tabParam change —
  // that races with the optimistic setActiveTab in handleTabChange.
  // The initial useState value handles the URL-on-load case; this effect
  // handles the case where the URL changes without a click (e.g. popstate).
  const lastSyncedTabParam = useRef(tabParam);
  useEffect(() => {
    if (tabParam === lastSyncedTabParam.current) return; // no external change
    lastSyncedTabParam.current = tabParam;
    const derived: WorkTab = tabParam === 'dashboard' ? 'dashboard' : 'schedule';
    setActiveTab(derived);
  }, [tabParam]);

  useEffect(() => {
    if (!actionNotice) return;
    const timeout = window.setTimeout(() => setActionNotice(null), 5000);
    return () => window.clearTimeout(timeout);
  }, [actionNotice]);

  useEffect(() => {
    setActionNotice(null);
  }, [taskSlugFromUrl]);

  // Breadcrumb (ADR-180: task-first, no agent middle segment)
  //
  // Work surface: Work › Task Title — tasks are first-class, agents are participants.
  // Exception: when ?agent= is present the user navigated here from the Agents surface
  // (via "Manage task" link) — breadcrumb traces actual navigation: Agents › Agent › Task.
  // Agent-filter-only list mode (no task selected) shows no breadcrumb — the filter chip
  // in WorkListSurface already communicates the active filter.
  useEffect(() => {
    if (taskSlugFromUrl) {
      const breadcrumbTask = selectedTask;

      if (agentFilter) {
        // Came from Agents surface — trace navigation history, not ownership
        const agent = agents.find(a => getAgentSlug(a) === agentFilter);
        const agentCrumbLabel = agent?.title ?? agentFilter;
        setBreadcrumb([
          { label: 'Agents', href: '/agents', kind: 'surface' },
          {
            label: agentCrumbLabel,
            href: `/agents?agent=${encodeURIComponent(agentFilter)}`,
            kind: 'agent' as const,
          },
          {
            label: taskNotFound
              ? 'Task not found'
              : breadcrumbTask?.title ?? taskSlugFromUrl,
            href: `/work?task=${encodeURIComponent(taskSlugFromUrl)}&agent=${encodeURIComponent(agentFilter)}`,
            kind: 'task',
          },
        ]);
      } else {
        // Standard Work navigation — task is the subject, no agent container
        setBreadcrumb([
          { label: 'Work', href: '/work', kind: 'surface' },
          {
            label: taskNotFound
              ? 'Task not found'
              : breadcrumbTask?.title ?? taskSlugFromUrl,
            href: `/work?task=${encodeURIComponent(taskSlugFromUrl)}`,
            kind: 'task',
          },
        ]);
      }
    } else {
      clearBreadcrumb();
    }
    return () => clearBreadcrumb();
  }, [taskSlugFromUrl, selectedTask?.title, taskNotFound, agentFilter, agents, setBreadcrumb, clearBreadcrumb]);

  // Actions
  const handleRunTask = useCallback(async (slug: string) => {
    setMutationPending(true);
    setPendingAction('run');
    setActionNotice({ kind: 'info', text: 'Running task now. This can take up to a minute.' });
    try {
      await api.recurrences.run(slug);
      setDetailRefreshKey((current) => current + 1);
      await Promise.all([reload(), reloadRecurrenceDetail()]);
      setActionNotice({ kind: 'success', text: 'Task run completed. Latest task data refreshed.' });
    } catch (err) {
      console.error('[Work] Failed to trigger task:', err);
      setActionNotice({
        kind: 'error',
        text: getActionErrorMessage(err, 'Failed to run task.'),
      });
    } finally {
      setMutationPending(false);
      setPendingAction(null);
    }
  }, [reload, reloadRecurrenceDetail]);

  const handlePauseTask = useCallback(async (slug: string) => {
    setMutationPending(true);
    setPendingAction('pause');
    setActionNotice(null);
    try {
      const task = (selectedRecurrenceDetail?.slug === slug ? selectedRecurrenceDetail : null) ?? tasks.find(t => t.slug === slug);
      const newStatus = task?.status === 'active' ? 'paused' : 'active';
      await api.recurrences.update(slug, { status: newStatus });
      await Promise.all([reload(), reloadRecurrenceDetail()]);
      setActionNotice({
        kind: 'success',
        text: newStatus === 'paused' ? 'Task paused.' : 'Task resumed.',
      });
    } catch (err) {
      console.error('[Work] Failed to update task:', err);
      setActionNotice({
        kind: 'error',
        text: getActionErrorMessage(err, 'Failed to update task.'),
      });
    } finally {
      setMutationPending(false);
      setPendingAction(null);
    }
  }, [tasks, selectedRecurrenceDetail, reload, reloadRecurrenceDetail]);

  const handleOpenChatDraft = useCallback((prompt?: string) => {
    if (!prompt) return;
    setChatDraftSeed({ id: crypto.randomUUID(), text: prompt });
    setChatOpenSignal((current) => current + 1);
  }, []);

  // Click row in list mode → URL transition to detail mode
  const handleSelect = useCallback((slug: string) => {
    const sp = new URLSearchParams(searchParams.toString());
    sp.set('task', slug);
    router.push(`/work?${sp.toString()}`, { scroll: false });
  }, [router, searchParams]);

  // Clear agent filter chip in list mode
  const handleClearAgentFilter = useCallback(() => {
    const sp = new URLSearchParams(searchParams.toString());
    sp.delete('agent');
    const qs = sp.toString();
    router.replace(qs ? `/work?${qs}` : '/work', { scroll: false });
  }, [router, searchParams]);

  const handleBackToList = useCallback(() => {
    const sp = new URLSearchParams(searchParams.toString());
    sp.delete('task');
    const qs = sp.toString();
    router.replace(qs ? `/work?${qs}` : '/work', { scroll: false });
  }, [router, searchParams]);

  const handleTabChange = useCallback((tab: WorkTab) => {
    setActiveTab(tab);
    // Always write tab to URL — no silent defaults — so the URL always
    // reflects the active tab and TP can deep-link to either.
    lastSyncedTabParam.current = tab;
    const sp = new URLSearchParams(searchParams.toString());
    sp.set('tab', tab);
    router.replace(`/work?${sp.toString()}`, { scroll: false });
  }, [router, searchParams]);

  const plusMenuActions: PlusMenuAction[] = useMemo(() => {
    if (selectedTask) return [];
    return [
      {
        id: 'create-task',
        label: 'Start new work',
        icon: Briefcase,
        verb: 'show' as const,
        onSelect: () => sendMessage('I want to set up some recurring work — ', chatSurfaceOverride ? { surface: chatSurfaceOverride } : undefined),
      },
    ];
  }, [selectedTask]);

  const chatSurfaceOverride = useMemo<DeskSurface | undefined>(() => {
    if (!selectedTask) return undefined;
    return { type: 'task-detail', taskSlug: selectedTask.slug };
  }, [selectedTask]);

  const chatEmptyState = (
    <div className="py-2 text-center">
      <MessageCircle className="mx-auto mb-1.5 h-5 w-5 text-muted-foreground/15" />
      <p className="text-[11px] text-muted-foreground/40">
        {selectedTask ? `Ask anything about "${selectedTask.title}"` : 'Ask anything about your work'}
      </p>
    </div>
  );

  if (loading && !tasks.length && !agents.length && !taskSlugFromUrl) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!taskSlugFromUrl && error && !tasks.length && !agents.length) {
    return (
      <div className="flex h-full">
        <div className="flex flex-1 flex-col bg-background">
          <PageHeader defaultLabel="Work" />
          <SurfaceState
            title="Failed to load work"
            description="The work index could not be loaded right now. Retry the workspace fetch."
            action={(
              <button
                onClick={() => void reload()}
                className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Retry
              </button>
            )}
          />
        </div>
      </div>
    );
  }

  return (
    <>
    <ThreePanelLayout
      chat={{
        surfaceOverride: chatSurfaceOverride,
        draftSeed: chatDraftSeed,
        plusMenuActions,
        placeholder: selectedTask ? `Ask about "${selectedTask.title}"...` : 'Ask anything or type / ...',
        emptyState: chatEmptyState,
        showCommandPicker: !selectedTask,
        contextLabel: selectedTask ? `viewing ${selectedTask.title}` : undefined,
        defaultOpen: true,
        openSignal: chatOpenSignal,
      }}
    >
      <PageHeader defaultLabel="Work" />
      {taskSlugFromUrl ? (
        taskDetailLoading && !selectedRecurrenceDetail ? (
          <div className="flex flex-1 items-center justify-center">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : taskNotFound ? (
          <SurfaceState
            title="Recurrence not found"
            description="That work item no longer exists or the link is stale."
            action={(
              <button
                onClick={handleBackToList}
                className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                Back to work
              </button>
            )}
          />
        ) : taskDetailError && !selectedRecurrenceDetail ? (
          <SurfaceState
            title="Failed to load recurrence"
            description={taskDetailError}
            action={(
              <>
                <button
                  onClick={() => void reloadRecurrenceDetail()}
                  className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Retry
                </button>
                <button
                  onClick={handleBackToList}
                  className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
                >
                  <ArrowLeft className="h-3.5 w-3.5" />
                  Back to work
                </button>
              </>
            )}
          />
        ) : selectedRecurrenceDetail ? (
        <WorkDetail
          key={`${selectedRecurrenceDetail.slug}:${detailRefreshKey}`}
          task={selectedRecurrenceDetail}
          agents={agents}
          refreshKey={detailRefreshKey}
          mutationPending={mutationPending}
          pendingAction={pendingAction}
          actionNotice={actionNotice}
          onRunTask={handleRunTask}
          onPauseTask={handlePauseTask}
          onOpenChat={handleOpenChatDraft}
          onSourcesUpdated={() => {
            reloadRecurrenceDetail();
            setDetailRefreshKey(k => k + 1);
          }}
        />
        ) : null
      ) : (
        <div className="flex flex-1 flex-col overflow-y-auto">
          <WorkListSurface
            tasks={tasks}
            agents={agents}
            narrativeByTask={narrativeByTask}
            agentFilter={agentFilter}
            dataError={error}
            activeTab={activeTab}
            onTabChange={handleTabChange}
            cockpitSlot={
              // Hidden when an agent filter is active (ADR-206 deliberate focus shift).
              !agentFilter
                ? <CockpitRenderer onOpenChatDraft={handleOpenChatDraft} />
                : undefined
            }
            onClearAgentFilter={handleClearAgentFilter}
            onSelect={handleSelect}
          />
        </div>
      )}
    </ThreePanelLayout>

    {/* RecurrenceSetupModal removed — all creation via Chat */}
    </>
  );
}
