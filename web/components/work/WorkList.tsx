'use client';

/**
 * WorkList — Left sidebar listing tasks, sorted by upcoming.
 *
 * ADR-163 Surface Restructure: This replaces the Pipeline tab that previously
 * lived on the Agents page. Work lives on /work now. Each task row shows:
 *   - Status dot (active/paused/completed)
 *   - Title
 *   - Assigned agent name
 *   - Mode badge (Recurring / One-time)
 *   - Next run relative time
 *
 * Active tasks sort by next_run_at ascending (soonest first).
 * Paused tasks appear below active, sorted by last_run_at desc.
 * Completed and archived hidden by default.
 */

import { cn } from '@/lib/utils';
import { Circle, Sparkles } from 'lucide-react';
import { formatRelativeTime } from '@/lib/formatting';
import { WorkModeBadge } from './WorkModeBadge';
import type { Task, Agent } from '@/types';

interface WorkListProps {
  tasks: Task[];
  agents: Agent[];
  selectedSlug: string | null;
  onSelect: (slug: string) => void;
}

function agentNameFor(task: Task, agents: Agent[]): string | null {
  const assigned = task.agent_slugs?.[0];
  if (!assigned) return null;
  const agent = agents.find(a => a.slug === assigned);
  return agent?.title ?? assigned;
}

export function WorkList({ tasks, agents, selectedSlug, onSelect }: WorkListProps) {
  const active = tasks
    .filter(t => t.status === 'active')
    .sort((a, b) => {
      const aRun = a.next_run_at || '9999';
      const bRun = b.next_run_at || '9999';
      return aRun.localeCompare(bRun);
    });
  const paused = tasks
    .filter(t => t.status === 'paused')
    .sort((a, b) => (b.last_run_at || '').localeCompare(a.last_run_at || ''));

  if (tasks.length === 0) {
    return (
      <div className="p-4 text-center">
        <Sparkles className="w-6 h-6 text-muted-foreground/20 mx-auto mb-2" />
        <p className="text-sm font-medium mb-1">No tasks yet</p>
        <p className="text-xs text-muted-foreground">
          Chat with your assistant to set up the first one.
        </p>
      </div>
    );
  }

  return (
    <div className="py-2">
      {active.length > 0 && (
        <div className="mb-2">
          <div className="px-3 py-1 text-[10px] uppercase tracking-wide text-muted-foreground/50">
            Active
          </div>
          {active.map(task => (
            <WorkRow
              key={task.slug}
              task={task}
              agentName={agentNameFor(task, agents)}
              selected={selectedSlug === task.slug}
              onSelect={() => onSelect(task.slug)}
            />
          ))}
        </div>
      )}
      {paused.length > 0 && (
        <div>
          <div className="px-3 py-1 text-[10px] uppercase tracking-wide text-muted-foreground/50">
            Paused
          </div>
          {paused.map(task => (
            <WorkRow
              key={task.slug}
              task={task}
              agentName={agentNameFor(task, agents)}
              selected={selectedSlug === task.slug}
              onSelect={() => onSelect(task.slug)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function WorkRow({
  task,
  agentName,
  selected,
  onSelect,
}: {
  task: Task;
  agentName: string | null;
  selected: boolean;
  onSelect: () => void;
}) {
  const isActive = task.status === 'active';
  const statusColor = isActive
    ? 'fill-green-500 text-green-500'
    : task.status === 'paused'
      ? 'fill-amber-500 text-amber-500'
      : 'text-muted-foreground/30';

  return (
    <button
      onClick={onSelect}
      className={cn(
        'w-full text-left px-3 py-2 transition-colors',
        selected ? 'bg-muted' : 'hover:bg-muted/50',
      )}
    >
      <div className="flex items-center gap-2 mb-1">
        <Circle className={cn('w-2 h-2 shrink-0', statusColor)} />
        <span className="text-sm font-medium flex-1 truncate">{task.title}</span>
        {task.essential && (
          <span className="text-[10px] text-amber-600" title="Essential task (cannot be archived)">
            ★
          </span>
        )}
      </div>
      <div className="flex items-center gap-1.5 pl-4 text-[11px] text-muted-foreground">
        <WorkModeBadge mode={task.mode} />
        {agentName && <span className="truncate">{agentName}</span>}
      </div>
      {(task.next_run_at || task.last_run_at) && (
        <div className="pl-4 mt-0.5 text-[10px] text-muted-foreground/70">
          {isActive && task.next_run_at && <span>Next: {formatRelativeTime(task.next_run_at)}</span>}
          {!isActive && task.last_run_at && <span>Last: {formatRelativeTime(task.last_run_at)}</span>}
        </div>
      )}
    </button>
  );
}
