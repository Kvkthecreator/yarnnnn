'use client';

/**
 * Work Page — List/detail surface (ADR-167).
 *
 * SURFACE-ARCHITECTURE.md v9: /work is a single surface with two modes:
 *   - List mode (no `?task=` param): full-width WorkListSurface with filter
 *     chips, search, group-by, agent filter
 *   - Detail mode (`?task={slug}`): kind-aware WorkDetail dispatching the
 *     middle band on task.output_kind (ADR-166)
 *
 * The left sidebar from earlier versions is GONE — list mode IS the navigator.
 * The breadcrumb (commit b033513) drives navigation between modes. Auto-select
 * of the first task is GONE — landing on /work shows the list, not someone
 * else's task by accident.
 *
 * The `?agent={slug}` query param is preserved as a deep-link shortcut: it
 * pre-applies the agent filter in list mode. The breadcrumb's "Competitive
 * Intelligence's work" segment continues to target this URL.
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Loader2, Briefcase, MessageCircle } from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useBreadcrumb } from '@/contexts/BreadcrumbContext';
import { useAgentsAndTasks } from '@/hooks/useAgentsAndTasks';
import { api } from '@/lib/api/client';
import { WorkListSurface } from '@/components/work/WorkListSurface';
import { WorkDetail } from '@/components/work/WorkDetail';
import { ThreePanelLayout } from '@/components/shell/ThreePanelLayout';
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

  const [mutationPending, setMutationPending] = useState(false);

  // Breadcrumb (matches commit b033513 segment shape)
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
      {selectedTask ? (
        <WorkDetail
          task={selectedTask}
          agents={agents}
          onRun={handleRunTask}
          onPause={handlePauseTask}
          onOpenChat={(prompt) => sendMessage(prompt || '')}
          busy={mutationPending}
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
