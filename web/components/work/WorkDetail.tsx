'use client';

/**
 * WorkDetail — Center panel content for selected task on /work.
 *
 * ADR-167 v2: This component is now content-only. The task title, status
 * metadata strip, mode badge, and Run/Pause/Edit-via-chat actions all moved
 * UP into the page-level <PageHeader /> rendered by `app/(authenticated)/
 * work/page.tsx`. WorkDetail renders only:
 *
 *   - ObjectiveBlock (chrome, suppressed for system_maintenance)
 *   - {kind-specific middle component}
 *   - AssignedAgentLink (chrome footer)
 *
 * The kind-aware middle band still dispatches on `task.output_kind`:
 *
 *   accumulates_context  → TrackingMiddle    (domain folder + CHANGELOG)
 *   produces_deliverable → DeliverableMiddle (today's iframe/markdown preview)
 *   external_action      → ActionMiddle      (fire history + platform link)
 *   system_maintenance   → MaintenanceMiddle (hygiene log + run history)
 *
 * The four middle components live in ./details/.
 *
 * The `essential` flag stays in the schema and the DB (it's load-bearing —
 * gates archive in routes/tasks.py), but it no longer renders as a visual
 * badge. Users discover it functionally when they try to archive a daily-
 * update task and the API rejects it.
 */

import Link from 'next/link';
import { ExternalLink, Briefcase } from 'lucide-react';
import { DeliverableMiddle } from './details/DeliverableMiddle';
import { TrackingMiddle } from './details/TrackingMiddle';
import { ActionMiddle } from './details/ActionMiddle';
import { MaintenanceMiddle } from './details/MaintenanceMiddle';
import { AGENTS_ROUTE } from '@/lib/routes';
import type { Task, Agent } from '@/types';

interface WorkDetailProps {
  task: Task;
  agents: Agent[];
  onOpenChat: (prompt?: string) => void;
}

function findAssignedAgent(task: Task, agents: Agent[]): Agent | null {
  const assigned = task.agent_slugs?.[0];
  if (!assigned) return null;
  return agents.find(a => a.slug === assigned) ?? null;
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

// ═══════════════════════════════════════════════════════════════
// MAIN
// ═══════════════════════════════════════════════════════════════

export function WorkDetail({ task, agents }: WorkDetailProps) {
  const assignedAgent = findAssignedAgent(task, agents);
  // ADR-167: system_maintenance tasks suppress the objective block — TP owns
  // their contract, not the user. Other kinds always render it if present.
  const showObjective = task.output_kind !== 'system_maintenance';

  return (
    <div className="flex-1 overflow-auto">
      {showObjective && <ObjectiveBlock task={task} />}
      <KindMiddle task={task} />
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
  );
}
