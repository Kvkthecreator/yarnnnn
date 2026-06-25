'use client';

/**
 * ActivityLog — the execution-lens body (ADR-340 D8 Machinery consolidation).
 *
 * Reads `execution_events` (one row per invocation, always written by
 * `record_execution_event`). Forensic view — complementary to /feed (operator
 * narrative).
 *
 * Single operator question this body answers: "Did the recurrences in my
 * workspace actually run, did they succeed, what did they cost?"
 *
 * ADR-340 D8: Activity folded to pane-grade under Recurrence. This component is
 * the SINGLE Activity body (Singular Implementation) — rendered as the "Runs"
 * lens inside the Recurrence window (`/recurrence?recurrence.pane=activity`). The former
 * standalone `/activity` page is now an ADR-308 server redirect stub. The
 * declaration lens ("what's scheduled, when does it fire") is the Recurrence
 * window's default mode; this is the execution drill-down.
 *
 * `slugFilter` is intra-surface filter state passed by the host (the Recurrence
 * window reads `?slug=` and hands it down) — pre-filters the execution-events
 * query to one recurrence. `onClearSlugFilter` clears it without a pathname
 * flip (ADR-297 D19.6).
 */

import { useEffect, useState, useCallback, useMemo } from 'react';
import { SurfaceLink } from '@/components/shell/SurfaceLink';
import { RefreshCw, CheckCircle2, XCircle, MinusCircle, ChevronDown, ChevronRight, X } from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import type { ExecutionEvent } from '@/types';

type ModeFilter = 'all' | 'judgment' | 'mechanical';
type StatusFilter = 'all' | 'success' | 'failed' | 'skipped';

// ─── helpers ────────────────────────────────────────────────────────────────

function formatDuration(ms: number | null): string {
  if (!ms) return '—';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatCost(usd: number | null, mode?: string): string {
  // Mechanical-mode rows are zero-cost by construction — render '—' so the
  // operator's eye doesn't read literal $0.0000 noise across the page.
  if (mode === 'mechanical') return '—';
  if (!usd) return '—';
  if (usd < 0.001) return `<$0.001`;
  return `$${usd.toFixed(4)}`;
}

function formatTokens(n: number | null): string {
  if (!n) return '—';
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return String(n);
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function statusIcon(status: ExecutionEvent['status']) {
  if (status === 'success') return <CheckCircle2 className="w-3.5 h-3.5 text-green-500 shrink-0" />;
  if (status === 'failed')  return <XCircle className="w-3.5 h-3.5 text-destructive shrink-0" />;
  return <MinusCircle className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0" />;
}

function triggerLabel(t: string): string {
  if (t === 'back_office') return 'system';
  return t;
}

// ─── grouped view ────────────────────────────────────────────────────────────

interface JobGroup {
  slug: string;
  mode: string;
  events: ExecutionEvent[];
  successCount: number;
  failedCount: number;
  skippedCount: number;
  lastRun: string;
  totalCost: number;
}

function groupBySlug(events: ExecutionEvent[]): JobGroup[] {
  const map = new Map<string, JobGroup>();
  for (const ev of events) {
    if (!map.has(ev.slug)) {
      map.set(ev.slug, {
        slug: ev.slug,
        mode: ev.mode,
        events: [],
        successCount: 0,
        failedCount: 0,
        skippedCount: 0,
        lastRun: ev.created_at,
        totalCost: 0,
      });
    }
    const g = map.get(ev.slug)!;
    g.events.push(ev);
    if (ev.status === 'success') g.successCount++;
    else if (ev.status === 'failed') g.failedCount++;
    else g.skippedCount++;
    if (ev.created_at > g.lastRun) g.lastRun = ev.created_at;
    g.totalCost += ev.cost_usd ?? 0;
  }
  return Array.from(map.values()).sort((a, b) =>
    b.lastRun.localeCompare(a.lastRun)
  );
}

// ─── EventRow ────────────────────────────────────────────────────────────────

function EventRow({ ev }: { ev: ExecutionEvent }) {
  const [expanded, setExpanded] = useState(false);
  const hasDetail = ev.status === 'failed' && (ev.error_reason || ev.error_detail);

  return (
    <div className="border-b border-border/40 last:border-0">
      <button
        className={cn(
          "w-full grid gap-2 px-4 py-2 text-xs text-left",
          "grid-cols-[1rem_1fr_4rem_4rem_4rem_4rem_4.5rem]",
          hasDetail ? "hover:bg-muted/40 cursor-pointer" : "cursor-default"
        )}
        onClick={() => hasDetail && setExpanded(e => !e)}
        disabled={!hasDetail}
      >
        {statusIcon(ev.status)}
        <span className="font-mono text-muted-foreground truncate">
          {relativeTime(ev.created_at)}
        </span>
        <span className="text-right text-muted-foreground/70">{triggerLabel(ev.trigger_type)}</span>
        <span className="text-right text-muted-foreground/70">{ev.tool_rounds != null ? `${ev.tool_rounds}r` : '—'}</span>
        <span className="text-right text-muted-foreground/70">{formatTokens((ev.input_tokens ?? 0) + (ev.output_tokens ?? 0))}</span>
        <span className="text-right text-muted-foreground/70">{formatCost(ev.cost_usd, ev.mode)}</span>
        <span className="text-right text-muted-foreground/70">{formatDuration(ev.duration_ms)}</span>
      </button>
      {expanded && hasDetail && (
        <div className="px-4 pb-3 space-y-1">
          {ev.error_reason && (
            <p className="text-xs font-medium text-destructive">{ev.error_reason}</p>
          )}
          {ev.error_detail && (
            <pre className="text-[10px] text-muted-foreground bg-muted/50 rounded p-2 overflow-x-auto whitespace-pre-wrap break-all">
              {ev.error_detail}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

// ─── JobCard ─────────────────────────────────────────────────────────────────

function JobCard({ group, defaultOpen = false }: { group: JobGroup; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  const lastStatus = group.events[0]?.status ?? 'skipped';

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      {/* Header — converted from <button> to <div role="button"> so the
          declaration-lens deep-link below can be a real <Link> without
          becoming a nested interactive element. Lens-sharpening per the
          Runs-vs-Schedule split (ADR-340 D8): this lens answers "did it
          run, succeed, what did it cost"; the link routes operators to the
          declaration lens for management. */}
      <div
        role="button"
        tabIndex={0}
        className="w-full flex items-center gap-3 px-4 py-3 text-sm text-left hover:bg-muted/30 transition-colors cursor-pointer"
        onClick={() => setOpen(o => !o)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setOpen(o => !o);
          }
        }}
      >
        {open
          ? <ChevronDown className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
          : <ChevronRight className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
        }

        <span className={cn(
          "w-2 h-2 rounded-full shrink-0",
          lastStatus === 'success' ? "bg-green-500" :
          lastStatus === 'failed'  ? "bg-destructive" :
          "bg-muted-foreground/30"
        )} />

        <span className="font-mono font-medium flex-1 truncate">{group.slug}</span>

        <div className="flex items-center gap-3 text-xs text-muted-foreground/70 shrink-0">
          <span className="text-green-600">{group.successCount} ok</span>
          {group.failedCount > 0 && (
            <span className="text-destructive">{group.failedCount} err</span>
          )}
          {group.skippedCount > 0 && (
            <span>{group.skippedCount} skip</span>
          )}
          <span>{relativeTime(group.lastRun)}</span>
          {group.totalCost > 0 && group.mode !== 'mechanical' && (
            <span>${group.totalCost.toFixed(4)}</span>
          )}
        </div>

        {/* Declaration-lens deep-link — foregrounds the Recurrence window at
            this slug where the operator can run / pause / edit it (ADR-340 D8).
            SurfaceLink renders a real <a> (so the role=button header isn't a
            nested interactive element) and routes through the window manager
            instead of hard-navigating off /desktop. */}
        <SurfaceLink
          to="recurrence"
          params={{ task: group.slug }}
          onClick={(e) => e.stopPropagation()}
          className="shrink-0 text-[10px] text-muted-foreground/40 hover:text-foreground hover:underline underline-offset-4 transition-colors"
          title="Manage this scheduled work — run, pause, or edit it"
        >
          Manage →
        </SurfaceLink>
      </div>

      {open && (
        <div className="border-t border-border/40 bg-muted/10">
          <div className="grid gap-2 px-4 py-1.5 text-[10px] text-muted-foreground/50 uppercase tracking-wide grid-cols-[1rem_1fr_4rem_4rem_4rem_4rem_4.5rem]">
            <span />
            <span>When</span>
            <span className="text-right">Trigger</span>
            <span className="text-right">Rounds</span>
            <span className="text-right">Tokens</span>
            <span className="text-right">Cost</span>
            <span className="text-right">Duration</span>
          </div>
          {group.events.map((ev, i) => (
            <EventRow key={ev.id ?? i} ev={ev} />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Filter pills ────────────────────────────────────────────────────────────

function FilterPill({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "px-2.5 py-1 text-xs rounded-md border transition-colors",
        active
          ? "border-foreground/30 bg-foreground/5 text-foreground"
          : "border-border text-muted-foreground hover:bg-muted/50"
      )}
    >
      {label}
    </button>
  );
}

// ─── ActivityLog (the shared execution-lens body) ────────────────────────────

export interface ActivityLogProps {
  /**
   * Pre-filter the execution-events query to one recurrence slug. The host
   * (Recurrence window) reads `?slug=` and passes it down; null = unfiltered.
   */
  slugFilter?: string | null;
  /**
   * Clear the slug filter — host updates `?slug=` without a pathname flip
   * (ADR-297 D19.6). Omit when the host doesn't own a clearable slug param.
   */
  onClearSlugFilter?: () => void;
}

export function ActivityLog({ slugFilter = null, onClearSlugFilter }: ActivityLogProps) {
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modeFilter, setModeFilter] = useState<ModeFilter>('all');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.system.executionEvents({
        limit: 500,
        ...(slugFilter && { slug: slugFilter }),
        ...(modeFilter !== 'all' && { mode: modeFilter }),
        ...(statusFilter !== 'all' && { status: statusFilter }),
      });
      setEvents(data);
    } catch {
      setError('Failed to load activity log.');
    } finally {
      setLoading(false);
    }
  }, [slugFilter, modeFilter, statusFilter]);

  useEffect(() => { load(); }, [load]);

  const groups = useMemo(() => groupBySlug(events), [events]);
  const totalCost = useMemo(
    () => events.filter(e => e.mode !== 'mechanical').reduce((s, e) => s + (e.cost_usd ?? 0), 0),
    [events]
  );

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 sm:px-6 py-4 border-b border-border/50 shrink-0">
        <div>
          <h1 className="text-sm font-semibold">Activity</h1>
          {!loading && events.length > 0 && (
            <p className="text-xs text-muted-foreground/60 mt-0.5">
              {groups.length} jobs · {events.length} runs · ${totalCost.toFixed(4)} total
            </p>
          )}
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-md border border-border hover:bg-muted transition-colors disabled:opacity-40"
        >
          <RefreshCw className={cn("w-3.5 h-3.5", loading && "animate-spin")} />
          Refresh
        </button>
      </div>

      {/* Filter row */}
      <div className="flex items-center gap-4 px-4 sm:px-6 py-3 border-b border-border/30 shrink-0 flex-wrap">
        {slugFilter && onClearSlugFilter && (
          <button
            onClick={onClearSlugFilter}
            className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-primary/10 text-primary text-xs hover:bg-primary/20 transition-colors"
            title="Clear slug filter"
          >
            <span className="font-mono">{slugFilter}</span>
            <X className="w-3 h-3" />
          </button>
        )}
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] uppercase tracking-wide text-muted-foreground/50 mr-1">Mode</span>
          <FilterPill label="All" active={modeFilter === 'all'} onClick={() => setModeFilter('all')} />
          <FilterPill label="Judgment" active={modeFilter === 'judgment'} onClick={() => setModeFilter('judgment')} />
          <FilterPill label="Mech" active={modeFilter === 'mechanical'} onClick={() => setModeFilter('mechanical')} />
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] uppercase tracking-wide text-muted-foreground/50 mr-1">Status</span>
          <FilterPill label="All" active={statusFilter === 'all'} onClick={() => setStatusFilter('all')} />
          <FilterPill label="Success" active={statusFilter === 'success'} onClick={() => setStatusFilter('success')} />
          <FilterPill label="Failed" active={statusFilter === 'failed'} onClick={() => setStatusFilter('failed')} />
          <FilterPill label="Skipped" active={statusFilter === 'skipped'} onClick={() => setStatusFilter('skipped')} />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6">
        {loading && events.length === 0 ? (
          <div className="text-sm text-muted-foreground/50 text-center py-16">Loading…</div>
        ) : error ? (
          <div className="text-sm text-destructive text-center py-16">{error}</div>
        ) : groups.length === 0 ? (
          <div className="text-sm text-muted-foreground/50 text-center py-16">
            No activity recorded yet. Jobs appear here after their first run.
          </div>
        ) : (
          <div className="space-y-2 max-w-4xl">
            {groups.map(g => (
              <JobCard
                key={g.slug}
                group={g}
                // Auto-open when arriving via a single-slug filter (the
                // operator wants the run history without an extra click).
                defaultOpen={!!slugFilter && groups.length === 1}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
