'use client';

/**
 * ReviewerActivityPanel — supervision surface for the Reviewer's autonomous
 * loop (ADR-251 D5, reframed 2026-05-08).
 *
 * Answers the operator's three supervision questions:
 *   1. Is autonomy alive?     ← Recent runs (execution_events)
 *   2. What did it do?        ← Recent autonomous actions (action_proposals)
 *   3. When will it next fire? ← Scheduled fires (back-office.yaml + cron math)
 *
 * Single source of truth: GET /api/agents/reviewer/activity. Reviewer-specific
 * by intent — heartbeat triggers + delegation ceiling are Reviewer concepts.
 * If a second agent ever needs an analogous panel, generalise then.
 *
 * Surfaces (per ADR-251 D5):
 *   - Reviewer agent detail Autonomy tab (below DelegationCard)
 *   - Chat WorkspaceContextOverlay Review section (below PrinciplesCard)
 *
 * Editing posture: read-only. Mutations route through chat per ADR-235 D1
 * + ADR-245 (substrate writes via primitives, not bespoke modals).
 */

import { useEffect, useState } from 'react';
import { Activity, Calendar, CheckCircle2, AlertCircle, ArrowRight, Inbox } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useNarrative } from '@/contexts/NarrativeContext';

interface RunRow {
  slug: string;
  status: string;          // success | failed | skipped
  created_at: string;
  error_reason: string | null;
  duration_ms: number | null;
}

interface ActionRow {
  id: string;
  action_type: string;
  status: string;          // pending | approved | rejected | executed | expired | rejected_at_execution
  expected_effect: string | null;
  approved_at: string | null;
  executed_at: string | null;
  approved_by: string | null;   // 'user' | 'auto_reversible' | null
  source: string | null;        // 'reviewer_periodic' | 'reviewer_heartbeat' | etc.
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
  return slug.replace(/^back-office-reviewer-/, '');
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
  // "trading.submit_order" → "submit_order"
  const tail = a.action_type.split('.').slice(-1)[0] || a.action_type;
  return a.expected_effect || tail;
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

export function ReviewerActivityPanel() {
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

  const noRunsInWindow = data.runs.length === 0;
  const lastRunAt = data.runs[0]?.created_at;
  const lastRunStale = lastRunAt
    ? (Date.now() - new Date(lastRunAt).getTime()) > 36 * 3_600_000  // >36h since any run
    : true;

  const editPrompt =
    "I want to change my Reviewer's schedule (when reflection or calibration runs). Walk me through the current cadence and what's possible.";

  return (
    <div className="rounded-lg border border-border/60 bg-muted/10 px-4 py-4 space-y-4">
      <div className="flex items-center gap-2">
        <Activity className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Reviewer Activity
        </span>
        <span className="ml-auto text-[10px] text-muted-foreground/60">
          Last {data.window_days}d
        </span>
      </div>

      {/* Liveness warning when no runs in window */}
      {noRunsInWindow && data.schedules.length > 0 && (
        <div className="rounded-md border border-amber-200/60 bg-amber-50/50 px-3 py-2.5 flex items-start gap-2">
          <AlertCircle className="h-3.5 w-3.5 text-amber-600 mt-0.5 shrink-0" />
          <div className="text-xs text-amber-800">
            No Reviewer runs in the last {data.window_days} days. Schedules below are configured
            but the scheduler may not be firing — check system status if this persists.
          </div>
        </div>
      )}

      {!noRunsInWindow && lastRunStale && (
        <div className="rounded-md border border-amber-200/60 bg-amber-50/50 px-3 py-2 text-[11px] text-amber-800">
          Last run was over 36h ago. Expected runs are configured below.
        </div>
      )}

      {/* Recent autonomous actions — the money-moving events */}
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/70 mb-1.5">
          Recent autonomous actions
        </p>
        {data.actions.length === 0 ? (
          <p className="text-xs text-muted-foreground/60">
            No autonomous actions yet in this window.
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
      </div>

      {/* Recent runs — liveness signal */}
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/70 mb-1.5">
          Recent runs
        </p>
        {noRunsInWindow ? (
          <p className="text-xs text-muted-foreground/60">No runs recorded.</p>
        ) : (
          <ul className="space-y-1">
            {data.runs.slice(0, 5).map((r, i) => (
              <li key={i} className="flex items-center gap-2 text-xs">
                {r.status === 'success' ? (
                  <CheckCircle2 className="h-3 w-3 text-emerald-600 shrink-0" />
                ) : (
                  <AlertCircle className="h-3 w-3 text-rose-600 shrink-0" />
                )}
                <span className="font-medium">{shortSlug(r.slug)}</span>
                {r.error_reason && (
                  <span className="text-rose-600/80 text-[10px]">· {r.error_reason}</span>
                )}
                <span className="ml-auto text-[10px] text-muted-foreground/60 tabular-nums">
                  {relativeTime(r.created_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Scheduled — what's coming */}
      {data.schedules.length > 0 && (
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/70 mb-1.5 flex items-center gap-1.5">
            <Calendar className="h-3 w-3" />
            Scheduled
          </p>
          <ul className="space-y-1">
            {data.schedules.map((s) => (
              <li key={s.slug} className="flex items-center gap-2 text-xs">
                <span className="font-medium">{shortSlug(s.slug)}</span>
                {s.paused && (
                  <span className="rounded bg-muted px-1 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
                    paused
                  </span>
                )}
                <span className="ml-auto text-muted-foreground/70 tabular-nums">
                  {s.next_fires_at ? `next ${relativeTime(s.next_fires_at)}` : (s.paused ? '—' : 'not scheduled')}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <button
        type="button"
        onClick={() => sendMessage(editPrompt)}
        className="flex items-center gap-1 text-xs text-primary hover:text-primary/80 transition-colors"
      >
        Edit schedule via chat <ArrowRight className="h-3 w-3" />
      </button>
    </div>
  );
}
