'use client';

/**
 * RecurrenceList — Atomic Recurrence surface body (ADR-297 D1).
 *
 * Renders all recurrences cadence-grouped (Recurring / Reactive) with
 * search, agent filter, and include-historical toggle. Answers the
 * operator's question "what runs, and when?"
 *
 * "Cadence" survives here as the temporal-classification concept
 * (cadenceCategory: Recurring vs Reactive grouping) — distinct from the
 * surface name, which is Recurrence (renamed from Cadence 2026-06-03;
 * the substrate + hooks already spoke "recurrence").
 *
 * System/back-office recurrences are hidden by default (visible via
 * include-historical toggle in the overflow menu). Connector vs user-
 * work distinction dissolved per ADR-261 — every recurrence is a first-
 * class scheduled item.
 *
 * Renamed from WorkListSurface in the ADR-297 atomic-shell migration.
 * The former Dashboard tab dissolved — cockpit rendering lives at the
 * dedicated /home atomic surface (ADR-312). Cockpit-slot + activeTab +
 * WorkTab concepts all removed; this is a single-mode list surface now.
 */

import { useRef, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import {
  Cpu,
  FileText,
  MoreHorizontal,
  Search,
  Settings2,
  Sparkles,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatRelativeTime } from '@/lib/formatting';
import { getAgentSlug } from '@/lib/agent-identity';
import {
  cadenceCategory,
  humanizeSchedule,
  CADENCE_ORDER,
  CADENCE_LABELS,
  type CadenceCategory,
} from '@/lib/schedule';
import type { Recurrence, Agent, NarrativeByTaskSlice } from '@/types';
import { BundleBanner } from '@/components/library/BundleBanner';
import { useComposition, getTab } from '@/lib/compositor';

interface RecurrenceListProps {
  tasks: Recurrence[];
  agents: Agent[];
  narrativeByTask: Map<string, NarrativeByTaskSlice>;
  agentFilter: string | null;
  dataError?: string | null;
  onClearAgentFilter: () => void;
  onSelect: (slug: string) => void;
}

// Per ADR-263, a recurrence's `mode` declares its wake intent:
//   mechanical → deterministic Python, no LLM, zero cost (Cpu icon)
//   judgment   → wakes the Reviewer with the prompt (FileText icon)
// Back-office recurrences (`back-office-` slug prefix) retain Settings2
// regardless of mode — they're plumbing housekeeping, conceptually distinct
// from operator-facing work and always visually muted.
//
// The icon shift is the cost-shape lever ADR-263 §6.3 promised: operators
// see at a glance which scheduled work fires LLM and which runs free.
function iconForRecurrence(rec: Recurrence): React.ElementType {
  if (rec.slug.startsWith('back-office-')) return Settings2;
  if (rec.mode === 'mechanical') return Cpu;
  return FileText;
}

// ─── Sorting ──────────────────────────────────────────────────────────────────

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

// ─── Search ───────────────────────────────────────────────────────────────────

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
  // ADR-268: schedule may be list-form (multiple fires per day); flatten
  // for the search-index token blob so any member matches the operator's
  // search query without leaking JSON array syntax into the tokens.
  const scheduleTokens = Array.isArray(task.schedule)
    ? task.schedule
    : task.schedule
      ? [task.schedule]
      : [];
  return [
    task.title,
    ...agentNamesFor(task, agents),
    task.slug,
    task.delivery,
    ...scheduleTokens,
    ...(task.context_reads ?? []),
    ...(task.context_writes ?? []),
    ...obj,
  ].filter(Boolean).join(' ').toLowerCase();
}

// ─── Overflow menu ────────────────────────────────────────────────────────────

function OverflowOptions({
  includeSystem,
  includeHistorical,
  onToggleSystem,
  onToggleHistorical,
}: {
  includeSystem: boolean;
  includeHistorical: boolean;
  onToggleSystem: () => void;
  onToggleHistorical: () => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const activeCount = (includeSystem ? 1 : 0) + (includeHistorical ? 1 : 0);

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
        <div className="absolute right-0 top-full mt-1 z-20 min-w-[220px] rounded-md border border-border bg-popover shadow-md py-1">
          <label className="flex items-center gap-2.5 px-3 py-2 text-xs text-muted-foreground hover:text-foreground hover:bg-muted cursor-pointer">
            <input type="checkbox" checked={includeSystem} onChange={onToggleSystem} className="rounded border-border" />
            Show system recurrences
          </label>
          <label className="flex items-center gap-2.5 px-3 py-2 text-xs text-muted-foreground hover:text-foreground hover:bg-muted cursor-pointer">
            <input type="checkbox" checked={includeHistorical} onChange={onToggleHistorical} className="rounded border-border" />
            Include completed &amp; archived
          </label>
        </div>
      )}
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────

export function RecurrenceList({
  tasks,
  agents,
  narrativeByTask,
  agentFilter,
  dataError,
  onClearAgentFilter,
  onSelect,
}: RecurrenceListProps) {
  const [search, setSearch] = useState('');
  const [includeSystem, setIncludeSystem] = useState(false);
  const [includeHistorical, setIncludeHistorical] = useState(false);

  // Base filter: status + system
  // Phase I: 'system' = back-office plumbing, identified by slug prefix
  // (post ADR-261 D1 there is no output_kind to dispatch on; back-office
  // recurrences carry the convention 'back-office-{slug}').
  const base = useMemo(() => {
    let result = tasks;
    if (!includeHistorical) result = result.filter(t => t.status !== 'archived' && t.status !== 'completed');
    if (!includeSystem) result = result.filter(t => !t.slug.startsWith('back-office-'));
    return result;
  }, [tasks, includeHistorical, includeSystem]);

  // Search + agent filter
  const filtered = useMemo(() => {
    let result = base;
    if (agentFilter) result = result.filter(t => t.agent_slugs?.includes(agentFilter));
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      result = result.filter(t => buildSearchText(t, agents).includes(q));
    }
    return result;
  }, [base, agentFilter, search, agents]);

  // ADR-225 Phase 3: bundle-supplied pinned tasks
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

  // Cadence-group the filtered list for the Schedule tab
  const cadenceGroups = useMemo(() => {
    const buckets: Record<CadenceCategory, Recurrence[]> = { recurring: [], reactive: [] };
    for (const r of filtered) buckets[cadenceCategory(r)].push(r);

    for (const key of Object.keys(buckets) as CadenceCategory[]) {
      buckets[key].sort((a, b) => {
        const aPinned = pinnedSlugs.has(a.slug);
        const bPinned = pinnedSlugs.has(b.slug);
        if (aPinned && !bPinned) return -1;
        if (!aPinned && bPinned) return 1;
        if (aPinned && bPinned) return (pinnedOrder.get(a.slug) ?? 0) - (pinnedOrder.get(b.slug) ?? 0);
        return compareTasks(a, b);
      });
    }

    return CADENCE_ORDER
      .map(key => ({ key, label: CADENCE_LABELS[key], items: buckets[key] }))
      .filter(g => g.items.length > 0);
  }, [filtered, pinnedSlugs, pinnedOrder]);

  const agentLabel = agentFilter
    ? agents.find(a => getAgentSlug(a) === agentFilter)?.title ?? agentFilter
    : null;

  return (
    <div className="flex flex-col h-full">
      {/* ── Toolbar ── */}
      <div className="px-4 sm:px-6 pt-3 pb-3 border-b border-border/40 shrink-0 space-y-3">
        {dataError && (
          <div className="rounded-md border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-[11px] text-amber-700">
            Showing last available data — refresh to retry.
          </div>
        )}

        {/* Bundle banner — operator-facing posture string from the active
            program's SURFACES.yaml. Optional; renders nothing when the
            bundle declares no banner. Kept here so program-shipped
            context still surfaces on the Recurrence list. */}
        <BundleBanner tab="work" />

        {/* Search + agent filter + pace badge + overflow */}
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
          {/* ADR-297 D20 (2026-05-24): PaceBadge deleted — pace + queue
              depth glance lives in the top-bar SystemStatusCluster
              (slot 2). Singular Implementation: one pace indicator. */}
          <OverflowOptions
            includeSystem={includeSystem}
            includeHistorical={includeHistorical}
            onToggleSystem={() => setIncludeSystem(v => !v)}
            onToggleHistorical={() => setIncludeHistorical(v => !v)}
          />
        </div>
      </div>

      {/* ── Cadence list ── */}
      <div className="flex-1 overflow-auto">
        {cadenceGroups.length === 0 ? (
          <EmptySchedule hasFilters={!!search || !!agentFilter} />
        ) : (
          <div className="px-4 sm:px-6 py-4 max-w-4xl space-y-6">
            {cadenceGroups.map(group => (
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
                  {group.items.map(task => (
                    <ScheduleRow
                      key={task.id}
                      task={task}
                      agents={agents}
                      narrativeSlice={narrativeByTask.get(task.slug) ?? null}
                      category={cadenceCategory(task)}
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

// ─── Schedule row ─────────────────────────────────────────────────────────────

function ScheduleRow({
  task,
  agents,
  narrativeSlice,
  category,
  isPinned,
  onSelect,
}: {
  task: Recurrence;
  agents: Agent[];
  narrativeSlice: NarrativeByTaskSlice | null;
  category: CadenceCategory;
  isPinned: boolean;
  onSelect: () => void;
}) {
  const isActive = task.status === 'active';
  const isPaused = task.paused === true;
  const isSystem = task.slug.startsWith('back-office-');

  const KindIcon = iconForRecurrence(task);

  const dotColor = isSystem
    ? 'bg-muted-foreground/20'
    : isActive
      ? 'bg-emerald-500'
      : isPaused
        ? 'bg-amber-400'
        : 'bg-muted-foreground/20';

  const cadenceText =
    category === 'recurring'
      ? humanizeSchedule(task.schedule)
      : 'On event';

  const assignedAgents = agentNamesFor(task, agents);

  // Declaration-lens signals only — what this recurrence is scheduled
  // to do and when. Execution detail (what happened, did it succeed,
  // cost) lives in the Runs lens of this same window (ADR-340 D8). The
  // deep-link below routes the operator there for that question.
  const lastMaterial = narrativeSlice?.last_material ?? null;
  const timeSignal = isActive && task.next_run_at
    ? `Next: ${formatRelativeTime(task.next_run_at)}`
    : lastMaterial
      ? `Last ran ${formatRelativeTime(lastMaterial.created_at)}`
      : null;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect();
        }
      }}
      className={cn(
        'w-full text-left px-3 py-2.5 rounded-lg hover:bg-muted/40 transition-colors flex items-center gap-3 group cursor-pointer',
        (isPaused || isSystem) && 'opacity-60',
      )}
    >
      <div className="relative shrink-0 flex items-center justify-center w-8 h-8 rounded-md bg-muted/50 group-hover:bg-muted/80 transition-colors">
        <KindIcon className={cn('w-3.5 h-3.5', isSystem ? 'text-muted-foreground/40' : 'text-muted-foreground')} />
        {(isActive || isPaused) && !isSystem && (
          <div className={cn('absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full ring-2 ring-background', dotColor)} />
        )}
      </div>

      <div className="flex-1 min-w-0">
        <p className={cn('text-sm truncate flex items-center gap-1.5', isSystem ? 'text-muted-foreground' : 'font-medium')}>
          {isPinned && (
            <span className="text-primary/60 text-[10px] leading-none" title="Pinned by program bundle">●</span>
          )}
          <span className="truncate">{task.title}</span>
        </p>
        <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
          <span className="text-[11px] text-muted-foreground/50">{cadenceText}</span>
          {/* ADR-263 cost-shape signal: surface mechanical mode explicitly so
              operators see at a glance which scheduled work fires LLM (default,
              unlabeled) vs which runs as deterministic Python (labeled).
              Judgment mode is implicit — labeling every row would be noise. */}
          {task.mode === 'mechanical' && !isSystem && (
            <>
              <span className="text-[11px] text-muted-foreground/30">·</span>
              <span
                className="text-[9px] font-medium uppercase tracking-wider text-muted-foreground/60 px-1 py-0.5 rounded bg-muted/60"
                title="Runs automatically — no AI cost, no decision needed."
              >
                Auto
              </span>
            </>
          )}
          {assignedAgents.length > 0 && (
            <>
              <span className="text-[11px] text-muted-foreground/30">·</span>
              <span className="text-[11px] text-muted-foreground/40 truncate">
                {assignedAgents.join(', ')}
              </span>
            </>
          )}
        </div>
      </div>

      {timeSignal && (
        <span className="text-[11px] text-muted-foreground/50 shrink-0 tabular-nums">
          {timeSignal}
        </span>
      )}

      {/* Execution-lens deep-link — the Runs lens of this same window
          (ADR-340 D8), pre-filtered to this recurrence's slug.
          stopPropagation so the link click doesn't also trigger row select. */}
      <Link
        href={`/recurrence?recurrence.pane=activity&recurrence.slug=${encodeURIComponent(task.slug)}`}
        onClick={(e) => e.stopPropagation()}
        className="shrink-0 text-[10px] text-muted-foreground/40 hover:text-foreground hover:underline underline-offset-4 transition-colors"
        title="See the run history for this scheduled work"
      >
        View runs →
      </Link>
    </div>
  );
}

// ─── Empty state ──────────────────────────────────────────────────────────────

function EmptySchedule({ hasFilters }: { hasFilters: boolean }) {
  return (
    <div className="flex items-center justify-center h-full min-h-[200px] px-4">
      <div className="text-center max-w-sm">
        <Sparkles className="w-6 h-6 text-muted-foreground/25 mx-auto mb-3" />
        <p className="text-sm font-medium mb-1.5">
          {hasFilters ? 'No recurrences match' : 'Nothing scheduled yet'}
        </p>
        <p className="text-xs text-muted-foreground mb-4">
          {hasFilters
            ? 'Clear filters to see all scheduled work.'
            : 'Tell YARNNN what you want done and on what cadence.'}
        </p>
        {!hasFilters && (
          <a
            href="/feed"
            className="inline-flex items-center gap-2 rounded-md bg-foreground px-3.5 py-1.5 text-xs font-medium text-background hover:bg-foreground/90 transition-colors"
          >
            Talk to YARNNN
          </a>
        )}
      </div>
    </div>
  );
}
