'use client';

/**
 * AgentContentView — Center panel content for selected agent.
 *
 * ADR-167 v2: This component is now content-only. The agent name, class,
 * domain, active task count, and last-run metadata all moved UP into the
 * page-level <PageHeader /> rendered by `app/(authenticated)/agents/page.tsx`.
 * AgentContentView renders only:
 *
 *   - IdentityCard (role, origin, AGENT.md instructions, distilled feedback)
 *   - HealthCard (stats + link-outs to /work and /context)
 *
 * The agent's first sentence ("mandate") that used to live in the in-component
 * AgentHeader has been dropped — the breadcrumb + page metadata strip already
 * declares "you are looking at this agent" without needing a tagline.
 */

import Link from 'next/link';
import {
  Briefcase,
  FolderOpen,
  MessageSquare,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { formatRelativeTime } from '@/lib/formatting';
import { WORK_ROUTE, CONTEXT_ROUTE } from '@/lib/routes';
import type { Agent, Task } from '@/types';

interface AgentContentViewProps {
  agent: Agent;
  tasks: Task[];
  onOpenChat: (prompt?: string) => void;
}

const CLASS_LABELS: Record<string, string> = {
  'domain-steward': 'Domain Steward',
  'synthesizer': 'Synthesizer',
  'platform-bot': 'Platform Bot',
  'meta-cognitive': 'Thinking Partner',
};

// ─── Identity Card ───

function IdentityCard({ agent }: { agent: Agent }) {
  const cls = agent.agent_class || 'domain-steward';
  const classLabel = CLASS_LABELS[cls] || cls;

  return (
    <div className="px-5 py-4 space-y-4">
      <div className="space-y-2">
        <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/40">Identity</h3>
        <div className="text-xs text-muted-foreground space-y-1">
          <p>· Name: {agent.title}</p>
          <p>· Role: {agent.role} ({classLabel})</p>
          {agent.context_domain && <p>· Domain: {agent.context_domain}/</p>}
          {agent.origin && <p>· Origin: {agent.origin.replace(/_/g, ' ')}</p>}
          <p>
            · Created:{' '}
            {new Date(agent.created_at).toLocaleDateString(undefined, {
              year: 'numeric', month: 'long', day: 'numeric',
            })}
          </p>
        </div>
      </div>

      {agent.agent_instructions && (
        <div className="space-y-2">
          <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/40">Instructions (AGENT.md)</h3>
          <div className="rounded-lg border border-border bg-muted/10 p-3">
            <div className="prose prose-sm max-w-none dark:prose-invert text-xs">
              <MarkdownRenderer content={agent.agent_instructions} />
            </div>
          </div>
        </div>
      )}

      {agent.agent_memory?.feedback && (
        <div className="space-y-2">
          <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/40">Feedback Distilled</h3>
          <div className="rounded-lg border border-border bg-muted/10 p-3">
            <div className="prose prose-sm max-w-none dark:prose-invert text-xs">
              <MarkdownRenderer content={agent.agent_memory.feedback} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Health Card ───

function HealthCard({
  agent,
  tasks,
  onOpenChat,
}: {
  agent: Agent;
  tasks: Task[];
  onOpenChat: (prompt?: string) => void;
}) {
  const activeTaskCount = tasks.filter(t => t.status === 'active').length;
  const totalRuns = agent.version_count ?? 0;
  const approvalPct = agent.quality_score != null
    ? Math.round((1 - (agent.quality_score || 0)) * 100)
    : null;
  const trend = agent.quality_trend;
  const domain = agent.context_domain;

  return (
    <div className="px-5 py-4 space-y-4 border-t border-border">
      <div className="space-y-2">
        <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/40">Health</h3>
        <div className="text-xs text-muted-foreground space-y-1">
          <p>· Tasks assigned: {activeTaskCount}</p>
          {totalRuns > 0 && <p>· Total runs: {totalRuns}</p>}
          {approvalPct != null && totalRuns >= 5 && (
            <p>
              · Approval rate: {approvalPct}%
              {trend && (
                <span className={cn(
                  'ml-1',
                  trend === 'improving' && 'text-green-500',
                  trend === 'declining' && 'text-red-500',
                )}>
                  ({trend === 'improving' ? '↑' : trend === 'declining' ? '↓' : '→'} {trend})
                </span>
              )}
            </p>
          )}
          {agent.last_run_at && <p>· Last run: {formatRelativeTime(agent.last_run_at)}</p>}
        </div>
      </div>

      {/* Links out */}
      <div className="space-y-2 pt-2">
        <Link
          href={`${WORK_ROUTE}?agent=${agent.slug}`}
          className="flex items-center gap-2 text-sm font-medium text-primary hover:underline"
        >
          <Briefcase className="w-4 h-4" />
          See this agent's work
        </Link>
        {domain && (
          <Link
            href={`${CONTEXT_ROUTE}?domain=${domain}`}
            className="flex items-center gap-2 text-sm font-medium text-primary hover:underline"
          >
            <FolderOpen className="w-4 h-4" />
            See this agent's context domain
          </Link>
        )}
        <button
          onClick={() => onOpenChat(`Tell me about ${agent.title}`)}
          className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground"
        >
          <MessageSquare className="w-4 h-4" />
          Chat about this agent
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// MAIN — Identity-only view (ADR-163 + ADR-167 v2)
// ═══════════════════════════════════════════════════════════════

export function AgentContentView({
  agent,
  tasks,
  onOpenChat,
}: AgentContentViewProps) {
  return (
    <div className="flex-1 overflow-auto">
      <IdentityCard agent={agent} />
      <HealthCard agent={agent} tasks={tasks} onOpenChat={onOpenChat} />
    </div>
  );
}
