'use client';

/**
 * AgentContentView — Center panel for selected agent.
 *
 * ADR-163 Surface Restructure: The Agents page shrinks to roster + identity
 * only. The tab-based layout (Report / Data / Pipeline / Agent from v7.2) is
 * gone. Work observation lives on /work, context browsing lives on /context.
 * The Agents page answers exactly one question: "Who is this agent, and are
 * they healthy?"
 *
 * Three sections in one scrollable view:
 *   1. Pinned header (avatar, name, class, domain, mandate)
 *   2. Identity card (AGENT.md instructions, role, origin, creation date)
 *   3. Health card (tasks assigned count, approval rate, last run) + links out
 */

import Link from 'next/link';
import {
  Layers,
  Brain,
  Plug,
  Briefcase,
  FolderOpen,
  MessageSquare,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { avatarColor } from '@/lib/agent-identity';
import { formatRelativeTime } from '@/lib/formatting';
import { WORK_ROUTE, CONTEXT_ROUTE } from '@/lib/routes';
import type { Agent, Task } from '@/types';

interface AgentContentViewProps {
  agent: Agent;
  tasks: Task[];
  onOpenChat: (prompt?: string) => void;
}

function getAgentMandate(agent: Agent): string | null {
  if (!agent.agent_instructions) return null;
  const first = agent.agent_instructions.split(/\.\s/)[0];
  return first ? first + '.' : null;
}

const CLASS_LABELS: Record<string, string> = {
  'domain-steward': 'Domain Steward',
  'synthesizer': 'Synthesizer',
  'platform-bot': 'Platform Bot',
};

function HeaderIcon({ agentClass }: { agentClass: string }) {
  const cls = 'w-5 h-5';
  switch (agentClass) {
    case 'synthesizer': return <Layers className={cls} />;
    case 'platform-bot': return <Plug className={cls} />;
    default: return <Brain className={cls} />;
  }
}

// ─── Pinned Header ───

function AgentHeader({ agent, tasks }: { agent: Agent; tasks: Task[] }) {
  const cls = agent.agent_class || 'domain-steward';
  const classLabel = CLASS_LABELS[cls] || cls;
  const domain = agent.context_domain;
  const color = avatarColor(agent.role);
  const mandate = getAgentMandate(agent);
  const activeTaskCount = tasks.filter(t => t.status === 'active').length;
  const lastRun = tasks.map(t => t.last_run_at).filter(Boolean).sort().reverse()[0];

  return (
    <div className="px-5 py-3 border-b border-border shrink-0">
      {/* Line 1: Avatar + Name + Mandate */}
      <div className="flex items-center gap-3">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
          style={{ backgroundColor: color + '18' }}
        >
          <div style={{ color }}><HeaderIcon agentClass={cls} /></div>
        </div>
        <div className="flex-1 min-w-0">
          <h2 className="text-base font-semibold truncate">{agent.title}</h2>
          {mandate && <p className="text-xs text-muted-foreground line-clamp-1 mt-0.5">{mandate}</p>}
        </div>
      </div>

      {/* Line 2: Identity signals */}
      <div className="flex items-center gap-1.5 mt-2 text-xs text-muted-foreground">
        <span>{classLabel}</span>
        {domain && (
          <><span className="text-muted-foreground/30">·</span><span>{domain}/</span></>
        )}
        <span className="text-muted-foreground/30">·</span>
        <span>{activeTaskCount} active {activeTaskCount === 1 ? 'task' : 'tasks'}</span>
        {lastRun && (
          <><span className="text-muted-foreground/30">·</span><span>Ran {formatRelativeTime(lastRun)}</span></>
        )}
      </div>
    </div>
  );
}

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
// MAIN — Identity-only view (ADR-163)
// ═══════════════════════════════════════════════════════════════

export function AgentContentView({
  agent,
  tasks,
  onOpenChat,
}: AgentContentViewProps) {
  return (
    <div className="flex flex-col h-full">
      <AgentHeader agent={agent} tasks={tasks} />
      <div className="flex-1 overflow-auto">
        <IdentityCard agent={agent} />
        <HealthCard agent={agent} tasks={tasks} onOpenChat={onOpenChat} />
      </div>
    </div>
  );
}
