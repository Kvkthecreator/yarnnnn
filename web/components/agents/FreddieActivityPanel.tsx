'use client';

/**
 * FreddieActivityPanel — Reviewer supervision surface.
 *
 * Authored 2026-05-14 as first-principles rewrite (replaces the
 * ADR-251-D5-era panel that read dissolved back-office.yaml substrate
 * and a stale slug filter). Now reads the canonical post-ADR-261
 * GET /api/agents/freddie/activity which derives from
 * /workspace/_recurrences.yaml (judgment-mode entries = Reviewer wakes
 * per ADR-263 D1).
 *
 * Single operator question this surface answers:
 *   "Is my Reviewer functioning autonomously the way it's been told to?"
 *
 * Four sections (top-to-bottom — most-actionable signal first):
 *
 *   1. Health headline — one-line liveness signal. Green = recent run.
 *      Amber = no run in the configured supervision window.
 *
 *   2. Upcoming wakes — when each judgment-mode recurrence next fires.
 *      Operator can see the cadence schedule at a glance and judge
 *      whether autonomy is well-shaped.
 *
 *   3. Recent autonomous actions — what the Reviewer has actually done
 *      on the operator's behalf (Reviewer-originated or auto-approved
 *      proposals). The money-moving trail.
 *
 *   4. Recent runs — every judgment-mode run in the supervision window.
 *      Forensic, but compact — each row deep-links to /activity for
 *      detail per the supervision-vs-execution lens distinction
 *      (WORKSPACE.md).
 *
 * Distinct from /activity (workspace-wide execution-lens covering every
 * recurrence + mode + cost): this surface is **Reviewer-only supervision**.
 * The "View all runs →" deep-link bridges to /activity for the broader
 * execution view.
 *
 * Read-only. Mutations route through chat per ADR-235 D1 + ADR-245
 * (substrate writes via primitives, not bespoke modals).
 *
 * Reused on:
 *   - Workspace Settings → System Agent → Activity (canonical home, ADR-412 D5)
 *   - Chat WorkspaceContextOverlay Review section
 */

import { useEffect, useState } from 'react';
import { ArrowRight, Calendar, CheckCircle2, AlertCircle, Inbox, Activity } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useNarrative } from '@/contexts/NarrativeContext';
import { SurfaceLink } from '@/components/shell/SurfaceLink';

interface RunRow {
  slug: string;
  status: string;          // success | failed | skipped
  created_at: string;
  error_reason: string | null;
  duration_ms: number | null;
}

interface ActionRow {
  id: string;
  // ADR-307: generic queue shape.
  primitive: string;
  family: 'capital' | 'substrate';
  decision_context: Record<string, unknown> | null;
  status: string;          // pending | approved | rejected | executed | expired | rejected_at_execution
  approved_at: string | null;
  executed_at: string | null;
  approved_by: string | null;   // 'user' | null
  source: string | null;        // 'reviewer:<occupant>'
  created_at: string;
}

interface ScheduleRow {
  slug: string;
  display_name: string;
  schedule: string | null;
  paused: boolean;
  next_fires_at: string | null;
}

interface ActivityData {
  runs: RunRow[];
  actions: ActionRow[];
  schedules: ScheduleRow[];
  window_days: number;
}

function shortSlug(slug: string): string {
  // Slugs are already human-readable in canonical _recurrences.yaml
  // (morning-reflection, signal-evaluation, pre-market-brief, etc.) —
  // no legacy prefix to strip post-ADR-261.
  return slug;
}

function relativeTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  const diffMs = Date.now() - new Date(iso).getTime();
  const future = diffMs < 0;
  const abs = Math.abs(diffMs);
  const m = Math.floor(abs / 60_000);
  const h = Math.floor(m / 60);
  const d = Math.floor(h / 24);
  const fmt =
    m < 1 ? 'now' :
    m < 60 ? `${m}m` :
    h < 24 ? `${h}h` :
    `${d}d`;
  return future ? `in ${fmt}` : `${fmt} ago`;
}

function shortAction(a: ActionRow): string {
  // ADR-307: derive a short label from the family-shaped decision_context,
  // falling back to the primitive name.
  const dc = (a.decision_context ?? {}) as Record<string, unknown>;
  if (a.family === 'substrate') {
    return (dc.message as string) || (dc.path as string) || a.primitive;
  }
  return (dc.expected_effect as string) || a.primitive.replace(/^platform_/, '');
}

function actionBadge(a: ActionRow): { label: string; tone: 'green' | 'amber' | 'red' | 'muted' } {
  if (a.status === 'executed' && a.approved_by === 'auto_reversible') {
    return { label: 'auto-executed', tone: 'green' };
  }
  if (a.status === 'executed') return { label: 'executed', tone: 'green' };
  if (a.status === 'approved') return { label: 'approved', tone: 'green' };
  if (a.status === 'rejected' || a.status === 'rejected_at_execution') {
    return { label: 'rejected', tone: 'red' };
  }
  if (a.status === 'expired') return { label: 'expired', tone: 'muted' };
  return { label: 'pending', tone: 'amber' };
}

function badgeClasses(tone: 'green' | 'amber' | 'red' | 'muted'): string {
  switch (tone) {
    case 'green': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    case 'amber': return 'bg-amber-50 text-amber-700 border-amber-200';
    case 'red':   return 'bg-rose-50 text-rose-700 border-rose-200';
    default:      return 'bg-muted text-muted-foreground border-border';
  }
}

export function FreddieActivityPanel() {
  const { sendMessage } = useNarrative();
  const [data, setData] = useState<ActivityData | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.agents.reviewerActivity()
      .then((d) => { if (!cancelled) setData(d); })
      .catch(() => { if (!cancelled) setData({ runs: [], actions: [], schedules: [], window_days: 7 }); });
    return () => { cancelled = true; };
  }, []);

  if (data === null) return null;

  const lastRunAt = data.runs[0]?.created_at;
  const hoursSinceLastRun = lastRunAt
    ? (Date.now() - new Date(lastRunAt).getTime()) / 3_600_000
    : null;

  // Health signal: derive from the nearest active schedule's cadence rather
  // than a fixed 36h. If the Reviewer is supposed to fire daily and last
  // ran 30h ago, that's a real liveness concern; if it fires weekly and
  // last ran 30h ago, that's normal. Until we have a robust per-recurrence
  // freshness model, use 36h as a coarse default for now but only when
  // we have at least one active schedule (otherwise the warning is
  // meaningless).
  const activeSchedules = data.schedules.filter(s => !s.paused);
  const hasActiveSchedules = activeSchedules.length > 0;
  const isStale = hasActiveSchedules && (
    hoursSinceLastRun === null || hoursSinceLastRun > 36
  );
  const isHealthy = hoursSinceLastRun !== null && hoursSinceLastRun <= 36;

  const editPrompt =
    "I want to change my agent's schedule (when reflection, calibration, or other judgment recurrences fire). Walk me through the current cadence.";

  return (
    <div className="space-y-5">
      {/* 1. Health headline */}
      <section className="rounded-lg border border-border bg-card p-4">
        <div className="flex items-center gap-2 mb-2">
          <Activity className="h-3.5 w-3.5 text-muted-foreground" />
          <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            Agent health
          </h3>
          <span className="ml-auto text-[10px] text-muted-foreground/60">
            Last {data.window_days}d
          </span>
        </div>
        {!hasActiveSchedules ? (
          <p className="text-sm text-muted-foreground">
            Your agent isn&apos;t on a schedule yet. It already responds when you
            message it or when an action needs a decision — that&apos;s always on.
            To have it check in on its own at set times, ask it in chat to set
            a schedule.
          </p>
        ) : isHealthy ? (
          <p className="text-sm text-foreground">
            <CheckCircle2 className="inline h-3.5 w-3.5 text-emerald-600 mr-1.5 -mt-0.5" />
            Last agent wake {relativeTime(lastRunAt)}. {data.runs.length} run{data.runs.length === 1 ? '' : 's'} in window.
          </p>
        ) : isStale ? (
          <div className="flex items-start gap-2 text-sm text-amber-800 bg-amber-50/60 rounded-md px-3 py-2 border border-amber-200/60">
            <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
            <span>
              {hoursSinceLastRun === null
                ? `No agent wakes in the last ${data.window_days} days, despite ${activeSchedules.length} active schedule${activeSchedules.length === 1 ? '' : 's'}. Check the scheduler.`
                : `Last wake was ${Math.floor(hoursSinceLastRun)}h ago. Expected by configured cadence below.`}
            </span>
          </div>
        ) : null}
      </section>

      {/* 2. Upcoming wakes */}
      {data.schedules.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-2">
            <Calendar className="h-3 w-3 text-muted-foreground" />
            <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              Upcoming wakes
            </h3>
            <span className="ml-auto text-[10px] text-muted-foreground/60">
              {data.schedules.length} judgment recurrence{data.schedules.length === 1 ? '' : 's'}
            </span>
          </div>
          <ul className="space-y-1">
            {data.schedules.map((s) => (
              <li key={s.slug} className="flex items-center gap-2 text-xs rounded-md border border-border/60 bg-background px-3 py-2">
                <span className="font-mono font-medium">{shortSlug(s.slug)}</span>
                {s.paused && (
                  <span className="rounded bg-muted px-1 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
                    paused
                  </span>
                )}
                <span className="text-[11px] text-muted-foreground/60 truncate">
                  {s.schedule || 'reactive'}
                </span>
                <span className="ml-auto text-muted-foreground/70 tabular-nums shrink-0 text-[11px]">
                  {s.next_fires_at ? relativeTime(s.next_fires_at) : (s.paused ? '—' : 'not scheduled')}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* 3. Recent autonomous actions */}
      <section>
        <div className="flex items-center gap-2 mb-2">
          <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            Recent autonomous actions
          </h3>
          {data.actions.length > 0 && (
            <span className="ml-auto text-[10px] text-muted-foreground/60">
              {data.actions.length}
            </span>
          )}
        </div>
        {data.actions.length === 0 ? (
          <p className="text-xs text-muted-foreground/60 px-1">
            No autonomous actions in this window. With autonomy set to Manual, every action waits
            for your approval — see /work for pending proposals.
          </p>
        ) : (
          <ul className="space-y-1.5">
            {data.actions.slice(0, 5).map((a) => {
              const b = actionBadge(a);
              return (
                <li
                  key={a.id}
                  className="flex items-center gap-2 rounded-md border border-border/60 bg-background px-3 py-2 text-xs"
                >
                  {b.tone === 'green' ? (
                    <CheckCircle2 className="h-3 w-3 text-emerald-600 shrink-0" />
                  ) : b.tone === 'red' ? (
                    <AlertCircle className="h-3 w-3 text-rose-600 shrink-0" />
                  ) : (
                    <Inbox className="h-3 w-3 text-muted-foreground shrink-0" />
                  )}
                  <span className="truncate">{shortAction(a)}</span>
                  <span className={`ml-auto rounded border px-1.5 py-0.5 text-[10px] uppercase tracking-wide shrink-0 ${badgeClasses(b.tone)}`}>
                    {b.label}
                  </span>
                  <span className="text-[10px] text-muted-foreground/60 shrink-0 tabular-nums">
                    {relativeTime(a.executed_at || a.approved_at || a.created_at)}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      {/* 4. Recent runs — compact, deep-links to /activity for forensic detail */}
      <section>
        <div className="flex items-center gap-2 mb-2">
          <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            Recent runs
          </h3>
          {data.runs.length > 0 && (
            <span className="ml-auto text-[10px] text-muted-foreground/60">
              {data.runs.length}
            </span>
          )}
        </div>
        {data.runs.length === 0 ? (
          <p className="text-xs text-muted-foreground/60 px-1">
            No runs recorded in the last {data.window_days} days.
          </p>
        ) : (
          <ul className="space-y-1">
            {data.runs.slice(0, 8).map((r, i) => (
              <li key={i} className="flex items-center gap-2 text-xs px-1 py-0.5">
                {r.status === 'success' ? (
                  <CheckCircle2 className="h-3 w-3 text-emerald-600 shrink-0" />
                ) : (
                  <AlertCircle className="h-3 w-3 text-rose-600 shrink-0" />
                )}
                <span className="font-mono">{shortSlug(r.slug)}</span>
                {r.error_reason && (
                  <span className="text-rose-600/80 text-[10px]">· {r.error_reason}</span>
                )}
                <SurfaceLink
                  to="recurrence"
                  params={{ pane: 'activity', slug: r.slug }}
                  className="ml-auto text-[10px] text-muted-foreground/40 hover:text-foreground hover:underline underline-offset-4 tabular-nums shrink-0"
                  title="See full execution detail in the Runs lens"
                >
                  {relativeTime(r.created_at)} →
                </SurfaceLink>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Cross-surface deep-link to workspace-wide execution-lens (the
          Runs lens of the Recurrence window — ADR-340 D8). */}
      <div className="flex items-center gap-3 pt-1">
        <SurfaceLink
          to="recurrence"
          params={{ pane: 'activity' }}
          className="inline-flex items-center gap-1 text-[11px] text-muted-foreground/60 hover:text-foreground hover:underline underline-offset-4 transition-colors"
        >
          View all runs <ArrowRight className="h-3 w-3" />
        </SurfaceLink>
        <span className="text-muted-foreground/30">·</span>
        <button
          type="button"
          onClick={() => sendMessage(editPrompt)}
          className="inline-flex items-center gap-1 text-[11px] text-primary/70 hover:text-primary hover:underline underline-offset-4 transition-colors"
        >
          Edit schedule via chat <ArrowRight className="h-3 w-3" />
        </button>
      </div>
    </div>
  );
}
