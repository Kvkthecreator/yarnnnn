'use client';

/**
 * WorkDetail — Center panel for selected task on /work.
 *
 * ADR-167: Refactored from a one-shape detail view into a thin shell that
 * dispatches the middle band on `task.output_kind`. The chrome (header,
 * objective, actions, assigned-to footer) is uniform across all four kinds.
 * The middle band — what the user actually came to see — diverges based on
 * what shape of work the task produces:
 *
 *   accumulates_context  → TrackingMiddle    (domain folder + CHANGELOG)
 *   produces_deliverable → DeliverableMiddle (today's iframe/markdown preview)
 *   external_action      → ActionMiddle      (fire history + platform link)
 *   system_maintenance   → MaintenanceMiddle (hygiene log + run history)
 *
 * The four middle components live in ./details/.
 *
 * Layout:
 *   - WorkHeader (chrome): title, mode badge, agent, schedule, next/last run
 *   - ObjectiveBlock (chrome, suppressed for system_maintenance)
 *   - {kind-specific middle component}
 *   - ActionsRow (chrome): Run now, Pause/Resume, Edit via chat
 *   - AssignedAgentLink (chrome)
 */

import Link from 'next/link';
import {
  Play,
  Pause,
  MessageSquare,
  ExternalLink,
  Briefcase,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatRelativeTime } from '@/lib/formatting';
import { WorkModeBadge } from './WorkModeBadge';
import { DeliverableMiddle } from './details/DeliverableMiddle';
import { TrackingMiddle } from './details/TrackingMiddle';
import { ActionMiddle } from './details/ActionMiddle';
import { MaintenanceMiddle } from './details/MaintenanceMiddle';
import { AGENTS_ROUTE } from '@/lib/routes';
import type { Task, Agent } from '@/types';

interface WorkDetailProps {
  task: Task;
  agents: Agent[];
  onRun: (slug: string) => void;
  onPause: (slug: string) => void;
  onOpenChat: (prompt?: string) => void;
  busy: boolean;
}

function findAssignedAgent(task: Task, agents: Agent[]): Agent | null {
  const assigned = task.agent_slugs?.[0];
  if (!assigned) return null;
  return agents.find(a => a.slug === assigned) ?? null;
}

// ─── Pinned Header ───

function WorkHeader({
  task,
  assignedAgent,
}: {
  task: Task;
  assignedAgent: Agent | null;
}) {
  return (
    <div className="px-5 py-3 border-b border-border shrink-0">
      <div className="flex items-center gap-2 mb-1">
        <h2 className="text-base font-semibold flex-1 truncate">{task.title}</h2>
        <WorkModeBadge mode={task.mode} />
        {task.essential && (
          <span
            className="text-[10px] rounded-full bg-amber-500/10 text-amber-700 px-2 py-0.5 font-medium"
            title="This task is essential to your workspace (ADR-161)"
          >
            ★ Essential
          </span>
        )}
      </div>
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
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
      </div>
      <div className="flex items-center gap-1.5 mt-1 text-[11px] text-muted-foreground/70">
        {task.next_run_at && <span>Next: {formatRelativeTime(task.next_run_at)}</span>}
        {task.next_run_at && task.last_run_at && <span className="text-muted-foreground/30">·</span>}
        {task.last_run_at && <span>Last: {formatRelativeTime(task.last_run_at)}</span>}
        {!task.next_run_at && !task.last_run_at && <span>Never run</span>}
      </div>
    </div>
  );
}

// ─── Objective ───

function ObjectiveBlock({ task }: { task: Task }) {
  if (!task.objective) return null;
  const { deliverable, audience, purpose, format } = task.objective;
  if (!deliverable && !audience && !purpose && !format) return null;

  return (
    <div className="px-5 py-4 border-b border-border/40">
      <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/40 mb-2">Objective</h3>
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

function KindMiddle({ task }: { task: Task }) {
  switch (task.output_kind) {
    case 'accumulates_context':
      return <TrackingMiddle task={task} />;
    case 'external_action':
      return <ActionMiddle task={task} />;
    case 'system_maintenance':
      return <MaintenanceMiddle task={task} />;
    case 'produces_deliverable':
    default:
      // Default to DeliverableMiddle for unknown/missing output_kind so legacy
      // tasks with no enriched type info still render something useful.
      return <DeliverableMiddle taskSlug={task.slug} />;
  }
}

// ─── Actions ───

function ActionsRow({
  task,
  onRun,
  onPause,
  onOpenChat,
  busy,
}: {
  task: Task;
  onRun: () => void;
  onPause: () => void;
  onOpenChat: (prompt?: string) => void;
  busy: boolean;
}) {
  const isActive = task.status === 'active';
  const pauseDisabled = busy || (task.essential && isActive === false);

  return (
    <div className="px-5 py-4 flex items-center gap-2 flex-wrap">
      <button
        onClick={onRun}
        disabled={busy || !isActive}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded bg-primary/10 text-primary hover:bg-primary/20 disabled:opacity-50"
      >
        <Play className="w-3 h-3" /> Run now
      </button>
      <button
        onClick={onPause}
        disabled={pauseDisabled}
        className={cn(
          'inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded border border-border',
          'text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-50',
        )}
        title={
          task.essential && !isActive
            ? 'Essential tasks can be paused but pausing this one leaves you without a daily check-in.'
            : undefined
        }
      >
        {isActive ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
        {isActive ? 'Pause' : 'Resume'}
      </button>
      <button
        onClick={() => onOpenChat(`I want to update the task "${task.title}"`)}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded border border-border text-muted-foreground hover:text-foreground hover:bg-muted ml-auto"
      >
        <MessageSquare className="w-3 h-3" /> Edit via chat
      </button>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// MAIN
// ═══════════════════════════════════════════════════════════════

export function WorkDetail({
  task,
  agents,
  onRun,
  onPause,
  onOpenChat,
  busy,
}: WorkDetailProps) {
  const assignedAgent = findAssignedAgent(task, agents);
  // ADR-167: system_maintenance tasks suppress the objective block — TP owns
  // their contract, not the user. Other kinds always render it if present.
  const showObjective = task.output_kind !== 'system_maintenance';

  return (
    <div className="flex flex-col h-full">
      <WorkHeader task={task} assignedAgent={assignedAgent} />
      <div className="flex-1 overflow-auto">
        {showObjective && <ObjectiveBlock task={task} />}
        <KindMiddle task={task} />
        <ActionsRow
          task={task}
          onRun={() => onRun(task.slug)}
          onPause={() => onPause(task.slug)}
          onOpenChat={onOpenChat}
          busy={busy}
        />
        {assignedAgent && (
          <div className="px-5 py-3 border-t border-border/40">
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
    </div>
  );
}
