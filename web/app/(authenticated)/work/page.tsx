'use client';

/**
 * Work Page — List/detail surface (ADR-167 + v2 amendment).
 *
 * SURFACE-ARCHITECTURE.md v9.1: /work is a single surface with two modes:
 *   - List mode (no `?task=` param): full-width WorkListSurface with filter
 *     chips, search, group-by, agent filter
 *   - Detail mode (`?task={slug}`): kind-aware WorkDetail dispatching the
 *     middle band on task.output_kind (ADR-166)
 *
 * The breadcrumb is rendered in-page via <PageHeader /> as the first row of
 * the center surface — no separate floating bar (ADR-167 v2). In detail mode,
 * the page composes PageHeader + WorkDetail as siblings inside ThreePanelLayout
 * children: PageHeader carries the breadcrumb path, the metadata strip
 * (subtitle), and the inline action buttons. WorkDetail renders only the
 * objective + kind-aware middle + assigned-agent footer — its old internal
 * header band and ActionsRow are dissolved into PageHeader.
 *
 * The `?agent={slug}` query param is preserved as a deep-link shortcut.
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import Link from 'next/link';
import { useSearchParams, useRouter } from 'next/navigation';
import { Loader2, Briefcase, MessageCircle, Play, Pause, MessageSquare } from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useBreadcrumb } from '@/contexts/BreadcrumbContext';
import { useAgentsAndTasks } from '@/hooks/useAgentsAndTasks';
import { api } from '@/lib/api/client';
import { WorkListSurface } from '@/components/work/WorkListSurface';
import { WorkDetail } from '@/components/work/WorkDetail';
import { WorkModeBadge } from '@/components/work/WorkModeBadge';
import { ThreePanelLayout } from '@/components/shell/ThreePanelLayout';
import { PageHeader } from '@/components/shell/PageHeader';
import { formatRelativeTime } from '@/lib/formatting';
import { AGENTS_ROUTE } from '@/lib/routes';
import { cn } from '@/lib/utils';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';

export default function WorkPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { sendMessage } = useTP();
  const { setBreadcrumb, clearBreadcrumb } = useBreadcrumb();
  const { agents, tasks, loading, reload } = useAgentsAndTasks();

  const agentFilter = searchParams.get('agent');
  const taskSlugFromUrl = searchParams.get('task');

  // Detail mode is determined by URL — no auto-selection (ADR-167)
  const selectedTask = useMemo(
    () => (taskSlugFromUrl ? tasks.find(t => t.slug === taskSlugFromUrl) ?? null : null),
    [taskSlugFromUrl, tasks],
  );

  const assignedAgent = useMemo(() => {
    if (!selectedTask) return null;
    const slug = selectedTask.agent_slugs?.[0];
    if (!slug) return null;
    return agents.find(a => a.slug === slug) ?? null;
  }, [selectedTask, agents]);

  const [mutationPending, setMutationPending] = useState(false);

  // Breadcrumb (segment shape from b033513; PageHeader renders inline now)
  useEffect(() => {
    if (selectedTask) {
      const agentSlug = agentFilter || selectedTask.agent_slugs?.[0];
      const agent = agentSlug ? agents.find(a => a.slug === agentSlug) : null;
      setBreadcrumb([
        { label: 'Work', href: '/work', kind: 'surface' },
        ...(agentSlug ? [{
          label: `${agent?.title ?? agentSlug}'s work`,
          href: `/work?agent=${encodeURIComponent(agentSlug)}`,
          kind: 'agent' as const,
        }] : []),
        {
          label: selectedTask.title,
          href: `/work?task=${encodeURIComponent(selectedTask.slug)}`,
          kind: 'task',
        },
      ]);
    } else if (agentFilter) {
      const agent = agents.find(a => a.slug === agentFilter);
      setBreadcrumb([
        { label: 'Work', href: '/work', kind: 'surface' },
        {
          label: `${agent?.title ?? agentFilter}'s work`,
          href: `/work?agent=${encodeURIComponent(agentFilter)}`,
          kind: 'agent',
        },
      ]);
    } else {
      clearBreadcrumb();
    }
    return () => clearBreadcrumb();
  }, [selectedTask?.slug, selectedTask?.title, selectedTask?.agent_slugs, agentFilter, agents, setBreadcrumb, clearBreadcrumb]);

  // Actions
  const handleRunTask = useCallback(async (slug: string) => {
    setMutationPending(true);
    try {
      await api.tasks.run(slug);
      await reload();
    } catch (err) {
      console.error('[Work] Failed to trigger task:', err);
    } finally {
      setMutationPending(false);
    }
  }, [reload]);

  const handlePauseTask = useCallback(async (slug: string) => {
    setMutationPending(true);
    try {
      const task = tasks.find(t => t.slug === slug);
      const newStatus = task?.status === 'active' ? 'paused' : 'active';
      await api.tasks.update(slug, { status: newStatus });
      await reload();
    } catch (err) {
      console.error('[Work] Failed to update task:', err);
    } finally {
      setMutationPending(false);
    }
  }, [tasks, reload]);

  // Click row in list mode → URL transition to detail mode
  const handleSelect = useCallback((slug: string) => {
    const sp = new URLSearchParams(searchParams.toString());
    sp.set('task', slug);
    router.replace(`/work?${sp.toString()}`, { scroll: false });
  }, [router, searchParams]);

  // Clear agent filter chip in list mode
  const handleClearAgentFilter = useCallback(() => {
    const sp = new URLSearchParams(searchParams.toString());
    sp.delete('agent');
    const qs = sp.toString();
    router.replace(qs ? `/work?${qs}` : '/work', { scroll: false });
  }, [router, searchParams]);

  const plusMenuActions: PlusMenuAction[] = useMemo(() => {
    if (selectedTask) {
      return [
        {
          id: 'run-now',
          label: 'Run now',
          icon: Briefcase,
          verb: 'prompt' as const,
          onSelect: () => { handleRunTask(selectedTask.slug); },
        },
        {
          id: 'edit-via-tp',
          label: 'Edit via chat',
          icon: MessageCircle,
          verb: 'prompt' as const,
          onSelect: () => { sendMessage(`I want to update the task "${selectedTask.title}"`); },
        },
      ];
    }
    return [
      {
        id: 'create-task',
        label: 'Create new work',
        icon: Briefcase,
        verb: 'prompt' as const,
        onSelect: () => { sendMessage('I want to set up new work. What do you suggest based on my context?'); },
      },
    ];
  }, [selectedTask, handleRunTask, sendMessage]);

  const chatEmptyState = (
    <div className="py-2 text-center">
      <MessageCircle className="mx-auto mb-1.5 h-5 w-5 text-muted-foreground/15" />
      <p className="text-[11px] text-muted-foreground/40">
        {selectedTask ? `Ask anything about "${selectedTask.title}"` : 'Ask anything about your work'}
      </p>
    </div>
  );

  // ─── Detail-mode subtitle: compact metadata strip (ADR-167 v2) ───
  // Replaces the old WorkHeader band inside WorkDetail. Lives in PageHeader so
  // the breadcrumb + status row form one cohesive header zone.
  const detailSubtitle = selectedTask ? (
    <div className="flex items-center gap-1.5 flex-wrap">
      <WorkModeBadge mode={selectedTask.mode} />
      <span className="text-muted-foreground/30">·</span>
      <span className="capitalize">{selectedTask.status}</span>
      {assignedAgent && (
        <>
          <span className="text-muted-foreground/30">·</span>
          <Link
            href={`${AGENTS_ROUTE}?agent=${assignedAgent.slug}`}
            className="hover:text-foreground hover:underline"
          >
            {assignedAgent.title}
          </Link>
        </>
      )}
      {selectedTask.schedule && (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span className="capitalize">{selectedTask.schedule}</span>
        </>
      )}
      {selectedTask.next_run_at && (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span>Next: {formatRelativeTime(selectedTask.next_run_at)}</span>
        </>
      )}
      {!selectedTask.next_run_at && selectedTask.last_run_at && (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span>Last: {formatRelativeTime(selectedTask.last_run_at)}</span>
        </>
      )}
      {!selectedTask.next_run_at && !selectedTask.last_run_at && (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span>Never run</span>
        </>
      )}
    </div>
  ) : undefined;

  // ─── Detail-mode actions (ADR-167 v2) ───
  // Pulled up from WorkDetail's old ActionsRow. One inline cluster in PageHeader.
  const detailActions = selectedTask ? (
    <>
      <button
        onClick={() => handleRunTask(selectedTask.slug)}
        disabled={mutationPending || selectedTask.status !== 'active'}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded bg-primary/10 text-primary hover:bg-primary/20 disabled:opacity-50"
      >
        <Play className="w-3 h-3" /> Run now
      </button>
      <button
        onClick={() => handlePauseTask(selectedTask.slug)}
        disabled={mutationPending}
        className={cn(
          'inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded border border-border',
          'text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-50',
        )}
      >
        {selectedTask.status === 'active' ? (
          <><Pause className="w-3 h-3" /> Pause</>
        ) : (
          <><Play className="w-3 h-3" /> Resume</>
        )}
      </button>
      <button
        onClick={() => sendMessage(`I want to update the task "${selectedTask.title}"`)}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded border border-border text-muted-foreground hover:text-foreground hover:bg-muted"
      >
        <MessageSquare className="w-3 h-3" /> Edit via chat
      </button>
    </>
  ) : undefined;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <ThreePanelLayout
      chat={{
        plusMenuActions,
        placeholder: selectedTask ? `Ask about "${selectedTask.title}"...` : 'Ask anything or type / ...',
        emptyState: chatEmptyState,
        showCommandPicker: !selectedTask,
        contextLabel: selectedTask ? `viewing ${selectedTask.title}` : undefined,
      }}
    >
      <PageHeader
        defaultLabel="Work"
        subtitle={detailSubtitle}
        actions={detailActions}
      />
      {selectedTask ? (
        <WorkDetail
          task={selectedTask}
          agents={agents}
          onOpenChat={(prompt) => sendMessage(prompt || '')}
        />
      ) : (
        <WorkListSurface
          tasks={tasks}
          agents={agents}
          agentFilter={agentFilter}
          onClearAgentFilter={handleClearAgentFilter}
          onSelect={handleSelect}
        />
      )}
    </ThreePanelLayout>
  );
}
