'use client';

/**
 * WorkListSurface — Full-width list surface for /work.
 *
 * SURFACE-ARCHITECTURE.md v13.0 — three-tab architecture.
 *
 * Three tabs:
 *   My Work (default) — user's knowledge work, grouped by output kind
 *     (Reports / Tracking / Actions). Cadence badge (Recurring / One-time)
 *     on each row.
 *   Connectors — platform-bound tasks (requires_platform), grouped by platform
 *   System — system_maintenance tasks, flat list
 *
 * Search is preserved within each tab.
 */

import { useRef, useEffect, useMemo, useState } from 'react';
import {
  Database,
  FileText,
  Link2,
  MoreHorizontal,
  Search,
  Send,
  Settings2,
  Sparkles,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatRelativeTime } from '@/lib/formatting';
import { getAgentSlug } from '@/lib/agent-identity';
import { recurrenceLabel } from '@/types';
import type { Recurrence, Agent, NarrativeByTaskSlice } from '@/types';
// ADR-225 Phase 2: bundle-supplied list-mode banner (e.g., alpha-trader's
// "Paper-only..." for current_phase=observation)
import { BundleBanner } from '@/components/library/BundleBanner';
// ADR-225 Phase 3: bundle-supplied pinned tasks float to top of their group
import { useComposition, getTab } from '@/lib/compositor';

interface WorkListSurfaceProps {
  tasks: Recurrence[];
  agents: Agent[];
  /**
   * ADR-219 Commit 4: narrative slices keyed by task slug. Source for
   * recent-activity headlines on the list rows, replacing the legacy
   * `task.last_run_at` timestamp. Tasks with no narrative entries yet
   * are simply absent from the map — the row falls back to the
   * forward-looking next_run_at signal (still useful) or no headline.
   */
  narrativeByTask: Map<string, NarrativeByTaskSlice>;
  agentFilter: string | null;
  dataError?: string | null;
  onClearAgentFilter: () => void;
  onSelect: (slug: string) => void;
}

type WorkTab = 'my-work' | 'connectors' | 'system';

// ─── Classification helpers ──────────────────────────────────────────────────

// Platform-bound task types — anything with requires_platform in the registry.
// Kept as a frontend set to avoid an extra API call.
const CONNECTOR_TYPE_KEYS = new Set([
  'slack-digest',
  'notion-digest',
  'github-digest',
  'commerce-digest',
  'revenue-report',
  'slack-respond',
  'notion-update',
  'trading-digest',
  'trading-signal',
  'trading-execute',
  'portfolio-review',
]);

function isConnectorTask(task: Recurrence): boolean {
  // ADR-231: type_key dissolved. Connector recurrences identified by slug
  // matching against the curated set (operator-conventional naming for
  // platform-awareness recurrences per ADR-207 P4a).
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

// ─── My Work grouping (primary axis: output kind) ───────────────────────────

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
  // ADR-231: type_key dissolved; use slug-prefix matching against the
  // operator-conventional platform-aware recurrence naming.
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

// ─── Search ──────────────────────────────────────────────────────────────────

function agentNameFor(task: Recurrence, agents: Agent[]): string | null {
  const assigned = task.agent_slugs?.[0];
  if (!assigned) return null;
  const agent = agents.find(a => getAgentSlug(a) === assigned);
  return agent?.title ?? assigned;
}

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

  // ── Apply search + agent filter to the active tab ──
  const tabTasks = activeTab === 'my-work' ? myWork : activeTab === 'connectors' ? connectors : system;

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
  // Pull `tabs.work.list.pinned_tasks` from active composition.
  // Pinned tasks float to the top of their group (preserving the
  // pinned-list ordering); non-pinned tasks fall through to the
  // existing compareTasks ordering. Singular implementation: the
  // Set lookup is the only place "is this task pinned?" gets decided.
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

    // Sort within each group: pinned first (in pinned-list order),
    // remainder via compareTasks.
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

  // For My Work: skip group headers if only one group exists
  const flattenMyWork = activeTab === 'my-work' && grouped.length <= 1;

  const tabs: { id: WorkTab; label: string; count: number; icon: React.ElementType }[] = [
    { id: 'my-work', label: 'My Work', count: myWork.length, icon: FileText },
    { id: 'connectors', label: 'Connectors', count: connectors.length, icon: Link2 },
    { id: 'system', label: 'System', count: system.length, icon: Settings2 },
  ];

  return (
    <div className="flex flex-col h-full">
      {/* ADR-215 Phase 4: zone header pair with Cockpit (CockpitRenderer above).
          The two zones — "Cockpit" (glance) and "Work" (manage) — share
          the /work surface under one vertical scroll per ADR-205 F2. The
          section labels make the zones legible without tabs. ADR-225 Phase 3:
          cockpit panes are compositor-resolved (kernel default or bundle). */}
      <div className="flex items-baseline justify-between px-4 sm:px-6 pt-5 pb-2 shrink-0">
        <h2 className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground/70">
          Work
        </h2>
        <span className="text-[10px] text-muted-foreground/40">
          Tasks you own — my work · connectors · system
        </span>
      </div>

      {/* ADR-225 Phase 2: bundle-supplied phase-aware banner (silent when absent) */}
      <BundleBanner tab="work" />

      {/* ── Toolbar ── */}
      <div className="px-4 sm:px-6 pb-3 border-b border-border/40 shrink-0 space-y-3">
        {dataError && (
          <div className="rounded-md border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-[11px] text-amber-700">
            Showing last available data — refresh to retry.
          </div>
        )}

        {/* Row 1: Tabs */}
        <div className="flex items-center gap-1">
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

        {/* Row 2: Search + agent filter + overflow */}
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
      </div>

      {/* ── List body ── */}
      <div className="flex-1 overflow-auto">
        {filtered.length === 0 ? (
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
        )}
      </div>
    </div>
  );
}

// ─── Row ─────────────────────────────────────────────────────────────────────

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

  // Status indicator color
  const dotColor = dim
    ? 'bg-muted-foreground/20'
    : isActive
      ? 'bg-emerald-500'
      : isPaused
        ? 'bg-amber-400'
        : 'bg-muted-foreground/20';

  // Agent names for inline display
  const assignedAgents = agentNamesFor(task, agents);

  const schedule = task.schedule
    ? task.schedule.charAt(0).toUpperCase() + task.schedule.slice(1)
    : null;

  // ADR-219 Commit 4: right-side signal sources from the narrative.
  //
  // Forward-looking: when active + scheduled, show the next-run hint
  // (this is the schedule, not historical activity — narrative
  // doesn't speak to the future).
  //
  // Backward-looking: replace the legacy `Last: 5m ago` timestamp
  // with the most-recent material narrative entry's headline. If
  // no narrative entry exists yet for this task (likely on
  // pre-Commit-2 tasks until the next run lands one), no headline
  // is shown — the row simply doesn't claim activity it can't
  // attribute. This is the singular-implementation answer per
  // discipline rule 1.
  const lastMaterial = narrativeSlice?.last_material ?? null;
  const timeSignal = isActive && task.next_run_at
    ? `Next: ${formatRelativeTime(task.next_run_at)}`
    : lastMaterial
      ? `${formatRelativeTime(lastMaterial.created_at)}`
      : null;
  const headlineSummary = !isActive && lastMaterial ? lastMaterial.summary : null;

  // Sub-label varies by tab
  let subParts: string[] = [];
  if (tab === 'my-work') {
    // Group header shows kind — row shows schedule
    if (schedule) subParts.push(schedule);
  } else if (tab === 'connectors') {
    if (schedule) subParts.push(schedule);
  } else {
    if (schedule) subParts.push(schedule);
  }

  return (
    <button
      onClick={onSelect}
      className={cn(
        'w-full text-left px-3 py-2.5 rounded-lg hover:bg-muted/40 transition-colors flex items-center gap-3 group',
        dim && 'opacity-50',
      )}
    >
      {/* Status dot + kind icon */}
      <div className="relative shrink-0 flex items-center justify-center w-8 h-8 rounded-md bg-muted/50 group-hover:bg-muted/80 transition-colors">
        <KindIcon className={cn('w-3.5 h-3.5', dim ? 'text-muted-foreground/40' : 'text-muted-foreground')} />
        {(isActive || isPaused) && !dim && (
          <div className={cn('absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full ring-2 ring-background', dotColor)} />
        )}
      </div>

      {/* Title + metadata */}
      <div className="flex-1 min-w-0">
        <p className={cn('text-sm truncate flex items-center gap-1.5', dim ? 'text-muted-foreground' : 'font-medium')}>
          {/* ADR-225 Phase 3: bundle-pinned tasks float to the top of
              their group with a subtle pin glyph for legibility. */}
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
        {/* ADR-219 Commit 4: narrative headline — the most-recent material
            invocation's summary, sourced from session_messages. Active
            scheduled tasks keep their forward-looking next-run signal in
            the right column; this line shows what actually shipped last. */}
        {headlineSummary && (
          <p className="text-[11px] text-muted-foreground/60 truncate mt-0.5 italic">
            {headlineSummary}
          </p>
        )}
      </div>

      {/* Time signal */}
      {timeSignal && (
        <span className="text-[11px] text-muted-foreground/50 shrink-0 tabular-nums">
          {timeSignal}
        </span>
      )}
    </button>
  );
}

// ─── Empty state ─────────────────────────────────────────────────────────────

function EmptyResult({ tab, hasFilters }: { tab: WorkTab; hasFilters: boolean }) {
  // ADR-190 + ADR-189: empty states funnel back to /chat (the authorship
  // surface) so a user who lands on /work or /agents with nothing yet has
  // a clear path forward. CTA present only on the "no work authored yet"
  // case — not when filters merely hide existing work.
  const messages: Record<WorkTab, { icon: React.ElementType; title: string; sub: string; cta?: { label: string; href: string } }> = {
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
