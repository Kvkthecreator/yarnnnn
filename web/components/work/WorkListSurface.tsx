'use client';

/**
 * WorkListSurface — Full-width list surface for /work (ADR-167).
 *
 * Replaces the old left-sidebar WorkList. This is what you see when you land
 * on /work with no `?task=` param: a filterable, groupable list of every task
 * in your workspace.
 *
 * Features:
 *   - Filter chips on output_kind: All | Tracking | Reports | Actions | System
 *   - Search box across title, agent, delivery, type, objective, domains
 *   - Group-by dropdown: Output kind (default) | Agent | Status | Schedule
 *   - Status filter: active+paused (default), optional completed+archived
 *   - Agent filter: pre-applied if `?agent={slug}` is in URL; user can clear
 *
 * Click a row → onSelect(slug) → page transitions to detail mode by updating
 * the URL to `?task={slug}`.
 */

import { useMemo, useState } from 'react';
import { Circle, Search, Sparkles, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatRelativeTime } from '@/lib/formatting';
import { WorkModeBadge } from './WorkModeBadge';
import { getAgentSlug } from '@/lib/agent-identity';
import type { Task, Agent } from '@/types';

interface WorkListSurfaceProps {
  tasks: Task[];
  agents: Agent[];
  /** Pre-applied agent filter from URL `?agent={slug}` (or null) */
  agentFilter: string | null;
  /** Non-fatal data loading error when stale list data is still available */
  dataError?: string | null;
  /** Called when user clears the agent filter via the chip */
  onClearAgentFilter: () => void;
  onSelect: (slug: string) => void;
}

type KindFilter = 'all' | 'accumulates_context' | 'produces_deliverable' | 'external_action' | 'system_maintenance';
type GroupBy = 'output_kind' | 'agent' | 'status' | 'schedule';

const KIND_CHIPS: { id: KindFilter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'accumulates_context', label: 'Tracking' },
  { id: 'produces_deliverable', label: 'Reports' },
  { id: 'external_action', label: 'Actions' },
  { id: 'system_maintenance', label: 'System' },
];

const KIND_LABEL: Record<string, string> = {
  accumulates_context: 'Tracking',
  produces_deliverable: 'Reports',
  external_action: 'Actions',
  system_maintenance: 'System',
};

const GROUP_BY_LABEL: Record<GroupBy, string> = {
  output_kind: 'Output kind',
  agent: 'Agent',
  status: 'Status',
  schedule: 'Schedule',
};

const STATUS_LABEL: Record<string, string> = {
  active: 'Active',
  paused: 'Paused',
  completed: 'Completed',
  archived: 'Archived',
};

const GROUP_ORDER: Record<GroupBy, string[]> = {
  output_kind: ['Tracking', 'Reports', 'Actions', 'System', 'Other'],
  agent: [],
  status: ['Active', 'Paused', 'Completed', 'Archived', 'Unknown'],
  schedule: [],
};

function agentNameFor(task: Task, agents: Agent[]): string {
  const assigned = task.agent_slugs?.[0];
  if (!assigned) return 'Unassigned';
  // Use getAgentSlug() — agent.slug may not be populated from API response
  const agent = agents.find(a => getAgentSlug(a) === assigned);
  return agent?.title ?? assigned;
}

function statusRank(status: string | undefined): number {
  switch (status) {
    case 'active':
      return 0;
    case 'paused':
      return 1;
    case 'completed':
      return 2;
    case 'archived':
      return 3;
    default:
      return 4;
  }
}

function groupKeyFor(task: Task, groupBy: GroupBy, agents: Agent[]): string {
  switch (groupBy) {
    case 'output_kind':
      return KIND_LABEL[task.output_kind ?? ''] ?? 'Other';
    case 'agent':
      return agentNameFor(task, agents);
    case 'status':
      return STATUS_LABEL[task.status] ?? 'Unknown';
    case 'schedule':
      return task.schedule || 'On-demand';
  }
}

function compareTasks(a: Task, b: Task): number {
  const statusDiff = statusRank(a.status) - statusRank(b.status);
  if (statusDiff !== 0) return statusDiff;

  const aNext = a.next_run_at ? new Date(a.next_run_at).getTime() : Number.POSITIVE_INFINITY;
  const bNext = b.next_run_at ? new Date(b.next_run_at).getTime() : Number.POSITIVE_INFINITY;
  if (a.status === 'active' || a.status === 'paused' || b.status === 'active' || b.status === 'paused') {
    if (aNext !== bNext) return aNext - bNext;
  }

  const aLast = a.last_run_at ? new Date(a.last_run_at).getTime() : 0;
  const bLast = b.last_run_at ? new Date(b.last_run_at).getTime() : 0;
  if (aLast !== bLast) return bLast - aLast;

  return a.title.localeCompare(b.title);
}

function buildSearchText(task: Task, agents: Agent[]): string {
  const objective = task.objective
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
    ...objective,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
}

function compareGroups(groupBy: GroupBy, a: string, b: string): number {
  const explicitOrder = GROUP_ORDER[groupBy];
  if (explicitOrder.length > 0) {
    const aIndex = explicitOrder.indexOf(a);
    const bIndex = explicitOrder.indexOf(b);
    if (aIndex !== -1 || bIndex !== -1) {
      return (aIndex === -1 ? explicitOrder.length : aIndex) - (bIndex === -1 ? explicitOrder.length : bIndex);
    }
  }
  return a.localeCompare(b);
}

export function WorkListSurface({
  tasks,
  agents,
  agentFilter,
  dataError,
  onClearAgentFilter,
  onSelect,
}: WorkListSurfaceProps) {
  const [kindFilter, setKindFilter] = useState<KindFilter>('all');
  const [search, setSearch] = useState('');
  const [groupBy, setGroupBy] = useState<GroupBy>('output_kind');
  const [includeHistorical, setIncludeHistorical] = useState(false);

  // Apply filters in pipeline order
  const filtered = useMemo(() => {
    let result = tasks;
    if (!includeHistorical) {
      result = result.filter(t => t.status !== 'archived' && t.status !== 'completed');
    }
    if (kindFilter !== 'all') {
      result = result.filter(t => t.output_kind === kindFilter);
    }
    if (agentFilter) {
      result = result.filter(t => t.agent_slugs?.includes(agentFilter));
    }
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      result = result.filter(t => buildSearchText(t, agents).includes(q));
    }
    return result;
  }, [tasks, kindFilter, agentFilter, search, includeHistorical, agents]);

  // Group + sort within each group
  const grouped = useMemo(() => {
    const groups: Record<string, Task[]> = {};
    for (const task of filtered) {
      const key = groupKeyFor(task, groupBy, agents);
      if (!groups[key]) groups[key] = [];
      groups[key].push(task);
    }
    // Sort tasks within each group: active/paused first, upcoming first, then recent history.
    for (const key of Object.keys(groups)) {
      groups[key].sort(compareTasks);
    }
    return Object.entries(groups).sort((a, b) => compareGroups(groupBy, a[0], b[0]));
  }, [filtered, groupBy, agents]);

  const agentLabel = agentFilter
    ? agents.find(a => getAgentSlug(a) === agentFilter)?.title ?? agentFilter
    : null;

  return (
    <div className="flex flex-col h-full">
      {/* ── Header: filters + search + group-by ── */}
      <div className="px-6 py-4 border-b border-border/60 shrink-0 space-y-3">
        {dataError && (
          <div className="rounded-md border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-[11px] text-amber-700">
            Showing the last available work index. Refresh the page to retry the failed background load.
          </div>
        )}

        {/* Kind chips */}
        <div className="flex items-center gap-1 flex-wrap">
          {KIND_CHIPS.map(chip => {
            const isActive = kindFilter === chip.id;
            return (
              <button
                key={chip.id}
                onClick={() => setKindFilter(chip.id)}
                className={cn(
                  'px-3 py-1 rounded-full text-xs font-medium transition-colors',
                  isActive
                    ? 'bg-foreground text-background'
                    : 'bg-muted/60 text-muted-foreground hover:bg-muted',
                )}
              >
                {chip.label}
              </button>
            );
          })}
        </div>

        {/* Search + group-by + agent filter chip */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="relative flex-1 min-w-[200px] max-w-md">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/40" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search tasks, agents, domains..."
              className="w-full pl-7 pr-3 py-1.5 text-xs bg-muted/40 border border-border/60 rounded-md focus:outline-none focus:ring-1 focus:ring-ring focus:border-ring"
            />
          </div>

          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-muted-foreground/60">Group by:</span>
            <select
              value={groupBy}
              onChange={e => setGroupBy(e.target.value as GroupBy)}
              className="bg-muted/40 border border-border/60 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
            >
              {(Object.entries(GROUP_BY_LABEL) as [GroupBy, string][]).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>

          <label className="flex items-center gap-1.5 text-[11px] text-muted-foreground cursor-pointer">
            <input
              type="checkbox"
              checked={includeHistorical}
              onChange={e => setIncludeHistorical(e.target.checked)}
              className="rounded border-border"
            />
            Include completed and archived
          </label>

          {agentFilter && (
            <button
              onClick={onClearAgentFilter}
              className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-primary/10 text-primary text-[11px] hover:bg-primary/20"
            >
              Agent: {agentLabel}
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      {/* ── List body ── */}
      <div className="flex-1 overflow-auto">
        {filtered.length === 0 ? (
          <EmptyResult hasFilters={kindFilter !== 'all' || !!search || !!agentFilter || includeHistorical} />
        ) : (
          <div className="px-6 py-4 space-y-6 max-w-5xl">
            {grouped.map(([groupName, items]) => (
              <section key={groupName}>
                <h3 className="text-[11px] font-medium text-muted-foreground/60 mb-2">
                  {groupName} <span className="text-muted-foreground/30 normal-case">· {items.length}</span>
                </h3>
                <div className="rounded-md border border-border/60 divide-y divide-border/40 overflow-hidden">
                  {items.map(task => (
                    <WorkRow
                      key={task.slug}
                      task={task}
                      agentName={agentNameFor(task, agents)}
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

// ─── Row ───

function WorkRow({
  task,
  agentName,
  onSelect,
}: {
  task: Task;
  agentName: string;
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
      className="w-full text-left px-4 py-3 hover:bg-muted/40 transition-colors flex items-center gap-3"
    >
      <Circle className={cn('w-2 h-2 shrink-0', statusColor)} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium truncate">{task.title}</span>
        </div>
        <div className="flex items-center gap-1.5 mt-0.5 text-[11px] text-muted-foreground">
          <WorkModeBadge mode={task.mode} />
          <span className="truncate">{agentName}</span>
          {task.schedule && (
            <>
              <span className="text-muted-foreground/30">·</span>
              <span className="capitalize">{task.schedule}</span>
            </>
          )}
        </div>
      </div>
      <div className="text-[10px] text-muted-foreground/70 shrink-0 text-right">
        {isActive && task.next_run_at && <div>Next: {formatRelativeTime(task.next_run_at)}</div>}
        {!isActive && task.last_run_at && <div>Last: {formatRelativeTime(task.last_run_at)}</div>}
      </div>
    </button>
  );
}

// ─── Empty state ───

function EmptyResult({ hasFilters }: { hasFilters: boolean }) {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <Sparkles className="w-6 h-6 text-muted-foreground/20 mx-auto mb-2" />
        <p className="text-sm font-medium mb-1">
          {hasFilters ? 'No tasks match your filters' : 'No tasks yet'}
        </p>
        <p className="text-xs text-muted-foreground">
          {hasFilters
            ? 'Try clearing filters or searching differently.'
            : 'Chat with TP to set up your first task.'}
        </p>
      </div>
    </div>
  );
}
