'use client';

/**
 * WorkListSurface — Full-width list surface for /work (ADR-167).
 *
 * SURFACE-ARCHITECTURE.md v10.0 — polished list layout (2026-04-14).
 *
 * Layout:
 *   Row 1: Mode chips (Recurring | One-time — no "All"; unselected = show all)
 *   Row 2: Search (flex) + Group-by toggle (Mode | Agent) + ··· overflow
 *           (include archived, include system tasks)
 *
 * Group headers key on output_kind label when grouped by mode
 * ("Reports", "Tracking", "Actions") — more descriptive than "Recurring".
 *
 * Row metadata is context-aware: agent name suppressed when grouped by agent,
 * mode badge suppressed when grouped by mode. Next/Last time is the primary
 * scan signal — bumped to text-xs.
 */

import { useRef, useEffect, useMemo, useState } from 'react';
import { MoreHorizontal, Search, Sparkles, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatRelativeTime } from '@/lib/formatting';
import { WorkModeBadge } from './WorkModeBadge';
import { getAgentSlug } from '@/lib/agent-identity';
import { taskModeLabel } from '@/types';
import type { Task, Agent } from '@/types';

interface WorkListSurfaceProps {
  tasks: Task[];
  agents: Agent[];
  agentFilter: string | null;
  dataError?: string | null;
  onClearAgentFilter: () => void;
  onSelect: (slug: string) => void;
}

type ModeFilter = 'recurring' | 'one-time' | null;
type GroupBy = 'mode' | 'agent';

// output_kind → human group label (used when groupBy='mode')
const KIND_GROUP_LABEL: Record<string, string> = {
  produces_deliverable: 'Reports',
  accumulates_context:  'Tracking',
  external_action:      'Actions',
  system_maintenance:   'System',
};

function kindGroupLabel(task: Task): string {
  return KIND_GROUP_LABEL[task.output_kind ?? ''] ?? 'Other';
}

const KIND_GROUP_ORDER = ['Reports', 'Tracking', 'Actions', 'Other', 'System'];

function isSystemTask(task: Task): boolean {
  return task.output_kind === 'system_maintenance';
}

function agentNameFor(task: Task, agents: Agent[]): string {
  const assigned = task.agent_slugs?.[0];
  if (!assigned) return 'Unassigned';
  const agent = agents.find(a => getAgentSlug(a) === assigned);
  return agent?.title ?? assigned;
}

function statusRank(status: string | undefined): number {
  switch (status) {
    case 'active':    return 0;
    case 'paused':    return 1;
    case 'completed': return 2;
    case 'archived':  return 3;
    default:          return 4;
  }
}

function compareTasks(a: Task, b: Task): number {
  const statusDiff = statusRank(a.status) - statusRank(b.status);
  if (statusDiff !== 0) return statusDiff;
  const aNext = a.next_run_at ? new Date(a.next_run_at).getTime() : Number.POSITIVE_INFINITY;
  const bNext = b.next_run_at ? new Date(b.next_run_at).getTime() : Number.POSITIVE_INFINITY;
  if ((a.status === 'active' || b.status === 'active') && aNext !== bNext) return aNext - bNext;
  const aLast = a.last_run_at ? new Date(a.last_run_at).getTime() : 0;
  const bLast = b.last_run_at ? new Date(b.last_run_at).getTime() : 0;
  if (aLast !== bLast) return bLast - aLast;
  return a.title.localeCompare(b.title);
}

function buildSearchText(task: Task, agents: Agent[]): string {
  const obj = task.objective
    ? [task.objective.deliverable, task.objective.audience, task.objective.purpose, task.objective.format]
    : [];
  return [
    task.title,
    agentNameFor(task, agents),
    task.type_key,
    task.delivery,
    task.schedule,
    ...(task.context_reads ?? []),
    ...(task.context_writes ?? []),
    ...obj,
  ].filter(Boolean).join(' ').toLowerCase();
}

function compareGroups(groupBy: GroupBy, a: string, b: string): number {
  if (groupBy === 'mode') {
    const ai = KIND_GROUP_ORDER.indexOf(a);
    const bi = KIND_GROUP_ORDER.indexOf(b);
    if (ai !== -1 || bi !== -1) {
      return (ai === -1 ? KIND_GROUP_ORDER.length : ai) - (bi === -1 ? KIND_GROUP_ORDER.length : bi);
    }
  }
  return a.localeCompare(b);
}

// ─── Overflow menu for rare options ────────────────────────────────────────

function OverflowOptions({
  includeHistorical,
  includeSystem,
  onToggleHistorical,
  onToggleSystem,
}: {
  includeHistorical: boolean;
  includeSystem: boolean;
  onToggleHistorical: () => void;
  onToggleSystem: () => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const activeCount = (includeHistorical ? 1 : 0) + (includeSystem ? 1 : 0);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(o => !o)}
        className={cn(
          'inline-flex items-center justify-center w-7 h-7 rounded border transition-colors',
          activeCount > 0
            ? 'border-primary/40 text-primary bg-primary/5'
            : 'border-border/60 text-muted-foreground hover:text-foreground hover:bg-muted',
        )}
        aria-label="More filters"
      >
        <MoreHorizontal className="w-3.5 h-3.5" />
        {activeCount > 0 && (
          <span className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-primary text-[8px] text-primary-foreground flex items-center justify-center font-medium">
            {activeCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 z-20 min-w-[200px] rounded-md border border-border bg-popover shadow-md py-1">
          <label className="flex items-center gap-2.5 px-3 py-2 text-xs text-muted-foreground hover:text-foreground hover:bg-muted cursor-pointer">
            <input
              type="checkbox"
              checked={includeHistorical}
              onChange={onToggleHistorical}
              className="rounded border-border"
            />
            Include completed &amp; archived
          </label>
          <label className="flex items-center gap-2.5 px-3 py-2 text-xs text-muted-foreground hover:text-foreground hover:bg-muted cursor-pointer">
            <input
              type="checkbox"
              checked={includeSystem}
              onChange={onToggleSystem}
              className="rounded border-border"
            />
            Include system tasks
          </label>
        </div>
      )}
    </div>
  );
}

// ─── Main ───────────────────────────────────────────────────────────────────

export function WorkListSurface({
  tasks,
  agents,
  agentFilter,
  dataError,
  onClearAgentFilter,
  onSelect,
}: WorkListSurfaceProps) {
  const [modeFilter, setModeFilter] = useState<ModeFilter>(null);
  const [search, setSearch] = useState('');
  const [groupBy, setGroupBy] = useState<GroupBy>('mode');
  const [includeHistorical, setIncludeHistorical] = useState(false);
  const [includeSystem, setIncludeSystem] = useState(false);

  const filtered = useMemo(() => {
    let result = tasks;
    if (!includeSystem)      result = result.filter(t => !isSystemTask(t));
    if (!includeHistorical)  result = result.filter(t => t.status !== 'archived' && t.status !== 'completed');
    if (modeFilter === 'recurring')
      result = result.filter(t => taskModeLabel(t.mode) === 'Recurring');
    if (modeFilter === 'one-time')
      result = result.filter(t => taskModeLabel(t.mode) === 'One-time');
    if (agentFilter)
      result = result.filter(t => t.agent_slugs?.includes(agentFilter));
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      result = result.filter(t => buildSearchText(t, agents).includes(q));
    }
    return result;
  }, [tasks, modeFilter, agentFilter, search, includeHistorical, includeSystem, agents]);

  const grouped = useMemo(() => {
    const groups: Record<string, Task[]> = {};
    for (const task of filtered) {
      const key = groupBy === 'mode' ? kindGroupLabel(task) : agentNameFor(task, agents);
      if (!groups[key]) groups[key] = [];
      groups[key].push(task);
    }
    for (const key of Object.keys(groups)) groups[key].sort(compareTasks);
    return Object.entries(groups).sort((a, b) => compareGroups(groupBy, a[0], b[0]));
  }, [filtered, groupBy, agents]);

  const agentLabel = agentFilter
    ? agents.find(a => getAgentSlug(a) === agentFilter)?.title ?? agentFilter
    : null;

  return (
    <div className="flex flex-col h-full">
      {/* ── Toolbar ── */}
      <div className="px-4 sm:px-6 pt-4 pb-3 border-b border-border/60 shrink-0 space-y-2.5">
        {dataError && (
          <div className="rounded-md border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-[11px] text-amber-700">
            Showing last available data — refresh to retry.
          </div>
        )}

        {/* Row 1: mode chips (no All — unselected = show all) */}
        <div className="flex items-center gap-1.5">
          {(['recurring', 'one-time'] as const).map(id => {
            const label = id === 'recurring' ? 'Recurring' : 'One-time';
            const active = modeFilter === id;
            return (
              <button
                key={id}
                onClick={() => setModeFilter(active ? null : id)}
                className={cn(
                  'px-3 py-1 rounded-full text-xs font-medium transition-colors',
                  active
                    ? 'bg-foreground text-background'
                    : 'bg-muted/60 text-muted-foreground hover:bg-muted',
                )}
              >
                {label}
              </button>
            );
          })}

          {/* Agent filter chip — appears inline when active */}
          {agentFilter && (
            <button
              onClick={onClearAgentFilter}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-primary/10 text-primary text-xs hover:bg-primary/20 transition-colors"
            >
              {agentLabel}
              <X className="w-3 h-3" />
            </button>
          )}
        </div>

        {/* Row 2: search + group-by toggle + overflow */}
        <div className="flex items-center gap-2">
          {/* Search */}
          <div className="relative flex-1 min-w-0">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/40" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search…"
              className="w-full pl-8 pr-3 py-1.5 text-xs bg-muted/40 border border-border/60 rounded-md focus:outline-none focus:ring-1 focus:ring-ring focus:border-ring"
            />
          </div>

          {/* Group-by segmented toggle */}
          <div className="flex items-center rounded-md border border-border/60 overflow-hidden text-xs shrink-0">
            {(['mode', 'agent'] as const).map(opt => (
              <button
                key={opt}
                onClick={() => setGroupBy(opt)}
                className={cn(
                  'px-2.5 py-1.5 capitalize transition-colors',
                  groupBy === opt
                    ? 'bg-foreground text-background font-medium'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/60',
                )}
              >
                {opt === 'mode' ? 'Kind' : 'Agent'}
              </button>
            ))}
          </div>

          {/* Overflow (rare options) */}
          <OverflowOptions
            includeHistorical={includeHistorical}
            includeSystem={includeSystem}
            onToggleHistorical={() => setIncludeHistorical(v => !v)}
            onToggleSystem={() => setIncludeSystem(v => !v)}
          />
        </div>
      </div>

      {/* ── List body ── */}
      <div className="flex-1 overflow-auto">
        {filtered.length === 0 ? (
          <EmptyResult hasFilters={modeFilter !== null || !!search || !!agentFilter} />
        ) : (
          <div className="px-4 sm:px-6 py-4 space-y-5 max-w-4xl">
            {grouped.map(([groupName, items]) => (
              <section key={groupName}>
                <h3 className="text-[11px] font-medium text-muted-foreground/50 uppercase tracking-wide mb-1.5 px-1">
                  {groupName}
                  <span className="normal-case font-normal ml-1.5 text-muted-foreground/30">· {items.length}</span>
                </h3>
                <div className="rounded-lg border border-border/50 divide-y divide-border/30 overflow-hidden">
                  {items.map(task => (
                    <WorkRow
                      key={task.slug}
                      task={task}
                      agents={agents}
                      groupBy={groupBy}
                      dim={isSystemTask(task)}
                      onSelect={() => onSelect(task.slug)}
                    />
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Row ────────────────────────────────────────────────────────────────────

function WorkRow({
  task,
  agents,
  groupBy,
  dim,
  onSelect,
}: {
  task: Task;
  agents: Agent[];
  groupBy: GroupBy;
  dim?: boolean;
  onSelect: () => void;
}) {
  const isActive = task.status === 'active';
  const isPaused = task.status === 'paused';

  const statusColor = dim
    ? 'bg-muted-foreground/15'
    : isActive
      ? 'bg-green-500'
      : isPaused
        ? 'bg-amber-400'
        : 'bg-muted-foreground/25';

  // Sub-label: what to show depends on grouping context
  // - grouped by mode (kind): show agent name, since kind is already the group header
  // - grouped by agent: show kind label + schedule, since agent is already the group header
  const agentName = agentNameFor(task, agents);
  const kindLabel = KIND_GROUP_LABEL[task.output_kind ?? ''] ?? null;

  const subLeft = groupBy === 'agent'
    ? kindLabel          // agent already shown in group header
    : agentName;         // kind already shown in group header

  const schedule = task.schedule
    ? task.schedule.charAt(0).toUpperCase() + task.schedule.slice(1)
    : null;

  // Right-side time signal — the most scan-relevant piece
  const timeSignal = isActive && task.next_run_at
    ? `Next: ${formatRelativeTime(task.next_run_at)}`
    : task.last_run_at
      ? `Last: ${formatRelativeTime(task.last_run_at)}`
      : null;

  return (
    <button
      onClick={onSelect}
      className={cn(
        'w-full text-left px-4 py-3 hover:bg-muted/30 transition-colors flex items-center gap-3',
        dim && 'opacity-40',
      )}
    >
      {/* Status dot */}
      <div className={cn('w-1.5 h-1.5 rounded-full shrink-0', statusColor)} />

      {/* Title + sub-label */}
      <div className="flex-1 min-w-0">
        <p className={cn('text-sm truncate', dim ? 'text-muted-foreground' : 'text-foreground font-medium')}>
          {task.title}
        </p>
        <div className="flex items-center gap-1.5 mt-0.5">
          {/* Mode badge only when grouped by agent (kind not in group header) */}
          {groupBy === 'agent' && !dim && (
            <WorkModeBadge mode={task.mode} />
          )}
          {subLeft && (
            <span className="text-[11px] text-muted-foreground/70 truncate">{subLeft}</span>
          )}
          {schedule && (
            <>
              <span className="text-muted-foreground/25 text-[11px]">·</span>
              <span className="text-[11px] text-muted-foreground/50">{schedule}</span>
            </>
          )}
        </div>
      </div>

      {/* Time signal — primary scan target */}
      {timeSignal && (
        <span className="text-xs text-muted-foreground/60 shrink-0 tabular-nums">
          {timeSignal}
        </span>
      )}
    </button>
  );
}

// ─── Empty state ─────────────────────────────────────────────────────────────

function EmptyResult({ hasFilters }: { hasFilters: boolean }) {
  return (
    <div className="flex items-center justify-center h-full min-h-[200px]">
      <div className="text-center">
        <Sparkles className="w-5 h-5 text-muted-foreground/20 mx-auto mb-2" />
        <p className="text-sm font-medium mb-1">
          {hasFilters ? 'No tasks match' : 'No tasks yet'}
        </p>
        <p className="text-xs text-muted-foreground">
          {hasFilters ? 'Clear filters to see all work.' : 'Chat with TP to set up your first task.'}
        </p>
      </div>
    </div>
  );
}
