'use client';

/**
 * AgentContentView — Center panel content for a selected agent.
 *
 * ADR-167 v5 continued (2026-04-09): refactored block stream for
 * clarity. The v5 intro shipped with three residual problems caught in a
 * screenshot of /agents?agent=thinking-partner:
 *
 *   1. Duplicate titles. "Thinking Partner" appeared three times —
 *      breadcrumb chrome, SurfaceIdentityHeader h1, AND the first H1 of
 *      AGENT.md inside the nested instructions card. The nested-card
 *      framing wasn't enough to scope the third one because its text was
 *      literally identical to the surface H1.
 *   2. Mandate block was a duplicate of AGENT.md's first prose line. The
 *      full AGENT.md was rendered immediately below, including that same
 *      line. Dead weight.
 *   3. Metadata strip redundancy on agents where the class label equals
 *      the title (Thinking Partner → "Thinking Partner", Reporting →
 *      "Reporting"). The class segment was saying the same thing the h1
 *      was saying.
 *   4. `AGENT.MD` section label leaked the filesystem abstraction into
 *      the UI. Users shouldn't need to know the file exists.
 *   5. Block order was reference-first (instructions) then state (tasks),
 *      but the user's actual first question on an agent page is "what's
 *      this agent doing for me?" — which is state.
 *
 * Fixes applied in this rewrite:
 *
 *   - Mandate block DELETED entirely (with its `extractMandate` helper).
 *   - New `stripLeadingH1IfMatchesTitle()` helper preprocesses AGENT.md
 *     content: if the first non-blank line is an H1 whose text matches
 *     the agent title (case-insensitive), strip it plus any trailing
 *     blank lines. Safely handles both rich AGENT.md (with H1) and
 *     default one-paragraph content (no H1) — the latter is a no-op.
 *   - Instructions section label changed from `AGENT.md` to `How I work`.
 *   - Block order changed to state-first: AssignedWork → LearnedFromYou
 *     → HowIWork → footer stats.
 *   - `AgentMetadata` now skips the class-label segment when it equals
 *     the agent title (case-insensitive). TP and Reporting no longer
 *     self-duplicate.
 *
 * The overall shape is still: SurfaceIdentityHeader at top, stream of
 * blocks below, quiet stats + affordances at the footer. ADR-167 v5 is
 * unchanged; this is a content-model fix, not a layout change.
 */

import Link from 'next/link';
import {
  Briefcase,
  FolderOpen,
  MessageSquare,
  Sparkles,
  TrendingUp,
  TrendingDown,
  Minus,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { WorkModeBadge } from '@/components/work/WorkModeBadge';
import { SurfaceIdentityHeader } from '@/components/shell/SurfaceIdentityHeader';
import { formatRelativeTime } from '@/lib/formatting';
import { WORK_ROUTE, CONTEXT_ROUTE } from '@/lib/routes';
import type { Agent, Task } from '@/types';

// Singular, user-facing class labels. Must stay in sync with the section
// titles in AgentRosterSurface.tsx.
const CLASS_LABELS: Record<string, string> = {
  'domain-steward': 'Specialist',
  'synthesizer': 'Reporting',
  'platform-bot': 'Integration',
  'meta-cognitive': 'Thinking Partner',
};

interface AgentContentViewProps {
  agent: Agent;
  tasks: Task[];
  onOpenChat: (prompt?: string) => void;
}

// ───────────────────────────────────────────────────────────────
// Helpers
// ───────────────────────────────────────────────────────────────

/**
 * Strip the leading H1 from AGENT.md if its text matches the agent title
 * (case-insensitive exact match). This handles the "rich AGENT.md" case
 * where the authored content starts with `# Thinking Partner\n\n## Domain`
 * and would otherwise duplicate the SurfaceIdentityHeader h1 directly
 * above it. For the default-instructions case (no leading H1), returns
 * the content unchanged.
 *
 * Preserves everything else: if the leading H1 is DIFFERENT from the
 * title (unusual but possible — an agent renamed after AGENT.md was
 * authored), the H1 stays so the reader doesn't lose context. We only
 * strip when it's provably redundant.
 */
function stripLeadingH1IfMatchesTitle(
  content: string,
  title: string,
): string {
  const lines = content.split('\n');
  // Skip any leading blank lines
  let i = 0;
  while (i < lines.length && lines[i].trim() === '') i++;
  if (i >= lines.length) return content;

  const firstLine = lines[i].trim();
  if (!firstLine.startsWith('# ') || firstLine.startsWith('## ')) return content;

  const h1Text = firstLine.slice(2).trim();
  if (h1Text.toLowerCase() !== title.toLowerCase()) return content;

  // H1 matches title — strip it plus any trailing blank lines after it.
  let j = i + 1;
  while (j < lines.length && lines[j].trim() === '') j++;
  return lines.slice(j).join('\n');
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/40 mb-2">
      {children}
    </h3>
  );
}

// ───────────────────────────────────────────────────────────────
// Identity metadata (under SurfaceIdentityHeader h1)
// ───────────────────────────────────────────────────────────────

function AgentMetadata({ agent, tasks }: { agent: Agent; tasks: Task[] }) {
  const cls = agent.agent_class || 'domain-steward';
  const classLabel = CLASS_LABELS[cls] || cls;
  // Skip the class-label segment if it would duplicate the h1 above
  // (happens for Thinking Partner and Reporting where the class label
  // equals the agent title by design).
  const showClassLabel = classLabel.toLowerCase() !== agent.title.toLowerCase();
  const domain = agent.context_domain;
  const activeTaskCount = tasks.filter(t => t.status === 'active').length;
  const lastRun = tasks
    .map(t => t.last_run_at)
    .filter(Boolean)
    .sort()
    .reverse()[0] || agent.last_run_at || null;

  const segments: React.ReactNode[] = [];
  if (showClassLabel) segments.push(<span key="class">{classLabel}</span>);
  if (domain) segments.push(<span key="domain">{domain}/</span>);
  segments.push(
    <span key="tasks">
      {activeTaskCount} active {activeTaskCount === 1 ? 'task' : 'tasks'}
    </span>,
  );
  if (lastRun) segments.push(<span key="last-run">Ran {formatRelativeTime(lastRun)}</span>);

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      {segments.map((seg, i) => (
        <span key={i} className="flex items-center gap-1.5">
          {i > 0 && <span className="text-muted-foreground/30">·</span>}
          {seg}
        </span>
      ))}
    </div>
  );
}

// ───────────────────────────────────────────────────────────────
// Blocks
// ───────────────────────────────────────────────────────────────

function TasksBlock({ tasks }: { tasks: Task[] }) {
  if (tasks.length === 0) {
    return (
      <div className="px-6 py-5 border-t border-border/40">
        <SectionLabel>Assigned work</SectionLabel>
        <p className="text-sm text-muted-foreground/70">
          No tasks assigned yet.
        </p>
      </div>
    );
  }

  // Active first, then paused, then archived — all by last_run recency.
  const sorted = [...tasks].sort((a, b) => {
    const statusOrder: Record<string, number> = { active: 0, paused: 1, archived: 2 };
    const s = (statusOrder[a.status] ?? 3) - (statusOrder[b.status] ?? 3);
    if (s !== 0) return s;
    const at = a.last_run_at ? new Date(a.last_run_at).getTime() : 0;
    const bt = b.last_run_at ? new Date(b.last_run_at).getTime() : 0;
    return bt - at;
  });

  return (
    <div className="px-6 py-5 border-t border-border/40">
      <SectionLabel>Assigned work · {tasks.length}</SectionLabel>
      <div className="space-y-1">
        {sorted.map(task => (
          <Link
            key={task.id}
            href={`${WORK_ROUTE}?task=${encodeURIComponent(task.slug)}`}
            className={cn(
              'group flex items-center gap-3 rounded-md border border-border/40 bg-background hover:bg-muted/30 hover:border-border transition-colors px-3 py-2',
              task.status !== 'active' && 'opacity-60',
            )}
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium truncate">{task.title}</span>
                <WorkModeBadge mode={task.mode} />
                {task.status === 'paused' && (
                  <span className="text-[10px] rounded-full bg-amber-500/10 text-amber-700 px-1.5 py-0.5">
                    paused
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2 mt-0.5 text-[11px] text-muted-foreground">
                {task.schedule && <span className="truncate">{task.schedule}</span>}
                {task.schedule && task.last_run_at && <span className="text-muted-foreground/30">·</span>}
                {task.last_run_at && <span>Ran {formatRelativeTime(task.last_run_at)}</span>}
                {!task.last_run_at && !task.schedule && <span>never run</span>}
              </div>
            </div>
            <ChevronRight className="w-4 h-4 text-muted-foreground/30 group-hover:text-muted-foreground/70 shrink-0" />
          </Link>
        ))}
      </div>
    </div>
  );
}

function LearnedBlock({ agent }: { agent: Agent }) {
  const feedback = agent.agent_memory?.feedback;
  const reflections = agent.agent_memory?.reflections;
  if (!feedback && !reflections) return null;

  return (
    <div className="px-6 py-5 border-t border-border/40 space-y-5">
      {feedback && (
        <div>
          <SectionLabel>
            <span className="inline-flex items-center gap-1.5">
              <Sparkles className="w-3 h-3" />
              Learned from your feedback
            </span>
          </SectionLabel>
          <div className="rounded-lg border border-border/60 bg-muted/10 px-4 py-3">
            <div className="prose prose-sm max-w-none dark:prose-invert text-sm">
              <MarkdownRenderer content={feedback} />
            </div>
          </div>
        </div>
      )}
      {reflections && (
        <div>
          <SectionLabel>Recent reflections</SectionLabel>
          <div className="rounded-lg border border-border/60 bg-muted/10 px-4 py-3">
            <div className="prose prose-sm max-w-none dark:prose-invert text-sm">
              <MarkdownRenderer content={reflections} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function InstructionsBlock({ agent }: { agent: Agent }) {
  if (!agent.agent_instructions) return null;
  const content = stripLeadingH1IfMatchesTitle(agent.agent_instructions, agent.title);
  if (!content.trim()) return null;

  return (
    <div className="px-6 py-5 border-t border-border/40">
      <SectionLabel>How I work</SectionLabel>
      <div className="rounded-lg border border-border/60 bg-muted/10 px-4 py-3">
        <div className="prose prose-sm max-w-none dark:prose-invert">
          <MarkdownRenderer content={content} />
        </div>
      </div>
    </div>
  );
}

function StatsStrip({ agent, tasks, onOpenChat }: { agent: Agent; tasks: Task[]; onOpenChat: (prompt?: string) => void }) {
  const totalRuns = agent.version_count ?? 0;
  // quality_score is "edit burden" (0=clean, 1=heavy). Approval = 1 - score.
  const approvalPct = agent.quality_score != null
    ? Math.round((1 - (agent.quality_score || 0)) * 100)
    : null;
  const trend = agent.quality_trend;
  const avgEdit = agent.avg_edit_distance;
  const domain = agent.context_domain;

  const hasStats = totalRuns > 0 || approvalPct != null || avgEdit != null;

  return (
    <div className="px-6 py-5 border-t border-border/40 space-y-4">
      {hasStats && (
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-muted-foreground">
          {totalRuns > 0 && (
            <span>
              <span className="font-medium text-foreground">{totalRuns}</span> {totalRuns === 1 ? 'run' : 'runs'}
            </span>
          )}
          {approvalPct != null && totalRuns >= 5 && (
            <span className="inline-flex items-center gap-1">
              <span className="font-medium text-foreground">{approvalPct}%</span> approved
              {trend === 'improving' && <TrendingUp className="w-3 h-3 text-green-500" />}
              {trend === 'declining' && <TrendingDown className="w-3 h-3 text-red-500" />}
              {trend === 'stable' && <Minus className="w-3 h-3 text-muted-foreground/50" />}
            </span>
          )}
          {avgEdit != null && totalRuns >= 5 && (
            <span>
              avg edit distance <span className="font-medium text-foreground">{avgEdit.toFixed(2)}</span>
            </span>
          )}
          <span className="text-muted-foreground/40">
            Created {new Date(agent.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}
          </span>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <Link
          href={`${WORK_ROUTE}?agent=${agent.slug}`}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
        >
          <Briefcase className="w-4 h-4" />
          See full work list
        </Link>
        {domain && (
          <Link
            href={`${CONTEXT_ROUTE}?domain=${domain}`}
            className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
          >
            <FolderOpen className="w-4 h-4" />
            Open /{domain}/
          </Link>
        )}
        <button
          onClick={() => onOpenChat(`Tell me about ${agent.title}`)}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground"
        >
          <MessageSquare className="w-4 h-4" />
          Ask about this agent
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// MAIN
// ═══════════════════════════════════════════════════════════════

export function AgentContentView({
  agent,
  tasks,
  onOpenChat,
}: AgentContentViewProps) {
  return (
    <div className="flex-1 overflow-auto">
      <SurfaceIdentityHeader
        title={agent.title}
        metadata={<AgentMetadata agent={agent} tasks={tasks} />}
      />
      <div className="max-w-3xl">
        {/* State first — what this agent is doing for you right now */}
        <TasksBlock tasks={tasks} />
        <LearnedBlock agent={agent} />
        {/* Reference second — how it works */}
        <InstructionsBlock agent={agent} />
        {/* Quiet footer — performance summary + affordances */}
        <StatsStrip agent={agent} tasks={tasks} onOpenChat={onOpenChat} />
      </div>
    </div>
  );
}
