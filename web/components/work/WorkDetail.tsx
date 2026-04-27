'use client';

/**
 * WorkDetail — Center panel content for selected task on /work.
 *
 * SURFACE-ARCHITECTURE.md v11 — Work is operational only (ADR-180, 2026-04-14).
 * Work answers: "Is this task configured, healthy, and running correctly?"
 * Work does NOT show: output documents, accumulated files, domain knowledge.
 * Those live in Context.
 *
 * ADR-225 Phase 3 — Unified compositor seam:
 *   - Chrome (metadata strip + actions row) flows through
 *     `<ChromeRenderer>` consulting `resolveChrome()`. Bundle middles
 *     may declare `chrome` to override the kernel-default chrome for
 *     their matched task; missing parts inherit from the per-output_kind
 *     kernel default in `kernel-defaults.ts`.
 *   - Middle (content area) flows through `<MiddleResolver>` consulting
 *     `resolveMiddle()`.
 *   - Singular Implementation: the per-kind metadata + actions switches
 *     that lived in this file (DeliverableMetadata / TrackingMetadata /
 *     ActionMetadata / MaintenanceMetadata + their action clusters) are
 *     DELETED. Their replacements are kernel-chrome library components
 *     dispatched through the same registry as bundle components.
 *
 * Action handler threading: the `<WorkDetailActionsProvider>` carries
 * task + agents + lifecycle handlers + per-task surface state through
 * React context. Both kernel and bundle chrome components read via
 * `useWorkDetailActions()`.
 */

import { MiddleResolver } from '@/components/library/MiddleResolver';
import { ChromeRenderer } from '@/components/library/ChromeRenderer';
import {
  WorkDetailActionsProvider,
  type WorkDetailActionsContextValue,
} from '@/components/library/WorkDetailActionsContext';
import { resolveChrome, getDetailMiddles, useComposition } from '@/lib/compositor';
import { FeedbackStrip } from './details/FeedbackStrip';
import { SurfaceIdentityHeader } from '@/components/shell/SurfaceIdentityHeader';
import { cn } from '@/lib/utils';
import type { Task, TaskDetail, Agent } from '@/types';

interface WorkDetailProps {
  task: Task | TaskDetail;
  agents: Agent[];
  refreshKey: number;
  mutationPending: boolean;
  pendingAction: 'run' | 'pause' | null;
  actionNotice: { kind: 'info' | 'success' | 'error'; text: string } | null;
  onRunTask: (slug: string) => void;
  onPauseTask: (slug: string) => void;
  onOpenChat: (prompt?: string) => void;
  onSourcesUpdated?: () => void;
}

function findAssignedAgent(task: Task, agents: Agent[]): Agent | null {
  const assigned = task.agent_slugs?.[0];
  if (!assigned) return null;
  return agents.find(a => a.slug === assigned) ?? null;
}

// ─── Objective block — all kinds except system_maintenance ──────────────────

function ObjectiveBlock({ task }: { task: Task }) {
  if (!task.objective) return null;
  const { deliverable, audience, purpose, format } = task.objective;
  if (!deliverable && !audience && !purpose && !format) return null;

  return (
    <div className="px-6 py-4 border-b border-border/40">
      <h3 className="text-[11px] font-medium text-muted-foreground/60 mb-2">Objective</h3>
      <div className="text-xs text-muted-foreground space-y-0.5">
        {deliverable && <p>· Deliverable: {deliverable}</p>}
        {audience && <p>· Audience: {audience}</p>}
        {purpose && <p>· Purpose: {purpose}</p>}
        {format && <p>· Format: {format}</p>}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// MAIN
// ═══════════════════════════════════════════════════════════════

export function WorkDetail({
  task,
  agents,
  refreshKey,
  mutationPending,
  pendingAction,
  actionNotice,
  onRunTask,
  onPauseTask,
  onOpenChat,
  onSourcesUpdated,
}: WorkDetailProps) {
  const assignedAgent = findAssignedAgent(task, agents);
  const editPrompt = `Help me edit the task "${task.title}". Ask me what I want to change before making any updates.`;

  // Resolve chrome through the compositor seam (ADR-225 Phase 3).
  const { data: composition } = useComposition();
  const middles = getDetailMiddles(composition.composition, 'work');
  const chrome = resolveChrome(
    {
      task: {
        slug: task.slug,
        output_kind: task.output_kind ?? null,
      },
    },
    middles,
  );

  // Action handler context for both kernel and bundle chrome components.
  const actionsValue: WorkDetailActionsContextValue = {
    task,
    agents,
    assignedAgent,
    mutationPending,
    pendingAction,
    actionNotice,
    onRunTask,
    onPauseTask,
    onEdit: (prompt) => onOpenChat(prompt ?? editPrompt),
  };

  return (
    <WorkDetailActionsProvider value={actionsValue}>
      <div className="flex flex-col flex-1 min-h-0">
        {/* Sticky chrome */}
        <div className="shrink-0">
          <SurfaceIdentityHeader
            title={task.title}
            metadata={
              <div className="space-y-1">
                <ChromeRenderer decl={chrome.metadata} />
                {actionNotice && (
                  <p className={cn(
                    'text-[11px]',
                    actionNotice.kind === 'error'
                      ? 'text-destructive'
                      : actionNotice.kind === 'success'
                        ? 'text-primary'
                        : 'text-muted-foreground',
                  )}>
                    {actionNotice.text}
                  </p>
                )}
              </div>
            }
            actions={<ChromeRenderer decls={chrome.actions} />}
          />
          {task.output_kind !== 'system_maintenance' && <ObjectiveBlock task={task} />}
        </div>

        {/* Scrollable output region */}
        <div className="flex-1 overflow-auto min-h-0">
          <MiddleResolver task={task} refreshKey={refreshKey} onSourcesUpdated={onSourcesUpdated} />
          <FeedbackStrip task={task} onOpenChat={onOpenChat} />
        </div>
      </div>
    </WorkDetailActionsProvider>
  );
}
