'use client';

/**
 * Agents List — ADR-140
 *
 * Two sections:
 * 1. Workforce types explainer (what kinds of agents/bots exist)
 * 2. Your agents (existing agent cards with links to /agents/[id])
 *
 * ADR-140: 6 workforce types — 4 agents (research, content, marketing, crm) + 2 bots (slack_bot, notion_bot)
 */

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Users,
  Loader2,
  ChevronRight,
  FlaskConical,
  FileText,
  TrendingUp,
  MessageCircle,
  BookOpen,
} from 'lucide-react';
import type { Agent } from '@/types';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';

// =============================================================================
// Workforce Types — ADR-140
// =============================================================================

const WORKFORCE_TYPES = [
  {
    name: 'Research Agent',
    icon: FlaskConical,
    color: 'text-blue-500',
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/20',
    description: 'Investigates and analyzes topics across sources.',
    examples: 'Market analysis, competitor tracking, trend reports, Slack recaps',
    capabilities: ['Web search', 'Read platforms', 'Charts'],
    roles: ['research', 'briefer', 'monitor', 'scout', 'digest', 'researcher', 'analyst', 'synthesize', 'custom'],
  },
  {
    name: 'Content Agent',
    icon: FileText,
    color: 'text-purple-500',
    bg: 'bg-purple-500/10',
    border: 'border-purple-500/20',
    description: 'Creates deliverables from accumulated context.',
    examples: 'Investor updates, board decks, client reports, plans',
    capabilities: ['Read workspace', 'Charts', 'Compose HTML'],
    roles: ['content', 'drafter', 'writer', 'planner', 'prepare'],
  },
  {
    name: 'Marketing Agent',
    icon: TrendingUp,
    color: 'text-pink-500',
    bg: 'bg-pink-500/10',
    border: 'border-pink-500/20',
    description: 'Handles go-to-market activities and campaigns.',
    examples: 'Campaign briefs, launch plans, market positioning',
    capabilities: ['Web search', 'Read workspace', 'Compose HTML'],
    roles: ['marketing'],
  },
  {
    name: 'CRM Agent',
    icon: Users,
    color: 'text-orange-500',
    bg: 'bg-orange-500/10',
    border: 'border-orange-500/20',
    description: 'Manages relationships and tracks interactions.',
    examples: 'Customer follow-ups, relationship summaries, deal tracking',
    capabilities: ['Read platforms', 'Read workspace'],
    roles: ['crm'],
  },
  {
    name: 'Slack Bot',
    icon: MessageCircle,
    color: 'text-teal-500',
    bg: 'bg-teal-500/10',
    border: 'border-teal-500/20',
    description: 'Reads and writes Slack on your behalf.',
    examples: 'Channel summaries, automated replies, status updates',
    capabilities: ['Read Slack', 'Write Slack'],
    roles: ['slack_bot'],
  },
  {
    name: 'Notion Bot',
    icon: BookOpen,
    color: 'text-indigo-500',
    bg: 'bg-indigo-500/10',
    border: 'border-indigo-500/20',
    description: 'Reads and writes Notion on your behalf.',
    examples: 'Page updates, database entries, wiki maintenance',
    capabilities: ['Read Notion', 'Write Notion'],
    roles: ['notion_bot'],
  },
];

function getTypeForRole(role: string) {
  return WORKFORCE_TYPES.find(a => a.roles.includes(role)) || WORKFORCE_TYPES[0];
}

// =============================================================================
// Helpers
// =============================================================================

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

// =============================================================================
// Page
// =============================================================================

export default function AgentsListPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.agents.list()
      .then(setAgents)
      .catch(() => setAgents([]))
      .finally(() => setLoading(false));
  }, []);

  const activeAgents = agents.filter(a => a.status !== 'archived');

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-2">
          <Users className="w-6 h-6 text-muted-foreground" />
          <h1 className="text-2xl font-medium">Agents</h1>
        </div>
        <p className="text-sm text-muted-foreground max-w-2xl">
          Agents are persistent domain experts. Each has an identity, accumulated memory,
          and capabilities. They handle the full thinking chain: sense context, reason about
          it, and produce output. You describe what you need — the right agent gets created.
        </p>
      </div>

      {/* Workforce Types */}
      <div className="mb-12">
        <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-4">
          Workforce Types
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {WORKFORCE_TYPES.map(wtype => {
            const Icon = wtype.icon;
            return (
              <div
                key={wtype.name}
                className={cn(
                  'border rounded-xl p-5 space-y-3',
                  wtype.border,
                  wtype.bg,
                )}
              >
                <div className="flex items-center gap-2.5">
                  <Icon className={cn('w-5 h-5', wtype.color)} />
                  <h3 className="text-sm font-medium">{wtype.name}</h3>
                </div>
                <p className="text-sm text-muted-foreground">{wtype.description}</p>
                <p className="text-xs text-muted-foreground/60">{wtype.examples}</p>
                <div className="flex flex-wrap gap-1.5">
                  {wtype.capabilities.map(cap => (
                    <span
                      key={cap}
                      className="px-2 py-0.5 text-[10px] font-medium rounded-full border border-border bg-background text-muted-foreground"
                    >
                      {cap}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Your Agents */}
      <div>
        <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-4">
          Your Agents {activeAgents.length > 0 && <span className="opacity-60">({activeAgents.length})</span>}
        </h2>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
          </div>
        ) : activeAgents.length === 0 ? (
          <div className="text-center py-12 border border-border rounded-xl">
            <Users className="w-8 h-8 text-muted-foreground/20 mx-auto mb-2" />
            <p className="text-sm text-muted-foreground mb-1">No agents yet</p>
            <p className="text-xs text-muted-foreground/60 mb-4">
              Tell TP what work you need done.
            </p>
            <Link
              href="/tasks"
              className="inline-block px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              Go to tasks
            </Link>
          </div>
        ) : (
          <div className="border border-border rounded-xl overflow-hidden divide-y divide-border">
            {activeAgents.map(agent => {
              const wtype = getTypeForRole(agent.role);
              const Icon = wtype.icon;
              const isPaused = agent.status === 'paused';

              return (
                <Link
                  key={agent.id}
                  href={`/agents/${agent.id}`}
                  className="flex items-center justify-between p-4 hover:bg-muted/50 transition-colors group"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2.5 mb-1">
                      <Icon className={cn('w-4 h-4 shrink-0', wtype.color)} />
                      <span className="text-sm font-medium truncate">{agent.title}</span>
                      {isPaused && (
                        <span className="text-[10px] uppercase tracking-wider font-medium text-amber-500">
                          Paused
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-4 ml-[26px] text-xs text-muted-foreground">
                      <span>{wtype.name}</span>
                      {agent.last_run_at && (
                        <span>Last run: {formatRelativeTime(agent.last_run_at)}</span>
                      )}
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-muted-foreground/30 group-hover:text-foreground transition-colors shrink-0 ml-4" />
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
