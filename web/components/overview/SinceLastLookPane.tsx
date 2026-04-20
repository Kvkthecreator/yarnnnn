'use client';

/**
 * SinceLastLookPane — Briefing archetype (ADR-198 §3).
 *
 * Temporal pane: what has changed since the operator's last session.
 * Composed by SELECTION, not duplication (invariant B2) — shows counts and
 * most-recent items as pointers into Work / Team / Review. Never embeds
 * foreign substrate content.
 *
 * Data sources (all existing, no new API):
 *   - /api/tasks — recent run counts + most recent task with a recent run
 *   - /api/agents — workforce state summary
 *   - /api/workspace/file?path=/workspace/review/decisions.md — tail-parse
 *     for recent decisions (optional; degrades silently if absent or empty)
 *
 * Degradation: any missing signal collapses that row silently. The pane
 * only renders rows that have real data. If nothing is fresh, the pane
 * renders a "Quiet day" state per ADR-199 empty-state spec.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Loader2, CheckCircle2, ShieldCheck, Sparkles } from 'lucide-react';
import { api } from '@/lib/api/client';
import type { Task } from '@/types';

interface RecentDecision {
  raw: string;
  timestamp: string | null;
  identity: string | null;
  decision: string | null;
}

interface Summary {
  recentRunTasks: Task[]; // tasks whose last_run_at is within lookback
  totalActiveAgents: number;
  totalActiveTasks: number;
  recentDecisions: RecentDecision[];
}

const LOOKBACK_HOURS = 24;

export function SinceLastLookPane() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void loadSummary().then(setSummary).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <PaneFrame title="Since last look">
        <div className="flex items-center justify-center py-4">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      </PaneFrame>
    );
  }

  if (!summary) {
    return (
      <PaneFrame title="Since last look">
        <p className="rounded-md border border-dashed border-border px-4 py-4 text-center text-xs text-muted-foreground">
          Nothing to report yet.
        </p>
      </PaneFrame>
    );
  }

  const hasActivity =
    summary.recentRunTasks.length > 0 || summary.recentDecisions.length > 0;

  if (!hasActivity) {
    const headlineTask = summary.recentRunTasks[0];
    return (
      <PaneFrame title="Since last look">
        <p className="rounded-md border border-dashed border-border px-4 py-4 text-center text-xs text-muted-foreground">
          Quiet {timeWindowLabel()}. {summary.totalActiveTasks} task
          {summary.totalActiveTasks === 1 ? '' : 's'} active across{' '}
          {summary.totalActiveAgents} agent
          {summary.totalActiveAgents === 1 ? '' : 's'}.
        </p>
      </PaneFrame>
    );
  }

  return (
    <PaneFrame title={`Since last look · past ${LOOKBACK_HOURS}h`}>
      <ul className="flex flex-col gap-1.5">
        {summary.recentRunTasks.length > 0 && (
          <li>
            <Link
              href={`/work?task=${encodeURIComponent(summary.recentRunTasks[0].slug)}`}
              className="group flex items-center gap-2 rounded-md border border-border bg-card px-3 py-2 text-sm hover:bg-muted/40"
            >
              <Sparkles className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              <span className="flex-1">
                <strong className="font-medium">
                  {summary.recentRunTasks.length} task run
                  {summary.recentRunTasks.length === 1 ? '' : 's'}
                </strong>
                <span className="text-muted-foreground">
                  {' '}· latest: {summary.recentRunTasks[0].title}
                </span>
              </span>
              <span className="text-[11px] text-muted-foreground group-hover:text-foreground">
                →
              </span>
            </Link>
          </li>
        )}
        {summary.recentDecisions.length > 0 && (
          <li>
            <Link
              href="/review"
              className="group flex items-center gap-2 rounded-md border border-border bg-card px-3 py-2 text-sm hover:bg-muted/40"
            >
              <ShieldCheck className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              <span className="flex-1">
                <strong className="font-medium">
                  {summary.recentDecisions.length} reviewer decision
                  {summary.recentDecisions.length === 1 ? '' : 's'}
                </strong>
                <span className="text-muted-foreground">
                  {' '}· {decisionIdentityBreakdown(summary.recentDecisions)}
                </span>
              </span>
              <span className="text-[11px] text-muted-foreground group-hover:text-foreground">
                →
              </span>
            </Link>
          </li>
        )}
      </ul>
    </PaneFrame>
  );
}

function PaneFrame({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </h2>
      {children}
    </section>
  );
}

function timeWindowLabel(): string {
  return `past ${LOOKBACK_HOURS}h`;
}

async function loadSummary(): Promise<Summary> {
  const sinceIso = new Date(Date.now() - LOOKBACK_HOURS * 3_600_000).toISOString();

  const [tasksResult, agentsResult, decisionsResult] = await Promise.allSettled([
    api.tasks.list(),
    api.agents.list('active'),
    api.workspace.getFile('/workspace/review/decisions.md'),
  ]);

  const tasks = tasksResult.status === 'fulfilled' ? tasksResult.value : [];
  const agents = agentsResult.status === 'fulfilled' ? agentsResult.value : [];
  const decisionsFile =
    decisionsResult.status === 'fulfilled' ? decisionsResult.value : null;

  const recentRunTasks = tasks
    .filter((t: Task) => {
      const lastRun = t.last_run_at;
      if (!lastRun) return false;
      return new Date(lastRun).toISOString() >= sinceIso;
    })
    .sort((a: Task, b: Task) => {
      const aRun = a.last_run_at ? new Date(a.last_run_at).getTime() : 0;
      const bRun = b.last_run_at ? new Date(b.last_run_at).getTime() : 0;
      return bRun - aRun;
    });

  const recentDecisions = parseRecentDecisions(
    decisionsFile?.content ?? '',
    sinceIso,
  );

  return {
    recentRunTasks,
    totalActiveAgents: agents.length,
    totalActiveTasks: tasks.filter((t: Task) => t.status === 'active').length,
    recentDecisions,
  };
}

/**
 * Parse decisions.md for entries newer than sinceIso.
 *
 * Expected format (per backend handoff):
 *   --- decision ---
 *   timestamp: <iso>
 *   reviewer_identity: human:<uuid> | ai:reviewer-sonnet-v1 | impersonated:<uid>-as-<slug>
 *   decision: approve | reject | defer
 *   ...
 *
 * This parser is deliberately tolerant — if the format drifts, it returns
 * whatever it can identify and degrades the rest. Silent-friendly per
 * invariant: no error shown if parse fails, just no decisions surfaced.
 */
function parseRecentDecisions(content: string, sinceIso: string): RecentDecision[] {
  if (!content) return [];
  const blocks = content.split(/\n?---\s*decision\s*---\n/i).filter(Boolean);
  const parsed: RecentDecision[] = [];
  for (const block of blocks) {
    const tsMatch = block.match(/timestamp:\s*(\S+)/i);
    const idMatch = block.match(/reviewer_identity:\s*(\S+)/i);
    const decMatch = block.match(/decision:\s*(\w+)/i);
    const timestamp = tsMatch?.[1] ?? null;
    if (timestamp && timestamp < sinceIso) continue; // too old
    parsed.push({
      raw: block.slice(0, 200),
      timestamp,
      identity: idMatch?.[1] ?? null,
      decision: decMatch?.[1] ?? null,
    });
  }
  return parsed;
}

function decisionIdentityBreakdown(decisions: RecentDecision[]): string {
  const counts = { human: 0, ai: 0, impersonated: 0, other: 0 };
  for (const d of decisions) {
    if (!d.identity) counts.other += 1;
    else if (d.identity.startsWith('human:')) counts.human += 1;
    else if (d.identity.startsWith('ai:')) counts.ai += 1;
    else if (d.identity.startsWith('impersonated:')) counts.impersonated += 1;
    else counts.other += 1;
  }
  const parts: string[] = [];
  if (counts.human > 0) parts.push(`${counts.human} human`);
  if (counts.ai > 0) parts.push(`${counts.ai} AI`);
  if (counts.impersonated > 0) parts.push(`${counts.impersonated} impersonated`);
  if (parts.length === 0) return `${decisions.length} total`;
  return parts.join(' · ');
}
