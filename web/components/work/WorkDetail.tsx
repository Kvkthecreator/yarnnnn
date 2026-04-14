'use client';

/**
 * WorkDetail — Center panel content for selected task on /work.
 *
 * SURFACE-ARCHITECTURE.md v11 — Work is operational only (ADR-180, 2026-04-14).
 *
 * Work answers: "Is this task configured, healthy, and running correctly?"
 * Work does NOT show: output documents, accumulated files, domain knowledge.
 * Those live in Context.
 *
 * Kind dispatch (ADR-166 + ADR-180):
 *   accumulates_context  → entity grid (TrackingEntityGrid) — click entity → Context
 *   produces_deliverable → inline output (DeliverableMiddle) — full view in Work
 *   external_action      → Fire primary + history (ActionMiddle)
 *   system_maintenance   → hygiene log (MaintenanceMiddle)
 *
 * ADR-180: Work is operational. For accumulates_context, the entity grid IS the
 * operational view — it shows what's being tracked and its freshness, with each
 * entity card navigating into Context for the detail view (section-swap feel).
 * For produces_deliverable, the output is the primary work artifact — rendered
 * inline so Work and Context surface the same thing from different angles.
 */

import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import {
  MoreHorizontal, Pause, Play, MessageSquare, Send, Loader2,
} from 'lucide-react';
import { ActionMiddle } from './details/ActionMiddle';
import { MaintenanceMiddle } from './details/MaintenanceMiddle';
import { TrackingEntityGrid } from './details/TrackingEntityGrid';
import { DeliverableMiddle } from './details/DeliverableMiddle';
import { WorkModeBadge } from './WorkModeBadge';
import { SurfaceIdentityHeader } from '@/components/shell/SurfaceIdentityHeader';
import { AGENTS_ROUTE, CONTEXT_ROUTE } from '@/lib/routes';
import { formatRelativeTime } from '@/lib/formatting';
import { resolveTaskSurface, SURFACE_TYPE_LABELS, resolveDomainWorkspacePath } from '@/lib/task-types';
import { cn } from '@/lib/utils';
import type { Task, TaskDetail, Agent } from '@/types';

interface WorkDetailProps {
  task: Task | TaskDetail;
  agents: Agent[];
  refreshKey: number;
  mutationPending: boolean;
  pendingAction: 'run' | 'pause' | null;
  actionNotice: { kind: 'info' | 'success' | 'error'; text: string } | null;
  onRunTask: (slug: string) => void;   // used for Fire on external_action
  onPauseTask: (slug: string) => void;
  onOpenChat: (prompt?: string) => void;
  // Called after platform source selection is saved (reload task + bump refresh)
  onSourcesUpdated?: () => void;
}

function findAssignedAgent(task: Task, agents: Agent[]): Agent | null {
  const assigned = task.agent_slugs?.[0];
  if (!assigned) return null;
  return agents.find(a => a.slug === assigned) ?? null;
}

// ─── Overflow menu (··· ) — lifecycle actions ───────────────────────────────

function OverflowMenu({
  task,
  mutationPending,
  onPause,
  onEdit,
}: {
  task: Task;
  mutationPending: boolean;
  onPause: () => void;
  onEdit: () => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const isActive = task.status === 'active';
  const isPaused = task.status === 'paused';
  const isTerminal = task.status === 'completed' || task.status === 'archived';

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  if (isTerminal) return null;

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(o => !o)}
        disabled={mutationPending}
        className="inline-flex items-center justify-center w-7 h-7 rounded border border-border text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-50"
        aria-label="More actions"
      >
        <MoreHorizontal className="w-3.5 h-3.5" />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 z-20 min-w-[140px] rounded-md border border-border bg-popover shadow-md py-1">
          {(isActive || isPaused) && (
            <button
              onClick={() => { setOpen(false); onPause(); }}
              disabled={mutationPending}
              className="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-50"
            >
              {isActive
                ? <><Pause className="w-3 h-3" /> Pause</>
                : <><Play className="w-3 h-3" /> Resume</>
              }
            </button>
          )}
          <button
            onClick={() => { setOpen(false); onEdit(); }}
            className="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted"
          >
            <MessageSquare className="w-3 h-3" /> Edit via chat
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Kind-aware metadata strips ─────────────────────────────────────────────

function DeliverableMetadata({ task, assignedAgent }: { task: Task; assignedAgent: Agent | null }) {
  const surface = resolveTaskSurface(
    (task as TaskDetail).deliverable_spec?.expected_output?.surface,
    task.type_key,
  );
  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <WorkModeBadge mode={task.mode} />
      {surface && (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground/50">
            {SURFACE_TYPE_LABELS[surface]}
          </span>
        </>
      )}
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
      {task.last_run_at ? (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span>Last output: {formatRelativeTime(task.last_run_at)}</span>
        </>
      ) : (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span className="text-muted-foreground/60">No output yet</span>
        </>
      )}
    </div>
  );
}

function TrackingMetadata({ task, assignedAgent }: { task: Task; assignedAgent: Agent | null }) {
  const writes = task.context_writes ?? [];
  const primaryDomain = writes.find(d => d !== 'signals') ?? writes[0] ?? null;

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <WorkModeBadge mode={task.mode} />
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
          <span>Last run: {formatRelativeTime(task.last_run_at)}</span>
        </>
      ) : (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span className="text-muted-foreground/60">Never run</span>
        </>
      )}
      {primaryDomain && (
        <>
          <span className="text-muted-foreground/30">·</span>
          <Link
            href={`${CONTEXT_ROUTE}?path=${encodeURIComponent(resolveDomainWorkspacePath(primaryDomain))}`}
            className="text-primary hover:underline text-[11px]"
          >
            → {resolveDomainWorkspacePath(primaryDomain)}/
          </Link>
        </>
      )}
    </div>
  );
}

function ActionMetadata({ task, assignedAgent }: { task: Task; assignedAgent: Agent | null }) {
  const target = (task.delivery && task.delivery !== 'none')
    ? task.delivery
    : task.objective?.audience || null;

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <WorkModeBadge mode={task.mode} />
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
      {target && (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span>Target: {target}</span>
        </>
      )}
      {task.last_run_at ? (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span>Last fired: {formatRelativeTime(task.last_run_at)}</span>
        </>
      ) : (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span className="text-muted-foreground/60">Never fired</span>
        </>
      )}
    </div>
  );
}

function MaintenanceMetadata({ task }: { task: Task }) {
  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <WorkModeBadge mode={task.mode} />
      {task.schedule && (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span className="capitalize">{task.schedule}</span>
        </>
      )}
      {task.last_run_at ? (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span>Last run: {formatRelativeTime(task.last_run_at)}</span>
        </>
      ) : (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span className="text-muted-foreground/60">Never run</span>
        </>
      )}
    </div>
  );
}

// ─── Kind-aware action clusters ─────────────────────────────────────────────

function DeliverableActions({
  task, mutationPending, onPause, onEdit,
}: { task: Task; mutationPending: boolean; onPause: () => void; onEdit: () => void }) {
  return (
    <OverflowMenu task={task} mutationPending={mutationPending} onPause={onPause} onEdit={onEdit} />
  );
}

function TrackingActions({
  task, mutationPending, onPause, onEdit,
}: { task: Task; mutationPending: boolean; onPause: () => void; onEdit: () => void }) {
  return (
    <OverflowMenu task={task} mutationPending={mutationPending} onPause={onPause} onEdit={onEdit} />
  );
}

function ActionActions({
  task, mutationPending, pendingAction, onFire, onEdit,
}: {
  task: Task;
  mutationPending: boolean;
  pendingAction: 'run' | 'pause' | null;
  onFire: () => void;
  onEdit: () => void;
}) {
  const isFiring = mutationPending && pendingAction === 'run';
  const isTerminal = task.status === 'completed' || task.status === 'archived';

  return (
    <>
      {!isTerminal && (
        <button
          onClick={onFire}
          disabled={mutationPending}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded bg-primary/10 text-primary hover:bg-primary/20 disabled:opacity-50"
        >
          {isFiring
            ? <Loader2 className="w-3 h-3 animate-spin" />
            : <Send className="w-3 h-3" />
          }
          Fire
        </button>
      )}
      {/* Overflow: Edit via chat only (no pause for reactive tasks) */}
      {!isTerminal && (
        <button
          onClick={onEdit}
          className="inline-flex items-center justify-center w-7 h-7 rounded border border-border text-muted-foreground hover:text-foreground hover:bg-muted"
          aria-label="Edit via chat"
        >
          <MessageSquare className="w-3.5 h-3.5" />
        </button>
      )}
    </>
  );
}

// system_maintenance: no actions
function MaintenanceActions() {
  return null;
}

// ─── Objective block — produces_deliverable only ─────────────────────────────

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

// ─── Kind dispatch (ADR-180) ─────────────────────────────────────────────────
// Work = operational. Outputs are rendered inline per kind — the Work↔Context
// navigation feels like a section swap because clicking entities/outputs uses
// router.replace to the Context path without a full page reload.
//
// accumulates_context  → entity grid (click entity → Context panel for that entity)
// produces_deliverable → inline output (DeliverableMiddle, with Context deep-link)
// external_action      → ActionMiddle (fire history + platform link)
// system_maintenance   → MaintenanceMiddle (hygiene log)

function KindMiddle({
  task,
  refreshKey,
  onSourcesUpdated,
}: {
  task: Task | TaskDetail;
  refreshKey: number;
  onSourcesUpdated?: () => void;
}) {
  switch (task.output_kind) {
    case 'accumulates_context':
      return <TrackingEntityGrid task={task} onSourcesUpdated={onSourcesUpdated} />;
    case 'external_action':
      return <ActionMiddle task={task} refreshKey={refreshKey} onSourcesUpdated={onSourcesUpdated} />;
    case 'system_maintenance':
      return <MaintenanceMiddle task={task} refreshKey={refreshKey} />;
    case 'produces_deliverable':
    default: {
      const taskDetail = task as TaskDetail;
      return (
        <DeliverableMiddle
          taskSlug={task.slug}
          refreshKey={refreshKey}
          deliverableSpec={taskDetail.deliverable_spec}
        />
      );
    }
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
  onSourcesUpdated,
}: WorkDetailProps) {
  const assignedAgent = findAssignedAgent(task, agents);
  const kind = task.output_kind ?? 'produces_deliverable';

  const editPrompt = `Help me edit the task "${task.title}". Ask me what I want to change before making any updates.`;

  // Per-kind metadata strip
  const metadata = (() => {
    const strip = (() => {
      switch (kind) {
        case 'accumulates_context':
          return <TrackingMetadata task={task} assignedAgent={assignedAgent} />;
        case 'external_action':
          return <ActionMetadata task={task} assignedAgent={assignedAgent} />;
        case 'system_maintenance':
          return <MaintenanceMetadata task={task} />;
        default:
          return <DeliverableMetadata task={task} assignedAgent={assignedAgent} />;
      }
    })();

    return (
      <div className="space-y-1">
        {strip}
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
    );
  })();

  // Per-kind actions
  const actions = (() => {
    switch (kind) {
      case 'accumulates_context':
        return (
          <TrackingActions
            task={task}
            mutationPending={mutationPending}
            onPause={() => onPauseTask(task.slug)}
            onEdit={() => onOpenChat(editPrompt)}
          />
        );
      case 'external_action':
        return (
          <ActionActions
            task={task}
            mutationPending={mutationPending}
            pendingAction={pendingAction}
            onFire={() => onRunTask(task.slug)}
            onEdit={() => onOpenChat(editPrompt)}
          />
        );
      case 'system_maintenance':
        return <MaintenanceActions />;
      default:
        return (
          <DeliverableActions
            task={task}
            mutationPending={mutationPending}
            onPause={() => onPauseTask(task.slug)}
            onEdit={() => onOpenChat(editPrompt)}
          />
        );
    }
  })();

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Sticky chrome */}
      <div className="shrink-0">
        <SurfaceIdentityHeader
          title={task.title}
          metadata={metadata}
          actions={actions}
        />
        {/* Objective block — all kinds (describes task purpose) */}
        <ObjectiveBlock task={task} />
      </div>

      {/* Scrollable output region */}
      <div className="flex-1 overflow-auto min-h-0">
        <KindMiddle task={task} refreshKey={refreshKey} onSourcesUpdated={onSourcesUpdated} />
      </div>
    </div>
  );
}
