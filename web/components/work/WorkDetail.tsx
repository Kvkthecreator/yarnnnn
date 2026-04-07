'use client';

/**
 * WorkDetail — Center panel for selected task on /work.
 *
 * ADR-163 Surface Restructure: This absorbs the Pipeline and Report content
 * that previously lived as tabs on the Agents page. A task's full detail
 * lives on /work now — schedule, next/last run, objective, output preview,
 * and actions (run now, pause/resume).
 *
 * Layout:
 *   - Pinned header: title, mode badge, assigned agent, essential badge
 *   - Objective block (from TASK.md)
 *   - Latest output preview (if any — iframe for HTML, markdown renderer for md)
 *   - Actions: Run now, Pause/Resume, Edit via TP (sends chat prompt)
 *   - Run history (compact list)
 *
 * The "Edit" and "Configure" paths all route back to TP chat — the source
 * of truth for task mutations is TASK.md, which is mutated by TP, not by
 * direct form posts.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Play,
  Pause,
  MessageSquare,
  Loader2,
  FileText,
  ExternalLink,
  Briefcase,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { formatRelativeTime } from '@/lib/formatting';
import { WorkModeBadge } from './WorkModeBadge';
import { AGENTS_ROUTE } from '@/lib/routes';
import type { Task, Agent, TaskOutput } from '@/types';

interface WorkDetailProps {
  task: Task;
  agents: Agent[];
  onRun: (slug: string) => void;
  onPause: (slug: string) => void;
  onOpenChat: (prompt?: string) => void;
  busy: boolean;
}

function findAssignedAgent(task: Task, agents: Agent[]): Agent | null {
  const assigned = task.agent_slugs?.[0];
  if (!assigned) return null;
  return agents.find(a => a.slug === assigned) ?? null;
}

// ─── Pinned Header ───

function WorkHeader({
  task,
  assignedAgent,
}: {
  task: Task;
  assignedAgent: Agent | null;
}) {
  return (
    <div className="px-5 py-3 border-b border-border shrink-0">
      <div className="flex items-center gap-2 mb-1">
        <h2 className="text-base font-semibold flex-1 truncate">{task.title}</h2>
        <WorkModeBadge mode={task.mode} />
        {task.essential && (
          <span
            className="text-[10px] rounded-full bg-amber-500/10 text-amber-700 px-2 py-0.5 font-medium"
            title="This task is essential to your workspace (ADR-161)"
          >
            ★ Essential
          </span>
        )}
      </div>
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <span className="capitalize">{task.status}</span>
        {assignedAgent && (
          <>
            <span className="text-muted-foreground/30">·</span>
            <Link
              href={`${AGENTS_ROUTE}?agent=${assignedAgent.slug}`}
              className="hover:text-foreground hover:underline"
            >
              {assignedAgent.title}
            </Link>
          </>
        )}
        {task.schedule && (
          <>
            <span className="text-muted-foreground/30">·</span>
            <span className="capitalize">{task.schedule}</span>
          </>
        )}
      </div>
      <div className="flex items-center gap-1.5 mt-1 text-[11px] text-muted-foreground/70">
        {task.next_run_at && <span>Next: {formatRelativeTime(task.next_run_at)}</span>}
        {task.next_run_at && task.last_run_at && <span className="text-muted-foreground/30">·</span>}
        {task.last_run_at && <span>Last: {formatRelativeTime(task.last_run_at)}</span>}
        {!task.next_run_at && !task.last_run_at && <span>Never run</span>}
      </div>
    </div>
  );
}

// ─── Objective ───

function ObjectiveBlock({ task }: { task: Task }) {
  if (!task.objective) return null;
  const { deliverable, audience, purpose, format } = task.objective;
  if (!deliverable && !audience && !purpose && !format) return null;

  return (
    <div className="px-5 py-4 border-b border-border/40">
      <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/40 mb-2">Objective</h3>
      <div className="text-xs text-muted-foreground space-y-0.5">
        {deliverable && <p>· Deliverable: {deliverable}</p>}
        {audience && <p>· Audience: {audience}</p>}
        {purpose && <p>· Purpose: {purpose}</p>}
        {format && <p>· Format: {format}</p>}
      </div>
    </div>
  );
}

// ─── Output preview ───

function OutputPreview({ taskSlug }: { taskSlug: string }) {
  const [loading, setLoading] = useState(true);
  const [latest, setLatest] = useState<TaskOutput | null>(null);

  useEffect(() => {
    setLoading(true);
    setLatest(null);
    api.tasks.getLatestOutput(taskSlug)
      .then(result => setLatest(result))
      .catch(() => setLatest(null))
      .finally(() => setLoading(false));
  }, [taskSlug]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!latest || (!latest.html_content && !latest.content)) {
    return (
      <div className="px-5 py-8 text-center">
        <FileText className="w-6 h-6 text-muted-foreground/15 mx-auto mb-2" />
        <p className="text-xs text-muted-foreground/60">
          No output yet. This task will produce its first output on its next run.
        </p>
      </div>
    );
  }

  return (
    <div className="border-b border-border/40">
      <div className="px-5 py-2 text-[11px] text-muted-foreground/60 flex items-center gap-2">
        <span>Latest output</span>
        {latest.date && (
          <>
            <span className="text-muted-foreground/30">·</span>
            <span>{latest.date}</span>
          </>
        )}
      </div>
      <div className="min-h-[300px] max-h-[600px] overflow-auto">
        {latest.html_content ? (
          <iframe
            srcDoc={latest.html_content}
            className="h-[600px] w-full border-0 bg-white"
            sandbox="allow-same-origin allow-scripts"
            title={`${taskSlug} output`}
          />
        ) : (
          <div className="p-5">
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <MarkdownRenderer content={latest.content ?? ''} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Actions ───

function ActionsRow({
  task,
  onRun,
  onPause,
  onOpenChat,
  busy,
}: {
  task: Task;
  onRun: () => void;
  onPause: () => void;
  onOpenChat: (prompt?: string) => void;
  busy: boolean;
}) {
  const isActive = task.status === 'active';
  const pauseDisabled = busy || (task.essential && isActive === false);

  return (
    <div className="px-5 py-4 flex items-center gap-2 flex-wrap">
      <button
        onClick={onRun}
        disabled={busy || !isActive}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded bg-primary/10 text-primary hover:bg-primary/20 disabled:opacity-50"
      >
        <Play className="w-3 h-3" /> Run now
      </button>
      <button
        onClick={onPause}
        disabled={pauseDisabled}
        className={cn(
          'inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded border border-border',
          'text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-50',
        )}
        title={
          task.essential && !isActive
            ? 'Essential tasks can be paused but pausing this one leaves you without a daily check-in.'
            : undefined
        }
      >
        {isActive ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
        {isActive ? 'Pause' : 'Resume'}
      </button>
      <button
        onClick={() => onOpenChat(`I want to update the task "${task.title}"`)}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded border border-border text-muted-foreground hover:text-foreground hover:bg-muted ml-auto"
      >
        <MessageSquare className="w-3 h-3" /> Edit via chat
      </button>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// MAIN
// ═══════════════════════════════════════════════════════════════

export function WorkDetail({
  task,
  agents,
  onRun,
  onPause,
  onOpenChat,
  busy,
}: WorkDetailProps) {
  const assignedAgent = findAssignedAgent(task, agents);

  return (
    <div className="flex flex-col h-full">
      <WorkHeader task={task} assignedAgent={assignedAgent} />
      <div className="flex-1 overflow-auto">
        <ObjectiveBlock task={task} />
        <OutputPreview taskSlug={task.slug} />
        <ActionsRow
          task={task}
          onRun={() => onRun(task.slug)}
          onPause={() => onPause(task.slug)}
          onOpenChat={onOpenChat}
          busy={busy}
        />
        {assignedAgent && (
          <div className="px-5 py-3 border-t border-border/40">
            <Link
              href={`${AGENTS_ROUTE}?agent=${assignedAgent.slug}`}
              className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
            >
              <Briefcase className="w-3 h-3" />
              Assigned to {assignedAgent.title}
              <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
