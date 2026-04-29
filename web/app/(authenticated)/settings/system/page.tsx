'use client';

/**
 * /settings/system — Back-office diagnostic view (ADR-206).
 *
 * ADR-206: back-office-* tasks are plumbing, not operator-facing work. The default
 * `GET /api/recurrences` response filters them out. This page passes `include_system=true`
 * to surface them for operators who want to inspect YARNNN's infrastructure —
 * last-run, next-scheduled, pause/resume. Not a primary nav destination.
 *
 * Consumes the same Task shape as /work. No separate API. Minimal UI — a table
 * of back-office tasks with status + last/next run + pause toggle.
 */

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { Loader2, RefreshCw, Cog, Pause, Play, ArrowLeft } from 'lucide-react';
import { APIError, api } from '@/lib/api/client';
import type { Task } from '@/types';

async function fetchSystemTasks(): Promise<Task[]> {
  return api.recurrences.list({ include_system: true });
}

function formatDate(value?: string | null): string {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export default function SystemDiagnosticPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingSlug, setPendingSlug] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const all = await fetchSystemTasks();
      setTasks(all.filter(t => (t.slug || '').startsWith('back-office-')));
    } catch (err) {
      if (err instanceof APIError) setError(err.message);
      else if (err instanceof Error) setError(err.message);
      else setError('Failed to load system tasks');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const togglePause = async (task: Task) => {
    setPendingSlug(task.slug);
    try {
      const nextStatus = task.status === 'active' ? 'paused' : 'active';
      await api.recurrences.update(task.slug, { status: nextStatus });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Update failed');
    } finally {
      setPendingSlug(null);
    }
  };

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <Link
            href="/settings"
            className="mb-2 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-3 w-3" /> Settings
          </Link>
          <h1 className="flex items-center gap-2 text-xl font-semibold text-foreground">
            <Cog className="h-5 w-5" /> System tasks
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Back-office plumbing YARNNN runs to keep the workspace healthy. Hidden from{' '}
            <Link href="/work" className="underline underline-offset-2 hover:text-foreground">
              /work
            </Link>{' '}
            by default. Materializes on trigger — proposal-cleanup on first proposal,
            outcome-reconciliation on platform connect, agent-hygiene at run threshold.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          className="inline-flex items-center gap-1 rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : error ? (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      ) : tasks.length === 0 ? (
        <div className="rounded-md border border-border p-8 text-center">
          <p className="text-sm text-muted-foreground">
            No system tasks have materialized yet.
          </p>
          <p className="mt-1 text-xs text-muted-foreground/70">
            They'll appear as triggers fire: first proposal, first platform connect, or
            when user-authored agents accumulate runs.
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-md border border-border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-4 py-2 text-left">Slug</th>
                <th className="px-4 py-2 text-left">Status</th>
                <th className="px-4 py-2 text-left">Schedule</th>
                <th className="px-4 py-2 text-left">Last run</th>
                <th className="px-4 py-2 text-left">Next run</th>
                <th className="px-4 py-2 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map(task => (
                <tr key={task.id} className="border-t border-border">
                  <td className="px-4 py-2 font-mono text-xs text-foreground">{task.slug}</td>
                  <td className="px-4 py-2 text-xs">
                    <span
                      className={
                        task.status === 'active'
                          ? 'rounded bg-green-500/10 px-2 py-0.5 text-green-600'
                          : 'rounded bg-yellow-500/10 px-2 py-0.5 text-yellow-600'
                      }
                    >
                      {task.status}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-xs text-muted-foreground">{task.schedule ?? '—'}</td>
                  <td className="px-4 py-2 text-xs text-muted-foreground">{formatDate(task.last_run_at)}</td>
                  <td className="px-4 py-2 text-xs text-muted-foreground">{formatDate(task.next_run_at)}</td>
                  <td className="px-4 py-2 text-right">
                    <button
                      type="button"
                      disabled={pendingSlug === task.slug}
                      onClick={() => void togglePause(task)}
                      className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-50"
                    >
                      {pendingSlug === task.slug ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : task.status === 'active' ? (
                        <>
                          <Pause className="h-3 w-3" /> Pause
                        </>
                      ) : (
                        <>
                          <Play className="h-3 w-3" /> Resume
                        </>
                      )}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="mt-4 text-[11px] text-muted-foreground/60">
        ADR-206 · system tasks auto-materialize on trigger conditions; this view is diagnostic only.
      </p>
    </div>
  );
}
