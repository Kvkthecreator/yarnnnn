'use client';

/**
 * DailyBriefing — Persistent collapsible header for the Home page.
 *
 * ONBOARDING-SCAFFOLD-AND-BRIEFING.md: Always rendered above chat.
 * Starts expanded on page load. Auto-collapses after first message.
 * User can manually toggle. Collapse state persists in localStorage.
 *
 * Three sections: What happened, Coming up, Needs attention.
 * Data sourced from agents + tasks API (no LLM cost).
 */

import { useState, useEffect, useMemo } from 'react';
import { ChevronDown, ChevronUp, Circle, Clock, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Agent, Task } from '@/types';

interface DailyBriefingProps {
  agents: Agent[];
  tasks: Task[];
  hasMessages: boolean;
}

const STORAGE_KEY = 'yarnnn-briefing-collapsed';

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
  const future = diff < 0;
  const absDiff = Math.abs(diff);
  const mins = Math.floor(absDiff / 60000);
  if (mins < 1) return future ? 'soon' : 'just now';
  if (mins < 60) return future ? `in ${mins}m` : `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return future ? `in ${hours}h` : `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return future ? `in ${days}d` : `${days}d ago`;
}

function getAgentSlug(agent: Agent): string {
  return agent.slug || agent.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
}

export function DailyBriefing({ agents, tasks, hasMessages }: DailyBriefingProps) {
  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window === 'undefined') return false;
    return localStorage.getItem(STORAGE_KEY) === 'true';
  });

  // Auto-collapse when user sends first message
  useEffect(() => {
    if (hasMessages && !collapsed) {
      setCollapsed(true);
      localStorage.setItem(STORAGE_KEY, 'true');
    }
  }, [hasMessages]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggle = () => {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem(STORAGE_KEY, String(next));
  };

  // ── Derive briefing data ──

  const activeTasks = useMemo(() => tasks.filter(t => t.status === 'active'), [tasks]);

  // What happened: tasks that ran in last 24h
  const recentRuns = useMemo(() => {
    const cutoff = Date.now() - 24 * 60 * 60 * 1000;
    return tasks
      .filter(t => t.last_run_at && new Date(t.last_run_at).getTime() > cutoff)
      .map(t => {
        const agentSlug = t.agent_slugs?.[0];
        const agent = agents.find(a => getAgentSlug(a) === agentSlug);
        return { task: t, agentTitle: agent?.title || agentSlug || t.title };
      });
  }, [tasks, agents]);

  // Coming up: next scheduled runs grouped by timeframe
  const comingUp = useMemo(() => {
    return activeTasks
      .filter(t => t.next_run_at)
      .sort((a, b) => new Date(a.next_run_at!).getTime() - new Date(b.next_run_at!).getTime())
      .slice(0, 5)
      .map(t => {
        const agentSlug = t.agent_slugs?.[0];
        const agent = agents.find(a => getAgentSlug(a) === agentSlug);
        return { task: t, agentTitle: agent?.title || t.title };
      });
  }, [activeTasks, agents]);

  // Needs attention: agents with 0 tasks, or tasks that failed
  const needsAttention = useMemo(() => {
    const items: { message: string; severity: 'warn' | 'info' }[] = [];

    // Agents with no tasks (domain stewards only — bots and synthesizers may legitimately have none)
    agents
      .filter(a => (a.agent_class || 'domain-steward') === 'domain-steward')
      .forEach(a => {
        const slug = getAgentSlug(a);
        const agentTasks = tasks.filter(t => t.agent_slugs?.includes(slug));
        if (agentTasks.length === 0) {
          items.push({ message: `${a.title} has no tasks — needs setup`, severity: 'info' });
        }
      });

    return items;
  }, [agents, tasks]);

  // Summary line for collapsed state
  const summaryParts: string[] = [];
  if (recentRuns.length > 0) summaryParts.push(`${recentRuns.length} ran`);
  if (comingUp.length > 0) summaryParts.push(`${comingUp.length} coming up`);
  if (needsAttention.length > 0) summaryParts.push(`${needsAttention.length} attention`);
  const summary = summaryParts.join(' · ') || 'No activity yet';

  const today = new Date().toLocaleDateString(undefined, { month: 'short', day: 'numeric' });

  // ── Render ──

  if (collapsed) {
    return (
      <button
        onClick={toggle}
        className="w-full flex items-center gap-2 px-4 py-2 text-xs border-b border-border bg-muted/20 hover:bg-muted/40 transition-colors"
      >
        <span className="font-medium text-muted-foreground">Daily Briefing</span>
        <span className="text-muted-foreground/60">{summary}</span>
        <ChevronDown className="w-3 h-3 text-muted-foreground/40 ml-auto shrink-0" />
      </button>
    );
  }

  return (
    <div className="border-b border-border bg-muted/10">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium">Daily Briefing</span>
          <span className="text-[10px] text-muted-foreground/50">{today}</span>
        </div>
        <button onClick={toggle} className="p-1 text-muted-foreground/40 hover:text-muted-foreground rounded">
          <ChevronUp className="w-3 h-3" />
        </button>
      </div>

      <div className="px-4 pb-3 space-y-3">
        {/* What happened */}
        {recentRuns.length > 0 && (
          <div>
            <p className="text-[10px] uppercase tracking-wide text-muted-foreground/50 mb-1">What happened</p>
            <div className="space-y-0.5">
              {recentRuns.map(({ task, agentTitle }) => (
                <div key={task.slug} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Circle className="w-1.5 h-1.5 fill-green-500 text-green-500 shrink-0" />
                  <span className="truncate">{agentTitle}: {task.title}</span>
                  {task.last_run_at && (
                    <span className="text-muted-foreground/40 shrink-0 ml-auto">{formatRelativeTime(task.last_run_at)}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Coming up */}
        {comingUp.length > 0 && (
          <div>
            <p className="text-[10px] uppercase tracking-wide text-muted-foreground/50 mb-1">Coming up</p>
            <div className="space-y-0.5">
              {comingUp.map(({ task, agentTitle }) => (
                <div key={task.slug} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Clock className="w-3 h-3 text-muted-foreground/30 shrink-0" />
                  <span className="truncate">{agentTitle}</span>
                  {task.next_run_at && (
                    <span className="text-muted-foreground/40 shrink-0 ml-auto">{formatRelativeTime(task.next_run_at)}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Needs attention */}
        {needsAttention.length > 0 && (
          <div>
            <p className="text-[10px] uppercase tracking-wide text-muted-foreground/50 mb-1">Needs attention</p>
            <div className="space-y-0.5">
              {needsAttention.map((item, i) => (
                <div key={i} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <AlertCircle className={cn('w-3 h-3 shrink-0', item.severity === 'warn' ? 'text-amber-500' : 'text-muted-foreground/30')} />
                  <span>{item.message}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* No activity fallback */}
        {recentRuns.length === 0 && comingUp.length === 0 && needsAttention.length === 0 && (
          <p className="text-xs text-muted-foreground/40">No activity yet. Your agents will start working once tasks are set up.</p>
        )}

        {/* Workspace signals (inline) */}
        <div className="flex items-center gap-3 text-[10px] text-muted-foreground/40 pt-1 border-t border-border/50">
          <span>{agents.length} agents</span>
          <span>{activeTasks.length} active tasks</span>
          <span>{tasks.filter(t => t.task_class === 'context').length} tracking</span>
          <span>{tasks.filter(t => t.task_class === 'synthesis').length} reporting</span>
        </div>
      </div>
    </div>
  );
}
