'use client';

/**
 * Work Page — Task list (left) + task detail (center) + TP chat (right).
 *
 * ADR-163 Surface Restructure: First-class top-level destination. Answers
 * "What is my workforce doing?" The task list is sorted by next_run_at
 * (upcoming soonest first). The detail panel shows the selected task's
 * full state including latest output, actions, and a link back to the
 * assigned agent.
 *
 * The `?agent=<slug>` query param filters the task list to that agent's
 * tasks — used when the user clicks "See this agent's work" from /agents.
 * The `?task=<slug>` query param deep-links to a specific task.
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Loader2, Briefcase, MessageCircle } from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useBreadcrumb } from '@/contexts/BreadcrumbContext';
import { useAgentsAndTasks } from '@/hooks/useAgentsAndTasks';
import { api } from '@/lib/api/client';
import { WorkList } from '@/components/work/WorkList';
import { WorkDetail } from '@/components/work/WorkDetail';
import { ThreePanelLayout } from '@/components/shell/ThreePanelLayout';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';

function EmptyState() {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center">
        <Briefcase className="w-8 h-8 text-muted-foreground/15 mx-auto mb-2" />
        <p className="text-sm text-muted-foreground/50">Select work</p>
      </div>
    </div>
  );
}

export default function WorkPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { sendMessage } = useTP();
  const { setBreadcrumb, clearBreadcrumb } = useBreadcrumb();
  const { agents, tasks, loading, reload } = useAgentsAndTasks();

  const agentFilter = searchParams.get('agent');
  const taskSlugFromUrl = searchParams.get('task');

  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [mutationPending, setMutationPending] = useState(false);

  // Filter tasks by agent if filter is set
  const filteredTasks = useMemo(() => {
    if (!agentFilter) return tasks;
    return tasks.filter(t => t.agent_slugs?.includes(agentFilter));
  }, [tasks, agentFilter]);

  // Auto-select from URL on first load
  useEffect(() => {
    if (taskSlugFromUrl && tasks.length > 0 && !selectedSlug) {
      const match = tasks.find(t => t.slug === taskSlugFromUrl);
      if (match) setSelectedSlug(match.slug);
    }
  }, [taskSlugFromUrl, tasks, selectedSlug]);

  // Auto-select first task if none selected and list has items
  useEffect(() => {
    if (!selectedSlug && filteredTasks.length > 0) {
      setSelectedSlug(filteredTasks[0].slug);
    }
  }, [filteredTasks, selectedSlug]);

  const selectedTask = useMemo(
    () => filteredTasks.find(t => t.slug === selectedSlug) ?? null,
    [filteredTasks, selectedSlug],
  );

  // Breadcrumb
  useEffect(() => {
    if (selectedTask) {
      setBreadcrumb([{ label: selectedTask.title }]);
    } else if (agentFilter) {
      const agent = agents.find(a => a.slug === agentFilter);
      setBreadcrumb([{ label: `${agent?.title ?? agentFilter}'s work` }]);
    } else {
      clearBreadcrumb();
    }
    return () => clearBreadcrumb();
  }, [selectedTask?.slug, selectedTask?.title, agentFilter, agents, setBreadcrumb, clearBreadcrumb]);

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

  const handleSelect = useCallback((slug: string) => {
    setSelectedSlug(slug);
    // Shallow-update URL with the selected task slug for deep-linking
    const sp = new URLSearchParams(searchParams.toString());
    sp.set('task', slug);
    router.replace(`/work?${sp.toString()}`, { scroll: false });
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
        {selectedTask ? `Ask anything about "${selectedTask.title}"` : 'Select work to get started'}
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
      leftPanel={{
        title: agentFilter
          ? `${agents.find(a => a.slug === agentFilter)?.title ?? agentFilter}'s work`
          : 'Work',
        content: (
          <WorkList
            tasks={filteredTasks}
            agents={agents}
            selectedSlug={selectedSlug}
            onSelect={handleSelect}
          />
        ),
        collapsedIcon: <Briefcase className="w-4 h-4" />,
        collapsedTitle: 'Work',
      }}
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
        <EmptyState />
      )}
    </ThreePanelLayout>
  );
}
