'use client';

/**
 * MaintenanceMiddle — Detail middle band for `output_kind: system_maintenance`.
 *
 * ADR-167 v5: the latest hygiene log markdown is wrapped in a bordered,
 * inset card for consistency with DeliverableMiddle and TrackingMiddle.
 * The nested-document pattern keeps the log's internal headers subordinate
 * to the task's real H1 in SurfaceIdentityHeader above.
 *
 * For TP-owned back office tasks (back-office-agent-hygiene,
 * back-office-workspace-cleanup) — these run deterministic Python (no LLM,
 * no playbooks). The user wants to know:
 *
 *   1. Did it run? (run history)
 *   2. What did it touch? (hygiene log markdown from output)
 *
 * No DELIVERABLE.md emphasis — TP owns the contract, not the user.
 */

import { useEffect, useState } from 'react';
import { Loader2, Wrench, CheckCircle2, AlertCircle } from 'lucide-react';
import { formatRelativeTime } from '@/lib/formatting';
import { api } from '@/lib/api/client';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import type { Task, TaskOutput } from '@/types';

export function MaintenanceMiddle({ task }: { task: Task }) {
  const [loading, setLoading] = useState(true);
  const [latest, setLatest] = useState<TaskOutput | null>(null);
  const [history, setHistory] = useState<TaskOutput[]>([]);

  useEffect(() => {
    setLoading(true);
    setLatest(null);
    setHistory([]);
    Promise.all([
      api.tasks.getLatestOutput(task.slug).catch(() => null),
      api.tasks.listOutputs(task.slug, 10).catch(() => ({ outputs: [] as TaskOutput[], total: 0 })),
    ])
      .then(([l, h]) => {
        setLatest(l);
        setHistory(h.outputs ?? []);
      })
      .finally(() => setLoading(false));
  }, [task.slug]);

  return (
    <>
      {/* Maintenance framing */}
      <div className="px-6 py-4 border-b border-border/40">
        <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/40 mb-2">
          Back Office Task
        </h3>
        <div className="flex items-start gap-2">
          <Wrench className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
          <p className="text-xs text-muted-foreground">
            This task is owned by Thinking Partner. It runs deterministic
            maintenance on your workspace — no LLM call, no quality gate. The
            artifact is a hygiene log of what it touched on each run.
          </p>
        </div>
      </div>

      {/* Latest hygiene log in a nested card */}
      <div className="px-6 py-4">
        <div className="flex items-center gap-2 mb-2">
          <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/40">Latest hygiene log</h3>
          {latest?.date && (
            <>
              <span className="text-muted-foreground/30 text-[10px]">·</span>
              <span className="text-[10px] text-muted-foreground/60">{latest.date}</span>
            </>
          )}
        </div>
        <div className="rounded-lg border border-border bg-muted/5 overflow-hidden">
          <div className="max-h-[400px] overflow-auto p-5">
            {loading ? (
              <div className="flex items-center justify-center py-2">
                <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
              </div>
            ) : latest && (latest.content || latest.md_content) ? (
              <div className="prose prose-sm max-w-none dark:prose-invert">
                <MarkdownRenderer content={latest.content ?? latest.md_content ?? ''} />
              </div>
            ) : (
              <p className="text-xs text-muted-foreground/60">
                No log yet. After the first run, you'll see what was cleaned up,
                paused, or otherwise acted on here.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Run history */}
      {history.length > 1 && (
        <div className="px-6 py-4 border-t border-border/40">
          <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/40 mb-2">Run history</h3>
          <ul className="divide-y divide-border/40">
            {history.map(o => {
              const ok =
                o.status === 'active' ||
                o.status === 'completed' ||
                o.status === 'delivered';
              return (
                <li key={o.folder} className="py-2 flex items-center gap-2">
                  {ok ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-green-500 shrink-0" />
                  ) : (
                    <AlertCircle className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                  )}
                  <span className="text-xs text-foreground">{o.date}</span>
                  <span className="text-[10px] text-muted-foreground/50">
                    ({formatRelativeTime(o.date)})
                  </span>
                  <span className="ml-auto text-[10px] text-muted-foreground/50 capitalize">
                    {o.status}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </>
  );
}
