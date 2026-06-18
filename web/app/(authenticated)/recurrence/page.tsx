'use client';

/**
 * Recurrence Page — atomic Recurrence surface (ADR-297 D1 + D19).
 *
 * D19 (2026-05-22) refactor: window-shaped per the OS metaphor. The
 * page DELETES its prior outer chrome (ThreePanelLayout + PageHeader +
 * setBreadcrumb). The WindowFrame is now the chrome.
 *
 * Renamed /work → /cadence in the ADR-297 atomic-shell migration, then
 * /cadence → /recurrence (2026-06-03) — the substrate (_recurrences.yaml)
 * + hooks (useRecurrenceDetail) already spoke "recurrence"; only the
 * surface label lagged. Tab framing fully dissolved — cockpit rendering
 * moved to the dedicated /home atomic surface (ADR-312). This surface is
 * a single-mode recurrence list answering "what runs, and when?"
 *
 * Two lenses on one machinery concern (ADR-340 D8 — Activity folded in):
 *   - Schedule lens (default): the declaration view — "what's scheduled, what
 *     fires when." List mode (no `?task=`): full-width RecurrenceList. Detail
 *     mode (`?task={slug}`): kind-aware recurrence detail via WorkDetail.
 *   - Runs lens (`?pane=activity`): the execution view — "did it run, what did
 *     it cost." Renders the shared ActivityLog (one Activity body; the former
 *     standalone /activity page is now an ADR-308 redirect stub). `?slug=` is
 *     the Runs lens's intra-surface filter (deep-link from a Schedule row's
 *     "View runs →" pre-filters to one recurrence).
 *
 * Declaration-led: the Schedule lens is the default — authored substrate
 * (_recurrences.yaml) before the execution ledger, and it survives the empty
 * workspace (declarations exist before runs). The header toggle switches lenses.
 *
 * The `?agent={slug}` query param is preserved as a deep-link shortcut
 * (window-internal state per D19.4 — like Figma's ?node-id=X). Stale
 * `?tab=…` query params are silently ignored.
 */

import { useState, useEffect, useMemo, useCallback, type ReactNode } from 'react';
import { useSearchParams } from 'next/navigation';
import { AlertCircle, ArrowLeft, Loader2, RefreshCw } from 'lucide-react';
import { useNarrative } from '@/contexts/NarrativeContext';
import { useAgentsAndRecurrences } from '@/hooks/useAgentsAndRecurrences';
import { useRecurrenceDetail } from '@/hooks/useRecurrenceDetail';
import { APIError, api } from '@/lib/api/client';
import { RecurrenceList } from '@/components/work/RecurrenceList';
import { WorkDetail } from '@/components/work/WorkDetail';
import { ActivityLog } from '@/components/activity/ActivityLog';
import { cn } from '@/lib/utils';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';

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

export default function RecurrencePage() {
  const searchParams = useSearchParams();
  // ADR-297 D19.6: ?task= / ?agent= are intra-surface deep-link state —
  // update them without a pathname flip (no router.push off /desktop).
  const { setSurfaceParams } = useSurfacePreferences();
  const { sendMessage } = useNarrative();
  // ADR-219 Commit 4: opt into narrative fetch — Cadence is the surface
  // that renders recent-activity headlines from session_messages.
  const { agents, tasks, narrativeByTask, loading, error, reload } = useAgentsAndRecurrences({ includeNarrative: true });

  const agentFilter = searchParams.get('agent');
  const taskSlugFromUrl = searchParams.get('task');
  // ADR-340 D8: ?pane=activity selects the Runs (execution) lens; default
  // (absent) is the Schedule (declaration) lens. ?slug= is the Runs lens's
  // intra-surface filter (deep-link from a Schedule row pre-filters to one
  // recurrence). Both are window-internal state per D19.6 — toggled via
  // setSurfaceParams without a pathname flip.
  const activeLens = searchParams.get('pane') === 'activity' ? 'runs' : 'schedule';
  const runsSlugFilter = searchParams.get('slug');
  const showRuns = activeLens === 'runs';
  const setLens = useCallback((lens: 'schedule' | 'runs') => {
    setSurfaceParams({ pane: lens === 'runs' ? 'activity' : null });
  }, [setSurfaceParams]);
  const clearRunsSlugFilter = useCallback(() => {
    setSurfaceParams({ slug: null });
  }, [setSurfaceParams]);
  // ADR-297: tab framing dissolved on Cadence. Cockpit lives at /cockpit;
  // this surface is a single-mode recurrence list. Stale ?tab=… query
  // params are silently ignored.
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

  useEffect(() => {
    if (!actionNotice) return;
    const timeout = window.setTimeout(() => setActionNotice(null), 5000);
    return () => window.clearTimeout(timeout);
  }, [actionNotice]);

  useEffect(() => {
    setActionNotice(null);
  }, [taskSlugFromUrl]);

  // D19 (2026-05-22): workspace-wide setBreadcrumb removed. The
  // WindowFrame title bar IS the breadcrumb; intra-surface selection
  // (which task is selected) is window-internal state rendered inside
  // the surface body via WorkDetail's own header chrome.

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

  // D19: WorkDetail accepts onOpenChat as an optional callback. The
  // universal ChatDrawer FAB provides the primary chat affordance now;
  // this hook routes a prompt through sendMessage so the drawer summons
  // with a pre-seeded message when the operator clicks an in-surface
  // "ask about this" chip.
  const handleOpenChatDraft = useCallback((prompt?: string) => {
    if (!prompt) return;
    sendMessage(prompt);
  }, [sendMessage]);

  // Click row in list mode → detail mode (intra-surface deep-link, no
  // pathname flip). setSurfaceParams merges onto the current query.
  const handleSelect = useCallback((slug: string) => {
    setSurfaceParams({ task: slug });
  }, [setSurfaceParams]);

  // Clear agent filter chip in list mode (null deletes the key).
  const handleClearAgentFilter = useCallback(() => {
    setSurfaceParams({ agent: null });
  }, [setSurfaceParams]);

  const handleBackToList = useCallback(() => {
    setSurfaceParams({ task: null });
  }, [setSurfaceParams]);

  // D19 (2026-05-22): the prior "+menu" PlusMenuAction array and the
  // chat-panel empty-state block were ThreePanelLayout-side affordances.
  // The universal ChatDrawer FAB now provides the singular summon
  // path; operators ask "set up new work" via the drawer instead of
  // through a per-surface action button.

  // ADR-340 D8: the lens toggle (Schedule ↔ Runs) is a persistent header,
  // rendered above every body state so the operator can always cross between
  // the declaration and execution views. Hidden only in task-detail mode,
  // where the WorkDetail surface owns its own header chrome + back affordance.
  const lensToggle = !taskSlugFromUrl ? (
    <div className="flex items-center gap-1 px-4 sm:px-6 pt-3 shrink-0">
      <button
        onClick={() => setLens('schedule')}
        className={cn(
          'px-3 py-1.5 text-xs rounded-md border transition-colors',
          !showRuns
            ? 'border-foreground/30 bg-foreground/5 text-foreground'
            : 'border-border text-muted-foreground hover:bg-muted/50',
        )}
      >
        Schedule
      </button>
      <button
        onClick={() => setLens('runs')}
        className={cn(
          'px-3 py-1.5 text-xs rounded-md border transition-colors',
          showRuns
            ? 'border-foreground/30 bg-foreground/5 text-foreground'
            : 'border-border text-muted-foreground hover:bg-muted/50',
        )}
      >
        Runs
      </button>
    </div>
  ) : null;

  // ADR-340 D8 Runs lens: the shared ActivityLog (execution-events body).
  // Independent of the schedule-data loading/error guards below — it owns
  // its own loading + error state. Renders for both list-mode and any
  // ?pane=activity arrival (deep-link from /activity redirect stub).
  if (showRuns && !taskSlugFromUrl) {
    return (
      <div className="flex h-full flex-1 min-w-0 min-h-0 flex-col bg-background">
        {lensToggle}
        <div className="flex-1 min-h-0">
          <ActivityLog slugFilter={runsSlugFilter} onClearSlugFilter={clearRunsSlugFilter} />
        </div>
      </div>
    );
  }

  if (loading && !tasks.length && !agents.length && !taskSlugFromUrl) {
    return (
      <div className="flex flex-col h-full">
        {lensToggle}
        <div className="flex flex-1 items-center justify-center">
          <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  if (!taskSlugFromUrl && error && !tasks.length && !agents.length) {
    return (
      <div className="flex h-full flex-1 flex-col bg-background">
        {lensToggle}
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
    );
  }

  return (
    <div className="flex h-full flex-1 min-w-0 min-h-0 flex-col overflow-y-auto bg-background">
      {lensToggle}
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
        <RecurrenceList
          tasks={tasks}
          agents={agents}
          narrativeByTask={narrativeByTask}
          agentFilter={agentFilter}
          dataError={error}
          onClearAgentFilter={handleClearAgentFilter}
          onSelect={handleSelect}
        />
      )}
    </div>
  );
}
