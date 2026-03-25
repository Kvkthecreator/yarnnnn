'use client';

/**
 * Agents List — ADR-138/139
 *
 * Two sections:
 * 1. Agent archetypes explainer (what kinds of agents exist)
 * 2. Your agents (existing agent cards with links to /agents/[id])
 *
 * ADR-138: Four archetypes — monitor, researcher, producer, operator
 */

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Users,
  Loader2,
  ChevronRight,
  Eye,
  FlaskConical,
  PenTool,
  Cog,
} from 'lucide-react';
import type { Agent } from '@/types';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';

// =============================================================================
// Archetypes — ADR-138
// =============================================================================

const ARCHETYPES = [
  {
    name: 'Monitor',
    icon: Eye,
    color: 'text-green-500',
    bg: 'bg-green-500/10',
    border: 'border-green-500/20',
    description: 'Watches a domain and surfaces what matters.',
    examples: 'Slack recaps, competitor alerts, customer feedback tracking',
    capabilities: ['Read platforms', 'Web search', 'Alert on changes'],
    roles: ['monitor', 'digest', 'briefer', 'scout'],
  },
  {
    name: 'Researcher',
    icon: FlaskConical,
    color: 'text-blue-500',
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/20',
    description: 'Investigates topics with depth across sources.',
    examples: 'Market analysis, due diligence, trend reports',
    capabilities: ['Web search', 'Read workspace', 'Charts'],
    roles: ['researcher', 'analyst', 'research', 'synthesize'],
  },
  {
    name: 'Producer',
    icon: PenTool,
    color: 'text-purple-500',
    bg: 'bg-purple-500/10',
    border: 'border-purple-500/20',
    description: 'Creates deliverables from accumulated context.',
    examples: 'Investor updates, board decks, client reports',
    capabilities: ['Read workspace', 'Charts', 'Compose HTML'],
    roles: ['producer', 'drafter', 'writer', 'planner', 'prepare'],
  },
  {
    name: 'Operator',
    icon: Cog,
    color: 'text-orange-500',
    bg: 'bg-orange-500/10',
    border: 'border-orange-500/20',
    description: 'Takes actions on platforms. Coming soon.',
    examples: 'Post to Slack, update Notion, CRM updates',
    capabilities: ['Write to platforms', 'Read workspace'],
    roles: ['operator', 'act'],
  },
];

function getArchetypeForRole(role: string) {
  return ARCHETYPES.find(a => a.roles.includes(role)) || ARCHETYPES[0];
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

      {/* Archetypes */}
      <div className="mb-12">
        <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-4">
          Agent Archetypes
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {ARCHETYPES.map(archetype => {
            const Icon = archetype.icon;
            return (
              <div
                key={archetype.name}
                className={cn(
                  'border rounded-xl p-5 space-y-3',
                  archetype.border,
                  archetype.bg,
                )}
              >
                <div className="flex items-center gap-2.5">
                  <Icon className={cn('w-5 h-5', archetype.color)} />
                  <h3 className="text-sm font-medium">{archetype.name}</h3>
                </div>
                <p className="text-sm text-muted-foreground">{archetype.description}</p>
                <p className="text-xs text-muted-foreground/60">{archetype.examples}</p>
                <div className="flex flex-wrap gap-1.5">
                  {archetype.capabilities.map(cap => (
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
              Go to the workfloor and describe what work you need.
            </p>
            <Link
              href="/workfloor"
              className="inline-block px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              Go to workfloor
            </Link>
          </div>
        ) : (
          <div className="border border-border rounded-xl overflow-hidden divide-y divide-border">
            {activeAgents.map(agent => {
              const archetype = getArchetypeForRole(agent.role);
              const Icon = archetype.icon;
              const isPaused = agent.status === 'paused';

              return (
                <Link
                  key={agent.id}
                  href={`/agents/${agent.id}`}
                  className="flex items-center justify-between p-4 hover:bg-muted/50 transition-colors group"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2.5 mb-1">
                      <Icon className={cn('w-4 h-4 shrink-0', archetype.color)} />
                      <span className="text-sm font-medium truncate">{agent.title}</span>
                      {isPaused && (
                        <span className="text-[10px] uppercase tracking-wider font-medium text-amber-500">
                          Paused
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-4 ml-[26px] text-xs text-muted-foreground">
                      <span>{archetype.name}</span>
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
