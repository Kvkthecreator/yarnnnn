'use client';

/**
 * WorkDetail — Center panel content for selected task on /work.
 *
 * ADR-167 v5: WorkDetail owns the task's visual identity. It renders:
 *
 *   1. SurfaceIdentityHeader  — task title (real H1), metadata strip
 *                               (mode · status · schedule · next run),
 *                               inline actions (Run / Pause / Edit via chat)
 *   2. ObjectiveBlock         — chrome, suppressed for system_maintenance
 *   3. KindMiddle             — dispatch on task.output_kind
 *   4. AssignedAgentLink      — footer link to the agent page
 *
 * This is a v5 change from v4 (and earlier), where the title + metadata +
 * actions lived up in PageHeader as chrome. That model created two problems:
 * (1) the task identity was visually separated from the task content, and
 * (2) PageHeader's promoted title duplicated against content H1s produced
 * by the output itself. v5 collapses task identity into the content area,
 * alongside the content it describes.
 *
 * The four output kinds still use the same kind-aware middle components in
 * `./details/`. They are content-only — they do NOT render a task title of
 * their own. SurfaceIdentityHeader is the single source of title truth.
 *
 *   accumulates_context  → TrackingMiddle    (domain folder + CHANGELOG card)
 *   produces_deliverable → DeliverableMiddle (output iframe in a nested card)
 *   external_action      → ActionMiddle      (fire history + platform link)
 *   system_maintenance   → MaintenanceMiddle (hygiene log in a nested card)
 */

import Link from 'next/link';
import { ExternalLink, Briefcase, Play, Pause, MessageSquare, Loader2 } from 'lucide-react';
import { DeliverableMiddle } from './details/DeliverableMiddle';
import { TrackingMiddle } from './details/TrackingMiddle';
import { ActionMiddle } from './details/ActionMiddle';
import { MaintenanceMiddle } from './details/MaintenanceMiddle';
import { WorkModeBadge } from './WorkModeBadge';
import { SurfaceIdentityHeader } from '@/components/shell/SurfaceIdentityHeader';
import { AGENTS_ROUTE } from '@/lib/routes';
import { formatRelativeTime } from '@/lib/formatting';
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
}

function findAssignedAgent(task: Task, agents: Agent[]): Agent | null {
  const assigned = task.agent_slugs?.[0];
  if (!assigned) return null;
  return agents.find(a => a.slug === assigned) ?? null;
}

// ─── Identity metadata (under H1) ───

function TaskMetadata({ task, assignedAgent }: { task: Task; assignedAgent: Agent | null }) {
  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <WorkModeBadge mode={task.mode} />
      <span className="text-muted-foreground/30">·</span>
      <span className="capitalize">{task.status}</span>
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
      {task.schedule && (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span className="capitalize">{task.schedule}</span>
        </>
      )}
      {task.next_run_at ? (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span>Next: {formatRelativeTime(task.next_run_at)}</span>
        </>
      ) : task.last_run_at ? (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span>Last: {formatRelativeTime(task.last_run_at)}</span>
        </>
      ) : (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span>Never run</span>
        </>
      )}
    </div>
  );
}

// ─── Identity actions (right of H1) ───

function TaskActions({
  task,
  mutationPending,
  pendingAction,
  onRun,
  onPause,
  onEdit,
}: {
  task: Task;
  mutationPending: boolean;
  pendingAction: 'run' | 'pause' | null;
  onRun: () => void;
  onPause: () => void;
  onEdit: () => void;
}) {
  const isRunPending = mutationPending && pendingAction === 'run';
  const isActive = task.status === 'active';
  const isPaused = task.status === 'paused';
  const isTerminal = task.status === 'completed' || task.status === 'archived';

  return (
    <>
      {/* Active: Run now + Pause. Paused: Resume only. Terminal: nothing. */}
      {isActive && (
        <>
          <button
            onClick={onRun}
            disabled={mutationPending}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded bg-primary/10 text-primary hover:bg-primary/20 disabled:opacity-50"
          >
            {isRunPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
            Run now
          </button>
          <button
            onClick={onPause}
            disabled={mutationPending}
            className={cn(
              'inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded border border-border',
              'text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-50',
            )}
          >
            <Pause className="w-3 h-3" /> Pause
          </button>
        </>
      )}
      {isPaused && (
        <button
          onClick={onPause}
          disabled={mutationPending}
          className={cn(
            'inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded border border-border',
            'text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-50',
          )}
        >
          <Play className="w-3 h-3" /> Resume
        </button>
      )}
      {!isTerminal && (
        <button
          onClick={onEdit}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded border border-border text-muted-foreground hover:text-foreground hover:bg-muted"
        >
          <MessageSquare className="w-3 h-3" /> Edit via chat
        </button>
      )}
    </>
  );
}

// ─── Objective (chrome section) ───

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

// ─── Kind dispatch (ADR-167) ───

function KindMiddle({ task, refreshKey }: { task: Task | TaskDetail; refreshKey: number }) {
  const deliverableSpec = (task as TaskDetail).deliverable_spec ?? null;
  switch (task.output_kind) {
    case 'accumulates_context':
      return <TrackingMiddle task={task} refreshKey={refreshKey} deliverableSpec={deliverableSpec} />;
    case 'external_action':
      return <ActionMiddle task={task} refreshKey={refreshKey} />;
    case 'system_maintenance':
      return <MaintenanceMiddle task={task} refreshKey={refreshKey} />;
    case 'produces_deliverable':
    default:
      // Default to DeliverableMiddle for unknown/missing output_kind so legacy
      // tasks with no enriched type info still render something useful.
      return <DeliverableMiddle taskSlug={task.slug} refreshKey={refreshKey} deliverableSpec={deliverableSpec} />;
  }
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
}: WorkDetailProps) {
  const assignedAgent = findAssignedAgent(task, agents);
  // ADR-167: system_maintenance tasks suppress the objective block — TP owns
  // their contract, not the user. Other kinds always render it if present.
  const showObjective = task.output_kind !== 'system_maintenance';

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Sticky chrome — header + objective never scroll away */}
      <div className="shrink-0">
        <SurfaceIdentityHeader
          title={task.title}
          metadata={(
            <div className="space-y-1">
              <TaskMetadata task={task} assignedAgent={assignedAgent} />
              {actionNotice && (
                <p
                  className={cn(
                    'text-[11px]',
                    actionNotice.kind === 'error'
                      ? 'text-destructive'
                      : actionNotice.kind === 'success'
                        ? 'text-primary'
                        : 'text-muted-foreground',
                  )}
                >
                  {actionNotice.text}
                </p>
              )}
            </div>
          )}
          actions={
            <TaskActions
              task={task}
              mutationPending={mutationPending}
              pendingAction={pendingAction}
              onRun={() => onRunTask(task.slug)}
              onPause={() => onPauseTask(task.slug)}
              onEdit={() => onOpenChat(`Help me edit the task "${task.title}". Ask me what I want to change before making any updates.`)}
            />
          }
        />
        {showObjective && <ObjectiveBlock task={task} />}
      </div>

      {/* Scrollable output region — only this zone scrolls */}
      <div className="flex-1 overflow-auto min-h-0">
        <KindMiddle task={task} refreshKey={refreshKey} />
      </div>

      {/* Sticky footer */}
      {assignedAgent && (
        <div className="shrink-0 px-6 py-3 border-t border-border/40">
          <Link
            href={`${AGENTS_ROUTE}?agent=${assignedAgent.slug}`}
            className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
          >
            <Briefcase className="w-3 h-3" />
            Assigned to {assignedAgent.title}
            <ExternalLink className="w-3 h-3" />
          </Link>
        </div>
      )}
    </div>
  );
}
