'use client';

/**
 * Agents List Page — Source-First Presentation
 *
 * Flat agent list with platform icons as primary visual anchor.
 * Each card shows:
 * - Platform icon(s) derived from sources + active/paused dot
 * - Title + skill label + schedule status line
 * - Destination + delivery status + active/paused badges
 *
 * ADR-109: Scope × Skill × Trigger
 * AGENT-PRESENTATION-PRINCIPLES.md: Source-first mental model
 */

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Loader2,
  Play,
  Pause,
  Plus,
  CheckCircle2,
  XCircle,
  ArrowRight,
  Sparkles,
  Globe,
  Brain,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow } from 'date-fns';
import { getPlatformIcon } from '@/components/ui/PlatformIcons';
import { SKILL_LABELS } from '@/lib/constants/agents';
import { cn } from '@/lib/utils';
import type { Agent, AgentStatus } from '@/types';

// =============================================================================
// Helpers: sorting & grouping (AGENT-PRESENTATION-PRINCIPLES.md Principle 4)
// =============================================================================

/** Derive the source-affinity group key for an agent */
function getSourceAffinityGroup(agent: Agent): string {
  const providers: Record<string, true> = {};
  for (const s of agent.sources ?? []) {
    const p = s.provider as string | undefined;
    if (p) {
      if (p === 'google') {
        const rid = s.resource_id;
        if (rid && (['INBOX', 'SENT', 'IMPORTANT', 'STARRED'].includes(rid.toUpperCase()) || rid.startsWith('label:'))) {
          providers['gmail'] = true;
        } else {
          providers['calendar'] = true;
        }
      } else {
        providers[p] = true;
      }
    }
  }
  const keys = Object.keys(providers);
  if (keys.length === 0) return 'research';
  if (keys.length >= 2) return 'cross-platform';
  return keys[0]; // 'slack', 'gmail', 'notion', 'calendar'
}

const GROUP_ORDER: Record<string, number> = {
  slack: 0, gmail: 1, notion: 2, calendar: 3,
  'cross-platform': 4, research: 5,
};

const GROUP_LABELS: Record<string, string> = {
  slack: 'Slack',
  gmail: 'Gmail',
  notion: 'Notion',
  calendar: 'Calendar',
  'cross-platform': 'Cross-platform',
  research: 'Research & Knowledge',
};

/** Sort: active before paused → most recently delivered first → alphabetical */
function sortAgents(agents: Agent[]): Agent[] {
  return [...agents].sort((a, b) => {
    // Active before paused
    if (a.status !== b.status) {
      return a.status === 'paused' ? 1 : -1;
    }
    // Most recently delivered first
    const aTime = a.last_run_at ? new Date(a.last_run_at).getTime() : 0;
    const bTime = b.last_run_at ? new Date(b.last_run_at).getTime() : 0;
    if (aTime !== bTime) return bTime - aTime;
    // Alphabetical tiebreaker
    return (a.title || '').localeCompare(b.title || '');
  });
}

/** Group agents by source affinity, returning ordered groups */
function groupAgentsBySource(agents: Agent[]): { key: string; label: string; agents: Agent[] }[] {
  const grouped: Record<string, Agent[]> = {};
  for (const agent of agents) {
    const key = getSourceAffinityGroup(agent);
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(agent);
  }
  return Object.entries(grouped)
    .map(([key, groupAgents]) => ({
      key,
      label: GROUP_LABELS[key] || key,
      agents: sortAgents(groupAgents),
    }))
    .sort((a, b) => (GROUP_ORDER[a.key] ?? 99) - (GROUP_ORDER[b.key] ?? 99));
}

// =============================================================================
// Helpers
// =============================================================================

function getModeStatusLine(d: Agent): string {
  switch (d.mode) {
    case 'goal': {
      const goalStatus = d.agent_memory?.goal?.status;
      return goalStatus ? `Goal: ${goalStatus}` : 'Goal mode';
    }
    case 'reactive': {
      const count = d.agent_memory?.observations?.length || 0;
      return count > 0 ? `${count} observation${count === 1 ? '' : 's'}` : 'Watching';
    }
    case 'proactive':
    case 'coordinator': {
      if (d.proactive_next_review_at) {
        try {
          return `Next review ${formatDistanceToNow(new Date(d.proactive_next_review_at), { addSuffix: true })}`;
        } catch {
          // fall through
        }
      }
      return d.mode === 'coordinator' ? 'Coordinator' : 'Proactive';
    }
    default: {
      // recurring — show schedule
      const s = d.schedule;
      if (!s?.frequency) return 'No schedule';
      const time = s.time || '09:00';
      let timeStr = time;
      try {
        const [hour, minute] = time.split(':').map(Number);
        const ampm = hour >= 12 ? 'pm' : 'am';
        const h12 = hour > 12 ? hour - 12 : hour === 0 ? 12 : hour;
        timeStr = `${h12}:${minute.toString().padStart(2, '0')}${ampm}`;
      } catch {
        // keep original
      }
      switch (s.frequency) {
        case 'daily': return `Daily ${timeStr}`;
        case 'weekly': {
          const day = s.day ? s.day.charAt(0).toUpperCase() + s.day.slice(1, 3) : 'Mon';
          return `${day} ${timeStr}`;
        }
        case 'biweekly': return 'Biweekly';
        case 'monthly': return 'Monthly';
        default: return s.frequency || 'Custom';
      }
    }
  }
}

function formatDestination(d: Agent): string | null {
  const dest = d.destination;
  if (!dest) return null;
  const target = dest.target;
  if (target === 'dm') return 'Slack DM';
  if (target?.includes('@')) return target;
  if (target?.startsWith('#')) return target;
  if (target?.startsWith('C')) return `#${target.slice(0, 8)}`;
  return dest.platform || null;
}

// =============================================================================
// Helpers: platform icon derivation (AGENT-PRESENTATION-PRINCIPLES.md)
// =============================================================================

function getAgentPlatformIcon(agent: Agent): React.ReactNode {
  const providers: Record<string, true> = {};
  for (const s of agent.sources ?? []) {
    const p = s.provider as string | undefined;
    if (p) {
      if (p === 'google') {
        const rid = s.resource_id;
        if (rid && (['INBOX', 'SENT', 'IMPORTANT', 'STARRED'].includes(rid.toUpperCase()) || rid.startsWith('label:'))) {
          providers['gmail'] = true;
        } else {
          providers['calendar'] = true;
        }
      } else {
        providers[p] = true;
      }
    }
  }

  const keys = Object.keys(providers);
  if (keys.length === 0) {
    if (agent.skill === 'research') return <Globe className="w-5 h-5" />;
    return <Brain className="w-5 h-5" />;
  }
  if (keys.length === 1) {
    return getPlatformIcon(keys[0], 'w-5 h-5');
  }
  // Multi-platform: stack first two
  return (
    <div className="flex items-center -space-x-1.5">
      {keys.slice(0, 2).map((p) => (
        <span key={p} className="inline-block">{getPlatformIcon(p, 'w-4 h-4')}</span>
      ))}
    </div>
  );
}

/** Small icon for group headers */
function getAgentPlatformIconForGroup(groupKey: string): React.ReactNode {
  switch (groupKey) {
    case 'cross-platform': return <Globe className="w-4 h-4" />;
    case 'research': return <Brain className="w-4 h-4" />;
    default: return getPlatformIcon(groupKey, 'w-4 h-4');
  }
}

// =============================================================================
// Components
// =============================================================================

function AgentCard({
  agent,
  onClick,
}: {
  agent: Agent;
  onClick: () => void;
}) {
  const typeLabel = SKILL_LABELS[agent.skill] || agent.skill;
  const statusLine = getModeStatusLine(agent);
  const destination = formatDestination(agent);
  const latestStatus = agent.latest_version_status;

  const lastDeliveryTime = agent.last_run_at
    ? formatDistanceToNow(new Date(agent.last_run_at), { addSuffix: true })
    : null;

  return (
    <button
      onClick={onClick}
      className="w-full p-4 hover:bg-muted/50 transition-colors text-left"
    >
      <div className="flex items-start gap-3">
        {/* Source-first: platform icon as primary visual anchor */}
        <div className="mt-1 shrink-0 text-muted-foreground relative">
          {getAgentPlatformIcon(agent)}
          <span className={cn(
            'absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full border border-background',
            agent.status === 'paused' ? 'bg-amber-400' : 'bg-green-500'
          )} />
        </div>

        <div className="flex-1 min-w-0">
          {/* Title row */}
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-medium truncate">{agent.title}</h3>
            {agent.origin === 'coordinator_created' && (
              <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                <Sparkles className="w-2.5 h-2.5" />
                Auto
              </span>
            )}
            {destination && (
              <span className="ml-auto text-xs text-muted-foreground flex items-center gap-0.5 shrink-0">
                <ArrowRight className="w-3 h-3" />
                {destination}
              </span>
            )}
          </div>

          {/* Type + mode-aware status */}
          <p className="text-xs text-muted-foreground mt-0.5">
            {typeLabel} · {statusLine}
          </p>

          {/* Last delivery + badges */}
          <div className="flex items-center gap-3 mt-2">
            {lastDeliveryTime && (
              <span className="text-xs text-muted-foreground">
                Last: {lastDeliveryTime}
              </span>
            )}
            {/* Delivery status */}
            {latestStatus && (
              <>
                {(latestStatus === 'delivered' || latestStatus === 'approved' || latestStatus === 'staged') && (
                  <span className="inline-flex items-center gap-1 text-xs text-green-600">
                    <CheckCircle2 className="w-3 h-3" />
                    Delivered
                  </span>
                )}
                {(latestStatus === 'failed' || latestStatus === 'rejected') && (
                  <span className="inline-flex items-center gap-1 text-xs text-red-600">
                    <XCircle className="w-3 h-3" />
                    Failed
                  </span>
                )}
                {latestStatus === 'generating' && (
                  <span className="inline-flex items-center gap-1 text-xs text-blue-600">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    Generating
                  </span>
                )}
              </>
            )}
            {/* Schedule status */}
            {agent.status === 'paused' ? (
              <span className="inline-flex items-center gap-1 text-xs text-amber-600">
                <Pause className="w-3 h-3" />
                Paused
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-xs text-green-600">
                <Play className="w-3 h-3" />
                Active
              </span>
            )}
          </div>
        </div>
      </div>
    </button>
  );
}

// =============================================================================
// Main Page
// =============================================================================

export default function AgentsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [currentFilter, setCurrentFilter] = useState<AgentStatus | 'all'>('all');

  useEffect(() => {
    loadAgents();
  }, [currentFilter]);

  const loadAgents = async () => {
    setLoading(true);
    try {
      const statusParam = currentFilter !== 'all' ? currentFilter : undefined;
      const data = await api.agents.list(statusParam);
      setAgents(data);
    } catch (err) {
      console.error('Failed to load agents:', err);
    } finally {
      setLoading(false);
    }
  };

  const totalCount = agents.length;
  const groups = groupAgentsBySource(agents);

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-3xl mx-auto px-4 md:px-6 py-6">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold">Agents</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Recurring outputs your agent produces on schedule.{' '}
            <Link href="/dashboard?create" className="text-primary hover:underline">
              Ask your agent
            </Link>{' '}
            to create one.
          </p>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2 mb-6">
          {(['all', 'active', 'paused'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setCurrentFilter(f)}
              className={`px-3 py-1.5 text-xs rounded-full border ${
                currentFilter === f
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'border-border hover:bg-muted'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
          {!loading && (
            <span className="text-xs text-muted-foreground ml-2">
              {totalCount} agent{totalCount === 1 ? '' : 's'}
            </span>
          )}
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : totalCount === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground mb-4">No agents yet</p>
            <button
              onClick={() => router.push('/dashboard?create')}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
            >
              <Plus className="w-4 h-4" />
              Create your first agent
            </button>
          </div>
        ) : (
          /* Source-affinity grouping (Principle 4) */
          <div className="space-y-6">
            {groups.map((group) => (
              <div key={group.key}>
                <div className="flex items-center gap-2 mb-2 px-1">
                  <span className="text-muted-foreground">{getAgentPlatformIconForGroup(group.key)}</span>
                  <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{group.label}</h2>
                  <span className="text-[10px] text-muted-foreground">{group.agents.length}</span>
                </div>
                <div className="border border-border rounded-lg divide-y divide-border overflow-hidden">
                  {group.agents.map((d) => (
                    <AgentCard
                      key={d.id}
                      agent={d}
                      onClick={() => router.push(`/agents/${d.id}`)}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
