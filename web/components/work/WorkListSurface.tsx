'use client';

/**
 * WorkListSurface — Full-width list surface for /work.
 *
 * Six tabs (ADR-243 folded into Work; Schedule page deleted):
 *
 *   Dashboard  — cockpit kernel (Mandate · Money truth · Performance · Tracking)
 *   My Work    — user's knowledge work, grouped by output kind (Reports / Tracking / Actions)
 *   Schedule   — cadence-grouped view (Recurring / Reactive / One-time); replaces /schedule page
 *   Connectors — platform-bound tasks, grouped by platform
 *   System     — system_maintenance tasks, flat list
 *   Decisions  — Reviewer decisions stream (/workspace/review/decisions.md)
 *
 * Cockpit content (formerly always-visible above the list) is now the
 * Dashboard tab — opt-in, no longer forced above every list view.
 *
 * /schedule route is a redirect stub → /work (same row data, cadence framing).
 */

import { useRef, useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  CalendarClock,
  Database,
  FileText,
  LayoutDashboard,
  Link2,
  MoreHorizontal,
  Scale,
  Search,
  Send,
  Settings2,
  Sparkles,
  X,
} from 'lucide-react';
// ADR-241 D3: Decisions Stream relocated from /agents to /work
import { DecisionsStream } from './details/DecisionsStream';
import { cn } from '@/lib/utils';
import { formatRelativeTime } from '@/lib/formatting';
import { getAgentSlug } from '@/lib/agent-identity';
import { recurrenceLabel } from '@/types';
import {
  cadenceCategory,
  humanizeSchedule,
  CADENCE_ORDER,
  CADENCE_LABELS,
  type CadenceCategory,
} from '@/lib/schedule';
import type { Recurrence, Agent, NarrativeByTaskSlice } from '@/types';
// ADR-225 Phase 2: bundle-supplied list-mode banner
import { BundleBanner } from '@/components/library/BundleBanner';
// ADR-225 Phase 3: bundle-supplied pinned tasks float to top of their group
import { useComposition, getTab } from '@/lib/compositor';

interface WorkListSurfaceProps {
  tasks: Recurrence[];
  agents: Agent[];
  /**
   * ADR-219 Commit 4: narrative slices keyed by task slug. Source for
   * recent-activity headlines on the list rows, replacing the legacy
   * `task.last_run_at` timestamp.
   */
  narrativeByTask: Map<string, NarrativeByTaskSlice>;
  agentFilter: string | null;
  dataError?: string | null;
  /** Cockpit content rendered inside the Dashboard tab. */
  cockpitSlot?: ReactNode;
  onClearAgentFilter: () => void;
  onSelect: (slug: string) => void;
}

// ADR-241 D3: 'decisions' tab added — surfaces /workspace/review/decisions.md
type WorkTab = 'dashboard' | 'my-work' | 'schedule' | 'connectors' | 'system' | 'decisions';

// ─── Classification helpers ──────────────────────────────────────────────────

// Platform-bound recurrences — shown under "Connectors" not "My Work."
const CONNECTOR_TYPE_KEYS = new Set([
  'slack-digest',
  'notion-digest',
  'github-digest',
  'slack-respond',
  'notion-update',
  'commerce-digest',
  'revenue-report',
  'track-universe',
  'trade-proposal',
]);

function isConnectorTask(task: Recurrence): boolean {
  return CONNECTOR_TYPE_KEYS.has(task.slug);
}

function isSystemTask(task: Recurrence): boolean {
  return task.output_kind === 'system_maintenance';
}

function isMyWorkTask(task: Recurrence): boolean {
  return !isConnectorTask(task) && !isSystemTask(task);
}

// output_kind → icon component
const KIND_ICON: Record<string, React.ElementType> = {
  produces_deliverable: FileText,
  accumulates_context: Database,
  external_action: Send,
  system_maintenance: Settings2,
};

// ─── My Work grouping (output kind) ─────────────────────────────────────────

const OUTPUT_KIND_LABELS: Record<string, string> = {
  accumulates_context: 'Tracking',
  produces_deliverable: 'Reports',
  external_action: 'Actions',
};

function myWorkGroup(task: Recurrence): string {
  return OUTPUT_KIND_LABELS[task.output_kind ?? ''] ?? 'Reports';
}

const MY_WORK_GROUP_ORDER = ['Reports', 'Tracking', 'Actions'];

// ─── Connector grouping (by platform) ────────────────────────────────────────

function connectorPlatform(task: Recurrence): string {
  const key = task.slug ?? '';
  if (key.startsWith('slack')) return 'Slack';
  if (key.startsWith('notion')) return 'Notion';
  if (key.startsWith('github')) return 'GitHub';
  if (key.startsWith('commerce') || key.startsWith('revenue')) return 'Commerce';
  if (key.startsWith('trading') || key.startsWith('portfolio')) return 'Trading';
  return 'Other';
}

const CONNECTOR_GROUP_ORDER = ['Slack', 'Notion', 'GitHub', 'Commerce', 'Trading', 'Other'];

// ─── Sorting ─────────────────────────────────────────────────────────────────

function statusRank(status: string | undefined): number {
  switch (status) {
    case 'active':    return 0;
    case 'paused':    return 1;
    case 'completed': return 2;
    case 'archived':  return 3;
    default:          return 4;
  }
}

function compareTasks(a: Recurrence, b: Recurrence): number {
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

function compareGroups(order: string[], a: string, b: string): number {
  const ai = order.indexOf(a);
  const bi = order.indexOf(b);
  if (ai !== -1 || bi !== -1) {
    return (ai === -1 ? order.length : ai) - (bi === -1 ? order.length : bi);
  }
  return a.localeCompare(b);
}

// ─── Search helpers ──────────────────────────────────────────────────────────

function agentNamesFor(task: Recurrence, agents: Agent[]): string[] {
  if (!task.agent_slugs?.length) return [];
  return task.agent_slugs.map(slug => {
    const agent = agents.find(a => getAgentSlug(a) === slug);
    return agent?.title ?? slug;
  });
}

function buildSearchText(task: Recurrence, agents: Agent[]): string {
  const obj = task.objective
    ? [task.objective.deliverable, task.objective.audience, task.objective.purpose, task.objective.format]
    : [];
  return [
    task.title,
    ...agentNamesFor(task, agents),
    task.slug,
    task.shape,
    task.delivery,
    task.schedule,
    ...(task.context_reads ?? []),
    ...(task.context_writes ?? []),
    ...obj,
  ].filter(Boolean).join(' ').toLowerCase();
}

// ─── Overflow menu ───────────────────────────────────────────────────────────

function OverflowOptions({
  includeHistorical,
  onToggleHistorical,
}: {
  includeHistorical: boolean;
  onToggleHistorical: () => void;
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

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(o => !o)}
        className={cn(
          'inline-flex items-center justify-center w-7 h-7 rounded border transition-colors',
          includeHistorical
            ? 'border-primary/40 text-primary bg-primary/5'
            : 'border-border/60 text-muted-foreground hover:text-foreground hover:bg-muted',
        )}
        aria-label="More filters"
      >
        <MoreHorizontal className="w-3.5 h-3.5" />
        {includeHistorical && (
          <span className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-primary text-[8px] text-primary-foreground flex items-center justify-center font-medium">
            1
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 z-20 min-w-[220px] rounded-md border border-border bg-popover shadow-md py-1">
          <label className="flex items-center gap-2.5 px-3 py-2 text-xs text-muted-foreground hover:text-foreground hover:bg-muted cursor-pointer">
            <input
              type="checkbox"
              checked={includeHistorical}
              onChange={onToggleHistorical}
              className="rounded border-border"
            />
            Include completed &amp; archived
          </label>
        </div>
      )}
    </div>
  );
}

// ─── Main ────────────────────────────────────────────────────────────────────

export function WorkListSurface({
  tasks,
  agents,
  narrativeByTask,
  agentFilter,
  dataError,
  cockpitSlot,
  onClearAgentFilter,
  onSelect,
}: WorkListSurfaceProps) {
  const [activeTab, setActiveTab] = useState<WorkTab>('my-work');
  const [search, setSearch] = useState('');
  const [includeHistorical, setIncludeHistorical] = useState(false);

  // ── Partition tasks into tabs ──
  const { myWork, connectors, system } = useMemo(() => {
    const base = includeHistorical
      ? tasks
      : tasks.filter(t => t.status !== 'archived' && t.status !== 'completed');

    return {
      myWork: base.filter(isMyWorkTask),
      connectors: base.filter(isConnectorTask),
      system: base.filter(isSystemTask),
    };
  }, [tasks, includeHistorical]);

  // ── Schedule tab: all non-archived recurrences, cadence-grouped ──
  const scheduleRecurrences = useMemo(() => {
    return tasks.filter(t => t.status !== 'archived');
  }, [tasks]);

  // ── Active task list for the selected tab (Dashboard/Schedule/Decisions handled separately) ──
  const tabTasks = activeTab === 'my-work'
    ? myWork
    : activeTab === 'connectors'
      ? connectors
      : activeTab === 'system'
        ? system
        : [];

  const filtered = useMemo(() => {
    let result = tabTasks;
    if (agentFilter) {
      result = result.filter(t => t.agent_slugs?.includes(agentFilter));
    }
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      result = result.filter(t => buildSearchText(t, agents).includes(q));
    }
    return result;
  }, [tabTasks, agentFilter, search, agents]);

  // ── ADR-225 Phase 3: bundle-supplied pinned tasks ──
  const { data: composition } = useComposition();
  const pinnedSlugs = useMemo(() => {
    const list = getTab(composition.composition, 'work').list?.pinned_tasks ?? [];
    return new Set(list);
  }, [composition]);
  const pinnedOrder = useMemo(() => {
    const list = getTab(composition.composition, 'work').list?.pinned_tasks ?? [];
    const map = new Map<string, number>();
    list.forEach((slug, idx) => map.set(slug, idx));
    return map;
  }, [composition]);

  // ── Group by tab-specific logic ──
  const grouped = useMemo(() => {
    const groups: Record<string, Recurrence[]> = {};

    for (const task of filtered) {
      let key: string;
      if (activeTab === 'my-work') {
        key = myWorkGroup(task);
      } else if (activeTab === 'connectors') {
        key = connectorPlatform(task);
      } else {
        key = 'System';
      }
      if (!groups[key]) groups[key] = [];
      groups[key].push(task);
    }

    for (const key of Object.keys(groups)) {
      groups[key].sort((a, b) => {
        const aPinned = pinnedSlugs.has(a.slug);
        const bPinned = pinnedSlugs.has(b.slug);
        if (aPinned && !bPinned) return -1;
        if (!aPinned && bPinned) return 1;
        if (aPinned && bPinned) {
          return (pinnedOrder.get(a.slug) ?? 0) - (pinnedOrder.get(b.slug) ?? 0);
        }
        return compareTasks(a, b);
      });
    }

    const order = activeTab === 'my-work'
      ? MY_WORK_GROUP_ORDER
      : activeTab === 'connectors'
        ? CONNECTOR_GROUP_ORDER
        : ['System'];

    return Object.entries(groups).sort((a, b) => compareGroups(order, a[0], b[0]));
  }, [filtered, activeTab, pinnedSlugs, pinnedOrder]);

  const agentLabel = agentFilter
    ? agents.find(a => getAgentSlug(a) === agentFilter)?.title ?? agentFilter
    : null;

  const flattenMyWork = activeTab === 'my-work' && grouped.length <= 1;

  // Search/filter UI is hidden on substrate-driven tabs (Dashboard, Schedule, Decisions)
  const isListTab = activeTab === 'my-work' || activeTab === 'connectors' || activeTab === 'system';

  const tabs: { id: WorkTab; label: string; count: number; icon: React.ElementType }[] = [
    { id: 'dashboard', label: 'Dashboard', count: 0, icon: LayoutDashboard },
    { id: 'my-work', label: 'My Work', count: myWork.length, icon: FileText },
    { id: 'schedule', label: 'Schedule', count: 0, icon: CalendarClock },
    { id: 'connectors', label: 'Connectors', count: connectors.length, icon: Link2 },
    { id: 'system', label: 'System', count: system.length, icon: Settings2 },
    { id: 'decisions', label: 'Decisions', count: 0, icon: Scale },
  ];

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-baseline justify-between px-4 sm:px-6 pt-5 pb-2 shrink-0">
        <h2 className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground/70">
          Work
        </h2>
        <span className="text-[10px] text-muted-foreground/40">
          dashboard · my work · schedule · connectors · system
        </span>
      </div>

      {/* ADR-225 Phase 2: bundle-supplied phase-aware banner */}
      <BundleBanner tab="work" />

      {/* ── Toolbar ── */}
      <div className="px-4 sm:px-6 pb-3 border-b border-border/40 shrink-0 space-y-3">
        {dataError && (
          <div className="rounded-md border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-[11px] text-amber-700">
            Showing last available data — refresh to retry.
          </div>
        )}

        {/* Tab row */}
        <div className="flex items-center gap-1 flex-wrap">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors',
                activeTab === tab.id
                  ? 'bg-foreground text-background'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted/60',
              )}
            >
              <tab.icon className="w-3 h-3" />
              {tab.label}
              {tab.count > 0 && (
                <span className={cn(
                  'ml-0.5 min-w-[16px] h-4 rounded-full text-[10px] font-medium inline-flex items-center justify-center px-1',
                  activeTab === tab.id
                    ? 'bg-background/20 text-background'
                    : 'bg-muted text-muted-foreground',
                )}>
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Search + agent filter + overflow — only on list tabs */}
        {isListTab && (
          <div className="flex items-center gap-2">
            <div className="relative flex-1 min-w-0">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/40" />
              <input
                type="text"
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search..."
                className="w-full pl-8 pr-3 py-1.5 text-xs bg-muted/40 border border-border/60 rounded-md focus:outline-none focus:ring-1 focus:ring-ring focus:border-ring"
              />
            </div>

            {agentFilter && (
              <button
                onClick={onClearAgentFilter}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md bg-primary/10 text-primary text-xs hover:bg-primary/20 transition-colors shrink-0"
              >
                {agentLabel}
                <X className="w-3 h-3" />
              </button>
            )}

            <OverflowOptions
              includeHistorical={includeHistorical}
              onToggleHistorical={() => setIncludeHistorical(v => !v)}
            />
          </div>
        )}
      </div>

      {/* ── Tab body ── */}
      <div className="flex-1 overflow-auto">

        {/* Dashboard — cockpit kernel (Mandate · Money truth · Performance · Tracking) */}
        {activeTab === 'dashboard' && (
          <div className="h-full">
            {cockpitSlot ?? (
              <div className="flex items-center justify-center h-full min-h-[200px] px-4">
                <div className="text-center max-w-sm">
                  <LayoutDashboard className="w-6 h-6 text-muted-foreground/25 mx-auto mb-3" />
                  <p className="text-sm font-medium mb-1.5">No dashboard yet</p>
                  <p className="text-xs text-muted-foreground">The operational dashboard will appear here once your workspace is set up.</p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Schedule — cadence-grouped (Recurring / Reactive / One-time) */}
        {activeTab === 'schedule' && (
          <ScheduleTabContent recurrences={scheduleRecurrences} onSelect={onSelect} />
        )}

        {/* Decisions — substrate-driven stream */}
        {activeTab === 'decisions' && (
          <div className="px-4 sm:px-6 py-4 max-w-4xl">
            <DecisionsStream />
          </div>
        )}

        {/* List tabs: my-work / connectors / system */}
        {isListTab && (
          filtered.length === 0 ? (
            <EmptyResult tab={activeTab} hasFilters={!!search || !!agentFilter} />
          ) : (
            <div className="px-4 sm:px-6 py-4 space-y-6 max-w-4xl">
              {grouped.map(([groupName, items]) => (
                <section key={groupName}>
                  {!flattenMyWork && (
                    <div className="flex items-center gap-2 mb-2 px-1">
                      <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                        {groupName}
                      </span>
                      <span className="text-[11px] text-muted-foreground/40">{items.length}</span>
                      <div className="flex-1 border-t border-border/30" />
                    </div>
                  )}
                  <div className="space-y-1">
                    {items.map(task => (
                      <WorkRow
                        key={task.slug}
                        task={task}
                        agents={agents}
                        narrativeSlice={narrativeByTask.get(task.slug) ?? null}
                        tab={activeTab}
                        isPinned={pinnedSlugs.has(task.slug)}
                        onSelect={() => onSelect(task.slug)}
                      />
                    ))}
                  </div>
                </section>
              ))}
            </div>
          )
        )}
      </div>
    </div>
  );
}

// ─── Schedule tab content ─────────────────────────────────────────────────────

function ScheduleTabContent({
  recurrences,
  onSelect,
}: {
  recurrences: Recurrence[];
  onSelect: (slug: string) => void;
}) {
  const grouped = useMemo(() => {
    const buckets: Record<CadenceCategory, Recurrence[]> = {
      recurring: [],
      reactive: [],
      'one-time': [],
    };
    for (const r of recurrences) {
      buckets[cadenceCategory(r)].push(r);
    }
    return CADENCE_ORDER
      .map(key => ({
        key,
        label: CADENCE_LABELS[key],
        items: buckets[key],
      }))
      .filter(g => g.items.length > 0);
  }, [recurrences]);

  if (grouped.length === 0) {
    return (
      <div className="flex items-center justify-center h-full min-h-[200px] px-4">
        <div className="text-center max-w-sm">
          <CalendarClock className="w-6 h-6 text-muted-foreground/25 mx-auto mb-3" />
          <p className="text-sm font-medium mb-1.5">Nothing scheduled</p>
          <p className="text-xs text-muted-foreground">
            Tell YARNNN what you want done and on what cadence.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="px-4 sm:px-6 py-4 max-w-4xl space-y-6">
      {grouped.map(group => (
        <section key={group.key}>
          <header className="mb-2 px-1">
            <h3 className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
              {group.label.title}
              <span className="ml-2 text-[11px] font-normal text-muted-foreground/40">
                {group.items.length}
              </span>
            </h3>
            <p className="text-[11px] text-muted-foreground/60 mt-0.5">
              {group.label.description}
            </p>
          </header>
          <div className="space-y-1">
            {group.items.map(r => (
              <ScheduleRow key={r.id} recurrence={r} category={cadenceCategory(r)} onSelect={onSelect} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function ScheduleRow({
  recurrence,
  category,
  onSelect,
}: {
  recurrence: Recurrence;
  category: CadenceCategory;
  onSelect: (slug: string) => void;
}) {
  const cadenceText =
    category === 'recurring'
      ? humanizeSchedule(recurrence.schedule)
      : category === 'reactive'
        ? 'On event'
        : 'One-time';

  const isPaused = recurrence.paused === true;
  const isCompleted = recurrence.status === 'completed';
  const dotColor = isPaused
    ? 'bg-amber-500'
    : isCompleted
      ? 'bg-muted-foreground/40'
      : 'bg-emerald-500';

  return (
    <button
      onClick={() => onSelect(recurrence.slug)}
      className={cn(
        'w-full text-left px-3 py-2.5 rounded-lg hover:bg-muted/40 transition-colors flex items-center gap-3',
        isPaused && 'opacity-60',
      )}
    >
      <span className={cn('h-2 w-2 rounded-full shrink-0', dotColor)} />
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium truncate">{recurrence.title}</div>
        <div className="text-[11px] text-muted-foreground/60 mt-0.5 truncate">
          {cadenceText}
        </div>
      </div>
      <div className="text-[11px] text-muted-foreground/50 shrink-0 text-right tabular-nums">
        {recurrence.next_run_at ? (
          <>Next {formatRelativeTime(recurrence.next_run_at)}</>
        ) : recurrence.last_run_at ? (
          <>Last {formatRelativeTime(recurrence.last_run_at)}</>
        ) : (
          <span className="text-muted-foreground/40 italic">Not yet run</span>
        )}
      </div>
    </button>
  );
}

// ─── Work row ─────────────────────────────────────────────────────────────────

function WorkRow({
  task,
  agents,
  narrativeSlice,
  tab,
  isPinned,
  onSelect,
}: {
  task: Recurrence;
  agents: Agent[];
  narrativeSlice: NarrativeByTaskSlice | null;
  tab: WorkTab;
  isPinned: boolean;
  onSelect: () => void;
}) {
  const isActive = task.status === 'active';
  const isPaused = task.paused === true;
  const dim = tab === 'system';

  const KindIcon = KIND_ICON[task.output_kind ?? ''] ?? FileText;

  const dotColor = dim
    ? 'bg-muted-foreground/20'
    : isActive
      ? 'bg-emerald-500'
      : isPaused
        ? 'bg-amber-400'
        : 'bg-muted-foreground/20';

  const assignedAgents = agentNamesFor(task, agents);

  const schedule = task.schedule
    ? task.schedule.charAt(0).toUpperCase() + task.schedule.slice(1)
    : null;

  const lastMaterial = narrativeSlice?.last_material ?? null;
  const timeSignal = isActive && task.next_run_at
    ? `Next: ${formatRelativeTime(task.next_run_at)}`
    : lastMaterial
      ? `${formatRelativeTime(lastMaterial.created_at)}`
      : null;
  const headlineSummary = !isActive && lastMaterial ? lastMaterial.summary : null;

  const subParts: string[] = schedule ? [schedule] : [];

  return (
    <button
      onClick={onSelect}
      className={cn(
        'w-full text-left px-3 py-2.5 rounded-lg hover:bg-muted/40 transition-colors flex items-center gap-3 group',
        dim && 'opacity-50',
      )}
    >
      <div className="relative shrink-0 flex items-center justify-center w-8 h-8 rounded-md bg-muted/50 group-hover:bg-muted/80 transition-colors">
        <KindIcon className={cn('w-3.5 h-3.5', dim ? 'text-muted-foreground/40' : 'text-muted-foreground')} />
        {(isActive || isPaused) && !dim && (
          <div className={cn('absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full ring-2 ring-background', dotColor)} />
        )}
      </div>

      <div className="flex-1 min-w-0">
        <p className={cn('text-sm truncate flex items-center gap-1.5', dim ? 'text-muted-foreground' : 'font-medium')}>
          {isPinned && (
            <span
              className="text-primary/60 text-[10px] leading-none"
              aria-label="Pinned by program bundle"
              title="Pinned by program bundle"
            >
              ●
            </span>
          )}
          <span className="truncate">{task.title}</span>
        </p>
        <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
          {subParts.map((part, i) => (
            <span key={i} className="text-[11px] text-muted-foreground/50">
              {i > 0 && <span className="mr-1.5">·</span>}
              {part}
            </span>
          ))}
          {assignedAgents.length > 0 && (
            <>
              {subParts.length > 0 && <span className="text-[11px] text-muted-foreground/30">·</span>}
              <span className="text-[11px] text-muted-foreground/40 truncate">
                {assignedAgents.join(', ')}
              </span>
            </>
          )}
        </div>
        {headlineSummary && (
          <p className="text-[11px] text-muted-foreground/60 truncate mt-0.5 italic">
            {headlineSummary}
          </p>
        )}
      </div>

      {timeSignal && (
        <span className="text-[11px] text-muted-foreground/50 shrink-0 tabular-nums">
          {timeSignal}
        </span>
      )}
    </button>
  );
}

// ─── Empty states ─────────────────────────────────────────────────────────────

function EmptyResult({ tab, hasFilters }: { tab: WorkTab; hasFilters: boolean }) {
  const messages: Partial<Record<WorkTab, { icon: React.ElementType; title: string; sub: string; cta?: { label: string; href: string } }>> = {
    'my-work': {
      icon: Sparkles,
      title: hasFilters ? 'No tasks match' : 'No tasks yet',
      sub: hasFilters
        ? 'Clear filters to see all work.'
        : 'Describe your work to YARNNN. Create the tasks that do it.',
      cta: hasFilters ? undefined : { label: 'Talk to YARNNN', href: '/chat' },
    },
    connectors: {
      icon: Link2,
      title: hasFilters ? 'No connector tasks match' : 'No connectors active',
      sub: hasFilters
        ? 'Clear filters to see all connector tasks.'
        : 'Connect a platform in Settings to get started.',
    },
    system: {
      icon: Settings2,
      title: 'No system tasks',
      sub: 'System tasks are created automatically.',
    },
  };

  const msg = messages[tab];
  if (!msg) return null;
  const Icon = msg.icon;

  return (
    <div className="flex items-center justify-center h-full min-h-[200px] px-4">
      <div className="text-center max-w-sm">
        <Icon className="w-6 h-6 text-muted-foreground/25 mx-auto mb-3" />
        <p className="text-sm font-medium mb-1.5">{msg.title}</p>
        <p className="text-xs text-muted-foreground mb-4">{msg.sub}</p>
        {msg.cta && (
          <a
            href={msg.cta.href}
            className="inline-flex items-center gap-2 rounded-md bg-foreground px-3.5 py-1.5 text-xs font-medium text-background hover:bg-foreground/90 transition-colors"
          >
            {msg.cta.label}
          </a>
        )}
      </div>
    </div>
  );
}
