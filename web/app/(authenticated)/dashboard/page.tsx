'use client';

/**
 * Supervision Dashboard — Agent Health + Composer Activity
 *
 * Landing page showing ambient awareness of autonomous agent work:
 * 1. Agent health grid (maturity, status, last run)
 * 2. Composer activity feed (lifecycle actions, bootstraps)
 * 3. Attention banner (auto-paused agents, failed runs)
 * 4. Summary stats (counts, maturity distribution)
 *
 * Replaced the ChatFirstDesk (now at /orchestrator).
 * See docs/design/SUPERVISION-DASHBOARD.md for design rationale.
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Loader2,
  MessageSquare,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Pause,
  ArrowRight,
  Sparkles,
  HeartPulse,
  Globe,
  Brain,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { ORCHESTRATOR_ROUTE } from '@/lib/routes';
import { getPlatformIcon } from '@/components/ui/PlatformIcons';
import { SKILL_LABELS } from '@/lib/constants/agents';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import type { Skill } from '@/types';

// =============================================================================
// Types
// =============================================================================

type DashboardData = Awaited<ReturnType<typeof api.dashboard.getSummary>>;
type AgentHealth = DashboardData['agents'][number];
type ComposerAction = DashboardData['composer_actions'][number];
type AttentionItem = DashboardData['attention'][number];

// =============================================================================
// Maturity badge
// =============================================================================

const MATURITY_CONFIG = {
  mature: { label: 'Mature', color: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' },
  developing: { label: 'Developing', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' },
  nascent: { label: 'Nascent', color: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400' },
};

function MaturityBadge({ maturity }: { maturity: string }) {
  const config = MATURITY_CONFIG[maturity as keyof typeof MATURITY_CONFIG] ?? MATURITY_CONFIG.nascent;
  return (
    <span className={cn('text-xs px-1.5 py-0.5 rounded font-medium', config.color)}>
      {config.label}
    </span>
  );
}

// =============================================================================
// Agent source icon helper
// =============================================================================

function getAgentSourceIcon(agent: AgentHealth): React.ReactNode {
  const providers: string[] = [];
  for (const s of agent.sources ?? []) {
    if (s.provider) {
      const p = s.provider === 'google'
        ? (s.resource_id?.startsWith('label:') ? 'gmail' : 'calendar')
        : s.provider;
      if (!providers.includes(p)) providers.push(p);
    }
  }
  if (providers.length === 0) {
    return agent.skill === 'research'
      ? <Globe className="w-4 h-4 text-muted-foreground" />
      : <Brain className="w-4 h-4 text-muted-foreground" />;
  }
  return getPlatformIcon(providers[0], 'w-4 h-4');
}

// =============================================================================
// Page Component
// =============================================================================

export default function DashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const result = await api.dashboard.getSummary();
        if (!cancelled) {
          setData(result);
          setLoading(false);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'Failed to load dashboard');
          setLoading(false);
        }
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-destructive">{error || 'Failed to load dashboard'}</p>
      </div>
    );
  }

  const { agents, composer_actions, attention, stats } = data;

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-4xl mx-auto px-4 md:px-6 py-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Dashboard</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Your agent workforce at a glance
            </p>
          </div>
          <button
            onClick={() => router.push(ORCHESTRATOR_ROUTE)}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            <MessageSquare className="w-4 h-4" />
            Ask Orchestrator
          </button>
        </div>

        {/* Attention Banner */}
        {attention.length > 0 && (
          <div className="space-y-2">
            {attention.map((item, i) => (
              <AttentionBanner key={i} item={item} onClick={() => router.push(`/agents/${item.agent_id}`)} />
            ))}
          </div>
        )}

        {/* Stats Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Active Agents" value={stats.active_agents} subtext={`${stats.total_agents} total`} />
          <StatCard label="Runs This Week" value={stats.runs_this_week} />
          <StatCard
            label="Mature"
            value={stats.maturity_distribution.mature}
            subtext={`${stats.maturity_distribution.developing} developing`}
          />
          <StatCard
            label="Nascent"
            value={stats.maturity_distribution.nascent}
            subtext="need more runs"
          />
        </div>

        {/* Agent Health Grid */}
        <section>
          <h2 className="text-lg font-semibold mb-3">Agent Health</h2>
          {agents.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <p>No agents yet.</p>
              <button
                onClick={() => router.push(`${ORCHESTRATOR_ROUTE}?create`)}
                className="mt-2 text-primary hover:underline text-sm"
              >
                Create your first agent
              </button>
            </div>
          ) : (
            <div className="grid gap-3">
              {agents.map((agent) => (
                <AgentHealthCard
                  key={agent.id}
                  agent={agent}
                  onClick={() => router.push(`/agents/${agent.id}`)}
                />
              ))}
            </div>
          )}
        </section>

        {/* Composer Activity Feed */}
        {composer_actions.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold mb-3">Composer Activity</h2>
            <div className="space-y-2">
              {composer_actions.map((action, i) => (
                <ComposerActionCard key={i} action={action} onClick={
                  action.agent_id ? () => router.push(`/agents/${action.agent_id}`) : undefined
                } />
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// Sub-components
// =============================================================================

function StatCard({ label, value, subtext }: { label: string; value: number; subtext?: string }) {
  return (
    <div className="p-4 rounded-lg border border-border bg-card">
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-sm font-medium text-muted-foreground">{label}</p>
      {subtext && <p className="text-xs text-muted-foreground mt-0.5">{subtext}</p>}
    </div>
  );
}

function AttentionBanner({ item, onClick }: { item: AttentionItem; onClick: () => void }) {
  const icon = item.type === 'auto_paused'
    ? <Pause className="w-4 h-4" />
    : item.type === 'failed'
      ? <XCircle className="w-4 h-4" />
      : <AlertTriangle className="w-4 h-4" />;

  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-3 p-3 rounded-lg border border-amber-200 bg-amber-50 dark:border-amber-900/50 dark:bg-amber-950/20 hover:bg-amber-100 dark:hover:bg-amber-950/30 text-left"
    >
      <span className="text-amber-600 dark:text-amber-400">{icon}</span>
      <span className="text-sm flex-1">{item.message}</span>
      <ArrowRight className="w-4 h-4 text-muted-foreground" />
    </button>
  );
}

function AgentHealthCard({ agent, onClick }: { agent: AgentHealth; onClick: () => void }) {
  const isPaused = agent.status === 'paused';
  const skillLabel = SKILL_LABELS[agent.skill as Skill] ?? agent.skill;

  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full flex items-center gap-3 p-3 rounded-lg border border-border hover:bg-muted/50 text-left transition-colors',
        isPaused && 'opacity-60',
      )}
    >
      {/* Platform icon + status dot */}
      <div className="relative shrink-0">
        {getAgentSourceIcon(agent)}
        <span className={cn(
          'absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full border border-background',
          isPaused ? 'bg-amber-400' : 'bg-green-500',
        )} />
      </div>

      {/* Title + skill */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium truncate">{agent.title}</span>
          {agent.origin && agent.origin !== 'user_configured' && (
            <span className="text-xs px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
              {agent.origin === 'composer' ? 'Composer' : agent.origin === 'system_bootstrap' ? 'Bootstrap' : 'Auto'}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
          <span>{skillLabel}</span>
          {agent.total_runs > 0 && (
            <>
              <span>&middot;</span>
              <span>{agent.total_runs} runs</span>
            </>
          )}
          {agent.approval_rate !== null && (
            <>
              <span>&middot;</span>
              <span>{Math.round(agent.approval_rate * 100)}% approved</span>
            </>
          )}
        </div>
      </div>

      {/* Maturity + last run */}
      <div className="flex items-center gap-2 shrink-0">
        {agent.edit_trend !== null && (
          agent.edit_trend < 0
            ? <span title="Improving (less editing)"><TrendingDown className="w-3.5 h-3.5 text-green-500" /></span>
            : agent.edit_trend > 0
              ? <span title="More editing needed"><TrendingUp className="w-3.5 h-3.5 text-amber-500" /></span>
              : null
        )}
        <MaturityBadge maturity={agent.maturity} />
        {agent.last_run_at && (
          <span className="text-xs text-muted-foreground whitespace-nowrap">
            {formatDistanceToNow(new Date(agent.last_run_at), { addSuffix: true })}
          </span>
        )}
      </div>
    </button>
  );
}

function ComposerActionCard({ action, onClick }: { action: ComposerAction; onClick?: () => void }) {
  const icon = action.type === 'created'
    ? <Sparkles className="w-4 h-4 text-amber-500" />
    : action.type === 'paused'
      ? <Pause className="w-4 h-4 text-amber-500" />
      : <HeartPulse className="w-4 h-4 text-muted-foreground" />;

  const Wrapper = onClick ? 'button' : 'div';

  return (
    <Wrapper
      onClick={onClick}
      className={cn(
        'flex items-start gap-3 p-3 rounded-lg border border-border text-left',
        onClick && 'hover:bg-muted/50 cursor-pointer',
      )}
    >
      <span className="mt-0.5 shrink-0">{icon}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm">{action.summary || `${action.type}: ${action.agent_title || 'Agent'}`}</p>
        <p className="text-xs text-muted-foreground mt-0.5">
          {formatDistanceToNow(new Date(action.created_at), { addSuffix: true })}
        </p>
      </div>
      {onClick && <ArrowRight className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />}
    </Wrapper>
  );
}
