'use client';

/**
 * /backend — per-job execution log for the operator.
 *
 * Shows every invocation attempt recorded in execution_events:
 * slug, shape, status, cost, duration, tokens, error detail.
 * Back-office jobs (reviewer-calibration, outcome-reconciliation, etc.)
 * and operational recurrences (track-universe, signal-evaluation, etc.)
 * all appear here grouped by slug with an expandable per-run log.
 *
 * Read-only surface. No mutations — job management stays in /work.
 */

import { useEffect, useState, useCallback } from 'react';
import { RefreshCw, CheckCircle2, XCircle, MinusCircle, ChevronDown, ChevronRight } from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import type { ExecutionEvent } from '@/types';

// ─── helpers ────────────────────────────────────────────────────────────────

function formatDuration(ms: number | null): string {
  if (!ms) return '—';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatCost(usd: number | null): string {
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

function shapeLabel(shape: string): string {
  const map: Record<string, string> = {
    deliverable: 'Report',
    accumulation: 'Tracker',
    action: 'Action',
    maintenance: 'System',
  };
  return map[shape] ?? shape;
}

function triggerLabel(t: string): string {
  if (t === 'back_office') return 'system';
  return t;
}

// ─── grouped view ────────────────────────────────────────────────────────────

interface JobGroup {
  slug: string;
  shape: string;
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
        shape: ev.shape,
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
  // Sort groups: most recently run first
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
        <span className="text-right text-muted-foreground/70">{formatCost(ev.cost_usd)}</span>
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

function JobCard({ group }: { group: JobGroup }) {
  const [open, setOpen] = useState(false);
  const lastStatus = group.events[0]?.status ?? 'skipped';

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      {/* Header */}
      <button
        className="w-full flex items-center gap-3 px-4 py-3 text-sm text-left hover:bg-muted/30 transition-colors"
        onClick={() => setOpen(o => !o)}
      >
        {open
          ? <ChevronDown className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
          : <ChevronRight className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
        }

        {/* Last-run status dot */}
        <span className={cn(
          "w-2 h-2 rounded-full shrink-0",
          lastStatus === 'success' ? "bg-green-500" :
          lastStatus === 'failed'  ? "bg-destructive" :
          "bg-muted-foreground/30"
        )} />

        <span className="font-mono font-medium flex-1 truncate">{group.slug}</span>

        <span className="text-xs text-muted-foreground/60 shrink-0">
          {shapeLabel(group.shape)}
        </span>

        <div className="flex items-center gap-3 text-xs text-muted-foreground/70 shrink-0">
          <span className="text-green-600">{group.successCount} ok</span>
          {group.failedCount > 0 && (
            <span className="text-destructive">{group.failedCount} err</span>
          )}
          {group.skippedCount > 0 && (
            <span>{group.skippedCount} skip</span>
          )}
          <span>{relativeTime(group.lastRun)}</span>
          {group.totalCost > 0 && (
            <span>{formatCost(group.totalCost)}</span>
          )}
        </div>
      </button>

      {/* Run log */}
      {open && (
        <div className="border-t border-border/40 bg-muted/10">
          {/* Column headers */}
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

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function BackendPage() {
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.system.executionEvents({ limit: 500 });
      setEvents(data);
    } catch {
      setError('Failed to load execution log.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const groups = groupBySlug(events);
  const totalCost = events.reduce((s, e) => s + (e.cost_usd ?? 0), 0);

  return (
    <div className="flex flex-col h-full">
      {/* Page header — inline since PageHeader only accepts defaultLabel */}
      <div className="flex items-center justify-between px-4 sm:px-6 py-4 border-b border-border/50 shrink-0">
        <div>
          <h1 className="text-sm font-semibold">Backend</h1>
          {!loading && events.length > 0 && (
            <p className="text-xs text-muted-foreground/60 mt-0.5">
              {groups.length} jobs · {events.length} runs · {formatCost(totalCost)} total
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

      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6">
        {loading && events.length === 0 ? (
          <div className="text-sm text-muted-foreground/50 text-center py-16">Loading…</div>
        ) : error ? (
          <div className="text-sm text-destructive text-center py-16">{error}</div>
        ) : groups.length === 0 ? (
          <div className="text-sm text-muted-foreground/50 text-center py-16">
            No executions recorded yet. Jobs appear here after their first run.
          </div>
        ) : (
          <div className="space-y-2 max-w-4xl">
            {groups.map(g => (
              <JobCard key={g.slug} group={g} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
